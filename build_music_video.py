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
METADATA_POOL_PATH = MUSIC_DIR / "metadata_pool.json"

OUTPUT_1HOUR = BASE_DIR / "output_1hour.mp4"
OUTPUT_SHORT = BASE_DIR / "output_short.mp4"
OUTPUT_THUMB = BASE_DIR / "output_music_thumb.jpg"

TOKEN_FILE = BASE_DIR / ".youtube_token_overseas_japan.json"


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


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


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


def download_background_image(meta: Dict[str, Any], out_jpg: Path) -> Path:
    """
    Download 1280x720 background image from Pollinations.ai using `meta["image_prompt"]`:
    `https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true`
    Center-crops 5% edges to remove any watermark, or falls back to procedural artwork.
    """
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
            cw, ch = int(im.width * 0.94), int(im.height * 0.92)
            im = im.crop(((im.width - cw) // 2, (im.height - ch) // 2, (im.width - cw) // 2 + cw, (im.height - ch) // 2 + ch))
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
    Build a seamless 1280x720 highway driving motion loop MP4:
    - Priority 1: If `stocks/music/bg_videos/` has a Flow `.mp4` video, converts it into a seamless
      Ping-Pong (forward + reverse) 1280x720@24fps loop so there is zero jump cut!
    - Priority 2: If no Flow `.mp4` is present yet, synthesizes a 24fps 3D Midnight Highway Driving
      Animation over the upper sky/cityscape of `bg_jpg` — featuring rushing perspective road lanes,
      glowing neon guardrails, overhead sodium streetlamps swooshing past, and a 90s JDM sports car
      rear silhouette with glowing red twin tail lights!
    """
    flow_mp4 = find_matching_flow_video(meta)
    if flow_mp4 is not None:
        logger.info(f"Building seamless Ping-Pong highway loop from Flow video: {flow_mp4.name} ...")
        # Create a forward + reverse ping-pong loop scaled cleanly to 1280x720@24fps
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

    logger.info("Synthesizing 24fps 3D Midnight Tokyo Highway High-Speed Driving Loop (96 frames / 4.0s cycle)...")
    W, H = 1280, 720
    horizon_y = 376
    total_frames = 96  # 4.0 seconds @ 24fps, exact integer phase multiples for 100% seamless loop

    base_im = Image.open(bg_jpg).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    genre = meta.get("genre", "90s Eurobeat")
    if "Eurobeat" in genre:
        neon_rgb = (56, 189, 248)
        rail_rgb = (244, 63, 94)
        speed_mult = 4
    elif "Disco" in genre:
        neon_rgb = (244, 114, 182)
        rail_rgb = (253, 224, 71)
        speed_mult = 2
    else:
        neon_rgb = (56, 189, 248)
        rail_rgb = (167, 139, 250)
        speed_mult = 2

    with tempfile.TemporaryDirectory(prefix="hwy_frames_") as tmp_s:
        frames_dir = Path(tmp_s)
        vp_x = W // 2

        for f_idx in range(total_frames):
            t_norm = f_idx / float(total_frames)  # 0.0 .. 1.0
            # Subtle camera sway (simulating high-speed lane weave)
            sway_x = int(16.0 * math.sin(2.0 * math.pi * t_norm))
            cur_vp_x = vp_x + sway_x // 3

            frame = base_im.copy()
            draw = ImageDraw.Draw(frame, "RGBA")

            # 1. Dark wet highway asphalt trapezium from horizon_y to H
            road_top_half = 58
            road_bot_half = int(W * 0.72)
            # Darken lower half for road bed + neon reflection shoulders
            draw.rectangle((0, horizon_y, W, H), fill=(7, 9, 18, 242))

            # Glowing city reflection bands on wet shoulders outside guardrails
            for s_i in range(1, 14):
                z_s = ((s_i / 13.0) + t_norm * speed_mult) % 1.0
                if z_s < 0.02:
                    continue
                p_s = z_s ** 2.1
                ry = int(horizon_y + p_s * (H - horizon_y))
                rw = int(road_top_half + p_s * (road_bot_half - road_top_half))
                alpha_s = int(95 * p_s)
                draw.line([(0, ry), (max(0, cur_vp_x - rw - 10), ry)], fill=(*neon_rgb, alpha_s), width=2)
                draw.line([(min(W, cur_vp_x + rw + 10), ry), (W, ry)], fill=(*rail_rgb, alpha_s), width=2)

            # Main asphalt surface polygon
            asphalt_poly = [
                (cur_vp_x - road_top_half, horizon_y),
                (cur_vp_x + road_top_half, horizon_y),
                (cur_vp_x + road_bot_half + sway_x, H),
                (cur_vp_x - road_bot_half + sway_x, H),
            ]
            draw.polygon(asphalt_poly, fill=(14, 18, 30, 255))

            # Glowing side guardrails (double neon lines)
            for offset_top, offset_bot, col_g, w_g in [
                (road_top_half, road_bot_half, (*rail_rgb, 245), 4),
                (road_top_half + 6, road_bot_half + 28, (*neon_rgb, 180), 2),
            ]:
                draw.line(
                    [(cur_vp_x - offset_top, horizon_y), (cur_vp_x - offset_bot + sway_x, H)],
                    fill=col_g,
                    width=w_g,
                )
                draw.line(
                    [(cur_vp_x + offset_top, horizon_y), (cur_vp_x + offset_bot + sway_x, H)],
                    fill=col_g,
                    width=w_g,
                )

            # 2. High-Speed Dashed Lane Markers rushing from horizon to bottom
            num_dashes = 10
            for d_i in range(num_dashes):
                z0 = ((d_i + (t_norm * speed_mult * num_dashes)) % num_dashes) / float(num_dashes)
                z1 = min(1.0, z0 + 0.055)
                if z1 <= z0 or z0 < 0.03:
                    continue
                p0 = z0 ** 2.25
                p1 = z1 ** 2.25
                y0 = int(horizon_y + p0 * (H - horizon_y))
                y1 = int(horizon_y + p1 * (H - horizon_y))

                # Draw 3 highway lane dividers (-0.35, 0.0, +0.35 of road half-width)
                for lane_rel in (-0.36, 0.0, 0.36):
                    hw0 = road_top_half + p0 * (road_bot_half - road_top_half)
                    hw1 = road_top_half + p1 * (road_bot_half - road_top_half)
                    cx0 = cur_vp_x + int(sway_x * p0 + lane_rel * hw0)
                    cx1 = cur_vp_x + int(sway_x * p1 + lane_rel * hw1)
                    bw0 = max(1, int(1 + p0 * 8))
                    bw1 = max(2, int(1 + p1 * 11))
                    col_dash = (254, 240, 138, 240) if lane_rel == 0.0 else (241, 245, 249, 225)
                    draw.polygon(
                        [(cx0 - bw0, y0), (cx0 + bw0, y0), (cx1 + bw1, y1), (cx1 - bw1, y1)],
                        fill=col_dash,
                    )

            # 3. Overhead Sodium Highway Streetlamps & Guardrail Posts rushing past on both sides
            num_poles = 7
            for p_i in range(num_poles):
                zp = ((p_i + (t_norm * (speed_mult // 2) * num_poles)) % num_poles) / float(num_poles)
                if zp < 0.05:
                    continue
                pp = zp ** 2.15
                py = int(horizon_y + pp * (H - horizon_y))
                hw = road_top_half + pp * (road_bot_half - road_top_half)
                pole_h = int(28 + pp * 250)
                pole_w = max(1, int(1 + pp * 5))
                arm_w = int(14 + pp * 95)

                for side in (-1, 1):
                    px = cur_vp_x + int(sway_x * pp + side * hw)
                    top_py = max(0, py - pole_h)
                    # Vertical pole
                    draw.line([(px, py), (px, top_py)], fill=(148, 163, 184, int(190 * pp)), width=pole_w)
                    # Inward overhanging streetlamp arm
                    arm_x = px - side * arm_w
                    draw.line([(px, top_py), (arm_x, top_py + int(6 * pp))], fill=(203, 213, 225, int(200 * pp)), width=max(1, pole_w - 1))
                    # Glowing sodium / cyan highway lamp halo
                    lamp_r = max(2, int(3 + pp * 16))
                    ly = top_py + int(6 * pp)
                    draw.ellipse(
                        (arm_x - lamp_r * 2, ly - lamp_r, arm_x + lamp_r * 2, ly + lamp_r),
                        fill=(253, 224, 71, int(115 * pp)),
                    )
                    draw.ellipse(
                        (arm_x - lamp_r, ly - lamp_r // 2, arm_x + lamp_r, ly + lamp_r // 2),
                        fill=(255, 255, 255, int(245 * pp)),
                    )

            # 4. Horizon Neon Bridge Glow
            draw.line([(0, horizon_y), (W, horizon_y)], fill=(255, 255, 255, 220), width=2)
            draw.line([(0, horizon_y + 2), (W, horizon_y + 2)], fill=(*rail_rgb, 210), width=3)

            # 5. Sleek 90s JDM Sports Car Rear Silhouette + Glowing Red Tail Lights & Exhaust Pulse
            car_cx = W // 2 + int(sway_x * 0.85)
            car_vib = int(1.5 * math.sin(2.0 * math.pi * t_norm * 12))
            car_y0 = 492 + car_vib
            car_w, car_h = 250, 96

            # Red tail light reflection on wet asphalt behind the car
            draw.ellipse(
                (car_cx - 135, car_y0 + 78, car_cx - 35, car_y0 + 132),
                fill=(239, 68, 68, 95),
            )
            draw.ellipse(
                (car_cx + 35, car_y0 + 78, car_cx + 135, car_y0 + 132),
                fill=(239, 68, 68, 95),
            )

            # Car lower body & rear diffuser
            body_poly = [
                (car_cx - car_w // 2, car_y0 + 48),
                (car_cx - car_w // 2 + 18, car_y0 + 18),
                (car_cx + car_w // 2 - 18, car_y0 + 18),
                (car_cx + car_w // 2, car_y0 + 48),
                (car_cx + car_w // 2 - 6, car_y0 + 86),
                (car_cx - car_w // 2 + 6, car_y0 + 86),
            ]
            draw.polygon(body_poly, fill=(18, 24, 38, 255), outline=(148, 163, 184, 220))

            # Fastback cabin / rear window
            cabin_poly = [
                (car_cx - 88, car_y0 + 18),
                (car_cx - 62, car_y0 - 16),
                (car_cx + 62, car_y0 - 16),
                (car_cx + 88, car_y0 + 18),
            ]
            draw.polygon(cabin_poly, fill=(10, 15, 28, 255), outline=(100, 116, 139, 210))

            # Rear GT Wing / Spoiler
            draw.line([(car_cx - 106, car_y0 + 8), (car_cx + 106, car_y0 + 8)], fill=(30, 41, 59, 255), width=5)

            # Iconic 90s Twin Round / Strip Glowing Red Tail Lights
            draw.rounded_rectangle((car_cx - 114, car_y0 + 30, car_cx + 114, car_y0 + 50), radius=6, fill=(127, 29, 29, 255))
            for tl_x in (car_cx - 92, car_cx - 58, car_cx + 58, car_cx + 92):
                draw.ellipse((tl_x - 16, car_y0 + 26, tl_x + 16, car_y0 + 54), fill=(239, 68, 68, 165))
                draw.ellipse((tl_x - 10, car_y0 + 31, tl_x + 10, car_y0 + 49), fill=(254, 202, 202, 255))

            # Glowing green JDM license plate
            draw.rounded_rectangle((car_cx - 22, car_y0 + 54, car_cx + 22, car_y0 + 74), radius=3, fill=(22, 163, 74, 235), outline=(255, 255, 255, 210))

            frame.save(frames_dir / f"f_{f_idx:04d}.jpg", "JPEG", quality=92)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(frames_dir / "f_%04d.jpg"),
                "-vf",
                "vignette=PI/5,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                str(out_loop_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    logger.info(f"Built 3D highway driving motion loop: {out_loop_mp4.name}")
    return out_loop_mp4


def render_16x9_hud_and_thumb(
    bg_jpg: Path,
    meta: Dict[str, Any],
    hud_png: Path,
    thumb_jpg: Path,
    font_path: str,
) -> None:
    """
    Create:
    1) A subtle retro VHS / Aesthetic HUD overlay (`hud_png`, 1280x720 RGBA) for the 1-hour video
    2) A high-CTR 1280x720 YouTube thumbnail (`thumb_jpg`)
    """
    genre = meta.get("genre", "90s Retro Mix").upper()
    short_hook = meta.get("short_hook_text", "90s Retro Vibes 🎧 Full 1 Hour in Channel")

    hud = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud, "RGBA")

    for y in range(540, 720):
        alpha = int(165 * ((y - 540) / 180.0) ** 1.3)
        draw.line([(0, y), (1280, y)], fill=(6, 8, 18, alpha))

    f_badge = load_font(font_path, 18)
    f_title = load_font(font_path, 22)

    badge_txt = f"● REC  |  {genre}  |  1-HOUR MIDNIGHT HIGHWAY MIX"
    tb = draw.textbbox((0, 0), badge_txt, font=f_badge)
    bw = (tb[2] - tb[0]) + 36
    draw.rounded_rectangle((28, 24, 28 + bw, 62), radius=10, fill=(12, 16, 30, 210), outline=(253, 224, 71, 220), width=2)
    draw.text((46, 33), badge_txt, font=f_badge, fill=(253, 224, 71, 255))

    clean_title = meta.get("title", "").split("|")[0].strip()[:62]
    draw.text(
        (32, 682),
        f"NOW PLAYING: {clean_title}",
        font=f_title,
        fill=(241, 245, 249, 235),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 230),
    )
    hud.save(hud_png, "PNG")

    base = Image.open(bg_jpg).convert("RGBA")
    t_draw = ImageDraw.Draw(base, "RGBA")
    t_draw.rounded_rectangle((36, 480, 1244, 684), radius=20, fill=(8, 12, 24, 228), outline=(56, 189, 248, 240), width=3)
    f_th_big = load_font(font_path, 38)
    f_th_sub = load_font(font_path, 25)
    t_draw.text((64, 505), clean_title.upper()[:52], font=f_th_big, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    t_draw.text((64, 575), f"{genre}  •  1 HOUR ENDURANCE WORK & DRIVE BGM", font=f_th_sub, fill=(253, 224, 71, 255))
    t_draw.text((64, 622), short_hook.replace("🎧", "|").replace("🪩", "|"), font=f_th_sub, fill=(125, 211, 252, 255))
    base.convert("RGB").save(thumb_jpg, "JPEG", quality=95)


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
    Synthesize the 16:9 1-Hour Endurance Video (`output_1hour.mp4`, 1280x720):
    - Loops the high-speed highway driving video (`bg_loop_mp4`) seamlessly for `duration_sec`.
    - Overlays the retro HUD (`hud_png`) and real-time audio spectrum (`showwaves=s=1200x95:mode=cline`).
    """
    logger.info(f"Rendering 16:9 highway driving music video ({duration_sec}s): {out_mp4} ...")
    fps = 24
    filter_complex = (
        f"[0:v]setpts=PTS-STARTPTS[bg];"
        f"[bg][1:v]overlay=0:0[bghud];"
        f"[2:a]showwaves=s=1200x95:mode=cline:rate={fps}:colors=0x38bdf8|0xf472b6|0xfde047,format=rgba,"
        f"colorchannelmixer=aa=0.88[sw];"
        f"[bghud][sw]overlay=40:580:shortest=1,format=yuv420p[vout]"
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
        "23",
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
    logger.info(f"Completed 16:9 video: {out_mp4} ({out_mp4.stat().st_size / (1024*1024):.1f} MB)")
    return out_mp4


def render_short_vertical_hud(
    bg_jpg: Path,
    meta: Dict[str, Any],
    out_vertical_hud_png: Path,
    font_path: str,
) -> Path:
    """
    Build the 720x1280 (9:16) RGBA overlay for `output_short.mp4` with a transparent center window
    (`x=28..692, y=282..780`) so the moving highway driving video plays live inside the center frame!
    """
    SW, SH = 720, 1280
    raw = Image.open(bg_jpg).convert("RGB")

    scale = max(SW / raw.width, SH / raw.height)
    nw, nh = int(raw.width * scale), int(raw.height * scale)
    bg_crop = raw.resize((nw, nh), Image.Resampling.LANCZOS).crop(
        ((nw - SW) // 2, (nh - SH) // 2, (nw - SW) // 2 + SW, (nh - SH) // 2 + SH)
    )
    bg_blur = bg_crop.filter(ImageFilter.GaussianBlur(radius=28))
    bg_blur = ImageEnhance.Brightness(bg_blur).enhance(0.32).convert("RGBA")

    draw = ImageDraw.Draw(bg_blur, "RGBA")

    # 1. Top Hook Banner (y=88..248)
    draw.rounded_rectangle((28, 88, SW - 28, 248), radius=20, fill=(12, 18, 36, 238), outline=(253, 224, 71, 250), width=3)
    hook_raw = meta.get("short_hook_text", "90s Retro Vibes 🎧 Full 1 Hour in Channel")
    clean_hook = hook_raw.replace("🎧", " // ").replace("🪩", " // ").replace("✨", "").strip()
    parts = [p.strip() for p in clean_hook.split("//") if p.strip()]
    line1 = parts[0].upper() if parts else "90S RETRO VIBES"
    line2 = parts[1].upper() if len(parts) > 1 else "FULL 1 HOUR IN CHANNEL"

    f_h1 = load_font(font_path, 33)
    f_h2 = load_font(font_path, 24)
    tb1 = draw.textbbox((0, 0), line1, font=f_h1)
    tb2 = draw.textbbox((0, 0), line2, font=f_h2)
    draw.text(((SW - (tb1[2] - tb1[0])) // 2, 114), line1, font=f_h1, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 240))
    draw.text(((SW - (tb2[2] - tb2[0])) // 2, 178), f"▶ {line2}", font=f_h2, fill=(253, 224, 71, 255), stroke_width=2, stroke_fill=(0, 0, 0, 240))

    # 2. Punch a transparent window at (x=28..692, y=282..780) where the live highway driving video will play
    fx0, fy0, fx1, fy1 = 28, 282, SW - 28, 780
    draw.rounded_rectangle((fx0, fy0, fx1, fy1), radius=22, fill=(0, 0, 0, 0), outline=(56, 189, 248, 245), width=4)

    genre = meta.get("genre", "90s Retro Mix").upper()
    f_g = load_font(font_path, 19)
    tb_g = draw.textbbox((0, 0), genre, font=f_g)
    gw = (tb_g[2] - tb_g[0]) + 32
    draw.rounded_rectangle((fx0 + 16, fy0 + 16, fx0 + 16 + gw, fy0 + 56), radius=10, fill=(220, 38, 38, 240), outline=(255, 255, 255, 230), width=2)
    draw.text((fx0 + 32, fy0 + 26), genre, font=f_g, fill=(255, 255, 255, 255))

    # 3. Spectrum Frame Box (y=808..1028)
    draw.rounded_rectangle((28, 808, SW - 28, 1028), radius=18, fill=(8, 12, 24, 215), outline=(244, 114, 182, 220), width=2)

    # 4. Bottom Track Title & Channel CTA (y=1058..1185)
    f_bot = load_font(font_path, 22)
    f_cta = load_font(font_path, 20)
    short_title = meta.get("title", "").split("|")[0].strip()[:38]
    tb_bt = draw.textbbox((0, 0), short_title, font=f_bot)
    draw.text(((SW - (tb_bt[2] - tb_bt[0])) // 2, 1068), short_title, font=f_bot, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 240))

    cta_str = "TAP CHANNEL FOR FULL 1-HOUR WORK & DRIVE BGM"
    tb_c = draw.textbbox((0, 0), cta_str, font=f_cta)
    draw.text(((SW - (tb_c[2] - tb_c[0])) // 2, 1116), cta_str, font=f_cta, fill=(125, 211, 252, 255))

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
    Synthesize `output_short.mp4` (720x1280, 9:16, 30 seconds):
    - Extracts the 30s..60s climax slice of `src_mp3`.
    - Plays the moving highway driving video (`bg_loop_mp4`) inside the center window (`y=282..780`).
    - Overlays the large real-time audio spectrum (`showwaves=s=636x190:mode=cline`) at `y=822`.
    """
    logger.info(f"Rendering 9:16 Shorts highway driving video (30s): {out_short_mp4} ...")
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
            f"[a_viz]showwaves=s=636x190:mode=cline:rate={fps}:colors=0x38bdf8|0xf472b6|0xfde047,format=rgba[sw];"
            f"[v2][sw]overlay=42:822:shortest=1,format=yuv420p[vout]"
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
            "21",
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

    logger.info(f"Completed 9:16 Shorts video: {out_short_mp4} ({out_short_mp4.stat().st_size / (1024*1024):.1f} MB)")
    return out_short_mp4


def get_youtube_service():
    """
    Build an authenticated YouTube Data API v3 client using either:
    1) Environment variables (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`) on GitHub Actions
    2) Local `.youtube_token_overseas_japan.json` token file
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]
    creds = None

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

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
    elif TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    else:
        raise RuntimeError(
            "No YouTube credentials found. Set YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN "
            f"or provide {TOKEN_FILE}."
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
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
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
    Move the used MP3 to `stocks/music/done/`, mark the metadata item as `"used": true`
    in `stocks/music/metadata_pool.json`, and commit/push when running in CI.
    """
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_mp3 = DONE_DIR / f"{ts}_{mp3_path.name}"
    shutil.move(str(mp3_path), str(dest_mp3))
    logger.info(f"Moved MP3 to done: {dest_mp3}")

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build & upload 1-Hour Retro Music Video + 9:16 Short from Suno MP3.")
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

        # Step 1: Download 1280x720 background image from Pollinations.ai
        download_background_image(chosen_meta, bg_jpg)

        # Step 2: Build High-Speed Highway Driving Video Loop (Flow MP4 if present, else 24fps 3D Highway Animation)
        build_highway_driving_loop_mp4(bg_jpg, chosen_meta, bg_loop_mp4, fps=24)

        # Step 3: Render HUD overlay and YouTube thumbnail
        render_16x9_hud_and_thumb(bg_jpg, chosen_meta, hud_png, OUTPUT_THUMB, font_path)

        # Step 4: Build looped 1-hour audio + 16:9 video (`output_1hour.mp4`)
        build_1hour_loop_audio(chosen_mp3, looped_m4a, target_duration_sec=args.duration)
        build_1hour_video(bg_loop_mp4, hud_png, looped_m4a, OUTPUT_1HOUR, duration_sec=args.duration)

        # Step 5: Build 9:16 vertical Short (`output_short.mp4`) from 30s..60s of the MP3 with live highway motion
        build_short_video(bg_jpg, bg_loop_mp4, chosen_mp3, chosen_meta, OUTPUT_SHORT, font_path)

    if args.dry_run:
        logger.info("Dry-run complete! Videos generated at:")
        logger.info(f"  - 1-Hour Video : {OUTPUT_1HOUR}")
        logger.info(f"  - Short Video  : {OUTPUT_SHORT}")
        logger.info(f"  - Thumbnail    : {OUTPUT_THUMB}")
        return 0

    # Step 6: Upload both videos to YouTube & move MP3 to done/
    youtube = get_youtube_service()
    long_id = upload_video_to_youtube(
        youtube=youtube,
        video_path=OUTPUT_1HOUR,
        title=chosen_meta["title"],
        description=chosen_meta["description"],
        tags=chosen_meta.get("tags", []),
        privacy_status=args.privacy,
        thumbnail_path=OUTPUT_THUMB,
    )

    short_title = chosen_meta.get(
        "short_title",
        f"{chosen_meta.get('short_hook_text', '90s Retro Vibes')} | {chosen_meta['genre']} #Shorts",
    )
    short_desc = (
        f"🎧 Listen to the full 1-Hour {chosen_meta['genre']} Mix here: https://youtu.be/{long_id}\n\n"
        f"{chosen_meta['description']}"
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
