import { notFound } from "next/navigation";
import { and, desc, eq, ilike, or, sql } from "drizzle-orm";
import { db } from "@/db";
import { botUsers } from "@/db/schema";
import { requireAccount } from "@/lib/auth";
import { getBotForOwner } from "@/lib/bots";
import { Badge, BotTabs, Card, inputCls, SubmitButton } from "@/components/ui";
import { toggleBanAction } from "../../../actions";

export const dynamic = "force-dynamic";
const PAGE = 50;

export default async function UsersPage({ params, searchParams }: { params: Promise<{ botId: string }>; searchParams: Promise<{ q?: string; page?: string }> }) {
  const { botId } = await params;
  const { q = "", page = "1" } = await searchParams;
  const account = await requireAccount();
  const bot = await getBotForOwner(Number(botId), account.id);
  if (!bot) notFound();

  const p = Math.max(1, Number(page) || 1);
  const where = and(
    eq(botUsers.botId, bot.id),
    q ? or(ilike(botUsers.username, `%${q}%`), ilike(botUsers.firstName, `%${q}%`), ilike(botUsers.lastName, `%${q}%`), sql`${botUsers.telegramId}::text like ${"%" + q + "%"}`) : undefined,
  );
  const [rows, [{ total }]] = await Promise.all([
    db.select().from(botUsers).where(where).orderBy(desc(botUsers.lastSeenAt)).limit(PAGE).offset((p - 1) * PAGE),
    db.select({ total: sql<number>`count(*)::int` }).from(botUsers).where(where),
  ]);
  const pages = Math.max(1, Math.ceil(total / PAGE));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">@{bot.username} · Пользователи</h1>
      <BotTabs botId={bot.id} />
      <Card
        title={`Всего: ${total}`}
        action={
          <form className="flex gap-2">
            <input name="q" defaultValue={q} placeholder="Поиск по имени, @username, ID" className={`${inputCls} w-64`} />
            <SubmitButton variant="ghost">Найти</SubmitButton>
          </form>
        }
      >
        {rows.length === 0 ? (
          <p className="text-sm text-slate-500">Никого не найдено.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr><th className="pb-2">Пользователь</th><th className="pb-2">ID</th><th className="pb-2">Язык</th><th className="pb-2">Активность</th><th className="pb-2">Статус</th><th /></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((u) => (
                <tr key={u.id}>
                  <td className="py-2">
                    <span className="font-medium">{[u.firstName, u.lastName].filter(Boolean).join(" ") || "—"}</span>
                    {u.username && <span className="ml-1 text-slate-500">@{u.username}</span>}
                  </td>
                  <td className="py-2 font-mono text-xs">{u.telegramId}</td>
                  <td className="py-2">{u.languageCode ?? "—"}</td>
                  <td className="py-2 text-slate-600">{u.lastSeenAt.toLocaleDateString("ru-RU")}</td>
                  <td className="py-2 space-x-1">
                    {u.isBanned && <Badge tone="red">бан</Badge>}
                    {u.isBlocked && <Badge tone="slate">заблокировал бота</Badge>}
                    {!u.isBanned && !u.isBlocked && <Badge tone="green">активен</Badge>}
                  </td>
                  <td className="py-2 text-right">
                    <form action={toggleBanAction}>
                      <input type="hidden" name="botId" value={bot.id} />
                      <input type="hidden" name="id" value={u.id} />
                      <button className={`rounded-lg px-3 py-1 text-xs font-medium ${u.isBanned ? "text-emerald-700 hover:bg-emerald-50" : "text-rose-600 hover:bg-rose-50"}`}>{u.isBanned ? "Разбанить" : "Забанить"}</button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {pages > 1 && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <a className={`text-sky-600 ${p <= 1 ? "pointer-events-none opacity-40" : ""}`} href={`?q=${encodeURIComponent(q)}&page=${p - 1}`}>← Назад</a>
            <span className="text-slate-500">{p} / {pages}</span>
            <a className={`text-sky-600 ${p >= pages ? "pointer-events-none opacity-40" : ""}`} href={`?q=${encodeURIComponent(q)}&page=${p + 1}`}>Вперёд →</a>
          </div>
        )}
      </Card>
    </div>
  );
}
