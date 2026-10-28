#!/usr/bin/env python3
"""
build_and_upload.py

Supports both:
1. Standard stock JSONs (`title`, `image_prompt`)
2. Animal Battle Long + Shorts hybrid JSONs (`title_long`, `title_short`, `flow_clip_filename`,
   `fallback_image_prompt`, `is_short_included`)

Features:
- Generates TTS narration with `edge-tts` and measures exact duration via `ffprobe`.
- Downloads background images from Pollinations.ai (free, no API key required) or uses Google Flow MP4 clips.
- Renders a crisp semi-transparent black bar + Japanese/English subtitles via Pillow + FFmpeg `overlay`
  (works on all FFmpeg builds including macOS Homebrew FFmpeg without requiring `libfreetype`/`drawtext`).
- Applies smooth FFmpeg `zoompan` matched to exact narration duration.
- Builds both the full 16:9 Long video (`1280x720`) AND the vertical 9:16 YouTube Shorts video (`1080x1920`).
- Mixes looped BGM from `assets/bgm/` at 15% volume.
"""

import argparse
import asyncio
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
from pathlib import Path
from typing import Any, Dict, List, Optional

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STOCKS_DIR = BASE_DIR / "stocks"
BGM_DIR = BASE_DIR / "assets" / "bgm"
FLOW_CLIPS_DIR = BASE_DIR / "assets" / "flow_clips"
OUTPUT_DIR = BASE_DIR / "output"

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
VIDEO_FPS = 25


def find_cjk_font() -> str:
    """Locate Ubuntu's `fonts-noto-cjk` or macOS Japanese font."""
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            logger.info(f"Using font: {path}")
            return path

    try:
        res = subprocess.run(
            ["fc-match", "-f", "%{file}", "Noto Sans CJK JP"],
            capture_output=True,
            text=True,
            check=True,
        )
        matched = res.stdout.strip()
        if matched and os.path.exists(matched):
            return matched
    except Exception:
        pass

    raise FileNotFoundError(
        "Could not find CJK font. On Ubuntu: sudo apt-get install -y fonts-noto-cjk"
    )


async def generate_tts_audio(text: str, voice: str, output_mp3: Path) -> None:
    """Generate MP3 narration from text using edge-tts with retries."""
    last_err = None
    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            await communicate.save(str(output_mp3))
            if output_mp3.exists() and output_mp3.stat().st_size > 0:
                return
        except Exception as exc:
            last_err = exc
            logger.warning(f"edge-tts attempt {attempt}/3 failed: {exc}")
            await asyncio.sleep(2 * attempt)
    raise RuntimeError(f"Failed to generate TTS audio after 3 attempts: {last_err}")


