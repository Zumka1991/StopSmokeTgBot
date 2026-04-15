"""
Планировщик и фоновые задачи — ежедневная мотивация, проверка рейтинга, рассылки.
"""
import asyncio
import logging

from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, scheduler
from quotes import get_random_quote
from utils import format_duration, calculate_savings
import database as db

logger = logging.getLogger(__name__)


async def send_daily_motivation():
    """Отправка ежедневной мотивации"""
    users = await db.get_users_with_notifications()

    for user in users:
        try:
            quote = get_random_quote()

            quit_date = datetime.fromisoformat(user["quit_date"])
            delta = datetime.now() - quit_date
            duration = format_duration(delta)
            savings = calculate_savings(user, delta)

            message_text = f"""
🌅 *Доброе утро!*

{quote}

━━━━━━━━━━━━━━━━━━━━

📊 *Ваша статистика:*
🕐 Без сигарет: *{duration}*
💰 Сэкономлено: *{savings:,.0f}₽*

━━━━━━━━━━━━━━━━━━━━

🌐 *Сообщество StopSmoke:*
🔗 https://stopsmoke.info

Статьи, книги, болталка и счётчик!

💪 *Ещё один день победы!*
"""
            await bot.send_message(user["user_id"], message_text)
            logger.info(f"Отправлена мотивация пользователю {user['user_id']}")
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user['user_id']}: {e}")


async def check_rating_confirmations():
    """Проверка подтверждения участия в рейтинге"""
    users = await db.get_users_for_rating_check()
    now = datetime.now()

    for user in users:
        try:
            last_active = user.get("last_active")
            quit_date = user.get("quit_date")

            if not quit_date:
                continue

            quit_dt = datetime.fromisoformat(quit_date)
            days_since_quit = (now - quit_dt).days

            # Определяем интервал проверки в зависимости от стажа
            if days_since_quit <= 30:
                check_interval = 2
            elif days_since_quit <= 90:
                check_interval = 5
            else:
                check_interval = 7

            if not last_active:
                last_active_dt = quit_dt
            else:
                last_active_dt = datetime.fromisoformat(last_active)

            days_since_active = (now - last_active_dt).days

            if days_since_active >= check_interval:
                reminder_text = f"""
⚠️ *Подтвердите участие в рейтинге!*

Вы не заходили в бот уже {days_since_active} дн.

Чтобы остаться в рейтинге, подтвердите участие одним нажатием:
"""
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Подтвердить участие", callback_data="confirm_rating")],
                    [InlineKeyboardButton(text="🙈 Скрыть из рейтинга", callback_data="hide_from_rating")]
                ])

                await bot.send_message(user["user_id"], reminder_text, reply_markup=keyboard)
                logger.info(f"Отправлено напоминание о подтверждении рейтинга пользователю {user['user_id']}")

                if days_since_active >= check_interval * 2:
                    await db.toggle_rating_visibility(user["user_id"], False)
                    logger.info(f"Пользователь {user['user_id']} автоматически скрыт из рейтинга")

        except Exception as e:
            logger.error(f"Ошибка проверки рейтинга для пользователя {user.get('user_id')}: {e}")


async def send_broadcast_mail(admin_id: int, text: str):
    """Асинхронная рассылка сообщения всем пользователям"""
    user_ids = await db.get_all_user_ids()

    sent = 0
    errors = 0

    for i, user_id in enumerate(user_ids):
        try:
            await bot.send_message(user_id, text)
            sent += 1
            await asyncio.sleep(0.3)

            if sent % 50 == 0:
                logger.info(f"Рассылка: отправлено {sent}/{len(user_ids)}")
        except Exception as e:
            errors += 1
            logger.error(f"Ошибка рассылки пользователю {user_id}: {e}")

    report = f"✅ *Рассылка завершена!*\n\n📊 Отправлено: *{sent}*\n❌ Ошибок: *{errors}*\n📨 Всего в базе: *{len(user_ids)}*"
    await bot.send_message(admin_id, report)
    logger.info(f"Рассылка завершена. Отправлено: {sent}, ошибок: {errors}")


async def run_startup_broadcast():
    """Разовая рассылка при запуске"""
    broadcast_key = "ai_referral_broadcast_v1"

    if await db.is_broadcast_sent(broadcast_key):
        logger.info("Рассылка уже была выполнена ранее")
        return

    logger.info("Начало разовой рассылки...")
    user_ids = await db.get_all_user_ids()

    broadcast_text = (
        "🤖 *ИИ-Ассистент готов вам помочь!*\n\n"
        "Друзья, теперь в нашем боте доступен умный ИИ-помощник, который поможет вам "
        "справиться с тягой к курению в любую минуту. \n\n"
        "Чтобы открыть доступ к нему, вам нужно пригласить всего одного друга! \n\n"
        "Нажмите на кнопку ниже, чтобы получить свою персональную ссылку. "
        "Вместе бросать намного легче! 💪"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Пригласить друга", callback_data="show_ref_link")]
    ])

    sent_count = 0
    error_count = 0

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, broadcast_text, reply_markup=keyboard)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            error_count += 1
            logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    await db.set_broadcast_sent(broadcast_key)
    logger.info(f"Рассылка завершена. Успешно: {sent_count}, Ошибок: {error_count}")


def setup_scheduler_jobs():
    """Настройка задач планировщика"""
    # Ежедневная мотивация в 9:00
    scheduler.add_job(
        send_daily_motivation,
        "cron",
        hour=9,
        minute=0,
        id="daily_motivation"
    )

    # Проверка подтверждения рейтинга каждый день в 12:00
    scheduler.add_job(
        check_rating_confirmations,
        "cron",
        hour=12,
        minute=0,
        id="rating_confirmation"
    )

    scheduler.start()
    logger.info("Планировщик запущен")
