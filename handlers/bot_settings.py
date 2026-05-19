from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery, InputMediaAudio, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardButton, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import UserBot, get_db_session, User, get_lang, Mailing, BotMenuButton, BotSubscription, Channels
from dict import MESSAGES
from sqlalchemy.future import select
from sqlalchemy import func
import asyncio
import csv
import io
from config import dp
from datetime import datetime
from handlers.menu_handlers.adding_button import BotSettingsStates

router = Router(name=__name__)

class MainBotSettingsStates(StatesGroup):
    main_menu = State()
    bot_settings = State()
    editing_greeting = State()

@router.callback_query(F.data.startswith("statistics_"))
async def statistics_callback(callback_query: CallbackQuery, state: FSMContext):
    # Извлекаем user_id и определяем язык пользователя
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    bot_id = int(callback_query.data.split("_")[1])  # Извлекаем bot_id из callback data

    async with await get_db_session() as session:
        # Получаем данные о боте
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()

        if bot_entry:
            # Получаем пользователей, связанных с ботом
            user_result = await session.execute(
                select(User).filter(User.bot_token == bot_entry.bot_token)
            )
            users = user_result.scalars().all()

            # Считаем статистику
            total_users = len(users)  # Всего пользователей
            blocked_users = bot_entry.users_blocked
            sent_messages = bot_entry.total_messages_count  # Сообщений всего
            incoming_messages = bot_entry.sent_messages_count  # Входящих сообщений
            replied_messages = bot_entry.replied_messages_count  # Ответов

            # Подсчёт пользователей по временным периодам
            today = datetime.utcnow().date()
            start_of_month = today.replace(day=1)
            start_of_year = today.replace(month=1, day=1)

            users_today = await session.execute(
                select(func.count(User.id)).filter(
                    User.bot_token == bot_entry.bot_token,
                    func.date(User.created_at) == today,
                )
            )
            users_today_count = users_today.scalar() or 0

            users_month = await session.execute(
                select(func.count(User.id)).filter(
                    User.bot_token == bot_entry.bot_token,
                    func.date(User.created_at) >= start_of_month,
                )
            )
            users_month_count = users_month.scalar() or 0

            users_year = await session.execute(
                select(func.count(User.id)).filter(
                    User.bot_token == bot_entry.bot_token,
                    func.date(User.created_at) >= start_of_year,
                )
            )
            users_year_count = users_year.scalar() or 0

            # Формируем текст для отправки
            statistics_text = MESSAGES[lang]["bot_statistics"].format(
                bot_username=bot_entry.bot_username,
                total_users=total_users,
                blocked_users=blocked_users,
                sent_messages=sent_messages,
                incoming_messages=incoming_messages,
                replied_messages=replied_messages,
                users_today=users_today_count,
                users_month=users_month_count,
                users_year=users_year_count,
            )
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["export_users"], callback_data=f"export_users_{bot_id}"))
            keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

            # Отправляем сообщение
            await callback_query.message.edit_text(
                statistics_text, parse_mode="Markdown", reply_markup=keyboard.as_markup()
            )
        else:
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
            await callback_query.message.answer(
                MESSAGES[lang]["bot_not_found"], parse_mode="Markdown", reply_markup=keyboard.as_markup()
            )

    # Обновляем состояние
    await state.update_data(previous_state=BotSettingsStates.bot_settings_menu, bot_id=bot_id)
    await callback_query.answer()
    
