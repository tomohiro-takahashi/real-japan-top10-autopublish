# Google Flow 動画生成タスクリスト (`FLOW_TASKS.md`)

月に1回、以下の英語プロンプトを **Google Flow** にコピペして5秒間のMP4クリップを生成し、指定のファイル名で [`assets/flow_clips/`](file:///Users/takahashitomohiro/Desktop/Youtube%20PJ/assets/flow_clips) フォルダに保存してください。
（※もしファイルが未配置の場合でも、動画生成スクリプト側で自動的に `fallback_image_prompt` から劇画風画像を生成してエフェクト付きで繋ぐ安全設計になっています）

---

## 一覧表（全5本 × 3クリップ ＝ 計15クリップ）

| 台本ID | 対戦カード | シーン | 保存ファイル名 (`assets/flow_clips/` 内) | Google Flow コピペ用プロンプト (5秒・16:9) |
| :--- | :--- | :---: | :--- | :--- |
| `battle_001` | ラーテル vs コモドオオトカゲ | Scene 1 (対峙と威嚇) | `battle_001_clip1.mp4` | `Photorealistic National Geographic wildlife cinematography, 4k, harsh midday sunlight on a dry rocky savanna steppes. A honey badger with black and white fur stands in a low aggressive stance, snarling up at a massive 3-meter Komodo dragon flicking its yellow forked tongue. Low camera angle slowly pushing in, dust blowing across rocks, intense 5-second shot.` |
| `battle_001` | ラーテル vs コモドオオトカゲ | Scene 5 (最初の激突) | `battle_001_clip2.mp4` | `Photorealistic wildlife action shot, 4k cinematic slow motion. A giant Komodo dragon whips its thick muscular tail across dry dirt, knocking a honey badger sideways, and the honey badger immediately scrambles back up and charges straight at the dragon's open jaws. Dust clouds exploding, 5-second dynamic shot.` |
| `battle_001` | ラーテル vs コモドオオトカゲ | Scene 8 (決定打の一撃) | `battle_001_clip3.mp4` | `Photorealistic National Geographic footage, 4k intense close-up. The massive 80kg Komodo dragon uses its heavy body and clawed forelegs to pin the smaller 14kg honey badger firmly against the rocky ground, shaking its head powerfully as dust rises around them. Cinematic natural lighting, 5-second shot.` |
| `battle_002` | ヒクイドリ vs ドーベルマン | Scene 1 (対峙と威嚇) | `battle_002_clip1.mp4` | `Photorealistic National Geographic wildlife footage, 4k, dappled sunlight at the edge of a tropical rainforest clearing. A tall Southern Cassowary with vivid blue neck skin and a helmet-like casque stares down a muscular black-and-tan Doberman Pinscher barking fiercely with bared teeth. Tense 5-second camera tracking shot.` |
| `battle_002` | ヒクイドリ vs ドーベルマン | Scene 5 (最初の激突) | `battle_002_clip2.mp4` | `Photorealistic high-speed wildlife cinematography, 4k slow motion. A Doberman lunges forward to bite, and a giant Southern Cassowary leaps vertically into the air, thrusting both powerful scaly legs forward into the dog's chest in mid-air. Dirt and leaves flying, intense 5-second shot.` |
| `battle_002` | ヒクイドリ vs ドーベルマン | Scene 8 (決定打の一撃) | `battle_002_clip3.mp4` | `Photorealistic dramatic wildlife shot, 4k. The giant Southern Cassowary slams its massive three-toed foot with the 12cm inner dagger claw forcefully downward, pinning the Doberman to the forest floor in a cloud of dust. Intense cinematic lighting, 5-second shot.` |
| `battle_003` | クズリ vs ブチハイエナ | Scene 1 (対峙と威嚇) | `battle_003_clip1.mp4` | `Photorealistic National Geographic wildlife footage, 4k, overcast twilight on a rocky grassland border. A fierce thick-furred Wolverine snarls defensively over a carcass as a massive Spotted Hyena with sloping shoulders and powerful jaws approaches menacingly, ears cocked forward. Tense 5-second camera pan.` |
| `battle_003` | クズリ vs ブチハイエナ | Scene 5 (最初の激突) | `battle_003_clip2.mp4` | `Photorealistic wildlife combat footage, 4k slow motion. A ferocious Wolverine lunges upward clawing at a Spotted Hyena's snout, and the much larger 70kg Hyena absorbs the hit and slams its heavy chest forward to bowl the Wolverine over in the dirt. Intense 5-second shot.` |
| `battle_003` | クズリ vs ブチハイエナ | Scene 8 (決定打の一撃) | `battle_003_clip3.mp4` | `Photorealistic dramatic wildlife cinematography, 4k. The massive 70kg Spotted Hyena clamps its powerful jaws firmly across the back of the smaller 22kg Wolverine, lifting and shaking it violently across the dusty steppe ground. Intense natural lighting, 5-second shot.` |
| `battle_004` | ホッキョクグマ vs ナイルワニ | Scene 1 (対峙と威嚇) | `battle_004_clip1.mp4` | `Photorealistic National Geographic wildlife footage, 4k, dramatic misty morning light at a shallow 30cm river estuary sandbar. A colossal white Polar Bear stands in ankle-deep water roaring down at a massive 4.5-meter Nile Crocodile hissing with its armored jaws wide open. Water ripples and mist, 5-second cinematic shot.` |
| `battle_004` | ホッキョクグマ vs ナイルワニ | Scene 5 (最初の激突) | `battle_004_clip2.mp4` | `Photorealistic wildlife combat footage, 4k slow motion. A giant Nile Crocodile lunges in shallow water, clamping its jaws onto a Polar Bear's forearm, and the massive Polar Bear plants its hind legs and slams its other huge paw down onto the crocodile's snout, water splashing violently, 5-second shot.` |
| `battle_004` | ホッキョクグマ vs ナイルワニ | Scene 8 (決定打の一撃) | `battle_004_clip3.mp4` | `Photorealistic dramatic wildlife shot, 4k. The colossal 600kg Polar Bear pins the Nile Crocodile down in shallow water with both massive paws holding the reptile's head and neck, driving its powerful jaws straight down into the back of the crocodile's neck. Heavy water spray, 5-second shot.` |
| `battle_005` | 100kgオオスズメバチ vs シベリアトラ | Scene 1 (対峙と威嚇) | `battle_005_clip1.mp4` | `Photorealistic cinematic creature feature & National Geographic style, 4k, sunlit forest clearing. A terrifying giant 100kg Asian Giant Hornet, 1.8 meters long with glossy orange-and-black chitin armor and vibrating wings, hovers low above the grass facing a massive 300kg Siberian Tiger crouching and roaring fiercely. Dust and grass blowing from wing wash, 5-second shot.` |
| `battle_005` | 100kgオオスズメバチ vs シベリアトラ | Scene 5 (最初の激突) | `battle_005_clip2.mp4` | `Photorealistic cinematic action shot, 4k slow motion. The massive 300kg Siberian Tiger leaps and swipes its huge paw, slamming the 100kg Giant Hornet onto the grassy ground, and the armored hornet immediately buzzes its wings and latches its six hooked legs onto the tiger's shoulders. 5-second shot.` |
| `battle_005` | 100kgオオスズメバチ vs シベリアトラ | Scene 8 (決定打の一撃) | `battle_005_clip3.mp4` | `Photorealistic dramatic creature combat shot, 4k. Clinging to the Siberian Tiger's back, the 100kg Giant Hornet arches its striped abdomen and drives its long stinger repeatedly into the roaring tiger's shoulder and flank as the tiger collapses onto the grass. Intense cinematic lighting, 5-second shot.` |
| `battle_006` | オオカワウソ vs デンキウナギ | Scene 1 (対峙と威嚇) | `battle_006_clip1.mp4` | `Photorealistic National Geographic wildlife footage, 4k, humid Amazon riverbank with 40cm shallow murky water. A giant 1.8-meter Giant River Otter with wet glossy brown fur and bared sharp fangs snarls aggressively at a massive 2.4-meter Electric Eel undulating menacingly near the water surface. Tense 5-second shot.` |
| `battle_006` | オオカワウソ vs デンキウナギ | Scene 5 (最初の激突) | `battle_006_clip2.mp4` | `Photorealistic wildlife action shot, 4k slow motion. A Giant River Otter lunges at an Electric Eel in shallow water, and the eel arches its body violently as the otter recoils backward in a massive splash of water onto the muddy bank. Intense 5-second shot.` |
| `battle_006` | オオカワウソ vs デンキウナギ | Scene 8 (決定打の一撃) | `battle_006_clip3.mp4` | `Photorealistic dramatic wildlife cinematography, 4k. As the Giant River Otter bites down onto the thick neck of the Electric Eel in shallow water, the 2.4-meter eel coils its long body tightly around the otter's torso, causing the otter's muscles to lock up rigid and collapse into the shallow water. 5-second shot.` |

---

## 高速コピペ用ブロック（クリップ別）

### 1. `battle_001`（ラーテル vs コモドオオトカゲ）
- **`battle_001_clip1.mp4`** (Scene 1: 対峙と威嚇)
```text
Photorealistic National Geographic wildlife cinematography, 4k, harsh midday sunlight on a dry rocky savanna steppes. A honey badger with black and white fur stands in a low aggressive stance, snarling up at a massive 3-meter Komodo dragon flicking its yellow forked tongue. Low camera angle slowly pushing in, dust blowing across rocks, intense 5-second shot.
```
- **`battle_001_clip2.mp4`** (Scene 5: 最初の激突と攻防)
```text
Photorealistic wildlife action shot, 4k cinematic slow motion. A giant Komodo dragon whips its thick muscular tail across dry dirt, knocking a honey badger sideways, and the honey badger immediately scrambles back up and charges straight at the dragon's open jaws. Dust clouds exploding, 5-second dynamic shot.
```
- **`battle_001_clip3.mp4`** (Scene 8: 決定打となる必殺の一撃)
```text
Photorealistic National Geographic footage, 4k intense close-up. The massive 80kg Komodo dragon uses its heavy body and clawed forelegs to pin the smaller 14kg honey badger firmly against the rocky ground, shaking its head powerfully as dust rises around them. Cinematic natural lighting, 5-second shot.
```

### 2. `battle_002`（ヒクイドリ vs ドーベルマン）
- **`battle_002_clip1.mp4`** (Scene 1: 対峙と威嚇)
```text
Photorealistic National Geographic wildlife footage, 4k, dappled sunlight at the edge of a tropical rainforest clearing. A tall Southern Cassowary with vivid blue neck skin and a helmet-like casque stares down a muscular black-and-tan Doberman Pinscher barking fiercely with bared teeth. Tense 5-second camera tracking shot.
```
- **`battle_002_clip2.mp4`** (Scene 5: 最初の激突と攻防)
```text
Photorealistic high-speed wildlife cinematography, 4k slow motion. A Doberman lunges forward to bite, and a giant Southern Cassowary leaps vertically into the air, thrusting both powerful scaly legs forward into the dog's chest in mid-air. Dirt and leaves flying, intense 5-second shot.
```
- **`battle_002_clip3.mp4`** (Scene 8: 決定打となる必殺の一撃)
```text
Photorealistic dramatic wildlife shot, 4k. The giant Southern Cassowary slams its massive three-toed foot with the 12cm inner dagger claw forcefully downward, pinning the Doberman to the forest floor in a cloud of dust. Intense cinematic lighting, 5-second shot.
```

### 3. `battle_003`（クズリ vs ブチハイエナ）
- **`battle_003_clip1.mp4`** (Scene 1: 対峙と威嚇)
```text
Photorealistic National Geographic wildlife footage, 4k, overcast twilight on a rocky grassland border. A fierce thick-furred Wolverine snarls defensively over a carcass as a massive Spotted Hyena with sloping shoulders and powerful jaws approaches menacingly, ears cocked forward. Tense 5-second camera pan.
```
- **`battle_003_clip2.mp4`** (Scene 5: 最初の激突と攻防)
```text
Photorealistic wildlife combat footage, 4k slow motion. A ferocious Wolverine lunges upward clawing at a Spotted Hyena's snout, and the much larger 70kg Hyena absorbs the hit and slams its heavy chest forward to bowl the Wolverine over in the dirt. Intense 5-second shot.
```
- **`battle_003_clip3.mp4`** (Scene 8: 決定打となる必殺の一撃)
```text
Photorealistic dramatic wildlife cinematography, 4k. The massive 70kg Spotted Hyena clamps its powerful jaws firmly across the back of the smaller 22kg Wolverine, lifting and shaking it violently across the dusty steppe ground. Intense natural lighting, 5-second shot.
```

### 4. `battle_004`（ホッキョクグマ vs ナイルワニ）
- **`battle_004_clip1.mp4`** (Scene 1: 対峙と威嚇)
```text
Photorealistic National Geographic wildlife footage, 4k, dramatic misty morning light at a shallow 30cm river estuary sandbar. A colossal white Polar Bear stands in ankle-deep water roaring down at a massive 4.5-meter Nile Crocodile hissing with its armored jaws wide open. Water ripples and mist, 5-second cinematic shot.
```
- **`battle_004_clip2.mp4`** (Scene 5: 最初の激突と攻防)
```text
Photorealistic wildlife combat footage, 4k slow motion. A giant Nile Crocodile lunges in shallow water, clamping its jaws onto a Polar Bear's forearm, and the massive Polar Bear plants its hind legs and slams its other huge paw down onto the crocodile's snout, water splashing violently, 5-second shot.
```
- **`battle_004_clip3.mp4`** (Scene 8: 決定打となる必殺の一撃)
```text
Photorealistic dramatic wildlife shot, 4k. The colossal 600kg Polar Bear pins the Nile Crocodile down in shallow water with both massive paws holding the reptile's head and neck, driving its powerful jaws straight down into the back of the crocodile's neck. Heavy water spray, 5-second shot.
```

### 5. `battle_005`（体重100kgに巨大化したオオスズメバチ vs シベリアトラ）
- **`battle_005_clip1.mp4`** (Scene 1: 対峙と威嚇)
```text
Photorealistic cinematic creature feature & National Geographic style, 4k, sunlit forest clearing. A terrifying giant 100kg Asian Giant Hornet, 1.8 meters long with glossy orange-and-black chitin armor and vibrating wings, hovers low above the grass facing a massive 300kg Siberian Tiger crouching and roaring fiercely. Dust and grass blowing from wing wash, 5-second shot.
```
- **`battle_005_clip2.mp4`** (Scene 5: 最初の激突と攻防)
```text
Photorealistic cinematic action shot, 4k slow motion. The massive 300kg Siberian Tiger leaps and swipes its huge paw, slamming the 100kg Giant Hornet onto the grassy ground, and the armored hornet immediately buzzes its wings and latches its six hooked legs onto the tiger's shoulders. 5-second shot.
```
- **`battle_005_clip3.mp4`** (Scene 8: 決定打となる必殺の一撃)
```text
Photorealistic dramatic creature combat shot, 4k. Clinging to the Siberian Tiger's back, the 100kg Giant Hornet arches its striped abdomen and drives its long stinger repeatedly into the roaring tiger's shoulder and flank as the tiger collapses onto the grass. Intense cinematic lighting, 5-second shot.
```

### 6. `battle_006`（オオカワウソ vs デンキウナギ）
- **`battle_006_clip1.mp4`** (Scene 1: 対峙と威嚇)
```text
Photorealistic National Geographic wildlife footage, 4k, humid Amazon riverbank with 40cm shallow murky water. A giant 1.8-meter Giant River Otter with wet glossy brown fur and bared sharp fangs snarls aggressively at a massive 2.4-meter Electric Eel undulating menacingly near the water surface. Tense 5-second shot.
```
- **`battle_006_clip2.mp4`** (Scene 5: 最初の激突と攻防)
```text
Photorealistic wildlife action shot, 4k slow motion. A Giant River Otter lunges at an Electric Eel in shallow water, and the eel arches its body violently as the otter recoils backward in a massive splash of water onto the muddy bank. Intense 5-second shot.
```
- **`battle_006_clip3.mp4`** (Scene 8: 決定打となる必殺の一撃)
```text
Photorealistic dramatic wildlife cinematography, 4k. As the Giant River Otter bites down onto the thick neck of the Electric Eel in shallow water, the 2.4-meter eel coils its long body tightly around the otter's torso, causing the otter's muscles to lock up rigid and collapse into the shallow water. 5-second shot.
```
