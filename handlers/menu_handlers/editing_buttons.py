from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete
from sqlalchemy.future import select
from db import UserBot, get_db_session, increment_sent_messages_count, increment_replied_messages_count, BotMenuButton, get_lang
from dict import MESSAGES
from config import media_group_tasks, media_groups
import asyncio
from handlers.menu_handlers.adding_button import BotSettingsStates

router = Router(name=__name__)

@router.callback_query(F.data.startswith("button_"))
async def button_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    button_id = int(callback_query.data.split("_")[-1])

    # Получение информации о кнопке из базы данных
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()

    if not button:
        await callback_query.message.answer(MESSAGES[lang]["button_not_found"])
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
        reply_markup=keyboard.as_markup()
    )
    await state.update_data(previous_state=BotSettingsStates.main_menu)
    await callback_query.message.delete()
    await callback_query.answer()

@router.callback_query(F.data.startswith("edit_button_"))
async def edit_button_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    button_id = int(callback_query.data.split("_")[-1])
    
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
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(BotSettingsStates.editing_button)
    await state.update_data(previous_state=BotSettingsStates.button)
    await callback_query.answer()

@router.callback_query(F.data.startswith("dettach_start_"))
async def dettach_button_start(callback_query: CallbackQuery, state: FSMContext):
    button_id = int(callback_query.data.split("_")[-1])
    
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()
        
        button.linked_to_start = False
        await session.commit()
        
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
        reply_markup=keyboard.as_markup()
    )
    await state.update_data(previous_state=BotSettingsStates.button)
    await callback_query.answer()

@router.callback_query(F.data.startswith("attach_start_"))
async def attach_button_to_start(callback_query: CallbackQuery, state: FSMContext):
    button_id = int(callback_query.data.split("_")[-1])
    
    data = await state.get_data()
    from_adding_button = data.get("from_adding_button")
    
    bot_token = callback_query.bot.token
    
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()
        
        bot_result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
        bot_entry = bot_result.scalars().first()

        if button:
            # Проверка кнопок, привязанных к старту
            result_start_buttons = await session.execute(
                select(BotMenuButton).filter(
                    BotMenuButton.bot_token == button.bot_token,
                    BotMenuButton.linked_to_start == True
                )
            )
            start_buttons = result_start_buttons.scalars().all()

            # Определение, привязывать ли новую кнопку к старту
            linked_to_start = False
            if start_buttons:
                for start_button in start_buttons:
                        if start_button.button_type == button.button_type:
                            linked_to_start = True
                            break        
            else:
                # Если нет кнопок, привязанных к старту, привязываем новую кнопку
                linked_to_start = True

            button.linked_to_start = linked_to_start
            if not linked_to_start:
                await callback_query.answer("К старту могут быть привязаны кнопки только одного и того же вида Inline или Обычные")
                return
            await session.commit()
            
    keyboard = InlineKeyboardBuilder()
    
    if from_adding_button:
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["back"], 
                callback_data="back"
            )
        )
        
        await callback_query.message.edit_text(
            MESSAGES[lang]["button_added"],
            reply_markup=keyboard.as_markup()
        )
        await state.clear()
        await state.update_data(previous_state = BotSettingsStates.bot_settings_menu, bot_id = bot_entry.id)
    # Создание инлайн-клавиатуры с действиями
    else:
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
            reply_markup=keyboard.as_markup()
        )
        await state.update_data(previous_state=BotSettingsStates.button)
        await callback_query.answer()