@router.callback_query(F.data.startswith("export_users_"))
async def export_users_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    bot_id = int(callback_query.data.split("_")[-1])

    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()

        if not bot_entry:
            await callback_query.answer(MESSAGES[lang]["bot_not_found"], show_alert=True)
            return

        user_result = await session.execute(
            select(User).filter(User.bot_token == bot_entry.bot_token)
        )
        users = user_result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "username", "first_name", "last_name", "language_code", "created_at", "is_banned"])
    for user in users:
        writer.writerow([
            user.user_id,
            user.username or "",
            user.first_name or "",
            user.last_name or "",
            user.language_code or "",
            user.created_at.isoformat() if user.created_at else "",
            user.is_banned or False
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    input_file = BufferedInputFile(csv_bytes, filename=f"users_{bot_entry.bot_username}.csv")

    await callback_query.message.answer_document(input_file)
    await callback_query.answer()

@router.callback_query(F.data.startswith("feedback_"))
async def feedback_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "Обратная связь".
    """
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    bot_id = int(callback_query.data.split("_")[1])

    # Получаем данные о боте из базы данных
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()

    if not bot_entry:
        await callback_query.message.edit_text(MESSAGES[lang]["bot_not_found"])
        await callback_query.answer()
        return

    # Формируем URL для подключения бота к чату
    bot_username = bot_entry.bot_username
    chat_url = f"https://t.me/{bot_username}?startgroup=start"

    # Создаем клавиатуру
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["new_chat"], url=chat_url))
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["disable_chats"], callback_data=f"disable_chats_{bot_id}"))
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    # Отправляем сообщение с описанием и клавиатурой
    await callback_query.message.edit_text(
        MESSAGES[lang]["feedback_description"],
        reply_markup=keyboard.as_markup()
    )
    await state.update_data(previous_state=BotSettingsStates.bot_settings_menu, bot_id=bot_id)
    await callback_query.answer()

@router.callback_query(F.data.startswith("disable_chats_"))
async def disable_chats(callback_query: CallbackQuery):
    """
    Обработчик для отключения чата (установка sent_messages_to в NULL).
    """
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    # Извлекаем bot_id из callback_data
    bot_id = int(callback_query.data.split("_")[-1])

    # Подключение к базе данных и обновление записи
    async with await get_db_session() as session:
        # Находим бота по bot_id
        result = await session.execute(
            select(UserBot).filter(UserBot.id == bot_id)
        )
        bot_entry = result.scalars().first()

        if not bot_entry:
            await callback_query.message.answer("Бот не найден.")
            return

        # Устанавливаем sent_messages_to в NULL
        bot_entry.sent_messages_to = None
        await session.commit()
        
    # Получаем данные о боте из базы данных
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()

    if not bot_entry:
        await callback_query.message.edit_text(MESSAGES[lang]["bot_not_found"])
        await callback_query.answer()
        return

    # Формируем URL для подключения бота к чату
    bot_username = bot_entry.bot_username
    chat_url = f"https://t.me/{bot_username}?startgroup=start"

    # Создаем клавиатуру
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["new_chat"], url=chat_url))
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["disable_chats"], callback_data=f"disable_chats_{bot_id}"))
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    # Отправляем подтверждение пользователю
    await callback_query.message.answer(MESSAGES[lang]["chat_unbound"], reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("open_"))
async def bot_settings_main_menu(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    async with await get_db_session() as session:
        admin_result = await session.execute(
                select(UserBot).filter(
                    UserBot.bot_token == callback_query.bot.token
                )
            )
        bot = admin_result.scalars().first()
    
    if callback_query.data.startswith("open_menu_"):
        
        if callback_query.from_user.id != bot.user_id:
            return
        
        async with await get_db_session() as session:
            bot_result = await session.execute(
                select(UserBot).filter(UserBot.bot_token == callback_query.bot.token)
            )
            user_bot = bot_result.scalars().first()

            if not user_bot:
                await callback_query.message.edit_text(MESSAGES[lang]["bot_not_found"])
                return

        async with await get_db_session() as session:
            buttons_result = await session.execute(
                select(BotMenuButton).filter(BotMenuButton.bot_token == callback_query.bot.token)
            )
            buttons = buttons_result.scalars().all()

        keyboard = InlineKeyboardBuilder()
        # Формируем кнопки парами
        for i in range(0, len(buttons), 2):
            pair = buttons[i:i+2]  # Берем по 2 кнопки
            keyboard.row(
                *(InlineKeyboardButton(text=button.button_text, callback_data=f"button_{button.id}") for button in pair)
            )
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["add_button"], callback_data=f"add_button_{user_bot.id}"))
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

        await callback_query.message.edit_text(
            MESSAGES[lang]["main_menu_description"],
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(BotSettingsStates.main_menu)
        await state.update_data(bot_id=user_bot.id, previous_state=BotSettingsStates.bot_settings_menu)
        return
    elif callback_query.data.startswith("open_channels_"):
        lang = await get_lang(callback_query.from_user.id)
        
        async with await get_db_session() as session:
            channels_result = await session.execute(
                select(Channels).filter(
                    Channels.bot_id == bot.id
                )
            )
            channels = channels_result.scalars().all()
        
        keyboard = InlineKeyboardBuilder()
        if channels:
            for channel in channels:
                keyboard.row(InlineKeyboardButton(text=channel.channel_name, callback_data=f"channel_settings_{channel.id}"))
            keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
            
            await callback_query.message.edit_text(
                text=MESSAGES[lang]["channels_message"],
                parse_mode="Markdown",
                reply_markup=keyboard.as_markup()
                )
            
            await state.update_data(previous_state=BotSettingsStates.bot_settings_menu)
        else:
            keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
            
            await callback_query.message.edit_text(
                text=MESSAGES[lang]["channels_message"],
                parse_mode="Markdown",
                reply_markup=keyboard.as_markup()
                )
            
            await state.update_data(previous_state=BotSettingsStates.bot_settings_menu)
    elif callback_query.data.startswith("open_mailings_"):
        if callback_query.from_user.id != bot.user_id:
            return
        
        bot_token = callback_query.bot.token

        async with await get_db_session() as session:
            # Получение информации о боте
            bot_result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
            bot_entry = bot_result.scalars().first()

            if not bot_entry:
                await callback_query.message.edit_text("Ошибка: бот не найден.")
                return

            # Подсчёт пользователей бота
            users_result = await session.execute(select(User).filter(User.bot_token == bot_token))
            total_users = len(users_result.scalars().all())

            # Проверка лимита сообщений
            has_subscription = await session.execute(
                select(BotSubscription).filter(BotSubscription.bot_id == bot_entry.id)
            )
            has_subscription = has_subscription.scalars().first()
            daily_limit = 50000 if has_subscription else 100

            # Подсчёт отправленных сообщений за сегодня
            today = datetime.utcnow().date()
            sent_today_result = await session.execute(
                select(func.sum(Mailing.counted_msg)).filter(
                    Mailing.bot_id == bot_entry.id,
                    Mailing.scheduled_time >= today
                )
            )
            sent_today = sent_today_result.scalar() or 0
            remaining_limit = daily_limit - sent_today

            # Подсчёт запланированных рассылок
            scheduled_today_result = await session.execute(
                select(func.count(Mailing.id)).filter(
                    Mailing.bot_id == bot_entry.id,
                    Mailing.scheduled_time >= today,
                    Mailing.is_sent == False
                )
            )
            scheduled_today = scheduled_today_result.scalar() or 0

            total_scheduled_result = await session.execute(
                select(func.count(Mailing.id)).filter(
                    Mailing.bot_id == bot_entry.id,
                    Mailing.is_sent == False
                )
            )
            total_scheduled = total_scheduled_result.scalar() or 0

            # Подсчёт завершённых рассылок
            completed_today_result = await session.execute(
                select(func.count(Mailing.id)).filter(
                    Mailing.bot_id == bot_entry.id,
                    Mailing.is_sent == True,
                    Mailing.scheduled_time >= today
                )
            )
            completed_today = completed_today_result.scalar() or 0

            total_completed_result = await session.execute(
                select(func.count(Mailing.id)).filter(
                    Mailing.bot_id == bot_entry.id,
                    Mailing.is_sent == True
                )
            )
            total_completed = total_completed_result.scalar() or 0

            message_text = MESSAGES[lang]["mailing_statistics"].format(
                scheduled_today=scheduled_today,
                total_scheduled=total_scheduled,
                completed_today=completed_today,
                total_completed=total_completed,
                total_users=total_users,
                blocked_users=bot_entry.users_blocked or 0,
                daily_limit=daily_limit,
                sent_today=sent_today,
                remaining_limit=remaining_limit
            )

            # Создание клавиатуры
            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["create_mailing"], callback_data=f"create_mailing_{bot_entry.id}")
            )
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["scheduled"], callback_data=f"scheduled_mailing_{bot_entry.id}")
            )
            keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

            # Отправка сообщения
            await callback_query.message.edit_text(
                message_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            await state.update_data(bot_id=bot_entry.id, previous_state=BotSettingsStates.bot_settings_menu)
            return
        
    elif callback_query.data.startswith("open_greetings_"):
        # Получаем текущее приветственное сообщение из базы данных
        async with await get_db_session() as session:
            result = await session.execute(
                select(UserBot).filter(UserBot.bot_token == callback_query.bot.token)
            )
            bot_entry = result.scalars().first()

        # Установка значения по умолчанию
        greeting_message = bot_entry.greeting_message or MESSAGES[lang]["greeting_not_set"]
        
        sent_message_ids = []
        if bot_entry.greeting_file:
            media_entries = bot_entry.greeting_file.split(",")
            # Отправка одного медиафайла
            media_type, file_id = media_entries[0].split(":")
            if media_type == "photo":
                sent_message = await callback_query.message.answer_photo(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "video":
                sent_message = await callback_query.message.answer_video(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "document":
                sent_message = await callback_query.message.answer_document(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "audio":
                sent_message = await callback_query.message.answer_audio(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "video_note":
                sent_message = await callback_query.message.answer_video_note(file_id, caption=greeting_message, parse_mode="Markdown")
            else:
            # Отправляем только текстовое сообщение
                sent_message = await callback_query.message.answer(greeting_message, parse_mode="Markdown")
        else:
            sent_message = await callback_query.message.answer(greeting_message, parse_mode="Markdown")
        if sent_message:
            sent_message_ids.append(sent_message.message_id)

        # Клавиатура
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

        await callback_query.message.answer(
            text = MESSAGES[lang]["current_greeting"],
            parse_mode="Markdown",
            reply_markup=keyboard.as_markup()
        )

        await callback_query.message.delete()
        
        # Устанавливаем состояние для ожидания нового приветствия
        await state.set_state(BotSettingsStates.editing_greeting)
        await state.update_data(bot_id=bot_entry.id, previous_state=BotSettingsStates.bot_settings_menu, sent_message_ids = sent_message_ids)
        return
        
@router.message(BotSettingsStates.editing_greeting)
async def set_new_greeting(message: Message, state: FSMContext):
    data = await state.get_data()
    sent_message_ids = data.get("sent_message_ids")
    
    if sent_message_ids:
        for sent_message_id in sent_message_ids:
            try:
                await message.bot.delete_message(message.chat.id, sent_message_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщения {sent_message_id}: {e}")
                
    user_id = message.from_user.id
    lang = await get_lang(user_id)

    if message.media_group_id:
        return
    else:
        if message.photo:
            file_id = message.photo[-1].file_id
            media_type = "photo"
        elif message.video:
            file_id = message.video.file_id
            media_type = "video"
        elif message.document:
            file_id = message.document.file_id
            media_type = "document"
        elif message.audio:
            file_id = message.audio.file_id
            media_type = "audio"
        elif message.text:
            file_id = None
            media_type = "text"
        elif message.video_note:
            file_id = message.video_note.file_id
            media_type = "video_note"
        else:
            await message.answer("Этот тип сообщений не поддерживается.")
            return

        # Сохраняем информацию в состояние
        async with await get_db_session() as session:
            result = await session.execute(
                select(UserBot).filter(UserBot.bot_token == message.bot.token)
            )
            bot_entry = result.scalars().first()
            
            bot_entry.greeting_file = f"{media_type}:{file_id}"
            bot_entry.greeting_message = message.md_text.replace("\\", "") or ""
            
            await session.commit()
        
        bot_token = message.bot.token
        
        # Получение информации о боте из базы данных
        async with await get_db_session() as session:
            result_bot = await session.execute(
                select(UserBot).filter(UserBot.bot_token == bot_token)
            )
            bot = result_bot.scalars().first()  # Извлекаем бота
            
            if not bot:
                return
        
        keyboard = InlineKeyboardBuilder()
        
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["add_button_greetings"], callback_data=f"add_inline_button_{bot.id}"),
            InlineKeyboardButton(text=MESSAGES[lang]["back_to_start"], callback_data=f"back"),
        )
        
        await message.answer(MESSAGES[lang]["greeting_updated"], reply_markup=keyboard.as_markup())
        await state.update_data(bot_id=bot.id, previous_state=BotSettingsStates.bot_settings_menu, from_greeting=True)