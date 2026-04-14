import asyncio
import logging
import os
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import AsyncOpenAI

import database as db
from keyboards import (
    get_main_keyboard,
    get_start_keyboard,
    get_settings_keyboard,
    get_confirm_reset_keyboard,
    get_relapse_keyboard,
    get_number_keyboard,
    get_price_keyboard,
    get_back_keyboard,
    get_rating_keyboard,
    get_rating_confirm_keyboard,
    get_diary_menu_keyboard,
    get_diary_dates_keyboard,
    get_diary_delete_date_keyboard,
    get_diary_confirm_delete_keyboard,
    get_ai_keyboard
)
from quotes import get_random_quote, ACHIEVEMENT_MESSAGES
from share_card import create_share_card

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден! Создайте файл .env с токеном бота.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-001")

client = None
if OPENROUTER_API_KEY:
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


# ============ FSM ДЛЯ ДНЕВНИКА ============

class DiaryState(StatesGroup):
    waiting_for_text = State()


class AIState(StatesGroup):
    waiting_for_question = State()


class ActivityTrackerMiddleware:
    """Middleware для отслеживания активности пользователя"""
    async def __call__(self, handler, event, data):
        user = data.get('event_from_user')
        if user:
            try:
                await db.update_user_activity(user.id)
            except Exception as e:
                logger.error(f"Ошибка обновления активности: {e}")
        return await handler(event, data)


def format_duration(delta: timedelta) -> str:
    """Форматирование длительности"""
    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []
    if days > 0:
        days_word = "день" if days == 1 else "дней" if days > 4 else "дня"
        parts.append(f"{days} {days_word}")
    if hours > 0:
        hours_word = "час" if hours == 1 else "часов" if hours > 4 else "часа"
        parts.append(f"{hours} {hours_word}")
    if minutes > 0 and days == 0:
        min_word = "минута" if minutes == 1 else "минут" if minutes > 4 else "минуты"
        parts.append(f"{minutes} {min_word}")

    return " ".join(parts) if parts else "меньше минуты"


def calculate_savings(user: dict, delta: timedelta) -> float:
    """Расчёт сэкономленных денег"""
    days = delta.total_seconds() / 86400
    cigarettes_not_smoked = days * user.get("cigarettes_per_day", 20)
    packs_not_bought = cigarettes_not_smoked / user.get("cigarettes_in_pack", 20)
    return packs_not_bought * user.get("price_per_pack", 150)


def calculate_cigarettes_not_smoked(user: dict, delta: timedelta) -> int:
    """Расчёт невыкуренных сигарет"""
    days = delta.total_seconds() / 86400
    return int(days * user.get("cigarettes_per_day", 20))


def get_progress_bar(percent: float, length: int = 10) -> str:
    """Создание прогресс-бара"""
    filled = int(percent / 100 * length)
    empty = length - filled
    return "▓" * filled + "░" * empty


# ============ КОМАНДЫ ============

@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "Друг"

    # Проверка реферала
    referred_by = None
    if command.args and command.args.startswith("ref_"):
        try:
            referred_by = int(command.args.replace("ref_", ""))
            if referred_by == user_id:  # Нельзя пригласить самого себя
                referred_by = None
        except ValueError:
            pass

    is_new = await db.add_user(user_id, username, first_name, referred_by)
    user = await db.get_user(user_id)

    if is_new or not user.get("quit_date"):
        welcome_text = f"""
🚭 *Добро пожаловать в StopSmoke Bot!*

Привет, *{first_name}*! 👋

Я помогу тебе бросить курить и отслеживать прогресс.

📊 *Что я умею:*
• Считать дни без сигарет
• Показывать сэкономленные деньги
• Отправлять ежедневную мотивацию
• Вести рейтинг с другими участниками
• Отмечать твои достижения

🌐 *Также посетите наше сообщество:*
🔗 https://stopsmoke.info

Статьи, книги, болталка и счётчик отказа от никотина!

Готов начать путь к здоровой жизни?
"""
        await message.answer(
            welcome_text,
            reply_markup=get_start_keyboard()
        )
    else:
        await message.answer(
            f"С возвращением, *{first_name}*! 💪\n\n"
            "Используй кнопки ниже для навигации.",
            reply_markup=get_main_keyboard()
        )


@dp.message(Command("help"))
@dp.message(F.text == "❓ Помощь / ИИ поддержка")
async def cmd_help(message: Message):
    """Помощь и ИИ поддержка"""
    help_text = f"""
🚭 *StopSmoke Bot — Помощь*

*Основные команды:*
/start — Начать использование
/progress — Показать прогресс
/rating — Таблица лидеров
/motivation — Получить мотивацию
/settings — Настройки

━━━━━━━━━━━━━━━━━━━━

🤖 *ИИ Поддержка*

Наш ИИ-ассистент поможет вам справиться с тягой к курению и ответит на любые вопросы. 
Доступ открывается после приглашения хотя бы одного друга!
"""
    await message.answer(help_text, reply_markup=get_ai_keyboard())


