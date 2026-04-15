import logging
import traceback
from datetime import datetime, timedelta

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from config import dp, bot
from utils import format_duration, calculate_savings, calculate_cigarettes_not_smoked, escape_markdown
from keyboards import (
    get_start_keyboard,
    get_main_keyboard,
    get_settings_keyboard,
    get_confirm_reset_keyboard,
    get_relapse_keyboard,
    get_number_keyboard,
    get_price_keyboard,
    get_back_keyboard,
    get_rating_keyboard,
    get_diary_menu_keyboard,
    get_diary_dates_keyboard,
    get_diary_delete_date_keyboard,
    get_diary_confirm_delete_keyboard,
    get_ai_keyboard,
    get_tracking_menu_keyboard,
    get_tracking_subs_keyboard,
    get_tracking_watchers_keyboard,
    get_friend_progress_keyboard,
    get_inbox_message_keyboard,
)
from quotes import get_random_quote
from share_card import create_share_card
import database as db
from states import DiaryState, AIState, TrackingState

from handlers.commands import show_rating_page


# ============ CALLBACK HANDLERS ============

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

    # Уведомляем подтверждённых подписчиков о срыве.
    await _notify_watchers_about_relapse(callback.from_user)


async def _notify_watchers_about_relapse(target_user) -> None:
    """Шлёт всем confirmed-наблюдателям уведомление о срыве target_user.

    target_user — aiogram.User: ожидаются поля id, first_name, username.
    Тихо логирует ошибки, не падает целиком если один получатель недоступен.
    """
    target_id = target_user.id
    try:
        watcher_ids = await db.get_confirmed_watcher_ids(target_id)
    except Exception as e:
        logger.error(f"Не удалось получить watchers для {target_id}: {e}")
        return

    if not watcher_ids:
        return

    name = target_user.first_name or target_user.username or "Твой подопечный"
    handle = f"@{target_user.username}" if target_user.username else ""
    title_user = escape_markdown(name) + (f" ({escape_markdown(handle)})" if handle else "")

    text = (
        "💔 *Срыв у того, за кем ты следишь*\n\n"
        f"{title_user} только что отметил срыв и начал отсчёт заново.\n\n"
        "Это не провал — это часть пути. Если можешь, напиши ему сейчас "
        "пару тёплых слов поддержки. В такие моменты это особенно важно."
    )

    kb = get_inbox_message_keyboard(target_id)
    for wid in watcher_ids:
        try:
            await bot.send_message(wid, text, reply_markup=kb)
        except Exception as e:
            logger.warning(f"Не доставлено уведомление о срыве watcher={wid} target={target_id}: {e}")


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


# ============ ДНЕВНИК ============

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


# ============ ИИ ПОДДЕРЖКА ============

@dp.callback_query(F.data == "ask_ai")
async def callback_ask_ai(callback: CallbackQuery, state: FSMContext):
    """Начало диалога с ИИ"""
    user_id = callback.from_user.id
    has_access = await db.has_user_ai_access(user_id)

    if not has_access:
        # Получаем инфо о боте для ссылки
        bot_info = await bot.get_me()
        user_id = callback.from_user.id
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

        await callback.message.edit_text(
            "🔒 *Доступ ограничен*\n\n"
            "ИИ-ассистент доступен только тем, кто пригласил хотя бы одного друга.\n\n"
            f"🔗 *Ваша ссылка для приглаения:*\n`{ref_link}`\n\n"
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


@dp.callback_query(F.data == "show_ref_link")
async def callback_show_ref_link(callback: CallbackQuery):
    """Показ реферальной ссылки"""
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    await callback.message.answer(
        "🚀 *Ваша пригласительная ссылка:*\n\n"
        f"`{ref_link}`\n\n"
        "Отправьте её другу, и как только он запустит бота, вам откроется доступ к ИИ-ассистенту! 💪"
    )
    await callback.answer()


# ============ ОТСЛЕЖИВАНИЕ ПРОГРЕССА ============

@dp.callback_query(F.data == "track_menu")
async def callback_track_menu(callback: CallbackQuery, state: FSMContext):
    """Меню отслеживания: добавить, мои подписки, мои наблюдатели."""
    await state.clear()
    user_id = callback.from_user.id
    subs = await db.get_my_subscriptions(user_id)
    watchers = await db.get_my_watchers(user_id)
    blocked = await db.is_tracking_blocked(user_id)
    confirmed_subs = sum(1 for s in subs if s["status"] == "confirmed")
    pending_subs = sum(1 for s in subs if s["status"] == "pending")
    confirmed_watchers = sum(1 for w in watchers if w["status"] == "confirmed")

    block_line = (
        "🚫 *Приём наблюдателей: ВЫКЛ* — новые запросы отклоняются автоматически."
        if blocked
        else "🛡 *Приём наблюдателей: ВКЛ* — другие могут отправлять тебе запросы."
    )

    text = (
        "👥 *Отслеживание прогресса друга*\n\n"
        "Взаимная поддержка: ты можешь следить за прогрессом друга и видеть "
        "его статистику, а если он сорвётся — тебе придёт уведомление, чтобы "
        "вовремя поддержать.\n\n"
        f"📋 Ты следишь: *{confirmed_subs}* (ожидают ответа: {pending_subs})\n"
        f"👀 За тобой следят: *{confirmed_watchers}*\n"
        f"{block_line}\n\n"
        "Что хочешь сделать?"
    )
    kb = get_tracking_menu_keyboard(
        has_subs=bool(subs),
        has_watchers=bool(watchers),
        blocked=blocked,
    )
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "track_toggle_block")
async def callback_track_toggle_block(callback: CallbackQuery):
    """Переключение блокировки прямо из меню (эквивалент /stopw)."""
    user_id = callback.from_user.id
    currently_blocked = await db.is_tracking_blocked(user_id)

    if currently_blocked:
        await db.set_tracking_blocked(user_id, False)
        await callback.message.answer(
            "✅ *Отслеживание снова разрешено.* Старые подписки не возвращаются автоматически.",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    await db.set_tracking_blocked(user_id, True)
    purged = await db.purge_watchers(user_id)
    target_display = callback.from_user.first_name or callback.from_user.username or "Пользователь"
    target_handle = f"@{callback.from_user.username}" if callback.from_user.username else ""

    notified = 0
    for wid in purged:
        try:
            handle_part = f" ({escape_markdown(target_handle)})" if target_handle else ""
            await bot.send_message(
                wid,
                f"🚫 *Отслеживание прекращено*\n\n"
                f"Пользователь *{escape_markdown(target_display)}*{handle_part} "
                "запретил отслеживание своего прогресса. Подписка снята автоматически."
            )
            notified += 1
        except Exception as e:
            logger.warning(f"toggle_block: не уведомили watcher={wid}: {e}")

    suffix = (
        f" Сняли {len(purged)} подписок, уведомили {notified}."
        if purged else " Активных подписок не было."
    )
    await callback.message.answer(
        "🛡 *Отслеживание запрещено.*" + suffix
        + "\n\nСнять блок: /stopw или эта же кнопка в меню.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer("Готово")


@dp.callback_query(F.data == "track_add")
async def callback_track_add(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод @username."""
    await state.set_state(TrackingState.waiting_for_username)
    await callback.message.answer(
        "✍️ Отправь *@username* того, за кем хочешь следить.\n\n"
        "Можно с собакой или без, можно ссылку `t.me/...`.\n"
        "Чтобы отменить — отправь `/cancel` или любую команду.",
    )
    await callback.answer()


@dp.callback_query(F.data == "track_my_subs")
async def callback_track_my_subs(callback: CallbackQuery):
    """Список 'За кем я слежу'."""
    user_id = callback.from_user.id
    subs = await db.get_my_subscriptions(user_id)
    if not subs:
        watchers = await db.get_my_watchers(user_id)
        blocked = await db.is_tracking_blocked(user_id)
        await callback.message.answer(
            "📋 Ты пока ни за кем не следишь.",
            reply_markup=get_tracking_menu_keyboard(False, bool(watchers), blocked)
        )
        await callback.answer()
        return

    lines = ["📋 *За кем ты следишь:*\n"]
    for s in subs:
        name = s.get("first_name") or s.get("username") or f"id{s['target_id']}"
        status_label = {
            "confirmed": "✅ подтверждено",
            "pending": "⏳ ждём ответа",
            "declined": "🚫 отклонено"
        }.get(s["status"], s["status"])
        suffix = ""
        if s["status"] == "confirmed" and s.get("quit_date"):
            try:
                qd = datetime.fromisoformat(s["quit_date"])
                d = datetime.now() - qd
                if d.total_seconds() > 0:
                    suffix = f" — {format_duration(d)} без сигарет"
            except Exception:
                pass
        lines.append(f"• *{escape_markdown(name)}* — {status_label}{escape_markdown(suffix)}")

    lines.append("\n_Жми на друга в списке ниже, чтобы посмотреть его прогресс._")

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=get_tracking_subs_keyboard(subs)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("track_view_"))
async def callback_track_view(callback: CallbackQuery):
    """Карточка прогресса друга — доступна только для confirmed-подписок."""
    try:
        target_id = int(callback.data.removeprefix("track_view_"))
    except ValueError:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    watcher_id = callback.from_user.id

    # Проверяем, что подписка существует и confirmed.
    subs = await db.get_my_subscriptions(watcher_id)
    sub = next((s for s in subs if s["target_id"] == target_id), None)
    if not sub:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    if sub["status"] != "confirmed":
        await callback.answer("Доступ к статистике появится после подтверждения", show_alert=True)
        return

    # Если за время подписки цель включила блок — закрываем доступ.
    if await db.is_tracking_blocked(target_id):
        await db.remove_subscription(watcher_id, target_id)
        await callback.message.answer(
            "🚫 Этот пользователь запретил отслеживание. Подписка снята.",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    target_user = await db.get_user(target_id)
    if not target_user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    name = target_user.get("first_name") or target_user.get("username") or "Друг"
    handle = f"@{target_user['username']}" if target_user.get("username") else ""
    handle_part = f" ({escape_markdown(handle)})" if handle else ""

    quit_date_raw = target_user.get("quit_date")
    if not quit_date_raw:
        text = (
            f"📊 *Прогресс: {escape_markdown(name)}*{handle_part}\n\n"
            "_Друг ещё не указал дату отказа от курения._\n"
            "Когда укажет — здесь появится статистика."
        )
    else:
        quit_date = datetime.fromisoformat(quit_date_raw)
        delta = datetime.now() - quit_date
        if delta.total_seconds() < 0:
            text = (
                f"📊 *Прогресс: {escape_markdown(name)}*{handle_part}\n\n"
                f"📅 Дата отказа запланирована: *{quit_date.strftime('%d.%m.%Y')}*\n"
                "Друг ещё не начал — подбодри его!"
            )
        else:
            duration = format_duration(delta)
            savings = calculate_savings(target_user, delta)
            cigarettes = calculate_cigarettes_not_smoked(target_user, delta)
            stats = await db.get_user_stats(target_id)
            attempts = stats.get("relapse_count", 0) + 1
            text = (
                f"📊 *Прогресс: {escape_markdown(name)}*{handle_part}\n\n"
                f"🕐 *Без сигарет:* {duration}\n"
                f"📅 *Дата отказа:* {quit_date.strftime('%d.%m.%Y')}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Сэкономлено:* {savings:,.0f}₽\n"
                f"🚬 *Не выкурено:* {cigarettes:,} сигарет\n"
                f"🔄 *Попытка №:* {attempts}\n\n"
                "_Если есть возможность — напиши пару слов поддержки, "
                "это помогает гораздо больше, чем кажется._"
            )

    await callback.message.answer(
        text,
        reply_markup=get_friend_progress_keyboard(target_id)
    )
    await callback.answer()


@dp.callback_query(F.data == "track_my_watchers")
async def callback_track_my_watchers(callback: CallbackQuery):
    """Список 'Кто следит за мной'."""
    user_id = callback.from_user.id
    watchers = await db.get_my_watchers(user_id)
    if not watchers:
        subs = await db.get_my_subscriptions(user_id)
        blocked = await db.is_tracking_blocked(user_id)
        await callback.message.answer(
            "👀 За тобой пока никто не следит.",
            reply_markup=get_tracking_menu_keyboard(bool(subs), False, blocked)
        )
        await callback.answer()
        return

    lines = ["👀 *Кто следит за тобой:*\n"]
    for w in watchers:
        name = w.get("first_name") or w.get("username") or f"id{w['watcher_id']}"
        status_label = {
            "confirmed": "✅ подтверждено",
            "pending": "⏳ ждёт твоего ответа",
            "declined": "🚫 ты отклонил"
        }.get(w["status"], w["status"])
        lines.append(f"• *{escape_markdown(name)}* — {status_label}")

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=get_tracking_watchers_keyboard(watchers)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("track_accept_"))
async def callback_track_accept(callback: CallbackQuery):
    """Цель принимает заявку наблюдателя."""
    try:
        watcher_id = int(callback.data.removeprefix("track_accept_"))
    except ValueError:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    target_id = callback.from_user.id
    ok = await db.respond_to_subscription(watcher_id, target_id, accept=True)
    if not ok:
        await callback.answer("Заявка уже неактуальна", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    target_display = callback.from_user.first_name or callback.from_user.username or "Пользователь"
    try:
        await callback.message.edit_text(
            "✅ Ты принял запрос на отслеживание. Этот человек будет получать "
            "уведомление, если ты отметишь срыв — он рядом, чтобы поддержать."
        )
    except Exception:
        pass
    await callback.answer("Принято!")

    # Уведомим наблюдателя — с кнопкой написать в благодарность.
    try:
        await bot.send_message(
            watcher_id,
            f"✅ *{escape_markdown(target_display)}* принял твой запрос на отслеживание. "
            "Теперь ты будешь видеть его прогресс и получишь уведомление, если он сорвётся.",
            reply_markup=get_inbox_message_keyboard(target_id)
        )
    except Exception as e:
        logger.warning(f"Не доставлено подтверждение watcher={watcher_id}: {e}")


@dp.callback_query(F.data.startswith("track_decline_"))
async def callback_track_decline(callback: CallbackQuery):
    """Цель отклоняет заявку."""
    try:
        watcher_id = int(callback.data.removeprefix("track_decline_"))
    except ValueError:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    target_id = callback.from_user.id
    ok = await db.respond_to_subscription(watcher_id, target_id, accept=False)
    target_display = callback.from_user.first_name or callback.from_user.username or "Пользователь"

    try:
        await callback.message.edit_text("❌ Запрос отклонён.")
    except Exception:
        pass
    await callback.answer()

    if ok:
        try:
            await bot.send_message(
                watcher_id,
                f"❌ *{escape_markdown(target_display)}* отклонил твой запрос на отслеживание."
            )
        except Exception as e:
            logger.warning(f"Не доставлено уведомление об отказе watcher={watcher_id}: {e}")


@dp.callback_query(F.data.startswith("track_unsub_"))
async def callback_track_unsub(callback: CallbackQuery):
    """Я отписываюсь от человека, за которым следил."""
    try:
        target_id = int(callback.data.removeprefix("track_unsub_"))
    except ValueError:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    watcher_id = callback.from_user.id
    removed = await db.remove_subscription(watcher_id, target_id)
    if removed:
        await callback.answer("Отписался")
        try:
            # Тихо уведомим бывшую цель — без алармизма.
            await bot.send_message(
                target_id,
                "ℹ️ Один из наблюдателей перестал следить за твоим прогрессом."
            )
        except Exception:
            pass
    else:
        await callback.answer("Подписка уже не существует", show_alert=True)
    # Перерисуем список.
    await callback_track_my_subs(callback)


@dp.callback_query(F.data.startswith("track_msg_"))
async def callback_track_msg(callback: CallbackQuery, state: FSMContext):
    """Запрос на отправку сообщения отслеживаемому юзеру (или ответ).

    Доступно если между текущим юзером и target есть подтверждённая
    подписка в любую сторону (watcher↔target).
    """
    try:
        recipient_id = int(callback.data.removeprefix("track_msg_"))
    except ValueError:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    sender_id = callback.from_user.id
    if recipient_id == sender_id:
        await callback.answer("Нельзя писать самому себе", show_alert=True)
        return

    if not await db.has_active_subscription_pair(sender_id, recipient_id):
        await callback.answer(
            "Нет активной подписки между вами — писать нельзя.",
            show_alert=True
        )
        return

    recipient = await db.get_user(recipient_id)
    name = (recipient or {}).get("first_name") or (recipient or {}).get("username") or "пользователю"

    await state.set_state(TrackingState.waiting_for_message)
    await state.update_data(recipient_id=recipient_id)

    await callback.message.answer(
        f"💬 *Сообщение для {escape_markdown(name)}*\n\n"
        "Напиши текст одним сообщением — я доставлю.\n"
        "Лимит: 1000 символов. Отмена — /cancel или любая команда.",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("track_kick_"))
async def callback_track_kick(callback: CallbackQuery):
    """Я удаляю наблюдателя, который следил за мной."""
    try:
        watcher_id = int(callback.data.removeprefix("track_kick_"))
    except ValueError:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    target_id = callback.from_user.id
    removed = await db.remove_subscription(watcher_id, target_id)
    if removed:
        await callback.answer("Удалён")
        try:
            await bot.send_message(
                watcher_id,
                "ℹ️ Пользователь, за которым ты следил, отозвал доступ к своему прогрессу."
            )
        except Exception:
            pass
    else:
        await callback.answer("Запись уже не существует", show_alert=True)
    await callback_track_my_watchers(callback)
