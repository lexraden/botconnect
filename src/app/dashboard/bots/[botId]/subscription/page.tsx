import { notFound } from "next/navigation";
import { desc, eq } from "drizzle-orm";
import { db } from "@/db";
import { payments, subscriptions } from "@/db/schema";
import { requireAccount } from "@/lib/auth";
import { getBotForOwner, getMailingQuota } from "@/lib/bots";
import { env, getPlans } from "@/lib/env";
import { isPaymentsEnabled } from "@/lib/payments";
import { ActionForm, Badge, BotTabs, Card, SubmitButton } from "@/components/ui";
import { createInvoiceAction } from "../../../actions";

export const dynamic = "force-dynamic";

export default async function SubscriptionPage({ params }: { params: Promise<{ botId: string }> }) {
  const { botId } = await params;
  const account = await requireAccount();
  const bot = await getBotForOwner(Number(botId), account.id);
  if (!bot) notFound();

  const [quota, history, invoices] = await Promise.all([
    getMailingQuota(bot.id),
    db.select().from(subscriptions).where(eq(subscriptions.botId, bot.id)).orderBy(desc(subscriptions.endsAt)).limit(10),
    db.select().from(payments).where(eq(payments.botId, bot.id)).orderBy(desc(payments.createdAt)).limit(10),
  ]);
  const plans = getPlans();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">@{bot.username} · Подписка</h1>
      <BotTabs botId={bot.id} />

      <Card title="Текущий тариф">
        {quota.subscription ? (
          <p className="text-sm">
            <Badge tone="blue">PRO</Badge> активна до <b>{quota.subscription.endsAt.toLocaleDateString("ru-RU")}</b>. Лимит рассылок: {env.proDailyLimit.toLocaleString("ru-RU")} сообщений в день.
          </p>
        ) : (
          <p className="text-sm text-slate-600">
            <Badge>FREE</Badge> Лимит рассылок: {env.freeDailyLimit} сообщений в день, до {env.freeBotsLimit} активных ботов.
          </p>
        )}
      </Card>

      <div className="grid gap-3 sm:grid-cols-3">
        {plans.map((p) => (
          <Card key={p.months} className="text-center">
            <p className="text-3xl font-bold">{p.price} <span className="text-base font-medium text-slate-500">USDT</span></p>
            <p className="mt-1 text-sm text-slate-600">{p.months} {p.months === 1 ? "месяц" : p.months < 5 ? "месяца" : "месяцев"}</p>
            <p className="text-xs text-slate-400">{(p.price / p.months).toFixed(2)} USDT / мес</p>
            <ActionForm action={createInvoiceAction} className="mt-4">
              <input type="hidden" name="botId" value={bot.id} />
              <input type="hidden" name="months" value={p.months} />
              <SubmitButton className="w-full">{isPaymentsEnabled() ? "Оплатить через @CryptoBot" : "Платежи не настроены"}</SubmitButton>
            </ActionForm>
          </Card>
        ))}
      </div>

      {!isPaymentsEnabled() && (
        <p className="text-sm text-amber-700">Чтобы принимать оплату, задайте <code>CRYPTO_BOT_TOKEN</code> и укажите вебхук <code>{env.publicUrl ?? "https://your-domain"}/api/payments/cryptobot</code> в настройках @CryptoBot.</p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="История подписок">
          {history.length === 0 ? <p className="text-sm text-slate-500">Пока пусто.</p> : (
            <ul className="divide-y divide-slate-100 text-sm">
              {history.map((s) => (
                <li key={s.id} className="flex justify-between py-2">
                  <span>{s.months} мес · {s.price} {s.currency}</span>
                  <span className="text-slate-500">{s.startsAt.toLocaleDateString("ru-RU")} — {s.endsAt.toLocaleDateString("ru-RU")}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Счета">
          {invoices.length === 0 ? <p className="text-sm text-slate-500">Пока пусто.</p> : (
            <ul className="divide-y divide-slate-100 text-sm">
              {invoices.map((i) => (
                <li key={i.id} className="flex items-center justify-between py-2">
                  <span>{i.months} мес · {i.amount} {i.currency}</span>
                  <span className="flex items-center gap-2">
                    <Badge tone={i.status === "paid" ? "green" : i.status === "pending" ? "amber" : "slate"}>{i.status}</Badge>
                    {i.status === "pending" && i.payUrl && <a href={i.payUrl} className="text-sky-600 underline" target="_blank">оплатить</a>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