@dp.message(Command("visibleall"))
async def cmd_visibleall(message: Message):
    """Сделать всех пользователей видимыми в рейтинге"""
    count = await db.make_all_users_visible()

    await message.answer(
        f"✅ *Рейтинг обновлён!*\n\n"
        f"Видимых пользователей: *{count}*\n\n"
        "Все, кто указал дату отказа, теперь видны в рейтинге."
    )


@dp.message(Command("progress"))
@dp.message(F.text == "📊 Мой прогресс")
async def cmd_progress(message: Message):
    """Показать прогресс"""
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer(
            "Сначала начните с команды /start",
            reply_markup=get_main_keyboard()
        )
        return

    if not user.get("quit_date"):
        await message.answer(
            "Вы ещё не указали дату отказа от курения!\n"
            "Нажмите кнопку ниже, чтобы начать.",
            reply_markup=get_start_keyboard()
        )
        return

    quit_date = datetime.fromisoformat(user["quit_date"])
    now = datetime.now()
    delta = now - quit_date

    duration = format_duration(delta)
    savings = calculate_savings(user, delta)
    cigarettes = calculate_cigarettes_not_smoked(user, delta)

    # Прогресс до следующей вехи (условно до 1 года)
    days_total = delta.days
    next_milestone = 365
    progress_percent = min(100, (days_total / next_milestone) * 100)
    progress_bar = get_progress_bar(progress_percent)

    stats = await db.get_user_stats(message.from_user.id)

    progress_text = f"""
📊 *Ваш прогресс*

🕐 *Без сигарет:* {duration}
📅 *Дата отказа:* {quit_date.strftime("%d.%m.%Y")}

━━━━━━━━━━━━━━━━━━━━

💰 *Сэкономлено:* {savings:,.0f}₽
🚬 *Не выкурено:* {cigarettes:,} сигарет
⏱ *Сэкономлено времени:* ~{cigarettes * 5} мин

━━━━━━━━━━━━━━━━━━━━

📈 *Прогресс до 1 года:*
{progress_bar} {progress_percent:.1f}%

🔄 *Попыток:* {stats.get('relapse_count', 0) + 1}

━━━━━━━━━━━━━━━━━━━━

💪 *Продолжайте в том же духе!*
"""
    await message.answer(progress_text, reply_markup=get_relapse_keyboard())


@dp.message(Command("rating"))
@dp.message(F.text == "🏆 Рейтинг")
async def cmd_rating(message: Message):
    """Показать рейтинг"""
    await show_rating_page(message, 0)


async def show_rating_page(message_or_callback, page: int):
    """Показать страницу рейтинга"""
    offset = page * 10
    leaderboard = await db.get_leaderboard(11, offset)  # +1 чтобы проверить есть ли следующая страница

    if not leaderboard:
        text = "🏆 *Рейтинг пока пуст*\n\n"
        text += "Станьте первым участником!"
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(
                text,
                reply_markup=get_main_keyboard()
            )
        else:
            await message_or_callback.message.edit_text(text)
            await message_or_callback.answer()
        return

    # Проверяем есть ли следующая страница
    has_next = len(leaderboard) > 10
    if has_next:
        leaderboard = leaderboard[:10]  # Убираем лишнего пользователя

    current_user_id = message_or_callback.from_user.id
    rating_text = f"🏆 *Таблица лидеров* (стр. {page + 1})\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, user in enumerate(leaderboard):
        quit_date = datetime.fromisoformat(user["quit_date"])
        delta = datetime.now() - quit_date
        duration = format_duration(delta)

        global_rank = offset + i + 1
        medal = medals[i] if (page == 0 and i < 3) else f"{global_rank}."
        name = user.get("first_name") or user.get("username") or "Аноним"

        is_current = "👈 ВЫ" if user["user_id"] == current_user_id else ""

        rating_text += f"{medal} *{name}* — {duration} {is_current}\n"

    rating_text += "\n💪 _Чем дольше без сигарет — тем выше в рейтинге!_"

    # Определяем есть ли предыдущая страница
    has_prev = page > 0

    keyboard = get_rating_keyboard(page, has_prev, has_next)

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(rating_text, reply_markup=keyboard)
    else:
        await message_or_callback.message.edit_text(rating_text, reply_markup=keyboard)
        await message_or_callback.answer()


@dp.message(Command("motivation"))
@dp.message(F.text == "💪 Мотивация")
async def cmd_motivation(message: Message):
    """Получить мотивацию"""
    quote = get_random_quote()
    await message.answer(
        f"💫 *Мотивация дня:*\n\n{quote}",
        reply_markup=get_main_keyboard()
    )


