from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete, func
from sqlalchemy.future import select
from db import UserBot, get_db_session, increment_sent_messages_count, increment_replied_messages_count, BotMenuButton, User, Mailing, BotSubscription, get_lang
from dict import MESSAGES
from datetime import datetime, timedelta
from pytz import timezone
from config import media_group_tasks, media_groups
import asyncio
from handlers.menu_handlers.adding_button import BotSettingsStates

class MailingStates(StatesGroup):
    main_menu = State()
    awaiting_message = State()
    confirm_message = State()
    mailing_time = State()
    confirm_mailing = State()
    editing_mailings = State()
    awaiting_url_button = State()

router = Router(name=__name__)

@router.callback_query(F.data.startswith("create_mailing_"))
async def create_mailing_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик для начала создания рассылки.
    """
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)  # Получаем язык пользователя
    bot_id = int(callback_query.data.split("_")[-1])

    await state.update_data(bot_id=bot_id)

    # Создаем клавиатуру
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    # Отправляем сообщение пользователю
    await callback_query.message.edit_text(
        MESSAGES[lang]["send_mailing_message"],
        reply_markup=keyboard.as_markup()
    )

    # Устанавливаем состояние
    await state.set_state(MailingStates.awaiting_message)
    await state.update_data(previous_state=MailingStates.main_menu)
    await callback_query.answer()

@router.message(MailingStates.awaiting_message)
async def handle_mailing_message(message: Message, state: FSMContext):
    """
    Обработка сообщения для рассылки.
    """
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    
    if message.media_group_id:
        # Обработка медиагруппы
        media_group_id = message.media_group_id

        # Если медиагруппа ещё не создана, создаём её
        if not media_groups[media_group_id]['messages']:
            media_groups[media_group_id]['caption'] = message.md_text

        # Добавляем сообщение в медиагруппу
        media_groups[media_group_id]['messages'].append(message)

        # Отменяем предыдущую задачу обработки этой медиагруппы, если она есть
        if media_group_id in media_group_tasks:
            media_group_tasks[media_group_id].cancel()

        # Создаем новую задачу для обработки медиагруппы
        media_group_tasks[media_group_id] = asyncio.create_task(
            process_media_group_for_mailing(media_group_id, state, message, lang)
        )
    else:
        # Обработка одиночного сообщения
        await process_single_message_for_mailing(message, state, lang)

async def process_media_group_for_mailing(media_group_id, state: FSMContext, message: Message, lang):
    """
    Завершение обработки медиагруппы и сохранение в состоянии.
    """
    await asyncio.sleep(1.5)  # Ждём завершения загрузки медиагруппы

    media_group_data = media_groups.pop(media_group_id, None)
    if not media_group_data:
        return  # Нет сообщений для обработки

    if media_group_id in media_group_tasks:
        media_group_tasks.pop(media_group_id)

    messages = media_group_data['messages']
    caption_text = media_group_data['caption'] or ""

    # Сортируем сообщения по message_id для правильного порядка
    messages.sort(key=lambda msg: msg.message_id)

    # Собираем медиафайлы
    media_entries = []
    for msg in messages:
        if msg.photo:
            media_entries.append(f"photo:{msg.photo[-1].file_id}")
        elif msg.video:
            media_entries.append(f"video:{msg.video.file_id}")
        elif msg.document:
            media_entries.append(f"document:{msg.document.file_id}")
        elif msg.audio:
            media_entries.append(f"audio:{msg.audio.file_id}")

    # Сохраняем информацию в состояние
    await state.update_data(
        mailing_content={
            "caption": caption_text,
            "media_group": media_entries
        }
    )

    # Формируем клавиатуру
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["send"], callback_data="send_mailing"),
        InlineKeyboardButton(text=MESSAGES[lang]["schedule"], callback_data="schedule_mailing"),
    )
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    
    await state.set_state(MailingStates.awaiting_url_button)
    await state.update_data(previous_state=MailingStates.awaiting_message)

    
    # Переход к подтверждению
    await message.answer(
        text=MESSAGES[lang]["confirm_mailing"],
        reply_markup=keyboard.as_markup(),
    )

async def process_single_message_for_mailing(message: Message, state: FSMContext, lang):
    """
    Обработка одиночного сообщения и сохранение в состоянии.
    """
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
    else:
        await message.answer("Этот тип сообщений не поддерживается.")
        return

    # Сохраняем информацию в состояние
    await state.update_data(
        mailing_content={
            "text": message.md_text,
            "file_id": file_id,
            "file_type": media_type
        }
    )

    # Формируем клавиатуру
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["skip"], callback_data="skip_url"),
    )
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    await state.set_state(MailingStates.awaiting_url_button)
    await state.update_data(previous_state=MailingStates.awaiting_message)

    await message.answer(
        text=MESSAGES[lang]["enter_url_button_data"],
        reply_markup=keyboard.as_markup(),
    )
    
@router.message(MailingStates.awaiting_url_button)
async def save_url_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    
    parts = message.text.split("|")
    if len(parts) != 2:
        await message.answer(text = MESSAGES[lang]["invalid_url_format"])
        return

    button_text, button_url = parts[0].strip(), parts[1].strip()

    # Сохраняем кнопку в состоянии
    await state.update_data(
        url_button={
            "text": button_text,
            "url": button_url
        }
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["send"], callback_data="send_mailing"),
        InlineKeyboardButton(text=MESSAGES[lang]["schedule"], callback_data="schedule_mailing"),
    )
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    
    # Переход к подтверждению
    await message.answer(
        text=MESSAGES[lang]["confirm_mailing"],
        reply_markup=keyboard.as_markup(),
    )

@router.callback_query(F.data == "skip_url", MailingStates.awaiting_url_button)
async def skip_url(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["send"], callback_data="send_mailing"),
        InlineKeyboardButton(text=MESSAGES[lang]["schedule"], callback_data="schedule_mailing"),
    )
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    
    await callback_query.message.edit_text(
        text=MESSAGES[lang]["confirm_mailing"],
        reply_markup=keyboard.as_markup(),
    )
    
@router.callback_query(F.data == "send_mailing")
async def send_mailing_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "Отправить" для рассылки.
    """
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    data = await state.get_data()
    bot_id = data.get("bot_id")
    mailing_content = data.get("mailing_content")
    url_button = data.get("url_button", None)

    if not mailing_content:
        await callback_query.message.edit_text("Ошибка: контент для рассылки не найден.")
        await state.clear()
        await callback_query.answer()
        return

    # Получение информации о боте и пользователях
    async with await get_db_session() as session:
        # Получаем запись бота
        bot_result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = bot_result.scalars().first()

        if not bot_entry:
            await callback_query.message.edit_text("Ошибка: бот не найден.")
            await state.clear()
            await callback_query.answer()
            return

        # Получение пользователей бота
        users_result = await session.execute(select(User).filter(User.bot_token == bot_entry.bot_token))
        bot_users = users_result.scalars().all()

        subscription_result = await session.execute(select(BotSubscription).filter(BotSubscription.bot_id == bot_entry.id))
        have_subscription = subscription_result.scalars().first()
        
        if have_subscription:
            user_limit = 50000
        else:
            user_limit = 100  # Здесь замените на реальный лимит из подписки пользователя

        # Подсчёт отправленных сегодня сообщений
        today = datetime.utcnow().date()
        sent_today_result = await session.execute(
            select(func.sum(Mailing.counted_msg)).filter(
                Mailing.bot_id == bot_id,
                Mailing.scheduled_time >= today,
                Mailing.is_sent == True
            )
        )
        scalar_result = sent_today_result.scalar()
        sent_today_count = int(scalar_result) if scalar_result else 0
        remaining_limit = user_limit - sent_today_count

    # Проверка на оставшийся лимит
    if remaining_limit <= 0:
        await callback_query.message.edit_text(
            MESSAGES[lang]["daily_limit_reached"].format(
                user_limit=user_limit,
                sent_today_count=sent_today_count,
            )
        )
        await state.update_data(bot_id=bot_id, previous_state = BotSettingsStates.bot_settings_menu)
        await callback_query.answer()
        return

    # Сохранение рассылки в базу данных
    async with await get_db_session() as session:
        # Подготовка данных для сохранения
        reply_message = mailing_content.get("text") or mailing_content.get("caption")
        if "media_group" in mailing_content:
            file_id = ",".join(mailing_content["media_group"])
        elif mailing_content.get("file_id"):
            file_id = f"{mailing_content['file_type']}:{mailing_content['file_id']}"
        else:
            file_id = f"text:None"

        new_mailing = Mailing(
            bot_id=bot_id,
            reply_message=reply_message,
            file_id=file_id,
            button_text = url_button["text"] if url_button else None,
            button_url = url_button["url"] if url_button else None,
            scheduled_time=datetime.utcnow(),
            is_sent=False
        )
        session.add(new_mailing)
        await session.commit()

        mailing_id = new_mailing.id

    # Отправка сообщений
    blocked_users_count = 0
    success_count = 0
    if url_button:
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=url_button["text"], url=url_button["url"]))
        keyboard = keyboard.as_markup()
    else:
        keyboard = None
    
    for user in bot_users[:remaining_limit]:  # Ограничиваем рассылку оставшимся лимитом
        try:
            if "media_group" in mailing_content:
                # Отправка медиагруппы
                media_group = []
                for i, media in enumerate(mailing_content["media_group"]):
                    media_type, file_id = media.split(":")
                    caption = reply_message if i == 0 else None
                    if media_type == "photo":
                        media_group.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode="Markdown"))
                    elif media_type == "video":
                        media_group.append(InputMediaVideo(media=file_id, caption=caption, parse_mode="Markdown"))
                    elif media_type == "document":
                        media_group.append(InputMediaDocument(media=file_id, caption=caption, parse_mode="Markdown"))
                    elif media_type == "audio":
                        media_group.append(InputMediaAudio(media=file_id, caption=caption, parse_mode="Markdown"))
                await callback_query.message.bot.send_media_group(chat_id=user.user_id, media=media_group)
            elif mailing_content.get("file_id"):
                # Отправка одиночного медиа
                file_type = mailing_content["file_type"]
                file_id = mailing_content["file_id"]
                if file_type == "photo":
                    await callback_query.message.bot.send_photo(
                        chat_id=user.user_id,
                        photo=file_id,
                        caption=reply_message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                elif file_type == "video":
                    await callback_query.message.bot.send_video(
                        chat_id=user.user_id,
                        video=file_id,
                        caption=reply_message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                elif file_type == "document":
                    await callback_query.message.bot.send_document(
                        chat_id=user.user_id,
                        document=file_id,
                        caption=reply_message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                elif file_type == "audio":
                    await callback_query.message.bot.send_audio(
                        chat_id=user.user_id,
                        audio=file_id,
                        caption=reply_message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                elif file_type == "text":
                    await callback_query.message.bot.send_message(
                        chat_id=user.user_id,
                        text=reply_message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
            else:
                # Отправка текста
                await callback_query.message.bot.send_message(
                    chat_id=user.user_id,
                    text=reply_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard.as_markup()
                )
            success_count += 1
        except Exception as e:
            if "bot was blocked by the user" in str(e):
                blocked_users_count += 1

        await asyncio.sleep(0.034)

    # Обновление рассылки как завершенной и количества заблокировавших
    async with await get_db_session() as session:
        # Обновляем рассылку
        result = await session.execute(select(Mailing).filter(Mailing.id == mailing_id))
        mailing = result.scalars().first()
        if mailing:
            mailing.is_sent = True
            mailing.counted_msg = success_count
            await session.commit()

        # Обновляем количество заблокировавших
        bot_result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = bot_result.scalars().first()
        if bot_entry:
            bot_entry.users_blocked = (bot_entry.users_blocked or 0) + blocked_users_count
            await session.commit()

    await callback_query.message.edit_text(
    MESSAGES[lang]["mailing_finished"].format(
        success_count=success_count,
        blocked_users_count=blocked_users_count,
    )
        )
    await state.clear()
    await return_to_main_menu(callback_query.message, state, lang)
    await callback_query.answer()

@router.callback_query(F.data == "schedule_mailing")
async def schedule_mailing_handler(callback_query: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback_query.from_user.id)

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    
    await callback_query.message.edit_text(
        MESSAGES[lang]["schedule_mailing_prompt"],
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.update_data(previous_state=MailingStates.confirm_mailing)
    await state.set_state(MailingStates.mailing_time)
   
@router.message(MailingStates.mailing_time)
async def schedule_mailing_handler(message: Message, state: FSMContext):
    """
    Обработка кнопки "Запланировать" для рассылки с проверкой лимита сообщений.
    """
    lang = await get_lang(message.from_user.id)

    data = await state.get_data()
    bot_id = data.get("bot_id")
    mailing_content = data.get("mailing_content")
    url_button = data.get("url_button", None)

    if not mailing_content:
        await message.answer(MESSAGES[lang]["mailing_content_error"])
        await state.clear()
        return

    # Парсинг времени из сообщения
    try:
        user_input = message.text.strip()
        scheduled_time = None
        moscow_tz = timezone("Europe/Moscow")

        # Проверяем формат времени
        if ":" in user_input or " " in user_input:
            if ":" in user_input and len(user_input.split(" ")) == 1:  # Формат 03:28
                current_date = datetime.now(moscow_tz).date()
                scheduled_time = datetime.strptime(user_input, "%H:%M").replace(
                    year=current_date.year, month=current_date.month, day=current_date.day
                )
                # Если время уже прошло, переносим на следующий день
                if moscow_tz.localize(scheduled_time) <= datetime.now(moscow_tz):
                    scheduled_time += timedelta(days=1)

            elif len(user_input.split(" ")) == 2 and ":" in user_input:  # Формат 03:28 12.01
                time_part, date_part = user_input.split(" ", 1)
                if "." in date_part:  # Формат 03:28 12.01
                    scheduled_time = datetime.strptime(f"{time_part} {date_part}", "%H:%M %d.%m")
                    scheduled_time = scheduled_time.replace(year=datetime.now(moscow_tz).year)
                else:  # Формат 03:28 12 01
                    scheduled_time = datetime.strptime(f"{time_part} {date_part}", "%H:%M %d %m")

            elif len(user_input.split(" ")) == 2 and " " in user_input:  # Формат 03 28
                scheduled_time = datetime.strptime(user_input, "%H %M").replace(
                    year=datetime.now(moscow_tz).year, month=datetime.now(moscow_tz).month, day=datetime.now(moscow_tz).day
                )
                # Если время уже прошло, переносим на следующий день
                if moscow_tz.localize(scheduled_time) <= datetime.now(moscow_tz):
                    scheduled_time += timedelta(days=1)

            elif "-" in user_input:  # Формат 2025-01-12 03:28
                date_part, time_part = user_input.split(" ")
                scheduled_time = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M")
        else:
            raise ValueError("Неверный формат времени.")

        # Приводим время к московской временной зоне
        if scheduled_time is not None:
            scheduled_time = moscow_tz.localize(scheduled_time)

    except ValueError:
        await message.answer(MESSAGES[lang]["schedule_mailing_error"], parse_mode="Markdown")
        return

    # Проверяем, чтобы время было в будущем
    if scheduled_time <= datetime.now(moscow_tz):  # Оба объекта теперь "offset-aware"
        await message.answer(MESSAGES[lang]["schedule_time_past_error"])
        return

    # Удаляем временную зону перед сохранением в базу данных
    scheduled_time_naive = scheduled_time.replace(tzinfo=None)

    # Сохранение рассылки в базу данных
    async with await get_db_session() as session:
        # Получение информации о боте
        bot = await session.get(UserBot, bot_id)
        if not bot:
            await message.answer(MESSAGES[lang]["bot_not_found"])
            await state.clear()
            return

        # Определение лимита сообщений
        has_subscription = await session.execute(
            select(BotSubscription).filter(BotSubscription.bot_id == bot_id)
        )
        has_subscription = has_subscription.scalars().first()
        daily_limit = 50000 if has_subscription else 100

        # Подсчет отправленных сообщений за день, на который запланирована рассылка
        target_date = scheduled_time.date()
        sent_on_target_date = await session.execute(
            select(func.sum(Mailing.counted_msg)).filter(
                Mailing.bot_id == bot_id,
                func.date(Mailing.scheduled_time) == target_date,
                Mailing.is_sent == True
            )
        )
        sent_on_target_date = sent_on_target_date.scalar() or 0

        total_users_count = await session.execute(
            select(func.count(User.id)).filter(
                User.bot_token == bot.bot_token,
            )
        )
        total_users_count = total_users_count.scalar() or 0
        
        # Подсчет доступных пользователей
        available_users = total_users_count - bot.users_blocked

        # Проверяем, превышает ли лимит
        if sent_on_target_date + available_users > daily_limit:
            await message.answer(
                MESSAGES[lang]["schedule_limit_exceeded"].format(
                    daily_limit=daily_limit,
                    target_date=target_date,
                    sent_on_target_date=sent_on_target_date,
                    available_users=available_users
                )
            )
            return

        # Подготовка данных для сохранения
        reply_message = mailing_content.get("text") or mailing_content.get("caption")
        if "media_group" in mailing_content:
            file_id = ",".join(mailing_content["media_group"])
        elif mailing_content.get("file_id"):
            file_id = f"{mailing_content['file_type']}:{mailing_content['file_id']}"
        else:
            file_id = "text:None"

        new_mailing = Mailing(
            bot_id=bot_id,
            reply_message=reply_message,
            file_id=file_id,
            scheduled_time=scheduled_time_naive,
            counted_msg=available_users,
            button_text=url_button["text"] if url_button else None,
            button_url=url_button["url"] if url_button else None,
            is_sent=False
        )
        session.add(new_mailing)
        await session.commit()

    # Уведомление о запланированной рассылке
    await message.answer(
        MESSAGES[lang]["schedule_success"].format(
            scheduled_time=scheduled_time.strftime("%Y-%m-%d %H:%M")
        )
    )
    
    await state.clear()
    await return_to_main_menu(message, state, lang)

@router.callback_query(F.data.startswith("scheduled_mailing_"))
async def scheduled_mailing_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки "Запланировано".
    """
    lang = await get_lang(callback_query.from_user.id)  # Получаем язык пользователя
    bot_id = int(callback_query.data.split("_")[-1])

    async with await get_db_session() as session:
        # Получаем все запланированные рассылки для данного бота
        scheduled_result = await session.execute(
            select(Mailing).filter(
                Mailing.bot_id == bot_id,
                Mailing.is_sent == False
            ).order_by(Mailing.scheduled_time)
        )
        scheduled_mailings = scheduled_result.scalars().all()

    if not scheduled_mailings:
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
        await callback_query.message.edit_text(
            MESSAGES[lang]["no_scheduled_mailings"],
            reply_markup=keyboard.as_markup()
        )
        await state.update_data(previous_state=MailingStates.main_menu, bot_id=bot_id)
        await callback_query.answer()
        return

    # Создание клавиатуры
    keyboard = InlineKeyboardBuilder()

    # Словарь эмодзи для типов сообщений
    emoji_dict = {
        "photo": "🖼️",
        "video": "🎥",
        "audio": "🎵",
        "document": "📄",
        "text": "📝",
        None: "❔"
    }
    type_dict = {
        "photo": {"ru": "Фото", "en": "Photo"},
        "video": {"ru": "Видео", "en": "Video"},
        "audio": {"ru": "Аудио", "en": "Audio"},
        "document": {"ru": "Документ", "en": "Document"},
        "text": {"ru": "Текст", "en": "Text"},
        None: {"ru": "Неизвестно", "en": "Unknown"}
    }

    for mailing in scheduled_mailings:
        # Обработка file_id
        file_ids = mailing.file_id.split(",") if mailing.file_id else []
        media_types = {file_id.split(":")[0] for file_id in file_ids}  # Уникальные типы файлов

        if len(media_types) == 1:
            # Один тип медиа
            media_type = list(media_types)[0]
            emoji = emoji_dict.get(media_type, "❔")
            type_name = type_dict.get(media_type, {}).get(lang, "Unknown")
        elif len(media_types) > 1:
            # Разные типы медиа
            emoji = "📦"
            type_name = {"ru": "Разные медиа", "en": "Mixed Media"}[lang]
        else:
            # Текстовое сообщение без файлов
            emoji = emoji_dict["text"]
            type_name = type_dict["text"][lang]

        # Формируем текст кнопки
        button_text = f"{emoji} {type_name}, {mailing.scheduled_time.strftime('%Y-%m-%d %H:%M')}"
        keyboard.row(InlineKeyboardButton(text=button_text, callback_data=f"edit_mailing_{mailing.id}"))

    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    # Отправка сообщения с клавиатурой
    await callback_query.message.edit_text(
        MESSAGES[lang]["scheduled_mailings"],
        reply_markup=keyboard.as_markup()
    )
    await state.update_data(previous_state=MailingStates.main_menu, bot_id=bot_id)
    await callback_query.answer()

@router.callback_query(F.data.startswith("edit_mailing_"))
async def edit_mailing_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка нажатия на кнопку запланированной рассылки.
    """
    lang = await get_lang(callback_query.from_user.id)
    mailing_id = int(callback_query.data.split("_")[-1])

    async with await get_db_session() as session:
        # Получаем информацию о рассылке
        result = await session.execute(
            select(Mailing).filter(Mailing.id == mailing_id)
        )
        mailing = result.scalars().first()

    if not mailing:
        await callback_query.message.edit_text(MESSAGES[lang]["edit_mailing_error"])
        await callback_query.answer()
        return

    if mailing.button_text and mailing.button_url:
        keyboard_for_message = InlineKeyboardBuilder()
        keyboard_for_message.row(InlineKeyboardButton(text=mailing.button_text, url=mailing.button_url))
        keyboard_for_message = keyboard_for_message.as_markup()
    else:
        keyboard_for_message = None
    # Отправка сообщения рассылки
    sent_message_ids = []
    if mailing.file_id:
        file_ids = mailing.file_id.split(",")
        if len(file_ids) > 1:
            # Медиагруппа
            media_group = []
            for i, file_entry in enumerate(file_ids):
                media_type, file_id = file_entry.split(":")
                if media_type == "photo":
                    media_group.append(
                        InputMediaPhoto(media=file_id, caption=mailing.reply_message if i == 0 else None, parse_mode="Markdown")
                    )
                elif media_type == "video":
                    media_group.append(
                        InputMediaVideo(media=file_id, caption=mailing.reply_message if i == 0 else None, parse_mode="Markdown")
                    )
                elif media_type == "document":
                    media_group.append(
                        InputMediaDocument(media=file_id, caption=mailing.reply_message if i == 0 else None, parse_mode="Markdown")
                    )
                elif media_type == "audio":
                    media_group.append(
                        InputMediaAudio(media=file_id, caption=mailing.reply_message if i == 0 else None, parse_mode="Markdown")
                    )
            sent_messages = await callback_query.message.answer_media_group(media_group)
            sent_message_ids = [msg.message_id for msg in sent_messages]
        else:
            # Одиночное сообщение
            media_type, file_id = file_ids[0].split(":")
            if media_type == "photo":
                sent_message = await callback_query.message.answer_photo(file_id, caption=mailing.reply_message, parse_mode="Markdown", reply_markup=keyboard_for_message)
            elif media_type == "video":
                sent_message = await callback_query.message.answer_video(file_id, caption=mailing.reply_message, parse_mode="Markdown", reply_markup=keyboard_for_message)
            elif media_type == "document":
                sent_message = await callback_query.message.answer_document(file_id, caption=mailing.reply_message, parse_mode="Markdown", reply_markup=keyboard_for_message)
            elif media_type == "audio":
                sent_message = await callback_query.message.answer_audio(file_id, caption=mailing.reply_message, parse_mode="Markdown", reply_markup=keyboard_for_message)
            elif media_type == "text":
                sent_message = await callback_query.message.answer(mailing.reply_message, parse_mode="Markdown", reply_markup=keyboard_for_message)
            sent_message_ids.append(sent_message.message_id)

    # Сохраняем ID отправленных сообщений в состояние
    await state.update_data(sent_message_ids=sent_message_ids, mailing_id=mailing.id)

    # Формирование нового меню
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["cancel_mailing"], callback_data=f"delete_mailing_{mailing.id}")
    )
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
    )

    type_dict = {
        "photo": "Фото" if lang == "ru" else "Photo",
        "video": "Видео" if lang == "ru" else "Video",
        "audio": "Аудио" if lang == "ru" else "Audio",
        "document": "Документ" if lang == "ru" else "Document",
        "text": "Текст" if lang == "ru" else "Text",
        None: "Неизвестно" if lang == "ru" else "Unknown"
    }

    # Формируем текст меню
    file_type = mailing.file_id.split(":")[0] if mailing.file_id else "text"
    menu_text = MESSAGES[lang]["mailing_info"].format(
        mailing_id=mailing.id,
        mailing_type=type_dict[file_type],
        scheduled_time=mailing.scheduled_time.strftime('%Y-%m-%d %H:%M')
    )

    await callback_query.message.answer(menu_text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await callback_query.message.delete()
    await state.update_data(previous_state=MailingStates.editing_mailings)
    await callback_query.answer()

@router.callback_query(F.data.startswith("delete_mailing_"))
async def delete_mailing_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки удаления рассылки.
    """
    user_id = callback_query.from_user.id
    lang = get_lang(user_id)
    
    mailing_id = int(callback_query.data.split("_")[-1])

    async with await get_db_session() as session:
        # Удаление рассылки из базы данных
        result = await session.execute(
            select(Mailing).filter(Mailing.id == mailing_id)
        )
        mailing = result.scalars().first()

        if not mailing:
            await callback_query.message.answer(MESSAGES[lang]["mailing_not_found"])
            await state.clear()
            await return_to_main_menu(callback_query.message, state, lang)
            await callback_query.answer()
            return

        await session.delete(mailing)
        await session.commit()

    await callback_query.message.answer(MESSAGES[lang]["mailing_deleted"])
    await state.clear()
    await return_to_main_menu(callback_query.message, state, lang)
    await callback_query.answer()
    
async def return_to_main_menu(message: Message, state: FSMContext, lang):
    bot_token = message.bot.token

    async with await get_db_session() as session:
        # Получение информации о боте
        bot_result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
        bot_entry = bot_result.scalars().first()

        if not bot_entry:
            await message.edit_text(MESSAGES[lang]["bot_not_found"])
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

    # Формирование текста сообщения
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
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data=f"back")
    )

    # Отправка сообщения
    await message.answer(
        message_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await state.update_data(previous_state=BotSettingsStates.bot_settings_menu, bot_id = bot_entry.id)

# Задаем временную зону для МСК
moscow_tz = timezone("Europe/Moscow")

async def process_scheduled_mailings():
    """
    Функция для проверки запланированных рассылок и их отправки (параллельно).
    """
    while True:
        async with await get_db_session() as session:
            # Текущее время в МСК
            now_msk = datetime.now(moscow_tz)
            naive_now_msk = now_msk.replace(tzinfo=None)

            # Получаем все рассылки, которые запланированы на отправку
            scheduled_mailings_result = await session.execute(
                select(Mailing).filter(
                    Mailing.scheduled_time <= naive_now_msk,
                    Mailing.is_sent == False
                )
            )
            scheduled_mailings = scheduled_mailings_result.scalars().all() or []

        # Запускаем каждую рассылку как отдельную задачу
        tasks = []
        for mailing in scheduled_mailings:
                tasks.append(asyncio.create_task(send_mailing_task(mailing.id)))

        # Проверяем, что tasks — это список перед asyncio.gather()
        if tasks:
            await asyncio.gather(*tasks)

        # Пауза перед следующей проверкой
        await asyncio.sleep(60)

async def send_mailing_task(mailing_id):
    """
    Задача для отправки рассылки с учетом лимита сообщений.
    """
    async with await get_db_session() as session:
        mailing_result = await session.execute(select(Mailing).filter(Mailing.id == mailing_id))
        mailing = mailing_result.scalars().first()
        # Получаем информацию о боте
        bot_result = await session.execute(select(UserBot).filter(UserBot.id == mailing.bot_id))
        bot_entry = bot_result.scalars().first()

        if not bot_entry:
            print(f"⚠️ Бот с ID {mailing.bot_id} не найден. Пропуск рассылки ID {mailing.id}.")
            return

        bot = Bot(token=bot_entry.bot_token)

        # Проверка лимита сообщений
        has_subscription = await session.execute(
            select(BotSubscription).filter(BotSubscription.bot_id == bot_entry.id)
        )
        has_subscription = has_subscription.scalars().first()
        daily_limit = 50000 if has_subscription else 100

        # Подсчет уже отправленных сообщений на дату рассылки
        target_date = mailing.scheduled_time.date()
        sent_on_target_date = await session.execute(
            select(func.sum(Mailing.counted_msg)).filter(
                Mailing.bot_id == bot_entry.id,
                func.date(Mailing.scheduled_time) == target_date,
                Mailing.is_sent == True
            )
        )
        scalar_result = sent_on_target_date.scalar()
        sent_on_target_date = int(scalar_result) if scalar_result else 0

        # Доступные сообщения для отправки
        remaining_limit = daily_limit - sent_on_target_date

        # Проверяем, если лимит уже исчерпан
        if remaining_limit <= 0:
            print(f"⚠️ Лимит сообщений для бота {bot_entry.bot_username} на {target_date} исчерпан.")
            mailing.is_sent = True
            await session.commit()
            return

        # Получаем пользователей для рассылки
        users_result = await session.execute(select(User).filter(User.bot_token == bot_entry.bot_token))
        bot_users = users_result.scalars().all()

        # Привязываем объект mailing к текущей сессии
        mailing_result = await session.execute(select(Mailing).filter(Mailing.id == mailing.id))
        mailing = mailing_result.scalars().first()

        if not mailing:
            print(f"⚠️ Рассылка с ID {mailing.id} не найдена.")
            return

        # Подготовка контента для рассылки
        blocked_users_count = 0
        success_count = 0
        reply_message = mailing.reply_message
        file_ids = mailing.file_id.split(",")  # Медиа-группа хранится как список ID через запятую

        if mailing.button_text and mailing.button_url:
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text=mailing.button_text, url=mailing.button_url))
            keyboard = keyboard.as_markup()
        else:
            keyboard = None

        for user in bot_users[:remaining_limit]:  # Ограничиваем рассылку до оставшегося лимита
            try:
                if len(file_ids) > 1:  # Медиа-группа
                    media_group = []
                    for i, media in enumerate(file_ids):
                        media_type, file_id = media.split(":")
                        caption = reply_message if i == 0 else None  # Текст добавляем только к первому элементу
                        if media_type == "photo":
                            media_group.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode="Markdown"))
                        elif media_type == "video":
                            media_group.append(InputMediaVideo(media=file_id, caption=caption, parse_mode="Markdown"))
                        elif media_type == "document":
                            media_group.append(InputMediaDocument(media=file_id, caption=caption, parse_mode="Markdown"))
                        elif media_type == "audio":
                            media_group.append(InputMediaAudio(media=file_id, caption=caption, parse_mode="Markdown"))
                    await bot.send_media_group(chat_id=user.user_id, media=media_group)
                elif file_ids[0].startswith("photo:"):
                    await bot.send_photo(chat_id=user.user_id, photo=file_ids[0].split(":", 1)[1], caption=reply_message, parse_mode="Markdown")
                elif file_ids[0].startswith("video:"):
                    await bot.send_video(chat_id=user.user_id, video=file_ids[0].split(":", 1)[1], caption=reply_message, parse_mode="Markdown")
                elif file_ids[0].startswith("document:"):
                    await bot.send_document(chat_id=user.user_id, document=file_ids[0].split(":", 1)[1], caption=reply_message, parse_mode="Markdown")
                elif file_ids[0].startswith("audio:"):
                    await bot.send_audio(chat_id=user.user_id, audio=file_ids[0].split(":", 1)[1], caption=reply_message, parse_mode="Markdown")
                else:
                    # Отправка текста
                    await bot.send_message(chat_id=user.user_id, text=reply_message, parse_mode="Markdown")

                success_count += 1
            except Exception as e:
                if "bot was blocked by the user" in str(e):
                    blocked_users_count += 1

            # Добавляем задержку, чтобы избежать ограничения по запросам
            await asyncio.sleep(0.034)

        # Обновляем статус рассылки в базе данных
        mailing.is_sent = True
        mailing.counted_msg = success_count
        await session.commit()

        # Обновляем информацию о заблокировавших пользователях
        bot_entry.users_blocked = (bot_entry.users_blocked or 0) + blocked_users_count
        await session.commit()

        await bot.session.close()
