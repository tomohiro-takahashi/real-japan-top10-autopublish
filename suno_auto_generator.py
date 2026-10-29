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
CLERK_BASE = "https://auth.suno.com/v1/client"
SUNO_STUDIO_API = "https://studio-api.prod.suno.com"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def build_suno_style_and_title(meta: Dict[str, Any]) -> Tuple[str, str, bool, str]:
    """
    Build a Suno Pro (v6 `chirp-hawk`) optimal `tags` (style of music) string, `title`,
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


LOCAL_COOKIE_FILE = Path(__file__).resolve().parent / ".suno_cookie.txt"


def normalize_suno_cookie(raw_cookie: str) -> str:
    """Accept either a full Cookie header ('__client=eyJ...') or a raw JWT value ('eyJ...') and normalize it."""
    val = raw_cookie.strip().strip('"').strip("'")
    if not val:
        return ""
    if "=" not in val or val.startswith("eyJ"):
        return f"__client={val}"
    return val


class SunoUnofficialClient:
    """
    Lightweight zero-dependency client for Suno's web studio API using the user's `SUNO_COOKIE`
    (or `.suno_cookie.txt` / optional `SUNO_API_BASE_URL` proxy).
    Optimized for Suno Pro/Premier paid plans (v6 `chirp-hawk` -> v5 `chirp-crow` -> v4.5 `chirp-auk`).
    """

    def __init__(self, cookie: Optional[str] = None, api_base_url: Optional[str] = None) -> None:
        raw_c = cookie or os.environ.get("SUNO_COOKIE") or ""
        if not raw_c and LOCAL_COOKIE_FILE.exists():
            raw_c = LOCAL_COOKIE_FILE.read_text(encoding="utf-8").strip()
        self.cookie = normalize_suno_cookie(raw_c)
        self.api_base_url = (api_base_url or os.environ.get("SUNO_API_BASE_URL") or "").strip().rstrip("/")
        self.session_id: Optional[str] = None
        self.jwt_token: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.cookie or self.api_base_url)

    def _authenticate_clerk(self) -> str:
        """Exchange the `__client` cookie on `auth.suno.com` for a short-lived Clerk JWT token."""
        for base_url in (CLERK_BASE, "https://clerk.suno.com/v1/client"):
            try:
                url = f"{base_url}?_clerk_js_version={CLERK_VERSION}"
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
                if sessions:
                    self.session_id = sessions[0].get("id")
                    active_jwt = sessions[0].get("last_active_token", {}).get("jwt")
                    if active_jwt:
                        self.jwt_token = active_jwt
                        return active_jwt
                    return self._refresh_jwt(base_url)
            except Exception:
                continue

        raise RuntimeError(
            "Suno Clerk authentication failed: no active sessions found in SUNO_COOKIE. "
            "Run `python suno_auto_generator.py --browser-login` to refresh your session."
        )

    def _refresh_jwt(self, base_url: str = CLERK_BASE) -> str:
        if not self.session_id:
            return self._authenticate_clerk()
        token_url = f"{base_url}/sessions/{self.session_id}/tokens?_clerk_js_version={CLERK_VERSION}"
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
        Trigger Suno Pro/Premier custom generation using the highest available Pro model (`v6` / `chirp-hawk`)
        and download BOTH resulting MP3 clips into `out_dir`, merging them into a 7-8 min master MP3.
        """
        if not self.is_configured():
            logger.info("SUNO_COOKIE / SUNO_API_BASE_URL not set; skipping remote Suno API call.")
            return None

        style, title, make_instrumental, structure_prompt = build_suno_style_and_title(meta)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Mode A: Self-hosted / Proxy Suno API
        if self.api_base_url:
            logger.info(f"Requesting Suno generation via proxy {self.api_base_url} for '{title}'...")
            gen_url = f"{self.api_base_url}/api/custom_generate"
            payload = {
                "prompt": structure_prompt,
                "tags": style,
                "title": title,
                "make_instrumental": make_instrumental,
                "model": os.environ.get("SUNO_MODEL_VERSION", "chirp-hawk"),
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

        # Mode B: Direct Suno Studio API with Clerk Cookie
        # Dynamically query /api/billing/info/ to get the account's latest Pro model (e.g. v6 'chirp-hawk')!
        self._authenticate_clerk()
        dynamic_models: List[str] = []
        try:
            binfo = self._studio_request("/api/billing/info/")
            for m_obj in binfo.get("models", []):
                if m_obj.get("can_use") and m_obj.get("external_key"):
                    if m_obj.get("is_default_model"):
                        dynamic_models.insert(0, m_obj["external_key"])
                    else:
                        dynamic_models.append(m_obj["external_key"])
        except Exception:
            pass

        env_mv = os.environ.get("SUNO_MODEL_VERSION", "").strip()
        model_candidates = [
            m
            for m in [
                env_mv,
                *dynamic_models,
                "chirp-hawk",
                "chirp-crow",
                "chirp-v5",
                "chirp-bluejay",
                "chirp-auk",
                "chirp-v4",
            ]
            if m
        ]
        seen_mv = set()
        ordered_models = [m for m in model_candidates if not (m in seen_mv or seen_mv.add(m))]

        self._authenticate_clerk()
        turnstile_token = self._acquire_turnstile_token()
        gen_resp = None
        used_mv = ordered_models[0]
        for candidate_mv in ordered_models:
            logger.info(f"Authenticating with Suno Clerk & generating '{title}' [model={candidate_mv}]...")
            gen_payload: Dict[str, Any] = {
                "gpt_description_prompt": "",
                "mv": candidate_mv,
                "prompt": "" if make_instrumental else structure_prompt,
                "make_instrumental": make_instrumental,
                "tags": style,
                "title": title,
                "generation_type": "TEXT",
            }
            if turnstile_token:
                gen_payload["token"] = turnstile_token
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
            feed_items: List[Dict[str, Any]] = []
            try:
                feed_v2 = self._studio_request(f"/api/feed/v2?ids={urllib.parse.quote(ids_param)}")
                if isinstance(feed_v2, dict) and isinstance(feed_v2.get("clips"), list):
                    feed_items = feed_v2["clips"]
            except Exception:
                pass
            if not feed_items:
                feed_v1 = self._studio_request(f"/api/feed/?ids={urllib.parse.quote(ids_param)}")
                if isinstance(feed_v1, list):
                    feed_items = feed_v1

            for item in feed_items:
                cid = item.get("id", "track")
                status = item.get("status", "")
                audio_url = item.get("audio_url", "")
                media_urls = item.get("media_urls") or []
                if (not audio_url or "forbidden" in audio_url) and media_urls:
                    audio_url = media_urls[0].get("url", "")
                if status == "error":
                    raise RuntimeError(f"Suno clip generation errored: {item}")
                logger.info(f"  [Poll] Clip {cid[:8]} status={status} media_ready={bool(audio_url and 'forbidden' not in audio_url)}")
                # Wait for status == "complete" so we get the full-length Pro Plan Studio Master WAV -> 320kbps MP3
                if status == "complete" and cid not in downloaded_paths:
                    mp3_dest = out_dir / f"suno_{meta.get('id', 'track')}_{cid[:8]}.mp3"
                    downloaded_paths[cid] = self._download_pro_wav_as_mp3(cid, mp3_dest, fallback_url=audio_url)
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
                            "-c:a", "libmp3lame", "-b:a", "320k",
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

    def _download_pro_wav_as_mp3(self, clip_id: str, mp3_dest: Path, fallback_url: str = "") -> Path:
        """Export lossless Studio Master WAV via Pro Plan endpoint (/api/gen/{id}/convert_wav/ -> /wav_file/) and encode to 320kbps MP3."""
        import subprocess

        self._refresh_jwt()
        try:
            self._studio_request(f"/api/gen/{clip_id}/convert_wav/", payload={})
        except Exception:
            pass

        wav_url = ""
        for _ in range(24):
            time.sleep(2.5)
            try:
                w_info = self._studio_request(f"/api/gen/{clip_id}/wav_file/")
                if isinstance(w_info, dict) and w_info.get("wav_file_url"):
                    wav_url = w_info["wav_file_url"]
                    break
            except Exception:
                pass

        if wav_url:
            wav_tmp = mp3_dest.with_suffix(".wav")
            self._download_file(wav_url, wav_tmp)
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_tmp), "-c:a", "libmp3lame", "-b:a", "320k", str(mp3_dest)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wav_tmp.unlink(missing_ok=True)
            logger.info(f"Converted lossless Pro WAV -> 320kbps MP3: {mp3_dest}")
            return mp3_dest

        if fallback_url and "forbidden" not in fallback_url:
            return self._download_file(fallback_url, mp3_dest)
        raise RuntimeError(f"Could not obtain WAV or MP3 download URL for clip {clip_id}")

    def _acquire_turnstile_token(self, sitekey: str = "0x4AAAAAADI7xDNyj-3LcIbi", timeout_sec: int = 25) -> Optional[str]:
        """Acquire a Cloudflare Turnstile token on https://suno.com/create via Chrome CDP."""
        import shutil
        import subprocess
        import sys

        chrome_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            shutil.which("google-chrome") or "",
            shutil.which("google-chrome-stable") or "",
            shutil.which("chromium") or "",
            shutil.which("chromium-browser") or "",
        ]
        chrome_bin = next((c for c in chrome_candidates if c and os.path.exists(c)), None)
        if not chrome_bin:
            logger.warning("Google Chrome not found for Turnstile token acquisition.")
            return None

        profile_dir = Path(__file__).resolve().parent / ".suno_chrome_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        port = 9249
        cmd = [
            chrome_bin,
            "--disable-blink-features=AutomationControlled",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile_dir}",
            "--window-size=1280,800",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
        if os.name == "posix" and sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
            xvfb = shutil.which("xvfb-run")
            if xvfb:
                cmd = [xvfb, "-a"] + cmd

        cookie_list = []
        for part in self.cookie.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                if k.startswith("__client"):
                    cookie_list.append(
                        {"name": k, "value": v, "domain": "auth.suno.com", "path": "/", "secure": True, "httpOnly": k == "__client", "sameSite": "None"}
                    )
                else:
                    cookie_list.append({"name": k, "value": v, "domain": ".suno.com", "path": "/", "secure": True})

        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            tabs = []
            for _ in range(20):
                time.sleep(0.5)
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                        tabs = json.loads(r.read().decode("utf-8"))
                    if [t for t in tabs if t.get("type") == "page"]:
                        break
                except Exception:
                    pass
            page_tabs = [t for t in tabs if t.get("type") == "page"]
            if not page_tabs:
                return None
            ws_url = page_tabs[0]["webSocketDebuggerUrl"]
            _cdp_send_command(ws_url, "Network.setCookies", {"cookies": cookie_list}, 1)
            _cdp_send_command(ws_url, "Page.navigate", {"url": "https://suno.com/create"}, 2)

            for _ in range(25):
                time.sleep(1.0)
                chk = _cdp_send_command(
                    ws_url,
                    "Runtime.evaluate",
                    {"expression": 'JSON.stringify({url: location.href, hasTs: typeof window.turnstile !== "undefined"})', "returnByValue": True},
                    3,
                )
                val_str = chk.get("result", {}).get("result", {}).get("value", "{}")
                v = json.loads(val_str) if val_str else {}
                if v.get("url") == "https://suno.com/create" and v.get("hasTs"):
                    break

            setup_js = f"""(() => {{
                window.__tsToken = null;
                const div = document.createElement('div');
                div.style.cssText = 'position:fixed;top:10px;left:10px;z-index:999999;background:#fff;width:300px;height:65px;';
                document.body.appendChild(div);
                window.turnstile.render(div, {{
                    sitekey: '{sitekey}',
                    callback: (token) => {{ window.__tsToken = token; }},
                }});
                return 'rendered';
            }})()"""
            _cdp_send_command(ws_url, "Runtime.evaluate", {"expression": setup_js, "returnByValue": True}, 4)

            t0 = time.time()
            msg_id = 10
            while time.time() - t0 < timeout_sec:
                time.sleep(1.0)
                msg_id += 1
                res = _cdp_send_command(
                    ws_url,
                    "Runtime.evaluate",
                    {"expression": "window.__tsToken || ''", "returnByValue": True},
                    msg_id,
                )
                tok = res.get("result", {}).get("result", {}).get("value", "")
                if tok:
                    logger.info(f"Acquired Cloudflare Turnstile token ({len(tok)} chars) in {time.time() - t0:.1f}s.")
                    return tok
        except Exception as exc:
            logger.warning(f"Turnstile token acquisition failed ({exc}).")
        finally:
            proc.terminate()
        return None

    def get_billing_info(self) -> Dict[str, Any]:
        """Fetch Suno account billing/credits info using the active Clerk session."""
        self._authenticate_clerk()
        return self._studio_request("/api/billing/info/")

    @staticmethod
    def _download_file(url: str, dest: Path) -> Path:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        logger.info(f"Downloaded Suno audio ({len(data) / (1024*1024):.2f} MB) -> {dest}")
        return dest


