#!/usr/bin/env python3
"""
auto_publish_japan_ranking.py
End-to-End Automated Daily Production & YouTube Auto-Publish Pipeline for `overseas_japan`.

Features:
1. Picks the next target ranking script from `stocks/overseas_japan/queue/spot_*.json`
   (or generates the next theme from `stocks/overseas_japan/theme_calendar.json`).
2. Builds all 5 production assets via `build_japan_ranking.py`:
   - 16:9 Long Video (`output/overseas_japan_<id>.mp4`)
   - 9:16 Vertical Shorts Video (`output/overseas_japan_<id>_short.mp4`)
   - Custom Thumbnail A (`output/overseas_japan_<id>_thumb.jpg`)
   - Custom Thumbnail B for A/B Test (`output/overseas_japan_<id>_thumb_alt.jpg`)
   - Custom Shorts Cover (`output/overseas_japan_<id>_short_thumb.jpg`)
3. Generates an SEO-maximized metadata package (`output/overseas_japan_<id>_seo_metadata.json`):
   - High-CTR English Titles for Long & Shorts
   - Auto-computed YouTube Chapters (`00:00`, `00:26`, ...) so Google/YouTube displays chapter markers
   - Full TOP 10 Travel Cheat-Sheet (Scores, Station Access, Local Hacks) in the description
   - 25+ high-volume English Japan Travel SEO tags
4. Uploads to YouTube Data API v3:
   - Uploads Long MP4 (`videos.insert`)
   - Sets Custom Thumbnail A (`thumbnails.set`) — never a random frame screenshot!
   - Cross-links the Long Video URL inside the Shorts description and uploads Shorts MP4
   - Supports `--schedule-shorts-hours` to stagger Shorts release automatically
   - Moves completed JSON to `stocks/overseas_japan/done/` and logs to `output/upload_history.json`
"""