@router.callback_query(F.data.startswith("attach_button_"))
async def attach_button_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    button_id = int(callback_query.data.split("_")[-1])

    await state.update_data(attach_button_id=button_id)

    # Получаем информацию о текущей кнопке
    async with await get_db_session() as session:
        result_current = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.id == button_id)
        )
        current_button = result_current.scalars().first()

        if not current_button:
            await callback_query.message.edit_text(MESSAGES[lang]["current_button_not_found"])
            await callback_query.answer()
            return

        # Получаем список кнопок данного бота
        result_buttons = await session.execute(
            select(BotMenuButton).filter(
                BotMenuButton.bot_token == callback_query.message.bot.token,
                BotMenuButton.action_type != "link"  # Исключаем кнопки с действием "link"
            )
        )
        all_buttons = result_buttons.scalars().all()

    # Отбираем кнопки, к которым можно прикрепить текущую кнопку
    valid_buttons = []
    for button in all_buttons:
        if button.id != button_id:
            if len(button.file_id.split(",")) == 1:
                async with await get_db_session() as session:
                    result_linked = await session.execute(
                        select(BotMenuButton).filter(BotMenuButton.linked_button_id == button.id)
                    )
                    linked_buttons = result_linked.scalars().all()

                if all(linked_button.button_type == current_button.button_type for linked_button in linked_buttons):
                    if not (current_button.button_type == "regular" and button.action_type == "replace"):
                        if len(button.file_id.split(",")) <= 1:
                            valid_buttons.append(button)

    # Создание инлайн-клавиатуры с кнопками для выбора
    keyboard = InlineKeyboardBuilder()
    for button in valid_buttons:
        keyboard.add(
            InlineKeyboardButton(text=button.button_text, callback_data=f"attach_to_{button.id}")
        )
    
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["detach_button"], callback_data=f"detach_button_{button_id}"))
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    await callback_query.message.edit_text(
        MESSAGES[lang]["attach_button_instructions"],
        reply_markup=keyboard.as_markup()
    )
    await state.update_data(previous_state = BotSettingsStates.editing_button)
    await callback_query.answer()

@router.callback_query(F.data.startswith("attach_to_"))
async def finalize_attachment(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    attach_button_id = data.get("attach_button_id")
    from_adding_button = data.get("from_adding_button")
    target_button_id = int(callback_query.data.split("_")[-1])
    
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    async with await get_db_session() as session:
        result_attach = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == attach_button_id))
        attach_button = result_attach.scalars().first()

        result_target = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == target_button_id))
        target_button = result_target.scalars().first()
        
        bot_result = await session.execute(select(UserBot).filter(UserBot.bot_token == callback_query.bot.token))
        bot_entry = bot_result.scalars().first()

        if not attach_button or not target_button:
            await callback_query.message.edit_text("Ошибка: кнопка не найдена.")
            await callback_query.answer()
            return

        # Проверка привязанных кнопок к целевой кнопке
        result_linked_buttons = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.linked_button_id == target_button.id)
        )
        linked_buttons = result_linked_buttons.scalars().all()

        # Проверка типов привязанных кнопок
        if linked_buttons:
            for linked_button in linked_buttons:
                if linked_button.button_type != attach_button.button_type:
                    await callback_query.message.edit_text("Нельзя привязывать кнопки разных типов.")
                    await callback_query.answer()
                    return

        # Добавляем связь между кнопками
        attach_button.linked_button_id = target_button.id
        attach_button.linked_to_start = False
        await session.commit()

    await state.clear()
    
    keyboard = InlineKeyboardBuilder()
    
    if from_adding_button:
        keyboard.row(
            InlineKeyboardButton(
                text=MESSAGES[lang]["back"], 
                callback_data="back"
            )
        )
        
        await callback_query.message.edit_text(
            MESSAGES[lang]["button_added"],
            reply_markup=keyboard.as_markup()
        )
        await state.update_data(previous_state = BotSettingsStates.bot_settings_menu, bot_id = bot_entry.id)
    else:
        await show_updated_button(attach_button_id, state, callback_query.message, lang)
        await callback_query.message.delete()
        await callback_query.answer()

@router.callback_query(F.data.startswith("detach_button_"))
async def detach_button_callback(callback_query: CallbackQuery, state: FSMContext):
    button_id = int(callback_query.data.split("_")[-1])
    
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()

        if not button:
            await callback_query.message.edit_text("Ошибка: кнопка не найдена.")
            await callback_query.answer()
            return

        # Убираем привязку кнопки
        button.linked_button_id = None
        button.linked_to_start = False
        await session.commit()
        
    await state.clear()
    await show_updated_button(button_id, state, callback_query.message, lang)
    await callback_query.message.delete()
    await callback_query.answer()

