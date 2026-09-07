import { safeEqual } from "@/lib/crypto";
import { handleMainBotUpdate } from "@/lib/telegram/main-bot";
import type { TgUpdate } from "@/lib/telegram/types";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const expected = process.env.MAIN_BOT_WEBHOOK_SECRET;
  if (!expected) return new Response("main bot not configured", { status: 503 });
  const secret = req.headers.get("x-telegram-bot-api-secret-token") ?? "";
  if (!safeEqual(secret, expected)) return new Response("forbidden", { status: 403 });

  try {
    const update = (await req.json()) as TgUpdate;
    await handleMainBotUpdate(update);
  } catch (e) {
    console.error("[main bot] update failed:", e);
  }
  return Response.json({ ok: true });
}
