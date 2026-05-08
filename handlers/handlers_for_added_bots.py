from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart, Command
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete, func
from sqlalchemy.future import select
from db import UserBot, get_db_session, increment_sent_messages_count, increment_replied_messages_count, BotMenuButton, User, Mailing, BotSubscription, get_lang
from dict import MESSAGES
from datetime import datetime
from config import WEBHOOK_TUNNEL_URL
from handlers.menu_handlers.adding_button import BotSettingsStates

router = Router()

class NotReplyAndNotButtonFilter(Filter):
    async def __call__(self, message: types.Message) -> bool:
        if message.reply_to_message:
            return False  # Это ответное сообщение, не обрабатываем

        # Проверяем, не является ли текст кнопкой
        async with await get_db_session() as session:
            result = await session.execute(select(BotMenuButton).filter(
                BotMenuButton.bot_token == message.bot.token,
                BotMenuButton.button_text == message.text,
                BotMenuButton.button_type == "regular"
            ))
            button = result.scalars().first()

        return button is None

class IsCommandFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        if not message.text.startswith("/"):  # Сообщение должно начинаться с "/"
            return False

        # Убираем "/", чтобы проверить текст команды
        command = message.text

        # Проверяем, не привязана ли команда к кнопке
        async with await get_db_session() as session:
            result = await session.execute(
                select(BotMenuButton).filter(
                    BotMenuButton.bot_token == message.bot.token,
                    BotMenuButton.command == command
                )
            )
            button = result.scalars().first()

        # Если команда привязана к кнопке, возвращаем True, иначе False
        return button is not None

