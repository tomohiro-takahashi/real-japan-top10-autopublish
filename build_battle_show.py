#!/usr/bin/env python3
"""
build_battle_show.py

Transforms an animal battle into a high-energy TV/YouTube Battle Broadcast Show:
1. Two-voice fast-paced dialogue:
   - Play-by-play Announcer (ja-JP-KeitaNeural, +18% rate)
   - Science Analyst (ja-JP-NanamiNeural, +15% rate)
2. Fighting-Game / Broadcast HUD Overlay on every cut:
   - Top HP Bars & Battery/Stamina Gauges for both fighters that dynamically animate/drop
   - Pop-up Fighter Spec Cards / VS Comparison Tables during analysis cuts
   - Giant Impact Telops ("WARNING! 860V", "CRITICAL HIT!", "PLOT TWIST!", "K.O.!")
   - Line-by-line color-coded subtitles switching every 3-6 seconds
3. Sound Effects (SE) & Driving Battle BGM:
   - Automatically synthesizes punchy impact hits, 860V electric zaps, warning sirens,
     digital radar beeps, and an energetic rhythmic battle beat.
4. Supports Google Flow MP4 clips (only 5-6 clips needed per video, using slow-mo/zoom replay).
"""

import asyncio
import json
import logging
import math
import os
import struct
import subprocess
import tempfile
import time
import urllib.parse
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
FLOW_CLIPS_DIR = BASE_DIR / "assets" / "flow_clips"
OUTPUT_DIR = BASE_DIR / "output"

W = 1280
H = 720
FPS = 25


def find_cjk_font() -> str:
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("CJK font not found")


# ==============================================================================
# Sound Effects (SE) & Rhythmic Battle BGM Synthesizer (Pure Python + Math)
# ==============================================================================
def write_wav(path: Path, samples: List[float], sample_rate: int = 44100) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            frames.extend(struct.pack("<h", int(clamped * 32767)))
        wf.writeframes(frames)


def generate_sfx(sfx_type: str, output_wav: Path) -> Optional[Path]:
    sr = 44100
    samples: List[float] = []
    import random as rnd

    if sfx_type == "gong":
        # Deep dramatic impact boom
        dur = 1.2
        for i in range(int(sr * dur)):
            t = i / sr
            env = math.exp(-t * 3.5)
            freq = 95 * math.exp(-t * 1.2) + 45
            val = (
                0.6 * math.sin(2 * math.pi * freq * t)
                + 0.25 * math.sin(2 * math.pi * (freq * 1.5) * t)
                + 0.15 * (rnd.random() * 2 - 1) * math.exp(-t * 12)
            ) * env
            samples.append(val * 0.7)
    elif sfx_type == "data":
        # High-tech HUD scanner beeps
        dur = 0.55
        for i in range(int(sr * dur)):
            t = i / sr
            step = int(t * 18)
            freq = 880 + (step % 4) * 220
            env = 0.35 if (t * 18) % 1.0 < 0.65 else 0.0
            samples.append(math.sin(2 * math.pi * freq * t) * env)
    elif sfx_type == "electric":
        # 860V high-voltage crackle & zap
        dur = 1.1
        for i in range(int(sr * dur)):
            t = i / sr
            env = math.exp(-t * 2.2)
            mod = math.sin(2 * math.pi * 45 * t)
            zap = math.sin(2 * math.pi * (320 + 600 * mod) * t)
            noise = (rnd.random() * 2 - 1) * (1.0 if rnd.random() > 0.3 else 0.2)
            samples.append((0.55 * zap + 0.45 * noise) * env * 0.75)
    elif sfx_type == "hit":
        # Heavy physical strike / bite crunch
        dur = 0.5
        for i in range(int(sr * dur)):
            t = i / sr
            env = math.exp(-t * 9.0)
            low = math.sin(2 * math.pi * (140 * math.exp(-t * 6) + 40) * t)
            crunch = (rnd.random() * 2 - 1) * math.exp(-t * 14)
            samples.append((0.65 * low + 0.5 * crunch) * env * 0.85)
    elif sfx_type == "alarm":
        # Danger / Plot Twist siren
        dur = 0.9
        for i in range(int(sr * dur)):
            t = i / sr
            cycle = (t * 4.0) % 1.0
            freq = 600 + 450 * cycle
            samples.append(math.sin(2 * math.pi * freq * t) * 0.45 * math.exp(-t * 1.2))
    elif sfx_type == "ko":
        # K.O. double explosion bell
        dur = 1.4
        for i in range(int(sr * dur)):
            t = i / sr
            env = math.exp(-t * 2.5)
            bell = math.sin(2 * math.pi * 520 * t) + 0.5 * math.sin(2 * math.pi * 780 * t)
            boom = math.sin(2 * math.pi * 65 * t) * math.exp(-t * 4)
            samples.append((0.4 * bell + 0.6 * boom) * env * 0.8)
    else:
        return None

    write_wav(output_wav, samples, sr)
    return output_wav


