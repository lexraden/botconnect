import { notFound } from "next/navigation";
import { requireAccount } from "@/lib/auth";
import { getBotForOwner, getBotStats, getMailingQuota, webhookUrlFor } from "@/lib/bots";
import { ActionForm, Badge, BotTabs, Card, ConfirmButton, Field, inputCls, Stat, SubmitButton } from "@/components/ui";
import { deleteBotAction, reconnectWebhookAction, toggleBotAction, updateBotSettingsAction } from "../../actions";

export const dynamic = "force-dynamic";

export default async function BotOverviewPage({ params, searchParams }: { params: Promise<{ botId: string }>; searchParams: Promise<{ webhook?: string }> }) {
  const { botId } = await params;
  const { webhook } = await searchParams;
  const account = await requireAccount();
  const bot = await getBotForOwner(Number(botId), account.id);
  if (!bot) notFound();

  const [stats, quota] = await Promise.all([getBotStats(bot.id), getMailingQuota(bot.id)]);
  const webhookUrl = webhookUrlFor(bot.id);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">
            @{bot.username} <Badge tone={bot.isActive ? "green" : "slate"}>{bot.isActive ? "активен" : "выключен"}</Badge>{" "}
            {quota.isPro && <Badge tone="blue">PRO</Badge>}
          </h1>
          <p className="text-sm text-slate-500">{bot.title} · подключён {bot.createdAt.toLocaleDateString("ru-RU")}</p>
        </div>
        <div className="flex gap-2">
          <form action={toggleBotAction}>
            <input type="hidden" name="botId" value={bot.id} />
            <SubmitButton variant="ghost">{bot.isActive ? "Выключить" : "Включить"}</SubmitButton>
          </form>
          <form action={deleteBotAction}>
            <input type="hidden" name="botId" value={bot.id} />
            <ConfirmButton message="Удалить бота и все его данные (пользователи, кнопки, рассылки)?">Удалить</ConfirmButton>
          </form>
        </div>
      </div>

      <BotTabs botId={bot.id} />

      {webhook === "failed" && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Бот сохранён, но вебхук не установлен (нет PUBLIC_URL или Telegram вернул ошибку). Проверьте настройки и нажмите «Переподключить вебхук».
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Пользователей" value={stats.total} hint={`+${stats.today} за сутки`} />
        <Stat label="Заблокировали бота" value={stats.blocked} hint={`${stats.banned} в бане`} />
        <Stat label="Входящих / ответов" value={`${bot.receivedCount} / ${bot.repliedCount}`} />
        <Stat label="Лимит рассылок" value={`${quota.sentToday} / ${quota.dailyLimit}`} hint={quota.isPro ? "PRO-тариф" : "бесплатный тариф"} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Приветствие и обратная связь">
          <ActionForm action={updateBotSettingsAction}>
            <input type="hidden" name="botId" value={bot.id} />
            <Field label="Текст приветствия (/start)" hint="Поддерживается HTML: <b>, <i>, <a href>. Пусто — стандартное приветствие.">
              <textarea name="greetingText" rows={4} className={inputCls} defaultValue={bot.greetingText ?? ""} />
            </Field>
            <div className="grid grid-cols-[1fr_140px] gap-3">
              <Field label="file_id вложения (опц.)">
                <input name="greetingFileId" className={inputCls} defaultValue={bot.greetingFileId ?? ""} placeholder="AgACAgIAAxkBAAI..." />
              </Field>
              <Field label="Тип">
                <select name="greetingFileType" className={inputCls} defaultValue={bot.greetingFileType ?? ""}>
                  <option value="">—</option>
                  <option value="photo">photo</option>
                  <option value="video">video</option>
                  <option value="animation">animation</option>
                  <option value="document">document</option>
                </select>
              </Field>
            </div>
            <Field label="ID чата для входящих сообщений" hint="Добавьте бота админом в группу — ID подставится автоматически (если ещё не задан). Или укажите вручную, например -1001234567890.">
              <input name="forwardChatId" className={inputCls} defaultValue={bot.forwardChatId ?? ""} placeholder="-100…" />
            </Field>
            <SubmitButton>Сохранить</SubmitButton>
          </ActionForm>
        </Card>

        <div className="space-y-6">
          <Card title="Вебхук">
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-xs text-slate-500">URL</dt>
                <dd className="break-all font-mono text-xs">{webhookUrl ?? <span className="text-amber-700">PUBLIC_URL не задан</span>}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Последний апдейт</dt>
                <dd>{bot.lastWebhookAt ? bot.lastWebhookAt.toLocaleString("ru-RU") : "—"}</dd>
              </div>
            </dl>
            <form action={reconnectWebhookAction} className="mt-4">
              <input type="hidden" name="botId" value={bot.id} />
              <SubmitButton variant="ghost">Переподключить вебхук</SubmitButton>
            </form>
          </Card>

          <Card title="Как получать file_id">
            <p className="text-sm text-slate-600">
              Отправьте фото/видео/документ своему боту <b>@{bot.username}</b> — оно перешлётся в чат обратной связи. Ответьте на него командой <code>/fileid</code>, и бот пришлёт <code>file_id</code>. Либо используйте @RawDataBot.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