@dp.message(F.text == "🌐 Сообщество")
async def cmd_community(message: Message):
    """Сообщество StopSmoke"""
    community_text = """
🌐 *Сообщество StopSmoke*

🔗 https://stopsmoke.info

*Что вас ждёт:*

📚 *Статьи* — полезные материалы о вреде курения и способах отказа

📖 *Книги* — подборка литературы для мотивации

💬 *Болталка* — общайтесь с единомышленниками, делитесь опытом

⏱️ *Счётчик* — наглядный счётчик времени без никотина

Присоединяйтесь к сообществу людей, которые бросают курить!
"""
    await message.answer(
        community_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Перейти на сайт",
                    url="https://stopsmoke.info"
                )
            ]
        ])
    )


@dp.message(F.text == "🎯 Достижения")
async def cmd_achievements(message: Message):
    """Показать достижения"""
    user = await db.get_user(message.from_user.id)

    if not user or not user.get("quit_date"):
        await message.answer(
            "Сначала укажите дату отказа от курения!",
            reply_markup=get_start_keyboard()
        )
        return

    quit_date = datetime.fromisoformat(user["quit_date"])
    delta = datetime.now() - quit_date
    total_minutes = delta.total_seconds() / 60

    # Определяем полученные достижения
    thresholds = [
        (60, "1_hour"),
        (720, "12_hours"),
        (1440, "1_day"),
        (2880, "2_days"),
        (4320, "3_days"),
        (10080, "1_week"),
        (20160, "2_weeks"),
        (43200, "1_month"),
        (129600, "3_months"),
        (259200, "6_months"),
        (525600, "1_year"),
        (1051200, "2_years"),
        (2628000, "5_years"),
        (5256000, "10_years"),
    ]

    earned = []
    upcoming = []

    for threshold, key in thresholds:
        if total_minutes >= threshold:
            earned.append(ACHIEVEMENT_MESSAGES[key].split("\n")[0])
        elif len(upcoming) < 3:
            upcoming.append(ACHIEVEMENT_MESSAGES[key].split("\n")[0].replace("🏅", "🔒").replace("🥉", "🔒").replace("🥈", "🔒").replace("🥇", "🔒").replace("🏆", "🔒").replace("👑", "🔒").replace("💎", "🔒"))

    achievements_text = "🎯 *Ваши достижения*\n\n"

    if earned:
        achievements_text += "*Получены:*\n"
        for ach in earned:
            achievements_text += f"{ach}\n"
    else:
        achievements_text += "_Пока нет достижений. Продолжайте!_\n"

    if upcoming:
        achievements_text += "\n*Следующие:*\n"
        for ach in upcoming:
            achievements_text += f"{ach}\n"

    achievements_text += f"\n📊 _Всего достижений: {len(earned)}/{len(thresholds)}_"

    await message.answer(achievements_text, reply_markup=get_main_keyboard())


@dp.message(Command("settings"))
@dp.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message):
    """Настройки"""
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer(
            "Сначала начните с команды /start",
            reply_markup=get_main_keyboard()
        )
        return

    notifications = bool(user.get("notifications_enabled", 1))
    rating_visible = bool(user.get("rating_visible", 1))

    quit_date_str = "Не установлена"
    if user.get("quit_date"):
        quit_date = datetime.fromisoformat(user["quit_date"])
        quit_date_str = quit_date.strftime("%d.%m.%Y")

    settings_text = f"""
⚙️ *Настройки*

📅 Дата отказа: *{quit_date_str}*
🚬 Сигарет в день: *{user.get('cigarettes_per_day', 20)}*
💵 Цена пачки: *{user.get('price_per_pack', 150):.0f}₽*
📦 Сигарет в пачке: *{user.get('cigarettes_in_pack', 20)}*
🔔 Уведомления: *{'Включены' if notifications else 'Выключены'}*
👁️ В рейтинге: *{'Виден' if rating_visible else 'Скрыт'}*

_Нажмите кнопку для изменения:_
"""
    await message.answer(
        settings_text,
        reply_markup=get_settings_keyboard(notifications, rating_visible)
    )


# ============ CALLBACK HANDLERS ============