@router.callback_query(F.data.startswith("rename_button_"))
async def rename_button_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    button_id = int(callback_query.data.split("_")[-1])

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    
    await state.update_data(rename_button_id=button_id)
    await callback_query.message.edit_text(
        MESSAGES[lang]["enter_new_button_name"],
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(BotSettingsStates.editing_button_text)
    await state.update_data(previous_state = BotSettingsStates.editing_button)
    await callback_query.answer()

@router.message(BotSettingsStates.editing_button_text)
async def update_button_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    
    data = await state.get_data()
    button_id = data.get("rename_button_id")
    new_name = message.text[:35]

    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()

        if button:
            button.button_text = new_name
            await session.commit()
            await state.clear()
            await show_updated_button(button_id, state, message, lang)
        else:
            await message.answer("Ошибка: кнопка не найдена.")

@router.callback_query(F.data.startswith("update_content_"))
async def update_content_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    button_id = int(callback_query.data.split("_")[-1])

    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))
    
    await state.update_data(update_content_button_id=button_id)
    await callback_query.message.edit_text(
        MESSAGES[lang]["send_new_content"],
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(BotSettingsStates.editing_button_reply_message)
    await state.update_data(previous_state = BotSettingsStates.editing_button)
    await callback_query.answer()

@router.message(BotSettingsStates.editing_button_reply_message)
async def process_message_update(message: Message, state: FSMContext):
    """
    Обработка сообщения: одиночное или медиагруппа.
    """
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    
    data = await state.get_data()
    button_id = data.get("update_content_button_id")

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
            process_media_group_update(media_group_id, button_id, state, message, lang)
        )
    else:
        # Одиночное сообщение
        await process_single_message_update(message, button_id, state, lang)

@router.callback_query(F.data.startswith("delete_button_"))
async def delete_button_callback(callback_query: CallbackQuery, state: FSMContext):
    button_id = int(callback_query.data.split("_")[-1])

    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    
    # Удаление связанных сообщений
    data = await state.get_data()
    sent_message_ids = data.get("sent_message_ids", [])
    for sent_message_id in sent_message_ids:
        try:
            await callback_query.message.bot.delete_message(callback_query.message.chat.id, sent_message_id)
        except Exception as e:
            print(f"Ошибка при удалении сообщения {sent_message_id}: {e}")

    # Удаление кнопки из базы данных
    async with await get_db_session() as session:
        # Обновление записей, которые ссылаются на удаляемую кнопку
        await session.execute(
            update(BotMenuButton).where(BotMenuButton.linked_button_id == button_id).values(linked_button_id=None)
        )
        await session.commit()

        # Удаление кнопки
        await session.execute(
            delete(BotMenuButton).where(BotMenuButton.id == button_id)
        )
        await session.commit()

    # Перестроение меню
    bot_token = callback_query.bot.token
    
    # Извлечение текущего бота пользователя из базы данных
    async with await get_db_session() as session:
        result_bot = await session.execute(
            select(UserBot).filter(UserBot.bot_token == bot_token)
        )
        user_bot = result_bot.scalars().first()  # Извлекаем бота
        
        if not user_bot:
            await callback_query.message.answer("Бот не найден в системе.")
            return

    # Извлечение обновлённого списка кнопок
    async with await get_db_session() as session:
        result = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.bot_token == bot_token)
        )
        buttons = result.scalars().all()

    # Создание инлайн-кнопок для обновлённого меню
    keyboard = InlineKeyboardBuilder()

    for i in range(0, len(buttons), 2):
        pair = buttons[i:i+2]  # Берем по 2 кнопки
        keyboard.row(
            *(InlineKeyboardButton(text=button.button_text, callback_data=f"button_{button.id}") for button in pair)
        )

    keyboard.row(InlineKeyboardButton(text="➕", callback_data=f"add_button_{user_bot.id}"))

    # Отправка обновлённого меню
    await callback_query.message.edit_text(
        MESSAGES[lang]["main_menu_description"],
        reply_markup=keyboard.as_markup()
    )
    await callback_query.answer()

