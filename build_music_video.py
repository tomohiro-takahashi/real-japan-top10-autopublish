#!/usr/bin/env python3
"""
build_music_video.py
====================
Suno MP3 Automated 1-Hour Retro Music Loop (16:9) & Vertical Shorts (9:16) Builder + YouTube Uploader.
Designed to run 100% free & zero-local-CPU on GitHub Actions (or locally).

Upgraded Features:
1. Suno Unofficial API Integration (`suno_auto_generator.py`):
   - First checks `stocks/music/queue/` for any manually dropped `.mp3` files.
   - If `queue/` is empty and `SUNO_COOKIE` (or `SUNO_API_BASE_URL`) is configured, automatically requests
     a new 90s Eurobeat / 80s Japanese Boogie Disco / 90s City Pop track from Suno and downloads the MP3!
2. Real Moving Highway Driving Video Support (`stocks/music/bg_videos/` + 3D Highway Motion Engine):
   - If a Flow/Veo `.mp4` clip is placed in `stocks/music/bg_videos/` (e.g. `eurobeat_01.mp4`, `citypop_01.mp4`, `disco_01.mp4`),
     automatically converts it into a seamless Ping-Pong (forward + reverse) 16:9 motion loop.
   - If `stocks/music/bg_videos/` is empty, renders a 24fps 3D Midnight Tokyo Highway High-Speed Driving Animation
     (rushing road lane markers, passing neon streetlights, glowing speed lines, and rear sports car silhouette with
     vibrating twin tail lights over the Pollinations.ai retro sky/cityscape)!
3. Real-time Audio Spectrum (`showwaves`) + Vignette + Fast `-c:v libx264 -preset veryfast` encoding for both:
   - `output_1hour.mp4` (1280x720, ~3600s)
   - `output_short.mp4` (720x1280, 30s from 30s..60s of the MP3)
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import os
import random
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from suno_auto_generator import SunoUnofficialClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("music_video_builder")

BASE_DIR = Path(__file__).resolve().parent
MUSIC_DIR = BASE_DIR / "stocks" / "music"
QUEUE_DIR = MUSIC_DIR / "queue"
DONE_DIR = MUSIC_DIR / "done"
BG_VIDEOS_DIR = MUSIC_DIR / "bg_videos"
ARTWORKS_DIR = MUSIC_DIR / "artworks"
METADATA_POOL_PATH = MUSIC_DIR / "metadata_pool.json"

OUTPUT_1HOUR = BASE_DIR / "output_1hour.mp4"
OUTPUT_SHORT = BASE_DIR / "output_short.mp4"
OUTPUT_THUMB = BASE_DIR / "output_music_thumb.jpg"

TOKEN_FILE_MUSIC = BASE_DIR / ".youtube_token_music.json"
TOKEN_FILE_FALLBACK = BASE_DIR / ".youtube_token_overseas_japan.json"
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"


def find_bold_font() -> str:
    """Find a clean bold sans-serif font on macOS or Ubuntu (GitHub Actions)."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""


def find_cjk_font() -> str:
    """Find a bold Japanese CJK font on macOS or Ubuntu (GitHub Actions)."""
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""


def find_cjk_heavy_font() -> str:
    """Find an extra-heavy Japanese Gothic font for record-jacket main headlines."""
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return find_cjk_font()


