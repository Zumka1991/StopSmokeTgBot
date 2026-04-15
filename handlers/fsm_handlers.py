"""
FSM хендлеры — обработка состояний дневника и ИИ-ассистента.
"""
import logging
from datetime import datetime

import telegramify_markdown

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import dp, bot, client, OPENROUTER_MODEL
from keyboards import get_main_keyboard, get_ai_keyboard
import database as db
from states import DiaryState, AIState
from utils import format_duration, calculate_savings, calculate_cigarettes_not_smoked

logger = logging.getLogger(__name__)


@dp.message(F.text.regexp(r"^\d{2}\.\d{2}\.\d{4}$"))
async def handle_date_input(message: Message):
    """Обработка ввода даты"""
    try:
        date = datetime.strptime(message.text, "%d.%m.%Y")

        if date > datetime.now():
            await message.answer("❌ Дата не может быть в будущем!", reply_markup=get_main_keyboard())
            return

        await db.set_quit_date(message.from_user.id, date)

        delta = datetime.now() - date
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

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

        duration = " ".join(parts) if parts else "меньше минуты"

        await message.answer(
            f"✅ *Дата установлена!*\n\n"
            f"📅 Вы бросили: *{date.strftime('%d.%m.%Y')}*\n"
            f"🕐 Без сигарет: *{duration}*\n\n"
            "💪 *Отличная работа!*",
            reply_markup=get_main_keyboard()
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты!\nИспользуйте формат: ДД.ММ.ГГГГ",
            reply_markup=get_main_keyboard()
        )


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
        reply_markup=__get_diary_after_save_keyboard()
    )


def __get_diary_after_save_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Добавить ещё", callback_data="diary_add"),
            InlineKeyboardButton(text="📓 В меню", callback_data="diary_menu")
        ]
    ])


SYSTEM_PROMPT_TEMPLATE = """\
Тебя зовут Лена. Ты — эмпатичный ассистент поддержки в Telegram-боте \
'StopSmoke', помогаешь людям бросить курить и справляться с никотиновой \
зависимостью. Твой создатель — Мышонок.

# Твой подход
Опирайся на доказательные методы: мотивационное интервью (открытые \
вопросы, отражающее слушание), КПТ (работа с автоматическими мыслями), \
профилактику срыва по Marlatt. Сначала пойми ситуацию, потом советуй. \
Если человек пишет «хочу курить» — спроси, что происходит, а не сразу \
выдавай список техник.

# Тематика
Отвечай только на темы курения, никотина, вейпов, кальянов и отказа \
от них. На посторонние вопросы тепло объясняй, что ты здесь для другого.

# Острая тяга закурить (приоритет)
Если человек пишет, что хочет закурить прямо сейчас:
- Отвечай коротко (2–4 строки), без длинных лекций.
- Предложи ОДНУ технику, не список:
  - 4D — отложить на 5 минут, глубоко подышать, выпить воды, отвлечься.
  - Urge surfing — наблюдать за волной желания, она спадёт за 3–5 минут.
  - HALT-проверка — голоден / зол / одинок / устал?
- Напомни: тяга проходит сама, даже если ничего не делать.

# Срыв
Если человек закурил после паузы — никогда не стыди. Различай lapse \
(один эпизод) и relapse (полный возврат). Помоги нормализовать, понять \
триггер, продолжить путь. «Один срыв не отменяет твой прогресс».

# Безопасность
- Лекарства (НЗТ-пластыри/жвачки, варениклин/Чампикс, бупропион/Зибан) — \
рекомендуй обсудить с врачом, не назначай схемы и дозировки.
- Беременность + курение — особенно бережно, направляй к врачу.
- Признаки депрессии или мысли о суициде — мягко перенаправь к \
специалисту, упомяни телефон доверия 8-800-2000-122 (бесплатно по России).

# Стиль общения
- Тёплый, человечный, без морализаторства и пафоса.
- Короткие сообщения: 1–3 абзаца. В кризисе — ещё короче.
- Открытые вопросы вместо советов сверху: «как ты сейчас?», \
«что помогало тебе раньше?».
- Эмодзи редко и к месту, не для украшения.
- Русский язык.
- Markdown: **жирный**, *курсив*, `код`, [ссылка](url), списки. Без HTML.

# Представление
Если в истории нет твоих сообщений — коротко представься. \
Если уже общались — не представляйся повторно.

# Контекст пользователя
{user_context}
"""


async def build_user_context(user_id: int) -> str:
    """Собирает блок с актуальными данными пользователя для system prompt."""
    user = await db.get_user(user_id)
    if not user:
        return "Данных о пользователе пока нет."

    name = user.get("first_name") or "пользователь"
    lines = [f"Имя: {name}"]

    quit_date_raw = user.get("quit_date")
    if quit_date_raw:
        quit_date = datetime.fromisoformat(quit_date_raw)
        delta = datetime.now() - quit_date
        if delta.total_seconds() < 0:
            lines.append(
                f"Дата отказа запланирована на {quit_date.strftime('%d.%m.%Y')} "
                "(пользователь ещё не бросил)."
            )
        else:
            cigs = calculate_cigarettes_not_smoked(user, delta)
            saved = calculate_savings(user, delta)
            lines.append(f"Не курит: {format_duration(delta)}")
            lines.append(f"Не выкурено сигарет: {cigs}")
            lines.append(f"Сэкономлено: {saved:.0f} ₽")
    else:
        lines.append("Дата отказа ещё не установлена.")

    cpd = user.get("cigarettes_per_day")
    if cpd:
        lines.append(f"Курил(а) до отказа: {cpd} сигарет в день.")

    lines.append(
        "Используй эти цифры, чтобы поддержать и персонализировать ответ, "
        "но не вываливай их все сразу — упоминай уместно."
    )
    return "\n".join(lines)


def build_system_prompt(user_context: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(user_context=user_context)


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

    user_context = await build_user_context(user_id)
    system_prompt = build_system_prompt(user_context)

    waiting_msg = await message.answer("🤖 Думаю...")

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

        # Сохраняем оригинальный ответ ассистента (в Markdown) в БД
        await db.add_ai_chat_message(user_id, "assistant", ai_text)
        await db.increment_ai_usage(user_id)

        # Конвертируем стандартный Markdown в Telegram MarkdownV2
        # с корректным экранированием всех спецсимволов и добавляем
        # подпись ассистента жирным сверху.
        ai_text_md = telegramify_markdown.markdownify(
            f"**ИИ-Ассистент Лена**\n\n{ai_text}"
        )

        # Отправляем с поддержкой MarkdownV2
        if len(ai_text_md) > 4000:
            await waiting_msg.delete()
            for i in range(0, len(ai_text_md), 4000):
                await message.answer(ai_text_md[i:i+4000], parse_mode="MarkdownV2")
        else:
            await waiting_msg.edit_text(ai_text_md, parse_mode="MarkdownV2")

    except Exception as e:
        logger.error(f"Ошибка ИИ-помощника: {e}")
        try:
            await waiting_msg.edit_text("😔 К сожалению, я временно не могу ответить. Попробуйте еще раз позже.")
        except Exception:
            await message.answer("😔 Произошла ошибка. Попробуйте позже.")

    await state.clear()
    await message.answer("Желаете задать еще один вопрос?", reply_markup=get_ai_keyboard())
