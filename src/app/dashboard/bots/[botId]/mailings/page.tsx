import { notFound } from "next/navigation";
import { desc, eq } from "drizzle-orm";
import { db } from "@/db";
import { mailings } from "@/db/schema";
import { requireAccount } from "@/lib/auth";
import { getBotForOwner, getMailingQuota } from "@/lib/bots";
import { countRecipients } from "@/lib/mailing";
import { env } from "@/lib/env";
import { ActionForm, Badge, BotTabs, Card, ConfirmButton, Field, inputCls, Stat, SubmitButton } from "@/components/ui";
import { cancelMailingAction, createMailingAction } from "../../../actions";

export const dynamic = "force-dynamic";

const statusTone = { scheduled: "amber", running: "blue", done: "green", failed: "red", cancelled: "slate" } as const;
const statusLabel = { scheduled: "запланирована", running: "отправляется", done: "готово", failed: "ошибка", cancelled: "отменена" } as const;

export default async function MailingsPage({ params }: { params: Promise<{ botId: string }> }) {
  const { botId } = await params;
  const account = await requireAccount();
  const bot = await getBotForOwner(Number(botId), account.id);
  if (!bot) notFound();

  const [list, quota, recipients] = await Promise.all([
    db.select().from(mailings).where(eq(mailings.botId, bot.id)).orderBy(desc(mailings.createdAt)).limit(50),
    getMailingQuota(bot.id),
    countRecipients(bot.id),
  ]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">@{bot.username} · Рассылки</h1>
      <BotTabs botId={bot.id} />

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Получателей сейчас" value={recipients} hint="без заблокировавших и забаненных" />
        <Stat label="Отправлено сегодня" value={`${quota.sentToday} / ${quota.dailyLimit}`} />
        <Stat label="Осталось на сегодня" value={quota.remaining} hint={quota.isPro ? "PRO" : "бесплатный тариф"} />
      </div>

      {!env.cronSecret && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <b>CRON_SECRET не задан.</b> Рассылки отправляются планировщиком: настройте вызов <code>GET /api/cron</code> раз в минуту с заголовком <code>Authorization: Bearer CRON_SECRET</code>.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <Card title="История">
          {list.length === 0 ? (
            <p className="text-sm text-slate-500">Рассылок ещё не было.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-500">
                <tr><th className="pb-2">Когда</th><th className="pb-2">Текст</th><th className="pb-2">Статус</th><th className="pb-2 text-right">Отпр. / ошиб.</th><th /></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {list.map((m) => (
                  <tr key={m.id}>
                    <td className="py-2 align-top text-slate-600 whitespace-nowrap">{m.scheduledAt.toLocaleString("ru-RU")}</td>
                    <td className="py-2 align-top max-w-[260px] truncate" title={m.text ?? ""}>{m.text || <i className="text-slate-400">{m.fileType}</i>}</td>
                    <td className="py-2 align-top">
                      <Badge tone={statusTone[m.status as keyof typeof statusTone] ?? "slate"}>{statusLabel[m.status as keyof typeof statusLabel] ?? m.status}</Badge>
                      {m.error && <p className="mt-1 text-xs text-rose-600">{m.error}</p>}
                    </td>
                    <td className="py-2 align-top text-right tabular-nums">{m.sentCount} / {m.failedCount}</td>
                    <td className="py-2 align-top text-right">
                      {m.status === "scheduled" && (
                        <form action={cancelMailingAction}>
                          <input type="hidden" name="botId" value={bot.id} />
                          <input type="hidden" name="id" value={m.id} />
                          <ConfirmButton message="Отменить рассылку?">Отменить</ConfirmButton>
                        </form>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Новая рассылка">
          <ActionForm action={createMailingAction}>
            <input type="hidden" name="botId" value={bot.id} />
            <Field label="Текст (HTML)">
              <textarea name="text" rows={5} className={inputCls} />
            </Field>
            <div className="grid grid-cols-[1fr_120px] gap-3">
              <Field label="file_id (опц.)"><input name="fileId" className={inputCls} /></Field>
              <Field label="Тип">
                <select name="fileType" className={inputCls} defaultValue="">
                  <option value="">—</option><option value="photo">photo</option><option value="video">video</option><option value="animation">animation</option><option value="document">document</option>
                </select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Текст кнопки"><input name="buttonText" className={inputCls} /></Field>
              <Field label="Ссылка кнопки"><input name="buttonUrl" className={inputCls} placeholder="https://" /></Field>
            </div>
            <Field label="Когда отправить" hint="Пусто — в ближайшую минуту. Время — по вашим часам браузера.">
              <input name="scheduledAt" type="datetime-local" className={inputCls} />
            </Field>
            <SubmitButton className="w-full">Запустить</SubmitButton>
          </ActionForm>
        </Card>
      </div>
    </div>
  );
}
