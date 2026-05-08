from datetime import datetime
from aiogram import types, Router, F, Bot
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup
import aiohttp
from db import UserBot, get_lang, BotMenuButton, Mailing, User, BotSubscription, get_bot_username, get_db_session, PendingPayment
from dict import MESSAGES
from config import crypto_bot
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update, delete, func
from sqlalchemy.future import select
from dateutil.relativedelta import relativedelta
from handlers.bot_settings import MainBotSettingsStates
import logging
import asyncio

router = Router(name=__name__)

class PaymentStates(StatesGroup):
    choose_bot = State()
    choose_duration = State()
    choose_payment_type = State()

async def get_crypto_rate(crypto_symbol, fiat_currency='rub'):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_symbol}&vs_currencies={fiat_currency}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data[crypto_symbol][fiat_currency]

async def convert_to_crypto(amount_in_rub, crypto_symbol):
    rate = await get_crypto_rate(crypto_symbol)
    amount_in_crypto = amount_in_rub / rate
    return amount_in_crypto

@router.callback_query(F.data == "subscription")
async def handle_subscription_payment(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработка списка ботов для подписки.
    """
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
                builder.row(
                    InlineKeyboardButton(
                        text=f"{bot.bot_username}",
                        callback_data=f"for_bot_subscription_{bot.id}"
                    )
                )
            builder.row(InlineKeyboardButton(text=MESSAGES[lang]['back'], callback_data="back"))

            await callback_query.message.edit_text(
                MESSAGES[lang]['subscription_bot'],
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            await state.update_data(previous_state=MainBotSettingsStates.main_menu)
        else:
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
            await callback_query.message.edit_text(MESSAGES[lang]['no_bots'], reply_markup=keyboard)
            await state.clear()

    except Exception as e:
        logging.error(f"Error in handle_subscription_payment: {e}")
        await callback_query.message.edit_text(MESSAGES[lang]['error_occurred'])
        await state.clear()

@router.callback_query(F.data.startswith("for_bot_subscription_"))
async def select_subscription_bot(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик выбора бота для подписки.
    """
    user_telegram_id = callback_query.from_user.id
    lang = await get_lang(user_telegram_id)

    await callback_query.answer()
    bot_id = int(callback_query.data.replace("for_bot_subscription_", ""))

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
                await callback_query.message.edit_text(MESSAGES[lang]['bot_not_found'], parse_mode='HTML')
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
                    if months == 1:
                        price_text = f"{months} {MESSAGES[lang]['month']} - {price_usdt:.2f} USDT"
                    else:
                        price_text = f"{months} {MESSAGES[lang]['months']} - {price_usdt:.2f} USDT"
                else:
                    if months == 1:
                        price_text = f"{months} {MESSAGES[lang]['month']} - {price_rub} {MESSAGES[lang]['rub']}"
                    elif months == 3:
                        price_text = f"{months} {MESSAGES[lang]['month3']} - {price_rub} {MESSAGES[lang]['rub']}"
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
                parse_mode='HTML'
            )
            await state.update_data(selected_bot_id=bot_id)
            await state.update_data(previous_state=PaymentStates.choose_bot, key=key)
            await state.set_state(PaymentStates.choose_duration)
        else:
            # Если подписки нет, предлагаем выбрать длительность подписки
            builder = InlineKeyboardBuilder()
            for key, (months, price_rub) in prices_rub.items():
                if lang == 'en':
                    price_usdt = await convert_to_crypto(price_rub, "tether")
                    if months == 1:
                        price_text = f"{months} {MESSAGES[lang]['month']} - {price_usdt:.2f} USDT"
                    else:
                        price_text = f"{months} {MESSAGES[lang]['months']} - {price_usdt:.2f} USDT"
                else:
                    if months == 1:
                        price_text = f"{months} {MESSAGES[lang]['month']} - {price_rub} {MESSAGES[lang]['rub']}"
                    elif months == 3:
                        price_text = f"{months} {MESSAGES[lang]['month3']} - {price_rub} {MESSAGES[lang]['rub']}"
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
                parse_mode='HTML'
            )
            await state.update_data(selected_bot_id=bot_id)
            await state.update_data(previous_state=PaymentStates.choose_bot)
            await state.set_state(PaymentStates.choose_duration)

    except Exception as e:
        logging.error(f"Error in select_subscription_bot handler: {e}")
        await callback_query.message.edit_text(chat_id=callback_query.message.chat.id, text=MESSAGES[lang]['error_occurred'])
        await state.clear()

