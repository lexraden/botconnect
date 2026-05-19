from aiogram import types
import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, func, ForeignKey, UniqueConstraint, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from config import DATABASE_URL, TOKEN
from datetime import datetime
# Создаем базу для ORM
Base = declarative_base()

# Создание асинхронного движка
engine = create_async_engine(DATABASE_URL, echo=False)

# Создание сессии
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Модель для таблицы ботов
class UserBot(Base):
    __tablename__ = 'user_bots'

    id = Column(Integer, primary_key=True, index=True)            # Уникальный идентификатор записи
    user_id = Column(BigInteger, nullable=False)                  # ID пользователя, добавившего бота
    bot_token = Column(String, unique=True, nullable=False)       # Токен бота
    bot_username = Column(String, nullable=False)                 # Имя бота
    sent_messages_count = Column(Integer, default=0)              # Счетчик отправленных сообщений
    replied_messages_count = Column(Integer, default=0)           # Счетчик ответов на сообщения
    greeting_message = Column(String, nullable=True)              # Приветственное сообщение
    greeting_file = Column(String, nullable=True)                 # Файл приветственного сообщения
    sent_messages_to = Column(BigInteger, nullable=True)          # Чат куда будут перенаправляться сообщения
    total_messages_count = Column(Integer, default=0)             # Общее количество сообщений (sent + replied)
    created_at = Column(DateTime, server_default=func.now())      # Время добавления бота
    users_blocked = Column(Integer, default=0)                    # Кол-во пользователей заблокировавших бота
    is_started = Column(Boolean, default=True)                    # Включен ли бот

    users = relationship('User', back_populates='bot', cascade="all, delete")
    buttons = relationship('BotMenuButton', back_populates='bot', cascade="all, delete")
    mailings = relationship('Mailing', back_populates='bot', cascade="all, delete")
    subscriptions = relationship("BotSubscription", back_populates="bot", cascade="all, delete")  
    pending_payments = relationship("PendingPayment", back_populates="bot", cascade="all, delete")
    channels = relationship("Channels", back_populates="bot", cascade="all, delete")  
    
    def __repr__(self):
        return f"<UserBot(user_id={self.user_id}, bot_token={self.bot_token}, bot_username={self.bot_username})>"

# Модель для таблицы пользователей
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)                                # Уникальный идентификатор записи
    user_id = Column(BigInteger, nullable=False)                                      # ID пользователя в Telegram
    username = Column(String, nullable=True)                                          # Имя пользователя
    first_name = Column(String, nullable=True)                                        # Имя пользователя
    last_name = Column(String, nullable=True)                                         # Фамилия пользователя
    language_code = Column(String, nullable=True)                                     # Язык пользователя
    bot_token = Column(String, ForeignKey('user_bots.bot_token'), nullable=False)     # Токен бота
    from_chat_id = Column(BigInteger, nullable=True, default=None)                    # В какой чат добавлялся пользователь 
    is_banned = Column(Boolean, default=False, nullable = True)                       # Забанен ли пользователь
    created_at = Column(DateTime, server_default=func.now())                          # Время добавления пользователя

    bot = relationship('UserBot', back_populates='users')  # Связь с моделью UserBot

    __table_args__ = (UniqueConstraint('user_id', 'bot_token', name='uq_user_bot'),)  # Уникальность пары user_id и bot_token

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username}, first_name={self.first_name}, last_name={self.last_name})>"

# Модель для пользователей из главного бота
class MainBotUser(Base):
    __tablename__ = "main_bot_users"

    id = Column(Integer, primary_key=True, autoincrement=True)          # Уникальный идентификатор записи
    user_id = Column(BigInteger, nullable=False, unique=True)           # ID пользователя в Telegram
    username = Column(String, nullable=True)                            # Имя пользователя
    first_name = Column(String, nullable=True)                          # Имя пользователя
    last_name = Column(String, nullable=True)                           # Фамилия пользователя
    language_code = Column(String, nullable=True)                       # Язык пользователя
    created_at = Column(DateTime, server_default=func.now())            # Время добавления пользователя

    def __repr__(self):
        return (
            f"<MainBotUser(id={self.id}, user_id={self.user_id}, username={self.username}, "
            f"first_name={self.first_name}, last_name={self.last_name}, "
            f"language_code={self.language_code})>"
        )

