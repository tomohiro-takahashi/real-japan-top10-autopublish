#!/usr/bin/env python3
"""
analyze_channel_analytics.py
Fetches YouTube channel & video analytics for both:
1. Real Japan Top 10 — Local Data & History (.youtube_token_overseas_japan.json)
2. MIDNIGHT COCKPIT / あの頃の夜と音楽 (.youtube_token_music.json)
using low-quota playlistItems.list + videos.list (only 2 quota units per channel)
and checks remaining content stock counts.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from auto_publish_japan_ranking import get_youtube_client
from build_music_video import get_youtube_service

BASE_DIR = Path(__file__).resolve().parent


def fetch_channel_report(yt, label: str) -> Dict[str, Any]:
    ch_res = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()
    items = ch_res.get("items", [])
    if not items:
        return {"label": label, "error": "No channel found for token"}
    ch = items[0]
    uploads_pid = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    pl_res = yt.playlistItems().list(part="contentDetails", playlistId=uploads_pid, maxResults=50).execute()
    vid_ids = [it["contentDetails"]["videoId"] for it in pl_res.get("items", [])]

    videos_data: List[Dict[str, Any]] = []
    if vid_ids:
        v_res = yt.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=",".join(vid_ids[:50]),
        ).execute()
        for v in v_res.get("items", []):
            stats = v.get("statistics", {})
            dur = v.get("contentDetails", {}).get("duration", "")
            is_short = ("M" not in dur) or dur.startswith("PT1M") or "#Shorts" in v["snippet"].get("title", "")
            videos_data.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "publishedAt": v["snippet"]["publishedAt"],
                "privacyStatus": v["status"].get("privacyStatus"),
                "publishAt": v["status"].get("publishAt"),
                "duration": dur,
                "type": "Short" if is_short else "Long",
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "url": f"https://youtube.com/shorts/{v['id']}" if is_short else f"https://youtu.be/{v['id']}",
            })

    videos_data.sort(key=lambda x: x["views"], reverse=True)
    return {
        "label": label,
        "channel_id": ch["id"],
        "channel_title": ch["snippet"]["title"],
        "custom_url": ch["snippet"].get("customUrl", ""),
        "subscribers": int(ch["statistics"].get("subscriberCount", 0)),
        "total_views": int(ch["statistics"].get("viewCount", 0)),
        "video_count": int(ch["statistics"].get("videoCount", 0)),
        "videos": videos_data,
    }


def main() -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channels": [],
    }
    try:
        yt_jp = get_youtube_client()
        report["channels"].append(fetch_channel_report(yt_jp, "Real Japan Top 10 (Overseas)"))
    except Exception as exc:
        report["channels"].append({"label": "Real Japan Top 10 (Overseas)", "error": str(exc)})

    try:
        yt_m = get_youtube_service()
        report["channels"].append(fetch_channel_report(yt_m, "MIDNIGHT COCKPIT (Music)"))
    except Exception as exc:
        report["channels"].append({"label": "MIDNIGHT COCKPIT (Music)", "error": str(exc)})

    out_path = BASE_DIR / "output" / "latest_analytics_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
