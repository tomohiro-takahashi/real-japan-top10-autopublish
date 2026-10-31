#!/usr/bin/env python3
"""
build_world_history_cinema.py

Definitive Complete Edition (【完全保存版】フランス革命のすべて ― リアルな日常・図解・最新研究の諸説まで完全網羅)
- Combines 20 photorealistic 10-second Google Flow live-action cinema scenes (`scene_01.mp4` .. `scene_20.mp4`)
  featuring consistent registered characters (`Marie Antoinette`, `Louis XVI`, `Robespierre`, `Marguerite`).
- Inserts 6 museum-grade 1280x720 historical diagrams, budget charts, maps, and scholarly theory comparison tables
  (`diagram_01.png` .. `diagram_06.png`) as connecting analytical segments ("繋ぎ") between and within chapters.
- Total duration: ~11 to 13 minutes (7 comprehensive chapters covering every major event + 6 major scholarly debates/諸説).
"""

import asyncio
import math
import random
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
from PIL import Image, ImageDraw, ImageFont

from build_japan_ranking import (
    BASE_DIR,
    OUTPUT_DIR,
    draw_rounded_box,
    find_cjk_font,
    get_duration,
)
from build_history_thumbnail_proposals import build_proposal_D
from history_infographics import render_diagram_board, render_question_card

FLOW_DIR = BASE_DIR / "assets" / "flow_history_fr_rev"
DIAG_DIR = FLOW_DIR / "diagrams"
W, H = 1280, 720
SW, SH = 1080, 1920
FPS = 25
VOICE_NARRATOR = "ja-JP-KeitaNeural"


def fit_font_w(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: str,
    max_pt: int,
    min_pt: int,
    max_w: int,
) -> ImageFont.FreeTypeFont:
    for pt in range(max_pt, min_pt - 1, -1):
        f = ImageFont.truetype(font_path, pt)
        tb = draw.textbbox((0, 0), text, font=f)
        if (tb[2] - tb[0]) <= max_w:
            return f
    return ImageFont.truetype(font_path, min_pt)


def synthesize_history_se(se_kind: str, sr: int = 44100) -> List[float]:
    """Synthesize subtle cinematic historical sound effects at scene transitions."""
    if se_kind == "blade_glint":
        dur = 0.65
        n = int(sr * dur)
        return [
            0.38 * math.sin(2 * math.pi * 2480 * (i / sr)) * math.exp(-(i / sr) * 6.5)
            + 0.25 * math.sin(2 * math.pi * 3720 * (i / sr)) * math.exp(-(i / sr) * 9.0)
            + 0.45 * math.sin(2 * math.pi * (82.0 * math.exp(-(i / sr) * 3.0) + 42.0) * (i / sr)) * math.exp(-(i / sr) * 4.5)
            for i in range(n)
        ]
    elif se_kind == "question_sting":
        # Dramatic documentary "QUESTION" impact: deep timpani boom + suspense harpsichord minor chord
        dur = 0.90
        n = int(sr * dur)
        return [
            0.70 * math.sin(2 * math.pi * (88.0 * math.exp(-(i / sr) * 4.5) + 44.0) * (i / sr)) * math.exp(-(i / sr) * 3.8)
            + 0.26 * math.sin(2 * math.pi * 293.66 * (i / sr)) * math.exp(-(i / sr) * 3.5)
            + 0.22 * math.sin(2 * math.pi * 349.23 * (i / sr)) * math.exp(-(i / sr) * 3.8)
            + 0.20 * math.sin(2 * math.pi * 440.00 * (i / sr)) * math.exp(-(i / sr) * 4.0)
            + 0.14 * math.sin(2 * math.pi * 880.00 * (i / sr)) * math.exp(-(i / sr) * 7.5)
            for i in range(n)
        ]
    elif se_kind == "low_timpani":
        dur = 0.75
        n = int(sr * dur)
        return [
            0.60 * math.sin(2 * math.pi * (78.0 * math.exp(-(i / sr) * 4.0) + 46.0) * (i / sr)) * math.exp(-(i / sr) * 4.2)
            + 0.20 * math.sin(2 * math.pi * 145.0 * (i / sr)) * math.exp(-(i / sr) * 8.0)
            for i in range(n)
        ]
    elif se_kind == "cannon_boom":
        dur = 0.85
        n = int(sr * dur)
        rng = random.Random(1789)
        return [
            (
                0.65 * math.sin(2 * math.pi * (68.0 * math.exp(-(i / sr) * 3.5) + 36.0) * (i / sr))
                + 0.35 * (rng.uniform(-1.0, 1.0) * math.exp(-(i / sr) * 7.5))
            )
            * math.exp(-(i / sr) * 3.8)
            for i in range(n)
        ]
    elif se_kind == "page_turn":
        dur = 0.45
        n = int(sr * dur)
        return [
            (0.22 * math.sin(2 * math.pi * 520.0 * (i / sr)) + 0.18 * math.sin(2 * math.pi * 780.0 * (i / sr)))
            * math.exp(-(i / sr) * 9.0)
            for i in range(n)
        ]
    elif se_kind == "dawn_chord":
        dur = 0.80
        n = int(sr * dur)
        return [
            (
                0.22 * math.sin(2 * math.pi * 293.66 * (i / sr))
                + 0.18 * math.sin(2 * math.pi * 440.0 * (i / sr))
                + 0.16 * math.sin(2 * math.pi * 587.33 * (i / sr))
            )
            * math.exp(-(i / sr) * 3.2)
            for i in range(n)
        ]
    return []


def generate_cinematic_history_bgm(total_dur: float, out_wav: Path, sr: int = 44100) -> None:
    """Generate a rich 16-second Baroque D-minor orchestral cello + harpsichord arpeggio + timpani loop."""
    loop_dur = 16.0
    n_samples = int(sr * loop_dur)
    chords = [
        (73.42, 146.83, 174.61, 220.00, [293.66, 349.23, 440.00, 587.33, 440.00, 349.23, 293.66, 220.00]),  # Dm
        (58.27, 116.54, 146.83, 174.61, [233.08, 293.66, 349.23, 466.16, 349.23, 293.66, 233.08, 174.61]),  # Bb
        (49.00, 98.00, 146.83, 196.00, [196.00, 293.66, 392.00, 466.16, 392.00, 293.66, 233.08, 196.00]),   # Gm
        (55.00, 110.00, 138.59, 164.81, [220.00, 277.18, 329.63, 440.00, 349.23, 329.63, 277.18, 220.00]),  # A7
    ]
    bar_sec = 4.0
    note_sec = 0.5  # 8 harpsichord arpeggio notes per 4s bar

    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)

        buf = bytearray()
        for i in range(n_samples):
            t = i / sr
            bar_idx = int(t / bar_sec) % len(chords)
            f_bass, f_root, f_third, f_fifth, arp_notes = chords[bar_idx]

            bar_pos = (t % bar_sec) / bar_sec
            swell = 0.35 + 0.65 * (math.sin(math.pi * bar_pos) ** 0.7)

            vibrato = 1.0 + 0.003 * math.sin(2 * math.pi * 5.2 * t)
            cello = (
                0.32 * math.sin(2 * math.pi * f_bass * t)
                + 0.24 * math.sin(2 * math.pi * f_root * vibrato * t)
                + 0.16 * math.sin(2 * math.pi * f_third * vibrato * t)
                + 0.14 * math.sin(2 * math.pi * f_fifth * vibrato * t)
            ) * swell

            # Baroque harpsichord plucked arpeggio (gives clear rhythmic drive and historical atmosphere)
            note_idx = int((t % bar_sec) / note_sec) % len(arp_notes)
            note_t = t % note_sec
            f_arp = arp_notes[note_idx]
            harp_env = math.exp(-note_t * 6.5)
            harpsichord = (
                0.20 * math.sin(2 * math.pi * f_arp * t)
                + 0.12 * math.sin(2 * math.pi * (f_arp * 2.0) * t)
                + 0.06 * math.sin(2 * math.pi * (f_arp * 3.0) * t)
            ) * harp_env

            beat_pos = t % 2.0
            pulse = 0.30 * math.sin(2 * math.pi * 54.0 * beat_pos) * math.exp(-beat_pos * 7.0)

            val_l = max(-0.95, min(0.95, (cello + harpsichord * 1.1 + pulse) * 0.52))
            val_r = max(-0.95, min(0.95, (cello * 0.96 + harpsichord * 0.85 + pulse) * 0.52))
            buf.extend(struct.pack("<hh", int(val_l * 32767), int(val_r * 32767)))

        wf.writeframes(buf)


