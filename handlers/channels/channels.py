from aiogram import Router, types, Bot, types , F
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION, BaseFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ChatMemberUpdated, ChatJoinRequest, KeyboardButton, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import exists, and_
from sqlalchemy import case
from db import ChannelMessage, ChannelMessageButton, UserBot, User, BotSubscription, Channels, get_lang, get_db_session
from handlers.bot_settings import MainBotSettingsStates
from handlers.menu_handlers.adding_button import BotSettingsStates
from config import admins
from datetime import datetime
from dict import MESSAGES
import asyncio


class CaptchaTextFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        if not message.text:
            return False
        user_id = message.from_user.id
        async with await get_db_session() as session:
            user_result = await session.execute(
                select(User).filter(User.user_id == user_id, User.bot_token == bot.token)
            )
            user = user_result.scalars().first()
            if not user or not user.from_chat_id:
                return False
            channel_result = await session.execute(
                select(Channels).filter(Channels.channel_id == user.from_chat_id)
            )
            channel = channel_result.scalars().first()
            if not channel or not channel.captcha:
                return False
            if channel.captcha_button_text:
                return message.text == channel.captcha_button_text
            else:
                return message.text in [MESSAGES["ru"]["not_robot"], MESSAGES["en"]["not_robot"]]

router = Router(name=__name__)

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_bot_added(event: ChatMemberUpdated, bot: Bot):
    async with await get_db_session() as session:
        # Получаем информацию о боте из базы данных
        result = await session.execute(
            select(UserBot).filter(UserBot.bot_token == bot.token)
        )
        user_bot = result.scalars().first()

        if user_bot:
            # Получаем информацию о канале
            chat = event.chat
            channel_id = chat.id
            try:
                full_chat = await bot.get_chat(channel_id)
                channel_name = full_chat.title or "Unknown"
            except Exception:
                channel_name = chat.title or "Unknown"

            # Проверяем, что канал еще не добавлен в базу данных
            existing_channel = await session.execute(
                select(Channels).filter(Channels.channel_id == channel_id)
            )
            is_new = not existing_channel.scalars().first()

            if is_new:
                # Создаем новую запись в таблице Channels
                new_channel = Channels(
                    bot_id=user_bot.id,
                    channel_name=channel_name,
                    channel_id=channel_id
                )
                session.add(new_channel)

                try:
                    await session.commit()
                    print(f"Канал {channel_name} (ID: {channel_id}) успешно добавлен в базу данных.")
                except IntegrityError:
                    await session.rollback()
                    print(f"Ошибка при добавлении канала {channel_name} (ID: {channel_id}). Возможно, канал уже существует.")

            # Отправляем уведомление только для новых каналов
            if not is_new:
                return

            channel_result = await session.execute(
                select(Channels).filter(Channels.channel_id == channel_id)
            )
            channel = channel_result.scalars().first()
            # Отправляем сообщение пользователю, который добавил бота
            user_id = user_bot.user_id

            lang = await get_lang(user_id)

            message_text = (
                MESSAGES[lang]["bot_added_to_channel"].format(channel_name = channel_name)
            )

            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["setup_channel"], callback_data=f"channel_settings_{channel.id}"
                )
            )

            try:
                await bot.send_message(chat_id=user_id, text=message_text, parse_mode="Markdown", reply_markup=keyboard.as_markup())
                await bot.session.close()
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_bot_removed(event: ChatMemberUpdated, bot: Bot):
    async with await get_db_session() as session:
        # Получаем информацию о боте из базы данных
        result = await session.execute(
            select(UserBot).filter(UserBot.bot_token == event.new_chat_member.bot.token)
        )
        user_bot = result.scalars().first()

        if user_bot:
            # Получаем информацию о канале
            chat = event.chat
            channel_id = chat.id
            channel_name = chat.title or "Unknown"

            # Проверяем, что канал существует в базе данных
            existing_channel = await session.execute(
                select(Channels).filter(Channels.channel_id == channel_id)
            )
            channel_to_remove = existing_channel.scalars().first()

            if channel_to_remove:
                # Удаляем запись о канале из базы данных
                await session.delete(channel_to_remove)

                try:
                    await session.commit()
                    print(f"Канал {channel_name} (ID: {channel_id}) успешно удален из базы данных.")
                except Exception as e:
                    await session.rollback()
                    print(f"Ошибка при удалении канала {channel_name} (ID: {channel_id}): {e}")

            # Отправляем сообщение пользователю, который удалил бота
            user_id = user_bot.user_id
            
            lang = await get_lang(user_id)
            
            message_text = (
                MESSAGES[lang]["bot_removed_from_channel"].format(channel_name = channel_name)
            )

            try:
                await bot.send_message(chat_id=user_id, text=message_text, parse_mode="Markdown")
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                   
@router.chat_join_request()
async def handle_join_request(event: ChatJoinRequest, bot: Bot):
    # Информация о пользователе и канале
    async with await get_db_session() as session:
        channel_result = await session.execute(
            select(Channels).filter(Channels.channel_id == event.chat.id)
        )
        channel = channel_result.scalars().first()

    if not channel:
        return

    if not channel.auto_accept:
        return
    
    await asyncio.sleep(1)
    
    user_id = event.from_user.id
    username = event.from_user.username
    first_name = event.from_user.first_name
    last_name = event.from_user.last_name
    language_code = event.from_user.language_code
    chat_id = event.chat.id
    channel_name = event.chat.title
    
    async with await get_db_session() as session:
        user_result = await session.execute(
            select(User).filter(User.user_id == event.from_user.id,
                                User.bot_token == bot.token)
        )
        user = user_result.scalars().first()
        
        if not user:
            new_user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code if language_code in ("ru", "en") else "en",
                bot_token=bot.token,
                from_chat_id=chat_id
            )
            session.add(new_user)
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(e)
        if user:
            user.from_chat_id = chat_id
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(e)

    if channel.captcha:
        try:
            lang = language_code if language_code in ("ru", "en") else "en"
            captcha_btn_text = channel.captcha_button_text or MESSAGES[lang]["not_robot"]
            keyboard = ReplyKeyboardBuilder()
            keyboard.add(KeyboardButton(text=captcha_btn_text))
            try:
                await bot.send_message(text = MESSAGES[lang]["captcha_message"].format(channel_name = channel_name), chat_id=user_id, reply_markup=keyboard.as_markup(resize_keyboard = True), parse_mode="Markdown")
            except Exception:
                await bot.send_message(text = MESSAGES[lang]["captcha_message"].format(channel_name = channel_name), chat_id=user_id, reply_markup=keyboard.as_markup(resize_keyboard = True))
        except Exception as e:
            print(f"Не удалось одобрить запрос пользователя {username} (ID: {user_id}): {e}")
    else:
        async with await get_db_session() as session:
            message_result = await session.execute(
                select(ChannelMessage).filter(
                    ChannelMessage.channel_id == channel.id,
                    ChannelMessage.message_type == "greetings"
                ).order_by(
                    case(
                        (ChannelMessage.language_code == "all", 1),
                        (ChannelMessage.language_code == user.language_code, 2),
                        else_=3
                    )
                ).limit(1)
                )
            channel_message = message_result.scalars().first()
            
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        print(f"Запрос на вступление одобрен для пользователя {user_id}")
        if channel_message:
            await send_channel_message(bot, user_id, channel_message)
        else:
            await bot.send_message(user_id, "Вы зашли в канал")