def get_audio_duration(audio_path: Path) -> float:
    """Return exact duration in seconds of an audio file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return max(float(res.stdout.strip()), 1.0)


def download_pollinations_image(prompt: str, output_img: Path, seed: int) -> None:
    """Download background image from Pollinations.ai (free, no API key required)."""
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={VIDEO_WIDTH}&height={VIDEO_HEIGHT}&nologo=true&seed={seed}"
    )
    headers = {"User-Agent": "Mozilla/5.0 YouTubeAutoPipeline/2.0"}

    for attempt in range(1, 4):
        try:
            logger.info(f"Downloading image from Pollinations.ai (attempt {attempt}/3)...")
            resp = requests.get(url, headers=headers, timeout=45)
            if resp.status_code == 200 and len(resp.content) > 1024:
                output_img.write_bytes(resp.content)
                return
            logger.warning(f"Pollinations status {resp.status_code}")
        except Exception as exc:
            logger.warning(f"Image download attempt {attempt}/3 error: {exc}")
        time.sleep(2 * attempt)

    logger.warning("Pollinations.ai unreachable; generating stylized fallback visual.")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (18, 24, 38))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        r = int(18 + (y / VIDEO_HEIGHT) * 35)
        g = int(24 + (y / VIDEO_HEIGHT) * 20)
        b = int(38 + (y / VIDEO_HEIGHT) * 45)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))
    img.save(output_img, quality=92)


def render_subtitle_overlay_png(
    subtitle_text: str,
    font_path: str,
    output_png: Path,
    width: int,
    height: int,
    is_vertical: bool = False,
) -> None:
    """
    Render a transparent RGBA overlay with a semi-transparent black bottom bar
    and crisp outlined subtitle text.
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_height = 290 if is_vertical else 185
    bar_y0 = height - bar_height - (180 if is_vertical else 0)
    bar_y1 = bar_y0 + bar_height

    # Semi-transparent black bar (68% opacity)
    draw.rectangle([(0, bar_y0), (width, bar_y1)], fill=(0, 0, 0, 175))

    font_size = 38 if is_vertical else 31
    font = ImageFont.truetype(font_path, font_size)

    normalized_sub = subtitle_text.replace("\\n", "\n").strip()
    raw_lines = normalized_sub.split("\n")

    # Auto-wrap any overly long line so it stays comfortably within the frame
    max_pixel_w = width - 90
    wrapped_lines: List[str] = []
    for line in raw_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        if (bbox[2] - bbox[0]) <= max_pixel_w:
            wrapped_lines.append(line)
        else:
            cur = ""
            for ch in line:
                test = cur + ch
                tb = draw.textbbox((0, 0), test, font=font)
                if (tb[2] - tb[0]) > max_pixel_w and cur:
                    wrapped_lines.append(cur)
                    cur = ch
                else:
                    cur = test
            if cur:
                wrapped_lines.append(cur)

    line_spacing = 12
    line_heights: List[int] = []
    line_widths: List[int] = []
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(max(bbox[3] - bbox[1], font_size))

    total_text_h = sum(line_heights) + line_spacing * max(len(wrapped_lines) - 1, 0)
    cur_y = bar_y0 + (bar_height - total_text_h) // 2

    for line, lw, lh in zip(wrapped_lines, line_widths, line_heights):
        x = (width - lw) // 2
        draw.text(
            (x, cur_y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=3,
            stroke_fill=(0, 0, 0, 235),
        )
        cur_y += lh + line_spacing

    overlay.save(output_png, "PNG")


def build_zoompan_filter(
    scene_index: int, total_frames: int, width: int, height: int
) -> str:
    """Build smooth FFmpeg zoompan filter string."""
    mode = scene_index % 4
    if mode == 0:
        z_expr = "min(zoom+0.0008,1.18)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 1:
        z_expr = "1.14"
        x_expr = f"(iw-iw/zoom)*(on/{max(total_frames, 1)})"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 2:
        z_expr = "if(eq(on,1),1.18,max(zoom-0.0008,1.0))"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        z_expr = "1.14"
        x_expr = f"(iw-iw/zoom)*(1-on/{max(total_frames, 1)})"
        y_expr = "ih/2-(ih/zoom/2)"

    return (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s={width}x{height}:fps={VIDEO_FPS}"
    )


def create_scene_video(
    scene_index: int,
    image_path: Optional[Path],
    flow_clip_path: Optional[Path],
    audio_path: Path,
    subtitle_text: str,
    font_path: str,
    output_scene_mp4: Path,
    work_dir: Path,
    is_vertical: bool = False,
) -> None:
    """
    Render a single scene MP4 (either 16:9 or 9:16 Shorts).
    Uses `flow_clip_path` if present in `assets/flow_clips/`, otherwise uses `image_path` + `zoompan`,
    and composites the Pillow-rendered subtitle overlay PNG.
    """
    width = SHORT_WIDTH if is_vertical else VIDEO_WIDTH
    height = SHORT_HEIGHT if is_vertical else VIDEO_HEIGHT
    duration = get_audio_duration(audio_path)
    scene_duration = round(duration + 0.2, 3)
    total_frames = max(int(math.ceil(scene_duration * VIDEO_FPS)), VIDEO_FPS)

    tag = "short" if is_vertical else "long"
    overlay_png = work_dir / f"overlay_{tag}_{scene_index:02d}.png"
    render_subtitle_overlay_png(
        subtitle_text=subtitle_text,
        font_path=font_path,
        output_png=overlay_png,
        width=width,
        height=height,
        is_vertical=is_vertical,
    )

    if flow_clip_path and flow_clip_path.exists():
        logger.info(
            f"Using Google Flow clip '{flow_clip_path.name}' for scene {scene_index + 1} ({tag})"
        )
        scale_crop = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={VIDEO_FPS}"
        )
        filter_complex = (
            f"[0:v]{scale_crop}[bg];"
            f"[bg][1:v]overlay=0:0,format=yuv420p[vout]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(flow_clip_path),
            "-i",
            str(overlay_png),
            "-i",
            str(audio_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "2:a",
            "-t",
            f"{scene_duration:.3f}",
            "-r",
            str(VIDEO_FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            str(output_scene_mp4),
        ]
    else:
        assert image_path is not None
        zoompan_chain = build_zoompan_filter(scene_index, total_frames, width, height)
        filter_complex = (
            f"[0:v]{zoompan_chain}[bg];"
            f"[bg][1:v]overlay=0:0,format=yuv420p[vout]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(image_path),
            "-i",
            str(overlay_png),
            "-i",
            str(audio_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "2:a",
            "-t",
            f"{scene_duration:.3f}",
            "-r",
            str(VIDEO_FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            str(output_scene_mp4),
        ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def select_bgm_file(channel: str) -> Optional[Path]:
    if not BGM_DIR.exists():
        return None
    extensions = ("*.mp3", "*.wav", "*.m4a", "*.ogg", "*.flac")
    channel_matches: List[Path] = []
    all_matches: List[Path] = []
    for ext in extensions:
        for file_path in sorted(BGM_DIR.glob(ext)):
            all_matches.append(file_path)
            if file_path.name.lower().startswith(channel.lower()):
                channel_matches.append(file_path)
    if channel_matches:
        return random.choice(channel_matches)
    if all_matches:
        return random.choice(all_matches)
    return None


def generate_fallback_bgm(output_bgm_path: Path, duration: float = 60.0) -> Path:
    expr = (
        "0.12*sin(2*PI*110*t)+0.08*sin(2*PI*164.81*t)+"
        "0.06*sin(2*PI*220*t)+0.05*sin(2*PI*277.18*t)"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"aevalsrc='{expr}':s=44100:d={duration}",
        "-af",
        "lowpass=f=800,afade=t=in:st=0:d=2,afade=t=out:st=58:d=2",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(output_bgm_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_bgm_path


def concat_and_mix_bgm(
    scene_videos: List[Path],
    channel: str,
    final_output_mp4: Path,
    work_dir: Path,
    prefix: str = "long",
) -> None:
    concat_list_path = work_dir / f"concat_list_{prefix}.txt"
    lines = [f"file '{v.resolve()}'" for v in scene_videos]
    concat_list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    merged_no_bgm = work_dir / f"merged_{prefix}_no_bgm.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list_path),
            "-c",
            "copy",
            str(merged_no_bgm),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    bgm_file = select_bgm_file(channel)
    if bgm_file is None:
        bgm_file = generate_fallback_bgm(work_dir / "fallback_bgm.mp3")

    filter_complex = (
        "[0:a]volume=1.0[voice];"
        "[1:a]volume=0.15[bgm];"
        "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(merged_no_bgm),
            "-stream_loop",
            "-1",
            "-i",
            str(bgm_file),
            "-filter_complex",
            filter_complex,
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
            "-shortest",
            str(final_output_mp4),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def upload_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    channel: str,
) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    channel_upper = channel.upper()
    client_id = (
        os.environ.get(f"YOUTUBE_CLIENT_ID_{channel_upper}")
        or os.environ.get("YOUTUBE_CLIENT_ID")
    )
    client_secret = (
        os.environ.get(f"YOUTUBE_CLIENT_SECRET_{channel_upper}")
        or os.environ.get("YOUTUBE_CLIENT_SECRET")
    )
    refresh_token = (
        os.environ.get(f"YOUTUBE_REFRESH_TOKEN_{channel_upper}")
        or os.environ.get("YOUTUBE_REFRESH_TOKEN")
    )

    if not (client_id and client_secret and refresh_token):
        raise RuntimeError(
            f"Missing YouTube OAuth2 environment variables for channel '{channel}'."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)

    privacy_status = os.environ.get("YOUTUBE_PRIVACY_STATUS", "public")
    category_id = "15" if channel == "animal_battle" else "22"
    default_lang = "ja" if channel == "animal_battle" else "en"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": default_lang,
            "defaultAudioLanguage": default_lang,
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

    logger.info(f"Uploading '{title}' to YouTube ({privacy_status})...")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id", "unknown")
    logger.info(f"Successfully uploaded! https://youtu.be/{video_id}")
    return video_id


def process_one_script(
    channel: str, skip_upload: bool = False, specific_script: Optional[str] = None
) -> bool:
    queue_dir = STOCKS_DIR / channel / "queue"
    done_dir = STOCKS_DIR / channel / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if specific_script:
        candidate = Path(specific_script)
        if not candidate.exists():
            candidate = queue_dir / specific_script
        if not candidate.exists():
            raise FileNotFoundError(f"Script file not found: {specific_script}")
        script_path = candidate
    else:
        queue_files = sorted(queue_dir.glob("*.json"))
        if not queue_files:
            logger.info(f"[{channel}] No pending JSON scripts found in {queue_dir}.")
            return False
        script_path = queue_files[0]

    logger.info(f"[{channel}] Processing script: {script_path.name}")

    with script_path.open("r", encoding="utf-8") as f:
        script_data = json.load(f)

    voice = script_data.get("voice") or (
        "ja-JP-KeitaNeural" if channel == "animal_battle" else "en-US-ChristopherNeural"
    )
    scenes = script_data.get("scenes", [])
    if not scenes:
        raise ValueError(f"Script {script_path} contains no scenes.")

    font_path = find_cjk_font()
    final_long_mp4 = OUTPUT_DIR / f"{channel}_{script_path.stem}_long.mp4"
    final_short_mp4 = OUTPUT_DIR / f"{channel}_{script_path.stem}_short.mp4"

    has_shorts = any(s.get("is_short_included") for s in scenes)

    with tempfile.TemporaryDirectory(prefix=f"yt_{channel}_") as tmp_dir_str:
        work_dir = Path(tmp_dir_str)
        long_scene_videos: List[Path] = []
        short_scene_videos: List[Path] = []

        for idx, scene in enumerate(scenes):
            narration = scene["narration"].strip()
            subtitle = scene["subtitle"].strip()
            img_prompt = (
                scene.get("fallback_image_prompt") or scene.get("image_prompt") or ""
            ).strip()
            flow_clip_name = scene.get("flow_clip_filename")
            flow_clip_path = (
                FLOW_CLIPS_DIR / flow_clip_name if flow_clip_name else None
            )

            audio_path = work_dir / f"scene_{idx:02d}.mp3"
            image_path = work_dir / f"scene_{idx:02d}.jpg"
            long_scene_mp4 = work_dir / f"scene_long_{idx:02d}.mp4"

            logger.info(f"[{channel}] Scene {idx + 1}/{len(scenes)}: Generating TTS...")
            asyncio.run(generate_tts_audio(narration, voice, audio_path))

            if not (flow_clip_path and flow_clip_path.exists()):
                seed = abs(hash(f"{script_path.stem}_{idx}")) % 1000000
                download_pollinations_image(img_prompt, image_path, seed=seed)

            logger.info(
                f"[{channel}] Scene {idx + 1}/{len(scenes)}: Rendering video scene..."
            )
            create_scene_video(
                scene_index=idx,
                image_path=image_path,
                flow_clip_path=flow_clip_path,
                audio_path=audio_path,
                subtitle_text=subtitle,
                font_path=font_path,
                output_scene_mp4=long_scene_mp4,
                work_dir=work_dir,
                is_vertical=False,
            )
            long_scene_videos.append(long_scene_mp4)

            if scene.get("is_short_included"):
                short_scene_mp4 = work_dir / f"scene_short_{idx:02d}.mp4"
                create_scene_video(
                    scene_index=idx,
                    image_path=image_path,
                    flow_clip_path=flow_clip_path,
                    audio_path=audio_path,
                    subtitle_text=subtitle,
                    font_path=font_path,
                    output_scene_mp4=short_scene_mp4,
                    work_dir=work_dir,
                    is_vertical=True,
                )
                short_scene_videos.append(short_scene_mp4)

        concat_and_mix_bgm(
            scene_videos=long_scene_videos,
            channel=channel,
            final_output_mp4=final_long_mp4,
            work_dir=work_dir,
            prefix="long",
        )
        logger.info(f"[{channel}] Long MP4 created: {final_long_mp4}")

        if has_shorts and short_scene_videos:
            concat_and_mix_bgm(
                scene_videos=short_scene_videos,
                channel=channel,
                final_output_mp4=final_short_mp4,
                work_dir=work_dir,
                prefix="short",
            )
            logger.info(f"[{channel}] Shorts MP4 created: {final_short_mp4}")

    if skip_upload:
        logger.info(
            f"[{channel}] --skip-upload set. Keeping {script_path.name} in queue."
        )
        return True

    title_long = script_data.get("title_long") or script_data.get("title", "")
    description = script_data.get("description", "")
    tags = script_data.get("tags", [])

    upload_to_youtube(final_long_mp4, title_long, description, tags, channel)

    if has_shorts and final_short_mp4.exists() and script_data.get("title_short"):
        upload_to_youtube(
            final_short_mp4,
            script_data["title_short"],
            description,
            tags + ["Shorts"],
            channel,
        )

    dest_path = done_dir / script_path.name
    shutil.move(str(script_path), str(dest_path))
    logger.info(f"[{channel}] Moved consumed script to: {dest_path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Long & Shorts MP4s from stock JSON and upload to YouTube."
    )
    parser.add_argument(
        "--channel",
        choices=["overseas_japan", "animal_battle", "all"],
        default="all",
        help="Target channel queue to process (default: all).",
    )
    parser.add_argument(
        "--script",
        default=None,
        help="Optional specific JSON filename or path (e.g. battle_006.json).",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Generate the MP4 video(s) without uploading to YouTube or moving the JSON.",
    )
    args = parser.parse_args()

    channels = (
        ["overseas_japan", "animal_battle"]
        if args.channel == "all"
        else [args.channel]
    )

    for ch in channels:
        process_one_script(
            channel=ch, skip_upload=args.skip_upload, specific_script=args.script
        )


if __name__ == "__main__":
    main()
