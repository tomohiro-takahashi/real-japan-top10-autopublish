#!/usr/bin/env python3
"""
build_music_video.py
====================
Suno MP3 Automated 1-Hour Retro Music Loop (16:9) & Vertical Shorts (9:16) Builder + YouTube Uploader.
Designed to run 100% free & zero-local-CPU on GitHub Actions (or locally).

Workflow:
1. Picks 1 MP3 from `stocks/music/queue/` and 1 unused metadata entry from `stocks/music/metadata_pool.json`.
2. Downloads a 1280x720 90s retro aesthetic background image from Pollinations.ai
   (`https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true`),
   with a built-in high-resolution procedural 90s Retro Anime / Synthwave artwork fallback if Pollinations is unreachable.
3. Synthesizes `output_1hour.mp4` (1280x720, ~3600s):
   - Loops the MP3 with smooth fade-in/fade-out transitions to reach ~3600 seconds.
   - Applies continuous background visual motion / atmospheric vignette + real-time `showwaves` / `showfreqs` audio spectrum overlay.
   - Optimized with `-c:v libx264 -preset veryfast -tune stillimage`.
4. Synthesizes `output_short.mp4` (720x1280, 30s from 30s..60s of the MP3):
   - Vertical 9:16 layout with centered artwork, large audio spectrum, and top English hook text
     (e.g. `"90s Retro Vibes 🎧 Full 1 Hour in Channel"`).
5. Uploads both videos to YouTube via YouTube Data API v3, moves the MP3 to `stocks/music/done/`,
   marks the metadata item as `"used": true` in `stocks/music/metadata_pool.json`, and commits/pushes on GitHub Actions.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import os
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("music_video_builder")

BASE_DIR = Path(__file__).resolve().parent
MUSIC_DIR = BASE_DIR / "stocks" / "music"
QUEUE_DIR = MUSIC_DIR / "queue"
DONE_DIR = MUSIC_DIR / "done"
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


def get_audio_duration(mp3_path: Path) -> float:
    """Return duration of an audio file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(mp3_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def generate_synthesized_retro_test_mp3(out_mp3: Path, duration_sec: int = 195) -> Path:
    """
    Generate a lush 3m15s 90s City Pop / Synthwave stereo MP3 via FFmpeg `aevalsrc`
    when `--generate-sample-mp3` is requested for testing.
    """
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    # Warm 90s chord progression + bass pulse + arpeggio
    expr = (
        "0.22*sin(2*PI*110*t)*(1+0.4*sin(2*PI*2*t))"
        "+0.16*sin(2*PI*220*t)+0.14*sin(2*PI*277.18*t)+0.14*sin(2*PI*329.63*t)+0.12*sin(2*PI*415.30*t)"
        "+0.10*sin(2*PI*(440+110*floor(mod(t*4,4)))*t)*exp(-mod(t*4,1)*3.5)"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"aevalsrc='{expr}|{expr}':s=44100:d={duration_sec}",
        "-af",
        "afade=t=in:st=0:d=2.5,afade=t=out:st=" + str(max(1, duration_sec - 3)) + ":d=3.0",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(out_mp3),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"Generated sample test MP3: {out_mp3} ({duration_sec}s)")
    return out_mp3


def pick_mp3_and_metadata() -> Tuple[Optional[Path], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Pick 1 MP3 from `stocks/music/queue/` and 1 unused metadata item from `stocks/music/metadata_pool.json`.
    """
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)

    mp3_files = sorted(
        [p for p in QUEUE_DIR.iterdir() if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".m4a")]
    )
    if not mp3_files:
        logger.warning(f"No MP3 files found in {QUEUE_DIR}")
        return None, None, []

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

    chosen_mp3 = mp3_files[0]
    chosen_meta = unused[0]
    logger.info(f"Selected MP3: {chosen_mp3.name}")
    logger.info(f"Selected Metadata [{chosen_meta['id']}] ({chosen_meta['genre']}): {chosen_meta['title']}")
    return chosen_mp3, chosen_meta, pool


def render_procedural_retro_artwork(meta: Dict[str, Any], out_jpg: Path, width: int = 1280, height: int = 720) -> Path:
    """
    Render a rich 90s Retro Anime / Synthwave Night Tokyo illustration at 1280x720
    as a rock-solid fallback if Pollinations.ai is rate-limited or offline.
    """
    genre = meta.get("genre", "90s City Pop")
    img = Image.new("RGB", (width, height), (10, 8, 26))
    draw = ImageDraw.Draw(img, "RGBA")

    # 1. Twilight / Neon Sky Gradient
    if "Eurobeat" in genre:
        top_c, mid_c, hor_c = (8, 10, 28), (38, 16, 68), (225, 45, 85)
        sun_c1, sun_c2 = (255, 210, 60), (255, 50, 100)
        grid_c = (0, 240, 255, 135)
    elif "Disco" in genre:
        top_c, mid_c, hor_c = (12, 6, 34), (75, 15, 95), (255, 60, 165)
        sun_c1, sun_c2 = (255, 230, 90), (255, 40, 150)
        grid_c = (255, 80, 220, 135)
    else:  # City Pop
        top_c, mid_c, hor_c = (6, 16, 42), (28, 45, 105), (245, 95, 145)
        sun_c1, sun_c2 = (254, 240, 138), (244, 63, 94)
        grid_c = (56, 189, 248, 135)

    horizon_y = int(height * 0.62)
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

    # 2. Starfield in upper sky
    import random
    rng = random.Random(hash(meta.get("id", "retro")))
    for _ in range(95):
        sx = rng.randint(10, width - 10)
        sy = rng.randint(10, int(horizon_y * 0.7))
        sr = rng.choice([1, 1, 2])
        alpha = rng.randint(130, 255)
        draw.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(255, 250, 240, alpha))

    # 3. Giant 80s/90s Outrun Sliced Neon Sun
    sun_r = int(height * 0.22)
    sun_cx, sun_cy = width // 2, horizon_y - int(sun_r * 0.25)
    for dy in range(-sun_r, sun_r):
        sy = sun_cy + dy
        if sy >= horizon_y:
            continue
        # Horizontal scanline cutouts in lower half of sun
        if dy > 10 and (dy // 9) % 2 == 0:
            continue
        dx = int(math.sqrt(max(0, sun_r * sun_r - dy * dy)))
        u = (dy + sun_r) / (2 * sun_r)
        sr = int(sun_c1[0] * (1 - u) + sun_c2[0] * u)
        sg = int(sun_c1[1] * (1 - u) + sun_c2[1] * u)
        sb = int(sun_c1[2] * (1 - u) + sun_c2[2] * u)
        draw.line([(sun_cx - dx, sy), (sun_cx + dx, sy)], fill=(sr, sg, sb, 240))

    # 4. Tokyo Skyline Silhouettes + Lit Neon Windows along Horizon
    bx = 0
    while bx < width:
        bw = rng.randint(34, 82)
        bh = rng.randint(45, 195)
        by0 = horizon_y - bh
        draw.rectangle((bx, by0, bx + bw, horizon_y), fill=(12, 14, 28, 255), outline=(45, 55, 85, 180), width=1)
        # Lit windows
        win_col = rng.choice([(253, 224, 71, 210), (56, 189, 248, 210), (244, 114, 182, 210)])
        for wy in range(by0 + 8, horizon_y - 8, 10):
            for wx in range(bx + 6, bx + bw - 8, 9):
                if rng.random() < 0.42:
                    draw.rectangle((wx, wy, wx + 4, wy + 5), fill=win_col)
        bx += bw - rng.randint(0, 6)

    # 5. Lower Perspective Highway / Bay Reflection Grid
    draw.rectangle((0, horizon_y, width, height), fill=(8, 10, 22, 255))
    # Horizontal perspective lines
    for i in range(1, 18):
        py = horizon_y + int((height - horizon_y) * ((i / 17.0) ** 1.65))
        draw.line([(0, py), (width, py)], fill=grid_c, width=2)
    # Radial perspective lines from vanishing point
    vp_x, vp_y = width // 2, horizon_y
    for i in range(-14, 15):
        bx_end = vp_x + i * 165
        draw.line([(vp_x, vp_y), (bx_end, height)], fill=grid_c, width=2)

    # Glow line on horizon
    draw.line([(0, horizon_y - 1), (width, horizon_y - 1)], fill=(255, 255, 255, 235), width=3)
    draw.line([(0, horizon_y + 2), (width, horizon_y + 2)], fill=(244, 63, 94, 210), width=4)

    img.save(out_jpg, "JPEG", quality=95)
    return out_jpg


def download_background_image(meta: Dict[str, Any], out_jpg: Path) -> Path:
    """
    Download 1280x720 background image from Pollinations.ai using `meta["image_prompt"]`:
    `https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true`
    Falls back automatically to procedural 90s retro artwork if Pollinations returns an error/timeout.
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
            # Gently center-crop 5% off edges to eliminate any corner watermark while preserving 16:9 composition
            cw, ch = int(im.width * 0.94), int(im.height * 0.92)
            im = im.crop(((im.width - cw) // 2, (im.height - ch) // 2, (im.width - cw) // 2 + cw, (im.height - ch) // 2 + ch))
            im = im.resize((1280, 720), Image.Resampling.LANCZOS)
            im.save(out_jpg, "JPEG", quality=95)
            logger.info(f"Downloaded Pollinations background image: {out_jpg} ({im.size})")
            return out_jpg
        except Exception as exc:
            logger.warning(f"Pollinations download attempt {attempt}/2 failed ({exc}).")
            time.sleep(2.0)

    logger.info("Using high-contrast procedural 90s Retro Anime / Synthwave background illustration fallback.")
    return render_procedural_retro_artwork(meta, out_jpg, 1280, 720)


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

    # 1. Transparent HUD for 1-Hour Video
    hud = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud, "RGBA")

    # Subtle bottom gradient behind the real-time audio spectrum so waves pop cleanly
    for y in range(520, 720):
        alpha = int(175 * ((y - 520) / 200.0) ** 1.3)
        draw.line([(0, y), (1280, y)], fill=(6, 8, 18, alpha))

    f_badge = load_font(font_path, 18)
    f_title = load_font(font_path, 22)

    # Top-left retro cassette badge
    badge_txt = f"● REC  |  {genre}  |  1-HOUR NON-STOP MIX"
    tb = draw.textbbox((0, 0), badge_txt, font=f_badge)
    bw = (tb[2] - tb[0]) + 36
    draw.rounded_rectangle((28, 24, 28 + bw, 62), radius=10, fill=(12, 16, 30, 210), outline=(253, 224, 71, 220), width=2)
    draw.text((46, 33), badge_txt, font=f_badge, fill=(253, 224, 71, 255))

    # Bottom caption strip below spectrum
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

    # 2. High-CTR 1280x720 Thumbnail
    base = Image.open(bg_jpg).convert("RGBA")
    t_draw = ImageDraw.Draw(base, "RGBA")
    t_draw.rounded_rectangle((36, 480, 1244, 684), radius=20, fill=(8, 12, 24, 228), outline=(56, 189, 248, 240), width=3)
    f_th_big = load_font(font_path, 38)
    f_th_sub = load_font(font_path, 25)
    t_draw.text((64, 505), clean_title.upper()[:52], font=f_th_big, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    t_draw.text((64, 575), f"{genre}  •  1 HOUR ENDURANCE WORK & DRIVE BGM", font=f_th_sub, fill=(253, 224, 71, 255))
    t_draw.text((64, 622), short_hook.replace("🎧", "|"), font=f_th_sub, fill=(125, 211, 252, 255))
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
        # Encode 1 faded cycle first
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

        # Stream-loop the faded unit to target_duration_sec using -c copy (takes <1 second!)
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
    bg_jpg: Path,
    hud_png: Path,
    looped_audio_m4a: Path,
    out_mp4: Path,
    duration_sec: int = 3600,
) -> Path:
    """
    Synthesize the 16:9 1-Hour Endurance Video (`output_1hour.mp4`, 1280x720):
    - Visual Effect A: Smooth continuous zoom/pan motion (`zoompan`) + retro atmospheric vignette (`vignette=PI/5`)
      on the background illustration so it is never flagged as static content.
    - Visual Effect B: Real-time audio spectrum (`showwaves=s=1200x110:mode=cline:rate=24:colors=0x38bdf8|0xf472b6`)
      drawn at the lower section of the screen (`y=560`).
    - Fast encoding with `-c:v libx264 -preset veryfast -tune stillimage`.
    """
    logger.info(f"Rendering 16:9 video ({duration_sec}s): {out_mp4} ...")
    fps = 24
    # Pre-render a 20-second seamless zoom-in / zoom-out background motion loop (480 frames)
    # so FFmpeg doesn't have to recompute zoompan 86,400 times, while keeping continuous motion + real-time audio spectrum!
    with tempfile.TemporaryDirectory(prefix="music_bgloop_") as tmp_s:
        tmp_dir = Path(tmp_s)
        bg_loop_mp4 = tmp_dir / "bg_motion_20s.mp4"
        loop_frames = 20 * fps  # 480 frames = 20s cycle (10s gentle zoom in, 10s gentle zoom out + vignette)
        zp_filter = (
            f"scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,"
            f"zoompan=z='1.06+0.05*sin(2*PI*on/{loop_frames})':"
            f"x='iw/2-(iw/zoom/2)+18*sin(2*PI*on/{loop_frames})':"
            f"y='ih/2-(ih/zoom/2)':d={loop_frames}:s=1280x720:fps={fps},"
            f"vignette=PI/5,format=yuv420p"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(bg_jpg),
                "-vf",
                zp_filter,
                "-t",
                "20",
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                str(bg_loop_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Now combine the looping moving background + HUD + real-time audio spectrum (`showwaves`) for the full duration
        filter_complex = (
            f"[0:v]setpts=PTS-STARTPTS[bg];"
            f"[bg][1:v]overlay=0:0[bghud];"
            f"[2:a]showwaves=s=1200x110:mode=cline:rate={fps}:colors=0x38bdf8|0xf472b6|0xfde047,format=rgba,"
            f"colorchannelmixer=aa=0.88[sw];"
            f"[bghud][sw]overlay=40:565:shortest=1,format=yuv420p[vout]"
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
            "-tune",
            "stillimage",
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


def render_short_vertical_canvas(
    bg_jpg: Path,
    meta: Dict[str, Any],
    out_vertical_jpg: Path,
    font_path: str,
) -> Path:
    """
    Build the 720x1280 (9:16) vertical base canvas for `output_short.mp4`:
    - Blurred neon ambient backdrop (720x1280)
    - Top Hook Banner with English text (e.g. `"90s Retro Vibes 🎧 Full 1 Hour in Channel"`)
    - Centered sharp 16:9 / 4:3 Retro Artwork frame with glowing neon border
    - Bottom Genre & CTA pill
    """
    SW, SH = 720, 1280
    raw = Image.open(bg_jpg).convert("RGB")

    # Fill 720x1280 blurred background
    scale = max(SW / raw.width, SH / raw.height)
    nw, nh = int(raw.width * scale), int(raw.height * scale)
    bg_crop = raw.resize((nw, nh), Image.Resampling.LANCZOS).crop(((nw - SW) // 2, (nh - SH) // 2, (nw - SW) // 2 + SW, (nh - SH) // 2 + SH))
    bg_blur = bg_crop.filter(ImageFilter.GaussianBlur(radius=28))
    bg_blur = ImageEnhance.Brightness(bg_blur).enhance(0.32).convert("RGBA")

    draw = ImageDraw.Draw(bg_blur, "RGBA")

    # 1. Top Hook Banner (y=88..248)
    draw.rounded_rectangle((28, 88, SW - 28, 248), radius=20, fill=(12, 18, 36, 238), outline=(253, 224, 71, 250), width=3)
    hook_raw = meta.get("short_hook_text", "90s Retro Vibes 🎧 Full 1 Hour in Channel")
    # Replace emoji with clean ASCII symbol if using standard DejaVu/Arial so no tofu boxes appear
    clean_hook = hook_raw.replace("🎧", " // ").replace("✨", "").strip()
    parts = [p.strip() for p in clean_hook.split("//") if p.strip()]
    line1 = parts[0].upper() if parts else "90S RETRO VIBES"
    line2 = parts[1].upper() if len(parts) > 1 else "FULL 1 HOUR IN CHANNEL"

    f_h1 = load_font(font_path, 33)
    f_h2 = load_font(font_path, 24)
    tb1 = draw.textbbox((0, 0), line1, font=f_h1)
    tb2 = draw.textbbox((0, 0), line2, font=f_h2)
    draw.text(((SW - (tb1[2] - tb1[0])) // 2, 114), line1, font=f_h1, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 240))
    draw.text(((SW - (tb2[2] - tb2[0])) // 2, 178), f"▶ {line2}", font=f_h2, fill=(253, 224, 71, 255), stroke_width=2, stroke_fill=(0, 0, 0, 240))

    # 2. Centered Artwork Frame (x=28..692, y=282..780 -> 664x498)
    fx0, fy0, fx1, fy1 = 28, 282, SW - 28, 780
    fw, fh = fx1 - fx0, fy1 - fy0
    sc_art = max(fw / raw.width, fh / raw.height)
    aw, ah = int(raw.width * sc_art), int(raw.height * sc_art)
    art_crop = raw.resize((aw, ah), Image.Resampling.LANCZOS).crop(((aw - fw) // 2, (ah - fh) // 2, (aw - fw) // 2 + fw, (ah - fh) // 2 + fh))
    art_crop = ImageEnhance.Contrast(art_crop).enhance(1.06)

    mask = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fw, fh), radius=22, fill=255)
    bg_blur.paste(art_crop.convert("RGBA"), (fx0, fy0), mask)
    draw.rounded_rectangle((fx0, fy0, fx1, fy1), radius=22, fill=None, outline=(56, 189, 248, 245), width=4)

    # Genre pill on top-left of artwork
    genre = meta.get("genre", "90s Retro Mix").upper()
    f_g = load_font(font_path, 19)
    tb_g = draw.textbbox((0, 0), genre, font=f_g)
    gw = (tb_g[2] - tb_g[0]) + 32
    draw.rounded_rectangle((fx0 + 16, fy0 + 16, fx0 + 16 + gw, fy0 + 56), radius=10, fill=(220, 38, 38, 240), outline=(255, 255, 255, 230), width=2)
    draw.text((fx0 + 32, fy0 + 26), genre, font=f_g, fill=(255, 255, 255, 255))

    # 3. Spectrum Frame Box (y=808..1028) where FFmpeg will overlay the large real-time audio spectrum
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

    bg_blur.convert("RGB").save(out_vertical_jpg, "JPEG", quality=95)
    return out_vertical_jpg


def build_short_video(
    bg_jpg: Path,
    src_mp3: Path,
    meta: Dict[str, Any],
    out_short_mp4: Path,
    font_path: str,
) -> Path:
    """
    Synthesize `output_short.mp4` (720x1280, 9:16, 30 seconds):
    - Extracts the 30s..60s climax slice of `src_mp3` (with fallback to 0s..30s if the MP3 is shorter than 60s).
    - Renders the vertical 720x1280 canvas with top English hook text & centered artwork.
    - Overlays a large real-time audio spectrum (`showwaves=s=636x190:mode=cline`) in the center-lower box.
    """
    logger.info(f"Rendering 9:16 Shorts video (30s): {out_short_mp4} ...")
    mp3_dur = get_audio_duration(src_mp3)
    start_sec = 30.0 if mp3_dur >= 62.0 else max(0.0, mp3_dur * 0.2)
    clip_dur = min(30.0, max(10.0, mp3_dur - start_sec))

    with tempfile.TemporaryDirectory(prefix="music_short_") as tmp_s:
        tmp_dir = Path(tmp_s)
        vert_jpg = tmp_dir / "short_canvas.jpg"
        render_short_vertical_canvas(bg_jpg, meta, vert_jpg, font_path)

        fps = 24
        total_frames = int(clip_dur * fps)
        # Subtle breathing zoom on the vertical canvas + large real-time audio spectrum in the box at y=822
        filter_complex = (
            f"[0:v]scale=1440:2560,zoompan=z='1.02+0.02*sin(2*PI*on/{total_frames})':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=720x1280:fps={fps}[bg];"
            f"[1:a]atrim=start={start_sec:.2f}:duration={clip_dur:.2f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=1.0,afade=t=out:st={max(1.0, clip_dur - 1.5):.2f}:d=1.5[aud];"
            f"[aud]asplit=2[a_out][a_viz];"
            f"[a_viz]showwaves=s=636x190:mode=cline:rate={fps}:colors=0x38bdf8|0xf472b6|0xfde047,format=rgba[sw];"
            f"[bg][sw]overlay=42:822:shortest=1,format=yuv420p[vout]"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(vert_jpg),
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
            "-tune",
            "stillimage",
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
        help="If stocks/music/queue/ is empty, synthesize a sample retro MP3 for testing.",
    )
    args = parser.parse_args()

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)

    mp3_files = [p for p in QUEUE_DIR.iterdir() if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".m4a")]
    if not mp3_files and args.generate_sample_mp3:
        sample_path = QUEUE_DIR / "sample_retro_citypop_01.mp3"
        generate_synthesized_retro_test_mp3(sample_path, duration_sec=195)

    chosen_mp3, chosen_meta, pool = pick_mp3_and_metadata()
    if not chosen_mp3 or not chosen_meta:
        logger.info("No MP3 in stocks/music/queue/. Exiting cleanly (0).")
        return 0

    font_path = find_bold_font()

    with tempfile.TemporaryDirectory(prefix="music_build_") as tmp_s:
        tmp_dir = Path(tmp_s)
        bg_jpg = tmp_dir / "background_1280x720.jpg"
        hud_png = tmp_dir / "hud_1280x720.png"
        looped_m4a = tmp_dir / "looped_1hour.m4a"

        # Step 1: Download 1280x720 background image from Pollinations.ai (with automatic retro fallback)
        download_background_image(chosen_meta, bg_jpg)

        # Step 2: Render HUD overlay and YouTube thumbnail
        render_16x9_hud_and_thumb(bg_jpg, chosen_meta, hud_png, OUTPUT_THUMB, font_path)

        # Step 3: Build looped 1-hour audio + 16:9 video (`output_1hour.mp4`)
        build_1hour_loop_audio(chosen_mp3, looped_m4a, target_duration_sec=args.duration)
        build_1hour_video(bg_jpg, hud_png, looped_m4a, OUTPUT_1HOUR, duration_sec=args.duration)

        # Step 4: Build 9:16 vertical Short (`output_short.mp4`) from 30s..60s of the MP3
        build_short_video(bg_jpg, chosen_mp3, chosen_meta, OUTPUT_SHORT, font_path)

    if args.dry_run:
        logger.info("Dry-run complete! Videos generated at:")
        logger.info(f"  - 1-Hour Video : {OUTPUT_1HOUR}")
        logger.info(f"  - Short Video  : {OUTPUT_SHORT}")
        logger.info(f"  - Thumbnail    : {OUTPUT_THUMB}")
        return 0

    # Step 5: Upload both videos to YouTube & move MP3 to done/
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

    short_title = f"{chosen_meta.get('short_hook_text', '90s Retro Vibes')} | {chosen_meta['genre']} #Shorts"
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
