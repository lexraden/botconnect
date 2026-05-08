from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.future import select
from sqlalchemy import update, func, and_, not_, or_
from config import admins
from dict import MESSAGES
from db import UserBot, get_db_session, get_lang, MainBotUser, BotSubscription, User
from handlers.bot_settings import MainBotSettingsStates
from handlers.handlers_for_added_bots import add_and_run_new_bot
from datetime import datetime, timedelta
import asyncio
import re
import logging

router = Router(name=__name__)

class AddBotStates(StatesGroup):
    waiting_for_token = State()

async def escape_markdown_v2(text: str) -> str:
    """
    Асинхронно экранирует специальные символы для MarkdownV2.
    """
    special_characters = r"_]()`>#+-=|}.!"
    for char in special_characters:
        text = text.replace(char, f"\\{char}")
    return text

@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    await state.clear()
    
    # Добавление пользователя в базу данных или проверка существования
    async with await get_db_session() as session:
        # Проверяем, существует ли пользователь с указанным user_id
        user_result = await session.execute(
            select(MainBotUser).filter(
                MainBotUser.user_id == user_id
            )
        )
        user = user_result.scalars().first()
        
        if not user:
            # Добавляем нового пользователя
            new_user = MainBotUser(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=None,  # Изначально язык не установлен
            )
            session.add(new_user)
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(e)
            # Предлагаем выбрать язык
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🇷🇺Русский", callback_data="lang_ru")],
                    [InlineKeyboardButton(text="🇺🇸English", callback_data="lang_en")],
                ]
            )
            await message.answer(
                "Выберите язык / Select your language:", reply_markup=keyboard
            )
            return
        
        # Если пользователь уже существует, проверяем установлен ли язык
        if not user.language_code:
            # Если язык не установлен, предлагаем выбрать
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🇷🇺Русский", callback_data="lang_ru")],
                    [InlineKeyboardButton(text="🇺🇸English", callback_data="lang_en")],
                ]
            )
            await message.answer(
                "Выберите язык / Select your language:", reply_markup=keyboard
            )
            return

        # Если язык установлен, выводим стартовое сообщение
        lang = user.language_code
        text = MESSAGES[lang]["start_message"]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["add_bot"], callback_data="add_bot"),
                    InlineKeyboardButton(text=MESSAGES[lang]["my_bots"], callback_data="my_bots"),
                ],
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["help"], callback_data="help"),
                    InlineKeyboardButton(text=MESSAGES[lang]["ads"], callback_data="ads"),
                ],
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["pro_subscription"], callback_data="subscription"),
                ],
                
            ]
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@router.message(Command("lang"))
async def lang_handler(message: Message):
    """
    Обработчик команды /lang. Отправляет Inline-клавиатуру с доступными языками.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇺🇸English", callback_data="lang_en")],
        ]
    )

    await message.answer(
        "Выберите язык / Select your language:", reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("lang_"))
async def language_selection_handler(callback_query: CallbackQuery):
    """
    Обрабатывает выбор языка через Inline-кнопки и сохраняет язык в базу данных.
    """
    user_id = callback_query.from_user.id
    selected_language = callback_query.data.split("_")[1]  # Получаем код языка
    
    async with await get_db_session() as session:
        await session.execute(
            update(MainBotUser)
            .where(MainBotUser.user_id == user_id)
            .values(language_code=selected_language)
        )
        await session.commit()

    lang = await get_lang(user_id)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=MESSAGES[lang]["add_bot"], callback_data="add_bot"),
                InlineKeyboardButton(text=MESSAGES[lang]["my_bots"], callback_data="my_bots"),
            ],
            [
                InlineKeyboardButton(text=MESSAGES[lang]["help"], callback_data="help"),
                InlineKeyboardButton(text=MESSAGES[lang]["ads"], callback_data="ads"),
            ],
            [
                InlineKeyboardButton(text=MESSAGES[lang]["pro_subscription"], callback_data="subscription"),
            ],
        ]
    )
    
    await callback_query.message.edit_text(MESSAGES[lang]["start_message"], parse_mode="Markdown", reply_markup=keyboard)

# Хендлер для нажатия на кнопку "Добавить бот"
@router.callback_query(F.data == "add_bot")
async def add_bot_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    text = MESSAGES[lang]["add_bot_instructions"]
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard.as_markup())
    await state.set_state(AddBotStates.waiting_for_token)
    await state.update_data(previous_state=MainBotSettingsStates.main_menu)
    await callback_query.answer()

# Обработчик текста для получения токена
@router.message(AddBotStates.waiting_for_token)
async def handle_token(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    text = message.text.strip()

    # Регулярное выражение для поиска токена
    token_pattern = r'\b(\d+:[A-Za-z0-9_-]{35})\b'
    match = re.search(token_pattern, text)

    if not match:
        await message.answer(MESSAGES[lang]["invalid_token"])
        return

    token = match.group(1)  # Извлекаем токен из совпадения
    logging.info(token)
    # Проверка токена через Telegram API
    try:
        async with Bot(token=token) as new_bot:  # Контекстный менеджер для корректного закрытия сессии
            me = await new_bot.get_me()
    except Exception:
        await message.answer(MESSAGES[lang]["invalid_token"])
        return

    # Подтверждение подключения
    bot_username = me.username
    was_activated = await add_and_run_new_bot(token, bot_username, user_id)

    if was_activated:
        # Бот добавлен и включен
        async with await get_db_session() as session:
            # Проверяем, существует ли бот с таким токеном в базе
            result = await session.execute(select(UserBot).filter(UserBot.bot_token == token))
            bot_entry = result.scalars().first()

            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["configure_bot"], callback_data=f"bot_{bot_entry.id}"))

        response_text = MESSAGES[lang]["bot_connected"].format(bot_username=bot_username)
        await message.answer(
            text = response_text,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
    else:
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["pay_subscription"], callback_data=f"subscription"))
            
        # Бот добавлен, но не включен из-за превышения лимита
        response_text = MESSAGES[lang]["bot_connected_but_not_activated"].format(bot_username=bot_username)
        await message.answer(
            text = response_text,
            reply_markup=keyboard.as_markup()
        )

    # Завершаем состояние
    await state.clear()
    
@router.callback_query(F.data == "my_bots")
async def my_bots_callback(callback_query: CallbackQuery, state: FSMContext):
    # Извлекаем user_id и определяем язык пользователя
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    # Получаем сессию базы данных
    async with await get_db_session() as session:
        # Запрос на получение всех ботов для текущего пользователя
        result = await session.execute(select(UserBot).filter(UserBot.user_id == user_id))
        user_bots = result.scalars().all()

    # Если боты найдены, создаём inline клавиатуру
    if user_bots:
        keyboard = InlineKeyboardBuilder()

        for bot in user_bots:
            # Создаём кнопку для каждого бота
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["bot_button"].format(bot_username=bot.bot_username),
                    callback_data=f"bot_{bot.id}"
                )
            )

        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

        bot_list_text = MESSAGES[lang]["your_bots"]
        await callback_query.message.edit_text(bot_list_text, reply_markup=keyboard.as_markup())
        await state.update_data(previous_state=MainBotSettingsStates.main_menu)
    else:
        # Клавиатура, если ботов нет
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["add_bot"], callback_data="add_bot"),
                    InlineKeyboardButton(text=MESSAGES[lang]["my_bots"], callback_data="my_bots"),
                ],
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["help"], callback_data="help"),
                    InlineKeyboardButton(text=MESSAGES[lang]["ads"], callback_data="ads"),
                ],
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["pro_subscription"], callback_data="subscription"),
                ],
            ]
        )
        bot_list_text = MESSAGES[lang]["no_bots"]
        await callback_query.message.edit_text(text=bot_list_text, reply_markup=keyboard)

    # Ответ на callback
    await callback_query.answer()

@router.callback_query(F.data == "help")
async def help_button(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back")
        )
    
    await callback_query.message.edit_text(MESSAGES[lang]["help_button"], reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await state.update_data(previous_state=MainBotSettingsStates.main_menu)
    
    await callback_query.answer()

@router.callback_query(F.data.startswith("bot_"))
async def my_bots_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    bot_id = int(callback_query.data.split("_")[-1])
    
    async with await get_db_session() as session:
        # Запрос на получение всех ботов для текущего пользователя
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot = result.scalars().first()
    
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["bot_settings"], url=f"https://t.me/{bot.bot_username}?start=settings")
        )
    if bot.is_started:
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["disable_bot"], callback_data=f"disable_bot_{bot.id}")
        )
    else:
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["enable_bot"], callback_data=f"enable_bot_{bot.id}")
        )
    keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["bot_delete_button"], callback_data=f"delete_bot_{bot.id}")
        )
    keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back")
        )
    
    await callback_query.message.edit_text(text = MESSAGES[lang]["bot_settings_description"], reply_markup=keyboard.as_markup(), parse_mode = "Markdown")
    await state.update_data(previous_state=MainBotSettingsStates.main_menu, bot_id=bot.id)

@router.callback_query(F.data.startswith("disable_bot_"))
async def disable_bot_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "Отключить бота".
    """
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    bot_id = int(callback_query.data.split("_")[2])

    async with await get_db_session() as session:
        # Получаем бота из базы данных
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()

        if not bot_entry:
            await callback_query.message.edit_text(MESSAGES[lang]["bot_not_found"])
            await callback_query.answer()
            return

        # Отключаем бота в базе данных
        bot_entry.is_started = False
        await session.commit()

    # Завершение работы задачи бота
    try:
        BOT = Bot(bot_entry.bot_token)
        await BOT.delete_webhook()
        await BOT.session.close()

        # Получаем информацию о боте из базы данных
        async with await get_db_session() as session:
            result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
            bot = result.scalars().first()

        if bot:
            # Генерируем клавиатуру с действиями для управления ботом
            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["bot_settings"], url=f"https://t.me/{bot.bot_username}?start=settings")
                )
            if bot.is_started:
                keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["disable_bot"], callback_data=f"disable_bot_{bot.id}")
                )
            else:
                keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["enable_bot"], callback_data=f"enable_bot_{bot.id}")
                )
            keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["bot_delete_button"], callback_data=f"delete_bot_{bot_entry.id}")
                )
            keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back")
                )

            # Отправляем сообщение с меню
            await callback_query.message.edit_text(
                text=MESSAGES[lang]["bot_settings_description"],
                reply_markup=keyboard.as_markup()
            )
        else:
            await callback_query.answer(MESSAGES[lang]["bot_not_found"], show_alert=True)

        await state.update_data(previous_state=MainBotSettingsStates.main_menu, bot_id=bot_id)
        await callback_query.answer()
    except Exception as e:
        await callback_query.message.edit_text(MESSAGES[lang]["bot_disable_error"].format(error=str(e)))

    await callback_query.answer()