@router.message(CaptchaTextFilter())
async def handle_captcha_request(message: Message, state: FSMContext, bot: Bot):
    # Получаем ID пользователя и чата
    user_id = message.from_user.id

    # Информация о пользователе и канале
    async with await get_db_session() as session:
        user_result = await session.execute(
            select(User).filter(User.user_id == user_id, User.bot_token == bot.token)
        )
        user = user_result.scalars().first()

        if not user:
            return

        channel_result = await session.execute(
            select(Channels).filter(Channels.channel_id == user.from_chat_id)
        )
        channel = channel_result.scalars().first()

        if not channel:
            return

    lang = await get_lang(user_id)
    
    try:
        async with await get_db_session() as session:
            message_result = await session.execute(
                select(ChannelMessage).filter(
                    ChannelMessage.channel_id == channel.id,
                    ChannelMessage.message_type == "greetings"
                ).order_by(
                    case(
                        (ChannelMessage.language_code == "all", 1),
                        (ChannelMessage.language_code == user.language_code, 2),
                        else_=3
                    )
                ).limit(1)
                )
            channel_message = message_result.scalars().first()
        
        await bot.approve_chat_join_request(chat_id=user.from_chat_id, user_id=user_id)
        if channel_message:
            await send_channel_message(bot, user_id, channel_message)
        else:
            await bot.send_message(user_id, text = MESSAGES[lang]["user_joined_channel"])
    except Exception as e:
        await message.answer("❌ Произошла ошибка при добавлении в чат. Пожалуйста, попробуйте позже.")
        print(f"Ошибка при одобрении запроса: {e}")

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def handle_user_leave_chat(event: ChatMemberUpdated, bot: Bot):
    user_id = event.from_user.id
    
    async with await get_db_session() as session:
        user_result = await session.execute(
            select(User).filter(User.user_id == user_id)
        )
        user = user_result.scalars().first()

        if not user:
            return

        if not user.from_chat_id:
            return

        channel_result = await session.execute(
            select(Channels).filter(Channels.channel_id == user.from_chat_id)
        )
        channel = channel_result.scalars().first()

        if not channel:
            return

        if not channel.auto_accept:
            return
        
        message_result = await session.execute(
            select(ChannelMessage).filter(
                ChannelMessage.channel_id == channel.id,
                ChannelMessage.message_type == "farewell"
            ).order_by(
                case(
                    (ChannelMessage.language_code == "all", 1),
                    (ChannelMessage.language_code == user.language_code, 2),
                    else_=3
                )
            ).limit(1)
        )
        channel_message = message_result.scalars().first()
        
        lang = await get_lang(user_id)
        
        if user:
            try:
                if channel_message:
                    await send_channel_message(bot, user_id, channel_message)
                else:
                    await bot.send_message(user_id, text = MESSAGES[lang]["user_leaved_channel"].format(channel_name = channel.channel_name))
            except Exception as e:
                print("Произошла ошибка при удалении пользователя из канала")
                
async def send_channel_message(bot: Bot, user_id: int, channel_message: ChannelMessage):
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
        await bot.send_media_group(user_id, media_group)
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
            await bot.send_photo(user_id, file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "video":
            await bot.send_video(user_id, file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "document":
            await bot.send_document(user_id, file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "audio":
            await bot.send_audio(user_id, file_id, caption=channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "text":
            await bot.send_message(user_id, channel_message.message_text, parse_mode="Markdown", reply_markup=message_keyboard)
        elif media_type == "video_note":
            await bot.send_video_note(user_id, file_id, reply_markup=message_keyboard)
           