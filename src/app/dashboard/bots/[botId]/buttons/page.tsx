import { notFound } from "next/navigation";
import { asc, eq } from "drizzle-orm";
import { db } from "@/db";
import { menuButtons } from "@/db/schema";
import { requireAccount } from "@/lib/auth";
import { getBotForOwner } from "@/lib/bots";
import { ActionForm, Badge, BotTabs, Card, ConfirmButton, Field, inputCls, SubmitButton } from "@/components/ui";
import { deleteButtonAction, saveButtonAction } from "../../../actions";

export const dynamic = "force-dynamic";

export default async function ButtonsPage({ params, searchParams }: { params: Promise<{ botId: string }>; searchParams: Promise<{ edit?: string }> }) {
  const { botId } = await params;
  const { edit } = await searchParams;
  const account = await requireAccount();
  const bot = await getBotForOwner(Number(botId), account.id);
  if (!bot) notFound();

  const buttons = await db.select().from(menuButtons).where(eq(menuButtons.botId, bot.id)).orderBy(asc(menuButtons.position), asc(menuButtons.id));
  const editing = edit ? buttons.find((b) => b.id === Number(edit)) : undefined;
  const inlineParents = buttons.filter((b) => b.kind === "inline" && b.action !== "url" && b.id !== editing?.id);
  const byParent = (pid: number | null) => buttons.filter((b) => b.kind === "inline" && (b.parentId ?? null) === pid);

  const renderTree = (pid: number | null, depth = 0): React.ReactNode =>
    byParent(pid).map((b) => (
      <li key={b.id}>
        <ButtonRow b={b} botId={bot.id} depth={depth} />
        <ul>{renderTree(b.id, depth + 1)}</ul>
      </li>
    ));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">@{bot.username} · Меню</h1>
      <BotTabs botId={bot.id} />

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          <Card title="Inline-меню (под приветствием)">
            {byParent(null).length === 0 ? <Empty /> : <ul className="space-y-1">{renderTree(null)}</ul>}
          </Card>
          <Card title="Reply-клавиатура (кнопки внизу экрана)">
            {buttons.filter((b) => b.kind === "reply").length === 0 ? (
              <Empty />
            ) : (
              <ul className="space-y-1">
                {buttons.filter((b) => b.kind === "reply").map((b) => (
                  <li key={b.id}><ButtonRow b={b} botId={bot.id} depth={0} /></li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <Card title={editing ? `Редактировать «${editing.text}»` : "Новая кнопка"} action={editing && <a href={`/dashboard/bots/${bot.id}/buttons`} className="text-xs text-slate-500 hover:underline">отмена</a>}>
          <ActionForm action={saveButtonAction} key={editing?.id ?? "new"}>
            <input type="hidden" name="botId" value={bot.id} />
            {editing && <input type="hidden" name="id" value={editing.id} />}
            <Field label="Текст кнопки">
              <input name="text" className={inputCls} defaultValue={editing?.text ?? ""} required maxLength={64} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Тип">
                <select name="kind" className={inputCls} defaultValue={editing?.kind ?? "inline"}>
                  <option value="inline">inline</option>
                  <option value="reply">reply</option>
                </select>
              </Field>
              <Field label="Действие">
                <select name="action" className={inputCls} defaultValue={editing?.action ?? "send"}>
                  <option value="send">отправить сообщение</option>
                  <option value="edit">заменить сообщение</option>
                  <option value="url">открыть ссылку</option>
                </select>
              </Field>
            </div>
            <Field label="Родительская кнопка (вложенное меню)">
              <select name="parentId" className={inputCls} defaultValue={editing?.parentId ?? ""}>
                <option value="">— корень —</option>
                {inlineParents.map((p) => (
                  <option key={p.id} value={p.id}>{p.text}</option>
                ))}
              </select>
            </Field>
            <Field label="Ответ (текст, HTML)">
              <textarea name="replyText" rows={4} className={inputCls} defaultValue={editing?.replyText ?? ""} />
            </Field>
            <div className="grid grid-cols-[1fr_120px] gap-3">
              <Field label="file_id вложения">
                <input name="fileId" className={inputCls} defaultValue={editing?.fileId ?? ""} />
              </Field>
              <Field label="Тип файла">
                <select name="fileType" className={inputCls} defaultValue={editing?.fileType ?? ""}>
                  <option value="">—</option>
                  <option value="photo">photo</option>
                  <option value="video">video</option>
                  <option value="animation">animation</option>
                  <option value="document">document</option>
                  <option value="audio">audio</option>
                </select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="URL (для действия «ссылка»)">
                <input name="url" className={inputCls} defaultValue={editing?.url ?? ""} placeholder="https://" />
              </Field>
              <Field label="Команда (опц.)">
                <input name="command" className={inputCls} defaultValue={editing?.command ?? ""} placeholder="/prices" />
              </Field>
            </div>
            <Field label="Порядок">
              <input name="position" type="number" className={inputCls} defaultValue={editing?.position ?? 0} />
            </Field>
            <SubmitButton className="w-full">{editing ? "Сохранить" : "Добавить кнопку"}</SubmitButton>
          </ActionForm>
        </Card>
      </div>
    </div>
  );
}

function Empty() {
  return <p className="text-sm text-slate-500">Кнопок пока нет. Добавьте первую в форме справа.</p>;
}

function ButtonRow({ b, botId, depth }: { b: typeof menuButtons.$inferSelect; botId: number; depth: number }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2" style={{ marginLeft: depth * 20 }}>
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium">{b.text}</span>
        <Badge>{b.action}</Badge>
        {b.command && <Badge tone="blue">{b.command}</Badge>}
        {b.fileType && <Badge tone="amber">{b.fileType}</Badge>}
      </div>
      <div className="flex items-center gap-1">
        <a href={`/dashboard/bots/${botId}/buttons?edit=${b.id}`} className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100">Изменить</a>
        <form action={deleteButtonAction}>
          <input type="hidden" name="botId" value={botId} />
          <input type="hidden" name="id" value={b.id} />
          <ConfirmButton message={`Удалить кнопку «${b.text}»?`}>Удалить</ConfirmButton>
        </form>
      </div>
    </div>
  );
}
