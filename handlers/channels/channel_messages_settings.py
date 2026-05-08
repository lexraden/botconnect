from aiogram import Router, types, Bot, types , F
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ChatMemberUpdated, ChatJoinRequest, KeyboardButton, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import exists, and_, delete
from db import UserBot, User, BotSubscription, Channels, ChannelMessage, ChannelMessageButton, get_lang, get_db_session
from handlers.bot_settings import MainBotSettingsStates
from handlers.menu_handlers.adding_button import BotSettingsStates
from handlers.channels.channel_settings import ChannelSetingsStates
from config import admins, media_group_tasks, media_groups
from datetime import datetime
from dict import MESSAGES
import asyncio

router = Router(name=__name__)

async def buttons_settings_menu(message: Message, state: FSMContext, lang: str, channel_message_id: int):
    async with await get_db_session() as session:
        message_result = await session.execute(
            select(ChannelMessage).filter(ChannelMessage.id == channel_message_id)
        )
        channel_message = message_result.scalars().first()
        
        channel_result = await session.execute(
            select(Channels).filter(Channels.id == channel_message.channel_id)
        )
        channel = channel_result.scalars().first()
        
    flag_emoji = {
                "ru": "🇷🇺",
                "en": "🇺🇸",
                "all": "🌐"
            }
    
    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()
    if len(channel_message.message_file.split(",")) == 1:
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["edit_url_buttons_message"],
                callback_data=f"edit_url_buttons_message_{channel_message.id}"
            )
        )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_lang"].format(language=flag_emoji.get(channel_message.language_code)),
            callback_data=f"change_message_lang_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_content"],
            callback_data=f"change_message_content_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["delete_channel_message"],
            callback_data=f"delete_channel_message_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["back"], 
            callback_data="back"
        )
    )
    
    media_entries = channel_message.message_file.split(",")
    sent_message_ids = []
    if len(media_entries) > 1:
        media_group = []
        for entry in media_entries:
            media_type, file_id = entry.split(":")
            if media_type == "photo":
                media_group.append(InputMediaPhoto(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "video":
                media_group.append(InputMediaVideo(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "document":
                media_group.append(InputMediaDocument(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "audio":
                media_group.append(InputMediaAudio(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
        sent_messages = await message.answer_media_group(media_group)
        sent_message_ids = [msg.message_id for msg in sent_messages]
    else:
        media_type, file_id = channel_message.message_file.split(":")
        async with await get_db_session() as session:
            # Загружаем кнопки из базы данных
            result = await session.execute(
                select(ChannelMessageButton).where(ChannelMessageButton.message_id == channel_message.id).order_by(ChannelMessageButton.row)
            )
            buttons = result.scalars().all()
        
        # Создаем клавиатуру
        message_keyboard = None
        if buttons:
            message_keyboard_builder = InlineKeyboardBuilder()
            current_row = None
            row_buttons = []
            
            for button in buttons:
                if button.row != current_row:
                    if row_buttons:  # Если есть кнопки в текущей строке, добавляем их
                        message_keyboard_builder.row(*row_buttons)
                        row_buttons = []
                    current_row = button.row
                
                # Добавляем кнопку в текущую строку
                row_buttons.append(InlineKeyboardButton(text=button.button_text, url=button.button_url))
            
            # Добавляем последнюю строку кнопок
            if row_buttons:
                message_keyboard_builder.row(*row_buttons)
            
            message_keyboard = message_keyboard_builder.as_markup()
        
        if media_type == "photo":
            sent_message = await message.answer_photo(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "video":
            sent_message = await message.answer_video(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "document":
            sent_message = await message.answer_document(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "audio":
            sent_message = await message.answer_audio(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "text":
            sent_message = await message.answer(channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "video_note":
            sent_message = await message.answer_video_note(file_id, reply_markup=message_keyboard)
        if sent_message:
            sent_message_ids.append(sent_message.message_id)
    
    await message.answer(
        MESSAGES[lang]["message_settings"].format(channel_name = channel.channel_name,
                                                  language = flag_emoji[channel_message.language_code],
                                                  message_type = MESSAGES[lang]["greetings"] if channel_message.message_type == "greetings" else MESSAGES[lang]["farewell"]),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    
    await state.clear()
    
    if sent_message_ids:
        await state.update_data(sent_message_ids=sent_message_ids)
    
    await state.update_data(previous_state = ChannelSetingsStates.channel_messages, channel_message_id = channel_message.id, channel_id = channel_message.channel_id, message_type = channel_message.message_type)

@router.callback_query(F.data.startswith("edit_message_"))
async def message_settings(callback_query: CallbackQuery, state: FSMContext):
    channel_message_id = int(callback_query.data.split("_")[-1])
    
    lang = await get_lang(callback_query.from_user.id)
    
    async with await get_db_session() as session:
        message_result = await session.execute(
            select(ChannelMessage).filter(ChannelMessage.id == channel_message_id)
        )
        channel_message = message_result.scalars().first()
        
        channel_result = await session.execute(
            select(Channels).filter(Channels.id == channel_message.channel_id)
        )
        channel = channel_result.scalars().first()
        
    flag_emoji = {
                "ru": "🇷🇺",
                "en": "🇺🇸",
                "all": "🌐"
            }
    
    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["edit_url_buttons_message"],
            callback_data=f"edit_url_buttons_message_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_lang"].format(language=flag_emoji.get(channel_message.language_code)),
            callback_data=f"change_message_lang_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_content"],
            callback_data=f"change_message_content_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["delete_channel_message"],
            callback_data=f"delete_channel_message_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["back"], 
            callback_data="back"
        )
    )
    
    media_entries = channel_message.message_file.split(",")
    sent_message_ids = []
    if len(media_entries) > 1:
        media_group = []
        for entry in media_entries:
            media_type, file_id = entry.split(":")
            if media_type == "photo":
                media_group.append(InputMediaPhoto(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "video":
                media_group.append(InputMediaVideo(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "document":
                media_group.append(InputMediaDocument(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "audio":
                media_group.append(InputMediaAudio(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
        sent_messages = await callback_query.message.answer_media_group(media_group)
        sent_message_ids = [msg.message_id for msg in sent_messages]
    else:
        media_type, file_id = channel_message.message_file.split(":")
        async with await get_db_session() as session:
            # Загружаем кнопки из базы данных
            result = await session.execute(
                select(ChannelMessageButton).where(ChannelMessageButton.message_id == channel_message.id).order_by(ChannelMessageButton.row)
            )
            buttons = result.scalars().all()
        
        # Создаем клавиатуру
        message_keyboard = None
        if buttons:
            message_keyboard_builder = InlineKeyboardBuilder()
            current_row = None
            row_buttons = []
            
            for button in buttons:
                if button.row != current_row:
                    if row_buttons:  # Если есть кнопки в текущей строке, добавляем их
                        message_keyboard_builder.row(*row_buttons)
                        row_buttons = []
                    current_row = button.row
                
                # Добавляем кнопку в текущую строку
                row_buttons.append(InlineKeyboardButton(text=button.button_text, url=button.button_url))
            
            # Добавляем последнюю строку кнопок
            if row_buttons:
                message_keyboard_builder.row(*row_buttons)
            
            message_keyboard = message_keyboard_builder.as_markup()
        
        if media_type == "photo":
            sent_message = await callback_query.message.answer_photo(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "video":
            sent_message = await callback_query.message.answer_video(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "document":
            sent_message = await callback_query.message.answer_document(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "audio":
            sent_message = await callback_query.message.answer_audio(file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "text":
            sent_message = await callback_query.message.answer(channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "video_note":
            sent_message = await callback_query.message.answer_video_note(file_id, reply_markup=message_keyboard)
        if sent_message:
            sent_message_ids.append(sent_message.message_id)
    
    await callback_query.message.answer(
        MESSAGES[lang]["message_settings"].format(channel_name = channel.channel_name,
                                                  language = flag_emoji[channel_message.language_code],
                                                  message_type = MESSAGES[lang]["greetings"] if channel_message.message_type == "greetings" else MESSAGES[lang]["farewell"]),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    
    await callback_query.message.delete()
    
    await state.clear()
    
    if sent_message_ids:
        await state.update_data(sent_message_ids=sent_message_ids)
    
    await state.update_data(previous_state = ChannelSetingsStates.channel_messages, channel_message_id = channel_message.id, channel_id = channel_message.channel_id, message_type = channel_message.message_type)
    
@router.callback_query(F.data.startswith("edit_url_buttons_message_"))
async def message_buttons_settings(callback_query: CallbackQuery, state: FSMContext):
    channel_message_id = int(callback_query.data.split("_")[-1])
    
    lang = await get_lang(callback_query.from_user.id)
    
    data = await state.get_data()
    sent_message_ids = data.get("sent_message_ids")
    
    if sent_message_ids:
        for sent_message_id in sent_message_ids:
            try:
                await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message_id)
                await state.update_data(sent_message_ids = None)
            except Exception as e:
                print(f"Ошибка при удалении сообщения {sent_message_id}: {e}")
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["delete_url_buttons_message"],
            callback_data=f"delete_url_buttons_message_{channel_message_id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["back"], 
            callback_data="back"
        )
    )
    
    await state.set_state(ChannelSetingsStates.awaiting_buttons)
    
    await state.update_data(previous_state = ChannelSetingsStates.channel_message_settings, channel_message_id = channel_message_id)
    
    await callback_query.message.edit_text(text=MESSAGES[lang]["message_buttons_settings"], parse_mode="Markdown", reply_markup=keyboard.as_markup())
    
@router.message(ChannelSetingsStates.awaiting_buttons)
async def save_message_buttons(message: Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    channel_message_id = data.get("channel_message_id")
    
    lang = await get_lang(message.from_user.id)
    
    if not channel_message_id:
        await message.answer("Произошла ошибка при сохранении кнопок.")
        return
    
    # Парсим текст сообщения
    try:
        rows = message.text.strip().split("\n")
        buttons_data = []
        
        for row in rows:
            if not row.strip():
                continue  # Пропускаем пустые строки
            
            buttons_in_row = row.split("|")
            parsed_buttons = []
            
            for button in buttons_in_row:
                parts = button.strip().split("-", 1)
                if len(parts) != 2:
                    raise ValueError(f"Некорректный формат кнопки: '{button}'")
                
                button_text, button_url = parts
                button_text = button_text.strip()
                button_url = button_url.strip()
                
                if not button_text or not button_url:
                    raise ValueError(f"Некорректный формат кнопки: '{button}'")
                
                parsed_buttons.append({"text": button_text, "url": button_url})
            
            buttons_data.append(parsed_buttons)
    except ValueError as e:
        await message.answer(f"Ошибка в формате данных: {e}")
        return
    
    # Очищаем старые кнопки для этого сообщения
    async with await get_db_session() as session:
        await session.execute(
            delete(ChannelMessageButton).where(ChannelMessageButton.message_id == channel_message_id)
        )
        
        # Сохраняем новые кнопки
        for row_index, row in enumerate(buttons_data):
            for button in row:
                new_button = ChannelMessageButton(
                    message_id=channel_message_id,
                    button_text=button["text"],
                    button_url=button["url"],
                    row=row_index + 1  # Нумерация строк начинается с 1
                )
                session.add(new_button)
        
        await session.commit()
    
    await buttons_settings_menu(message, state, lang, channel_message_id)

@router.callback_query(F.data.startswith("change_message_lang_"))
async def change_message_lang(callback_query: CallbackQuery, state: FSMContext):
    channel_message_id = int(callback_query.data.split("_")[-1])
    
    data = await state.get_data()
    sent_message_ids = data.get("sent_message_ids")
    
    if sent_message_ids:
        for sent_message_id in sent_message_ids:
            try:
                await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message_id)
                await state.update_data(sent_message_ids = None)
            except Exception as e:
                print(f"Ошибка при удалении сообщения {sent_message_id}: {e}")
    
    flag_emoji = {
            "ru": "🇷🇺",
            "en": "🇺🇸",
            "all": "🌐"
        }
    
    # Получаем язык пользователя
    lang = await get_lang(callback_query.from_user.id)
    
    # Получаем сессию через middleware или функцию
    async with await get_db_session() as session:
        # Получаем сообщение из базы данных
        result = await session.execute(select(ChannelMessage).where(ChannelMessage.id == channel_message_id ))
        channel_message = result.scalars().first()
        
        if not channel_message:
            await callback_query.answer(MESSAGES[lang]["message_not_found"], show_alert=True)
            return
        
        # Текущий язык сообщения
        current_language = channel_message.language_code
        
        # Формируем клавиатуру с помощью InlineKeyboardBuilder
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["set_language_ru"], callback_data=f"set_message_lang_{channel_message_id }_ru")
        )
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["set_language_en"], callback_data=f"set_message_lang_{channel_message_id }_en")
        )
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["set_language_all"], callback_data=f"set_message_lang_{channel_message_id }_all")
        )
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
        )
        
        await state.update_data(previous_state = ChannelSetingsStates.channel_message_settings, channel_message_id = channel_message_id, channel_id = channel_message.channel_id)
        
        # Отправляем сообщение с текущим языком и кнопками
        await callback_query.message.edit_text(
            MESSAGES[lang]["current_language"].format(
                language=flag_emoji.get(current_language),
                code=current_language
            ),
            reply_markup=keyboard.as_markup()
        )

@router.callback_query(F.data.startswith("set_message_lang_"))
async def set_message_lang(callback_query: CallbackQuery, state:FSMContext):
    new_lang = callback_query.data.split("_")[-1]
    channel_message_id = int(callback_query.data.split("_")[-2])
    
    # Получаем язык пользователя
    lang = await get_lang(callback_query.from_user.id)
    
    flag_emoji = {
            "ru": "🇷🇺",
            "en": "🇺🇸",
            "all": "🌐"
        }
    
    # Получаем сессию через middleware или функцию
    async with await get_db_session() as session:
        # Получаем сообщение из базы данных
        result = await session.execute(select(ChannelMessage).where(ChannelMessage.id == channel_message_id))
        channel_message = result.scalars().first()
        
        if not channel_message:
            await callback_query.answer(MESSAGES[lang]["message_not_found"], show_alert=True)
            return
        
        # Обновляем язык в базе данных
        channel_message.language_code = new_lang
        await session.commit()
        
        # Уведомляем пользователя
        await callback_query.answer(
            MESSAGES[lang]["language_changed"].format(language=flag_emoji.get(new_lang), code=new_lang),
            show_alert=True
        )
        
        # Формируем клавиатуру с помощью InlineKeyboardBuilder
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["set_language_ru"], callback_data=f"set_message_lang_{channel_message_id}_ru")
        )
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["set_language_en"], callback_data=f"set_message_lang_{channel_message_id}_en")
        )
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["set_language_all"], callback_data=f"set_message_lang_{channel_message_id}_all")
        )
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
        )
        
        await state.update_data(previous_state = ChannelSetingsStates.channel_message_settings, channel_message_id = channel_message_id, channel_id = channel_message.channel_id)
        
        # Обновляем сообщение с новым языком
        await callback_query.message.edit_text(
            MESSAGES[lang]["current_language"].format(
                language=flag_emoji.get(new_lang),
                code=new_lang
            ),
            reply_markup=keyboard.as_markup()
        )
    
@router.callback_query(F.data.startswith("change_message_content_"))
async def change_message_content(callback_query: CallbackQuery, state: FSMContext):
    lang = await get_lang(callback_query.from_user.id)
    
    data = await state.get_data()
    sent_message_ids = data.get("sent_message_ids")
    
    if sent_message_ids:
        for sent_message_id in sent_message_ids:
            try:
                await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message_id)
                await state.update_data(sent_message_ids = None)
            except Exception as e:
                print(f"Ошибка при удалении сообщения {sent_message_id}: {e}")
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
        )
    
    await state.set_state(ChannelSetingsStates.awaiting_new_message)
    await state.update_data(previous_state = ChannelSetingsStates.channel_message_settings)

    await callback_query.message.edit_text(text=MESSAGES[lang]["change_message_content_text"], reply_markup=keyboard.as_markup())
    
@router.message(ChannelSetingsStates.awaiting_new_message)
async def message_to_send(message: Message, state: FSMContext):
    """
    Обработка сообщения: одиночное или медиагруппа.
    """
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    data = await state.get_data()
    channel_message_id = data.get("channel_message_id")

    if message.media_group_id:
        # Обработка медиагруппы
        media_group_id = message.media_group_id

        # Если медиагруппа ещё не создана, создаём её
        if not media_groups[media_group_id]['messages']:
            media_groups[media_group_id]['caption'] = message.md_text.replace("\\", "")

        # Добавляем сообщение в медиагруппу
        media_groups[media_group_id]['messages'].append(message)

        # Отменяем предыдущую задачу обработки этой медиагруппы, если она есть
        if media_group_id in media_group_tasks:
            media_group_tasks[media_group_id].cancel()

        # Создаем новую задачу для обработки медиагруппы
        media_group_tasks[media_group_id] = asyncio.create_task(
            process_media_group(media_group_id, state, channel_message_id, message, lang)
        )
    else:
        # Одиночное сообщение
        await process_single_message(message, state, channel_message_id, lang)
        
async def process_media_group(media_group_id: str, state: FSMContext, channel_message_id: int, message: Message, lang: str):
    """
    Завершение обработки медиагруппы и сохранение в базу данных.
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

    # Сохраняем в базу данных
    async with await get_db_session() as session: 
        message_result = await session.execute(
            select(ChannelMessage).filter(
                ChannelMessage.id == channel_message_id
            )
        )
        existing_message = message_result.scalars().first()
        
        channel_result = await session.execute(select(Channels).filter(Channels.id == existing_message.channel_id))
        channel = channel_result.scalars().first()
        
        if existing_message:                          
            existing_message.message_text = caption_text
            existing_message.message_file = ",".join(media_entries)
            await session.commit()
            await asyncio.sleep(0.5)
            await state.clear()

    # Извлечение обновлённого сообщения
    async with await get_db_session() as session:
        result = await session.execute(
            select(ChannelMessage).filter(
                ChannelMessage.id == channel_message_id
            )
        )
        channel_message = result.scalars().first()

    flag_emoji = {
                "ru": "🇷🇺",
                "en": "🇺🇸",
                "all": "🌐"
            }
    
    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["edit_url_buttons_message"],
            callback_data=f"edit_url_buttons_message_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_lang"].format(language=flag_emoji.get(channel_message.language_code)),
            callback_data=f"change_message_lang_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_content"],
            callback_data=f"change_message_content_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["delete_channel_message"],
            callback_data=f"delete_channel_message_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["back"], 
            callback_data="back"
        )
    )
    
    media_entries = channel_message.message_file.split(",")

    if len(media_entries) > 1:
        media_group = []
        for entry in media_entries:
            media_type, file_id = entry.split(":")
            if media_type == "photo":
                media_group.append(InputMediaPhoto(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "video":
                media_group.append(InputMediaVideo(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "document":
                media_group.append(InputMediaDocument(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
            elif media_type == "audio":
                media_group.append(InputMediaAudio(media=file_id, caption=channel_message.message_text if len(media_group) == 0 else None, parse_mode="Markdown"))
        sent_messages = await message.answer_media_group(media_group)
        sent_message_ids = [msg.message_id for msg in sent_messages]
    
    await message.answer(
        MESSAGES[lang]["message_settings"].format(channel_name = channel.channel_name,
                                                  language = flag_emoji[channel_message.language_code],
                                                  message_type = MESSAGES[lang]["greetings"] if channel_message.message_type == "greetings" else MESSAGES[lang]["farewell"]),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    
    await state.clear()
    
    if sent_message_ids:
        await state.update_data(sent_message_ids=sent_message_ids)
    
    await state.update_data(previous_state = ChannelSetingsStates.channel_messages, channel_message_id = channel_message.id, channel_id = channel.id, message_type = channel_message.message_type)

async def process_single_message(message: Message, state: FSMContext, channel_message_id: int, lang: str):
    """
    Обработка одиночного сообщения (текст, фото, видео, документ и т.д.).
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
    elif message.video_note:
        file_id = message.video_note.file_id
        media_type = "video_note"
    elif message.text:
        file_id = None
        media_type = "text"
    else:
        await message.answer("Этот тип сообщений не поддерживается.")
        return
    
    message_text = message.md_text.replace("\\", "")
    
    # Сохраняем в базу данных
    async with await get_db_session() as session: 
        message_result = await session.execute(
            select(ChannelMessage).filter(
                ChannelMessage.id == channel_message_id
            )
        )
        existing_message = message_result.scalars().first()
        
        channel_result = await session.execute(select(Channels).filter(Channels.id == existing_message.channel_id))
        channel = channel_result.scalars().first()
        
        if existing_message:
            # Обновляем существующее сообщение
            existing_message.message_text = message_text
            existing_message.message_file = f"{media_type}:{file_id}"
            await session.commit()
            await asyncio.sleep(0.5)
            await state.clear()

    # Перестроение меню
    # Извлечение обновлённого сообщения
    async with await get_db_session() as session:
        result = await session.execute(
            select(ChannelMessage).filter(
                ChannelMessage.id == channel_message_id
            )
        )
        channel_message = result.scalars().first()
        
        # Загружаем кнопки из базы данных
        result = await session.execute(
            select(ChannelMessageButton).where(ChannelMessageButton.message_id == channel_message.id).order_by(ChannelMessageButton.row)
        )
        buttons = result.scalars().all()
        
        # Создаем клавиатуру
        message_keyboard = None
        if buttons:
            message_keyboard_builder = InlineKeyboardBuilder()
            current_row = None
            row_buttons = []
            
            for button in buttons:
                if button.row != current_row:
                    if row_buttons:  # Если есть кнопки в текущей строке, добавляем их
                        message_keyboard_builder.row(*row_buttons)
                        row_buttons = []
                    current_row = button.row
                
                # Добавляем кнопку в текущую строку
                row_buttons.append(InlineKeyboardButton(text=button.button_text, url=button.button_url))
            
            # Добавляем последнюю строку кнопок
            if row_buttons:
                message_keyboard_builder.row(*row_buttons)
            
            message_keyboard = message_keyboard_builder.as_markup()

    flag_emoji = {
                "ru": "🇷🇺",
                "en": "🇺🇸",
                "all": "🌐"
            }
    
    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["edit_url_buttons_message"],
            callback_data=f"edit_url_buttons_message_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_lang"].format(language=flag_emoji.get(channel_message.language_code)),
            callback_data=f"change_message_lang_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["change_message_content"],
            callback_data=f"change_message_content_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["delete_channel_message"],
            callback_data=f"delete_channel_message_{channel_message.id}"
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["back"], 
            callback_data="back"
        )
    )
    
    sent_message_ids = []
    if media_type == "photo":
        sent_message = await message.answer_photo(file_id, caption=message_text, parse_mode="Markdown", reply_markup=message_keyboard)
    elif media_type == "video":
        sent_message = await message.answer_video(file_id, caption=message_text, parse_mode="Markdown", reply_markup=message_keyboard)
    elif media_type == "document":
        sent_message = await message.answer_document(file_id, caption=message_text, parse_mode="Markdown", reply_markup=message_keyboard)
    elif media_type == "audio":
        sent_message = await message.answer_audio(file_id, caption=message_text, parse_mode="Markdown", reply_markup=message_keyboard)
    elif media_type == "text":
        sent_message = await message.answer(message_text, parse_mode="Markdown", reply_markup=message_keyboard)
    elif media_type == "video_note":
        sent_message = await message.answer_video_note(file_id, reply_markup=message_keyboard)
    if sent_message:
        sent_message_ids.append(sent_message.message_id)
    
    await message.answer(
        MESSAGES[lang]["message_settings"].format(channel_name = channel.channel_name,
                                                  language = flag_emoji[channel_message.language_code],
                                                  message_type = MESSAGES[lang]["greetings"] if channel_message.message_type == "greetings" else MESSAGES[lang]["farewell"]),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    await state.clear()
    
    # Сохраняем ID отправленных сообщений в состояние
    if sent_message_ids:
        await state.update_data(sent_message_ids=sent_message_ids)
    
    await state.update_data(previous_state = ChannelSetingsStates.channel_messages, channel_message_id = channel_message.id, channel_id = channel.id, message_type = channel_message.message_type)

@router.callback_query(F.data.startswith("delete_channel_message_"))
async def change_message_content(callback_query: CallbackQuery, state: FSMContext):
    channel_message_id = int(callback_query.data.split("_")[-1])
    
    lang = await get_lang(callback_query.from_user.id)
    
    async with await get_db_session() as session:
        result = await session.execute(
            select(ChannelMessage).filter(
                ChannelMessage.id == channel_message_id
            )
        )
        channel_message = result.scalars().first()
        
        channel_result = await session.execute(
            select(Channels).filter(
                Channels.id == channel_message.channel_id
            )
        )
        channel = channel_result.scalars().first()
        
        await session.delete(channel_message)
        await session.commit()
        
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["user_access"], callback_data=f"user_access_settings_{channel.id}")
    )
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["channel_greetings_settings"], callback_data=f"channel_greetings_settings_{channel.id}")
    )
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["channel_farewell_settings"], callback_data=f"channel_farewell_settings_{channel.id}")
    )
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["delete_channel"], callback_data=f"delete_channel_{channel.id}")
    )
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
    )

    await state.update_data(previous_state=ChannelSetingsStates.channels, bot_id = channel.bot_id)

    await callback_query.message.edit_text(
        text=MESSAGES[lang]["channel_settings_text"].format(channel_name = channel.channel_name),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )