from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Мой прогресс"),
                KeyboardButton(text="🏆 Рейтинг")
            ],
            [
                KeyboardButton(text="💪 Мотивация"),
                KeyboardButton(text="🎯 Достижения")
            ],
            [
                KeyboardButton(text="📓 Дневник"),
                KeyboardButton(text="⚙️ Настройки")
            ],
            [
                KeyboardButton(text="🌐 Сообщество"),
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для начала"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚀 Начать сейчас!",
                callback_data="start_now"
            )
        ],
        [
            InlineKeyboardButton(
                text="📅 Выбрать дату",
                callback_data="choose_date"
            )
        ]
    ])
    return keyboard


def get_settings_keyboard(notifications_enabled: bool, rating_visible: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    notif_text = "🔔 Уведомления: ВКЛ" if notifications_enabled else "🔕 Уведомления: ВЫКЛ"
    rating_text = "👁️ Видимость в рейтинге: ВКЛ" if rating_visible else "🙈 Видимость в рейтинге: ВЫКЛ"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📅 Дата отказа",
                callback_data="set_quit_date"
            )
        ],
        [
            InlineKeyboardButton(
                text=notif_text,
                callback_data="toggle_notifications"
            )
        ],
        [
            InlineKeyboardButton(
                text=rating_text,
                callback_data="toggle_rating_visibility"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚬 Сигарет в день",
                callback_data="set_cigarettes"
            )
        ],
        [
            InlineKeyboardButton(
                text="💵 Цена пачки",
                callback_data="set_price"
            )
        ],
        [
            InlineKeyboardButton(
                text="📦 Сигарет в пачке",
                callback_data="set_pack_size"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Начать заново",
                callback_data="reset_progress"
            )
        ]
    ])
    return keyboard


def get_confirm_reset_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения сброса"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да, начать заново",
                callback_data="confirm_reset"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_reset"
            )
        ]
    ])
    return keyboard


def get_rating_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения участия в рейтинге"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить участие",
                callback_data="confirm_rating"
            ),
            InlineKeyboardButton(
                text="🙈 Скрыть из рейтинга",
                callback_data="hide_from_rating"
            )
        ]
    ])
    return keyboard


def get_diary_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню дневника"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✏️ Добавить запись",
                callback_data="diary_add"
            )
        ],
        [
            InlineKeyboardButton(
                text="📖 Прочитать записи",
                callback_data="diary_read"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Удалить записи",
                callback_data="diary_delete"
            )
        ]
    ])
    return keyboard


def get_diary_dates_keyboard(dates: list) -> InlineKeyboardMarkup:
    """Клавиатура с датами записей"""
    buttons = []
    for date_str in dates:
        buttons.append([
            InlineKeyboardButton(
                text=f"📅 {date_str}",
                callback_data=f"diary_date_{date_str}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="diary_menu"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_diary_delete_date_keyboard(dates: list) -> InlineKeyboardMarkup:
    """Клавиатура с датами для удаления"""
    buttons = []
    for date_str in dates:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑️ {date_str}",
                callback_data=f"diary_del_date_{date_str}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="diary_menu"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_diary_confirm_delete_keyboard(date_str: str) -> InlineKeyboardMarkup:
    """Подтверждение удаления записей за дату"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да, удалить",
                callback_data=f"diary_del_confirm_{date_str}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="diary_delete"
            )
        ]
    ])
    return keyboard


def get_relapse_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для срыва"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="😔 Я сорвался",
                callback_data="relapse"
            ),
            InlineKeyboardButton(
                text="📤 Поделиться",
                callback_data="share_result"
            )
        ],
        [
            InlineKeyboardButton(
                text="💪 Нет, я держусь!",
                callback_data="stay_strong"
            )
        ]
    ])
    return keyboard


def get_rating_keyboard(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """Клавиатура навигации рейтинга"""
    buttons = []
    nav_row = []

    if has_prev:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"rating_prev_{page}"
            )
        )

    if has_next:
        nav_row.append(
            InlineKeyboardButton(
                text="▶️ Вперёд",
                callback_data=f"rating_next_{page}"
            )
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="back_to_main"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_settings"
            )
        ]
    ])
    return keyboard


def get_number_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура для выбора числа"""
    buttons = []
    row = []

    numbers = [5, 10, 15, 20, 25, 30, 40, 50, 60]

    for i, num in enumerate(numbers):
        row.append(
            InlineKeyboardButton(
                text=str(num),
                callback_data=f"{callback_prefix}_{num}"
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_settings"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_price_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора цены"""
    prices = [100, 150, 200, 250, 300, 350, 400, 500, 600]
    buttons = []
    row = []

    for price in prices:
        row.append(
            InlineKeyboardButton(
                text=f"{price}₽",
                callback_data=f"price_{price}"
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_settings"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