def find_cjk_mincho_font() -> str:
    """Find a Japanese Mincho / Serif font for nostalgic emotional catchphrases."""
    candidates = [
        "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
        "/System/Library/Fonts/ヒラギノ明朝 ProN W4.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return find_cjk_font()


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def clean_ascii_text(text: str) -> str:
    """Replace emojis with clean separators and strip non-ASCII symbols so missing glyph boxes (□) never appear."""
    import re as _re

    t = (
        text.replace("🎧", " // ")
        .replace("🪩", " // ")
        .replace("🏎️", "")
        .replace("🏎", "")
        .replace("✨", "")
        .replace("🔥", "")
        .replace("🌃", "")
        .replace("—", " - ")
        .replace("–", "-")
    )
    t = _re.sub(r"[^\x20-\x7E]", " ", t)
    t = _re.sub(r"\s{2,}", " ", t).strip(" |-")
    return t


def fit_font_for_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: str,
    max_size: int,
    min_size: int,
    max_w: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Pick the largest font size in [min_size, max_size] where `text` fits within `max_w` pixels."""
    for sz in range(max_size, min_size - 1, -1):
        f = load_font(font_path, sz)
        tb = draw.textbbox((0, 0), text, font=f)
        if (tb[2] - tb[0]) <= max_w:
            return f
    return load_font(font_path, min_size)


def smart_truncate(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_w: int,
) -> str:
    """Truncate strictly at whole-word or clause boundaries so words are never cut mid-word."""
    clean = " ".join(text.split())
    if not clean:
        return ""
    tb = draw.textbbox((0, 0), clean, font=font)
    if (tb[2] - tb[0]) <= max_w:
        return clean

    for sep in (" | ", " // ", " - ", ": ", "; ", ", "):
        if sep in clean:
            head = clean.split(sep)[0].strip()
            tb_h = draw.textbbox((0, 0), head, font=font)
            if len(head) >= 10 and (tb_h[2] - tb_h[0]) <= max_w:
                return head

    words = clean.split(" ")
    while len(words) > 1:
        words.pop()
        cand = " ".join(words).rstrip(",;:-—|/")
        tb_c = draw.textbbox((0, 0), cand, font=font)
        if (tb_c[2] - tb_c[0]) <= max_w:
            return cand
    return clean


def get_audio_duration(media_path: Path) -> float:
    """Return duration of an audio or video file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def generate_synthesized_retro_test_mp3(out_mp3: Path, duration_sec: int = 195) -> Path:
    """
    Generate a driving 3m15s 90s Eurobeat / Synthwave stereo MP3 via FFmpeg `aevalsrc`
    when `--generate-sample-mp3` is requested for testing.
    """
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    expr = (
        "0.24*sin(2*PI*110*t)*(1+0.5*sin(2*PI*4*t))"
        "+0.16*sin(2*PI*220*t)+0.14*sin(2*PI*277.18*t)+0.14*sin(2*PI*329.63*t)+0.12*sin(2*PI*440*t)"
        "+0.12*sin(2*PI*(440+110*floor(mod(t*5,4)))*t)*exp(-mod(t*5,1)*3.2)"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"aevalsrc='{expr}|{expr}':s=44100:d={duration_sec}",
        "-af",
        "afade=t=in:st=0:d=2.0,afade=t=out:st=" + str(max(1, duration_sec - 3)) + ":d=3.0",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(out_mp3),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"Generated sample test MP3: {out_mp3} ({duration_sec}s)")
    return out_mp3


def pick_mp3_and_metadata(
    auto_suno: bool = True,
) -> Tuple[Optional[Path], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    1. Pick 1 unused metadata item from `stocks/music/metadata_pool.json`.
    2. Check `stocks/music/queue/` for an existing `.mp3`.
    3. If `queue/` is empty and `auto_suno=True`, invoke `SunoUnofficialClient` using `SUNO_COOKIE`
       (or `SUNO_API_BASE_URL`) to generate & download a fresh Suno MP3 into `queue/`.
    """
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    BG_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    if not METADATA_POOL_PATH.exists():
        raise FileNotFoundError(f"Metadata pool not found: {METADATA_POOL_PATH}")

    raw_pool = json.loads(METADATA_POOL_PATH.read_text(encoding="utf-8"))
    pool: List[Dict[str, Any]] = raw_pool["items"] if isinstance(raw_pool, dict) and "items" in raw_pool else raw_pool
    unused = [item for item in pool if not item.get("used", False)]
    if not unused:
        logger.warning("All metadata entries in metadata_pool.json were marked used; resetting pool to unused.")
        for item in pool:
            item["used"] = False
        unused = pool

    chosen_meta = unused[0]

    mp3_files = sorted(
        [p for p in QUEUE_DIR.iterdir() if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".m4a")]
    )
    if not mp3_files and auto_suno:
        suno_client = SunoUnofficialClient()
        if suno_client.is_configured():
            try:
                generated_mp3 = suno_client.generate_and_download_mp3(chosen_meta, QUEUE_DIR)
                if generated_mp3 and generated_mp3.exists():
                    mp3_files = [generated_mp3]
            except Exception as exc:
                logger.error(f"Suno automatic generation failed: {exc}")

    if not mp3_files:
        logger.warning(f"No MP3 files found in {QUEUE_DIR} (and SUNO_COOKIE not active).")
        return None, None, []

    chosen_mp3 = mp3_files[0]
    logger.info(f"Selected MP3: {chosen_mp3.name}")
    logger.info(f"Selected Metadata [{chosen_meta['id']}] ({chosen_meta['genre']}): {chosen_meta['title']}")
    return chosen_mp3, chosen_meta, pool


def render_procedural_retro_artwork(meta: Dict[str, Any], out_jpg: Path, width: int = 1280, height: int = 720) -> Path:
    """
    Render a rich 90s Retro Anime / Synthwave Night Tokyo illustration at 1280x720
    as a fallback if Pollinations.ai is rate-limited or offline.
    """
    genre = meta.get("genre", "90s City Pop")
    img = Image.new("RGB", (width, height), (10, 8, 26))
    draw = ImageDraw.Draw(img, "RGBA")

    if "Eurobeat" in genre:
        top_c, mid_c, hor_c = (8, 10, 28), (38, 16, 68), (225, 45, 85)
        sun_c1, sun_c2 = (255, 210, 60), (255, 50, 100)
    elif "Disco" in genre:
        top_c, mid_c, hor_c = (12, 6, 34), (75, 15, 95), (255, 60, 165)
        sun_c1, sun_c2 = (255, 230, 90), (255, 40, 150)
    else:
        top_c, mid_c, hor_c = (6, 16, 42), (28, 45, 105), (245, 95, 145)
        sun_c1, sun_c2 = (254, 240, 138), (244, 63, 94)

    horizon_y = int(height * 0.54)
    for y in range(horizon_y):
        t = y / max(1, horizon_y)
        if t < 0.55:
            u = t / 0.55
            r = int(top_c[0] * (1 - u) + mid_c[0] * u)
            g = int(top_c[1] * (1 - u) + mid_c[1] * u)
            b = int(top_c[2] * (1 - u) + mid_c[2] * u)
        else:
            u = (t - 0.55) / 0.45
            r = int(mid_c[0] * (1 - u) + hor_c[0] * u)
            g = int(mid_c[1] * (1 - u) + hor_c[1] * u)
            b = int(mid_c[2] * (1 - u) + hor_c[2] * u)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    rng = random.Random(hash(meta.get("id", "retro")))
    for _ in range(90):
        sx = rng.randint(10, width - 10)
        sy = rng.randint(10, int(horizon_y * 0.7))
        sr = rng.choice([1, 1, 2])
        draw.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(255, 250, 240, rng.randint(140, 255)))

    sun_r = int(height * 0.19)
    sun_cx, sun_cy = width // 2, horizon_y - int(sun_r * 0.2)
    for dy in range(-sun_r, sun_r):
        sy = sun_cy + dy
        if sy >= horizon_y:
            continue
        if dy > 8 and (dy // 8) % 2 == 0:
            continue
        dx = int(math.sqrt(max(0, sun_r * sun_r - dy * dy)))
        u = (dy + sun_r) / (2 * sun_r)
        sr = int(sun_c1[0] * (1 - u) + sun_c2[0] * u)
        sg = int(sun_c1[1] * (1 - u) + sun_c2[1] * u)
        sb = int(sun_c1[2] * (1 - u) + sun_c2[2] * u)
        draw.line([(sun_cx - dx, sy), (sun_cx + dx, sy)], fill=(sr, sg, sb, 240))

    bx = 0
    while bx < width:
        bw = rng.randint(36, 84)
        bh = rng.randint(45, 180)
        by0 = horizon_y - bh
        draw.rectangle((bx, by0, bx + bw, horizon_y), fill=(12, 14, 28, 255), outline=(45, 55, 85, 180), width=1)
        win_col = rng.choice([(253, 224, 71, 210), (56, 189, 248, 210), (244, 114, 182, 210)])
        for wy in range(by0 + 8, horizon_y - 8, 10):
            for wx in range(bx + 6, bx + bw - 8, 9):
                if rng.random() < 0.42:
                    draw.rectangle((wx, wy, wx + 4, wy + 5), fill=win_col)
        bx += bw - rng.randint(0, 6)

    img.save(out_jpg, "JPEG", quality=95)
    return out_jpg


def resolve_curated_artwork_path(meta: Dict[str, Any]) -> Optional[Path]:
    """
    Resolve the curated high-sense 16:9 Japanese retro master illustration in `stocks/music/artworks/`.
    """
    ARTWORKS_DIR.mkdir(parents=True, exist_ok=True)
    explicit = meta.get("artwork_file", "")
    if explicit and (ARTWORKS_DIR / explicit).exists():
        return ARTWORKS_DIR / explicit

    genre = meta.get("genre", "").lower()
    mapping = [
        ("eurobeat", "eurobeat.jpg"),
        ("disco", "disco.jpg"),
        ("boogie", "disco.jpg"),
        ("rave", "tkrave.jpg"),
        ("tk", "tkrave.jpg"),
        ("80s city pop", "citypop80s.jpg"),
        ("sax aor", "citypop80s.jpg"),
        ("urban", "urban90s.jpg"),
        ("shibuya", "urban90s.jpg"),
        ("arcade", "arcade.jpg"),
        ("fusion", "arcade.jpg"),
    ]
    for key, fname in mapping:
        if key in genre and (ARTWORKS_DIR / fname).exists():
            return ARTWORKS_DIR / fname

    all_arts = sorted([p for p in ARTWORKS_DIR.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if all_arts:
        return all_arts[hash(meta.get("id", "0")) % len(all_arts)]
    return None


def download_background_image(meta: Dict[str, Any], out_jpg: Path) -> Path:
    """
    Load the curated high-sense 16:9 Japanese retro illustration from `stocks/music/artworks/` first.
    Falls back to Pollinations.ai or procedural artwork only if `stocks/music/artworks/` is empty.
    """
    curated = resolve_curated_artwork_path(meta)
    if curated is not None and curated.exists():
        im = Image.open(curated).convert("RGB")
        im = im.resize((1280, 720), Image.Resampling.LANCZOS)
        im.save(out_jpg, "JPEG", quality=96)
        logger.info(f"Loaded curated Japanese retro master illustration: {curated.name} -> {out_jpg.name}")
        return out_jpg

    prompt = meta.get(
        "image_prompt",
        "90s retro anime style aesthetic, lo-fi vintage illustration, midnight Tokyo highway, sports car, neon lights, 16:9",
    )
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true"
    logger.info(f"Downloading background image from Pollinations.ai: {url[:95]}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }
    for attempt in range(1, 3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=35) as resp:
                raw = resp.read()
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            x0, y0 = int(im.width * 0.03), int(im.height * 0.03)
            x1, y1 = int(im.width * 0.97), int(im.height * 0.90)
            im = im.crop((x0, y0, x1, y1))
            im = im.resize((1280, 720), Image.Resampling.LANCZOS)
            im.save(out_jpg, "JPEG", quality=95)
            logger.info(f"Downloaded Pollinations background image: {out_jpg} ({im.size})")
            return out_jpg
        except Exception as exc:
            logger.warning(f"Pollinations download attempt {attempt}/2 failed ({exc}).")
            time.sleep(2.0)

    logger.info("Using procedural 90s Retro Anime / Synthwave background illustration fallback.")
    return render_procedural_retro_artwork(meta, out_jpg, 1280, 720)


def find_matching_flow_video(meta: Dict[str, Any]) -> Optional[Path]:
    """
    Check `stocks/music/bg_videos/` for a user-supplied Flow / Veo MP4 loop matching the genre.
    Matches `eurobeat*.mp4`, `disco*.mp4`, `citypop*.mp4` or falls back to any `.mp4` in `bg_videos/`.
    """
    if not BG_VIDEOS_DIR.exists():
        return None
    all_mp4s = sorted([p for p in BG_VIDEOS_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"])
    if not all_mp4s:
        return None

    genre = meta.get("genre", "").lower()
    if "eurobeat" in genre:
        key = "eurobeat"
    elif "disco" in genre or "boogie" in genre:
        key = "disco"
    else:
        key = "citypop"

    matched = [p for p in all_mp4s if key in p.stem.lower()]
    pool = matched if matched else all_mp4s
    idx = hash(meta.get("id", "0")) % len(pool)
    chosen = pool[idx]
    logger.info(f"Found Flow background video in stocks/music/bg_videos/: {chosen.name}")
    return chosen


def build_highway_driving_loop_mp4(
    bg_jpg: Path,
    meta: Dict[str, Any],
    out_loop_mp4: Path,
    fps: int = 24,
) -> Path:
    """
    Build a seamless 1280x720 motion loop MP4:
    - Priority 1: If `stocks/music/bg_videos/` has a Flow `.mp4` video, converts it into a seamless
      Ping-Pong (forward + reverse) 1280x720@24fps loop so there is zero jump cut!
    - Priority 2: Preserves 100% of the curated master illustration (`bg_jpg`) and animates it at 24fps
      (96 frames / 4.0s seamless cycle) with smooth breathing camera drift, pulsing neon highlight bloom,
      and atmospheric drifting light trails / bokeh particles so the artwork shines without any crude polygon overwrite.
    """
    flow_mp4 = find_matching_flow_video(meta)
    if flow_mp4 is not None:
        logger.info(f"Building seamless Ping-Pong highway loop from Flow video: {flow_mp4.name} ...")
        vf = (
            f"[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps={fps},setsar=1,"
            f"vignette=PI/6,split[fwd][tmp];"
            f"[tmp]reverse[rev];"
            f"[fwd][rev]concat=n=2:v=1:a=0,format=yuv420p[vout]"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(flow_mp4),
                "-filter_complex",
                vf,
                "-map",
                "[vout]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                str(out_loop_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return out_loop_mp4

    logger.info("Synthesizing 24fps Cinematic Japanese Retro Illustration Motion Loop (96 frames / 4.0s cycle)...")
    W, H = 1280, 720
    total_frames = 96  # 4.0 seconds @ 24fps

    # Overscan to 1344x756 (1.05x) for smooth sub-pixel-like camera drift without losing borders
    OW, OH = 1344, 756
    overscan_im = Image.open(bg_jpg).convert("RGB").resize((OW, OH), Image.Resampling.LANCZOS)

    genre = meta.get("genre", "90s Eurobeat")
    if "Eurobeat" in genre or "Arcade" in genre:
        accent_c1, accent_c2 = (253, 224, 71), (56, 189, 248)
    elif "Disco" in genre or "Rave" in genre:
        accent_c1, accent_c2 = (244, 114, 182), (253, 224, 71)
    else:
        accent_c1, accent_c2 = (56, 189, 248), (253, 224, 71)

    rng = random.Random(hash(meta.get("id", "retro_loop")))
    # Pre-generate 28 seamless drifting bokeh / light particles
    particles = []
    for _ in range(28):
        particles.append(
            {
                "x0": rng.uniform(0.05, 0.95),
                "y0": rng.uniform(0.08, 0.72),
                "r": rng.choice([2, 3, 4, 6]),
                "phase": rng.uniform(0.0, 1.0),
                "col": accent_c1 if rng.random() < 0.55 else accent_c2,
                "alpha": rng.randint(45, 110),
            }
        )

    with tempfile.TemporaryDirectory(prefix="retro_frames_") as tmp_s:
        frames_dir = Path(tmp_s)

        for f_idx in range(total_frames):
            t_norm = f_idx / float(total_frames)  # 0.0 .. 1.0
            theta = 2.0 * math.pi * t_norm

            # Smooth figure-8 camera breath within the 1344x756 overscan canvas
            cx_off = int((OW - W) * 0.5 + 22.0 * math.sin(theta))
            cy_off = int((OH - H) * 0.5 + 10.0 * math.cos(theta))
            frame = overscan_im.crop((cx_off, cy_off, cx_off + W, cy_off + H))

            # Subtle analog neon pulse (1.00 .. 1.06 brightness & color warmth)
            pulse = 1.0 + 0.045 * math.sin(2.0 * theta)
            frame = ImageEnhance.Brightness(frame).enhance(pulse)
            frame = ImageEnhance.Color(frame).enhance(1.02 + 0.03 * math.cos(theta))

            draw = ImageDraw.Draw(frame, "RGBA")

            # Subtle drifting atmospheric bokeh / light reflections
            for pt in particles:
                p_t = (pt["phase"] + t_norm) % 1.0
                px = int((pt["x0"] + 0.04 * math.sin(2.0 * math.pi * p_t)) * W) % W
                py = int((pt["y0"] - 0.06 * math.cos(2.0 * math.pi * p_t)) * H) % H
                pr = pt["r"]
                pa = int(pt["alpha"] * (0.55 + 0.45 * math.sin(2.0 * math.pi * p_t)))
                draw.ellipse((px - pr * 2, py - pr * 2, px + pr * 2, py + pr * 2), fill=(*pt["col"], pa // 3))
                draw.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(255, 255, 255, pa))

            frame.save(frames_dir / f"f_{f_idx:04d}.jpg", "JPEG", quality=94)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(frames_dir / "f_%04d.jpg"),
                "-vf",
                "format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                str(out_loop_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    logger.info(f"Built cinematic retro illustration motion loop: {out_loop_mp4.name}")
    return out_loop_mp4


def _draw_soft_shadow_text(
    base_rgba: Image.Image,
    pos: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: Tuple[int, int, int, int],
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 220),
    shadow_offset: Tuple[int, int] = (0, 4),
    blur_radius: int = 6,
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 200),
) -> None:
    """Render crisp Japanese typography with a soft Gaussian drop-shadow like a professional record jacket."""
    x, y = pos
    if blur_radius > 0:
        sh_layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(sh_layer, "RGBA")
        sh_draw.text(
            (x + shadow_offset[0], y + shadow_offset[1]),
            text,
            font=font,
            fill=shadow_color,
            stroke_width=max(2, stroke_width + 2),
            stroke_fill=shadow_color,
        )
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        base_rgba.alpha_composite(sh_layer)

    draw = ImageDraw.Draw(base_rgba, "RGBA")
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill if stroke_width > 0 else None,
    )


def _extract_ja_parts(meta: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Return (era_label, catchphrase, main_headline, sub_spec) in Japanese for thumbnails & HUDs."""
    era_label = meta.get("thumb_era_label") or "40代・50代に捧ぐ  ｜  1980s-90s ARCHIVE"
    catch_txt = meta.get("thumb_catch") or "聴くだけで、当時の記憶がよみがえる——"
    main_txt = meta.get("thumb_main") or "深夜の首都高・青春BGMアーカイブ"
    sub_txt = meta.get("thumb_sub") or "作業・ドライブ用BGM  ｜  全16曲ノンストップ・フルアルバム（60分耐久）"
    return era_label, catch_txt, main_txt, sub_txt


def render_16x9_hud_and_thumb(
    bg_jpg: Path,
    meta: Dict[str, Any],
    hud_png: Path,
    thumb_jpg: Path,
    font_path: str,
) -> None:
    """
    Create:
    1) A refined Japanese FM-Radio / Record-Jacket HUD overlay (`hud_png`, 1280x720 RGBA) for the 1-hour video
    2) A high-sense Japanese 80s/90s Record-Jacket YouTube thumbnail (`thumb_jpg`, 1280x720) where the
       curated illustration shines without tacky black boxes or supermarket stickers.
    """
    cjk_reg_path = find_cjk_font() or font_path
    cjk_heavy_path = find_cjk_heavy_font() or cjk_reg_path
    cjk_mincho_path = find_cjk_mincho_font() or cjk_reg_path

    era_label, catch_txt, main_txt, sub_txt = _extract_ja_parts(meta)

    # =========================================================================
    # 1) 16:9 VIDEO OVERLAY HUD (`hud_png`) — Minimalist Japanese FM-Radio Style
    # =========================================================================
    hud = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud, "RGBA")

    # Smooth bottom gradient (y=520..720) for audio spectrum + track caption
    for y in range(520, 720):
        u = (y - 520) / 200.0
        alpha = int(205 * (u ** 1.45))
        draw.line([(0, y), (1280, y)], fill=(5, 8, 18, alpha))

    # Top-left minimalist frosted pill
    f_hud_top = load_font(cjk_reg_path, 17)
    hud_top_txt = f"●  {era_label}"
    tb_top = draw.textbbox((0, 0), hud_top_txt, font=f_hud_top)
    tw_top = (tb_top[2] - tb_top[0]) + 36
    draw.rounded_rectangle(
        (32, 26, 32 + tw_top, 60),
        radius=17,
        fill=(8, 12, 24, 155),
        outline=(253, 224, 71, 140),
        width=1,
    )
    draw.text((50, 34), hud_top_txt, font=f_hud_top, fill=(248, 250, 252, 235))

    # Bottom caption under the audio equalizer (y=678)
    hud_bot_txt = f"♪  {main_txt}   —   {sub_txt}"
    f_hud_bot = fit_font_for_width(draw, hud_bot_txt, cjk_reg_path, 20, 15, 1280 - 96)
    draw.text(
        (44, 676),
        hud_bot_txt,
        font=f_hud_bot,
        fill=(241, 245, 249, 240),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 210),
    )
    hud.save(hud_png, "PNG")

    # =========================================================================
    # 2) 16:9 YOUTUBE THUMBNAIL (`thumb_jpg`) — Japanese Record-Jacket Design
    # =========================================================================
    base = Image.open(bg_jpg).convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)

    # Subtle contrast & saturation polish on the master illustration
    base_rgb = ImageEnhance.Contrast(base.convert("RGB")).enhance(1.06)
    base_rgb = ImageEnhance.Color(base_rgb).enhance(1.08)
    base = base_rgb.convert("RGBA")

    grad = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grad, "RGBA")

    # Top subtle vignette (y=0..115) so the top-left editorial tag is effortlessly legible
    for y in range(0, 115):
        u = 1.0 - (y / 115.0)
        alpha = int(125 * (u ** 1.6))
        g_draw.line([(0, y), (1280, y)], fill=(4, 7, 16, alpha))

    # Smooth multi-stop bottom cinema gradient (y=360..720) — zero boxy borders!
    for y in range(360, 720):
        u = (y - 360) / 360.0
        alpha = int(242 * (u ** 1.35))
        g_draw.line([(0, y), (1280, y)], fill=(4, 7, 18, alpha))

    base.alpha_composite(grad)
    t_draw = ImageDraw.Draw(base, "RGBA")

    # A. Top-Left Editorial Archive Tag (Vertical Gold Bar + Frosted Pill)
    f_era = load_font(cjk_reg_path, 21)
    tb_era = t_draw.textbbox((0, 0), era_label, font=f_era)
    era_w = (tb_era[2] - tb_era[0]) + 44
    t_draw.rounded_rectangle(
        (44, 32, 44 + era_w, 76),
        radius=8,
        fill=(8, 12, 24, 175),
        outline=(255, 255, 255, 65),
        width=1,
    )
    # Warm gold left accent bar inside the tag
    t_draw.rounded_rectangle((44, 32, 52, 76), radius=3, fill=(251, 191, 36, 255))
    t_draw.text((66, 43), era_label, font=f_era, fill=(254, 240, 138, 255))

    # B. Bottom-Left Record-Jacket Typography (Mincho Catchphrase + Heavy Gothic Headline)
    max_text_w = 1180

    # 1. Emotional Catchphrase (Mincho / Serif in warm champagne gold)
    f_catch = fit_font_for_width(t_draw, catch_txt, cjk_mincho_path, 29, 20, max_text_w)
    _draw_soft_shadow_text(
        base,
        (48, 480),
        catch_txt,
        font=f_catch,
        fill=(253, 224, 71, 255),
        shadow_color=(0, 0, 0, 235),
        shadow_offset=(0, 3),
        blur_radius=5,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 210),
    )

    # 2. Main Japanese Headline (Extra-Heavy Gothic W8 in pure white with deep cinema shadow)
    f_main = fit_font_for_width(t_draw, main_txt, cjk_heavy_path, 62, 38, max_text_w)
    _draw_soft_shadow_text(
        base,
        (46, 524),
        main_txt,
        font=f_main,
        fill=(255, 255, 255, 255),
        shadow_color=(0, 0, 0, 245),
        shadow_offset=(0, 5),
        blur_radius=8,
        stroke_width=2,
        stroke_fill=(6, 10, 24, 230),
    )

    # 3. Thin Editorial Gold/Silver Divider Line (y=616)
    t_draw = ImageDraw.Draw(base, "RGBA")
    t_draw.line([(48, 618), (68, 618)], fill=(251, 191, 36, 255), width=3)
    t_draw.line([(74, 618), (960, 618)], fill=(226, 232, 240, 115), width=1)

    # 4. Bottom Album Spec Line (Clean Gothic W6 in silver-white)
    f_sub = fit_font_for_width(t_draw, sub_txt, cjk_reg_path, 22, 16, 920)
    _draw_soft_shadow_text(
        base,
        (48, 634),
        sub_txt,
        font=f_sub,
        fill=(226, 232, 240, 245),
        shadow_color=(0, 0, 0, 220),
        shadow_offset=(0, 2),
        blur_radius=4,
    )

    # C. Bottom-Right Minimalist CD/Vinyl Spec Badge ("60 MIN / 16 TRACKS")
    t_draw = ImageDraw.Draw(base, "RGBA")
    stamp_txt = "60 MIN  /  16 TRACKS"
    f_stamp = load_font(font_path, 18)
    tb_st = t_draw.textbbox((0, 0), stamp_txt, font=f_stamp)
    st_w = (tb_st[2] - tb_st[0]) + 40
    st_x0 = 1280 - 44 - st_w
    st_y0 = 624
    t_draw.rounded_rectangle(
        (st_x0, st_y0, st_x0 + st_w, st_y0 + 42),
        radius=21,
        fill=(12, 18, 34, 200),
        outline=(251, 191, 36, 215),
        width=2,
    )
    t_draw.text(
        (st_x0 + 20, st_y0 + 11),
        stamp_txt,
        font=f_stamp,
        fill=(253, 224, 71, 255),
    )

    base.convert("RGB").save(thumb_jpg, "JPEG", quality=96)


