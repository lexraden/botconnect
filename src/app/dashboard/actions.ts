"use server";

import { and, eq, sql } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { db } from "@/db";
import { bots, botUsers, channelMessages, channels, mailings, menuButtons } from "@/db/schema";
import { requireAccount } from "@/lib/auth";
import { connectBot, deleteBot, getBotForOwner, getMailingQuota, registerWebhook, setBotActive } from "@/lib/bots";
import { createInvoice } from "@/lib/payments";

export type ActionState = { ok?: boolean; error?: string; message?: string } | undefined;

const str = (fd: FormData, k: string) => {
  const v = fd.get(k);
  return typeof v === "string" ? v.trim() : "";
};
const num = (fd: FormData, k: string) => Number(str(fd, k));
const opt = (v: string) => (v ? v : null);

async function ownedBot(botId: number) {
  const acc = await requireAccount();
  const bot = await getBotForOwner(botId, acc.id);
  if (!bot) throw new Error("Бот не найден");
  return { acc, bot };
}

// ---------- Bots ----------

export async function addBotAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const acc = await requireAccount();
  const res = await connectBot(acc.id, str(fd, "token"));
  if (!res.ok) return { error: res.error };
  revalidatePath("/dashboard");
  redirect(`/dashboard/bots/${res.bot.id}${res.webhook ? "" : "?webhook=failed"}`);
}

export async function toggleBotAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  await setBotActive(bot, !bot.isActive);
  revalidatePath("/dashboard");
  revalidatePath(`/dashboard/bots/${bot.id}`);
}

export async function reconnectWebhookAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  await registerWebhook(bot);
  revalidatePath(`/dashboard/bots/${bot.id}`);
}

export async function deleteBotAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  await deleteBot(bot);
  revalidatePath("/dashboard");
  redirect("/dashboard");
}

export async function updateBotSettingsAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const { bot } = await ownedBot(num(fd, "botId"));
  const forwardRaw = str(fd, "forwardChatId");
  const forwardChatId = forwardRaw ? Number(forwardRaw) : null;
  if (forwardRaw && !Number.isInteger(forwardChatId)) return { error: "ID чата должен быть числом (например -1001234567890)" };

  await db
    .update(bots)
    .set({
      greetingText: opt(str(fd, "greetingText")),
      greetingFileId: opt(str(fd, "greetingFileId")),
      greetingFileType: opt(str(fd, "greetingFileType")),
      forwardChatId,
    })
    .where(eq(bots.id, bot.id));

  revalidatePath(`/dashboard/bots/${bot.id}`);
  return { ok: true, message: "Настройки сохранены" };
}

// ---------- Buttons ----------

export async function saveButtonAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const { bot } = await ownedBot(num(fd, "botId"));
  const id = str(fd, "id") ? num(fd, "id") : null;
  const text = str(fd, "text");
  if (!text) return { error: "Текст кнопки обязателен" };
  const kind = str(fd, "kind") === "reply" ? "reply" : "inline";
  const action = ["send", "edit", "url"].includes(str(fd, "action")) ? str(fd, "action") : "send";
  const url = opt(str(fd, "url"));
  if (action === "url" && !/^https?:\/\//.test(url ?? "")) return { error: "Для URL-кнопки нужна ссылка http(s)://" };
  let command = opt(str(fd, "command"));
  if (command && !command.startsWith("/")) command = `/${command}`;
  const parentRaw = str(fd, "parentId");
  const parentId = parentRaw ? Number(parentRaw) : null;

  const values = {
    botId: bot.id,
    text,
    kind,
    action,
    replyText: opt(str(fd, "replyText")),
    fileId: opt(str(fd, "fileId")),
    fileType: opt(str(fd, "fileType")),
    url,
    command,
    parentId: kind === "inline" ? parentId : null,
    position: Number(str(fd, "position") || 0),
  };

  if (id) {
    await db.update(menuButtons).set(values).where(and(eq(menuButtons.id, id), eq(menuButtons.botId, bot.id)));
  } else {
    await db.insert(menuButtons).values(values);
  }
  revalidatePath(`/dashboard/bots/${bot.id}/buttons`);
  return { ok: true, message: id ? "Кнопка обновлена" : "Кнопка добавлена" };
}

export async function deleteButtonAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  const id = num(fd, "id");
  await db.update(menuButtons).set({ parentId: null }).where(and(eq(menuButtons.parentId, id), eq(menuButtons.botId, bot.id)));
  await db.delete(menuButtons).where(and(eq(menuButtons.id, id), eq(menuButtons.botId, bot.id)));
  revalidatePath(`/dashboard/bots/${bot.id}/buttons`);
}

// ---------- Mailings ----------

