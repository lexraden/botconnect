import { createSession, redirectTo, upsertAccount, verifyTelegramLogin } from "@/lib/auth";

export const dynamic = "force-dynamic";

/** Telegram Login Widget redirect target (data-auth-url). */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const params = Object.fromEntries(url.searchParams.entries());
  const identity = verifyTelegramLogin(params);
  if (!identity) return redirectTo("/login?error=telegram", 302);
  const acc = await upsertAccount(identity);
  await createSession(acc.id);
  return redirectTo("/dashboard", 302);
}
