from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.filters import Filter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, KeyboardButton, InlineKeyboardMarkup, InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete
from sqlalchemy.future import select
from db import UserBot, get_db_session, increment_sent_messages_count, increment_replied_messages_count, BotMenuButton, Mailing, User, get_lang, BotSubscription
from config import media_group_tasks, media_groups
from datetime import datetime
from handlers.menu_handlers.adding_button import BotSettingsStates
from handlers.menu_handlers.mailing import MailingStates
from handlers.bot_settings import MainBotSettingsStates
from handlers.subscription import PaymentStates, convert_to_crypto
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
            except Exception as e:
                print(f"Ошибка при удалении сообщения {sent_message_id}: {e}")
        
    if previous_state == MainBotSettingsStates.main_menu:
        user_id = callback_query.from_user.id
        lang = await get_lang(user_id)

        text = MESSAGES[lang]["start_message"]

        # Создание клавиатуры
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
        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
        await state.clear()
    
    elif previous_state == PaymentStates.choose_bot:
        user_id = callback_query.from_user.id
        lang = await get_lang(user_id)
        
        try:
            async with await get_db_session() as session:
                # Получаем список ботов, добавленных пользователем
                bots = await session.execute(
                    select(UserBot).filter(UserBot.user_id == user_id)
                )
                bots_list = bots.scalars().all()

            # Создаем inline-кнопки для выбора бота
            if bots_list:
                builder = InlineKeyboardBuilder()
                for bot in bots_list:
                    builder.add(
                        InlineKeyboardButton(
                            text=f"{bot.bot_username}",
                            callback_data=f"for_bot_subscription_{bot.id}"
                        )
                    )
                builder.row(InlineKeyboardButton(text=MESSAGES[lang]['back'], callback_data="back"))

                await callback_query.message.edit_text(
                    MESSAGES[lang]['subscription_bot'],
                    reply_markup=builder.as_markup()
                )
            else:
                await callback_query.message.edit_text(MESSAGES[lang]['no_bots'])
                await state.clear()
        except Exception as e:
            await callback_query.message.edit_text(MESSAGES[lang]['error_occurred'])
            await state.clear()
    
    elif previous_state == PaymentStates.choose_duration:
        user_telegram_id = callback_query.from_user.id
        lang = await get_lang(user_telegram_id)

        data = await state.get_data()
        bot_id = data.get("selected_bot_id")

        # Цены подписки
        prices_rub = {
            "subscription_1_month": (1, 299),
            "subscription_3_months": (3, 599),
            "subscription_6_months": (6, 999),
            "subscription_12_months": (12, 1499),
        }

        try:
            async with await get_db_session() as session:
                # Проверяем существование бота
                selected_bot = await session.get(UserBot, bot_id)
                if not selected_bot:
                    await callback_query.message.edit_text(MESSAGES[lang]['bot_not_found'], parse_mode='Markdown')
                    await state.clear()
                    return

                # Проверка наличия активной подписки на этого бота
                active_subscription = await session.execute(
                    select(BotSubscription).filter(
                        BotSubscription.bot_id == bot_id
                    ).order_by(BotSubscription.end_date.desc())
                )
                active_subscription = active_subscription.scalars().first()

            if active_subscription:
                # Если есть активная подписка, показываем информацию о ней
                formatted_end_date = active_subscription.end_date.strftime('%d.%m.%Y')

                # Создаем клавиатуру для подписки
                builder = InlineKeyboardBuilder()
                for key, (months, price_rub) in prices_rub.items():
                    if lang == 'en':
                        price_usdt = await convert_to_crypto(price_rub, "tether")
                        price_text = f"{months} {MESSAGES[lang]['months']} - {price_usdt:.2f} USDT"
                    else:
                        price_text = f"{months} {MESSAGES[lang]['months']} - {price_rub} {MESSAGES[lang]['rub']}"

                    builder.row(
                        InlineKeyboardButton(
                            text=price_text,
                            callback_data=key
                        )
                    )

                builder.row(
                    InlineKeyboardButton(
                        text=MESSAGES[lang]['back'],
                        callback_data="back"
                    )
                )

                message_text = MESSAGES[lang]['subscription_already_active'].format(end_date=formatted_end_date)
                await callback_query.message.edit_text(
                    message_text,
                    reply_markup=builder.as_markup(),
                    parse_mode='Markdown'
                )
                await state.update_data(selected_bot_id=bot_id)
                await state.update_data(previous_state=PaymentStates.choose_bot)
                await state.set_state(PaymentStates.choose_duration)
            else:
                # Если подписки нет, предлагаем выбрать длительность подписки
                builder = InlineKeyboardBuilder()
                for key, (months, price_rub) in prices_rub.items():
                    if lang == 'en':
                        price_usdt = await convert_to_crypto(price_rub, "tether")
                        price_text = f"{months} {MESSAGES[lang]['months']} - {price_usdt:.2f} USDT"
                    else:
                        price_text = f"{months} {MESSAGES[lang]['months']} - {price_rub} {MESSAGES[lang]['rub']}"

                    builder.row(
                        InlineKeyboardButton(
                            text=price_text,
                            callback_data=key
                        )
                    )

                builder.row(
                    InlineKeyboardButton(
                        text=MESSAGES[lang]['back'],
                        callback_data="back"
                    )
                )

                await callback_query.message.edit_text(
                    MESSAGES[lang]['choose_subscription_duration'],
                    reply_markup=builder.as_markup(),
                    parse_mode='Markdown'
                )
                await state.update_data(selected_bot_id=bot_id)
                await state.update_data(previous_state=PaymentStates.choose_bot)
                await state.set_state(PaymentStates.choose_duration)

        except Exception as e:
            await callback_query.message.edit_text(chat_id=callback_query.message.chat.id, text=MESSAGES[lang]['error_occurred'])
            await state.clear()
        
    elif previous_state == PaymentStates.choose_payment_type:
        user_id = callback_query.from_user.id
        lang = await get_lang(user_id)
        data = await state.get_data()
        selected_bot_id = data.get("selected_bot_id")

        duration_map = {
            "subscription_1_month": {"ru": ("1 месяц", 299, 1), "en": ("1 month", 299, 1)},
            "subscription_3_months": {"ru": ("3 месяца", 599, 3), "en": ("3 months", 599, 3)},
            "subscription_6_months": {"ru": ("6 месяцев", 999, 6), "en": ("6 months", 999, 6)},
            "subscription_12_months": {"ru": ("12 месяцев", 1499, 12), "en": ("12 months", 1499, 12)},
        }

        try:
            async with await get_db_session() as session:
                # Проверяем существование бота
                bot = await session.get(UserBot, selected_bot_id)
                if not bot:
                    await callback_query.message.edit_text(MESSAGES[lang]['error_bot_not_found'])
                    return

                subscription_key = data.get("key")
                if subscription_key in duration_map:
                    duration_text, base_price, months = duration_map[subscription_key][lang]

                    # Обновляем данные состояния
                    await state.update_data(
                        subscription_duration=duration_text,
                        subscription_price=base_price,
                        subscription_months=months
                    )

                    # Показываем пользователю информацию о подписке
                    await callback_query.message.edit_text(
                        MESSAGES[lang]['subscription_selected'].format(
                            duration=duration_text,
                            price=f"{base_price} {MESSAGES[lang]['rub']}"
                        )
                    )

                    # Генерируем меню для выбора метода оплаты
                    builder = InlineKeyboardBuilder()
                    builder.add(InlineKeyboardButton(text=MESSAGES[lang]['pay_via_telegram_stars'], callback_data="pay_via_telegram_stars"))
                    builder.add(InlineKeyboardButton(text=MESSAGES[lang]['pay_via_crypto_bot'], callback_data="pay_via_crypto_bot"))
                    builder.row(InlineKeyboardButton(text=MESSAGES[lang]['back'], callback_data="go_back"))

                    await callback_query.message.edit_text(
                        MESSAGES[lang]['choose_payment_method'],
                        reply_markup=builder.as_markup()
                    )
                    await state.update_data(previous_state = PaymentStates.choose_duration)
                else:
                    await callback_query.message.edit_text(MESSAGES[lang]['invalid_subscription_choice'])
                    await state.clear()

        except Exception as e:
            await callback_query.message.edit_text(MESSAGES[lang]['error_occurred'])
            await state.clear()
            
            