export async function createMailingAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const { bot } = await ownedBot(num(fd, "botId"));
  const text = opt(str(fd, "text"));
  const fileId = opt(str(fd, "fileId"));
  if (!text && !fileId) return { error: "Нужен текст или file_id вложения" };
  const buttonText = opt(str(fd, "buttonText"));
  const buttonUrl = opt(str(fd, "buttonUrl"));
  if ((buttonText && !buttonUrl) || (!buttonText && buttonUrl)) return { error: "Для кнопки нужны и текст, и ссылка" };

  const when = str(fd, "scheduledAt");
  const scheduledAt = when ? new Date(when) : new Date();
  if (Number.isNaN(scheduledAt.getTime())) return { error: "Некорректная дата" };

  const quota = await getMailingQuota(bot.id);
  if (quota.remaining <= 0) return { error: `Дневной лимит ${quota.dailyLimit} сообщений исчерпан` };

  await db.insert(mailings).values({
    botId: bot.id,
    text,
    fileId,
    fileType: opt(str(fd, "fileType")),
    buttonText,
    buttonUrl,
    scheduledAt,
    status: "scheduled",
  });
  revalidatePath(`/dashboard/bots/${bot.id}/mailings`);
  return { ok: true, message: when ? "Рассылка запланирована" : "Рассылка поставлена в очередь (отправится в ближайшую минуту)" };
}

export async function cancelMailingAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  await db
    .update(mailings)
    .set({ status: "cancelled", finishedAt: new Date() })
    .where(and(eq(mailings.id, num(fd, "id")), eq(mailings.botId, bot.id), eq(mailings.status, "scheduled")));
  revalidatePath(`/dashboard/bots/${bot.id}/mailings`);
}

// ---------- Users ----------

export async function toggleBanAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  await db
    .update(botUsers)
    .set({ isBanned: sql`not ${botUsers.isBanned}` })
    .where(and(eq(botUsers.id, num(fd, "id")), eq(botUsers.botId, bot.id)));
  revalidatePath(`/dashboard/bots/${bot.id}/users`);
}

// ---------- Channels ----------

export async function updateChannelAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  const id = num(fd, "id");
  await db
    .update(channels)
    .set({
      autoAccept: fd.get("autoAccept") === "on",
      captcha: fd.get("captcha") === "on",
      captchaButtonText: opt(str(fd, "captchaButtonText")),
    })
    .where(and(eq(channels.id, id), eq(channels.botId, bot.id)));
  revalidatePath(`/dashboard/bots/${bot.id}/channels`);
}

export async function saveChannelMessageAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const { bot } = await ownedBot(num(fd, "botId"));
  const channelId = num(fd, "channelId");
  const [ch] = await db.select().from(channels).where(and(eq(channels.id, channelId), eq(channels.botId, bot.id))).limit(1);
  if (!ch) return { error: "Канал не найден" };
  const kind = ["greeting", "farewell", "captcha"].includes(str(fd, "kind")) ? str(fd, "kind") : "greeting";
  const languageCode = str(fd, "languageCode") || "any";

  // buttons: lines "Текст | https://url | row"
  const buttons = str(fd, "buttons")
    .split("\n")
    .map((l) => l.split("|").map((s) => s.trim()))
    .filter((p) => p.length >= 2 && p[0] && /^https?:\/\//.test(p[1]))
    .map((p, i) => ({ text: p[0], url: p[1], row: Number(p[2]) || i + 1 }));

  const values = { text: opt(str(fd, "text")), fileId: opt(str(fd, "fileId")), fileType: opt(str(fd, "fileType")), buttons };
  await db
    .insert(channelMessages)
    .values({ channelId, kind, languageCode, ...values })
    .onConflictDoUpdate({ target: [channelMessages.channelId, channelMessages.kind, channelMessages.languageCode], set: values });
  revalidatePath(`/dashboard/bots/${bot.id}/channels`);
  return { ok: true, message: "Сообщение сохранено" };
}

export async function deleteChannelMessageAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  const id = num(fd, "id");
  const [row] = await db
    .select({ id: channelMessages.id })
    .from(channelMessages)
    .innerJoin(channels, eq(channels.id, channelMessages.channelId))
    .where(and(eq(channelMessages.id, id), eq(channels.botId, bot.id)))
    .limit(1);
  if (row) await db.delete(channelMessages).where(eq(channelMessages.id, id));
  revalidatePath(`/dashboard/bots/${bot.id}/channels`);
}

export async function removeChannelAction(fd: FormData) {
  const { bot } = await ownedBot(num(fd, "botId"));
  await db.delete(channels).where(and(eq(channels.id, num(fd, "id")), eq(channels.botId, bot.id)));
  revalidatePath(`/dashboard/bots/${bot.id}/channels`);
}

// ---------- Subscription ----------

export async function createInvoiceAction(_prev: ActionState, fd: FormData): Promise<ActionState> {
  const { acc, bot } = await ownedBot(num(fd, "botId"));
  try {
    const payment = await createInvoice(acc.id, bot.id, num(fd, "months"));
    revalidatePath(`/dashboard/bots/${bot.id}/subscription`);
    if (payment.payUrl) redirect(payment.payUrl);
    return { ok: true, message: "Счёт создан" };
  } catch (e) {
    if ((e as Error & { digest?: string }).digest?.startsWith("NEXT_REDIRECT")) throw e;
    return { error: (e as Error).message };
  }
}