@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    
    await state.clear()
    # Добавление пользователя в базу данных
    async with await get_db_session() as session:
        # Проверяем, существует ли пользователь с указанным user_id и bot_token
        user_result = await session.execute(
            select(User).filter(
                User.user_id == message.from_user.id,
                User.bot_token == message.bot.token
            )
        )
        user = user_result.scalars().first()

        if not user:
            # Добавляем нового пользователя
            new_user = User(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code,
                bot_token=message.bot.token
            )
            session.add(new_user)
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(e)
        admin_result = await session.execute(
            select(UserBot).filter(
                UserBot.bot_token == message.bot.token
            )
        )
        bot = admin_result.scalars().first()
                
    if message.text.startswith("/start menu"):
        
        if message.from_user.id != bot.user_id:
            return
        
        async with await get_db_session() as session:
            bot_result = await session.execute(
                select(UserBot).filter(UserBot.bot_token == message.bot.token)
            )
            user_bot = bot_result.scalars().first()

            if not user_bot:
                await message.answer(MESSAGES[lang]["bot_not_found"])
                return

        async with await get_db_session() as session:
            buttons_result = await session.execute(
                select(BotMenuButton).filter(BotMenuButton.bot_token == message.bot.token)
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
        
        await message.answer(
            MESSAGES[lang]["main_menu_description"],
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(BotSettingsStates.main_menu)
        return
    
    elif message.text.startswith("/start@"):
        async with await get_db_session() as session:
            bot_result = await session.execute(select(UserBot).filter(UserBot.bot_token == message.bot.token))
            bot_entry = bot_result.scalars().first()

            if not bot_entry:
                await message.answer(MESSAGES[lang]["bot_not_found"])
                return

            bot_entry.sent_messages_to = message.chat.id
            await session.commit()

        await message.answer(MESSAGES[lang]["bot_connected_to_chat"])
        return
        
    elif message.text.startswith("/start mailing"):
        if message.from_user.id != bot.user_id:
            return
        
        bot_token = message.bot.token

        async with await get_db_session() as session:
            # Получение информации о боте
            bot_result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
            bot_entry = bot_result.scalars().first()

            if not bot_entry:
                await message.edit_text("Ошибка: бот не найден.")
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
            await message.answer(
                message_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            return
        
    elif message.text.startswith("/start greeting"):
        if message.from_user.id != bot.user_id:
            return

        # Получаем текущее приветственное сообщение из базы данных
        async with await get_db_session() as session:
            result = await session.execute(
                select(UserBot).filter(UserBot.bot_token == message.bot.token)
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
                sent_message = await message.answer_photo(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "video":
                sent_message = await message.answer_video(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "document":
                sent_message = await message.answer_document(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "audio":
                sent_message = await message.answer_audio(file_id, caption=greeting_message, parse_mode="Markdown")
            elif media_type == "video_note":
                sent_message = await message.answer_video_note(file_id, caption=greeting_message, parse_mode="Markdown")
            else:
            # Отправляем только текстовое сообщение
                sent_message = await message.answer(greeting_message, parse_mode="Markdown")
        else:
            sent_message = await message.answer(greeting_message, parse_mode="Markdown")
        if sent_message:
            sent_message_ids.append(sent_message.message_id)

        # Клавиатура
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

        await message.edit_text(
            text = MESSAGES[lang]["current_greeting"],
            parse_mode="Markdown",
            reply_markup=keyboard.as_markup()
        )

        # Устанавливаем состояние для ожидания нового приветствия
        await state.set_state(BotSettingsStates.editing_greeting)
        await state.update_data(bot_id=bot_entry.id, previous_state=BotSettingsStates.bot_settings_menu, sent_message_ids = sent_message_ids)
        return
    
    elif message.text.startswith("/start settings"):
        if message.from_user.id != bot.user_id:
            return
        
        user_id = message.from_user.id
        lang = await get_lang(user_id)

        # Извлекаем ID бота из callback_data
        bot_token = message.bot.token

        # Получаем информацию о боте из базы данных
        async with await get_db_session() as session:
            result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
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
            await message.answer(
                MESSAGES[lang]["bot_management"].format(bot_username=bot.bot_username),
                reply_markup=keyboard.as_markup()
            )
        else:
            # Если бот не найден, отправляем ошибку
            await message.answer(MESSAGES[lang]["bot_not_found"], show_alert=True)

        # Обновляем состояние
        await state.update_data(bot_id=bot.id)
        return
    
    # Извлечение кнопок из базы данных
    async with await get_db_session() as session:
        # Получаем приветственное сообщение
        result_bot = await session.execute(
            select(UserBot).filter(UserBot.bot_token == message.bot.token)
        )
        bot = result_bot.scalars().first()
        greeting_message = bot.greeting_message
        greeting_file = bot.greeting_file
        
        # Замена переменных %name% и %id% на данные пользователя
        user_name = message.from_user.full_name
        user_id = message.from_user.id
        greeting_message = greeting_message.replace("%name%", user_name).replace("%id%", str(user_id))

        # Извлечение кнопок
        result_buttons = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.bot_token == message.bot.token,
                                            BotMenuButton.linked_to_start == True)
        )
        buttons = result_buttons.scalars().all()

    keyboard_builder = None
    if buttons:
        # Определяем тип первой кнопки
        first_button_type = buttons[0].button_type

        if first_button_type == "inline":
            keyboard_builder = InlineKeyboardBuilder()
            for i in range(0, len(buttons), 2):
                pair = buttons[i:i+2]  # Берем по 2 кнопки
                keyboard_builder.row(
                    *(InlineKeyboardButton(
                        text=button.button_text,
                        url=button.reply_message if button.action_type == "link" else None,
                        callback_data=f"inline_button_{button.id}" if button.action_type != "link" else None
                    ) for button in pair)
                )
            keyboard_builder = keyboard_builder.as_markup()
        elif first_button_type == "regular":
            keyboard_builder = ReplyKeyboardBuilder()
            for i in range(0, len(buttons), 2):
                pair = buttons[i:i+2]  # Берем по 2 кнопки
                keyboard_builder.row(
                    *(KeyboardButton(text=button.button_text) for button in pair)
                )
            keyboard_builder = keyboard_builder.as_markup(resize_keyboard=True)

        if greeting_file:
            media_entries = greeting_file.split(",")
            # Отправка одного медиафайла
            media_type, file_id = media_entries[0].split(":")
            if media_type == "photo":
                await message.answer_photo(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "video":
                await message.answer_video(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "document":
                await message.answer_document(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "audio":
                await message.answer_audio(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "video_note":
                await message.answer_video_note(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            else:
            # Отправляем только текстовое сообщение
                await message.answer(greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
        else:
            await message.answer(greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
    else:
        if greeting_file:
            media_entries = greeting_file.split(",")
            # Отправка одного медиафайла
            media_type, file_id = media_entries[0].split(":")
            if media_type == "photo":
                await message.answer_photo(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "video":
                await message.answer_video(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "document":
                await message.answer_document(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "audio":
                await message.answer_audio(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            elif media_type == "video_note":
                await message.answer_video_note(file_id, caption=greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
            else:
            # Отправляем только текстовое сообщение
                await message.answer(greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")
        else:
            await message.answer(greeting_message, reply_markup=keyboard_builder, parse_mode="Markdown")

@router.message(Command("settings"))
async def settings(message: Message, state: FSMContext):       
    user_id = message.from_user.id
    lang = await get_lang(user_id)

    # Извлекаем ID бота из callback_data
    bot_token = message.bot.token

    # Получаем информацию о боте из базы данных
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
        bot = result.scalars().first()
    
    if message.from_user.id != bot.user_id:
        return
        
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
        await message.answer(
            MESSAGES[lang]["bot_management"].format(bot_username=bot.bot_username),
            reply_markup=keyboard.as_markup()
        )
    else:
        # Если бот не найден, отправляем ошибку
        await message.answer(MESSAGES[lang]["bot_not_found"], show_alert=True)

    # Обновляем состояние
    await state.update_data(bot_id=bot.id)

@router.message(IsCommandFilter())
async def handle_command_keyboard(message: Message):
    """
    Обработчик для вызова клавиатуры соответствующей кнопкам типа через команду.
    """
    command = message.text

    async with await get_db_session() as session:
        # Получаем кнопки, связанные с этой командой
        result = await session.execute(
            select(BotMenuButton).filter(
                BotMenuButton.bot_token == message.bot.token,
                BotMenuButton.command == command
            )
        )
        buttons = result.scalars().all()

    if not buttons:
        return

    # Определяем тип кнопок (все кнопки должны быть одного типа)
    button_type = buttons[0].button_type

    if button_type == "inline":
        # Генерация Inline-клавиатуры
        keyboard = InlineKeyboardBuilder()
        for i in range(0, len(buttons), 2):
            pair = buttons[i:i+2]  # Берём по 2 кнопки
            keyboard.row(
                *[
                    InlineKeyboardButton(
                        text=button.button_text,
                        url=button.reply_message if button.action_type == "link" else None,
                        callback_data=f"inline_button_{button.id}" if button.action_type != "link" else None
                    )
                    for button in pair
                ]
            )
        await message.answer("Меню:", reply_markup=keyboard.as_markup())

    elif button_type == "regular":
        # Генерация Reply-клавиатуры
        keyboard = ReplyKeyboardBuilder()
        for i in range(0, len(buttons), 2):
            pair = buttons[i:i+2]  # Берём по 2 кнопки
            keyboard.row(
                *[KeyboardButton(text=button.button_text) for button in pair]
            )
        await message.answer("Меню:", reply_markup=keyboard.as_markup(resize_keyboard=True))

    else:
        await message.answer("Не удалось определить тип кнопок.")

# Хендлер для администратора, который будет отвечать на пересланные сообщения
@router.message(F.reply_to_message and F.reply_to_message.forward_from)
async def admin_reply_message(message: types.Message):
    user_id = message.from_user.id
    lang = await get_lang(user_id)  # Получаем язык пользователя

    async with await get_db_session() as session:
        # Ищем бота по его токену
        result = await session.execute(select(UserBot).filter(UserBot.bot_token == message.bot.token))
        bot_entry = result.scalars().first()

    if not bot_entry:
        print("Бот не найден в базе данных.")
        return

    if message.text.startswith("/ban"):
        handeled_message_user_id = message.reply_to_message.forward_from.id
        async with await get_db_session() as session:
            # Ищем бота по его токену
            user_result = await session.execute(select(User).filter(User.bot_token == message.bot.token,
                                                                    User.user_id == handeled_message_user_id))
            user_for_ban = user_result.scalars().first()
            
            user_for_ban.is_banned = True
            await session.commit()
        await message.answer("User was banned")
        return
    
    if message.text.startswith("/unban"):
        handeled_message_user_id = message.reply_to_message.forward_from.id
        async with await get_db_session() as session:
            # Ищем бота по его токену
            user_result = await session.execute(select(User).filter(User.bot_token == message.bot.token,
                                                                    User.user_id == handeled_message_user_id))
            user_for_ban = user_result.scalars().first()
            
            user_for_ban.is_banned = False
            await session.commit()
        await message.answer("User was unbanned")
        return
    
    # Если сообщения отправляются в чат
    if bot_entry.sent_messages_to:
        if message.reply_to_message:
            original_message = message.reply_to_message

            # Проверка, является ли оригинальное сообщение пересланным
            if original_message.forward_from:
                try:
                    # Пересылаем ответ пользователю
                    await message.bot.send_message(
                        chat_id=original_message.forward_from.id,  # Отправляем в чат пользователя
                        text=message.md_text,  # Ответ от администратора
                        parse_mode="Markdown"  # Форматирование текста
                    )
                    await increment_replied_messages_count(message.bot.token)  # Увеличиваем счетчик ответов
                except Exception as e:
                    print(f"Ошибка при отправке ответа пользователю: {e}")
            else:
                await message.reply(MESSAGES[lang]["not_forwarded_message"])
        else:
            await message.reply(MESSAGES[lang]["reply_to_message"])
    else:
        admin_id = bot_entry.user_id  # Получаем ID администратора (создателя бота)

        # Проверяем, является ли отправитель администратором
        if message.from_user.id == admin_id:
            if message.reply_to_message:
                original_message = message.reply_to_message

                # Проверка, является ли оригинальное сообщение пересланным
                if original_message.forward_from:
                    try:
                        await message.bot.send_message(
                            chat_id=original_message.forward_from.id,  # Отправляем в чат пользователя
                            text=message.md_text,  # Ответ от администратора
                            parse_mode="Markdown"  # Форматирование текста
                        )
                        await increment_replied_messages_count(message.bot.token)  # Увеличиваем счетчик ответов
                    except Exception as e:
                        print(f"Ошибка при отправке ответа пользователю: {e}")
                else:
                    await message.reply(MESSAGES[lang]["not_forwarded_message"])
            else:
                await message.reply(MESSAGES[lang]["reply_to_message"])

@router.message(NotReplyAndNotButtonFilter())
async def forward_message_to_admin(message: types.Message):
    async with await get_db_session() as session:
        # Ищем бота по его токену
        result = await session.execute(select(UserBot).filter(UserBot.bot_token == message.bot.token))
        bot_entry = result.scalars().first()

        user_result = await session.execute(select(User).filter(User.user_id == message.from_user.id,
                                                                User.bot_token == message.bot.token))
        from_user = user_result.scalars().first()
    
    if bot_entry and not from_user.is_banned:
        if bot_entry.sent_messages_to:
            if message.chat.id == bot_entry.sent_messages_to:
                return
            else:
                try:
                    await message.bot.forward_message(chat_id=bot_entry.sent_messages_to, from_chat_id=message.chat.id, message_id=message.message_id)
                    await increment_sent_messages_count(message.bot.token)
                except Exception as e:
                    print(f"Ошибка при отправке сообщения админу: {e}")   
        else:  
            admin_id = bot_entry.user_id  # Получаем ID администратора (создателя бота)

            # Проверяем, не отправил ли это сообщение сам администратор
            if message.from_user.id != admin_id:
                # Пересылаем сообщение админу
                try:
                    await message.bot.forward_message(chat_id=admin_id, from_chat_id=message.chat.id, message_id=message.message_id)
                    await increment_sent_messages_count(message.bot.token)
                except Exception as e:
                    print(f"Ошибка при отправке сообщения админу: {e}")
    else:
        print("Бот не найден в базе данных.")

# Хендлер для нажатия кнопок меню
@router.message()
async def handle_button_click(message: Message):
    # Проверка, нажата ли одна из кнопок
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(
            BotMenuButton.bot_token == message.bot.token,
            BotMenuButton.button_text == message.text
        ))
        button = result.scalars().first()
        
        # Извлечение привязанных кнопок
        result_attached = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.linked_button_id == button.id)
        )
        attached_buttons = result_attached.scalars().all()

    keyboard = None
    if attached_buttons:
        # Определяем тип первой кнопки
        first_button_type = attached_buttons[0].button_type

        if first_button_type == "inline":
            keyboard = InlineKeyboardBuilder()
            for i in range(0, len(attached_buttons), 2):
                # Берем по 2 кнопки
                pair = attached_buttons[i:i + 2]
                keyboard.row(
                    *(
                        InlineKeyboardButton(
                            text=attached_button.button_text,
                            url=attached_button.reply_message
                        ) if attached_button.action_type == "link" else InlineKeyboardButton(
                            text=attached_button.button_text,
                            callback_data=f"inline_button_{attached_button.id}"
                        ) for attached_button in pair
                    )
                )
            keyboard = keyboard.as_markup()

        elif first_button_type == "regular":
            keyboard = ReplyKeyboardBuilder()
            for i in range(0, len(attached_buttons), 2):
                # Берем по 2 кнопки
                pair = attached_buttons[i:i + 2]
                keyboard.row(
                    *(KeyboardButton(text=attached_button.button_text) for attached_button in pair)
                )
            keyboard = keyboard.as_markup(resize_keyboard=True)
    
    if button:
        # Проверка типа кнопки и отправка соответствующего сообщения
        if button.button_type.startswith("regular"):
            if button.file_id:
                # Отправка медиафайлов или медиагрупп
                media_entries = button.file_id.split(",")
                if len(media_entries) > 1:
                    # Медиагруппа
                    media = []
                    for i, entry in enumerate(media_entries):
                        media_type, file_id = entry.split(":")
                        if file_id:
                            if media_type == "photo":
                                media.append(InputMediaPhoto(media=file_id, caption=button.reply_message if i == 0 else None, parse_mode="Markdown"))
                            elif media_type == "video":
                                media.append(InputMediaVideo(media=file_id, caption=button.reply_message if i == 0 else None, parse_mode="Markdown"))
                            elif media_type == "document":
                                media.append(InputMediaDocument(media=file_id, caption=button.reply_message if i == 0 else None, parse_mode="Markdown"))
                            elif media_type == "audio":
                                media.append(InputMediaAudio(media=file_id, caption=button.reply_message if i == 0 else None, parse_mode="Markdown"))
                    await message.answer_media_group(media)
                else:
                    # Одиночный медиафайл
                    media_type, file_id = media_entries[0].split(":")
                    if file_id:
                        if media_type == "photo":
                            await message.answer_photo(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                        elif media_type == "video":
                            await message.answer_video(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                        elif media_type == "document":
                            await message.answer_document(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                        elif media_type == "audio":
                            await message.answer_audio(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                        elif media_type == "text":
                            await message.answer(button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
    else:
        return
    
@router.callback_query(F.data.startswith("inline_button_"))
async def handle_inline_button_click(callback_query: CallbackQuery):
    # Извлечение ID кнопки из callback_data
    button_id = int(callback_query.data.split("_")[-1])

    # Получение информации о кнопке из базы данных
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()
        
        # Получение прикрепленных кнопок
        result_attached = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.linked_button_id == button_id)
        )
        attached_buttons = result_attached.scalars().all()

    if not button:
        await callback_query.answer("Кнопка не найдена.", show_alert=True)
        return

    keyboard = None
    if attached_buttons:
        # Определяем тип первой кнопки
        first_button_type = attached_buttons[0].button_type

        if first_button_type == "inline":
            keyboard = InlineKeyboardBuilder()
            for i in range(0, len(attached_buttons), 2):
                # Берем по 2 кнопки
                pair = attached_buttons[i:i + 2]
                keyboard.row(
                    *(
                        InlineKeyboardButton(
                            text=attached_button.button_text,
                            url=attached_button.reply_message
                        ) if attached_button.action_type == "link" else InlineKeyboardButton(
                            text=attached_button.button_text,
                            callback_data=f"inline_button_{attached_button.id}"
                        ) for attached_button in pair
                    )
                )
            keyboard = keyboard.as_markup()

        elif first_button_type == "regular":
            keyboard = ReplyKeyboardBuilder()
            for i in range(0, len(attached_buttons), 2):
                # Берем по 2 кнопки
                pair = attached_buttons[i:i + 2]
                keyboard.row(
                    *(KeyboardButton(text=attached_button.button_text) for attached_button in pair)
                )
            keyboard = keyboard.as_markup(resize_keyboard=True)
    
    # Обработка действий кнопки в зависимости от её типа
    if button.action_type == "send_new":
        # Отправка нового сообщения
        if button.file_id:
            # Если привязаны медиафайлы
            media_entries = button.file_id.split(",")
            if len(media_entries) > 1:
                # Медиагруппа
                media_group = []
                for entry in media_entries:
                    media_type, file_id = entry.split(":")
                    if media_type == "photo":
                        media_group.append(InputMediaPhoto(media=file_id, caption=button.reply_message, parse_mode="Markdown"))
                    elif media_type == "video":
                        media_group.append(InputMediaVideo(media=file_id, caption=button.reply_message, parse_mode="Markdown"))
                    elif media_type == "document":
                        media_group.append(InputMediaDocument(media=file_id, caption=button.reply_message, parse_mode="Markdown"))
                    elif media_type == "audio":
                        media_group.append(InputMediaAudio(media=file_id, caption=button.reply_message, parse_mode="Markdown"))
                await callback_query.message.answer_media_group(media_group)
            else:
                # Одиночный файл
                media_type, file_id = media_entries[0].split(":")
                if media_type == "photo":
                    await callback_query.message.answer_photo(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "video":
                    await callback_query.message.answer_video(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "document":
                    await callback_query.message.answer_document(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "audio":
                    await callback_query.message.answer_audio(file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "text":
                    await callback_query.message.answer(button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
        else:
            # Просто текстовое сообщение
            await callback_query.message.answer(button.reply_message, parse_mode="Markdown")

    elif button.action_type == "replace":
        if button.file_id:
            # Если привязаны медиафайлы
            media_entries = button.file_id.split(",")
            if len(media_entries) > 1:
                # Медиагруппа
                media_group = []
                for i, entry in enumerate(media_entries):
                    media_type, file_id = entry.split(":")
                    if media_type == "photo":
                        media_group.append(
                            InputMediaPhoto(
                                media=file_id,
                                caption=button.reply_message if i == 0 else None, parse_mode="Markdown"
                            )
                        )
                    elif media_type == "video":
                        media_group.append(
                            InputMediaVideo(
                                media=file_id,
                                caption=button.reply_message if i == 0 else None, parse_mode="Markdown"
                            )
                        )
                    elif media_type == "document":
                        media_group.append(
                            InputMediaDocument(
                                media=file_id,
                                caption=button.reply_message if i == 0 else None, parse_mode="Markdown"
                            )
                        )
                    elif media_type == "audio":
                        media_group.append(
                            InputMediaAudio(
                                media=file_id,
                                caption=button.reply_message if i == 0 else None, parse_mode="Markdown"
                            )
                        )

                # Удаление текущего сообщения
                try:
                    await callback_query.message.delete()
                except Exception as e:
                    print(f"Ошибка при удалении сообщения: {e}")

                # Отправка новой медиагруппы
                await callback_query.message.answer_media_group(media_group)
            else:
                # Одиночный файл
                media_type, file_id = media_entries[0].split(":")
                if media_type == "photo":
                    try:
                        await callback_query.message.edit_media(
                            InputMediaPhoto(media=file_id, caption=button.reply_message, parse_mode="Markdown"),
                            reply_markup=keyboard
                        )
                    except Exception:
                        await callback_query.message.delete()
                        await callback_query.message.answer_photo(photo=file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "video":
                    try:
                        await callback_query.message.edit_media(
                            InputMediaVideo(media=file_id, caption=button.reply_message, parse_mode="Markdown"),
                            reply_markup=keyboard
                        )
                    except Exception:
                        await callback_query.message.delete()
                        await callback_query.message.answer_video(photo=file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "document":
                    try:
                        await callback_query.message.edit_media(
                            InputMediaDocument(media=file_id, caption=button.reply_message, parse_mode="Markdown"),
                            reply_markup=keyboard
                        )
                    except Exception:
                        await callback_query.message.delete()
                        await callback_query.message.answer_document(photo=file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "audio":
                    try:
                        await callback_query.message.edit_media(
                            InputMediaAudio(media=file_id, caption=button.reply_message, parse_mode="Markdown"),
                            reply_markup=keyboard
                        )
                    except Exception:
                        await callback_query.message.delete()
                        await callback_query.message.answer_audio(photo=file_id, caption=button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                elif media_type == "text":
                    try:
                        await callback_query.message.edit_text(button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
                    except Exception:
                        await callback_query.message.delete()
                        await callback_query.message.answer(button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
        else:
            # Замена текста
            await callback_query.message.edit_text(button.reply_message, parse_mode="Markdown", reply_markup=keyboard)
    await callback_query.answer()

async def setup_and_run_bot(bot_token: str):
    """
    Настройка бота через webhook.
    """
    # Создаем объект Bot
    bot = Bot(token=bot_token)
    
    # Настройка webhook
    webhook_path = f"/bot/{bot_token}"
    webhook_url = f"{WEBHOOK_TUNNEL_URL}{webhook_path}"

    # Проверяем текущий webhook и обновляем его при необходимости
    current_webhook_info = await bot.get_webhook_info()
    if current_webhook_info.url != webhook_url:
        await bot.set_webhook(url=webhook_url, drop_pending_updates = True, allowed_updates=["message", "inline_query", "chat_member", "callback_query", "chat_member", "chat_join_request", "my_chat_member"])
    
    commands = [
        types.BotCommand(command="/start", description="Начать"),
        types.BotCommand(command="/settings", description="Настройки")
    ]
    await bot.set_my_commands(commands)

    # Закрываем сессию после настройки webhook
    await bot.session.close()

# Функция для обработки добавления бота в базу данных и его запуска
async def add_and_run_new_bot(token: str, bot_username: str, user_id: int):
    """
    Добавляет нового бота и запускает его, если лимит включённых ботов не превышен.

    Возвращает:
    True, если бот успешно включён.
    False, если бот добавлен, но не включён.
    """
    async with await get_db_session() as session:
        # Проверяем, существует ли бот с таким токеном в базе
        result = await session.execute(select(UserBot).filter(UserBot.bot_token == token))
        bot_entry = result.scalars().first()
        
        if bot_entry:
            # Если бот уже существует, обновляем user_id
            try:
                await session.execute(
                    update(UserBot)
                    .where(UserBot.bot_token == token)
                    .values(user_id=user_id)
                )
                await session.commit()
                print(f"User ID для бота @{bot_username} был обновлен на {user_id}.")
                return True
            except IntegrityError:
                await session.rollback()
                print("Ошибка при обновлении записи.")
                return False
        else:
            # Подсчитываем количество включённых ботов
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

            # Ограничение на 3 активных бота
            bot_limit = 3 + active_subscription_count

            # Проверяем, можно ли включить бота
            can_activate = active_bots_count < bot_limit

            # Добавляем нового бота
            new_bot_entry = UserBot(
                user_id=user_id,
                bot_token=token,
                bot_username=bot_username,
                is_started=can_activate  # Включаем бота только если не превышен лимит
            )
            session.add(new_bot_entry)

            try:
                await session.commit()
                print(f"Новый бот @{bot_username} был добавлен в базу данных.")
            except IntegrityError:
                await session.rollback()
                print("Ошибка при добавлении нового бота.")
                return False

    # Запускаем бота только если лимит не превышен
    if can_activate:
        await setup_and_run_bot(token)
        return True

    return False


