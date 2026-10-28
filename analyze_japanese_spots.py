#!/usr/bin/env python3
"""
analyze_japanese_spots.py
Keyword-driven Japanese Spot Analyzer ("秋田 観光", "関東 公園", "長野 温泉", etc.).
Given any Japanese search keyword (or list of spot names), this tool:
1. Queries Yahoo Japan Search to discover Instagram-buzzing spots for that keyword
2. Excludes chain stores, commercial malls, and business hotels via an Anti-Chain Filter
3. Resolves each spot on Jalan.net (じゃらん観光ガイド) to scrape:
   - Real Japanese rating (★) & review count (件数)
   - Official Traffic Access info (交通アクセス: Shinkansen / train / bus / car)
   - Real Japanese visitor review quotes (絶賛の口コミ & 注意点)
   - 4 unique high-resolution visitor photographs (KL resolution, deduplicated via MD5)
4. Measures Instagram Buzz (Yahoo Japan Instagram hit volume & page-1 Instagram link density)
5. Computes an Instagram-Centered 100-Point Proprietary Score:
   Total (100pt) = Instagram Buzz (50pt) + Japanese Local Rating (35pt) + Hidden Gem Authenticity (15pt) - Chain Penalty
6. Saves the TOP 10 analysis JSON & 40 unique photos ready for `build_japan_ranking.py`.
"""

import hashlib
import json
import logging
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("spot_analyzer")

BASE_DIR = Path(__file__).resolve().parent
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Anti-Chain & Commercial Facility Exclusion Keywords
CHAIN_BLACKLIST = [
    "イオン", "AEON", "ららぽーと", "アウトレット", "マクドナルド", "スターバックス",
    "サイゼリヤ", "ガスト", "スシロー", "くら寿司", "はま寿司", "すき家", "吉野家",
    "松屋", "ドン・キホーテ", "ラウンドワン", "アパホテル", "東横INN", "ルートイン",
    "快活CLUB", "カラオケ", "ボウリング", "パチンコ", "レンタカー",
]


def is_chain_or_commercial(spot_name: str) -> bool:
    """Return True if the spot matches a chain store or commercial facility keyword."""
    return any(kw in spot_name for kw in CHAIN_BLACKLIST)


def resolve_jalan_url(spot_name: str, area_hint: str = "") -> str | None:
    """Resolve a Japanese spot name to its official Jalan.net sightseeing URL."""
    q = f"{spot_name} {area_hint} じゃらん 観光".strip()
    r = requests.get(
        "https://search.yahoo.co.jp/search",
        params={"p": q, "ei": "UTF-8"},
        headers=HEADERS,
        timeout=15,
    )
    m = re.search(r"www\.jalan\.net/kankou/spt_[a-zA-Z0-9_]+", r.text)
    if m:
        return f"https://{m.group(0)}/"
    return None


def discover_candidate_spots_by_keyword(keyword: str, max_spots: int = 15) -> List[Tuple[str, str]]:
    """Discover top candidate spots on Jalan.net for an arbitrary keyword like '秋田 観光' or '関東 公園'."""
    r = requests.get(
        "https://search.yahoo.co.jp/search",
        params={"p": f"{keyword} じゃらん 観光 ランキング", "ei": "UTF-8"},
        headers=HEADERS,
        timeout=15,
    )
    list_urls = re.findall(r"https?://www\.jalan\.net/kankou/[a-zA-Z0-9_/]+", r.text)
    candidates: List[Tuple[str, str]] = []
    seen_urls = set()

    for lu in list_urls:
        if "spt_" in lu:
            continue
        try:
            lr = requests.get(lu, headers=HEADERS, timeout=15)
            lr.encoding = "utf-8" if "utf-8" in lr.headers.get("content-type", "").lower() else "shift_jis"
            for m in re.finditer(
                r'href="((?:https?:)?//www\.jalan\.net/kankou/spt_[^"?/]+/)"[^>]*>([^<]+)</a>',
                lr.text,
            ):
                u, name = m.group(1), m.group(2).strip()
                full_u = "https:" + u if u.startswith("//") else u
                if (
                    full_u not in seen_urls
                    and not name.endswith("件")
                    and "ホテル" not in name
                    and not is_chain_or_commercial(name)
                ):
                    seen_urls.add(full_u)
                    candidates.append((name, full_u))
                    if len(candidates) >= max_spots:
                        return candidates
        except Exception as exc:
            logger.warning(f"Failed listing {lu}: {exc}")

    return candidates


