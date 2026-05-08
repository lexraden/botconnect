from aiogram import Router, types, Bot, types , F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.future import select
from sqlalchemy.sql import exists, and_
from db import UserBot, User, BotSubscription, get_lang, get_db_session
from handlers.bot_settings import MainBotSettingsStates
from config import admins
from datetime import datetime
from dict import MESSAGES
import asyncio

router = Router(name=__name__)

class AdSendingStates(StatesGroup):
    awaiting_message = State()
    awaiting_url = State()
    confirm_sending = State()
    
class AdProcessStates(StatesGroup):
    awaiting_message = State()


@router.message(Command("send_ad"))
async def send_ad_command(message: Message, state: FSMContext):
    """
    Обработчик команды /send_ad.
    """
    if message.from_user.id in admins:
        await message.answer("Пожалуйста, пришлите пост для рассылки.")
        await state.set_state(AdSendingStates.awaiting_message)
    else:
        return

@router.message(AdSendingStates.awaiting_message)
async def process_ad_content(message: Message, state: FSMContext):
    """
    Обработка содержимого поста для рассылки.
    """
    ad_content = message.md_text
    ad_content = ad_content.replace("\\", "")
    
    # Сохраняем содержимое поста
    await state.update_data(ad_content=ad_content)
    
    if message.reply_markup:
        await state.update_data(sending_keyboard = message.reply_markup)
        
        # Подтверждение отправки
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить", callback_data="send_ad_confirm")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_ad")]
            ]
        )
    
        await message.answer(
            "Вы уверены, что хотите отправить рассылку?\n\n" + ad_content,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(AdSendingStates.confirm_sending)
    
    else:
        if not ad_content:
            await message.answer("Ошибка: Пожалуйста, отправьте текст или медиа с подписью.")
            return
        
        # Создаем клавиатуру для выбора: добавить ссылку или отправить без нее
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(text="Отправить без ссылки", callback_data="send_without_url")
        )
        
        await message.answer(
            "Введите ссылку для поста",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(AdSendingStates.awaiting_url)

@router.callback_query(F.data == "send_without_url", AdSendingStates.awaiting_url)
async def process_ad_no_url(callback_query: CallbackQuery, state: FSMContext):
    """
    Отправка поста без ссылки.
    """
    data = await state.get_data()
    ad_content = data.get("ad_content")
    
    # Подтверждение отправки
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="send_ad_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_ad")]
        ]
    )
    
    await callback_query.message.answer(
        "Вы уверены, что хотите отправить рассылку?\n\n" + ad_content,
        reply_markup=keyboard
    )
    await state.set_state(AdSendingStates.confirm_sending)


@router.message(AdSendingStates.awaiting_url)
async def process_ad_url(message: Message, state: FSMContext):
    """
    Обработка ссылки для поста.
    """
    url_text = message.text
    
    # Проверяем валидность ссылки (простая проверка на наличие http/https)
    if not url_text.startswith(("http://", "https://")):
        await message.answer("Ошибка: Некорректная ссылка. Пожалуйста, отправьте корректную ссылку.")
        return
    
    # Сохраняем ссылку
    await state.update_data(url_text=url_text)
    
    data = await state.get_data()
    ad_content = data.get("ad_content")
    
    # Подтверждение отправки
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="send_ad_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_ad")]
        ]
    )
    
    await message.answer(
        "Вы уверены, что хотите отправить рассылку?\n\n" + ad_content + f"\n\nСсылка: {url_text}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(AdSendingStates.confirm_sending)

@router.callback_query(F.data == "send_ad_confirm")
async def confirm_ad_sending(callback_query: CallbackQuery, state: FSMContext):
    """
    Подтверждение отправки рассылки.
    """
    data = await state.get_data()
    ad_content = data.get("ad_content")
    url_text = data.get("url_text", None)
    sending_keyboard = data.get("sending_keyboard", None)

    if not ad_content:
        lang = await get_lang(callback_query.from_user.id)
        await callback_query.message.edit_text(MESSAGES[lang]["ad_content_missing"])
        await state.clear()
        return

    async with await get_db_session() as session:
        # Получаем всех ботов без подписки
        bots_result = await session.execute(
            select(UserBot).filter(
                ~exists().where(
                    and_(
                        BotSubscription.bot_id == UserBot.id,
                        BotSubscription.end_date > datetime.now()
                    )
                )
            )
        )
        bots = bots_result.scalars().all()

    # Создаём задачи для рассылки от каждого бота
    tasks = []
    for bot_entry in bots:
        tasks.append(asyncio.create_task(send_ad_to_users(bot_entry, ad_content, url_text, sending_keyboard)))

    # Запускаем рассылку параллельно
    await asyncio.gather(*tasks)

    lang = await get_lang(callback_query.from_user.id)
    await callback_query.message.edit_text(MESSAGES[lang]["ad_sent_success"])
    await state.clear()

async def send_ad_to_users(bot_entry: UserBot, ad_content: str, url_text: str = None, sending_keyboard: InlineKeyboardMarkup = None):
    """
    Функция отправки рассылки от конкретного бота.
    """
    bot = Bot(token=bot_entry.bot_token)

    async with await get_db_session() as session:
        users_result = await session.execute(
            select(User).where(User.bot_token == bot_entry.bot_token)
        )
        users = users_result.scalars().all()
    if url_text:
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="Перейти по ссылке", url=url_text))
        keyboard = keyboard.as_markup()
    elif sending_keyboard:
        keyboard = sending_keyboard
    else:
        keyboard = None
    
    for user in users:
        try:
            await bot.send_message(chat_id=user.user_id, text=ad_content, parse_mode="Markdown", reply_markup=keyboard)
            await asyncio.sleep(0.034)  # Задержка для предотвращения rate limit
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

    await bot.session.close()

@router.callback_query(F.data == "cancel_ad")
async def cancel_ad_sending(callback_query: CallbackQuery, state: FSMContext):
    """
    Отмена отправки рассылки.
    """
    await callback_query.message.edit_text("Рассылка отменена.")
    await state.clear()

@router.callback_query(F.data == "ads")
async def ads_handler(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработка нажатия на кнопку "Реклама".
    """
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)

    text = (
        MESSAGES[lang]["ads_message"]
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back"))

    await callback_query.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
    await state.update_data(previous_state = MainBotSettingsStates.main_menu)
    await state.set_state(AdProcessStates.awaiting_message)
    await callback_query.answer()
    
@router.message(AdProcessStates.awaiting_message)
async def receive_ad_post(message: Message, state: FSMContext):
    """
    Обработчик для получения текста рекламного поста и пересылки его администратору.
    """
    admin_id = admins[0]  # Замените на реальный ID администратора
    lang = await get_lang(message.from_user.id)

    # Проверяем, содержит ли сообщение текст
    if not message.md_text.strip():
        await message.reply(MESSAGES[lang]["empty_ad_post"])
        return

    try:
        # Пересылаем сообщение администратору
        await message.forward(chat_id=admin_id)

        # Уведомляем пользователя об успешной отправке
        await message.reply(MESSAGES[lang]["ad_post_received"])
        
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
        
        await message.answer(MESSAGES[lang]["start_message"], parse_mode="Markdown", reply_markup=keyboard)
        
        await state.clear()
        
    except Exception:
        await message.reply(MESSAGES[lang]["ad_post_error"])
        
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
        
        await message.answer(MESSAGES[lang]["start_message"], parse_mode="Markdown", reply_markup=keyboard)
    
    await state.clear()
