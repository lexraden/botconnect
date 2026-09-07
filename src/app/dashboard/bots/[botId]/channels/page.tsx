import { notFound } from "next/navigation";
import { asc, eq, inArray } from "drizzle-orm";
import { db } from "@/db";
import { channelMessages, channels } from "@/db/schema";
import { requireAccount } from "@/lib/auth";
import { getBotForOwner } from "@/lib/bots";
import { ActionForm, Badge, BotTabs, Card, ConfirmButton, Field, inputCls, SubmitButton } from "@/components/ui";
import { deleteChannelMessageAction, removeChannelAction, saveChannelMessageAction, updateChannelAction } from "../../../actions";

export const dynamic = "force-dynamic";

const kindLabel: Record<string, string> = { greeting: "Приветствие", farewell: "Прощание", captcha: "Текст капчи" };

export default async function ChannelsPage({ params }: { params: Promise<{ botId: string }> }) {
  const { botId } = await params;
  const account = await requireAccount();
  const bot = await getBotForOwner(Number(botId), account.id);
  if (!bot) notFound();

  const list = await db.select().from(channels).where(eq(channels.botId, bot.id)).orderBy(asc(channels.createdAt));
  const messages = list.length
    ? await db.select().from(channelMessages).where(inArray(channelMessages.channelId, list.map((c) => c.id)))
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">@{bot.username} · Каналы</h1>
      <BotTabs botId={bot.id} />

      <Card title="Как подключить канал или группу">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
          <li>Добавьте <b>@{bot.username}</b> администратором в канал/группу (права: приглашать пользователей, одобрять заявки).</li>
          <li>Сделать это должен владелец аккаунта (Telegram ID {account.telegramId}) — чужие подключения бот игнорирует.</li>
          <li>Канал появится здесь автоматически. Включите приём заявок по ссылке-приглашению с заявками, чтобы работали автоприём и капча.</li>
        </ol>
      </Card>

      {list.length === 0 && <p className="text-sm text-slate-500">Подключённых каналов пока нет.</p>}

      {list.map((ch) => {
        const msgs = messages.filter((m) => m.channelId === ch.id);
        return (
          <Card
            key={ch.id}
            title={<span>{ch.title} <Badge tone={ch.isConnected ? "green" : "red"}>{ch.isConnected ? "подключён" : "бот удалён из админов"}</Badge> <Badge>{ch.type}</Badge></span>}
            action={
              <form action={removeChannelAction}>
                <input type="hidden" name="botId" value={bot.id} />
                <input type="hidden" name="id" value={ch.id} />
                <ConfirmButton message="Удалить канал и его сообщения из панели?">Удалить</ConfirmButton>
              </form>
            }
          >
            <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
              <form action={updateChannelAction} className="space-y-3 rounded-xl bg-slate-50 p-4">
                <input type="hidden" name="botId" value={bot.id} />
                <input type="hidden" name="id" value={ch.id} />
                <p className="font-mono text-xs text-slate-500">chat_id: {ch.chatId}</p>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="autoAccept" defaultChecked={ch.autoAccept} /> Автоприём заявок</label>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="captcha" defaultChecked={ch.captcha} /> Капча перед приёмом</label>
                <Field label="Текст кнопки капчи">
                  <input name="captchaButtonText" className={inputCls} defaultValue={ch.captchaButtonText ?? ""} placeholder="✅ Я не робот" />
                </Field>
                <SubmitButton variant="ghost">Сохранить настройки</SubmitButton>
              </form>

              <div className="space-y-4">
                <div>
                  <h3 className="mb-2 text-sm font-semibold">Сообщения</h3>
                  {msgs.length === 0 ? (
                    <p className="text-sm text-slate-500">Сообщений нет — добавьте приветствие ниже.</p>
                  ) : (
                    <ul className="space-y-2">
                      {msgs.map((m) => (
                        <li key={m.id} className="flex items-start justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                          <div>
                            <Badge tone="blue">{kindLabel[m.kind] ?? m.kind}</Badge> <Badge>{m.languageCode}</Badge>
                            <p className="mt-1 whitespace-pre-wrap text-slate-700">{m.text}</p>
                            {m.buttons.length > 0 && <p className="mt-1 text-xs text-slate-500">Кнопки: {m.buttons.map((b) => b.text).join(", ")}</p>}
                          </div>
                          <form action={deleteChannelMessageAction}>
                            <input type="hidden" name="botId" value={bot.id} />
                            <input type="hidden" name="id" value={m.id} />
                            <ConfirmButton message="Удалить сообщение?">✕</ConfirmButton>
                          </form>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <details className="rounded-xl border border-dashed border-slate-300 p-4">
                  <summary className="cursor-pointer text-sm font-medium">Добавить / изменить сообщение</summary>
                  <ActionForm action={saveChannelMessageAction} className="mt-3">
                    <input type="hidden" name="botId" value={bot.id} />
                    <input type="hidden" name="channelId" value={ch.id} />
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Тип">
                        <select name="kind" className={inputCls} defaultValue="greeting">
                          <option value="greeting">Приветствие</option><option value="farewell">Прощание</option><option value="captcha">Текст капчи</option>
                        </select>
                      </Field>
                      <Field label="Язык" hint="any — для всех; ru, en… — по language_code">
                        <input name="languageCode" className={inputCls} defaultValue="any" />
                      </Field>
                    </div>
                    <Field label="Текст (HTML)" hint="Переменные: {name}, {username}">
                      <textarea name="text" rows={4} className={inputCls} />
                    </Field>
                    <div className="grid grid-cols-[1fr_120px] gap-3">
                      <Field label="file_id"><input name="fileId" className={inputCls} /></Field>
                      <Field label="Тип">
                        <select name="fileType" className={inputCls} defaultValue=""><option value="">—</option><option value="photo">photo</option><option value="video">video</option><option value="animation">animation</option><option value="document">document</option></select>
                      </Field>
                    </div>
                    <Field label="Кнопки-ссылки" hint="По одной на строку: Текст | https://url | номер_строки">
                      <textarea name="buttons" rows={3} className={inputCls} placeholder={"Наш сайт | https://example.com | 1\nЧат | https://t.me/chat | 2"} />
                    </Field>
                    <SubmitButton>Сохранить сообщение</SubmitButton>
                  </ActionForm>
                </details>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
