import { eq } from "drizzle-orm";
import { db } from "@/db";
import { accounts } from "@/db/schema";
import { consumeLoginToken, createSession, redirectTo, upsertAccount } from "@/lib/auth";

export const dynamic = "force-dynamic";

/** Magic link issued by the main bot via /login */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const token = url.searchParams.get("token") ?? "";
  const telegramId = token ? await consumeLoginToken(token) : null;
  if (!telegramId) return redirectTo("/login?error=expired", 302);

  const [existing] = await db.select().from(accounts).where(eq(accounts.telegramId, telegramId)).limit(1);
  const acc = existing ?? (await upsertAccount({ id: telegramId }));
  await createSession(acc.id);
  return redirectTo("/dashboard", 302);
}
