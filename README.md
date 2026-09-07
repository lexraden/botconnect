# Bot Connect v2 — конструктор Telegram-ботов с веб-панелью

> **v2 — полная переработка.** Весь код v1 (Python / aiogram / FastAPI, ~10 400 строк
> Telegram-меню) заменён на **Next.js 16 (App Router) + Drizzle ORM + PostgreSQL**
> с веб-панелью управления и stateless-обработкой вебхуков.

Bot Connect позволяет за 30 секунд подключить бота из @BotFather и получить:

| Модуль | Что умеет |
|---|---|
| 💬 **Обратная связь** | Сообщения пользователей копируются в вашу группу; ответ reply'ем уходит обратно пользователю. Бан/разбан кнопкой или `/ban`, `/unban`, `/fileid`. |
| 🧩 **Меню** | Inline- и reply-кнопки, вложенные разделы с «Назад», URL-кнопки, привязка к `/командам`, медиа-вложения, действие «заменить сообщение». |
| 📣 **Рассылки** | Мгновенные и отложенные, с кнопкой-ссылкой и вложением. Пакетная отправка с курсором (возобновляемая), учёт заблокировавших, дневные лимиты FREE/PRO. |
| 🛡️ **Каналы** | Автоподключение при добавлении бота админом, автоприём заявок, капча, приветствия/прощания по языкам с кнопками, `{name}`/`{username}`. |
| 💳 **Подписка** | Тарифы в USDT через @CryptoBot: создание счёта, подписанный вебхук `invoice_paid`, фолбэк-сверка в кроне, продление «встык». |
| 🔐 **Вход** | Telegram Login Widget **или** magic-link из главного бота (`/login`). Без паролей. |

---

## Что было не так в v1 и как это решено в v2

### Безопасность
| v1 | v2 |
|---|---|
| Токен бота в URL вебхука `/bot/{token}` → утекал в access-логи (в репо даже был фильтр-маскировщик логов) | URL содержит только внутренний `botId`; подлинность проверяется заголовком `X-Telegram-Bot-Api-Secret-Token` (уникальный секрет на бота) |
| Токены в БД открытым текстом | AES-256-GCM (`ENCRYPTION_KEY`), в UI токен не показывается |
| `bot_token` — внешний ключ в `users`, `bot_menu_buttons` → нельзя перевыпустить токен | Все связи по `bots.id`; повторное подключение бота с новым токеном просто ротирует токен и секрет |
| Любой POST на `/bot/{что угодно}` создавал `Bot()` и обрабатывал апдейт | 404 / 403 до какой-либо обработки; идемпотентность по `update_id` (Telegram ретраит апдейты) |
| Главный бот и подключённые боты — один вебхук-роут | Разделены; главный бот — отдельный секрет |

### Логика
| v1 | v2 |
|---|---|
| `process_scheduled_mailings` содержит `while True`, и его же вызывают в `while True` из `main.py` (вложенный бесконечный цикл) | HTTP-крон `GET /api/cron` раз в минуту; атомарный захват рассылки через `FOR UPDATE SKIP LOCKED` — несколько воркеров не отправят одно и то же дважды |
| Проверка подписки не смотрела на `end_date` → истёкшая подписка давала лимит 50 000 | `getActiveSubscription` фильтрует `ends_at > now()`; лимиты считаются от активной подписки |
| Polling всех pending-платежей каждые 60 с, без TTL | Вебхук CryptoBot с проверкой HMAC-подписи; счета с TTL 1 ч; сверка только «живых» счетов |
| `channel_id` уникален глобально — канал нельзя подключить к двум ботам | Уникальность `(bot_id, chat_id)` |
| `len(result.scalars().all())` для подсчёта, naive MSK-время вперемешку с UTC, `datetime.utcnow()` | `COUNT(*)`, `timestamptz` везде, `numeric` для денег |
| Ответ админа искался по метаданным forward (ломается у пользователей со скрытым аккаунтом) | Таблица `forwarded_messages` — точное сопоставление `admin_message_id → user` |

### Архитектура и эксплуатация
| v1 | v2 |
|---|---|
| `MemoryStorage` FSM + фоновые задачи в процессе → один инстанс, всё теряется при рестарте | Полностью stateless: любое число инстансов / serverless, состояние — только в PostgreSQL |
| Файлы по 900–1100 строк (`go_back.py` — 909 строк навигации по меню) | Вся настройка — веб-панель (server actions); обработчик Telegram ~500 строк |
| `Base.metadata.create_all` + ad-hoc `ALTER TABLE` в коде | Drizzle-схема + SQL-миграции в `drizzle/` |
| Нет тестов, CI, Dockerfile, типов | TypeScript strict, ESLint, GitHub Actions, Dockerfile, docker-compose (app + db + cron), `vercel.json` с кроном |
| `aiogram` держал aiohttp-сессии на каждый вебхук (не закрывались) | Тонкий fetch-клиент Bot API без long-lived сессий, `retry_after` для 429 |

