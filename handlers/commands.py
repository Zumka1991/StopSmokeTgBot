"""
Command хендлеры — /start, /help, /progress, /rating, /stats, /settings и т.д.
"""
import logging
import traceback
from datetime import datetime

from aiogram import F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import dp, bot, is_admin, ADMIN_USERNAMES
from keyboards import (
    get_main_keyboard,
    get_start_keyboard,
    get_settings_keyboard,
    get_ai_keyboard,
    get_relapse_keyboard,
    get_rating_keyboard,
    get_diary_menu_keyboard,
)
from quotes import get_random_quote, ACHIEVEMENT_MESSAGES
from utils import format_duration, calculate_savings, calculate_cigarettes_not_smoked, escape_markdown, get_progress_bar
import database as db

logger = logging.getLogger(__name__)


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
            if referred_by == user_id:
                referred_by = None
        except ValueError:
            pass

    is_new = await db.add_user(user_id, username, first_name, referred_by)
    user = await db.get_user(user_id)

    if is_new or not user.get("quit_date"):
        free_mode = await db.get_free_ai_mode()

        if free_mode:
            ai_text = """🤖 *ИИ-Поддержка:*
Вам доступен наш умный ИИ-ассистент, который поможет справиться с тягой в любую минуту!"""
        else:
            ai_text = """🤖 *ИИ-Поддержка:*
Пригласите хотя бы одного друга, и вам откроется доступ к нашему умному ИИ-ассистенту, который поможет справиться с тягой в любую минуту!"""

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

{ai_text}

🌐 *Наше сообщество:*
🔗 https://stopsmoke.info

Готов начать путь к здоровой жизни?
"""
        await message.answer(welcome_text, reply_markup=get_start_keyboard())
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
    free_mode = await db.get_free_ai_mode()

    if free_mode:
        ai_access_text = "ИИ-ассистент доступен для всех пользователей!"
    else:
        ai_access_text = "Доступ открывается после приглашения хотя бы одного друга!"

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
{ai_access_text}
"""
    await message.answer(help_text, reply_markup=get_ai_keyboard())


@dp.message(F.text == "📓 Дневник")
async def cmd_diary(message: Message):
    """Меню дневника"""
    await message.answer(
        "📓 *Дневник*\n\n"
        "Что хотите сделать?",
        reply_markup=get_diary_menu_keyboard()
    )


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
        await message.answer("Сначала начните с команды /start", reply_markup=get_main_keyboard())
        return

    if not user.get("quit_date"):
        await message.answer(
            "Вы ещё не указали дату отказа от курения!\nНажмите кнопку ниже, чтобы начать.",
            reply_markup=get_start_keyboard()
        )
        return

    quit_date = datetime.fromisoformat(user["quit_date"])
    now = datetime.now()
    delta = now - quit_date

    duration = format_duration(delta)
    savings = calculate_savings(user, delta)
    cigarettes = calculate_cigarettes_not_smoked(user, delta)

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
    leaderboard = await db.get_leaderboard(11, offset)

    if not leaderboard:
        text = "🏆 *Рейтинг пока пуст*\n\nСтаньте первым участником!"

        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=get_main_keyboard())
        else:
            await message_or_callback.message.edit_text(text)
            await message_or_callback.answer()
        return

    has_next = len(leaderboard) > 10
    if has_next:
        leaderboard = leaderboard[:10]

    current_user_id = message_or_callback.from_user.id
    rating_text = f"🏆 *Таблица лидеров* (стр. {page + 1})\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, user in enumerate(leaderboard):
        quit_date = datetime.fromisoformat(user["quit_date"])
        delta = datetime.now() - quit_date
        duration = format_duration(delta)

        global_rank = offset + i + 1
        medal = medals[i] if (page == 0 and i < 3) else f"{global_rank}."

        username = user.get("username")
        if username:
            name = f"{escape_markdown(user.get('first_name', 'Аноним'))} (@{escape_markdown(username)})"
        else:
            name = user.get("first_name") or "Аноним"

        is_current = "👈 ВЫ" if user["user_id"] == current_user_id else ""
        rating_text += f"{medal} *{name}* — {duration} {is_current}\n"

    rating_text += "\n💪 _Чем дольше без сигарет — тем выше в рейтинге!_"
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
    await message.answer(f"💫 *Мотивация дня:*\n\n{quote}", reply_markup=get_main_keyboard())


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
            [InlineKeyboardButton(text="🌐 Перейти на сайт", url="https://stopsmoke.info")]
        ])
    )


