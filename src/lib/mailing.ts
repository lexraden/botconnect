import { and, asc, eq, gt, lte, sql } from "drizzle-orm";
import { db } from "@/db";
import { bots, botUsers, mailings, type Mailing } from "@/db/schema";
import { botClient, getMailingQuota } from "./bots";
import { markBlocked } from "./telegram/handle-update";
import { TelegramError } from "./telegram/api";

const BATCH_SIZE = 200; // users per cron tick per mailing
const SEND_CONCURRENCY = 20; // ~ Telegram allows ~30 msg/s per bot
const MAX_RUN_MS = 25_000; // stay well under serverless / proxy timeouts

/**
 * Cron entry point. Picks due mailings, claims them atomically (so several cron
 * runners / instances never send the same mailing twice), sends a batch and
 * persists a cursor. Large mailings are finished across several ticks.
 *
 * v1 had `while True` nested inside another `while True` and no claiming at all.
 */
export async function runDueMailings(): Promise<{ processed: number; sent: number }> {
  const started = Date.now();
  let processed = 0;
  let sent = 0;

  while (Date.now() - started < MAX_RUN_MS) {
    const claimed = await claimNextMailing();
    if (!claimed) break;
    processed++;
    sent += await processMailing(claimed);
  }
  return { processed, sent };
}

async function claimNextMailing(): Promise<Mailing | null> {
  // Atomic claim: only one worker flips scheduled -> running for a given row.
  // Mailings stuck in "running" for > 10 minutes (crashed worker) are re-claimed.
  const rows = await db.execute<Mailing>(sql`
    update mailings set status = 'running', started_at = coalesce(started_at, now())
    where id = (
      select id from mailings
      where (status = 'scheduled' and scheduled_at <= now())
         or (status = 'running' and started_at < now() - interval '10 minutes')
      order by scheduled_at asc
      for update skip locked
      limit 1
    )
    returning *
  `);
  const row = (rows.rows?.[0] ?? null) as Record<string, unknown> | null;
  if (!row) return null;
  // node-postgres returns snake_case for raw SQL; map to drizzle's camelCase model
  const [m] = await db.select().from(mailings).where(eq(mailings.id, Number(row.id))).limit(1);
  return m ?? null;
}

async function processMailing(m: Mailing): Promise<number> {
  const [bot] = await db.select().from(bots).where(eq(bots.id, m.botId)).limit(1);
  if (!bot || !bot.isActive) {
    await finish(m.id, "failed", "Бот не найден или выключен");
    return 0;
  }

  const quota = await getMailingQuota(bot.id);
  if (quota.remaining <= 0) {
    await finish(m.id, "failed", `Достигнут дневной лимит (${quota.dailyLimit})`);
    return 0;
  }

  const limit = Math.min(BATCH_SIZE, quota.remaining);
  const recipients = await db
    .select({ telegramId: botUsers.telegramId })
    .from(botUsers)
    .where(and(eq(botUsers.botId, bot.id), eq(botUsers.isBlocked, false), eq(botUsers.isBanned, false), gt(botUsers.telegramId, m.lastUserId)))
    .orderBy(asc(botUsers.telegramId))
    .limit(limit);

  if (recipients.length === 0) {
    await finish(m.id, "done");
    return 0;
  }

  const tg = botClient(bot);
  const markup = m.buttonText && m.buttonUrl ? { inline_keyboard: [[{ text: m.buttonText, url: m.buttonUrl }]] } : undefined;
  let sent = 0;
  let failed = 0;
  const blocked: number[] = [];

  for (let i = 0; i < recipients.length; i += SEND_CONCURRENCY) {
    const chunk = recipients.slice(i, i + SEND_CONCURRENCY);
    await Promise.all(
      chunk.map(async ({ telegramId }) => {
        try {
          await tg.sendContent(telegramId, { text: m.text, fileId: m.fileId, fileType: m.fileType }, markup);
          sent++;
        } catch (e) {
          failed++;
          if (e instanceof TelegramError && e.isUnreachable) blocked.push(telegramId);
        }
      }),
    );
    // gentle pacing: ~20 msgs / 700ms ≈ 28 msg/s
    await new Promise((r) => setTimeout(r, 700));
  }

  for (const id of blocked) await markBlocked(bot.id, id, true);

  const lastUserId = recipients[recipients.length - 1].telegramId;
  const exhausted = recipients.length < limit;
  await db
    .update(mailings)
    .set({
      sentCount: sql`${mailings.sentCount} + ${sent}`,
      failedCount: sql`${mailings.failedCount} + ${failed}`,
      lastUserId,
      status: exhausted ? "done" : "scheduled", // not done yet -> re-queue for the next tick
      startedAt: exhausted ? mailings.startedAt : null,
      finishedAt: exhausted ? new Date() : null,
    })
    .where(eq(mailings.id, m.id));

  return sent;
}

async function finish(id: number, status: "done" | "failed", error?: string) {
  await db.update(mailings).set({ status, error: error ?? null, finishedAt: new Date() }).where(eq(mailings.id, id));
}

/** Small helper for the dashboard: how many recipients a mailing would reach right now. */
export async function countRecipients(botId: number): Promise<number> {
  const [row] = await db
    .select({ n: sql<number>`count(*)::int` })
    .from(botUsers)
    .where(and(eq(botUsers.botId, botId), eq(botUsers.isBlocked, false), eq(botUsers.isBanned, false)));
  return row?.n ?? 0;
}

export async function listDue() {
  return db.select().from(mailings).where(and(eq(mailings.status, "scheduled"), lte(mailings.scheduledAt, new Date())));
}
