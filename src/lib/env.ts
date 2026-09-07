/**
 * Centralised, lazily-read environment config.
 * Nothing here throws at import time so that `next build` works without secrets;
 * accessors throw only when a feature that needs the secret is actually used.
 */

function req(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Environment variable ${name} is required`);
  return v;
}

export const env = {
  get databaseUrl() {
    return req("DATABASE_URL");
  },
  /** Public base URL of this deployment, e.g. https://botconnect.example.com */
  get publicUrl(): string | undefined {
    const v = process.env.PUBLIC_URL || process.env.NEXT_PUBLIC_APP_URL;
    return v ? v.replace(/\/+$/, "") : undefined;
  },
  /** Token of the "main" Bot Connect bot (login + notifications). Optional. */
  get mainBotToken(): string | undefined {
    return process.env.MAIN_BOT_TOKEN || undefined;
  },
  get mainBotUsername(): string | undefined {
    return process.env.MAIN_BOT_USERNAME || undefined;
  },
  /** 32-byte key (hex or base64) used to encrypt bot tokens at rest. */
  get encryptionKey(): string {
    return process.env.ENCRYPTION_KEY || process.env.SESSION_SECRET || "dev-insecure-key-change-me";
  },
  get sessionSecret(): string {
    return process.env.SESSION_SECRET || process.env.ENCRYPTION_KEY || "dev-insecure-secret-change-me";
  },
  get cronSecret(): string | undefined {
    return process.env.CRON_SECRET || undefined;
  },
  get cryptoBotToken(): string | undefined {
    return process.env.CRYPTO_BOT_TOKEN || undefined;
  },
  get cryptoBotTestnet(): boolean {
    return process.env.CRYPTO_BOT_TESTNET === "true";
  },
  /** Comma-separated Telegram IDs with admin access in the dashboard. */
  get adminIds(): number[] {
    return (process.env.ADMINS || "")
      .split(",")
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isFinite(n) && n > 0);
  },
  /** Allow password-less "dev login" form (never enable in production). */
  get allowDevLogin(): boolean {
    return process.env.ALLOW_DEV_LOGIN === "true";
  },
  get freeDailyLimit(): number {
    return Number(process.env.FREE_DAILY_MAILING_LIMIT || 100);
  },
  get proDailyLimit(): number {
    return Number(process.env.PRO_DAILY_MAILING_LIMIT || 50000);
  },
  get freeBotsLimit(): number {
    return Number(process.env.FREE_BOTS_LIMIT || 3);
  },
};

/** Subscription plans (months -> price in USDT). Override via PLANS_JSON. */
export function getPlans(): { months: number; price: number }[] {
  const raw = process.env.PLANS_JSON;
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as { months: number; price: number }[];
      if (Array.isArray(parsed) && parsed.length) return parsed;
    } catch {
      /* fall through */
    }
  }
  return [
    { months: 1, price: 5 },
    { months: 3, price: 12 },
    { months: 12, price: 40 },
  ];
}
