# Google Flow (Veo) 背景動画生成ガイド (`stocks/music/bg_videos/`)

`build_music_video.py` は **`stocks/music/bg_videos/` に `.mp4` ファイルが存在する場合、最優先（Priority 1）でそのFlow動画を採用** し、自動的に継ぎ目のない **Ping-Pong（順再生＋逆再生）シームレス1時間ループ** に変換します。

さらに、すでに完成している `stocks/music/artworks/` の **6枚の35mm実写フィルム写真** を Google Flow（https://labs.google/fx/tools/flow）の **「Frames to Video（画像から動画生成）」** に入力することで、サムネイルと100%同じ世界観のまま本物の実写映像として動かすことができます。

---

## 6ジャンルの保存ファイル名と Flow 用プロンプト

生成した `.mp4`（5〜8秒）を以下のファイル名で `/Users/takahashitomohiro/Desktop/Youtube PJ/stocks/music/bg_videos/` に保存してください。

### 1. `eurobeat.mp4`（90年代ユーロビート・首都高ナイトドライブ）
- **ベース画像（任意）**: `stocks/music/artworks/eurobeat.jpg`
- **Flow Prompt**:
  ```text
  Subtle cinematic 35mm film motion, POV from inside a dark 1990s Japanese car cockpit cruising smoothly along the midnight Shuto Expressway toward Rainbow Bridge. Warm orange sodium streetlamps glide gently across the wet windshield and dark dashboard, distant red tail lights moving smoothly ahead, calm atmospheric night drive, 24fps film grain, no sudden camera movement.
  ```

### 2. `disco.mp4`（80年代ディスコ＆ブギー・六本木ラウンジ＆レコード）
- **ベース画像（任意）**: `stocks/music/artworks/disco.jpg`
- **Flow Prompt**:
  ```text
  Subtle cinematic 35mm film motion, 1986 Tokyo high-floor bar lounge at night overlooking Tokyo Tower. On the mahogany counter, the vintage Technics vinyl record spins smoothly, warm amber VU meter needles gently bounce to the rhythm, ice in the whiskey glass glints softly, distant city lights shimmer through the window, 24fps film grain.
  ```

### 3. `tkrave.mp4`（90年代シンセダンス・雨の首都高＆カーステレオ）
- **ベース画像（任意）**: `stocks/music/artworks/tkrave.jpg`
- **Flow Prompt**:
  ```text
  Subtle cinematic 35mm film motion, inside a 1995 Japanese car at midnight in the rain. The vintage amber car stereo equalizer bars gently pulse, raindrops slowly trickle down the windshield with soft bokeh reflections of Shinjuku skyscrapers and red tail lights in the background, calm nostalgic mood, 24fps.
  ```

### 4. `citypop80s.mp4`（80年代シティポップ＆AOR・夕暮れの湘南R134）
- **ベース画像（任意）**: `stocks/music/artworks/citypop80s.jpg`
- **Flow Prompt**:
  ```text
  Subtle cinematic 35mm film motion, 1985 Shonan Route 134 coastal highway at deep twilight blue hour. Gentle ocean waves roll onto the shore in the distance, palm trees sway very softly in the evening breeze, warm sodium highway lamps glow steadily along the coast, nostalgic 1980s Japanese AOR album atmosphere, 24fps.
  ```

### 5. `urban90s.mp4`（90年代アーバンメロウ・深夜の書斎＆カセットデッキ）
- **ベース画像（任意）**: `stocks/music/artworks/urban90s.jpg`
- **Flow Prompt**:
  ```text
  Subtle cinematic 35mm film motion, close-up of a vintage brushed-aluminum cassette tape deck on a dark walnut desk at night. The cassette tape reels turn slowly and steadily, warm amber analog VU meter needles sway gently, soft rain trickles down the window glass in the blurred Tokyo night background, 24fps.
  ```

### 6. `arcade.mp4`（80-90年代湾岸フュージョン・アナログタコメーター）
- **ベース画像（任意）**: `stocks/music/artworks/arcade.jpg`
- **Flow Prompt**:
  ```text
  Subtle cinematic 35mm film motion, close-up of a late-1980s Japanese sports coupe dashboard entering a midnight highway tunnel. The warm amber analog tachometer needle hovers and subtly responds around 4500 RPM, warm orange tunnel ceiling lights glide smoothly across the windshield glass, 24fps film look.
  ```
