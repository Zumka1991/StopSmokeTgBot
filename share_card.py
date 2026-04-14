"""Генерация карточки прогресса для шаринга"""

from PIL import Image, ImageDraw, ImageFont
from datetime import timedelta
import os


def create_share_card(
    first_name: str,
    delta: timedelta,
    savings: float,
    cigarettes: int,
    quit_date_str: str,
    output_path: str = "data/share_card.png"
) -> str:
    """Создать карточку прогресса"""

    # Параметры
    WIDTH = 1080
    PADDING = 60
    LINE_HEIGHT = 80

    # Определяем высоту
    days = delta.days
    hours = delta.seconds // 3600

    # Цвета
    BG_COLOR = "#1a1a2e"
    ACCENT_COLOR = "#00d4ff"
    TEXT_COLOR = "#ffffff"
    SUB_COLOR = "#a0a0b0"
    CARD_COLOR = "#16213e"

    # Создаём изображение
    img = Image.new('RGB', (WIDTH, 1400), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Шрифты
    try:
        font_title = ImageFont.truetype("arial.ttf", 72)
        font_subtitle = ImageFont.truetype("arial.ttf", 42)
        font_value = ImageFont.truetype("arial.ttf", 96)
        font_label = ImageFont.truetype("arial.ttf", 36)
        font_date = ImageFont.truetype("arial.ttf", 32)
    except:
        # Fallback на дефолтные шрифты
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_value = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_date = ImageFont.load_default()

    # Заголовок
    y = PADDING
    draw.text((PADDING, y), "🚭 StopSmoke Bot", fill=ACCENT_COLOR, font=font_title)

    # Подзаголовок
    y += 100
    draw.text((PADDING, y), f"{first_name} бросает курить!", fill=TEXT_COLOR, font=font_subtitle)

    # Основной блок — дни
    y += 120
    card_height = 300
    draw.rounded_rectangle(
        [PADDING, y, WIDTH - PADDING, y + card_height],
        radius=30,
        fill=CARD_COLOR
    )

    # Дни
    days_text = f"{days}"
    days_w = draw.textlength(days_text, font=font_value)
    draw.text(((WIDTH - days_w) / 2, y + 40), days_text, fill=ACCENT_COLOR, font=font_value)

    days_label = "дней без сигарет"
    days_l_w = draw.textlength(days_label, font=font_label)
    draw.text(((WIDTH - days_l_w) / 2, y + 150), days_label, fill=SUB_COLOR, font=font_label)

    hours_text = f"{hours} часов"
    hours_w = draw.textlength(hours_text, font=font_label)
    draw.text(((WIDTH - hours_w) / 2, y + 210), hours_text, fill=SUB_COLOR, font=font_label)

    # Дата отказа
    y += card_height + 30
    date_text = f"📅 Дата отказа: {quit_date_str}"
    date_w = draw.textlength(date_text, font=font_date)
    draw.text(((WIDTH - date_w) / 2, y), date_text, fill=SUB_COLOR, font=font_date)

    # Статистика — 2 колонки
    y += 80
    col_width = (WIDTH - PADDING * 2 - 40) / 2

    # Левая колонка — сэкономлено
    draw.rounded_rectangle(
        [PADDING, y, PADDING + col_width, y + 200],
        radius=20,
        fill=CARD_COLOR
    )
    money_text = f"{savings:,.0f}₽"
    money_w = draw.textlength(money_text, font=font_value)
    draw.text((PADDING + (col_width - money_w) / 2, y + 30), money_text, fill="#4ade80", font=font_value)
    money_label = "сэкономлено"
    money_l_w = draw.textlength(money_label, font=font_label)
    draw.text((PADDING + (col_width - money_l_w) / 2, y + 130), money_label, fill=SUB_COLOR, font=font_label)

    # Правая колонка — не выкурено
    right_x = PADDING + col_width + 40
    draw.rounded_rectangle(
        [right_x, y, right_x + col_width, y + 200],
        radius=20,
        fill=CARD_COLOR
    )
    cig_text = f"{cigarettes:,}"
    cig_w = draw.textlength(cig_text, font=font_value)
    draw.text((right_x + (col_width - cig_w) / 2, y + 30), cig_text, fill="#f97316", font=font_value)
    cig_label = "сигарет не выкурено"
    cig_l_w = draw.textlength(cig_label, font=font_label)
    draw.text((right_x + (col_width - cig_l_w) / 2, y + 130), cig_label, fill=SUB_COLOR, font=font_label)

    # Прогресс-бар здоровья (условно до 1 года)
    y += 260
    progress_label = "Прогресс до 1 года:"
    prog_l_w = draw.textlength(progress_label, font=font_label)
    draw.text((PADDING, y), progress_label, fill=SUB_COLOR, font=font_label)

    y += 50
    bar_width = WIDTH - PADDING * 2
    bar_height = 30
    progress = min(100, (days / 365) * 100)
    filled = int(bar_width * progress / 100)

    draw.rounded_rectangle(
        [PADDING, y, WIDTH - PADDING, y + bar_height],
        radius=15,
        fill="#2a2a4a"
    )
    if filled > 0:
        draw.rounded_rectangle(
            [PADDING, y, PADDING + filled, y + bar_height],
            radius=15,
            fill=ACCENT_COLOR
        )

    y += 50
    percent_text = f"{progress:.1f}%"
    percent_w = draw.textlength(percent_text, font=font_label)
    draw.text(((WIDTH - percent_w) / 2, y), percent_text, fill=ACCENT_COLOR, font=font_label)

    # Футер
    y += 80
    footer_text = "💪 Присоединяйся!"
    footer_w = draw.textlength(footer_text, font=font_subtitle)
    draw.text(((WIDTH - footer_w) / 2, y), footer_text, fill=ACCENT_COLOR, font=font_subtitle)

    # Сохраняем
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG", quality=95)

    return output_path