@router.callback_query(F.data.startswith("enable_bot_"))
async def activate_bot_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "Включить бота" с проверкой лимита.
    """
    from handlers.handlers_for_added_bots import setup_and_run_bot

    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    bot_id = int(callback_query.data.split("_")[2])

    async with await get_db_session() as session:
        # Получаем бота из базы данных
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()

        if not bot_entry:
            await callback_query.message.edit_text(MESSAGES[lang]["bot_not_found"])
            await callback_query.answer()
            return

        # Проверяем, включен ли бот
        if bot_entry.is_started:
            await callback_query.message.edit_text(
                MESSAGES[lang]["bot_already_active"].format(bot_username=bot_entry.bot_username)
            )
            await callback_query.answer()
            return

        # Подсчитываем количество включенных ботов для пользователя
        active_bots_count = await session.execute(
            select(func.count(UserBot.id))
            .filter(UserBot.user_id == user_id, UserBot.is_started == True)
        )
        active_bots_count = active_bots_count.scalar() or 0

        user_bots_result = await session.execute(
                select(UserBot.id).filter(UserBot.user_id == user_id)
            )
        user_bots_ids = [bot for bot in user_bots_result.scalars().all()]

        # Считаем количество активных подписок для этих ботов
        active_subscription_count = 0
        if user_bots_ids:
            active_subscription_count_result = await session.execute(
                select(func.count(BotSubscription.id))
                .filter(BotSubscription.bot_id.in_(user_bots_ids))
            )
            active_subscription_count = active_subscription_count_result.scalar() or 0
        
        # Лимит включенных ботов
        bot_limit = 3 + active_subscription_count
        if active_bots_count >= bot_limit:
            # Генерация клавиатуры
            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["pay_subscription"], callback_data=f"subscription")
                )
            keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back")
                )

            # Вывод сообщения о превышении лимита
            await callback_query.message.edit_text(
                MESSAGES[lang]["bot_activation_limit_exceeded"].format(limit=bot_limit),
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            await callback_query.answer()
            return

        # Обновляем статус бота в базе данных
        bot_entry.is_started = True
        await session.commit()

    # Запускаем бота
    try:
        asyncio.create_task(setup_and_run_bot(bot_entry.bot_token))

        # Обновляем клавиатуру и сообщение
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["bot_settings"], url=f"https://t.me/{bot_entry.bot_username}?start=settings")
            )
        if bot_entry.is_started:
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["disable_bot"], callback_data=f"disable_bot_{bot_entry.id}")
            )
        else:
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["enable_bot"], callback_data=f"enable_bot_{bot_entry.id}")
            )
        keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["bot_delete_button"], callback_data=f"delete_bot_{bot_entry.id}")
            )
        keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back")
            )

        await callback_query.message.edit_text(
            text=MESSAGES[lang]["bot_settings_description"],
            reply_markup=keyboard.as_markup(),
        )
    except Exception as e:
        # Если ошибка, откатываем статус
        async with await get_db_session() as session:
            bot_entry.is_started = False
            await session.commit()

        await callback_query.message.edit_text(MESSAGES[lang]["bot_activate_error"].format(error=str(e)))

    await callback_query.answer()

@router.callback_query(F.data.startswith("delete_bot_"))
async def bot_delete(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    bot_id = int(callback_query.data.split("_")[-1])
    lang = await get_lang(user_id)
    
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        user_bot = result.scalars().first()
        
        sub_result = await session.execute(select(BotSubscription).filter(BotSubscription.bot_id == bot_id))
        subscription = sub_result.scalars().first()
        
    keyboard = InlineKeyboardBuilder()
    
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["accept_bot_delete"], callback_data=f"accept_delete_bot_{bot_id}"))
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    
    await state.update_data(previous_state=MainBotSettingsStates.main_menu, bot_id=bot_id)
    
    await callback_query.message.edit_text(text=MESSAGES[lang]["bot_delete_asnwer"].format(bot_name = user_bot.bot_username) + MESSAGES[lang]["bot_has_subscription"] if subscription else MESSAGES[lang]["bot_delete_asnwer"].format(bot_name = user_bot.bot_username),
                                           reply_markup=keyboard.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("accept_delete_bot_"))
async def accept_bot_delete(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    bot_id = int(callback_query.data.split("_")[-1])
    lang = await get_lang(user_id)
    
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        user_bot = result.scalars().first()
        
        await session.delete(user_bot)
        await session.commit()
    
    try:
        bot = Bot(token=user_bot.bot_token)
        await bot.delete_webhook()
        await bot.session.close()
    except:
        logging.info("Ошибка при удалении бота")
        
    async with await get_db_session() as session:
        # Запрос на получение всех ботов для текущего пользователя
        result = await session.execute(select(UserBot).filter(UserBot.user_id == user_id))
        user_bots = result.scalars().all()

    # Если боты найдены, создаём inline клавиатуру
    if user_bots:
        keyboard = InlineKeyboardBuilder()

        for bot in user_bots:
            # Создаём кнопку для каждого бота
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["bot_button"].format(bot_username=bot.bot_username),
                    callback_data=f"bot_{bot.id}"
                )
            )

        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

        bot_list_text = MESSAGES[lang]["your_bots"]
        await callback_query.message.edit_text(bot_list_text, reply_markup=keyboard.as_markup())
        await state.update_data(previous_state=MainBotSettingsStates.main_menu)
    else:
        # Клавиатура, если ботов нет
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["add_bot"], callback_data="add_bot"),
                    InlineKeyboardButton(text=MESSAGES[lang]["my_bots"], callback_data="my_bots"),
                ],
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["help"], callback_data="help"),
                    InlineKeyboardButton(text=MESSAGES[lang]["ads"], callback_data="ads"),
                ],
                [
                    InlineKeyboardButton(text=MESSAGES[lang]["pro_subscription"], callback_data="subscription"),
                ],
            ]
        )
        bot_list_text = MESSAGES[lang]["no_bots"]
        await callback_query.message.edit_text(text=bot_list_text, reply_markup=keyboard)

@router.message(Command("stats"))
async def main_bot_stats(message: Message, state: FSMContext):
    
    if message.from_user.id not in admins:
        return
    
    async with await get_db_session() as session:
        now = datetime.now()

        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result_today = await session.execute(
            select(func.count())
            .select_from(MainBotUser)
            .filter(MainBotUser.created_at >= start_of_day)
        )
        users_today = result_today.scalar()

        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result_month = await session.execute(
            select(func.count())
            .select_from(MainBotUser)
            .filter(MainBotUser.created_at >= start_of_month)
        )
        users_this_month = result_month.scalar()
        
        result_month_secondary_bots = await session.execute(
            select(func.count(func.distinct(User.user_id)))
            .select_from(User)
            .filter(User.created_at >= start_of_month)
        )
        users_this_month_secondary_bots = result_month_secondary_bots.scalar()

        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        result_year = await session.execute(
            select(func.count())
            .select_from(MainBotUser)
            .filter(MainBotUser.created_at >= start_of_year)
        )
        users_this_year = result_year.scalar()
        
        # Запрос для подсчета пользователей ботов без активной подписки
        result_total_for_ads = await session.execute(
            select(func.count(func.distinct(User.user_id)))
            .select_from(User)
            .join(User.bot)  # Присоединяем бота к пользователю
            .outerjoin(BotSubscription, UserBot.id == BotSubscription.bot_id)  
            .filter(
                UserBot.is_started == True,  # Бот включен
                BotSubscription.id.is_(None)  # Нет активной подписки
            )
        )
        total_users_for_ads = result_total_for_ads.scalar()
        
        result_total = await session.execute(
            select(func.count(func.distinct(User.user_id)))  # Считаем уникальные user_id
            .select_from(User)
        )

        total_users = result_total.scalar()
        
        result_total_main_bot = await session.execute(
            select(func.count())
            .select_from(MainBotUser)
        )
        total_users_main_bot = result_total_main_bot.scalar()
        
        result_subscription = await session.execute(
            select(func.count())
            .select_from(BotSubscription)
        )
        total_subscriptions = result_subscription.scalar()
        
        result_total_bots = await session.execute(
            select(func.count())
            .select_from(UserBot)
        )
        total_bots = result_total_bots.scalar()
        
        stats_message = (
                    f"Статистика\n\n"
                    "🔹Главный бот\n"
                    f"  Пользователи за день: {users_today}\n"
                    f"  Пользователи за месяц: {users_this_month}\n"
                    f"  Пользователи за год: {users_this_year}\n"
                    f"  Пользователей в главном боте: {total_users_main_bot}\n"
                    "🔹Второстепенные боты\n"
                    f"  Пользователи за месяц: {users_this_month_secondary_bots}\n"
                    f"  Всего ботов: {total_bots}\n"
                    f"  Всего пользователей в ботах: {total_users}\n" 
                    f"  Всего пользователей для рекламы: {total_users_for_ads}\n"                  
                    f"  Всего платных подписок: {total_subscriptions}"
                )
        
        await message.answer(stats_message)