@dp.callback_query(F.data == "start_now")
async def callback_start_now(callback: CallbackQuery):
    """Начать прямо сейчас"""
    user_id = callback.from_user.id
    await db.set_quit_date(user_id, datetime.now())

    await callback.message.edit_text(
        "🎉 *Отлично! Ваш путь начался!*\n\n"
        f"📅 Дата старта: *{datetime.now().strftime('%d.%m.%Y %H:%M')}*\n\n"
        "Я буду отправлять вам ежедневную мотивацию "
        "и отслеживать ваш прогресс.\n\n"
        "💪 *Вы справитесь!*"
    )
    await callback.message.answer(
        "Используйте кнопки для навигации:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "choose_date")
async def callback_choose_date(callback: CallbackQuery):
    """Выбор даты (упрощённо — сегодня)"""
    await callback.message.edit_text(
        "📅 *Выбор даты*\n\n"
        "Введите дату в формате ДД.ММ.ГГГГ\n"
        "Например: 01.12.2024\n\n"
        "Или нажмите кнопку ниже, чтобы начать сегодня.",
        reply_markup=get_start_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "set_quit_date")
async def callback_set_quit_date(callback: CallbackQuery):
    """Установка даты отказа"""
    user = await db.get_user(callback.from_user.id)
    current_date = ""
    if user and user.get("quit_date"):
        quit_date = datetime.fromisoformat(user["quit_date"])
        current_date = f"\n\n📅 Текущая дата: *{quit_date.strftime('%d.%m.%Y')}*"

    await callback.message.edit_text(
        f"📅 *Установка даты отказа от курения*\n\n"
        f"Введите дату в формате ДД.ММ.ГГГГ\n"
        f"Например: 01.12.2024{current_date}",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "toggle_notifications")
async def callback_toggle_notifications(callback: CallbackQuery):
    """Переключение уведомлений"""
    user = await db.get_user(callback.from_user.id)
    current = bool(user.get("notifications_enabled", 1))
    new_state = not current
    rating_visible = bool(user.get("rating_visible", 1))

    await db.toggle_notifications(callback.from_user.id, new_state)

    status = "включены 🔔" if new_state else "выключены 🔕"
    await callback.answer(f"Уведомления {status}")

    # Обновляем клавиатуру
    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(new_state, rating_visible)
    )


@dp.callback_query(F.data == "toggle_rating_visibility")
async def callback_toggle_rating_visibility(callback: CallbackQuery):
    """Переключение видимости в рейтинге"""
    user = await db.get_user(callback.from_user.id)
    current = bool(user.get("rating_visible", 1))
    new_state = not current
    notifications = bool(user.get("notifications_enabled", 1))

    await db.toggle_rating_visibility(callback.from_user.id, new_state)

    status = "виден в рейтинге 👁️" if new_state else "скрыт из рейтинга 🙈"
    await callback.answer(f"Теперь вы {status}")

    # Обновляем клавиатуру
    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(notifications, new_state)
    )


@dp.callback_query(F.data == "confirm_rating")
async def callback_confirm_rating(callback: CallbackQuery):
    """Подтверждение участия в рейтинге"""
    await db.confirm_rating_participation(callback.from_user.id)

    await callback.message.edit_text(
        "✅ *Участие подтверждено!*\n\n"
        "Вы снова видны в рейтинге. Продолжайте держаться! 💪"
    )
    await callback.answer("Отлично! Рейтинг обновлён 🏆")


@dp.callback_query(F.data == "hide_from_rating")
async def callback_hide_from_rating(callback: CallbackQuery):
    """Скрытие из рейтинга"""
    user = await db.get_user(callback.from_user.id)
    notifications = bool(user.get("notifications_enabled", 1))

    await db.toggle_rating_visibility(callback.from_user.id, False)

    await callback.message.edit_text(
        "🙈 *Вы скрыты из рейтинга*\n\n"
        "Не переживайте! Можете вернуться в любой момент "
        "через настройки.",
        reply_markup=get_settings_keyboard(notifications, False)
    )
    await callback.answer("Скрыто из рейтинга")


@dp.callback_query(F.data == "set_cigarettes")
async def callback_set_cigarettes(callback: CallbackQuery):
    """Установка количества сигарет"""
    await callback.message.edit_text(
        "🚬 *Сколько сигарет в день вы курили?*\n\n"
        "Выберите количество:",
        reply_markup=get_number_keyboard("cig")
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("cig_"))
async def callback_cig_number(callback: CallbackQuery):
    """Обработка выбора количества сигарет"""
    number = int(callback.data.split("_")[1])
    await db.update_user_settings(callback.from_user.id, cigarettes_per_day=number)
    await callback.answer(f"Установлено: {number} сигарет в день")

    user = await db.get_user(callback.from_user.id)
    notifications = bool(user.get("notifications_enabled", 1))

    await callback.message.edit_text(
        f"✅ Сохранено: *{number} сигарет в день*\n\n"
        "Вернуться в настройки?",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "set_price")
async def callback_set_price(callback: CallbackQuery):
    """Установка цены пачки"""
    await callback.message.edit_text(
        "💵 *Какая цена пачки сигарет?*\n\n"
        "Выберите примерную стоимость:",
        reply_markup=get_price_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("price_"))
async def callback_price_number(callback: CallbackQuery):
    """Обработка выбора цены"""
    price = int(callback.data.split("_")[1])
    await db.update_user_settings(callback.from_user.id, price_per_pack=price)
    await callback.answer(f"Установлено: {price}₽ за пачку")

    await callback.message.edit_text(
        f"✅ Сохранено: *{price}₽ за пачку*\n\n"
        "Вернуться в настройки?",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "set_pack_size")
