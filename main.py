import asyncio
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request
from aiogram import types, Bot, Dispatcher
from handlers import start, bot_settings
from config import bot, dp, WEBHOOK_TUNNEL_URL, TOKEN
from db import create_tables, UserBot, get_db_session, engine
from sqlalchemy.future import select
from handlers import handlers_for_added_bots, ads, go_back, subscription, go_back_main
import uvicorn
from handlers.menu_handlers import adding_button, editing_buttons, mailing
from handlers.channels import channels, channel_access, channel_messages, channel_settings, channel_messages_settings

dp_for_added_bots = Dispatcher()

dp_for_added_bots.include_routers(channels.router, channel_access.router, channel_messages.router, channel_settings.router, channel_messages_settings.router)
dp_for_added_bots.include_router(bot_settings.router)
dp_for_added_bots.include_router(adding_button.router)
dp_for_added_bots.include_router(editing_buttons.router)
dp_for_added_bots.include_router(go_back.router)
dp_for_added_bots.include_router(mailing.router)
dp_for_added_bots.include_router(handlers_for_added_bots.router)

app = FastAPI()

# Уникальный путь для основного бота
MAIN_BOT_WEBHOOK_PATH = f"/bot/{TOKEN}"
MAIN_BOT_WEBHOOK_URL = f"{WEBHOOK_TUNNEL_URL}{MAIN_BOT_WEBHOOK_PATH}"

async def periodic_mailing_task():
    while True:
        try:
            await mailing.process_scheduled_mailings()
        except Exception as e:
            logging.error(f"Ошибка в обработке рассылок: {e}")
        await asyncio.sleep(60)  # Интервал в секундах между проверками

# Периодическая проверка платежей
async def periodic_subscription_check_task(bot: Bot):
    while True:
        try:
            await subscription.check_pending_payments(bot)
        except Exception as e:
            logging.error(f"Ошибка в проверке платежей: {e}")
        await asyncio.sleep(60)  # Интервал в секундах между проверками

async def periodic_subscription_check(bot: Bot):
    while True:
        await subscription.check_and_remove_expired_subscriptions(bot)
        await asyncio.sleep(3600)  # Час

# Настройка webhook для основного бота
@app.on_event("startup")
async def setup_main_bot_webhook():
    """
    Настройка webhook для основного бота.
    """
    await create_tables()
    
    asyncio.create_task(periodic_mailing_task())
    asyncio.create_task(periodic_subscription_check_task(bot))
    asyncio.create_task(periodic_subscription_check(bot))
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # Логи в консоль
            RotatingFileHandler(
                "bot.log",           # Имя файла для записи логов
                maxBytes=50 * 1024 * 1024,  # Максимальный размер файла (5 МБ)
                backupCount=3             # Количество резервных копий
            )
        ]
    )

    # Регистрация хендлеров для основного бота
    dp.include_router(start.router)
    dp.include_router(subscription.router)
    dp.include_router(go_back_main.router)
    dp.include_router(ads.router)

    commands = [
        types.BotCommand(command="/start", description="Начать"),
        types.BotCommand(command="/lang", description="Поменять язык"),
        types.BotCommand(command="/help", description="Помощь")
    ]
    await bot.set_my_commands(commands)

    # Устанавливаем webhook
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != MAIN_BOT_WEBHOOK_URL:
        await bot.set_webhook(url=MAIN_BOT_WEBHOOK_URL, drop_pending_updates = True)

@app.post(MAIN_BOT_WEBHOOK_PATH)
async def process_main_bot_webhook(request: Request):
    """
    Обработка запросов для основного бота.
    """
    try:
        telegram_update = types.Update(**await request.json())
        await dp.feed_update(bot, telegram_update)
    except Exception as e:
        logging.error(f"Ошибка при обработке вебхука: {e}")
    
    # Возвращаем 200 даже в случае ошибки
    return {"status": "success"}

# Настройка webhook для всех добавленных ботов
@app.on_event("startup")
async def setup_added_bots_webhook():
    """
    Настройка webhook для всех добавленных ботов.
    """
    async with await get_db_session() as session:
        # Получаем токены всех ботов из базы данных
        result = await session.execute(select(UserBot.bot_token).filter(UserBot.is_started == True))
        bot_tokens = [row[0] for row in result.fetchall()]

    # Устанавливаем webhook для каждого добавленного бота
    for bot_token in bot_tokens:
        await handlers_for_added_bots.setup_and_run_bot(bot_token)

@app.post("/bot/{bot_token}")
async def process_added_bot_webhook(bot_token: str, request: Request):
    """
    Обработка запросов webhook для добавленных ботов.
    """
    try:
        request_data = await request.json()
        telegram_update = types.Update(**request_data)

        # Генерируем Dispatcher и Bot для конкретного токена
        bot = Bot(token=bot_token)
        # Обрабатываем обновление
        await dp_for_added_bots.feed_update(bot, telegram_update)

    except Exception as e:
        logging.error(f"Ошибка при обработке вебхука: {e}")
    
    # Возвращаем 200 даже в случае ошибки
    return {"status": "success"}

@app.on_event("shutdown")
async def on_shutdown():
    """
    Завершение работы ботов.
    """
    try:
        # Удаляем webhook для основного бота
        await bot.delete_webhook(drop_pending_updates = True)
        await bot.session.close()

        # Завершаем работу всех добавленных ботов
        async with await get_db_session() as session:
            result = await session.execute(select(UserBot.bot_token))
            bot_tokens = [row[0] for row in result.fetchall()]
            for bot_token in bot_tokens:
                added_bot = Bot(token=bot_token)
                await added_bot.delete_webhook(drop_pending_updates = True)
                await added_bot.session.close()
        
        await engine.dispose()

    except Exception as e:
        print(f"Ошибка при завершении работы: {e}")