# Модель для таблицы кнопок
class BotMenuButton(Base):
    __tablename__ = 'bot_menu_buttons'

    id = Column(Integer, primary_key=True, index=True)                                        # Уникальный идентификатор записи
    bot_token = Column(String, ForeignKey('user_bots.bot_token'), nullable=False)             # Токен бота
    button_text = Column(String, nullable=False)                                              # Текст кнопки
    reply_message = Column(String, nullable=True)                                             # Сообщение, отправляемое при нажатии
    file_id = Column(String, nullable=True)                                                   # ID файла (документ, фото и т.д.)
    button_type = Column(String, nullable=True)                                               # Тип кнопки (текст, файл, и т.д.)
    action_type = Column(String, nullable=False, default="send_new")                          # Действие кнопки (изменить сообщение, отправить новое, URL)
    linked_button_id = Column(Integer, ForeignKey('bot_menu_buttons.id'), nullable=True)      # ID связанной инлайн-кнопки
    linked_to_start = Column(Boolean, nullable=True)                                          # Привязана ли кнопка к старту
    from_greeting = Column(Boolean, nullable=True, default = False)                           # Добавлена ли эта кнопка из приветствия
    command = Column(String, nullable=True, default=None)                                     # Команда, вызывающая кнопку
    created_at = Column(DateTime, server_default=func.now())                                  # Дата создания кнопки
    
    bot = relationship('UserBot', back_populates='buttons')

    def __repr__(self):
        return (f"<BotMenuButton(bot_token={self.bot_token}, button_text={self.button_text}, "
                f"reply_message={self.reply_message}, file_id={self.file_id}, button_type={self.button_type}, "
                f"action_type={self.action_type}, linked_button_id={self.linked_button_id})>")

# Модель для таблицы рассылок ботов
class Mailing(Base):
    __tablename__ = 'mailings'

    id = Column(Integer, primary_key=True, autoincrement=True)              # Уникальный идентификатор рассылки
    bot_id = Column(Integer, ForeignKey('user_bots.id'), nullable=False)    # ID бота, сделавшего рассылку
    reply_message = Column(String, nullable=True)                           # Сообщение, отправляемое при рассылке
    file_id = Column(String, nullable=True)                                 # ID файла (документ, фото и т.д.)
    counted_msg = Column(BigInteger, nullable=False, default=0)             # Кол-во отправленных сообщений
    button_text =  Column(String, nullable=True)                            # Текст кнопки для рассылки
    button_url = Column(String, nullable=True)                              # URL кнопки для рассылки
    scheduled_time = Column(DateTime, nullable=True)                        # Время, на которое запланирована рассылка
    is_sent = Column(Boolean, default=False)                                # Флаг, указывающий, была ли рассылка отправлена

    # Связь с таблицей UserBot
    bot = relationship('UserBot', back_populates='mailings')

    def __repr__(self):
        return (f"<Mailing(id={self.id}, bot_id={self.bot_id},"
                f"scheduled_time={self.scheduled_time}, is_sent={self.is_sent})>")

# Модель для таблицы подписок на ботов
class BotSubscription(Base):
    __tablename__ = "bot_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)              # Уникальный идентификатор
    bot_id = Column(Integer, ForeignKey("user_bots.id"), nullable=False)    # Ссылка на бота
    subscription_months = Column(Integer, nullable=False)                   # Количество месяцев подписки
    subscription_price = Column(Float, nullable=False)                      # Цена подписки
    start_date = Column(DateTime, default=datetime.utcnow)                  # Дата начала подписки
    end_date = Column(DateTime, nullable=False)                             # Дата окончания подписки

    # Связь с моделью UserBot
    bot = relationship("UserBot", back_populates="subscriptions")

    def __repr__(self):
        return (
            f"<BotSubscription("
            f"id={self.id}, "
            f"bot_id={self.bot_id}, "
            f"subscription_months={self.subscription_months}, "
            f"subscription_price={self.subscription_price}, "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date})>"
        )

class PendingPayment(Base):
    __tablename__ = "pending_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)                  # Уникальный идентификатор
    invoice_id = Column(BigInteger, unique=True, nullable=False)                # Уникальный идентификатор счета
    user_id = Column(BigInteger, nullable=False)                                # ID пользователя
    bot_id = Column(Integer, ForeignKey("user_bots.id"), nullable=False)        # ID бота
    subscription_months = Column(Integer, nullable=False)                       # Количество месяцев подписки
    subscription_price = Column(Float, nullable=False)                          # Цена подписки
    created_at = Column(DateTime, default=datetime.now)                         # Время создания платежа

    # Связи
    bot = relationship("UserBot", back_populates="pending_payments")

    def __repr__(self):
        return (
            f"<PendingPayment(id={self.id}, invoice_id={self.invoice_id}, "
            f"user_id={self.user_id}, bot_id={self.bot_id}, "
            f"subscription_months={self.subscription_months}, subscription_price={self.subscription_price}, "
            f"created_at={self.created_at})>"
        )

class Channels(Base):
    __tablename__ = "bots_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)              # Уникальный идентификатор
    bot_id = Column(Integer, ForeignKey("user_bots.id"), nullable=False)    # ID бота
    channel_name = Column(String, nullable=False)                           # Имя канала
    channel_id = Column(BigInteger, nullable=False, unique=True)            # ID канала
    auto_accept = Column(Boolean, default=True)                             # Включено ли автопринятие заявок
    captcha = Column(Boolean, default=False)                                # Включена ли капча
    captcha_button_text = Column(String, nullable=True, default=None)       # Текст кнопки капчи

    bot = relationship("UserBot", back_populates="channels")
    messages = relationship("ChannelMessage", back_populates="channels", cascade="all, delete")

    def __repr__(self):
        return (
            f"<Channel(id={self.id}, bot_id={self.bot_id}, channel_name='{self.channel_name}', "
            f"channel_id={self.channel_id})>"
        )

