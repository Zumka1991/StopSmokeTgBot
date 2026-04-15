"""
Утилитарные функции — форматирование, расчёты, экранирование.
"""
from datetime import timedelta


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


def escape_markdown(text: str) -> str:
    """Экранирование спецсимволов Markdown v1"""
    for char in ('_', '*', '`', '['):
        text = text.replace(char, f'\\{char}')
    return text


def escape_markdown_v2(text: str) -> str:
    """Экранирование спецсимволов Markdown v2 для ответов ИИ"""
    for char in ('_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'):
        text = text.replace(char, f'\\{char}')
    return text


def get_progress_bar(percent: float, length: int = 10) -> str:
    """Создание прогресс-бара"""
    filled = int(percent / 100 * length)
    empty = length - filled
    return "▓" * filled + "░" * empty
