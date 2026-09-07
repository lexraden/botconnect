import Link from "next/link";
import type { ReactNode } from "react";
import { requireAccount } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const account = await requireAccount();
  const name = [account.firstName, account.lastName].filter(Boolean).join(" ") || account.username || `id${account.telegramId}`;
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-sky-600 text-white">🤖</span>
            Bot Connect <span className="rounded bg-sky-100 px-1 text-[10px] font-bold text-sky-700">v2</span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-slate-600">
              {name} {account.isAdmin && <span className="ml-1 rounded bg-amber-100 px-1.5 text-xs font-medium text-amber-800">admin</span>}
            </span>
            <form action="/api/auth/logout" method="post">
              <button className="text-slate-500 hover:text-slate-900">Выйти</button>
            </form>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