def build_1hour_loop_audio(
    src_mp3: Path,
    out_m4a: Path,
    target_duration_sec: int = 3600,
) -> float:
    """
    Create a single seamless ~3600s audio track by applying a smooth 2.5s fade-in and 2.5s fade-out
    to a single cycle of `src_mp3`, then stream-looping it to `target_duration_sec`.
    """
    single_dur = get_audio_duration(src_mp3)
    fade_d = min(2.5, max(0.5, single_dur * 0.05))
    fade_out_st = max(0.5, single_dur - fade_d)

    with tempfile.TemporaryDirectory(prefix="music_loop_") as tmp_s:
        tmp_dir = Path(tmp_s)
        unit_m4a = tmp_dir / "unit_faded.m4a"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(src_mp3),
                "-af",
                f"afade=t=in:st=0:d={fade_d:.2f},afade=t=out:st={fade_out_st:.2f}:d={fade_d:.2f}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "44100",
                "-ac",
                "2",
                str(unit_m4a),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(unit_m4a),
                "-t",
                str(target_duration_sec),
                "-c",
                "copy",
                str(out_m4a),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    actual_dur = get_audio_duration(out_m4a)
    logger.info(f"Built looped audio track: {out_m4a.name} ({actual_dur:.1f}s from {single_dur:.1f}s source)")
    return actual_dur