def generate_driving_battle_bgm(output_mp3: Path, duration_sec: float = 160.0) -> Path:
    """Synthesize an energetic 128 BPM electronic battle beat with bassline and hi-hats."""
    sr = 22050
    bpm = 128.0
    beat_dur = 60.0 / bpm
    loop_beats = 16
    loop_dur = loop_beats * beat_dur
    total_samples = int(sr * loop_dur)

    import random as rnd
    rnd.seed(42)

    bass_notes = [55.0, 55.0, 65.41, 55.0, 73.42, 65.41, 49.0, 55.0] * 2
    loop_samples: List[float] = []

    for i in range(total_samples):
        t = i / sr
        beat_idx = int(t / beat_dur)
        beat_pos = (t % beat_dur) / beat_dur

        # Kick drum on every beat
        kick_env = math.exp(-beat_pos * 14.0)
        kick_freq = 120.0 * math.exp(-beat_pos * 18.0) + 42.0
        kick = 0.55 * math.sin(2 * math.pi * kick_freq * t) * kick_env

        # Off-beat hi-hat
        sub_pos = ((t + beat_dur / 2) % beat_dur) / beat_dur
        hat_env = math.exp(-sub_pos * 35.0)
        hat = 0.18 * (rnd.random() * 2 - 1) * hat_env

        # Driving saw-like bassline (1/8th notes)
        eighth_pos = (t % (beat_dur / 2)) / (beat_dur / 2)
        b_freq = bass_notes[beat_idx % len(bass_notes)]
        bass_env = math.exp(-eighth_pos * 4.5)
        bass = (
            0.28 * math.sin(2 * math.pi * b_freq * t)
            + 0.14 * math.sin(2 * math.pi * (b_freq * 2) * t)
        ) * bass_env

        # Tense minor synth chord pad
        pad = (
            0.06 * math.sin(2 * math.pi * 220.0 * t)
            + 0.05 * math.sin(2 * math.pi * 261.63 * t)
            + 0.05 * math.sin(2 * math.pi * 329.63 * t)
        )

        loop_samples.append(max(-1.0, min(1.0, kick + hat + bass + pad)))

    wav_loop = output_mp3.with_suffix(".wav")
    write_wav(wav_loop, loop_samples, sr)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(wav_loop),
            "-t",
            f"{duration_sec:.1f}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(output_mp3),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return output_mp3


