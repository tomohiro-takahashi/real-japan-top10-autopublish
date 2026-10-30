#!/usr/bin/env python3
"""
real_hits_mix_builder.py
========================
Builds and uploads 2-Hour+ Full-Length "Real 80s/90s Western Legend 24-Track Masterpiece Mixes" (起爆剤モード)
for `MIDNIGHT COCKPIT / あの頃の夜と音楽`.
- Runs 1x daily (22:00 JST) alongside the 1x daily (20:00 JST) Suno original upload.
- Each mix is a deeply curated ~2-Hour (24 full-length iconic songs, ~105-125 minutes) definitive compilation:
  1. `real_mix_001`: 【名画メドレー】80s-90s 映画主題歌＆サウンドトラック永久保存版（全24曲・約2時間）
  2. `real_mix_002`: 【夜に聴きたい洋楽】一日の終わりに心がほどける80s-90s AOR＆極上メロウバラード（全24曲・約2時間）
  3. `real_mix_003`: 【ピアノが落ち着く洋楽】静かな夜に聴きたい70s-90s ピアノ名曲バラード決定版（全24曲・約2時間）
  4. `real_mix_004`: 【サックスが沁みる夜】ウイスキー片手に聴きたい80s-90s サックス＆アーバンナイト名曲選（全24曲・約2時間）
  5. `real_mix_005`: 【アコギが心地よい洋楽】休日の午後や夕暮れに聴きたいアコースティック＆ソフトロック決定版（全24曲・約2時間）
  6. `real_mix_006`: 【雨の夜に聴きたい洋楽】窓を打つ雨音と聴く80s-90s 泣けるラブバラード名曲集（全24曲・約2時間）
  7. `real_mix_007`: 【バブル世代必見】1986年六本木・マハラジャ洋楽ディスコ＆ハイエナジー大全集（全24曲・約2時間）
  8. `real_mix_008`: 【夜のハイウェイ洋楽】深夜の高速道路で聴きたい80s-90s アメリカンロック＆ドライブ大全集（全24曲・約2時間）
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from build_music_video import (
    MUSIC_DIR,
    OUTPUT_1HOUR,
    OUTPUT_SHORT,
    OUTPUT_SHORT_MEDLEY,
    OUTPUT_THUMB,
    _draw_soft_shadow_text,
    build_1hour_video,
    build_highway_driving_loop_mp4,
    build_short_medley_video,
    build_short_video,
    compute_music_golden_time_iso,
    download_background_image,
    find_bold_font,
    find_cjk_font,
    find_cjk_mincho_font,
    fit_font_for_width,
    get_audio_duration,
    get_youtube_service,
    load_font,
    render_16x9_hud_and_thumb,
    upload_video_to_youtube,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("real_hits_mix")

REAL_HITS_POOL_PATH = MUSIC_DIR / "real_hits_pool.json"


DEFAULT_REAL_HIT_MIXES: List[Dict[str, Any]] = [
    # 01: 80s-90s 名画主題歌＆サウンドトラック永久保存版（2時間・全24曲）
    {
        "id": "real_mix_001",
        "used": False,
        "genre": "80s City Pop & Sax AOR",
        "artwork_file": "citypop80s.jpg",
        "title": "【名画メドレー】イントロで名シーンが蘇る！80年代・90年代「映画主題歌＆サントラ」洋楽名曲集【2時間・全24曲フル】トップガン / BTTF / スタンド・バイ・ミー / アルマゲドン",
        "short_title": "【名画メドレー】イントロで映画の名シーンが蘇る！80s-90s映画主題歌24選 🎧本編2時間はチャンネルへ！ #Shorts #映画音楽",
        "thumb_era_label": "40代・50代 永久保存版  ｜  80s-90s MOVIE SOUNDTRACKS — 2 HOURS / 24 SONGS",
        "thumb_catch": "イントロが流れた瞬間、あの頃の銀幕と青春の記憶がよみがえる——",
        "thumb_main": "80s-90s 名画主題歌メドレー【2時間】",
        "thumb_sub": "トップガン / BTTF / スタンド・バイ・ミー / フラッシュダンス / ボディガード / アルマゲドン 他 全24曲",
        "tracks": [
            {"artist": "Kenny Loggins", "title": "Danger Zone", "ja_title": "映画『トップガン』", "query": "Kenny Loggins Danger Zone official audio"},
            {"artist": "Berlin", "title": "Take My Breath Away", "ja_title": "映画『トップガン』愛のテーマ", "query": "Berlin Take My Breath Away official audio"},
            {"artist": "Huey Lewis & The News", "title": "The Power of Love", "ja_title": "映画『バック・トゥ・ザ・フューチャー』", "query": "Huey Lewis and the News The Power of Love official audio"},
            {"artist": "Ben E. King", "title": "Stand by Me", "ja_title": "映画『スタンド・バイ・ミー』", "query": "Ben E King Stand by Me official audio"},
            {"artist": "Irene Cara", "title": "Flashdance... What a Feeling", "ja_title": "映画『フラッシュダンス』", "query": "Irene Cara Flashdance What a Feeling official audio"},
            {"artist": "Michael Sembello", "title": "Maniac", "ja_title": "映画『フラッシュダンス』", "query": "Michael Sembello Maniac official audio"},
            {"artist": "Kenny Loggins", "title": "Footloose", "ja_title": "映画『フットルース』", "query": "Kenny Loggins Footloose official audio"},
            {"artist": "Survivor", "title": "Eye of the Tiger", "ja_title": "映画『ロッキー3』", "query": "Survivor Eye of the Tiger official audio"},
            {"artist": "Ray Parker Jr.", "title": "Ghostbusters", "ja_title": "映画『ゴーストバスターズ』", "query": "Ray Parker Jr Ghostbusters official audio"},
            {"artist": "Limahl", "title": "The NeverEnding Story", "ja_title": "映画『ネバーエンディング・ストーリー』", "query": "Limahl The NeverEnding Story official audio"},
            {"artist": "Joe Cocker & Jennifer Warnes", "title": "Up Where We Belong", "ja_title": "映画『愛と青春の旅だち』", "query": "Joe Cocker Jennifer Warnes Up Where We Belong official audio"},
            {"artist": "Lionel Richie", "title": "Say You, Say Me", "ja_title": "映画『ホワイトナイツ／白夜』", "query": "Lionel Richie Say You Say Me official audio"},
            {"artist": "Christopher Cross", "title": "Arthur's Theme (Best That You Can Do)", "ja_title": "映画『ミスター・アーサー』", "query": "Christopher Cross Arthur's Theme Best That You Can Do official audio"},
            {"artist": "Starship", "title": "Nothing's Gonna Stop Us Now", "ja_title": "映画『マネキン』", "query": "Starship Nothing's Gonna Stop Us Now official audio"},
            {"artist": "The Beach Boys", "title": "Kokomo", "ja_title": "映画『カクテル』", "query": "Beach Boys Kokomo official audio"},
            {"artist": "Roy Orbison", "title": "Oh, Pretty Woman", "ja_title": "映画『プリティ・ウーマン』", "query": "Roy Orbison Oh Pretty Woman official audio"},
            {"artist": "Roxette", "title": "It Must Have Been Love", "ja_title": "映画『プリティ・ウーマン』", "query": "Roxette It Must Have Been Love official audio"},
            {"artist": "The Righteous Brothers", "title": "Unchained Melody", "ja_title": "映画『ゴースト／ニューヨークの幻』", "query": "Righteous Brothers Unchained Melody official audio"},
            {"artist": "Whitney Houston", "title": "I Will Always Love You", "ja_title": "映画『ボディガード』", "query": "Whitney Houston I Will Always Love You official audio"},
            {"artist": "Bryan Adams", "title": "(Everything I Do) I Do It for You", "ja_title": "映画『ロビン・フッド』", "query": "Bryan Adams Everything I Do I Do It for You official audio"},
            {"artist": "Celine Dion", "title": "My Heart Will Go On", "ja_title": "映画『タイタニック』", "query": "Celine Dion My Heart Will Go On official audio"},
            {"artist": "Aerosmith", "title": "I Don't Want to Miss a Thing", "ja_title": "映画『アルマゲドン』", "query": "Aerosmith I Don't Want to Miss a Thing official audio"},
            {"artist": "Sting", "title": "Shape of My Heart", "ja_title": "映画『レオン』", "query": "Sting Shape of My Heart official audio"},
            {"artist": "Simon & Garfunkel", "title": "The Sound of Silence", "ja_title": "映画『卒業』", "query": "Simon and Garfunkel The Sound of Silence official audio"},
        ],
        "tags": ["映画音楽", "名画メドレー", "80年代洋楽", "90年代洋楽", "トップガン", "バックトゥザフューチャー", "スタンドバイミー", "アルマゲドン", "40代", "50代", "洋楽メドレー", "作業用BGM", "ドライブBGM", "2時間"],
    },
    # 02: 夜に聴く・極上の80s-90s AOR＆メロウバラード（2時間・全24曲）
    {
        "id": "real_mix_002",
        "used": False,
        "genre": "80s City Pop & Sax AOR",
        "artwork_file": "citypop80s.jpg",
        "title": "【夜に聴きたい洋楽】一日の終わりに心がほどける80年代・90年代AOR＆極上バラード【2時間・全24曲フル】Bobby Caldwell / Boz Scaggs / Sade / Toto",
        "short_title": "【夜に聴きたい洋楽】疲れた夜に心がほどける80s-90s AOR＆バラード24選 🎧本編2時間はチャンネルへ！ #Shorts #80s洋楽",
        "thumb_era_label": "40代・50代 永久保存版  ｜  NIGHT RELAX AOR — 2 HOURS / 24 SONGS",
        "thumb_catch": "一日の終わりに、あの頃の優しい洋楽が心を解きほぐす——",
        "thumb_main": "夜に聴きたい大人の洋楽AOR【2時間】",
        "thumb_sub": "Bobby Caldwell / Boz Scaggs / Sade / Toto / Chicago / Billy Joel 他 全24曲",
        "tracks": [
            {"artist": "Bobby Caldwell", "title": "What You Won't Do for Love", "ja_title": "風のシルエット", "query": "Bobby Caldwell What You Won't Do for Love official audio"},
            {"artist": "Boz Scaggs", "title": "We're All Alone", "ja_title": "ウィ・アー・オール・アローン", "query": "Boz Scaggs We're All Alone official audio"},
            {"artist": "Chicago", "title": "Hard to Say I'm Sorry", "ja_title": "素直になれなくて", "query": "Chicago Hard to Say I'm Sorry official audio"},
            {"artist": "Toto", "title": "Africa", "ja_title": "アフリカ", "query": "Toto Africa official audio"},
            {"artist": "Christopher Cross", "title": "Arthur's Theme (Best That You Can Do)", "ja_title": "ニューヨーク・シティ・セレナーデ", "query": "Christopher Cross Arthur's Theme Best That You Can Do official audio"},
            {"artist": "Grover Washington Jr. feat. Bill Withers", "title": "Just the Two of Us", "ja_title": "クリスタルの恋人たち", "query": "Grover Washington Jr Just the Two of Us official audio"},
            {"artist": "Air Supply", "title": "All Out of Love", "ja_title": "オール・アウト・オブ・ラヴ", "query": "Air Supply All Out of Love official audio"},
            {"artist": "George Benson", "title": "Nothing's Gonna Change My Love for You", "ja_title": "変わらぬ想い", "query": "George Benson Nothing's Gonna Change My Love for You official audio"},
            {"artist": "Billy Joel", "title": "Just the Way You Are", "ja_title": "素顔のままで", "query": "Billy Joel Just the Way You Are official audio"},
            {"artist": "Sade", "title": "Smooth Operator", "ja_title": "スムース・オペレーター", "query": "Sade Smooth Operator official audio"},
            {"artist": "Richard Marx", "title": "Right Here Waiting", "ja_title": "ライト・ヒア・ウェイティング", "query": "Richard Marx Right Here Waiting official audio"},
            {"artist": "Toto", "title": "Rosanna", "ja_title": "ロザーナ", "query": "Toto Rosanna official audio"},
            {"artist": "Steely Dan", "title": "Peg", "ja_title": "ペグ", "query": "Steely Dan Peg official audio"},
            {"artist": "The Doobie Brothers", "title": "What a Fool Believes", "ja_title": "ホワット・ア・フール・ビリーヴス", "query": "Doobie Brothers What a Fool Believes official audio"},
            {"artist": "Hall & Oates", "title": "I Can't Go for That (No Can Do)", "ja_title": "アイ・キャント・ゴー・フォー・ザット", "query": "Hall and Oates I Can't Go for That official audio"},
            {"artist": "Boz Scaggs", "title": "Jojo", "ja_title": "ジョジョ", "query": "Boz Scaggs Jojo official audio"},
            {"artist": "Bobby Caldwell", "title": "Heart of Mine", "ja_title": "ハート・オブ・マイン", "query": "Bobby Caldwell Heart of Mine official audio"},
            {"artist": "Simply Red", "title": "Holding Back the Years", "ja_title": "ホールディング・バック・ザ・イヤーズ", "query": "Simply Red Holding Back the Years official audio"},
            {"artist": "Anita Baker", "title": "Sweet Love", "ja_title": "スウィート・ラヴ", "query": "Anita Baker Sweet Love official audio"},
            {"artist": "Earth, Wind & Fire", "title": "After the Love Has Gone", "ja_title": "アフター・ザ・ラヴ・ハズ・ゴーン", "query": "Earth Wind and Fire After the Love Has Gone official audio"},
            {"artist": "Player", "title": "Baby Come Back", "ja_title": "ベイビー・カム・バック", "query": "Player Baby Come Back official audio"},
            {"artist": "Ambrosia", "title": "Biggest Part of Me", "ja_title": "ビゲスト・パート・オブ・ミー", "query": "Ambrosia Biggest Part of Me official audio"},
            {"artist": "Christopher Cross", "title": "Sailing", "ja_title": "セイリング", "query": "Christopher Cross Sailing official audio"},
            {"artist": "Toto", "title": "Georgy Porgy", "ja_title": "ジョージー・ポージー", "query": "Toto Georgy Porgy official audio"},
        ],
        "tags": ["夜に聴きたい洋楽", "80年代洋楽", "AOR", "洋楽メドレー", "40代", "50代", "Bobby Caldwell", "Boz Scaggs", "Chicago", "Toto", "懐かしい洋楽", "洋楽バラード", "作業用BGM", "2時間"],
    },
    # 03: ピアノが落ち着く・静かな夜の洋楽ピアノバラード（2時間・全24曲）
    {
        "id": "real_mix_003",
        "used": False,
        "genre": "90s Urban Mellow & Shibuya Groove",
        "artwork_file": "urban90s.jpg",
        "title": "【ピアノが落ち着く洋楽】静かな夜に心が安らぐ70s・80s・90sピアノ名曲バラード決定版【2時間・全24曲フル】Billy Joel / Elton John / Carpenters / Chicago",
        "short_title": "【ピアノが落ち着く洋楽】静かな夜に聴きたいピアノ名曲バラード全24曲 🎧本編2時間はチャンネルへ！ #Shorts #洋楽バラード",
        "thumb_era_label": "40代・50代 永久保存版  ｜  MELLOW PIANO BALLADS — 2 HOURS / 24 SONGS",
        "thumb_catch": "美しいピアノのイントロだけで、あの頃の記憶がよみがえる——",
        "thumb_main": "ピアノが落ち着く洋楽バラード【2時間】",
        "thumb_sub": "Billy Joel / Elton John / Carpenters / Chicago / Journey / Queen 他 全24曲",
        "tracks": [
            {"artist": "Billy Joel", "title": "Honesty", "ja_title": "オネスティ", "query": "Billy Joel Honesty official audio"},
            {"artist": "Billy Joel", "title": "Piano Man", "ja_title": "ピアノ・マン", "query": "Billy Joel Piano Man official audio"},
            {"artist": "Elton John", "title": "Your Song", "ja_title": "ユア・ソング（僕の歌は君の歌）", "query": "Elton John Your Song official audio"},
            {"artist": "Chicago", "title": "Hard to Say I'm Sorry", "ja_title": "素直になれなくて", "query": "Chicago Hard to Say I'm Sorry official audio"},
            {"artist": "Journey", "title": "Open Arms", "ja_title": "オープン・アームズ", "query": "Journey Open Arms official audio"},
            {"artist": "Christopher Cross", "title": "Arthur's Theme (Best That You Can Do)", "ja_title": "ニューヨーク・シティ・セレナーデ", "query": "Christopher Cross Arthur's Theme Best That You Can Do official audio"},
            {"artist": "Richard Marx", "title": "Right Here Waiting", "ja_title": "ライト・ヒア・ウェイティング", "query": "Richard Marx Right Here Waiting official audio"},
            {"artist": "Lionel Richie", "title": "Hello", "ja_title": "ハロー", "query": "Lionel Richie Hello official audio"},
            {"artist": "Phil Collins", "title": "Against All Odds (Take a Look at Me Now)", "ja_title": "みつめて欲しい", "query": "Phil Collins Against All Odds official audio"},
            {"artist": "Styx", "title": "Babe", "ja_title": "ベイブ", "query": "Styx Babe official audio"},
            {"artist": "Carpenters", "title": "I Need to Be in Love", "ja_title": "青春の輝き", "query": "Carpenters I Need to Be in Love official audio"},
            {"artist": "Billy Joel", "title": "Just the Way You Are", "ja_title": "素顔のままで", "query": "Billy Joel Just the Way You Are official audio"},
            {"artist": "Billy Joel", "title": "New York State of Mind", "ja_title": "ニューヨークの想い", "query": "Billy Joel New York State of Mind official audio"},
            {"artist": "Elton John", "title": "Sorry Seems to Be the Hardest Word", "ja_title": "悲しみのバラード", "query": "Elton John Sorry Seems to Be the Hardest Word official audio"},
            {"artist": "Carpenters", "title": "Rainy Days and Mondays", "ja_title": "雨の日と月曜日は", "query": "Carpenters Rainy Days and Mondays official audio"},
            {"artist": "Chicago", "title": "You're the Inspiration", "ja_title": "유・アー・ジ・インスピレーション", "query": "Chicago You're the Inspiration official audio"},
            {"artist": "Journey", "title": "Faithfully", "ja_title": "時への誓い", "query": "Journey Faithfully official audio"},
            {"artist": "Commodores", "title": "Easy", "ja_title": "イージー", "query": "Commodores Easy official audio"},
            {"artist": "Gilbert O'Sullivan", "title": "Alone Again (Naturally)", "ja_title": "アローン・アゲイン", "query": "Gilbert O'Sullivan Alone Again Naturally official audio"},
            {"artist": "10cc", "title": "I'm Not in Love", "ja_title": "アイム・ノット・イン・ラヴ", "query": "10cc I'm Not in Love official audio"},
            {"artist": "Roberta Flack", "title": "Killing Me Softly with His Song", "ja_title": "やさしく歌って", "query": "Roberta Flack Killing Me Softly with His Song official audio"},
            {"artist": "Vanessa Williams", "title": "Save the Best for Last", "ja_title": "セイヴ・ザ・ベスト・フォー・ラスト", "query": "Vanessa Williams Save the Best for Last official audio"},
            {"artist": "Bruce Hornsby & The Range", "title": "The Way It Is", "ja_title": "ザ・ウェイ・イット・イズ", "query": "Bruce Hornsby The Way It Is official audio"},
            {"artist": "Billy Joel", "title": "She's Always a Woman", "ja_title": "シーズ・オールウェイズ・ア・ウーマン", "query": "Billy Joel She's Always a Woman official audio"},
        ],
        "tags": ["ピアノが落ち着く", "洋楽バラード", "80年代洋楽", "Billy Joel", "Honesty", "Elton John", "Chicago", "Journey", "Carpenters", "40代", "50代", "夜に聴きたい洋楽", "作業用BGM", "睡眠用BGM"],
    },
    # 04: サックスが沁みる夜・ウイスキーと聴く深夜バー（2時間・全24曲）
    {
        "id": "real_mix_004",
        "used": False,
        "genre": "80s City Pop & Sax AOR",
        "artwork_file": "citypop80s.jpg",
        "title": "【サックスが沁みる夜】ウイスキー片手に聴きたい80s-90s洋楽サックス＆アーバンナイト名曲選【2時間・全24曲フル】Wham! / Sade / Grover Washington Jr.",
        "short_title": "【サックスが沁みる夜】ウイスキー片手に聴きたい80s-90s洋楽名曲全24曲 🎧本編2時間はチャンネルへ！ #Shorts #AOR",
        "thumb_era_label": "40代・50代 永久保存版  ｜  MIDNIGHT SAXOPHONE & AOR — 2 HOURS / 24 SONGS",
        "thumb_catch": "琥珀色のグラスと、夜の静寂に響くむせび泣くサックス——",
        "thumb_main": "サックスが沁みる夜の洋楽【2時間】",
        "thumb_sub": "Wham! / Sade / Grover Washington Jr. / Glenn Frey / Kenny G 他 全24曲",
        "tracks": [
            {"artist": "Wham!", "title": "Careless Whisper", "ja_title": "ケアレス・ウィスパー", "query": "Wham Careless Whisper official audio"},
            {"artist": "Sade", "title": "Smooth Operator", "ja_title": "スムース・オペレーター", "query": "Sade Smooth Operator official audio"},
            {"artist": "Grover Washington Jr. feat. Bill Withers", "title": "Just the Two of Us", "ja_title": "クリスタルの恋人たち", "query": "Grover Washington Jr Just the Two of Us official audio"},
            {"artist": "Glenn Frey", "title": "The One You Love", "ja_title": "ザ・ワン・ユー・ラヴ", "query": "Glenn Frey The One You Love official audio"},
            {"artist": "Gerry Rafferty", "title": "Baker Street", "ja_title": "ベイカー・ストリート", "query": "Gerry Rafferty Baker Street official audio"},
            {"artist": "Billy Joel", "title": "Just the Way You Are", "ja_title": "素顔のままで", "query": "Billy Joel Just the Way You Are official audio"},
            {"artist": "Spandau Ballet", "title": "True", "ja_title": "トゥルー", "query": "Spandau Ballet True official audio"},
            {"artist": "Hall & Oates", "title": "One on One", "ja_title": "ワン・オン・ワン", "query": "Hall and Oates One on One official audio"},
            {"artist": "Quarterflash", "title": "Harden My Heart", "ja_title": "ミスティ・ハート", "query": "Quarterflash Harden My Heart official audio"},
            {"artist": "Kenny G", "title": "Songbird", "ja_title": "ソングバード", "query": "Kenny G Songbird official audio"},
            {"artist": "Simply Red", "title": "Holding Back the Years", "ja_title": "ホールディング・バック・ザ・イヤーズ", "query": "Simply Red Holding Back the Years official audio"},
            {"artist": "Sade", "title": "Your Love Is King", "ja_title": "ユア・ラヴ・イズ・キング", "query": "Sade Your Love Is King official audio"},
            {"artist": "Candy Dulfer & Dave Stewart", "title": "Lily Was Here", "ja_title": "リリー・ワズ・ヒア", "query": "Candy Dulfer Dave Stewart Lily Was Here official audio"},
            {"artist": "Kenny G", "title": "Silhouette", "ja_title": "シルエット", "query": "Kenny G Silhouette official audio"},
            {"artist": "Supertramp", "title": "The Logical Song", "ja_title": "ロジカル・ソング", "query": "Supertramp The Logical Song official audio"},
            {"artist": "Al Stewart", "title": "Year of the Cat", "ja_title": "イヤー・オブ・ザ・キャット", "query": "Al Stewart Year of the Cat official audio"},
            {"artist": "Dire Straits", "title": "Your Latest Trick", "ja_title": "ユア・レイテスト・トリック", "query": "Dire Straits Your Latest Trick official audio"},
            {"artist": "Roxy Music", "title": "Avalon", "ja_title": "アヴァロン", "query": "Roxy Music Avalon official audio"},
            {"artist": "Foreigner", "title": "Urgent", "ja_title": "アージェント", "query": "Foreigner Urgent official audio"},
            {"artist": "Men at Work", "title": "Who Can It Be Now?", "ja_title": "ノックは夜中に", "query": "Men at Work Who Can It Be Now official audio"},
            {"artist": "INXS", "title": "Never Tear Us Apart", "ja_title": "ネヴァー・ティア・アス・アパート", "query": "INXS Never Tear Us Apart official audio"},
            {"artist": "Tina Turner", "title": "The Best", "ja_title": "ザ・ベスト", "query": "Tina Turner The Best official audio"},
            {"artist": "Sade", "title": "The Sweetest Taboo", "ja_title": "スウィーテスト・タブー", "query": "Sade The Sweetest Taboo official audio"},
            {"artist": "Double", "title": "The Captain of Her Heart", "ja_title": "キャプテン・オブ・ハー・ハート", "query": "Double The Captain of Her Heart official audio"},
        ],
        "tags": ["サックス", "夜に聴きたい洋楽", "80年代洋楽", "AOR", "Careless Whisper", "Sade", "ウイスキーに合う曲", "40代", "50代", "大人BGM", "バーBGM", "作業用BGM"],
    },
    # 05: アコギが心地よい・休日の午後＆夕暮れソフトロック（2時間・全24曲）
    {
        "id": "real_mix_005",
        "used": False,
        "genre": "90s Urban Mellow & Shibuya Groove",
        "artwork_file": "urban90s.jpg",
        "title": "【アコギが心地よい洋楽】休日の午後や夕暮れに聴きたいアコースティック＆ソフトロック決定版【2時間・全24曲フル】Eric Clapton / America / Extreme / Eagles",
        "short_title": "【アコギが心地よい洋楽】休日の夕暮れに聴きたいアコースティック名曲24選 🎧本編2時間はチャンネルへ！ #Shorts #洋楽",
        "thumb_era_label": "40代・50代 永久保存版  ｜  ACOUSTIC & SOFT ROCK — 2 HOURS / 24 SONGS",
        "thumb_catch": "優しいアコースティックギターの弦音が、心を穏やかに整える——",
        "thumb_main": "アコギが心地よい大人の洋楽【2時間】",
        "thumb_sub": "Eric Clapton / Extreme / America / Kansas / Bread / James Taylor 他 全24曲",
        "tracks": [
            {"artist": "Eric Clapton", "title": "Tears in Heaven", "ja_title": "ティアーズ・イン・ヘヴン", "query": "Eric Clapton Tears in Heaven official audio"},
            {"artist": "Extreme", "title": "More Than Words", "ja_title": "モア・ザン・ワーズ", "query": "Extreme More Than Words official audio"},
            {"artist": "Mr. Big", "title": "To Be With You", "ja_title": "トゥ・ビー・ウィズ・ユー", "query": "Mr Big To Be With You official audio"},
            {"artist": "America", "title": "A Horse with No Name", "ja_title": "名前のない馬", "query": "America A Horse with No Name official audio"},
            {"artist": "Kansas", "title": "Dust in the Wind", "ja_title": "すべては風の中に", "query": "Kansas Dust in the Wind official audio"},
            {"artist": "Bread", "title": "If", "ja_title": "イフ", "query": "Bread If official audio"},
            {"artist": "James Taylor", "title": "You've Got a Friend", "ja_title": "君の友だち", "query": "James Taylor You've Got a Friend official audio"},
            {"artist": "Tracy Chapman", "title": "Fast Car", "ja_title": "ファスト・カー", "query": "Tracy Chapman Fast Car official audio"},
            {"artist": "Simon & Garfunkel", "title": "The Boxer", "ja_title": "ボクサー", "query": "Simon and Garfunkel The Boxer official audio"},
            {"artist": "Christopher Cross", "title": "Sailing", "ja_title": "セイリング", "query": "Christopher Cross Sailing official audio"},
            {"artist": "Lobo", "title": "I'd Love You to Want Me", "ja_title": "片想いと僕", "query": "Lobo I'd Love You to Want Me official audio"},
            {"artist": "Eric Clapton", "title": "Wonderful Tonight", "ja_title": "ワンダフル・トゥナイト", "query": "Eric Clapton Wonderful Tonight official audio"},
            {"artist": "America", "title": "Ventura Highway", "ja_title": "ヴェンチュラ・ハイウェイ", "query": "America Ventura Highway official audio"},
            {"artist": "America", "title": "Sister Golden Hair", "ja_title": "金色の髪の少女", "query": "America Sister Golden Hair official audio"},
            {"artist": "Eagles", "title": "Take It Easy", "ja_title": "テイク・イット・イージー", "query": "Eagles Take It Easy official audio"},
            {"artist": "Eagles", "title": "Tequila Sunrise", "ja_title": "テキーラ・サンライズ", "query": "Eagles Tequila Sunrise official audio"},
            {"artist": "Bread", "title": "Make It with You", "ja_title": "二人の架け橋", "query": "Bread Make It with You official audio"},
            {"artist": "Dan Fogelberg", "title": "Longer", "ja_title": "ロンガー", "query": "Dan Fogelberg Longer official audio"},
            {"artist": "Jim Croce", "title": "Time in a Bottle", "ja_title": "タイム・イン・ア・ボトル", "query": "Jim Croce Time in a Bottle official audio"},
            {"artist": "John Denver", "title": "Take Me Home, Country Roads", "ja_title": "カントリー・ロード", "query": "John Denver Take Me Home Country Roads official audio"},
            {"artist": "Cat Stevens", "title": "Wild World", "ja_title": "ワイルド・ワールド", "query": "Cat Stevens Wild World official audio"},
            {"artist": "Seals and Crofts", "title": "Summer Breeze", "ja_title": "サマー・ブリーズ", "query": "Seals and Crofts Summer Breeze official audio"},
            {"artist": "Orleans", "title": "Dance with Me", "ja_title": "ダンス・ウィズ・ミー", "query": "Orleans Dance with Me official audio"},
            {"artist": "Eric Clapton", "title": "Change the World", "ja_title": "チェンジ・ザ・ワールド", "query": "Eric Clapton Change the World official audio"},
        ],
        "tags": ["アコギ", "アコースティック", "ソフトロック", "80年代洋楽", "90年代洋楽", "Eric Clapton", "More Than Words", "40代", "50代", "休日BGM", "カフェBGM", "作業用BGM", "2時間"],
    },
    # 06: 雨の夜に聴きたい・心を癒やすスローバラード（2時間・全24曲）
    {
        "id": "real_mix_006",
        "used": False,
        "genre": "90s Urban Mellow & Shibuya Groove",
        "artwork_file": "urban90s.jpg",
        "title": "【雨の夜に聴きたい洋楽】窓を打つ雨音と聴く80年代・90年代スローバラード名曲大全集【2時間・全24曲フル】Whitney Houston / Cyndi Lauper / Celine Dion",
        "short_title": "【雨の夜に聴きたい洋楽】心にしみる80s-90sスローバラード名曲24選 🎧本編2時間はチャンネルへ！ #Shorts #洋楽バラード",
        "thumb_era_label": "40代・50代 永久保存版  ｜  RAINY NIGHT BALLADS — 2 HOURS / 24 SONGS",
        "thumb_catch": "静かな雨の夜、あの頃の甘いラブバラードに身を委ねる——",
        "thumb_main": "雨の夜に聴きたい洋楽バラード【2時間】",
        "thumb_sub": "Cyndi Lauper / Whitney Houston / Air Supply / Celine Dion 他 全24曲",
        "tracks": [
            {"artist": "Cyndi Lauper", "title": "Time After Time", "ja_title": "タイム・アフター・タイム", "query": "Cyndi Lauper Time After Time official audio"},
            {"artist": "Air Supply", "title": "Even the Nights Are Better", "ja_title": "さよならロンリー・ラヴ", "query": "Air Supply Even the Nights Are Better official audio"},
            {"artist": "Whitney Houston", "title": "Saving All My Love for You", "ja_title": "すべてをあなたに", "query": "Whitney Houston Saving All My Love for You official audio"},
            {"artist": "George Michael", "title": "One More Try", "ja_title": "ワン・モア・トライ", "query": "George Michael One More Try official audio"},
            {"artist": "Atlantic Starr", "title": "Always", "ja_title": "オールウェイズ", "query": "Atlantic Starr Always official audio"},
            {"artist": "Peabo Bryson & Regina Belle", "title": "A Whole New World", "ja_title": "ホール・ニュー・ワールド", "query": "Peabo Bryson Regina Belle A Whole New World official audio"},
            {"artist": "Vanessa Williams", "title": "Save the Best for Last", "ja_title": "セイヴ・ザ・ベスト・フォー・ラスト", "query": "Vanessa Williams Save the Best for Last official audio"},
            {"artist": "Roberta Flack", "title": "Killing Me Softly with His Song", "ja_title": "やさしく歌って", "query": "Roberta Flack Killing Me Softly with His Song official audio"},
            {"artist": "Mariah Carey", "title": "Hero", "ja_title": "ヒーロー", "query": "Mariah Carey Hero official audio"},
            {"artist": "Boyz II Men", "title": "End of the Road", "ja_title": "エンド・オブ・ザ・ロード", "query": "Boyz II Men End of the Road official audio"},
            {"artist": "Toni Braxton", "title": "Un-Break My Heart", "ja_title": "アンブレイク・マイ・ハート", "query": "Toni Braxton Un-Break My Heart official audio"},
            {"artist": "Lionel Richie & Diana Ross", "title": "Endless Love", "ja_title": "エンドレス・ラヴ", "query": "Lionel Richie Diana Ross Endless Love official audio"},
            {"artist": "Whitney Houston", "title": "Greatest Love of All", "ja_title": "グレイテスト・ラヴ・オブ・オール", "query": "Whitney Houston Greatest Love of All official audio"},
            {"artist": "Mariah Carey", "title": "Without You", "ja_title": "ウィズアウト・ユー", "query": "Mariah Carey Without You official audio"},
            {"artist": "Celine Dion", "title": "Because You Loved Me", "ja_title": "ビコーズ・ユー・ラヴド・ミー", "query": "Celine Dion Because You Loved Me official audio"},
            {"artist": "Air Supply", "title": "Lost in Love", "ja_title": "ロスト・イン・ラヴ", "query": "Air Supply Lost in Love official audio"},
            {"artist": "Air Supply", "title": "The One That You Love", "ja_title": "シー・イズ・ザ・ワン", "query": "Air Supply The One That You Love official audio"},
            {"artist": "pretenders", "title": "I'll Stand by You", "ja_title": "アイル・スタンド・バイ・ユー", "query": "Pretenders I'll Stand by You official audio"},
            {"artist": "Cyndi Lauper", "title": "True Colors", "ja_title": "トゥルー・カラーズ", "query": "Cyndi Lauper True Colors official audio"},
            {"artist": "Madonna", "title": "Crazy for You", "ja_title": "クレイジー・フォー・ユー", "query": "Madonna Crazy for You official audio"},
            {"artist": "Janet Jackson", "title": "Again", "ja_title": "アゲイン", "query": "Janet Jackson Again official audio"},
            {"artist": "Babyface", "title": "Every Time I Close My Eyes", "ja_title": "エヴリ・タイム・アイ・クローズ・マイ・アイズ", "query": "Babyface Every Time I Close My Eyes official audio"},
            {"artist": "Surface", "title": "Shower Me with Your Love", "ja_title": "シャワー・ミー・ウィズ・ユア・ラヴ", "query": "Surface Shower Me with Your Love official audio"},
            {"artist": "Champaign", "title": "How 'Bout Us", "ja_title": "ハウ・バウト・アス", "query": "Champaign How Bout Us official audio"},
        ],
        "tags": ["雨の夜に聴きたい", "洋楽バラード", "80年代洋楽", "90年代洋楽", "Cyndi Lauper", "Whitney Houston", "Air Supply", "40代", "50代", "睡眠用BGM", "2時間"],
    },
    # 07: バブル期の六本木・マハラジャ80sディスコ大全集（2時間・全24曲）
    {
        "id": "real_mix_007",
        "used": False,
        "genre": "80s Japanese Boogie Disco",
        "artwork_file": "disco.jpg",
        "title": "【バブル世代必見】イントロで六本木が蘇る！80年代ディスコ＆ユーロビート洋楽ヒット大全集【2時間・全24曲フル】Earth, Wind & Fire / Boys Town Gang 他",
        "short_title": "【バブル世代必見】イントロで六本木が蘇る！80年代ディスコ洋楽全24曲 🎧本編2時間はチャンネルへ！ #Shorts #80sディスコ",
        "thumb_era_label": "40代・50代 永久保存版  ｜  1980s ROPPONGI DISCO — 2 HOURS / 24 SONGS",
        "thumb_catch": "ミラーボールの輝きと、あの頃の週末の熱狂がよみがえる——",
        "thumb_main": "80年代 六本木ディスコ洋楽【2時間】",
        "thumb_sub": "Earth, Wind & Fire / Boys Town Gang / Dead Or Alive / Bananarama 他 全24曲",
        "tracks": [
            {"artist": "Earth, Wind & Fire", "title": "September", "ja_title": "セプテンバー", "query": "Earth Wind and Fire September official audio"},
            {"artist": "Boys Town Gang", "title": "Can't Take My Eyes Off You", "ja_title": "君の瞳に恋してる", "query": "Boys Town Gang Can't Take My Eyes Off You official audio"},
            {"artist": "Earth, Wind & Fire", "title": "Boogie Wonderland", "ja_title": "ブギー・ワンダーランド", "query": "Earth Wind and Fire Boogie Wonderland official audio"},
            {"artist": "Kool & The Gang", "title": "Celebration", "ja_title": "セレブレイション", "query": "Kool and the Gang Celebration official audio"},
            {"artist": "Dead Or Alive", "title": "You Spin Me Round (Like a Record)", "ja_title": "ユー・スピン・ミー・ラウンド", "query": "Dead Or Alive You Spin Me Round Like a Record official audio"},
            {"artist": "Bananarama", "title": "Venus", "ja_title": "ヴィーナス", "query": "Bananarama Venus official audio"},
            {"artist": "Rick Astley", "title": "Never Gonna Give You Up", "ja_title": "ギヴ・ユー・アップ", "query": "Rick Astley Never Gonna Give You Up official audio"},
            {"artist": "Kylie Minogue", "title": "I Should Be So Lucky", "ja_title": "ラッキー・ラブ", "query": "Kylie Minogue I Should Be So Lucky official audio"},
            {"artist": "Michael Sembello", "title": "Maniac", "ja_title": "マニアック (フラッシュダンス)", "query": "Michael Sembello Maniac official audio"},
            {"artist": "Irene Cara", "title": "Flashdance... What a Feeling", "ja_title": "ホワット・ア・フィーリング", "query": "Irene Cara Flashdance What a Feeling official audio"},
            {"artist": "Chaka Khan", "title": "I Feel for You", "ja_title": "アイ・フィール・フォー・ユー", "query": "Chaka Khan I Feel for You official audio"},
            {"artist": "Earth, Wind & Fire", "title": "Let's Groove", "ja_title": "レッツ・グルーヴ", "query": "Earth Wind and Fire Let's Groove official audio"},
            {"artist": "Donna Summer", "title": "Hot Stuff", "ja_title": "ホット・スタッフ", "query": "Donna Summer Hot Stuff official audio"},
            {"artist": "Gloria Gaynor", "title": "I Will Survive", "ja_title": "恋のサバイバル", "query": "Gloria Gaynor I Will Survive official audio"},
            {"artist": "Village People", "title": "Y.M.C.A.", "ja_title": "Y.M.C.A.", "query": "Village People YMCA official audio"},
            {"artist": "ABBA", "title": "Dancing Queen", "ja_title": "ダンシング・クイーン", "query": "ABBA Dancing Queen official audio"},
            {"artist": "Bee Gees", "title": "Stayin' Alive", "ja_title": "ステイン・アライヴ", "query": "Bee Gees Stayin Alive official audio"},
            {"artist": "Chic", "title": "Le Freak", "ja_title": "おしゃれフリーク", "query": "Chic Le Freak official audio"},
            {"artist": "Sister Sledge", "title": "We Are Family", "ja_title": "ウィ・アー・ファミリー", "query": "Sister Sledge We Are Family official audio"},
            {"artist": "kc and the Sunshine Band", "title": "That's the Way (I Like It)", "ja_title": "ザッツ・ザ・ウェイ", "query": "KC and the Sunshine Band That's the Way I Like It official audio"},
            {"artist": "Boney M.", "title": "Sunny", "ja_title": "サニー", "query": "Boney M Sunny official audio"},
            {"artist": "Arabesque", "title": "Hello Mr. Monkey", "ja_title": "ハロー・ミスター・モンキー", "query": "Arabesque Hello Mr Monkey official audio"},
            {"artist": "The Nolans", "title": "I'm in the Mood for Dancing", "ja_title": "ダンシング・シスター", "query": "The Nolans I'm in the Mood for Dancing official audio"},
            {"artist": "Wham!", "title": "Wake Me Up Before You Go-Go", "ja_title": "ウキウキ・ウェイク・ミー・アップ", "query": "Wham Wake Me Up Before You Go-Go official audio"},
        ],
        "tags": ["80年代ディスコ", "80年代洋楽", "バブル世代", "マハラジャ", "六本木ディスコ", "40代", "50代", "Earth Wind and Fire", "君の瞳に恋してる", "洋楽メドレー", "ドライブBGM", "2時間"],
    },
    # 08: 夜の高速道路・80sハイウェイ＆アメリカンロック大全集（2時間・全24曲）
    {
        "id": "real_mix_008",
        "used": False,
        "genre": "90s Eurobeat",
        "artwork_file": "eurobeat.jpg",
        "title": "【夜のハイウェイ洋楽】深夜の高速道路で聴いた80年代・90年代アメリカンロック名曲大全集【2時間・全24曲フル】Journey / Bon Jovi / Van Halen / Foreigner",
        "short_title": "【夜のハイウェイ洋楽】夜の高速道路で聴いた80s-90sロック名曲24選 🎧本編2時間はチャンネルへ！ #Shorts #80s洋楽",
        "thumb_era_label": "40代・50代 永久保存版  ｜  1980s HIGHWAY ROCK — 2 HOURS / 24 SONGS",
        "thumb_catch": "アクセルを踏み込んだ瞬間、あの頃のハイウェイが蘇る——",
        "thumb_main": "夜のハイウェイ洋楽ロック【2時間】",
        "thumb_sub": "Journey / Bon Jovi / Van Halen / Foreigner / REO Speedwagon 他 全24曲",
        "tracks": [
            {"artist": "Journey", "title": "Separate Ways (Worlds Apart)", "ja_title": "セパレイト・ウェイズ", "query": "Journey Separate Ways Worlds Apart official audio"},
            {"artist": "Bon Jovi", "title": "Livin' on a Prayer", "ja_title": "リヴィン・オン・ア・プレイヤー", "query": "Bon Jovi Livin on a Prayer official audio"},
            {"artist": "Van Halen", "title": "Jump", "ja_title": "ジャンプ", "query": "Van Halen Jump official audio"},
            {"artist": "Survivor", "title": "Eye of the Tiger", "ja_title": "アイ・オブ・ザ・タイガー", "query": "Survivor Eye of the Tiger official audio"},
            {"artist": "Europe", "title": "The Final Countdown", "ja_title": "ファイナル・カウントダウン", "query": "Europe The Final Countdown official audio"},
            {"artist": "Journey", "title": "Don't Stop Believin'", "ja_title": "ドント・ストップ・ビリーヴィン", "query": "Journey Don't Stop Believin official audio"},
            {"artist": "Starship", "title": "We Built This City", "ja_title": "シスコはロック・シティ", "query": "Starship We Built This City official audio"},
            {"artist": "Bryan Adams", "title": "Summer of '69", "ja_title": "想い出のサマー", "query": "Bryan Adams Summer of 69 official audio"},
            {"artist": "Bon Jovi", "title": "You Give Love a Bad Name", "ja_title": "禁じられた愛", "query": "Bon Jovi You Give Love a Bad Name official audio"},
            {"artist": "Bon Jovi", "title": "It's My Life", "ja_title": "イッツ・マイ・ライフ", "query": "Bon Jovi It's My Life official audio"},
            {"artist": "Foreigner", "title": "I Want to Know What Love Is", "ja_title": "アイ・ウォント・トゥ・ノウ・ホワット・ラヴ・イズ", "query": "Foreigner I Want to Know What Love Is official audio"},
            {"artist": "REO Speedwagon", "title": "Keep On Loving You", "ja_title": "キープ・オン・ラヴィング・ユー", "query": "REO Speedwagon Keep On Loving You official audio"},
            {"artist": "REO Speedwagon", "title": "Can't Fight This Feeling", "ja_title": "涙のフィーリング", "query": "REO Speedwagon Can't Fight This Feeling official audio"},
            {"artist": "Toto", "title": "Hold the Line", "ja_title": "ホールド・ザ・ライン", "query": "Toto Hold the Line official audio"},
            {"artist": "Boston", "title": "More Than a Feeling", "ja_title": "宇宙の彼方へ", "query": "Boston More Than a Feeling official audio"},
            {"artist": "Kansas", "title": "Carry On Wayward Son", "ja_title": "伝承", "query": "Kansas Carry On Wayward Son official audio"},
            {"artist": "Styx", "title": "Mr. Roboto", "ja_title": "ミスター・ロボット", "query": "Styx Mr Roboto official audio"},
            {"artist": "Yes", "title": "Owner of a Lonely Heart", "ja_title": "ロンリー・ハート", "query": "Yes Owner of a Lonely Heart official audio"},
            {"artist": "Asia", "title": "Heat of the Moment", "ja_title": "ヒート・オブ・ザ・モーメント", "query": "Asia Heat of the Moment official audio"},
            {"artist": "Mr. Mister", "title": "Broken Wings", "ja_title": "ブロークン・ウィングス", "query": "Mr Mister Broken Wings official audio"},
            {"artist": "Cutting Crew", "title": "(I Just) Died in Your Arms", "ja_title": "愛に抱かれた夜", "query": "Cutting Crew I Just Died in Your Arms official audio"},
            {"artist": "Whitesnake", "title": "Here I Go Again", "ja_title": "ヒア・アイ・ゴー・アゲイン", "query": "Whitesnake Here I Go Again official audio"},
            {"artist": "Scorpions", "title": "Rock You Like a Hurricane", "ja_title": "ハリケーン", "query": "Scorpions Rock You Like a Hurricane official audio"},
            {"artist": "Def Leppard", "title": "Pour Some Sugar on Me", "ja_title": "シュガー・オン・ミー", "query": "Def Leppard Pour Some Sugar on Me official audio"},
        ],
        "tags": ["80年代洋楽", "洋楽ロック", "ドライブBGM", "Journey", "Bon Jovi", "Van Halen", "40代", "50代", "懐かしい洋楽", "高速道路BGM", "作業用BGM", "2時間"],
    },
]


def ensure_real_hits_pool() -> List[Dict[str, Any]]:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    if not REAL_HITS_POOL_PATH.exists():
        REAL_HITS_POOL_PATH.write_text(
            json.dumps({"total": len(DEFAULT_REAL_HIT_MIXES), "items": DEFAULT_REAL_HIT_MIXES}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return DEFAULT_REAL_HIT_MIXES
    raw = json.loads(REAL_HITS_POOL_PATH.read_text(encoding="utf-8"))
    items = raw["items"] if isinstance(raw, dict) and "items" in raw else raw
    if not items or len(items[0].get("tracks", [])) < 20:
        REAL_HITS_POOL_PATH.write_text(
            json.dumps({"total": len(DEFAULT_REAL_HIT_MIXES), "items": DEFAULT_REAL_HIT_MIXES}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return DEFAULT_REAL_HIT_MIXES
    return items


def save_real_hits_pool(pool: List[Dict[str, Any]], chosen_id: str, auto_git_push: bool = True) -> None:
    REAL_HITS_POOL_PATH.write_text(
        json.dumps({"total": len(pool), "items": pool}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if auto_git_push and os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
                check=True,
            )
            subprocess.run(["git", "add", "stocks/music/real_hits_pool.json"], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"chore(music): mark {chosen_id} as published in real_hits_pool.json"],
                check=True,
            )
            subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], check=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
            logger.info("Committed and pushed updated real_hits_pool.json to GitHub.")
        except Exception as exc:
            logger.warning(f"Git commit/push warning: {exc}")


def _fmt_hhmmss(seconds: float) -> str:
    total = int(seconds)
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    if hh > 0:
        return f"{hh:d}:{mm:02d}:{ss:02d}"
    return f"{mm:02d}:{ss:02d}"


def download_and_mix_real_tracks(
    tracks: List[Dict[str, str]],
    out_m4a: Path,
    out_mp3_for_short: Path,
    max_total_duration_sec: int = 10800,
    medley_out_dir: Optional[Path] = None,
) -> Tuple[str, float, List[Path]]:
    """
    Download all 24 tracks via `yt-dlp` at full length (up to 480s per song so every song plays completely!),
    normalize loudness (`loudnorm`), apply smooth 2.5s fade-in/out per track, concatenate into `out_m4a` (~2 hours),
    and return `(formatted_timestamps, actual_duration, medley_track_paths)`.
    """
    import yt_dlp

    per_track_max = 480 if max_total_duration_sec >= 3600 else int((max_total_duration_sec - 5) / max(1, len(tracks)))
    medley_saved: List[Path] = []

    with tempfile.TemporaryDirectory(prefix="real_hits_dl_") as tmp_s:
        tmp_dir = Path(tmp_s)
        norm_segments: List[Path] = []
        timestamp_lines: List[str] = []
        cursor_sec = 0.0

        for idx, tr in enumerate(tracks, start=1):
            query = tr["query"]
            sc_query = f"{tr['artist']} {tr['title']}"
            raw_out_tmpl = str(tmp_dir / f"raw_{idx:02d}.%(ext)s")
            logger.info(f"[{idx}/{len(tracks)}] Downloading Full Track via yt-dlp: {tr['artist']} - {tr['title']} ...")

            def _duration_filter(info_dict: Dict[str, Any], *, incomplete: bool = False) -> Optional[str]:
                dur = info_dict.get("duration")
                if dur is not None and (dur < 95 or dur > 660):
                    return "Track duration outside 95s..660s full-song window"
                return None

            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "outtmpl": raw_out_tmpl,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "max_downloads": 1,
                "match_filter": _duration_filter,
            }
            search_targets = (
                [f"scsearch10:{sc_query}", f"ytsearch3:{query}"]
                if os.environ.get("GITHUB_ACTIONS") == "true"
                else [f"ytsearch3:{query}", f"scsearch10:{sc_query}"]
            )
            for starget in search_targets:
                for old_f in tmp_dir.glob(f"raw_{idx:02d}.*"):
                    old_f.unlink(missing_ok=True)
                try:
                    with yt_dlp.YoutubeDL(dict(ydl_opts)) as ydl:
                        ydl.download([starget])
                except yt_dlp.utils.MaxDownloadsReached:
                    pass
                except Exception as dl_exc:
                    if "Maximum number of downloads reached" not in str(dl_exc):
                        logger.warning(f"  -> {starget} warning: {dl_exc}")
                downloaded = sorted(tmp_dir.glob(f"raw_{idx:02d}.*"))
                if downloaded and get_audio_duration(downloaded[0]) >= 60.0:
                    break

            downloaded = sorted(tmp_dir.glob(f"raw_{idx:02d}.*"))
            if not downloaded:
                raise RuntimeError(f"yt-dlp failed to download audio for: {query}")
            src_audio = downloaded[0]

            raw_dur = get_audio_duration(src_audio)
            seg_dur = min(raw_dur, float(per_track_max))
            fade_out_st = max(1.0, seg_dur - 3.0)

            norm_m4a = tmp_dir / f"seg_{idx:02d}.m4a"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(src_audio),
                    "-t",
                    f"{seg_dur:.2f}",
                    "-af",
                    f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=2.0,afade=t=out:st={fade_out_st:.2f}:d=3.0",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    str(norm_m4a),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            actual_seg_dur = get_audio_duration(norm_m4a)
            ts_str = _fmt_hhmmss(cursor_sec)
            timestamp_lines.append(
                f"{ts_str} {idx:02d}. {tr['artist']} — {tr['title']} （{tr['ja_title']}）"
            )
            cursor_sec += actual_seg_dur
            norm_segments.append(norm_m4a)

            if idx == 1:
                shutil.copy2(norm_m4a, out_mp3_for_short)
            if medley_out_dir and idx in (2, 3, 4):
                m_dest = medley_out_dir / f"medley_trk_{idx:02d}.m4a"
                shutil.copy2(norm_m4a, m_dest)
                medley_saved.append(m_dest)

        concat_txt = tmp_dir / "concat.txt"
        concat_txt.write_text(
            "\n".join([f"file '{p.as_posix()}'" for p in norm_segments]) + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_txt),
                "-t",
                str(max_total_duration_sec),
                "-c",
                "copy",
                str(out_m4a),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    total_dur = get_audio_duration(out_m4a)
    logger.info(f"Built 2-Hour Full-Length 24-Track Real Hits Mix audio: {out_m4a.name} ({total_dur:.1f}s / {total_dur/60:.1f}m across {len(tracks)} tracks)")
    return "\n".join(timestamp_lines), total_dur, medley_saved


def decorate_hud_and_thumb_with_setlist(
    hud_png: Path,
    thumb_jpg: Path,
    tracks: List[Dict[str, str]],
    font_path: str,
) -> None:
    """
    Overlay a sleek 3-column 24-track SETLIST card onto `hud_png` (1920x1080) and replace the `NO ADS` pill
    with `2 HOURS / 24 SONGS` so viewers immediately see all 24 famous artist & song names on screen.
    """
    cjk_reg_path = find_cjk_font() or font_path
    cjk_mincho_path = find_cjk_mincho_font() or cjk_reg_path

    hud = Image.open(hud_png).convert("RGBA")
    draw = ImageDraw.Draw(hud, "RGBA")

    lx0, ly0, lx1, ly1 = 72, 134, 1848, 520
    draw.rounded_rectangle(
        (lx0, ly0, lx1, ly1),
        radius=22,
        fill=(8, 12, 22, 182),
        outline=(217, 179, 108, 150),
        width=2,
    )
    f_head = load_font(cjk_reg_path, 21)
    draw.text(
        (lx0 + 28, ly0 + 14),
        f"♪ 2-HOUR FULL-LENGTH {len(tracks)} TRACKS SETLIST  ｜  収録名曲リスト（概要欄チャプターから全24曲へジャンプ可能）",
        font=f_head,
        fill=(217, 179, 108, 245),
    )
    draw.line([(lx0 + 28, ly0 + 46), (lx1 - 28, ly0 + 46)], fill=(217, 179, 108, 95), width=1)

    col_w = ((lx1 - lx0) - 84) // 3
    for idx, tr in enumerate(tracks[:24]):
        col = idx // 8
        row = idx % 8
        col_x = lx0 + 28 + col * (col_w + 18)
        row_y = ly0 + 56 + row * 40
        line_txt = f"{idx+1:02d}. {tr['artist']} - {tr['title']}"
        f_row = fit_font_for_width(draw, line_txt, cjk_mincho_path, 19, 14, col_w - 8)
        _draw_soft_shadow_text(
            hud,
            (col_x, row_y),
            line_txt,
            font=f_row,
            fill=(250, 248, 242, 248),
            blur_radius=3,
        )

    draw = ImageDraw.Draw(hud, "RGBA")
    stamp_txt = f"2 HOURS / {len(tracks)} SONGS"
    f_stamp = load_font(font_path, 23)
    tb_st = draw.textbbox((0, 0), stamp_txt, font=f_stamp)
    st_w = (tb_st[2] - tb_st[0]) + 64
    st_x0 = 1920 - 72 - st_w
    draw.rounded_rectangle(
        (1920 - 440, 964, 1920 - 68, 1028),
        radius=27,
        fill=(8, 10, 16, 255),
    )
    draw.rounded_rectangle(
        (st_x0, 969, st_x0 + st_w, 1023),
        radius=27,
        fill=(10, 12, 18, 200),
        outline=(217, 179, 108, 155),
        width=2,
    )
    draw.text((st_x0 + 32, 983), stamp_txt, font=f_stamp, fill=(226, 214, 185, 245))
    hud.save(hud_png, "PNG")


def build_real_hits_description(meta: Dict[str, Any], formatted_timestamps: str) -> str:
    tracks_summary = " / ".join([f"{t['artist']}「{t['title']}」" for t in meta["tracks"][:10]]) + f" ほか全{len(meta['tracks'])}曲フル尺収録"
    return (
        f"🎧 {meta['title']}\n\n"
        f"1980年代〜1990年代の映画主題歌やFMラジオ、夜のドライブで流れていた本物の洋楽レジェンド名曲全{len(meta['tracks'])}曲（{tracks_summary}）を、"
        "1曲ずつフル尺・約2時間ノンストップでお届けする永久保存版メドレーです。\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ 収録曲トラックリスト / チャプター (全{len(meta['tracks'])}曲フル尺・約2時間):\n"
        f"{formatted_timestamps}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🌙 途中に広告が入らない【広告なし】の深夜ドライブ・80s/90s AORプレイリスト（毎日19時公開）も\n"
        "👇 チャンネルトップからぜひチャンネル登録してお楽しみください。\n"
        "https://www.youtube.com/@midnight_cockpit\n\n"
        "#80年代洋楽 #90年代洋楽 #映画音楽 #名画メドレー #AOR #洋楽メドレー #40代 #50代 #懐かしい洋楽 #作業用BGM #ドライブBGM"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build & upload 2-Hour Full-Length Real 80s/90s Western Legend 24-Song Hit Mix + 2 Shorts (Design A & C).")
    parser.add_argument("--mix-id", default="", help="Specific mix id from real_hits_pool.json (default: first unused).")
    parser.add_argument("--max-duration", type=int, default=10800, help="Max total duration in seconds (default: 10800 = up to 3 hours).")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publish-now", action="store_true", help="Publish immediately even if outside Japan Golden Time.")
    args = parser.parse_args()

    pool = ensure_real_hits_pool()
    chosen_meta: Optional[Dict[str, Any]] = None
    if args.mix_id:
        for item in pool:
            if item["id"] == args.mix_id:
                chosen_meta = item
                break
    if chosen_meta is None:
        unused = [item for item in pool if not item.get("used", False)]
        if not unused:
            for item in pool:
                item["used"] = False
            unused = pool
        chosen_meta = unused[0]

    max_dur = args.max_duration
    font_path = find_bold_font()

    with tempfile.TemporaryDirectory(prefix="real_mix_build_") as tmp_s:
        tmp_dir = Path(tmp_s)
        bg_jpg = tmp_dir / "bg_1920x1080.jpg"
        bg_loop_mp4 = tmp_dir / "loop_1920x1080.mp4"
        hud_png = tmp_dir / "hud_1920x1080.png"
        mixed_m4a = tmp_dir / "real_mix.m4a"
        first_mp3 = tmp_dir / "first_track.m4a"
        medley_dir = tmp_dir / "medley_tracks"
        medley_dir.mkdir(parents=True, exist_ok=True)

        formatted_ts, actual_dur, medley_files = download_and_mix_real_tracks(
            chosen_meta["tracks"],
            mixed_m4a,
            first_mp3,
            max_total_duration_sec=max_dur,
            medley_out_dir=medley_dir,
        )

        download_background_image(chosen_meta, bg_jpg)
        build_highway_driving_loop_mp4(bg_jpg, chosen_meta, bg_loop_mp4, fps=24)
        render_16x9_hud_and_thumb(bg_jpg, chosen_meta, hud_png, OUTPUT_THUMB, font_path)
        decorate_hud_and_thumb_with_setlist(hud_png, OUTPUT_THUMB, chosen_meta["tracks"], font_path)

        build_1hour_video(bg_loop_mp4, hud_png, mixed_m4a, OUTPUT_1HOUR, duration_sec=int(actual_dur))
        build_short_video(bg_jpg, bg_loop_mp4, first_mp3, chosen_meta, OUTPUT_SHORT, font_path)
        build_short_medley_video(
            bg_loop_mp4,
            mixed_m4a,
            chosen_meta,
            OUTPUT_SHORT_MEDLEY,
            font_path,
            medley_audio_files=medley_files,
        )

    full_desc = build_real_hits_description(chosen_meta, formatted_ts)
    long_title = chosen_meta["title"]
    short_title = chosen_meta["short_title"]
    tr_med = chosen_meta["tracks"][1:4] if len(chosen_meta["tracks"]) >= 4 else chosen_meta["tracks"][:3]
    med_names = " / ".join(t["artist"] for t in tr_med)
    medley_short_title = f"【洋楽神曲3連発】{med_names}｜イントロで鳥肌が立つ80s-90s名曲メドレー 🎧本編2時間は関連動画へ #Shorts"[:100]

    if args.dry_run:
        logger.info(
            f"Dry-run complete! Main: {OUTPUT_1HOUR} ({actual_dur/60:.1f}m), Short A: {OUTPUT_SHORT}, Short C: {OUTPUT_SHORT_MEDLEY}"
        )
        logger.info(f"Timestamps:\n{formatted_ts}")
        return 0

    publish_at_short_a = None if args.publish_now else compute_music_golden_time_iso(20, 0)
    publish_at_long = None if args.publish_now else compute_music_golden_time_iso(20, 30)
    publish_at_short_c = None if args.publish_now else compute_music_golden_time_iso(21, 0)

    try:
        youtube = get_youtube_service()
        long_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_1HOUR,
            title=long_title,
            description=full_desc,
            tags=chosen_meta["tags"],
            privacy_status=args.privacy,
            thumbnail_path=OUTPUT_THUMB,
            publish_at_iso=publish_at_long,
        )
        short_desc = f"🎧 本編2時間フルメドレー動画（全24曲フル尺）はこちら 👉 https://youtu.be/{long_id}\n\n{full_desc}"
        short_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_SHORT,
            title=short_title,
            description=short_desc,
            tags=chosen_meta["tags"] + ["Shorts", "YouTubeShorts"],
            privacy_status=args.privacy,
            thumbnail_path=None,
            publish_at_iso=publish_at_short_a,
        )
        short_medley_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_SHORT_MEDLEY,
            title=medley_short_title,
            description=short_desc,
            tags=chosen_meta["tags"] + ["Shorts", "YouTubeShorts", "洋楽メドレー"],
            privacy_status=args.privacy,
            thumbnail_path=None,
            publish_at_iso=publish_at_short_c,
        )
    except Exception as exc:
        logger.warning(f"Upload deferred ({exc}).")
        raise

    for item in pool:
        if item["id"] == chosen_meta["id"]:
            item["used"] = True
            item["published_at"] = datetime.now(timezone.utc).isoformat()
            item["youtube_long_id"] = long_id
            item["youtube_short_id"] = short_id
            item["youtube_short_medley_id"] = short_medley_id
            break
    save_real_hits_pool(pool, chosen_meta["id"], auto_git_push=True)
    logger.info(
        f"Published 2-Hour Full-Length 24-Track Real Hits Mix [{chosen_meta['id']}]: Long={long_id}, ShortA={short_id}, ShortC={short_medley_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
