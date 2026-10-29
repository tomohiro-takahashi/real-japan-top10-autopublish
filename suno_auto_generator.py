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


def build_suno_style_and_title(meta: Dict[str, Any]) -> Tuple[str, str, bool, str]:
    """
    Build a Suno v4 (Paid Plan) optimal `tags` (style of music) string, `title`,
    `make_instrumental` flag, and structured arrangement `prompt` from a metadata entry.
    """
    genre = meta.get("genre", "90s City Pop")
    raw_title = meta.get("title", "Midnight Tokyo Drive").split("|")[0].replace("[1 Hour]", "").strip()

    if "Eurobeat" in genre:
        style = (
            "1990s Initial D Eurobeat, high energy 158 BPM, Japanese touge drift racing, "
            "explosive brass synth riff, driving octave Eurobeat bassline, crisp LinnDrum & TR-909, "
            "shredding electric guitar solo, Super Eurobeat Dave Rodgers style, studio master quality"
        )
        structure_prompt = (
            "[Intro: High-speed synthesizer arpeggio & racing engine atmosphere]\n"
            "[Build-up: Explosive Eurobeat snare roll]\n"
            "[Main Riff: Iconic 90s Super Eurobeat brass synth hook]\n"
            "[Verse 1: Driving octave bassline & rhythmic synth chords]\n"
            "[Pre-Chorus: Rising melodic tension]\n"
            "[Chorus: Maximum energy Eurobeat synth brass & melodic lead]\n"
            "[Bridge: Virtuoso melodic electric guitar solo]\n"
            "[Final Chorus: Key modulation +1 semitone, full power synth brass]\n"
            "[Outro: Clean fade-out for seamless loop]"
        )
    elif "Disco" in genre or "Boogie" in genre:
        style = (
            "1980s Japanese Boogie Disco, 118 BPM, 1986 bubble era Tokyo Roppongi nightclub funk, "
            "virtuoso thumb slap bass, Roland Juno-106 & Jupiter-8 analog synth brass, "
            "Nile Rodgers style funky rhythm guitar, Toshiki Kadomatsu & Anri groove, warm analog master"
        )
        structure_prompt = (
            "[Intro: Punchy 80s slap bass & crisp gated-reverb drums]\n"
            "[Main Groove: Jupiter-8 analog brass stabs & funky rhythm guitar]\n"
            "[Verse: Smooth Tokyo midnight boogie groove with Rhodes chords]\n"
            "[Chorus: Euphoric 80s Japanese disco horn section & synth lead]\n"
            "[Solo: Virtuoso slap bass & talkbox synth solo]\n"
            "[Chorus: Full Roppongi dancefloor climax]\n"
            "[Outro: Smooth disco groove fade for seamless loop]"
        )
    else:
        style = (
            "1990s Japanese City Pop & AOR, 108 BPM, midnight Tokyo bayshore highway Wangan drive, "
            "warm Fender Rhodes electric piano, smooth fretless & slap bass, chorus clean Stratocaster guitar, "
            "emotional alto saxophone solo, Tatsuro Yamashita & Piper aesthetic, audiophile analog warmth"
        )
        structure_prompt = (
            "[Intro: Warm Fender Rhodes electric piano & midnight highway rain ambiance]\n"
            "[Verse: Smooth slap bass & clean chorus guitar groove]\n"
            "[Pre-Chorus: Lush 90s analog synth strings]\n"
            "[Chorus: Nostalgic midnight Tokyo City Pop melody]\n"
            "[Solo: Emotional alto saxophone solo over jazzy 7th chords]\n"
            "[Bridge: Dreamy electric piano breakdown]\n"
            "[Final Chorus: Full band sunset-to-midnight bayshore groove]\n"
            "[Outro: Gentle Rhodes chord fade for seamless loop]"
        )

    return style, raw_title[:60], True, structure_prompt