# ==============================================================================
# Dialogue Script for Battle 006 (Fast-Paced 2-Host Broadcast + HUD States)
# ==============================================================================
BATTLE_006_SHOW_BEATS: List[Dict[str, Any]] = [
    # --- Scene 1: Mystery Incident Hook (Flow Clip 1) ---
    {
        "visual_key": "scene_01",
        "flow_clip": "battle_006_clip1.mp4",
        "image_prompt": "Dramatic comic book wildlife art, giant 1.8m ferocious Amazon river otter standing over a defeated caiman crocodile on a dark misty riverbank, glowing eyes, intense contrast, 16:9",
        "speaker": "announcer",
        "voice": "ja-JP-KeitaNeural",
        "rate": "+20%",
        "text": "緊急レポート！南米アマゾンの川岸で、全身の鱗を噛み砕かれた体長2メートルのワニの死体が発見された！犯人はジャガーじゃない、なんと私たちが水族館で可愛いと撫でている『カワウソ』の仲間だ！",
        "subtitle": "【緊急報告】アマゾンでワニの惨殺死体を発見！\n犯人は…水族館で人気の「カワウソ」の仲間だった！？",
        "banner": "FILE 06: アマゾン水辺の異常事件",
        "banner_color": (220, 38, 38),
        "hp_left": 100,
        "hp_right": 100,
        "sfx": "gong",
        "hud_mode": "battle",
    },
    {
        "visual_key": "scene_01",
        "flow_clip": "battle_006_clip1.mp4",
        "image_prompt": "Dramatic comic book wildlife art, giant 1.8m ferocious Amazon river otter standing over a defeated caiman crocodile on a dark misty riverbank, glowing eyes, intense contrast, 16:9",
        "speaker": "analyst",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+16%",
        "text": "それがアマゾン最凶の見た目詐欺モンスター『オオカワウソ』よ。でもそんな川の覇者ですら、川底から『860ボルトの黒い影』が浮上した瞬間、ピタリと動きを止めるの。",
        "subtitle": "解説：正体はアマゾン最凶の「オオカワウソ」。\nだがその狂獣すら、川底から「860Vの影」が現れると凍りつく！",
        "banner": "オオカワウソ vs デンキウナギ",
        "banner_color": (37, 99, 235),
        "hp_left": 100,
        "hp_right": 100,
        "sfx": "electric",
        "hud_mode": "battle",
    },
    # --- Scene 2: Fighter 1 Spec Card (Giant Otter) ---
    {
        "visual_key": "scene_02",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book close-up of a monstrous 1.8m Giant River Otter roaring with massive canine fangs, dark jungle background, 16:9",
        "speaker": "announcer",
        "voice": "ja-JP-KeitaNeural",
        "rate": "+20%",
        "text": "まずは赤コーナー！コツメカワウソの10倍デカい、全長1.8メートル・体重32キロの怪物オオカワウソ！現地名は『川のオオカミ』、ワニの頭蓋骨をポテトチップスみたいに噛み砕く顎を持っているぞ！",
        "subtitle": "【赤コーナー：オオカワウソ】全長1.8m・体重32kg！\nワニの頭骨をポテトチップスのように砕く「川のオオカミ」！",
        "banner": "FIGHTER DATA: オオカワウソ",
        "banner_color": (234, 88, 12),
        "hp_left": 100,
        "hp_right": 100,
        "sfx": "data",
        "hud_mode": "card_left",
    },
    {
        "visual_key": "scene_02",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book close-up of a monstrous 1.8m Giant River Otter roaring with massive canine fangs, dark jungle background, 16:9",
        "speaker": "analyst",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+16%",
        "text": "しかも最大の武器は『1平方センチに10万本の超高密度毛皮』ね。毛の間に分厚い空気の層を閉じ込めているから、水中でも電気を通しにくい天然の絶縁ラバースーツを着ているようなものよ！",
        "subtitle": "解説：さらに「1㎠に10万本の超高密度毛皮」を装備！\n毛の間の「空気バリア」が電気を弾く天然の絶縁スーツになる！",
        "banner": "特殊防御：空気層の絶縁バリア毛皮",
        "banner_color": (16, 185, 129),
        "hp_left": 100,
        "hp_right": 100,
        "sfx": "data",
        "hud_mode": "card_left",
    },
    # --- Scene 3: Fighter 2 Spec Card (Electric Eel) ---
    {
        "visual_key": "scene_03",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book illustration of a giant 2.4m Electric Eel glowing with blue lightning arcs in dark Amazon water, 16:9",
        "speaker": "announcer",
        "voice": "ja-JP-KeitaNeural",
        "rate": "+20%",
        "text": "対する青コーナー！全長2.4メートル、体の80パーセントが発電バッテリーでできている生体兵器『デンキウナギ・ボルタイ』！その電圧は家庭用コンセントの8.6倍、なんと860ボルトだァ！",
        "subtitle": "【青コーナー：デンキウナギ】全長2.4mの80%が発電器官！\n家庭用電源の8.6倍「最大860ボルト」の電流を放つ生体兵器！",
        "banner": "FIGHTER DATA: デンキウナギ (860V)",
        "banner_color": (37, 99, 235),
        "hp_left": 100,
        "hp_right": 100,
        "sfx": "electric",
        "hud_mode": "card_right",
    },
    {
        "visual_key": "scene_03",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book illustration of a giant 2.4m Electric Eel glowing with blue lightning arcs in dark Amazon water, 16:9",
        "speaker": "analyst",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+16%",
        "text": "川を渡ろうとした馬すら一撃で失神させて溺れさせた記録があるわ。さあ、空気バリアの毛皮を持つカワウソか、860ボルトの電撃か？実はこの戦い、最後の1秒で『残酷な物理トラップ』が発動するの！",
        "subtitle": "【予想タイム】空気バリアのカワウソ vs 860Vウナギ！\n実は最後の1秒で「残酷な物理トラップ」が発動する…！",
        "banner": "PREDICTION TIME: 勝つのはどっちだ！？",
        "banner_color": (168, 85, 247),
        "hp_left": 100,
        "hp_right": 100,
        "sfx": "alarm",
        "hud_mode": "vs_table",
    },
    # --- Scene 4: Round 1 Clash (Flow Clip 2) ---
    {
        "visual_key": "scene_04",
        "flow_clip": "battle_006_clip2.mp4",
        "image_prompt": "Dramatic comic book action, Giant River Otter slashing at an Electric Eel in shallow water while blue lightning explodes outward, 16:9",
        "speaker": "announcer",
        "voice": "ja-JP-KeitaNeural",
        "rate": "+22%",
        "text": "水深40センチの浅瀬でゴングが鳴った！オオカワウソが時速15キロの猛スピードでウナギの尻尾を引っ掻いた！直後、デンキウナギの860ボルト水中放電が炸裂ァァ！",
        "subtitle": "【ROUND 1】カワウソが超高速でウナギの尻尾を奇襲！\n直後、ウナギの「860V水中放電」が浅瀬に炸裂したァァ！",
        "banner": "★ 860V UNDERWATER DISCHARGE!!",
        "banner_color": (234, 179, 8),
        "hp_left": 92,
        "hp_right": 85,
        "sfx": "electric",
        "hud_mode": "battle",
    },
    {
        "visual_key": "scene_04",
        "flow_clip": "battle_006_clip2.mp4",
        "image_prompt": "Dramatic comic book action, Giant River Otter slashing at an Electric Eel in shallow water while blue lightning explodes outward, 16:9",
        "speaker": "analyst",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+18%",
        "text": "ところが見て！カワウソはピンピンして砂州へ飛び退いたわ！真水は電流が拡散しやすいうえ、カワウソの毛皮の『空気バリア』がゴム合羽みたいに水中電流をブロックしたのよ！",
        "subtitle": "解説：なんとカワウソはノーダメージで飛び退いた！\n真水での電流拡散＋「毛皮の空気バリア」が電撃を無効化！",
        "banner": "GUARD SUCCESS! 空気バリアで電撃無効化",
        "banner_color": (16, 185, 129),
        "hp_left": 92,
        "hp_right": 75,
        "sfx": "hit",
        "hud_mode": "battle",
    },
    # --- Scene 5: Otter Dominates & Eel's Weakness ---
    {
        "visual_key": "scene_05",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book art, clever Giant River Otter circling rapidly kicking up mud around an exhausted gasping Electric Eel, 16:9",
        "speaker": "announcer",
        "voice": "ja-JP-KeitaNeural",
        "rate": "+22%",
        "text": "ここからオオカワウソの圧倒的ペースだ！泥水を蹴り上げてフェイントをかけ、ウナギに空撃ちの放電を連発させているぞ！ウナギの電力ゲージがどんどん減っていく！",
        "subtitle": "【ROUND 2】カワウソが頭脳戦のフェイントで圧倒！\nウナギに空撃ち放電を連発させ、バッテリーを削り取る！",
        "banner": "OTTER DOMINATING! ウナギ電力低下",
        "banner_color": (234, 88, 12),
        "hp_left": 92,
        "hp_right": 45,
        "sfx": "hit",
        "hud_mode": "battle",
    },
    {
        "visual_key": "scene_05",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book art, clever Giant River Otter circling rapidly kicking up mud around an exhausted gasping Electric Eel, 16:9",
        "speaker": "analyst",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+18%",
        "text": "実はデンキウナギは10分に1回、水面に顔を出して空気を吸わないと溺れる弱点があるの。ほら、酸素が切れたウナギが苦しそうに水面へ頭を出したわ！",
        "subtitle": "解説：ウナギは「10分に1回、水面で息継ぎ」しないと溺れる！\nついに酸素が切れたウナギが、無防備な頭を水面に出した！",
        "banner": "CHANCE!! ウナギが息継ぎで無防備に！",
        "banner_color": (220, 38, 38),
        "hp_left": 92,
        "hp_right": 25,
        "sfx": "alarm",
        "hud_mode": "battle",
    },
    # --- Scene 6: The Fatal Bite & Plot Twist (Flow Clip 3) ---
    {
        "visual_key": "scene_06",
        "flow_clip": "battle_006_clip3.mp4",
        "image_prompt": "Dramatic comic book climax, Giant River Otter biting the Electric Eel's neck as massive 860V blue lightning surges straight through the otter's mouth and brain, 16:9",
        "speaker": "announcer",
        "voice": "ja-JP-KeitaNeural",
        "rate": "+22%",
        "text": "その隙を逃さない！オオカワウソが死角から飛びかかり、ウナギの首の後ろに勝利の牙を突き立てたァ！勝負あり、カワウソの圧勝かァァ！？",
        "subtitle": "カワウソがウナギの首筋へ「トドメの噛みつき」を決めた！\n勝負あり！オオカワウソの圧勝だ——誰もがそう思った瞬間！",
        "banner": "FINISHING BLOW!? 首筋へ渾身の噛みつき！",
        "banner_color": (234, 88, 12),
        "hp_left": 92,
        "hp_right": 12,
        "sfx": "hit",
        "hud_mode": "battle",
    },
    {
        "visual_key": "scene_06",
        "flow_clip": "battle_006_clip3.mp4",
        "image_prompt": "Dramatic comic book climax, Giant River Otter biting the Electric Eel's neck as massive 860V blue lightning surges straight through the otter's mouth and brain, 16:9",
        "speaker": "analyst",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+18%",
        "text": "待って！カワウソの体が噛みついたまま完全に凍りついたわ！外側の毛皮は電気を防げても、噛みついた『口の中の濡れた歯茎と舌』には毛が1本も生えていないのよ！",
        "subtitle": "【大逆転トラップ発動】噛みついた瞬間、カワウソが凍りついた！？\n毛皮は絶縁でも「口の中の濡れた歯茎と舌」は無防備だった！",
        "banner": "CRITICAL TRAP!! 口腔粘膜から860V逆流！",
        "banner_color": (220, 38, 38),
        "hp_left": 15,
        "hp_right": 12,
        "sfx": "electric",
        "hud_mode": "battle",
    },
    # --- Scene 7: Tetanic Lock & K.O. Verdict ---
    {
        "visual_key": "scene_07",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book X-ray shock illustration, 860V current locking the otter's jaw muscles and paralyzing its nervous system in shallow water, 16:9",
        "speaker": "announcer",
        "voice": "ja-JP-KeitaNeural",
        "rate": "+20%",
        "text": "な、なんだってェ！？牙を通じて860ボルトが口の中から数センチ先の脳幹と心臓へダイレクトに逆流している！でも危ないなら口を離して逃げればいいんじゃないのか！？",
        "subtitle": "実況：口の中から脳幹と心臓へ860Vがダイレクト直撃！\nなぜカワウソは口を離して逃げないんだ！？",
        "banner": "DANGER!! 顎の筋肉が「強直麻痺」でロック！",
        "banner_color": (220, 38, 38),
        "hp_left": 0,
        "hp_right": 12,
        "sfx": "electric",
        "hud_mode": "battle",
    },
    {
        "visual_key": "scene_07",
        "flow_clip": None,
        "image_prompt": "Dramatic comic book X-ray shock illustration, 860V current locking the otter's jaw muscles and paralyzing its nervous system in shallow water, 16:9",
        "speaker": "analyst",
        "voice": "ja-JP-NanamiNeural",
        "rate": "+16%",
        "text": "無理よ！高圧電流が顎の筋肉に流れると『強直麻痺』が起きて、自分の意思では1ミリも口を開けられなくなるの！最後に口で噛みつくしかない肉食獣の宿命が自爆スイッチになり、デンキウナギの大逆転K.O.勝利よ！",
        "subtitle": "【決着：デンキウナギ大逆転K.O.勝利！】\n高圧電流で顎がロックし離せない！「口で噛む宿命」が自爆スイッチに！",
        "banner": "WINNER: デンキウナギ (大逆転 K.O.!!)",
        "banner_color": (37, 99, 235),
        "hp_left": 0,
        "hp_right": 12,
        "sfx": "ko",
        "hud_mode": "ko",
    },
]


