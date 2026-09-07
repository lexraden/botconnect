import type { FileType, ReplyMarkup, TgMessage, TgUser } from "./types";

export class TelegramError extends Error {
  constructor(
    public readonly code: number,
    public readonly description: string,
    public readonly retryAfter?: number,
  ) {
    super(`Telegram API ${code}: ${description}`);
  }
  /** User blocked the bot / deactivated account / chat not found */
  get isUnreachable() {
    return this.code === 403 || (this.code === 400 && /chat not found|user is deactivated|bot was blocked/i.test(this.description));
  }
}

interface ApiResponse<T> {
  ok: boolean;
  result?: T;
  description?: string;
  error_code?: number;
  parameters?: { retry_after?: number };
}

/**
 * Tiny stateless Bot API client. No long-lived sessions, safe for serverless.
 * Automatically honours `retry_after` once for 429.
 */
export class TelegramBot {
  private readonly base: string;

  constructor(readonly token: string) {
    this.base = `https://api.telegram.org/bot${token}`;
  }

  async call<T = unknown>(method: string, params: Record<string, unknown> = {}, retry = true): Promise<T> {
    const body: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue;
      body[k] = typeof v === "object" ? JSON.stringify(v) : v;
    }
    const res = await fetch(`${this.base}/${method}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(20_000),
    });
    const json = (await res.json().catch(() => ({ ok: false, description: "Invalid JSON" }))) as ApiResponse<T>;
    if (!json.ok) {
      const retryAfter = json.parameters?.retry_after;
      if (json.error_code === 429 && retryAfter && retry && retryAfter <= 5) {
        await new Promise((r) => setTimeout(r, retryAfter * 1000));
        return this.call<T>(method, params, false);
      }
      throw new TelegramError(json.error_code ?? res.status, json.description ?? "Unknown error", retryAfter);
    }
    return json.result as T;
  }

  getMe() {
    return this.call<TgUser & { can_join_groups: boolean }>("getMe");
  }

  setWebhook(url: string, secretToken: string) {
    return this.call<boolean>("setWebhook", {
      url,
      secret_token: secretToken,
      drop_pending_updates: true,
      allowed_updates: ["message", "callback_query", "my_chat_member", "chat_member", "chat_join_request"],
    });
  }

  deleteWebhook() {
    return this.call<boolean>("deleteWebhook", { drop_pending_updates: true });
  }

  setMyCommands(commands: { command: string; description: string }[]) {
    return this.call<boolean>("setMyCommands", { commands });
  }

  sendMessage(chatId: number, text: string, extra: Record<string, unknown> = {}) {
    return this.call<TgMessage>("sendMessage", { chat_id: chatId, text, ...extra });
  }

  editMessageText(chatId: number, messageId: number, text: string, extra: Record<string, unknown> = {}) {
    return this.call<TgMessage>("editMessageText", { chat_id: chatId, message_id: messageId, text, ...extra });
  }

  deleteMessage(chatId: number, messageId: number) {
    return this.call<boolean>("deleteMessage", { chat_id: chatId, message_id: messageId }).catch(() => false);
  }

  answerCallbackQuery(id: string, text?: string) {
    return this.call<boolean>("answerCallbackQuery", { callback_query_id: id, text }).catch(() => false);
  }

  copyMessage(toChatId: number, fromChatId: number, messageId: number, extra: Record<string, unknown> = {}) {
    return this.call<{ message_id: number }>("copyMessage", {
      chat_id: toChatId,
      from_chat_id: fromChatId,
      message_id: messageId,
      ...extra,
    });
  }

  approveChatJoinRequest(chatId: number, userId: number) {
    return this.call<boolean>("approveChatJoinRequest", { chat_id: chatId, user_id: userId });
  }

  declineChatJoinRequest(chatId: number, userId: number) {
    return this.call<boolean>("declineChatJoinRequest", { chat_id: chatId, user_id: userId });
  }

  /**
   * Sends text or media + caption depending on fileType. Used by greeting, buttons, mailings, channel messages.
   */
  sendContent(
    chatId: number,
    content: { text?: string | null; fileId?: string | null; fileType?: string | null },
    replyMarkup?: ReplyMarkup,
    extra: Record<string, unknown> = {},
  ) {
    const base = { chat_id: chatId, reply_markup: replyMarkup, parse_mode: "HTML", ...extra };
    if (content.fileId && content.fileType) {
      const methodByType: Record<FileType, string> = {
        photo: "sendPhoto",
        video: "sendVideo",
        document: "sendDocument",
        animation: "sendAnimation",
        audio: "sendAudio",
        voice: "sendVoice",
      };
      const method = methodByType[content.fileType as FileType] ?? "sendDocument";
      return this.call<TgMessage>(method, { ...base, [content.fileType]: content.fileId, caption: content.text || undefined });
    }
    return this.call<TgMessage>("sendMessage", { ...base, text: content.text || " " });
  }
}

/** Escape user text for HTML parse_mode */
export function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
