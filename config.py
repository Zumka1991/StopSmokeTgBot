"""
Конфигурация бота — загрузка переменных окружения, инициализация глобальных объектов.
"""
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# === Переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Создайте файл .env с токеном бота.")

ADMIN_USERNAMES = set(os.getenv("ADMIN_USERNAMES", "").replace(" ", "").split(",")) - {""}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-001")

# === Глобальные объекты ===
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# === OpenAI клиент (может быть None) ===
client = None
if OPENROUTER_API_KEY:
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


def is_admin(username: str) -> bool:
    """Проверка, является ли пользователь админом"""
    if not username:
        return False
    return username.lstrip("@") in {u.lstrip("@") for u in ADMIN_USERNAMES}


def register_middleware():
    """Регистрация middleware"""
    from middleware import ActivityTrackerMiddleware
    dp.message.middleware(ActivityTrackerMiddleware())
    dp.callback_query.middleware(ActivityTrackerMiddleware())
    logger.info("Middleware активности зарегистрирован")