# ==============================================================================
# Visual Asset Fetcher (Local Pre-Generated Art -> Pollinations -> Fallback)
# ==============================================================================
def fetch_visual_image(vkey: str, prompt: str, out_path: Path, seed: int, scene_num: int) -> None:
    local_asset = BASE_DIR / "assets" / "images" / "battle_006" / f"{vkey}.jpg"
    if local_asset.exists():
        import shutil
        shutil.copyfile(local_asset, out_path)
        return

    encoded = urllib.parse.quote(prompt, safe="")
    urls = [
        f"https://image.pollinations.ai/prompt/{encoded}?width={W}&height={H}&nologo=true&seed={seed}&model=flux",
    ]
    headers = {"User-Agent": "Mozilla/5.0 BattleShowEngine/3.0"}
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 2048:
                out_path.write_bytes(resp.content)
                return
        except Exception:
            pass

    img = Image.new("RGB", (W, H), (12, 16, 28))
    img.save(out_path, quality=92)


# ==============================================================================
# Fighting-Game & TV Broadcast HUD Overlay Renderer
# ==============================================================================
def render_broadcast_hud_png(
    beat: Dict[str, Any],
    font_path: str,
    output_png: Path,
) -> None:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    f_small = ImageFont.truetype(font_path, 20)
    f_med = ImageFont.truetype(font_path, 25)
    f_sub = ImageFont.truetype(font_path, 31)
    f_banner = ImageFont.truetype(font_path, 26)
    f_title = ImageFont.truetype(font_path, 42)

    # 1. TOP FIGHTING-GAME HP BAR HUD
    draw.rectangle([(0, 0), (W, 92)], fill=(8, 12, 22, 215))
    draw.line([(0, 92), (W, 92)], fill=(255, 255, 255, 90), width=2)

    hp_l = beat["hp_left"]
    hp_r = beat["hp_right"]

    # Left Fighter: オオカワウソ
    draw.ellipse([(28, 14), (46, 32)], fill=(239, 68, 68, 255))
    draw.text(
        (54, 12),
        "オオカワウソ (32kg / 絶縁毛皮)",
        font=f_small,
        fill=(255, 230, 200, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 240),
    )
    bar_w = 470
    bar_h = 26
    draw.rectangle([(28, 42), (28 + bar_w, 42 + bar_h)], fill=(45, 50, 60, 240), outline=(255, 255, 255, 180), width=2)
    fill_l = int(bar_w * (hp_l / 100.0))
    col_l = (34, 197, 94, 255) if hp_l > 40 else (239, 68, 68, 255)
    if fill_l > 0:
        draw.rectangle([(30, 44), (28 + fill_l, 40 + bar_h)], fill=col_l)
    draw.text((38, 43), f"HP {hp_l}%", font=f_small, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 220))

    # Center "VS" badge
    draw.ellipse([(W // 2 - 36, 14), (W // 2 + 36, 82)], fill=(220, 38, 38, 245), outline=(255, 215, 0, 255), width=3)
    draw.text((W // 2 - 22, 32), "VS", font=f_banner, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))

    # Right Fighter: デンキウナギ
    rx0 = W - 28 - bar_w
    draw.ellipse([(rx0, 14), (rx0 + 18, 32)], fill=(59, 130, 246, 255))
    draw.text(
        (rx0 + 26, 12),
        "デンキウナギ (22kg / 最大860V)",
        font=f_small,
        fill=(200, 230, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 240),
    )
    draw.rectangle([(rx0, 42), (rx0 + bar_w, 42 + bar_h)], fill=(45, 50, 60, 240), outline=(255, 255, 255, 180), width=2)
    fill_r = int(bar_w * (hp_r / 100.0))
    col_r = (59, 130, 246, 255) if hp_r > 30 else (234, 179, 8, 255)
    if fill_r > 0:
        draw.rectangle([(rx0 + bar_w - fill_r, 44), (rx0 + bar_w - 2, 40 + bar_h)], fill=col_r)
    draw.text((rx0 + bar_w - 115, 43), f"電力 {hp_r}%", font=f_small, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 220))

    # 2. TOP-LEFT EVENT BANNER PILL
    banner_txt = beat.get("banner", "")
    if banner_txt:
        b_col = beat.get("banner_color", (220, 38, 38))
        tb = draw.textbbox((0, 0), banner_txt, font=f_banner)
        bw = (tb[2] - tb[0]) + 44
        draw.rectangle([(28, 106), (28 + bw, 152)], fill=(*b_col, 235), outline=(255, 255, 255, 220), width=2)
        draw.text((48, 114), banner_txt, font=f_banner, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 220))

    # 3. CENTER SPEC CARDS / VS TABLE / K.O. STAMP
    hud_mode = beat.get("hud_mode", "battle")
    if hud_mode == "card_left":
        draw.rectangle([(60, 175), (640, 495)], fill=(15, 23, 42, 215), outline=(249, 115, 22, 255), width=3)
        rows = [
            "【赤コーナー：オオカワウソ】",
            "・体格：全長 1.8m / 体重 32kg",
            "・攻撃：咬合力 ワニ頭骨粉砕クラス",
            "・防御：1㎠に10万本の空気バリア毛皮",
            "・知能：群れ戦術＆急所狙い ランクS",
        ]
        for idx, r in enumerate(rows):
            draw.text((85, 198 + idx * 54), r, font=f_med, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 220))

    elif hud_mode == "card_right":
        draw.rectangle([(640, 175), (1220, 495)], fill=(15, 23, 42, 215), outline=(59, 130, 246, 255), width=3)
        rows = [
            "【青コーナー：デンキウナギ】",
            "・体格：全長 2.4m / 体重 22kg",
            "・特殊能力：最大 860V 高圧電流放電",
            "・構造：体長の80%が発電バッテリー",
            "・弱点：10分に1回の水面空気呼吸が必須",
        ]
        for idx, r in enumerate(rows):
            draw.text((665, 198 + idx * 54), r, font=f_med, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 220))

    elif hud_mode == "vs_table":
        draw.rectangle([(180, 175), (1100, 495)], fill=(15, 23, 42, 225), outline=(168, 85, 247, 255), width=3)
        rows = [
            "項目          オオカワウソ(32kg)   vs   デンキウナギ(22kg)",
            "────────────────────────────────────────",
            "メイン武器    ワニ砕きの牙・爪     vs   860V 超高圧電撃",
            "防御・耐性    空気層の絶縁毛皮     vs   厚い絶縁脂肪層",
            "スピード      水中時速15km(敏捷)   vs   待ち伏せ・跳躍放電",
            "勝敗のカギ    息継ぎの隙を噛めるか vs   口腔粘膜へのカウンター",
        ]
        for idx, r in enumerate(rows):
            col = (253, 224, 71, 255) if idx in (0, 5) else (255, 255, 255, 255)
            draw.text((215, 195 + idx * 46), r, font=f_med, fill=col, stroke_width=2, stroke_fill=(0, 0, 0, 220))

    elif hud_mode == "ko":
        draw.rectangle([(260, 245), (1020, 415)], fill=(185, 28, 28, 225), outline=(253, 224, 71, 255), width=5)
        draw.text(
            (315, 280),
            "★ K.O.!! 口腔粘膜ショート決着 ★",
            font=f_title,
            fill=(255, 255, 255, 255),
            stroke_width=3,
            stroke_fill=(0, 0, 0, 255),
        )
        draw.text(
            (375, 348),
            "勝者：デンキウナギ（1対1 勝率80%）",
            font=f_banner,
            fill=(253, 224, 71, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 240),
        )

    # 4. BOTTOM SUBTITLE BAR WITH SPEAKER TAG
    bar_h = 165
    bar_y0 = H - bar_h
    draw.rectangle([(0, bar_y0), (W, H)], fill=(6, 10, 18, 210))

    is_announcer = beat["speaker"] == "announcer"
    spk_label = "【熱血実況】" if is_announcer else "【科学解説】"
    spk_col = (239, 68, 68, 255) if is_announcer else (14, 165, 233, 255)

    draw.rectangle([(28, bar_y0 - 20), (195, bar_y0 + 22)], fill=spk_col, outline=(255, 255, 255, 230), width=2)
    draw.text((42, bar_y0 - 13), spk_label, font=f_small, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 220))

    lines = beat["subtitle"].split("\n")
    line_spacing = 12
    total_h = len(lines) * 34 + (len(lines) - 1) * line_spacing
    cur_y = bar_y0 + (bar_h - total_h) // 2 + 8

    for line in lines:
        tb = draw.textbbox((0, 0), line, font=f_sub)
        lw = tb[2] - tb[0]
        x = (W - lw) // 2
        txt_col = (255, 255, 255, 255) if is_announcer else (224, 242, 254, 255)
        draw.text(
            (x, cur_y),
            line,
            font=f_sub,
            fill=txt_col,
            stroke_width=3,
            stroke_fill=(0, 0, 0, 245),
        )
        cur_y += 34 + line_spacing

    overlay.save(output_png, "PNG")


