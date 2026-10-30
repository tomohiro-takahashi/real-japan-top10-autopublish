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

from suno_auto_generator import WESTERN_AOR_VOCAL_LYRICS, SunoUnofficialClient

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
OUTPUT_SHORT_MEDLEY = BASE_DIR / "output_short_medley.mp4"
OUTPUT_THUMB = BASE_DIR / "output_music_thumb.jpg"

TOKEN_FILE_MUSIC = BASE_DIR / ".youtube_token_music.json"
TOKEN_FILE_FALLBACK = BASE_DIR / ".youtube_token_overseas_japan.json"
CLIENT_SECRET_FILE_MUSIC = BASE_DIR / "client_secret_music.json"
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
            archive_root = QUEUE_DIR.parent / "archive"
            pool_mp3s = sorted(
                [p for p in archive_root.rglob("*.mp3") if p.is_file() and p.stat().st_size > 500_000]
            )
            if pool_mp3s:
                meta_id = chosen_meta.get("id", "music_track")
                offset = sum(ord(ch) for ch in meta_id) % len(pool_mp3s)
                rotated = pool_mp3s[offset:] + pool_mp3s[:offset]
                target_n = int(os.environ.get("SUNO_BATCHES_PER_VIDEO", "8")) * 2
                tracks_to_use = [rotated[i % len(rotated)] for i in range(target_n)]
                logger.info(
                    f"Assembling fallback {target_n}-track album master for {meta_id} from {len(pool_mp3s)} archived Suno Pro tracks..."
                )
                fallback_master = suno_client._assemble_album_master(chosen_meta, tracks_to_use, QUEUE_DIR)
                if fallback_master and fallback_master.exists():
                    mp3_files = [fallback_master]

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
        im = im.resize((1920, 1080), Image.Resampling.LANCZOS)
        im = ImageEnhance.Sharpness(im).enhance(1.25)
        im.save(out_jpg, "JPEG", quality=97)
        logger.info(f"Loaded curated Japanese retro master illustration (1920x1080): {curated.name} -> {out_jpg.name}")
        return out_jpg

    prompt = meta.get(
        "image_prompt",
        "90s retro anime style aesthetic, lo-fi vintage illustration, midnight Tokyo highway, sports car, neon lights, 16:9",
    )
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true"
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
            im = im.resize((1920, 1080), Image.Resampling.LANCZOS)
            im.save(out_jpg, "JPEG", quality=96)
            logger.info(f"Downloaded Pollinations background image: {out_jpg} ({im.size})")
            return out_jpg
        except Exception as exc:
            logger.warning(f"Pollinations download attempt {attempt}/2 failed ({exc}).")
            time.sleep(2.0)

    logger.info("Using procedural 90s Retro Anime / Synthwave background illustration fallback.")
    return render_procedural_retro_artwork(meta, out_jpg, 1920, 1080)