async def callback_set_pack_size(callback: CallbackQuery):
    """Установка размера пачки"""
    await callback.message.edit_text(
        "📦 *Сколько сигарет в пачке?*\n\n"
        "Выберите количество:",
        reply_markup=get_number_keyboard("pack")
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("pack_"))
async def callback_pack_number(callback: CallbackQuery):
    """Обработка выбора размера пачки"""
    number = int(callback.data.split("_")[1])
    await db.update_user_settings(callback.from_user.id, cigarettes_in_pack=number)
    await callback.answer(f"Установлено: {number} сигарет в пачке")

    await callback.message.edit_text(
        f"✅ Сохранено: *{number} сигарет в пачке*\n\n"
        "Вернуться в настройки?",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "back_to_settings")
async def callback_back_to_settings(callback: CallbackQuery):
    """Возврат в настройки"""
    user = await db.get_user(callback.from_user.id)
    notifications = bool(user.get("notifications_enabled", 1))
    rating_visible = bool(user.get("rating_visible", 1))

    quit_date_str = "Не установлена"
    if user.get("quit_date"):
        quit_date = datetime.fromisoformat(user["quit_date"])
        quit_date_str = quit_date.strftime("%d.%m.%Y")

    settings_text = f"""
⚙️ *Настройки*

📅 Дата отказа: *{quit_date_str}*
🚬 Сигарет в день: *{user.get('cigarettes_per_day', 20)}*
💵 Цена пачки: *{user.get('price_per_pack', 150):.0f}₽*
📦 Сигарет в пачке: *{user.get('cigarettes_in_pack', 20)}*
🔔 Уведомления: *{'Включены' if notifications else 'Выключены'}*
👁️ В рейтинге: *{'Виден' if rating_visible else 'Скрыт'}*

_Нажмите кнопку для изменения:_
"""
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_settings_keyboard(notifications, rating_visible)
    )
    await callback.answer()