---

## Быстрый старт (локально)

```bash
git clone https://github.com/lexraden/botconnect.git && cd botconnect
cp .env.example .env            # заполните переменные
npm ci
npx drizzle-kit push            # создать таблицы (или: npx drizzle-kit migrate)
npm run dev                     # http://localhost:3000
```

Для локальной разработки без Telegram-логина поставьте `ALLOW_DEV_LOGIN=true` —
на `/login` появится форма входа по Telegram ID. **В продакшене выключите.**

Чтобы Telegram доставлял апдейты локально, пробросьте туннель (`ngrok http 3000`) и
укажите его адрес в `PUBLIC_URL`. После этого на странице бота нажмите «Переподключить вебхук».

## Docker

```bash
cp .env.example .env && nano .env
docker compose up -d --build
docker compose exec app npx drizzle-kit migrate
```

`docker-compose.yml` поднимает PostgreSQL, приложение и sidecar-крон (curl раз в минуту).

## Деплой на Vercel / Railway

1. Задайте переменные окружения из `.env.example` (`PUBLIC_URL` — ваш HTTPS-домен).
2. Примените миграции: `npx drizzle-kit migrate` (с `DATABASE_URL` прод-базы).
3. Крон: на Vercel он уже описан в `vercel.json` и автоматически шлёт `Authorization: Bearer $CRON_SECRET`.
   На Railway/VPS — любой планировщик:
   `* * * * * curl -fsS -H "Authorization: Bearer $CRON_SECRET" https://ваш-домен/api/cron`
4. Главный бот (опционально, для входа через Telegram): задайте `MAIN_BOT_TOKEN`, `MAIN_BOT_USERNAME`,
   `MAIN_BOT_WEBHOOK_SECRET`, в @BotFather → `/setdomain` укажите ваш домен, затем один раз установите вебхук:
   ```bash
   curl "https://api.telegram.org/bot$MAIN_BOT_TOKEN/setWebhook" \
     -d url="$PUBLIC_URL/api/telegram/main" -d secret_token="$MAIN_BOT_WEBHOOK_SECRET"
   ```
5. Платежи (опционально): создайте приложение в @CryptoBot → Crypto Pay, токен в `CRYPTO_BOT_TOKEN`,
   вебхук `https://ваш-домен/api/payments/cryptobot`.

## Структура

```
src/
├── app/
│   ├── api/
│   │   ├── telegram/bots/[botId]/route.ts   # вебхук подключённых ботов (secret_token)
│   │   ├── telegram/main/route.ts           # вебхук главного бота (логин)
│   │   ├── cron/route.ts                    # рассылки, сверка платежей, уборка
│   │   ├── payments/cryptobot/route.ts      # вебхук CryptoBot (HMAC)
│   │   ├── auth/{telegram,magic,dev,logout} # аутентификация
│   │   └── health/route.ts
│   ├── dashboard/
│   │   ├── actions.ts                       # все server actions (CRUD)
│   │   ├── page.tsx                         # список ботов + подключение
│   │   └── bots/[botId]/{page,buttons,mailings,users,channels,subscription}
│   ├── login/page.tsx
│   └── page.tsx                             # лендинг
├── components/ui.tsx                        # мелкие UI-примитивы
├── db/{schema.ts,index.ts}                  # Drizzle
└── lib/
    ├── telegram/{api,types,handle-update,main-bot}.ts
    ├── auth.ts  bots.ts  mailing.ts  payments.ts  crypto.ts  env.ts
drizzle/                                     # SQL-миграции
```

## Переменные окружения

См. `.env.example`. Обязательные для продакшена: `DATABASE_URL`, `PUBLIC_URL`, `SESSION_SECRET`,
`ENCRYPTION_KEY`, `CRON_SECRET`. Остальные включают отдельные модули (логин через Telegram, платежи).

`SESSION_SECRET` и `ENCRYPTION_KEY` при `NODE_ENV=production` обязательны: без них приложение
отвечает ошибкой, а не подставляет запасное значение. Запасное значение лежит в исходниках,
поэтому с ним кто угодно подделал бы сессионную куку и расшифровал бы токены ботов.

`drizzle-kit` берёт адрес базы из `DATABASE_URL` (см. `drizzle.config.ts`).

## Миграция данных с v1

Таблицы v2 несовместимы с v1 по дизайну (токены зашифрованы, связи по id).
Скрипт переноса сводится к: для каждой строки `user_bots` → `connectBot(ownerId, bot_token)`
(проверит токен, зашифрует и поставит вебхук), затем перенести `users` → `bot_users`,
`bot_menu_buttons` → `menu_buttons` (`bot_token` → `bots.id`), `bots_channels` → `channels`.
Активные подписки — `bot_subscriptions` с `end_date > now()` → `subscriptions`.

## Лицензия

MIT
