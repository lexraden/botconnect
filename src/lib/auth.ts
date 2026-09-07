import { createHash } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { and, eq, gt, isNull } from "drizzle-orm";
import { db } from "@/db";
import { accounts, loginTokens, type Account } from "@/db/schema";
import { hmacSha256, randomToken, safeEqual } from "./crypto";
import { env } from "./env";

const COOKIE = "bc_session";
const SESSION_TTL_SEC = 60 * 60 * 24 * 30;

// ---------- Session cookie (signed, stateless) ----------

function sign(payload: string): string {
  return `${payload}.${hmacSha256(env.sessionSecret, payload)}`;
}

function verify(value: string): { accountId: number } | null {
  const idx = value.lastIndexOf(".");
  if (idx < 0) return null;
  const payload = value.slice(0, idx);
  const sig = value.slice(idx + 1);
  if (!safeEqual(sig, hmacSha256(env.sessionSecret, payload))) return null;
  try {
    const data = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as { accountId: number; exp: number };
    if (data.exp < Date.now() / 1000) return null;
    return { accountId: data.accountId };
  } catch {
    return null;
  }
}

export async function createSession(accountId: number) {
  const payload = Buffer.from(JSON.stringify({ accountId, exp: Math.floor(Date.now() / 1000) + SESSION_TTL_SEC })).toString("base64url");
  const store = await cookies();
  store.set(COOKIE, sign(payload), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_TTL_SEC,
  });
}

export async function destroySession() {
  const store = await cookies();
  store.delete(COOKIE);
}

export async function getCurrentAccount(): Promise<Account | null> {
  const store = await cookies();
  const raw = store.get(COOKIE)?.value;
  if (!raw) return null;
  const session = verify(raw);
  if (!session) return null;
  const [acc] = await db.select().from(accounts).where(eq(accounts.id, session.accountId)).limit(1);
  return acc ?? null;
}

export async function requireAccount(): Promise<Account> {
  const acc = await getCurrentAccount();
  if (!acc) redirect("/login");
  return acc;
}

// ---------- Account upsert ----------

export interface TelegramIdentity {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

export async function upsertAccount(u: TelegramIdentity): Promise<Account> {
  const isAdmin = env.adminIds.includes(u.id);
  const [acc] = await db
    .insert(accounts)
    .values({ telegramId: u.id, firstName: u.first_name, lastName: u.last_name, username: u.username, languageCode: u.language_code ?? "ru", isAdmin })
    .onConflictDoUpdate({
      target: accounts.telegramId,
      set: { firstName: u.first_name, lastName: u.last_name, username: u.username, isAdmin },
    })
    .returning();
  return acc;
}

// ---------- Telegram Login Widget ----------

/** https://core.telegram.org/widgets/login#checking-authorization */
export function verifyTelegramLogin(params: Record<string, string>): TelegramIdentity | null {
  const token = env.mainBotToken;
  if (!token) return null;
  const { hash, ...rest } = params;
  if (!hash) return null;
  const dataCheck = Object.keys(rest)
    .sort()
    .map((k) => `${k}=${rest[k]}`)
    .join("\n");
  const secret = createHash("sha256").update(token).digest();
  const expected = hmacSha256(secret, dataCheck);
  if (!safeEqual(expected, hash)) return null;
  const authDate = Number(rest.auth_date);
  if (!authDate || Date.now() / 1000 - authDate > 86400) return null;
  return { id: Number(rest.id), first_name: rest.first_name, last_name: rest.last_name, username: rest.username };
}

// ---------- Magic link issued by the main bot ----------

export async function issueLoginToken(telegramId: number): Promise<string> {
  const token = randomToken(24);
  await db.insert(loginTokens).values({ token, telegramId, expiresAt: new Date(Date.now() + 10 * 60 * 1000) });
  return token;
}

export async function consumeLoginToken(token: string): Promise<number | null> {
  const [row] = await db
    .update(loginTokens)
    .set({ usedAt: new Date() })
    .where(and(eq(loginTokens.token, token), isNull(loginTokens.usedAt), gt(loginTokens.expiresAt, new Date())))
    .returning({ telegramId: loginTokens.telegramId });
  return row?.telegramId ?? null;
}

/** Relative redirect that works behind any reverse proxy (no dependency on req.url host). */
export function redirectTo(path: string, status: 302 | 303 | 307 = 303): Response {
  return new Response(null, { status, headers: { Location: path } });
}
