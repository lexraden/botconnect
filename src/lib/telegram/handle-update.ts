import { and, asc, eq, isNull, sql } from "drizzle-orm";
import { db } from "@/db";
import {
  accounts,
  bots,
  botUsers,
  channelMessages,
  channels,
  forwardedMessages,
  menuButtons,
  pendingJoinRequests,
  processedUpdates,
  type Bot,
  type MenuButton,
} from "@/db/schema";
import { botClient } from "@/lib/bots";
import { escapeHtml, TelegramBot, TelegramError } from "./api";
import {
  displayName,
  extractFile,
  type InlineKeyboardMarkup,
  type ReplyKeyboardMarkup,
  type ReplyMarkup,
  type TgCallbackQuery,
  type TgChatJoinRequest,
  type TgChatMemberUpdated,
  type TgMessage,
  type TgUpdate,
  type TgUser,
} from "./types";

/**
 * Entry point: process a single update for a user bot.
 * Fully stateless: every request may land on a different instance.
 */
export async function handleBotUpdate(bot: Bot, update: TgUpdate): Promise<void> {
  // Idempotency: Telegram retries the same update on timeouts / non-200.
  const inserted = await db
    .insert(processedUpdates)
    .values({ botId: bot.id, updateId: update.update_id })
    .onConflictDoNothing()
    .returning({ updateId: processedUpdates.updateId });
  if (inserted.length === 0) return;

  const tg = botClient(bot);

  if (update.message) return handleMessage(bot, tg, update.message);
  if (update.callback_query) return handleCallback(bot, tg, update.callback_query);
  if (update.my_chat_member) return handleMyChatMember(bot, tg, update.my_chat_member);
  if (update.chat_member) return handleChatMember(bot, tg, update.chat_member);
  if (update.chat_join_request) return handleJoinRequest(bot, tg, update.chat_join_request);
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

async function handleMessage(bot: Bot, tg: TelegramBot, m: TgMessage) {
  const from = m.from;
  if (!from || from.is_bot) return;

  // Admin chat (group/topic) where feedback is forwarded: handle replies
  if (m.chat.type !== "private") {
    if (bot.forwardChatId && m.chat.id === bot.forwardChatId && m.reply_to_message) {
      await handleAdminReply(bot, tg, m);
    }
    return;
  }

  const user = await upsertUser(bot.id, from);
  if (user.isBanned) return;

  const text = m.text?.trim() ?? "";

  if (text.startsWith("/start")) {
    const payload = text.split(/\s+/)[1];
    if (payload?.startsWith("captcha_")) {
      // deep-link fallback from captcha message
      return;
    }
    return sendGreeting(bot, tg, m.chat.id);
  }

  // Custom command bound to a button (/prices etc.)
  if (text.startsWith("/")) {
    const [button] = await db
      .select()
      .from(menuButtons)
      .where(and(eq(menuButtons.botId, bot.id), eq(menuButtons.command, text.split("@")[0])))
      .limit(1);
    if (button) return sendButtonContent(bot, tg, m.chat.id, button);
  }

  // Reply-keyboard button pressed
  if (text) {
    const [button] = await db
      .select()
      .from(menuButtons)
      .where(and(eq(menuButtons.botId, bot.id), eq(menuButtons.kind, "reply"), eq(menuButtons.text, text)))
      .limit(1);
    if (button) return sendButtonContent(bot, tg, m.chat.id, button);
  }

  // Otherwise — feedback: forward to owner
  await forwardToAdmin(bot, tg, m, from);
}

async function forwardToAdmin(bot: Bot, tg: TelegramBot, m: TgMessage, from: TgUser) {
  const target = bot.forwardChatId;
  if (!target) {
    // Owner hasn't set forward chat yet – fall back to owner's private chat with THIS bot is impossible
    // (bot can't initiate), so just acknowledge.
    await tg.sendMessage(m.chat.id, "✅ Сообщение получено. Мы ответим вам в ближайшее время.").catch(() => undefined);
    return;
  }

  const header =
    `👤 <b>${escapeHtml(displayName(from))}</b>` +
    (from.username ? ` (@${escapeHtml(from.username)})` : "") +
    ` · <code>${from.id}</code>\n<i>Ответьте на это сообщение, чтобы написать пользователю</i>`;

  try {
    const copied = await tg.copyMessage(target, m.chat.id, m.message_id, {
      reply_markup: {
        inline_keyboard: [[{ text: "🚫 Забанить", callback_data: `ban:${from.id}` }]],
      },
    });
    await tg.sendMessage(target, header, {
      parse_mode: "HTML",
      reply_parameters: { message_id: copied.message_id },
    }).catch(() => undefined);

    await db.insert(forwardedMessages).values({
      botId: bot.id,
      adminChatId: target,
      adminMessageId: copied.message_id,
      userTelegramId: from.id,
      userMessageId: m.message_id,
    });
    await db.update(bots).set({ receivedCount: sql`${bots.receivedCount} + 1` }).where(eq(bots.id, bot.id));
  } catch (e) {
    console.error(`[bot ${bot.id}] forward failed:`, (e as Error).message);
  }
}

async function handleAdminReply(bot: Bot, tg: TelegramBot, m: TgMessage) {
  const replyTo = m.reply_to_message!;
  // Admin may reply either to the copied message or to our header message (which itself replies to the copy)
  const candidates = [replyTo.message_id, replyTo.reply_to_message?.message_id].filter((x): x is number => Boolean(x));

  let mapping: typeof forwardedMessages.$inferSelect | undefined;
  for (const id of candidates) {
    [mapping] = await db
      .select()
      .from(forwardedMessages)
      .where(and(eq(forwardedMessages.botId, bot.id), eq(forwardedMessages.adminChatId, m.chat.id), eq(forwardedMessages.adminMessageId, id)))
      .limit(1);
    if (mapping) break;
  }
  if (!mapping) return;

  const text = m.text?.trim();
  if (text === "/ban") {
    await setBanned(bot.id, mapping.userTelegramId, true);
    await tg.sendMessage(m.chat.id, `🚫 Пользователь ${mapping.userTelegramId} заблокирован.`).catch(() => undefined);
    return;
  }
  if (text === "/unban") {
    await setBanned(bot.id, mapping.userTelegramId, false);
    await tg.sendMessage(m.chat.id, `✅ Пользователь ${mapping.userTelegramId} разблокирован.`).catch(() => undefined);
    return;
  }
  if (text === "/fileid") {
    const file = extractFile(replyTo);
    await tg
      .sendMessage(m.chat.id, file ? `<b>${file.fileType}</b>\n<code>${escapeHtml(file.fileId)}</code>` : "В этом сообщении нет вложения.", { parse_mode: "HTML" })
      .catch(() => undefined);
    return;
  }

  try {
    await tg.copyMessage(mapping.userTelegramId, m.chat.id, m.message_id, {
      reply_parameters: { message_id: mapping.userMessageId, allow_sending_without_reply: true },
    });
    await db.update(bots).set({ repliedCount: sql`${bots.repliedCount} + 1` }).where(eq(bots.id, bot.id));
  } catch (e) {
    const err = e as TelegramError;
    if (err instanceof TelegramError && err.isUnreachable) {
      await markBlocked(bot.id, mapping.userTelegramId, true);
      await tg.sendMessage(m.chat.id, "⚠️ Пользователь заблокировал бота, сообщение не доставлено.").catch(() => undefined);
    } else {
      await tg.sendMessage(m.chat.id, `⚠️ Не удалось отправить: ${escapeHtml(err.message)}`, { parse_mode: "HTML" }).catch(() => undefined);
    }
  }
}

// ---------------------------------------------------------------------------
// Greeting & menu
// ---------------------------------------------------------------------------

async function loadButtons(botId: number) {
  return db.select().from(menuButtons).where(eq(menuButtons.botId, botId)).orderBy(asc(menuButtons.position), asc(menuButtons.id));
}

function buildInline(buttons: MenuButton[], parentId: number | null, backTo?: number | null): InlineKeyboardMarkup | undefined {
  const rows: InlineKeyboardMarkup["inline_keyboard"] = [];
  const level = buttons.filter((b) => b.kind === "inline" && (b.parentId ?? null) === parentId);
  for (let i = 0; i < level.length; i += 2) {
    rows.push(
      level.slice(i, i + 2).map((b) =>
        b.action === "url" && b.url ? { text: b.text, url: b.url } : { text: b.text, callback_data: `btn:${b.id}` },
      ),
    );
  }
  if (parentId !== null) rows.push([{ text: "⬅️ Назад", callback_data: backTo ? `btn:${backTo}` : "menu:root" }]);
  return rows.length ? { inline_keyboard: rows } : undefined;
}

function buildReplyKeyboard(buttons: MenuButton[]): ReplyKeyboardMarkup | undefined {
  const reply = buttons.filter((b) => b.kind === "reply");
  if (!reply.length) return undefined;
  const rows: { text: string }[][] = [];
  for (let i = 0; i < reply.length; i += 2) rows.push(reply.slice(i, i + 2).map((b) => ({ text: b.text })));
  return { keyboard: rows, resize_keyboard: true, is_persistent: true };
}

async function sendGreeting(bot: Bot, tg: TelegramBot, chatId: number) {
  const buttons = await loadButtons(bot.id);
  const inline = buildInline(buttons, null);
  const reply = buildReplyKeyboard(buttons);
  const text = bot.greetingText || `Здравствуйте! Напишите ваше сообщение, и мы ответим вам здесь.`;

  // Telegram allows only one reply_markup per message: send reply keyboard first (if any), then inline menu.
  if (reply && inline) {
    await tg.sendContent(chatId, { text, fileId: bot.greetingFileId, fileType: bot.greetingFileType }, reply);
    await tg.sendMessage(chatId, "Меню:", { reply_markup: inline });
  } else {
    await tg.sendContent(chatId, { text, fileId: bot.greetingFileId, fileType: bot.greetingFileType }, inline ?? reply);
  }
}

async function sendButtonContent(bot: Bot, tg: TelegramBot, chatId: number, button: MenuButton, editMessageId?: number) {
  const all = await loadButtons(bot.id);
  const children = buildInline(all, button.id, button.parentId);
  const markup: ReplyMarkup | undefined = children;
  const content = { text: button.replyText || button.text, fileId: button.fileId, fileType: button.fileType };

  if (button.action === "edit" && editMessageId && !button.fileId) {
    try {
      await tg.editMessageText(chatId, editMessageId, content.text, { parse_mode: "HTML", reply_markup: markup });
      return;
    } catch {
      /* message may contain media -> fall back to a new message */
    }
  }
  await tg.sendContent(chatId, content, markup);
}

// ---------------------------------------------------------------------------
// Callbacks
// ---------------------------------------------------------------------------

async function handleCallback(bot: Bot, tg: TelegramBot, cq: TgCallbackQuery) {
  const data = cq.data ?? "";
  const chatId = cq.message?.chat.id;

  if (data.startsWith("btn:") && chatId) {
    const id = Number(data.slice(4));
    const [button] = await db.select().from(menuButtons).where(and(eq(menuButtons.id, id), eq(menuButtons.botId, bot.id))).limit(1);
    await tg.answerCallbackQuery(cq.id);
    if (button) await sendButtonContent(bot, tg, chatId, button, cq.message?.message_id);
    return;
  }

  if (data === "menu:root" && chatId) {
    await tg.answerCallbackQuery(cq.id);
    const buttons = await loadButtons(bot.id);
    const inline = buildInline(buttons, null);
    if (cq.message && inline) {
      await tg.editMessageText(chatId, cq.message.message_id, bot.greetingText || "Меню:", { parse_mode: "HTML", reply_markup: inline }).catch(() => sendGreeting(bot, tg, chatId));
    }
    return;
  }

  if (data.startsWith("ban:") && chatId && chatId === bot.forwardChatId) {
    const userId = Number(data.slice(4));
    await setBanned(bot.id, userId, true);
    await tg.answerCallbackQuery(cq.id, "Пользователь заблокирован");
    return;
  }

  if (data.startsWith("captcha:")) {
    const channelId = Number(data.slice(8));
    await resolveCaptcha(bot, tg, cq, channelId);
    return;
  }

  await tg.answerCallbackQuery(cq.id);
}

// ---------------------------------------------------------------------------
// Membership: block tracking, channel connection, greetings/farewells
// ---------------------------------------------------------------------------

async function handleMyChatMember(bot: Bot, tg: TelegramBot, ev: TgChatMemberUpdated) {
  const status = ev.new_chat_member.status;

  if (ev.chat.type === "private") {
    await markBlocked(bot.id, ev.from.id, status === "kicked");
    return;
  }

  // Bot added as admin to a channel/supergroup by its owner -> connect
  if (ev.chat.type === "channel" || ev.chat.type === "supergroup" || ev.chat.type === "group") {
    const connected = status === "administrator";
    const [ownerAccount] = await db.select({ telegramId: accounts.telegramId }).from(accounts).where(eq(accounts.id, bot.ownerId)).limit(1);
    const isOwner = ownerAccount?.telegramId === ev.from.id;

    if (connected && !isOwner) {
      // Only the bot's owner may connect channels; leave quietly otherwise
      await tg.call("leaveChat", { chat_id: ev.chat.id }).catch(() => undefined);
      return;
    }

    if (connected) {
      await db
        .insert(channels)
        .values({ botId: bot.id, chatId: ev.chat.id, title: ev.chat.title ?? String(ev.chat.id), type: ev.chat.type === "channel" ? "channel" : "supergroup", isConnected: true })
        .onConflictDoUpdate({
          target: [channels.botId, channels.chatId],
          set: { title: ev.chat.title ?? String(ev.chat.id), isConnected: true },
        });
      // First "/start@bot" in a group used to bind forward chat in v1; in v2 it's set from the dashboard
      // but we also auto-bind if forwarding isn't configured yet and this is a group.
      if (!bot.forwardChatId && ev.chat.type !== "channel") {
        await db.update(bots).set({ forwardChatId: ev.chat.id }).where(and(eq(bots.id, bot.id), isNull(bots.forwardChatId)));
        await tg.sendMessage(ev.chat.id, "✅ Бот подключён. Сообщения пользователей будут приходить сюда — отвечайте на них reply'ем.").catch(() => undefined);
      }
    } else if (status === "left" || status === "kicked" || status === "member") {
      await db.update(channels).set({ isConnected: false }).where(and(eq(channels.botId, bot.id), eq(channels.chatId, ev.chat.id)));
    }
  }
}

async function handleChatMember(bot: Bot, tg: TelegramBot, ev: TgChatMemberUpdated) {
  const [channel] = await db.select().from(channels).where(and(eq(channels.botId, bot.id), eq(channels.chatId, ev.chat.id))).limit(1);
  if (!channel || !channel.isConnected) return;

  const was = ev.old_chat_member.status;
  const now = ev.new_chat_member.status;
  const joined = (was === "left" || was === "kicked") && (now === "member" || now === "administrator" || now === "restricted");
  const left = (was === "member" || was === "administrator" || was === "restricted") && (now === "left" || now === "kicked");
  const user = ev.new_chat_member.user;

  if (joined) await sendChannelMessage(tg, channel.id, "greeting", user);
  else if (left) await sendChannelMessage(tg, channel.id, "farewell", user);
}

async function handleJoinRequest(bot: Bot, tg: TelegramBot, req: TgChatJoinRequest) {
  const [channel] = await db.select().from(channels).where(and(eq(channels.botId, bot.id), eq(channels.chatId, req.chat.id))).limit(1);
  if (!channel || !channel.isConnected || !channel.autoAccept) return;

  await upsertUser(bot.id, req.from);

  if (channel.captcha) {
    await db.insert(pendingJoinRequests).values({ channelId: channel.id, userTelegramId: req.from.id }).onConflictDoNothing();
    const msg = await getChannelMessage(channel.id, "captcha", req.from.language_code);
    const text = msg?.text || `Чтобы вступить в «${escapeHtml(req.chat.title ?? "канал")}», подтвердите, что вы не робот.`;
    const markup: InlineKeyboardMarkup = { inline_keyboard: [[{ text: channel.captchaButtonText || "✅ Я не робот", callback_data: `captcha:${channel.id}` }]] };
    await tg.sendContent(req.user_chat_id, { text, fileId: msg?.fileId, fileType: msg?.fileType }, markup).catch(() => undefined);
    return;
  }

  try {
    await tg.approveChatJoinRequest(req.chat.id, req.from.id);
    await sendChannelMessage(tg, channel.id, "greeting", req.from, req.user_chat_id);
  } catch (e) {
    console.error(`[bot ${bot.id}] approve failed:`, (e as Error).message);
  }
}

async function resolveCaptcha(bot: Bot, tg: TelegramBot, cq: TgCallbackQuery, channelId: number) {
  const [channel] = await db.select().from(channels).where(and(eq(channels.id, channelId), eq(channels.botId, bot.id))).limit(1);
  if (!channel) return tg.answerCallbackQuery(cq.id, "Канал не найден");

  const deleted = await db
    .delete(pendingJoinRequests)
    .where(and(eq(pendingJoinRequests.channelId, channelId), eq(pendingJoinRequests.userTelegramId, cq.from.id)))
    .returning();
  if (!deleted.length) return tg.answerCallbackQuery(cq.id, "Заявка уже обработана");

  try {
    await tg.approveChatJoinRequest(channel.chatId, cq.from.id);
    await tg.answerCallbackQuery(cq.id, "Заявка одобрена ✅");
    if (cq.message) await tg.deleteMessage(cq.message.chat.id, cq.message.message_id);
    await sendChannelMessage(tg, channel.id, "greeting", cq.from, cq.from.id);
  } catch (e) {
    await tg.answerCallbackQuery(cq.id, `Ошибка: ${(e as Error).message}`);
  }
}

async function getChannelMessage(channelId: number, kind: string, lang?: string) {
  const rows = await db.select().from(channelMessages).where(and(eq(channelMessages.channelId, channelId), eq(channelMessages.kind, kind)));
  return rows.find((r) => r.languageCode === (lang ?? "")) ?? rows.find((r) => r.languageCode === "any") ?? rows[0] ?? null;
}

async function sendChannelMessage(tg: TelegramBot, channelId: number, kind: "greeting" | "farewell", user: TgUser, chatId?: number) {
  const msg = await getChannelMessage(channelId, kind, user.language_code);
  if (!msg || (!msg.text && !msg.fileId)) return;
  const text = (msg.text ?? "").replace(/\{name\}/g, escapeHtml(displayName(user))).replace(/\{username\}/g, user.username ? `@${user.username}` : escapeHtml(displayName(user)));
  const rowsMap = new Map<number, { text: string; url: string }[]>();
  for (const b of msg.buttons ?? []) {
    if (!rowsMap.has(b.row)) rowsMap.set(b.row, []);
    rowsMap.get(b.row)!.push({ text: b.text, url: b.url });
  }
  const markup: InlineKeyboardMarkup | undefined = rowsMap.size ? { inline_keyboard: [...rowsMap.entries()].sort((a, b) => a[0] - b[0]).map(([, r]) => r) } : undefined;
  await tg.sendContent(chatId ?? user.id, { text, fileId: msg.fileId, fileType: msg.fileType }, markup).catch(() => undefined);
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

async function upsertUser(botId: number, u: TgUser) {
  const [user] = await db
    .insert(botUsers)
    .values({
      botId,
      telegramId: u.id,
      username: u.username,
      firstName: u.first_name,
      lastName: u.last_name,
      languageCode: u.language_code,
    })
    .onConflictDoUpdate({
      target: [botUsers.botId, botUsers.telegramId],
      set: { username: u.username, firstName: u.first_name, lastName: u.last_name, languageCode: u.language_code, isBlocked: false, lastSeenAt: new Date() },
    })
    .returning();
  return user;
}

export async function markBlocked(botId: number, telegramId: number, blocked: boolean) {
  await db.update(botUsers).set({ isBlocked: blocked }).where(and(eq(botUsers.botId, botId), eq(botUsers.telegramId, telegramId)));
}

async function setBanned(botId: number, telegramId: number, banned: boolean) {
  await db.update(botUsers).set({ isBanned: banned }).where(and(eq(botUsers.botId, botId), eq(botUsers.telegramId, telegramId)));
}

/** Utility for the webhook route to touch the "last seen" timestamp cheaply. */
export async function touchBot(botId: number) {
  await db.update(bots).set({ lastWebhookAt: new Date() }).where(eq(bots.id, botId));
}

export { extractFile };
