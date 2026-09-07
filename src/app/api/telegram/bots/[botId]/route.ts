import { eq } from "drizzle-orm";
import { db } from "@/db";
import { bots } from "@/db/schema";
import { safeEqual } from "@/lib/crypto";
import { handleBotUpdate, touchBot } from "@/lib/telegram/handle-update";
import type { TgUpdate } from "@/lib/telegram/types";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/**
 * Webhook for user bots. The URL contains only the internal bot id;
 * authenticity is verified via Telegram's `X-Telegram-Bot-Api-Secret-Token`.
 * (v1 put the raw bot token into the URL and it leaked into every access log.)
 */
export async function POST(req: Request, ctx: { params: Promise<{ botId: string }> }) {
  const { botId: rawId } = await ctx.params;
  const botId = Number(rawId);
  if (!Number.isInteger(botId)) return new Response("not found", { status: 404 });

  const [bot] = await db.select().from(bots).where(eq(bots.id, botId)).limit(1);
  if (!bot) return new Response("not found", { status: 404 });

  const secret = req.headers.get("x-telegram-bot-api-secret-token") ?? "";
  if (!safeEqual(secret, bot.webhookSecret)) return new Response("forbidden", { status: 403 });

  if (!bot.isActive) return Response.json({ ok: true, skipped: true });

  let update: TgUpdate;
  try {
    update = (await req.json()) as TgUpdate;
  } catch {
    return new Response("bad request", { status: 400 });
  }

  try {
    await handleBotUpdate(bot, update);
    await touchBot(bot.id);
  } catch (e) {
    // Always answer 200: otherwise Telegram keeps retrying a poison update forever.
    console.error(`[webhook bot ${bot.id}] update ${update.update_id} failed:`, e);
  }
  return Response.json({ ok: true });
}