def build_1hour_video(
    bg_loop_mp4: Path,
    hud_png: Path,
    looped_audio_m4a: Path,
    out_mp4: Path,
    duration_sec: int = 3600,
) -> Path:
    """
    Synthesize the 16:9 1-Hour Endurance Video (`output_1hour.mp4`, 1920x1080 Full HD):
    - Loops the high-speed highway driving video (`bg_loop_mp4`) seamlessly for `duration_sec`.
    - Overlays the retro HUD (`hud_png`) and real-time audio spectrum (`showwaves=s=1200x95:mode=cline`).
    """
    logger.info(f"Rendering 16:9 1080p Full HD highway driving music video ({duration_sec}s): {out_mp4} ...")
    fps = 24
    filter_complex = (
        f"[0:v]setpts=PTS-STARTPTS[bg];"
        f"[bg][1:v]overlay=0:0[bghud];"
        f"[2:a]showwaves=s=1200x95:mode=cline:rate={fps}:scale=sqrt:colors=0x38bdf8|0xf472b6|0xfde047,format=rgba,"
        f"colorchannelmixer=aa=0.88[sw];"
        f"[bghud][sw]overlay=40:580:shortest=1,scale=1920:1080:flags=lanczos,unsharp=3:3:0.5:3:3:0.0,format=yuv420p[vout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(bg_loop_mp4),
        "-i",
        str(hud_png),
        "-i",
        str(looped_audio_m4a),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "2:a",
        "-t",
        str(duration_sec),
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-maxrate",
        "6M",
        "-bufsize",
        "12M",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        "-shortest",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"Completed 16:9 1080p video: {out_mp4} ({out_mp4.stat().st_size / (1024*1024):.1f} MB)")
    return out_mp4