@router.callback_query(F.data.startswith("link_to_command_"))
async def link_to_command_callback(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки для привязки команды к кнопке.
    """
    lang = await get_lang(callback_query.from_user.id)
    button_id = int(callback_query.data.split("_")[-1])

    # Сохраняем ID кнопки в состоянии
    await state.update_data(button_id=button_id)

    # Создаем клавиатуру с кнопкой «Назад»
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    # Отправляем сообщение с инструкцией
    await callback_query.message.edit_text(
        MESSAGES[lang]["link_to_command_instruction"],
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(BotSettingsStates.awaiting_command)
    await state.update_data(previous_state = BotSettingsStates.editing_button)
    await callback_query.answer()

@router.message(BotSettingsStates.awaiting_command)
async def handle_command_input(message: Message, state: FSMContext):
    """
    Обработка команды, которую пользователь хочет привязать к кнопке.
    """
    user_id = message.from_user.id
    lang = await get_lang(user_id)
    command = message.text.strip()
    data = await state.get_data()
    button_id = data.get("button_id")
    from_adding_button = data.get("from_adding_button")

    # Проверяем, чтобы команда не была /start
    if command == "/start":
        await message.answer(MESSAGES[lang]["command_not_allowed"])
        return

    async with await get_db_session() as session:
        # Проверяем, существует ли уже кнопка с такой командой
        existing_button_result = await session.execute(
            select(BotMenuButton).filter(BotMenuButton.command == command)
        )
        existing_button = existing_button_result.scalars().first()

        # Получаем текущую кнопку по ID
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()
        
        bot_result = await session.execute(select(UserBot).filter(UserBot.bot_token == message.bot.token))
        bot_entry = bot_result.scalars().first()

        if not button:
            await message.answer(MESSAGES[lang]["button_not_found"])
            await state.clear()
            return

        # Проверяем типы кнопок, если команда уже привязана
        if existing_button and existing_button.button_type != button.button_type:
            await message.answer(MESSAGES[lang]["command_type_mismatch"])
            return

        # Сохраняем команду в столбец `command`
        button.command = command
        await session.commit()
    
    keyboard = InlineKeyboardBuilder()
    
    if from_adding_button:
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
        await state.update_data(previous_state = BotSettingsStates.bot_settings_menu, bot_id = bot_entry.id)
    else:
        await message.answer(MESSAGES[lang]["command_saved"].format(command=command))
        await state.clear()
        await show_updated_button(button_id, state, message, lang)
    
async def process_media_group_update(media_group_id: str, button_id: int, state: FSMContext, message: Message, lang):
    """
    Завершение обработки медиагруппы и обновление кнопки в базе данных.
    """
    await asyncio.sleep(1.5)
    
    media_group_data = media_groups.pop(media_group_id, None)
    if not media_group_data:
        return

    messages = media_group_data["messages"]
    caption_text = media_group_data["caption"]

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

    # Обновление кнопки в базе данных
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()

        if button:
            button.file_id = ",".join(media_entries)
            button.reply_message = caption_text
            await session.commit()

    await state.clear()
    await show_updated_button(button_id, state, message, lang)

async def process_single_message_update(message: Message, button_id: int, state: FSMContext, lang):
    """
    Обработка одиночного сообщения и обновление кнопки в базе данных.
    """
    file_id = None
    if message.photo:
        file_id = f"photo:{message.photo[-1].file_id}"
    elif message.video:
        file_id = f"video:{message.video.file_id}"
    elif message.document:
        file_id = f"document:{message.document.file_id}"
    elif message.audio:
        file_id = f"audio:{message.audio.file_id}"
    else:
        file_id = "text:None"

    # Обновление кнопки в базе данных
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()

        if button:
            button.file_id = file_id
            button.reply_message = message.text if button.action_type == "link" else message.md_text.replace("\\", "")
            await session.commit()

    await state.clear()
    await show_updated_button(button_id, state, message, lang)

async def show_updated_button(button_id: int, state: FSMContext, message: Message, lang):
    """
    Отображение обновленного содержимого кнопки и её меню.
    """
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.id == button_id))
        button = result.scalars().first()

    # Создание меню для редактирования или удаления кнопки
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["edit_button"], callback_data=f"edit_button_{button.id}"),
        InlineKeyboardButton(text=MESSAGES[lang]["delete_button"], callback_data=f"delete_button_{button.id}")
    )
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

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
            sent_messages = await message.answer_media_group(media_group)
            sent_message_ids = [msg.message_id for msg in sent_messages]
        else:
            # Если это одиночный файл
            media_type, file_id = media_entries[0].split(":")
            if media_type == "photo":
                sent_message = await message.answer_photo(file_id, caption=button.reply_message, parse_mode="Markdown")
            elif media_type == "video":
                sent_message = await message.answer_video(file_id, caption=button.reply_message, parse_mode="Markdown")
            elif media_type == "document":
                sent_message = await message.answer_document(file_id, caption=button.reply_message, parse_mode="Markdown")
            elif media_type == "audio":
                sent_message = await message.answer_audio(file_id, caption=button.reply_message, parse_mode="Markdown")
            elif media_type == "text":
                sent_message = await message.answer(button.reply_message, parse_mode="Markdown")
            if sent_message:
                sent_message_ids.append(sent_message.message_id)

    if sent_message_ids:
        await state.update_data(sent_message_ids=sent_message_ids)

    await message.answer(
        MESSAGES[lang]["button_display_message"].format(button_text=button.button_text),
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(None)
    await state.update_data(previous_state=BotSettingsStates.main_menu)