"""Генерация премиальной карточки прогресса для шаринга"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import timedelta, datetime
import os
import logging
import platform

logger = logging.getLogger(__name__)

# Пути к шрифтам
FONT_PATHS = {
    "win": {
        "regular": "C:/Windows/Fonts/segoeui.ttf",
        "bold": "C:/Windows/Fonts/segoeuib.ttf",
        "emoji": "C:/Windows/Fonts/seguiemj.ttf"
    },
    "linux": {
        "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
        "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
        "emoji": ["/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"]
    }
}

def get_font_path(type_key: str) -> str:
    os_name = platform.system().lower()
    if "windows" in os_name: return FONT_PATHS["win"][type_key]
    paths = FONT_PATHS["linux"][type_key]
    for p in paths:
        if os.path.exists(p): return p
    return paths[0]

def get_font(type_key: str, size: int) -> ImageFont.FreeTypeFont:
    try: return ImageFont.truetype(get_font_path(type_key), size)
    except: return ImageFont.load_default()

def draw_mesh_background(width: int, height: int):
    base = Image.new('RGBA', (width, height), (7, 10, 19, 255))
    glow = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    def dg(cx, cy, r, c):
        for i in range(r, 0, -5):
            a = int(c[3] * (1 - (i/r)**1.5))
            d.ellipse([cx-i, cy-i, cx+i, cy+i], fill=(c[0], c[1], c[2], a))
    dg(width*0.8, height*0.1, 950, (14, 165, 233, 45))
    dg(width*0.1, height*0.9, 850, (16, 185, 129, 38))
    glow_filtered = glow.filter(ImageFilter.GaussianBlur(65))
    base.alpha_composite(glow_filtered)
    return base

def draw_glass_card(img: Image.Image, x, y, w, h, radius=40):
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    region = img.crop((x, y, x+w, y+h)).filter(ImageFilter.GaussianBlur(40))
    overlay = Image.new('RGBA', (w, h), (255, 255, 255, 15))
    img.paste(Image.alpha_composite(region, overlay), (x, y), mask)
    b_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(b_layer).rounded_rectangle([x, y, x+w, y+h], radius=radius, outline=(255, 255, 255, 35), width=2)
    img.alpha_composite(b_layer)

def create_ultra_minimal_logo(size=300):
    badge = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(badge)
    for i in range(15):
        alpha = int(20 * (1 - i/15))
        d.rounded_rectangle([15-i, 15-i, size-5+i, size-5+i], radius=70+i, fill=(0, 0, 0, alpha))
    d.rounded_rectangle([10, 10, size-10, size-10], radius=65, fill=(255, 255, 255, 255))
    LOGO_V3 = "data/logo_v3.png"
    if os.path.exists(LOGO_V3):
        try:
            icon = Image.open(LOGO_V3).convert('RGBA')
            pad = 50
            icon_size = size - pad * 2
            icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            badge.paste(icon, (pad, pad), icon)
        except:
            pass
    return badge

def create_share_card(first_name, delta, savings, cigarettes, quit_date_str, output_path="data/share_card.png"):
    WIDTH, HEIGHT = 1080, 1920
    PADDING = 80
    img = draw_mesh_background(WIDTH, HEIGHT)
    draw = ImageDraw.Draw(img, 'RGBA')

    f_h1 = get_font("bold", 76); f_days = get_font("bold", 240); f_label = get_font("regular", 44)
    f_stat_v = get_font("bold", 68); f_stat_l = get_font("regular", 30)
    f_emoji = get_font("emoji", 48)

    logo_size = 300
    logo = create_ultra_minimal_logo(logo_size)
    img.paste(logo, ((WIDTH - logo_size) // 2, 100), logo)

    bbox = draw.textbbox((0, 0), first_name, font=f_h1)
    draw.text(((WIDTH - (bbox[2]-bbox[0])) / 2, 450), first_name, fill=(255, 255, 255, 255), font=f_h1)
    sub = "на пути к здоровью"; bbox = draw.textbbox((0, 0), sub, font=f_label)
    draw.text(((WIDTH - (bbox[2]-bbox[0])) / 2, 540), sub, fill=(148, 163, 184, 255), font=f_label)

    days = delta.days; cy, ch = 650, 480
    draw_glass_card(img, PADDING, cy, WIDTH - PADDING * 2, ch)
    txt_d = str(days); bbox = draw.textbbox((0, 0), txt_d, font=f_days)
    draw.text(((WIDTH - (bbox[2]-bbox[0])) / 2, cy + 30), txt_d, fill=(255, 255, 255, 255), font=f_days)
    
    if 11 <= days % 100 <= 14: dw = "ДНЕЙ"
    elif days % 10 == 1: dw = "ДЕНЬ"
    elif 2 <= days % 10 <= 4: dw = "ДНЯ"
    else: dw = "ДНЕЙ"
    lbl = f"{dw} БЕЗ СИГАРЕТ"; bbox = draw.textbbox((0, 0), lbl, font=get_font("bold", 52))
    draw.text(((WIDTH - (bbox[2]-bbox[0])) / 2, cy + 300), lbl, fill=(56, 189, 248, 255), font=get_font("bold", 52))
    h_txt = f"и {delta.seconds // 3600} часов свободы"; bbox = draw.textbbox((0, 0), h_txt, font=f_label)
    draw.text(((WIDTH - (bbox[2]-bbox[0])) / 2, cy + 390), h_txt, fill=(148, 163, 184, 255), font=f_label)

    sy, sw, sh = 1180, (WIDTH - PADDING * 2 - 40) // 2, 260
    st_data = [{"v": f"{savings:,.0f}₽", "l": "Сэкономлено", "i": "💰"}, {"v": f"{cigarettes:,}", "l": "Не выкурено", "i": "🚭"}, {"v": f"{int(cigarettes * 5 / 60)}ч", "l": "Жизни спасено", "i": "❤️"}, {"v": f"{quit_date_str}", "l": "Дата старта", "i": "📅"}]
    for i, s in enumerate(st_data):
        sx, scy = PADDING + (i%2)*(sw+40), sy + (i//2)*(sh+40)
        draw_glass_card(img, sx, scy, sw, sh, radius=35)
        v_b = draw.textbbox((0,0), s["v"], font=f_stat_v); draw.text((sx+(sw-(v_b[2]-v_b[0]))/2, scy+80), s["v"], fill=(255,255,255,255), font=f_stat_v)
        l_b = draw.textbbox((0,0), s["l"], font=f_stat_l); draw.text((sx+(sw-(l_b[2]-l_b[0]))/2, scy+170), s["l"], fill=(148, 163, 184, 255), font=f_stat_l)
        draw.text((sx+30, scy+25), s["i"], fill=(255,255,255,255), font=f_emoji)

    py = 1780; draw.text((PADDING, py), "Прогресс до 1 года", fill=(148, 163, 184, 255), font=f_stat_l)
    draw.rounded_rectangle([PADDING, py+60, WIDTH-PADDING, py+88], radius=14, fill=(30, 41, 59, 255))
    pct = min(100, (days / 365) * 100)
    if pct > 0: draw.rounded_rectangle([PADDING, py+60, PADDING + int((WIDTH-PADDING*2)*pct/100), py+88], radius=14, fill=(14, 165, 233, 255))
    
    p = os.path.abspath(output_path); os.makedirs(os.path.dirname(p), exist_ok=True)
    img.convert('RGB').save(p, "PNG", quality=95)
    return p