def render_short_vertical_hud(
    bg_jpg: Path,
    meta: Dict[str, Any],
    out_vertical_hud_png: Path,
    font_path: str,
) -> Path:
    """
    Build the 720x1280 (9:16) RGBA overlay for `output_short.mp4` in a 100% Japanese Record-Jacket
    layout with a transparent center window (`x=28..692, y=282..780`) where the animated artwork plays live!
    """
    SW, SH = 720, 1280
    raw = Image.open(bg_jpg).convert("RGB")

    scale = max(SW / raw.width, SH / raw.height)
    nw, nh = int(raw.width * scale), int(raw.height * scale)
    bg_crop = raw.resize((nw, nh), Image.Resampling.LANCZOS).crop(
        ((nw - SW) // 2, (nh - SH) // 2, (nw - SW) // 2 + SW, (nh - SH) // 2 + SH)
    )
    bg_blur = bg_crop.filter(ImageFilter.GaussianBlur(radius=30))
    bg_blur = ImageEnhance.Brightness(bg_blur).enhance(0.28).convert("RGBA")

    cjk_reg_path = find_cjk_font() or font_path
    cjk_heavy_path = find_cjk_heavy_font() or cjk_reg_path
    cjk_mincho_path = find_cjk_mincho_font() or cjk_reg_path

    era_label, catch_txt, main_txt, _ = _extract_ja_parts(meta)
    draw = ImageDraw.Draw(bg_blur, "RGBA")

    # 1. Top Japanese Editorial Header (y=76..258)
    f_era = fit_font_for_width(draw, era_label, cjk_reg_path, 18, 14, SW - 96)
    tb_e = draw.textbbox((0, 0), era_label, font=f_era)
    ew = (tb_e[2] - tb_e[0]) + 36
    ex0 = (SW - ew) // 2
    draw.rounded_rectangle(
        (ex0, 78, ex0 + ew, 114),
        radius=18,
        fill=(12, 18, 34, 210),
        outline=(251, 191, 36, 190),
        width=1,
    )
    draw.text(((SW - (tb_e[2] - tb_e[0])) // 2, 86), era_label, font=f_era, fill=(253, 224, 71, 255))

    # Catchphrase (Mincho)
    f_catch = fit_font_for_width(draw, catch_txt, cjk_mincho_path, 23, 16, SW - 64)
    tb_c = draw.textbbox((0, 0), catch_txt, font=f_catch)
    _draw_soft_shadow_text(
        bg_blur,
        ((SW - (tb_c[2] - tb_c[0])) // 2, 134),
        catch_txt,
        font=f_catch,
        fill=(254, 240, 138, 255),
        blur_radius=4,
    )

    # Main Title (Heavy Gothic)
    draw = ImageDraw.Draw(bg_blur, "RGBA")
    f_main = fit_font_for_width(draw, main_txt, cjk_heavy_path, 40, 24, SW - 56)
    tb_m = draw.textbbox((0, 0), main_txt, font=f_main)
    _draw_soft_shadow_text(
        bg_blur,
        ((SW - (tb_m[2] - tb_m[0])) // 2, 178),
        main_txt,
        font=f_main,
        fill=(255, 255, 255, 255),
        blur_radius=6,
        stroke_width=2,
        stroke_fill=(4, 8, 20, 230),
    )

    # 2. Punch a transparent window at (x=28..692, y=282..780) where the live animated illustration plays
    draw = ImageDraw.Draw(bg_blur, "RGBA")
    fx0, fy0, fx1, fy1 = 28, 282, SW - 28, 780
    draw.rounded_rectangle(
        (fx0, fy0, fx1, fy1),
        radius=18,
        fill=(0, 0, 0, 0),
        outline=(251, 191, 36, 210),
        width=2,
    )

    # 3. Spectrum Equalizer Frame Box (y=808..1028)
    draw.rounded_rectangle(
        (28, 808, SW - 28, 1028),
        radius=16,
        fill=(6, 10, 22, 205),
        outline=(148, 163, 184, 110),
        width=1,
    )

    # 4. Bottom Japanese Spec & Channel CTA (y=1054..1168)
    bot_spec = "作業・ドライブ用BGM  ｜  全16曲ノンストップ（60分耐久）"
    f_bs = fit_font_for_width(draw, bot_spec, cjk_reg_path, 21, 15, SW - 56)
    tb_bs = draw.textbbox((0, 0), bot_spec, font=f_bs)
    draw.text(
        ((SW - (tb_bs[2] - tb_bs[0])) // 2, 1058),
        bot_spec,
        font=f_bs,
        fill=(241, 245, 249, 245),
    )

    cta_ja = "本編フルアルバム（1時間耐久）はチャンネルから"
    f_cta = fit_font_for_width(draw, cta_ja, cjk_heavy_path, 21, 16, SW - 96)
    tb_cta = draw.textbbox((0, 0), cta_ja, font=f_cta)
    text_w = tb_cta[2] - tb_cta[0]
    cw = text_w + 68
    cx0 = (SW - cw) // 2
    draw.rounded_rectangle(
        (cx0, 1104, cx0 + cw, 1152),
        radius=24,
        fill=(15, 23, 42, 230),
        outline=(251, 191, 36, 220),
        width=2,
    )
    # Vector gold play triangle on the left inside the pill
    tri_x = cx0 + 24
    tri_cy = 1128
    draw.polygon(
        [(tri_x, tri_cy - 8), (tri_x, tri_cy + 8), (tri_x + 13, tri_cy)],
        fill=(253, 224, 71, 255),
    )
    draw.text(
        (tri_x + 22, 1116),
        cta_ja,
        font=f_cta,
        fill=(253, 224, 71, 255),
    )

    bg_blur.save(out_vertical_hud_png, "PNG")
    return out_vertical_hud_png


def build_short_video(
    bg_jpg: Path,
    bg_loop_mp4: Path,
    src_mp3: Path,
    meta: Dict[str, Any],
    out_short_mp4: Path,
    font_path: str,
) -> Path:
    """
    Synthesize `output_short.mp4` (1080x1920 Full HD 9:16, 30 seconds):
    - Extracts the 30s..60s climax slice of `src_mp3`.
    - Plays the moving highway driving video (`bg_loop_mp4`) inside the center window (`y=282..780`).
    - Overlays the large real-time audio spectrum (`showwaves=s=636x190:mode=p2p:scale=sqrt`) at `y=822` and upscales to 1080x1920 Full HD.
    """
    logger.info(f"Rendering 9:16 1080p Full HD Shorts highway driving video (30s): {out_short_mp4} ...")
    mp3_dur = get_audio_duration(src_mp3)
    start_sec = 30.0 if mp3_dur >= 62.0 else max(0.0, mp3_dur * 0.2)
    clip_dur = min(30.0, max(10.0, mp3_dur - start_sec))

    with tempfile.TemporaryDirectory(prefix="music_short_") as tmp_s:
        tmp_dir = Path(tmp_s)
        vert_hud_png = tmp_dir / "short_hud.png"
        render_short_vertical_hud(bg_jpg, meta, vert_hud_png, font_path)

        fps = 24
        filter_complex = (
            f"color=c=0x080c18:s=720x1280:r={fps}[base];"
            f"[0:v]scale=886:498,crop=664:498:(iw-664)/2:0,setpts=PTS-STARTPTS[vid];"
            f"[base][vid]overlay=28:282:shortest=1[v1];"
            f"[v1][1:v]overlay=0:0[v2];"
            f"[2:a]atrim=start={start_sec:.2f}:duration={clip_dur:.2f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=1.0,afade=t=out:st={max(1.0, clip_dur - 1.5):.2f}:d=1.5[aud];"
            f"[aud]asplit=2[a_out][a_viz];"
            f"[a_viz]showwaves=s=636x190:mode=cline:rate={fps}:scale=sqrt:colors=0xfde047|0x38bdf8,format=rgba[sw];"
            f"[v2][sw]overlay=42:822:shortest=1,scale=1080:1920:flags=lanczos,unsharp=3:3:0.5:3:3:0.0,format=yuv420p[vout]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(bg_loop_mp4),
            "-i",
            str(vert_hud_png),
            "-i",
            str(src_mp3),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[a_out]",
            "-t",
            f"{clip_dur:.2f}",
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
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
            "-movflags",
            "+faststart",
            str(out_short_mp4),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info(f"Completed 9:16 1080p Shorts video: {out_short_mp4} ({out_short_mp4.stat().st_size / (1024*1024):.1f} MB)")
    return out_short_mp4


def run_music_oauth_setup() -> None:
    """Run one-time interactive browser OAuth2 login for the Retro Music BGM YouTube Channel and save .youtube_token_music.json."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]
    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError(f"Missing {CLIENT_SECRET_FILE}")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), scopes)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE_MUSIC.write_text(creds.to_json(), encoding="utf-8")
    logger.info(f"Saved Music Channel OAuth token to {TOKEN_FILE_MUSIC}")


def get_youtube_service():
    """
    Build an authenticated YouTube Data API v3 client for the Music Channel using:
    1) `YOUTUBE_CLIENT_ID_MUSIC` / `YOUTUBE_CLIENT_SECRET_MUSIC` / `YOUTUBE_REFRESH_TOKEN_MUSIC` on GitHub Actions
    2) Local `.youtube_token_music.json` token file (or fallback if explicitly desired locally)
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]
    creds = None

    client_id = os.environ.get("YOUTUBE_CLIENT_ID_MUSIC") or os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET_MUSIC") or os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN_MUSIC")

    if client_id and client_secret and refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        creds.refresh(Request())
    elif TOKEN_FILE_MUSIC.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE_MUSIC), scopes)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE_MUSIC.write_text(creds.to_json(), encoding="utf-8")
    elif not os.environ.get("GITHUB_ACTIONS") and TOKEN_FILE_FALLBACK.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE_FALLBACK), scopes)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE_FALLBACK.write_text(creds.to_json(), encoding="utf-8")
    else:
        raise RuntimeError(
            "Music Channel YouTube credentials not configured yet. "
            "Run `python build_music_video.py --auth-setup` or set YOUTUBE_REFRESH_TOKEN_MUSIC in GitHub Secrets."
        )

    return build("youtube", "v3", credentials=creds)