class SunoUnofficialClient:
    """
    Lightweight zero-dependency client for Suno's web studio API using the user's `SUNO_COOKIE`
    (or an optional `SUNO_API_BASE_URL` proxy). Optimized for Suno Pro/Premier paid plans (`chirp-v4`).
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
        Trigger Suno Pro/Premier custom generation (`chirp-v4` with fallback to `chirp-v3-5`)
        and download BOTH resulting MP3 clips into `out_dir` so no paid credits are wasted.
        """
        if not self.is_configured():
            logger.info("SUNO_COOKIE / SUNO_API_BASE_URL not set; skipping remote Suno API call.")
            return None

        style, title, make_instrumental, structure_prompt = build_suno_style_and_title(meta)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Mode A: Self-hosted / Proxy Suno API (e.g., gcui-art/suno-api)
        if self.api_base_url:
            logger.info(f"Requesting Suno v4 generation via proxy {self.api_base_url} for '{title}'...")
            gen_url = f"{self.api_base_url}/api/custom_generate"
            payload = {
                "prompt": structure_prompt,
                "tags": style,
                "title": title,
                "make_instrumental": make_instrumental,
                "model": os.environ.get("SUNO_MODEL_VERSION", "chirp-v4"),
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
            downloaded: List[Path] = []
            if isinstance(clips, list):
                for idx, clip in enumerate(clips):
                    audio_url = clip.get("audio_url")
                    clip_id = clip.get("id", f"{meta.get('id', 'suno')}_{idx+1}")
                    if audio_url:
                        downloaded.append(self._download_file(audio_url, out_dir / f"suno_{clip_id}.mp3"))
            return downloaded[0] if downloaded else None

        # Mode B: Direct Suno Studio API with Clerk Cookie (Suno Paid Plan: chirp-v5 / chirp-v4-5 / chirp-auk / chirp-v4)
        env_mv = os.environ.get("SUNO_MODEL_VERSION", "").strip()
        model_candidates = [m for m in [env_mv, "chirp-v5", "chirp-v4-5", "chirp-auk", "chirp-v4", "chirp-v3-5"] if m]
        # Deduplicate while preserving order
        seen_mv = set()
        ordered_models = [m for m in model_candidates if not (m in seen_mv or seen_mv.add(m))]

        self._authenticate_clerk()
        gen_resp = None
        used_mv = ordered_models[0]
        for candidate_mv in ordered_models:
            logger.info(f"Authenticating with Suno Clerk & generating '{title}' [model={candidate_mv}]...")
            gen_payload = {
                "gpt_description_prompt": "",
                "mv": candidate_mv,
                "prompt": structure_prompt,
                "make_instrumental": make_instrumental,
                "tags": style,
                "title": title,
            }
            try:
                gen_resp = self._studio_request("/api/generate/v2/", payload=gen_payload)
                if gen_resp and gen_resp.get("clips"):
                    used_mv = candidate_mv
                    logger.info(f"Suno accepted model '{used_mv}'!")
                    break
            except Exception as exc:
                logger.warning(f"Suno model '{candidate_mv}' not available ({exc}); trying next model...")

        if not gen_resp or not gen_resp.get("clips"):
            raise RuntimeError(f"Suno generate/v2 returned no clips across models {ordered_models}: {gen_resp}")

        clips = gen_resp.get("clips", [])
        clip_ids = [c["id"] for c in clips if "id" in c]
        logger.info(f"Suno Paid Plan ({used_mv}) generation started! Clip IDs: {clip_ids}. Polling until audio is complete...")

        downloaded_paths: Dict[str, Path] = {}
        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            time.sleep(8.0)
            self._refresh_jwt()
            ids_param = ",".join(clip_ids)
            feed = self._studio_request(f"/api/feed/?ids={urllib.parse.quote(ids_param)}")
            if isinstance(feed, list):
                for item in feed:
                    cid = item.get("id", "track")
                    status = item.get("status", "")
                    audio_url = item.get("audio_url", "")
                    if status == "error":
                        raise RuntimeError(f"Suno clip generation errored: {item}")
                    # Wait for status == "complete" so we get the full-length high-bitrate MP3 file
                    if status == "complete" and audio_url and cid not in downloaded_paths:
                        dest = out_dir / f"suno_{meta.get('id', 'track')}_{cid[:8]}.mp3"
                        downloaded_paths[cid] = self._download_file(audio_url, dest)
                if len(downloaded_paths) >= len(clip_ids):
                    break

        if downloaded_paths:
            tracks = list(downloaded_paths.values())
            if len(tracks) >= 2:
                # 1 Suno generation call ALWAYS creates 2 variations for a single 10-credit charge.
                # Combine Variation A + Variation B into ONE 7-8 min master MP3 for THIS video,
                # so tomorrow's video generates a fresh song matching tomorrow's theme!
                master_mp3 = out_dir / f"suno_{meta.get('id', 'track')}_dual_master.mp3"
                try:
                    import subprocess
                    subprocess.run(
                        [
                            "ffmpeg", "-y",
                            "-i", str(tracks[0]),
                            "-i", str(tracks[1]),
                            "-filter_complex", "[0:a][1:a]acrossfade=d=3.0:c1=tri:c2=tri[aout]",
                            "-map", "[aout]",
                            "-c:a", "libmp3lame", "-b:a", "192k",
                            str(master_mp3),
                        ],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    for t_p in tracks:
                        t_p.unlink(missing_ok=True)
                    logger.info(f"Merged both Suno variations from 1 generation into master track: {master_mp3}")
                    return master_mp3
                except Exception as exc:
                    logger.warning(f"Could not merge dual Suno tracks ({exc}); keeping primary track.")
                    for t_p in tracks[1:]:
                        t_p.unlink(missing_ok=True)
            return tracks[0]

        raise TimeoutError(f"Timed out waiting for Suno clips {clip_ids} after {timeout_sec}s.")

    @staticmethod
    def _download_file(url: str, dest: Path) -> Path:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        logger.info(f"Downloaded Suno MP3 ({len(data) / (1024*1024):.2f} MB) -> {dest}")
        return dest
