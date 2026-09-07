import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentAccount } from "@/lib/auth";
import { env } from "@/lib/env";
import { inputCls } from "@/components/ui";

export const dynamic = "force-dynamic";

const errors: Record<string, string> = {
  telegram: "Не удалось проверить данные Telegram. Попробуйте ещё раз.",
  expired: "Ссылка для входа истекла или уже использована. Запросите новую командой /login.",
  dev: "Введите корректный Telegram ID.",
};

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  if (await getCurrentAccount()) redirect("/dashboard");
  const { error } = await searchParams;
  const botUsername = env.mainBotUsername;
  const widget = Boolean(env.mainBotToken && botUsername);

  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/60">
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-800">← На главную</Link>
        <h1 className="mt-4 text-2xl font-bold">Вход в панель</h1>
        <p className="mt-1 text-sm text-slate-600">Авторизация через Telegram — пароли не нужны.</p>

        {error && <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{errors[error] ?? "Ошибка входа"}</p>}

        {widget ? (
          <div className="mt-6 space-y-4">
            <div className="flex justify-center">
              {/* Telegram Login Widget: https://core.telegram.org/widgets/login */}
              <script async src="https://telegram.org/js/telegram-widget.js?22" data-telegram-login={botUsername} data-size="large" data-auth-url="/api/auth/telegram" data-request-access="write" />
            </div>
            <p className="text-center text-xs text-slate-500">или</p>
            <a href={`https://t.me/${botUsername}?start=login`} className="block rounded-xl border border-slate-300 px-4 py-3 text-center text-sm font-medium hover:bg-slate-50">
              Получить ссылку для входа в @{botUsername}
            </a>
          </div>
        ) : (
          <div className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
            Главный бот не настроен. Укажите <code>MAIN_BOT_TOKEN</code> и <code>MAIN_BOT_USERNAME</code> в переменных окружения, чтобы включить вход через Telegram.
          </div>
        )}

        {env.allowDevLogin && (
          <form action="/api/auth/dev" method="post" className="mt-6 space-y-3 rounded-xl border border-dashed border-slate-300 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Dev-вход (ALLOW_DEV_LOGIN=true)</p>
            <input name="telegram_id" type="number" placeholder="Ваш Telegram ID, напр. 123456789" defaultValue="123456789" className={inputCls} required />
            <input name="name" placeholder="Имя" defaultValue="Dev User" className={inputCls} />
            <button className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">Войти без Telegram</button>
          </form>
        )}
      </div>
    </main>
  );
}
