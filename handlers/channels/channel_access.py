from aiogram import Router, types, Bot, types , F
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ChatMemberUpdated, ChatJoinRequest, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import exists, and_
from db import UserBot, User, BotSubscription, Channels, get_lang, get_db_session
from handlers.bot_settings import MainBotSettingsStates
from handlers.menu_handlers.adding_button import BotSettingsStates
from config import admins
from datetime import datetime
from dict import MESSAGES
from handlers.channels.channel_settings import ChannelSetingsStates
import asyncio

router = Router(name=__name__)

@router.callback_query(F.data.startswith("user_access_settings_"))
async def user_access_settings(callback_query: CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[-1])

    lang = await get_lang(callback_query.from_user.id)

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

    await state.update_data(previous_state = ChannelSetingsStates.channel_settings, channel_id = channel_id)

    await callback_query.message.edit_text(
        text=MESSAGES[lang]["user_access_text"].format(channel_name = channel.channel_name,
                                                       user_access = "✅" if channel.auto_accept else "❌",
                                                       captcha = "✅" if channel.captcha else "❌"),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(F.data.startswith("auto_access_switch_"))
async def enable_auto_access(callback_query: CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[-1])

    lang = await get_lang(callback_query.from_user.id)

    async with await get_db_session() as session:
        channel_result = await session.execute(
                select(Channels).filter(Channels.id == channel_id)
            )
        channel = channel_result.scalars().first()

        channel.auto_accept = not channel.auto_accept

        await session.commit()

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

    await callback_query.message.edit_text(
        text=MESSAGES[lang]["user_access_text"].format(channel_name = channel.channel_name,
                                                       user_access = "✅" if channel.auto_accept else "❌",
                                                       captcha = "✅" if channel.captcha else "❌"),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(F.data.startswith("captha_switch_"))
async def enable_auto_access(callback_query: CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[-1])

    lang = await get_lang(callback_query.from_user.id)

    async with await get_db_session() as session:
        channel_result = await session.execute(
                select(Channels).filter(Channels.id == channel_id)
            )
        channel = channel_result.scalars().first()

        channel.captcha = not channel.captcha

        await session.commit()

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

    await callback_query.message.edit_text(
        text=MESSAGES[lang]["user_access_text"].format(channel_name = channel.channel_name,
                                                       user_access = "✅" if channel.auto_accept else "❌",
                                                       captcha = "✅" if channel.captcha else "❌"),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(F.data.startswith("captcha_settings_"))
async def captcha_settings(callback_query: CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[-1])

    lang = await get_lang(callback_query.from_user.id)

    async with await get_db_session() as session:
        channel_result = await session.execute(
                select(Channels).filter(Channels.id == channel_id)
            )
        channel = channel_result.scalars().first()

    current_text = channel.captcha_button_text or MESSAGES[lang]["not_robot"]

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
    )

    await callback_query.message.edit_text(
        text=MESSAGES[lang]["captcha_current_text"].format(text=current_text) + "\n\n" + MESSAGES[lang]["captcha_text_prompt"],
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

    await state.set_state(ChannelSetingsStates.awaiting_captcha_text)
    await state.update_data(previous_state=ChannelSetingsStates.user_access, channel_id=channel_id)

@router.message(ChannelSetingsStates.awaiting_captcha_text)
async def save_captcha_text(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    data = await state.get_data()
    channel_id = data.get("channel_id")

    async with await get_db_session() as session:
        channel_result = await session.execute(
                select(Channels).filter(Channels.id == channel_id)
            )
        channel = channel_result.scalars().first()

        channel.captcha_button_text = message.text

        await session.commit()

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=MESSAGES[lang]["back"], callback_data="back")
    )

    await message.answer(
        text=MESSAGES[lang]["captcha_text_updated"],
        reply_markup=keyboard.as_markup()
    )

    await state.update_data(previous_state=ChannelSetingsStates.user_access, channel_id=channel_id)

