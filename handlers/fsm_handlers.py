"""
FSM хендлеры — обработка состояний дневника и ИИ-ассистента.
"""
import logging
import re
import html
from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import dp, bot, client, OPENROUTER_MODEL
from keyboards import get_main_keyboard, get_ai_keyboard
import database as db
from states import DiaryState, AIState

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
    Тебя зовут Лена. У тебя женский пол. Ты — человечный и эмпатичный ассистент поддержки в Telegram боте 'StopSmoke'. Твой создатель - Мышонок.
    Твоя специализация — помощь людям в отказе от курения и борьбе с никотиновой зависимостью.

    Твои правила:
    1. Отвечай ТОЛЬКО на вопросы, связанные с курением, сигаретами, вейпами, никотином и процессом отказа от них.
    2. Если пользователь задает вопрос на другую тему, мягко и тепло объясни, что ты здесь только для поддержки в борьбе с курением.
    3. Тон общения: очень теплый, мягкий, поддерживающий и человечный. Избегай сухого академического стиля.
    4. Пиши информативно, чтобы человек понял суть. Если вопрос требует развернутого ответа, отвечай развернуто.
    5. Общайся на русском языке.
    6. Постарайся мотивировать пользователей на то, чтобы не сорваться.
    7. Используй HTML-теги для форматирования: <b>жирный</b>, <i>курсив</i>. НЕ ИСПОЛЬЗУЙ Markdown (никаких ** или _).
    8. Представляйся при первом сообщении.
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

        # Экранируем HTML спецсимволы, чтобы не сломать parse_mode="HTML"
        ai_text = html.escape(ai_text)

        # Преобразуем **текст** в <b>текст</b> для надежности жирного шрифта в HTML
        ai_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", ai_text)
        # Также преобразуем _курсив_
        ai_text = re.sub(r"_(.*?)_", r"<i>\1</i>", ai_text)
        # Преобразуем `код` и <code>код</code> в <b>жирный</b> по просьбе пользователя
        ai_text = re.sub(r"`(.*?)`", r"<b>\1</b>", ai_text)
        ai_text = re.sub(r"&lt;code&gt;(.*?)&lt;/code&gt;", r"<b>\1</b>", ai_text)

        # Сохраняем ответ ассистента в БД
        await db.add_ai_chat_message(user_id, "assistant", ai_text)
        await db.increment_ai_usage(user_id)

        # Отправляем с поддержкой HTML
        if len(ai_text) > 4000:
            await waiting_msg.delete()
            for i in range(0, len(ai_text), 4000):
                await message.answer(ai_text[i:i+4000], parse_mode="HTML")
        else:
            await waiting_msg.edit_text(ai_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка ИИ-помощника: {e}")
        try:
            await waiting_msg.edit_text("😔 К сожалению, я временно не могу ответить. Попробуйте еще раз позже.")
        except Exception:
            await message.answer("😔 Произошла ошибка. Попробуйте позже.")

    await state.clear()
    await message.answer("Желаете задать еще один вопрос?", reply_markup=get_ai_keyboard())