@dp.callback_query(F.data == "reset_progress")
async def callback_reset_progress(callback: CallbackQuery):
    """Сброс прогресса"""
    await callback.message.edit_text(
        "⚠️ *Вы уверены?*\n\n"
        "Это сбросит ваш текущий прогресс "
        "и начнёт отсчёт заново.\n\n"
        "_Статистика срывов сохранится._",
        reply_markup=get_confirm_reset_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm_reset")
async def callback_confirm_reset(callback: CallbackQuery):
    """Подтверждение сброса"""
    await db.add_relapse(callback.from_user.id, "Сброс прогресса")
    await db.reset_quit_date(callback.from_user.id)

    await callback.message.edit_text(
        "🔄 *Прогресс сброшен*\n\n"
        "Не переживайте! Каждая попытка — это шаг к успеху.\n\n"
        f"📅 Новая дата старта: *{datetime.now().strftime('%d.%m.%Y %H:%M')}*\n\n"
        "💪 *В этот раз получится!*"
    )
    await callback.message.answer(
        "Удачи!",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel_reset")
async def callback_cancel_reset(callback: CallbackQuery):
    """Отмена сброса"""
    await callback.answer("Отменено! Продолжайте в том же духе! 💪")

    user = await db.get_user(callback.from_user.id)
    notifications = bool(user.get("notifications_enabled", 1))

    await callback.message.edit_text(
        "✅ *Отлично!* Продолжайте держаться!\n\n"
        "Вернуться в настройки?",
        reply_markup=get_back_keyboard()
    )


@dp.callback_query(F.data == "relapse")
async def callback_relapse(callback: CallbackQuery):
    """Обработка срыва"""
    await callback.message.edit_text(
        "😔 *Ничего страшного!*\n\n"
        "Срыв — это не провал, а часть пути.\n"
        "Многие успешно бросают не с первой попытки.\n\n"
        "Хотите начать заново?",
        reply_markup=get_confirm_reset_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "stay_strong")
async def callback_stay_strong(callback: CallbackQuery):
    """Держится!"""
    quote = get_random_quote()
    await callback.message.edit_text(
        f"💪 *Отлично! Вы молодец!*\n\n{quote}"
    )
    await callback.answer("Так держать! 🎉")


@dp.callback_query(F.data == "share_result")
async def callback_share_result(callback: CallbackQuery):
    """Поделиться результатом — генерация карточки"""
    await callback.answer("Генерирую карточку... 🎨")

    user = await db.get_user(callback.from_user.id)

    if not user or not user.get("quit_date"):
        await callback.answer("Сначала укажите дату отказа!", show_alert=True)
        return

    try:
        quit_date = datetime.fromisoformat(user["quit_date"])
        now = datetime.now()
        delta = now - quit_date

        savings = calculate_savings(user, delta)
        cigarettes = calculate_cigarettes_not_smoked(user, delta)
        first_name = user.get("first_name") or callback.from_user.first_name or "Участник"
        quit_date_str = quit_date.strftime("%d.%m.%Y")

        # Генерируем карточку
        card_path = create_share_card(first_name, delta, savings, cigarettes, quit_date_str)

        bot_username = (await bot.get_me()).username

        # Отправляем как фото через FSInputFile
        photo = FSInputFile(card_path)
        await callback.message.answer_photo(
            photo=photo,
            caption=(
                f"🚭 *StopSmoke Bot — Мой результат*\n\n"
                f"👤 *{first_name}* бросает курить!\n\n"
                f"📅 Дата отказа: *{quit_date_str}*\n"
                f"💰 Сэкономил: *{savings:,.0f}₽*\n"
                f"🚬 Не выкурил: *{cigarettes:,} сигарет*\n\n"
                f"💪 Присоединяйся! Бросай курить вместе со мной!"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚭 Тоже бросить!",
                        url=f"https://t.me/{bot_username}"
                    )
                ]
            ])
        )

    except Exception as e:
        logger.error(f"Ошибка генерации карточки: {e}")
        logger.error(traceback.format_exc())
        await callback.message.answer(
            "😔 Не удалось создать карточку. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )


@dp.callback_query(F.data.startswith("rating_prev_") | F.data.startswith("rating_next_"))
async def callback_rating_navigation(callback: CallbackQuery):
    """Навигация по рейтингу"""
    action, page_str = callback.data.rsplit("_", 1)
    page = int(page_str)

    if action == "rating_prev":
        page -= 1
    else:
        page += 1

    await show_rating_page(callback, page)



# ============ ОБРАБОТКА ТЕКСТА (дата) ============

@dp.message(F.text.regexp(r"^\d{2}\.\d{2}\.\d{4}$"))
async def handle_date_input(message: Message):
    """Обработка ввода даты"""
    try:
        date = datetime.strptime(message.text, "%d.%m.%Y")

        if date > datetime.now():
            await message.answer(
                "❌ Дата не может быть в будущем!",
                reply_markup=get_main_keyboard()
            )
            return

        await db.set_quit_date(message.from_user.id, date)

        delta = datetime.now() - date
        duration = format_duration(delta)

        await message.answer(
            f"✅ *Дата установлена!*\n\n"
            f"📅 Вы бросили: *{date.strftime('%d.%m.%Y')}*\n"
            f"🕐 Без сигарет: *{duration}*\n\n"
            "💪 *Отличная работа!*",
            reply_markup=get_main_keyboard()
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты!\n"
            "Используйте формат: ДД.ММ.ГГГГ",
            reply_markup=get_main_keyboard()
        )


# ============ ДНЕВНИК ============

@dp.message(F.text == "📓 Дневник")
async def cmd_diary(message: Message):
    """Главное меню дневника"""
    await message.answer(
        "📓 *Дневник*\n\n"
        "Записывайте свои мысли, чувства и наблюдения.\n"
        "Это помогает осознать прогресс и справиться с трудностями.\n\n"
        "Что хотите сделать?",
        reply_markup=get_diary_menu_keyboard()
    )


@dp.callback_query(F.data == "diary_menu")
async def callback_diary_menu(callback: CallbackQuery):
    """Возврат в меню дневника"""
    await callback.message.edit_text(
        "📓 *Дневник*\n\n"
        "Что хотите сделать?",
        reply_markup=get_diary_menu_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "diary_add")
async def callback_diary_add(callback: CallbackQuery, state: FSMContext):
    """Начало добавления записи"""
    await callback.message.edit_text(
        "✏️ *Новая запись в дневнике*\n\n"
        "Введите дату в формате ДД.ММ.ГГГГ\n"
        "Например: 14.04.2026\n\n"
        "Или отправьте дату сегодняшнего дня кнопкой ниже:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Сегодня",
                    callback_data="diary_date_today"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="diary_menu"
                )
            ]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "diary_date_today")
async def callback_diary_date_today(callback: CallbackQuery, state: FSMContext):
    """Выбор сегодняшней даты"""
    today = datetime.now().strftime("%d.%m.%Y")
    await state.update_data(diary_date=today)
    await state.set_state(DiaryState.waiting_for_text)

    await callback.message.edit_text(
        f"📅 *Дата записи:* {today}\n\n"
        "Напишите свой текст для дневника.\n"
        "Это может быть всё что угодно:\n"
        "• Как вы себя чувствуете\n"
        "• Что мотивирует\n"
        "• Какие трудности\n"
        "• Маленькие победы\n\n"
        "_Отправьте текст сообщения:_",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="diary_menu"
                )
            ]
        ])
    )
    await callback.answer()


@dp.message(DiaryState.waiting_for_text)
async def handle_diary_entry(message: Message, state: FSMContext):
    """Обработка текста записи дневника"""
    user_data = await state.get_data()
    entry_date = user_data.get("diary_date")

    if not entry_date:
        await message.answer("❌ Ошибка. Попробуйте снова через меню дневника.")
        await state.clear()
        return

    entry_text = message.text
    await db.add_diary_entry(message.from_user.id, entry_date, entry_text)

    await state.clear()

    await message.answer(
        f"✅ *Запись сохранена!*\n\n"
        f"📅 Дата: *{entry_date}*\n"
        f"📝 Текст: {entry_text[:100]}{'...' if len(entry_text) > 100 else ''}\n\n"
        "Хотите добавить ещё одну запись?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Добавить ещё",
                    callback_data="diary_add"
                ),
                InlineKeyboardButton(
                    text="📓 В меню",
                    callback_data="diary_menu"
                )
            ]
        ])
    )