def find_matching_flow_video(meta: Dict[str, Any]) -> Optional[Path]:
    """
    Check `stocks/music/bg_videos/` for a Google Flow / Veo MP4 loop matching the 6 genres.
    Matches `eurobeat*.mp4`, `disco*.mp4`, `tkrave*.mp4`, `citypop80s*.mp4`, `urban90s*.mp4`, `arcade*.mp4`.
    """
    if not BG_VIDEOS_DIR.exists():
        return None
    all_mp4s = sorted([p for p in BG_VIDEOS_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"])
    if not all_mp4s:
        return None

    genre = meta.get("genre", "").lower()
    if "eurobeat" in genre:
        keys = ["eurobeat"]
    elif "disco" in genre or "boogie" in genre:
        keys = ["disco"]
    elif "rave" in genre or "tk " in genre or "synth dance" in genre:
        keys = ["tkrave", "rave"]
    elif "urban" in genre or "mellow" in genre or "shibuya" in genre:
        keys = ["urban90s", "urban"]
    elif "arcade" in genre or "fusion" in genre:
        keys = ["arcade", "fusion"]
    else:
        keys = ["citypop80s", "citypop"]

    matched = [p for p in all_mp4s if any(k in p.stem.lower() for k in keys)]
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
    Build a seamless native 1920x1080 motion loop MP4:
    - Priority 1: If `stocks/music/bg_videos/` has a Flow `.mp4` video, converts it into a seamless
      Ping-Pong (forward + reverse) 1920x1080@24fps loop so there is zero jump cut!
    - Priority 2: Preserves 100% of the curated master illustration (`bg_jpg`) and animates it at native 1920x1080@24fps
      (96 frames / 4.0s seamless cycle) with smooth breathing camera drift, pulsing neon highlight bloom,
      and atmospheric drifting light trails / bokeh particles.
    """
    flow_mp4 = find_matching_flow_video(meta)
    if flow_mp4 is not None:
        logger.info(f"Building seamless 24fps master loop (1920x1080) from Google Flow video: {flow_mp4.name} ...")
        vf = (
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,fps={fps},setsar=1,"
            f"vignette=PI/7,format=yuv420p[vout]"
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
                "-profile:v",
                "high",
                "-level",
                "4.2",
                "-crf",
                "16",
                str(out_loop_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return out_loop_mp4

    genre = meta.get("genre", "90s Eurobeat")
    if "Eurobeat" in genre or "Arcade" in genre or "Fusion" in genre:
        motion_mode = "driving"  # Rhythmic highway driving drift + passing warm sodium streetlight sweep
        total_frames = 96        # 4.0s cycle @ 24fps
        pan_x, pan_y = 24.0, 9.0
        pulse_amp, pulse_freq = 0.042, 2.0
    elif "Disco" in genre or "Rave" in genre or "Dance" in genre:
        motion_mode = "groove"   # Lounge / Car-stereo groove sway + warm VU meter / backlight pulse
        total_frames = 108       # 4.5s cycle @ 24fps
        pan_x, pan_y = 18.0, 7.5
        pulse_amp, pulse_freq = 0.036, 2.0
    else:
        motion_mode = "mellow"   # Ultra-slow meditative breath for City Pop / AOR / Study cassette
        total_frames = 144       # 6.0s cycle @ 24fps
        pan_x, pan_y = 13.5, 6.0
        pulse_amp, pulse_freq = 0.022, 1.0

    logger.info(
        f"Synthesizing 24fps Native 1080p Calm 35mm Film Motion Loop [{motion_mode}] ({total_frames} frames / {total_frames/fps:.1f}s cycle)..."
    )
    W, H = 1920, 1080
    OW, OH = 2004, 1128
    overscan_im = Image.open(bg_jpg).convert("RGB").resize((OW, OH), Image.Resampling.LANCZOS)

    with tempfile.TemporaryDirectory(prefix="calm_frames_") as tmp_s:
        frames_dir = Path(tmp_s)

        for f_idx in range(total_frames):
            t_norm = f_idx / float(total_frames)  # 0.0 .. 1.0
            theta = 2.0 * math.pi * t_norm

            # 1. Smooth camera breath matched to genre tempo
            cx_off = int((OW - W) * 0.5 + pan_x * math.sin(theta))
            cy_off = int((OH - H) * 0.5 + pan_y * math.cos(theta))
            frame = overscan_im.crop((cx_off, cy_off, cx_off + W, cy_off + H))

            # 2. Warm analog exposure & color warmth pulse matched to genre beat
            pulse = 1.0 + pulse_amp * math.sin(pulse_freq * theta)
            frame = ImageEnhance.Brightness(frame).enhance(pulse)
            frame = ImageEnhance.Color(frame).enhance(1.0 + (pulse_amp * 0.6) * math.cos(theta))

            # 3. Genre-specific subtle atmospheric light reflection
            if motion_mode == "driving":
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay, "RGBA")
                band_cx = int(W * (1.15 - 1.30 * t_norm))
                for b_off in range(-135, 136, 9):
                    dist = abs(b_off) / 135.0
                    a_band = int(16 * (1.0 - dist) ** 2)
                    if a_band > 0:
                        x0_b = band_cx + b_off - 105
                        x1_b = band_cx + b_off + 105
                        od.line([(x0_b, 0), (x1_b, int(H * 0.68))], fill=(245, 195, 110, a_band), width=9)
                frame_rgba = frame.convert("RGBA")
                frame_rgba.alpha_composite(overlay)
                frame = frame_rgba.convert("RGB")
            elif motion_mode == "groove":
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay, "RGBA")
                g_alpha = int(14 * (0.5 + 0.5 * math.sin(2.0 * theta)))
                if g_alpha > 0:
                    od.ellipse((int(W * 0.22), int(H * 0.35), int(W * 0.78), int(H * 0.82)), fill=(235, 185, 95, g_alpha))
                    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=54))
                    frame_rgba = frame.convert("RGBA")
                    frame_rgba.alpha_composite(overlay)
                    frame = frame_rgba.convert("RGB")

            frame.save(frames_dir / f"f_{f_idx:04d}.jpg", "JPEG", quality=96)

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
                "-profile:v",
                "high",
                "-level",
                "4.2",
                "-crf",
                "16",
                str(out_loop_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    logger.info(f"Built calm 35mm film motion loop [{motion_mode}]: {out_loop_mp4.name}")
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
    sub_txt = meta.get("thumb_sub") or "MIDNIGHT COCKPIT  ｜  あの頃の夜と音楽"
    if meta.get("_under_15m") and ("60分" in sub_txt or "16曲" in sub_txt):
        sub_txt = "MIDNIGHT COCKPIT  ｜  あの頃の夜と音楽"
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
    1) An understated, eye-friendly Japanese Mincho/Gothic HUD overlay (`hud_png`, 1280x720 RGBA) for the 1-hour video
    2) A calm, mature 35mm-film Japanese Record-Jacket / AOR CD-style thumbnail (`thumb_jpg`, 1280x720)
       aimed at Japanese 40代・50代 adults.
    """
    cjk_reg_path = find_cjk_font() or font_path
    cjk_mincho_path = find_cjk_mincho_font() or cjk_reg_path

    era_label, catch_txt, main_txt, sub_txt = _extract_ja_parts(meta)

    # =========================================================================
    # 1) 16:9 VIDEO OVERLAY HUD (`hud_png`, Native 1920x1080 Full HD)
    #    NOTE: Also serves as the auto-captured YouTube thumbnail frame on unverified channels!
    # =========================================================================
    HW, HH = 1920, 1080
    hud = Image.new("RGBA", (HW, HH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud, "RGBA")

    # Subtle top vignette (y=0..158)
    for y in range(0, 158):
        u = 1.0 - (y / 158.0)
        alpha = int(110 * (u ** 1.6))
        draw.line([(0, y), (HW, y)], fill=(4, 6, 12, alpha))

    # Smooth dark gradient at the bottom (y=540..1080) so large Mincho title & waveform are crisp
    for y in range(540, HH):
        u = (y - 540) / 540.0
        alpha = int(235 * (u ** 1.35))
        draw.line([(0, y), (HW, y)], fill=(4, 6, 12, alpha))

    # Top-left understated editorial label (warm amber vertical bar + crisp text)
    f_hud_top = load_font(cjk_reg_path, 27)
    draw.rectangle((72, 57, 78, 99), fill=(217, 179, 108, 245))
    _draw_soft_shadow_text(
        hud,
        (99, 61),
        era_label,
        font=f_hud_top,
        fill=(226, 214, 185, 245),
        blur_radius=6,
    )

    # Top-right permanent Subscribe & Save Banner (fixed on screen throughout the entire video)
    draw = ImageDraw.Draw(hud, "RGBA")
    sub_bx0, sub_by0, sub_bx1, sub_by1 = 1236, 46, 1848, 110
    draw.rounded_rectangle(
        (sub_bx0, sub_by0, sub_bx1, sub_by1),
        radius=32,
        fill=(10, 14, 24, 215),
        outline=(217, 179, 108, 185),
        width=2,
    )
    # Red/Crimson YouTube-style play/subscribe pill on the left side of the banner
    draw.rounded_rectangle(
        (sub_bx0 + 10, sub_by0 + 9, sub_bx0 + 218, sub_by1 - 9),
        radius=23,
        fill=(198, 40, 40, 245),
    )
    # White play triangle inside the red pill
    tri_cx, tri_cy = sub_bx0 + 36, (sub_by0 + sub_by1) // 2
    draw.polygon(
        [(tri_cx - 6, tri_cy - 8), (tri_cx - 6, tri_cy + 8), (tri_cx + 8, tri_cy)],
        fill=(255, 255, 255, 255),
    )
    f_sub_btn = load_font(cjk_reg_path, 21)
    draw.text((sub_bx0 + 52, sub_by0 + 20), "チャンネル登録", font=f_sub_btn, fill=(255, 255, 255, 255))
    f_sub_msg = load_font(cjk_reg_path, 21)
    draw.text(
        (sub_bx0 + 234, sub_by0 + 20),
        "毎晩80s・90s名曲を追加中｜保存して聴く",
        font=f_sub_msg,
        fill=(238, 224, 190, 248),
    )

    is_vocal = bool(meta.get("vocal_playlist") or "洋楽" in meta.get("title", "") or "歌詞" in meta.get("title", ""))
    if is_vocal and WESTERN_AOR_VOCAL_LYRICS:
        # Render an understated, classy Lyrics & Japanese Translation card in the upper-right/center calm region
        song_idx = hash(meta.get("id", "0")) % len(WESTERN_AOR_VOCAL_LYRICS)
        s_primary = WESTERN_AOR_VOCAL_LYRICS[song_idx]
        s_second = WESTERN_AOR_VOCAL_LYRICS[(song_idx + 1) % len(WESTERN_AOR_VOCAL_LYRICS)]
        draw = ImageDraw.Draw(hud, "RGBA")
        lx0, ly0, lx1, ly1 = 72, 162, 1280, 408
        draw.rounded_rectangle(
            (lx0, ly0, lx1, ly1),
            radius=22,
            fill=(8, 12, 22, 158),
            outline=(217, 179, 108, 130),
            width=2,
        )
        f_lhead = load_font(cjk_reg_path, 22)
        f_len = load_font(font_path, 27)
        f_lja = load_font(cjk_mincho_path, 25)
        draw.text((lx0 + 30, ly0 + 20), "♪ LYRICS & TRANSLATION  ｜  歌詞・日本語対訳", font=f_lhead, fill=(217, 179, 108, 245))
        draw.line([(lx0 + 30, ly0 + 56), (lx1 - 30, ly0 + 56)], fill=(217, 179, 108, 90), width=1)
        _draw_soft_shadow_text(
            hud,
            (lx0 + 30, ly0 + 70),
            f'"{s_primary["lyric_card_en"].strip()}"',
            font=f_len,
            fill=(252, 250, 245, 250),
            blur_radius=4,
        )
        _draw_soft_shadow_text(
            hud,
            (lx0 + 30, ly0 + 110),
            s_primary["lyric_card_ja"],
            font=f_lja,
            fill=(235, 213, 160, 245),
            blur_radius=4,
        )
        _draw_soft_shadow_text(
            hud,
            (lx0 + 30, ly0 + 158),
            f'"{s_second["lyric_card_en"].strip()}"',
            font=f_len,
            fill=(240, 244, 248, 235),
            blur_radius=4,
        )
        _draw_soft_shadow_text(
            hud,
            (lx0 + 30, ly0 + 196),
            s_second["lyric_card_ja"],
            font=f_lja,
            fill=(226, 214, 185, 235),
            blur_radius=4,
        )

    max_text_w = 1740
    draw = ImageDraw.Draw(hud, "RGBA")

    # 1. Emotional Catchphrase (Mincho in warm champagne gold)
    f_hud_catch = fit_font_for_width(draw, catch_txt, cjk_mincho_path, 42, 30, max_text_w)
    _draw_soft_shadow_text(
        hud,
        (72, 711),
        catch_txt,
        font=f_hud_catch,
        fill=(235, 213, 160, 255),
        blur_radius=7,
    )

    # 2. Main Japanese Headline (Refined Mincho in warm ivory-white — native 1080p!)
    draw = ImageDraw.Draw(hud, "RGBA")
    f_hud_main = fit_font_for_width(draw, main_txt, cjk_mincho_path, 87, 54, max_text_w)
    _draw_soft_shadow_text(
        hud,
        (69, 777),
        main_txt,
        font=f_hud_main,
        fill=(252, 250, 245, 255),
        blur_radius=10,
        stroke_width=2,
        stroke_fill=(8, 10, 16, 225),
    )

    # 3. Bottom Album Spec Line & Minimalist Spec Pill (below waveform y=906..954)
    draw = ImageDraw.Draw(hud, "RGBA")
    f_hud_sub = fit_font_for_width(draw, sub_txt, cjk_reg_path, 30, 22, 1350)
    _draw_soft_shadow_text(
        hud,
        (72, 981),
        sub_txt,
        font=f_hud_sub,
        fill=(203, 213, 225, 238),
        blur_radius=4,
    )

    draw = ImageDraw.Draw(hud, "RGBA")
    if is_vocal:
        stamp_txt = "NO ADS  ｜  歌詞・和訳付き"
        f_stamp = load_font(cjk_reg_path, 23)
    else:
        stamp_txt = "NO ADS  ｜  NON-STOP MIX" if meta.get("_under_15m") else "NO ADS  ｜  60 MIN MIX"
        f_stamp = load_font(cjk_reg_path, 23)
    tb_st = draw.textbbox((0, 0), stamp_txt, font=f_stamp)
    st_w = (tb_st[2] - tb_st[0]) + 54
    st_x0 = HW - 72 - st_w
    draw.rounded_rectangle(
        (st_x0, 969, st_x0 + st_w, 1023),
        radius=27,
        fill=(10, 12, 18, 175),
        outline=(217, 179, 108, 145),
        width=2,
    )
    draw.text(
        (st_x0 + 27, 983),
        stamp_txt,
        font=f_stamp,
        fill=(226, 214, 185, 240),
    )
    hud.save(hud_png, "PNG")

    # =========================================================================
    # 2) 16:9 YOUTUBE THUMBNAIL (`thumb_jpg`) — Calm Adult 35mm Film / CD Jacket
    # =========================================================================
    base = Image.open(bg_jpg).convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)

    grad = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grad, "RGBA")

    # Subtle top vignette (y=0..105)
    for y in range(0, 105):
        u = 1.0 - (y / 105.0)
        alpha = int(115 * (u ** 1.6))
        g_draw.line([(0, y), (1280, y)], fill=(4, 6, 12, alpha))

    # Smooth bottom gradient (y=370..720) — zero boxy borders!
    for y in range(370, 720):
        u = (y - 370) / 350.0
        alpha = int(238 * (u ** 1.35))
        g_draw.line([(0, y), (1280, y)], fill=(4, 6, 12, alpha))

    base.alpha_composite(grad)
    t_draw = ImageDraw.Draw(base, "RGBA")

    # A. Top-Left Understated Archive Tag (Warm Amber Vertical Bar + Crisp Text)
    f_era = load_font(cjk_reg_path, 19)
    t_draw.rectangle((48, 38, 52, 66), fill=(217, 179, 108, 245))
    _draw_soft_shadow_text(
        base,
        (66, 40),
        era_label,
        font=f_era,
        fill=(226, 214, 185, 245),
        blur_radius=4,
    )

    # B. Bottom-Left Mature Mincho Typography
    t_draw = ImageDraw.Draw(base, "RGBA")
    max_text_w = 1160

    # 1. Emotional Catchphrase (Mincho in warm champagne gold)
    f_catch = fit_font_for_width(t_draw, catch_txt, cjk_mincho_path, 28, 20, max_text_w)
    _draw_soft_shadow_text(
        base,
        (48, 490),
        catch_txt,
        font=f_catch,
        fill=(235, 213, 160, 255),
        blur_radius=5,
    )

    # 2. Main Japanese Headline (Refined Mincho in warm ivory-white)
    t_draw = ImageDraw.Draw(base, "RGBA")
    f_main = fit_font_for_width(t_draw, main_txt, cjk_mincho_path, 58, 36, max_text_w)
    _draw_soft_shadow_text(
        base,
        (46, 534),
        main_txt,
        font=f_main,
        fill=(252, 250, 245, 255),
        blur_radius=7,
        stroke_width=1,
        stroke_fill=(8, 10, 16, 225),
    )

    # 3. Thin Champagne-Gold Divider Line (y=622)
    t_draw = ImageDraw.Draw(base, "RGBA")
    t_draw.line([(48, 622), (880, 622)], fill=(217, 179, 108, 130), width=1)

    # 4. Bottom Album Spec Line (Clean Gothic in warm silver)
    f_sub = fit_font_for_width(t_draw, sub_txt, cjk_reg_path, 20, 15, 900)
    _draw_soft_shadow_text(
        base,
        (48, 636),
        sub_txt,
        font=f_sub,
        fill=(203, 213, 225, 238),
        blur_radius=3,
    )

    # C. Bottom-Right Minimalist Spec Pill
    t_draw = ImageDraw.Draw(base, "RGBA")
    if is_vocal:
        stamp_txt = "NO ADS  ｜  歌詞・和訳付き"
    else:
        stamp_txt = "NO ADS  ｜  NON-STOP MIX" if meta.get("_under_15m") else "NO ADS  ｜  60 MIN MIX"
    f_stamp = load_font(cjk_reg_path, 15)
    tb_st = t_draw.textbbox((0, 0), stamp_txt, font=f_stamp)
    st_w = (tb_st[2] - tb_st[0]) + 36
    st_x0 = 1280 - 48 - st_w
    t_draw.rounded_rectangle(
        (st_x0, 628, st_x0 + st_w, 664),
        radius=18,
        fill=(10, 12, 18, 175),
        outline=(217, 179, 108, 145),
        width=1,
    )
    t_draw.text(
        (st_x0 + 18, 638),
        stamp_txt,
        font=f_stamp,
        fill=(226, 214, 185, 240),
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
    Synthesize the 16:9 Video (`output_1hour.mp4`, Native 1920x1080 Full HD) in ~5 seconds via 2-Stage Master Loop Stream-Copy:
    Stage 1: Composite `bg_loop_mp4` + `hud_png` + 16s waveform + subtle 35mm grain into a single 16-second H.264 master loop (~3s).
    Stage 2: Stream-copy (`-stream_loop -1 -c:v copy -c:a copy`) the master loop across `duration_sec` (~2s, ~350MB for 2 hours).
    """
    logger.info(f"Rendering native 16:9 1080p Full HD calm adult music video ({duration_sec}s): {out_mp4} ...")
    fps = 24
    loop_dur = max(8.0, min(20.0, get_audio_duration(bg_loop_mp4) or 16.0))

    with tempfile.TemporaryDirectory(prefix="master_loop_") as tmp_s:
        master_loop = Path(tmp_s) / "composited_loop.mp4"
        filter_complex = (
            f"[0:v]setpts=PTS-STARTPTS[bg];"
            f"[bg][1:v]overlay=0:0[bghud];"
            f"[2:a]atrim=0:{loop_dur:.2f},asetpts=PTS-STARTPTS,"
            f"showwaves=s=1788x48:mode=cline:rate={fps}:scale=sqrt:colors=0xd9b36c,format=rgba,"
            f"colorchannelmixer=aa=0.42[sw];"
            f"[bghud][sw]overlay=66:906:shortest=1,noise=c0s=2:c0f=t,unsharp=3:3:0.45:3:3:0.0,format=yuv420p[vout]"
        )
        cmd_stage1 = [
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
            "-an",
            "-t",
            f"{loop_dur:.2f}",
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-crf",
            "18",
            "-g",
            str(fps),
            "-keyint_min",
            str(fps),
            "-sc_threshold",
            "0",
            "-pix_fmt",
            "yuv420p",
            str(master_loop),
        ]
        subprocess.run(cmd_stage1, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cmd_stage2 = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(master_loop),
            "-i",
            str(looped_audio_m4a),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-t",
            str(duration_sec),
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            "-shortest",
            str(out_mp4),
        ]
        subprocess.run(cmd_stage2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info(f"Completed native 16:9 1080p video: {out_mp4} ({out_mp4.stat().st_size / (1024*1024):.1f} MB)")
    return out_mp4


def _make_short_cinema_gradient_overlay(width: int = 1080, height: int = 1920) -> Image.Image:
    """
    Create a transparent 1080x1920 RGBA gradient mask for full-screen 9:16 live cinema video:
    - Top zone (y=0..350): soft dark vignette
    - Upper-mid windshield zone (y=350..880): nearly transparent (alpha=35) so the live moving highway shines through
    - Lower-mid eye-level reading zone (y=880..1920): smooth cinema dark gradient for crisp, box-free typography
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for y in range(height):
        if y < 350:
            a = int(155 - (y / 350.0) * 115)
        elif y < 860:
            a = 38
        elif y < 1440:
            a = int(38 + ((y - 860) / 580.0) * 182)
        else:
            a = 225
        draw.line([(0, y), (width, y)], fill=(6, 9, 18, a))
    return overlay


def render_short_vertical_hud(
    bg_jpg: Path,
    meta: Dict[str, Any],
    out_vertical_hud_png: Path,
    font_path: str,
    act_idx: int = 1,
) -> Path:
    """
    Design A (案A：全面シネマ背景＋映画字幕・特大曲名型, 1080x1920 RGBA overlay):
    - Full-screen 9:16 live motion video plays underneath across the entire 1080x1920 canvas (no small 16:9 box).
    - Upper eye-level (y=295..565): Crimson pill badge + large emotional Mincho hook.
    - Lower-center eye-level (y=930..1440): Gold divider line + Giant Song Title & Artist + 4-Act movie subtitles.
    - Bottom (y=1475..1560): Sleek gold-outlined CTA pill + live audio waveform below at y=1580.
    """
    SW, SH = 1080, 1920
    canvas = _make_short_cinema_gradient_overlay(SW, SH)

    cjk_reg_path = find_cjk_font() or font_path
    cjk_heavy_path = find_cjk_heavy_font() or cjk_reg_path
    cjk_mincho_path = find_cjk_mincho_font() or cjk_reg_path

    era_label, catch_txt, main_txt, sub_txt = _extract_ja_parts(meta)
    real_tracks = meta.get("tracks") or []
    track_titles = meta.get("track_titles") or []
    is_vocal = bool(
        real_tracks
        or meta.get("vocal_playlist")
        or "洋楽" in meta.get("title", "")
        or "歌詞" in meta.get("title", "")
    )
    song_idx = hash(meta.get("id", "0")) % len(WESTERN_AOR_VOCAL_LYRICS) if WESTERN_AOR_VOCAL_LYRICS else 0
    s_primary = WESTERN_AOR_VOCAL_LYRICS[song_idx] if WESTERN_AOR_VOCAL_LYRICS else {}
    s_second = WESTERN_AOR_VOCAL_LYRICS[(song_idx + 1) % len(WESTERN_AOR_VOCAL_LYRICS)] if WESTERN_AOR_VOCAL_LYRICS else {}

    draw = ImageDraw.Draw(canvas, "RGBA")

    # 1. Top-Center Crimson Badge at y=296..360 (below YouTube Shorts top UI dead-zone)
    badge_top = (meta.get("target_badge") or "40代・50代が涙した名曲").replace("【", "").replace("】", "").strip()
    if len(badge_top) > 18:
        badge_top = "40代・50代が涙した名曲"
    f_btop = fit_font_for_width(draw, badge_top, cjk_heavy_path, 28, 20, SW - 240)
    tb_bt = draw.textbbox((0, 0), badge_top, font=f_btop)
    btw = (tb_bt[2] - tb_bt[0]) + 72
    btx0 = (SW - btw) // 2
    draw.rounded_rectangle((btx0, 296, btx0 + btw, 360), radius=32, fill=(185, 28, 28, 238))
    draw.text(((SW - (tb_bt[2] - tb_bt[0])) // 2, 311), badge_top, font=f_btop, fill=(255, 255, 255, 255))

    # 2. Large Mincho Emotional Hook at y=395..565
    hook_l1 = "イントロ3秒で、"
    hook_l2 = "あの頃の夜が蘇る——"
    if catch_txt and len(catch_txt) <= 18:
        hook_l1 = catch_txt
    if main_txt and len(main_txt) <= 16:
        hook_l2 = main_txt

    f_h1 = fit_font_for_width(draw, hook_l1, cjk_mincho_path, 64, 38, SW - 140)
    f_h2 = fit_font_for_width(draw, hook_l2, cjk_mincho_path, 66, 38, SW - 140)
    _draw_soft_shadow_text(canvas, (84, 396), hook_l1, font=f_h1, fill=(255, 255, 255, 255), blur_radius=10)
    _draw_soft_shadow_text(canvas, (84, 488), hook_l2, font=f_h2, fill=(253, 224, 71, 255), blur_radius=10)

    # 3. Lower-Center Giant Song Typography (y=930..1215)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.line([(84, 932), (SW - 84, 932)], fill=(253, 224, 71, 210), width=3)

    # 4 Step Progress Dots above the right end of the gold divider
    for step_i in range(1, 5):
        dx = SW - 210 + (step_i - 1) * 36
        dy = 906
        r_dot = 8 if step_i == act_idx else 5
        col_dot = (253, 224, 71, 255) if step_i == act_idx else (148, 163, 184, 160)
        draw.ellipse((dx - r_dot, dy - r_dot, dx + r_dot, dy + r_dot), fill=col_dot)

    if real_tracks:
        tr0 = real_tracks[0]
        big_title_1 = tr0["title"]
        big_title_2 = f"{tr0['artist']}"
        big_sub = f"邦題：{tr0.get('ja_title', '')}  ｜  80s-90s 洋楽レジェンド名曲"
    elif is_vocal and s_primary:
        big_title_1 = s_primary.get("title_en", "Midnight Bayshore")
        big_title_2 = f"邦題：{s_primary.get('title_ja', '真夜中のベイショア')}"
        big_sub = f"{era_label}  ｜  英語詞・日本語対訳付き"
    else:
        t0_raw = track_titles[0] if track_titles else "Midnight Bayshore Express (1987)"
        if "—" in t0_raw:
            p_en, p_ja = [x.strip() for x in t0_raw.split("—", 1)]
        elif "-" in t0_raw:
            p_en, p_ja = [x.strip() for x in t0_raw.split("-", 1)]
        else:
            p_en, p_ja = t0_raw, main_txt
        big_title_1 = p_en
        big_title_2 = p_ja
        big_sub = f"{era_label}  ｜  {sub_txt}"

    max_tw = SW - 168
    f_bt1 = fit_font_for_width(draw, big_title_1, font_path, 68, 36, max_tw)
    f_bt2 = fit_font_for_width(draw, big_title_2, cjk_heavy_path, 52, 30, max_tw)
    f_bsub = fit_font_for_width(draw, big_sub, cjk_heavy_path, 34, 22, max_tw)

    _draw_soft_shadow_text(canvas, (84, 962), big_title_1, font=f_bt1, fill=(255, 255, 255, 255), blur_radius=8)
    _draw_soft_shadow_text(canvas, (84, 1054), big_title_2, font=f_bt2, fill=(253, 224, 71, 255), blur_radius=8)
    _draw_soft_shadow_text(canvas, (84, 1142), big_sub, font=f_bsub, fill=(226, 232, 240, 250), blur_radius=6)

    # 4. 4-Act Movie Trailer Subtitles at y=1245..1420 (changes every 5.0s)
    if act_idx == 1:
        if real_tracks:
            sub_1 = "「夜の首都高、FMから流れた瞬間に"
            sub_2 = "  助手席の空気が変わった永遠の名曲」"
        elif is_vocal:
            sub_1 = f"“{s_primary.get('lyric_card_en', 'Breathe in deep, the weekend has finally begun...').strip()}”"
            sub_2 = f"「{s_primary.get('lyric_card_ja', '深く息を吸い込んでごらん、ようやく週末が始まったから——')}」"
        else:
            sub_1 = "「カセットテープを押し込んだ瞬間、"
            sub_2 = "  1987年の夜のハイウェイが目の前に広がる」"
    elif act_idx == 2:
        if real_tracks and len(real_tracks) >= 3:
            sub_1 = f"他収録：{real_tracks[1]['artist']}「{real_tracks[1]['title']}」"
            sub_2 = f"{real_tracks[2]['artist']}「{real_tracks[2]['title']}」など全{len(real_tracks)}曲"
        elif is_vocal and s_second:
            sub_1 = f"“{s_second.get('lyric_card_en', 'City lights reflecting on the midnight bayshore...').strip()}”"
            sub_2 = f"「{s_second.get('lyric_card_ja', '午前0時の湾岸線、街の灯りがフロントガラスに溶けていく——')}」"
        else:
            sub_1 = "「ナトリウム灯が流れる午前0時のコックピット、"
            sub_2 = "  サックスとアナログシンセが心に沁みる夜」"
    elif act_idx == 3:
        sub_1 = "「本編は全曲フル尺・ノンストップ高音質収録"
        sub_2 = "  深夜ドライブ・晩酌・作業用BGMの永久保存版」"
    else:
        sub_1 = "「続きのフル音源（長時間メドレー）は、"
        sub_2 = "  すぐ下の『▶ 関連動画リンク』から今すぐ聴けます」"

    draw = ImageDraw.Draw(canvas, "RGBA")
    f_s1 = fit_font_for_width(draw, sub_1, cjk_mincho_path, 40, 24, max_tw)
    f_s2 = fit_font_for_width(draw, sub_2, cjk_mincho_path, 40, 24, max_tw)
    _draw_soft_shadow_text(canvas, (84, 1248), sub_1, font=f_s1, fill=(255, 255, 255, 255), blur_radius=6)
    _draw_soft_shadow_text(
        canvas,
        (84, 1316),
        sub_2,
        font=f_s2,
        fill=(167, 243, 208, 255) if act_idx >= 3 else (255, 255, 255, 255),
        blur_radius=6,
    )

    # 5. Sleek Gold-Bordered CTA Pill at y=1470..1555
    draw = ImageDraw.Draw(canvas, "RGBA")
    cta_ja = "▶ 本編フル音源メドレーは下の関連動画へ"
    f_cta = fit_font_for_width(draw, cta_ja, cjk_heavy_path, 32, 22, SW - 220)
    tb_cta = draw.textbbox((0, 0), cta_ja, font=f_cta)
    cw = (tb_cta[2] - tb_cta[0]) + 110
    cx0_b = (SW - cw) // 2
    draw.rounded_rectangle(
        (cx0_b, 1470, cx0_b + cw, 1554),
        radius=42,
        fill=(10, 14, 24, 205),
        outline=(253, 224, 71, 235),
        width=3,
    )
    draw.text(((SW - (tb_cta[2] - tb_cta[0])) // 2, 1494), cta_ja, font=f_cta, fill=(253, 224, 71, 255))

    canvas.save(out_vertical_hud_png, "PNG")
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
    Synthesize Short #1 (`output_short.mp4` — Design A: Full-Screen 9:16 Cinema + Giant Song Title & 4-Act Subtitles, 20s):
    - Scales `bg_loop_mp4` to fill the ENTIRE 1080x1920 vertical screen (no small 16:9 box).
    - Starts at 42.0s chorus climax with 0.08s instant full-volume drop.
    - Switches through 4 Cinema Subtitle scenes every 5.0s (`0-5s`, `5-10s`, `10-15s`, `15-20s`).
    """
    logger.info(f"Rendering Short #1 [Design A: Full-Screen Cinema Typography, 20s]: {out_short_mp4} ...")
    mp3_dur = get_audio_duration(src_mp3)
    start_sec = 42.0 if mp3_dur >= 65.0 else (30.0 if mp3_dur >= 52.0 else max(0.0, mp3_dur * 0.25))
    clip_dur = min(20.0, max(10.0, mp3_dur - start_sec))
    seg_d = clip_dur / 4.0

    with tempfile.TemporaryDirectory(prefix="music_short_a_") as tmp_s:
        tmp_dir = Path(tmp_s)
        hud_paths = []
        for act_i in range(1, 5):
            hp = tmp_dir / f"short_hud_act{act_i}.png"
            render_short_vertical_hud(bg_jpg, meta, hp, font_path, act_idx=act_i)
            hud_paths.append(hp)

        fps = 24
        t1 = seg_d
        t2 = seg_d * 2.0
        t3 = seg_d * 3.0
        filter_complex = (
            f"[0:v]scale=-2:1920:flags=lanczos,crop=1080:1920:(iw-1080)/2:0,setpts=PTS-STARTPTS[v1];"
            f"[v1][1:v]overlay=0:0:enable='lt(t,{t1:.2f})'[v_a1];"
            f"[v_a1][2:v]overlay=0:0:enable='between(t,{t1:.2f},{t2:.2f})'[v_a2];"
            f"[v_a2][3:v]overlay=0:0:enable='between(t,{t2:.2f},{t3:.2f})'[v_a3];"
            f"[v_a3][4:v]overlay=0:0:enable='gte(t,{t3:.2f})'[v2];"
            f"[5:a]atrim=start={start_sec:.2f}:duration={clip_dur:.2f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=0.08,afade=t=out:st={max(1.0, clip_dur - 0.8):.2f}:d=0.8[aud];"
            f"[aud]asplit=2[a_out][a_viz];"
            f"[a_viz]showwaves=s=880x60:mode=cline:rate={fps}:scale=sqrt:colors=0xd9b36c,format=rgba,"
            f"colorchannelmixer=aa=0.68[sw];"
            f"[v2][sw]overlay=100:1578:shortest=1,noise=c0s=3:c0f=t+u,unsharp=3:3:0.45:3:3:0.0,format=yuv420p[vout]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(bg_loop_mp4),
            "-i",
            str(hud_paths[0]),
            "-i",
            str(hud_paths[1]),
            "-i",
            str(hud_paths[2]),
            "-i",
            str(hud_paths[3]),
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
            "-movflags",
            "+faststart",
            str(out_short_mp4),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info(f"Completed Short #1 [Design A]: {out_short_mp4} ({out_short_mp4.stat().st_size / (1024*1024):.1f} MB)")
    return out_short_mp4


def _extract_three_medley_items(meta: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Return 3 `(artist_or_label, song_title_with_ja)` pairs for Design C (3-Song Chorus Medley Short).
    For Real Hits Mix, uses tracks #2, #3, #4 (or #1, #2, #3 if fewer) so Short #1 and Short #2 cover 4 famous hits!
    """
    real_tracks = meta.get("tracks") or []
    if len(real_tracks) >= 4:
        picked = [real_tracks[1], real_tracks[2], real_tracks[3]]
        return [(t["artist"], f"{t['title']}（{t.get('ja_title', '')}）") for t in picked]
    if len(real_tracks) >= 3:
        picked = real_tracks[:3]
        return [(t["artist"], f"{t['title']}（{t.get('ja_title', '')}）") for t in picked]

    track_titles = meta.get("track_titles") or []
    era_label, _, main_txt, _ = _extract_ja_parts(meta)
    items: List[Tuple[str, str]] = []
    for idx in range(3):
        raw_t = track_titles[idx] if idx < len(track_titles) else f"Midnight Groove Track 0{idx+1}"
        items.append((era_label, raw_t))
    return items


def render_short_medley_hud(
    meta: Dict[str, Any],
    out_hud_png: Path,
    font_path: str,
    active_idx: int = 0,
) -> Path:
    """
    Design C (案C：神曲サビ3連発カウントダウン型, 1080x1920 RGBA overlay):
    - Full-screen 9:16 live motion video plays underneath.
    - Upper eye-level (y=295..455): `【イントロで鳥肌】` + `夜のドライブ神曲 3連発` headline.
    - Center-lower eye-level (y=865..1440): 3 stacked Song Cards (`01`, `02`, `03`) where `active_idx` (0, 1, or 2)
      lights up in bright gold (`NOW PLAYING`) while the other two show `NEXT` / `LAST`.
    """
    SW, SH = 1080, 1920
    canvas = _make_short_cinema_gradient_overlay(SW, SH)

    cjk_reg_path = find_cjk_font() or font_path
    cjk_heavy_path = find_cjk_heavy_font() or cjk_reg_path
    _, _, main_txt, _ = _extract_ja_parts(meta)
    real_tracks = meta.get("tracks") or []

    top_kicker = "【イントロで鳥肌】" if real_tracks else "【サビ3連発メドレー】"
    top_headline = "80s-90s 洋楽神曲 3連発" if real_tracks else f"{main_txt[:13]} 3連発"

    _draw_soft_shadow_text(
        canvas,
        (75, 295),
        top_kicker,
        font=load_font(cjk_heavy_path, 50),
        fill=(253, 224, 71, 255),
        blur_radius=8,
    )
    draw = ImageDraw.Draw(canvas, "RGBA")
    f_head = fit_font_for_width(draw, top_headline, cjk_heavy_path, 54, 34, SW - 150)
    _draw_soft_shadow_text(
        canvas,
        (75, 372),
        top_headline,
        font=f_head,
        fill=(255, 255, 255, 255),
        blur_radius=8,
    )

    items = _extract_three_medley_items(meta)
    stage_labels = ["0:00~", "0:06~", "0:13~"]
    for i, (artist_str, song_str) in enumerate(items[:3]):
        y0 = 865 + i * 192
        y1 = y0 + 168
        num_str = f"0{i+1}"
        draw = ImageDraw.Draw(canvas, "RGBA")
        is_active = i == active_idx
        if is_active:
            draw.rounded_rectangle(
                (64, y0, SW - 64, y1),
                radius=24,
                fill=(15, 23, 42, 232),
                outline=(253, 224, 71, 255),
                width=4,
            )
            draw.rounded_rectangle((88, y0 + 24, 198, y1 - 24), radius=16, fill=(253, 224, 71, 255))
            draw.text((110, y0 + 46), num_str, font=load_font(font_path, 52), fill=(10, 12, 18, 255))
            head_line = f"▶ NOW PLAYING  ｜  {artist_str}"
            f_hl = fit_font_for_width(draw, head_line, cjk_heavy_path, 29, 19, SW - 320)
            f_sl = fit_font_for_width(draw, song_str, cjk_heavy_path, 36, 22, SW - 320)
            draw.text((224, y0 + 26), head_line, font=f_hl, fill=(253, 224, 71, 255))
            draw.text((224, y0 + 82), song_str, font=f_sl, fill=(255, 255, 255, 255))
        else:
            status_tag = "PLAYED" if i < active_idx else ("NEXT (" + stage_labels[i] + ")" if i == active_idx + 1 else "LAST (" + stage_labels[i] + ")")
            draw.rounded_rectangle(
                (64, y0, SW - 64, y1),
                radius=24,
                fill=(10, 14, 24, 182),
                outline=(148, 163, 184, 125),
                width=2,
            )
            draw.text((110, y0 + 46), num_str, font=load_font(font_path, 48), fill=(148, 163, 184, 205))
            head_line = f"{status_tag}  ｜  {artist_str}"
            f_hl = fit_font_for_width(draw, head_line, cjk_reg_path, 26, 18, SW - 320)
            f_sl = fit_font_for_width(draw, song_str, cjk_reg_path, 33, 20, SW - 320)
            draw.text((224, y0 + 28), head_line, font=f_hl, fill=(148, 163, 184, 225))
            draw.text((224, y0 + 82), song_str, font=f_sl, fill=(203, 213, 225, 225))

    draw = ImageDraw.Draw(canvas, "RGBA")
    cta_ja = "▶ 全曲フル尺メドレーは下の関連動画へ"
    f_cta = fit_font_for_width(draw, cta_ja, cjk_heavy_path, 32, 22, SW - 220)
    tb_cta = draw.textbbox((0, 0), cta_ja, font=f_cta)
    cw = (tb_cta[2] - tb_cta[0]) + 110
    cx0_b = (SW - cw) // 2
    draw.rounded_rectangle(
        (cx0_b, 1470, cx0_b + cw, 1554),
        radius=42,
        fill=(10, 14, 24, 205),
        outline=(253, 224, 71, 235),
        width=3,
    )
    draw.text(((SW - (tb_cta[2] - tb_cta[0])) // 2, 1494), cta_ja, font=f_cta, fill=(253, 224, 71, 255))

    canvas.save(out_hud_png, "PNG")
    return out_hud_png


def build_short_medley_video(
    bg_loop_mp4: Path,
    src_mp3: Path,
    meta: Dict[str, Any],
    out_medley_mp4: Path,
    font_path: str,
    medley_audio_files: Optional[List[Path]] = None,
) -> Path:
    """
    Synthesize Short #2 (`output_short_medley.mp4` — Design C: 3-Song Chorus Medley Countdown, 19.5s = 6.5s x 3):
    - Extracts 3 distinct 6.5-second chorus hooks (either from `medley_audio_files` or 3 distinct offsets in `src_mp3`).
    - Plays them back-to-back while Cards `01` -> `02` -> `03` light up in sync!
    """
    logger.info(f"Rendering Short #2 [Design C: 3-Song Chorus Medley Countdown, 19.5s]: {out_medley_mp4} ...")
    seg_d = 6.5
    total_dur = seg_d * 3.0

    with tempfile.TemporaryDirectory(prefix="music_short_c_") as tmp_s:
        tmp_dir = Path(tmp_s)
        hud_paths = []
        for idx in range(3):
            hp = tmp_dir / f"medley_hud_{idx}.png"
            render_short_medley_hud(meta, hp, font_path, active_idx=idx)
            hud_paths.append(hp)

        part_wavs: List[Path] = []
        if medley_audio_files and len(medley_audio_files) >= 3:
            for idx, af in enumerate(medley_audio_files[:3]):
                adur = get_audio_duration(af)
                st = 42.0 if adur >= 60.0 else max(0.0, adur * 0.25)
                part_p = tmp_dir / f"part_{idx}.m4a"
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-ss", f"{st:.2f}",
                        "-t", f"{seg_d:.2f}",
                        "-i", str(af),
                        "-af", f"afade=t=in:st=0:d=0.08,afade=t=out:st={seg_d - 0.35:.2f}:d=0.35",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                        str(part_p),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                part_wavs.append(part_p)
        else:
            mp3_dur = get_audio_duration(src_mp3)
            offsets = (
                [42.0, 235.0, 430.0]
                if mp3_dur >= 460.0
                else [max(0.0, mp3_dur * 0.15), max(0.0, mp3_dur * 0.45), max(0.0, mp3_dur * 0.72)]
            )
            for idx, st in enumerate(offsets):
                part_p = tmp_dir / f"part_{idx}.m4a"
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-ss", f"{st:.2f}",
                        "-t", f"{seg_d:.2f}",
                        "-i", str(src_mp3),
                        "-af", f"afade=t=in:st=0:d=0.08,afade=t=out:st={seg_d - 0.35:.2f}:d=0.35",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                        str(part_p),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                part_wavs.append(part_p)

        concat_txt = tmp_dir / "medley_concat.txt"
        concat_txt.write_text("".join(f"file '{p.as_posix()}'\n" for p in part_wavs), encoding="utf-8")
        medley_m4a = tmp_dir / "medley_audio.m4a"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(medley_m4a)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        fps = 24
        t1 = seg_d
        t2 = seg_d * 2.0
        filter_complex = (
            f"[0:v]scale=-2:1920:flags=lanczos,crop=1080:1920:(iw-1080)*0.65:0,setpts=PTS-STARTPTS[v1];"
            f"[v1][1:v]overlay=0:0:enable='lt(t,{t1:.2f})'[v_s1];"
            f"[v_s1][2:v]overlay=0:0:enable='between(t,{t1:.2f},{t2:.2f})'[v_s2];"
            f"[v_s2][3:v]overlay=0:0:enable='gte(t,{t2:.2f})'[v2];"
            f"[4:a]asplit=2[a_out][a_viz];"
            f"[a_viz]showwaves=s=880x60:mode=cline:rate={fps}:scale=sqrt:colors=0xd9b36c,format=rgba,"
            f"colorchannelmixer=aa=0.68[sw];"
            f"[v2][sw]overlay=100:1578:shortest=1,noise=c0s=3:c0f=t+u,unsharp=3:3:0.45:3:3:0.0,format=yuv420p[vout]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(bg_loop_mp4),
            "-i",
            str(hud_paths[0]),
            "-i",
            str(hud_paths[1]),
            "-i",
            str(hud_paths[2]),
            "-i",
            str(medley_m4a),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[a_out]",
            "-t",
            f"{total_dur:.2f}",
            "-r",
            str(fps),
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
            "-movflags",
            "+faststart",
            str(out_medley_mp4),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info(f"Completed Short #2 [Design C]: {out_medley_mp4} ({out_medley_mp4.stat().st_size / (1024*1024):.1f} MB)")
    return out_medley_mp4


def run_music_oauth_setup() -> None:
    """Run one-time interactive browser OAuth2 login for the Retro Music BGM YouTube Channel and save .youtube_token_music.json."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]
    secret_path = CLIENT_SECRET_FILE_MUSIC if CLIENT_SECRET_FILE_MUSIC.exists() else CLIENT_SECRET_FILE
    if not secret_path.exists():
        raise FileNotFoundError(f"Missing {secret_path}")
    logger.info(f"Using OAuth client secret file: {secret_path}")
    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), scopes)
    creds = flow.run_local_server(port=0, prompt="select_account consent")
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


def compute_music_golden_time_iso(
    target_hour_jst: int = 19,
    target_minute_jst: int = 0,
) -> Optional[str]:
    """
    Compute the exact ISO-8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`) for YouTube's `status.publishAt`
    so all 6 daily Music channel videos (2 Longs + 4 Shorts = 9,700 / 10,000 API units) land on Japan Golden Time:
    - Suno Release: Short #1 (案A) at 18:30 JST, Long at 19:00 JST, Short #2 (案C) at 19:30 JST
    - Western Mix : Short #1 (案A) at 20:00 JST, Long at 20:30 JST, Short #2 (案C) at 21:00 JST
    """
    from datetime import timedelta

    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)

    candidate_jst = now_jst.replace(
        hour=target_hour_jst,
        minute=target_minute_jst,
        second=0,
        microsecond=0,
    )
    if candidate_jst <= now_jst + timedelta(minutes=12):
        candidate_jst += timedelta(days=1)

    utc_dt = candidate_jst.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_video_to_youtube(
    youtube,
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    privacy_status: str = "public",
    thumbnail_path: Optional[Path] = None,
    publish_at_iso: Optional[str] = None,
) -> str:
    """Upload a video to YouTube Data API v3 and optionally set its custom thumbnail and scheduled publishAt."""
    from googleapiclient.http import MediaFileUpload

    status_dict: Dict[str, Any] = {
        "privacyStatus": "private" if (publish_at_iso and privacy_status == "public") else privacy_status,
        "selfDeclaredMadeForKids": False,
    }
    if publish_at_iso and privacy_status == "public":
        status_dict["publishAt"] = publish_at_iso

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags[:35],
            "categoryId": "10",  # Music category
            "defaultLanguage": "ja",
            "defaultAudioLanguage": "ja",
        },
        "status": status_dict,
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
    if publish_at_iso and privacy_status == "public":
        logger.info(
            f"Uploaded {video_path.name} -> https://youtu.be/{video_id} (Scheduled for Golden Time: {publish_at_iso})"
        )
    else:
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
    if mp3_path.exists() and (mp3_path.stat().st_size > 48 * 1024 * 1024 or os.environ.get("GITHUB_ACTIONS") == "true"):
        mp3_path.unlink(missing_ok=True)
        logger.info(f"Cleaned up large concatenated master MP3 ({mp3_path.name}) before git push (individual tracks preserved in archive/).")
    elif mp3_path.exists():
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
                ["git", "commit", "-m", f"chore(music): mark {chosen_meta['id']} and {mp3_path.name} as published"],
                check=True,
            )
            subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], check=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
            logger.info("Committed and pushed updated music queue & metadata_pool.json to GitHub.")
        except Exception as exc:
            logger.warning(f"Git commit/push warning: {exc}")


def resolve_description_with_chapters(
    chosen_mp3: Path,
    chosen_meta: Dict[str, Any],
    duration_sec: int = 3600,
) -> str:
    """Replace {TIMESTAMPS} and {{TIMESTAMPS}} in chosen_meta['description'] with exact chapter timestamps filtered to duration_sec."""
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

    # Filter timestamp lines so only chapters starting before duration_sec - 10s are included
    valid_lines: List[str] = []
    for raw_line in ts_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(" ", 1)[0].split(":")
        try:
            if len(parts) == 2:
                sec = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                sec = 0
            if sec < max(60, duration_sec - 10):
                valid_lines.append(line)
        except Exception:
            valid_lines.append(line)

    if valid_lines:
        ts_block = "\n".join(valid_lines)

    out_desc = desc.replace("{{TIMESTAMPS}}", ts_block).replace("{TIMESTAMPS}", ts_block)
    if duration_sec <= 900 and valid_lines:
        n_tr = len(valid_lines)
        out_desc = (
            out_desc.replace("全16曲ノンストップフルアルバム", f"全{n_tr}曲ノンストップミックス")
            .replace("全16曲ノンストップ", f"全{n_tr}曲ノンストップ")
            .replace("全16曲", f"全{n_tr}曲")
        )

    is_vocal = bool(
        chosen_meta.get("vocal_playlist")
        or "洋楽" in chosen_meta.get("title", "")
        or "歌詞" in chosen_meta.get("title", "")
    )
    if is_vocal and WESTERN_AOR_VOCAL_LYRICS and "📝 収録曲 歌詞" not in out_desc:
        lyrics_blocks: List[str] = [
            "\n\n━━━━━━━━━━━━━━━━━━━━━━\n📝 収録曲 歌詞＆日本語対訳 (Lyrics & Translation)\n━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for idx, s_obj in enumerate(WESTERN_AOR_VOCAL_LYRICS, start=1):
            clean_lyrics = "\n".join(
                ln for ln in s_obj["prompt"].splitlines() if not ln.strip().startswith("[")
            ).strip()
            lyrics_blocks.append(
                f"♪ 0{idx}. {s_obj['title_en']} （邦題：{s_obj['title_ja']}）\n"
                f"\"{s_obj['lyric_card_en'].strip()}\"\n"
                f"（対訳：{s_obj['lyric_card_ja']}）\n\n"
                f"{clean_lyrics}"
            )
        out_desc = out_desc + "\n\n".join(lyrics_blocks)

    out_desc = out_desc.replace("カバー", "").replace("Cover", "").replace("cover", "")
    return out_desc


def detect_channel_long_uploads_allowed() -> Tuple[bool, bool]:
    """
    Query YouTube Data API v3 `channels().list(part="status", mine=True)` (1 quota unit)
    to check whether phone verification is completed (`longUploadsStatus == "allowed"`)
    and whether monetization is enabled (`isChannelMonetizationEnabled`).
    Returns `(long_uploads_allowed, is_monetized)`.
    """
    try:
        yt = get_youtube_service()
        resp = yt.channels().list(part="status", mine=True).execute()
        items = resp.get("items") or []
        if items:
            st = items[0].get("status", {})
            long_status = st.get("longUploadsStatus", "eligible")
            monetized = bool(st.get("isChannelMonetizationEnabled", False))
            logger.info(
                f"YouTube Channel Status: longUploadsStatus={long_status}, isChannelMonetizationEnabled={monetized}"
            )
            return (long_status == "allowed"), monetized
    except Exception as exc:
        logger.warning(f"Could not query channel status for auto-duration detection: {exc}")
    return False, False


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
        help="Target duration in seconds for output_1hour.mp4 (default: 3600 = 1-Hour full length).",
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
    parser.add_argument(
        "--publish-now",
        action="store_true",
        help="Publish immediately even if outside Japan Golden Time (18:00-22:15 JST).",
    )
    args = parser.parse_args()

    if args.auth_setup:
        run_music_oauth_setup()
        return 0

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    BG_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    _, is_monetized = detect_channel_long_uploads_allowed()
    target_duration = args.duration if args.duration > 0 else 3600
    if os.environ.get("SUNO_BATCHES_PER_VIDEO") in (None, "", "2", "auto"):
        os.environ["SUNO_BATCHES_PER_VIDEO"] = "8" if target_duration > 900 else "2"

    chosen_mp3, chosen_meta, pool = pick_mp3_and_metadata(auto_suno=True)

    if not chosen_mp3 and args.generate_sample_mp3:
        sample_path = QUEUE_DIR / "sample_retro_highway_01.mp3"
        generate_synthesized_retro_test_mp3(sample_path, duration_sec=195)
        chosen_mp3, chosen_meta, pool = pick_mp3_and_metadata(auto_suno=False)

    if not chosen_mp3 or not chosen_meta:
        logger.info("No MP3 in stocks/music/queue/ and SUNO_COOKIE not active. Exiting cleanly (0).")
        return 0

    if target_duration <= 900:
        chosen_meta["_under_15m"] = True
    else:
        chosen_meta.pop("_under_15m", None)

    font_path = find_bold_font()

    with tempfile.TemporaryDirectory(prefix="music_build_") as tmp_s:
        tmp_dir = Path(tmp_s)
        bg_jpg = tmp_dir / "background_1920x1080.jpg"
        bg_loop_mp4 = tmp_dir / "highway_loop_1920x1080.mp4"
        hud_png = tmp_dir / "hud_1920x1080.png"
        looped_m4a = tmp_dir / "looped_1hour.m4a"

        # Step 1: Load 1920x1080 curated Japanese retro artwork
        download_background_image(chosen_meta, bg_jpg)

        # Step 2: Build 24fps motion loop
        build_highway_driving_loop_mp4(bg_jpg, chosen_meta, bg_loop_mp4, fps=24)

        # Step 3: Render HUD overlay and YouTube thumbnail
        render_16x9_hud_and_thumb(bg_jpg, chosen_meta, hud_png, OUTPUT_THUMB, font_path)

        # Step 4: Build looped audio + 16:9 video (`output_1hour.mp4`)
        build_1hour_loop_audio(chosen_mp3, looped_m4a, target_duration_sec=target_duration)
        build_1hour_video(bg_loop_mp4, hud_png, looped_m4a, OUTPUT_1HOUR, duration_sec=target_duration)

        # Step 5: Build 2 distinct 9:16 vertical Shorts (Short #1: Design A Cinema, Short #2: Design C 3-Song Medley)
        build_short_video(bg_jpg, bg_loop_mp4, chosen_mp3, chosen_meta, OUTPUT_SHORT, font_path)
        build_short_medley_video(bg_loop_mp4, chosen_mp3, chosen_meta, OUTPUT_SHORT_MEDLEY, font_path)

    full_description = resolve_description_with_chapters(chosen_mp3, chosen_meta, duration_sec=target_duration)
    long_title = chosen_meta["title"].replace("カバー", "").replace("Cover", "")
    short_title = chosen_meta.get(
        "short_title",
        f"{chosen_meta.get('target_badge', '【40代・50代必見】')}{chosen_meta.get('thumb_main', '青春BGM')} 🎧本編はチャンネルへ！ #Shorts",
    ).replace("カバー", "").replace("Cover", "")
    medley_short_title = (
        f"【サビ3連発】{chosen_meta.get('thumb_main', '80年代・夜のドライブ神曲')}｜あの頃の夜が蘇る名曲メドレー 🎧本編は関連動画へ #Shorts"
    )[:100]
    if target_duration <= 900:
        long_title = long_title.replace("1時間耐久", "").strip()
        short_title = short_title.replace("本編1時間は", "本編は").replace("1時間耐久", "").strip()
        full_description = full_description.replace("・1時間耐久", "").replace("1時間耐久", "").replace("全16曲（60分）", "")
    else:
        if "1時間" not in long_title and len(long_title) <= 92:
            long_title = f"{long_title}【1時間耐久】"

    if not is_monetized and os.environ.get("INCLUDE_NO_ADS_TAG", "1") == "1" and "【広告なし】" not in long_title:
        long_title = f"【広告なし】{long_title}"
    elif is_monetized:
        long_title = long_title.replace("【広告なし】", "").replace("【広告なし・", "【")

    if args.dry_run:
        logger.info("Dry-run complete! Videos generated at:")
        logger.info(f"  - Main Video          : {OUTPUT_1HOUR}")
        logger.info(f"  - Short #1 (Design A) : {OUTPUT_SHORT}")
        logger.info(f"  - Short #2 (Design C) : {OUTPUT_SHORT_MEDLEY}")
        logger.info(f"  - Thumbnail           : {OUTPUT_THUMB}")
        return 0

    publish_at_short_a = None if args.publish_now else compute_music_golden_time_iso(18, 30)
    publish_at_long = None if args.publish_now else compute_music_golden_time_iso(19, 0)
    publish_at_short_c = None if args.publish_now else compute_music_golden_time_iso(19, 30)

    # Step 6: Upload Long + 2 Shorts (Design A & Design C) to YouTube & move MP3 to done/
    try:
        youtube = get_youtube_service()
        long_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_1HOUR,
            title=long_title,
            description=full_description,
            tags=chosen_meta.get("tags", []),
            privacy_status=args.privacy,
            thumbnail_path=OUTPUT_THUMB,
            publish_at_iso=publish_at_long,
        )

        short_desc = (
            f"🎧 本編フル動画はこちら 👉 https://youtu.be/{long_id}\n\n"
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
            publish_at_iso=publish_at_short_a,
        )
        short_medley_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_SHORT_MEDLEY,
            title=medley_short_title,
            description=short_desc,
            tags=chosen_meta.get("tags", []) + ["Shorts", "YouTubeShorts", "サビメドレー"],
            privacy_status=args.privacy,
            thumbnail_path=None,
            publish_at_iso=publish_at_short_c,
        )
        logger.info(f"Uploaded Short #2 (Design C Medley) -> https://youtu.be/{short_medley_id}")
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
