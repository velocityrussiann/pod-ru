"""
VELOCITY RUSSIAN PODCAST GENERATOR
15-min bilingual Russian/English podcast at A2 level
2 hosts: Anna & Ivan
"""
import os, sys, json, asyncio, subprocess, random, requests, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL") or "openai"

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"

HOST1_VOICE = "ru-RU-SvetlanaNeural"
HOST2_VOICE = "ru-RU-DmitryNeural"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

TOPICS = [
    "Путешествие в новую страну - Traveling to a new country",
    "Традиционная еда - Traditional food",
    "Повседневный распорядок - Daily routine",
    "Праздники и торжества - Holidays and celebrations",
    "Погода и времена года - Weather and seasons",
    "Семья и друзья - Family and friends",
    "Музыка и фильмы - Music and movies",
    "Спорт и тренировки - Sports and exercise",
    "Идеальный город - The ideal city",
    "Изучение языков - Learning languages",
    "Выходные - The weekend",
    "Покупки и одежда - Shopping and clothes",
    "Общественный транспорт - Public transport",
    "В ресторане - At the restaurant",
    "Здоровье и благополучие - Health and wellness",
]

YELLOW = (247, 202, 0)
DARK_BG = (11, 14, 27)
WHITE = (255, 255, 255)
LIGHT_GRAY = (170, 180, 205)
DARK_LINE = (50, 55, 75)

