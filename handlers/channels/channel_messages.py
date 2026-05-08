from aiogram import Router, types, Bot, types , F
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ChatMemberUpdated, ChatJoinRequest, KeyboardButton, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import exists, and_
from db import UserBot, User, BotSubscription, Channels, ChannelMessage, get_lang, get_db_session
from handlers.bot_settings import MainBotSettingsStates
from handlers.menu_handlers.adding_button import BotSettingsStates
from handlers.channels.channel_settings import ChannelSetingsStates
from config import admins, media_group_tasks, media_groups
from datetime import datetime
from dict import MESSAGES
import asyncio

router = Router(name=__name__)

@router.callback_query(F.data.startswith("channel_greetings_settings_") | F.data.startswith("channel_farewell_settings_"))
async def channel_greetings_settings(callback_query: CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[-1])
    message_type = callback_query.data.split("_")[1]
    
    lang = await get_lang(callback_query.from_user.id)
    
    async with await get_db_session() as session:
        channel_result = await session.execute(
            select(Channels).filter(Channels.id == channel_id)
        )
        channel = channel_result.scalars().first()

        if not channel:
            await callback_query.answer("Канал не найден.", show_alert=True)
            return

        messages_result = await session.execute(
            select(ChannelMessage).filter(ChannelMessage.channel_id == channel_id,
                                          ChannelMessage.message_type == message_type)
        )
        messages = messages_result.scalars().all()

        # Словарь эмодзи для типов сообщений
        emoji_dict = {
            "photo": "🖼️",
            "video": "🎥",
            "audio": "🎵",
            "document": "📄",
            "text": "📝",
            "video_note": "🎥",
            "media_group": "📦",
            None: "❔"
        }

        # Словарь типов сообщений
        type_dict = {
            "photo": {"ru": "Фото", "en": "Photo"},
            "video": {"ru": "Видео", "en": "Video"},
            "audio": {"ru": "Аудио", "en": "Audio"},
            "document": {"ru": "Документ", "en": "Document"},
            "text": {"ru": "Текст", "en": "Text"},
            "video_note": {"ru": "Кружок", "en": "Video Note"},
            "media_group": {"ru": "Разные медиа", "en": "Mixed Media"},
            None: {"ru": "Неизвестно", "en": "Unknown"},
        }

        # Создаем клавиатуру с помощью InlineKeyboardBuilder
        keyboard = InlineKeyboardBuilder()

        has_ru_message = any(msg.language_code == "ru" for msg in messages)
        has_en_message = any(msg.language_code == "en" for msg in messages)
        has_all_message = any(msg.language_code == "all" for msg in messages)
        
        for msg in messages:
            # Определяем смайлик флага в зависимости от языка
            flag_emoji = {
                "ru": "🇷🇺",
                "en": "🇺🇸",
                "all": "🌐"
            }.get(msg.language_code, "❓")  # Если язык неизвестен, используем "❓"

            if msg.message_file:
                # Определяем тип файла на основе содержимого file_id
                if len(msg.message_file.split(",")) > 1:
                    media_type = "media_group"
                elif "photo" in msg.message_file:
                    media_type = "photo"
                elif "video" in msg.message_file:
                    media_type = "video"
                elif "document" in msg.message_file:
                    media_type = "document"
                elif "audio" in msg.message_file or "voice" in msg.message_file:
                    media_type = "audio"
                elif "video_note" in msg.message_file:
                    media_type = "video"
                elif "text" in msg.message_file:
                    media_type = "text"
                else:
                    media_type = None

                preview_text = f"{type_dict.get(media_type, {}).get(lang, 'Unknown')}: {msg.message_text[:30] + "..." if len(msg.message_text) > 30 else msg.message_text}"
            else:
                media_type = None
                preview_text = type_dict[None][lang]

            # Получаем эмодзи и название типа сообщения
            emoji = emoji_dict.get(media_type, "❔")
            type_name = type_dict.get(media_type, {}).get(lang, "Unknown")

            # Формируем текст кнопки
            button_text = f"{flag_emoji} {emoji} {preview_text if preview_text else type_name}"

            # Добавляем кнопку
            keyboard.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"edit_message_{msg.id}"
                )
            )

        if not has_all_message and not (has_ru_message and has_en_message):
            keyboard.row(
                InlineKeyboardButton(
                    text="➕",
                    callback_data=f"add_greetings_{channel_id}" if message_type == "greetings" else f"add_farewell_{channel_id}"
                )
            )
        
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
        )
        
        await state.update_data(previous_state=ChannelSetingsStates.channel_settings, message_type=message_type, channel_id=channel_id)

        # Отправляем сообщение с клавиатурой
        await callback_query.message.edit_text(
            text=MESSAGES[lang]["channel_greetings_settings_message"] if message_type == "greetings" else MESSAGES[lang]["channel_farewell_settings_message"],
            reply_markup=keyboard.as_markup()
        )

