import { destroySession, redirectTo } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST() {
  await destroySession();
  return redirectTo("/login");
}
