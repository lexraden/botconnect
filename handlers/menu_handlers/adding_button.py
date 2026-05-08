from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete, text
from sqlalchemy.future import select
from db import UserBot, get_db_session, increment_sent_messages_count, increment_replied_messages_count, BotMenuButton, get_lang
from dict import MESSAGES
from config import media_group_tasks, media_groups
import asyncio

class BotSettingsStates(StatesGroup):
    bot_settings_menu = State()
    main_menu = State()
    button = State()
    editing_button = State()
    editing_button_text = State()
    editing_button_reply_message = State()
    adding_button = State()
    choosing_inline_type = State()
    waiting_for_button_text = State()
    waiting_for_reply_message = State()
    awaiting_command = State()
    editing_greeting = State()

router = Router(name=__name__)

@router.callback_query(F.data.startswith("add_button_"))
async def add_button_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    bot_id = int(callback_query.data.split("_")[-1])

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
    await state.update_data(bot_id=bot_id, previous_state=BotSettingsStates.main_menu)
    await callback_query.answer()

@router.callback_query(F.data.startswith("add_regular_button_"))
async def add_regular_button_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    bot_id = int(callback_query.data.split("_")[-1])
    await state.update_data(
        button_type="regular", 
        action_type="send_new", 
        bot_id=bot_id, 
        previous_state=BotSettingsStates.adding_button
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    await callback_query.message.edit_text(
        MESSAGES[lang]["enter_button_name"],
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(BotSettingsStates.waiting_for_button_text)
    await callback_query.answer()

@router.callback_query(F.data.startswith("add_inline_button_"))
async def inline_button_type_selection(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    bot_id = int(callback_query.data.split("_")[-1])

    # Предлагаем пользователю выбрать тип inline кнопки
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
        reply_markup=keyboard.as_markup()
    )
    await state.update_data(previous_state=BotSettingsStates.adding_button)
    await callback_query.answer()

@router.callback_query(F.data.startswith("set_inline_type_link_"))
async def set_inline_type_link(callback_query: CallbackQuery, state: FSMContext):
    bot_id = int(callback_query.data.split("_")[-1])
    lang = await get_lang(callback_query.from_user.id)
    await state.update_data(bot_id=bot_id, button_type="inline", action_type = "link", previous_state = BotSettingsStates.choosing_inline_type)
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    await callback_query.message.edit_text(MESSAGES[lang]["enter_button_name"], reply_markup=keyboard.as_markup())
    await state.set_state(BotSettingsStates.waiting_for_button_text)
    await callback_query.answer()

@router.callback_query(F.data.startswith("set_inline_type_replace_"))
async def set_inline_type_replace(callback_query: CallbackQuery, state: FSMContext):
    bot_id = int(callback_query.data.split("_")[-1])
    lang = await get_lang(callback_query.from_user.id)
    await state.update_data(bot_id=bot_id, button_type="inline", action_type = "replace", previous_state = BotSettingsStates.choosing_inline_type)
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    await callback_query.message.edit_text(MESSAGES[lang]["enter_button_name"], reply_markup=keyboard.as_markup())
    await state.set_state(BotSettingsStates.waiting_for_button_text)
    await callback_query.answer()

@router.callback_query(F.data.startswith("set_inline_type_new_"))
async def set_inline_type_new(callback_query: CallbackQuery, state: FSMContext):
    bot_id = int(callback_query.data.split("_")[-1])
    lang = await get_lang(callback_query.from_user.id)
    await state.update_data(bot_id=bot_id, button_type="inline", action_type = "send_new", previous_state = BotSettingsStates.choosing_inline_type)
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    await callback_query.message.edit_text(MESSAGES[lang]["enter_button_name"], reply_markup=keyboard.as_markup())
    await state.set_state(BotSettingsStates.waiting_for_button_text)
    await callback_query.answer()

@router.message(BotSettingsStates.waiting_for_button_text)
async def set_button_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    
    data = await state.get_data()
    action_type = data.get("action_type")
    
    button_text = message.text[:35]
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=MESSAGES[lang]["back"], 
            callback_data="back"
        )
    )
    await message.answer(
        MESSAGES[lang]["enter_reply_message"] if action_type != "link" else MESSAGES[lang]["enter_reply_link"], 
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(BotSettingsStates.waiting_for_reply_message)
    await state.update_data(button_text=button_text)

@router.message(BotSettingsStates.waiting_for_reply_message)
async def process_message(message: Message, state: FSMContext):
    """
    Обработка сообщения: одиночное или медиагруппа.
    """
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    data = await state.get_data()
    bot_id = data.get("bot_id")
    button_text = data.get("button_text")
    button_type = data.get("button_type")
    action_type = data.get("action_type")

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

        # Создаем новую задачу для обработки медиагруппы после задержки
        media_group_tasks[media_group_id] = asyncio.create_task(
            process_media_group(media_group_id, state, button_text, bot_id, message, button_type, action_type, lang)
        )
    else:
        # Одиночное сообщение
        await process_single_message(message, state, bot_id, button_text, button_type, action_type, lang)
        
async def process_media_group(media_group_id, state: FSMContext, button_text: str, bot_id: int, message: Message, button_type: str, action_type: str, lang):
    """
    Завершение обработки медиагруппы и сохранение в базу данных.
    """
    await asyncio.sleep(1.5)  # Ждём завершения загрузки медиагруппы
    
    if action_type == "link":
        await message.answer("Пожалуйста, пришлите ссылку для кнопки")
        await set_button_text(message, state)
        return

    data = await state.get_data()
    from_greeting = data.get("from_greeting", None)      
   
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
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()
        
        if bot_entry:
            if from_greeting:
                old_button_result = await session.execute(select(BotMenuButton).filter(BotMenuButton.from_greeting == True,
                                                                                       BotMenuButton.bot_token == bot_entry.bot_token))
                old_button = old_button_result.scalars().first()
                if old_button:
                    await session.delete(old_button)
                            
            new_button = BotMenuButton(
                bot_token=bot_entry.bot_token,
                button_text=button_text,
                reply_message=caption_text,
                file_id=",".join(media_entries),
                button_type=button_type,
                action_type=action_type,
                linked_to_start=True if from_greeting else False,
                from_greeting = True if from_greeting else False
            )
            session.add(new_button)
            await session.commit()
            await asyncio.sleep(0.5)
            await state.clear()
    
    # Перестроение меню
    bot_token = message.bot.token
    
    # Извлечение текущего бота пользователя из базы данных
    async with await get_db_session() as session:
        result_bot = await session.execute(
            select(UserBot).filter(UserBot.bot_token == bot_token)
        )
        user_bot = result_bot.scalars().first()  # Извлекаем бота
        
        if not user_bot:
            await message.answer(MESSAGES[lang]["bot_not_found"],)
            return

    # Извлечение обновлённого списка кнопок
    async with await get_db_session() as session:
        result = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.bot_token == bot_token,
                                         BotMenuButton.reply_message == caption_text,
                                         BotMenuButton.button_text == button_text)
        )
        button = result.scalars().first()

    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()
    if from_greeting:
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["back"], 
                callback_data="back"
            )
        )
        await message.answer(
            MESSAGES[lang]["button_added"],
            reply_markup=keyboard.as_markup()
        )
        await state.clear()
        await state.update_data(previous_state = BotSettingsStates.bot_settings_menu, bot_id = user_bot.id)
    else:
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["attach_button"], 
                callback_data=f"attach_button_{button.id}"
            )
        )
        if button.linked_to_start:
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["detach_start"], 
                    callback_data=f"dettach_start_{button.id}"
                )
            )    
        else:
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["attach_start"], 
                    callback_data=f"attach_start_{button.id}"
                )
            )
        keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["link_to_command"], 
                    callback_data=f"link_to_command_{button.id}"
                )
            )

        # Отправка обновлённого меню
        await message.answer(
            MESSAGES[lang]["where_to_attach"],
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(BotSettingsStates.main_menu)
        await state.update_data(button_id = button.id, from_adding_button = True)

async def process_single_message(message: Message, state: FSMContext, bot_id: int, button_text: str, button_type: str, action_type: str, lang):
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
    elif message.text:
        file_id = None
        media_type = "text"
    else:
        await message.answer("Этот тип сообщений не поддерживается.")
        return
    
    message_text = message.text if action_type=="link" else message.md_text.replace("\\", "")
    
    data = await state.get_data()
    from_greeting = data.get("from_greeting", None)
    
    # Сохранение в базу данных
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.id == bot_id))
        bot_entry = result.scalars().first()

        if bot_entry:
            if from_greeting:
                old_button_result = await session.execute(select(BotMenuButton).filter(BotMenuButton.from_greeting == True,
                                                                                       BotMenuButton.bot_token == bot_entry.bot_token))
                old_button = old_button_result.scalars().first()
                if old_button:
                    await session.delete(old_button)
                    
            new_button = BotMenuButton(
                bot_token=bot_entry.bot_token,
                button_text=button_text,
                reply_message=message_text,
                file_id=f"{media_type}:{file_id}",
                button_type=button_type,
                action_type=action_type,
                linked_to_start=True if from_greeting else False,
                from_greeting = True if from_greeting else False
            )
            session.add(new_button)
            await session.commit()

    # Перестроение меню
    bot_token = message.bot.token
    
    # Извлечение текущего бота пользователя из базы данных
    async with await get_db_session() as session:
        result_bot = await session.execute(
            select(UserBot).filter(UserBot.bot_token == bot_token)
        )
        user_bot = result_bot.scalars().first()  # Извлекаем бота
        
        if not user_bot:
            await message.answer(MESSAGES[lang]["bot_not_found"])
            return

    # Извлечение обновлённого списка кнопок
    async with await get_db_session() as session:
        result = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.bot_token == bot_token,
                                         BotMenuButton.reply_message == message_text,
                                         BotMenuButton.button_text == button_text)
        )
        button = result.scalars().first()

    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()
    
    data = await state.get_data()
    from_greeting = data.get("from_greeting", None)

    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()
    if from_greeting:
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["back"], 
                callback_data="back"
            )
        )
        await message.answer(
            MESSAGES[lang]["button_added"],
            reply_markup=keyboard.as_markup()
        )
        await state.clear()
        await state.update_data(previous_state = BotSettingsStates.bot_settings_menu, bot_id = user_bot.id)
    else:
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["attach_button"], 
                callback_data=f"attach_button_{button.id}"
            )
        )
        if button.linked_to_start:
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["detach_start"], 
                    callback_data=f"dettach_start_{button.id}"
                )
            )    
        else:
            keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["attach_start"], 
                    callback_data=f"attach_start_{button.id}"
                )
            )
        keyboard.row(
                InlineKeyboardButton(
                    text=MESSAGES[lang]["link_to_command"], 
                    callback_data=f"link_to_command_{button.id}"
                )
            )

        # Отправка обновлённого меню
        await message.answer(
            MESSAGES[lang]["where_to_attach"],
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(BotSettingsStates.main_menu)
        await state.update_data(button_id = button.id, from_adding_button = True)