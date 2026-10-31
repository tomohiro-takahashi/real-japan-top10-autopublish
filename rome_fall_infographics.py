#!/usr/bin/env python3
"""
rome_fall_infographics.py

Renders 8 museum-grade 1280x720 historical infographic, data chart, and multi-theory
comparison boards (`diagram_01.png` .. `diagram_08.png`) plus 8 dramatic Question
Close-Up cards (`q_01.png` .. `q_08.png`) for Episode 2:
"Why Did the Roman Empire Fall? (210 Theories & Scientific Evidence)".
"""

import subprocess
from pathlib import Path
from typing import Dict, Tuple
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from build_japan_ranking import draw_rounded_box, find_cjk_font
from history_infographics import _base_board, _fit_font

W, H = 1280, 720


def _draw_stroked_txt(draw: ImageDraw.ImageDraw, pos: Tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: Tuple[int, int, int, int], sw: int = 3) -> None:
    x, y = pos
    for dx in range(-sw, sw + 1):
        for dy in range(-sw, sw + 1):
            if dx * dx + dy * dy <= sw * sw + 1:
                draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 245))
    draw.text((x, y), text, font=font, fill=fill)


def _draw_pattern_a_silhouette_1280(
    draw: ImageDraw.ImageDraw,
    cx: int,
    base_y: int,
    kind: str,  # "left_hero" | "right_power"
    accent: Tuple[int, int, int, int],
) -> None:
    """Draw a Pattern-A (裏視点物語 style) silhouette figure at 1280x720 scale."""
    head_r = 38
    head_cy = base_y - 165
    torso_top = head_cy + head_r - 5
    torso_w = 88

    body_fill = (24, 24, 30, 255) if kind == "left_hero" else (38, 18, 20, 255)
    rim_col = (240, 225, 180, 255) if kind == "left_hero" else accent

    # Cloak polygon
    draw.polygon(
        [
            (cx - torso_w // 2, torso_top),
            (cx + torso_w // 2, torso_top),
            (cx + int(torso_w * 0.68), base_y),
            (cx - int(torso_w * 0.68), base_y),
        ],
        fill=body_fill,
        outline=rim_col,
        width=3,
    )
    # Head
    face_fill = (248, 246, 240, 255) if kind == "left_hero" else body_fill
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=face_fill, outline=rim_col, width=3)

    if kind == "left_hero":
        # Hourglass / cross tunic emblem
        cy_e = torso_top + 56
        s = 18
        draw.polygon([(cx - s, cy_e - s), (cx + s, cy_e - s), (cx, cy_e)], fill=body_fill, outline=rim_col, width=2)
        draw.polygon([(cx - s, cy_e + s), (cx + s, cy_e + s), (cx, cy_e)], fill=body_fill, outline=rim_col, width=2)
    else:
        # Crown + anger mark (💢) or power seal
        crown_y = head_cy - head_r + 4
        cw, ch = 34, 24
        draw.polygon(
            [
                (cx - cw, crown_y),
                (cx - cw - 5, crown_y - ch),
                (cx - cw // 2, crown_y - ch // 2),
                (cx, crown_y - ch - 6),
                (cx + cw // 2, crown_y - ch // 2),
                (cx + cw + 5, crown_y - ch),
                (cx + cw, crown_y),
            ],
            fill=(235, 190, 55, 255),
            outline=(255, 235, 140, 255),
            width=2,
        )
        ax, ay = cx - head_r - 16, head_cy - head_r + 8
        for ox, oy, st, en in [(-9, -9, 300, 120), (9, -9, 60, 240), (-9, 9, 240, 60), (9, 9, 120, 300)]:
            draw.arc([ax + ox - 9, ay + oy - 9, ax + ox + 9, ay + oy + 9], start=st, end=en, fill=(235, 45, 45, 255), width=4)


def _draw_two_col_cards(
    draw: ImageDraw.ImageDraw,
    jp: str,
    left_title: str,
    left_color: Tuple[int, int, int, int],
    left_rows: list,
    right_title: str,
    right_color: Tuple[int, int, int, int],
    right_rows: list,
    bottom_summary: str,
) -> None:
    """
    Pattern-A (裏視点物語 style) Visual Mechanism & Comparison Diagram:
    Instead of 16 lines of small text, draws:
    - Left Character/Concept Silhouette + `───` Callout Line + 2 concise visual keyword pills
    - Center `＝` / `→` visual equation connector
    - Right Character/Concept Silhouette + `───` Callout Line + 2 concise visual keyword pills
    """
    hy = int(H * 0.76)  # 547

    # 1. Left Silhouette & Callout (`x=270`)
    lx = 250
    _draw_pattern_a_silhouette_1280(draw, lx, hy, "left_hero", left_color)
    # Callout line (`─── left_title`)
    f_call = _fit_font(draw, left_title, jp, 21, 14, 480)
    tb_l = draw.textbbox((0, 0), left_title, font=f_call)
    tw_l = tb_l[2] - tb_l[0]
    draw.line([(lx, hy - 185), (72, 132)], fill=(235, 235, 240, 215), width=2)
    draw.line([(72, 132), (72 + tw_l + 10, 132)], fill=(235, 235, 240, 215), width=2)
    _draw_stroked_txt(draw, (76, 102), left_title, f_call, (255, 235, 165, 255), sw=3)

    # 2 concise visual keyword pills on the left
    for idx_r, (h_txt, _) in enumerate(left_rows[:2]):
        py = 162 + idx_r * 66
        draw_rounded_box(draw, (56, py, 560, py + 52), radius=12, fill=(22, 26, 36, 230), outline=left_color, width=2)
        f_k = _fit_font(draw, h_txt, jp, 19, 13, 476)
        draw.text((74, py + 14), h_txt, font=f_k, fill=(255, 255, 255, 255))

    # 2. Center Visual Connector (`＝` / `→`)
    f_eq = ImageFont.truetype(jp, 54)
    _draw_stroked_txt(draw, (612, 295), "＝", f_eq, (255, 215, 90, 255), sw=5)

    # 3. Right Silhouette & Callout (`x=1010`)
    rx = 1010
    _draw_pattern_a_silhouette_1280(draw, rx, hy, "right_power", right_color)
    f_rcall = _fit_font(draw, right_title, jp, 21, 14, 480)
    tb_r = draw.textbbox((0, 0), right_title, font=f_rcall)
    tw_r = tb_r[2] - tb_r[0]
    draw.line([(rx, hy - 185), (710, 132)], fill=(235, 235, 240, 215), width=2)
    draw.line([(710, 132), (710 + tw_r + 10, 132)], fill=(235, 235, 240, 215), width=2)
    _draw_stroked_txt(draw, (714, 102), right_title, f_rcall, (150, 230, 255, 255), sw=3)

    # 2 concise visual keyword pills on the right
    for idx_r, (h_txt, _) in enumerate(right_rows[:2]):
        py = 162 + idx_r * 66
        draw_rounded_box(draw, (710, py, 1224, py + 52), radius=12, fill=(22, 26, 36, 230), outline=right_color, width=2)
        f_k = _fit_font(draw, h_txt, jp, 19, 13, 486)
        draw.text((728, py + 14), h_txt, font=f_k, fill=(255, 255, 255, 255))


def render_rome_diagram_board(diagram_id: str, out_png: Path) -> None:
    if diagram_id == "diagram_01":
        img, draw, jp = _base_board("歴史図解 ①", "デマンド集計「ローマ帝国滅亡・210の原因説」6大分類")
        _draw_two_col_cards(
            draw,
            jp,
            "① 内部崩壊・社会・医療系の仮説",
            (165, 42, 42, 240),
            [
                ("① 道徳退廃・キリスト教説（ギボン 1776年）", "「パンとサーカス」による市民の堕落と尚武の精神の喪失"),
                ("② 鉛中毒による貴族発狂説（ヌリアグ 1983年）", "鉛製水道管・鉛鍋のワイン甘味料による神経毒性と少子化"),
                ("③ 少子高齢化・エリート層の消滅説", "貴族階級の独身主義と出生率低下による統治人材の枯渇"),
                ("④ 奴隷制経済の限界・技術停滞説", "安価な奴隷労働に依存し、蒸気機関や水車などの省力化が停滞"),
            ],
            "② 経済・環境・地政学系の最新学説",
            (38, 105, 165, 240),
            [
                ("⑤ 通貨偽造とハイパーインフレ説（経済史）", "デナリウス銀貨の銀含有率が98%→2%へ暴落し市場経済が崩壊"),
                ("⑥ 気候寒冷化＋巨大パンデミック説（ハーパー 2017年）", "ローマ温暖期の終焉とアントニヌス・キプリアヌス疫病の直撃"),
                ("⑦ フン族西進＆ゲルマン超部族化説（ヘザー 2005年）", "ローマ自身が育てた強大なゲルマン部族連合による軍事包囲"),
                ("⑧ 北アフリカ（カルタゴ）喪失による財政破綻説", "439年に最大の穀倉・税収源をヴァンダル族に奪われた致命傷"),
            ],
            "◎ 結論：単一の原因ではなく「環境・疫病・通貨劣化」で体力を削られた末、439年の北アフリカ喪失で財政が破綻した複合崩壊",
        )
        img.save(out_png)

    elif diagram_id == "diagram_02":
        img, draw, jp = _base_board("科学検証 ②", "俗説「ローマ人は鉛中毒で狂って滅んだ」の最新ファクトチェック")
        _draw_two_col_cards(
            draw,
            jp,
            "× 誤解された俗説（ヌリアグ説・1983年）",
            (165, 42, 42, 240),
            [
                ("主張①「鉛製水道管でローマ市民全員が鉛中毒」", "水道橋から市内に引く鉛管（フィストゥラ）が帝国を滅ぼしたとする説"),
                ("反証（2014年 PNAS論文：Hugo Delileら）", "堆積物分析で水道水の鉛は湧水の100倍と判明したが致死量には程遠い"),
                ("なぜ水道水は安全だったのか？（水垢のバリア）", "硬水のカルシウムが管内に『炭酸カルシウム皮膜』を作り鉛溶出を遮断"),
                ("決定的な矛盾：鉛管は「帝国絶頂期」から使用", "紀元前後の繁栄期から500年間使われており、5世紀滅亡の原因ではない"),
            ],
            "◎ 真の毒源「デフルトゥム（鉛鍋シロップ）」",
            (38, 118, 92, 240),
            [
                ("真犯人は水道ではなく「ワインの甘味料」", "ブドウ果汁を『鉛の鍋』で3分の1に煮詰めたシロップ（デフルトゥム）"),
                ("劇物「酢酸鉛（鉛糖）」の化学反応", "酸性の果汁が鉛鍋を溶かし、強い甘みを持つ神経毒『酢酸鉛』が生成"),
                ("再現実験で検出された衝撃の鉛濃度", "現代の再現実験で1リットル中数百mg（安全基準の数万倍）の鉛を検出"),
                ("被害は「ワインを大量に飲む貴族層」に集中", "皇帝や元老院議員の痛風・神経障害の一因だが、帝国滅亡の主因ではない"),
            ],
            "◎ 科学的結論：水道管による帝国滅亡説は誤り。鉛鍋の甘味料『デフルトゥム』が貴族の健康を蝕んだが、国家崩壊の主因ではない",
        )
        img.save(out_png)

    elif diagram_id == "diagram_03":
        img, draw, jp = _base_board("経済図解 ③", "デナリウス銀貨の銀含有率暴落（98%→2%）とハイパーインフレ")
        _draw_two_col_cards(
            draw,
            jp,
            "① 軍事費不足による「銀貨の改鋳（通貨偽造）」",
            (218, 178, 72, 240),
            [
                ("アウグストゥス帝：銀純度 98.0%（純銀3.9g）", "地中海全域で信用された世界最強の基軸通貨デナリウス"),
                ("3世紀の危機：銀純度 わずか 2.0%（銀メッキ銅貨）", "兵士の給与を払うため銅を混ぜ続け、実質的な偽造通貨へ暴落"),
            ],
            "② 通貨劣化が招いた「小麦200倍のハイパーインフレ」",
            (185, 45, 45, 240),
            [
                ("① 小麦価格が「約200倍」に暴騰（パピルス記録）", "市民の貯金は紙屑同然となり、政府自身もメッキ貨の受け取りを拒否"),
                ("② 貨幣経済が崩壊し「物納・農奴制」へ逆戻り", "農民を土地に縛り付ける中世封建制（コロナトゥス）の原型が誕生"),
            ],
            "◎ 結論：軍事費捻出のための「銀貨改鋳（通貨偽造）」が地中海市場経済を内部から破壊した",
        )
        img.save(out_png)

    elif diagram_id == "diagram_04":
        img, draw, jp = _base_board("学説比較 ④", "通説「パンとサーカス・キリスト教原因説（ギボン）」が覆った理由")
        _draw_two_col_cards(
            draw,
            jp,
            "× 古典的通説：ギボン『ローマ帝国衰亡史』（1776年）",
            (165, 42, 42, 240),
            [
                ("主張①「市民の贅沢と道徳の退廃で滅んだ」", "無償の小麦配給と戦車競走（パンとサーカス）が市民を怠惰にした"),
                ("主張②「キリスト教がローマの軍事精神を弱めた」", "平和と来世の救済を説くキリスト教が愛国心と軍隊を弱体化させた"),
                ("主張③「優秀な人材が軍や行政ではなく修道院へ逃げた」", "国家の危機に知識人が聖職者となり、帝国の統治能力が落ちたとする説"),
                ("なぜこの通説が生まれたのか？（18世紀啓蒙思想のバイアス）", "18世紀の思想家ギボンが当時のカトリック教会批判をローマ史に投影"),
            ],
            "◎ 現代歴史学の決定的反証（東ローマ1000年の繁栄）",
            (38, 118, 92, 240),
            [
                ("反証①「キリスト教の中心地・東ローマはさらに1000年続いた」", "最も熱心なキリスト教国だった東ローマ（ビザンツ）は1453年まで繁栄"),
                ("反証②「市民が軍の主力だったのは共和政期まで」", "帝政初期（アウグストゥス期）から既に国境の職業軍人が防衛を担っていた"),
                ("反証③「後期のローマ軍規模はむしろ絶頂期より拡大」", "4世紀のローマ軍は約40万〜50万人と、五賢帝時代（約30万人）より増強"),
                ("真の違いは「道徳」ではなく「地政学と税収構造」", "東ローマは豊かなエジプトと小アジアの税収を守り抜いたため生き残った"),
            ],
            "◎ 結論：「道徳の退廃」や「キリスト教」が滅亡原因なら、東ローマ帝国がその後1000年も超大国として繁栄した説明がつかない",
        )
        img.save(out_png)

    elif diagram_id == "diagram_05":
        img, draw, jp = _base_board("最新論争 ⑤", "「気候変動＆パンデミック決定論（2017年）」vs「歴史学界の反論（2018年）」")
        _draw_two_col_cards(
            draw,
            jp,
            "学説A：カイル・ハーパー『The Fate of Rome』（2017年）",
            (175, 95, 30, 240),
            [
                ("① ローマ温暖期（前200〜後150年）の終焉", "温暖湿潤な気候が終わり、干ばつと寒冷化が農業生産を直撃"),
                ("② アントニヌス疫病（165〜180年・天然痘説）", "医師ガレノスが記録。帝国人口6,000万人の約10〜15%が死亡"),
                ("③ キプリアヌス疫病（249〜262年・出血熱説）", "3世紀の危機の真っ只中に発生し、兵士不足と税収激減を引き起こした"),
                ("④ 536年の火山噴火による「古代末期小氷期」とペスト", "太陽が1年半陰り、541年のユスティニアヌス疫病（ペスト）で決定打"),
            ],
            "学説B：ハルドン、ニューフィールドらの批判論文（2018年〜）",
            (38, 105, 165, 240),
            [
                ("反論①「疫病から476年の滅亡まで300年も時間差がある」", "165年や250年の疫病の後、4世紀に帝国は一度完全に復興している"),
                ("反論②「エジプトのパピルス文書では農業生産は維持」", "特定の都市の被害を帝国全体に過大推計していると古気候・文献学が批判"),
                ("反論③「536年の小氷期とペストは西ローマ滅亡（476年）の後」", "西ローマが崩壊した5世紀は、それらの大災害より前の時代である"),
                ("現代の合意：自然災害は「基礎体力を削った背景要因」", "環境だけで自動的に滅んだのではなく、政治・軍事の失敗が直接の引き金"),
            ],
            "◎ 重要視点：最新科学（気候・疫病説）も万能ではなく、「300年の時間差」をめぐって現在も最先端の学術論争が続いている",
        )
        img.save(out_png)

    elif diagram_id == "diagram_06":
        img, draw, jp = _base_board("軍事・地政学 ⑥", "フン族のドミノ衝撃と「ゲルマン超部族連合」への進化（378年ハドリアノポリス）")
        _draw_two_col_cards(
            draw,
            jp,
            "× 旧来のイメージ：「未開の野蛮人が突然押し寄せた」",
            (165, 42, 42, 240),
            [
                ("教科書の単純な図式", "毛皮を着た原始的なゲルマン部族が、文明国ローマを数で圧倒したという誤解"),
                ("実際は「ローマ自身が400年かけて彼らを育てた」", "国境交易・補助金・傭兵雇用を通じてローマの武器・戦術・農業が流出"),
                ("小部族から「数万人規模の超部族連合」へ統合", "1世紀にはバラバラだった小部族が、ゴート・フランク・ヴァンダルへ大統合"),
                ("ローマ軍内部の「フォエデラティ（同盟部族軍）」依存", "正規軍の損失を埋めるため、ゲルマン人を部族単位でそのまま雇用"),
            ],
            "◎ ピーター・ヘザー（オックスフォード大）の地政学解明",
            (38, 105, 165, 240),
            [
                ("375年：ユーラシア草原から「フン族」が出現", "圧倒的な複合弓と騎馬戦術を持つフン族がゴート族の領土を背後から撃破"),
                ("376年：ゴート族20万人がドナウ川を渡り難民流入", "ローマ官僚の食料横領と虐待が引き金となり、ゴート族が一斉蜂起"),
                ("378年8月9日：ハドリアノポリスの戦いでローマ主力軍壊滅", "東方皇帝ウァレンスが戦死し、精鋭軍の3分の2（約2万人）を1日で喪失"),
                ("以後、帝国境内に「独立した武装ゲルマン国家」が常駐", "国境防衛線が突破され、帝国内部で領土と税収を蚕食される悪循環へ"),
            ],
            "◎ 結論：ローマは「未開の野蛮人」に負けたのではなく、ローマ自身の軍事・経済システムを吸収して進化した隣人に敗れた",
        )
        img.save(out_png)

    elif diagram_id == "diagram_07":
        img, draw, jp = _base_board("財政破綻の決定打 ⑦", "なぜ西ローマだけが滅びたのか？「439年 カルタゴ陥落（北アフリカ喪失）」")
        _draw_two_col_cards(
            draw,
            jp,
            "西ローマ帝国の生命線だった「北アフリカ（カルタゴ）」",
            (185, 135, 35, 240),
            [
                ("① イタリアと首都ローマを養う「最大の穀倉地帯」", "現在のチュニジア・アルジェリア沿岸は小麦とオリーブ油の巨大産地"),
                ("② 西ローマ政府の「最重要の黒字税収源」", "ガリアやブリタニアが戦乱で荒廃する中、平和な北アフリカが財政を支えた"),
                ("③ 439年：ヴァンダル王ガイセリックがカルタゴを占領", "北アフリカの穀物船団と税収が一夜にして遮断され、地中海制海権を喪失"),
                ("④ 税収を失った西ローマは「軍隊に給料が払えない」状態へ", "歳入が半減し、防衛力低下→さらなる領土喪失のデススパイラルに突入"),
            ],
            "468年「ボン岬沖の海戦」の敗北と476年の終焉",
            (165, 42, 42, 240),
            [
                ("468年：東西ローマ連合による「乾坤一擲の北アフリカ奪還作戦」", "軍船1,100隻・兵力10万人・金6万4千ポンド（1年分の国家予算超）を投入"),
                ("ヴァンダル軍の「火船（焼き討ち船）奇襲」で大艦隊が壊滅", "風が吹く夜間に火をつけた船を流し込まれ、ローマ艦隊の主力の大半が焼失"),
                ("東ローマも破産寸前に陥り、西ローマを見捨てる", "これにより西ローマ帝国は財源奪還の最後の希望を完全に失った"),
                ("そのわずか8年後（476年）：傭兵隊長オドアケルが皇帝廃位", "給料の代わりにイタリアの土地3分の1を要求した傭兵軍により西ローマ消滅"),
            ],
            "◎ 結論：410年のローマ略奪ではなく、「439年の北アフリカ喪失」と「468年ボン岬沖の海戦敗北」が西ローマ財政にとどめを刺した",
        )
        img.save(out_png)

    elif diagram_id == "diagram_08":
        img, draw, jp = _base_board("考古学データ ⑧", "476年は「緩やかな移行」か「文明の崩壊」か？3つの科学エビデンス")
        _draw_two_col_cards(
            draw,
            jp,
            "学説①：ピーター・ブラウンら「連続的変容（後期古代）説」",
            (38, 105, 165, 240),
            [
                ("476年に「ローマが滅んだ」と気づいた同時代人はいなかった", "少年皇帝ロムルスが退位した後も、ローマ元老院や執政官制度は存続"),
                ("ゲルマン王たちはローマの法律・ラテン語・キリスト教を継承", "オドアケルや東ゴート王テオドリックは東ローマ皇帝の代官として統治"),
                ("「暗黒時代（Dark Ages）」という呼称への見直し", "修道院での写本文化やキリスト教芸術は発展し、中世へ緩やかに移行した"),
                ("※しかし「庶民の物質的な生活水準」はどうなったのか？", "文献史料（エリート層の記録）だけでは見えない現実を考古学が暴いた"),
            ],
            "学説②：ウォード＝パーキンス「文明崩壊説」3大考古学データ",
            (165, 42, 42, 240),
            [
                ("① 屋根瓦と量産陶器の完全消滅（先史時代への退行）", "農村まで普及していた瓦屋根とろくろ陶器が消え、青銅器時代以下の手捏ね土器へ"),
                ("② 家畜（牛）の体格が「10〜15cm」一気に小型化", "出土した牛の骨の計測で、ローマ期の高度な品種・飼料管理が消滅し先史サイズに縮小"),
                ("③ グリーンランド氷床コアの「大気中鉛・銅汚染」がゼロに急落", "ローマ期の巨大な銀・銅製錬工業が崩壊し、産業革命まで1,000年間回復せず"),
                ("④ 人口の激減：100万都市ローマが「人口3万人」の廃墟へ", "水道橋が止まり、巨大建築のレンガを剥がして小さな小屋を作る時代へ"),
            ],
            "◎ 最終結論：文化や宗教は受け継がれたが、インフラ・分業経済・生活水準という「物質文明」は紛れもなく1,000年巻き戻った",
        )
        img.save(out_png)


ROME_QUESTION_SPECS: Dict[str, Dict[str, object]] = {
    "q_01": {
        "scene": "scene_02",
        "sec": 2.0,
        "badge": "歴史の疑問 Q1 ／ 210の滅亡仮説",
        "line1": "なぜローマ帝国の滅亡原因には",
        "line2": "「210通り」もの学説が存在するのか？",
        "hint": "▶ 次の図解：ドイツの歴史家デマンドが集計した「210の仮説」6大分類マップ",
    },
    "q_02": {
        "scene": "scene_05",
        "sec": 2.5,
        "badge": "歴史の疑問 Q2 ／ 都市伝説の科学検証",
        "line1": "「鉛製の水道管でローマ人が狂って滅んだ」",
        "line2": "という有名な通説は、科学的に本当なのか？",
        "hint": "▶ 次の図解：2014年PNAS論文の鉛同位体データと、真の毒源『デフルトゥム』",
    },
    "q_03": {
        "scene": "scene_07",
        "sec": 2.0,
        "badge": "歴史の疑問 Q3 ／ 通貨崩壊とインフレ",
        "line1": "なぜ世界最強だった「デナリウス銀貨」は",
        "line2": "銀98%から「2%のメッキ銅貨」に暴落したのか？",
        "hint": "▶ 次の図解：出土銀貨の冶金分析グラフと「小麦価格200倍」のハイパーインフレ",
    },
    "q_04": {
        "scene": "scene_10",
        "sec": 2.0,
        "badge": "歴史の疑問 Q4 ／ 教科書の通説を疑う",
        "line1": "「パンとサーカスによる堕落とキリスト教」で",
        "line2": "ローマが滅んだという通説はなぜ誤りなのか？",
        "hint": "▶ 次の図解：ギボン『ローマ帝国衰亡史』の通説を覆す「東ローマ1000年繁栄」の証拠",
    },
    "q_05": {
        "scene": "scene_13",
        "sec": 2.0,
        "badge": "歴史の疑問 Q5 ／ 気候変動と疫病の論争",
        "line1": "気候の寒冷化と「2つの未知のパンデミック」は",
        "line2": "ローマ滅亡の決定打だったのか？（最新学説の対立）",
        "hint": "▶ 次の図解：2017年ハーパーの環境決定論 vs 2018年ハルドンらの「300年時間差」反論",
    },
    "q_06": {
        "scene": "scene_18",
        "sec": 2.0,
        "badge": "歴史の疑問 Q6 ／ ゲルマン大移動の真相",
        "line1": "なぜ世界最強のローマ軍は「傭兵だらけ」になり、",
        "line2": "378年ハドリアノポリスで壊滅したのか？",
        "hint": "▶ 次の図解：フン族のドミノ衝撃と、ローマ自身が育てた「ゲルマン超部族連合」",
    },
    "q_07": {
        "scene": "scene_19",
        "sec": 2.0,
        "badge": "歴史の疑問 Q7 ／ 西ローマ財政破綻の真犯人",
        "line1": "なぜ東ローマは生き残り、西ローマだけが滅んだ？",
        "line2": "439年「北アフリカ喪失」の致命傷とは？",
        "hint": "▶ 次の図解：最大の穀倉カルタゴ陥落と、468年「ボン岬沖の海戦」1000隻壊滅の悲劇",
    },
    "q_08": {
        "scene": "scene_23",
        "sec": 2.0,
        "badge": "歴史の疑問 Q8 ／ 変容か、文明の終焉か",
        "line1": "476年の滅亡は「中世への緩やかな移行」か、",
        "line2": "それとも「文明が1000年巻き戻った崩壊」か？",
        "hint": "▶ 次の図解：屋根瓦の消滅・牛の小型化・氷床コアが暴く「物質文明崩壊」3大データ",
    },
}


def render_pattern_a_question_card(spec: Dict[str, object], out_png: Path) -> None:
    """Render a Pattern-A (裏視点物語 style) Silhouette + Fluffy Question Cloud (`💭`) scene."""
    img, draw, jp = _base_board(str(spec["badge"]).split("／")[0].strip(), str(spec["badge"]).split("／")[-1].strip())
    hy = int(H * 0.76)

    # Character silhouette on left (`x=290`) pondering the question
    _draw_pattern_a_silhouette_1280(draw, 290, hy, "left_hero", (235, 195, 85, 255))
    f_lbl = ImageFont.truetype(jp, 20)
    draw.line([(330, hy - 180), (390, hy - 210)], fill=(235, 235, 240, 215), width=2)
    draw.line([(390, hy - 210), (540, hy - 210)], fill=(235, 235, 240, 215), width=2)
    _draw_stroked_txt(draw, (395, hy - 238), "素朴な疑問", f_lbl, (245, 245, 250, 255), sw=3)

    # Fluffy white thought/question cloud in upper-right (`cx=760, cy=235`)
    cx, cy = 760, 235
    tw, th = 760, 156
    x0, y0 = cx - tw // 2, cy - th // 2
    x1, y1 = cx + tw // 2, cy + th // 2
    for px, py, pr in [
        (x0 + 38, y0 + 24, 42),
        (cx - 120, y0 + 12, 48),
        (cx + 120, y0 + 12, 48),
        (x1 - 38, y0 + 24, 42),
        (x0 + 24, cy + 10, 40),
        (x1 - 24, cy + 10, 40),
        (cx - 140, y1 - 14, 42),
        (cx + 140, y1 - 14, 42),
    ]:
        draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(248, 248, 252, 255))
    draw.rounded_rectangle([x0 + 12, y0 + 14, x1 - 12, y1 - 14], radius=32, fill=(248, 248, 252, 255))

    # Trailing thought dots toward the silhouette's head
    draw.ellipse([348, 318, 368, 338], fill=(248, 248, 252, 255))
    draw.ellipse([325, 342, 339, 356], fill=(248, 248, 252, 255))

    l1 = str(spec["line1"])
    l2 = str(spec["line2"])
    f1 = _fit_font(draw, l1, jp, 28, 18, tw - 70)
    f2 = _fit_font(draw, l2, jp, 30, 18, tw - 70)
    b1 = draw.textbbox((0, 0), l1, font=f1)
    b2 = draw.textbbox((0, 0), l2, font=f2)
    draw.text((cx - (b1[2] - b1[0]) // 2, cy - 42), l1, font=f1, fill=(30, 34, 44, 255))
    draw.text((cx - (b2[2] - b2[0]) // 2, cy + 8), l2, font=f2, fill=(185, 28, 28, 255))

    img.save(out_png)


def render_rome_question_card(q_id: str, out_png: Path, flow_dir: Path) -> None:
    render_pattern_a_question_card(ROME_QUESTION_SPECS[q_id], out_png)


def render_all_rome_diagrams(flow_dir: Path, diag_dir: Path) -> None:
    diag_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 9):
        did = f"diagram_{i:02d}"
        render_rome_diagram_board(did, diag_dir / f"{did}.png")
        qid = f"q_{i:02d}"
        render_rome_question_card(qid, diag_dir / f"{qid}.png", flow_dir)


if __name__ == "__main__":
    fdir = Path("/Users/takahashitomohiro/Desktop/Youtube PJ/assets/flow_history_rome_fall")
    ddir = fdir / "diagrams"
    render_all_rome_diagrams(fdir, ddir)
    print("Rendered all 8 Roman Empire diagrams and 8 Question cards!")
