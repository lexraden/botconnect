import { safeEqual } from "@/lib/crypto";
import { env } from "@/lib/env";
import { runDueMailings } from "@/lib/mailing";
import { reconcilePendingPayments } from "@/lib/payments";
import { db } from "@/db";
import { sql } from "drizzle-orm";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/**
 * Single cron endpoint. Call it every minute (Vercel Cron, Railway cron, GitHub Actions, `curl` in crontab...).
 *   GET /api/cron   Authorization: Bearer $CRON_SECRET
 *
 * v1 ran three `while True` loops inside the web process, which broke with >1 worker and on restarts.
 */
export async function GET(req: Request) {
  const secret = env.cronSecret;
  const auth = req.headers.get("authorization") ?? "";
  const provided = auth.startsWith("Bearer ") ? auth.slice(7) : new URL(req.url).searchParams.get("secret") ?? "";
  if (!secret || !safeEqual(provided, secret)) return new Response("forbidden", { status: 403 });

  const started = Date.now();
  const [mailings, paymentsResult] = await Promise.all([runDueMailings(), reconcilePendingPayments()]);

  // housekeeping: idempotency table & stale join requests
  await db.execute(sql`delete from processed_updates where created_at < now() - interval '2 days'`);
  await db.execute(sql`delete from pending_join_requests where created_at < now() - interval '3 days'`);
  await db.execute(sql`delete from login_tokens where expires_at < now() - interval '1 day'`);

  return Response.json({ ok: true, ms: Date.now() - started, mailings, payments: paymentsResult });
}
