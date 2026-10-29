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
    """Remove any Japanese/CJK characters and empty parentheses so all rendered slides stay 100% English."""
    cleaned = re.sub(r"[\u3000-\u9fff\uff00-\uffef]+", "", text or "")
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

    # Otherwise drop whole words from the end
    words = s.split(" ")
    while len(words) > 1:
        words.pop()
        candidate = " ".join(words).rstrip(",;:|—-")
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
        ("RAPID PREVIEW  |  RANK #10", (30, 58, 138, 245)),
        ("RAPID PREVIEW  |  RANK #7", (2, 132, 199, 245)),
        ("TOP 5 HIDDEN GEM  |  RANK #5", (16, 185, 129, 245)),
        ("BRONZE MEDAL  |  RANK #3", (220, 38, 38, 248)),
        ("RUNNER-UP  |  RANK #2", (220, 38, 38, 248)),
        ("WAIT UNTIL YOU SEE #1!", (217, 119, 6, 252)),
    ]

    f_pill = ImageFont.truetype(font_path, 21)
    f_sub = ImageFont.truetype(font_path, 20)

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

        pill_txt, pill_col = flash_labels[i % len(flash_labels)]
        rank_str = row.get("rank", f"#{10 - i}")
        score_str = row.get("score", "95/100pt")
        name_en = strip_cjk(row.get("name_en", "Secret Local Spot"))
        dish_en = strip_cjk(row.get("dish", "Voted by Japanese Locals"))
        acc_en = strip_cjk(row.get("access_short", row.get("budget", "Direct Train Access")))

        # Zoom-safe centered lower card (bx0=96..W-96, by0=362..482 so 1.06x zoom never touches HUD)
        bx0, by0, bx1, by1 = 96, 362, W - 96, 482
        max_card_tw = (bx1 - bx0) - 48
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=16, fill=(8, 12, 24, 228), outline=(253, 224, 71, 245), width=3)

        tb_p = draw.textbbox((0, 0), pill_txt, font=f_pill)
        pw = (tb_p[2] - tb_p[0]) + 34
        draw.rounded_rectangle((bx0 + 16, by0 - 20, bx0 + 16 + pw, by0 + 20), radius=10, fill=pill_col, outline=(255, 255, 255, 245), width=2)
        draw.text((bx0 + 33, by0 - 11), pill_txt, font=f_pill, fill=(255, 255, 255, 255))

        prog_txt = f"HIGHLIGHT {i + 1}/{len(pick_indices)}  >>  COUNTDOWN"
        tb_pr = draw.textbbox((0, 0), prog_txt, font=f_sub)
        draw.text((bx1 - (tb_pr[2] - tb_pr[0]) - 22, by0 + 8), prog_txt, font=f_sub, fill=(125, 211, 252, 255))

        if i == len(pick_indices) - 1:
            headline = f"#1 SPOT SCORED {score_str.upper()} — CAN YOU GUESS WHICH ONE?"
            subline = f"Hint: {dish_en}  |  Access: {acc_en}"
        else:
            headline = f"{rank_str}  {name_en}  ({score_str})"
            subline = f"{dish_en}  |  Access: {acc_en}"

        f_spot_fit = fit_font_for_width(draw, headline, font_path, 32, 22, max_card_tw)
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

            acc_short = row.get("access_short", row.get("budget", ""))
            while len(acc_short) > 6:
                tb_a = draw.textbbox((0, 0), acc_short, font=f_hack)
                if (tb_a[2] - tb_a[0]) <= badge_w + 2:
                    break
                acc_short = acc_short[:-2] + "…"
            draw.text((rx + 2, y0 + 42), acc_short, font=f_hack, fill=(125, 211, 252))

            tx = rx + badge_w + 10
            max_tw = x1 - tx - 8

            def fit_line(txt: str, fnt: ImageFont.FreeTypeFont) -> str:
                s = txt
                while len(s) > 6:
                    tb_s = draw.textbbox((0, 0), s, font=fnt)
                    if (tb_s[2] - tb_s[0]) <= max_tw:
                        return s
                    s = s[:-2] + "…"
                return s

            title_str = fit_line(row["name_en"], f_title)
            dish_str = fit_line(row["dish"], f_sub)
            hack_str = fit_line(f"TIP: {row['hack']}", f_hack)

            draw.text((tx, y0 + 6), title_str, font=f_title, fill=(255, 255, 255))
            draw.text((tx, y0 + 30), dish_str, font=f_sub, fill=(253, 224, 71))
            draw.text((tx, y0 + 50), hack_str, font=f_hack, fill=(167, 243, 208))
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

    # Top-right Area & Budget Pill on Row 1
    info_right = f"{seg['area']}  |  {seg['budget']}"
    tb_r = draw.textbbox((0, 0), info_right, font=f_tag)
    rw = tb_r[2] - tb_r[0]
    right_box_x0 = W - rw - 44

    draw.rectangle(
        [(right_box_x0, 12), (W - 20, 46)],
        fill=(30, 41, 59, 245),
        outline=(148, 163, 184, 210),
        width=2,
    )
    draw.text((W - rw - 32, 19), info_right, font=f_tag, fill=(253, 224, 71, 255))

    # Main English Place Title on Row 2 (Large 26px bold with dark stroke)
    title_en = strip_cjk(seg["place_en"].strip()).replace("What You Get in This 9-Min Guide", "TOP 10 COUNTDOWN PREVIEW — WATCH UNTIL #1!")
    f_title_fit = fit_font_for_width(draw, title_en, font_path, 26, 18, W - 48)
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

    # 2. Optional Real Local Review Card (when seg_type == "review" — 100% English, Large 20px font)
    if seg.get("seg_type") == "review" and seg.get("review_praise_en"):
        f_rhead = ImageFont.truetype(font_path, 17)
        card_x0, card_x1 = 24, W - 24
        max_rw = (card_x1 - card_x0) - 32

        c1_y0, c1_y1 = 336, 430
        lbl1 = "WHAT JAPANESE LOCALS LOVE (PRAISE)"
        tb_l1 = draw.textbbox((0, 0), lbl1, font=f_rhead)
        l1_w = (tb_l1[2] - tb_l1[0]) + 28
        praise_txt = strip_cjk(seg["review_praise_en"])
        f_ren1 = fit_font_for_width(draw, praise_txt, font_path, 20, 14, max_rw)
        draw.rectangle([(card_x0, c1_y0), (card_x1, c1_y1)], fill=(12, 19, 34, 238), outline=(16, 185, 129, 250), width=2)
        draw.rectangle([(card_x0, c1_y0), (card_x0 + l1_w, c1_y0 + 32)], fill=(16, 185, 129, 250))
        draw.text((card_x0 + 14, c1_y0 + 7), lbl1, font=f_rhead, fill=(255, 255, 255, 255))
        draw.text((card_x0 + 16, c1_y0 + 46), praise_txt, font=f_ren1, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 230))

        c2_y0, c2_y1 = 440, 534
        lbl2 = "LOCAL WARNING & INSIDER HACK"
        tb_l2 = draw.textbbox((0, 0), lbl2, font=f_rhead)
        l2_w = (tb_l2[2] - tb_l2[0]) + 28
        warn_txt = strip_cjk(seg["review_warn_en"])
        f_ren2 = fit_font_for_width(draw, warn_txt, font_path, 20, 14, max_rw)
        draw.rectangle([(card_x0, c2_y0), (card_x1, c2_y1)], fill=(12, 19, 34, 238), outline=(245, 158, 11, 250), width=2)
        draw.rectangle([(card_x0, c2_y0), (card_x0 + l2_w, c2_y0 + 32)], fill=(217, 119, 6, 250))
        draw.text((card_x0 + 14, c2_y0 + 7), lbl2, font=f_rhead, fill=(255, 255, 255, 255))
        draw.text((card_x0 + 16, c2_y0 + 46), warn_txt, font=f_ren2, fill=(253, 224, 71, 255), stroke_width=2, stroke_fill=(0, 0, 0, 230))

    # 3. Bottom Insider Tip Bar + Subtitle Bar
    sub_bar_h = 132
    sub_y0 = H - sub_bar_h
    tip_bar_h = 44
    tip_y0 = sub_y0 - tip_bar_h

    sec_label = "INSIDER TIP"
    tb_sec = draw.textbbox((0, 0), sec_label, font=f_tag)
    sec_w = (tb_sec[2] - tb_sec[0]) + 36
    tip_txt = strip_cjk(seg["insider_tip"])
    f_tip_fit = fit_font_for_width(draw, tip_txt, font_path, 19, 14, W - sec_w - 32)
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
                    f"[bg][{n_fl}:v]overlay=0:0,scale=1920:1080:flags=lanczos,unsharp=3:3:0.6:3:3:0.0,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
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
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                    "-shortest", str(seg_mp4),
                ])
            else:
                if seg_type == "summary" or (seg_type == "area_guide" and "2/2" in badge):
                    filter_complex = (
                        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={dur},setpts=PTS-STARTPTS,fps={FPS},setsar=1[bg];"
                        f"[bg][2:v]overlay=0:0,scale=1920:1080:flags=lanczos,unsharp=3:3:0.6:3:3:0.0,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
                    )
                else:
                    zp_a = f"zoompan=z='min(zoom+0.0018,1.16)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={half_frames}:s={W}x{H}:fps={FPS}"
                    zp_b = f"zoompan=z='1.14':x='(iw-iw/zoom)*(on/{half_frames})':y='ih/2-(ih/zoom/2)':d={half_frames}:s={W}x{H}:fps={FPS}"
                    filter_complex = (
                        f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},{zp_a},trim=duration={half_dur},setpts=PTS-STARTPTS,setsar=1[va];"
                        f"[1:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},{zp_b},trim=duration={dur - half_dur + 0.1},setpts=PTS-STARTPTS,setsar=1[vb];"
                        f"[va][vb]concat=n=2:v=1:a=0[bg];"
                        f"[bg][2:v]overlay=0:0,scale=1920:1080:flags=lanczos,unsharp=3:3:0.6:3:3:0.0,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
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
                    "-crf",
                    "17",
                    "-maxrate",
                    "8M",
                    "-bufsize",
                    "16M",
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
    Render Cut 1A of the Opening Hook (y=384..1418) — 100% English, High-Contrast Large Fonts:
    Shows 'WHAT YOU GET IN THIS 60s VIDEO' with 3 large Value Promise Cards + real visitor thumbnails!
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

    # Header Banner inside Content Board (y=384..476)
    draw.rounded_rectangle((36, 384, SW - 36, 474), radius=20, fill=(185, 28, 28, 248), outline=(253, 224, 71, 255), width=3)
    f_hb_en = ImageFont.truetype(font_path, 30)
    f_hb_sub = ImageFont.truetype(font_path, 21)
    hb1 = "WHAT YOU GET IN THIS 60s GUIDE"
    hb2 = "500K JAPANESE IG POSTS × LOCAL REVIEWS — ZERO TOURIST TRAPS"
    tb1 = draw.textbbox((0, 0), hb1, font=f_hb_en)
    tb2 = draw.textbbox((0, 0), hb2, font=f_hb_sub)
    draw.text(((SW - (tb1[2] - tb1[0])) // 2, 394), hb1, font=f_hb_en, fill=(255, 255, 255, 255))
    draw.text(((SW - (tb2[2] - tb2[0])) // 2, 436), hb2, font=f_hb_sub, fill=(253, 224, 71, 255))

    # 3 Large Content Promise Cards (y=494..1418, each 292px tall) — 100% English
    promises = [
        {
            "badge": "CONTENT 01  |  REAL LOCAL RANKING",
            "badge_col": (16, 185, 129, 255),
            "border_col": (52, 211, 153, 245),
            "title_en": "500,000 Japanese IG Posts Analyzed",
            "sub_en": "Scored out of 100pt: IG Buzz (50pt) + Reviews (35pt)",
            "desc1": "Ranked by real Japanese travelers & local historians",
            "desc2": "Zero tourist traps — 100% authentic cultural landmarks!",
            "thumb": summary_rows[0]["thumb"] if len(summary_rows) > 0 else "",
            "thumb_tag": "#1 SPOT",
        },
        {
            "badge": "CONTENT 02  |  EXACT ACCESS GUIDE",
            "badge_col": (2, 132, 199, 255),
            "border_col": (56, 189, 248, 245),
            "title_en": "Shinkansen & Local Station Times",
            "sub_en": "Direct Bullet Train Routes from Tokyo & Kyoto",
            "desc1": "Exact JR Shinkansen & local train travel minutes",
            "desc2": "Includes ticket combo hacks & best arrival times!",
            "thumb": summary_rows[1]["thumb"] if len(summary_rows) > 1 else "",
            "thumb_tag": "#2 SPOT",
        },
        {
            "badge": "CONTENT 03  |  LOCAL HACKS & LIST",
            "badge_col": (217, 119, 6, 255),
            "border_col": (253, 224, 71, 245),
            "title_en": "Honest Warnings + Full TOP 10 List",
            "sub_en": "Real Visitor Praise, Warnings & Pro Tips",
            "desc1": "Honest local warnings you must know before visiting!",
            "desc2": "Plus a screenshot-ready TOP 10 Cheat-Sheet at the end!",
            "thumb": summary_rows[2]["thumb"] if len(summary_rows) > 2 else "",
            "thumb_tag": "#3 SPOT",
        },
    ]

    f_tag = ImageFont.truetype(font_path, 20)
    f_ten = ImageFont.truetype(font_path, 28)
    f_sub = ImageFont.truetype(font_path, 22)
    f_dsc = ImageFont.truetype(font_path, 20)

    for idx, pr in enumerate(promises):
        cy0 = 494 + idx * 310
        cy1 = cy0 + 292
        draw.rounded_rectangle((36, cy0, SW - 36, cy1), radius=22, fill=(12, 20, 36, 242), outline=pr["border_col"], width=3)

        tw, th_h = 236, cy1 - cy0 - 28
        tx0, ty0 = 50, cy0 + 14
        p_path = cache_dir / pr["thumb"]
        if pr["thumb"] and p_path.exists():
            tile = fit_crop(Image.open(p_path), tw, th_h)
            mask = Image.new("L", (tw, th_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw, th_h), radius=16, fill=255)
            canvas.paste(tile.convert("RGBA"), (tx0, ty0), mask)
            draw.rounded_rectangle((tx0, ty0, tx0 + tw, ty0 + th_h), radius=16, fill=None, outline=(255, 255, 255, 220), width=2)
            draw.rounded_rectangle((tx0 + 10, ty0 + 10, tx0 + 126, ty0 + 46), radius=8, fill=(10, 14, 24, 230), outline=pr["border_col"], width=1)
            draw.text((tx0 + 22, ty0 + 18), pr["thumb_tag"], font=f_dsc, fill=(253, 224, 71, 255))

        rx = tx0 + tw + 24
        tb_b = draw.textbbox((0, 0), pr["badge"], font=f_tag)
        bw = (tb_b[2] - tb_b[0]) + 32
        draw.rounded_rectangle((rx, cy0 + 18, rx + bw, cy0 + 62), radius=10, fill=pr["badge_col"])
        draw.text((rx + 16, cy0 + 29), pr["badge"], font=f_tag, fill=(255, 255, 255, 255))

        draw.text((rx, cy0 + 78), pr["title_en"], font=f_ten, fill=(255, 255, 255, 255))
        draw.text((rx, cy0 + 122), pr["sub_en"], font=f_sub, fill=(253, 224, 71, 255))
        draw.text((rx, cy0 + 174), pr["desc1"], font=f_dsc, fill=(224, 242, 254, 255))
        draw.text((rx, cy0 + 214), pr["desc2"], font=f_dsc, fill=(167, 243, 208, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_hook_jpg(
    ranking_id: str,
    area_guide: Dict[str, Any],
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg: Path,
) -> None:
    """Render a sleek mobile-first 1080x1920 Hook screen over a Gaussian-blurred ambient backdrop (100% English)."""
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

    # 1. Center Japan Map + Shinkansen Card (x=36..1044, y=384..940)
    mx0, my0, mx1, my1 = 36, 384, SW - 36, 940
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
    pad_x0, pad_y0, pad_x1, pad_y1 = mx0 + 28, my0 + 78, mx0 + 518, my1 - 24

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

    f_big = ImageFont.truetype(font_path, 34)
    f_lbl = ImageFont.truetype(font_path, 20)
    f_sub = ImageFont.truetype(font_path, 17)
    sx0, sx1 = mx0 + 538, mx1 - 22

    top1_acc = smart_truncate(draw, summary_rows[0].get("access_short", "Direct Shinkansen").upper(), f_lbl, sx1 - sx0 - 36) if summary_rows else "DIRECT SHINKANSEN"
    top2_acc = smart_truncate(draw, summary_rows[1].get("access_short", "JR Express Train").upper(), f_lbl, sx1 - sx0 - 36) if len(summary_rows) > 1 else "JR EXPRESS TRAIN"

    stat_boxes = [
        ("TOP #1", top1_acc, "Easy Day Trip via JR Pass", (16, 185, 129, 245)),
        ("TOP #2", top2_acc, "100% Authentic Local Ranking", (217, 119, 6, 245)),
    ]
    for idx, (big_t, l1, l2, col) in enumerate(stat_boxes):
        by0 = my0 + 82 + idx * 224
        by1 = by0 + 204
        draw.rounded_rectangle((sx0, by0, sx1, by1), radius=14, fill=(15, 23, 42, 240), outline=col, width=2)
        draw.rounded_rectangle((sx0 + 16, by0 + 16, sx1 - 16, by0 + 88), radius=10, fill=col)
        tb = draw.textbbox((0, 0), big_t, font=f_big)
        draw.text((sx0 + ((sx1 - sx0) - (tb[2] - tb[0])) // 2, by0 + 30), big_t, font=f_big, fill=(255, 255, 255, 255))
        draw.text((sx0 + 20, by0 + 108), l1, font=f_lbl, fill=(253, 224, 71, 255))
        draw.text((sx0 + 20, by0 + 146), l2, font=f_sub, fill=(226, 232, 240, 255))

    # 2. Top 3 Visual Cards (x=36..1044, y=966..1418) — 100% English
    gy0, gy1 = 966, 1418
    col_w = (SW - 72 - 24) // 3
    f_rk = ImageFont.truetype(font_path, 23)
    f_acc_sm = ImageFont.truetype(font_path, 16)

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

        draw.rounded_rectangle((cx0 + 4, gy1 - 84, cx1 - 4, gy1 - 4), radius=12, fill=(8, 12, 22, 238))
        raw_nm = strip_cjk(row["name_en"].split("(")[0].strip())
        f_nm_fit = fit_font_for_width(draw, raw_nm, font_path, 21, 15, col_w - 20)
        clean_nm = smart_truncate(draw, raw_nm, f_nm_fit, col_w - 20)
        tb_n = draw.textbbox((0, 0), clean_nm, font=f_nm_fit)
        draw.text((cx0 + ((cx1 - cx0) - (tb_n[2] - tb_n[0])) // 2, gy1 - 72), clean_nm, font=f_nm_fit, fill=(253, 224, 71, 255))

        acc_short = smart_truncate(draw, row.get("access_short", row.get("budget", "")), f_acc_sm, col_w - 20)
        tb_j = draw.textbbox((0, 0), acc_short, font=f_acc_sm)
        draw.text((cx0 + ((cx1 - cx0) - (tb_j[2] - tb_j[0])) // 2, gy1 - 36), acc_short, font=f_acc_sm, fill=(255, 255, 255, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_outro_jpg(
    ranking_id: str,
    summary_rows: List[Dict[str, Any]],
    font_path: str,
    out_jpg: Path,
) -> None:
    """
    Render a mobile-optimized TOP 5 Podium Cards + #6-#10 Compact Badges screen (100% English)
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

    y0_base = 384
    card_h = 156
    gap = 10
    for i, row in enumerate(summary_rows[:5]):
        ry0 = y0_base + i * (card_h + gap)
        ry1 = ry0 + card_h
        is_no1 = row["rank"] == "#1"
        is_top3 = row["rank"] in ("#1", "#2", "#3")
        border_c = (253, 224, 71, 255) if is_no1 else ((248, 113, 113, 235) if is_top3 else (96, 165, 250, 220))
        draw.rounded_rectangle((36, ry0, SW - 36, ry1), radius=18, fill=(12, 20, 36, 242), outline=border_c, width=3)

        p_path = cache_dir / row["thumb"]
        tw, th_h = 186, card_h - 16
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
        draw.rounded_rectangle((tx, ry0 + 12, tx + badge_w, ry0 + 54), radius=10, fill=b_col)
        draw.text((tx + (badge_w - (tb_r[2] - tb_r[0])) // 2, ry0 + 21), r_txt, font=f_rk, fill=(255, 255, 255, 255))

        max_title_w = (SW - 52) - (tx + badge_w + 14)
        full_title = smart_truncate(draw, row["name_en"], f_title, max_title_w)
        clean_dish = strip_cjk(row["dish"].split("(")[0].strip())
        clean_hack = strip_cjk(row["hack"].strip())
        max_line_w = (SW - 52) - tx
        acc_line = smart_truncate(draw, f"ACCESS: {row['budget']}  |  {clean_dish}", f_sub, max_line_w)
        hack_line = smart_truncate(draw, f"HACK: {clean_hack}", f_sub, max_line_w)
        draw.text((tx + badge_w + 14, ry0 + 18), full_title, font=f_title, fill=(255, 255, 255, 255))
        draw.text((tx, ry0 + 68), acc_line, font=f_sub, fill=(125, 211, 252, 255))
        draw.text((tx, ry0 + 106), hack_line, font=f_sub, fill=(167, 243, 208, 255))

    if len(summary_rows) >= 10:
        by0, by1 = 1226, 1418
        draw.rounded_rectangle((36, by0, SW - 36, by1), radius=18, fill=(15, 23, 42, 242), outline=(148, 163, 184, 210), width=2)
        draw.text((58, by0 + 14), "RANKS #6 TO #10 (IN FULL 9-MIN VIDEO):", font=f_sub, fill=(253, 224, 71, 255))
        for j, r_row in enumerate(summary_rows[5:10]):
            col_x = 58 if j < 3 else 548
            row_y = by0 + 54 + (j % 3) * 42
            txt = smart_truncate(draw, f"{r_row['rank']} ({r_row['score']}): {r_row['name_en']}", f_mini, 470)
            draw.text((col_x, row_y), txt, font=f_mini, fill=(241, 245, 249, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_cinema_frame_jpg(
    raw_photo_path: Path,
    photo_label: str,
    font_path: str,
    out_jpg: Path,
) -> None:
    """
    Composite a 4:3 visitor photograph inside a razor-sharp centered Cinema Window (1008x756)
    over a dark Gaussian-blurred 1080x1920 ambient background!
    """
    from PIL import ImageFilter, ImageChops

    raw_im = Image.open(raw_photo_path).convert("RGB")
    white_bg = Image.new("RGB", raw_im.size, (250, 250, 250))
    diff = ImageChops.difference(raw_im, white_bg).convert("L")
    diff = diff.point(lambda p: 255 if p > 18 else 0)
    bbox = diff.getbbox()
    if bbox and (bbox[2] - bbox[0]) > raw_im.width * 0.6 and (bbox[3] - bbox[1]) > raw_im.height * 0.5:
        raw_im = raw_im.crop(bbox)

    bg = fit_crop(raw_im, SW, SH).filter(ImageFilter.GaussianBlur(radius=36))
    bg = ImageEnhance.Brightness(bg).enhance(0.32)
    canvas = bg.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    fx0, fy0, fx1, fy1 = 36, 384, SW - 36, 1140
    fw, fh = fx1 - fx0, fy1 - fy0
    sharp_photo = fit_crop(raw_im, fw, fh)
    sharp_photo = ImageEnhance.Contrast(sharp_photo).enhance(1.06)

    mask = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fw, fh), radius=24, fill=255)
    canvas.paste(sharp_photo.convert("RGBA"), (fx0, fy0), mask)
    draw.rounded_rectangle((fx0, fy0, fx1, fy1), radius=24, fill=None, outline=(255, 255, 255, 240), width=4)

    f_tag = ImageFont.truetype(font_path, 20)
    clean_lbl = smart_truncate(draw, photo_label, f_tag, fw - 72)
    tb_t = draw.textbbox((0, 0), clean_lbl, font=f_tag)
    tw = (tb_t[2] - tb_t[0]) + 34
    draw.rounded_rectangle((fx0 + 18, fy0 + 18, fx0 + 18 + tw, fy0 + 62), radius=12, fill=(10, 14, 24, 225), outline=(253, 224, 71, 235), width=2)
    draw.text((fx0 + 35, fy0 + 29), clean_lbl, font=f_tag, fill=(253, 224, 71, 255))

    canvas.convert("RGB").save(out_jpg, "JPEG", quality=95)


def render_short_hud_png(
    scene: Dict[str, Any],
    font_path: str,
    out_png: Path,
) -> None:
    """
    Render the sleek mobile-first floating HUD (100% English, High-Contrast Large Fonts, Zero Mid-Word Truncation).
    """
    overlay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    f_pill = ImageFont.truetype(font_path, 25)
    f_rhead = ImageFont.truetype(font_path, 22)
    f_ren = ImageFont.truetype(font_path, 26)

    # 1. Floating Centered Rank Pill (y=118..178)
    pill_txt = strip_cjk(scene["badge"])
    is_gold = "NO.1" in pill_txt or "#1 " in pill_txt
    p_col = (217, 119, 6, 250) if is_gold else (220, 38, 38, 250)
    tb_p = draw.textbbox((0, 0), pill_txt, font=f_pill)
    pw = (tb_p[2] - tb_p[0]) + 56
    px0 = (SW - pw) // 2
    draw.rounded_rectangle((px0, 118, px0 + pw, 178), radius=30, fill=p_col, outline=(254, 240, 138, 255), width=3)
    draw.text((px0 + 28, 134), pill_txt, font=f_pill, fill=(255, 255, 255, 255))

    # 2. Bold Centered English Title + English Sub-line (y=194..290)
    t_en = strip_cjk(scene["title_en"])
    f_title = fit_font_for_width(draw, t_en, font_path, 42, 26, SW - 56)
    t_en = smart_truncate(draw, t_en, f_title, SW - 56)
    tb_t = draw.textbbox((0, 0), t_en, font=f_title)
    draw.text(((SW - (tb_t[2] - tb_t[0])) // 2, 192), t_en, font=f_title, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255))

    t_sub = strip_cjk(scene.get("sub_en", ""))
    if t_sub:
        f_sub = fit_font_for_width(draw, t_sub, font_path, 24, 17, SW - 56)
        t_sub = smart_truncate(draw, t_sub, f_sub, SW - 56)
        tb_j = draw.textbbox((0, 0), t_sub, font=f_sub)
        draw.text(((SW - (tb_j[2] - tb_j[0])) // 2, 252), t_sub, font=f_sub, fill=(253, 224, 71, 255), stroke_width=3, stroke_fill=(0, 0, 0, 240))

    # 3. Floating Centered Access Pill (y=302..356)
    if scene.get("access"):
        acc_txt = strip_cjk(scene["access"].replace("🚄", "").split("|")[0].strip())
        f_acc = fit_font_for_width(draw, acc_txt, font_path, 22, 16, SW - 88)
        acc_txt = smart_truncate(draw, acc_txt, f_acc, SW - 88)
        tb_a = draw.textbbox((0, 0), acc_txt, font=f_acc)
        aw = (tb_a[2] - tb_a[0]) + 48
        ax0 = (SW - aw) // 2
        draw.rounded_rectangle((ax0, 302, ax0 + aw, 356), radius=26, fill=(8, 47, 73, 238), outline=(56, 189, 248, 235), width=2)
        draw.text((ax0 + 24, 316), acc_txt, font=f_acc, fill=(224, 242, 254, 255))

    # 4. Single Sleek Social Card below Cinema Frame (y=1168..1418) — 100% English
    if scene.get("card_title") and scene.get("card_body_en"):
        cx0, cy0, cx1, cy1 = 36, 1168, SW - 36, 1418
        is_warn = scene.get("card_style") == "warn"
        c_border = (245, 158, 11, 255) if is_warn else (16, 185, 129, 255)
        c_tag_bg = (217, 119, 6, 255) if is_warn else (16, 185, 129, 255)

        draw.rounded_rectangle((cx0, cy0, cx1, cy1), radius=20, fill=(12, 20, 36, 242), outline=c_border, width=3)
        ct_lbl = strip_cjk(scene["card_title"])
        tb_ct = draw.textbbox((0, 0), ct_lbl, font=f_rhead)
        ct_w = (tb_ct[2] - tb_ct[0]) + 36
        draw.rounded_rectangle((cx0 + 20, cy0 + 18, cx0 + 20 + ct_w, cy0 + 64), radius=10, fill=c_tag_bg)
        draw.text((cx0 + 38, cy0 + 29), ct_lbl, font=f_rhead, fill=(255, 255, 255, 255))

        q_lines = wrap_text_lines(draw, strip_cjk(scene["card_body_en"]), f_ren, cx1 - cx0 - 56)
        for li, ql in enumerate(q_lines[:3]):
            draw.text((cx0 + 28, cy0 + 82 + li * 42), ql, font=f_ren, fill=(255, 255, 255, 255))

    # 5. CapCut / Hormozi-Style Floating Outline Pop Captions (y=1460..1655)
    pop_lines = scene.get("pop_lines", [])
    for li, raw_pl in enumerate(pop_lines[:2]):
        pl = strip_cjk(raw_pl)
        f_pop = fit_font_for_width(draw, pl, font_path, 38, 22, SW - 56)
        pl = smart_truncate(draw, pl, f_pop, SW - 56)
        tb_l = draw.textbbox((0, 0), pl, font=f_pop)
        lx = (SW - (tb_l[2] - tb_l[0])) // 2
        ly = 1465 + li * 62
        col = (253, 224, 71, 255) if li == 1 else (255, 255, 255, 255)
        draw.text((lx + 3, ly + 4), pl, font=f_pop, fill=(0, 0, 0, 230), stroke_width=7, stroke_fill=(0, 0, 0, 230))
        draw.text((lx, ly), pl, font=f_pop, fill=col, stroke_width=5, stroke_fill=(0, 0, 0, 255))

    overlay.save(out_png, "PNG")


def build_shorts_video(script_path: Path) -> Path:
    """
    Build a high-retention 8-Scene CapCut-Style YouTube Short (1080x1920) — 100% Dynamic & English:
    Driven completely by the ranking JSON's Top 3 spots (sp3/rv3, sp2/rv2, sp1/rv1) and summary_rows!
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
    hook_title = strip_cjk(shorts_cfg.get("promise_catch", f"SKIP TOURIST TRAPS! {short_region} TOP 10"))
    hook_narration = shorts_cfg.get(
        "narration_hook",
        f"Stop going to crowded tourist traps! In the next 60 seconds, here are the Top 3 spots in {short_region} ranked from 500,000 Japanese Instagram posts and local reviews!",
    )

    short_scenes = [
        {
            "mode": "hook",
            "se_type": "area_chime",
            "badge": shorts_cfg.get("hook_badge", "95% OF FOREIGN TOURISTS MISS THIS!"),
            "title_en": hook_title,
            "sub_en": "500,000 Japanese IG Posts × Local Reviews",
            "access": "IN THIS VIDEO: 1. 100pt Ranking  2. Train Access  3. Local Hacks",
            "narration": hook_narration,
            "pop_lines": [hook_title, "Top 3 Ranked by Japanese Locals!"],
        },
        {
            "mode": "cinema",
            "se_type": "top3_hit",
            "badge": f"NO.3  |  SCORE: {r3_row['score'].upper()}",
            "title_en": r3_row["name_en"].split("(")[0].strip(),
            "sub_en": r3_row["dish"].split("(")[0].strip(),
            "access": f"ACCESS: {sp3.get('access_info', r3_row['budget'])}",
            "photos": [sp3["photos"][0], sp3["photos"][1]],
            "photo_tags": ["HIGH-RES PHOTO (1/4)", "HIGH-RES PHOTO (2/4)"],
            "card_style": "praise",
            "card_title": "LOCAL PRAISE & HIGHLIGHT",
            "card_body_en": rv3.get("review_praise_en", sp3["insider_tip"]),
            "narration": sp3["narration"],
            "pop_lines": [f"#3 {r3_row['name_en'].split('(')[0].strip().upper()} ({r3_row['score']})", r3_row["dish"].split("(")[0].strip()],
        },
        {
            "mode": "cinema",
            "se_type": "review_pop",
            "badge": "NO.3  |  INSIDER HACK",
            "title_en": r3_row["name_en"].split("(")[0].strip(),
            "sub_en": f"PRO TIP: {r3_row['hack']}",
            "access": f"TIP: {sp3.get('insider_tip', r3_row['hack'])}",
            "photos": [rv3["photos"][0], rv3["photos"][1]],
            "photo_tags": ["HIGH-RES PHOTO (3/4)", "HIGH-RES PHOTO (4/4)"],
            "card_style": "warn",
            "card_title": "LOCAL HACK & WARNING",
            "card_body_en": rv3.get("review_warn_en", r3_row["hack"]),
            "narration": rv3["narration"],
            "pop_lines": ["LOCAL INSIDER WARNING!", r3_row["hack"]],
        },
        {
            "mode": "cinema",
            "se_type": "top3_hit",
            "badge": f"NO.2  |  SCORE: {r2_row['score'].upper()}",
            "title_en": r2_row["name_en"].split("(")[0].strip(),
            "sub_en": r2_row["dish"].split("(")[0].strip(),
            "access": f"ACCESS: {sp2.get('access_info', r2_row['budget'])}",
            "photos": [sp2["photos"][0], sp2["photos"][1]],
            "photo_tags": ["HIGH-RES PHOTO (1/4)", "HIGH-RES PHOTO (2/4)"],
            "card_style": "praise",
            "card_title": "LOCAL PRAISE & HIGHLIGHT",
            "card_body_en": rv2.get("review_praise_en", sp2["insider_tip"]),
            "narration": sp2["narration"],
            "pop_lines": [f"#2 {r2_row['name_en'].split('(')[0].strip().upper()} ({r2_row['score']})", r2_row["dish"].split("(")[0].strip()],
        },
        {
            "mode": "cinema",
            "se_type": "review_pop",
            "badge": "NO.2  |  INSIDER HACK",
            "title_en": r2_row["name_en"].split("(")[0].strip(),
            "sub_en": f"PRO TIP: {r2_row['hack']}",
            "access": f"TIP: {sp2.get('insider_tip', r2_row['hack'])}",
            "photos": [rv2["photos"][0], rv2["photos"][1]],
            "photo_tags": ["HIGH-RES PHOTO (3/4)", "HIGH-RES PHOTO (4/4)"],
            "card_style": "warn",
            "card_title": "LOCAL HACK & WARNING",
            "card_body_en": rv2.get("review_warn_en", r2_row["hack"]),
            "narration": rv2["narration"],
            "pop_lines": ["LOCAL INSIDER WARNING!", r2_row["hack"]],
        },
        {
            "mode": "cinema",
            "se_type": "top3_hit",
            "badge": f"NO.1  |  SCORE: {r1_row['score'].upper()}",
            "title_en": r1_row["name_en"].split("(")[0].strip(),
            "sub_en": r1_row["dish"].split("(")[0].strip(),
            "access": f"ACCESS: {sp1.get('access_info', r1_row['budget'])}",
            "photos": [sp1["photos"][0], sp1["photos"][1]],
            "photo_tags": ["HIGH-RES PHOTO (1/4)", "HIGH-RES PHOTO (2/4)"],
            "card_style": "praise",
            "card_title": "LOCAL PRAISE & HIGHLIGHT",
            "card_body_en": rv1.get("review_praise_en", sp1["insider_tip"]),
            "narration": sp1["narration"],
            "pop_lines": [f"#1 {r1_row['name_en'].split('(')[0].strip().upper()} ({r1_row['score']})", r1_row["dish"].split("(")[0].strip()],
        },
        {
            "mode": "cinema",
            "se_type": "review_pop",
            "badge": "NO.1  |  LOCAL RULE & HACK",
            "title_en": r1_row["name_en"].split("(")[0].strip(),
            "sub_en": f"PRO TIP: {r1_row['hack']}",
            "access": f"TIP: {sp1.get('insider_tip', r1_row['hack'])}",
            "photos": [rv1["photos"][0], rv1["photos"][1]],
            "photo_tags": ["HIGH-RES PHOTO (3/4)", "HIGH-RES PHOTO (4/4)"],
            "card_style": "warn",
            "card_title": "LOCAL HACK & WARNING",
            "card_body_en": rv1.get("review_warn_en", r1_row["hack"]),
            "narration": rv1["narration"],
            "pop_lines": ["MUST-KNOW LOCAL RULE!", r1_row["hack"]],
        },
        {
            "mode": "outro",
            "se_type": "area_chime",
            "badge": "FULL TOP 10 CHEAT-SHEET",
            "title_en": "Screenshot This TOP 10 List!",
            "sub_en": f"{prefecture} — Complete Guide",
            "access": "TAP RELATED VIDEO BELOW FOR FULL 9-MIN GUIDE!",
            "narration": shorts_cfg.get("narration_outro", "Screenshot this full Top 10 list right now, and tap the related video below for our full 9-minute insider guide!"),
            "pop_lines": ["PAUSE & SCREENSHOT THIS LIST!", "Tap Below for Full 9-Min Video!"],
        },
    ]

    with tempfile.TemporaryDirectory(prefix="yt_short_") as tmp_str:
        work_dir = Path(tmp_str)
        seg_videos: List[Path] = []
        seg_starts: List[float] = []
        cur_t = 0.0

        for idx, sc in enumerate(short_scenes):
            logger.info(f"Building Shorts Scene {idx + 1}/{len(short_scenes)}: {sc['badge']}")
            seg_starts.append(cur_t)

            tts_mp3 = work_dir / f"stts_{idx:02d}.mp3"
            comm = edge_tts.Communicate(text=sc["narration"], voice=voice, rate="+22%")
            asyncio.run(comm.save(str(tts_mp3)))

            seg_wav = work_dir / f"swav_{idx:02d}.wav"
            st_kind = "spot" if sc["se_type"] == "top3_hit" else ("review" if sc["se_type"] == "review_pop" else "spot")
            dur = build_segment_audio_with_se(tts_mp3, st_kind, sc["badge"], seg_wav)
            cur_t += dur

            p1 = work_dir / f"sp_{idx:02d}_a.jpg"
            p2 = work_dir / f"sp_{idx:02d}_b.jpg"
            short_flash: List[Path] = []
            if sc["mode"] == "hook":
                # Rapid 4-Cut Visual Flash for the first ~8s of Shorts (zero text-table screen!)
                pick_r = [4, 2, 1] if len(summary_rows) >= 5 else list(range(min(3, len(summary_rows))))
                for sfi, r_i in enumerate(pick_r):
                    sf_p = work_dir / f"shook_flash_{sfi}.jpg"
                    r_row = summary_rows[r_i]
                    render_short_cinema_frame_jpg(
                        cache_dir / r_row["thumb"],
                        f"RAPID PREVIEW: {r_row['rank']} {strip_cjk(r_row['name_en'])}",
                        font_path,
                        sf_p,
                    )
                    short_flash.append(sf_p)
                render_short_hook_jpg(ranking_id, area_guide, summary_rows, font_path, p2)
                short_flash.append(p2)
                shutil.copyfile(short_flash[0], p1)
            elif sc["mode"] == "outro":
                render_short_outro_jpg(ranking_id, summary_rows, font_path, p1)
                shutil.copyfile(p1, p2)
            else:
                render_short_cinema_frame_jpg(cache_dir / sc["photos"][0], sc["photo_tags"][0], font_path, p1)
                render_short_cinema_frame_jpg(cache_dir / sc["photos"][1], sc["photo_tags"][1], font_path, p2)

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
                fc_s.append(f"[bg][{n_sf}:v]overlay=0:0,unsharp=3:3:0.6:3:3:0.0,scale=in_range=pc:out_range=tv,format=yuv420p[vout]")
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
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                    "-shortest", str(seg_mp4),
                ])
                subprocess.run(s_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                if sc["mode"] == "outro":
                    filter_complex = (
                        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={dur},setpts=PTS-STARTPTS,fps={FPS},setsar=1[bg];"
                        f"[bg][2:v]overlay=0:0,unsharp=3:3:0.6:3:3:0.0,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
                    )
                else:
                    # Rapid 2-cut transition (Cut 1A -> Cut 1B for every Cinema scene!)
                    filter_complex = (
                        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={half_dur},setpts=PTS-STARTPTS,fps={FPS},setsar=1[va];"
                        f"[1:v]loop=loop=-1:size=1:start=0,trim=duration={dur - half_dur + 0.1},setpts=PTS-STARTPTS,fps={FPS},setsar=1[vb];"
                        f"[va][vb]concat=n=2:v=1:a=0[bg];"
                        f"[bg][2:v]overlay=0:0,unsharp=3:3:0.6:3:3:0.0,scale=in_range=pc:out_range=tv,format=yuv420p[vout]"
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
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
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
        f_tt = ImageFont.truetype(w9_path, 18)
        tb_r = d.textbbox((0, 0), rank_txt, font=f_rk)
        rw = (tb_r[2] - tb_r[0]) + 22
        d.rounded_rectangle((14, 14, 14 + rw, 46), radius=8, fill=(*badge_col, 250), outline=(255, 255, 255, 255), width=2)
        d.text((25, 21), rank_txt, font=f_rk, fill=(255, 255, 255, 255))

        tb_t = d.textbbox((0, 0), title_txt, font=f_tt)
        d.text(((card_w - (tb_t[2] - tb_t[0])) // 2, card_h - 36), title_txt, font=f_tt, fill=(15, 23, 42, 255))

        rot = base.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True)
        sh = Image.new("RGBA", (rot.width + 32, rot.height + 32), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", rot.size, (0, 0, 0, 220)), (20, 22), rot.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(radius=10))
        sh.alpha_composite(rot, (12, 10))
        return sh

    p1_path = img_dir / rows[0]["thumb"]
    p2_path = img_dir / rows[1]["thumb"]
    p3_path = img_dir / rows[2]["thumb"]

    thumb_a = OUTPUT_DIR / f"overseas_japan_{rid}_thumb.jpg"
    thumb_b = OUTPUT_DIR / f"overseas_japan_{rid}_thumb_alt.jpg"
    thumb_s = OUTPUT_DIR / f"overseas_japan_{rid}_short_thumb.jpg"

    # Design A (1280x720)
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

    pol3 = make_polaroid_card(p3_path, 272, 194, f"#3  {rows[2]['score']}", rows[2]["name_en"][:20], (2, 132, 199), -5.5)
    pol2 = make_polaroid_card(p2_path, 272, 194, f"#2  {rows[1]['score']}", rows[1]["name_en"][:20], (220, 38, 38), 5.5)
    canvas_a.alpha_composite(pol3, (972, 252))
    canvas_a.alpha_composite(pol2, (966, 466))

    f_b1 = ImageFont.truetype(w9_path, 22)
    f_b2 = ImageFont.truetype(w9_path, 21)
    t_no1 = f"NO.1: {rows[0]['score'].upper()}"
    t_ph = rows[0]["dish"].split("(")[0].strip().upper()[:28] + "!"
    tb_n1 = d_a.textbbox((0, 0), t_no1, font=f_b1)
    tb_ph = d_a.textbbox((0, 0), t_ph, font=f_b2)
    w_n1 = (tb_n1[2] - tb_n1[0]) + 32
    w_ph = (tb_ph[2] - tb_ph[0]) + 34
    bx1 = 1260
    bx0 = bx1 - (w_n1 + w_ph + 20)
    d_a.rounded_rectangle((bx0, 20, bx1, 88), radius=16, fill=(12, 18, 32, 242), outline=(253, 224, 71, 255), width=3)
    d_a.rounded_rectangle((bx0 + 8, 28, bx0 + 8 + w_n1, 80), radius=10, fill=(217, 119, 6, 255))
    d_a.text((bx0 + 24, 42), t_no1, font=f_b1, fill=(255, 255, 255, 255))
    d_a.text((bx0 + 8 + w_n1 + 16, 43), t_ph, font=f_b2, fill=(253, 224, 71, 255))

    tc = data.get("thumb_config", {})
    hero_line1 = tc.get("hero_line1", "SKIP KYOTO!")
    hero_line2 = tc.get("hero_line2", "REAL JAPAN")
    banner_title = tc.get("banner_title", "AKITA TOP 10")
    banner_sub = tc.get("banner_sub", "HIDDEN GEMS VOTED BY LOCALS")
    map_header = tc.get("map_header", "WHERE IS AKITA?")
    map_pill = tc.get("map_pill", "3h 15m")
    map_line1 = tc.get("map_line1", "Direct Shinkansen")
    map_line2 = tc.get("map_line2", "from Tokyo Station!")
    map_footer = tc.get("map_footer", "95% LOCAL GUESTS")
    highlight_prefs = set(tc.get("highlight_prefs_ja", [target_pref_ja]))

    d_a.rounded_rectangle((28, 20, 512, 76), radius=12, fill=(220, 38, 38, 255), outline=(253, 224, 71, 255), width=3)
    f_rib = ImageFont.truetype(w9_path, 23)
    rib_txt = tc.get("ribbon_text", "500,000 JAPANESE IG POSTS")
    tb_rb = d_a.textbbox((0, 0), rib_txt, font=f_rib)
    d_a.text((28 + (484 - (tb_rb[2] - tb_rb[0])) // 2, 36), rib_txt, font=f_rib, fill=(255, 255, 255, 255))

    f_hero1 = ImageFont.truetype(black_path, 70 if len(hero_line1) > 11 else 74)
    f_hero2 = ImageFont.truetype(black_path, 68 if len(hero_line2) > 11 else 80)
    draw_pro_3d_text(canvas_a, (28, 88), hero_line1, f_hero1, (255, 255, 255), (218, 234, 255), stroke_w=9, depth=8)
    draw_pro_3d_text(canvas_a, (28, 178), hero_line2, f_hero2, (255, 248, 130), (245, 158, 11), stroke_w=10, depth=9)

    d_a.rounded_rectangle((28, 288, 502, 396), radius=18, fill=(14, 116, 144, 248), outline=(167, 243, 208, 255), width=3)
    f_ak = ImageFont.truetype(w9_path, 38 if len(banner_title) > 12 else 42)
    f_ak_sub = ImageFont.truetype(w9_path, 19 if len(banner_sub) > 27 else 20)
    d_a.text((48, 300), banner_title, font=f_ak, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 240))
    d_a.text((48, 355), banner_sub, font=f_ak_sub, fill=(253, 224, 71, 255), stroke_width=2, stroke_fill=(0, 0, 0, 230))

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
    f_m1 = ImageFont.truetype(w9_path, 18)
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

    f_c1 = ImageFont.truetype(w9_path, 22)
    f_c2 = ImageFont.truetype(w9_path, 18)
    tc1 = f"#1 {rows[0]['name_en'].upper()} ({rows[0]['score'].split('/')[0].strip()} PT)"
    tc2 = tc.get("no1_sub_badge", "IG Buzz: 50/50pt  |  Jalan: ★4.4")
    w_c = max(d_a.textbbox((0, 0), tc1, font=f_c1)[2], d_a.textbbox((0, 0), tc2, font=f_c2)[2]) + 36
    cx0_b = 466
    d_a.rounded_rectangle((cx0_b, 608, cx0_b + w_c, 696), radius=18, fill=(12, 18, 32, 242), outline=(245, 158, 11, 255), width=3)
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
    for y in range(H - 210, H):
        t = (y - (H - 210)) / 210
        a = int(242 * (t ** 1.3))
        od_b.line([(0, y), (W, y)], fill=(6, 10, 22, a))
    canvas_b.alpha_composite(ov_b)

    d_b = ImageDraw.Draw(canvas_b)
    d_b.line([(415, 0), (335, H)], fill=(15, 23, 42, 255), width=14)
    d_b.line([(415, 0), (335, H)], fill=(253, 224, 71, 255), width=5)
    d_b.line([(805, 0), (725, H)], fill=(15, 23, 42, 255), width=14)
    d_b.line([(805, 0), (725, H)], fill=(253, 224, 71, 255), width=5)

    f_sub_b = ImageFont.truetype(w9_path, 22)
    t_sub_b = "RANKED BY 500,000 JAPANESE IG POSTS & REVIEWS"
    tb_sb = d_b.textbbox((0, 0), t_sub_b, font=f_sub_b)
    w_sb = (tb_sb[2] - tb_sb[0]) + 40
    d_b.rounded_rectangle((28, 18, 28 + w_sb, 68), radius=10, fill=(220, 38, 38, 255), outline=(253, 224, 71, 255), width=3)
    d_b.text((48, 32), t_sub_b, font=f_sub_b, fill=(255, 255, 255, 255))

    f_b_main = ImageFont.truetype(black_path, 82 if len(banner_title) > 12 else 86)
    draw_pro_3d_text(canvas_b, (28, 72), banner_title, f_b_main, (255, 250, 145), (245, 158, 11), stroke_w=10, depth=9)

    f_vs = ImageFont.truetype(black_path, 28)
    for vx, vy in [(375, 360), (765, 360)]:
        d_b.ellipse((vx - 34, vy - 34, vx + 34, vy + 34), fill=(220, 38, 38, 255), outline=(253, 224, 71, 255), width=4)
        tb_v = d_b.textbbox((0, 0), "VS", font=f_vs)
        d_b.text((vx - (tb_v[2] - tb_v[0]) // 2, vy - 18), "VS", font=f_vs, fill=(255, 255, 255, 255))

    f_rk_b = ImageFont.truetype(black_path, 32)
    f_nm_b = ImageFont.truetype(w9_path, 24)
    f_tg_b = ImageFont.truetype(w9_path, 15)

    panels_b = [
        (18, 544, f"#3 ({rows[2]['score'].split('/')[0].strip()} PT)", rows[2]["name_en"].upper(), rows[2]["dish"].split("(")[0].strip().upper(), (2, 132, 199)),
        (362, 544, f"#2 ({rows[1]['score'].split('/')[0].strip()} PT)", rows[1]["name_en"].upper(), rows[1]["dish"].split("(")[0].strip().upper(), (234, 88, 12)),
        (754, 520, f"#1 WINNER ({rows[0]['score'].split('/')[0].strip()} PT)", rows[0]["name_en"].upper(), rows[0]["dish"].split("(")[0].strip().upper(), (220, 38, 38)),
    ]
    for px, py, rk_s, nm_en, tg_en, col in panels_b:
        tb_r = d_b.textbbox((0, 0), rk_s, font=f_rk_b)
        bw = (tb_r[2] - tb_r[0]) + 28
        d_b.rounded_rectangle((px, py, px + bw, py + 52), radius=12, fill=(*col, 255), outline=(253, 224, 71, 255), width=3)
        d_b.text((px + 14, py + 7), rk_s, font=f_rk_b, fill=(255, 255, 255, 255))
        d_b.text((px + 4, py + 62), tg_en, font=f_tg_b, fill=(253, 224, 71, 255), stroke_width=3, stroke_fill=(0, 0, 0, 245))
        d_b.text((px + 4, py + 88), nm_en, font=f_nm_b, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255))

    canvas_b.convert("RGB").save(thumb_b, "JPEG", quality=96)
    logger.info(f"Completed Custom Thumbnail B (1280x720): {thumb_b}")

    # =========================================================================
    # Design 3 (1280x720): "TOURIST TRAP vs REAL LOCAL #1" Split Comparison
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

    f_lb = ImageFont.truetype(w9_path, 24)
    f_ls = ImageFont.truetype(w9_path, 19)
    d3.text((28, 595), tc.get("trap_title", "OVERCROWDED TRAP"), font=f_lb, fill=(252, 165, 165, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    d3.text((28, 632), tc.get("trap_sub", "90% of Foreign Tourists Go Here"), font=f_ls, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))

    d3.rounded_rectangle((540, 180, 1020, 254), radius=14, fill=(5, 150, 105, 250), outline=(253, 224, 71, 255), width=4)
    rl_stamp = tc.get("real_stamp", "REAL LOCAL #1")
    tb_rl = d3.textbbox((0, 0), rl_stamp, font=f_st)
    d3.text((540 + (480 - (tb_rl[2] - tb_rl[0])) // 2, 194), rl_stamp, font=f_st, fill=(255, 255, 255, 255))

    f_top3 = ImageFont.truetype(black_path, 74)
    top3_txt = f"{hero_line1} {hero_line2}"[:22]
    draw_pro_3d_text(canvas_3, (28, 18), top3_txt, f_top3, (255, 250, 140), (245, 158, 11), stroke_w=10, depth=9)

    d3.rounded_rectangle((490, 568, 1252, 696), radius=20, fill=(10, 18, 34, 245), outline=(253, 224, 71, 255), width=4)
    f_w1 = ImageFont.truetype(black_path, 36)
    f_w2 = ImageFont.truetype(w9_path, 19)
    d3.text((514, 584), f"#1 {rows[0]['name_en'].upper()} ({rows[0]['score'].split('/')[0]} PT)", font=f_w1, fill=(253, 224, 71, 255))
    d3.text((514, 644), f"{rows[0]['dish'].split('(')[0].strip()}  |  500K IG Posts Analyzed", font=f_w2, fill=(167, 243, 208, 255))

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
    f_c_rk = ImageFont.truetype(black_path, 25)
    f_c_nm = ImageFont.truetype(w9_path, 22)
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
        rw = (tb_r[2] - tb_r[0]) + 24
        px, py = cx + 16, (cy + 16 if is_top else cy + ch - 62)
        d4.rounded_rectangle((px, py, px + rw, py + 44), radius=10, fill=(*bcol, 250), outline=(255, 255, 255, 255), width=2)
        d4.text((px + 12, py + 6), rk_t, font=f_c_rk, fill=(255, 255, 255, 255))
        d4.text((px + rw + 14, py + 10), row["name_en"].upper(), font=f_c_nm, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))

    ex0, ey0, ex1, ey1 = 235, 232, 1045, 488
    sh4 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh4).rounded_rectangle((ex0 - 12, ey0 - 8, ex1 + 12, ey1 + 16), radius=34, fill=(0, 0, 0, 235))
    canvas_4.alpha_composite(sh4.filter(ImageFilter.GaussianBlur(radius=14)))
    d4 = ImageDraw.Draw(canvas_4)
    d4.rounded_rectangle((ex0, ey0, ex1, ey1), radius=28, fill=(10, 16, 32, 248), outline=(253, 224, 71, 255), width=5)
    d4.rounded_rectangle((ex0 + 50, ey0 - 24, ex1 - 50, ey0 + 26), radius=18, fill=(220, 38, 38, 255), outline=(253, 224, 71, 255), width=3)
    f_em_sub = ImageFont.truetype(w9_path, 21)
    t_em = "RANKED BY 500,000 JAPANESE IG POSTS"
    tb_em = d4.textbbox((0, 0), t_em, font=f_em_sub)
    d4.text(((W - (tb_em[2] - tb_em[0])) // 2, ey0 - 10), t_em, font=f_em_sub, fill=(255, 255, 255, 255))
    f_em_main = ImageFont.truetype(black_path, 78)
    tb_bm = d4.textbbox((0, 0), banner_title, font=f_em_main)
    draw_pro_3d_text(canvas_4, ((W - (tb_bm[2] - tb_bm[0])) // 2, ey0 + 36), banner_title, f_em_main, (255, 250, 140), (245, 158, 11), stroke_w=10, depth=8)
    f_em_bot = ImageFont.truetype(w9_path, 20)
    t_eb = f"{hero_line1} {banner_sub}"
    tb_eb = d4.textbbox((0, 0), t_eb, font=f_em_bot)
    d4.text(((W - (tb_eb[2] - tb_eb[0])) // 2, ey1 - 48), t_eb, font=f_em_bot, fill=(167, 243, 208, 255))

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
    t_r5 = "500K JAPANESE IG POSTS × LOCAL REVIEW RANKING"
    tb_r5 = d5.textbbox((0, 0), t_r5, font=f_em_sub)
    rw5 = (tb_r5[2] - tb_r5[0]) + 60
    d5.rounded_rectangle(((W - rw5) // 2, 16, (W + rw5) // 2, 64), radius=24, fill=(220, 38, 38, 255), outline=(253, 224, 71, 255), width=3)
    d5.text(((W - (tb_r5[2] - tb_r5[0])) // 2, 29), t_r5, font=f_em_sub, fill=(255, 255, 255, 255))

    f_cin = ImageFont.truetype(black_path, 74)
    cin_title = f"{hero_line1} {hero_line2}"[:22]
    tb_cin = d5.textbbox((0, 0), cin_title, font=f_cin)
    draw_pro_3d_text(canvas_5, ((W - (tb_cin[2] - tb_cin[0])) // 2, 72), cin_title, f_cin, (255, 250, 145), (245, 158, 11), stroke_w=10, depth=8)

    pod_cards = [
        (28, 548, 390, 148, f"#1 {rows[0]['name_en'].upper()[:15]}", f"{rows[0]['score']}  |  {rows[0]['access_short']}", rows[0]["dish"].split("(")[0].strip()[:26], (220, 38, 38)),
        (445, 548, 390, 148, f"#2 {rows[1]['name_en'].upper()[:15]}", f"{rows[1]['score']}  |  {rows[1]['access_short']}", rows[1]["dish"].split("(")[0].strip()[:26], (234, 88, 12)),
        (862, 548, 390, 148, f"#3 {rows[2]['name_en'].upper()[:15]}", f"{rows[2]['score']}  |  {rows[2]['access_short']}", rows[2]["dish"].split("(")[0].strip()[:26], (2, 132, 199)),
    ]
    f_p1 = ImageFont.truetype(black_path, 24)
    f_p2 = ImageFont.truetype(w9_path, 16)
    f_p3 = ImageFont.truetype(w9_path, 16)
    for px, py, pw, ph, pt1, pt2, pt3, pcol in pod_cards:
        d5.rounded_rectangle((px, py, px + pw, py + ph), radius=18, fill=(10, 18, 34, 245), outline=(253, 224, 71, 255), width=3)
        d5.rounded_rectangle((px + 10, py + 10, px + pw - 10, py + 56), radius=10, fill=(*pcol, 255))
        d5.text((px + 20, py + 16), pt1, font=f_p1, fill=(255, 255, 255, 255))
        d5.text((px + 18, py + 70), pt2, font=f_p2, fill=(253, 224, 71, 255))
        d5.text((px + 18, py + 104), pt3, font=f_p3, fill=(167, 243, 208, 255))

    # Save all 5 templates and automatically rotate which template is set as primary `thumb_a` & `thumb_b` by episode number!
    all_tpls = [canvas_a, canvas_b, canvas_3, canvas_4, canvas_5]
    for idx_t, c_im in enumerate(all_tpls, 1):
        p_t = OUTPUT_DIR / f"overseas_japan_{rid}_thumb_tpl{idx_t}.jpg"
        c_im.convert("RGB").save(p_t, "JPEG", quality=96)

    import re
    m_num = re.search(r"(\d+)$", rid)
    ep_idx = (int(m_num.group(1)) - 1) if m_num else 0
    primary_im = all_tpls[ep_idx % 5]
    secondary_im = all_tpls[(ep_idx + 2) % 5]
    primary_im.convert("RGB").save(thumb_a, "JPEG", quality=96)
    secondary_im.convert("RGB").save(thumb_b, "JPEG", quality=96)
    logger.info(f"Auto-rotated primary thumbnail for '{rid}' -> Template #{(ep_idx % 5) + 1} (Alt: Template #{((ep_idx + 2) % 5) + 1})")

    # =========================================================================
    # Design C (1080x1920): Vertical YouTube Shorts Custom Cover
    # =========================================================================
    SW_T, SH_T = 1080, 1920
    canvas_s = Image.new("RGBA", (SW_T, SH_T), (8, 12, 24, 255))
    sh_hero = grade_photo(Image.open(p1_path), SW_T, 1320, sat=1.45, con=1.22, bri=1.06)
    canvas_s.paste(sh_hero.convert("RGBA"), (0, 260))

    ov_s = Image.new("RGBA", (SW_T, SH_T), (0, 0, 0, 0))
    od_s = ImageDraw.Draw(ov_s)
    for y in range(540):
        a = int(252 * (1 - max(0, (y - 240)) / 300) ** 1.5) if y > 240 else 252
        od_s.line([(0, y), (SW_T, y)], fill=(8, 13, 26, a))
    for y in range(1180, SH_T):
        t = min(1.0, (y - 1180) / 380)
        a = int(252 * (t ** 1.3))
        od_s.line([(0, y), (SW_T, y)], fill=(8, 13, 26, a))
    canvas_s.alpha_composite(ov_s)

    d_s = ImageDraw.Draw(canvas_s)
    d_s.rounded_rectangle((110, 56, 970, 130), radius=37, fill=(220, 38, 38, 255), outline=(253, 224, 71, 255), width=4)
    f_sr = ImageFont.truetype(w9_path, 34)
    t_sr = "500K JAPANESE IG POSTS ANALYZED"
    tb_sr = d_s.textbbox((0, 0), t_sr, font=f_sr)
    d_s.text(((SW_T - (tb_sr[2] - tb_sr[0])) // 2, 74), t_sr, font=f_sr, fill=(255, 255, 255, 255))

    f_sh1 = ImageFont.truetype(black_path, 104 if len(hero_line1) > 11 else 112)
    f_sh2 = ImageFont.truetype(black_path, 102 if len(hero_line2) > 11 else 118)
    draw_pro_3d_text(canvas_s, (95, 148), hero_line1, f_sh1, (255, 255, 255), (218, 234, 255), stroke_w=12, depth=10)
    draw_pro_3d_text(canvas_s, (105, 282), hero_line2, f_sh2, (255, 248, 130), (245, 158, 11), stroke_w=12, depth=10)

    d_s.rounded_rectangle((80, 440, 1000, 548), radius=22, fill=(14, 116, 144, 248), outline=(167, 243, 208, 255), width=4)
    f_sak = ImageFont.truetype(black_path, 58)
    tb_sak = d_s.textbbox((0, 0), banner_title, font=f_sak)
    d_s.text(((SW_T - (tb_sak[2] - tb_sak[0])) // 2, 456), banner_title, font=f_sak, fill=(255, 255, 255, 255))

    sp_p3 = make_polaroid_card(p3_path, 430, 310, f"#3  {rows[2]['score']}", rows[2]["name_en"], (2, 132, 199), -5.0)
    sp_p2 = make_polaroid_card(p2_path, 430, 310, f"#2  {rows[1]['score']}", rows[1]["name_en"], (220, 38, 38), 5.0)
    canvas_s.alpha_composite(sp_p3, (65, 1390))
    canvas_s.alpha_composite(sp_p2, (545, 1390))

    d_s.rounded_rectangle((70, 1210, 1010, 1365), radius=26, fill=(12, 18, 32, 245), outline=(253, 224, 71, 255), width=5)
    f_sn1 = ImageFont.truetype(w9_path, 44)
    f_sn2 = ImageFont.truetype(w9_path, 28)
    t_sn1 = f"#1 {rows[0]['name_en'].upper()} ({rows[0]['score'].split('/')[0].strip()} PT)"
    t_sn2 = rows[0]["dish"].split("(")[0].strip().upper() + "!"
    tb_sn1 = d_s.textbbox((0, 0), t_sn1, font=f_sn1)
    tb_sn2 = d_s.textbbox((0, 0), t_sn2, font=f_sn2)
    d_s.text(((SW_T - (tb_sn1[2] - tb_sn1[0])) // 2, 1232), t_sn1, font=f_sn1, fill=(253, 224, 71, 255))
    d_s.text(((SW_T - (tb_sn2[2] - tb_sn2[0])) // 2, 1302), t_sn2, font=f_sn2, fill=(167, 243, 208, 255))

    canvas_s.convert("RGB").save(thumb_s, "JPEG", quality=96)
    logger.info(f"Completed Custom Shorts Thumbnail C (1080x1920): {thumb_s}")
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