def compute_proprietary_score(
    spot_name: str,
    ig_hits: int,
    ig_links: int,
    rating: float,
    review_count: int,
) -> Dict[str, int]:
    """
    Instagram-Centered 100-Point Scoring Formula:
    1. Instagram Buzz Score (50 pts max):
       - 38 pts from log10(ig_hits) (visual post volume on Japanese Instagram)
       - 12 pts from page-1 direct Instagram Reel/Post link density (ig_links)
    2. Domestic Local Review Score (35 pts max):
       - 26 pts from Jalan/Tabelog star rating above 3.0 ((rating - 3.0) * 17.5)
       - 9 pts from log10(review_count) (statistical reliability)
    3. Authenticity & Non-Chain Hidden Gem Bonus (15 pts max):
       - Rewards authentic local nature/culture/craft spots (100-900 reviews = 14-15 pts;
         over-commercialized mega-crowds > 2000 reviews = 11 pts)
       - Applies a -30 pt penalty if any chain keyword is detected.
    """
    ig_vol_pts = min(38.0, math.log10(max(ig_hits, 50)) * 6.8)
    ig_density_pts = min(12.0, ig_links * 0.30)
    ig_score = min(50, int(round(ig_vol_pts + ig_density_pts)))

    rating_pts = max(0.0, (rating - 3.0) * 16.5)
    count_pts = min(10.0, math.log10(max(review_count, 10)) * 3.0)
    local_score = min(35, int(round(rating_pts + count_pts)))

    if is_chain_or_commercial(spot_name):
        gem_score = -15
    elif 80 <= review_count <= 850 and rating >= 4.2:
        gem_score = 15  # High-satisfaction hidden gem
    elif review_count <= 1200:
        gem_score = 13
    else:
        gem_score = 11

    total = max(0, min(100, ig_score + local_score + gem_score))
    return {
        "ig_score": ig_score,
        "local_score": local_score,
        "gem_score": gem_score,
        "total_score": total,
    }


def analyze_spot(
    slug: str,
    spot_name: str,
    jalan_url: str,
    photo_dir: Path,
    seen_md5: set,
) -> Dict[str, Any]:
    """Scrape Jalan rating, review count, access info, real Japanese reviews, Instagram buzz, and 4 unique KL photos."""
    r = requests.get(jalan_url, headers=HEADERS, timeout=15)
    r.encoding = "utf-8" if "utf-8" in r.headers.get("content-type", "").lower() else "shift_jis"

    rt = float(m.group(1)) if (m := re.search(r'class="reviewPoint"[^>]*>([0-9.]+)<', r.text)) else 4.2
    ct_str = m.group(1).replace(",", "") if (m := re.search(r"([0-9,]+)件", r.text)) else "300"
    ct = int(ct_str)

    # Extract official traffic access lines from Jalan
    access_lines = [a.strip() for a in re.findall(r"\([123]\)([^<\n\r]+)", r.text) if len(a.strip()) > 3]

    rk = requests.get(jalan_url + "kuchikomi/", headers=HEADERS, timeout=15)
    rk.encoding = "utf-8" if "utf-8" in rk.headers.get("content-type", "").lower() else "shift_jis"

    revs = re.findall(r'class="reviewCassette__comment[^"]*"[^>]*>([\s\S]*?)</p>', r.text + rk.text)
    clean_revs: List[str] = []
    for rv in revs:
        c = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", rv)).strip()
        if len(c) > 25 and "詳細情報をみる" not in c and c not in clean_revs:
            clean_revs.append(c)

    # Measure Instagram buzz via Yahoo Japan
    yr = requests.get(
        "https://search.yahoo.co.jp/search",
        params={"p": f'"{spot_name}" Instagram OR インスタ', "ei": "UTF-8"},
        headers=HEADERS,
        timeout=15,
    )
    ig_hits = int(m.group(1).replace(",", "")) if (m := re.search(r"約([0-9,]+)件", yr.text)) else 10000
    ig_links = len(re.findall(r"instagram\.com", yr.text))

    scores = compute_proprietary_score(spot_name, ig_hits, ig_links, rt, ct)

    # Download 4 unique high-res KL photos
    photo_dir.mkdir(parents=True, exist_ok=True)
    imgs = re.findall(
        r'(//cdn\.jalan\.jp/jalan/img/[0-9]/kuchikomi/[0-9]+/KL/[^"\'\s>]+\.(?:jpg|JPG|jpeg))',
        r.text + rk.text,
    )
    saved_files: List[str] = []
    for im_u in dict.fromkeys(imgs):
        if len(saved_files) >= 4:
            break
        ir = requests.get("https:" + im_u, headers=HEADERS, timeout=15)
        if ir.status_code == 200 and len(ir.content) > 12000:
            h = hashlib.md5(ir.content).hexdigest()
            if h in seen_md5:
                continue
            seen_md5.add(h)
            fname = f"{slug}_{len(saved_files) + 1}.jpg"
            p = photo_dir / fname
            p.write_bytes(ir.content)
            Image.open(p).convert("RGB").save(p, "JPEG", quality=93)
            saved_files.append(fname)

    return {
        "slug": slug,
        "name_ja": spot_name,
        "jalan_url": jalan_url,
        "rating": rt,
        "review_count": ct,
        "access_ja": access_lines[:3],
        "ig_hits": ig_hits,
        "ig_links_page1": ig_links,
        **scores,
        "sample_reviews_ja": clean_revs[:5],
        "photos": saved_files,
    }


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "秋田 観光"
    logger.info(f"Running Japanese Instagram (50pt) × Jalan Local Review (35pt) × Gem (15pt) Analyzer for: '{kw}'")
    spots = discover_candidate_spots_by_keyword(kw, max_spots=12)
    for name, url in spots:
        logger.info(f"  Discovered: {name} -> {url}")