@dp.message(Command("resetai"))
async def cmd_reset_ai(message: Message):
    """Обнуление счётчика вопросов к ИИ"""
    await db.reset_ai_counter(message.from_user.id)
    await message.answer(
        "✅ *Счётчик общения с ИИ обнулён!*\n\nТеперь вам снова доступно 10 вопросов на сегодня.",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показать статистику бота"""
    stats = await db.get_bot_stats()

    brief_text = f"""
📊 *Статистика StopSmoke Bot*

👥 *Пользователи:*
• Всего: *{stats['total_users']}*
• Активных: *{stats['active_users']}*
• Новых сегодня: *+{stats['new_today']}*
• Новых за неделю: *+{stats['new_week']}*
• Новых за месяц: *+{stats['new_month']}*

🤝 *Рефералы:*
• Переходов по ссылкам: *{stats['total_referrals']}*
• Пользователей с рефералами: *{stats['users_with_referrals']}*

💰 *Общий прогресс:*
• Сэкономлено: *{stats['total_savings']:,.0f}₽*
• Не выкурено: *{stats['total_cigarettes']:,} сигарет*
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Расширенная", callback_data="stats_extended")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await message.answer(brief_text, reply_markup=keyboard)


@dp.callback_query(F.data == "stats_extended")
async def callback_stats_extended(callback: CallbackQuery):
    """Расширенная статистика"""
    stats = await db.get_bot_stats()

    extended_text = f"""
📊 *Расширенная статистика*

👥 *Пользователи:*
• Всего в боте: *{stats['total_users']}*
• С датой отказа: *{stats['active_users']}*
• Новых сегодня: *+{stats['new_today']}*
• Новых за неделю: *+{stats['new_week']}*
• Новых за месяц: *+{stats['new_month']}*

━━━━━━━━━━━━━━━━━━━━

🚭 *Прогресс отказа:*
• Всего не выкурено: *{stats['total_cigarettes']:,} сигарет*
• Сэкономлено денег: *{stats['total_savings']:,.0f}₽*
• Средний срок: *{stats['avg_days']:.1f} дней*

━━━━━━━━━━━━━━━━━━━━

🤝 *Реферальная программа:*
• Всего переходов: *{stats['total_referrals']}*
• Пользователей с рефералами: *{stats['users_with_referrals']}*

━━━━━━━━━━━━━━━━━━━━

🎯 *Достижения:*
• Выдано достижений: *{stats['total_achievements']}*

📓 *Дневник:*
• Записей: *{stats['diary_entries']}*

🔄 *Срывы:*
• Всего срывов: *{stats['total_relapses']}*
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Краткая", callback_data="stats_brief")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(extended_text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "stats_brief")
async def callback_stats_brief(callback: CallbackQuery):
    """Краткая статистика"""
    stats = await db.get_bot_stats()

    brief_text = f"""
📊 *Статистика StopSmoke Bot*

👥 *Пользователи:*
• Всего: *{stats['total_users']}*
• Активных: *{stats['active_users']}*
• Новых сегодня: *+{stats['new_today']}*
• Новых за неделю: *+{stats['new_week']}*
• Новых за месяц: *+{stats['new_month']}*

🤝 *Рефералы:*
• Переходов по ссылкам: *{stats['total_referrals']}*
• Пользователей с рефералами: *{stats['users_with_referrals']}*

💰 *Общий прогресс:*
• Сэкономлено: *{stats['total_savings']:,.0f}₽*
• Не выкурено: *{stats['total_cigarettes']:,} сигарет*
"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Расширенная", callback_data="stats_extended")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(brief_text, reply_markup=keyboard)
    await callback.answer()


@dp.message(F.text == "🎯 Достижения")
async def cmd_achievements(message: Message):
    """Показать достижения"""
    user = await db.get_user(message.from_user.id)

    if not user or not user.get("quit_date"):
        await message.answer("Сначала укажите дату отказа от курения!", reply_markup=get_start_keyboard())
        return

    quit_date = datetime.fromisoformat(user["quit_date"])
    delta = datetime.now() - quit_date
    total_minutes = delta.total_seconds() / 60

    thresholds = [
        (60, "1_hour"), (720, "12_hours"), (1440, "1_day"), (2880, "2_days"),
        (4320, "3_days"), (10080, "1_week"), (20160, "2_weeks"), (43200, "1_month"),
        (129600, "3_months"), (259200, "6_months"), (525600, "1_year"),
        (1051200, "2_years"), (2628000, "5_years"), (5256000, "10_years"),
    ]

    earned = []
    upcoming = []

    for threshold, key in thresholds:
        if total_minutes >= threshold:
            earned.append(ACHIEVEMENT_MESSAGES[key].split("\n")[0])
        elif len(upcoming) < 3:
            upcoming.append(
                ACHIEVEMENT_MESSAGES[key].split("\n")[0]
                .replace("🏅", "🔒").replace("🥉", "🔒").replace("🥈", "🔒")
                .replace("🥇", "🔒").replace("🏆", "🔒").replace("👑", "🔒").replace("💎", "🔒")
            )

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
        await message.answer("Сначала начните с команды /start", reply_markup=get_main_keyboard())
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
    await message.answer(settings_text, reply_markup=get_settings_keyboard(notifications, rating_visible))