@dp.callback_query(F.data == "diary_read")
async def callback_diary_read(callback: CallbackQuery):
    """Показать список дат"""
    dates = await db.get_diary_dates(callback.from_user.id)

    if not dates:
        await callback.message.edit_text(
            "📖 *Записей пока нет*\n\n"
            "Начните вести дневник — это помогает\n"
            "осознать свой прогресс!\n\n"
            "_Отправьте текст в любое время._",
            reply_markup=get_diary_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📖 *Выберите дату для просмотра:*\n\n"
        "Нажмите на дату, чтобы прочитать записи:",
        reply_markup=get_diary_dates_keyboard(dates)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("diary_date_"))
async def callback_diary_show_entries(callback: CallbackQuery):
    """Показать записи за выбранную дату"""
    date_str = callback.data.replace("diary_date_", "")

    entries = await db.get_diary_entries_by_date(callback.from_user.id, date_str)

    if not entries:
        await callback.answer("Записей нет за эту дату", show_alert=True)
        return

    text = f"📅 *Записи за {date_str}:*\n\n"
    for i, entry in enumerate(entries, 1):
        text += f"*{i}.* {entry['entry_text']}\n\n"

    text += f"_Всего записей: {len(entries)}_"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Назад к датам",
                    callback_data="diary_read"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📓 Меню дневника",
                    callback_data="diary_menu"
                )
            ]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "diary_delete")
async def callback_diary_delete(callback: CallbackQuery):
    """Показать список дат для удаления"""
    dates = await db.get_diary_dates(callback.from_user.id)

    if not dates:
        await callback.message.edit_text(
            "🗑️ *Нечего удалять*\n\n"
            "У вас пока нет записей в дневнике.",
            reply_markup=get_diary_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🗑️ *Выберите дату для удаления:*\n\n"
        "Все записи за эту дату будут удалены.",
        reply_markup=get_diary_delete_date_keyboard(dates)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("diary_del_date_"))
async def callback_diary_del_confirm(callback: CallbackQuery):
    """Подтверждение удаления записей"""
    date_str = callback.data.replace("diary_del_date_", "")

    entries = await db.get_diary_entries_by_date(callback.from_user.id, date_str)
    count = len(entries)

    await callback.message.edit_text(
        f"⚠️ *Удалить записи за {date_str}?*\n\n"
        f"Будет удалено записей: *{count}*\n\n"
        "_Это действие нельзя отменить!_",
        reply_markup=get_diary_confirm_delete_keyboard(date_str)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("diary_del_confirm_"))
async def callback_diary_del_execute(callback: CallbackQuery):
    """Выполнение удаления"""
    date_str = callback.data.replace("diary_del_confirm_", "")

    deleted = await db.delete_diary_entries_by_date(callback.from_user.id, date_str)

    await callback.message.edit_text(
        f"🗑️ *Удалено {deleted} записей за {date_str}*\n\n"
        "Вернуться в меню дневника?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📓 Меню дневника",
                    callback_data="diary_menu"
                )
            ]
        ])
    )
    await callback.answer("Записи удалены")


# ============ ПЛАНИРОВЩИК ============

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
                check_interval = 2  # первые 30 дней — проверка каждые 2 дня
            elif days_since_quit <= 90:
                check_interval = 5  # до 90 дней — каждые 5 дней
            else:
                check_interval = 7  # старше 90 дней — каждые 7 дней

            if not last_active:
                # Никогда не был активен — считаем от даты отказа
                last_active_dt = quit_dt
            else:
                last_active_dt = datetime.fromisoformat(last_active)

            days_since_active = (now - last_active_dt).days

            # Если прошло больше интервала — отправляем напоминание
            if days_since_active >= check_interval:
                reminder_text = f"""
⚠️ *Подтвердите участие в рейтинге!*

Вы не заходили в бот уже {days_since_active} дн.

Чтобы остаться в рейтинге, подтвердите участие одним нажатием:
"""
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Подтвердить участие",
                            callback_data="confirm_rating"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🙈 Скрыть из рейтинга",
                            callback_data="hide_from_rating"
                        )
                    ]
                ])

                await bot.send_message(user["user_id"], reminder_text, reply_markup=keyboard)
                logger.info(f"Отправлено напоминание о подтверждении рейтинга пользователю {user['user_id']}")

                # Если прошло в 2 раза больше интервала — скрываем автоматически
                if days_since_active >= check_interval * 2:
                    await db.toggle_rating_visibility(user["user_id"], False)
                    logger.info(f"Пользователь {user['user_id']} автоматически скрыт из рейтинга")

        except Exception as e:
            logger.error(f"Ошибка проверки рейтинга для пользователя {user.get('user_id')}: {e}")