def upload_video_to_youtube(
    youtube,
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    privacy_status: str = "public",
    thumbnail_path: Optional[Path] = None,
) -> str:
    """Upload a video to YouTube Data API v3 and optionally set its custom thumbnail."""
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags[:35],
            "categoryId": "10",  # Music category
            "defaultLanguage": "ja",
            "defaultAudioLanguage": "ja",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=10 * 1024 * 1024,
        resumable=True,
    )
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            logger.info(f"Uploading {video_path.name}: {int(status.progress() * 100)}%")

    video_id = response["id"]
    logger.info(f"Uploaded {video_path.name} -> https://youtu.be/{video_id}")

    if thumbnail_path and thumbnail_path.exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
            ).execute()
            logger.info(f"Custom thumbnail set for {video_id}")
        except Exception as exc:
            logger.warning(f"Could not set custom thumbnail for {video_id}: {exc}")

    return video_id


def mark_done_and_git_push(
    mp3_path: Path,
    chosen_meta: Dict[str, Any],
    pool: List[Dict[str, Any]],
    long_vid_id: str,
    short_vid_id: str,
    auto_git_push: bool = True,
) -> None:
    """
    Move the used MP3 (and any companion `.chapters.json`) to `stocks/music/done/`,
    mark the metadata item as `"used": true` in `stocks/music/metadata_pool.json`,
    and commit/push when running in CI.
    """
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_mp3 = DONE_DIR / f"{ts}_{mp3_path.name}"
    shutil.move(str(mp3_path), str(dest_mp3))
    logger.info(f"Moved MP3 to done: {dest_mp3}")

    chapters_file = mp3_path.with_suffix(".chapters.json")
    if chapters_file.exists():
        shutil.move(str(chapters_file), str(DONE_DIR / f"{ts}_{chapters_file.name}"))

    for item in pool:
        if item.get("id") == chosen_meta.get("id"):
            item["used"] = True
            item["published_at"] = datetime.now(timezone.utc).isoformat()
            item["youtube_long_id"] = long_vid_id
            item["youtube_short_id"] = short_vid_id
            break

    out_payload = {"total": len(pool), "items": pool}
    METADATA_POOL_PATH.write_text(
        json.dumps(out_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info(f"Updated {METADATA_POOL_PATH} ({chosen_meta['id']} -> used=True)")

    if auto_git_push and os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
                check=True,
            )
            subprocess.run(["git", "add", "stocks/music/"], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"chore(music): mark {chosen_meta['id']} and {mp3_path.name} as published [skip ci]"],
                check=True,
            )
            subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], check=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
            logger.info("Committed and pushed updated music queue & metadata_pool.json to GitHub.")
        except Exception as exc:
            logger.warning(f"Git commit/push warning: {exc}")


