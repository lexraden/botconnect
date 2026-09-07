import { createHash, createHmac } from "node:crypto";
import { and, eq, gt, lt } from "drizzle-orm";
import { db } from "@/db";
import { accounts, bots, payments, subscriptions } from "@/db/schema";
import { safeEqual } from "./crypto";
import { env, getPlans } from "./env";
import { getActiveSubscription } from "./bots";
import { notifyOwner } from "./telegram/main-bot";

/**
 * Crypto Pay API (@CryptoBot). https://help.crypt.bot/crypto-pay-api
 * v1 polled every pending invoice every 60 s. v2 receives a signed webhook
 * and only falls back to polling for invoices that never received a webhook.
 */

const API = () => (env.cryptoBotTestnet ? "https://testnet-pay.crypt.bot/api" : "https://pay.crypt.bot/api");

interface CryptoInvoice {
  invoice_id: number;
  status: "active" | "paid" | "expired";
  pay_url?: string;
  bot_invoice_url?: string;
  mini_app_invoice_url?: string;
  amount: string;
  asset?: string;
  payload?: string;
}

async function cryptoCall<T>(method: string, body: Record<string, unknown> = {}): Promise<T> {
  const token = env.cryptoBotToken;
  if (!token) throw new Error("CRYPTO_BOT_TOKEN не настроен");
  const res = await fetch(`${API()}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json", "Crypto-Pay-API-Token": token },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15_000),
  });
  const json = (await res.json()) as { ok: boolean; result?: T; error?: { name: string } };
  if (!json.ok) throw new Error(`CryptoPay: ${json.error?.name ?? res.status}`);
  return json.result as T;
}

export function isPaymentsEnabled() {
  return Boolean(env.cryptoBotToken);
}

export async function createInvoice(accountId: number, botId: number, months: number) {
  const plan = getPlans().find((p) => p.months === months);
  if (!plan) throw new Error("Неизвестный тариф");

  const expiresIn = 3600;
  const inv = await cryptoCall<CryptoInvoice>("createInvoice", {
    currency_type: "crypto",
    asset: "USDT",
    amount: plan.price.toFixed(2),
    description: `Bot Connect: подписка на ${months} мес.`,
    payload: JSON.stringify({ botId, months, accountId }),
    expires_in: expiresIn,
    allow_comments: false,
  });

  const payUrl = inv.bot_invoice_url ?? inv.pay_url ?? inv.mini_app_invoice_url ?? "";
  const [row] = await db
    .insert(payments)
    .values({
      botId,
      accountId,
      provider: "cryptobot",
      invoiceId: String(inv.invoice_id),
      payUrl,
      months,
      amount: plan.price.toFixed(2),
      currency: "USDT",
      status: "pending",
      expiresAt: new Date(Date.now() + expiresIn * 1000),
    })
    .returning();
  return row;
}

/** Verify `crypto-pay-api-signature` header: HMAC-SHA256(body) with key = SHA256(token). */
export function verifyCryptoWebhook(rawBody: string, signature: string | null): boolean {
  const token = env.cryptoBotToken;
  if (!token || !signature) return false;
  const secret = createHash("sha256").update(token).digest();
  const expected = createHmac("sha256", secret).update(rawBody).digest("hex");
  return safeEqual(expected, signature);
}

/** Idempotently mark invoice as paid and extend the subscription. */
export async function applyPaidInvoice(invoiceId: string): Promise<boolean> {
  const [payment] = await db
    .update(payments)
    .set({ status: "paid", paidAt: new Date() })
    .where(and(eq(payments.invoiceId, invoiceId), eq(payments.status, "pending")))
    .returning();
  if (!payment) return false; // already applied or unknown

  const current = await getActiveSubscription(payment.botId);
  const startsAt = current ? current.endsAt : new Date();
  const endsAt = new Date(startsAt);
  endsAt.setMonth(endsAt.getMonth() + payment.months);

  await db.insert(subscriptions).values({
    botId: payment.botId,
    months: payment.months,
    price: payment.amount,
    currency: payment.currency,
    startsAt,
    endsAt,
  });

  const [row] = await db
    .select({ telegramId: accounts.telegramId, username: bots.username })
    .from(bots)
    .innerJoin(accounts, eq(accounts.id, bots.ownerId))
    .where(eq(bots.id, payment.botId))
    .limit(1);
  if (row) {
    await notifyOwner(row.telegramId, `✅ Оплата получена. Подписка для @${row.username} активна до <b>${endsAt.toLocaleDateString("ru-RU")}</b>.`);
  }
  return true;
}

/** Fallback for the cron: reconcile pending invoices that are still within TTL, expire the rest. */
export async function reconcilePendingPayments(): Promise<{ paid: number; expired: number }> {
  const now = new Date();
  const expired = await db
    .update(payments)
    .set({ status: "expired" })
    .where(and(eq(payments.status, "pending"), lt(payments.expiresAt, now)))
    .returning({ id: payments.id });

  let paid = 0;
  if (isPaymentsEnabled()) {
    const pending = await db
      .select({ invoiceId: payments.invoiceId })
      .from(payments)
      .where(and(eq(payments.status, "pending"), gt(payments.expiresAt, now)))
      .limit(100);
    if (pending.length) {
      const res = await cryptoCall<{ items: CryptoInvoice[] }>("getInvoices", {
        invoice_ids: pending.map((p) => p.invoiceId).join(","),
      }).catch(() => ({ items: [] as CryptoInvoice[] }));
      for (const inv of res.items ?? []) {
        if (inv.status === "paid" && (await applyPaidInvoice(String(inv.invoice_id)))) paid++;
      }
    }
  }
  return { paid, expired: expired.length };
}
