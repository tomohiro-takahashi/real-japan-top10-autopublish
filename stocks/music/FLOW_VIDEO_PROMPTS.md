# Google Flow (Veo) & AI動画生成ツール用：高速ドライブ・レトロ背景ループ動画プロンプト集

[`build_music_video.py`](file:///Users/takahashitomohiro/Desktop/Youtube%20PJ/build_music_video.py) は、以下のフォルダに `.mp4` 動画を入れておくだけで、**ジャンルに合わせて自動でその高速道路・ネオン街動画を選択し、シームレス（前後Ping-Pongまたはループ）に1時間耐久動画＆ショート動画へ合成**します。

- 保存先フォルダ: [`stocks/music/bg_videos/`](file:///Users/takahashitomohiro/Desktop/Youtube%20PJ/stocks/music/bg_videos)
- ファイル名の付け方（自動でジャンル判定されます）:
  - ユーロビート用: `eurobeat_01.mp4`, `eurobeat_02.mp4` など
  - シティポップ用: `citypop_01.mp4`, `citypop_02.mp4` など
  - 80sディスコ用: `disco_01.mp4`, `disco_02.mp4` など
- ※もし [`stocks/music/bg_videos/`](file:///Users/takahashitomohiro/Desktop/Youtube%20PJ/stocks/music/bg_videos) が空の場合でも、静止画ではなく**Pythonが毎フレーム3D描画する「深夜の首都高・湾岸線 3Dハイウェイ高速走行アニメーション動画」**が自動で生成されます。

---

## 1. 90s Eurobeat 用（首都高C1・深夜ドリフト・頭文字D / 湾岸ミッドナイト風）

### プロンプト①：夜の首都高を猛スピードで疾走する90年代スポーツカー（背面ローアングル）
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 90s retro Japanese anime style, cel-shaded vintage aesthetic, low-angle rear tracking shot of a white 1990s Japanese sports car (AE86 / RX-7 style) speeding fast down the midnight Tokyo Shuto Expressway C1 highway, glowing red tail lights leaving light trails, orange sodium streetlamps and overhead highway signs rushing past overhead at high speed, neon Tokyo city skyscrapers in the background, dynamic speed lines, VHS anime aesthetic, 16:9, 24fps`

### プロンプト②：深夜の峠（箱根・榛名山風）を連続ドリフトで駆け抜けるシーン
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 90s retro anime aesthetic, Initial D style cel-shaded animation, dynamic third-person chase camera following a yellow 1990s JDM coupe drifting around a midnight mountain pass (touge) hairpin corner, guardrails and pine trees rushing past rapidly, headlights cutting through night mist, glowing brake discs, intense sense of speed, 1990s VHS grain, 16:9`

### プロンプト③：夜の高速トンネルを時速200kmで突き抜けるコックピット/ボンネット視点
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 90s retro anime style, first-person hood camera POV driving at extreme speed through a futuristic 1990s Tokyo underground highway tunnel at midnight, rows of warm orange and cyan ceiling lights streaking past endlessly, wet asphalt road reflections, digital retro dashboard glow, Wangan Midnight anime vibe, 16:9`

---

## 2. 90s City Pop 用（夜の湾岸線・レインボーブリッジ・エモい東京夜景ドライブ）

### プロンプト④：夜の東京湾岸線とレインボーブリッジを走るエモい夜景ドライブ
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 90s retro Japanese anime aesthetic, lo-fi vintage cel-shaded illustration, smooth cruising shot of a classic 1990s convertible driving across the Tokyo Rainbow Bridge at midnight, pastel pink and cyan neon city skyline reflecting on the dark ocean water of Tokyo Bay, streetlamps gliding past smoothly, nostalgic warm melancholy atmosphere, 90s anime VHS aesthetic, 16:9`

### プロンプト⑤：雨上がりの深夜の海岸線（湘南・横浜ベイブリッジ風）車窓ループ
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 90s retro anime style, aesthetic side-angle tracking shot of a vintage Japanese coupe cruising along a midnight coastal highway beside the ocean, palm trees and glowing neon convenience store signs passing by in the background, wet road reflecting magenta and turquoise twilight sky, relaxing City Pop mood, 16:9`

### プロンプト⑥：深夜の高層ビル群を抜ける首都高クルーズ（東京タワー夜景）
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 90s retro anime style aesthetic, smooth forward POV driving along an elevated Tokyo expressway at night, glowing red Tokyo Tower and shimmering office building windows passing by on both sides, soft purple and blue night sky, nostalgic 1990s Japanese OVA animation quality, 16:9`

---

## 3. 80s Japanese Boogie Disco 用（1986年バブル期の六本木・ネオン街＆高速クルーズ）

### プロンプト⑦：1986年バブル期の東京・六本木ネオン大通りを走るオープンカー
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 1980s retro Japanese anime aesthetic, vibrant cel-shaded animation, tracking shot of a sleek red 1980s sports car cruising through a dazzling 1986 Roppongi & Ginza neon street at night, giant glowing retro Japanese neon billboards, disco lights, and golden streetlights rushing past, bubble-era Tokyo nightlife energy, 16:9`

### プロンプト⑧：ミラーボールとレーザーが輝く80年代ディスコ・フロア＆夜景ペントハウス
> **Prompt (そのままFlowにコピペ):**
> `Seamless loop, 1980s retro Japanese anime style, inside a luxury 1986 Tokyo penthouse nightclub with floor-to-ceiling windows overlooking the moving neon city highway below, a giant sparkling disco mirror ball rotating slowly at the top, pink and gold laser beams sweeping across the room, vintage 80s city pop & boogie aesthetic, 16:9`