async def generate_beat_tts(text: str, voice: str, rate: str, out_mp3: Path) -> None:
    comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await comm.save(str(out_mp3))


def get_duration(path: Path) -> float:
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(float(res.stdout.strip()), 0.8)


def build_show() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    font_path = find_cjk_font()
    final_mp4 = OUTPUT_DIR / "animal_battle_battle_006_show.mp4"

    with tempfile.TemporaryDirectory(prefix="yt_show_") as tmp_str:
        work_dir = Path(tmp_str)
        visual_cache: Dict[str, Path] = {}
        beat_videos: List[Path] = []

        for idx, beat in enumerate(BATTLE_006_SHOW_BEATS):
            logger.info(f"Building Beat {idx + 1}/{len(BATTLE_006_SHOW_BEATS)}: {beat['banner']}")
            vkey = beat["visual_key"]
            if vkey not in visual_cache:
                img_path = work_dir / f"{vkey}.jpg"
                fetch_visual_image(
                    vkey, beat["image_prompt"], img_path, seed=600 + idx * 17, scene_num=idx
                )
                visual_cache[vkey] = img_path
            bg_img = visual_cache[vkey]

            tts_mp3 = work_dir / f"tts_{idx:02d}.mp3"
            asyncio.run(
                generate_beat_tts(beat["text"], beat["voice"], beat["rate"], tts_mp3)
            )

            # Mix SFX at the start of the beat audio if configured
            sfx_name = beat.get("sfx")
            mixed_audio = work_dir / f"audio_{idx:02d}.m4a"
            if sfx_name:
                sfx_wav = work_dir / f"sfx_{idx:02d}.wav"
                generate_sfx(sfx_name, sfx_wav)
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(tts_mp3),
                        "-i",
                        str(sfx_wav),
                        "-filter_complex",
                        "[0:a]volume=1.0[v];[1:a]volume=0.45[s];[v][s]amix=inputs=2:duration=first:normalize=0[aout]",
                        "-map",
                        "[aout]",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        str(mixed_audio),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(tts_mp3),
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        str(mixed_audio),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            dur = round(get_duration(mixed_audio) + 0.15, 3)
            frames = max(int(math.ceil(dur * FPS)), FPS)

            hud_png = work_dir / f"hud_{idx:02d}.png"
            render_broadcast_hud_png(beat, font_path, hud_png)

            flow_clip_name = beat.get("flow_clip")
            flow_path = (
                FLOW_CLIPS_DIR / flow_clip_name if flow_clip_name else None
            )

            beat_mp4 = work_dir / f"beat_{idx:02d}.mp4"
            if flow_path and flow_path.exists():
                vf = (
                    f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H},fps={FPS}[bg];"
                    f"[bg][1:v]overlay=0:0,format=yuv420p[vout]"
                )
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(flow_path),
                    "-i",
                    str(hud_png),
                    "-i",
                    str(mixed_audio),
                    "-filter_complex",
                    vf,
                    "-map",
                    "[vout]",
                    "-map",
                    "2:a",
                    "-t",
                    f"{dur:.3f}",
                    "-r",
                    str(FPS),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "20",
                    "-c:a",
                    "copy",
                    "-shortest",
                    str(beat_mp4),
                ]
            else:
                # Dynamic camera motion alternating zoom-in, pan, and shake on hits
                if idx % 2 == 0:
                    zp = f"zoompan=z='min(zoom+0.0022,1.22)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
                else:
                    zp = f"zoompan=z='1.18':x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
                vf = (
                    f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
                    f"crop={W*2}:{H*2},{zp}[bg];"
                    f"[bg][1:v]overlay=0:0,format=yuv420p[vout]"
                )
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(bg_img),
                    "-i",
                    str(hud_png),
                    "-i",
                    str(mixed_audio),
                    "-filter_complex",
                    vf,
                    "-map",
                    "[vout]",
                    "-map",
                    "2:a",
                    "-t",
                    f"{dur:.3f}",
                    "-r",
                    str(FPS),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "20",
                    "-c:a",
                    "copy",
                    "-shortest",
                    str(beat_mp4),
                ]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            beat_videos.append(beat_mp4)

        # Concatenate all 14 fast-paced beats
        concat_txt = work_dir / "concat.txt"
        concat_txt.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in beat_videos) + "\n",
            encoding="utf-8",
        )
        merged_mp4 = work_dir / "merged.mp4"
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
                "-c",
                "copy",
                str(merged_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        total_dur = get_duration(merged_mp4)
        bgm_mp3 = work_dir / "battle_bgm.mp3"
        generate_driving_battle_bgm(bgm_mp3, duration_sec=total_dur + 5.0)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(merged_mp4),
                "-i",
                str(bgm_mp3),
                "-filter_complex",
                "[0:a]volume=1.0[v];[1:a]volume=0.22[b];[v][b]amix=inputs=2:duration=first:normalize=0[aout]",
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
                str(final_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    logger.info(f"Completed Battle Show MP4: {final_mp4}")
    return final_mp4


if __name__ == "__main__":
    build_show()