@router.callback_query(F.data.startswith("add_greetings_") | F.data.startswith("add_farewell_"))
async def add_message_to_channel(callback_query: CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[-1])
    message_type = callback_query.data.split("_")[-2]
    
    async with await get_db_session() as session:
        message_result = await session.execute(
            select(ChannelMessage).filter(ChannelMessage.channel_id == channel_id,
                                          ChannelMessage.message_type == message_type)
        )
        channel_messages = message_result.scalars().all()
    
        has_ru_message = any(msg.language_code == "ru" for msg in channel_messages)
        has_en_message = any(msg.language_code == "en" for msg in channel_messages)
    
    lang = await get_lang(callback_query.from_user.id)
    
    keyboard = InlineKeyboardBuilder()
    if channel_messages:
        if has_en_message and not has_ru_message:
            keyboard.row(
                InlineKeyboardButton(text="🇷🇺 RU", callback_data="choose_ru")
            )
        elif has_ru_message and not has_en_message:
            keyboard.row(
                InlineKeyboardButton(text="🇺🇸 EN", callback_data="choose_en")
            )
    else:
        keyboard.row(
            InlineKeyboardButton(text="🇺🇸 EN", callback_data="choose_en")
        )
        keyboard.row(
            InlineKeyboardButton(text="🇷🇺 RU", callback_data="choose_ru")
        )
        keyboard.row(
            InlineKeyboardButton(text="🌐 ALL", callback_data="choose_all")
        )
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
    )
    
    await state.update_data(previous_state=ChannelSetingsStates.channel_settings)
    
    await callback_query.message.edit_text(text=MESSAGES[lang]["choose_message_language"], reply_markup=keyboard.as_markup(), parse_mode="Markdown")
        
@router.callback_query(F.data.startswith("choose_"))
async def add_message_to_channel(callback_query: CallbackQuery, state: FSMContext):    
    lang = await get_lang(callback_query.from_user.id)
    
    language_code = callback_query.data.split("_")[-1]
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
    )
    
    await state.set_state(ChannelSetingsStates.awaiting_message)
    await state.update_data(previous_state=ChannelSetingsStates.language_choose, language_code=language_code)
    
    await callback_query.message.edit_text(text=MESSAGES[lang]["message_to_send"], reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    
@router.message(ChannelSetingsStates.awaiting_message)
async def message_to_send(message: Message, state: FSMContext):
    """
    Обработка сообщения: одиночное или медиагруппа.
    """
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    data = await state.get_data()
    channel_id = data.get("channel_id")
    message_type = data.get("message_type")
    language_code = data.get("language_code")

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
            process_media_group(media_group_id, state, message_type, channel_id, message, language_code, lang)
        )
    else:
        # Одиночное сообщение
        await process_single_message(message, state, channel_id, message_type, language_code, lang)
        
async def process_media_group(media_group_id: str, state: FSMContext, message_type: str, channel_id: int, message: Message, language_code: str, lang: str):
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
        result = await session.execute(select(Channels).filter(Channels.id == channel_id))
        channel = result.scalars().first()
        
        if channel:                          
            new_message = ChannelMessage(
                channel_id=channel_id,
                language_code=language_code,
                message_type=message_type,
                message_text=caption_text,
                message_file=",".join(media_entries)
            )
            session.add(new_message)
            await session.commit()
            await asyncio.sleep(0.5)
            await state.clear()
    
    # Перестроение меню 
    # Извлечение обновлённого сообщения
    async with await get_db_session() as session:
        result = await session.execute(
            select(ChannelMessage).filter(ChannelMessage.channel_id == channel_id,
                                          ChannelMessage.language_code == language_code,
                                          ChannelMessage.message_type == message_type
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
            text=MESSAGES[lang]["change_message_lang"].format(language=flag_emoji.get(language_code)),
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
                                                  message_type = MESSAGES[lang]["greetings"] if channel_message.message_type == "grettings" else MESSAGES[lang]["farewell"]),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    
    await state.clear()
    
    if sent_message_ids:
        await state.update_data(sent_message_ids=sent_message_ids)
    
    await state.update_data(previous_state = ChannelSetingsStates.channel_messages, channel_message_id = channel_message.id, channel_id = channel.channel_id, message_type = channel_message.message_type)

async def process_single_message(message: Message, state: FSMContext, channel_id: int, message_type: str, language_code: str, lang: str):
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
        result = await session.execute(select(Channels).filter(Channels.id == channel_id))
        channel = result.scalars().first()
        
        if channel:                          
            new_message = ChannelMessage(
                channel_id=channel_id,
                language_code=language_code,
                message_type=message_type,
                message_text=message_text,
                message_file=f"{media_type}:{file_id}"
            )
            session.add(new_message)
            await session.commit()
            await asyncio.sleep(0.5)
            await state.clear()

    # Перестроение меню
    # Извлечение обновлённого сообщения
    async with await get_db_session() as session:
        result = await session.execute(
            select(ChannelMessage).filter(ChannelMessage.channel_id == channel_id,
                                          ChannelMessage.language_code == language_code,
                                          ChannelMessage.message_type == message_type
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
            text=MESSAGES[lang]["change_message_lang"].format(language=flag_emoji.get(language_code)),
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
        sent_message = await message.answer_photo(file_id, caption=message_text, parse_mode="Markdown")
    elif media_type == "video":
        sent_message = await message.answer_video(file_id, caption=message_text, parse_mode="Markdown")
    elif media_type == "document":
        sent_message = await message.answer_document(file_id, caption=message_text, parse_mode="Markdown")
    elif media_type == "audio":
        sent_message = await message.answer_audio(file_id, caption=message_text, parse_mode="Markdown")
    elif media_type == "text":
        sent_message = await message.answer(message_text, parse_mode="Markdown")
    if sent_message:
        sent_message_ids.append(sent_message.message_id)
    
    await message.answer(
        MESSAGES[lang]["message_settings"].format(channel_name = channel.channel_name,
                                                  language = flag_emoji[channel_message.language_code],
                                                  message_type = MESSAGES[lang]["greetings"] if channel_message.message_type == "grettings" else MESSAGES[lang]["farewell"]),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
    await state.clear()
    
    # Сохраняем ID отправленных сообщений в состояние
    if sent_message_ids:
        await state.update_data(sent_message_ids=sent_message_ids)
    
    await state.update_data(previous_state = ChannelSetingsStates.channel_messages, channel_message_id = channel_message.id, channel_id = channel.channel_id, message_type = channel_message.message_type)