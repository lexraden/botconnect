import Link from "next/link";
import { getCurrentAccount } from "@/lib/auth";

export const dynamic = "force-dynamic";

const features = [
  { icon: "💬", title: "Обратная связь", text: "Сообщения пользователей попадают в вашу группу, ответ reply'ем уходит обратно. Бан в один клик." },
  { icon: "🧩", title: "Меню и команды", text: "Inline- и reply-кнопки, вложенные разделы, ссылки, привязка к /командам, медиа-вложения." },
  { icon: "📣", title: "Рассылки", text: "Мгновенные и отложенные рассылки с кнопкой, авто-учёт заблокировавших, дневные лимиты." },
  { icon: "🛡️", title: "Каналы", text: "Автоприём заявок, капча, приветствия и прощания с кнопками по языкам." },
  { icon: "🔐", title: "Безопасность", text: "Токены зашифрованы AES-256-GCM, вебхуки с secret_token, идемпотентная обработка апдейтов." },
  { icon: "⚡", title: "Масштабирование", text: "Stateless-обработчики без in-memory состояния: любое число инстансов, cron через HTTP." },
];

export default async function HomePage() {
  const account = await getCurrentAccount();
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-sky-600 text-white">🤖</span>
          Bot Connect <span className="rounded-md bg-sky-100 px-1.5 text-xs font-bold text-sky-700">v2</span>
        </div>
        <Link href={account ? "/dashboard" : "/login"} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
          {account ? "Открыть панель" : "Войти"}
        </Link>
      </header>

      <section className="mt-20 text-center">
        <h1 className="text-[clamp(2rem,6vw,3.5rem)] font-bold leading-tight tracking-tight text-slate-950">
          Конструктор Telegram-ботов<br />с веб-панелью
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600">
          Подключите бота из @BotFather за 30 секунд — получите бота обратной связи, меню, рассылки и защиту каналов. Без кода и без хостинга.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href={account ? "/dashboard" : "/login"} className="rounded-xl bg-sky-600 px-6 py-3 text-base font-semibold text-white shadow-lg shadow-sky-200 hover:bg-sky-700">
            Начать бесплатно
          </Link>
          <a href="https://github.com/lexraden/botconnect" className="rounded-xl border border-slate-300 bg-white px-6 py-3 text-base font-semibold text-slate-700 hover:bg-slate-50">
            GitHub
          </a>
        </div>
      </section>

      <section className="mt-20 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="text-2xl">{f.icon}</div>
            <h3 className="mt-3 font-semibold text-slate-900">{f.title}</h3>
            <p className="mt-1 text-sm text-slate-600">{f.text}</p>
          </div>
        ))}
      </section>

      <footer className="mt-20 border-t border-slate-200 pt-6 text-center text-sm text-slate-500">
        Next.js · Drizzle ORM · PostgreSQL · Telegram Bot API
      </footer>
    </main>
  );
}