# ============ ИИ ПОДДЕРЖКА ============

@dp.callback_query(F.data == "ask_ai")
async def callback_ask_ai(callback: CallbackQuery, state: FSMContext):
    """Начало диалога с ИИ"""
    user_id = callback.from_user.id
    referral_count = await db.get_referral_count(user_id)

    if referral_count < 1:
        # Получаем инфо о боте для ссылки
        bot_info = await bot.get_me()
        user_id = callback.from_user.id
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        
        await callback.message.edit_text(
            "🔒 *Доступ ограничен*\n\n"
            "ИИ-ассистент доступен только тем, кто пригласил хотя бы одного друга.\n\n"
            f"🔗 *Ваша ссылка для приглашения:*\n`{ref_link}`\n\n"
            "Пригласите друга и возвращайтесь за поддержкой! 💪",
            reply_markup=get_ai_keyboard()
        )
        await callback.answer()
        return

    can_ask, left = await db.check_ai_limit(user_id)
    if not can_ask:
        await callback.answer("Вы исчерпали лимит (10 вопросов в день). Ждем вас завтра!", show_alert=True)
        return

    await callback.message.edit_text(
        "🤖 *Я слушаю!*\n\n"
        "Задайте любой вопрос о том, как бросить курить, как справиться с тягой "
        "или просто попросите поддержки.\n\n"
        f"💡 _У вас осталось {left} вопроса на сегодня._",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
        ])
    )
    await state.set_state(AIState.waiting_for_question)
    await callback.answer()


@dp.message(AIState.waiting_for_question)
async def handle_ai_question(message: Message, state: FSMContext):
    """Обработка вопроса к ИИ"""
    if not client:
        await message.answer("⚠️ ИИ-поддержка временно недоступна (не настроен API ключ).")
        await state.clear()
        return

    user_id = message.from_user.id
    can_ask, _ = await db.check_ai_limit(user_id)
    
    if not can_ask:
        await message.answer("❌ Лимит вопросов на сегодня исчерпан.")
        await state.clear()
        return

    system_prompt = """
    Ты — человечный и эмпатичный ассистент поддержки в боте 'StopSmoke'. 
    Твоя специализация — помощь людям в отказе от курения и борьбе с никотиновой зависимостью.

    Твои правила:
    1. Отвечай ТОЛЬКО на вопросы, связанные с курением, сигаретами, вейпами, никотином и процессом отказа от них. 
    2. Если пользователь задает вопрос на другую тему, мягко и тепло объясни, что ты здесь только для поддержки в борьбе с курением.
    3. Тон общения: очень теплый, мягкий, поддерживающий и человечный. Избегай сухого академического стиля.
    4. Краткость: не пиши слишком длинные ответы. Будь лаконичен, но содержателен.
    5. Общайся на русском языке.
    """

    waiting_msg = await message.answer("🤖 *Думаю...*")

    try:
        # Получаем историю переписки (последние 20 сообщений)
        history = await db.get_ai_chat_history(user_id, limit=20)
        
        # Формируем список сообщений для API
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            api_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Добавляем текущее сообщение пользователя
        api_messages.append({"role": "user", "content": message.text})
        
        # Сохраняем сообщение пользователя в БД сразу
        await db.add_ai_chat_message(user_id, "user", message.text)

        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=api_messages,
            max_tokens=600
        )
        
        ai_text = response.choices[0].message.content
        
        # Сохраняем ответ ассистента в БД
        await db.add_ai_chat_message(user_id, "assistant", ai_text)
        await db.increment_ai_usage(user_id)
        
        # Обработка ответа
        if len(ai_text) > 4000:
            await waiting_msg.delete()
            for i in range(0, len(ai_text), 4000):
                await message.answer(ai_text[i:i+4000])
        else:
            # Используем HTML для избежания ошибок парсинга Markdown от ИИ
            await waiting_msg.edit_text(ai_text, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Ошибка ИИ-помощника: {e}")
        try:
            await waiting_msg.edit_text("😔 К сожалению, я временно не могу ответить. Попробуйте еще раз позже.")
        except:
            await message.answer("😔 Произошла ошибка. Попробуйте позже.")

    await state.clear()
    await message.answer("Желаете задать еще один вопрос?", reply_markup=get_ai_keyboard())


@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "С возвращением! Выбирайте раздел:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


# ============ ЗАПУСК ============

async def on_startup():
    """Действия при запуске"""
    await db.init_db()
    logger.info("База данных инициализирована")

    # Регистрируем middleware
    dp.message.middleware(ActivityTrackerMiddleware())
    dp.callback_query.middleware(ActivityTrackerMiddleware())
    logger.info("Middleware активности зарегистрирован")

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