class ChannelMessage(Base):
    __tablename__ = "channel_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)                                  # Уникальный идентификатор записи
    channel_id = Column(BigInteger, ForeignKey("bots_channels.id"), nullable=False)             # ID канала
    language_code = Column(String, nullable=False)                                              # Код языка (например, "en", "ru")
    message_type = Column(String, nullable=False)                                               # Тип сообщения: "greeting" или "farewell"
    message_text = Column(String, nullable=True)                                                # Текст сообщения
    message_file = Column(String, nullable=True)                                                # Файл для сообщения

    channels = relationship("Channels", back_populates="messages")
    buttons = relationship("ChannelMessageButton", back_populates="message", cascade="all, delete")

    def __repr__(self):
        return (
            f"<ChannelMessage(id={self.id}, channel_id={self.channel_id}, "
            f"language_code='{self.language_code}', message_type='{self.message_type}', message_text='{self.message_text}')>"
        )

class ChannelMessageButton(Base):
    __tablename__ = "channel_message_buttons"

    id = Column(Integer, primary_key=True, autoincrement=True)                                 # Уникальный идентификатор записи
    message_id = Column(Integer, ForeignKey("channel_messages.id"), nullable=False)            # ID сообщения, к которому привязана кнопка
    button_text = Column(String, nullable=False)                                               # Текст на кнопке
    button_url = Column(String, nullable=False)                                                # URL, который открывается при нажатии на кнопку
    row = Column(Integer, nullable=False)                                                      # Строка на которой находится кнопка 

    message = relationship("ChannelMessage", back_populates="buttons")

    def __repr__(self):
        return (
            f"<ChannelMessageButton(id={self.id}, message_id={self.message_id}, "
            f"button_text='{self.button_text}', button_url='{self.button_url}')>"
        )

# Функция для создания таблиц
async def create_tables():
    async with engine.begin() as conn:
        # Создание таблиц в базе данных
        await conn.run_sync(Base.metadata.create_all)
        # Миграция: добавляем новые колонки если их нет
        await conn.execute(
            sqlalchemy.text(
                "ALTER TABLE bots_channels ADD COLUMN IF NOT EXISTS captcha_button_text VARCHAR DEFAULT NULL"
            )
        )

# Функция для получения сессии
async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        return session

# Функция для получения кнопок бота
async def get_buttons_for_bot(bot_token: str):
    async with await get_db_session() as session:
        result = await session.execute(select(BotMenuButton).filter(BotMenuButton.bot_token == bot_token))
        return result.scalars().all()

async def get_bot_username(bot_id: int):
    async with await get_db_session() as session:
        bot = await session.get(UserBot, bot_id)
        return bot.bot_username if bot else None

async def get_lang(user_id: int):
    async with await get_db_session() as session:
        result = await session.execute(select(MainBotUser).filter(MainBotUser.user_id == user_id))
        lang = result.scalars().first()
        return lang.language_code if lang else None

async def save_user_for_bot(message: types.Message, bot_token: str):
    async with await get_db_session() as session:
        # Проверяем, существует ли уже пользователь с таким user_id
        result = await session.execute(select(User).filter(User.user_id == message.from_user.id, User.bot_token == bot_token))
        user = result.scalars().first()

        # Если пользователь не найден, добавляем нового
        if not user:
            new_user = User(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code,
                is_blocked=False,
                bot_token=bot_token  # Связываем пользователя с ботом через bot_token
            )
            session.add(new_user)
            try:
                await session.commit()
                print(f"Пользователь {message.from_user.username} добавлен в базу данных для бота {bot_token}.")
            except Exception as e:
                await session.rollback()
                print(f"Ошибка при добавлении пользователя: {e}")
        else:
            print(f"Пользователь {message.from_user.username} уже существует в базе данных.")

# Функция для обновления счетчика отправленных сообщений
async def increment_sent_messages_count(bot_token: str):
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
        bot_entry = result.scalars().first()

        if bot_entry:
            bot_entry.sent_messages_count += 1
            bot_entry.total_messages_count += 1  # Обновляем общее количество сообщений
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Ошибка при обновлении счетчика отправленных сообщений: {e}")

# Функция для обновления счетчика ответов на сообщения
async def increment_replied_messages_count(bot_token: str):
    async with await get_db_session() as session:
        result = await session.execute(select(UserBot).filter(UserBot.bot_token == bot_token))
        bot_entry = result.scalars().first()

        if bot_entry:
            bot_entry.replied_messages_count += 1
            bot_entry.total_messages_count += 1  # Обновляем общее количество сообщений
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Ошибка при обновлении счетчика ответов на сообщения: {e}")