def load_font(size, bold=False, italic=False):
    fonts_to_try = []
    if italic and bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuiz.ttf", "C:/Windows/Fonts/arialbi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf",
            str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf"),
        ])
    elif italic:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuii.ttf", "C:/Windows/Fonts/ariali.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
            str(FONTS_DIR / "DejaVuSans-Oblique.ttf"),
        ])
    elif bold:
        fonts_to_try.extend([
            str(FONTS_DIR / "DejaVuSans-Bold.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/Inter-Bold-slnt=0.ttf", "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    else:
        fonts_to_try.extend([
            str(FONTS_DIR / "DejaVuSans.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/Inter-Regular-slnt=0.ttf", "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ])

    for fp in fonts_to_try:
        if Path(fp).exists():
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def clean_text(text):
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\b(mm+|um+|uh+|ah+|äh+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

ROMAN_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
}

def romanize_russian(text):
    """Transliterate Cyrillic Russian to Latin (heuristic fallback)."""
    if not text:
        return text
    out = []
    for ch in text:
        out.append(ROMAN_MAP[ch] if ch in ROMAN_MAP else ch)
    roman = ''.join(out)
    return re.sub(r'\s+', ' ', roman).strip()

def sanitize_translit(text):
    """Drop non-Latin chars from transliteration so no tofu glyphs appear (font is Latin-only)."""
    if not text:
        return text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    out = []
    for ch in text:
        o = ord(ch)
        if 0x20 <= o <= 0x7E or o in (0x0A, 0x0D):
            out.append(ch)
        else:
            out.append(' ')
    return re.sub(r'\s+', ' ', ''.join(out)).strip()

def _wrap_latin(text, font, max_w, draw):
    """Wrap latin text into lines, each <= max_w."""
    words = text.split()
    lines, cur = [], []
    for w in words:
        t = ' '.join(cur + [w])
        bb = draw.textbbox((0, 0), t, font=font)
        if bb[2] - bb[0] <= max_w or not cur:
            cur.append(w)
        else:
            if cur:
                lines.append(' '.join(cur))
            cur = [w]
    if cur:
        lines.append(' '.join(cur))
    return lines

def _wrap_any(text, font, max_w, draw):
    """Wrap any text (Cyrillic ok) into lines, each <= max_w."""
    return _wrap_latin(text, font, max_w, draw)

def _translit_ink_height(font, lines):
    """Measured ink height of the (already-wrapped) translit lines."""
    if not lines:
        return 0
    from PIL import Image as _I, ImageDraw as _D
    tmp = _I.new('RGB', (1920, 200), (0, 0, 0))
    tdraw = _D.Draw(tmp)
    lh = int(font.size * 1.3)
    bb = tdraw.textbbox((0, 0), lines[0], font=font)
    first_ink = bb[3] - bb[1]
    return (len(lines) - 1) * lh + first_ink

def draw_translit(draw, text, center_y, font, max_w=1350, line_height=52):
    """Draw transliteration (latin italic) centered, like english translation."""
    lines = _wrap_latin(text, font, max_w, draw)
    if not lines:
        return 0, 0
    total_h = len(lines) * line_height
    start_y = center_y - total_h // 2
    ink_min_top = None
    ink_max = None
    for idx, line in enumerate(lines):
        lx = VIDEO_WIDTH // 2
        ly = start_y + idx * line_height + line_height // 2
        draw.text((lx, ly), line, fill=LIGHT_GRAY, font=font, anchor="mm")
        bb = draw.textbbox((lx, ly), line, font=font, anchor="mm")
        ink_min_top = bb[1] if ink_min_top is None else min(ink_min_top, bb[1])
        ink_max = bb[3] if ink_max is None else max(ink_max, bb[3])
    return ink_min_top or start_y, ink_max or start_y + total_h

def auto_highlight_russian(text):
    stopwords = {'и', 'в', 'на', 'с', 'по', 'для', 'что', 'это', 'как', 'я', 'ты', 'он', 'она', 'мы', 'вы', 'они', 'не', 'но', 'если', 'когда', 'очень'}
    if '**' in text:
        return text
    words = text.split()
    candidates = []
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[^\w\u0400-\u04FF\u00E0-\u00F6\u00F8-\u00FF\'’]', '', w, flags=re.UNICODE)
        if clean_w.lower() not in stopwords and len(clean_w) >= 3:
            candidates.append((len(clean_w), idx, w, clean_w))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_idx = candidates[0][1]
        raw_w = words[best_idx]
        clean_w = candidates[0][3]
        highlighted = raw_w.replace(clean_w, f"**{clean_w}**")
        words[best_idx] = highlighted
        return " ".join(words)
    return text

def draw_microphone_icon(draw, center_x, center_y, radius=24):
    draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                 outline=YELLOW, width=3)
    w, h = 10, 18
    draw.rounded_rectangle([center_x - w//2, center_y - 12, center_x + w//2, center_y - 12 + h],
                           radius=4, fill=YELLOW)
    draw.arc([center_x - 10, center_y - 4, center_x + 10, center_y + 12],
             start=0, end=180, fill=YELLOW, width=3)
    draw.line([(center_x, center_y + 12), (center_x, center_y + 17)], fill=YELLOW, width=3)
    draw.line([(center_x - 7, center_y + 17), (center_x + 7, center_y + 17)], fill=YELLOW, width=3)

def draw_person_icon(draw, center_x, center_y):
    draw.ellipse([center_x - 6, center_y - 12, center_x + 6, center_y], fill=YELLOW)
    draw.chord([center_x - 12, center_y + 2, center_x + 12, center_y + 20],
               start=180, end=360, fill=YELLOW)

def draw_russian_flag(img, draw, center_x, center_y, radius=22):
    flag_img = Image.new('RGBA', (radius*2, radius*2), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(flag_img)
    # Russian flag: white top, blue middle, red bottom
    h = radius * 2
    fdraw.rectangle([(0, 0), (radius*2, int(h * 0.33))], fill=(255, 255, 255, 255))
    fdraw.rectangle([(0, int(h * 0.33)), (radius*2, int(h * 0.66))], fill=(0, 57, 166, 255))
    fdraw.rectangle([(0, int(h * 0.66)), (radius*2, h)], fill=(213, 43, 30, 255))
    
    mask = Image.new('L', (radius*2, radius*2), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, radius*2, radius*2], fill=255)
    img.paste(flag_img, (center_x - radius, center_y - radius), mask)

def draw_headphones_icon(draw, center_x, center_y):
    draw.arc([center_x - 14, center_y - 14, center_x + 14, center_y + 6],
             start=180, end=360, fill=YELLOW, width=3)
    draw.rounded_rectangle([center_x - 16, center_y - 3, center_x - 10, center_y + 11], radius=2, fill=YELLOW)
    draw.rounded_rectangle([center_x + 10, center_y - 3, center_x + 16, center_y + 11], radius=2, fill=YELLOW)

def draw_rich_text_centered(draw, text, center_y, font, max_w=1550, line_height=90):
    text = auto_highlight_russian(text)
    pattern = r'(\*\*.*?\*\*)'
    raw_parts = re.split(pattern, text)
    tokens = []
    for part in raw_parts:
        if part.startswith('**') and part.endswith('**'):
            tokens.append((part[2:-2], True))
        elif part:
            tokens.append((part, False))
            
    words_with_status = []
    for text_chunk, is_yellow in tokens:
        words = text_chunk.split(' ')
        for i, w in enumerate(words):
            if w:
                words_with_status.append((w, is_yellow))
            if i < len(words) - 1:
                words_with_status.append((' ', False))

    lines = []
    current_line = []
    current_line_width = 0

    for item in words_with_status:
        word, is_yellow = item
        w_bbox = draw.textbbox((0, 0), word, font=font)
        w_width = w_bbox[2] - w_bbox[0]

        if current_line_width + w_width <= max_w or not current_line:
            current_line.append((word, is_yellow, w_width))
            current_line_width += w_width
        else:
            if current_line and current_line[-1][0] == ' ':
                current_line_width -= current_line[-1][2]
                current_line.pop()
            lines.append((current_line, current_line_width))
            if word == ' ':
                current_line = []
                current_line_width = 0
            else:
                current_line = [(word, is_yellow, w_width)]
                current_line_width = w_width

    if current_line:
        if current_line[-1][0] == ' ':
            current_line_width -= current_line[-1][2]
            current_line.pop()
        lines.append((current_line, current_line_width))

    total_height = len(lines) * line_height
    start_y = center_y - total_height // 2

    ink_min_top = None
    ink_max = None
    for line_idx, (line_words, line_w) in enumerate(lines):
        start_x = (VIDEO_WIDTH - line_w) // 2
        curr_x = start_x
        curr_y = start_y + line_idx * line_height

        for word, is_yellow, w_w in line_words:
            color = YELLOW if is_yellow else WHITE
            draw.text((curr_x, curr_y), word, fill=color, font=font)
            bb = draw.textbbox((curr_x, curr_y), word, font=font)
            ink_min_top = bb[1] if ink_min_top is None else min(ink_min_top, bb[1])
            ink_max = bb[3] if ink_max is None else max(ink_max, bb[3])
            curr_x += w_w

    if ink_min_top is None:
        ink_min_top = start_y
        ink_max = start_y + total_height
    return ink_min_top, ink_max

def draw_english_translation(draw, text, center_y, font, max_w=1350, line_height=52):
    words = text.split()
    lines = []
    current_line = []
    
    for w in words:
        test_line = ' '.join(current_line + [w])
        bb = draw.textbbox((0, 0), test_line, font=font)
        if bb[2] - bb[0] <= max_w:
            current_line.append(w)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [w]
    if current_line:
        lines.append(' '.join(current_line))
        
    total_h = len(lines) * line_height
    start_y = center_y - total_h // 2

    ink_min_top = None
    ink_max = None
    for idx, line in enumerate(lines):
        lx = VIDEO_WIDTH // 2
        ly = start_y + idx * line_height + line_height // 2
        draw.text((lx, ly), line, fill=LIGHT_GRAY, font=font, anchor="mm")
        bb = draw.textbbox((lx, ly), line, font=font, anchor="mm")
        ink_min_top = bb[1] if ink_min_top is None else min(ink_min_top, bb[1])
        ink_max = bb[3] if ink_max is None else max(ink_max, bb[3])
    if ink_min_top is None:
        ink_min_top = start_y
        ink_max = start_y + total_h
    return ink_min_top, ink_max

def create_frame(turn, output_path, frame_num=0):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)
    draw = ImageDraw.Draw(img)

    glow = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([(-200, VIDEO_HEIGHT-600), (600, VIDEO_HEIGHT+200)], fill=(30, 20, 60, 40))
    gdraw.ellipse([(VIDEO_WIDTH-500, -200), (VIDEO_WIDTH+300, 600)], fill=(30, 20, 60, 40))
    img.paste(glow, (0, 0), glow)

    f_title_white = load_font(36, bold=True)
    f_title_sub = load_font(18, bold=False)
    f_title_sub_muted = load_font(15, bold=False)
    f_ep = load_font(22, bold=True)
    f_speaker = load_font(26, bold=True)
    f_hablando = load_font(24, bold=False)
    f_russian = load_font(64, bold=True)
    f_english = load_font(42, bold=False, italic=True)
    f_footer = load_font(22, bold=False)

    # === TOP HEADER ===
    header_y = 68
    draw_microphone_icon(draw, center_x=70, center_y=header_y, radius=24)

    draw.text((110, header_y), "VELOCITY", fill=WHITE, font=f_title_white, anchor="lm")
    v_bbox = draw.textbbox((110, header_y), "VELOCITY", font=f_title_white, anchor="lm")
    
    draw.text((v_bbox[2] + 8, header_y), "RUSSIAN", fill=YELLOW, font=f_title_white, anchor="lm")
    s_bbox = draw.textbbox((v_bbox[2] + 8, header_y), "RUSSIAN", font=f_title_white, anchor="lm")

    draw.text((s_bbox[2] + 8, header_y), "PODCAST", fill=WHITE, font=f_title_white, anchor="lm")
    p_bbox = draw.textbbox((s_bbox[2] + 8, header_y), "PODCAST", font=f_title_white, anchor="lm")

    draw.line([(p_bbox[2] + 20, 48), (p_bbox[2] + 20, 88)], fill=DARK_LINE, width=2)

    sub_x = p_bbox[2] + 35
    draw.text((sub_x, header_y - 12), "Russian Podcast", fill=WHITE, font=f_title_sub, anchor="lm")
    draw.text((sub_x, header_y + 12), "Learn Through Conversations", fill=LIGHT_GRAY, font=f_title_sub_muted, anchor="lm")

    ep_num = (frame_num // 150) + 1 if isinstance(frame_num, int) else 1
    ep_str = f"EP {ep_num:02d}"
    draw.rounded_rectangle([(1640, 46), (1750, 90)], radius=8, fill=YELLOW)
    draw.text((1695, header_y), ep_str, fill=DARK_BG, font=f_ep, anchor="mm")

    draw_russian_flag(img, draw, center_x=1810, center_y=header_y, radius=22)

    draw.line([(0, 130), (VIDEO_WIDTH, 130)], fill=YELLOW, width=2)

    # === SPEAKER STATUS SECTION ===
    is_host1 = turn.get("speaker") == "Host1"
    speaker_name = "ANNA" if is_host1 else "IVAN"
    pill_x, pill_y = 120, 210
    pill_w, pill_h = 220, 52

    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
                           radius=26, outline=YELLOW, width=2)
    draw_person_icon(draw, center_x=pill_x + 36, center_y=pill_y + 26)
    draw.text((pill_x + 60, pill_y + 26), speaker_name, fill=YELLOW, font=f_speaker, anchor="lm")

    draw.text((pill_x + pill_w + 25, pill_y + 26), "govorit", fill=LIGHT_GRAY, font=f_hablando, anchor="lm")

    # === MAIN RUSSIAN TEXT + TRANSLITERATION (top-anchored, uniform gap) ===
    ZONE_TOP = 300
    DIV_Y = 615
    ZONE_H = (DIV_Y - 30) - ZONE_TOP
    russian_text = turn.get("russian", turn.get("spanish", ""))
    translit_text = romanize_russian(sanitize_translit(turn.get("translit", "")))
    if not translit_text:
        translit_text = romanize_russian(russian_text)
    translit_text = re.sub(r'\*\*(.*?)\*\*', r'\1', translit_text).strip()

    # 1) choose largest Russian font that wraps into <= 3 lines
    ru_font = None
    ru_size = 64
    for test_size in [64, 56, 48, 40, 34, 28, 24, 20]:
        tf = load_font(test_size, bold=True)
        tl = _wrap_any(russian_text, tf, 1550, draw)
        if len(tl) <= 3:
            ru_font, ru_size, final_lines = tf, test_size, tl
            break
    if ru_font is None:
        ru_font, ru_size = load_font(20, bold=True), 20
        all_lines = _wrap_any(russian_text, ru_font, 1550, draw)
        final_lines = all_lines[:3]
        if len(all_lines) > 3 and russian_text:
            final_lines[-1] = final_lines[-1].rstrip() + "..."

    # 2) wrap translit at starting size
    tl_size = 34
    tl_font = load_font(tl_size, bold=False, italic=True)
    tl_lines = _wrap_latin(translit_text, tl_font, 1350, draw)
    n_tl = len(tl_lines)

    RO_GAP = 14
    ru_lh = int(ru_size * 1.4)
    tl_lh = int(tl_size * 1.3)

    # 3) dynamically shrink BOTH fonts until everything fits above the divider
    while True:
        block_h = len(final_lines) * ru_lh + (RO_GAP if n_tl else 0) + n_tl * tl_lh
        if block_h <= ZONE_H or ru_size <= 20:
            break
        ru_size = max(20, ru_size - 2)
        tl_size = max(18, tl_size - 1)
        ru_font = load_font(ru_size, bold=True)
        tl_font = load_font(tl_size, bold=False, italic=True)
        final_lines = _wrap_any(russian_text, ru_font, 1550, draw)
        if len(final_lines) > 3:
            final_lines = final_lines[:3]
            final_lines[-1] = final_lines[-1].rstrip() + "..."
        n_ja = len(final_lines)
        tl_lines = _wrap_latin(translit_text, tl_font, 1350, draw)
        n_tl = len(tl_lines)
        ru_lh = int(ru_size * 1.4)
        tl_lh = int(tl_size * 1.3)

    n_ja = len(final_lines)
    ja_ink_top, ja_ink_bottom = draw_rich_text_centered(
        draw, " ".join(final_lines), center_y=ZONE_TOP + n_ja * ru_lh // 2,
        font=ru_font, max_w=1550, line_height=ru_lh)

    # === TRANSLITERATION (italic latin, uniform ink gap below Russian) ===
    if n_tl:
        ih = _translit_ink_height(tl_font, tl_lines)
        target_top = ja_ink_bottom + RO_GAP
        ly0 = target_top + ih / 2
        tl_center = ly0 - tl_lh // 2 + (n_tl * tl_lh) // 2
        draw_translit(draw, " ".join(tl_lines), center_y=tl_center,
                      font=tl_font, max_w=1350, line_height=tl_lh)

    # === CENTER DIVIDER WITH DOT ===
    div_y = 615
    draw.line([(VIDEO_WIDTH//2 - 300, div_y), (VIDEO_WIDTH//2 + 300, div_y)], fill=YELLOW, width=2)
    draw.ellipse([(VIDEO_WIDTH//2 - 8, div_y - 8), (VIDEO_WIDTH//2 + 8, div_y + 8)], fill=YELLOW)

    # === ENGLISH TRANSLATION ===
    english_text = turn.get("english", "")
    draw_english_translation(draw, english_text, center_y=715, font=f_english, max_w=1350, line_height=52)

    # === BOTTOM FOOTER ===
    draw.line([(0, 975), (VIDEO_WIDTH, 975)], fill=YELLOW, width=2)

    footer_y = 1025
    draw_headphones_icon(draw, center_x=VIDEO_WIDTH//2 - 270, center_y=footer_y)
    draw.text((VIDEO_WIDTH//2 - 240, footer_y), "Learn Russian Naturally", fill=WHITE, font=f_footer, anchor="lm")
    
    fn_bbox = draw.textbbox((VIDEO_WIDTH//2 - 240, footer_y), "Learn Russian Naturally", font=f_footer, anchor="lm")
    draw.line([(fn_bbox[2] + 20, footer_y - 12), (fn_bbox[2] + 20, footer_y + 12)], fill=DARK_LINE, width=2)
    
    draw.text((fn_bbox[2] + 40, footer_y), "velocityrussian.com", fill=WHITE, font=f_footer, anchor="lm")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=92)


def parse_turns_json(content, target_key="russian"):
    """Robustly parse JSON array of turns from LLM output, handling unescaped control chars, code fences, and partial json."""
    clean = content.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()

    try:
        obj = json.loads(clean, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    fixed = re.sub(r'(?<!\\)\n', r'\\n', clean)
    try:
        obj = json.loads(fixed, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    recovered = []
    start = None
    depth = 0
    for ci, ch in enumerate(clean):
        if ch == '{':
            if depth == 0:
                start = ci
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = clean[start:ci + 1]
                try:
                    t = json.loads(chunk, strict=False)
                    if isinstance(t, dict):
                        recovered.append(t)
                except Exception:
                    try:
                        chunk_fixed = re.sub(r'(?<!\\)\n', r'\\n', chunk)
                        t = json.loads(chunk_fixed, strict=False)
                        if isinstance(t, dict):
                            recovered.append(t)
                    except Exception:
                        pass
                start = None
    if recovered:
        return recovered

    regex = re.compile(
        r'\{\s*"speaker"\s*:\s*"(?P<speaker>[^"]+)"\s*,\s*'
        r'(?:"(?:' + target_key + r'|text|content|spanish)"\s*:\s*"(?P<tgt>.*?)"\s*,\s*)?'
        r'(?:"(?:translit|transliteration|romaji)"\s*:\s*"(?P<trld>.*?)"\s*,\s*)?'
        r'(?:"english"\s*:\s*"(?P<en>.*?)"\s*)?'
        r'\}', re.DOTALL
    )
    for m in regex.finditer(clean):
        spk = m.group("speaker") or "Host1"
        tgt = m.group("tgt") or ""
        trld = m.group("trld") or ""
        en = m.group("en") or ""
        if tgt:
            recovered.append({"speaker": spk, target_key: tgt, "translit": trld, "english": en})

    return recovered

def _fetch_turns_batch(topic, topic_es, topic_en, start_turn, batch_size=10):
    """Fetch one small batch of turns with multi-model fallback and robust parsing."""
    current_host = "Host2" if start_turn % 2 == 0 else "Host1"
    next_host = "Host1" if current_host == "Host2" else "Host2"
    host_role = "Ivan" if current_host == "Host2" else "Anna"

    intro_instruction = ""
    if start_turn == 0:
        intro_instruction = ("IMPORTANT: This is the FIRST batch. Keep the introduction SHORT - just 2 lines total "
                             "(one from Ivan/Host2, one from Anna/Host1), then immediately dive into the topic. "
                             "No long welcome speeches.\n")
    elif start_turn < 4:
        intro_instruction = "Continue naturally into the topic conversation. No new introductions.\n"

    prompt = f"""You are writing a Russian/English learning podcast at A2 level with transliteration.
Topic: {topic}

The dialogue so far is at turn {start_turn}. The current speaker is {host_role} ({current_host}).
Write the NEXT {batch_size} turns. Speakers STRICTLY alternate starting with {current_host}.

{intro_instruction}Each turn: 3-4 SHORT sentences (6-10 words each) with PERIODS for natural TTS pauses. 20-30 seconds spoken.
Simple present tense. A2 vocabulary. Natural Russian. Include "translit" (Latin-letter pronunciation spelling a beginner can read aloud) for every Russian line. NO filler sounds.
IMPORTANT: Highlight exactly 1 key A2 target vocabulary word in each turn's Russian text using double asterisks, for example: "Мы смотрим в **будущее**."
IMPORTANT: Format as a single compact JSON array without unescaped line breaks inside string values.

Return EXACTLY {batch_size} turns as a JSON array (no markdown). Each turn has "russian", "translit", and "english":
[{{"speaker": "{current_host}", "russian": "...", "translit": "...", "english": "..."}},
 {{"speaker": "{next_host}", "russian": "...", "translit": "...", "english": "..."}}]"""

    candidate_models = [AI_MODEL, "openai", "mistral", "qwen"]
    models_to_try = []
    for mod in candidate_models:
        if mod and mod not in models_to_try:
            models_to_try.append(mod)

    for attempt, model_name in enumerate(models_to_try):
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You write natural A2-level Russian podcast scripts with VERY clear punctuation. Every sentence must have at least 2 commas for natural TTS pauses. Anna and Ivan strictly alternate. Always include a \"translit\" field: a Latin-letter pronunciation spelling of the Russian text that a beginner can read aloud. Highlight 1 key target word per turn in double asterisks like **slovo**. No filler sounds. Output single compact JSON array without unescaped newlines inside strings."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code != 200:
                print(f"  Batch attempt {attempt+1} ({model_name}) returned HTTP {resp.status_code}", flush=True)
                continue
            content = resp.json()["choices"][0]["message"]["content"].strip()
            script = parse_turns_json(content, "russian")
            valid = []
            for i, turn in enumerate(script):
                if not isinstance(turn, dict):
                    continue
                rus = turn.get("russian") or turn.get("spanish") or turn.get("text") or turn.get("content") or ""
                en = turn.get("english") or turn.get("translation") or ""
                translit = turn.get("translit") or turn.get("romanji") or turn.get("transliteration") or turn.get("romaji") or ""
                if not rus:
                    continue
                valid.append({
                    "speaker": current_host if i % 2 == 0 else next_host,
                    "russian": clean_text(rus),
                    "translit": clean_text(translit) if translit else romanize_russian(clean_text(rus)),
                    "english": clean_text(en) if en else "Translation unavailable"
                })
            if len(valid) >= 4:
                return valid
            else:
                print(f"  Batch attempt {attempt+1} ({model_name}) parsed only {len(valid)} turns, trying next model...", flush=True)
        except Exception as e:
            print(f"  Batch attempt {attempt+1} ({model_name}) failed: {e}", flush=True)
            import time
            time.sleep(1)
    return None


def _generate_topic():
    """Have the AI invent a brand-new random topic (unlimited variety).
    Returns 'Russian - English' or None on failure (caller falls back to TOPICS)."""
    seed = random.randint(100000, 999999)
    candidate_models = [AI_MODEL, "openai", "mistral"]
    for m in candidate_models:
        if not m:
            continue
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": m,
                "messages": [
                    {"role": "system", "content": "You invent fresh, interesting, everyday topics for a Russian/English A2 learning podcast. Always pick something new and varied from all areas of daily life, as a SHORT noun phrase (2-5 words), NOT a full sentence."},
                    {"role": "user", "content": f"Create EXACTLY ONE brand-new topic (uniqueness seed {seed}) for a Russian/English A2 podcast. Return ONLY one line in this exact format: <topic in Russian> - <topic in English>. The Russian part must be a short noun phrase in Russian. No numbering, no bullets, no extra text."}
                ],
                "temperature": 1.1,
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip()
                if content and " - " in content:
                    return content
        except Exception as e:
            print(f"  Topic gen ({m}) failed: {e}", flush=True)
    return None


def _fallback_script(topic_es, topic_en, target=150):
    """Generate 150 unique, educational, progressive dialogue turns in Russian with transliteration covering diverse conversation phases."""
    phases = [
        # Phase 1: Greetings & Introduction
        [
            ("Host2", f"Привет всем, меня зовут Иван. Добро пожаловать в Velocity Russian! Сегодня мы обсуждаем **{topic_es}**.",
                      f"Hello everyone, my name is Ivan. Welcome to Velocity Russian! Today we discuss {topic_en}."),
            ("Host1", f"Здравствуй, Иван, и привет всем слушателям! Эта тема очень **полезна** для изучения русского языка.",
                      f"Hello Ivan, and hello to all listeners! This topic is very useful for learning Russian."),
            ("Host2", f"Точно, Анна. Каждый день люди сталкиваются с этим, но часто не знают, как правильно **говорить**.",
                      f"Exactly, Anna. Every day people encounter this, but often don't know how to speak properly."),
            ("Host1", f"Да, поэтому мы будем использовать простые фразы и понятные слова, чтобы каждый мог **понять**.",
                      f"Yes, that's why we will use simple phrases and clear words, so that everyone can understand."),
            ("Host2", f"Отлично! Давай начнём с первого вопроса: что для тебя значит **{topic_es}** в повседневной жизни?",
                      f"Great! Let's start with the first question: what does {topic_en} mean to you in daily life?"),
            ("Host1", f"Для меня это важная часть дня, которая приносит радость и даёт нам заряд **бодрости**.",
                      f"For me it's an important part of the day that brings joy and gives us a boost of energy."),
            ("Host2", f"Полностью согласен. Когда мы уделяем этому внимание, наше настроение становится намного **лучше**.",
                      f"Completely agree. When we pay attention to this, our mood becomes much better."),
            ("Host1", f"Верно, а знание нужных русских слов помогает легко поддержать любой дружеский **разговор**.",
                      f"True, and knowing the right Russian words helps easily maintain any friendly conversation."),
            ("Host2", f"Слушайте внимательно произношение и старайтесь повторять каждое новое слово **вслух**.",
                      f"Listen carefully to the pronunciation and try to repeat every new word aloud."),
            ("Host1", f"Замечательно, Иван! Давай теперь подробно разберём самые главные детали про **{topic_es}**.",
                      f"Wonderful, Ivan! Now let's examine the most important details about {topic_en} in depth.")
        ],
        # Phase 2: Morning routine & habits
        [
            ("Host2", f"Анна, как обычно начинается твоё утро, когда дело касается **{topic_es}**?",
                      f"Anna, how does your morning usually start when it comes to {topic_en}?"),
            ("Host1", f"Обычно я просыпаюсь рано, чтобы спокойно и без спешки заняться этим важным **делом**.",
                      f"Usually I wake up early to quietly and without rushing take care of this important matter."),
            ("Host2", f"Утреннее время действительно прекрасно. В доме ещё тихо, и можно спокойно **подумать**.",
                      f"Morning time is truly wonderful. The house is still quiet, and one can think calmly."),
            ("Host1", f"Спешка всегда только мешает. Хорошая утренняя **привычка** задаёт тон всему остальному дню.",
                      f"Rushing always only hurts. A good morning habit sets the tone for the whole rest of the day."),
            ("Host2", f"Многие люди, напротив, предпочитают уделять время **{topic_es}** вечером после долгой работы.",
                      f"Many people, on the contrary, prefer to dedicate time to {topic_en} in the evening after long work."),
            ("Host1", f"Конечно, у каждого человека свой удобный ритм. Главное — сохранять жизненный **баланс**.",
                      f"Of course, each person has their own convenient rhythm. The main thing is keeping life balance."),
            ("Host2", f"Ты права. Понимание своих собственных потребностей помогает человеку жить гораздо **спокойнее**.",
                      f"You are right. Understanding one's own needs helps a person live much more calmly."),
            ("Host1", f"А для наших слушателей регулярная ежедневная практика создаёт отличную языковую **память**.",
                      f"And for our listeners, regular daily practice creates an excellent language memory."),
            ("Host2", f"Именно! Заниматься десять минут каждый день намного полезнее, чем два часа один раз в **неделю**.",
                      f"Exactly! Practicing ten minutes every day is much more useful than two hours once a week."),
            ("Host1", f"Давай теперь обсудим, как **{topic_es}** проявляется в реальной городской обстановке.",
                      f"Let's now discuss how {topic_en} appears in a real city setting.")
        ],
        # Phase 3: In the city & public places
        [
            ("Host2", f"Когда мы выходим на улицу в городе, сразу видно, насколько популярен этот **выбор**.",
                      f"When we go out on the street in the city, it's immediately clear how popular this choice is."),
            ("Host1", f"Да, в кафе, в магазинах и парках люди часто говорят об этом с большим **интересом**.",
                      f"Yes, in cafes, shops and parks people often talk about this with great interest."),
            ("Host2", f"В России очень любят обсуждать такие вещи в кругу друзей за чашкой горячего **чая**.",
                      f"In Russia people love discussing such things with friends over a cup of hot tea."),
            ("Host1", f"Тёплое общение — это основа русской культуры. Никто не должен чувствовать себя **одиноко**.",
                      f"Warm communication is the foundation of Russian culture. Nobody should feel lonely."),
            ("Host2", f"Какие прилагательные чаще всего используют русские, когда описывают **{topic_es}**?",
                      f"What adjectives do Russians use most often when describing {topic_en}?"),
            ("Host1", f"Часто говорят 'хороший', 'настоящий', 'удобный' или 'полезный', чтобы подчеркнуть **качество**.",
                      f"They often say 'good', 'real', 'convenient' or 'useful' to emphasize the quality."),
            ("Host2", f"Слово 'качество' здесь идеально подходит. Люди всегда ценят надёжность и искреннее **внимание**.",
                      f"The word 'quality' fits perfectly here. People always value reliability and sincere attention."),
            ("Host1", f"Даже если цена чуть выше, высокое качество всегда полностью оправдывает сделанный **выбор**.",
                      f"Even if the price is a bit higher, high quality always fully justifies the choice made."),
            ("Host2", f"Отличный совет для путешественников в России: всегда спрашивайте мнение местных **жителей**.",
                      f"Great tip for travelers in Russia: always ask local residents for their opinion."),
            ("Host1", f"Местные жители всегда с радостью подскажут самые уютные места, где можно увидеть **{topic_es}**.",
                      f"Local residents are always happy to point out the coziest places to experience {topic_en}.")
        ],
        # Phase 4: Common beginner questions
        [
            ("Host2", f"Слушатель из другой страны спросил нас: сложно ли сразу понять все правила про **{topic_es}**?",
                      f"A listener from another country asked us: is it hard to immediately understand all rules about {topic_en}?"),
            ("Host1", f"Сначала это может показаться трудным, но при терпеливой практике всё станет очень **понятно**.",
                      f"At first it may seem difficult, but with patient practice everything will become very clear."),
            ("Host2", f"Какую главную ошибку обычно совершают начинающие, когда изучают эту новую **тему**?",
                      f"What main mistake do beginners usually make when studying this new topic?"),
            ("Host1", f"Главная ошибка — это бояться сказать что-то неправильно или ждать идеального знания с первого **дня**.",
                      f"The main mistake is being afraid of saying something wrong or expecting perfect knowledge from day one."),
            ("Host2", f"Ошибки абсолютно естественны! Каждая маленькая ошибка — это ценный шаг к **успеху**.",
                      f"Mistakes are completely natural! Every small mistake is a valuable step toward success."),
            ("Host1", f"Совершенно верно. В живом разговоре важнее всего выразить мысль и проявить взаимное **уважение**.",
                      f"Absolutely right. In live conversation, the most important thing is expressing thoughts and showing mutual respect."),
            ("Host2", f"Русские люди всегда очень тепло поддерживают иностранцев, которые стараются говорить на их **языке**.",
                      f"Russian people always very warmly support foreigners who try to speak their language."),
            ("Host1", f"Вы всегда встретите добрую улыбку, искреннюю помощь и желание продолжить **диалог**.",
                      f"You will always meet a kind smile, sincere help and a desire to continue dialogue."),
            ("Host2", f"Поэтому никогда не стесняйтесь обсуждать **{topic_es}** при первой удобной возможности!",
                      f"So never hesitate to discuss {topic_en} at the first convenient opportunity!"),
            ("Host1", f"Наберитесь смелости и используйте те полезные фразы, которые мы повторяем в этом **уроке**.",
                      f"Gather your courage and use the useful phrases that we repeat in this lesson.")
        ],
        # Phase 5: Cultural context & diversity
        [
            ("Host2", f"Анна, как различается отношение к **{topic_es}** в разных регионах такой огромной страны?",
                      f"Anna, how does the attitude towards {topic_en} differ across regions of such a huge country?"),
            ("Host1", f"В разных городах есть свои особенности, но искренний интерес и любовь везде одинаково **сильны**.",
                      f"Different cities have their own quirks, but sincere interest and love are equally strong everywhere."),
            ("Host2", f"Это разнообразие традиций делает русскую культуру невероятно глубокой и **богатой**.",
                      f"This diversity of traditions makes Russian culture incredibly deep and rich."),
            ("Host1", f"Каждый регион хранит свои уникальные рецепты, истории и способы сохранять народную **мудрость**.",
                      f"Each region preserves its unique recipes, stories and ways of keeping folk wisdom."),
            ("Host2", f"Иностранцы, приезжающие в Россию, часто удивляются, насколько здесь ценится душевное **тепло**.",
                      f"Foreigners visiting Russia are often surprised by how deeply heartfelt warmth is valued here."),
            ("Host1", f"Потому что в центре нашей культуры всегда стоят дружба, верность и поддержка **семьи**.",
                      f"Because friendship, loyalty and family support always stand at the center of our culture."),
            ("Host2", f"И тема **{topic_es}** гармонично вписывается в эти вечные жизненные ценности.",
                      f"And the topic of {topic_en} fits harmoniously into these timeless life values."),
            ("Host1", f"Это не просто слова, а настоящий практический опыт живого человеческого **общения**.",
                      f"This isn't just words, but a genuine practical experience of live human communication."),
            ("Host2", f"Когда мы делимся хорошим с другими, радость умножается и остаётся в памяти на долгие **годы**.",
                      f"When we share good things with others, joy multiplies and stays in memory for long years."),
            ("Host1", f"Золотые слова, Иван. Самые светлые воспоминания всегда связаны с простыми вещами вроде **этого**.",
                      f"Golden words, Ivan. The brightest memories are always tied to simple things like this.")
        ],
        # Phase 6: Practical vocabulary & tips
        [
            ("Host2", f"Давай поделимся со слушателями тремя практическими советами, как освоить **{topic_es}**.",
                      f"Let's share with listeners three practical tips on how to master {topic_en}."),
            ("Host1", f"Первый совет: заведите небольшую тетрадь и записывайте туда новые полезные **слова**.",
                      f"First tip: get a small notebook and write down new useful words there."),
            ("Host2", f"Отличный совет! Ручная запись активирует зрительную и мышечную память гораздо **сильнее**.",
                      f"Great tip! Writing by hand activates visual and muscular memory much more strongly."),
            ("Host1", f"Второй совет: слушайте русскую речь каждый день в наушниках, когда едете на **работу**.",
                      f"Second tip: listen to Russian speech every day in headphones when traveling to work."),
            ("Host2", f"Даже фоновое прослушивание помогает мозгу привыкать к естественной интонации и ритму **языка**.",
                      f"Even background listening helps the brain get used to the natural intonation and rhythm of the language."),
            ("Host1", f"И третий совет: не учите изолированные слова, а всегда запоминайте целые **предложения**.",
                      f"And the third tip: don't learn isolated words, but always memorize entire sentences."),
            ("Host2", f"Тогда в реальной ситуации нужная фраза сама легко вспомнится без лишних **раздумий**.",
                      f"Then in a real situation the needed phrase will easily come to mind by itself without hesitation."),
            ("Host1", f"Именно так мы и строим диалоги в наших подкастах на понятном уровне **А2**.",
                      f"That is exactly how we build dialogues in our podcasts at an accessible A2 level."),
            ("Host2", f"Слушатели пишут в комментариях, что этот метод приносит им ощутимый **прогресс**.",
                      f"Listeners write in the comments that this method brings them tangible progress."),
            ("Host1", f"Нам очень приятно слышать такие отзывы! Это вдохновляет нас продолжать эту полезную **работу**.",
                      f"We are very pleased to hear such feedback! It inspires us to continue this useful work.")
        ],
        # Phase 7: Real-life dialogue simulations
        [
            ("Host2", f"Давай разыграем короткую сценку: представь, что мы пришли в магазин выбирать **{topic_es}**.",
                      f"Let's roleplay a short scene: imagine we came to a shop to choose {topic_en}."),
            ("Host1", f"С удовольствием! 'Здравствуйте, подскажите, пожалуйста, какой вариант вы мне **посоветуете**?'",
                      f"With pleasure! 'Hello, could you please tell me which option you would advise me?'"),
            ("Host2", f"'Здравствуйте! Для начинающих я рекомендую вот этот надёжный и простой **вариант**.'",
                      f"'Hello! For beginners I recommend this reliable and simple option.'"),
            ("Host1", f"'Спасибо большое! А сколько времени требуется, чтобы освоить его в совершенстве на **практике**?'",
                      f"'Thank you very much! And how much time is needed to master it in practice?'"),
            ("Host2", f"'Обычно хватает пары недель регулярных занятий, если подходить к делу с должным **терпением**.'",
                      f"'Usually a couple of weeks of regular practice is enough if one approaches it with proper patience.'"),
            ("Host1", f"'Звучит отлично! Я обязательно попробую этот метод уже сегодня **вечером**.'",
                      f"'Sounds great! I will definitely try this method this very evening.'"),
            ("Host2", f"Вот такой простой и вежливый диалог можно легко провести в любом русском **городе**.",
                      f"A simple and polite dialogue like this can easily be conducted in any Russian city."),
            ("Host1", f"Обратите внимание на слова 'посоветуйте' и 'рекомендую' — они звучат очень **вежливо**.",
                      f"Pay attention to the words 'advise' and 'recommend' — they sound very polite."),
            ("Host2", f"Вежливость всегда открывает любые двери и располагает к вам любого **собеседника**.",
                      f"Politeness always opens any doors and endears any conversation partner to you."),
            ("Host1", f"Давайте закрепим эти фразы и продолжим изучать другие полезные **конструкции**.",
                      f"Let's consolidate these phrases and continue learning other useful structures.")
        ],
        # Phase 8: Personal opinions & reflections
        [
            ("Host2", f"Анна, а как лично твои друзья относятся к такой популярной теме, как **{topic_es}**?",
                      f"Anna, how do your personal friends feel about such a popular topic as {topic_en}?"),
            ("Host1", f"Многие из них сначала сомневались, но когда попробовали, оценили реальную **пользу**.",
                      f"Many of them doubted at first, but when they tried, they appreciated real benefit."),
            ("Host2", f"Сомнения в начале нового дела — это нормальная защитная реакция любого здорового **человека**.",
                      f"Doubts at the beginning of a new endeavor are a normal protective reaction of any healthy person."),
            ("Host1", f"Но когда мы делаем первый решительный шаг вперёд, страх уходит и появляется **уверенность**.",
                      f"But when we take the first decisive step forward, fear goes away and confidence appears."),
            ("Host2", f"Уверенность в речи приходит только с практикой, поэтому говорите чаще и ничего не **бойтесь**.",
                      f"Confidence in speech comes only with practice, so speak more often and fear nothing."),
            ("Host1", f"Даже если вы знаете всего двадцать русских слов, уже можно построить связный **рассказ**.",
                      f"Even if you know only twenty Russian words, you can already build a coherent story."),
            ("Host2", f"Главное — говорить от сердца и искренне стремиться передать свой позитивный **опыт**.",
                      f"The main thing is to speak from the heart and sincerely strive to convey your positive experience."),
            ("Host1", f"Наши слушатели по всему миру доказывают, что русский язык доступен каждому **желающему**.",
                      f"Our listeners around the world prove that Russian language is accessible to anyone interested."),
            ("Host2", f"Каждый новый день приносит им свежие знания и радость открытий в **мире** русского слова.",
                      f"Every new day brings them fresh knowledge and the joy of discoveries in the world of Russian words."),
            ("Host1", f"И мы искренне рады быть вашими проводниками на этом увлекательном творческом **пути**.",
                      f"And we are sincerely happy to be your guides on this exciting creative journey.")
        ],
        # Phase 9: Vocabulary review & quiz
        [
            ("Host2", f"Давай сделаем небольшое повторение главных слов, которые мы сегодня упомянули про **{topic_es}**.",
                      f"Let's do a short review of the main words that we mentioned today regarding {topic_en}."),
            ("Host1", f"С удовольствием! Первое ключевое слово — это **привычка**, то есть регулярное полезное действие.",
                      f"With pleasure! The first key word is 'habit', that is, a regular useful action."),
            ("Host2", f"Второе важное слово — это **качество**, которое отличает хорошую работу от плохой.",
                      f"The second important word is 'quality', which distinguishes good work from bad."),
            ("Host1", f"Третье слово — это **уважение**, основа любого приятного и продуктивного разговора.",
                      f"The third word is 'respect', the foundation of any pleasant and productive conversation."),
            ("Host2", f"Четвёртое слово — это **терпение**, без которого невозможно выучить ни один иностранный язык.",
                      f"The fourth word is 'patience', without which it's impossible to learn any foreign language."),
            ("Host1", f"И пятое слово — это **уверенность**, которая растёт с каждым пройденным уроком.",
                      f"And the fifth word is 'confidence', which grows with every completed lesson."),
            ("Host2", f"Попробуйте составить в комментариях собственное предложение с одним из этих целевых **слов**.",
                      f"Try to compose your own sentence in the comments with one of these target words."),
            ("Host1", f"Мы обязательно прочитаем ваши комментарии и поддержим каждого прилежного **ученика**.",
                      f"We will definitely read your comments and support every diligent student."),
            ("Host2", f"Такая интерактивная практика помогает запомнить материал намного быстрее и **надёжнее**.",
                      f"Such interactive practice helps remember the material much faster and more reliably."),
            ("Host1", f"Давай перейдём к заключительной части нашего насыщенного и тёплого **выпуска**.",
                      f"Let's move on to the final part of our rich and warm episode.")
        ],
        # Phase 10: Conclusion & wrap-up
        [
            ("Host2", f"Наш сегодняшний подкаст о **{topic_es}** подходит к своему логическому завершению.",
                      f"Our podcast today about {topic_en} is coming to its logical conclusion."),
            ("Host1", f"Время пролетело незаметно! Мы узнали много новых слов и полезных речевых **оборотов**.",
                      f"Time flew by unnoticed! We learned many new words and useful speech turns."),
            ("Host2", f"Не забывайте слушать этот выпуск несколько раз, чтобы закрепить правильное **произношение**.",
                      f"Don't forget to listen to this episode several times to consolidate proper pronunciation."),
            ("Host1", f"Каждое повторение делает вашу речь более беглой, красивой и по-настоящему **естественной**.",
                      f"Every repetition makes your speech more fluent, beautiful and truly natural."),
            ("Host2", f"Спасибо всем слушателям за внимание, активность и искренний интерес к нашей **программе**.",
                      f"Thank you to all listeners for attention, activity and sincere interest in our program."),
            ("Host1", f"Подписывайтесь на канал Velocity Russian, ставьте лайки и делитесь видео с **друзьями**.",
                      f"Subscribe to Velocity Russian channel, like and share videos with friends."),
            ("Host2", f"Впереди вас ждёт ещё много интересных тем и практических уроков на каждый **день**.",
                      f"Ahead of you are many more interesting topics and practical lessons for every day."),
            ("Host1", f"Желаем вам отличного настроения, вдохновения и лёгких успехов в **учёбе**!",
                      f"We wish you great mood, inspiration and easy success in your studies!"),
            ("Host2", f"До скорой встречи в следующем выпуске! Говорите по-русски с **удовольствием**!",
                      f"See you soon in the next episode! Speak Russian with pleasure!"),
            ("Host1", f"До свидания, дорогие друзья! Берегите себя и оставайтесь с **нами**!",
                      f"Goodbye, dear friends! Take care and stay with us!")
        ]
    ]

    all_templates = []
    for ph in phases:
        all_templates.extend(ph)
    turns = []
    for i in range(target):
        _, t_rus, t_en = all_templates[i % len(all_templates)]
        spk = "Host2" if i % 2 == 0 else "Host1"
        turns.append({
            "speaker": spk,
            "russian": t_rus,
            "translit": romanize_russian(t_rus),
            "english": t_en
        })
    return turns


def _extend_script(existing_turns, topic_es, topic_en, target=150):
    fallback_pool = _fallback_script(topic_es, topic_en, target)
    idx = 0
    cur_speaker = existing_turns[-1]["speaker"] if existing_turns else "Host1"
    while len(existing_turns) < target:
        cand = fallback_pool[idx % len(fallback_pool)]
        idx += 1
        needed_spk = "Host1" if cur_speaker == "Host2" else "Host2"
        existing_turns.append({
            "speaker": needed_spk,
            "russian": cand["russian"],
            "translit": cand["translit"],
            "english": cand["english"]
        })
        cur_speaker = needed_spk
    return existing_turns[:target]


def generate_script():
    topic = _generate_topic() or random.choice(TOPICS)
    topic_es = topic.split(" - ")[0]
    topic_en = topic.split(" - ")[1]

    TARGET = 150
    BATCH = 10
    all_turns = []
    consecutive_empty = 0
    import time as _time
    _deadline = _time.time() + 600  # generous 10 min cap

    while len(all_turns) < TARGET and consecutive_empty < 12 and _time.time() < _deadline:
        batch = _fetch_turns_batch(topic, topic_es, topic_en, len(all_turns), BATCH)
        if not batch:
            consecutive_empty += 1
            wait_s = min(15, 3 + consecutive_empty * 2)
            print(f"  API busy (consecutive fails: {consecutive_empty}) - waiting {wait_s}s before retrying...", flush=True)
            _time.sleep(wait_s)
            continue
        all_turns.extend(batch)
        consecutive_empty = 0
        print(f"  Script progress: {len(all_turns)}/{TARGET} turns", flush=True)
        if len(all_turns) < TARGET:
            _time.sleep(1)

    all_turns = all_turns[:TARGET]

    if not all_turns:
        print("  Using structured fallback script (150 unique turns)...", flush=True)
        all_turns = _fallback_script(topic_es, topic_en, TARGET)
    elif len(all_turns) < TARGET:
        print(f"  Extending {len(all_turns)} turns to {TARGET} with topic conversation...", flush=True)
        all_turns = _extend_script(all_turns, topic_es, topic_en, TARGET)

    # Short 2-line intro: Ivan (Host2) first, then Anna (Host1), then topic
    all_turns[0]["speaker"] = "Host2"
    all_turns[0]["russian"] = f"Привет, я Иван. Добро пожаловать в Velocity Russian. Сегодня мы говорим о **{topic_es}**."
    all_turns[0]["translit"] = romanize_russian(all_turns[0]["russian"])
    all_turns[0]["english"] = f"Hi, I'm Ivan. Welcome to Velocity Russian Podcast. Today we talk about {topic_en}."
    if len(all_turns) > 1:
        all_turns[1]["speaker"] = "Host1"
        all_turns[1]["russian"] = f"Спасибо, Иван. Сегодняшняя тема очень **интересная**. Начнём."
        all_turns[1]["translit"] = romanize_russian(all_turns[1]["russian"])
        all_turns[1]["english"] = f"Thanks, Ivan. Today's topic is very interesting. Let's start."

    print(f"  Script: {len(all_turns)} turns, topic: {topic_es}", flush=True)
    return all_turns, topic_es, topic_en


async def generate_audio(turns, target_dir=None):
    import edge_tts
    audio_files = []
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        audio_dir = Path(target_dir) if target_dir else OUTPUT_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        filename = audio_dir / f"audio_{i:03d}.mp3"
        spoken_text = re.sub(r'\*\*(.*?)\*\*', r'\1', turn.get("russian", turn.get("spanish", "")))
        try:
            communicate = edge_tts.Communicate(spoken_text, voice)
            await communicate.save(str(filename))
            try:
                r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(filename)], capture_output=True, text=True)
                duration = float(r.stdout.strip()) if r.stdout else 3.0
            except:
                duration = 3.0
        except Exception as e:
            print(f"  Audio {i} failed: {e}")
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", str(filename)], capture_output=True)
            duration = 3.0
        audio_files.append({"path": str(filename), "duration": duration, "speaker": turn["speaker"]})
    return audio_files

def create_video(turns, audio_files, video_dir=None):
    if video_dir is None:
        video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir = Path(video_dir)
    video_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    total_dur = 0

    for i, (turn, audio) in enumerate(zip(turns, audio_files)):
        img = video_dir / f"f_{i:04d}.png"
        create_frame(turn, str(img), i)
        clip = video_dir / f"c_{i:04d}.mp4"
        clips.append(clip)
        dur = audio["duration"]
        fade_start = max(0.0, dur - 0.3)
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", audio["path"],
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-preset", "medium",
            "-t", str(dur), "-af", f"afade=t=out:st={fade_start:.2f}:d=0.3",
            str(clip)
        ], check=True, capture_output=True)

        total_dur += audio["duration"]
        if (i + 1) % 25 == 0:
            print(f"  Frame {i+1}/{len(turns)}")

    concat = video_dir / "list.txt"
    with open(concat, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    out = video_dir / "podcast_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    "-movflags", "+faststart", str(out)], check=True)

    for c in clips:
        c.unlink(missing_ok=True)
    for a in audio_files:
        try:
            Path(a["path"]).unlink(missing_ok=True)
        except Exception:
            pass
    if concat.exists():
        concat.unlink(missing_ok=True)

    return out, total_dur


async def main():
    print("=" * 60)
    print("  VELOCITY RUSSIAN PODCAST")
    print("=" * 60)

    print("\n[1/4] Generating script (150 turns)...")
    turns, topic_es, topic_en = generate_script()

    video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(video_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump({"topic": topic_es, "topic_en": topic_en, "turns": turns}, f, indent=2, ensure_ascii=False)

    print(f"\n[2/4] Generating audio ({len(turns)} turns)...")
    audio_files = await generate_audio(turns, video_dir)
    total_audio = sum(a["duration"] for a in audio_files)
    print(f"  Total audio: {total_audio/60:.1f} min")

    print(f"\n[3/4] Creating video...")
    video_path, duration = create_video(turns, audio_files, video_dir)

    print(f"\n[4/4] Saving...")
    first_frame = video_dir / "f_0000.png"
    thumbnail_path = video_dir / "thumbnail.jpg"
    try:
        from PIL import Image as _Img
        if first_frame.exists():
            _Img.open(str(first_frame)).convert("RGB").save(str(thumbnail_path), quality=92)
    except Exception as e:
        print(f"  Thumbnail warn: {e}")

    title = build_podcast_title(topic_es, topic_en)
    description = build_podcast_description(topic_es, topic_en, len(turns), round(duration / 60, 1))
    tags = ["Learn Russian", "Russian", "Russian Podcast", "Learn Russian Naturally",
            "Russian for Beginners", "Bilingual", "Russian Listening", "Russian Conversation",
            topic_es, "Velocity Russian"]

    meta_out = {
        "title": title,
        "description": description,
        "tags": tags,
        "category_english": topic_es,
        "language": "Russian",
        "duration_minutes": round(duration / 60, 1),
        "turns_count": len(turns),
        "video_path": str(video_path),
        "thumbnail_path": str(thumbnail_path),
        "generated_at": datetime.now().isoformat(),
    }
    (OUTPUT_DIR).mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "latest_video.json", "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=2, ensure_ascii=False)
    with open(OUTPUT_DIR / "latest_upload_info.json", "w", encoding="utf-8") as f:
        json.dump({"title": title, "description": description,
                   "category": topic_es, "turns_count": len(turns)}, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("  PODCAST COMPLETE!")
    print(f"  Topic: {topic_es}")
    print(f"  Duration: {duration/60:.1f} min ({len(turns)} turns)")
    print(f"  Video: {video_path.name}")
    print("=" * 60)


def build_podcast_title(topic_es, topic_en):
    titles = [
        f"Russian Podcast: {topic_es} | Учи русский",
        f"Learn Russian: {topic_es} | Bilingual Podcast",
        f"{topic_es} | Russian Conversation for Beginners",
        f"{topic_es} | Практикуй русский с Анной и Иваном",
    ]
    return random.choice(titles)


def build_podcast_description(topic_es, topic_en, turns_count, duration_min):
    description = (
        f"🎙️ Добро пожаловать в Velocity Russian Podcast!\n\n"
        f"В этом выпуске Анна и Иван говорят о: {topic_es} ({topic_en}).\n"
        f"Непринуждённый двуязычный разговор на уровне A2, чтобы учить русский язык естественно.\n\n"
        f"✨ WHAT'S INSIDE THIS EPISODE:\n"
        f"• {turns_count} полезные фразы и выражения на русском\n"
        f"• Настоящие разговоры с повседневной лексикой\n"
        f"• Естественное произношение носителей языка\n"
        f"• Английский перевод в каждой строке\n\n"
        f"📚 HOW TO USE THIS PODCAST:\n"
        f"1️⃣ Слушайте русскую часть и пытайтесь понять\n"
        f"2️⃣ Проверьте английский перевод\n"
        f"3️⃣ Повторяйте фразы вслух\n"
        f"4️⃣ Слушайте завтра снова - каждый день становится легче!\n\n"
        f"🔔 Подпишитесь на новый урок каждый день.\n\n"
        f"🕓 Длительность: {duration_min} минут\n\n"
        f"#LearnRussian #RussianPodcast #Bilingual #LanguageLearning"
    )
    return description



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('  Cancelled.')