@router.callback_query(F.data.startswith("subscription_"))
async def select_subscription_duration(callback_query: types.CallbackQuery, state: FSMContext):
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

            subscription_key = callback_query.data
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
                builder.row(InlineKeyboardButton(text=MESSAGES[lang]['pay_via_telegram_stars'], callback_data="pay_via_telegram_stars"))
                builder.row(InlineKeyboardButton(text=MESSAGES[lang]['pay_via_crypto_bot'], callback_data="pay_via_crypto_bot"))
                builder.row(InlineKeyboardButton(text=MESSAGES[lang]['back'], callback_data="back"))

                await callback_query.message.edit_text(
                    MESSAGES[lang]['choose_payment_method'],
                    reply_markup=builder.as_markup()
                )
                await state.update_data(previous_state = PaymentStates.choose_duration)
            else:
                await callback_query.message.edit_text(MESSAGES[lang]['invalid_subscription_choice'])
                await state.clear()

    except Exception as e:
        logging.error(f"Error in select_subscription_duration: {e}")
        await callback_query.message.edit_text(MESSAGES[lang]['error_occurred'])
        await state.clear()

@router.callback_query(F.data == "pay_via_telegram_stars")
async def initiate_telegram_stars_payment(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    data = await state.get_data()

    subscription_price = data.get("subscription_price")
    subscription_months = data.get("subscription_duration")
    bot_id = data.get("selected_bot_id")

    try:
        bot_username = await get_bot_username(bot_id)
        if not bot_username:
            logging.error(f"[ERROR] Бот с id={bot_id} не найден.")
            await callback_query.message.answer(MESSAGES[lang]["error_bot_not_found"])
            await state.clear()
            return

        # Создание счета
        title = f"Подписка на бота {bot_username}"
        description = f"Подписка на {subscription_months} для бота {bot_username}"
        payload = f"{user_id}:{bot_id}:{subscription_months}:{subscription_price}"
        price = int(subscription_price / 2.15)  # Telegram Stars работает в копейках или другой валюте
        prices = [LabeledPrice(label="XTR", amount=price)]

        # Отправляем invoice
        await callback_query.message.answer_invoice(
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Замените на токен платежного провайдера
            currency="XTR",
            prices=prices,
            start_parameter="subscription_payment",
        )

        await callback_query.message.delete()
        await state.clear()

    except Exception as e:
        logging.error(f"Error initiating Telegram Stars payment: {e}")
        await callback_query.message.edit_text(MESSAGES[lang]["payment_failed"])
        await state.clear()

async def pre_checkout(query: PreCheckoutQuery):
    # Этот хэндлер нужен для проверки до того, как будет завершен платеж
    await query.answer(ok=True)

async def process_shipping(query: types.ShippingQuery):
    # Для оплаты Telegram Stars не нужен процесс доставки
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    successful_payment = message.successful_payment
    user_id = message.from_user.id
    lang = await get_lang(user_id)

    payload = successful_payment.invoice_payload
    try:
        user_id_from_payload, bot_id, subscription_months, subscription_price = map(int, payload.split(":"))

        async with await get_db_session() as session:
        # Получение бота через ORM
            bot = await session.get(UserBot, bot_id)
        if not bot:
            logging.error(f"Бот с id {bot_id} не найден.")
            await message.answer(MESSAGES[lang]["payment_failed"])
            return

        # Создание или обновление подписки
        end_date = datetime.now() + relativedelta(months=subscription_months)
        new_subscription = BotSubscription(
            bot_id=bot_id,
            subscription_months=subscription_months,
            subscription_price=subscription_price,
            start_date=datetime.now(),
            end_date=end_date,
        )
        session.add(new_subscription)
        await session.commit()

        # Сообщение об успешной подписке
        message_text = MESSAGES[lang]["payment_successful"].format(
            end_date=end_date.strftime("%d.%m.%Y"), bot_username=bot.bot_username
        )
        await message.answer(message_text, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error processing payment: {e}")
        await message.answer(MESSAGES[lang]["payment_failed"])

@router.callback_query(F.data == "pay_via_crypto_bot")
async def initiate_crypto_bot_payment(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    lang = await get_lang(user_id)
    data = await state.get_data()

    subscription_price = data.get("subscription_price")
    subscription_months = data.get("subscription_duration")
    bot_id = data.get("selected_bot_id")

    try:
        async with await get_db_session() as session:
            # Получаем имя бота через ORM
            bot = await session.get(UserBot, bot_id)
            if not bot:
                logging.error(f"Бот с id {bot_id} не найден.")
                await callback_query.message.answer(MESSAGES[lang]["error_bot_not_found"])
                await state.clear()
                return

            invoice = await crypto_bot.create_invoice(
                asset="USDT",
                amount=str(await convert_to_crypto(subscription_price, "tether")),
                description=f"Подписка на {subscription_months} для бота {bot.bot_username}",
                payload=f"{user_id}:{bot_id}:{subscription_months}",
                allow_comments=False,
                allow_anonymous=False,
                expires_in=600,
            )

            # Сохраняем информацию о платеже
            new_payment = PendingPayment(
                invoice_id=invoice.invoice_id,
                user_id=user_id,
                bot_id=bot_id,
                subscription_months=subscription_months,
                subscription_price=subscription_price,
            )
            session.add(new_payment)
            await session.commit()

        # Отправляем пользователю ссылку на оплату
        payment_link = invoice.bot_invoice_url
        message_text = MESSAGES[lang]["payment_initiated"] + f"\n{payment_link}"
        await callback_query.message.edit_text(message_text)
        await state.clear()

    except Exception as e:
        logging.error(f"Failed to create invoice: {e}")
        await callback_query.message.edit_text(MESSAGES[lang]["payment_failed"])
        await state.clear()

async def check_pending_payments(bot: Bot):
    """
    Проверка статусов незавершённых платежей и обработка подписок.
    """
    try:
        async with await get_db_session() as session:
            # Получаем все незавершенные платежи
            pending_payments = await session.execute(select(PendingPayment))
            pending_payments = pending_payments.scalars().all()

        for payment in pending_payments:
            invoice_id = payment.invoice_id
            user_id = payment.user_id
            bot_id = payment.bot_id
            subscription_months = payment.subscription_months
            subscription_price = payment.subscription_price

            try:
                # Проверяем статус счета
                invoices = await crypto_bot.get_invoices(invoice_ids=[invoice_id])
                if invoices and len(invoices) > 0:
                    invoice = invoices[0]
                    if invoice.status == "paid":
                        # Получаем информацию о боте
                        selected_bot = await session.get(UserBot, bot_id)
                        if not selected_bot:
                            logging.error(f"Бот с ID {bot_id} не найден. Пропуск.")
                            continue

                        # Обновляем подписку пользователя
                        end_date = datetime.now() + relativedelta(months=subscription_months)
                        new_subscription = BotSubscription(
                            bot_id=bot_id,
                            subscription_months=subscription_months,
                            subscription_price=subscription_price,
                            start_date=datetime.now(),
                            end_date=end_date,
                        )
                        session.add(new_subscription)

                        # Удаляем запись о платеже из pending_payments
                        await session.delete(payment)
                        await session.commit()

                        # Отправляем уведомление пользователю
                        lang = await get_lang(user_id)
                        end_date_str = end_date.strftime("%d.%m.%Y")
                        message_text = MESSAGES[lang]["payment_successful"].format(
                            bot_username=selected_bot.bot_username,
                            end_date=end_date_str,
                        )
                        await bot.send_message(chat_id=user_id, text=message_text)

                    elif invoice.status == "expired":
                        # Удаляем запись о платеже, если счет истек
                        await session.delete(payment)
                        await session.commit()

                        lang = await get_lang(user_id)
                        await bot.send_message(chat_id=user_id, text=MESSAGES[lang]["payment_failed"], parse_mode="Markdown")

                    # Если статус 'active', ничего не делаем и проверим позже
                else:
                    async with await get_db_session() as session:
                        # Удаляем запись, если счет не найден
                        await session.delete(payment)
                        await session.commit()
                    logging.warning(f"Invoice {invoice_id} не найден. Удален из pending payments.")

            except Exception as e:
                logging.error(f"Ошибка при проверке счета {invoice_id}: {e}")

    except Exception as main_error:
        logging.error(f"Ошибка в функции check_pending_payments: {main_error}")

async def check_and_remove_expired_subscriptions(bot: Bot):
    """
    Проверка истекших подписок и уведомление администраторов.
    """
    try:
        async with await get_db_session() as session:
            # Получаем текущую дату
            current_date = datetime.now()

            # Запрашиваем истекшие подписки
            expired_subscriptions = await session.execute(
                select(BotSubscription)
                .filter(BotSubscription.end_date < current_date)
            )
            expired_subscriptions = expired_subscriptions.scalars().all()

            for subscription in expired_subscriptions:
                # Получаем бота, связанного с подпиской
                bot_entry = await session.get(UserBot, subscription.bot_id)
                if not bot_entry:
                    continue

                # Уведомляем администратора бота
                try:
                    user_bots_result = await session.execute(
                            select(UserBot.id).filter(UserBot.user_id == bot_entry.user_id)
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

                    # Подсчитываем количество включенных ботов для пользователя
                    active_bots_count = await session.execute(
                        select(func.count(UserBot.id))
                        .filter(UserBot.user_id == bot_entry.user_id, UserBot.is_started == True)
                    )
                    active_bots_count = active_bots_count.scalar() or 0
                    
                    # Лимит включенных ботов
                    bot_limit = 3 + active_subscription_count
                    
                    if active_bots_count > bot_limit:
                        BOT = Bot(bot_entry.bot_token)
                        await BOT.delete_webhook()
                        await BOT.session.close()
                    
                    admin_id = bot_entry.user_id
                    lang = await get_lang(admin_id)
                    await bot.send_message(
                        chat_id=admin_id,
                        text=MESSAGES[lang]["subscription_expired"].format(
                            bot_username=bot_entry.bot_username
                        )
                    )
                except Exception as e:
                    logging.error(f"Ошибка при уведомлении администратора {admin_id}: {e}")

                # Удаляем подписку
                await session.delete(subscription)
                logging.info(f"Удалена подписка для бота @{bot_entry.bot_username}.")
            
            # Сохраняем изменения
            await session.commit()

    except Exception as e:
        logging.error(f"Ошибка при проверке истекших подписок: {e}")