# ---------------------------------------------------------------------------
# Definitive 15-Minute Complete Edition Script (25 Flow Scenes + 8 Diagrams)
# ---------------------------------------------------------------------------

COMPLETE_EDITION_BLOCKS: List[Dict[str, Any]] = [
    # ==================== PROLOGUE ====================
    {
        "kind": "video",
        "scene_id": "scene_01",
        "chapter": "PROLOGUE • 1793年10月16日 パリ・断頭台の王妃",
        "beats": [
            {
                "se": "blade_glint",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "1793年10月16日、パリ。かつてヨーロッパで最も華やかなヴェルサイユ宮殿に君臨した王妃マリー・アントワネットは、",
                "sub_top": "1793年10月16日 パリ・革命広場",
                "sub_main": "かつて最も華やかな宮殿に君臨した王妃マリー・アントワネットは",
            },
            {
                "se": "",
                "cam": "mid",
                "clip_window": (2.5, 7.5),
                "narration": "髪を短く刈り取られ、粗末な白い麻の服を着せられて、数万人の群衆が罵声を浴びせる処刑台へと歩みを進めていました。",
                "sub_top": "処刑台へと続く石階段",
                "sub_main": "髪を刈られ、白い麻の服で処刑台へと歩みを進めていた",
            },
            {
                "se": "low_timpani",
                "cam": "close",
                "clip_window": (5.0, 9.8),
                "narration": "なぜ、1000年続いた絶対的な王権がわずか数年で崩壊し、普通の市民たちが国王と王妃の首を落とすに至ったのか。今回は当時のリアルな日常から、教科書の通説を覆す最新研究の諸説まで、フランス革命のすべてを完全に紐解きます。",
                "sub_top": "【完全保存版】そもそも「フランス革命」とは何だったのか？",
                "sub_main": "当時のリアルな日常から最新研究の「諸説」まで完全に紐解く",
            },
        ],
    },
    # ==================== CHAPTER 1: ANCIEN REGIME & DAILY ROUTINE ====================
    {
        "kind": "video",
        "scene_id": "scene_02",
        "chapter": "CHAPTER I • 2%の特権階級と98%の平民",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "第1章、革命前夜のフランス社会。当時のフランスは『アンシャン・レジーム』と呼ばれる厳格な身分制度に支配されていました。",
                "sub_top": "第1章：アンシャン・レジーム（旧体制）の格差",
                "sub_main": "当時のフランスは厳格な3つの身分制度に支配されていた",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "泥水を跳ね上げて走る黄金の馬車と、重い荷物を背負って歩く貧しい市民。この光景こそ、当時の歪んだ社会構造そのものでした。",
                "sub_top": "貴族の黄金馬車とパリの平民",
                "sub_main": "泥水を跳ね上げる貴族の馬車と、重税に喘ぐ98%の市民",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_01",
        "chapter": "CHAPTER I • 【歴史図解①】身分ピラミッドと税負担",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "こちらの図をご覧ください。第1身分の聖職者と第2身分の貴族は、合わせても人口のわずか2パーセントに過ぎませんが、国土の35パーセント以上を所有し、直接税はほぼゼロという特権を持っていました。",
                "sub_top": "【図解①】人口2%の聖職者・貴族が富を独占",
                "sub_main": "人口2%の特権階級が国土の35%を所有し、直接税はほぼゼロ",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "一方、人口の98パーセントを占める第3身分の平民は、収穫した麦の35パーセントを国王への税金、20パーセントを領主への地代、10パーセントを教会の十分の一税として奪われ、手元にはわずか2割しか残りませんでした。",
                "sub_top": "【図解①】農民の収穫の行き先",
                "sub_main": "税金・領主地代・教会税で奪われ、農民の手元には2割しか残らない",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_09",
        "chapter": "CHAPTER I • パリ市民の過酷な早朝ルーティン",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "当時のパリ市民のリアルな1日を見てみましょう。朝5時、パン職人の妻マルグリットの1日は、凍てつく路地でセーヌ川の濁った水を木桶に汲むことから始まります。",
                "sub_top": "早朝5:00 パリ市民マルグリットの朝",
                "sub_main": "水道はなく、凍てつく早朝にセーヌ川の濁った水を汲む日常",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "当時のパリには上下水道がなく、2階から汚物が窓の外へ投げ捨てられていました。家族の食事は、石のように硬い黒パンと薄いスープだけです。",
                "sub_top": "18世紀パリの下町のリアル",
                "sub_main": "上下水道はなく、石のように硬い黒パンで飢えをしのぐ生活",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_10",
        "chapter": "CHAPTER I • ヴェルサイユ宮殿「100人が見守る着替え儀式」",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "一方、平民が6時間働いた午前11時、パリから20キロ離れたヴェルサイユ宮殿では、王妃マリー・アントワネットの起床の儀式『ルヴェ』が始まります。",
                "sub_top": "午前11:00 ヴェルサイユ宮殿「起床の儀式」",
                "sub_main": "平民が6時間働いた頃、宮殿では王妃の「起床の儀式」が始まる",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "なんと王妃が服を着替えるだけで数十人の貴族女性たちが取り囲み、『誰が王妃に下着を手渡すか』という順番を巡って激しい権力争いが繰り広げられていました。",
                "sub_top": "異常な宮廷儀礼の世界",
                "sub_main": "王妃に下着を渡す順番だけで貴族たちが権力争いを繰り広げていた",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_03",
        "chapter": "CHAPTER I • ヴェルサイユ宮殿1万人の狂乱と悪臭",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "夜になれば、何千本もの蜜蝋キャンドルが灯る鏡の間で、毎晩のように40品以上の料理が並ぶ大晩餐会とカード賭博が開かれました。",
                "sub_top": "午後20:00 鏡の間の晩餐会と賭博",
                "sub_main": "毎晩40品以上の料理が並び、一晩で平民の年収100年分が動く賭博",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "しかし、700部屋もある宮殿にトイレはほとんど無く、貴族たちは廊下の隅や階段の裏で用を足していたため、宮殿中は強い香水と汚物の悪臭が混ざり合っていたといいます。",
                "sub_top": "華やかなシルクのドレスの裏側",
                "sub_main": "700部屋の宮殿にトイレはほぼ無く、廊下は香水と汚物の悪臭に満ちていた",
            },
        ],
    },
    # ==================== CHAPTER 2: BANKRUPTCY, NECKLACE SCAM & ENLIGHTENMENT ====================
    {
        "kind": "video",
        "scene_id": "scene_11",
        "chapter": "CHAPTER II • 【諸説検証】王妃は本当に悪女だったのか？",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "第2章、フランス国家破産の真相と諸説。当時、国の借金が膨れ上がった原因はすべて王妃の浪費にあると噂され、彼女は『赤字夫人』と呼ばれました。",
                "sub_top": "第2章：「赤字夫人（マダム・デフィシット）」の噂",
                "sub_main": "国の借金はすべて王妃の浪費が原因だと噂され、憎悪が集中した",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "しかし近年の歴史研究では、この通説は大きく覆されています。果たして本当に王妃がフランスを破産させたのでしょうか？",
                "sub_top": "教科書の通説 vs 最新歴史学の検証",
                "sub_main": "本当にマリー・アントワネットがフランス国家を破産させたのか？",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_02",
        "chapter": "CHAPTER II • 【諸説比較表①】国家破産の真犯人と「お菓子発言」の嘘",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "こちらの比較表をご覧ください。1788年の国家予算の実際の内訳を見ると、ヴェルサイユ宮廷費は全体のわずか6パーセント前後に過ぎませんでした。財政を破綻させた本当の原因は、歳出の50パーセント以上を占めた『過去の戦争借金の利払い』だったのです。",
                "sub_top": "【諸説比較①】宮廷費は全体のわずか6%だった",
                "sub_main": "国家破産の真因は王妃の浪費ではなく、歳出の50%を超えた「借金の利払い」",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "また、有名な『パンがなければお菓子を食べればいいじゃない』という言葉も、王妃が言った記録は一切ありません。彼女が10歳の時に思想家ルソーが書いた本の一節が、のちに革命派の中傷プロパガンダとして王妃に結びつけられたというのが現在の歴史学の定説です。",
                "sub_top": "【諸説比較①】「お菓子（ブリオッシュ）を食べればいい」の真相",
                "sub_main": "ルソーの著書の一節が中傷ビラで王妃になすりつけられたのが真相",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_12",
        "chapter": "CHAPTER II • ルイ16世と「アメリカ独立戦争」13億リーヴルの重荷",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "では、なぜそこまで借金が膨らんだのか。最大の引き金は、国王ルイ16世が宿敵イギリスを叩くために参戦した『アメリカ独立戦争』でした。",
                "sub_top": "財政破綻の決定打：アメリカ独立戦争への参戦",
                "sub_main": "宿敵イギリスを叩くため、アメリカ独立戦争へ13億リーヴルを投入",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "アメリカに自由をもたらすために約13億リーヴルもの戦費を借金で賄った結果、フランス自身の首が回らなくなるという皮肉な事態に陥ったのです。",
                "sub_top": "帳簿を前に頭を抱える国王ルイ16世",
                "sub_main": "アメリカの自由を支援した莫大な借金が、フランス王室自身の首を絞めた",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_21",
        "chapter": "CHAPTER II • 1785年 王室の威信を砕いた「首飾り事件」",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "それでも国民が王妃を憎んだ決定的なきっかけが、1785年の『ダイヤモンド首飾り事件』です。女詐欺師ジャンヌ・ド・ヴァロワが王妃の偽手紙を作り、夜の庭園に王妃そっくりの娼婦を立たせて、ロアン枢機卿に160万リーヴルの首飾りを買わせて騙し取りました。",
                "sub_top": "1785年「ダイヤモンド首飾り事件」の巨大詐欺",
                "sub_main": "夜の庭園で王妃の替え玉を使い、160万リーヴルの首飾りを騙し取った詐欺事件",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "アントワネットは全くの無実でしたが、パリの市民たちは『王妃が裏で糸を引いて詐欺師に罪をなすりつけた』と信じ込み、王室の権威は地に落ちたのです。",
                "sub_top": "無実だったにもかかわらず集中した国民の憎悪",
                "sub_main": "王妃は無実だったが、市民は「王妃の陰謀」と信じ込み王室の権威が崩壊した",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_22",
        "chapter": "CHAPTER II • パリのカフェ文化と「啓蒙思想」の広がり",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "同じ頃、パリのカフェ・プロコープやパレ・ロワイヤルの広場では、弁護士や作家、市民たちが集まり、ある危険な思想について夜通し議論を交わしていました。",
                "sub_top": "1788年 パリのカフェに集う知識人と市民",
                "sub_main": "カフェやサロンで印刷された本が回覧され、新しい思想が急速に広まった",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "それまで絶対とされてきた『王の権力は神から授かったものだ』という王権神授説を根底から覆す、『啓蒙思想』の誕生です。",
                "sub_top": "「王権神授説」を揺るがした啓蒙思想",
                "sub_main": "「なぜ生まれつき王や貴族だけが特権を持つのか？」と人々が気づき始めた",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_07",
        "chapter": "CHAPTER II • 【事件・思想図解⑦】首飾り事件の構図と3大啓蒙思想家",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "こちらの図で整理しましょう。左側の首飾り事件によって王室の道徳的な権威が失墜し、同時に右側の3大啓蒙思想家が革命の理論的な武器を与えました。",
                "sub_top": "【図解⑦】王室の権威失墜と啓蒙思想の融合",
                "sub_main": "首飾り事件で王室の威信が崩れ、3大啓蒙思想家が革命の理論的武器を与えた",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "三権分立を説いたモンテスキュー、教会の腐敗を批判したヴォルテール、そして『国の主権は王ではなく人民にある』と説いたルソーの社会契約論。これらが識字率の上昇とともにパリの市民へと一気に浸透していったのです。",
                "sub_top": "【図解⑦】モンテスキュー・ヴォルテール・ルソーの衝撃",
                "sub_main": "ルソーの『社会契約論（人民主権）』は、のちの革命派のバイブルとなった",
            },
        ],
    },
    # ==================== CHAPTER 3: VOLCANO, FAMINE & BREAD RIOTS ====================
    {
        "kind": "video",
        "scene_id": "scene_13",
        "chapter": "CHAPTER III • 1788年7月 麦畑を全滅させた「巨大ひょう嵐」",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "第3章、異常気象とパン価格の暴騰。財政危機と思想の広がりに決定的な火をつけたのが、1788年7月13日、フランスの穀倉地帯を襲った歴史的な大嵐と巨大な雹でした。",
                "sub_top": "第3章：1788年7月13日 収穫直前の麦畑を襲った巨大ひょう嵐",
                "sub_main": "鶏卵大の巨大な雹（ひょう）がフランスの穀倉地帯を直撃し麦畑が壊滅",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "収穫間近だった小麦畑はわずか数時間で泥の中に叩き伏せられ、マルグリットたち農民や市民は絶望の淵に立たされます。",
                "sub_top": "泥の中で潰れた麦穂を拾うマルグリット",
                "sub_main": "わずか数時間で収穫が失われ、冬にはマイナス20度の厳冬が襲った",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_03",
        "chapter": "CHAPTER III • 【気象史学・データ③】火山噴火説とパン価格チャート",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "気象史学の有力な説によれば、この異常気象の原点は1783年のアイスランド・ラキ火山の大噴火にありました。成層圏を覆った火山ガスがヨーロッパの気候を狂わせ、大凶作とマイナス20度の厳冬を引き起こしたのです。",
                "sub_top": "【諸説③】アイスランド「ラキ火山」大噴火による気候変動説",
                "sub_main": "1783年の火山大噴火が欧州の気候を狂わせ、大凶作と厳冬を招いた",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "右のグラフの通り、主食である4ポンドのパン1個の値段は、平年の8スーから1789年7月には16スー以上へと倍増し、労働者の1日の給料のじつに88パーセント、およそ9割に達しました。",
                "sub_top": "【データ③】パン1個＝労働者の日給の88%（約9割）へ暴騰",
                "sub_main": "1789年7月、パン1個の価格が最も高騰したまさにその日に革命が起きた",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_04",
        "chapter": "CHAPTER III • 14時間働いてもパン1個すら買えないパリ",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "凍てつく早朝のパン屋の前には長蛇の列ができ、震える手で銅貨をすべて差し出しても、家族全員が食べられるパンは手に入りません。",
                "sub_top": "1789年冬 パリのパン屋に並ぶ長い行列",
                "sub_main": "袋の銅貨をすべて差し出しても、家族を養うパンが買えない絶望",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "高邁な政治思想ではなく、『このままでは今日、自分の子供が餓死する』という極限の飢えこそが、パリ市民を暴動へと駆り立てた最大の原動力でした。",
                "sub_top": "パリの街が巨大な火薬庫へと変わった瞬間",
                "sub_main": "「このままでは子供が餓死する」という極限の飢えが革命の原動力となった",
            },
        ],
    },
    # ==================== CHAPTER 4: ESTATES-GENERAL & STORMING THE BASTILLE ====================
    {
        "kind": "video",
        "scene_id": "scene_14",
        "chapter": "CHAPTER IV • 三部会の決裂と「球技場（テニスコート）の誓い」",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "第4章、三部会の決裂とバスティーユ襲撃。1789年5月、財政破綻を解決するため、ルイ16世は175年ぶりに聖職者・貴族・平民の代表が集まる『三部会』を招集しました。",
                "sub_top": "第4章：1789年5月 175年ぶりに招集された「三部会」",
                "sub_main": "貴族にも課税するため、ルイ16世が175年ぶりに三部会を招集",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "しかし議決方法を巡って特権階級と対立した平民代表たちは、若き弁護士ロベスピエールらと共に室内の球技場に集結し、『憲法を制定するまで決して解散しない』という有名な球技場の誓いを立てます。",
                "sub_top": "1789年6月20日「球技場（テニスコート）の誓い」",
                "sub_main": "ロベスピエールら第三身分の代表が集結し、憲法制定まで解散しないと誓う",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_05",
        "chapter": "CHAPTER IV • 1789年7月14日 バスティーユ牢獄襲撃",
        "beats": [
            {
                "se": "cannon_boom",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "国王がこの動きを武力で鎮圧しようとパリの周囲に軍隊を集結させると、1789年7月14日、ついに数万人のパリ市民が蜂起し、巨大な要塞『バスティーユ牢獄』へと雪崩れ込みました。",
                "sub_top": "1789年7月14日 バスティーユ牢獄襲撃",
                "sub_main": "国王軍の包囲に対抗し、数万人の市民がバスティーユ牢獄へ突撃",
            },
            {
                "se": "cannon_boom",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "約100人の市民が命を落とす激しい銃撃戦の末、難攻不落と言われた要塞はわずか数時間で陥落。世界の歴史がひっくり返った瞬間でした。",
                "sub_top": "バスティーユ陥落とフランス革命の勃発",
                "sub_main": "激しい銃撃戦の末に要塞が陥落し、絶対王政の権威が崩れ落ちた",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_15",
        "chapter": "CHAPTER IV • 【諸説検証】バスティーユ内部の意外な光景",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "ところが、マルグリットたち市民が松明を掲げてバスティーユの地下牢へ踏み込むと、そこには予想外の光景が広がっていました。",
                "sub_top": "陥落したバスティーユ牢獄の内部へ",
                "sub_main": "松明を掲げて地下牢へ踏み込んだ市民が見た「予想外の光景」とは",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "何百人もの政治犯が鎖に繋がれていると思いきや、中にいた囚人はたったの7人だけだったのです。",
                "sub_top": "圧政の象徴の意外な実態",
                "sub_main": "巨大な牢獄に収容されていた囚人は、実は「たったの7人」だけだった",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_04",
        "chapter": "CHAPTER IV • 【諸説比較表②】三部会の仕組みと「囚人7人」の内訳",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "こちらの表で整理しましょう。三部会で平民が怒ったのは、議員の人数は半分を占めていたのに『1つの身分につき1票』というルールのため、聖職者・貴族の2対1で必ず否決される仕組みだったからです。",
                "sub_top": "【図解④】なぜ三部会は「2対1」で決裂したのか？",
                "sub_main": "1身分1票のルールにより、平民の要求が2対1で必ず否決される仕組みだった",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "そしてバスティーユ牢獄にいた7人の囚人の内訳は、小切手の偽造犯が4人、精神疾患の人物が2人、家族の依頼で軟禁されていた放蕩貴族が1人だけ。市民の本当の目的は囚人解放ではなく、要塞に眠っていた13.6トンの火薬を手に入れることでした。",
                "sub_top": "【諸説④】バスティーユ「7人の囚人」の真実と13.6トンの火薬",
                "sub_main": "囚人は偽造犯4・精神疾患2・放蕩貴族1のみ。真の狙いは13.6トンの火薬だった",
            },
        ],
    },
    # ==================== CHAPTER 5: MARCH ON VERSAILLES, VARENNES & VALMY ====================
    {
        "kind": "video",
        "scene_id": "scene_06",
        "chapter": "CHAPTER V • 1789年10月 パリの女たちの「ヴェルサイユ行進」",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "第5章、ヴェルサイユ行進と深夜の国王逃亡劇。8月に『人は生まれながらに自由で平等である』と謳うフランス人権宣言が採択された後も、パリの食糧不足は解消されませんでした。",
                "sub_top": "第5章：1789年10月 パンを求めるパリの女性たちの蜂起",
                "sub_main": "人権宣言後もパン不足は続き、パリの女性たち数千人が立ち上がる",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "10月5日、土砂降りの雨の中をパリの女性たち数千人が20キロ行進してヴェルサイユ宮殿を包囲し、黄金の門を突破して宮殿内へなだれ込みました。",
                "sub_top": "雨の20km行進とヴェルサイユ宮殿包囲",
                "sub_main": "黄金の門を突破した群衆により、国王一家はパリへ強制連行された",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_16",
        "chapter": "CHAPTER V • パリ・テュイルリー宮殿に幽閉された国王一家",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "二度とヴェルサイユへ戻ることができなくなったルイ16世とマリー・アントワネットは、パリの中心にあるテュイルリー宮殿へと移され、事実上の囚人として監視下に置かれます。",
                "sub_top": "1790年 パリ・テュイルリー宮殿での事実上の軟禁生活",
                "sub_main": "ヴェルサイユから引きずり出され、パリの真ん中で監視下に置かれた国王一家",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "実はこの時点では、フランス国民の大多数はまだ『王を処刑して共和政にする』ことまでは望んでおらず、王を戴いた立憲君主制を支持していました。その空気を一夜にして変えたのが、あの運命の逃亡事件です。",
                "sub_top": "国民の信頼を決定的に壊した「運命の一夜」へ",
                "sub_main": "この時点ではまだ王を残す「立憲君主制」が主流だったが、ある事件ですべてが変わる",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_17",
        "chapter": "CHAPTER V • 1791年6月深夜「ヴァレンヌ逃亡事件」",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "1791年6月20日の深夜、ルイ16世とアントワネットは家庭教師や召使いに変装し、大型馬車でパリを密かに脱出してオーストリア領の国境を目指しました。",
                "sub_top": "1791年6月20日深夜「ヴァレンヌ逃亡事件」",
                "sub_main": "召使いに変装した国王一家が、深夜に馬車でパリを脱出し国境を目指す",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "しかし国境まであと一歩の宿場町ヴァレンヌで馬車を止められ、ランタンの光の下で紙幣や金貨に描かれた王の横顔と見比べられて正体が発覚。その場で逮捕され、パリへと送還されたのです。",
                "sub_top": "国境まであと40km、宿場町ヴァレンヌでの発覚",
                "sub_main": "ランタンの光の下で金貨・紙幣の肖像画と顔を見比べられ、その場で逮捕された",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_05",
        "chapter": "CHAPTER V • 【歴史マップ⑤】ヴァレンヌ逃亡ルートと3つの諸説",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "こちらのマップをご覧ください。パリから240キロを走り、目的地モンメディ要塞まであとわずか40キロという地点でなぜ捕まったのか。これには歴史学で3つの説が議論されています。",
                "sub_top": "【歴史マップ⑤】国境まであと40kmで逮捕された理由",
                "sub_main": "パリから240km走破しながら、なぜ国境寸前のヴァレンヌで捕まったのか？",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "1つ目は、別々に小型馬車で逃げる案を王が拒み、銀食器まで積んだ6頭立ての巨大馬車を使ったため3時間以上遅れたという説。2つ目は発行されたばかりのアッシニア紙幣の肖像で宿場長に見破られた説。そして3つ目は、王の権威を失墜させるため革命派の一部が計画を知りながらわざと泳がせたという説です。",
                "sub_top": "【諸説⑤】大型馬車の遅れ説 vs 紙幣の肖像一致説 vs 泳がせ説",
                "sub_main": "この逃亡事件により「王は外国軍と組んで国民を討つ気だ」と信頼が完全に崩壊した",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_23",
        "chapter": "CHAPTER V • 1792年9月「ヴァルミーの戦い」と国歌ラ・マルセイエーズ",
        "beats": [
            {
                "se": "cannon_boom",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "1792年、王室を救出しようとするオーストリア・プロイセン連合軍がフランスへ侵攻すると、全国から集まった義勇兵たちが『武器を取れ、市民よ！』とラ・マルセイエーズを歌いながら戦場へと行進しました。",
                "sub_top": "1792年 フランス国歌『ラ・マルセイエーズ』の誕生",
                "sub_main": "外国軍の侵攻に対し、義勇兵たちが『ラ・マルセイエーズ』を歌い戦場へ集結",
            },
            {
                "se": "cannon_boom",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "そして9月20日、風車の丘で行われた『ヴァルミーの戦い』で市民軍がプロイセンの精鋭軍を撃退。従軍していた文豪ゲーテは『今日この場所から、世界の新しい歴史が始まる』と書き残しました。",
                "sub_top": "1792年9月20日「ヴァルミーの戦い」の歴史的勝利",
                "sub_main": "文豪ゲーテが「今日ここから世界の新しい歴史が始まる」と記した市民軍の勝利",
            },
        ],
    },
    # ==================== CHAPTER 6: EXECUTIONS, THREE LEADERS & REIGN OF TERROR ====================
    {
        "kind": "video",
        "scene_id": "scene_18",
        "chapter": "CHAPTER VI • 1793年1月21日 国王ルイ16世の処刑",
        "beats": [
            {
                "se": "blade_glint",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "第6章、国王と王妃の処刑、そして恐怖政治の狂気。外国軍と内通していた証拠の秘密書簡が宮殿から発見されると、1793年1月21日、ついに国王ルイ16世が断頭台へと送られます。",
                "sub_top": "第6章：1793年1月21日 国王ルイ16世の処刑",
                "sub_main": "外国軍との内通を示す秘密書簡が発見され、ルイ16世が断頭台へ送られる",
            },
            {
                "se": "low_timpani",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "処刑台の上で『私は無実の罪で死ぬ。私の血がフランスの幸福を固めることを祈る』と叫ぼうとした王の声は、一斉に打ち鳴らされた軍太鼓の音にかき消されました。",
                "sub_top": "軍太鼓にかき消された国王の最期の言葉",
                "sub_main": "「私は無実の罪で死ぬ」という王の声は軍太鼓にかき消され、王政が終焉した",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_24",
        "chapter": "CHAPTER VI • 1793年10月 マリー・アントワネットの裁判と最期の言葉",
        "beats": [
            {
                "se": "",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "その9ヶ月後の10月、タンプル塔に幽閉されていたマリー・アントワネットも革命裁判所に引き出されます。検察側がまだ幼い息子ルイ17世に無理やり証言させた虐待の罪状を読み上げると、王妃は傍聴席の女性たちに向かって『すべての母親の良心に訴えます』と毅然と反論しました。",
                "sub_top": "1793年10月 革命裁判所で毅然と立つ王妃",
                "sub_main": "不当な罪状にも決して屈せず、「すべての母親の良心に訴えます」と反論した",
            },
            {
                "se": "blade_glint",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "死刑判決を受けた王妃が断頭台の階段を上る際、誤って死刑執行人サンソンの足を踏んでしまい、『ムッシュ、お許しください。わざとではありませんでした』と言い残したのが、彼女の人生最後の言葉となりました。",
                "sub_top": "王妃マリー・アントワネットの最期の言葉",
                "sub_main": "死刑執行人の足を踏み「お許しください、わざとではありませんでした」と言い残した",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_07",
        "chapter": "CHAPTER VI • 独裁者ロベスピエールと「恐怖政治」の暴走",
        "beats": [
            {
                "se": "blade_glint",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "しかし、王と王妃を処刑したフランスを待っていたのは、さらなる地獄でした。外国との戦争と国内の反乱に追い詰められたジャコバン派のロベスピエールは、反対派を片っ端から粛清する『恐怖政治』を開始します。",
                "sub_top": "1793〜1794年 ロベスピエールによる「恐怖政治」",
                "sub_main": "国内外の危機の中、ロベスピエールが反対派を次々と粛清する恐怖政治を開始",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "弁護士も、証人もない革命裁判所で次々と死刑判決が下され、わずか1年余りで1万7000人以上がギロチンで処刑されました。",
                "sub_top": "1年余りで1万7,000人以上を処刑",
                "sub_main": "弁護人も証人もない裁判で、昨日までの仲間や一般市民までが次々と処刑された",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_25",
        "chapter": "CHAPTER VI • 盟友ダントンの処刑と孤独な独裁者",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "狂気は味方すらも呑み込みます。過激派のマラーが浴槽で暗殺されると、ロベスピエールは『もう流血を止めるべきだ』と訴えたかつての盟友ダントンすらも反革命の罪で逮捕し、断頭台へと送りました。",
                "sub_top": "1794年4月 かつての盟友ダントンすら処刑",
                "sub_main": "「もう流血を止めるべきだ」と訴えた盟友ダントンすらもギロチンへ送った",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "処刑台へ向かう荷馬車の上から、ダントンはロベスピエールの家の閉ざされた窓を指差し、『ロベスピエールよ、お前もすぐに俺の後を追うことになるぞ！』と叫んだといいます。",
                "sub_top": "ダントンが遺した不気味な予言",
                "sub_main": "「ロベスピエールよ、お前もすぐに俺の後を追うことになるぞ！」",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_08",
        "chapter": "CHAPTER VI • 【派閥・人物図解⑧】右派・左派の語源と三巨頭の末路",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "こちらの図をご覧ください。実は現代の政治で使われる『右派・左派』という言葉は、このフランス革命の議場で議長席から見て右側に穏健な王党派、左側に急進的なジャコバン派が座ったことから生まれました。",
                "sub_top": "【図解⑧】現代の政治用語「右派・左派」はフランス革命で生まれた",
                "sub_main": "議長席から見て右に保守・穏健派、左に急進派が座ったことが「右派・左派」の語源",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "そして右側にある通り、革命を牽引したジャコバン派の三巨頭、マラーは25歳の女性コルデーに暗殺され、ダントンは盟友ロベスピエールに処刑され、残ったロベスピエールもまた、自らが作った恐怖のシステムによって追い詰められていきます。",
                "sub_top": "【図解⑧】ジャコバン派「三巨頭」マラー・ダントン・ロベスピエールの末路",
                "sub_main": "革命を動かした3人のリーダーは、わずか1年の間に全員が非業の死を遂げた",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_19",
        "chapter": "CHAPTER VI • 1794年7月「テルミドールのクーデター」",
        "beats": [
            {
                "se": "low_timpani",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "ダントンの予言からわずか3ヶ月後の1794年7月27日。『次は自分が殺される』と恐怖に駆られた議員たちが国民公会の議場で一斉に立ち上がり、『独裁者ロベスピエールを逮捕せよ！』と叫びました。",
                "sub_top": "1794年7月27日「テルミドールのクーデター」",
                "sub_main": "「次は自分が殺される」と怯えた議員たちが一斉に蜂起し、ロベスピエールを弾劾",
            },
            {
                "se": "blade_glint",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "銃撃で顎を砕かれながら逮捕されたロベスピエールはその翌日、自らが何千人も送り込んだのと同じ革命広場のギロチンにかけられ、恐怖政治は劇的な幕を閉じました。",
                "sub_top": "独裁者ロベスピエールの最期",
                "sub_main": "逮捕された翌日、ロベスピエール自身も同じギロチンで処刑され恐怖政治が終わった",
            },
        ],
    },
    {
        "kind": "diagram",
        "diagram_id": "diagram_06",
        "chapter": "FINAL CHAPTER • 【完全総括⑥】ギロチンの皮肉と「革命は成功か失敗か」",
        "beats": [
            {
                "se": "page_turn",
                "zoom": "in",
                "narration": "最後に、歴史の皮肉とフランス革命の評価を総括しましょう。実は恐怖の象徴となったギロチンは、もともと『平民も貴族と同じように一瞬で苦痛なく処刑する人道と平等の装置』として提案されたものでした。さらに諸説では、手先が器用だったルイ16世自身が『刃を斜めの直線にした方がよく切れる』と改良を助言したとも言われています。",
                "sub_top": "【歴史の皮肉⑥】ギロチンは「人道と平等」の発明だった",
                "sub_main": "ルイ16世自身が「斜めの刃」への改良を助言し、自らがその刃で処刑された皮肉",
            },
            {
                "se": "",
                "zoom": "out",
                "narration": "また歴史学では、王を倒したのに10年後に皇帝ナポレオンを生み、さらには王政復古まで起きたため『革命は一周回って失敗だった』とする保守派の見方と、それでも『生まれによる特権と封建制を完全に破壊し、法の下の平等を世界に広げた最大の転換点だった』とする肯定派の両面から今なお議論が続いています。",
                "sub_top": "【2大史観の総括】フランス革命は成功だったのか？失敗だったのか？",
                "sub_main": "王政が復活しても「生まれによる特権」は二度と戻らず、近代人権社会の礎となった",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_20",
        "chapter": "FINAL CHAPTER • 1799年 ナポレオンの登場と新しい時代へ",
        "beats": [
            {
                "se": "dawn_chord",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "1799年、10年間続いた革命の混乱に終止符を打ったのは、若き天才軍人ナポレオン・ボナパルトでした。",
                "sub_top": "1799年 若き英雄ナポレオン・ボナパルトの登場",
                "sub_main": "10年間の混乱の果てにナポレオンが登場し、革命の理念を全ヨーロッパへ広げていく",
            },
            {
                "se": "",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "ナポレオンはヨーロッパ中を席巻しながら、すべての市民が法の下に平等であるという『ナポレオン法典』を広め、古い中世の秩序を根底から塗り替えていきました。",
                "sub_top": "ナポレオン法典が変えた近代世界",
                "sub_main": "「法の下の平等」と「個人の所有権」はナポレオン法典を通じて世界標準となった",
            },
        ],
    },
    {
        "kind": "video",
        "scene_id": "scene_08",
        "chapter": "EPILOGUE • 現代を生きる私たちへ遺されたもの",
        "beats": [
            {
                "se": "dawn_chord",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "narration": "飢えた母親がパン1個を求めた叫びから始まり、王妃の処刑、恐怖政治の狂気、そして人権宣言へと至ったフランス革命。",
                "sub_top": "パン1個の叫びから始まった10年間",
                "sub_main": "多くの血と狂気を経て勝ち取られた「人は生まれながらに自由で平等である」という理念",
            },
            {
                "se": "dawn_chord",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "narration": "『親の身分や生まれによって、人の価値は決まらない』。私たちが当たり前のように享受している自由と平等は、230年前のパリの石畳の上で流されたおびただしい血の上に築かれているのです。",
                "sub_top": "【完全保存版】フランス革命のすべて ── 完",
                "sub_main": "230年前のパリで流された血の上に、私たちが生きる現代社会の自由と平等がある",
            },
        ],
    },
]


_GLOBAL_VV_ENGINE = None


def _get_vv_engine():
    global _GLOBAL_VV_ENGINE
    if _GLOBAL_VV_ENGINE is None:
        from voicevox_dialogue_engine import VoicevoxDirectEngine
        _GLOBAL_VV_ENGINE = VoicevoxDirectEngine()
    return _GLOBAL_VV_ENGINE


def _select_voicevox_role_and_text(text: str, se_kind: str) -> Tuple[str, str]:
    """
    Hybrid Master Voice Routing:
    - 80% calm main Narration (`冥鳴ひまり`, role='narrator')
    - Question transitions (`se_kind == 'question_sting'` or 'ここで第' in text) -> `四国めたん` (role='tsukkomi')
      with natural conversational phrasing (`でもちょっと待って！...`)
    - Royal/Emperor commands or conspiracies -> `麒ヶ島宗麟` (role='king')
    - Protagonist/Grand Master cries or citizen laments -> `玄野武宏` (role='protagonist') or `白上虎太郎` (role='citizen')
    """
    import re
    if se_kind == "question_sting" or ("ここで" in text and "疑問です" in text):
        cleaned = re.sub(r"^ここで.*?疑問です[。、\s]*", "でも、ちょっと待って！", text)
        return "tsukkomi", cleaned
    if any(k in text for k in ("『10月13日の夜明け前に開封せよ", "フィリップ4世は", "カラカラ帝", "ディオクレティアヌス帝")) and "『" in text:
        return "king", text
    if any(k in text for k in ("『神と王の法廷へ", "モレーは火刑台", "無実だ")) and "『" in text:
        return "protagonist_angry", text
    if any(k in text for k in ("巡礼者", "農民", "市民たち", "重税")) and "『" in text:
        return "citizen", text
    return "narrator", text


def build_narration_beat_wav(
    text: str,
    se_kind: str,
    out_wav: Path,
    work_dir: Path,
    beat_idx: int,
) -> float:
    """Generate VOICEVOX multi-cast narration + subtle historical SE for a single beat."""
    sr = 44100
    se_samples = synthesize_history_se(se_kind, sr) if se_kind else []
    # Keep SE subtle (0.45x) so narration always stays front-and-center
    combined: List[float] = [s * 0.45 for s in se_samples] + ([0.0] * int(sr * 0.04) if se_samples else [])

    vv = _get_vv_engine()
    role, spoken_text = _select_voicevox_role_and_text(text, se_kind)
    vv_raw_wav = work_dir / f"hist_beat_{beat_idx:03d}_vv24k.wav"
    wav_p = work_dir / f"hist_beat_{beat_idx:03d}_raw.wav"

    speed = 1.13 if role == "tsukkomi" else 1.10
    vv.synthesize_to_wav(spoken_text, vv_raw_wav, role=role, speed_override=speed)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(vv_raw_wav), "-ac", "1", "-ar", str(sr), "-f", "wav", str(wav_p)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with wave.open(str(wav_p), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        samples = [s / 32768.0 for (s,) in struct.iter_unpack("<h", raw)]
        while samples and abs(samples[0]) < 0.008:
            samples.pop(0)
        while samples and abs(samples[-1]) < 0.008:
            samples.pop()
        combined.extend(samples)
        combined.extend([0.0] * int(sr * 0.32))

    with wave.open(str(out_wav), "wb") as out_wf:
        out_wf.setnchannels(1)
        out_wf.setsampwidth(2)
        out_wf.setframerate(sr)
        buf = bytearray()
        for v in combined:
            iv = max(-32767, min(32767, int(v * 32767)))
            buf.extend(struct.pack("<h", iv))
        out_wf.writeframes(buf)

    return len(combined) / sr


def render_cinema_overlay_16x9(
    chapter_text: str,
    sub_top: str,
    sub_main: str,
    out_png: Path,
    is_diagram: bool = False,
) -> None:
    """
    Hybrid Master 1280x720 Overlay:
    - Live-Action (`is_diagram=False`):
      * NO bulky top-left gold box and NO bottom gold pill!
      * Subtle top-left chapter text + thin `───` callout pointer line (`sub_top`) pointing onto the 35mm scene
      * Clean white bottom subtitle (`sub_main`)
    - Pattern-A Diagram (`is_diagram=True`):
      * Soft bottom gradient + clean white bottom subtitle (`sub_main`) only, leaving the Pattern-A diagram unobstructed.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    jp_font_p = find_cjk_font()

    # Soft bottom cinema gradient for subtitle legibility
    start_y = 555 if is_diagram else 540
    for y in range(start_y, H):
        alpha = int(220 * ((y - start_y) / (H - start_y)) ** 1.25)
        draw.line([(0, y), (W, y)], fill=(5, 6, 10, alpha))

    if not is_diagram:
        # 1. Clean top-left chapter title (stroked text, no heavy box)
        chap_short = chapter_text.split("•")[-1].strip() if "•" in chapter_text else chapter_text
        f_chap = fit_font_w(draw, chap_short, jp_font_p, 24, 15, 680)
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                if dx or dy:
                    draw.text((38 + dx, 26 + dy), chap_short, font=f_chap, fill=(0, 0, 0, 235))
        draw.text((38, 26), chap_short, font=f_chap, fill=(255, 225, 130, 250))

        # 2. Thin `───` Callout Pointer Line (`sub_top`) pointing onto the live-action subject
        if sub_top:
            f_call = fit_font_w(draw, sub_top, jp_font_p, 20, 14, 520)
            tb_c = draw.textbbox((0, 0), sub_top, font=f_call)
            tw_c = tb_c[2] - tb_c[0]
            th_c = tb_c[3] - tb_c[1]
            ax, ay = 560, 285
            lx, ly = 620, 225
            if lx + tw_c + 24 > W - 30:
                lx = W - tw_c - 40
                ax = max(320, lx - 55)
            draw.line([(ax, ay), (lx, ly + th_c + 6)], fill=(235, 235, 240, 215), width=2)
            draw.line([(lx, ly + th_c + 6), (lx + tw_c + 10, ly + th_c + 6)], fill=(235, 235, 240, 215), width=2)
            for dx in (-2, 0, 2):
                for dy in (-2, 0, 2):
                    if dx or dy:
                        draw.text((lx + 4 + dx, ly + dy), sub_top, font=f_call, fill=(0, 0, 0, 240))
            draw.text((lx + 4, ly), sub_top, font=f_call, fill=(245, 245, 250, 255))

    # 3. Clean bottom subtitle (split into 2 balanced lines if long, or 1 crisp line)
    if len(sub_main) > 27:
        mid = len(sub_main) // 2
        split_idx = mid
        for offset in range(0, 10):
            for cand in (mid + offset, mid - offset):
                if 8 < cand < len(sub_main) - 6 and sub_main[cand] in "、。！？ 」』・":
                    split_idx = cand + 1
                    break
            else:
                continue
            break
        l1 = sub_main[:split_idx].strip()
        l2 = sub_main[split_idx:].strip()
        f1 = fit_font_w(draw, l1, jp_font_p, 29, 18, W - 70)
        f2 = fit_font_w(draw, l2, jp_font_p, 29, 18, W - 70)
        b1 = draw.textbbox((0, 0), l1, font=f1)
        b2 = draw.textbbox((0, 0), l2, font=f2)
        for txt_s, f_s, bw_s, y_s in [(l1, f1, b1[2] - b1[0], H - 96), (l2, f2, b2[2] - b2[0], H - 52)]:
            tx = (W - bw_s) // 2
            for dx in (-3, -2, 0, 2, 3):
                for dy in (-3, -2, 0, 2, 3):
                    if dx or dy:
                        draw.text((tx + dx, y_s + dy), txt_s, font=f_s, fill=(0, 0, 0, 245))
            draw.text((tx, y_s), txt_s, font=f_s, fill=(255, 255, 255, 255))
    else:
        f_main = fit_font_w(draw, sub_main, jp_font_p, 32, 19, W - 64)
        tb_m = draw.textbbox((0, 0), sub_main, font=f_main)
        tw_m = tb_m[2] - tb_m[0]
        tx = (W - tw_m) // 2
        ty = H - 72
        for dx in (-3, -2, 0, 2, 3):
            for dy in (-3, -2, 0, 2, 3):
                if dx or dy:
                    draw.text((tx + dx, ty + dy), sub_main, font=f_main, fill=(0, 0, 0, 245))
        draw.text((tx, ty), sub_main, font=f_main, fill=(255, 255, 255, 255))

    img.save(out_png)


def render_diagram_beat_segment(
    diagram_png: Path,
    overlay_png: Path,
    beat_wav: Path,
    dur: float,
    zoom_dir: str,
    out_mp4: Path,
) -> None:
    """Render a Pattern-A visual diagram segment with subtle motion and hardware encoding."""
    if zoom_dir == "in":
        scale_vf = f"scale={int(W*1.03)}:{int(H*1.03)},crop={W}:{H}:(iw-{W})/2:(ih-{H})/2"
    else:
        scale_vf = f"scale={W}:{H}"

    vf = (
        f"[0:v]fps={FPS},{scale_vf},format=rgba[bg];"
        f"[1:v]format=rgba[ov];"
        f"[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-framerate",
            "2",
            "-i",
            str(diagram_png),
            "-i",
            str(overlay_png),
            "-i",
            str(beat_wav),
            "-filter_complex",
            vf,
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(out_mp4),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def render_beat_video_segment(
    flow_mp4: Path,
    overlay_png: Path,
    beat_wav: Path,
    dur: float,
    cam_mode: str,
    clip_window: Tuple[float, float],
    out_mp4: Path,
) -> None:
    """Render a 35mm live-action video segment from the Google Flow clip using fast libx264 encoding."""
    tw, th = W, H
    t_start, t_end = clip_window
    slice_dur = max(2.0, t_end - t_start)
    pts_factor = max(1.0, dur / slice_dur)

    if cam_mode == "wide":
        crop_vf = f"scale={int(tw*1.04)}:{int(th*1.04)}:force_original_aspect_ratio=increase,crop={tw}:{th}:(iw-{tw})/2:(ih-{th})/2"
    elif cam_mode == "mid":
        crop_vf = f"scale={int(tw*1.16)}:{int(th*1.16)}:force_original_aspect_ratio=increase,crop={tw}:{th}:(iw-{tw})/2:(ih-{th})*0.38"
    else:
        crop_vf = f"scale={int(tw*1.26)}:{int(th*1.26)}:force_original_aspect_ratio=increase,crop={tw}:{th}:(iw-{tw})*0.46:(ih-{th})*0.35"

    vf = (
        f"[0:v]setpts={pts_factor:.4f}*(PTS-STARTPTS),"
        f"fps={FPS},{crop_vf},eq=contrast=1.05:saturation=1.06,format=rgba[bg];"
        f"[1:v]format=rgba[ov];"
        f"[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{t_start:.2f}",
            "-t",
            f"{slice_dur:.2f}",
            "-i",
            str(flow_mp4),
            "-i",
            str(overlay_png),
            "-i",
            str(beat_wav),
            "-filter_complex",
            vf,
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(out_mp4),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_thumbnail(out_jpg: Path) -> None:
    """Create a dramatic 1280x720 cinema thumbnail for the Complete Edition."""
    s5_mp4 = FLOW_DIR / "scene_05.mp4"
    frame_png = OUTPUT_DIR / "_tmp_hist_thumb_frame.png"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "2.5", "-i", str(s5_mp4), "-frames:v", "1", str(frame_png)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    bg = Image.open(frame_png).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov, "RGBA")
    jp_font_p = find_cjk_font()

    for y in range(H - 300, H):
        a = int(215 * ((y - (H - 300)) / 300) ** 1.35)
        draw.line([(0, y), (W, y)], fill=(5, 6, 10, a))

    draw_rounded_box(
        draw,
        (36, 32, 640, 94),
        radius=16,
        fill=(165, 22, 22, 235),
        outline=(255, 215, 100, 255),
        width=3,
    )
    f_tag = fit_font_w(draw, "【AI実写・完全保存版】フランス革命のすべて", jp_font_p, 29, 20, 575)
    draw.text((54, 45), "【AI実写・完全保存版】フランス革命のすべて", font=f_tag, fill=(255, 255, 255, 255))

    line1 = "パン1個＝日給の9割から断頭台まで"
    line2 = "教科書の通説と「諸説」を完全網羅"
    f1 = fit_font_w(draw, line1, jp_font_p, 64, 38, W - 80)
    f2 = fit_font_w(draw, line2, jp_font_p, 72, 42, W - 80)

    for text, fnt, y_pos, col in [
        (line1, f1, H - 215, (255, 218, 90, 255)),
        (line2, f2, H - 125, (255, 255, 255, 255)),
    ]:
        for dx in (-5, -3, 0, 3, 5):
            for dy in (-5, -3, 0, 3, 5):
                if dx != 0 or dy != 0:
                    draw.text((42 + dx, y_pos + dy), text, font=fnt, fill=(0, 0, 0, 250))
        draw.text((42, y_pos), text, font=fnt, fill=col)

    bg = Image.alpha_composite(bg, ov)
    bg.convert("RGB").save(out_jpg, quality=95)
    frame_png.unlink(missing_ok=True)


def resolve_scene_mp4(scene_id: str) -> Path:
    """Return the exact scene MP4, or a matching fallback if still downloading."""
    p = FLOW_DIR / f"{scene_id}.mp4"
    if p.exists() and p.stat().st_size > 50_000:
        return p
    fallbacks = {
        "scene_09": "scene_02",
        "scene_10": "scene_03",
        "scene_11": "scene_03",
        "scene_12": "scene_03",
        "scene_13": "scene_04",
        "scene_14": "scene_07",
        "scene_15": "scene_05",
        "scene_16": "scene_06",
        "scene_17": "scene_06",
        "scene_18": "scene_01",
        "scene_19": "scene_07",
        "scene_20": "scene_08",
        "scene_21": "scene_11",
        "scene_22": "scene_13",
        "scene_23": "scene_05",
        "scene_24": "scene_16",
        "scene_25": "scene_19",
    }
    fb = FLOW_DIR / f"{fallbacks.get(scene_id, 'scene_01')}.mp4"
    return fb


QUESTION_BEAT_MAP: Dict[str, Dict[str, str]] = {
    "diagram_01": {
        "q_id": "q_01",
        "narration": "ここで第1の疑問です。なぜ人口の98パーセントを占める平民が飢え、収穫の65パーセントが消えてしまったのでしょうか？",
        "sub_top": "【歴史の疑問 Q1】アンシャン・レジームの罠",
        "sub_main": "なぜ人口の「98%」が飢え、収穫の65%が消えたのか？",
    },
    "diagram_02": {
        "q_id": "q_02",
        "narration": "ここで第2の疑問です。なぜ王妃の浪費ではなく、借金がフランスという超大国を破産させたのでしょうか？",
        "sub_top": "【歴史の疑問 Q2】国家破産の真犯人とは？",
        "sub_main": "なぜ王妃の浪費ではなく、「借金」が国を潰したのか？",
    },
    "diagram_07": {
        "q_id": "q_03",
        "narration": "ここで第3の疑問です。なぜ無実の王妃が詐欺犯として憎まれ、人々は『もう王はいらない』と気づき始めたのでしょうか？",
        "sub_top": "【歴史の疑問 Q3】スキャンダルと啓蒙思想",
        "sub_main": "なぜ無実の王妃が憎まれ、「王はいらない」と気づいたのか？",
    },
    "diagram_03": {
        "q_id": "q_04",
        "narration": "ここで第4の疑問です。なぜパン1個の値段が、労働者の日給の9割にまで暴騰してしまったのでしょうか？",
        "sub_top": "【歴史の疑問 Q4】異常気象とパン価格暴騰",
        "sub_main": "なぜパン1個の値段が「日給の9割」に暴騰したのか？",
    },
    "diagram_04": {
        "q_id": "q_05",
        "narration": "ここで第5の疑問です。なぜ巨大なバスティーユ牢獄に、囚人がたったの7人しかいなかったのでしょうか？",
        "sub_top": "【歴史の疑問 Q5】バスティーユ襲撃の真実",
        "sub_main": "なぜ巨大なバスティーユ牢獄に囚人が「7人」しかいなかったのか？",
    },
    "diagram_05": {
        "q_id": "q_06",
        "narration": "ここで第6の疑問です。なぜ国境まであと40キロという目前で、国王一家は捕まってしまったのでしょうか？",
        "sub_top": "【歴史の疑問 Q6】ヴァレンヌ逃亡事件の謎",
        "sub_main": "なぜ国境まで「あと40km」で国王一家は捕まったのか？",
    },
    "diagram_08": {
        "q_id": "q_07",
        "narration": "ここで第7の疑問です。なぜ革命を成功させたリーダーたちは、最後には味方同士で殺し合ったのでしょうか？",
        "sub_top": "【歴史の疑問 Q7】恐怖政治と三巨頭の末路",
        "sub_main": "なぜ革命のリーダーたちは「味方同士」で殺し合ったのか？",
    },
    "diagram_06": {
        "q_id": "q_08",
        "narration": "そして最後の疑問です。結局、フランス革命は歴史的に見て成功だったのか、それとも失敗だったのでしょうか？",
        "sub_top": "【歴史の疑問 Q8】フランス革命の最終評価",
        "sub_main": "結局、フランス革命は「成功」か？それとも「失敗」か？",
    },
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)

    # Render all 8 diagram/table boards and all 8 Question Close-Up Cards first
    for i in range(1, 9):
        did = f"diagram_{i:02d}"
        render_diagram_board(did, DIAG_DIR / f"{did}.png")
        qid = f"q_{i:02d}"
        render_question_card(qid, DIAG_DIR / f"{qid}.png", FLOW_DIR)

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        long_segs: List[Path] = []
        beat_counter = 0

        for block in COMPLETE_EDITION_BLOCKS:
            kind = block["kind"]
            chapter = block["chapter"]

            if kind == "diagram":
                diag_id = block["diagram_id"]
                diag_png = DIAG_DIR / f"{diag_id}.png"

                # First insert the dramatic Question Close-Up Card ("なぜ〇〇なのか？") before the table/diagram!
                q_spec = QUESTION_BEAT_MAP.get(diag_id)
                if q_spec:
                    beat_counter += 1
                    q_png = DIAG_DIR / f"{q_spec['q_id']}.png"
                    q_wav = work_dir / f"beat_{beat_counter:03d}.wav"
                    q_dur = build_narration_beat_wav(
                        text=q_spec["narration"],
                        se_kind="question_sting",
                        out_wav=q_wav,
                        work_dir=work_dir,
                        beat_idx=beat_counter,
                    )
                    print(f"Beat {beat_counter:02d} (QUESTION {q_spec['q_id']}): {q_dur:.2f}s | {q_spec['sub_main']}")
                    q_ov = work_dir / f"ov_{beat_counter:03d}.png"
                    render_cinema_overlay_16x9(chapter, q_spec["sub_top"], q_spec["sub_main"], q_ov, is_diagram=True)
                    q_seg = work_dir / f"seg_{beat_counter:03d}.mp4"
                    render_diagram_beat_segment(
                        diagram_png=q_png,
                        overlay_png=q_ov,
                        beat_wav=q_wav,
                        dur=q_dur,
                        zoom_dir="in",
                        out_mp4=q_seg,
                    )
                    long_segs.append(q_seg)

                for beat in block["beats"]:
                    beat_counter += 1
                    beat_wav = work_dir / f"beat_{beat_counter:03d}.wav"
                    dur = build_narration_beat_wav(
                        text=beat["narration"],
                        se_kind=beat["se"],
                        out_wav=beat_wav,
                        work_dir=work_dir,
                        beat_idx=beat_counter,
                    )
                    print(f"Beat {beat_counter:02d} (DIAGRAM {diag_id}): {dur:.2f}s | {beat['sub_main']}")
                    ov_png = work_dir / f"ov_{beat_counter:03d}.png"
                    render_cinema_overlay_16x9(chapter, beat["sub_top"], beat["sub_main"], ov_png, is_diagram=True)
                    seg_mp4 = work_dir / f"seg_{beat_counter:03d}.mp4"
                    render_diagram_beat_segment(
                        diagram_png=diag_png,
                        overlay_png=ov_png,
                        beat_wav=beat_wav,
                        dur=dur,
                        zoom_dir=beat.get("zoom", "in"),
                        out_mp4=seg_mp4,
                    )
                    long_segs.append(seg_mp4)
            else:
                scene_id = block["scene_id"]
                flow_mp4 = resolve_scene_mp4(scene_id)
                for beat in block["beats"]:
                    beat_counter += 1
                    beat_wav = work_dir / f"beat_{beat_counter:03d}.wav"
                    dur = build_narration_beat_wav(
                        text=beat["narration"],
                        se_kind=beat["se"],
                        out_wav=beat_wav,
                        work_dir=work_dir,
                        beat_idx=beat_counter,
                    )
                    print(f"Beat {beat_counter:02d} (VIDEO {scene_id} -> {flow_mp4.name} [{beat['cam']}]): {dur:.2f}s | {beat['sub_main']}")
                    ov_png = work_dir / f"ov_{beat_counter:03d}.png"
                    render_cinema_overlay_16x9(chapter, beat["sub_top"], beat["sub_main"], ov_png, is_diagram=False)
                    seg_mp4 = work_dir / f"seg_{beat_counter:03d}.mp4"
                    render_beat_video_segment(
                        flow_mp4=flow_mp4,
                        overlay_png=ov_png,
                        beat_wav=beat_wav,
                        dur=dur,
                        cam_mode=beat["cam"],
                        clip_window=beat["clip_window"],
                        out_mp4=seg_mp4,
                    )
                    long_segs.append(seg_mp4)

        concat_long_txt = work_dir / "concat_long.txt"
        concat_long_txt.write_text("\n".join(f"file '{p}'" for p in long_segs))
        raw_long_mp4 = work_dir / "raw_long.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_long_txt), "-c", "copy", str(raw_long_mp4)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        long_dur = get_duration(raw_long_mp4)
        bgm_long_wav = work_dir / "bgm_long.wav"
        generate_cinematic_history_bgm(16.0, bgm_long_wav)

        out_long = OUTPUT_DIR / "history_french_revolution_complete_long.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(raw_long_mp4),
                "-stream_loop",
                "-1",
                "-i",
                str(bgm_long_wav),
                "-filter_complex",
                f"[0:a]volume=1.55[va];[1:a]atrim=0:{long_dur+1.0:.2f},volume=0.45,afade=t=out:st={max(0.0, long_dur-3.0):.2f}:d=3.0[ba];[va][ba]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(out_long),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[DONE] Complete Long video: {out_long} ({long_dur:.1f}s = {long_dur/60:.1f} mins)")

        out_thumb = OUTPUT_DIR / "history_french_revolution_thumb.jpg"
        build_proposal_D().convert("RGB").save(out_thumb, quality=95)
        print(f"[DONE] Thumbnail (Proposal D): {out_thumb}")


if __name__ == "__main__":
    main()