def _cdp_send_command(ws_url: str, method: str, params: Optional[Dict[str, Any]] = None, msg_id: int = 1) -> Dict[str, Any]:
    """Minimal zero-dependency RFC 6455 WebSocket client to send a single CDP command and return its JSON response."""
    import base64
    import socket
    import struct

    parsed = urllib.parse.urlparse(ws_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 9249
    path = parsed.path or "/"

    with socket.create_connection((host, port), timeout=15) as sock:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(handshake.encode("ascii"))
        sock.recv(4096)

        payload = json.dumps({"id": msg_id, "method": method, "params": params or {}}).encode("utf-8")
        mask_key = os.urandom(4)
        plen = len(payload)
        if plen < 126:
            header = bytearray([0x81, 0x80 | plen]) + mask_key
        else:
            header = bytearray([0x81, 0x80 | 126]) + struct.pack(">H", plen) + mask_key
        masked = bytearray(payload[i] ^ mask_key[i % 4] for i in range(plen))
        sock.sendall(header + masked)

        buf = b""
        sock.settimeout(12.0)
        target = f'"id":{msg_id}'.encode("ascii")
        try:
            while target not in buf:
                c = sock.recv(65536)
                if not c:
                    break
                buf += c
        except Exception:
            pass

        idx = buf.find(b'{"id":')
        if idx != -1:
            return json.loads(buf[idx:].decode("utf-8", errors="ignore"))
        return {}


def _cdp_get_all_cookies(ws_url: str) -> List[Dict[str, Any]]:
    """Minimal zero-dependency RFC 6455 WebSocket client to call Storage.getCookies on local Chrome DevTools port."""
    import base64
    import socket
    import struct

    parsed = urllib.parse.urlparse(ws_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 9234
    path = parsed.path or "/"

    with socket.create_connection((host, port), timeout=5) as sock:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(handshake.encode("ascii"))
        sock.recv(4096)

        payload = json.dumps({"id": 1, "method": "Storage.getCookies"}).encode("utf-8")
        mask_key = os.urandom(4)
        header = bytearray([0x81, 0x80 | len(payload)]) + mask_key
        masked = bytearray(payload[i] ^ mask_key[i % 4] for i in range(len(payload)))
        sock.sendall(header + masked)

        buf = b""
        sock.settimeout(2.0)
        try:
            while True:
                c = sock.recv(65536)
                if not c:
                    break
                buf += c
        except Exception:
            pass

        idx = buf.find(b'{"id":1')
        if idx != -1:
            msg = json.loads(buf[idx:].decode("utf-8", errors="ignore"))
            return msg.get("result", {}).get("cookies", [])
        return []


def interactive_browser_login_suno(timeout_sec: int = 300) -> str:
    """
    1) First checks if the user's active macOS Chrome profile (`Profile 1` or `Default`) already has a logged-in
       `auth.suno.com` session and extracts it headlessly in 3 seconds.
    2) Otherwise opens a visible Chrome window at `https://suno.com/create` and waits for login.
    """
    import shutil
    import subprocess

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_bin):
        raise FileNotFoundError(f"Google Chrome not found at {chrome_bin}")

    profile_dir = Path(__file__).resolve().parent / ".suno_chrome_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Sync existing macOS Chrome cookies from Profile 1 / Default if available
    chrome_base = Path.home() / "Library/Application Support/Google/Chrome"
    if (chrome_base / "Local State").exists():
        shutil.copy2(chrome_base / "Local State", profile_dir / "Local State")
    for pname in ("Profile 1", "Default"):
        src_p = chrome_base / pname
        if (src_p / "Cookies").exists():
            dst_p = profile_dir / pname
            dst_p.mkdir(parents=True, exist_ok=True)
            for fname in ("Cookies", "Cookies-journal", "Preferences"):
                if (src_p / fname).exists():
                    shutil.copy2(src_p / fname, dst_p / fname)

    port = 9234
    proc = subprocess.Popen(
        [
            chrome_bin,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--profile-directory=Profile 1",
            "https://suno.com",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(2.5)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3) as resp:
            ver = json.loads(resp.read().decode("utf-8"))
        cookies = _cdp_get_all_cookies(ver["webSocketDebuggerUrl"])
        suno_c = {c["name"]: c["value"] for c in cookies if "suno.com" in c.get("domain", "")}
        cookie_str = "; ".join(
            f"{k}={v}" for k, v in suno_c.items() if k.startswith("__client") or k.startswith("__session") or k == "sessionid"
        )
        if cookie_str:
            test_client = SunoUnofficialClient(cookie=cookie_str)
            info = test_client.get_billing_info()
            LOCAL_COOKIE_FILE.write_text(cookie_str + "\n", encoding="utf-8")
            logger.info("============================================================")
            logger.info("✅ Suno Browser Session Extracted & Verified Automatically!")
            logger.info(f"   Saved to       : {LOCAL_COOKIE_FILE}")
            logger.info(f"   Plan           : {info.get('plan', {}).get('name', 'Pro')}")
            logger.info(f"   Credits Left   : {info.get('total_credits_left')} / {info.get('monthly_limit')}")
            logger.info("============================================================")
            return cookie_str
    except Exception as exc:
        logger.warning(f"Could not extract from existing profile ({exc}).")
    finally:
        proc.terminate()

    raise RuntimeError("Please sign into https://suno.com in Google Chrome and re-run `--browser-login`.")


def main() -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Suno Paid Plan (v5/v4.5+/v4) Automated Track Generator & Cookie Setup")
    parser.add_argument(
        "--browser-login",
        action="store_true",
        help="Open Google Chrome to suno.com and automatically capture your __client cookie upon login.",
    )
    parser.add_argument(
        "--set-cookie",
        default=None,
        help="Save your Suno __client cookie to .suno_cookie.txt (and optionally sync to GitHub Secrets).",
    )
    parser.add_argument(
        "--check-credits",
        action="store_true",
        help="Verify Suno cookie authentication and print remaining credits / active plan.",
    )
    parser.add_argument(
        "--generate-next",
        action="store_true",
        help="Generate the next unused track from stocks/music/metadata_pool.json into stocks/music/queue/.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    if args.browser_login:
        interactive_browser_login_suno()
        return 0

    if args.set_cookie:
        norm = normalize_suno_cookie(args.set_cookie)
        LOCAL_COOKIE_FILE.write_text(norm + "\n", encoding="utf-8")
        logger.info(f"Saved normalized Suno cookie to {LOCAL_COOKIE_FILE}")

    client = SunoUnofficialClient()
    if args.check_credits:
        if not client.is_configured():
            logger.error("No SUNO_COOKIE configured. Pass --browser-login or --set-cookie '<__client value>'.")
            return 1
        info = client.get_billing_info()
        logger.info(f"Suno Account Verified! Credits left: {info.get('total_credits_left')} | Monthly limit: {info.get('monthly_limit')}")
        return 0

    if args.generate_next:
        pool_path = base_dir / "stocks" / "music" / "metadata_pool.json"
        queue_dir = base_dir / "stocks" / "music" / "queue"
        raw_pool = json.loads(pool_path.read_text(encoding="utf-8"))
        items = raw_pool["items"] if isinstance(raw_pool, dict) and "items" in raw_pool else raw_pool
        unused = [x for x in items if not x.get("used", False)] or items
        out_mp3 = client.generate_and_download_mp3(unused[0], queue_dir)
        logger.info(f"Generated MP3 ready in queue: {out_mp3}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
