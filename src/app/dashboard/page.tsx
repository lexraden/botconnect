import Link from "next/link";
import { desc, eq, sql } from "drizzle-orm";
import { db } from "@/db";
import { bots, botUsers } from "@/db/schema";
import { requireAccount } from "@/lib/auth";
import { env } from "@/lib/env";
import { ActionForm, Badge, Card, Field, inputCls, SubmitButton } from "@/components/ui";
import { addBotAction } from "./actions";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const account = await requireAccount();
  const list = await db
    .select({
      id: bots.id,
      username: bots.username,
      title: bots.title,
      isActive: bots.isActive,
      receivedCount: bots.receivedCount,
      repliedCount: bots.repliedCount,
      lastWebhookAt: bots.lastWebhookAt,
      createdAt: bots.createdAt,
      users: sql<number>`(select count(*) from ${botUsers} where ${botUsers.botId} = ${bots.id})::int`,
    })
    .from(bots)
    .where(eq(bots.ownerId, account.id))
    .orderBy(desc(bots.createdAt));

  const webhookReady = Boolean(env.publicUrl);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-bold">Мои боты</h1>
            <p className="text-sm text-slate-600">{list.length} из {env.freeBotsLimit} на бесплатном тарифе</p>
          </div>
        </div>

        {!webhookReady && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <b>PUBLIC_URL не задан.</b> Боты будут сохранены, но вебхук не установится — Telegram не сможет доставлять сообщения. Укажите публичный HTTPS-адрес приложения и нажмите «Переподключить вебхук» на странице бота.
          </div>
        )}

        {list.length === 0 ? (
          <Card>
            <div className="py-10 text-center">
              <div className="text-4xl">🤖</div>
              <p className="mt-3 font-medium">Пока нет ботов</p>
              <p className="mt-1 text-sm text-slate-600">Создайте бота в @BotFather и вставьте токен справа.</p>
            </div>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {list.map((b) => (
              <Link key={b.id} href={`/dashboard/bots/${b.id}`} className="group rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-sky-300 hover:shadow-md">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-slate-900 group-hover:text-sky-700">@{b.username}</p>
                    <p className="text-sm text-slate-500">{b.title}</p>
                  </div>
                  <Badge tone={b.isActive ? "green" : "slate"}>{b.isActive ? "активен" : "выключен"}</Badge>
                </div>
                <dl className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="rounded-lg bg-slate-50 p-2"><dt className="text-xs text-slate-500">Юзеры</dt><dd className="font-semibold">{b.users}</dd></div>
                  <div className="rounded-lg bg-slate-50 p-2"><dt className="text-xs text-slate-500">Входящих</dt><dd className="font-semibold">{b.receivedCount}</dd></div>
                  <div className="rounded-lg bg-slate-50 p-2"><dt className="text-xs text-slate-500">Ответов</dt><dd className="font-semibold">{b.repliedCount}</dd></div>
                </dl>
                <p className="mt-3 text-xs text-slate-400">
                  {b.lastWebhookAt ? `Последний апдейт: ${b.lastWebhookAt.toLocaleString("ru-RU")}` : "Апдейтов ещё не было"}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-4">
        <Card title="Подключить бота">
          <ActionForm action={addBotAction}>
            <Field label="Токен из @BotFather" hint="Токен шифруется перед сохранением и нигде не показывается целиком.">
              <input name="token" className={inputCls} placeholder="123456789:AAH..." required autoComplete="off" />
            </Field>
            <SubmitButton className="w-full">Подключить</SubmitButton>
          </ActionForm>
        </Card>
        <Card title="Как это работает">
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-600">
            <li>Создайте бота в <a className="text-sky-600 underline" href="https://t.me/BotFather" target="_blank">@BotFather</a> и скопируйте токен.</li>
            <li>Вставьте токен — мы проверим его через <code>getMe</code> и установим вебхук.</li>
            <li>Добавьте бота админом в группу — туда будут приходить сообщения пользователей.</li>
            <li>Настройте приветствие, меню и рассылки в панели.</li>
          </ol>
        </Card>
      </div>
    </div>
  );
}
