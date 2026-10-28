#!/usr/bin/env python3
"""
suno_auto_generator.py
======================
Suno Unofficial API / Session Cookie Automated MP3 Track Generator.
Supports:
1. Direct Clerk Session Token Exchange using `SUNO_COOKIE` (`__client` cookie from suno.com)
   against `https://clerk.suno.com/v1/client/sessions/{sid}/tokens` + `https://studio-api.prod.suno.com/api/generate/v2/`.
2. Optional local/self-hosted `SUNO_API_BASE_URL` (e.g. gcui-art/suno-api) if configured.
3. Automatic genre-tailored style & prompt builder for:
   - `90s Eurobeat` (High-BPM Initial D / Wangan Midnight synthesizer brass, eurobeat bassline)
   - `80s Japanese Boogie Disco` (1986 Roppongi slap bass, brass section, analog synth funk)
   - `90s City Pop` (Midnight Tokyo bayshore electric piano, jazzy guitar solo, smooth groove)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("suno_client")

CLERK_VERSION = "5.15.0"
CLERK_BASE = "https://clerk.suno.com/v1/client"
SUNO_STUDIO_API = "https://studio-api.prod.suno.com"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def build_suno_style_and_title(meta: Dict[str, Any]) -> Tuple[str, str, bool]:
    """
    Build a Suno v3.5 / v4 optimal `tags` (style of music) string, `title`, and `make_instrumental` flag
    from a metadata entry in `stocks/music/metadata_pool.json`.
    """
    genre = meta.get("genre", "90s City Pop")
    raw_title = meta.get("title", "Midnight Tokyo Drive").split("|")[0].replace("[1 Hour]", "").strip()

    if "Eurobeat" in genre:
        style = (
            "90s Eurobeat, high energy 158 BPM, Initial D style touge drift, "
            "synthesizer brass lead, driving octave synth bass, crisp eurobeat drums, "
            "melodic guitar solo, nostalgic 1990s Japanese arcade racing soundtrack, instrumental"
        )
    elif "Disco" in genre or "Boogie" in genre:
        style = (
            "1980s Japanese Boogie Disco, 118 BPM, bubble era Tokyo Roppongi nightclub funk, "
            "virtuoso slap bass, Roland Juno-106 analog synth brass, funky rhythm guitar, "
            "four-on-the-floor disco groove, Toshiki Kadomatsu aesthetic, instrumental"
        )
    else:
        style = (
            "90s Japanese City Pop, 108 BPM, midnight Tokyo bayshore highway drive, "
            "warm Fender Rhodes electric piano, smooth slap bass, chorus clean guitar, "
            "nostalgic saxophone & synth lead, Tatsuro Yamashita & AOR groove, instrumental"
        )

    return style, raw_title[:60], True


class SunoUnofficialClient:
    """
    Lightweight zero-dependency client for Suno's web studio API using the user's `SUNO_COOKIE`
    (or an optional `SUNO_API_BASE_URL` proxy).
    """

    def __init__(self, cookie: Optional[str] = None, api_base_url: Optional[str] = None) -> None:
        self.cookie = (cookie or os.environ.get("SUNO_COOKIE") or "").strip()
        self.api_base_url = (api_base_url or os.environ.get("SUNO_API_BASE_URL") or "").strip().rstrip("/")
        self.session_id: Optional[str] = None
        self.jwt_token: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.cookie or self.api_base_url)

    def _authenticate_clerk(self) -> str:
        """Exchange the `__client` cookie for a short-lived Clerk JWT token used by `studio-api.prod.suno.com`."""
        url = f"{CLERK_BASE}?_clerk_js_version={CLERK_VERSION}"
        req = urllib.request.Request(
            url,
            headers={
                "Cookie": self.cookie,
                "User-Agent": USER_AGENT,
                "Origin": "https://suno.com",
                "Referer": "https://suno.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        sessions = data.get("response", {}).get("sessions", [])
        if not sessions:
            raise RuntimeError(
                "Suno Clerk authentication failed: no active sessions found in SUNO_COOKIE. "
                "Please refresh your __client cookie from suno.com."
            )
        self.session_id = sessions[0].get("id")
        if not self.session_id:
            raise RuntimeError("Suno Clerk authentication failed: session ID missing.")

        return self._refresh_jwt()

    def _refresh_jwt(self) -> str:
        if not self.session_id:
            return self._authenticate_clerk()
        token_url = f"{CLERK_BASE}/sessions/{self.session_id}/tokens?_clerk_js_version={CLERK_VERSION}"
        req = urllib.request.Request(
            token_url,
            data=b"",
            method="POST",
            headers={
                "Cookie": self.cookie,
                "User-Agent": USER_AGENT,
                "Origin": "https://suno.com",
                "Referer": "https://suno.com/",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        jwt = data.get("jwt")
        if not jwt:
            raise RuntimeError("Suno Clerk token exchange returned empty jwt.")
        self.jwt_token = jwt
        return jwt

    def _studio_request(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        if not self.jwt_token:
            self._authenticate_clerk()

        url = f"{SUNO_STUDIO_API}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url,
            data=body,
            method="POST" if payload is not None else "GET",
            headers={
                "Authorization": f"Bearer {self.jwt_token}",
                "User-Agent": USER_AGENT,
                "Origin": "https://suno.com",
                "Referer": "https://suno.com/",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def generate_and_download_mp3(
        self,
        meta: Dict[str, Any],
        out_dir: Path,
        timeout_sec: int = 240,
    ) -> Optional[Path]:
        """
        Trigger Suno custom instrumental generation for `meta` and download the resulting MP3 into `out_dir`.
        """
        if not self.is_configured():
            logger.info("SUNO_COOKIE / SUNO_API_BASE_URL not set; skipping remote Suno API call.")
            return None

        style, title, make_instrumental = build_suno_style_and_title(meta)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Mode A: Self-hosted / Proxy Suno API (e.g., gcui-art/suno-api)
        if self.api_base_url:
            logger.info(f"Requesting Suno generation via proxy {self.api_base_url} for '{title}'...")
            gen_url = f"{self.api_base_url}/api/custom_generate"
            payload = {
                "prompt": "",
                "tags": style,
                "title": title,
                "make_instrumental": make_instrumental,
                "wait_audio": True,
            }
            req = urllib.request.Request(
                gen_url,
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                clips = json.loads(resp.read().decode("utf-8"))
            if isinstance(clips, list) and clips:
                audio_url = clips[0].get("audio_url")
                clip_id = clips[0].get("id", meta.get("id", "suno"))
                if audio_url:
                    return self._download_file(audio_url, out_dir / f"suno_{clip_id}.mp3")
            return None

        # Mode B: Direct Suno Studio API with Clerk Cookie
        logger.info(f"Authenticating with Suno Clerk & generating '{title}' ({style[:55]}...)...")
        self._authenticate_clerk()
        gen_payload = {
            "gpt_description_prompt": "",
            "mv": os.environ.get("SUNO_MODEL_VERSION", "chirp-v3-5"),
            "prompt": "",
            "make_instrumental": make_instrumental,
            "tags": style,
            "title": title,
        }
        gen_resp = self._studio_request("/api/generate/v2/", payload=gen_payload)
        clips = gen_resp.get("clips", [])
        if not clips:
            raise RuntimeError(f"Suno generate/v2 returned no clips: {gen_resp}")

        clip_ids = [c["id"] for c in clips if "id" in c]
        logger.info(f"Suno generation started! Clip IDs: {clip_ids}. Polling until audio is complete...")

        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            time.sleep(8.0)
            self._refresh_jwt()
            ids_param = ",".join(clip_ids)
            feed = self._studio_request(f"/api/feed/?ids={urllib.parse.quote(ids_param)}")
            if isinstance(feed, list):
                for item in feed:
                    status = item.get("status", "")
                    audio_url = item.get("audio_url", "")
                    if status in ("complete", "streaming") and audio_url and ".mp3" in audio_url:
                        cid = item.get("id", "track")
                        dest = out_dir / f"suno_{meta.get('id', 'track')}_{cid[:8]}.mp3"
                        return self._download_file(audio_url, dest)
                    if status == "error":
                        raise RuntimeError(f"Suno clip generation errored: {item}")

        raise TimeoutError(f"Timed out waiting for Suno clips {clip_ids} after {timeout_sec}s.")

    @staticmethod
    def _download_file(url: str, dest: Path) -> Path:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        logger.info(f"Downloaded Suno MP3 ({len(data) / (1024*1024):.2f} MB) -> {dest}")
        return dest
