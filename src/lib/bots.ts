import { and, count, eq, gt, sql } from "drizzle-orm";
import { db } from "@/db";
import { bots, botUsers, mailings, subscriptions, type Bot } from "@/db/schema";
import { decrypt, encrypt, randomToken } from "./crypto";
import { env } from "./env";
import { TelegramBot } from "./telegram/api";

export function webhookUrlFor(botId: number): string | null {
  const base = env.publicUrl;
  return base ? `${base}/api/telegram/bots/${botId}` : null;
}

export function botClient(bot: Pick<Bot, "encryptedToken">): TelegramBot {
  return new TelegramBot(decrypt(bot.encryptedToken));
}

export async function getBotForOwner(botId: number, ownerId: number): Promise<Bot | null> {
  const [bot] = await db
    .select()
    .from(bots)
    .where(and(eq(bots.id, botId), eq(bots.ownerId, ownerId)))
    .limit(1);
  return bot ?? null;
}

/**
 * Validates a token via getMe, stores it encrypted, registers the webhook.
 * Re-adding an existing bot (same telegram id) rotates its token/secret instead of failing.
 */
export async function connectBot(ownerId: number, rawToken: string): Promise<{ ok: true; bot: Bot; webhook: boolean } | { ok: false; error: string }> {
  const token = rawToken.trim();
  if (!/^\d{6,}:[A-Za-z0-9_-]{30,}$/.test(token)) {
    return { ok: false, error: "Неверный формат токена. Скопируйте токен из @BotFather целиком." };
  }

  const tg = new TelegramBot(token);
  let me: Awaited<ReturnType<TelegramBot["getMe"]>>;
  try {
    me = await tg.getMe();
  } catch (e) {
    return { ok: false, error: `Telegram отклонил токен: ${(e as Error).message}` };
  }

  const [existing] = await db.select().from(bots).where(eq(bots.telegramBotId, me.id)).limit(1);
  if (existing && existing.ownerId !== ownerId) {
    return { ok: false, error: "Этот бот уже подключён другим аккаунтом." };
  }

  if (!existing) {
    const [{ value: activeCount }] = await db
      .select({ value: count() })
      .from(bots)
      .where(and(eq(bots.ownerId, ownerId), eq(bots.isActive, true)));
    if (activeCount >= env.freeBotsLimit) {
      const hasPro = await ownerHasActiveSubscription(ownerId);
      if (!hasPro) {
        return { ok: false, error: `Лимит бесплатного тарифа — ${env.freeBotsLimit} активных бота. Оформите подписку на любом боте.` };
      }
    }
  }

  const webhookSecret = randomToken(24);
  const values = {
    ownerId,
    telegramBotId: me.id,
    username: me.username ?? String(me.id),
    title: me.first_name,
    encryptedToken: encrypt(token),
    webhookSecret,
    isActive: true,
  };

  const [bot] = existing
    ? await db.update(bots).set(values).where(eq(bots.id, existing.id)).returning()
    : await db.insert(bots).values(values).returning();

  const webhook = await registerWebhook(bot, tg);
  return { ok: true, bot, webhook };
}

export async function registerWebhook(bot: Bot, client?: TelegramBot): Promise<boolean> {
  const url = webhookUrlFor(bot.id);
  if (!url) return false;
  const tg = client ?? botClient(bot);
  try {
    await tg.setWebhook(url, bot.webhookSecret);
    await tg.setMyCommands([{ command: "start", description: "Начать" }]).catch(() => undefined);
    return true;
  } catch (e) {
    console.error(`[bots] setWebhook failed for bot ${bot.id}:`, (e as Error).message);
    return false;
  }
}

export async function setBotActive(bot: Bot, active: boolean): Promise<void> {
  const tg = botClient(bot);
  if (active) await registerWebhook(bot, tg);
  else await tg.deleteWebhook().catch(() => undefined);
  await db.update(bots).set({ isActive: active }).where(eq(bots.id, bot.id));
}

export async function deleteBot(bot: Bot): Promise<void> {
  await botClient(bot).deleteWebhook().catch(() => undefined);
  await db.delete(bots).where(eq(bots.id, bot.id));
}

// ---------- Subscriptions & limits ----------

export async function getActiveSubscription(botId: number) {
  const [sub] = await db
    .select()
    .from(subscriptions)
    .where(and(eq(subscriptions.botId, botId), gt(subscriptions.endsAt, new Date())))
    .orderBy(sql`${subscriptions.endsAt} desc`)
    .limit(1);
  return sub ?? null;
}

export async function ownerHasActiveSubscription(ownerId: number): Promise<boolean> {
  const [row] = await db
    .select({ id: subscriptions.id })
    .from(subscriptions)
    .innerJoin(bots, eq(bots.id, subscriptions.botId))
    .where(and(eq(bots.ownerId, ownerId), gt(subscriptions.endsAt, new Date())))
    .limit(1);
  return Boolean(row);
}

/** Mailing quota for the current UTC day. v1 bug: it ignored subscription expiry. */
export async function getMailingQuota(botId: number) {
  const sub = await getActiveSubscription(botId);
  const dailyLimit = sub ? env.proDailyLimit : env.freeDailyLimit;
  const [row] = await db
    .select({ sent: sql<number>`coalesce(sum(${mailings.sentCount}), 0)::int` })
    .from(mailings)
    .where(and(eq(mailings.botId, botId), sql`${mailings.scheduledAt} >= date_trunc('day', now() at time zone 'utc')`));
  const sentToday = row?.sent ?? 0;
  return { dailyLimit, sentToday, remaining: Math.max(0, dailyLimit - sentToday), isPro: Boolean(sub), subscription: sub };
}

export async function getBotStats(botId: number) {
  const [users] = await db
    .select({
      total: count(),
      blocked: sql<number>`count(*) filter (where ${botUsers.isBlocked})::int`,
      banned: sql<number>`count(*) filter (where ${botUsers.isBanned})::int`,
      today: sql<number>`count(*) filter (where ${botUsers.createdAt} >= now() - interval '1 day')::int`,
    })
    .from(botUsers)
    .where(eq(botUsers.botId, botId));
  return users;
}
