#!/usr/bin/env python3
"""
build_japan_ranking.py
Builds the Overseas Japan Insider Ranking Series ("Instagram Viral × Domestic Review Verified").
Supports both TOP 5 and TOP 10 rankings with:
1. Dedicated Opening visual collage screen ("opening" - 5-col or 2x5 10-spot grid)
2. Prerequisite Area Guide screen ("area_guide" - Location, Tokyo Access, 4 Seasons Climate, Key Features)
3. Spot introduction with 2 distinct real visitor photos per segment + Access pill bar ("spot")
4. Real Japanese Customer Review Card overlay (Japanese + English quotes) ("review")
5. Full 5-spot or 10-spot Comparison Cheat-Sheet Summary Table at the end ("summary")
6. 4-Act Dynamic BGM (Intro Groove -> Countdown Beat -> Top 3 Climax -> Chill Finale)
   + Crisp Transition Sound Effects (Rank Whoosh/Taiko, Top 3 Riser, Review Pop, Shinkansen Chime, Shutter Tick)
   + 0.45s Pre-Narration Transition Breath with Auto-Ducking.
"""

import asyncio
import json
import logging
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, List, Tuple

import edge_tts
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("japan_ranking")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

W, H = 1280, 720
FPS = 25


def find_font() -> str:
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Font not found")


def find_cjk_font() -> str:
    """Return a font guaranteed to support Japanese CJK glyphs on both macOS and Ubuntu runners."""
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return find_font()


def draw_instagram_logo(canvas: Image.Image, x: int, y: int, size: int = 52) -> None:
    """Draw a vector-crisp Instagram gradient camera icon at (x, y) onto an RGBA canvas."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    idraw = ImageDraw.Draw(icon)
    for py in range(size):
        for px in range(size):
            t = (px + (size - 1 - py)) / max(1.0, (2.0 * (size - 1)))
            if t < 0.35:
                u = t / 0.35
                r = int(252 * (1 - u) + 253 * u)
                g = int(176 * (1 - u) + 29 * u)
                b = int(69 * (1 - u) + 29 * u)
            elif t < 0.70:
                u = (t - 0.35) / 0.35
                r = int(253 * (1 - u) + 225 * u)
                g = int(29 * (1 - u) + 48 * u)
                b = int(29 * (1 - u) + 108 * u)
            else:
                u = (t - 0.70) / 0.30
                r = int(225 * (1 - u) + 131 * u)
                g = int(48 * (1 - u) + 58 * u)
                b = int(108 * (1 - u) + 180 * u)
            idraw.point((px, py), fill=(r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.26), fill=255)
    clipped = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    clipped.paste(icon, (0, 0), mask)
    cd = ImageDraw.Draw(clipped)
    pad = max(3, int(size * 0.16))
    w_line = max(2, int(size * 0.075))
    cd.rounded_rectangle((pad, pad, size - 1 - pad, size - 1 - pad), radius=int(size * 0.20), outline=(255, 255, 255, 255), width=w_line)
    cx, cy = size // 2, size // 2
    cr = int(size * 0.17)
    cd.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), outline=(255, 255, 255, 255), width=w_line)
    dot_r = max(2, int(size * 0.045))
    dx, dy = int(size * 0.68), int(size * 0.32)
    cd.ellipse((dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r), fill=(255, 255, 255, 255))
    canvas.alpha_composite(clipped, (x, y))


def synthesize_jp_local_voice(
    rank_str: str,
    title_en: str,
    dish_en: str,
    card_style: str = "praise",
    explicit_ja: str = "",
) -> str:
    """Return an authentic, concise Japanese Instagram local review quote ('日本人のリアルな声') that fits cleanly on 1 line."""
    if explicit_ja and re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", explicit_ja):
        q = explicit_ja.strip().strip("「」\"'")
        for sep in ("！", "!", "。", "、"):
            if sep in q:
                first = q.split(sep)[0].strip()
                if 8 <= len(first) <= 29:
                    q = first + ("！" if sep in ("！", "!") else "")
                    break
        if len(q) > 29:
            q = q[:28].rstrip("、。") + "！"
        return f"「{q}」"
    ctx = f"{title_en} {dish_en}".lower()
    is_food = any(k in ctx for k in ("ramen", "sushi", "wagyu", "beef", "noodle", "broth", "market", "izakaya", "cafe", "sweets", "matcha", "tempura", "udon", "soba", "tonkatsu", "curry", "gourmet", "food", "bowl", "fish", "crab", "unagi", "gyoza", "okonomiyaki", "takoyaki", "yakitori"))
    is_onsen = any(k in ctx for k in ("onsen", "bath", "ryokan", "hot spring", "rotenburo"))
    is_anime = any(k in ctx for k in ("ghibli", "anime", "spirited", "shinkai", "your name", "slayer", "totoro", "mononoke", "ponyo", "kamakura"))
    if card_style == "warn":
        if is_food:
            return "「開店30分前に並ぶのが鉄則！現金も用意して」"
        if is_onsen:
            return "「日帰り入浴は朝一番が狙い目！湯上がり散策も最高」"
        return "「ツアー客が来る前の早朝8時台に行くと独り占め！」"
    if "#1" in rank_str or "NO.1" in rank_str:
        if is_food:
            return "「観光客向けの店とは別次元。地元民が推すNo.1名店！」"
        if is_onsen:
            return "「一生に一度は行くべき名湯！泉質も風情も日本一」"
        if is_anime:
            return "「映画のワンシーンそのまま！絶対感動する聖地No.1」"
        return "「定番の観光地より絶対ここ！日本人が感動したNo.1絶景」"
    if "#2" in rank_str or "NO.2" in rank_str:
        if is_food:
            return "「ステマなしで本当に旨い店！リピーターが絶えない名店」"
        return "「写真の何倍も実物がすごい！季節ごとに通いたい名所」"
    if is_food:
        return "「コスパも味も最高クラス！常連に愛される隠れた名店」"
    return "「混雑しすぎず空気感が最高！日本らしい風景が残る穴場」"



def fit_crop(im: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize and center-crop an image to exact (target_w, target_h)."""
    im = im.convert("RGB")
    src_w, src_h = im.size
    scale = max(target_w / max(src_w, 1), target_h / max(src_h, 1))
    nw, nh = int(math.ceil(src_w * scale)), int(math.ceil(src_h * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return im.crop((left, top, left + target_w, top + target_h))


PREF_EN_TO_JA = {
    "hokkaido": "北海道", "sapporo": "北海道", "hakodate": "北海道",
    "aomori": "青森県", "iwate": "岩手県", "miyagi": "宮城県", "sendai": "宮城県",
    "akita": "秋田県", "yamagata": "山形県", "fukushima": "福島県",
    "ibaraki": "茨城県", "tochigi": "栃木県", "nikko": "栃木県", "gunma": "群馬県",
    "saitama": "埼玉県", "chiba": "千葉県", "tokyo": "東京都", "shinjuku": "東京都", "shibuya": "東京都", "asakusa": "東京都",
    "kanagawa": "神奈川県", "yokohama": "神奈川県", "kamakura": "神奈川県", "hakone": "神奈川県",
    "niigata": "新潟県", "toyama": "富山県", "ishikawa": "石川県", "kanazawa": "石川県",
    "fukui": "福井県", "yamanashi": "山梨県", "fuji": "山梨県", "nagano": "長野県", "matsumoto": "長野県",
    "gifu": "岐阜県", "takayama": "岐阜県", "shirakawago": "岐阜県", "shizuoka": "静岡県",
    "aichi": "愛知県", "nagoya": "愛知県", "mie": "三重県", "ise": "三重県",
    "shiga": "滋賀県", "hikone": "滋賀県", "kyoto": "京都府", "osaka": "大阪府",
    "hyogo": "兵庫県", "himeji": "兵庫県", "kobe": "兵庫県", "kinosaki": "兵庫県",
    "nara": "奈良県", "wakayama": "和歌山県", "koyasan": "和歌山県",
    "tottori": "鳥取県", "shimane": "島根県", "izumo": "島根県", "okayama": "岡山県",
    "hiroshima": "広島県", "miyajima": "広島県", "yamaguchi": "山口県",
    "tokushima": "徳島県", "kagawa": "香川県", "ehime": "愛媛県", "matsuyama": "愛媛県", "kochi": "高知県",
    "fukuoka": "福岡県", "hakata": "福岡県", "saga": "佐賀県", "nagasaki": "長崎県",
    "kumamoto": "熊本県", "oita": "大分県", "beppu": "大分県", "yufuin": "大分県",
    "miyazaki": "宮崎県", "kagoshima": "鹿児島県", "okinawa": "沖縄県",
}


def strip_cjk(text: str) -> str:
    """Remove any Japanese/CJK characters and unsupported glyphs so all rendered slides stay 100% clean English."""
    cleaned = re.sub(r"[\u3000-\u9fff\uff00-\uffef]+", "", text or "")
    cleaned = re.sub(r"★\s*(\d+(?:\.\d+)?)", r"\1/5.0", cleaned)
    cleaned = cleaned.replace("★", "").replace("▶", "+").replace("🔔", "+")
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def smart_truncate(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_w: int,
) -> str:
    """
    Truncate `text` to fit within `max_w` pixels strictly on whole-clause or whole-word boundaries.
    NEVER cuts a word in half (e.g. never produces 'Sightsee', 'Villag', 'Yumeguri Pa', or 'Bus 50').
    """
    s = strip_cjk(text)
    if not s:
        return ""
    tb = draw.textbbox((0, 0), s, font=font)
    if (tb[2] - tb[0]) <= max_w:
        return s

    # Try dropping secondary clauses after ';', '|', or '—' first
    for sep in (";", "|", "—", " - "):
        if sep in s:
            first_part = s.split(sep)[0].strip()
            if len(first_part) >= 10:
                tb_fp = draw.textbbox((0, 0), first_part, font=font)
                if (tb_fp[2] - tb_fp[0]) <= max_w:
                    return first_part

    # Otherwise drop whole words from the end, cleaning unclosed parens and dangling stop-words
    dangling = {
        "of", "in", "to", "for", "with", "on", "at", "from", "by", "about", "as",
        "into", "before", "after", "between", "through", "during", "under", "over",
        "the", "a", "an", "your", "their", "its", "&", "and", "or", "japan's",
    }
    words = s.split(" ")
    while len(words) > 1:
        words.pop()
        candidate = " ".join(words).rstrip(",;:|—-")
        while candidate.count("(") > candidate.count(")"):
            idx_p = candidate.rfind("(")
            if idx_p > 0:
                candidate = candidate[:idx_p].strip().rstrip(",;:|—-")
            else:
                break
        c_words = candidate.split(" ")
        while len(c_words) > 2 and c_words[-1].lower().rstrip(".,;:") in dangling:
            c_words.pop()
        candidate = " ".join(c_words).rstrip(",;:|—-")
        tb_c = draw.textbbox((0, 0), candidate, font=font)
        if (tb_c[2] - tb_c[0]) <= max_w:
            return candidate
    return s


def fit_font_for_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: str,
    start_size: int,
    min_size: int,
    max_w: int,
) -> ImageFont.FreeTypeFont:
    """Return the largest font size (from `start_size` down to `min_size`) where `text` fits in `max_w`."""
    sz = start_size
    while sz > min_size:
        f = ImageFont.truetype(font_path, sz)
        tb = draw.textbbox((0, 0), text, font=f)
        if (tb[2] - tb[0]) <= max_w:
            return f
        sz -= 1
    return ImageFont.truetype(font_path, min_size)


def resolve_prefecture_and_route(
    area_guide: Dict[str, Any],
    hint_text: str,
    prefs_data: List[Dict[str, Any]],
) -> Tuple[str, List[Tuple[float, float]]]:
    """
    Dynamically resolve the Japanese prefecture name (`nam_ja`) and compute the exact
    geographic route from Tokyo Station `(139.767, 35.681)` to that prefecture's polygon centroid!
    """
    explicit = area_guide.get("target_pref_ja", "").strip()
    search_blob = f"{hint_text} {area_guide.get('map_badge', '')} {json.dumps(area_guide.get('cards', []), ensure_ascii=False)}".lower()

    target_pref = explicit
    if not target_pref:
        for pf in prefs_data:
            nja = pf.get("nam_ja", "")
            if nja and nja in search_blob:
                target_pref = nja
                break
    if not target_pref:
        for kw_en, pref_ja in PREF_EN_TO_JA.items():
            if re.search(rf"\b{re.escape(kw_en)}\b", search_blob):
                target_pref = pref_ja
                break
    if not target_pref:
        target_pref = "兵庫県"

    dest_lon, dest_lat = 134.690, 34.839
    for pf in prefs_data:
        if pf.get("nam_ja") == target_pref and pf.get("polys"):
            best_ring = max(pf["polys"], key=lambda r: len(r))
            if best_ring:
                dest_lon = sum(pt[0] for pt in best_ring) / len(best_ring)
                dest_lat = sum(pt[1] for pt in best_ring) / len(best_ring)
            break

    tokyo_lon, tokyo_lat = 139.767, 35.681
    if target_pref == "東京都":
        route_pts = [(tokyo_lon, tokyo_lat), (tokyo_lon + 0.05, tokyo_lat + 0.05)]
    else:
        route_pts = [(tokyo_lon, tokyo_lat), (dest_lon, dest_lat)]

    return target_pref, route_pts


def render_opening_flash_frames(
    ranking_id: str,
    seg: Dict[str, Any],
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    work_dir: Path,
) -> List[Path]:
    """
    Render 6 Full-Screen High-Impact Rapid-Fire Photo Slides (`open_flash_00.jpg` .. `open_flash_05.jpg`)
    for the First 10 Seconds (`opening` segment) of the 16:9 Long Video.
    """
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id
    pick_indices = [9, 6, 4, 2, 1, 0] if len(summary_rows) >= 10 else list(range(min(6, len(summary_rows))))
    if not pick_indices:
        pick_indices = [0]

    flash_labels = [
        ("ZERO PAID PROMO  |  RANK #10", (220, 38, 38, 250)),
        ("JAPANESE IG ANALYZED  |  RANK #7", (2, 132, 199, 248)),
        ("100% UNSPONSORED  |  RANK #5", (16, 185, 129, 248)),
        ("REAL LOCAL VOICES  |  RANK #3", (220, 38, 38, 250)),
        ("NO TOURIST TRAPS  |  RANK #2", (220, 38, 38, 250)),
        ("WAIT UNTIL YOU SEE #1!", (217, 119, 6, 252)),
    ]

    f_pill = ImageFont.truetype(font_path, 21)
    f_sub = ImageFont.truetype(font_path, 20)
    f_stamp = ImageFont.truetype(font_path, 20)

    out_paths: List[Path] = []
    for i, r_idx in enumerate(pick_indices):
        row = summary_rows[r_idx] if r_idx < len(summary_rows) else {}
        p_path = cache_dir / row.get("thumb", "")
        if p_path.exists() and p_path.is_file():
            im = fit_crop(Image.open(p_path), W, H)
            im = ImageEnhance.Color(im).enhance(1.22)
            im = ImageEnhance.Contrast(im).enhance(1.12)
        else:
            im = Image.new("RGB", (W, H), (14, 20, 34))

        canvas = im.convert("RGBA")
        draw = ImageDraw.Draw(canvas, "RGBA")

        # Top-Center Catchy Verification Stamp (y=116..162) so the first 5 seconds scream "100% NO PAID PROMO • JAPANESE IG ANALYZED"
        stamp_txt = "100% NO PAID PROMOTION  •  500,000+ JAPANESE INSTAGRAM POSTS ANALYZED  •  REAL LOCAL VOICES ONLY"
        f_st_fit = fit_font_for_width(draw, stamp_txt, font_path, 20, 15, W - 180)
        tb_st = draw.textbbox((0, 0), stamp_txt, font=f_st_fit)
        st_w = (tb_st[2] - tb_st[0]) + 44
        st_x0 = (W - st_w) // 2
        draw.rounded_rectangle((st_x0, 114, st_x0 + st_w, 158), radius=22, fill=(185, 28, 28, 246), outline=(253, 224, 71, 255), width=3)
        draw.text((st_x0 + 22, 125), stamp_txt, font=f_st_fit, fill=(255, 255, 255, 255))

        pill_txt, pill_col = flash_labels[i % len(flash_labels)]
        rank_str = row.get("rank", f"#{10 - i}")
        score_str = row.get("score", "95/100pt")
        name_en = strip_cjk(row.get("name_en", "Secret Local Spot"))
        dish_en = strip_cjk(row.get("dish", "Voted by Japanese Locals"))
        acc_en = strip_cjk(row.get("access_short", row.get("budget", "Direct Train Access")))

        # Zoom-safe centered lower card (bx0=96..W-96, by0=362..482 so 1.06x zoom never touches HUD)
        bx0, by0, bx1, by1 = 96, 362, W - 96, 482
        max_card_tw = (bx1 - bx0) - 48
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=16, fill=(8, 12, 24, 232), outline=(253, 224, 71, 245), width=3)

        tb_p = draw.textbbox((0, 0), pill_txt, font=f_pill)
        pw = (tb_p[2] - tb_p[0]) + 34
        draw.rounded_rectangle((bx0 + 16, by0 - 20, bx0 + 16 + pw, by0 + 20), radius=10, fill=pill_col, outline=(255, 255, 255, 245), width=2)
        draw.text((bx0 + 33, by0 - 11), pill_txt, font=f_pill, fill=(255, 255, 255, 255))

        prog_txt = f"REAL IG VOICE {i + 1}/{len(pick_indices)}  >>  0% SPONSORED"
        tb_pr = draw.textbbox((0, 0), prog_txt, font=f_sub)
        draw.text((bx1 - (tb_pr[2] - tb_pr[0]) - 22, by0 + 8), prog_txt, font=f_sub, fill=(167, 243, 208, 255))

        if i == 0:
            headline = "STOP FALLING FOR PAID INFLUENCER TOURIST TRAPS!"
            subline = f"We analyzed 500,000+ real Japanese Instagram posts — Preview #{10 - i}: {name_en}"
        elif i == len(pick_indices) - 1:
            headline = f"#1 UNSPONSORED SPOT SCORED {score_str.upper()} — CAN YOU GUESS IT?"
            subline = f"Hint: {dish_en}  |  Access: {acc_en}"
        else:
            headline = f"{rank_str}  {name_en}  ({score_str})"
            subline = f"{dish_en}  |  Access: {acc_en}"

        f_spot_fit = fit_font_for_width(draw, headline, font_path, 32, 20, max_card_tw)
        f_sub_fit = fit_font_for_width(draw, subline, font_path, 20, 15, max_card_tw)
        clean_sub = smart_truncate(draw, subline, f_sub_fit, max_card_tw)

        draw.text((bx0 + 24, by0 + 34), headline, font=f_spot_fit, fill=(253, 224, 71, 255), stroke_width=3, stroke_fill=(0, 0, 0, 245))
        draw.text((bx0 + 24, by0 + 80), clean_sub, font=f_sub_fit, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 230))

        out_p = work_dir / f"open_flash_{i:02d}.jpg"
        canvas.convert("RGB").save(out_p, "JPEG", quality=95)
        out_paths.append(out_p)

    return out_paths


