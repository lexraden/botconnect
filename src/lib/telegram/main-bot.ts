import { issueLoginToken, upsertAccount } from "@/lib/auth";
import { env } from "@/lib/env";
import { TelegramBot } from "./api";
import type { TgUpdate } from "./types";

export function mainBot(): TelegramBot | null {
  const token = env.mainBotToken;
  return token ? new TelegramBot(token) : null;
}

/**
 * The main bot in v2 is intentionally tiny: it authenticates users into the web dashboard
 * and sends notifications. All configuration UI moved to the web.
 */
export async function handleMainBotUpdate(update: TgUpdate): Promise<void> {
  const tg = mainBot();
  if (!tg) return;
  const m = update.message;
  if (!m?.from || m.chat.type !== "private") return;

  const text = m.text?.trim() ?? "";
  await upsertAccount(m.from);

  if (text.startsWith("/start") || text.startsWith("/login")) {
    const token = await issueLoginToken(m.from.id);
    const base = env.publicUrl ?? "";
    const url = `${base}/api/auth/magic?token=${token}`;
    await tg.sendMessage(
      m.chat.id,
      [
        "👋 <b>Bot Connect v2</b>",
        "",
        "Управление ботами теперь в веб-панели: подключение ботов, меню, рассылки, каналы и подписка.",
        "",
        "Ссылка для входа действует 10 минут:",
      ].join("\n"),
      {
        parse_mode: "HTML",
        reply_markup: { inline_keyboard: [[{ text: "🔐 Открыть панель", url }]] },
      },
    );
    return;
  }

  if (text.startsWith("/help")) {
    await tg.sendMessage(m.chat.id, "Команды:\n/login — получить ссылку для входа в панель\n/help — помощь");
    return;
  }

  await tg.sendMessage(m.chat.id, "Отправьте /login, чтобы получить ссылку для входа в панель.");
}

export async function setupMainBotWebhook(): Promise<boolean> {
  const tg = mainBot();
  const base = env.publicUrl;
  const secret = process.env.MAIN_BOT_WEBHOOK_SECRET;
  if (!tg || !base || !secret) return false;
  await tg.setWebhook(`${base}/api/telegram/main`, secret);
  await tg.setMyCommands([
    { command: "login", description: "Войти в панель" },
    { command: "help", description: "Помощь" },
  ]);
  return true;
}

/** Notify an owner via the main bot (best effort). */
export async function notifyOwner(telegramId: number, text: string) {
  const tg = mainBot();
  if (!tg) return;
  await tg.sendMessage(telegramId, text, { parse_mode: "HTML" }).catch(() => undefined);
}
