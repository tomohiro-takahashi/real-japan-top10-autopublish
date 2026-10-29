#!/usr/bin/env python3
"""
real_hits_mix_builder.py
========================
Builds and uploads Full-Length "Real 80s/90s Western Legend 12-Track Hit Mixes" (起爆剤モード)
for `MIDNIGHT COCKPIT / あの頃の夜と音楽`.
- Zero Suno credits required! Can run on its own independent schedule (e.g. 2x/day).
- Features 12 distinct situational/instrument angles ("夜に聴く", "ピアノが落ち着く", "サックスが沁みる",
  "アコギが心地よい", "雨の夜", "仕事帰りドライブ", "六本木ディスコ", "ハイウェイロック", "休日の朝珈琲",
  "90sメガヒット", "泣きのギターバラード", "深夜2時のアーバンメロウ") × 12 full-length songs each (~52-60 minutes)!
- Renders a 2-column 12-track Setlist card directly onto the 1080p video HUD (`hud_png`).
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
    OUTPUT_THUMB,
    _draw_soft_shadow_text,
    build_1hour_video,
    build_highway_driving_loop_mp4,
    build_short_video,
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
    # 01: 夜に聴く・週末のリラックスAOR
    {
        "id": "real_mix_001",
        "used": False,
        "genre": "80s City Pop & Sax AOR",
        "artwork_file": "citypop80s.jpg",
        "title": "【夜に聴きたい洋楽】疲れた夜に心がほどける80年代AOR＆名曲バラード全12曲フルメドレー｜Bobby Caldwell / Boz Scaggs / Chicago / Toto",
        "short_title": "【夜に聴きたい洋楽】疲れた夜に心がほどける80年代AOR＆名曲バラード全12曲 🎧本編はチャンネルへ！ #Shorts #80s洋楽",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  NIGHT RELAX AOR — FULL 12 SONGS",
        "thumb_catch": "一日の終わりに、あの頃の優しい洋楽が心を解きほぐす——",
        "thumb_main": "夜に聴きたい大人の洋楽AOR 12選",
        "thumb_sub": "Bobby Caldwell / Boz Scaggs / Chicago / Toto / Billy Joel 他 全12曲フル尺",
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
        ],
        "tags": ["夜に聴きたい洋楽", "80年代洋楽", "AOR", "洋楽メドレー", "40代", "50代", "Bobby Caldwell", "Boz Scaggs", "Chicago", "Toto", "懐かしい洋楽", "洋楽バラード", "夜のドライブBGM", "作業用BGM"],
    },
    # 02: ピアノが落ち着く・静かな夜の洋楽ピアノバラード
    {
        "id": "real_mix_002",
        "used": False,
        "genre": "90s Urban Mellow & Shibuya Groove",
        "artwork_file": "urban90s.jpg",
        "title": "【ピアノが落ち着く洋楽】静かな夜に聴きたい80年代・90年代ピアノ名曲バラード全12曲フルメドレー｜Billy Joel / Elton John / Chicago / Journey",
        "short_title": "【ピアノが落ち着く洋楽】静かな夜に聴きたい80s-90sピアノ名曲バラード全12曲 🎧本編はチャンネルへ！ #Shorts #80s洋楽",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  MELLOW PIANO BALLADS — FULL 12 SONGS",
        "thumb_catch": "美しいピアノのイントロだけで、あの頃の記憶がよみがえる——",
        "thumb_main": "ピアノが落ち着く洋楽バラード12選",
        "thumb_sub": "Billy Joel / Elton John / Chicago / Journey / Carpenters 他 全12曲フル尺",
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
        ],
        "tags": ["ピアノが落ち着く", "洋楽バラード", "80年代洋楽", "Billy Joel", "Honesty", "Elton John", "Chicago", "Journey", "Carpenters", "40代", "50代", "夜に聴きたい洋楽", "作業用BGM", "睡眠用BGM"],
    },
    # 03: サックスが沁みる・ウイスキー片手に聴く深夜バー
    {
        "id": "real_mix_003",
        "used": False,
        "genre": "80s City Pop & Sax AOR",
        "artwork_file": "citypop80s.jpg",
        "title": "【サックスが沁みる夜】ウイスキー片手に聴きたい80s-90s洋楽サックス＆AOR名曲全12曲フルメドレー｜Wham! / Sade / Grover Washington Jr.",
        "short_title": "【サックスが沁みる夜】ウイスキー片手に聴きたい80s-90s洋楽名曲全12曲 🎧本編はチャンネルへ！ #Shorts #AOR",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  MIDNIGHT SAXOPHONE & AOR — FULL 12 SONGS",
        "thumb_catch": "琥珀色のグラスと、夜の静寂に響くむせび泣くサックス——",
        "thumb_main": "サックスが沁みる夜の洋楽12選",
        "thumb_sub": "Wham! / Sade / Grover Washington Jr. / Glenn Frey / Kenny G 他 全12曲フル尺",
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
        ],
        "tags": ["サックス", "夜に聴きたい洋楽", "80年代洋楽", "AOR", "Careless Whisper", "Sade", "ウイスキーに合う曲", "40代", "50代", "大人BGM", "バーBGM", "作業用BGM"],
    },
    # 04: アコギが心地よい・休日の午後＆夕暮れソフトロック
    {
        "id": "real_mix_004",
        "used": False,
        "genre": "90s Urban Mellow & Shibuya Groove",
        "artwork_file": "urban90s.jpg",
        "title": "【アコギが心地よい洋楽】休日の午後や夕暮れに聴きたいアコースティック＆ソフトロック名曲全12曲フルメドレー｜Eric Clapton / America / Extreme",
        "short_title": "【アコギが心地よい洋楽】休日の夕暮れに聴きたいアコースティック名曲全12曲 🎧本編はチャンネルへ！ #Shorts #洋楽",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  ACOUSTIC & SOFT ROCK — FULL 12 SONGS",
        "thumb_catch": "優しいアコースティックギターの弦音が、心を穏やかに整える——",
        "thumb_main": "アコギが心地よい大人の洋楽12選",
        "thumb_sub": "Eric Clapton / Extreme / America / Kansas / Bread / James Taylor 他 全12曲",
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
        ],
        "tags": ["アコギ", "アコースティック", "ソフトロック", "80年代洋楽", "90年代洋楽", "Eric Clapton", "More Than Words", "40代", "50代", "休日BGM", "カフェBGM", "作業用BGM"],
    },
    # 05: 雨の夜に聴きたい・心を癒やすスローバラード
    {
        "id": "real_mix_005",
        "used": False,
        "genre": "90s Urban Mellow & Shibuya Groove",
        "artwork_file": "urban90s.jpg",
        "title": "【雨の夜に聴きたい洋楽】窓を打つ雨音と聴く80年代・90年代スローバラード名曲全12曲フルメドレー｜Cyndi Lauper / Whitney Houston / Air Supply",
        "short_title": "【雨の夜に聴きたい洋楽】心にしみる80s-90sスローバラード名曲全12曲 🎧本編はチャンネルへ！ #Shorts #洋楽バラード",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  RAINY NIGHT BALLADS — FULL 12 SONGS",
        "thumb_catch": "静かな雨の夜、あの頃の甘いラブバラードに身を委ねる——",
        "thumb_main": "雨の夜に聴きたい洋楽バラード12選",
        "thumb_sub": "Cyndi Lauper / Whitney Houston / Air Supply / Atlantic Starr 他 全12曲",
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
        ],
        "tags": ["雨の夜に聴きたい", "洋楽バラード", "80年代洋楽", "90年代洋楽", "Cyndi Lauper", "Whitney Houston", "Air Supply", "40代", "50代", "睡眠用BGM", "リラックスBGM"],
    },
    # 06: 仕事帰りの夜間ドライブ・ウエストコーストAOR
    {
        "id": "real_mix_006",
        "used": False,
        "genre": "80s City Pop & Sax AOR",
        "artwork_file": "citypop80s.jpg",
        "title": "【夜のドライブ洋楽】仕事帰りの車内で聴きたい80年代ウエストコーストAOR＆ソフトロック全12曲フルメドレー｜Toto / Steely Dan / Doobie Brothers",
        "short_title": "【夜のドライブ洋楽】仕事帰りに聴きたい80年代ウエストコーストAOR全12曲 🎧本編はチャンネルへ！ #Shorts #AOR",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  WEST COAST NIGHT DRIVE AOR — FULL 12 SONGS",
        "thumb_catch": "テールランプが流れる夜の湾岸線、極上のAORグルーヴ——",
        "thumb_main": "夜のドライブで聴きたい洋楽AOR 12選",
        "thumb_sub": "Toto / Steely Dan / Doobie Brothers / Hall & Oates / Ned Doheny 他 全12曲",
        "tracks": [
            {"artist": "Toto", "title": "Georgy Porgy", "ja_title": "ジョージー・ポージー", "query": "Toto Georgy Porgy official audio"},
            {"artist": "Steely Dan", "title": "Peg", "ja_title": "ペグ", "query": "Steely Dan Peg official audio"},
            {"artist": "The Doobie Brothers", "title": "What a Fool Believes", "ja_title": "ホワット・ア・フール・ビリーヴス", "query": "Doobie Brothers What a Fool Believes official audio"},
            {"artist": "Hall & Oates", "title": "I Can't Go for That (No Can Do)", "ja_title": "アイ・キャント・ゴー・フォー・ザット", "query": "Hall and Oates I Can't Go for That official audio"},
            {"artist": "Michael McDonald", "title": "I Keep Forgettin'", "ja_title": "アイ・キープ・フォゲッティン", "query": "Michael McDonald I Keep Forgettin official audio"},
            {"artist": "Ned Doheny", "title": "Get It Up for Love", "ja_title": "ゲット・イット・アップ・フォー・ラヴ", "query": "Ned Doheny Get It Up for Love official audio"},
            {"artist": "Player", "title": "Baby Come Back", "ja_title": "ベイビー・カム・バック", "query": "Player Baby Come Back official audio"},
            {"artist": "Ambrosia", "title": "Biggest Part of Me", "ja_title": "ビゲスト・パート・オブ・ミー", "query": "Ambrosia Biggest Part of Me official audio"},
            {"artist": "Rupert Holmes", "title": "Escape (The Pina Colada Song)", "ja_title": "エスケイプ", "query": "Rupert Holmes Escape The Pina Colada Song official audio"},
            {"artist": "Christopher Cross", "title": "Ride Like the Wind", "ja_title": "風立ちぬ", "query": "Christopher Cross Ride Like the Wind official audio"},
            {"artist": "Boz Scaggs", "title": "Lowdown", "ja_title": "ロウダウン", "query": "Boz Scaggs Lowdown official audio"},
            {"artist": "Steely Dan", "title": "Hey Nineteen", "ja_title": "ヘイ・ナインティーン", "query": "Steely Dan Hey Nineteen official audio"},
        ],
        "tags": ["夜のドライブBGM", "AOR", "ウエストコースト", "80年代洋楽", "Toto", "Steely Dan", "Doobie Brothers", "40代", "50代", "車内BGM", "作業用BGM"],
    },
    # 07: バブル期の六本木・マハラジャ80sディスコ
    {
        "id": "real_mix_007",
        "used": False,
        "genre": "80s Japanese Boogie Disco",
        "artwork_file": "disco.jpg",
        "title": "【バブル世代必見】イントロで六本木が蘇る！80年代ディスコ洋楽ヒット曲全12曲ノンストップフルメドレー｜Earth, Wind & Fire / Boys Town Gang 他",
        "short_title": "【バブル世代必見】イントロで六本木が蘇る！80年代ディスコ洋楽全12曲メドレー 🎧本編はチャンネルへ！ #Shorts #80sディスコ",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  1980s ROPPONGI DISCO — FULL 12 SONGS",
        "thumb_catch": "ミラーボールの輝きと、あの頃の週末の熱狂がよみがえる——",
        "thumb_main": "80年代 六本木ディスコ洋楽12選",
        "thumb_sub": "Earth, Wind & Fire / Boys Town Gang / Dead Or Alive / Bananarama 他 全12曲",
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
        ],
        "tags": ["80年代ディスコ", "80年代洋楽", "バブル世代", "マハラジャ", "六本木ディスコ", "40代", "50代", "Earth Wind and Fire", "君の瞳に恋してる", "洋楽メドレー", "ドライブBGM", "作業用BGM"],
    },
    # 08: 夜の高速道路・80sハイウェイ＆映画主題歌ロック
    {
        "id": "real_mix_008",
        "used": False,
        "genre": "90s Eurobeat",
        "artwork_file": "eurobeat.jpg",
        "title": "【40代・50代必見】夜の高速道路で聴いた80年代洋楽ロック＆映画主題歌全12曲フルメドレー｜Kenny Loggins / Journey / Bon Jovi / Van Halen",
        "short_title": "【40代・50代必見】夜の高速道路で聴いた80年代洋楽ロック全12曲メドレー 🎧本編はチャンネルへ！ #Shorts #80s洋楽",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  1980s HIGHWAY ROCK — FULL 12 SONGS",
        "thumb_catch": "アクセルを踏み込んだ瞬間、あの頃のハイウェイが蘇る——",
        "thumb_main": "80年代 夜のハイウェイ洋楽ロック12選",
        "thumb_sub": "Kenny Loggins / Journey / Bon Jovi / Van Halen / Survivor 他 全12曲",
        "tracks": [
            {"artist": "Kenny Loggins", "title": "Danger Zone", "ja_title": "デンジャー・ゾーン (トップガン)", "query": "Kenny Loggins Danger Zone official audio"},
            {"artist": "Journey", "title": "Separate Ways (Worlds Apart)", "ja_title": "セパレイト・ウェイズ", "query": "Journey Separate Ways Worlds Apart official audio"},
            {"artist": "Bon Jovi", "title": "Livin' on a Prayer", "ja_title": "リヴィン・オン・ア・プレイヤー", "query": "Bon Jovi Livin on a Prayer official audio"},
            {"artist": "Van Halen", "title": "Jump", "ja_title": "ジャンプ", "query": "Van Halen Jump official audio"},
            {"artist": "Survivor", "title": "Eye of the Tiger", "ja_title": "アイ・オブ・ザ・タイガー (ロッキー3)", "query": "Survivor Eye of the Tiger official audio"},
            {"artist": "Europe", "title": "The Final Countdown", "ja_title": "ファイナル・カウントダウン", "query": "Europe The Final Countdown official audio"},
            {"artist": "Journey", "title": "Don't Stop Believin'", "ja_title": "ドント・ストップ・ビリーヴィン", "query": "Journey Don't Stop Believin official audio"},
            {"artist": "Starship", "title": "Nothing's Gonna Stop Us Now", "ja_title": "愛はとまらない", "query": "Starship Nothing's Gonna Stop Us Now official audio"},
            {"artist": "Bryan Adams", "title": "Summer of '69", "ja_title": "想い出のサマー", "query": "Bryan Adams Summer of 69 official audio"},
            {"artist": "Huey Lewis & The News", "title": "The Power of Love", "ja_title": "パワー・オブ・ラヴ (BTTF)", "query": "Huey Lewis and the News The Power of Love official audio"},
            {"artist": "Kenny Loggins", "title": "Footloose", "ja_title": "フットルース", "query": "Kenny Loggins Footloose official audio"},
            {"artist": "Berlin", "title": "Take My Breath Away", "ja_title": "愛は吐息のように (トップガン)", "query": "Berlin Take My Breath Away official audio"},
        ],
        "tags": ["80年代洋楽", "洋楽ロック", "ドライブBGM", "トップガン", "Journey", "Bon Jovi", "Van Halen", "40代", "50代", "懐かしい洋楽", "高速道路BGM", "作業用BGM"],
    },
    # 09: 休日の朝・珈琲の香りと聴く優しい70s-80s洋楽ポップス
    {
        "id": "real_mix_009",
        "used": False,
        "genre": "80s City Pop & Sax AOR",
        "artwork_file": "citypop80s.jpg",
        "title": "【休日に聴きたい洋楽】珈琲の香りと聴く70年代・80年代の優しい洋楽ポップス名曲全12曲フルメドレー｜Carpenters / Billy Joel / Bee Gees",
        "short_title": "【休日に聴きたい洋楽】珈琲と聴く70s-80s優しい洋楽ポップス全12曲 🎧本編はチャンネルへ！ #Shorts #懐かしの洋楽",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  WEEKEND COFFEE & GENTLE POP — FULL 12 SONGS",
        "thumb_catch": "穏やかな休日のひとときに、時代を超えて愛される優しい歌声を——",
        "thumb_main": "珈琲と聴く優しい洋楽ポップス12選",
        "thumb_sub": "Carpenters / Gilbert O'Sullivan / Billy Joel / Bee Gees / ABBA 他 全12曲",
        "tracks": [
            {"artist": "Carpenters", "title": "Yesterday Once More", "ja_title": "イエスタデイ・ワンス・モア", "query": "Carpenters Yesterday Once More official audio"},
            {"artist": "Gilbert O'Sullivan", "title": "Alone Again (Naturally)", "ja_title": "アローン・アゲイン", "query": "Gilbert O'Sullivan Alone Again Naturally official audio"},
            {"artist": "Carpenters", "title": "Close to You", "ja_title": "遙かなる影", "query": "Carpenters Close to You official audio"},
            {"artist": "Bee Gees", "title": "How Deep Is Your Love", "ja_title": "愛はきらめきの中に", "query": "Bee Gees How Deep Is Your Love official audio"},
            {"artist": "Billy Joel", "title": "She's Always a Woman", "ja_title": "シーズ・オールウェイズ・ア・ウーマン", "query": "Billy Joel She's Always a Woman official audio"},
            {"artist": "Olivia Newton-John", "title": "Have You Never Been Mellow", "ja_title": "そよ風の誘惑", "query": "Olivia Newton-John Have You Never Been Mellow official audio"},
            {"artist": "ABBA", "title": "Chiquitita", "ja_title": "チキチータ", "query": "ABBA Chiquitita official audio"},
            {"artist": "The Nolans", "title": "I'm in the Mood for Dancing", "ja_title": "ダンシング・シスター", "query": "The Nolans I'm in the Mood for Dancing official audio"},
            {"artist": "Stevie Wonder", "title": "I Just Called to Say I Love You", "ja_title": "心の愛", "query": "Stevie Wonder I Just Called to Say I Love You official audio"},
            {"artist": "10cc", "title": "I'm Not in Love", "ja_title": "アイム・ノット・イン・ラヴ", "query": "10cc I'm Not in Love official audio"},
            {"artist": "Albert Hammond", "title": "It Never Rains in Southern California", "ja_title": "カリフォルニアの青い空", "query": "Albert Hammond It Never Rains in Southern California official audio"},
            {"artist": "Carpenters", "title": "Top of the World", "ja_title": "トップ・オブ・ザ・ワールド", "query": "Carpenters Top of the World official audio"},
        ],
        "tags": ["Carpenters", "70年代洋楽", "80年代洋楽", "休日BGM", "カフェBGM", "40代", "50代", "懐かしい洋楽", "優しい洋楽", "作業用BGM"],
    },
    # 10: 90年代青春の洋楽メガヒット・タワレコ＆FM世代
    {
        "id": "real_mix_010",
        "used": False,
        "genre": "90s TK Rave & Synth Dance",
        "artwork_file": "tkrave.jpg",
        "title": "【90年代洋楽メドレー】青春時代にCDが擦り切れるほど聴いた90s洋楽メガヒット全12曲フルメドレー｜Oasis / Aerosmith / Backstreet Boys / Celine Dion",
        "short_title": "【90年代洋楽メドレー】CDが擦り切れるほど聴いた90s洋楽メガヒット全12曲 🎧本編はチャンネルへ！ #Shorts #90s洋楽",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  1990s MEGA HITS ARCHIVE — FULL 12 SONGS",
        "thumb_catch": "タワレコで試聴して買った、あの90年代の輝きが蘇る——",
        "thumb_main": "90年代 青春の洋楽メガヒット12選",
        "thumb_sub": "Oasis / Aerosmith / Backstreet Boys / Celine Dion / Eric Clapton 他 全12曲",
        "tracks": [
            {"artist": "Aerosmith", "title": "I Don't Want to Miss a Thing", "ja_title": "ミス・ア・シング (アルマゲドン)", "query": "Aerosmith I Don't Want to Miss a Thing official audio"},
            {"artist": "Oasis", "title": "Don't Look Back in Anger", "ja_title": "ドント・ルック・バック・イン・アンガー", "query": "Oasis Don't Look Back in Anger official audio"},
            {"artist": "Backstreet Boys", "title": "I Want It That Way", "ja_title": "アイ・ウォント・イット・ザット・ウェイ", "query": "Backstreet Boys I Want It That Way official audio"},
            {"artist": "Celine Dion", "title": "My Heart Will Go On", "ja_title": "マイ・ハート・ウィル・ゴー・オン (タイタニック)", "query": "Celine Dion My Heart Will Go On official audio"},
            {"artist": "Eric Clapton", "title": "Change the World", "ja_title": "チェンジ・ザ・ワールド", "query": "Eric Clapton Change the World official audio"},
            {"artist": "Jamiroquai", "title": "Virtual Insanity", "ja_title": "ヴァーチャル・インサニティ", "query": "Jamiroquai Virtual Insanity official audio"},
            {"artist": "Sheryl Crow", "title": "If It Makes You Happy", "ja_title": "イフ・イット・メイクス・ユー・ハッピー", "query": "Sheryl Crow If It Makes You Happy official audio"},
            {"artist": "Des'ree", "title": "You Gotta Be", "ja_title": "ユー・ガッタ・ビー", "query": "Des'ree You Gotta Be official audio"},
            {"artist": "Shanice", "title": "I Love Your Smile", "ja_title": "アイ・ラヴ・ユア・スマイル", "query": "Shanice I Love Your Smile official audio"},
            {"artist": "Simply Red", "title": "Stars", "ja_title": "スターズ", "query": "Simply Red Stars official audio"},
            {"artist": "Bryan Adams", "title": "(Everything I Do) I Do It for You", "ja_title": "アイ・ドゥ・イット・フォー・ユー", "query": "Bryan Adams Everything I Do I Do It for You official audio"},
            {"artist": "Oasis", "title": "Wonderwall", "ja_title": "ワンダーウォール", "query": "Oasis Wonderwall official audio"},
        ],
        "tags": ["90年代洋楽", "90s洋楽", "Oasis", "Aerosmith", "Backstreet Boys", "Jamiroquai", "40代", "50代", "青春の洋楽", "洋楽メドレー", "作業用BGM", "ドライブBGM"],
    },
    # 11: 泣きのギターソロ・夜更けのロックバラード
    {
        "id": "real_mix_011",
        "used": False,
        "genre": "90s Eurobeat",
        "artwork_file": "eurobeat.jpg",
        "title": "【泣きのギターバラード】夜更けに聴きたい80年代・90年代洋楽ロックバラード名曲全12曲フルメドレー｜Journey / Scorpions / Bon Jovi / Whitesnake",
        "short_title": "【泣きのギターバラード】夜更けに聴きたい80s-90s洋楽ロックバラード全12曲 🎧本編はチャンネルへ！ #Shorts #洋楽ロック",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  EMOTIONAL GUITAR ROCK BALLADS — FULL 12 SONGS",
        "thumb_catch": "魂を揺さぶる泣きのギターソロと、胸を締めつけるメロディ——",
        "thumb_main": "夜更けの洋楽ロックバラード12選",
        "thumb_sub": "Journey / Scorpions / Bon Jovi / Whitesnake / Guns N' Roses 他 全12曲",
        "tracks": [
            {"artist": "Journey", "title": "Faithfully", "ja_title": "時への誓い", "query": "Journey Faithfully official audio"},
            {"artist": "Bon Jovi", "title": "Always", "ja_title": "オールウェイズ", "query": "Bon Jovi Always official audio"},
            {"artist": "Scorpions", "title": "Wind of Change", "ja_title": "ウィンド・オブ・チェンジ", "query": "Scorpions Wind of Change official audio"},
            {"artist": "Foreigner", "title": "I Want to Know What Love Is", "ja_title": "アイ・ウォント・トゥ・ノウ・ホワット・ラヴ・イズ", "query": "Foreigner I Want to Know What Love Is official audio"},
            {"artist": "REO Speedwagon", "title": "Can't Fight This Feeling", "ja_title": "涙のフィーリング", "query": "REO Speedwagon Can't Fight This Feeling official audio"},
            {"artist": "Whitesnake", "title": "Is This Love", "ja_title": "イズ・ディス・ラヴ", "query": "Whitesnake Is This Love official audio"},
            {"artist": "Cheap Trick", "title": "The Flame", "ja_title": "永遠の愛の炎", "query": "Cheap Trick The Flame official audio"},
            {"artist": "Sheriff", "title": "When I'm with You", "ja_title": "ホエン・アイム・ウィズ・ユー", "query": "Sheriff When I'm with You official audio"},
            {"artist": "Heart", "title": "Alone", "ja_title": "アローン", "query": "Heart Alone official audio"},
            {"artist": "Night Ranger", "title": "Sister Christian", "ja_title": "シスター・クリスチャン", "query": "Night Ranger Sister Christian official audio"},
            {"artist": "Poison", "title": "Every Rose Has Its Thorn", "ja_title": "エヴリ・ローズ・ハズ・イッツ・ソーン", "query": "Poison Every Rose Has Its Thorn official audio"},
            {"artist": "Gary Moore", "title": "Still Got the Blues", "ja_title": "スティル・ゴット・ザ・ブルーズ", "query": "Gary Moore Still Got the Blues official audio"},
        ],
        "tags": ["ロックバラード", "ギターソロ", "80年代洋楽", "90年代洋楽", "Journey", "Bon Jovi", "Gary Moore", "40代", "50代", "夜に聴きたい洋楽", "ドライブBGM"],
    },
    # 12: 眠れない深夜2時・極上のアーバンメロウ＆ブラコン
    {
        "id": "real_mix_012",
        "used": False,
        "genre": "90s Urban Mellow & Shibuya Groove",
        "artwork_file": "urban90s.jpg",
        "title": "【深夜2時の洋楽】眠れない夜に心を包む80s-90sアーバンメロウ＆ブラコン名曲全12曲フルメドレー｜Anita Baker / Babyface / Sade / Luther Vandross",
        "short_title": "【深夜2時の洋楽】眠れない夜に聴きたい80s-90sアーバンメロウ名曲全12曲 🎧本編はチャンネルへ！ #Shorts #AOR",
        "thumb_era_label": "40代・50代に捧ぐ  ｜  2AM URBAN MELLOW & QUIET STORM — FULL 12 SONGS",
        "thumb_catch": "午前2時の静寂に溶ける、甘く洗練された大人のR&BとAOR——",
        "thumb_main": "深夜2時に聴きたいアーバン洋楽12選",
        "thumb_sub": "Anita Baker / Babyface / Sade / Luther Vandross / Earth, Wind & Fire 他 全12曲",
        "tracks": [
            {"artist": "Anita Baker", "title": "Sweet Love", "ja_title": "スウィート・ラヴ", "query": "Anita Baker Sweet Love official audio"},
            {"artist": "Sade", "title": "Kiss of Life", "ja_title": "キス・オブ・ライフ", "query": "Sade Kiss of Life official audio"},
            {"artist": "Luther Vandross", "title": "Never Too Much", "ja_title": "ネヴァー・トゥー・マッチ", "query": "Luther Vandross Never Too Much official audio"},
            {"artist": "Earth, Wind & Fire", "title": "After the Love Has Gone", "ja_title": "アフター・ザ・ラヴ・ハズ・ゴーン", "query": "Earth Wind and Fire After the Love Has Gone official audio"},
            {"artist": "Babyface", "title": "Every Time I Close My Eyes", "ja_title": "エヴリ・タイム・アイ・クローズ・マイ・アイズ", "query": "Babyface Every Time I Close My Eyes official audio"},
            {"artist": "Commodores", "title": "Easy", "ja_title": "イージー", "query": "Commodores Easy official audio"},
            {"artist": "The Isley Brothers", "title": "Between the Sheets", "ja_title": "ビトウィーン・ザ・シーツ", "query": "Isley Brothers Between the Sheets official audio"},
            {"artist": "Kool & The Gang", "title": "Cherish", "ja_title": "チェリッシュ", "query": "Kool and the Gang Cherish official audio"},
            {"artist": "Champaign", "title": "How 'Bout Us", "ja_title": "ハウ・バウト・アス", "query": "Champaign How Bout Us official audio"},
            {"artist": "Surface", "title": "Shower Me with Your Love", "ja_title": "シャワー・ミー・ウィズ・ユア・ラヴ", "query": "Surface Shower Me with Your Love official audio"},
            {"artist": "Karyn White", "title": "Superwoman", "ja_title": "スーパーウーマン", "query": "Karyn White Superwoman official audio"},
            {"artist": "swing Out Sister", "title": "Breakout", "ja_title": "ブレイクアウト", "query": "Swing Out Sister Breakout official audio"},
        ],
        "tags": ["深夜BGM", "ブラコン", "AOR", "80年代洋楽", "90年代洋楽", "Anita Baker", "Sade", "Babyface", "40代", "50代", "眠れない夜に", "大人BGM"],
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
    if len(items) < len(DEFAULT_REAL_HIT_MIXES):
        existing_used = {it["id"]: it for it in items if it.get("used")}
        merged: List[Dict[str, Any]] = []
        for d_item in DEFAULT_REAL_HIT_MIXES:
            if d_item["id"] in existing_used:
                merged.append(existing_used[d_item["id"]])
            else:
                merged.append(d_item)
        REAL_HITS_POOL_PATH.write_text(
            json.dumps({"total": len(merged), "items": merged}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return merged
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
                ["git", "commit", "-m", f"chore(music): mark {chosen_id} as published in real_hits_pool.json [skip ci]"],
                check=True,
            )
            subprocess.run(["git", "pull", "--rebase", "--autostash", "origin", "main"], check=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
            logger.info("Committed and pushed updated real_hits_pool.json to GitHub.")
        except Exception as exc:
            logger.warning(f"Git commit/push warning: {exc}")


def download_and_mix_real_tracks(
    tracks: List[Dict[str, str]],
    out_m4a: Path,
    out_mp3_for_short: Path,
    max_total_duration_sec: int = 4200,
) -> Tuple[str, float]:
    """
    Download all 12 tracks via `yt-dlp` at full length (up to 480s per track so full songs play completely!),
    normalize loudness (`loudnorm`), apply smooth 2.5s fade-in/out per track, concatenate into `out_m4a`,
    and return `(formatted_timestamps, actual_duration)`.
    """
    import yt_dlp

    per_track_max = 480 if max_total_duration_sec >= 1800 else int((max_total_duration_sec - 5) / max(1, len(tracks)))

    with tempfile.TemporaryDirectory(prefix="real_hits_dl_") as tmp_s:
        tmp_dir = Path(tmp_s)
        norm_segments: List[Path] = []
        timestamp_lines: List[str] = []
        cursor_sec = 0.0

        for idx, tr in enumerate(tracks, start=1):
            query = tr["query"]
            raw_out_tmpl = str(tmp_dir / f"raw_{idx:02d}.%(ext)s")
            logger.info(f"[{idx}/{len(tracks)}] Downloading Full Track via yt-dlp: {tr['artist']} - {tr['title']} ...")
            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "outtmpl": raw_out_tmpl,
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch1:{query}"])

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
            mm = int(cursor_sec) // 60
            ss = int(cursor_sec) % 60
            timestamp_lines.append(
                f"{mm:02d}:{ss:02d} {idx:02d}. {tr['artist']} — {tr['title']} （{tr['ja_title']}）"
            )
            cursor_sec += actual_seg_dur
            norm_segments.append(norm_m4a)

            if idx == 1:
                shutil.copy2(norm_m4a, out_mp3_for_short)

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
    logger.info(f"Built Full-Length 12-Track Real Hits Mix audio: {out_m4a.name} ({total_dur:.1f}s / {total_dur/60:.1f}m across {len(tracks)} tracks)")
    return "\n".join(timestamp_lines), total_dur


def decorate_hud_and_thumb_with_setlist(
    hud_png: Path,
    thumb_jpg: Path,
    tracks: List[Dict[str, str]],
    font_path: str,
) -> None:
    """
    Overlay a sleek 2-column 12-track SETLIST card onto `hud_png` (1920x1080) and replace the `NO ADS` pill
    with `FULL 12 SONGS MIX` so viewers immediately see all 12 famous artist & song names on screen.
    """
    cjk_reg_path = find_cjk_font() or font_path
    cjk_mincho_path = find_cjk_mincho_font() or cjk_reg_path

    hud = Image.open(hud_png).convert("RGBA")
    draw = ImageDraw.Draw(hud, "RGBA")

    lx0, ly0, lx1, ly1 = 72, 142, 1848, 492
    draw.rounded_rectangle(
        (lx0, ly0, lx1, ly1),
        radius=22,
        fill=(8, 12, 22, 176),
        outline=(217, 179, 108, 150),
        width=2,
    )
    f_head = load_font(cjk_reg_path, 22)
    draw.text(
        (lx0 + 28, ly0 + 16),
        f"♪ FULL-LENGTH {len(tracks)} TRACKS SETLIST  ｜  収録名曲リスト（概要欄チャプターから各曲へジャンプ可能）",
        font=f_head,
        fill=(217, 179, 108, 245),
    )
    draw.line([(lx0 + 28, ly0 + 50), (lx1 - 28, ly0 + 50)], fill=(217, 179, 108, 95), width=1)

    col_w = ((lx1 - lx0) - 84) // 2
    for idx, tr in enumerate(tracks[:12]):
        col = 0 if idx < 6 else 1
        row = idx % 6
        col_x = (lx0 + 28) if col == 0 else (lx0 + 48 + col_w)
        row_y = ly0 + 62 + row * 46
        line_txt = f"{idx+1:02d}. {tr['artist']} — {tr['title']} （{tr['ja_title']}）"
        f_row = fit_font_for_width(draw, line_txt, cjk_mincho_path, 22, 16, col_w - 10)
        _draw_soft_shadow_text(
            hud,
            (col_x, row_y),
            line_txt,
            font=f_row,
            fill=(250, 248, 242, 248),
            blur_radius=4,
        )

    # Replace bottom-right pill on HUD with "FULL 12 SONGS MIX"
    draw = ImageDraw.Draw(hud, "RGBA")
    stamp_txt = f"FULL {len(tracks)} SONGS MIX"
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
    tracks_summary = " / ".join([f"{t['artist']}「{t['title']}」" for t in meta["tracks"][:8]]) + " ほか全12曲フル尺収録"
    return (
        f"🎧 {meta['title']}\n\n"
        f"1980年代〜1990年代にFMラジオや夜のドライブ、ディスコ、カフェバーで流れていた本物の洋楽レジェンド名曲全12曲（{tracks_summary}）を、"
        "1曲ずつフル尺でじっくり聴けるノンストップ・メドレーでお届けします。\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏱️ 収録曲トラックリスト / チャプター (全12曲フル尺):\n"
        f"{formatted_timestamps}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🌙 途中に広告が入らない【広告なし】の深夜ドライブ・80s/90s AORプレイリストシリーズも\n"
        "👇 チャンネルトップから毎日公開中です！ぜひチャンネル登録してお楽しみください。\n"
        "https://www.youtube.com/@midnight_cockpit\n\n"
        "#80年代洋楽 #AOR #洋楽メドレー #40代 #50代 #懐かしい洋楽 #夜に聴きたい洋楽 #作業用BGM"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build & upload Full-Length Real 80s/90s Western Legend 12-Song Hit Mix.")
    parser.add_argument("--mix-id", default="", help="Specific mix id from real_hits_pool.json (default: first unused).")
    parser.add_argument("--max-duration", type=int, default=4200, help="Max total duration in seconds (default: 4200 = full length for all 12 songs).")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    parser.add_argument("--dry-run", action="store_true")
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

        formatted_ts, actual_dur = download_and_mix_real_tracks(
            chosen_meta["tracks"],
            mixed_m4a,
            first_mp3,
            max_total_duration_sec=max_dur,
        )

        download_background_image(chosen_meta, bg_jpg)
        build_highway_driving_loop_mp4(bg_jpg, chosen_meta, bg_loop_mp4, fps=24)
        render_16x9_hud_and_thumb(bg_jpg, chosen_meta, hud_png, OUTPUT_THUMB, font_path)
        decorate_hud_and_thumb_with_setlist(hud_png, OUTPUT_THUMB, chosen_meta["tracks"], font_path)

        build_1hour_video(bg_loop_mp4, hud_png, mixed_m4a, OUTPUT_1HOUR, duration_sec=int(actual_dur))
        build_short_video(bg_jpg, bg_loop_mp4, first_mp3, chosen_meta, OUTPUT_SHORT, font_path)

    full_desc = build_real_hits_description(chosen_meta, formatted_ts)
    long_title = chosen_meta["title"]
    short_title = chosen_meta["short_title"]

    if args.dry_run:
        logger.info(f"Dry-run complete! Main video: {OUTPUT_1HOUR} ({actual_dur/60:.1f}m), Short: {OUTPUT_SHORT}")
        logger.info(f"Timestamps:\n{formatted_ts}")
        return 0

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
        )
        short_desc = f"🎧 本編フルメドレー動画（全12曲フル尺）はこちら 👉 https://youtu.be/{long_id}\n\n{full_desc}"
        short_id = upload_video_to_youtube(
            youtube=youtube,
            video_path=OUTPUT_SHORT,
            title=short_title,
            description=short_desc,
            tags=chosen_meta["tags"] + ["Shorts", "YouTubeShorts"],
            privacy_status=args.privacy,
            thumbnail_path=None,
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
            break
    save_real_hits_pool(pool, chosen_meta["id"], auto_git_push=True)
    logger.info(f"Published Full-Length 12-Track Real Hits Mix [{chosen_meta['id']}]: Long={long_id}, Short={short_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