def resolve_description_with_chapters(chosen_mp3: Path, chosen_meta: Dict[str, Any]) -> str:
    """Replace {{TIMESTAMPS}} in chosen_meta['description'] with exact chapter timestamps from .chapters.json."""
    desc = chosen_meta.get("description", "")
    chapters_file = chosen_mp3.with_suffix(".chapters.json")
    ts_block = chosen_meta.get("default_timestamps", "00:00 Track 01")
    if chapters_file.exists():
        try:
            cdata = json.loads(chapters_file.read_text(encoding="utf-8"))
            if cdata.get("formatted_timestamps"):
                ts_block = cdata["formatted_timestamps"]
        except Exception:
            pass
    return desc.replace("{{TIMESTAMPS}}", ts_block)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build & upload 1-Hour Retro Music Video + 9:16 Short from Suno MP3.")
    parser.add_argument(
        "--auth-setup",
        action="store_true",
        help="Run one-time interactive Google OAuth2 browser login for the Music BGM YouTube Channel (.youtube_token_music.json).",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Target duration in seconds for output_1hour.mp4 (default: 3600).",
    )
    parser.add_argument(
        "--privacy",
        default="public",
        choices=["public", "unlisted", "private"],
        help="YouTube privacy status (default: public).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build videos locally without uploading to YouTube or moving files to done/.",
    )
    parser.add_argument(
        "--generate-sample-mp3",
        action="store_true",
        help="If stocks/music/queue/ is empty and SUNO_COOKIE is not set, synthesize a sample retro MP3 for testing.",
    )
    args = parser.parse_args()

    if args.auth_setup:
        run_music_oauth_setup()
        return 0

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    BG_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    chosen_mp3, chosen_meta, pool = pick_mp3_and_metadata(auto_suno=True)

    if not chosen_mp3 and args.generate_sample_mp3:
        sample_path = QUEUE_DIR / "sample_retro_highway_01.mp3"
        generate_synthesized_retro_test_mp3(sample_path, duration_sec=195)
        chosen_mp3, chosen_meta, pool = pick_mp3_and_metadata(auto_suno=False)

    if not chosen_mp3 or not chosen_meta:
        logger.info("No MP3 in stocks/music/queue/ and SUNO_COOKIE not active. Exiting cleanly (0).")
        return 0

    font_path = find_bold_font()

    with tempfile.TemporaryDirectory(prefix="music_build_") as tmp_s:
        tmp_dir = Path(tmp_s)
        bg_jpg = tmp_dir / "background_1280x720.jpg"
        bg_loop_mp4 = tmp_dir / "highway_loop_1280x720.mp4"
        hud_png = tmp_dir / "hud_1280x720.png"
        looped_m4a = tmp_dir / "looped_1hour.m4a"

        # Step 1: Load 1280x720 curated Japanese retro artwork
        download_background_image(chosen_meta, bg_jpg)

        # Step 2: Build 24fps motion loop
        build_highway_driving_loop_mp4(bg_jpg, chosen_meta, bg_loop_mp4, fps=24)

        # Step 3: Render HUD overlay and YouTube thumbnail
        render_16x9_hud_and_thumb(bg_jpg, chosen_meta, hud_png, OUTPUT_THUMB, font_path)

        # Step 4: Build looped 1-hour audio + 16:9 video (`output_1hour.mp4`)
        build_1hour_loop_audio(chosen_mp3, looped_m4a, target_duration_sec=args.duration)
        build_1hour_video(bg_loop_mp4, hud_png, looped_m4a, OUTPUT_1HOUR, duration_sec=args.duration)

        # Step 5: Build 9:16 vertical Short (`output_short.mp4`) from 30s..60s of the MP3 with live highway motion
        build_short_video(bg_jpg, bg_loop_mp4, chosen_mp3, chosen_meta, OUTPUT_SHORT, font_path)

    full_description = resolve_description_with_chapters(chosen_mp3, chosen_meta)

    if args.dry_run:
        logger.info("Dry-run complete! Videos generated at:")
        logger.info(f"  - 1-Hour Video : {OUTPUT_1HOUR}")
        logger.info(f"  - Short Video  : {OUTPUT_SHORT}")
        logger.info(f"  - Thumbnail    : {OUTPUT_THUMB}")
        return 0

    # Step 6: Upload both videos to YouTube & move MP3 to done/
    try:
        youtube = get_youtube_service()
        long_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_1HOUR,
            title=chosen_meta["title"],
            description=full_description,
            tags=chosen_meta.get("tags", []),
            privacy_status=args.privacy,
            thumbnail_path=OUTPUT_THUMB,
        )

        short_title = chosen_meta.get(
            "short_title",
            f"{chosen_meta.get('target_badge', '【40代・50代必見】')}{chosen_meta.get('thumb_main', '青春BGM')} 🎧本編1時間はチャンネルへ！ #Shorts",
        )
        short_desc = (
            f"🎧 本編（全16曲ノンストップ・1時間耐久フルアルバム）はこちら 👉 https://youtu.be/{long_id}\n\n"
            f"{full_description}"
        )
        short_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_SHORT,
            title=short_title,
            description=short_desc,
            tags=chosen_meta.get("tags", []) + ["Shorts", "YouTubeShorts"],
            privacy_status=args.privacy,
            thumbnail_path=None,
        )
    except Exception as exc:
        err_s = str(exc)
        if "uploadLimitExceeded" in err_s or "quotaExceeded" in err_s or "credentials not configured" in err_s:
            logger.warning(f"Deferring YouTube upload ({err_s}); keeping '{chosen_mp3.name}' in stocks/music/queue/ for next run.")
            return 0
        raise

    mark_done_and_git_push(
        mp3_path=chosen_mp3,
        chosen_meta=chosen_meta,
        pool=pool,
        long_vid_id=long_id,
        short_vid_id=short_id,
        auto_git_push=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
