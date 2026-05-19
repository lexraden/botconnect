from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, KeyboardButton, InlineKeyboardMarkup, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete, func
from sqlalchemy.future import select
from db import UserBot, get_db_session, increment_sent_messages_count, increment_replied_messages_count, BotMenuButton, Mailing, User, get_lang, BotSubscription, Channels, ChannelMessage, ChannelMessageButton
from config import media_group_tasks, media_groups, dp
from datetime import datetime
from handlers.menu_handlers.adding_button import BotSettingsStates
from handlers.menu_handlers.mailing import MailingStates
from handlers.channels.channel_settings import ChannelSetingsStates
from dict import MESSAGES

router = Router(name=__name__)

@router.callback_query(F.data == "back")
async def back_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    data = await state.get_data()
    previous_state = data.get("previous_state")
    sent_message_ids = data.get("sent_message_ids")
    
    if sent_message_ids:
        for sent_message_id in sent_message_ids:
            try:
                await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message_id)
                await state.update_data(sent_message_ids = None)
            except Exception as e:
                print(f"Ошибка при удалении сообщения {sent_message_id}: {e}")

    if previous_state == BotSettingsStates.bot_settings_menu:
        bot_id = data.get("bot_id") 
        
        # Получаем информацию о боте из базы данных
        async with await get_db_session() as session:
            result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
            bot = result.scalars().first()

            if bot:
                # Генерируем клавиатуру с действиями для управления ботом
                keyboard = InlineKeyboardBuilder()
                keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["greeting"], callback_data=f"open_greetings_{bot.id}"),
                    InlineKeyboardButton(text=MESSAGES[lang]["menu"], callback_data=f"open_menu_{bot.id}"),
                )
                keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["statistics"], callback_data=f"statistics_{bot.id}"),
                    InlineKeyboardButton(text=MESSAGES[lang]["mailings"], callback_data=f"open_mailings_{bot.id}"),
                )
                keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["channels"], callback_data="open_channels_"),
                )
                keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["feedback"], callback_data=f"feedback_{bot.id}")
                )

                # Отправляем сообщение с меню
                await callback_query.message.edit_text(
                    MESSAGES[lang]["bot_management"].format(bot_username=bot.bot_username),
                    reply_markup=keyboard.as_markup(),
                    )
            else:
                # Если бот не найден, отправляем ошибку
                await callback_query.answer(MESSAGES[lang]["bot_not_found"], show_alert=True)
        # Ответ на callback
        await callback_query.answer()
        await state.clear()
    
    elif previous_state == BotSettingsStates.main_menu:
        # Возврат в создание меню
        bot_token = callback_query.bot.token
        
        # Извлечение текущего бота пользователя из базы данных
        async with await get_db_session() as session:
            result_bot = await session.execute(
                select(UserBot).filter(UserBot.bot_token == bot_token)
            )
            user_bot = result_bot.scalars().first()  # Извлекаем бота
            
            if not user_bot:
                return

        # Извлечение обновлённого списка кнопок
        async with await get_db_session() as session:
            result = await session.execute(
                select(BotMenuButton).filter(BotMenuButton.bot_token == bot_token)
            )
            buttons = result.scalars().all()

        keyboard = InlineKeyboardBuilder()

        for i in range(0, len(buttons), 2):
            pair = buttons[i:i+2]  # Берем по 2 кнопки
            keyboard.row(
                *(InlineKeyboardButton(text=button.button_text, callback_data=f"button_{button.id}") for button in pair)
            )

        keyboard.row(InlineKeyboardButton(text="➕", callback_data=f"add_button_{user_bot.id}"))
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

        await callback_query.message.edit_text(
            MESSAGES[lang]["main_menu_description"],
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(BotSettingsStates.main_menu)
        await state.update_data(previous_state = BotSettingsStates.bot_settings_menu, bot_id = user_bot.id)

    elif previous_state == BotSettingsStates.button:
        button_id = data.get("edit_button_id")
        
        # Получение информации о кнопке из базы данных
        async with await get_db_session() as session:
            result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
            button = result.scalars().first()

        if not button:
            await callback_query.message.answer("Кнопка не найдена.")
            return

        # Отправка полного материала кнопки, если есть медиа
        sent_message_ids = []
        if button.file_id:
            media_entries = button.file_id.split(",")

            # Проверяем, если медиа состоит из нескольких файлов
            if len(media_entries) > 1:
                media_group = []
                for entry in media_entries:
                    media_type, file_id = entry.split(":")
                    if media_type == "photo":
                        media_group.append(InputMediaPhoto(media=file_id, caption=button.reply_message if len(media_group) == 0 else None, parse_mode="Markdown"))
                    elif media_type == "video":
                        media_group.append(InputMediaVideo(media=file_id, caption=button.reply_message if len(media_group) == 0 else None, parse_mode="Markdown"))
                    elif media_type == "document":
                        media_group.append(InputMediaDocument(media=file_id, caption=button.reply_message if len(media_group) == 0 else None, parse_mode="Markdown"))
                    elif media_type == "audio":
                        media_group.append(InputMediaAudio(media=file_id, caption=button.reply_message if len(media_group) == 0 else None, parse_mode="Markdown"))
                sent_messages = await callback_query.message.answer_media_group(media_group)
                sent_message_ids = [msg.message_id for msg in sent_messages]
            else:
                # Если это одиночный файл
                media_type, file_id = media_entries[0].split(":")
                if media_type == "photo":
                    sent_message = await callback_query.message.answer_photo(file_id, caption=button.reply_message, parse_mode="Markdown")
                elif media_type == "video":
                    sent_message = await callback_query.message.answer_video(file_id, caption=button.reply_message, parse_mode="Markdown")
                elif media_type == "document":
                    sent_message = await callback_query.message.answer_document(file_id, caption=button.reply_message, parse_mode="Markdown")
                elif media_type == "audio":
                    sent_message = await callback_query.message.answer_audio(file_id, caption=button.reply_message, parse_mode="Markdown")
                elif media_type == "text":
                    sent_message = await callback_query.message.answer(button.reply_message, parse_mode="Markdown")
                if sent_message:
                    sent_message_ids.append(sent_message.message_id)

        # Сохраняем ID отправленных сообщений в состояние
        if sent_message_ids:
            await state.update_data(sent_message_ids=sent_message_ids)

        # Создание меню для редактирования или удаления кнопки
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["edit_button"], callback_data=f"edit_button_{button.id}"),
            InlineKeyboardButton(text=MESSAGES[lang]["delete_button"], callback_data=f"delete_button_{button.id}")
        )
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
        )

        await callback_query.message.answer(
            MESSAGES[lang]["button_message"].format(button_text=button.button_text),
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.update_data(previous_state = BotSettingsStates.main_menu)
        await callback_query.message.delete()
        await callback_query.answer()
        
    elif previous_state == BotSettingsStates.choosing_inline_type:
        bot_id = data.get("bot_id")
        
        await state.set_state(BotSettingsStates.choosing_inline_type)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["inline_type_link"], 
                callback_data=f"set_inline_type_link_{bot_id}"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["inline_type_replace"], 
                callback_data=f"set_inline_type_replace_{bot_id}"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["inline_type_new"], 
                callback_data=f"set_inline_type_new_{bot_id}"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["back"], 
                callback_data="back"
            )
        )

        await callback_query.message.edit_text(
            MESSAGES[lang]["select_inline_type"],
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.update_data(previous_state = BotSettingsStates.adding_button)
        await callback_query.answer()
        
    elif previous_state == BotSettingsStates.waiting_for_button_text:
        await state.set_state(BotSettingsStates.waiting_for_button_text)
        await state.update_data(previous_state = BotSettingsStates.adding_button)
        await callback_query.message.edit_text(MESSAGES[lang]["enter_button_name"])
        await callback_query.answer()
        
    elif previous_state == BotSettingsStates.adding_button:
        bot_id = data.get("bot_id")
        # Создание инлайн-клавиатуры с выбором типа кнопки
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["regular_button"], 
                callback_data=f"add_regular_button_{bot_id}"
            ),
            InlineKeyboardButton(
                text=MESSAGES[lang]["inline_button"], 
                callback_data=f"add_inline_button_{bot_id}"
            )
        )
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["back"], 
                callback_data="back"
            )
        )

        await callback_query.message.edit_text(
            MESSAGES[lang]["add_button_instructions"],
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(BotSettingsStates.adding_button)
        await state.update_data(bot_id=bot_id, previous_state = BotSettingsStates.main_menu)
        await callback_query.answer()
    
    elif previous_state == BotSettingsStates.editing_button:
        user_id = callback_query.from_user.id

        button_id = data.get("edit_button_id") or data.get("button_id")
        
        # Удаление связанных сообщений
        data = await state.get_data()
        sent_message_ids = data.get("sent_message_ids", [])
        for sent_message_id in sent_message_ids:
            try:
                await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message_id)
            except Exception as e:
                print(f"Error deleting message {sent_message_id}: {e}")
        
        # Сохраняем ID редактируемой кнопки в состоянии
        await state.update_data(edit_button_id=button_id)

        async with await get_db_session() as session:
            result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
            button = result.scalars().first()
            
            # Создание инлайн-клавиатуры с действиями
            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["attach_button"], 
                    callback_data=f"attach_button_{button_id}"
                )
            )
            if button.linked_to_start:
                keyboard.row(
                    InlineKeyboardButton(
                        text=MESSAGES[lang]["detach_start"], 
                        callback_data=f"dettach_start_{button_id}"
                    )
                )    
            else:
                keyboard.row(
                    InlineKeyboardButton(
                        text=MESSAGES[lang]["attach_start"], 
                        callback_data=f"attach_start_{button_id}"
                    )
                )
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["link_to_command"], 
                    callback_data=f"link_to_command_{button_id}"
                )
            )                     
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["rename_button"], 
                    callback_data=f"rename_button_{button_id}"
                )
            )
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["update_content"], 
                    callback_data=f"update_content_{button_id}"
                )
            )
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["back"], 
                    callback_data="back"
                )
            )

        await callback_query.message.edit_text(
            MESSAGES[lang]["edit_button_prompt"],
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(BotSettingsStates.editing_button)
        await state.update_data(previous_state=BotSettingsStates.button)
        await callback_query.answer()
        
    elif previous_state == MailingStates.main_menu:
        bot_token = callback_query.message.bot.token

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
            InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
        )

        await state.update_data(bot_id=bot_entry.id, previous_state = BotSettingsStates.bot_settings_menu)
        
        # Отправка сообщения
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        
    elif previous_state == MailingStates.editing_mailings:
        bot_id = data.get("bot_id")

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
            await callback_query.message.edit_text(MESSAGES[lang]["no_scheduled_mailings"])
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
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.update_data(previous_state = MailingStates.main_menu)
        await callback_query.answer()
        
    elif previous_state == MailingStates.confirm_mailing:
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text=MESSAGES[lang]["send"], callback_data="send_mailing"),
            InlineKeyboardButton(text=MESSAGES[lang]["schedule"], callback_data="schedule_mailing"),
        )
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
        
        await state.update_data(previous_state = MailingStates.awaiting_message)
        
        await callback_query.message.edit_text(
        text=MESSAGES[lang]["confirm_mailing"],
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
        
    elif previous_state == MailingStates.awaiting_message:
        bot_id = data.get("bot_id")
        await state.update_data(bot_id=bot_id)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
        
        await callback_query.message.edit_text(
            MESSAGES[lang]["send_mailing_message"],
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )

        await state.set_state(MailingStates.awaiting_message)
        await state.update_data(previous_state = MailingStates.main_menu)
        await callback_query.answer()
    
    elif previous_state == ChannelSetingsStates.channels:
        bot_id = data.get("bot_id") 
        
        async with await get_db_session() as session:
            channels_result = await session.execute(
                select(Channels).filter(
                    Channels.bot_id == bot_id
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
    
    elif previous_state == ChannelSetingsStates.channel_settings:
        channel_id = data.get("channel_id")
    
        async with await get_db_session() as session:
            channel_result = await session.execute(
                    select(Channels).filter(Channels.id == channel_id)
                )
            channel = channel_result.scalars().first()
            
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
        
        await state.update_data(previous_state = ChannelSetingsStates.channels, channel_id = channel_id, bot_id = channel.bot_id)
        
        await callback_query.message.edit_text(
            text=MESSAGES[lang]["channel_settings_text"].format(channel_name = channel.channel_name),
            parse_mode="Markdown",
            reply_markup=keyboard.as_markup()
        )
    
    elif previous_state == ChannelSetingsStates.channel_messages:
        channel_id = data.get("channel_id")
        message_type = data.get("message_type")
        
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
                        callback_data=f"add_greeting_{channel_id}" if message_type == "greetings" else f"add_farewell_{channel_id}"
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

    elif previous_state == ChannelSetingsStates.channel_message_settings:
        channel_message_id = data.get("channel_message_id")
        
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
        
        await state.update_data(previous_state = ChannelSetingsStates.channel_messages, channel_message_id = channel_message.id, channel_id = channel.channel_id)

    elif previous_state == ChannelSetingsStates.user_access:
        channel_id = data.get("channel_id")

        async with await get_db_session() as session:
            channel_result = await session.execute(
                    select(Channels).filter(Channels.id == channel_id)
                )
            channel = channel_result.scalars().first()

            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["user_access_enabled"] if channel.auto_accept else MESSAGES[lang]["user_access_disabled"], callback_data=f"auto_access_switch_{channel.id}")
            )
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["captha_enabled"] if channel.captcha else MESSAGES[lang]["captha_disabled"], callback_data=f"captha_switch_{channel.id}")
            )
            if channel.captcha:
                keyboard.row(
                    InlineKeyboardButton(text=MESSAGES[lang]["captcha_settings"], callback_data=f"captcha_settings_{channel.id}")
                )
            keyboard.row(
                InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
            )

        await state.update_data(previous_state=ChannelSetingsStates.channel_settings, channel_id=channel_id)

        await callback_query.message.edit_text(
            text=MESSAGES[lang]["user_access_text"].format(channel_name=channel.channel_name,
                                                           user_access="✅" if channel.auto_accept else "❌",
                                                           captcha="✅" if channel.captcha else "❌"),
            parse_mode="Markdown",
            reply_markup=keyboard.as_markup()
        )