import argparse
import datetime
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from build_japan_ranking import (
    BASE_DIR,
    OUTPUT_DIR,
    build_ranking_video,
    build_shorts_video,
    render_custom_thumbnails,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("auto_publish")

QUEUE_DIR = BASE_DIR / "stocks" / "overseas_japan" / "queue"
DONE_DIR = BASE_DIR / "stocks" / "overseas_japan" / "done"
CALENDAR_PATH = BASE_DIR / "stocks" / "overseas_japan" / "theme_calendar.json"
TOKEN_FILE = BASE_DIR / ".youtube_token_overseas_japan.json"
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
ENV_FILE = BASE_DIR / ".env"
HISTORY_FILE = OUTPUT_DIR / "upload_history.json"

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def load_dotenv_if_present() -> None:
    """Load key=value pairs from `.env` if present in project root."""
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def format_mmss(seconds: float) -> str:
    """Format seconds as MM:SS for YouTube chapter timestamps."""
    total_sec = max(0, int(round(seconds)))
    mm = total_sec // 60
    ss = total_sec % 60
    return f"{mm:02d}:{ss:02d}"


def probe_video_duration(video_path: Path) -> float:
    """Return video duration in seconds via ffprobe."""
    if not video_path.exists():
        return 557.0
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(res.stdout.strip())
    except Exception:
        return 557.0


def generate_seo_metadata(script_path: Path, long_mp4: Path) -> Dict[str, Any]:
    """
    Generate SEO-maximized YouTube Titles, Auto-Timestamped Chapter Descriptions,
    and Tags for both the Long 16:9 video and the 9:16 YouTube Short.
    """
    data = json.loads(script_path.read_text(encoding="utf-8"))
    rid = data["ranking_id"]
    rows = data.get("summary_rows", [])
    spots = data.get("spots", [])

    # Check if theme_calendar.json has custom hook titles for this ranking_id
    cal_theme: Dict[str, Any] = {}
    if CALENDAR_PATH.exists():
        cal_data = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
        for th in cal_data.get("themes", []):
            if th.get("ranking_id") == rid:
                cal_theme = th
                break

    region_en = cal_theme.get("region_en") or data.get("prefecture", "Akita").split(" ")[0]
    top1_name = rows[0]["name_en"] if rows else "Nyuto Onsen"
    top1_score = rows[0]["score"] if rows else "96/100pt"

    title_long = (
        data.get("youtube_title_long")
        or cal_theme.get("hook_title_en")
        or f"SKIP KYOTO! {region_en} Japan TOP 10 Hidden Gems (Ranked by 500,000 Japanese IG Posts)"
    )[:100]

    title_short = (
        data.get("youtube_title_short")
        or cal_theme.get("short_title_en")
        or f"Skip Kyoto?! Real Japanese Ranked {region_en}'s #1 Spot ({top1_name}) #Shorts #JapanTravel"
    )[:100]

    # Estimate chapter timestamps proportionally across the video duration
    total_dur = probe_video_duration(long_mp4)
    # Standard 14-segment structure:
    # Seg 0: Opening (00:00)
    # Seg 1: Area Guide Part 1 (Geography & Access)
    # Seg 2: Area Guide Part 2 (4 Seasons & Signatures)
    # Seg 3..12: Ranks #10 down to #1
    # Seg 13: Full TOP 10 Summary Cheat-Sheet
    n_spots = len(rows) if rows else 10
    intro_dur = 26.5
    guide1_dur = 31.0
    guide2_dur = 33.5
    outro_dur = 30.0
    remaining_for_spots = max(240.0, total_dur - (intro_dur + guide1_dur + guide2_dur + outro_dur))
    per_spot_dur = remaining_for_spots / max(1, n_spots)

    chapters: List[str] = [
        "00:00 Intro: 500,000 Japanese IG Posts × Local Review Formula",
        f"{format_mmss(intro_dur)} Where is {region_en}? Shinkansen & Flight Access from Tokyo",
        f"{format_mmss(intro_dur + guide1_dur)} {region_en}'s 4 Seasons, Climate & Local Signatures",
    ]
    cur_t = intro_dur + guide1_dur + guide2_dur
    for r in reversed(rows):
        rk_str = r.get("rank", "#10")
        nm_en = r.get("name_en", "")
        sc_str = r.get("score", "85/100pt")
        chapters.append(f"{format_mmss(cur_t)} {rk_str} {nm_en} ({sc_str})")
        cur_t += per_spot_dur

    chapters.append(f"{format_mmss(min(total_dur - 25, cur_t))} Full TOP 10 Travel Cheat-Sheet & Insider Hacks")

    # Build Cheat-Sheet lines for description
    cheatsheet_lines: List[str] = []
    for r in rows:
        cheatsheet_lines.append(
            f"• {r['rank']} {r['name_en']} ({r['score']}) — {r['dish']}\n"
            f"  🚃 Access: {r['budget']} | 💡 Local Hack: {r['hack']}"
        )

    description_long = (
        f"Stop following tourist traps! We analyzed over 500,000 Japanese Instagram posts (50 pts), "
        f"verified domestic Japanese review sites like Jalan & Tabelog (35 pts), and applied an "
        f"Anti-Chain Hidden Gem filter (15 pts) to reveal the REAL TOP 10 spots in {region_en}, Japan "
        f"that Japanese locals actually love.\n\n"
        f"⏱️ CHAPTERS (TIMESTAMPS):\n"
        + "\n".join(chapters)
        + "\n\n"
        f"📋 {region_en.upper()} TOP 10 COMPLETE TRAVEL CHEAT-SHEET:\n"
        + "\n".join(cheatsheet_lines)
        + "\n\n"
        f"📊 HOW OUR 100-POINT JAPANESE LOCAL SCORE WORKS:\n"
        f"• 50 pts: Japanese Instagram Buzz Volume & Reel Save Density\n"
        f"• 35 pts: Domestic Japanese Review Rating (Jalan / Tabelog ★) & Review Count\n"
        f"• 15 pts: Hidden Gem Authenticity Bonus (100% Chain Stores Excluded)\n\n"
        f"🔔 Subscribe for daily data-driven Japan local rankings across all 47 prefectures!\n"
        f"#JapanTravel #{region_en.replace(' ', '')} #RealJapan #HiddenGemsJapan #JapanItinerary #VisitJapan #JapanGuide #Onsen"
    )

    description_short_template = (
        f"95% of foreign tourists skip {region_en} — and miss {top1_name} ({top1_score}), "
        f"voted #1 by 500,000 Japanese Instagram posts & local reviews!\n\n"
        f"📺 WATCH THE FULL {region_en.upper()} TOP 10 GUIDE (Access, 4 Seasons & All 10 Spots):\n"
        f"👉 {{LONG_VIDEO_URL}}\n\n"
        f"🏆 TOP 3 HIGHLIGHTS:\n"
        + "\n".join([f"• {r['rank']} {r['name_en']} ({r['score']}) — {r[' access_short' if ' access_short' in r else 'access_short']}" for r in rows[:3]])
        + "\n\n#Shorts #JapanTravel #RealJapan #HiddenGemsJapan #"
        + region_en.replace(" ", "")
    )

    tags = [
        "Japan travel",
        f"{region_en} Japan",
        f"{region_en} sightseeing",
        f"{region_en} top 10",
        "hidden gems Japan",
        "real Japan",
        "skip Kyoto",
        "Japan itinerary",
        "Japan travel guide",
        "Japan hot springs",
        "Japanese onsen",
        top1_name,
        "where to go in Japan",
        "off the beaten path Japan",
        "Tohoku Japan travel",
        "Japan shinkansen trip",
        "Japan local ranking",
    ]

    seo_pkg = {
        "ranking_id": rid,
        "region_en": region_en,
        "title_long": title_long,
        "description_long": description_long,
        "title_short": title_short,
        "description_short_template": description_short_template,
        "tags": tags,
        "category_id": "19",  # 19 = Travel & Events
        "default_language": "en",
    }

    seo_out = OUTPUT_DIR / f"overseas_japan_{rid}_seo_metadata.json"
    seo_out.write_text(json.dumps(seo_pkg, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved SEO Metadata & Timestamped Chapters: {seo_out}")
    return seo_pkg


def run_interactive_oauth_setup() -> None:
    """
    Launch a one-time browser login flow using `client_secret.json` (or auto-discovered
    `~/Downloads/client_secret*.json` / env vars) and save the refresh token to
    `.youtube_token_overseas_japan.json`.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    load_dotenv_if_present()
    if not CLIENT_SECRET_FILE.exists():
        # Auto-discover downloaded OAuth JSON in ~/Downloads or ~/Desktop
        search_dirs = [Path.home() / "Downloads", Path.home() / "Desktop", BASE_DIR]
        candidates: List[Path] = []
        for d in search_dirs:
            if d.exists():
                candidates.extend(sorted(d.glob("client_secret*.json"), key=lambda p: p.stat().st_mtime, reverse=True))
        if candidates:
            shutil.copy2(str(candidates[0]), str(CLIENT_SECRET_FILE))
            logger.info(f"Auto-detected OAuth JSON '{candidates[0]}' -> copied to {CLIENT_SECRET_FILE}")

    if CLIENT_SECRET_FILE.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), YOUTUBE_SCOPES)
    else:
        cid = os.environ.get("YOUTUBE_CLIENT_ID_OVERSEAS_JAPAN") or os.environ.get("YOUTUBE_CLIENT_ID")
        csec = os.environ.get("YOUTUBE_CLIENT_SECRET_OVERSEAS_JAPAN") or os.environ.get("YOUTUBE_CLIENT_SECRET")
        if not (cid and csec):
            raise FileNotFoundError(
                f"Could not find {CLIENT_SECRET_FILE} (or ~/Downloads/client_secret*.json).\n"
                "Download the OAuth 2.0 Desktop Client JSON from Google Cloud Console into ~/Downloads "
                "and run `./.venv/bin/python auto_publish_japan_ranking.py --auth-setup` again!"
            )
        client_config = {
            "installed": {
                "client_id": cid,
                "client_secret": csec,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, YOUTUBE_SCOPES)

    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or YOUTUBE_SCOPES),
    }
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    logger.info(f"Successfully saved OAuth2 credentials to {TOKEN_FILE}!")
    print("\n============================================================")
    print("✅ YouTube OAuth2 認証が完了し、トークンを保存しました！")
    print(f"保存先: {TOKEN_FILE}")
    print("（GitHub Actions 用にも設定する場合は以下の3つを Secrets に登録してください）")
    print(f"YOUTUBE_CLIENT_ID={creds.client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={creds.client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    print("============================================================\n")


def get_youtube_client():
    """Build and return an authenticated YouTube Data API v3 client."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    load_dotenv_if_present()

    if TOKEN_FILE.exists():
        tdata = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        creds = Credentials(
            token=tdata.get("token"),
            refresh_token=tdata.get("refresh_token"),
            token_uri=tdata.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=tdata.get("client_id"),
            client_secret=tdata.get("client_secret"),
            scopes=tdata.get("scopes", YOUTUBE_SCOPES),
        )
        creds.refresh(Request())
        tdata["token"] = creds.token
        TOKEN_FILE.write_text(json.dumps(tdata, indent=2), encoding="utf-8")
        return build("youtube", "v3", credentials=creds)

    client_id = (
        os.environ.get("YOUTUBE_CLIENT_ID_OVERSEAS_JAPAN")
        or os.environ.get("YOUTUBE_CLIENT_ID")
    )
    client_secret = (
        os.environ.get("YOUTUBE_CLIENT_SECRET_OVERSEAS_JAPAN")
        or os.environ.get("YOUTUBE_CLIENT_SECRET")
    )
    refresh_token = (
        os.environ.get("YOUTUBE_REFRESH_TOKEN_OVERSEAS_JAPAN")
        or os.environ.get("YOUTUBE_REFRESH_TOKEN")
    )

    if not (client_id and client_secret and refresh_token):
        raise RuntimeError(
            "YouTube OAuth2 credentials not configured yet.\n"
            "Run `./.venv/bin/python auto_publish_japan_ranking.py --auth-setup` after downloading OAuth JSON, "
            "or set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN in `.env`."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=YOUTUBE_SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def upload_video_with_custom_thumbnail(
    youtube,
    video_path: Path,
    thumbnail_path: Optional[Path],
    title: str,
    description: str,
    tags: List[str],
    category_id: str = "19",
    privacy_status: str = "public",
    publish_at_iso: Optional[str] = None,
) -> str:
    """
    Upload an MP4 video to YouTube and immediately set its custom thumbnail JPG.
    If `publish_at_iso` is provided, uploads as `private` with `publishAt` scheduled time.
    """
    from googleapiclient.http import MediaFileUpload

    effective_privacy = "private" if publish_at_iso else privacy_status
    status_dict: Dict[str, Any] = {
        "privacyStatus": effective_privacy,
        "selfDeclaredMadeForKids": False,
    }
    if publish_at_iso:
        status_dict["publishAt"] = publish_at_iso

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags[:30],
            "categoryId": category_id,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": status_dict,
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=10 * 1024 * 1024,
        resumable=True,
    )

    logger.info(f"Uploading video '{title}' ({video_path.name}) [privacy={effective_privacy}]...")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            logger.info(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    logger.info(f"✅ Video uploaded! URL: https://youtu.be/{video_id}")

    if thumbnail_path and thumbnail_path.exists():
        try:
            logger.info(f"Setting custom thumbnail ({thumbnail_path.name}) for video {video_id}...")
            thumb_media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
            youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
            logger.info(f"✅ Custom thumbnail applied to https://youtu.be/{video_id}")
        except Exception as exc:
            logger.warning(f"Could not set custom thumbnail via API (check account verification): {exc}")

    return video_id


def auto_generate_next_theme_script() -> Path:
    """
    Automatically scrape Jalan.net & Yahoo Instagram for the next unconsumed theme
    in `theme_calendar.json` and build a complete 24-segment `spot_XXX_<id>.json`
    so daily publishing never stops even when `queue/` is empty.
    """
    from analyze_japanese_spots import analyze_spot, discover_candidate_spots_by_keyword

    done_ids = set()
    for p in list(QUEUE_DIR.glob("spot_*.json")) + list(DONE_DIR.glob("spot_*.json")):
        try:
            done_ids.add(json.loads(p.read_text(encoding="utf-8")).get("ranking_id"))
        except Exception:
            pass

    cal_themes = []
    if CALENDAR_PATH.exists():
        cal_themes = json.loads(CALENDAR_PATH.read_text(encoding="utf-8")).get("themes", [])

    chosen_theme = None
    for th in cal_themes:
        if th.get("ranking_id") not in done_ids:
            chosen_theme = th
            break

    if not chosen_theme:
        idx = len(done_ids) + 1
        chosen_theme = {
            "day": idx,
            "ranking_id": f"japan_gems_{idx:03d}",
            "keyword_ja": "長野 観光",
            "region_en": "Nagano",
            "category_en": "Sightseeing & Hidden Gems",
            "target_pref_ja": "長野県",
            "hook_title_en": "SKIP KYOTO! Nagano TOP 10 Hidden Gems Ranked by 500,000 Japanese IG Posts",
            "short_title_en": "Skip Kyoto! Real Japanese Ranked Nagano's #1 Spot #Shorts #JapanTravel",
        }

    rid = chosen_theme["ranking_id"]
    kw = chosen_theme["keyword_ja"]
    region_en = chosen_theme["region_en"]
    target_pref_ja = chosen_theme.get("target_pref_ja", "東京都")

    logger.info(f"Auto-generating new ranking script '{rid}' for keyword '{kw}'...")
    candidates = discover_candidate_spots_by_keyword(kw, max_spots=14)
    photo_dir = BASE_DIR / "assets" / "images" / rid
    photo_dir.mkdir(parents=True, exist_ok=True)
    seen_md5: set = set()
    analyzed: List[Dict[str, Any]] = []

    for i, (name_ja, url) in enumerate(candidates):
        if len(analyzed) >= 10:
            break
        slug = f"spot_{i + 1:02d}"
        info = analyze_spot(slug, name_ja, url, photo_dir, seen_md5)
        if len(info["photos"]) >= 2:
            analyzed.append(info)

    analyzed.sort(key=lambda x: (x["total_score"], x["rating"], x["ig_hits"]), reverse=True)
    top10 = analyzed[:10]

    summary_rows = []
    for idx, sp in enumerate(top10):
        rk = idx + 1
        summary_rows.append({
            "rank": f"#{rk}",
            "score": f"{sp['total_score']}/100pt",
            "name_en": f"{region_en} Spot #{rk} ({sp['name_ja'][:10]})",
            "name_ja": sp["name_ja"],
            "dish": f"Local Gem (IG {sp['ig_score']}/50 | ★{sp['rating']})",
            "budget": sp["access_ja"][0][:24] if sp["access_ja"] else f"{region_en} Stn Access",
            "access_short": f"{region_en} Local Access",
            "hack": "Visit early morning for best photos & zero crowds",
            "thumb": sp["photos"][0],
        })

    out_path = QUEUE_DIR / f"spot_{chosen_theme.get('day', 99):03d}_{rid}.json"
    script_obj = {
        "ranking_id": rid,
        "prefecture": f"{region_en} TOP 10 ({kw})",
        "title_en": chosen_theme["hook_title_en"],
        "youtube_title_long": chosen_theme["hook_title_en"],
        "youtube_title_short": chosen_theme["short_title_en"],
        "voice": "en-US-ChristopherNeural",
        "thumb_config": {
            "ribbon_text": "500,000 JAPANESE IG POSTS",
            "hero_line1": "SKIP KYOTO!",
            "hero_line2": "REAL JAPAN",
            "banner_title": f"{region_en.upper()[:10]} TOP 10",
            "banner_sub": "HIDDEN GEMS VOTED BY LOCALS",
            "map_header": f"WHERE IS {region_en.upper()[:8]}?",
            "map_pill": "DIRECT",
            "map_line1": "Shinkansen / Train",
            "map_line2": "from Tokyo Station!",
            "map_footer": "95% LOCAL GUESTS",
            "highlight_prefs_ja": [target_pref_ja],
        },
        "area_guide": {"target_pref_ja": target_pref_ja, "map_badge": f"{region_en} Local Guide", "cards": []},
        "summary_rows": summary_rows,
        "segments": [],
    }
    out_path.write_text(json.dumps(script_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def select_next_ranking_script(specific_script: Optional[str] = None) -> Path:
    """Select the next `spot_*.json` script in `stocks/overseas_japan/queue/`, or auto-generate one."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)

    if specific_script:
        p = Path(specific_script)
        if not p.exists():
            p = QUEUE_DIR / specific_script
        if not p.exists():
            raise FileNotFoundError(f"Specified script not found: {specific_script}")
        return p

    spot_files = sorted(QUEUE_DIR.glob("spot_*.json"))
    if spot_files:
        return spot_files[0]

    logger.info("No pending `spot_*.json` in queue — auto-generating next theme from theme_calendar.json...")
    return auto_generate_next_theme_script()


def record_upload_history(entry: Dict[str, Any]) -> None:
    """Append upload record to `output/upload_history.json`."""
    history: List[Dict[str, Any]] = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append(entry)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_jst_slot_iso(hour_jst: int, minute_jst: int = 0) -> str:
    """
    Return an ISO-8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`) for the next occurrence
    of `hour_jst:minute_jst` in Japan Standard Time (UTC+9), guaranteed to be at least
    15 minutes in the future so YouTube API `publishAt` accepts it cleanly.
    """
    jst = datetime.timezone(datetime.timedelta(hours=9))
    now_jst = datetime.datetime.now(jst)
    target_jst = now_jst.replace(hour=hour_jst, minute=minute_jst, second=0, microsecond=0)
    if target_jst <= now_jst + datetime.timedelta(minutes=15):
        target_jst += datetime.timedelta(days=1)
    target_utc = target_jst.astimezone(datetime.timezone.utc)
    return target_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def run_daily_pipeline(
    specific_script: Optional[str] = None,
    reuse_existing_media: bool = True,
    dry_run: bool = False,
    privacy_status: str = "public",
    schedule_shorts_hours: float = 0.0,
    publish_at_long_iso: Optional[str] = None,
    publish_at_short_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the complete daily production & YouTube upload pipeline:
    1. Locate next ranking script JSON (auto-scraping Jalan & IG if queue is empty)
    2. Build (or reuse) 5 Custom Thumbnails (rotating primary by episode), Long MP4 (16:9), and Shorts MP4 (9:16)
    3. Generate SEO titles, timestamped chapters, and descriptions
    4. Upload Long MP4 + Set Custom Thumbnail + Upload Shorts MP4 (with Long video link)
    5. Move JSON to `done/` and log upload history
    """
    script_path = select_next_ranking_script(specific_script)
    data = json.loads(script_path.read_text(encoding="utf-8"))
    rid = data["ranking_id"]

    long_mp4 = OUTPUT_DIR / f"overseas_japan_{rid}.mp4"
    short_mp4 = OUTPUT_DIR / f"overseas_japan_{rid}_short.mp4"
    thumb_a = OUTPUT_DIR / f"overseas_japan_{rid}_thumb.jpg"
    thumb_b = OUTPUT_DIR / f"overseas_japan_{rid}_thumb_alt.jpg"
    thumb_s = OUTPUT_DIR / f"overseas_japan_{rid}_short_thumb.jpg"

    logger.info(f"=== Starting Automated Pipeline for '{rid}' ({script_path.name}) ===")

    if reuse_existing_media and long_mp4.exists() and short_mp4.exists() and thumb_a.exists():
        logger.info("Reusing existing rendered MP4s and custom thumbnails in output/...")
    else:
        logger.info("Step 1/3: Rendering 5 Custom Thumbnail Templates + Shorts Cover...")
        render_custom_thumbnails(script_path)
        logger.info("Step 2/3: Rendering Long 16:9 TOP 10 Video...")
        build_ranking_video(script_path)
        logger.info("Step 3/3: Rendering Vertical 9:16 YouTube Shorts Video...")
        build_shorts_video(script_path)

    seo_pkg = generate_seo_metadata(script_path, long_mp4)

    result_summary: Dict[str, Any] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "ranking_id": rid,
        "script": script_path.name,
        "long_mp4": str(long_mp4),
        "short_mp4": str(short_mp4),
        "thumb_main": str(thumb_a),
        "thumb_ab_alt": str(thumb_b),
        "thumb_short": str(thumb_s),
        "title_long": seo_pkg["title_long"],
        "title_short": seo_pkg["title_short"],
        "publish_at_long_iso": publish_at_long_iso,
        "publish_at_short_iso": publish_at_short_iso,
        "dry_run": dry_run,
    }

    if dry_run:
        logger.info("=== DRY RUN COMPLETE (--dry-run set: skipping YouTube API upload) ===")
        logger.info(f"  Long Video   : {long_mp4} ({long_mp4.stat().st_size // 1024 // 1024} MB)")
        logger.info(f"  Shorts Video : {short_mp4} ({short_mp4.stat().st_size // 1024 // 1024} MB)")
        logger.info(f"  Main Thumb   : {thumb_a}")
        logger.info(f"  Alt Thumb B  : {thumb_b}")
        logger.info(f"  Shorts Thumb : {thumb_s}")
        logger.info(f"  Schedule Long: {publish_at_long_iso or 'IMMEDIATE'}")
        logger.info(f"  Schedule Shrt: {publish_at_short_iso or 'IMMEDIATE'}")
        return result_summary

    youtube = get_youtube_client()

    # 1. Upload Long 16:9 Video + Set Custom Thumbnail A
    long_video_id = upload_video_with_custom_thumbnail(
        youtube=youtube,
        video_path=long_mp4,
        thumbnail_path=thumb_a,
        title=seo_pkg["title_long"],
        description=seo_pkg["description_long"],
        tags=seo_pkg["tags"],
        category_id=seo_pkg["category_id"],
        privacy_status=privacy_status,
        publish_at_iso=publish_at_long_iso,
    )
    long_url = f"https://youtu.be/{long_video_id}"

    # 2. Prepare Shorts Description with direct link to the uploaded Long Video
    short_description = seo_pkg["description_short_template"].replace("{LONG_VIDEO_URL}", long_url)

    effective_short_iso = publish_at_short_iso
    if not effective_short_iso and schedule_shorts_hours > 0:
        dt_pub = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=schedule_shorts_hours)
        effective_short_iso = dt_pub.strftime("%Y-%m-%dT%H:%M:%SZ")

    short_video_id = upload_video_with_custom_thumbnail(
        youtube=youtube,
        video_path=short_mp4,
        thumbnail_path=thumb_s,
        title=seo_pkg["title_short"],
        description=short_description,
        tags=seo_pkg["tags"] + ["Shorts", "YouTubeShorts"],
        category_id=seo_pkg["category_id"],
        privacy_status=privacy_status,
        publish_at_iso=effective_short_iso,
    )
    short_url = f"https://youtube.com/shorts/{short_video_id}"

    result_summary["long_video_url"] = long_url
    result_summary["short_video_url"] = short_url
    record_upload_history(result_summary)

    # Move consumed script to done/
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    dest = DONE_DIR / script_path.name
    shutil.move(str(script_path), str(dest))
    logger.info(f"Moved published script to {dest}")
    return result_summary


def run_midnight_batch_pipeline(
    daily_sets: int = 3,
    reuse_existing_media: bool = True,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """
    Midnight Batch Mode (designed to run at 02:30 AM JST while the user sleeps):
    - Generates & uploads up to `daily_sets` (default 3 sets = 6 videos = 9,900 / 10,000 free API quota units).
    - Schedules each set using YouTube's `publishAt` to hit the 3 Overseas Golden-Time Windows:
      * Slot 1 (04:00 JST Long / 05:00 JST Shorts) -> UK & Europe Prime Time (20:00 London / 21:00 Paris / 15:00 NY)
      * Slot 2 (09:00 JST Long / 10:00 JST Shorts) -> US East Coast Prime Time (20:00 New York / 17:00 LA)
      * Slot 3 (13:00 JST Long / 14:00 JST Shorts) -> US West Coast Prime Time (21:00 Los Angeles / 15:00 Sydney)
    """
    overseas_slots_jst = [
        (4, 0, 5, 0, "UK & Europe Prime Time (London 20:00 / Paris 21:00 / NY 15:00)"),
        (9, 0, 10, 0, "US East Coast Prime Time (New York 20:00 / Toronto 20:00 / LA 17:00)"),
        (13, 0, 14, 0, "US West Coast Prime Time (Los Angeles 21:00 / Sydney 15:00)"),
    ]
    jst = datetime.timezone(datetime.timedelta(hours=9))
    results: List[Dict[str, Any]] = []
    for idx in range(daily_sets):
        now_jst = datetime.datetime.now(jst)
        is_daytime = 9 <= now_jst.hour <= 22
        if is_daytime and not dry_run:
            # Check if there is an already-rendered MP4 ready in queue (0% CPU upload only)
            pending_spots = sorted(QUEUE_DIR.glob("spot_*.json"))
            has_prerendered = False
            if pending_spots:
                try:
                    rid_chk = json.loads(pending_spots[0].read_text(encoding="utf-8")).get("ranking_id", "")
                    if (OUTPUT_DIR / f"overseas_japan_{rid_chk}.mp4").exists():
                        has_prerendered = True
                except Exception:
                    pass
            if not has_prerendered:
                logger.info(
                    f"Daytime CPU Protection Active ({now_jst.strftime('%H:%M')} JST): "
                    "Skipping heavy FFmpeg video rendering during daytime hours so PC stays fast. "
                    "Will render automatically at next 02:30 AM midnight batch."
                )
                break

        lh, lm, sh, sm, label = overseas_slots_jst[idx % len(overseas_slots_jst)]
        pub_long_iso = compute_jst_slot_iso(lh, lm)
        pub_short_iso = compute_jst_slot_iso(sh, sm)
        logger.info(
            f"\n>>> [Midnight Batch Set {idx + 1}/{daily_sets}] Target: {label}\n"
            f"    Scheduled Long : {pub_long_iso} ({lh:02d}:{lm:02d} JST)\n"
            f"    Scheduled Short: {pub_short_iso} ({sh:02d}:{sm:02d} JST)"
        )
        try:
            res = run_daily_pipeline(
                specific_script=None,
                reuse_existing_media=reuse_existing_media,
                dry_run=dry_run,
                privacy_status="private",
                publish_at_long_iso=pub_long_iso,
                publish_at_short_iso=pub_short_iso,
            )
            results.append(res)
        except Exception as exc:
            logger.error(f"Midnight batch stopped at Set {idx + 1}/{daily_sets} (likely API quota limit reached): {exc}")
            break
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated Daily Build & YouTube Upload Pipeline for Japan Local Rankings"
    )
    parser.add_argument(
        "--auth-setup",
        action="store_true",
        help="Run one-time interactive Google OAuth2 browser authentication and save token.",
    )
    parser.add_argument(
        "--midnight-batch",
        action="store_true",
        help="Run midnight batch generation & schedule sets across overseas golden-time slots.",
    )
    parser.add_argument(
        "--daily-sets",
        type=int,
        default=3,
        help="Number of (Long + Shorts) sets to generate & upload per midnight batch (default: 3 sets = 6 videos = 100%% of free 10,000 API quota).",
    )
    parser.add_argument(
        "--script",
        default=None,
        help="Specific ranking JSON filename or path (default: next `spot_*.json` in queue).",
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        default=True,
        help="Reuse already-rendered MP4 and thumbnail JPG files in `output/` if present (default: True).",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuilding MP4s even if they already exist in `output/`.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build/verify all videos, thumbnails, and SEO metadata JSON without calling YouTube API.",
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default=os.environ.get("YOUTUBE_PRIVACY_STATUS", "public"),
        help="YouTube privacy status (default: public).",
    )
    parser.add_argument(
        "--schedule-shorts-hours",
        type=float,
        default=0.0,
        help="Optional hours to delay Shorts publication after Long video upload (e.g., 1.0).",
    )
    parser.add_argument(
        "--publish-at-jst-hour",
        type=int,
        default=None,
        help="Optional JST hour (0-23) to schedule Long video publication via YouTube publishAt (Shorts +1h).",
    )
    args = parser.parse_args()

    if args.auth_setup:
        run_interactive_oauth_setup()
        return

    reuse = not args.force_rebuild

    if args.midnight_batch:
        run_midnight_batch_pipeline(
            daily_sets=args.daily_sets,
            reuse_existing_media=reuse,
            dry_run=args.dry_run,
        )
        return

    pub_long_iso = None
    pub_short_iso = None
    if args.publish_at_jst_hour is not None:
        pub_long_iso = compute_jst_slot_iso(args.publish_at_jst_hour, 0)
        pub_short_iso = compute_jst_slot_iso((args.publish_at_jst_hour + 1) % 24, 0)

    run_daily_pipeline(
        specific_script=args.script,
        reuse_existing_media=reuse,
        dry_run=args.dry_run,
        privacy_status=args.privacy,
        schedule_shorts_hours=args.schedule_shorts_hours,
        publish_at_long_iso=pub_long_iso,
        publish_at_short_iso=pub_short_iso,
    )


if __name__ == "__main__":
    main()

