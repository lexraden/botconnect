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
import asyncio

class ChannelSetingsStates(StatesGroup):
    channels = State()
    channel_settings = State()
    channel_messages = State()
    channel_message_settings = State()
    language_choose = State()
    awaiting_message = State()
    awaiting_new_message = State()
    awaiting_buttons = State()
    awaiting_captcha_text = State()
    user_access = State()

router = Router(name=__name__)

@router.callback_query(F.data.startswith("channel_settings_"))
async def channel_settings(callback_query: CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.split("_")[-1])
    
    lang = await get_lang(callback_query.from_user.id)
    
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
    
    await state.update_data(previous_state=ChannelSetingsStates.channels, bot_id = channel.bot_id)
        
    await callback_query.message.edit_text(
        text=MESSAGES[lang]["channel_settings_text"].format(channel_name = channel.channel_name),
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )
        
@router.callback_query(F.data.startswith("delete_channel_"))
async def delete_channel(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    channel_id = int(callback_query.data.split("_")[-1])
    
    lang = await get_lang(callback_query.from_user.id)
    
    async with await get_db_session() as session:
        channel_result = await session.execute(
                select(Channels).filter(Channels.id == channel_id)
            )
        channel = channel_result.scalars().first()
        
        try:
            await bot.leave_chat(channel.channel_id)
        except Exception as e:
            print(f"Не удалось выйти из чата {channel.channel_name}: {e}")
        
        await session.delete(channel)
        await session.commit()
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=MESSAGES[lang]["back_to_start"]), callback_data="back")
    
    await state.update_data(previous_state=BotSettingsStates.main_menu)
    
    await callback_query.message.edit_text(text=MESSAGES[lang]["deleted_channel"].format(channel_name = channel.channel_name), reply_markup=keyboard.as_markup())
    