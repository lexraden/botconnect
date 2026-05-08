from dotenv import load_dotenv
import os
from aiogram import Router
from aiocryptopay import AioCryptoPay, Networks
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from collections import defaultdict

load_dotenv()

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
WEBHOOK_TUNNEL_URL = os.getenv("WEBHOOK_TUNNEL_URL")

admins = list(map(int, os.getenv("ADMINS", "").split(",")))

crypto_bot = AioCryptoPay(token= CRYPTO_BOT_TOKEN, network=Networks.MAIN_NET)

# Инициализация бота и диспетчера с использованием памяти для хранения состояний
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
# Инициализация роутера
router = Router()

media_groups = defaultdict(lambda: {'messages': [], 'caption': None})
media_group_tasks = {}