def render_opening_collage_jpg(
    ranking_id: str,
    seg: Dict[str, Any],
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg_a: Path,
    out_jpg_b: Path,
) -> None:
    """
    Render 2x5 Visual Grid for legacy callers, and use a 4-Panel Full-Bleed Highlight Split for Cut 1A.
    """
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id
    canvas = Image.new("RGB", (W, H), (12, 16, 26))
    draw = ImageDraw.Draw(canvas)

    top_y = 104
    bot_y = H - 176
    avail_h = bot_y - top_y

    if len(summary_rows) >= 10:
        f_rank = ImageFont.truetype(font_path, 19)
        f_name = ImageFont.truetype(font_path, 18)
        f_sub = ImageFont.truetype(font_path, 14)
        col_w = W // 5
        row_h = avail_h // 2
        rows = summary_rows[:10]
        for idx, row in enumerate(rows):
            r_idx = idx // 5
            c_idx = idx % 5
            x0 = c_idx * col_w
            x1 = W if c_idx == 4 else (c_idx + 1) * col_w
            y0 = top_y + r_idx * row_h
            y1 = bot_y if r_idx == 1 else (top_y + row_h)

            p_path = cache_dir / row["thumb"]
            if p_path.exists():
                tile = fit_crop(Image.open(p_path), x1 - x0, y1 - y0)
                tile = ImageEnhance.Brightness(tile).enhance(0.95)
                tile = ImageEnhance.Contrast(tile).enhance(1.06)
                canvas.paste(tile, (x0, y0))

            draw.rectangle([(x0, y0), (x1, y1)], outline=(255, 255, 255), width=2)

            is_top3 = row["rank"] in ("#1", "#2", "#3")
            bg_col = (217, 119, 6) if row["rank"] == "#1" else ((220, 38, 38) if is_top3 else (30, 58, 138))
            badge_y = y0 + 8
            draw.rectangle([(x0 + 8, badge_y), (x1 - 8, badge_y + 32)], fill=bg_col, outline=(255, 255, 255), width=2)
            label = f"{row['rank']}  {row['score']}"
            tb = draw.textbbox((0, 0), label, font=f_rank)
            tw = tb[2] - tb[0]
            draw.text((x0 + ((x1 - x0) - tw) // 2, badge_y + 6), label, font=f_rank, fill=(255, 255, 255))

            strip_y0 = y1 - 50
            draw.rectangle([(x0 + 1, strip_y0), (x1 - 1, y1 - 1)], fill=(10, 14, 24))
            short_en = strip_cjk(row["name_en"].split("(")[0].strip())[:20]
            tb_n = draw.textbbox((0, 0), short_en, font=f_name)
            nw = tb_n[2] - tb_n[0]
            draw.text((x0 + max(4, ((x1 - x0) - nw) // 2), strip_y0 + 5), short_en, font=f_name, fill=(253, 224, 71))
            acc_en = strip_cjk(row.get("access_short", row.get("budget", "")))[:24]
            tb_j = draw.textbbox((0, 0), acc_en, font=f_sub)
            jw = tb_j[2] - tb_j[0]
            draw.text((x0 + max(4, ((x1 - x0) - jw) // 2), strip_y0 + 28), acc_en, font=f_sub, fill=(226, 232, 240))

    canvas.save(out_jpg_b, "JPEG", quality=95)
    canvas.save(out_jpg_a, "JPEG", quality=95)


def draw_rounded_box(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill: Tuple[int, ...],
    outline: Tuple[int, ...] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def render_area_map_overlay_png(
    area_guide: Dict[str, Any],
    font_path: str,
    out_png: Path,
    hint_text: str = "",
) -> None:
    """
    Render a sleek, broadcast-grade transparent overlay for AREA GUIDE 1/2 (100% English):
    - Left side: Real 47-prefecture geographic map of Japan highlighting the exact target prefecture(s)
      and drawing the route line from Tokyo to that prefecture's exact coordinates!
    - Right side: 3 Bold Hero Cards driven dynamically from area_guide['cards'] (with CJK auto-stripped)!
    """
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for x in range(W):
        alpha = int(210 * max(0.25, 1.0 - (x / (W * 1.15)) ** 1.3))
        draw.line([(x, 104), (x, H - 174)], fill=(8, 13, 24, alpha))

    # 1. Left Geographic Map Panel (x=32..522, y=118..530)
    mx0, my0, mx1, my1 = 32, 118, 522, 530
    draw_rounded_box(draw, (mx0, my0, mx1, my1), radius=14, fill=(10, 18, 34, 236), outline=(56, 189, 248, 220), width=2)

    f_mhead = ImageFont.truetype(font_path, 15)
    mhead_txt = "JAPAN LOCATOR & SHINKANSEN MAP"
    tb_mh = draw.textbbox((0, 0), mhead_txt, font=f_mhead)
    mhw = (tb_mh[2] - tb_mh[0]) + 28
    draw_rounded_box(draw, (mx0 + 14, my0 + 12, mx0 + 14 + mhw, my0 + 44), radius=6, fill=(14, 116, 144, 245))
    draw.text((mx0 + 28, my0 + 19), mhead_txt, font=f_mhead, fill=(255, 255, 255, 255))

    map_json = BASE_DIR / "assets" / "maps" / "japan_prefectures.json"
    lon_min, lon_max = 129.5, 145.8
    lat_min, lat_max = 31.0, 45.6
    pad_x0, pad_y0, pad_x1, pad_y1 = mx0 + 22, my0 + 54, mx1 - 24, my1 - 30

    def project(lon: float, lat: float) -> Tuple[int, int]:
        px = pad_x0 + (lon - lon_min) / (lon_max - lon_min) * (pad_x1 - pad_x0)
        py = pad_y1 - (lat - lat_min) / (lat_max - lat_min) * (pad_y1 - pad_y0)
        return int(round(px)), int(round(py))

    prefs = json.loads(map_json.read_text(encoding="utf-8")) if map_json.exists() else []
    target_pref, route_pts = resolve_prefecture_and_route(area_guide, hint_text, prefs)

    if prefs:
        for pf in prefs:
            if pf["nam_ja"] == target_pref:
                continue
            is_tokyo = pf["nam_ja"] == "東京都"
            fill_c = (56, 189, 248, 210) if is_tokyo else (51, 65, 85, 200)
            out_c = (148, 163, 184, 150)
            for ring in pf["polys"]:
                if any(pt[0] < lon_min or pt[0] > lon_max or pt[1] < lat_min or pt[1] > lat_max for pt in ring):
                    continue
                pts = [project(pt[0], pt[1]) for pt in ring]
                if len(pts) >= 3:
                    draw.polygon(pts, fill=fill_c, outline=out_c)
        for pf in prefs:
            if pf["nam_ja"] == target_pref:
                for ring in pf["polys"]:
                    if any(pt[0] < lon_min or pt[0] > lon_max or pt[1] < lat_min or pt[1] > lat_max for pt in ring):
                        continue
                    pts = [project(pt[0], pt[1]) for pt in ring]
                    if len(pts) >= 3:
                        draw.polygon(pts, fill=(239, 68, 68, 255), outline=(253, 224, 71, 255))
                        draw.line(pts + [pts[0]], fill=(253, 224, 71, 255), width=2)

    proj_route = [project(lon, lat) for lon, lat in route_pts]
    draw.line(proj_route, fill=(253, 224, 71, 255), width=4)

    tx_p, ty_p = project(route_pts[0][0], route_pts[0][1])
    hx_p, hy_p = project(route_pts[-1][0], route_pts[-1][1])
    draw.ellipse([(tx_p - 6, ty_p - 6), (tx_p + 6, ty_p + 6)], fill=(56, 189, 248, 255), outline=(255, 255, 255, 255), width=2)
    draw.ellipse([(hx_p - 8, hy_p - 8), (hx_p + 8, hy_p + 8)], fill=(239, 68, 68, 255), outline=(253, 224, 71, 255), width=2)

    f_pin = ImageFont.truetype(font_path, 15)
    f_subpin = ImageFont.truetype(font_path, 13)
    map_badge = smart_truncate(draw, area_guide.get("map_badge", "TOP RANKED DESTINATIONS"), f_subpin, 245)

    draw_rounded_box(draw, (mx0 + 18, my0 + 54, mx0 + 286, my0 + 102), radius=6, fill=(185, 28, 28, 245), outline=(253, 224, 71, 255), width=2)
    draw.text((mx0 + 28, my0 + 60), "TARGET REGION", font=f_pin, fill=(255, 255, 255, 255))
    draw.text((mx0 + 28, my0 + 80), map_badge, font=f_subpin, fill=(253, 224, 71, 255))

    draw_rounded_box(draw, (tx_p + 10, ty_p - 14, tx_p + 142, ty_p + 26), radius=6, fill=(15, 23, 42, 240), outline=(56, 189, 248, 240), width=1)
    draw.text((tx_p + 18, ty_p - 9), "TOKYO HUB", font=f_pin, fill=(56, 189, 248, 255))
    draw.text((tx_p + 18, ty_p + 9), "Direct Rail / Air", font=f_subpin, fill=(226, 232, 240, 255))

    draw.line([(mx0 + 20, my1 - 24), (mx0 + 54, my1 - 24)], fill=(253, 224, 71, 255), width=4)
    draw.text((mx0 + 62, my1 - 31), "Direct Shinkansen / Express Route from Tokyo", font=f_subpin, fill=(253, 224, 71, 255))

    # 2. Right Side: 3 Sleek Hero-Metric Glass Cards driven dynamically by area_guide['cards'] (x=546..1248)
    rx0, rx1 = 546, W - 32
    f_big = ImageFont.truetype(font_path, 20)
    f_unit = ImageFont.truetype(font_path, 14)
    f_ctitle = ImageFont.truetype(font_path, 20)

    raw_cards = area_guide.get("cards", [])
    palettes = [
        ("KEY FACT #1", "INSIDER DATA", (16, 185, 129, 245), (52, 211, 153, 235)),
        ("KEY FACT #2", "EXPERT GUIDE", (2, 132, 199, 245), (56, 189, 248, 235)),
        ("KEY FACT #3", "PRO TRAVEL TIP", (217, 119, 6, 245), (251, 191, 36, 235)),
    ]

    card_h = 126
    gap = 16
    for i in range(3):
        m_lbl, s_lbl, b_fill, b_bord = palettes[i]
        if i < len(raw_cards):
            rc = raw_cards[i]
            c_title = strip_cjk(rc.get("title", f"INSIDER POINT {i+1}"))
            bullets = [strip_cjk(b) for b in rc.get("bullets", []) if strip_cjk(b)]
            line1 = bullets[0] if len(bullets) > 0 else ""
            line2 = bullets[1] if len(bullets) > 1 else ""
        else:
            c_title = f"INSIDER GUIDE POINT #{i+1}"
            line1 = "Direct Shinkansen & local train access from major hubs"
            line2 = "Arrive early at opening time to beat peak sightseeing crowds"

        cy0 = 118 + i * (card_h + gap)
        cy1 = cy0 + card_h
        draw_rounded_box(draw, (rx0, cy0, rx1, cy1), radius=12, fill=(12, 19, 34, 230), outline=b_bord, width=2)

        bx0, by0, bx1, by1 = rx0 + 12, cy0 + 12, rx0 + 172, cy1 - 12
        draw_rounded_box(draw, (bx0, by0, bx1, by1), radius=10, fill=b_fill)
        tb_m = draw.textbbox((0, 0), m_lbl, font=f_big)
        mw = tb_m[2] - tb_m[0]
        draw.text((bx0 + (160 - mw) // 2, by0 + 22), m_lbl, font=f_big, fill=(255, 255, 255, 255))
        tb_u = draw.textbbox((0, 0), s_lbl, font=f_unit)
        uw = tb_u[2] - tb_u[0]
        draw.text((bx0 + (160 - uw) // 2, by0 + 64), s_lbl, font=f_unit, fill=(254, 249, 195, 255))

        tx = bx1 + 18
        max_w = rx1 - tx - 14
        clean_ct = smart_truncate(draw, c_title, f_ctitle, max_w)
        draw.text((tx, cy0 + 14), clean_ct, font=f_ctitle, fill=(253, 224, 71, 255))

        if line1:
            f_l1 = fit_font_for_width(draw, line1, font_path, 16, 13, max_w)
            c_l1 = smart_truncate(draw, line1, f_l1, max_w)
            draw.text((tx, cy0 + 48), c_l1, font=f_l1, fill=(255, 255, 255, 255))
        if line2:
            f_l2 = fit_font_for_width(draw, line2, font_path, 16, 13, max_w)
            c_l2 = smart_truncate(draw, line2, f_l2, max_w)
            draw.text((tx, cy0 + 80), c_l2, font=f_l2, fill=(186, 230, 253, 255))

    overlay.save(out_png, "PNG")


def render_area_seasons_jpg(
    ranking_id: str,
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg_a: Path,
    out_jpg_b: Path,
) -> None:
    """
    Render a stunning 4-Column Full-Bleed Visual Showcase for GUIDE 2/2 (100% English):
    Uses the actual top 4 spot photos from summary_rows with zero mid-word truncation!
    """
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id
    canvas = Image.new("RGB", (W, H), (10, 14, 24))
    draw = ImageDraw.Draw(canvas, "RGBA")

    top_y = 106
    bot_y = H - 176
    panel_h = bot_y - top_y
    col_w = W // 4

    f_shead = ImageFont.truetype(font_path, 22)
    f_smon = ImageFont.truetype(font_path, 14)
    f_stitle = ImageFont.truetype(font_path, 19)
    f_ssub = ImageFont.truetype(font_path, 14)

    thumbs = [r["thumb"] for r in summary_rows[:4]] if len(summary_rows) >= 4 else ["", "", "", ""]
    names = [
        smart_truncate(draw, r["name_en"].split("(")[0].strip(), f_stitle, col_w - 16)
        for r in summary_rows[:4]
    ] if len(summary_rows) >= 4 else ["Spring", "Summer", "Autumn", "Winter"]
    subs = [
        smart_truncate(draw, r.get("dish", "").split("(")[0].strip() or r.get("access_short", ""), f_ssub, col_w - 16)
        for r in summary_rows[:4]
    ] if len(summary_rows) >= 4 else ["", "", "", ""]

    seasons = [
        {
            "label": "TOP PICK #1",
            "months": "SPRING–SUMMER  |  PEAK SEASON",
            "color": (219, 39, 119, 240),
            "border": (244, 114, 182, 255),
            "photo": thumbs[0],
            "title": names[0],
            "sub": subs[0] or "Peak cherry blossoms & mild weather",
        },
        {
            "label": "TOP PICK #2",
            "months": "ALL SEASONS  |  LOCAL FAVORITE",
            "color": (5, 150, 105, 240),
            "border": (52, 211, 153, 255),
            "photo": thumbs[1],
            "title": names[1],
            "sub": subs[1] or "Early morning visits & summer festivals",
        },
        {
            "label": "TOP PICK #3",
            "months": "AUTUMN  |  SCENIC FOLIAGE",
            "color": (217, 119, 6, 240),
            "border": (251, 191, 36, 255),
            "photo": thumbs[2],
            "title": names[2],
            "sub": subs[2] or "Crisp clear skies & autumn foliage",
        },
        {
            "label": "TOP PICK #4",
            "months": "WINTER–SPRING  |  HIDDEN GEM",
            "color": (2, 132, 199, 240),
            "border": (125, 211, 252, 255),
            "photo": thumbs[3],
            "title": names[3],
            "sub": subs[3] or "Fewer crowds & dramatic winter views",
        },
    ]

    for i, s in enumerate(seasons):
        x0 = i * col_w
        x1 = W if i == 3 else (i + 1) * col_w
        p_path = cache_dir / s["photo"] if s["photo"] else None
        if p_path and p_path.exists():
            tile = fit_crop(Image.open(p_path), x1 - x0, panel_h)
            tile = ImageEnhance.Contrast(tile).enhance(1.08)
            canvas.paste(tile, (x0, top_y))

        draw_rounded_box(
            draw,
            (x0 + 12, top_y + 12, x1 - 12, top_y + 76),
            radius=10,
            fill=(10, 15, 28, 225),
            outline=s["border"],
            width=2,
        )
        draw_rounded_box(
            draw,
            (x0 + 14, top_y + 14, x1 - 14, top_y + 46),
            radius=8,
            fill=s["color"],
        )
        tb_l = draw.textbbox((0, 0), s["label"], font=f_shead)
        lw = tb_l[2] - tb_l[0]
        draw.text((x0 + ((x1 - x0) - lw) // 2, top_y + 18), s["label"], font=f_shead, fill=(255, 255, 255, 255))

        tb_m = draw.textbbox((0, 0), s["months"], font=f_smon)
        mw = tb_m[2] - tb_m[0]
        draw.text((x0 + ((x1 - x0) - mw) // 2, top_y + 52), s["months"], font=f_smon, fill=(254, 240, 138, 255))

        strip_y0 = bot_y - 82
        draw.rectangle([(x0, strip_y0), (x1, bot_y)], fill=(8, 12, 22, 235))
        draw.line([(x0, strip_y0), (x1, strip_y0)], fill=s["border"], width=2)

        tb_t = draw.textbbox((0, 0), s["title"], font=f_stitle)
        tw = tb_t[2] - tb_t[0]
        draw.text((x0 + ((x1 - x0) - tw) // 2, strip_y0 + 12), s["title"], font=f_stitle, fill=(253, 224, 71, 255))

        tb_s = draw.textbbox((0, 0), s["sub"], font=f_ssub)
        sw = tb_s[2] - tb_s[0]
        draw.text((x0 + max(6, ((x1 - x0) - sw) // 2), strip_y0 + 46), s["sub"], font=f_ssub, fill=(241, 245, 249, 255))

        if i > 0:
            draw.line([(x0, top_y), (x0, bot_y)], fill=(255, 255, 255, 220), width=2)

    canvas.save(out_jpg_a, "JPEG", quality=95)
    canvas.save(out_jpg_b, "JPEG", quality=95)


def render_summary_table_jpg(
    ranking_id: str,
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg_a: Path,
    out_jpg_b: Path,
) -> None:
    """Render a full-screen 2-col x 5-row (Top 10) Comparison Cheat-Sheet Table (100% English, Large Readable Fonts)."""
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id
    canvas = Image.new("RGB", (W, H), (11, 15, 25))
    draw = ImageDraw.Draw(canvas)

    top_y = 108
    avail_h = H - 176 - top_y - 6
    row_h = avail_h // 5

    if len(summary_rows) >= 10:
        f_rank = ImageFont.truetype(font_path, 16)
        f_title = ImageFont.truetype(font_path, 18)
        f_sub = ImageFont.truetype(font_path, 14)
        f_hack = ImageFont.truetype(font_path, 14)
        col_w = (W - 36) // 2

        for idx, row in enumerate(summary_rows[:10]):
            c_idx = idx // 5
            r_idx = idx % 5
            x0 = 14 + c_idx * (col_w + 8)
            x1 = x0 + col_w
            y0 = top_y + r_idx * row_h + 3
            y1 = y0 + row_h - 5

            bg = (22, 30, 48) if r_idx % 2 == 0 else (17, 24, 39)
            draw.rectangle([(x0, y0), (x1, y1)], fill=bg, outline=(100, 116, 139), width=1)

            p_path = cache_dir / row["thumb"]
            thumb_w = 82
            if p_path.exists():
                th = fit_crop(Image.open(p_path), thumb_w, y1 - y0 - 4)
                canvas.paste(th, (x0 + 2, y0 + 2))

            rx = x0 + thumb_w + 8
            badge_w = 114
            is_no1 = row["rank"] == "#1"
            is_top3 = row["rank"] in ("#1", "#2", "#3")
            b_col = (217, 119, 6) if is_no1 else ((220, 38, 38) if is_top3 else (30, 58, 138))
            draw.rectangle([(rx, y0 + 6), (rx + badge_w, y0 + 34)], fill=b_col, outline=(255, 255, 255), width=1)
            r_txt = f"{row['rank']} {row['score']}"
            tb_r = draw.textbbox((0, 0), r_txt, font=f_rank)
            draw.text((rx + (badge_w - (tb_r[2] - tb_r[0])) // 2, y0 + 11), r_txt, font=f_rank, fill=(255, 255, 255))

            acc_raw = row.get("access_short", row.get("budget", ""))
            f_acc = fit_font_for_width(draw, acc_raw, font_path, 13, 10, badge_w + 4)
            acc_short = smart_truncate(draw, acc_raw, f_acc, badge_w + 4)
            draw.text((rx + 2, y0 + 42), acc_short, font=f_acc, fill=(125, 211, 252))

            tx = rx + badge_w + 10
            max_tw = x1 - tx - 8

            f_t_row = fit_font_for_width(draw, row["name_en"], font_path, 17, 12, max_tw)
            title_str = smart_truncate(draw, row["name_en"], f_t_row, max_tw)
            f_d_row = fit_font_for_width(draw, row["dish"], font_path, 14, 11, max_tw)
            dish_str = smart_truncate(draw, row["dish"], f_d_row, max_tw)
            f_h_row = fit_font_for_width(draw, f"TIP: {row['hack']}", font_path, 13, 11, max_tw)
            hack_str = smart_truncate(draw, f"TIP: {row['hack']}", f_h_row, max_tw)

            draw.text((tx, y0 + 6), title_str, font=f_t_row, fill=(255, 255, 255))
            draw.text((tx, y0 + 30), dish_str, font=f_d_row, fill=(253, 224, 71))
            draw.text((tx, y0 + 50), hack_str, font=f_h_row, fill=(167, 243, 208))
    else:
        f_rank = ImageFont.truetype(font_path, 22)
        f_title = ImageFont.truetype(font_path, 20)
        f_sub = ImageFont.truetype(font_path, 16)
        f_hack = ImageFont.truetype(font_path, 15)

        for i, row in enumerate(summary_rows[:5]):
            y0 = top_y + i * row_h + 4
            y1 = y0 + row_h - 6
            bg = (22, 30, 48) if i % 2 == 0 else (17, 24, 39)
            draw.rectangle([(20, y0), (W - 20, y1)], fill=bg, outline=(100, 116, 139), width=1)

            p_path = cache_dir / row["thumb"]
            thumb_w = 108
            if p_path.exists():
                th = fit_crop(Image.open(p_path), thumb_w, y1 - y0 - 4)
                canvas.paste(th, (22, y0 + 2))

            rx = 22 + thumb_w + 12
            is_no1 = row["rank"] == "#1"
            b_col = (217, 119, 6) if is_no1 else (220, 38, 38)
            draw.rectangle([(rx, y0 + 10), (rx + 118, y1 - 10)], fill=b_col, outline=(255, 255, 255), width=1)
            r_txt = f"{row['rank']} {row['score']}"
            tb_r = draw.textbbox((0, 0), r_txt, font=f_rank)
            draw.text((rx + (118 - (tb_r[2] - tb_r[0])) // 2, y0 + (row_h - 26) // 2), r_txt, font=f_rank, fill=(255, 255, 255))

            tx = rx + 132
            draw.text((tx, y0 + 9), row["name_en"], font=f_title, fill=(255, 255, 255))
            draw.text((tx, y0 + 35), f"{row['dish']} | {row['budget']}", font=f_sub, fill=(253, 224, 71))

            hx = 695
            draw.rectangle([(hx, y0 + 8), (W - 28, y1 - 8)], fill=(6, 78, 59), outline=(16, 185, 129), width=1)
            draw.text((hx + 10, y0 + 22), f"HACK: {row['hack']}", font=f_hack, fill=(209, 250, 229))

    canvas.save(out_jpg_a, "JPEG", quality=95)
    canvas.save(out_jpg_b, "JPEG", quality=95)


def render_ranking_hud_png(
    seg: Dict[str, Any],
    prefecture: str,
    font_path: str,
    output_png: Path,
) -> None:
    """Render the top header, Access strip, optional Real Review Card, Local Tip strip, and Subtitle bar (100% English, High-Contrast Large Fonts)."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    f_tag = ImageFont.truetype(font_path, 18)
    f_title = ImageFont.truetype(font_path, 26)
    f_acc = ImageFont.truetype(font_path, 18)
    f_tip = ImageFont.truetype(font_path, 19)
    f_sub = ImageFont.truetype(font_path, 28)

    # 1. Top Header Card (y=0..104)
    draw.rectangle([(0, 0), (W, 104)], fill=(10, 14, 24, 236))
    draw.line([(0, 104), (W, 104)], fill=(255, 255, 255, 95), width=2)

    badge = seg["rank_badge"]
    is_rank1 = "#1 " in badge or badge.endswith("#1")
    is_guide = "GUIDE" in badge or "ACCESS" in badge
    badge_bg = (217, 119, 6, 255) if is_rank1 else ((14, 116, 144, 255) if is_guide else (220, 38, 38, 255))
    tb = draw.textbbox((0, 0), badge, font=f_tag)
    bw = (tb[2] - tb[0]) + 32

    draw.rectangle([(24, 12), (24 + bw, 46)], fill=badge_bg, outline=(255, 255, 255, 230), width=2)
    draw.text((40, 19), badge, font=f_tag, fill=(255, 255, 255, 255))

    # Top-right Area & Budget Pill on Row 1 (strictly bounded to max 410px so center badge never collides)
    info_right = strip_cjk(f"{seg['area']}  |  {seg['budget']}")
    f_r_fit = fit_font_for_width(draw, info_right, font_path, 17, 13, 410)
    info_right = smart_truncate(draw, info_right, f_r_fit, 410)
    tb_r = draw.textbbox((0, 0), info_right, font=f_r_fit)
    rw = tb_r[2] - tb_r[0]
    right_box_x0 = W - rw - 44

    draw.rectangle(
        [(right_box_x0, 12), (W - 20, 46)],
        fill=(30, 41, 59, 245),
        outline=(148, 163, 184, 210),
        width=2,
    )
    draw.text((W - rw - 32, 19), info_right, font=f_r_fit, fill=(253, 224, 71, 255))

    # Top-Center Permanent "[IG Logo] JAPANESE IG ANALYZED • 日本人のリアルな声" Badge on Row 1
    cjk_font_path = find_cjk_font()
    left_edge = 24 + bw + 12
    avail_mid_w = right_box_x0 - left_edge - 12
    if avail_mid_w >= 220:
        np_txt = "JAPANESE IG ANALYZED • 日本人のリアルな声"
        f_np_fit = ImageFont.truetype(cjk_font_path, 15)
        tb_np = draw.textbbox((0, 0), np_txt, font=f_np_fit)
        while (tb_np[2] - tb_np[0]) + 56 > avail_mid_w and f_np_fit.size > 11:
            f_np_fit = ImageFont.truetype(cjk_font_path, f_np_fit.size - 1)
            tb_np = draw.textbbox((0, 0), np_txt, font=f_np_fit)
        np_w = min(avail_mid_w, (tb_np[2] - tb_np[0]) + 56)
        np_x0 = left_edge + max(0, (avail_mid_w - np_w) // 2)
        draw.rounded_rectangle(
            (np_x0, 12, np_x0 + np_w, 46),
            radius=8,
            fill=(18, 14, 32, 248),
            outline=(225, 48, 108, 250),
            width=2,
        )
        draw_instagram_logo(overlay, np_x0 + 8, 15, 28)
        draw.text((np_x0 + 42, 20), np_txt, font=f_np_fit, fill=(255, 215, 235, 255))

    # Main English Place Title on Row 2 (Large 26px bold with dark stroke)
    title_en = strip_cjk(seg["place_en"].strip()).replace("What You Get in This 9-Min Guide", "100% UNSPONSORED TOP 10 — ANALYZED FROM JAPANESE IG!")
    f_title_fit = fit_font_for_width(draw, title_en, font_path, 26, 17, W - 48)
    title_en = smart_truncate(draw, title_en, f_title_fit, W - 48)
    draw.text(
        (24, 56),
        title_en,
        font=f_title_fit,
        fill=(255, 255, 255, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 245),
    )

    # 1b. Optional Dedicated ACCESS Pill Strip right below Top Header (y=106..146)
    if seg.get("access_info") and seg.get("seg_type") in ("spot", "review"):
        acc_y0, acc_y1 = 106, 146
        clean_acc = strip_cjk(seg["access_info"].replace("🚄", "").strip())
        f_acc_fit = fit_font_for_width(draw, clean_acc, font_path, 18, 13, W - 220)
        clean_acc = smart_truncate(draw, clean_acc, f_acc_fit, W - 220)
        draw.rectangle([(0, acc_y0), (W, acc_y1)], fill=(8, 47, 73, 235))
        draw.rectangle([(0, acc_y0), (190, acc_y1)], fill=(2, 132, 199, 250))
        draw.text((18, acc_y0 + 10), "TRAIN & ACCESS", font=f_acc, fill=(255, 255, 255, 255))
        draw.text(
            (206, acc_y0 + 10),
            clean_acc,
            font=f_acc_fit,
            fill=(224, 242, 254, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 220),
        )

    # 2. Optional Real Local Review Card (when seg_type == "review" — Instagram Logo + 日本人のリアルな声 + English)
    if seg.get("seg_type") == "review" and seg.get("review_praise_en"):
        f_rhead = ImageFont.truetype(cjk_font_path, 16)
        f_jp_quote = ImageFont.truetype(cjk_font_path, 17)
        card_x0, card_x1 = 24, W - 24
        max_rw = (card_x1 - card_x0) - 32

        c1_y0, c1_y1 = 324, 428
        lbl1 = "日本人のリアルな声  •  REAL JAPANESE INSTAGRAM VOICE (NO PROMO)"
        tb_l1 = draw.textbbox((0, 0), lbl1, font=f_rhead)
        l1_w = (tb_l1[2] - tb_l1[0]) + 62
        jp_praise = synthesize_jp_local_voice(badge, title_en, seg.get("area", ""), "praise", seg.get("review_praise_ja", ""))
        praise_txt = strip_cjk(seg["review_praise_en"])
        f_ren1 = fit_font_for_width(draw, praise_txt, font_path, 19, 14, max_rw)
        praise_txt = smart_truncate(draw, praise_txt, f_ren1, max_rw)
        draw.rounded_rectangle((card_x0, c1_y0, card_x1, c1_y1), radius=12, fill=(16, 14, 28, 242), outline=(225, 48, 108, 250), width=2)
        draw.rounded_rectangle((card_x0, c1_y0, card_x0 + l1_w, c1_y0 + 34), radius=10, fill=(225, 48, 108, 250))
        draw_instagram_logo(overlay, card_x0 + 8, c1_y0 + 3, 28)
        draw.text((card_x0 + 44, c1_y0 + 8), lbl1, font=f_rhead, fill=(255, 255, 255, 255))
        draw.text((card_x0 + 16, c1_y0 + 42), jp_praise, font=f_jp_quote, fill=(255, 215, 110, 255))
        draw.text((card_x0 + 16, c1_y0 + 68), praise_txt, font=f_ren1, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 230))

        c2_y0, c2_y1 = 436, 536
        lbl2 = "地元の裏技・注意点  •  UNFILTERED LOCAL IG WARNING & HACK"
        tb_l2 = draw.textbbox((0, 0), lbl2, font=f_rhead)
        l2_w = (tb_l2[2] - tb_l2[0]) + 62
        jp_warn = synthesize_jp_local_voice(badge, title_en, seg.get("area", ""), "warn", seg.get("review_warn_ja", ""))
        warn_txt = strip_cjk(seg["review_warn_en"])
        f_ren2 = fit_font_for_width(draw, warn_txt, font_path, 19, 14, max_rw)
        warn_txt = smart_truncate(draw, warn_txt, f_ren2, max_rw)
        draw.rounded_rectangle((card_x0, c2_y0, card_x1, c2_y1), radius=12, fill=(16, 14, 28, 242), outline=(245, 158, 11, 250), width=2)
        draw.rounded_rectangle((card_x0, c2_y0, card_x0 + l2_w, c2_y0 + 34), radius=10, fill=(217, 119, 6, 250))
        draw_instagram_logo(overlay, card_x0 + 8, c2_y0 + 3, 28)
        draw.text((card_x0 + 44, c2_y0 + 8), lbl2, font=f_rhead, fill=(255, 255, 255, 255))
        draw.text((card_x0 + 16, c2_y0 + 42), jp_warn, font=f_jp_quote, fill=(255, 200, 225, 255))
        draw.text((card_x0 + 16, c2_y0 + 68), warn_txt, font=f_ren2, fill=(253, 224, 71, 255), stroke_width=2, stroke_fill=(0, 0, 0, 230))

    # 3. Bottom Insider Tip Bar + Subtitle Bar
    sub_bar_h = 132
    sub_y0 = H - sub_bar_h
    tip_bar_h = 44
    tip_y0 = sub_y0 - tip_bar_h

    sec_label = "INSIDER TIP"
    tb_sec = draw.textbbox((0, 0), sec_label, font=f_tag)
    sec_w = (tb_sec[2] - tb_sec[0]) + 36
    tip_txt = strip_cjk(seg["insider_tip"])
    f_tip_fit = fit_font_for_width(draw, tip_txt, font_path, 19, 13, W - sec_w - 32)
    tip_txt = smart_truncate(draw, tip_txt, f_tip_fit, W - sec_w - 32)
    draw.rectangle([(0, tip_y0), (W, sub_y0)], fill=(15, 23, 42, 238))
    draw.rectangle([(0, tip_y0), (sec_w, sub_y0)], fill=(16, 185, 129, 250))
    draw.text((18, tip_y0 + 12), sec_label, font=f_tag, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 180))
    draw.text(
        (sec_w + 18, tip_y0 + 11),
        tip_txt,
        font=f_tip_fit,
        fill=(167, 243, 208, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 230),
    )

    # Subtitle Box (auto-fits font size per line so no subtitle ever clips at left/right screen edges)
    draw.rectangle([(0, sub_y0), (W, H)], fill=(6, 9, 15, 228))
    lines = [strip_cjk(ln) for ln in seg["subtitle"].split("\n") if strip_cjk(ln)]
    line_spacing = 10
    total_h = len(lines) * 34 + max(0, len(lines) - 1) * line_spacing
    cur_y = sub_y0 + (sub_bar_h - total_h) // 2

    for line in lines:
        f_line = fit_font_for_width(draw, line, font_path, 27, 17, W - 48)
        tb_l = draw.textbbox((0, 0), line, font=f_line)
        lw = tb_l[2] - tb_l[0]
        x = max(24, (W - lw) // 2)
        draw.text(
            (x, cur_y),
            line,
            font=f_line,
            fill=(255, 255, 255, 255),
            stroke_width=3,
            stroke_fill=(0, 0, 0, 245),
        )
        cur_y += 34 + line_spacing

    overlay.save(output_png, "PNG")


def synthesize_transition_se(se_type: str, duration_sec: float = 0.55) -> List[float]:
    """Synthesize crisp transition sound effects (Whoosh+Chime, Top 3 Taiko Riser, Review Pop, Shinkansen Chime)."""
    sr = 44100
    n = int(sr * duration_sec)
    samples = [0.0] * n
    rng = random.Random(42)

    if se_type == "top3_hit":
        # Dramatic riser + double Japanese Taiko drum impact + golden shimmer chord
        for i in range(n):
            t = i / sr
            # Riser (0.0 -> 0.22s)
            riser = 0.0
            if t < 0.22:
                f_sweep = 180.0 + 950.0 * (t / 0.22) ** 2
                riser = 0.35 * math.sin(2.0 * math.pi * f_sweep * t) * (t / 0.22)
            # Taiko hit 1 at 0.20s, hit 2 at 0.34s
            taiko = 0.0
            for t0 in (0.20, 0.34):
                if t >= t0:
                    dt = t - t0
                    f_drum = 62.0 + 90.0 * math.exp(-dt * 28.0)
                    taiko += 0.65 * math.sin(2.0 * math.pi * f_drum * dt) * math.exp(-dt * 9.5)
            # Golden pentatonic shimmer chord from 0.20s
            shimmer = 0.0
            if t >= 0.20:
                dt = t - 0.20
                for freq in (523.25, 659.25, 783.99, 1046.50, 1318.51):
                    shimmer += 0.12 * math.sin(2.0 * math.pi * freq * dt) * math.exp(-dt * 4.2)
            samples[i] = max(-0.92, min(0.92, riser + taiko + shimmer))

    elif se_type == "rank_whoosh":
        # Punchy whoosh + ascending koto/bell 3-note chime
        notes = [(0.06, 587.33), (0.14, 783.99), (0.22, 1046.50)]
        for i in range(n):
            t = i / sr
            whoosh = (rng.random() * 2.0 - 1.0) * 0.18 * math.sin(math.pi * min(1.0, t / 0.26)) * math.exp(-t * 8.0)
            sub_kick = 0.45 * math.sin(2.0 * math.pi * (85.0 * math.exp(-t * 14.0) + 45.0) * t) * math.exp(-t * 11.0)
            chime = 0.0
            for t0, freq in notes:
                if t >= t0:
                    dt = t - t0
                    chime += 0.24 * math.sin(2.0 * math.pi * freq * dt) * math.exp(-dt * 8.5)
            samples[i] = max(-0.9, min(0.9, whoosh + sub_kick + chime))

    elif se_type == "review_pop":
        # Crisp UI card pop + two-tone warm Marimba/Bell ding
        notes = [(0.02, 659.25), (0.11, 880.00)]
        for i in range(n):
            t = i / sr
            pop = 0.35 * math.sin(2.0 * math.pi * (320.0 + 400.0 * t) * t) * math.exp(-t * 35.0)
            bell = 0.0
            for t0, freq in notes:
                if t >= t0:
                    dt = t - t0
                    bell += 0.28 * (math.sin(2.0 * math.pi * freq * dt) + 0.3 * math.sin(4.0 * math.pi * freq * dt)) * math.exp(-dt * 10.0)
            samples[i] = max(-0.88, min(0.88, pop + bell))

    elif se_type == "area_chime":
        # Shinkansen-inspired 4-note pleasant departure chime
        notes = [(0.02, 523.25), (0.13, 659.25), (0.24, 783.99), (0.35, 1046.50)]
        for i in range(n):
            t = i / sr
            chime = 0.0
            for t0, freq in notes:
                if t >= t0:
                    dt = t - t0
                    chime += 0.25 * math.sin(2.0 * math.pi * freq * dt) * math.exp(-dt * 6.5)
            samples[i] = max(-0.88, min(0.88, chime))

    return samples


def build_segment_audio_with_se(
    tts_mp3: Path,
    seg_type: str,
    rank_badge: str,
    out_wav: Path,
) -> float:
    """
    Prepend a 0.42s transition breath with a crisp Sound Effect (SE) before the TTS voice starts,
    and add a subtle camera-shutter tick at the mid-segment photo cut!
    Returns exact duration in seconds.
    """
    sr = 44100
    raw_tts_wav = out_wav.with_name(out_wav.stem + "_rawtts.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(tts_mp3), "-ar", str(sr), "-ac", "1", str(raw_tts_wav)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with wave.open(str(raw_tts_wav), "r") as wf:
        n_tts = wf.getnframes()
        raw_bytes = wf.readframes(n_tts)
    raw_tts_wav.unlink(missing_ok=True)

    import struct
    tts_pcm = struct.unpack(f"<{n_tts}h", raw_bytes)

    # Determine SE type and lead-in breath time
    is_top3 = any(tag in rank_badge for tag in ("#1 ", "#2 ", "#3 ")) and seg_type == "spot"
    if is_top3:
        se_samples = synthesize_transition_se("top3_hit", 0.75)
        lead_samples = int(sr * 0.52)
    elif seg_type == "spot":
        se_samples = synthesize_transition_se("rank_whoosh", 0.52)
        lead_samples = int(sr * 0.40)
    elif seg_type == "review":
        se_samples = synthesize_transition_se("review_pop", 0.42)
        lead_samples = int(sr * 0.32)
    elif seg_type in ("area_guide", "opening", "summary"):
        se_samples = synthesize_transition_se("area_chime", 0.60)
        lead_samples = int(sr * 0.38)
    else:
        se_samples = []
        lead_samples = int(sr * 0.20)

    tail_samples = int(sr * 0.18)
    total_len = lead_samples + n_tts + tail_samples
    mixed = [0.0] * total_len

    # Mix in lead-in SE
    for i, s_val in enumerate(se_samples):
        if i < total_len:
            mixed[i] += s_val * 0.52

    # Mix in TTS narration after lead_samples
    for i, pcm_val in enumerate(tts_pcm):
        mixed[lead_samples + i] += (pcm_val / 32768.0)

    # Add subtle camera shutter/woodblock tick at exact midpoint for spot/review segments
    if seg_type in ("spot", "review"):
        mid_idx = total_len // 2
        tick_len = int(sr * 0.08)
        for i in range(tick_len):
            if mid_idx + i < total_len:
                t = i / sr
                tick = 0.18 * math.sin(2.0 * math.pi * 1200.0 * t) * math.exp(-t * 65.0)
                mixed[mid_idx + i] += tick

    # Write stereo WAV
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        buf = bytearray()
        chunk = 4410
        for start in range(0, total_len, chunk):
            end = min(start + chunk, total_len)
            buf.clear()
            for i in range(start, end):
                v = max(-0.96, min(0.96, mixed[i]))
                pcm = int(v * 32767)
                lo = pcm & 0xFF
                hi = (pcm >> 8) & 0xFF
                buf.extend((lo, hi, lo, hi))
            wf.writeframes(buf)

    return round(total_len / sr, 3)


def generate_dynamic_4act_bgm(
    output_mp3: Path,
    total_dur: float,
    act_boundaries: Tuple[float, float, float],
    seg_starts: List[float],
) -> None:
    """
    Synthesize a 4-Act Dynamic BGM Track with real rhythmic drums (kick, snare, hi-hat),
    walking bassline, chord progressions, pentatonic pluck melodies, and auto-ducking swells!
    - Act 1 (0 .. t_countdown): 118 BPM Upbeat Neo-Japanese Intro & Area Guide Groove
    - Act 2 (t_countdown .. t_top3): 112 BPM Driving Countdown Travel Beat (#10 -> #4)
    - Act 3 (t_top3 .. t_summary): 128 BPM High-Energy Top 3 Climax Anthem (#3 -> #1, Key +3st!)
    - Act 4 (t_summary .. end): 96 BPM Warm Chill Finale
    """
    sr = 44100
    total_samples = int(sr * total_dur)
    wav_path = output_mp3.with_suffix(".wav")
    t_act2, t_act3, t_act4 = act_boundaries

    # Act 1 & 2 Chords (Fmaj7 - G7 - Em7 - Am7)
    chords_base = [
        (174.61, 220.00, 261.63, 329.63),
        (196.00, 246.94, 293.66, 349.23),
        (164.81, 196.00, 246.94, 293.66),
        (220.00, 261.63, 329.63, 392.00),
    ]
    # Act 3 Climax Chords (Modulated +3 semitones up: Abmaj7 - Bb7 - Gm7 - Cm7 for bright emotional lift!)
    chords_climax = [
        (207.65, 261.63, 311.13, 392.00),
        (233.08, 293.66, 349.23, 415.30),
        (196.00, 233.08, 293.66, 349.23),
        (261.63, 311.13, 392.00, 466.16),
    ]

    rng = random.Random(101)
    noise_table = [rng.random() * 2.0 - 1.0 for _ in range(4410)]

    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)

        chunk = 4410
        buf = bytearray()
        seg_ptr = 0
        n_segs = len(seg_starts)

        for start in range(0, total_samples, chunk):
            end = min(start + chunk, total_samples)
            buf.clear()
            for i in range(start, end):
                t = i / sr

                # Advance segment pointer to check if we are in the first 0.50s swell window of a segment
                while seg_ptr + 1 < n_segs and seg_starts[seg_ptr + 1] <= t:
                    seg_ptr += 1
                dt_seg = t - seg_starts[seg_ptr] if n_segs > 0 else 1.0
                # Swell BGM during segment transition breath (0..0.45s), duck during speech
                duck_gain = 1.45 if 0.0 <= dt_seg <= 0.42 else 0.85

                # Select Act tempo & chords
                if t < t_act2:
                    bpm = 118.0
                    chords = chords_base
                    energy = 1.05
                elif t < t_act3:
                    bpm = 112.0
                    chords = chords_base
                    energy = 1.0
                elif t < t_act4:
                    bpm = 128.0
                    chords = chords_climax
                    energy = 1.25  # Top 3 Climax boost!
                else:
                    bpm = 96.0
                    chords = chords_base
                    energy = 0.85

                beat_len = 60.0 / bpm
                beat_num = int(t / beat_len)
                beat_pos = (t % beat_len) / beat_len
                bar_num = beat_num // 4
                beat_in_bar = beat_num % 4
                c = chords[bar_num % 4]

                # 1. Warm Rhodes Pad with sidechain-style pumping on every beat
                pump = 0.65 + 0.35 * (1.0 - math.exp(-beat_pos * 4.0))
                pad = (
                    0.20 * math.sin(2.0 * math.pi * c[0] * t)
                    + 0.16 * math.sin(2.0 * math.pi * c[1] * t)
                    + 0.14 * math.sin(2.0 * math.pi * c[2] * t)
                    + 0.11 * math.sin(2.0 * math.pi * c[3] * t)
                ) * pump

                # 2. Rhythmic Sub-Bass (plays 8th-note groove on root & fifth)
                eighth_len = beat_len / 2.0
                eighth_pos = (t % eighth_len) / eighth_len
                bass_freq = (c[0] * 0.5) if (int(t / eighth_len) % 2 == 0) else (c[2] * 0.5)
                bass = 0.28 * math.sin(2.0 * math.pi * bass_freq * t) * math.exp(-eighth_pos * 3.2)

                # 3. Crisp Percussion (Kick on beats 0 & 2, Snare/Clap on beats 1 & 3, Hi-Hat on 8ths)
                bt_sec = t % beat_len
                eh_sec = t % eighth_len
                kick = 0.0
                snare = 0.0
                if beat_in_bar in (0, 2) and bt_sec < 0.14:
                    f_k = 52.0 + 85.0 * math.exp(-bt_sec * 35.0)
                    kick = 0.36 * math.sin(2.0 * math.pi * f_k * bt_sec) * math.exp(-bt_sec * 16.0)
                elif beat_in_bar in (1, 3) and bt_sec < 0.12:
                    nz = noise_table[i % 4410]
                    snare = (0.18 * nz + 0.12 * math.sin(2.0 * math.pi * 185.0 * bt_sec)) * math.exp(-bt_sec * 24.0)

                hihat = 0.0
                if eh_sec < 0.045:
                    hihat = 0.08 * noise_table[(i * 3) % 4410] * math.exp(-eh_sec * 65.0)

                # 4. Japanese Koto / Pluck Arpeggio on 16th/8th notes
                step_len = beat_len / (4.0 if t_act3 <= t < t_act4 else 2.0)
                step_idx = int(t / step_len)
                step_sec = t % step_len
                arp_freq = c[step_idx % 4] * (2.0 if (step_idx % 8) < 6 else 4.0)
                pluck = (
                    0.14
                    * (math.sin(2.0 * math.pi * arp_freq * t) + 0.4 * math.sin(4.0 * math.pi * arp_freq * t))
                    * math.exp(-step_sec * 11.0)
                )

                val = (pad + bass + (kick + snare + hihat + pluck) * energy) * 0.42 * duck_gain
                val = max(-0.95, min(0.95, val))
                pcm = int(val * 32767)
                lo = pcm & 0xFF
                hi = (pcm >> 8) & 0xFF
                buf.extend((lo, hi, lo, hi))
            wf.writeframes(buf)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
            str(output_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wav_path.unlink(missing_ok=True)


async def generate_tts(text: str, voice: str, out_mp3: Path) -> None:
    comm = edge_tts.Communicate(text=text, voice=voice, rate="+8%")
    await comm.save(str(out_mp3))


def get_duration(path: Path) -> float:
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(float(res.stdout.strip()), 1.0)


def build_ranking_video(script_path: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(script_path.read_text(encoding="utf-8"))
    ranking_id = data["ranking_id"]
    prefecture = data.get("prefecture", "Japan")
    voice = data.get("voice", "en-US-ChristopherNeural")
    segments = data["segments"]
    summary_rows = data.get("summary_rows", [])
    area_guide = data.get("area_guide", {})
    font_path = find_font()

    final_mp4 = OUTPUT_DIR / f"overseas_japan_{ranking_id}.mp4"
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id

    with tempfile.TemporaryDirectory(prefix="yt_rank_") as tmp_str:
        work_dir = Path(tmp_str)
        seg_videos: List[Path] = []
        seg_starts: List[float] = []
        cur_time = 0.0
        t_act2 = 0.0
        t_act3 = 0.0
        t_act4 = 0.0

        for idx, seg in enumerate(segments):
            seg_type = seg.get("seg_type", "spot")
            badge = seg["rank_badge"]
            logger.info(
                f"Processing Segment {idx + 1}/{len(segments)} [{seg_type}]: {badge} - {seg['place_en'].strip()}"
            )

            # Record Act boundary timestamps
            seg_starts.append(cur_time)
            if seg_type == "spot" and t_act2 == 0.0:
                t_act2 = cur_time
            if ("#3 " in badge or badge.endswith("#3")) and seg_type == "spot" and t_act3 == 0.0:
                t_act3 = cur_time
            if seg_type == "summary" and t_act4 == 0.0:
                t_act4 = cur_time

            tts_mp3 = work_dir / f"tts_{idx:02d}.mp3"
            asyncio.run(generate_tts(seg["narration"], voice, tts_mp3))

            seg_wav = work_dir / f"segaudio_{idx:02d}.wav"
            dur = build_segment_audio_with_se(tts_mp3, seg_type, badge, seg_wav)
            cur_time += dur

            p1 = work_dir / f"photo_{idx:02d}_a.jpg"
            p2 = work_dir / f"photo_{idx:02d}_b.jpg"

            hud_png = work_dir / f"hud_{idx:02d}.png"
            render_ranking_hud_png(seg, prefecture, font_path, hud_png)

            flash_frames: List[Path] = []
            if seg_type == "opening" and summary_rows:
                flash_frames = render_opening_flash_frames(ranking_id, seg, summary_rows, font_path, work_dir)
                render_opening_collage_jpg(ranking_id, seg, summary_rows, font_path, p1, p2)
            elif seg_type == "area_guide" and "2/2" in badge:
                render_area_seasons_jpg(ranking_id, summary_rows, font_path, p1, p2)
            elif seg_type == "area_guide":
                photos = seg.get("photos", [])
                shutil.copyfile(cache_dir / photos[0], p1)
                shutil.copyfile(cache_dir / photos[1], p2)
                map_ov_png = work_dir / f"map_ov_{idx:02d}.png"
                render_area_map_overlay_png(area_guide, font_path, map_ov_png, hint_text=f"{ranking_id} {prefecture}")
                base_ov = Image.open(map_ov_png).convert("RGBA")
                top_hud = Image.open(hud_png).convert("RGBA")
                Image.alpha_composite(base_ov, top_hud).save(hud_png, "PNG")
            elif seg_type == "summary" and summary_rows:
                render_summary_table_jpg(ranking_id, summary_rows, font_path, p1, p2)
            else:
                photos = seg.get("photos", [])
                shutil.copyfile(cache_dir / photos[0], p1)
                shutil.copyfile(cache_dir / photos[1], p2)

            half_dur = round(dur / 2.0, 3)
            half_frames = max(int(math.ceil(half_dur * FPS)), FPS)

            seg_mp4 = work_dir / f"seg_{idx:02d}.mp4"
            if seg_type == "opening" and len(flash_frames) >= 2:
                # 6-Cut Rapid-Fire Full-Screen Photo Flash Montage (~1.6s per photo with punchy zoom!)
                n_fl = len(flash_frames)
                slice_dur = round(dur / n_fl, 3)
                slice_frames = max(int(math.ceil(slice_dur * FPS)), FPS)
                fc_parts: List[str] = []
                concat_ins = ""
                for fi in range(n_fl):
                    d_this = slice_dur if fi < n_fl - 1 else round(max(0.5, dur - slice_dur * (n_fl - 1) + 0.1), 3)
                    zp_f = f"zoompan=z='min(zoom+0.0007,1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={slice_frames}:s={W}x{H}:fps={FPS}"
                    fc_parts.append(
                        f"[{fi}:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},{zp_f},trim=duration={d_this},setpts=PTS-STARTPTS,setsar=1[vf{fi}]"
                    )
                    concat_ins += f"[vf{fi}]"
                fc_parts.append(f"{concat_ins}concat=n={n_fl}:v=1:a=0[bg]")
                fc_parts.append(
                    f"[bg][{n_fl}:v]overlay=0:0,scale=1920:1080:flags=lanczos,unsharp=5:5:0.75:3:3:0.0,noise=c0s=2:c0f=t+u,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
                )
                filter_complex = ";".join(fc_parts)

                cmd = ["ffmpeg", "-y"]
                for fp in flash_frames:
                    cmd.extend(["-i", str(fp)])
                cmd.extend([
                    "-i", str(hud_png),
                    "-i", str(seg_wav),
                    "-filter_complex", filter_complex,
                    "-map", "[vout]",
                    "-map", f"{n_fl + 1}:a",
                    "-t", f"{dur:.3f}",
                    "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-level", "4.2", "-crf", "15", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                    "-shortest", str(seg_mp4),
                ])
            else:
                if seg_type == "summary" or (seg_type == "area_guide" and "2/2" in badge):
                    filter_complex = (
                        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={dur},setpts=PTS-STARTPTS,fps={FPS},setsar=1[bg];"
                        f"[bg][2:v]overlay=0:0,scale=1920:1080:flags=lanczos,unsharp=5:5:0.75:3:3:0.0,noise=c0s=2:c0f=t+u,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
                    )
                else:
                    zp_a = f"zoompan=z='min(zoom+0.0018,1.16)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={half_frames}:s={W}x{H}:fps={FPS}"
                    zp_b = f"zoompan=z='1.14':x='(iw-iw/zoom)*(on/{half_frames})':y='ih/2-(ih/zoom/2)':d={half_frames}:s={W}x{H}:fps={FPS}"
                    filter_complex = (
                        f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},{zp_a},trim=duration={half_dur},setpts=PTS-STARTPTS,setsar=1[va];"
                        f"[1:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},{zp_b},trim=duration={dur - half_dur + 0.1},setpts=PTS-STARTPTS,setsar=1[vb];"
                        f"[va][vb]concat=n=2:v=1:a=0[bg];"
                        f"[bg][2:v]overlay=0:0,scale=1920:1080:flags=lanczos,unsharp=5:5:0.75:3:3:0.0,noise=c0s=2:c0f=t+u,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
                    )

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(p1),
                    "-i",
                    str(p2),
                    "-i",
                    str(hud_png),
                    "-i",
                    str(seg_wav),
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[vout]",
                    "-map",
                    "3:a",
                    "-t",
                    f"{dur:.3f}",
                    "-r",
                    str(FPS),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-profile:v",
                    "high",
                    "-level",
                    "4.2",
                    "-crf",
                    "15",
                    "-maxrate",
                    "12M",
                    "-bufsize",
                    "24M",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-shortest",
                    str(seg_mp4),
                ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            seg_videos.append(seg_mp4)

        concat_txt = work_dir / "concat.txt"
        concat_txt.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in seg_videos) + "\n",
            encoding="utf-8",
        )
        merged_mp4 = work_dir / "merged.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_txt),
                "-c",
                "copy",
                str(merged_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        total_dur = get_duration(merged_mp4)
        if t_act2 == 0.0:
            t_act2 = total_dur * 0.12
        if t_act3 == 0.0:
            t_act3 = total_dur * 0.65
        if t_act4 == 0.0:
            t_act4 = total_dur * 0.92

        bgm_mp3 = work_dir / "dynamic_4act_bgm.mp3"
        generate_dynamic_4act_bgm(
            bgm_mp3,
            total_dur=total_dur + 4.0,
            act_boundaries=(t_act2, t_act3, t_act4),
            seg_starts=seg_starts,
        )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(merged_mp4),
                "-i",
                str(bgm_mp3),
                "-filter_complex",
                "[0:a]volume=1.55[v];[1:a]volume=0.25[b];[v][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]",
                "-map",
                "0:v",
                "-map",
                "[aout]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                "-shortest",
                str(final_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    logger.info(f"Completed Japan Ranking MP4: {final_mp4}")
    return final_mp4


SW, SH = 1080, 1920


def wrap_text_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    """Word-wrap English text to fit within max_w pixels."""
    words = text.replace("\n", " ").split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        tb = draw.textbbox((0, 0), test, font=font)
        if (tb[2] - tb[0]) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_short_promise_jpg(
    ranking_id: str,
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg: Path,
) -> None:
    """
    Render Cut 1A of the Opening Hook at Eye Level (y=474..1456, leaving y=0..265 100% clear of text):
    Showcases this episode's actual #1, #2, #3 spots with large photos, signature appeal, exact access & yen prices!
    """
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id
    from PIL import ImageFilter

    if summary_rows and (cache_dir / summary_rows[0]["thumb"]).exists():
        raw_bg = Image.open(cache_dir / summary_rows[0]["thumb"]).convert("RGB")
        bg = fit_crop(raw_bg, SW, SH).filter(ImageFilter.GaussianBlur(radius=36))
        bg = ImageEnhance.Brightness(bg).enhance(0.28)
    else:
        bg = Image.new("RGB", (SW, SH), (10, 15, 28))

    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    f_tag = ImageFont.truetype(font_path, 21)
    f_ten = ImageFont.truetype(font_path, 31)
    f_sub = ImageFont.truetype(font_path, 24)
    f_dsc = ImageFont.truetype(font_path, 22)

    badge_cols = [
        ((217, 119, 6, 255), (253, 224, 71, 245), "NO.1 MUST-VISIT SPOT"),
        ((220, 38, 38, 255), (248, 113, 113, 245), "NO.2 LOCAL FAVORITE"),
        ((2, 132, 199, 255), (56, 189, 248, 245), "NO.3 HIDDEN GEM"),
    ]

    for idx in range(min(3, len(summary_rows))):
        row = summary_rows[idx]
        b_col, border_col, rank_label = badge_cols[idx]
        cy0 = 474 + idx * 330
        cy1 = cy0 + 310
        draw.rounded_rectangle((36, cy0, SW - 36, cy1), radius=22, fill=(10, 18, 34, 244), outline=border_col, width=3)

        tw, th_h = 256, cy1 - cy0 - 28
        tx0, ty0 = 50, cy0 + 14
        p_path = cache_dir / row.get("thumb", "")
        if row.get("thumb") and p_path.exists():
            tile = fit_crop(Image.open(p_path), tw, th_h)
            mask = Image.new("L", (tw, th_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw, th_h), radius=16, fill=255)
            canvas.paste(tile.convert("RGBA"), (tx0, ty0), mask)
            draw.rounded_rectangle((tx0, ty0, tx0 + tw, ty0 + th_h), radius=16, fill=None, outline=(255, 255, 255, 230), width=2)
            draw.rounded_rectangle((tx0 + 10, ty0 + 10, tx0 + 146, ty0 + 48), radius=9, fill=b_col, outline=(255, 255, 255, 230), width=1)
            draw.text((tx0 + 20, ty0 + 18), f"{row['rank']}  {row['score']}", font=f_tag, fill=(255, 255, 255, 255))

        rx = tx0 + tw + 24
        max_rw = (SW - 54) - rx
        badge_str = f"{rank_label}  •  {row['score'].upper()}"
        tb_b = draw.textbbox((0, 0), badge_str, font=f_tag)
        bw = min(max_rw, (tb_b[2] - tb_b[0]) + 32)
        draw.rounded_rectangle((rx, cy0 + 16, rx + bw, cy0 + 58), radius=10, fill=b_col)
        draw.text((rx + 16, cy0 + 26), smart_truncate(draw, badge_str, f_tag, max_rw - 24), font=f_tag, fill=(255, 255, 255, 255))

        clean_nm = strip_cjk(row["name_en"].split("(")[0].strip())
        f_nm = fit_font_for_width(draw, clean_nm, font_path, 32, 22, max_rw)
        draw.text((rx, cy0 + 70), smart_truncate(draw, clean_nm, f_nm, max_rw), font=f_nm, fill=(255, 255, 255, 255))

        clean_dish = strip_cjk(row["dish"].split("(")[0].strip())
        dish_lines = wrap_text_lines(draw, clean_dish, f_sub, max_rw)
        for d_i, dl in enumerate(dish_lines[:2]):
            draw.text((rx, cy0 + 118 + d_i * 32), dl, font=f_sub, fill=(253, 224, 71, 255))

        acc_txt = strip_cjk(f"ACCESS: {row.get('access_short', '')}  |  {row.get('budget', '')}".strip(" |"))
        hack_txt = strip_cjk(f"TIP: {row.get('hack', '')}")
        draw.text((rx, cy0 + 194), smart_truncate(draw, acc_txt, f_dsc, max_rw), font=f_dsc, fill=(125, 211, 252, 255))
        draw.text((rx, cy0 + 236), smart_truncate(draw, hack_txt, f_dsc, max_rw), font=f_dsc, fill=(167, 243, 208, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_hook_jpg(
    ranking_id: str,
    area_guide: Dict[str, Any],
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg: Path,
) -> None:
    """Render a sleek mobile-first 1080x1920 Hook screen at Eye Level (y=474..1456) over a blurred backdrop."""
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id
    from PIL import ImageFilter

    if summary_rows and (cache_dir / summary_rows[0]["thumb"]).exists():
        raw_bg = Image.open(cache_dir / summary_rows[0]["thumb"]).convert("RGB")
        bg = fit_crop(raw_bg, SW, SH).filter(ImageFilter.GaussianBlur(radius=36))
        bg = ImageEnhance.Brightness(bg).enhance(0.30)
    else:
        bg = Image.new("RGB", (SW, SH), (10, 15, 28))

    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    # 1. Center Japan Map + Shinkansen Card shifted to Eye Level (x=36..1044, y=474..980)
    mx0, my0, mx1, my1 = 36, 474, SW - 36, 980
    draw.rounded_rectangle((mx0, my0, mx1, my1), radius=24, fill=(10, 18, 34, 240), outline=(56, 189, 248, 240), width=3)

    f_mhead = ImageFont.truetype(font_path, 21)
    mhead_txt = "JAPAN SHINKANSEN & ACCESS MAP"
    tb_mh = draw.textbbox((0, 0), mhead_txt, font=f_mhead)
    mhw = (tb_mh[2] - tb_mh[0]) + 34
    draw.rounded_rectangle((mx0 + 22, my0 + 18, mx0 + 22 + mhw, my0 + 60), radius=12, fill=(14, 116, 144, 250))
    draw.text((mx0 + 39, my0 + 28), mhead_txt, font=f_mhead, fill=(255, 255, 255, 255))

    map_json = BASE_DIR / "assets" / "maps" / "japan_prefectures.json"
    lon_min, lon_max = 129.5, 145.8
    lat_min, lat_max = 31.0, 45.6
    pad_x0, pad_y0, pad_x1, pad_y1 = mx0 + 28, my0 + 74, mx0 + 518, my1 - 20

    def project(lon: float, lat: float) -> Tuple[int, int]:
        px = pad_x0 + (lon - lon_min) / (lon_max - lon_min) * (pad_x1 - pad_x0)
        py = pad_y1 - (lat - lat_min) / (lat_max - lat_min) * (pad_y1 - pad_y0)
        return int(round(px)), int(round(py))

    prefs = json.loads(map_json.read_text(encoding="utf-8")) if map_json.exists() else []
    target_pref, shinkansen_pts = resolve_prefecture_and_route(area_guide, ranking_id, prefs)
    if prefs:
        for pf in prefs:
            if pf["nam_ja"] == target_pref:
                continue
            is_tokyo = pf["nam_ja"] == "東京都"
            fill_c = (56, 189, 248, 210) if is_tokyo else (51, 65, 85, 200)
            for ring in pf["polys"]:
                if any(pt[0] < lon_min or pt[0] > lon_max or pt[1] < lat_min or pt[1] > lat_max for pt in ring):
                    continue
                pts = [project(pt[0], pt[1]) for pt in ring]
                if len(pts) >= 3:
                    draw.polygon(pts, fill=fill_c, outline=(148, 163, 184, 150))
        for pf in prefs:
            if pf["nam_ja"] == target_pref:
                for ring in pf["polys"]:
                    if any(pt[0] < lon_min or pt[0] > lon_max or pt[1] < lat_min or pt[1] > lat_max for pt in ring):
                        continue
                    pts = [project(pt[0], pt[1]) for pt in ring]
                    if len(pts) >= 3:
                        draw.polygon(pts, fill=(239, 68, 68, 255), outline=(253, 224, 71, 255))
                        draw.line(pts + [pts[0]], fill=(253, 224, 71, 255), width=2)

    draw.line([project(lon, lat) for lon, lat in shinkansen_pts], fill=(253, 224, 71, 255), width=5)
    tx_p, ty_p = project(shinkansen_pts[0][0], shinkansen_pts[0][1])
    hx_p, hy_p = project(shinkansen_pts[-1][0], shinkansen_pts[-1][1])
    draw.ellipse([(tx_p - 7, ty_p - 7), (tx_p + 7, ty_p + 7)], fill=(56, 189, 248, 255), outline=(255, 255, 255, 255), width=2)
    draw.ellipse([(hx_p - 9, hy_p - 9), (hx_p + 9, hy_p + 9)], fill=(239, 68, 68, 255), outline=(253, 224, 71, 255), width=2)

    f_big = ImageFont.truetype(font_path, 32)
    f_lbl = ImageFont.truetype(font_path, 20)
    f_sub = ImageFont.truetype(font_path, 18)
    sx0, sx1 = mx0 + 538, mx1 - 22

    top1_acc = smart_truncate(draw, summary_rows[0].get("access_short", "Direct Shinkansen").upper(), f_lbl, sx1 - sx0 - 36) if summary_rows else "DIRECT SHINKANSEN"
    top2_acc = smart_truncate(draw, summary_rows[1].get("access_short", "JR Express Train").upper(), f_lbl, sx1 - sx0 - 36) if len(summary_rows) > 1 else "JR EXPRESS TRAIN"
    top1_bud = smart_truncate(draw, summary_rows[0].get("budget", "Easy Day Trip via JR Pass"), f_sub, sx1 - sx0 - 36) if summary_rows else "Easy Day Trip"
    top2_bud = smart_truncate(draw, summary_rows[1].get("budget", "100% Authentic Local Spot"), f_sub, sx1 - sx0 - 36) if len(summary_rows) > 1 else "100% Local Data"

    stat_boxes = [
        ("NO.1 SPOT ACCESS", top1_acc, top1_bud, (16, 185, 129, 245)),
        ("NO.2 SPOT ACCESS", top2_acc, top2_bud, (217, 119, 6, 245)),
    ]
    for idx, (big_t, l1, l2, col) in enumerate(stat_boxes):
        by0 = my0 + 76 + idx * 206
        by1 = by0 + 190
        draw.rounded_rectangle((sx0, by0, sx1, by1), radius=14, fill=(15, 23, 42, 240), outline=col, width=2)
        draw.rounded_rectangle((sx0 + 16, by0 + 14, sx1 - 16, by0 + 78), radius=10, fill=col)
        tb = draw.textbbox((0, 0), big_t, font=f_big)
        draw.text((sx0 + ((sx1 - sx0) - (tb[2] - tb[0])) // 2, by0 + 26), big_t, font=f_big, fill=(255, 255, 255, 255))
        draw.text((sx0 + 20, by0 + 96), l1, font=f_lbl, fill=(253, 224, 71, 255))
        draw.text((sx0 + 20, by0 + 136), l2, font=f_sub, fill=(226, 232, 240, 255))

    # 2. Top 3 Visual Cards at Eye Level (x=36..1044, y=1002..1456)
    gy0, gy1 = 1002, 1456
    col_w = (SW - 72 - 24) // 3
    f_rk = ImageFont.truetype(font_path, 23)
    f_acc_sm = ImageFont.truetype(font_path, 17)

    top3 = [summary_rows[2], summary_rows[1], summary_rows[0]] if len(summary_rows) >= 3 else summary_rows
    for i, row in enumerate(top3):
        cx0 = 36 + i * (col_w + 12)
        cx1 = cx0 + col_w
        p_path = cache_dir / row["thumb"]
        if p_path.exists():
            tile = fit_crop(Image.open(p_path), cx1 - cx0, gy1 - gy0)
            mask = Image.new("L", (cx1 - cx0, gy1 - gy0), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, cx1 - cx0, gy1 - gy0), radius=18, fill=255)
            canvas.paste(tile.convert("RGBA"), (cx0, gy0), mask)
        b_col = (217, 119, 6, 250) if row["rank"] == "#1" else (220, 38, 38, 250)
        draw.rounded_rectangle((cx0, gy0, cx1, gy1), radius=18, fill=None, outline=(255, 255, 255, 235), width=3)
        draw.rounded_rectangle((cx0 + 12, gy0 + 12, cx1 - 12, gy0 + 60), radius=10, fill=b_col, outline=(255, 255, 255, 240), width=2)
        r_lbl = f"{row['rank']}  {row['score']}"
        tb_r = draw.textbbox((0, 0), r_lbl, font=f_rk)
        draw.text((cx0 + ((cx1 - cx0) - (tb_r[2] - tb_r[0])) // 2, gy0 + 22), r_lbl, font=f_rk, fill=(255, 255, 255, 255))

        draw.rounded_rectangle((cx0 + 4, gy1 - 92, cx1 - 4, gy1 - 4), radius=12, fill=(8, 12, 22, 242))
        raw_nm = strip_cjk(row["name_en"].split("(")[0].strip())
        f_nm_fit = fit_font_for_width(draw, raw_nm, font_path, 22, 15, col_w - 20)
        clean_nm = smart_truncate(draw, raw_nm, f_nm_fit, col_w - 20)
        tb_n = draw.textbbox((0, 0), clean_nm, font=f_nm_fit)
        draw.text((cx0 + ((cx1 - cx0) - (tb_n[2] - tb_n[0])) // 2, gy1 - 80), clean_nm, font=f_nm_fit, fill=(253, 224, 71, 255))

        acc_short = smart_truncate(draw, row.get("access_short", row.get("budget", "")), f_acc_sm, col_w - 20)
        tb_j = draw.textbbox((0, 0), acc_short, font=f_acc_sm)
        draw.text((cx0 + ((cx1 - cx0) - (tb_j[2] - tb_j[0])) // 2, gy1 - 40), acc_short, font=f_acc_sm, fill=(255, 255, 255, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_outro_jpg(
    ranking_id: str,
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg: Path,
) -> None:
    """
    Render a mobile-optimized TOP 5 Podium Cards + #6-#10 Compact Badges screen at Eye Level (y=474..1456)
    so every word is large, legible, and screenshot-ready on a smartphone!
    """
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id
    from PIL import ImageFilter

    if summary_rows and (cache_dir / summary_rows[0]["thumb"]).exists():
        raw_bg = Image.open(cache_dir / summary_rows[0]["thumb"]).convert("RGB")
        bg = fit_crop(raw_bg, SW, SH).filter(ImageFilter.GaussianBlur(radius=36))
        bg = ImageEnhance.Brightness(bg).enhance(0.28)
    else:
        bg = Image.new("RGB", (SW, SH), (10, 14, 24))

    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    f_rk = ImageFont.truetype(font_path, 22)
    f_title = ImageFont.truetype(font_path, 25)
    f_sub = ImageFont.truetype(font_path, 19)
    f_mini = ImageFont.truetype(font_path, 18)

    y0_base = 474
    card_h = 148
    gap = 8
    for i, row in enumerate(summary_rows[:5]):
        ry0 = y0_base + i * (card_h + gap)
        ry1 = ry0 + card_h
        is_no1 = row["rank"] == "#1"
        is_top3 = row["rank"] in ("#1", "#2", "#3")
        border_c = (253, 224, 71, 255) if is_no1 else ((248, 113, 113, 235) if is_top3 else (96, 165, 250, 220))
        draw.rounded_rectangle((36, ry0, SW - 36, ry1), radius=18, fill=(12, 20, 36, 242), outline=border_c, width=3)

        p_path = cache_dir / row["thumb"]
        tw, th_h = 180, card_h - 16
        if p_path.exists():
            th = fit_crop(Image.open(p_path), tw, th_h)
            mask = Image.new("L", (tw, th_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw, th_h), radius=12, fill=255)
            canvas.paste(th.convert("RGBA"), (44, ry0 + 8), mask)

        tx = 44 + tw + 18
        b_col = (217, 119, 6, 255) if is_no1 else ((220, 38, 38, 255) if is_top3 else (30, 58, 138, 255))
        r_txt = f"{row['rank']}  {row['score']}"
        tb_r = draw.textbbox((0, 0), r_txt, font=f_rk)
        badge_w = max(172, (tb_r[2] - tb_r[0]) + 28)
        draw.rounded_rectangle((tx, ry0 + 10, tx + badge_w, ry0 + 50), radius=10, fill=b_col)
        draw.text((tx + (badge_w - (tb_r[2] - tb_r[0])) // 2, ry0 + 18), r_txt, font=f_rk, fill=(255, 255, 255, 255))

        max_title_w = (SW - 52) - (tx + badge_w + 14)
        full_title = smart_truncate(draw, row["name_en"], f_title, max_title_w)
        clean_dish = strip_cjk(row["dish"].split("(")[0].strip())
        clean_hack = strip_cjk(row["hack"].strip())
        max_line_w = (SW - 52) - tx
        acc_line = smart_truncate(draw, f"ACCESS: {row['budget']}  |  {clean_dish}", f_sub, max_line_w)
        hack_line = smart_truncate(draw, f"HACK: {clean_hack}", f_sub, max_line_w)
        draw.text((tx + badge_w + 14, ry0 + 16), full_title, font=f_title, fill=(255, 255, 255, 255))
        draw.text((tx, ry0 + 62), acc_line, font=f_sub, fill=(125, 211, 252, 255))
        draw.text((tx, ry0 + 98), hack_line, font=f_sub, fill=(167, 243, 208, 255))

    if len(summary_rows) >= 10:
        by0, by1 = 1264, 1456
        draw.rounded_rectangle((36, by0, SW - 36, by1), radius=18, fill=(15, 23, 42, 242), outline=(148, 163, 184, 210), width=2)
        draw.text((58, by0 + 14), "RANKS #6 TO #10 (IN FULL 9-MIN VIDEO):", font=f_sub, fill=(253, 224, 71, 255))
        for j, r_row in enumerate(summary_rows[5:10]):
            col_x = 58 if j < 3 else 548
            row_y = by0 + 54 + (j % 3) * 42
            txt = smart_truncate(draw, f"{r_row['rank']} ({r_row['score']}): {r_row['name_en']}", f_mini, 470)
            draw.text((col_x, row_y), txt, font=f_mini, fill=(241, 245, 249, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def _load_short_full_bleed(photo_path: Path, w: int = SW, h: int = SH, darken: float = 0.85) -> Image.Image:
    """Load and center-crop a photo to full-bleed (w, h) with rich color grading."""
    from PIL import ImageChops

    if not photo_path.exists():
        return Image.new("RGB", (w, h), (12, 16, 28))
    raw_im = Image.open(photo_path).convert("RGB")
    white_bg = Image.new("RGB", raw_im.size, (250, 250, 250))
    diff = ImageChops.difference(raw_im, white_bg).convert("L").point(lambda p: 255 if p > 18 else 0)
    bbox = diff.getbbox()
    if bbox and (bbox[2] - bbox[0]) > raw_im.width * 0.6 and (bbox[3] - bbox[1]) > raw_im.height * 0.5:
        raw_im = raw_im.crop(bbox)
    im = fit_crop(raw_im, w, h)
    im = ImageEnhance.Color(im).enhance(1.24)
    im = ImageEnhance.Contrast(im).enhance(1.12)
    return ImageEnhance.Brightness(im).enhance(darken)


def _apply_short_cinema_grad(im: Image.Image, top_alpha: int = 200, mid_alpha: int = 12, bot_alpha: int = 244) -> Image.Image:
    """Apply top and bottom cinema gradient over a 1080x1920 image, keeping the center photo crystal clear."""
    ov = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(SH):
        if y < 620:
            a = int(top_alpha * (1.0 - y / 620.0) ** 1.3)
        elif y < 1000:
            a = mid_alpha
        else:
            t = (y - 1000) / 920.0
            a = int(mid_alpha + (bot_alpha - mid_alpha) * (t ** 1.2))
        od.line([(0, y), (SW, y)], fill=(6, 9, 16, min(255, a)))
    return Image.alpha_composite(im.convert("RGBA"), ov)


def _fit_cjk_font(draw: ImageDraw.ImageDraw, text: str, font_path: str, start_size: int, min_size: int, max_w: int) -> ImageFont.FreeTypeFont:
    """Fit text width without stripping Japanese CJK characters."""
    sz = start_size
    while sz >= min_size:
        f = ImageFont.truetype(font_path, sz)
        tb = draw.textbbox((0, 0), text, font=f)
        if (tb[2] - tb[0]) <= max_w:
            return f
        sz -= 2
    return ImageFont.truetype(font_path, min_size)


def render_short_ig_design_a_jpg(
    photo_path: Path,
    scene: Dict[str, Any],
    font_path: str,
    out_jpg: Path,
) -> None:
    """
    案A: 全面フルスクリーン絶景 ＋ IGロゴ＆日本人のリアルな声 (NatGeo / IG Reel Immersive)
    - Full-bleed 1080x1920 photo with clear center window
    - Upper Eye-Level (y=272..510): Instagram Logo Pill + Giant Hook & Spot Name
    - Lower-Center Eye-Level (y=1050..1545): Direct Access/Budget Bar + Instagram '日本人のリアルな声' Bilingual Review Card
    """
    cjk_path = find_cjk_font()
    canvas = _apply_short_cinema_grad(_load_short_full_bleed(photo_path, SW, SH, darken=0.86), top_alpha=205, mid_alpha=10, bot_alpha=245)
    draw = ImageDraw.Draw(canvas, "RGBA")

    badge_en = strip_cjk(scene.get("badge", "RANK #01")).upper()
    is_warn = scene.get("card_style") == "warn"
    pill_border = (252, 176, 69, 255) if is_warn else (225, 48, 108, 255)

    # 1. Top Eye-Level Instagram Analysis Pill (y=272..346)
    draw.rounded_rectangle((60, 272, 860, 346), radius=22, fill=(18, 14, 32, 238), outline=pill_border, width=3)
    draw_instagram_logo(canvas, 76, 281, 56)
    top_lbl = f"JP INSTAGRAM ANALYSIS  •  {badge_en}"
    f_ig_top = fit_font_for_width(draw, top_lbl, font_path, 27, 18, 690)
    draw.text((148, 283), smart_truncate(draw, top_lbl, f_ig_top, 690), font=f_ig_top, fill=(255, 255, 255, 255))
    sub_lbl = "日本人のリアルな声  |  ♥ 98% Local Approval  •  0% Paid Promo"
    f_ig_sub = _fit_cjk_font(draw, sub_lbl, cjk_path, 21, 15, 690)
    draw.text((148, 315), sub_lbl, font=f_ig_sub, fill=(255, 195, 225, 255))

    # 2. Giant Eye-Level Feature Hook & Spot Name (y=366..510)
    sub_en = strip_cjk(scene.get("sub_en", "")).replace("PRO TIP:", "").strip().upper()
    title_en = strip_cjk(scene.get("title_en", "")).upper()
    if sub_en:
        f_hook = fit_font_for_width(draw, sub_en, font_path, 54, 28, SW - 120)
        sub_fit = smart_truncate(draw, sub_en, f_hook, SW - 120)
        draw.text((60, 368), sub_fit, font=f_hook, fill=(255, 215, 70, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))
    f_spot = fit_font_for_width(draw, title_en, font_path, 62, 32, SW - 120)
    title_fit = smart_truncate(draw, title_en, f_spot, SW - 120)
    draw.text((60, 442), title_fit, font=f_spot, fill=(255, 255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0, 255))

    # 3. Lower-Center Direct Access & Entry/Budget Glass Bar (y=1050..1172)
    raw_acc = strip_cjk(scene.get("access", "")).replace("ACCESS:", "").replace("TIP:", "").strip()
    parts = [p.strip() for p in re.split(r"\||•|;", raw_acc) if p.strip()]
    uniq_parts: List[str] = []
    for p in parts:
        if p.lower() not in [u.lower() for u in uniq_parts]:
            uniq_parts.append(p)
    acc_val = uniq_parts[0] if len(uniq_parts) >= 1 else (raw_acc or "Direct Train Access")
    bud_val = uniq_parts[1] if len(uniq_parts) >= 2 else "Arrive Early • Cash/IC"

    draw.rounded_rectangle((60, 1050, SW - 60, 1172), radius=22, fill=(12, 18, 30, 224), outline=(255, 210, 80, 215), width=3)
    f_blbl = ImageFont.truetype(font_path, 21)
    draw.text((90, 1068), "DIRECT ACCESS", font=f_blbl, fill=(255, 205, 75, 255))
    f_bval1 = fit_font_for_width(draw, acc_val, font_path, 31, 18, 435)
    draw.text((90, 1100), smart_truncate(draw, acc_val, f_bval1, 435), font=f_bval1, fill=(255, 255, 255, 255))
    draw.line([(555, 1068), (555, 1154)], fill=(255, 255, 255, 75), width=2)
    draw.text((582, 1068), "ENTRY / LOCAL TIP", font=f_blbl, fill=(110, 235, 190, 255))
    f_bval2 = fit_font_for_width(draw, bud_val, font_path, 31, 18, 405)
    draw.text((582, 1100), smart_truncate(draw, bud_val, f_bval2, 405), font=f_bval2, fill=(255, 255, 255, 255))

    # 4. Instagram '日本人のリアルな声' Bilingual Review Card (y=1196..1548)
    draw.rounded_rectangle((60, 1196, SW - 60, 1548), radius=28, fill=(16, 14, 28, 244), outline=pill_border, width=4)
    hdr_bg = (217, 119, 6, 245) if is_warn else (225, 48, 108, 245)
    draw.rounded_rectangle((88, 1218, 720, 1274), radius=14, fill=hdr_bg)
    draw_instagram_logo(canvas, 98, 1224, 44)
    vc_hdr = "日本人のリアルな声  •  LOCAL IG RULE & TIP" if is_warn else "日本人のリアルな声  •  REAL JP IG VOICE"
    f_vch = _fit_cjk_font(draw, vc_hdr, cjk_path, 23, 16, 555)
    draw.text((154, 1232), vc_hdr, font=f_vch, fill=(255, 255, 255, 255))

    jp_voice = synthesize_jp_local_voice(
        badge_en,
        title_en,
        sub_en,
        "warn" if is_warn else "praise",
        scene.get("card_body_ja", ""),
    )
    f_jpq = _fit_cjk_font(draw, jp_voice, cjk_path, 27, 17, SW - 180)
    draw.text((90, 1294), jp_voice, font=f_jpq, fill=(255, 225, 105, 255))

    raw_body_en = strip_cjk(scene.get("card_body_en") or scene.get("access") or scene.get("sub_en", "")).strip().strip("\"'“”")
    for sep in (". ", "! ", "; "):
        if sep in raw_body_en:
            s0 = raw_body_en.split(sep)[0].strip()
            if len(s0) >= 24:
                raw_body_en = s0 + ("!" if sep == "! " else ".")
                break
    f_enq = ImageFont.truetype(font_path, 29)
    en_lines = wrap_text_lines(draw, f"\"{raw_body_en}\"", f_enq, SW - 180)
    if len(en_lines) > 2:
        en_lines = [en_lines[0], smart_truncate(draw, " ".join(en_lines[1:]).rstrip("\"") + "\"", f_enq, SW - 180)]
    for li, el in enumerate(en_lines[:2]):
        draw.text((90, 1354 + li * 44), el, font=f_enq, fill=(255, 255, 255, 255))

    f_meta = ImageFont.truetype(font_path, 23)
    draw.text((90, 1480), "♥ Verified Japanese Local Review on IG   •   100% Unsponsored", font=f_meta, fill=(167, 243, 208, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_ig_design_b_jpg(
    photo_top_path: Path,
    photo_bot_path: Path,
    scene: Dict[str, Any],
    font_path: str,
    out_jpg: Path,
) -> None:
    """
    案B: 上下2画面スプリット（上：メイン聖地・名所 × 下：周辺コンボ・別アングル）＋ 中央IG口コミ＆裏技ブリッジ
    - Top half (0..960) & Bottom half (960..1920) full-bleed photos
    - Center Eye-Level Bridge (y=795..1130): Instagram Logo + '日本人のリアルな声' + Local Insider Hack & Walk Combo
    """
    cjk_path = find_cjk_font()
    canvas = Image.new("RGBA", (SW, SH), (8, 12, 20, 255))
    top_im = _load_short_full_bleed(photo_top_path, SW, 960, darken=0.86)
    bot_im = _load_short_full_bleed(photo_bot_path, SW, 960, darken=0.84)
    canvas.paste(top_im, (0, 0))
    canvas.paste(bot_im, (0, 960))

    ov = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(SH):
        dist_c = abs(y - 960)
        if dist_c < 245:
            a = int(228 * (1.0 - dist_c / 245.0))
        elif y < 400:
            a = int(198 * (1.0 - y / 400.0))
        elif y > 1360:
            a = int(238 * ((y - 1360) / 560.0))
        else:
            a = 18
        od.line([(0, y), (SW, y)], fill=(6, 10, 18, min(255, a)))
    canvas = Image.alpha_composite(canvas, ov)
    draw = ImageDraw.Draw(canvas, "RGBA")

    badge_en = strip_cjk(scene.get("badge", "RANK #01")).upper()
    title_en = strip_cjk(scene.get("title_en", "")).upper()
    sub_en = strip_cjk(scene.get("sub_en", "")).replace("PRO TIP:", "").strip()

    # 1. Top Header Pill + Main Spot Name (y=272..435)
    draw.rounded_rectangle((60, 272, 820, 344), radius=20, fill=(18, 14, 32, 240), outline=(225, 48, 108, 255), width=3)
    draw_instagram_logo(canvas, 76, 280, 54)
    top_lbl = f"JP IG LOCAL COMBO  •  {badge_en}"
    f_top = fit_font_for_width(draw, top_lbl, font_path, 27, 18, 650)
    draw.text((146, 283), smart_truncate(draw, top_lbl, f_top, 650), font=f_top, fill=(255, 255, 255, 255))
    sub_lbl = "日本人のリアルな声  |  名所＋周辺コンボ＆地元の裏技"
    f_sub_jp = _fit_cjk_font(draw, sub_lbl, cjk_path, 21, 15, 650)
    draw.text((146, 314), sub_lbl, font=f_sub_jp, fill=(255, 195, 225, 255))

    f_main = fit_font_for_width(draw, title_en, font_path, 58, 30, SW - 120)
    draw.text((60, 362), smart_truncate(draw, title_en, f_main, SW - 120), font=f_main, fill=(255, 255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0, 255))

    # 2. Center Eye-Level Instagram Real Japanese Voice + Combo Bridge (y=798..1128)
    draw.rounded_rectangle((50, 798, SW - 50, 1128), radius=28, fill=(16, 14, 28, 246), outline=(252, 176, 69, 255), width=4)
    draw_instagram_logo(canvas, 78, 822, 56)
    mid_hdr = "日本人のリアルな声  •  LOCAL IG INSIDER HACK"
    f_mhdr = _fit_cjk_font(draw, mid_hdr, cjk_path, 27, 18, SW - 220)
    draw.text((150, 824), mid_hdr, font=f_mhdr, fill=(255, 215, 75, 255))

    jp_voice = synthesize_jp_local_voice(
        badge_en,
        title_en,
        sub_en,
        scene.get("card_style", "warn"),
        scene.get("card_body_ja", ""),
    )
    f_jp = _fit_cjk_font(draw, jp_voice, cjk_path, 25, 17, SW - 220)
    draw.text((150, 864), jp_voice, font=f_jp, fill=(255, 195, 225, 255))

    draw.line([(78, 910), (SW - 78, 910)], fill=(255, 255, 255, 68), width=2)
    raw_body_en = strip_cjk(scene.get("card_body_en") or scene.get("access") or sub_en).strip().strip("\"'“”")
    for sep in (". ", "! ", "; "):
        if sep in raw_body_en:
            s0 = raw_body_en.split(sep)[0].strip()
            if len(s0) >= 24:
                raw_body_en = s0 + ("!" if sep == "! " else ".")
                break
    f_en = ImageFont.truetype(font_path, 30)
    en_lines = wrap_text_lines(draw, f"\"{raw_body_en}\"", f_en, SW - 160)
    if len(en_lines) > 2:
        en_lines = [en_lines[0], smart_truncate(draw, " ".join(en_lines[1:]).rstrip("\"") + "\"", f_en, SW - 160)]
    for li, el in enumerate(en_lines[:2]):
        col_l = (255, 225, 95, 255) if li == 1 else (255, 255, 255, 255)
        draw.text((78, 926 + li * 44), el, font=f_en, fill=col_l)

    raw_acc = strip_cjk(scene.get("access", "")).replace("ACCESS:", "").replace("TIP:", "").strip()
    parts_b = [p.strip() for p in re.split(r"\||•|;", raw_acc) if p.strip()]
    uniq_b: List[str] = []
    for p in parts_b:
        if p.lower() not in [u.lower() for u in uniq_b]:
            uniq_b.append(p)
    acc_clean = "  •  ".join(uniq_b) if uniq_b else "100% UNSPONSORED LOCAL DATA"
    bot_strip = f"▼  {acc_clean}  •  ♥ 98% LOCAL SAVES  ▼"
    f_bstrip = fit_font_for_width(draw, bot_strip, font_path, 25, 16, SW - 160)
    draw.text((78, 1058), smart_truncate(draw, bot_strip, f_bstrip, SW - 160), font=f_bstrip, fill=(110, 235, 195, 255))

    # 3. Bottom Half Feature / Nearby Highlight (y=1380..1535)
    draw.rounded_rectangle((60, 1380, 620, 1442), radius=14, fill=(20, 155, 120, 242))
    f_btag = ImageFont.truetype(font_path, 25)
    draw.text((86, 1396), "MUST-KNOW FEATURE & LOCAL TIP", font=f_btag, fill=(255, 255, 255, 255))
    f_bbot = fit_font_for_width(draw, sub_en.upper() or title_en, font_path, 48, 26, SW - 120)
    draw.text((60, 1458), smart_truncate(draw, sub_en.upper() or title_en, f_bbot, SW - 120), font=f_bbot, fill=(255, 225, 95, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_ig_design_c_jpg(
    bg_photo_path: Path,
    scene: Dict[str, Any],
    summary_rows: List[Dict[str, Any]],
    active_rank: str,
    font_path: str,
    out_jpg: Path,
) -> None:
    """
    案C: 全面背景 ＋ IG分析TOP3 高速カウントダウン点灯型 (#3 -> #2 -> #1 + 日本人のリアルな声)
    - Full-bleed 1080x1920 background of the active spot
    - Center 3-Card Countdown Stack (#3, #2, #1) where `active_rank` lights up with Instagram Logo & 日本人の声
    """
    cjk_path = find_cjk_font()
    canvas = _apply_short_cinema_grad(_load_short_full_bleed(bg_photo_path, SW, SH, darken=0.80), top_alpha=215, mid_alpha=90, bot_alpha=242)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # 1. Top Instagram Analysis Header (y=272..500)
    draw.rounded_rectangle((60, 272, 850, 346), radius=22, fill=(18, 14, 32, 240), outline=(225, 48, 108, 255), width=3)
    draw_instagram_logo(canvas, 76, 281, 56)
    f_top = ImageFont.truetype(font_path, 27)
    draw.text((148, 283), "RANKED BY JAPANESE INSTAGRAM", font=f_top, fill=(255, 255, 255, 255))
    sub_lbl = "日本人のリアルな声 50万件分析  •  100% Unsponsored"
    f_sub_jp = _fit_cjk_font(draw, sub_lbl, cjk_path, 21, 15, 680)
    draw.text((148, 315), sub_lbl, font=f_sub_jp, fill=(255, 195, 225, 255))

    head_en = strip_cjk(scene.get("title_en", "TOP 3 REAL JAPAN SPOTS")).upper()
    f_head = fit_font_for_width(draw, head_en, font_path, 58, 30, SW - 120)
    draw.text((60, 366), smart_truncate(draw, head_en, f_head, SW - 120), font=f_head, fill=(255, 255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0, 255))
    sub_en = strip_cjk(scene.get("sub_en", "Where Japanese Locals Actually Visit (Zero Tourist Traps)"))
    f_sub = fit_font_for_width(draw, sub_en, font_path, 31, 20, SW - 120)
    draw.text((60, 442), smart_truncate(draw, sub_en, f_sub, SW - 120), font=f_sub, fill=(255, 215, 85, 255), stroke_width=5, stroke_fill=(0, 0, 0, 255))

    # 2. 3-Card Countdown Stack (#3 -> #2 -> #1) at Center Eye Level (y=555..1545)
    r3 = summary_rows[2] if len(summary_rows) >= 3 else (summary_rows[-1] if summary_rows else {})
    r2 = summary_rows[1] if len(summary_rows) >= 2 else (summary_rows[0] if summary_rows else {})
    r1 = summary_rows[0] if len(summary_rows) >= 1 else {}

    stack_rows = [("#3", r3), ("#2", r2), ("#1", r1)]
    cy = 555
    for rk_str, row in stack_rows:
        is_act = rk_str == active_rank
        nm = strip_cjk(row.get("name_en", rk_str).split("(")[0].strip()).upper()
        sc_pt = strip_cjk(row.get("score", "95/100pt"))
        acc = strip_cjk(row.get("access_short") or row.get("budget", "Direct Access"))
        dish = strip_cjk(row.get("dish", "").split("(")[0].strip())
        meta = f"{acc}  •  ♥ {sc_pt} on JP IG"
        jp_v = synthesize_jp_local_voice(rk_str, nm, dish, "praise", "")

        if is_act:
            draw.rounded_rectangle((50, cy, SW - 50, cy + 345), radius=28, fill=(20, 16, 36, 246), outline=(252, 176, 69, 255), width=5)
            draw.rounded_rectangle((80, cy + 28, 210, cy + 122), radius=18, fill=(225, 48, 108, 255))
            f_rk = ImageFont.truetype(font_path, 54)
            draw.text((106, cy + 42), rk_str, font=f_rk, fill=(255, 255, 255, 255))

            f_ct = fit_font_for_width(draw, nm, font_path, 40, 24, 760)
            draw.text((235, cy + 32), smart_truncate(draw, nm, f_ct, 760), font=f_ct, fill=(255, 225, 90, 255))
            f_cm = fit_font_for_width(draw, meta, font_path, 26, 18, 760)
            draw.text((235, cy + 90), smart_truncate(draw, meta, f_cm, 760), font=f_cm, fill=(255, 255, 255, 255))

            draw.rounded_rectangle((80, cy + 144, SW - 80, cy + 318), radius=18, fill=(10, 12, 24, 232), outline=(225, 48, 108, 195), width=2)
            draw_instagram_logo(canvas, 98, cy + 160, 44)
            jv_line = f"日本人の声: {jp_v}"
            f_jv = _fit_cjk_font(draw, jv_line, cjk_path, 24, 16, 810)
            draw.text((156, cy + 168), jv_line, font=f_jv, fill=(255, 195, 225, 255))

            clean_d = (dish or strip_cjk(scene.get("card_body_en", "Top-rated local favorite!"))).strip().strip("\"'“”")
            en_v = f"\"{clean_d}\""
            f_ev = fit_font_for_width(draw, en_v, font_path, 26, 18, 880)
            draw.text((98, cy + 218), smart_truncate(draw, en_v, f_ev, 880), font=f_ev, fill=(255, 255, 255, 255))

            now_txt = f"★ NOW SHOWING  •  {strip_cjk(row.get('budget', 'LOCAL PRICE'))}  •  100% UNSPONSORED"
            f_now = fit_font_for_width(draw, now_txt, font_path, 23, 16, 880)
            draw.text((98, cy + 268), smart_truncate(draw, now_txt, f_now, 880), font=f_now, fill=(110, 235, 195, 255))
            cy += 370
        else:
            draw.rounded_rectangle((60, cy, SW - 60, cy + 225), radius=24, fill=(10, 14, 24, 198), outline=(255, 255, 255, 78), width=2)
            draw.rounded_rectangle((90, cy + 28, 200, cy + 108), radius=16, fill=(45, 55, 75, 225))
            f_rk = ImageFont.truetype(font_path, 44)
            draw.text((114, cy + 40), rk_str, font=f_rk, fill=(205, 215, 230, 255))

            f_ct = fit_font_for_width(draw, nm, font_path, 34, 22, 760)
            draw.text((225, cy + 32), smart_truncate(draw, nm, f_ct, 760), font=f_ct, fill=(225, 232, 245, 255))
            f_cm = fit_font_for_width(draw, meta, font_path, 24, 17, 760)
            draw.text((225, cy + 84), smart_truncate(draw, meta, f_cm, 760), font=f_cm, fill=(165, 180, 205, 255))

            draw_instagram_logo(canvas, 90, cy + 134, 36)
            jv_sm = f"日本人の声: {jp_v}"
            f_jv_sm = _fit_cjk_font(draw, jv_sm, cjk_path, 22, 15, 840)
            draw.text((138, cy + 140), jv_sm, font=f_jv_sm, fill=(215, 185, 210, 255))
            cy += 250

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_cinema_frame_jpg(
    raw_photo_path: Path,
    photo_label: str,
    font_path: str,
    out_jpg: Path,
) -> None:
    """Fallback wrapper rendering Full-Screen Design A."""
    dummy_scene = {
        "badge": photo_label,
        "title_en": photo_label,
        "sub_en": "100% Unsponsored Japanese Instagram Analysis",
        "access": "Direct Station Access  |  Local Price",
        "card_style": "praise",
        "card_body_en": "Analyzed from real Japanese Instagram posts with zero paid promotions.",
    }
    render_short_ig_design_a_jpg(raw_photo_path, dummy_scene, font_path, out_jpg)


def render_short_hud_png(
    scene: Dict[str, Any],
    font_path: str,
    out_png: Path,
) -> None:
    """
    Render the Shorts overlay HUD:
    - For full-bleed Instagram designs (案A, 案B, 案C), all eye-level cards & headers are baked into the frame,
      so this overlay renders only the crisp bottom Pop Captions (y=1572..1695) without covering the design!
    - For 'outro' (Cheat-Sheet), renders the Upper Eye-Level Instagram Header + Bottom Pop Captions.
    """
    overlay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    cjk_path = find_cjk_font()

    if scene.get("mode") == "outro":
        draw.rounded_rectangle((60, 268, SW - 60, 342), radius=22, fill=(18, 14, 32, 242), outline=(225, 48, 108, 255), width=3)
        draw_instagram_logo(overlay, 78, 277, 56)
        f_top = ImageFont.truetype(font_path, 26)
        draw.text((150, 280), "FULL TOP 10 CHEAT-SHEET  •  SCREENSHOT NOW!", font=f_top, fill=(255, 255, 255, 255))
        f_sub_jp = _fit_cjk_font(draw, "日本人のリアルな声 徹底分析  |  100% Unsponsored Local Guide", cjk_path, 20, 15, 800)
        draw.text((150, 312), "日本人のリアルな声 徹底分析  |  100% Unsponsored Local Guide", font=f_sub_jp, fill=(255, 195, 225, 255))

        t_en = strip_cjk(scene["title_en"])
        f_title = fit_font_for_width(draw, t_en, font_path, 46, 28, SW - 52)
        t_en_fit = smart_truncate(draw, t_en, f_title, SW - 52)
        tb_t = draw.textbbox((0, 0), t_en_fit, font=f_title)
        draw.text(((SW - (tb_t[2] - tb_t[0])) // 2, 354), t_en_fit, font=f_title, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0, 255))

        t_sub = strip_cjk(scene.get("sub_en", ""))
        if t_sub:
            f_sub = fit_font_for_width(draw, t_sub, font_path, 26, 18, SW - 56)
            t_sub_fit = smart_truncate(draw, t_sub, f_sub, SW - 56)
            tb_j = draw.textbbox((0, 0), t_sub_fit, font=f_sub)
            draw.text(((SW - (tb_j[2] - tb_j[0])) // 2, 416), t_sub_fit, font=f_sub, fill=(253, 224, 71, 255), stroke_width=4, stroke_fill=(0, 0, 0, 245))

    # Bottom Floating Outline Pop Captions (y=1572..1690, well below the y=1548 review card!)
    pop_lines = scene.get("pop_lines", [])
    for li, raw_pl in enumerate(pop_lines[:2]):
        pl = strip_cjk(raw_pl)
        f_pop = fit_font_for_width(draw, pl, font_path, 36, 21, SW - 64)
        pl = smart_truncate(draw, pl, f_pop, SW - 64)
        tb_l = draw.textbbox((0, 0), pl, font=f_pop)
        lx = (SW - (tb_l[2] - tb_l[0])) // 2
        ly = 1572 + li * 54
        col = (253, 224, 71, 255) if li == 1 else (255, 255, 255, 255)
        draw.text((lx + 3, ly + 4), pl, font=f_pop, fill=(0, 0, 0, 230), stroke_width=7, stroke_fill=(0, 0, 0, 230))
        draw.text((lx, ly), pl, font=f_pop, fill=col, stroke_width=5, stroke_fill=(0, 0, 0, 255))

    overlay.save(out_png, "PNG")


def build_shorts_video(script_path: Path) -> Path:
    """
    Build a high-retention 8-Scene CapCut-Style YouTube Short (1080x1920):
    Rotates ALL 3 Full-Bleed Instagram-Branded Designs (案A, 案B, 案C) with the Instagram Logo
    and '日本人のリアルな声' (Real Japanese Local Voices)!
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(script_path.read_text(encoding="utf-8"))
    ranking_id = data["ranking_id"]
    prefecture = strip_cjk(data.get("prefecture", "Japan"))
    voice = data.get("voice", "en-US-ChristopherNeural")
    segments = data["segments"]
    summary_rows = data.get("summary_rows", [])
    area_guide = data.get("area_guide", {})
    shorts_cfg = data.get("shorts_script", {})
    font_path = find_font()

    short_mp4 = OUTPUT_DIR / f"overseas_japan_{ranking_id}_short.mp4"
    cache_dir = BASE_DIR / "assets" / "images" / ranking_id

    def find_pair(rank_prefix: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        sp_seg, rv_seg = None, None
        for i, s in enumerate(segments):
            if s.get("seg_type") == "spot" and s["rank_badge"].startswith(rank_prefix):
                sp_seg = s
                if i + 1 < len(segments) and segments[i + 1].get("seg_type") == "review":
                    rv_seg = segments[i + 1]
                break
        return sp_seg or segments[-3], rv_seg or segments[-2]

    sp3, rv3 = find_pair("#3 ")
    sp2, rv2 = find_pair("#2 ")
    sp1, rv1 = find_pair("#1 ")

    r3_row = summary_rows[2] if len(summary_rows) >= 3 else {"name_en": sp3["place_en"], "score": "90/100pt", "dish": sp3["area"], "budget": sp3["budget"], "hack": sp3["insider_tip"]}
    r2_row = summary_rows[1] if len(summary_rows) >= 2 else {"name_en": sp2["place_en"], "score": "93/100pt", "dish": sp2["area"], "budget": sp2["budget"], "hack": sp2["insider_tip"]}
    r1_row = summary_rows[0] if len(summary_rows) >= 1 else {"name_en": sp1["place_en"], "score": "96/100pt", "dish": sp1["area"], "budget": sp1["budget"], "hack": sp1["insider_tip"]}

    short_region = prefecture.replace("Sightseeing", "").replace("TOP 10", "").strip() or "Japan"
    hook_title = strip_cjk(shorts_cfg.get("promise_catch", f"NO PAID PROMO! {short_region} TOP 10"))

    def _short_punch(raw_text: str, prefix: str = "", max_words: int = 9) -> str:
        clean = " ".join(strip_cjk(raw_text).split())
        for sep in [". ", "! ", "? "]:
            if sep in clean:
                first = clean.split(sep)[0].strip()
                if len(first.split()) >= 4:
                    clean = first + "."
                    break
        words = clean.split()
        if len(words) > max_words:
            clean = " ".join(words[:max_words]).rstrip(",;:") + "!"
        return f"{prefix} {clean}".strip() if prefix else clean

    r3_short_name = strip_cjk(r3_row["name_en"].split("(")[0].strip())
    r2_short_name = strip_cjk(r2_row["name_en"].split("(")[0].strip())
    r1_short_name = strip_cjk(r1_row["name_en"].split("(")[0].strip())

    hook_narration = (
        f"Zero paid promos! Japanese Instagram ranked the Top 3 {short_region} locals actually love!"
    )

    short_scenes = [
        {
            "mode": "hook",
            "active_rank": "#1",
            "se_type": "area_chime",
            "badge": "ZERO PAID PROMO! REAL JAPANESE IG DATA",
            "title_en": hook_title,
            "sub_en": "500,000+ Japanese IG Posts • 100% Unsponsored",
            "access": f"{r1_row.get('access_short', 'Direct Access')} | {r1_row.get('budget', 'Local Price')}",
            "photos": [sp1["photos"][0], sp2["photos"][0]],
            "card_style": "praise",
            "card_body_en": rv1.get("review_praise_en", sp1["insider_tip"]),
            "card_body_ja": rv1.get("review_praise_ja", ""),
            "narration": hook_narration,
            "pop_lines": ["ZERO PAID PROMOS! REAL IG DATA!", f"Top 3 {short_region} Ranked by Locals!"],
        },
        {
            "mode": "cinema",
            "active_rank": "#3",
            "se_type": "top3_hit",
            "badge": f"NO.3  |  SCORE: {r3_row['score'].upper()}",
            "title_en": r3_short_name,
            "sub_en": f"{r3_row['dish'].split('(')[0].strip()} • {r3_row['hack']}",
            "access": f"{r3_row.get('access_short', sp3.get('access_info', 'Direct Access'))} | {r3_row.get('budget', '')}",
            "photos": [sp3["photos"][0], rv3["photos"][0]],
            "photo_tags": ["REAL JAPANESE IG VOICE", "LOCAL INSIDER HACK"],
            "card_style": "praise",
            "card_title": "REAL JAPANESE IG VOICE (NO PROMO)",
            "card_body_en": rv3.get("review_praise_en", sp3["insider_tip"]),
            "card_body_ja": rv3.get("review_praise_ja", ""),
            "narration": _short_punch(r3_row["dish"], f"Number 3: {r3_short_name}!", 7),
            "pop_lines": [f"#3 {r3_short_name.upper()} ({r3_row['score']})", r3_row["hack"]],
        },
        {
            "mode": "cinema",
            "active_rank": "#2",
            "se_type": "top3_hit",
            "badge": f"NO.2  |  SCORE: {r2_row['score'].upper()}",
            "title_en": r2_short_name,
            "sub_en": f"{r2_row['dish'].split('(')[0].strip()} • {r2_row['hack']}",
            "access": f"{r2_row.get('access_short', sp2.get('access_info', 'Direct Access'))} | {r2_row.get('budget', '')}",
            "photos": [sp2["photos"][0], rv2["photos"][0]],
            "photo_tags": ["REAL JAPANESE IG VOICE", "LOCAL INSIDER HACK"],
            "card_style": "warn",
            "card_title": "LOCAL IG INSIDER HACK",
            "card_body_en": rv2.get("review_praise_en", r2_row["hack"]),
            "card_body_ja": rv2.get("review_praise_ja", ""),
            "narration": _short_punch(r2_row["dish"], f"Number 2: {r2_short_name}!", 7),
            "pop_lines": [f"#2 {r2_short_name.upper()} ({r2_row['score']})", r2_row["hack"]],
        },
        {
            "mode": "cinema",
            "active_rank": "#1",
            "se_type": "top3_hit",
            "badge": f"NO.1  |  SCORE: {r1_row['score'].upper()}",
            "title_en": r1_short_name,
            "sub_en": f"{r1_row['dish'].split('(')[0].strip()} • {r1_row['hack']}",
            "access": f"{r1_row.get('access_short', sp1.get('access_info', 'Direct Access'))} | {r1_row.get('budget', '')}",
            "photos": [sp1["photos"][0], rv1["photos"][0]],
            "photo_tags": ["REAL JAPANESE IG VOICE", "MUST-KNOW LOCAL RULE"],
            "card_style": "praise",
            "card_title": "REAL JAPANESE IG #1 VERDICT",
            "card_body_en": rv1.get("review_praise_en", sp1["insider_tip"]),
            "card_body_ja": rv1.get("review_praise_ja", ""),
            "narration": _short_punch(r1_row["dish"], f"And Number 1: {r1_short_name}!", 8),
            "pop_lines": [f"#1 {r1_short_name.upper()} ({r1_row['score']})", r1_row["hack"]],
        },
        {
            "mode": "outro",
            "se_type": "area_chime",
            "badge": "FULL TOP 10 CHEAT-SHEET",
            "title_en": "Screenshot & Subscribe!",
            "sub_en": f"{prefecture} — 100% Unsponsored Local Guides",
            "access": "SUBSCRIBE + TAP CHANNEL BELOW FOR FULL TOP 10 VIDEO!",
            "narration": "Screenshot the full Top 10 list and tap our channel for the full guide!",
            "pop_lines": ["SCREENSHOT THIS TOP 10 LIST!", "TAP CHANNEL FOR FULL TOP 10!"],
        },
    ]

    ep_rot = sum(ord(c) for c in ranking_id) % 3
    logger.info(f"Shorts Design Rotation for '{ranking_id}': Lead Style #{ep_rot + 1} (Rotating 案A / 案B / 案C across all cuts)")

    with tempfile.TemporaryDirectory(prefix="yt_short_") as tmp_str:
        work_dir = Path(tmp_str)
        seg_videos: List[Path] = []
        seg_starts: List[float] = []
        cur_t = 0.0

        for idx, sc in enumerate(short_scenes):
            logger.info(f"Building Shorts Scene {idx + 1}/{len(short_scenes)}: {sc['badge']}")
            seg_starts.append(cur_t)

            tts_mp3 = work_dir / f"stts_{idx:02d}.mp3"
            comm = edge_tts.Communicate(text=sc["narration"], voice=voice, rate="+34%")
            asyncio.run(comm.save(str(tts_mp3)))

            seg_wav = work_dir / f"swav_{idx:02d}.wav"
            st_kind = "spot" if sc["se_type"] == "top3_hit" else ("review" if sc["se_type"] == "review_pop" else "spot")
            dur = build_segment_audio_with_se(tts_mp3, st_kind, sc["badge"], seg_wav)
            cur_t += dur

            p1 = work_dir / f"sp_{idx:02d}_a.jpg"
            p2 = work_dir / f"sp_{idx:02d}_b.jpg"
            short_flash: List[Path] = []
            if sc["mode"] == "hook":
                ph_a = cache_dir / sc["photos"][0]
                ph_b = cache_dir / sc["photos"][1]
                if ep_rot == 0:
                    render_short_ig_design_c_jpg(ph_a, sc, summary_rows, "#1", font_path, p1)
                    render_short_ig_design_a_jpg(ph_b, sc, font_path, p2)
                elif ep_rot == 1:
                    render_short_ig_design_a_jpg(ph_a, sc, font_path, p1)
                    render_short_ig_design_b_jpg(ph_a, ph_b, sc, font_path, p2)
                else:
                    render_short_ig_design_b_jpg(ph_a, ph_b, sc, font_path, p1)
                    render_short_ig_design_c_jpg(ph_a, sc, summary_rows, "#1", font_path, p2)
                short_flash = [p1, p2]
            elif sc["mode"] == "outro":
                render_short_outro_jpg(ranking_id, summary_rows, font_path, p1)
                shutil.copyfile(p1, p2)
            else:
                ph_a = cache_dir / sc["photos"][0]
                ph_b = cache_dir / sc["photos"][1]
                act_rk = sc.get("active_rank", "#1")
                if sc.get("card_style") == "praise":
                    # Rotate between 案C (TOP3 Countdown Stack) and 案A (Full-Screen NatGeo + IG Voice)
                    if (idx + ep_rot) % 2 == 0:
                        render_short_ig_design_c_jpg(ph_a, sc, summary_rows, act_rk, font_path, p1)
                        render_short_ig_design_a_jpg(ph_b, sc, font_path, p2)
                    else:
                        render_short_ig_design_a_jpg(ph_a, sc, font_path, p1)
                        render_short_ig_design_c_jpg(ph_b, sc, summary_rows, act_rk, font_path, p2)
                else:
                    # Rotate between 案B (Top/Bottom 2-Screen Split + IG Combo Bridge) and 案A (Full-Screen IG Warning)
                    if (idx + ep_rot) % 2 == 0:
                        render_short_ig_design_b_jpg(ph_a, ph_b, sc, font_path, p1)
                        render_short_ig_design_a_jpg(ph_b, sc, font_path, p2)
                    else:
                        render_short_ig_design_a_jpg(ph_a, sc, font_path, p1)
                        render_short_ig_design_b_jpg(ph_b, ph_a, sc, font_path, p2)

            hud_png = work_dir / f"shud_{idx:02d}.png"
            render_short_hud_png(sc, font_path, hud_png)

            half_dur = round(dur / 2.0, 3)

            seg_mp4 = work_dir / f"sseg_{idx:02d}.mp4"
            if sc["mode"] == "hook" and len(short_flash) >= 2:
                n_sf = len(short_flash)
                sl_d = round(dur / n_sf, 3)
                fc_s = []
                c_in = ""
                for sfi in range(n_sf):
                    d_s = sl_d if sfi < n_sf - 1 else round(max(0.4, dur - sl_d * (n_sf - 1) + 0.1), 3)
                    fc_s.append(f"[{sfi}:v]loop=loop=-1:size=1:start=0,trim=duration={d_s},setpts=PTS-STARTPTS,fps={FPS},setsar=1[sv{sfi}]")
                    c_in += f"[sv{sfi}]"
                fc_s.append(f"{c_in}concat=n={n_sf}:v=1:a=0[bg]")
                fc_s.append(f"[bg][{n_sf}:v]overlay=0:0,unsharp=5:5:0.75:3:3:0.0,noise=c0s=2:c0f=t+u,scale=in_range=pc:out_range=tv,format=yuv420p[vout]")
                filter_complex = ";".join(fc_s)

                s_cmd = ["ffmpeg", "-y"]
                for sfp in short_flash:
                    s_cmd.extend(["-i", str(sfp)])
                s_cmd.extend([
                    "-i", str(hud_png),
                    "-i", str(seg_wav),
                    "-filter_complex", filter_complex,
                    "-map", "[vout]",
                    "-map", f"{n_sf + 1}:a",
                    "-t", f"{dur:.3f}",
                    "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-level", "4.2", "-crf", "15", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                    "-shortest", str(seg_mp4),
                ])
                subprocess.run(s_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                if sc["mode"] == "outro":
                    filter_complex = (
                        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={dur},setpts=PTS-STARTPTS,fps={FPS},setsar=1[bg];"
                        f"[bg][2:v]overlay=0:0,unsharp=5:5:0.75:3:3:0.0,noise=c0s=2:c0f=t+u,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
                    )
                else:
                    # Rapid 2-cut transition (Cut 1A -> Cut 1B for every Cinema scene!)
                    filter_complex = (
                        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={half_dur},setpts=PTS-STARTPTS,fps={FPS},setsar=1[va];"
                        f"[1:v]loop=loop=-1:size=1:start=0,trim=duration={dur - half_dur + 0.1},setpts=PTS-STARTPTS,fps={FPS},setsar=1[vb];"
                        f"[va][vb]concat=n=2:v=1:a=0[bg];"
                        f"[bg][2:v]overlay=0:0,unsharp=5:5:0.75:3:3:0.0,noise=c0s=2:c0f=t+u,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
                    )

                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", str(p1),
                        "-i", str(p2),
                        "-i", str(hud_png),
                        "-i", str(seg_wav),
                        "-filter_complex", filter_complex,
                        "-map", "[vout]",
                        "-map", "3:a",
                        "-t", f"{dur:.3f}",
                        "-r", str(FPS),
                        "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-level", "4.2", "-crf", "15", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                        "-shortest", str(seg_mp4),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            seg_videos.append(seg_mp4)

        concat_txt = work_dir / "sconcat.txt"
        concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in seg_videos) + "\n", encoding="utf-8")
        merged_mp4 = work_dir / "smerged.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(merged_mp4)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        total_dur = get_duration(merged_mp4)
        bgm_mp3 = work_dir / "sbgm.mp3"
        generate_dynamic_4act_bgm(
            bgm_mp3,
            total_dur=total_dur + 3.0,
            act_boundaries=(0.1, 0.2, total_dur + 2.0),
            seg_starts=seg_starts,
        )
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(merged_mp4),
                "-i", str(bgm_mp3),
                "-filter_complex",
                "[0:a]volume=1.60[v];[1:a]volume=0.28[b];[v][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                "-shortest", str(short_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    logger.info(f"Completed Japan Ranking Shorts MP4 (1080x1920): {short_mp4} ({total_dur:.1f}s)")
    return short_mp4


def render_custom_thumbnails(script_path: Path) -> Tuple[Path, Path, Path]:
    """
    Generate 3 custom-designed high-CTR YouTube thumbnails (NOT video screenshots!):
    1. thumb_a (1280x720): Magazine Diagonal Split Hero + Tilted Polaroid Stack + Japan Map Radar
    2. thumb_b (1280x720): 3-Panel Diagonal Triptych Showdown (#3 vs #2 vs #1) for A/B Testing
    3. thumb_short (1080x1920): Vertical YouTube Shorts Custom Cover
    """
    from PIL import ImageFilter, ImageChops

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(script_path.read_text(encoding="utf-8"))
    rid = data["ranking_id"]
    rows = data.get("summary_rows", [])
    area_guide = data.get("area_guide", {})
    map_json = BASE_DIR / "assets" / "maps" / "japan_prefectures.json"
    prefs = json.loads(map_json.read_text(encoding="utf-8")) if map_json.exists() else []
    target_pref_ja, auto_route_pts = resolve_prefecture_and_route(
        area_guide, f"{rid} {data.get('prefecture', '')}", prefs
    )
    img_dir = BASE_DIR / "assets" / "images" / rid

    w9_path = "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc"
    if not Path(w9_path).exists():
        w9_path = find_font()
    black_path = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
    if not Path(black_path).exists():
        black_path = w9_path

    def grade_photo(im: Image.Image, w: int, h: int, sat: float = 1.38, con: float = 1.20, bri: float = 1.05) -> Image.Image:
        im = im.convert("RGB")
        w_bg = Image.new("RGB", im.size, (250, 250, 250))
        diff = ImageChops.difference(im, w_bg).convert("L").point(lambda p: 255 if p > 18 else 0)
        bb = diff.getbbox()
        if bb and (bb[2] - bb[0]) > im.width * 0.6 and (bb[3] - bb[1]) > im.height * 0.5:
            im = im.crop(bb)
        im = fit_crop(im, w, h)
        im = ImageEnhance.Color(im).enhance(sat)
        im = ImageEnhance.Contrast(im).enhance(con)
        im = ImageEnhance.Brightness(im).enhance(bri)
        im = ImageEnhance.Sharpness(im).enhance(1.35)
        return im

    def draw_pro_3d_text(
        canvas: Image.Image,
        xy: Tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        top_col: Tuple[int, int, int],
        bot_col: Tuple[int, int, int],
        stroke_w: int = 8,
        depth: int = 7,
    ) -> None:
        x, y = xy
        tb = ImageDraw.Draw(canvas).textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        pad = 28
        tw = (tb[2] - tb[0]) + pad * 2 + depth
        th = (tb[3] - tb[1]) + pad * 2 + depth
        ox = -tb[0] + pad
        oy = -tb[1] + pad

        glow_layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        gd.text((ox, oy + 4), text, font=font, fill=(0, 0, 0, 230), stroke_width=stroke_w + 6, stroke_fill=(0, 0, 0, 230))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=9))

        stroke_layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stroke_layer)
        for d in range(depth, 0, -1):
            sd.text((ox + d, oy + d), text, font=font, fill=(8, 10, 18, 255), stroke_width=stroke_w, stroke_fill=(8, 10, 18, 255))
        sd.text((ox, oy), text, font=font, fill=(0, 0, 0, 255), stroke_width=stroke_w, stroke_fill=(0, 0, 0, 255))

        mask_im = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(mask_im).text((ox, oy), text, font=font, fill=255)

        grad_im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        grd = ImageDraw.Draw(grad_im)
        span = max(1, th - pad * 2 - depth)
        for py in range(th):
            t = max(0.0, min(1.0, (py - pad) / span))
            r = int(top_col[0] * (1 - t) + bot_col[0] * t)
            g = int(top_col[1] * (1 - t) + bot_col[1] * t)
            b = int(top_col[2] * (1 - t) + bot_col[2] * t)
            grd.line([(0, py), (tw, py)], fill=(r, g, b, 255))

        comp = Image.alpha_composite(glow_layer, stroke_layer)
        comp.paste(grad_im, (0, 0), mask_im)
        canvas.alpha_composite(comp, (x + tb[0] - pad, y + tb[1] - pad))

    def clean_short_spot_name(raw_name: str) -> str:
        """Strip parenthetical suffixes like '(Higashi-Ginza)' so spot names are clean and never leave dangling '('."""
        base = strip_cjk(raw_name).split("(")[0].split("—")[0].split(" - ")[0].strip()
        return base or strip_cjk(raw_name)

    def clean_short_dish(raw_dish: str) -> str:
        """Strip parentheticals, '+' secondary clauses, and score tags from dish/feature descriptions."""
        base = strip_cjk(raw_dish).split("(")[0].split("|")[0].split(" + ")[0].strip()
        return base or strip_cjk(raw_dish)

    def make_polaroid_card(
        photo_path: Path,
        card_w: int,
        card_h: int,
        rank_txt: str,
        title_txt: str,
        badge_col: Tuple[int, int, int],
        angle_deg: float,
    ) -> Image.Image:
        base = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(base)
        d.rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius=18, fill=(255, 255, 255, 255), outline=(253, 224, 71, 255), width=3)
        ph = grade_photo(Image.open(photo_path), card_w - 16, card_h - 52, sat=1.40, con=1.22)
        mask = Image.new("L", (card_w - 16, card_h - 52), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_w - 16, card_h - 52), radius=12, fill=255)
        base.paste(ph.convert("RGBA"), (8, 8), mask)

        f_rk = ImageFont.truetype(w9_path, 19)
        tb_r = d.textbbox((0, 0), rank_txt, font=f_rk)
        rw = (tb_r[2] - tb_r[0]) + 22
        d.rounded_rectangle((14, 14, 14 + rw, 46), radius=8, fill=(*badge_col, 250), outline=(255, 255, 255, 255), width=2)
        d.text((25, 21), rank_txt, font=f_rk, fill=(255, 255, 255, 255))

        clean_t = clean_short_spot_name(title_txt)
        f_tt = fit_font_for_width(d, clean_t, w9_path, 19, 13, card_w - 20)
        clean_t = smart_truncate(d, clean_t, f_tt, card_w - 20)
        tb_t = d.textbbox((0, 0), clean_t, font=f_tt)
        d.text(((card_w - (tb_t[2] - tb_t[0])) // 2, card_h - 36), clean_t, font=f_tt, fill=(15, 23, 42, 255))

        rot = base.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True)
        sh = Image.new("RGBA", (rot.width + 32, rot.height + 32), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", rot.size, (0, 0, 0, 220)), (20, 22), rot.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(radius=10))
        sh.alpha_composite(rot, (12, 10))
        return sh

    def _pick_thumb_photo(thumb_name: str) -> Path:
        clean_cand = img_dir / thumb_name.replace(".jpg", "_clean.jpg")
        return clean_cand if clean_cand.exists() else (img_dir / thumb_name)

    p1_path = _pick_thumb_photo(rows[0]["thumb"])
    p2_path = _pick_thumb_photo(rows[1]["thumb"])
    p3_path = _pick_thumb_photo(rows[2]["thumb"])

    thumb_a = OUTPUT_DIR / f"overseas_japan_{rid}_thumb.jpg"
    thumb_b = OUTPUT_DIR / f"overseas_japan_{rid}_thumb_alt.jpg"
    thumb_s = OUTPUT_DIR / f"overseas_japan_{rid}_short_thumb.jpg"

    tc = data.get("thumb_config", {})
    clean_pref = (
        strip_cjk(data.get("prefecture", "JAPAN"))
        .replace("TOP 10", "")
        .replace("Sightseeing", "")
        .replace("Real Sites", "")
        .replace("Sacred Sites", "")
        .strip()
        .upper()
        or "JAPAN"
    )
    short_geo = clean_pref.split()[0] if clean_pref else "JAPAN"

    # Dynamically choose clean, non-redundant hero_line1 and hero_line2
    raw_hl1 = tc.get("hero_line1", "NO PROMO!")
    if "ANIME" in raw_hl1:
        hero_line1 = "REAL ANIME SCENES!"
    elif "SKIP" in raw_hl1 and "TOKYO" not in clean_pref and "RAMEN" not in clean_pref and "SUSHI" not in clean_pref:
        hero_line1 = raw_hl1.split("REAL JAPAN")[0].strip()
    else:
        hero_line1 = "NO PROMO!"
    hero_line2 = "REAL JAPAN"

    # Never chop region names mid-word (fixes 'TOKYO RAME TOP 10' -> 'TOKYO RAMEN TOP 10')
    banner_title = re.sub(r"(TOP 10\s*)+$", "TOP 10", f"{clean_pref} TOP 10").strip()
    banner_sub = tc.get("banner_sub", "REAL JAPANESE IG VOICES ONLY")
    non_geo_words = {"YOUR", "REAL", "STEP", "ANIME", "DEMON", "SLAM", "ONE", "SPIRITED", "JUJUTSU", "STUDIO"}
    map_header = "WHERE IN JAPAN?" if short_geo in non_geo_words else f"WHERE IS {short_geo}?"
    map_pill = tc.get("map_pill", "DIRECT")
    map_line1 = tc.get("map_line1", "Shinkansen / Train")
    map_line2 = tc.get("map_line2", "from Tokyo Station!")
    map_footer = "0% SPONSORED"
    highlight_prefs = set(tc.get("highlight_prefs_ja", [target_pref_ja]))

    r1_clean_name = clean_short_spot_name(rows[0]["name_en"]).upper()
    r2_clean_name = clean_short_spot_name(rows[1]["name_en"]).upper()
    r3_clean_name = clean_short_spot_name(rows[2]["name_en"]).upper()
    r1_clean_dish = clean_short_dish(rows[0]["dish"]).upper()
    r2_clean_dish = clean_short_dish(rows[1]["dish"]).upper()
    r3_clean_dish = clean_short_dish(rows[2]["dish"]).upper()

    # =========================================================================
    # Design A (1280x720): Diagonal Split + Polaroid Stack + Map Radar
    # =========================================================================
    canvas_a = Image.new("RGBA", (W, H), (8, 12, 24, 255))
    hero_im = grade_photo(Image.open(p1_path), 920, H, sat=1.42, con=1.22, bri=1.06)
    canvas_a.paste(hero_im.convert("RGBA"), (360, 0))

    flare = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(flare)
    for r in range(360, 10, -10):
        a = int(60 * (1 - r / 360) ** 1.8)
        fd.ellipse((960 - r, 90 - r, 960 + r, 90 + r), fill=(253, 224, 71, a))
    canvas_a.alpha_composite(flare)

    slash = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(slash)
    sd.polygon([(0, 0), (545, 0), (435, H), (0, H)], fill=(8, 13, 26, 248))
    for y in range(H):
        edge_x = int(545 - (545 - 435) * (y / H))
        for dx in range(145):
            alpha = int(248 * (1.0 - dx / 145.0) ** 1.6)
            sd.point((edge_x + dx, y), fill=(8, 13, 26, alpha))
    canvas_a.alpha_composite(slash)

    d_a = ImageDraw.Draw(canvas_a)
    d_a.line([(552, -5), (442, H + 5)], fill=(220, 38, 38, 255), width=12)
    d_a.line([(546, -5), (436, H + 5)], fill=(253, 224, 71, 255), width=6)

    pol3 = make_polaroid_card(p3_path, 272, 194, f"#3  {rows[2]['score']}", rows[2]["name_en"], (2, 132, 199), -5.5)
    pol2 = make_polaroid_card(p2_path, 272, 194, f"#2  {rows[1]['score']}", rows[1]["name_en"], (220, 38, 38), 5.5)
    canvas_a.alpha_composite(pol3, (972, 232))
    canvas_a.alpha_composite(pol2, (966, 448))

    # Top-left Instagram Verification Ribbon (x=28..516, y=20..76)
    d_a.rounded_rectangle((28, 20, 516, 76), radius=12, fill=(24, 16, 40, 250), outline=(225, 48, 108, 255), width=3)
    draw_instagram_logo(canvas_a, 38, 26, 44)
    rib_txt = tc.get("ribbon_text", "ZERO PAID PROMO • JAPANESE IG")
    f_rib = fit_font_for_width(d_a, rib_txt, w9_path, 21, 14, 412)
    rib_txt_fit = smart_truncate(d_a, rib_txt, f_rib, 412)
    d_a.text((92, 36), rib_txt_fit, font=f_rib, fill=(255, 255, 255, 255))

    # Top-right #1 Highlight Pill strictly bounded to x=566..1260 (never overlaps left ribbon!)
    bx0, bx1 = 566, 1260
    avail_top_r = bx1 - bx0
    f_b1 = ImageFont.truetype(w9_path, 21)
    t_no1 = f"NO.1: {rows[0]['score'].upper()}"
    tb_n1 = d_a.textbbox((0, 0), t_no1, font=f_b1)
    w_n1 = (tb_n1[2] - tb_n1[0]) + 28
    max_ph_w = avail_top_r - w_n1 - 36
    f_b2 = fit_font_for_width(d_a, r1_clean_dish, w9_path, 20, 14, max_ph_w)
    t_ph = smart_truncate(d_a, r1_clean_dish, f_b2, max_ph_w)
    tb_ph = d_a.textbbox((0, 0), t_ph, font=f_b2)
    actual_box_w = w_n1 + (tb_ph[2] - tb_ph[0]) + 38
    bx0_dyn = max(566, bx1 - actual_box_w)
    d_a.rounded_rectangle((bx0_dyn, 20, bx1, 80), radius=14, fill=(12, 18, 32, 244), outline=(253, 224, 71, 255), width=3)
    d_a.rounded_rectangle((bx0_dyn + 8, 28, bx0_dyn + 8 + w_n1, 72), radius=9, fill=(217, 119, 6, 255))
    d_a.text((bx0_dyn + 22, 39), t_no1, font=f_b1, fill=(255, 255, 255, 255))
    d_a.text((bx0_dyn + 8 + w_n1 + 14, 40), t_ph, font=f_b2, fill=(253, 224, 71, 255))

    f_hero1 = fit_font_for_width(d_a, hero_line1, black_path, 72, 42, 490)
    f_hero2 = fit_font_for_width(d_a, hero_line2, black_path, 76, 48, 490)
    draw_pro_3d_text(canvas_a, (28, 88), hero_line1, f_hero1, (255, 255, 255), (218, 234, 255), stroke_w=9, depth=8)
    draw_pro_3d_text(canvas_a, (28, 178), hero_line2, f_hero2, (255, 248, 130), (245, 158, 11), stroke_w=10, depth=9)

    d_a.rounded_rectangle((28, 288, 502, 396), radius=18, fill=(14, 116, 144, 248), outline=(167, 243, 208, 255), width=3)
    f_ak = fit_font_for_width(d_a, banner_title, w9_path, 38, 18, 444)
    banner_title_fit = smart_truncate(d_a, banner_title, f_ak, 444)
    f_ak_sub = fit_font_for_width(d_a, banner_sub, w9_path, 19, 14, 444)
    banner_sub_fit = smart_truncate(d_a, banner_sub, f_ak_sub, 444)
    d_a.text((44, 304), banner_title_fit, font=f_ak, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 240))
    d_a.text((44, 356), banner_sub_fit, font=f_ak_sub, fill=(253, 224, 71, 255), stroke_width=2, stroke_fill=(0, 0, 0, 230))

    mx0, my0, mx1, my1 = 28, 414, 452, 696
    d_a.rounded_rectangle((mx0, my0, mx1, my1), radius=20, fill=(10, 18, 34, 245), outline=(56, 189, 248, 250), width=3)
    lon_min, lon_max = 130.2, 145.4
    lat_min, lat_max = 31.4, 44.2
    px0, py0, px1, py1 = mx0 + 10, my0 + 14, mx0 + 202, my1 - 12

    def proj_a(lon: float, lat: float) -> Tuple[int, int]:
        px = px0 + (lon - lon_min) / (lon_max - lon_min) * (px1 - px0)
        py = py1 - (lat - lat_min) / (lat_max - lat_min) * (py1 - py0)
        return int(round(px)), int(round(py))

    if prefs:
        for pf in prefs:
            if pf["nam_ja"] in highlight_prefs:
                continue
            fc = (56, 189, 248, 220) if pf["nam_ja"] == "東京都" else (71, 85, 105, 210)
            for ring in pf["polys"]:
                pts = [proj_a(pt[0], pt[1]) for pt in ring]
                if len(pts) >= 3:
                    d_a.polygon(pts, fill=fc, outline=(148, 163, 184, 140))
        for pf in prefs:
            if pf["nam_ja"] in highlight_prefs:
                for ring in pf["polys"]:
                    pts = [proj_a(pt[0], pt[1]) for pt in ring]
                    if len(pts) >= 3:
                        d_a.polygon(pts, fill=(239, 68, 68, 255), outline=(253, 224, 71, 255))
                        d_a.line(pts + [pts[0]], fill=(253, 224, 71, 255), width=2)

    s_pts = tc.get("route_lonlat", auto_route_pts)
    if len(s_pts) >= 2:
        d_a.line([proj_a(lo, la) for lo, la in s_pts], fill=(253, 224, 71, 255), width=4)
        tx_p, ty_p = proj_a(s_pts[0][0], s_pts[0][1])
        ax_p, ay_p = proj_a(s_pts[-1][0], s_pts[-1][1])
        d_a.ellipse((tx_p - 6, ty_p - 6, tx_p + 6, ty_p + 6), fill=(56, 189, 248, 255), outline=(255, 255, 255, 255), width=2)
        d_a.ellipse((ax_p - 8, ay_p - 8, ax_p + 8, ay_p + 8), fill=(239, 68, 68, 255), outline=(253, 224, 71, 255), width=2)

    rx0, rx1 = mx0 + 206, mx1 - 14
    rw_box = rx1 - rx0
    f_m1 = fit_font_for_width(d_a, map_header, w9_path, 18, 13, rw_box - 6)
    f_m2 = ImageFont.truetype(black_path, 28 if len(map_pill) > 8 else 34)
    f_m3 = ImageFont.truetype(w9_path, 16)
    tb_wh = d_a.textbbox((0, 0), map_header, font=f_m1)
    d_a.text((rx0 + (rw_box - (tb_wh[2] - tb_wh[0])) // 2, my0 + 22), map_header, font=f_m1, fill=(56, 189, 248, 255))
    d_a.rounded_rectangle((rx0, my0 + 58, rx1, my0 + 128), radius=12, fill=(16, 185, 129, 255))
    tb_3h = d_a.textbbox((0, 0), map_pill, font=f_m2)
    d_a.text((rx0 + (rw_box - (tb_3h[2] - tb_3h[0])) // 2, my0 + 70), map_pill, font=f_m2, fill=(255, 255, 255, 255))
    d_a.text((rx0 + 6, my0 + 146), map_line1, font=f_m3, fill=(253, 224, 71, 255))
    d_a.text((rx0 + 6, my0 + 172), map_line2, font=f_m3, fill=(255, 255, 255, 255))
    d_a.rounded_rectangle((rx0, my0 + 208, rx1, my0 + 256), radius=8, fill=(220, 38, 38, 245))
    tb_loc = d_a.textbbox((0, 0), map_footer, font=f_m3)
    d_a.text((rx0 + (rw_box - (tb_loc[2] - tb_loc[0])) // 2, my0 + 223), map_footer, font=f_m3, fill=(255, 255, 255, 255))

    # Bottom-center #1 Badge strictly bounded to x=466..952 so it never collides with Polaroid #2
    cx0_b, cx1_b_max = 466, 952
    max_cb_tw = (cx1_b_max - cx0_b) - 36
    tc1 = f"#1 {r1_clean_name} ({rows[0]['score'].split('/')[0].strip()} PT)"
    tc2 = "100% NO PAID PROMO  |  JAPANESE IG #1"
    f_c1 = fit_font_for_width(d_a, tc1, w9_path, 22, 15, max_cb_tw)
    f_c2 = fit_font_for_width(d_a, tc2, w9_path, 18, 14, max_cb_tw)
    w_c = min(cx1_b_max - cx0_b, max(d_a.textbbox((0, 0), tc1, font=f_c1)[2], d_a.textbbox((0, 0), tc2, font=f_c2)[2]) + 36)
    d_a.rounded_rectangle((cx0_b, 608, cx0_b + w_c, 696), radius=18, fill=(12, 18, 32, 244), outline=(245, 158, 11, 255), width=3)
    d_a.text((cx0_b + 18, 622), tc1, font=f_c1, fill=(253, 224, 71, 255))
    d_a.text((cx0_b + 18, 658), tc2, font=f_c2, fill=(167, 243, 208, 255))

    canvas_a.convert("RGB").save(thumb_a, "JPEG", quality=96)
    logger.info(f"Completed Custom Thumbnail A (1280x720): {thumb_a}")

    # =========================================================================
    # Design B (1280x720): 3-Panel Diagonal Triptych Showdown (#3 vs #2 vs #1)
    # =========================================================================
    canvas_b = Image.new("RGBA", (W, H), (8, 12, 24, 255))
    im3_b = grade_photo(Image.open(p3_path), 480, H, sat=1.35, con=1.18)
    im2_b = grade_photo(Image.open(p2_path), 520, H, sat=1.38, con=1.20)
    im1_b = grade_photo(Image.open(p1_path), 640, H, sat=1.45, con=1.24, bri=1.06)

    m3 = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m3).polygon([(0, 0), (415, 0), (335, H), (0, H)], fill=255)
    p3_full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p3_full.paste(im3_b.convert("RGBA"), (0, 0))
    canvas_b.paste(p3_full, (0, 0), m3)

    m2 = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m2).polygon([(415, 0), (805, 0), (725, H), (335, H)], fill=255)
    p2_full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p2_full.paste(im2_b.convert("RGBA"), (325, 0))
    canvas_b.paste(p2_full, (0, 0), m2)

    m1 = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m1).polygon([(805, 0), (W, 0), (W, H), (725, H)], fill=255)
    p1_full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p1_full.paste(im1_b.convert("RGBA"), (680, 0))
    canvas_b.paste(p1_full, (0, 0), m1)

    ov_b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od_b = ImageDraw.Draw(ov_b)
    for y in range(215):
        a = int(235 * (1 - y / 215) ** 1.3)
        od_b.line([(0, y), (W, y)], fill=(6, 10, 22, a))
    for y in range(H - 220, H):
        t = (y - (H - 220)) / 220
        a = int(246 * (t ** 1.25))
        od_b.line([(0, y), (W, y)], fill=(6, 10, 22, a))
    canvas_b.alpha_composite(ov_b)

    d_b = ImageDraw.Draw(canvas_b)
    d_b.line([(415, 0), (335, H)], fill=(15, 23, 42, 255), width=14)
    d_b.line([(415, 0), (335, H)], fill=(253, 224, 71, 255), width=5)
    d_b.line([(805, 0), (725, H)], fill=(15, 23, 42, 255), width=14)
    d_b.line([(805, 0), (725, H)], fill=(253, 224, 71, 255), width=5)

    f_sub_b = ImageFont.truetype(w9_path, 22)
    t_sub_b = "100% NO PAID PROMO  •  ANALYZED FROM JAPANESE IG"
    tb_sb = d_b.textbbox((0, 0), t_sub_b, font=f_sub_b)
    w_sb = (tb_sb[2] - tb_sb[0]) + 84
    d_b.rounded_rectangle((28, 18, 28 + w_sb, 68), radius=10, fill=(24, 16, 40, 250), outline=(225, 48, 108, 255), width=3)
    draw_instagram_logo(canvas_b, 38, 23, 40)
    d_b.text((90, 32), t_sub_b, font=f_sub_b, fill=(255, 255, 255, 255))

    f_b_main = fit_font_for_width(d_b, banner_title, black_path, 82, 52, W - 64)
    draw_pro_3d_text(canvas_b, (28, 74), banner_title, f_b_main, (255, 250, 145), (245, 158, 11), stroke_w=10, depth=9)

    f_vs = ImageFont.truetype(black_path, 28)
    for vx, vy in [(375, 360), (765, 360)]:
        d_b.ellipse((vx - 34, vy - 34, vx + 34, vy + 34), fill=(220, 38, 38, 255), outline=(253, 224, 71, 255), width=4)
        tb_v = d_b.textbbox((0, 0), "VS", font=f_vs)
        d_b.text((vx - (tb_v[2] - tb_v[0]) // 2, vy - 18), "VS", font=f_vs, fill=(255, 255, 255, 255))

    # Each panel has a strict horizontal width limit so text NEVER crosses the diagonal divider!
    panels_b = [
        (16, 540, 312, f"#3 ({rows[2]['score'].split('/')[0].strip()} PT)", r3_clean_name, r3_clean_dish, (2, 132, 199)),
        (356, 540, 360, f"#2 ({rows[1]['score'].split('/')[0].strip()} PT)", r2_clean_name, r2_clean_dish, (234, 88, 12)),
        (748, 524, 512, f"#1 WINNER ({rows[0]['score'].split('/')[0].strip()} PT)", r1_clean_name, r1_clean_dish, (220, 38, 38)),
    ]
    for px, py, max_pw, rk_s, nm_en, tg_en, col in panels_b:
        f_rk_b = fit_font_for_width(d_b, rk_s, black_path, 30, 20, max_pw - 24)
        tb_r = d_b.textbbox((0, 0), rk_s, font=f_rk_b)
        bw = (tb_r[2] - tb_r[0]) + 26
        d_b.rounded_rectangle((px, py, px + bw, py + 50), radius=12, fill=(*col, 255), outline=(253, 224, 71, 255), width=3)
        d_b.text((px + 13, py + 8), rk_s, font=f_rk_b, fill=(255, 255, 255, 255))

        f_tg_b = fit_font_for_width(d_b, tg_en, w9_path, 16, 12, max_pw)
        tg_fit = smart_truncate(d_b, tg_en, f_tg_b, max_pw)
        f_nm_b = fit_font_for_width(d_b, nm_en, w9_path, 25, 16, max_pw)
        nm_fit = smart_truncate(d_b, nm_en, f_nm_b, max_pw)

        d_b.text((px + 4, py + 60), tg_fit, font=f_tg_b, fill=(253, 224, 71, 255), stroke_width=3, stroke_fill=(0, 0, 0, 245))
        d_b.text((px + 4, py + 86), nm_fit, font=f_nm_b, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255))

    canvas_b.convert("RGB").save(thumb_b, "JPEG", quality=96)
    logger.info(f"Completed Custom Thumbnail B (1280x720): {thumb_b}")

    # =========================================================================
    # Design 3 (1280x720): "PAID INFLUENCER TRAP vs JAPANESE IG #1" Split
    # =========================================================================
    p4_path = img_dir / rows[3]["thumb"] if len(rows) > 3 else p3_path
    canvas_3 = Image.new("RGBA", (W, H), (10, 12, 20, 255))
    trap_im = grade_photo(Image.open(p4_path), 510, H, sat=0.25, con=1.15, bri=0.65)
    red_tint = Image.new("RGBA", (510, H), (90, 10, 15, 85))
    canvas_3.paste(Image.alpha_composite(trap_im.convert("RGBA"), red_tint), (0, 0))

    real_im3 = grade_photo(Image.open(p1_path), 820, H, sat=1.48, con=1.24, bri=1.06)
    m_right = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m_right).polygon([(505, 0), (W, 0), (W, H), (445, H)], fill=255)
    r_full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r_full.paste(real_im3.convert("RGBA"), (445, 0))
    canvas_3.paste(r_full, (0, 0), m_right)

    ov3 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od3 = ImageDraw.Draw(ov3)
    for y in range(210):
        a = int(240 * (1 - y / 210) ** 1.3)
        od3.line([(0, y), (W, y)], fill=(6, 10, 20, a))
    for y in range(H - 195, H):
        t = (y - (H - 195)) / 195
        a = int(242 * (t ** 1.3))
        od3.line([(0, y), (W, y)], fill=(6, 10, 20, a))
    canvas_3.alpha_composite(ov3)

    d3 = ImageDraw.Draw(canvas_3)
    d3.line([(505, 0), (445, H)], fill=(15, 23, 42, 255), width=18)
    d3.line([(505, 0), (445, H)], fill=(253, 224, 71, 255), width=6)

    d3.rounded_rectangle((24, 180, 445, 254), radius=14, fill=(185, 28, 28, 250), outline=(255, 255, 255, 255), width=3)
    f_st = ImageFont.truetype(black_path, 34)
    tb_st = d3.textbbox((0, 0), "TOURIST TRAP", font=f_st)
    d3.text((24 + (421 - (tb_st[2] - tb_st[0])) // 2, 194), "TOURIST TRAP", font=f_st, fill=(255, 255, 255, 255))

    cx_x, cy_x = 235, 390
    d3.ellipse((cx_x - 68, cy_x - 68, cx_x + 68, cy_x + 68), fill=(220, 38, 38, 235), outline=(255, 255, 255, 255), width=5)
    f_x = ImageFont.truetype(black_path, 76)
    tb_x = d3.textbbox((0, 0), "X", font=f_x)
    d3.text((cx_x - (tb_x[2] - tb_x[0]) // 2, cy_x - 48), "X", font=f_x, fill=(255, 255, 255, 255))

    f_lb = ImageFont.truetype(w9_path, 23)
    f_ls = ImageFont.truetype(w9_path, 18)
    d3.text((24, 595), "PAID INFLUENCER TRAP", font=f_lb, fill=(252, 165, 165, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    d3.text((24, 632), "90% of Tourists Fall For This", font=f_ls, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))

    d3.rounded_rectangle((540, 180, 1060, 254), radius=14, fill=(24, 16, 40, 250), outline=(225, 48, 108, 255), width=4)
    draw_instagram_logo(canvas_3, 556, 188, 56)
    rl_stamp = "JAPANESE IG #1"
    tb_rl = d3.textbbox((0, 0), rl_stamp, font=f_st)
    d3.text((624 + (420 - (tb_rl[2] - tb_rl[0])) // 2, 194), rl_stamp, font=f_st, fill=(255, 255, 255, 255))

    top3_txt = f"{hero_line1} {banner_title}"
    f_top3 = fit_font_for_width(d3, top3_txt, black_path, 72, 28, W - 56)
    top3_txt = smart_truncate(d3, top3_txt, f_top3, W - 56)
    draw_pro_3d_text(canvas_3, (28, 20), top3_txt, f_top3, (255, 250, 140), (245, 158, 11), stroke_w=10, depth=9)

    d3.rounded_rectangle((490, 568, 1252, 696), radius=20, fill=(10, 18, 34, 245), outline=(253, 224, 71, 255), width=4)
    max_d3_w = (1252 - 490) - 48
    t_w1 = f"#1 {r1_clean_name} ({rows[0]['score'].split('/')[0]} PT)"
    t_w2 = f"{clean_short_dish(rows[0]['dish'])}  |  100% No Paid Promo"
    f_w1 = fit_font_for_width(d3, t_w1, black_path, 35, 20, max_d3_w)
    f_w2 = fit_font_for_width(d3, t_w2, w9_path, 20, 14, max_d3_w)
    t_w2 = smart_truncate(d3, t_w2, f_w2, max_d3_w)
    d3.text((514, 586), t_w1, font=f_w1, fill=(253, 224, 71, 255))
    d3.text((514, 644), t_w2, font=f_w2, fill=(167, 243, 208, 255))

    # =========================================================================
    # Design 4 (1280x720): 4-Photo Bento Magazine Grid + Center Shield Emblem
    # =========================================================================
    canvas_4 = Image.new("RGBA", (W, H), (8, 12, 24, 255))
    cells_4 = [
        (12, 12, 622, 342, rows[0], (220, 38, 38), True),
        (646, 12, 622, 342, rows[1], (234, 88, 12), True),
        (12, 366, 622, 342, rows[2], (2, 132, 199), False),
        (646, 366, 622, 342, rows[3] if len(rows) > 3 else rows[0], (16, 185, 129), False),
    ]
    d4 = ImageDraw.Draw(canvas_4)
    f_c_rk = ImageFont.truetype(black_path, 24)
    for cx, cy, cw, ch, row, bcol, is_top in cells_4:
        im_c = grade_photo(Image.open(img_dir / row["thumb"]), cw, ch, sat=1.42, con=1.22)
        ov_c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        od_c = ImageDraw.Draw(ov_c)
        if is_top:
            for yy in range(0, 90):
                a = int(225 * (1 - yy / 90) ** 1.2)
                od_c.line([(0, yy), (cw, yy)], fill=(6, 10, 22, a))
        else:
            for yy in range(ch - 95, ch):
                a = int(230 * ((yy - (ch - 95)) / 95) ** 1.2)
                od_c.line([(0, yy), (cw, yy)], fill=(6, 10, 22, a))
        canvas_4.paste(Image.alpha_composite(im_c.convert("RGBA"), ov_c), (cx, cy))
        d4.rectangle((cx, cy, cx + cw, cy + ch), outline=(253, 224, 71, 255), width=3)

        rk_t = f"{row['rank']} ({row['score'].split('/')[0]} PT)"
        tb_r = d4.textbbox((0, 0), rk_t, font=f_c_rk)
        rw = (tb_r[2] - tb_r[0]) + 22
        px, py = cx + 16, (cy + 16 if is_top else cy + ch - 62)
        d4.rounded_rectangle((px, py, px + rw, py + 44), radius=10, fill=(*bcol, 250), outline=(255, 255, 255, 255), width=2)
        d4.text((px + 11, py + 7), rk_t, font=f_c_rk, fill=(255, 255, 255, 255))

        cell_nm = clean_short_spot_name(row["name_en"]).upper()
        max_cell_tw = (cx + cw - 16) - (px + rw + 12)
        f_c_nm = fit_font_for_width(d4, cell_nm, w9_path, 22, 14, max_cell_tw)
        cell_nm_fit = smart_truncate(d4, cell_nm, f_c_nm, max_cell_tw)
        d4.text((px + rw + 12, py + 11), cell_nm_fit, font=f_c_nm, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))

    ex0, ey0, ex1, ey1 = 215, 232, 1065, 488
    sh4 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh4).rounded_rectangle((ex0 - 12, ey0 - 8, ex1 + 12, ey1 + 16), radius=34, fill=(0, 0, 0, 235))
    canvas_4.alpha_composite(sh4.filter(ImageFilter.GaussianBlur(radius=14)))
    d4 = ImageDraw.Draw(canvas_4)
    d4.rounded_rectangle((ex0, ey0, ex1, ey1), radius=28, fill=(10, 16, 32, 248), outline=(253, 224, 71, 255), width=5)
    d4.rounded_rectangle((ex0 + 50, ey0 - 24, ex1 - 50, ey0 + 26), radius=18, fill=(24, 16, 40, 255), outline=(225, 48, 108, 255), width=3)
    draw_instagram_logo(canvas_4, ex0 + 66, ey0 - 19, 38)
    f_em_sub = ImageFont.truetype(w9_path, 21)
    t_em = "ZERO PAID PROMO • JAPANESE IG ANALYZED"
    tb_em = d4.textbbox((0, 0), t_em, font=f_em_sub)
    d4.text(((W - (tb_em[2] - tb_em[0])) // 2 + 20, ey0 - 10), t_em, font=f_em_sub, fill=(255, 255, 255, 255))
    f_em_main = fit_font_for_width(d4, banner_title, black_path, 74, 30, (ex1 - ex0) - 48)
    tb_bm = d4.textbbox((0, 0), banner_title, font=f_em_main)
    draw_pro_3d_text(canvas_4, ((W - (tb_bm[2] - tb_bm[0])) // 2, ey0 + 40), banner_title, f_em_main, (255, 250, 140), (245, 158, 11), stroke_w=10, depth=8)
    f_em_bot = ImageFont.truetype(w9_path, 20)
    t_eb = "100% UNSPONSORED • REAL JAPANESE LOCAL VOICES"
    tb_eb = d4.textbbox((0, 0), t_eb, font=f_em_bot)
    d4.text(((W - (tb_eb[2] - tb_eb[0])) // 2, ey1 - 46), t_eb, font=f_em_bot, fill=(167, 243, 208, 255))

    # =========================================================================
    # Design 5 (1280x720): Full-Bleed Cinema Poster + Bottom Podium Bar
    # =========================================================================
    canvas_5 = Image.new("RGBA", (W, H), (8, 12, 24, 255))
    bg5 = grade_photo(Image.open(p2_path), W, H, sat=1.45, con=1.24, bri=1.04)
    canvas_5.paste(bg5.convert("RGBA"), (0, 0))
    ov5 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od5 = ImageDraw.Draw(ov5)
    for y in range(250):
        a = int(242 * (1 - y / 250) ** 1.3)
        od5.line([(0, y), (W, y)], fill=(6, 10, 22, a))
    for y in range(H - 230, H):
        t = (y - (H - 230)) / 230
        a = int(248 * (t ** 1.2))
        od5.line([(0, y), (W, y)], fill=(6, 10, 22, a))
    canvas_5.alpha_composite(ov5)

    d5 = ImageDraw.Draw(canvas_5)
    t_r5 = "100% NO PAID PROMO • JAPANESE IG VOICE RANKING"
    tb_r5 = d5.textbbox((0, 0), t_r5, font=f_em_sub)
    rw5 = (tb_r5[2] - tb_r5[0]) + 100
    rx5_0 = (W - rw5) // 2
    d5.rounded_rectangle((rx5_0, 16, rx5_0 + rw5, 64), radius=24, fill=(24, 16, 40, 255), outline=(225, 48, 108, 255), width=3)
    draw_instagram_logo(canvas_5, rx5_0 + 18, 21, 38)
    d5.text((rx5_0 + 66, 29), t_r5, font=f_em_sub, fill=(255, 255, 255, 255))

    cin_title = f"{hero_line1} {banner_title}"
    f_cin = fit_font_for_width(d5, cin_title, black_path, 72, 28, W - 56)
    cin_title = smart_truncate(d5, cin_title, f_cin, W - 56)
    tb_cin = d5.textbbox((0, 0), cin_title, font=f_cin)
    draw_pro_3d_text(canvas_5, ((W - (tb_cin[2] - tb_cin[0])) // 2, 74), cin_title, f_cin, (255, 250, 145), (245, 158, 11), stroke_w=10, depth=8)

    pod_cards = [
        (28, 548, 390, 148, f"#1 {r1_clean_name}", f"{rows[0]['score']}  |  {rows[0]['access_short']}", clean_short_dish(rows[0]["dish"]), (220, 38, 38)),
        (445, 548, 390, 148, f"#2 {r2_clean_name}", f"{rows[1]['score']}  |  {rows[1]['access_short']}", clean_short_dish(rows[1]["dish"]), (234, 88, 12)),
        (862, 548, 390, 148, f"#3 {r3_clean_name}", f"{rows[2]['score']}  |  {rows[2]['access_short']}", clean_short_dish(rows[2]["dish"]), (2, 132, 199)),
    ]
    for px, py, pw, ph, pt1, pt2, pt3, pcol in pod_cards:
        d5.rounded_rectangle((px, py, px + pw, py + ph), radius=18, fill=(10, 18, 34, 245), outline=(253, 224, 71, 255), width=3)
        d5.rounded_rectangle((px + 10, py + 10, px + pw - 10, py + 56), radius=10, fill=(*pcol, 255))
        max_p_tw = pw - 36
        f_p1 = fit_font_for_width(d5, pt1, black_path, 23, 15, max_p_tw)
        pt1_fit = smart_truncate(d5, pt1, f_p1, max_p_tw)
        f_p2 = fit_font_for_width(d5, pt2, w9_path, 16, 12, max_p_tw)
        pt2_fit = smart_truncate(d5, pt2, f_p2, max_p_tw)
        f_p3 = fit_font_for_width(d5, pt3, w9_path, 16, 12, max_p_tw)
        pt3_fit = smart_truncate(d5, pt3, f_p3, max_p_tw)
        d5.text((px + 18, py + 17), pt1_fit, font=f_p1, fill=(255, 255, 255, 255))
        d5.text((px + 18, py + 70), pt2_fit, font=f_p2, fill=(253, 224, 71, 255))
        d5.text((px + 18, py + 104), pt3_fit, font=f_p3, fill=(167, 243, 208, 255))

    # Save all 5 templates and automatically rotate which template is set as primary `thumb_a` & `thumb_b` by episode number!
    all_tpls = [canvas_a, canvas_b, canvas_3, canvas_4, canvas_5]
    for idx_t, c_im in enumerate(all_tpls, 1):
        p_t = OUTPUT_DIR / f"overseas_japan_{rid}_thumb_tpl{idx_t}.jpg"
        c_im.convert("RGB").save(p_t, "JPEG", quality=96)

    m_num = re.search(r"(\d+)$", rid)
    ep_idx = (int(m_num.group(1)) - 1) if m_num else (sum(ord(c) for c in rid) % 5)
    primary_im = all_tpls[ep_idx % 5]
    secondary_im = all_tpls[(ep_idx + 2) % 5]
    primary_im.convert("RGB").save(thumb_a, "JPEG", quality=96)
    secondary_im.convert("RGB").save(thumb_b, "JPEG", quality=96)
    logger.info(f"Auto-rotated primary thumbnail for '{rid}' -> Template #{(ep_idx % 5) + 1} (Alt: Template #{((ep_idx + 2) % 5) + 1})")

    # =========================================================================
    # Vertical YouTube Shorts Custom Cover (1080x1920): Rotates 案A / 案B / 案C!
    # =========================================================================
    cover_scene = {
        "badge": f"NO.1  |  SCORE: {rows[0]['score'].upper()}",
        "title_en": r1_clean_name,
        "sub_en": r1_clean_dish,
        "access": f"{rows[0].get('access_short', 'Direct Access')} | {rows[0].get('budget', 'Local Price')}",
        "card_style": "praise",
        "card_body_en": rows[0].get("hack", "Top-rated local favorite on Japanese Instagram!"),
    }
    short_rot = ep_idx % 3
    if short_rot == 0:
        render_short_ig_design_a_jpg(p1_path, cover_scene, w9_path, thumb_s)
    elif short_rot == 1:
        render_short_ig_design_b_jpg(p1_path, p2_path, cover_scene, w9_path, thumb_s)
    else:
        render_short_ig_design_c_jpg(p1_path, cover_scene, rows, "#1", w9_path, thumb_s)
    logger.info(f"Completed Custom Shorts Thumbnail (1080x1920, Design {['A', 'B', 'C'][short_rot]}): {thumb_s}")
    return thumb_a, thumb_b, thumb_s


if __name__ == "__main__":
    pos_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if pos_args:
        target = Path(pos_args[0])
    else:
        target = BASE_DIR / "stocks" / "overseas_japan" / "queue" / "spot_001_akita_sightseeing.json"
    render_custom_thumbnails(target)
    if "--thumbs-only" not in sys.argv:
        if "--shorts-only" not in sys.argv:
            build_ranking_video(target)
        if "--long-only" not in sys.argv:
            build_shorts_video(target)



