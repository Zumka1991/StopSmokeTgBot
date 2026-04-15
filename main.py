"""
StopSmoke Bot — точка входа.
"""
import asyncio
import logging

from config import dp, bot, scheduler, register_middleware
import database as db
from scheduler import setup_scheduler_jobs, run_startup_broadcast
from handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def on_startup():
    """Действия при запуске"""
    await db.init_db()
    logger.info("База данных инициализирована")

    register_middleware()

    register_handlers(dp)

    setup_scheduler_jobs()

    # Запускаем фоновую рассылку (если не была выполнена)
    asyncio.create_task(run_startup_broadcast())


async def on_shutdown():
    """Действия при остановке"""
    scheduler.shutdown()
    logger.info("Бот остановлен")


async def main():
    """Главная функция"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
