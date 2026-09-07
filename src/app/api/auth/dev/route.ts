import { createSession, redirectTo, upsertAccount } from "@/lib/auth";
import { env } from "@/lib/env";

export const dynamic = "force-dynamic";

/** Password-less local login. Enabled only with ALLOW_DEV_LOGIN=true. */
export async function POST(req: Request) {
  if (!env.allowDevLogin) return new Response("disabled", { status: 404 });
  const form = await req.formData();
  const id = Number(form.get("telegram_id"));
  const name = String(form.get("name") || "Dev User");
  if (!Number.isInteger(id) || id <= 0) return redirectTo("/login?error=dev");
  const acc = await upsertAccount({ id, first_name: name });
  await createSession(acc.id);
  return redirectTo("/dashboard");
}
