#!/usr/bin/env python3
"""
history_infographics.py

Renders 6 museum-grade 1280x720 historical infographic, diagram, map, and
scholarly theory comparison boards (解説の図・表・マップ・諸説比較静止画)
to be inserted as connecting analytical segments ("繋ぎ") in the Complete Edition
of the French Revolution documentary.
"""

from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

from build_japan_ranking import draw_rounded_box, find_cjk_font

W, H = 1280, 720


def _fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: str, max_pt: int, min_pt: int, max_w: int) -> ImageFont.FreeTypeFont:
    for pt in range(max_pt, min_pt - 1, -1):
        f = ImageFont.truetype(font_path, pt)
        tb = draw.textbbox((0, 0), text, font=f)
        if (tb[2] - tb[0]) <= max_w:
            return f
    return ImageFont.truetype(font_path, min_pt)


def _base_board(title_tag: str, main_title: str) -> Tuple[Image.Image, ImageDraw.ImageDraw, str]:
    """Create a Pattern-A (裏視点物語 style) dark atmospheric 1280x720 illustration canvas."""
    img = Image.new("RGBA", (W, H), (14, 17, 24, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    jp = find_cjk_font()

    # Smooth atmospheric vertical gradient
    for y in range(H):
        t = y / float(H)
        r = int(24 * (1 - t) + 10 * t)
        g = int(28 * (1 - t) + 12 * t)
        b = int(38 * (1 - t) + 18 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Soft center radial backlight glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    cx, cy = W // 2, int(H * 0.44)
    for rad in range(360, 30, -18):
        alpha = int(48 * (1.0 - rad / 360.0))
        gdraw.ellipse([cx - int(rad * 1.35), cy - rad, cx + int(rad * 1.35), cy + rad], fill=(95, 80, 55, alpha))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle ground horizon line
    hy = int(H * 0.76)
    draw.rectangle([0, hy, W, H], fill=(10, 12, 16, 235))
    draw.line([(0, hy), (W, hy)], fill=(95, 85, 68, 135), width=2)

    # Clean top title (stroked, no cluttered box frame)
    full_head = f"【{title_tag}】{main_title}"
    f_title = _fit_font(draw, full_head, jp, 26, 17, W - 80)
    tb = draw.textbbox((0, 0), full_head, font=f_title)
    tx = (W - (tb[2] - tb[0])) // 2
    ty = 26
    for dx in (-3, 0, 3):
        for dy in (-3, 0, 3):
            if dx or dy:
                draw.text((tx + dx, ty + dy), full_head, font=f_title, fill=(0, 0, 0, 240))
    draw.text((tx, ty), full_head, font=f_title, fill=(255, 225, 130, 255))
    rgb_img = img.convert("RGB")
    return rgb_img, ImageDraw.Draw(rgb_img, "RGBA"), jp


def render_diagram_board(diagram_id: str, out_png: Path) -> None:
    """Render one of the 6 historical diagram/table boards (`diagram_01` .. `diagram_06`)."""
    if diagram_id == "diagram_01":
        # 【図解①】18世紀フランスの身分ピラミッドと税負担の歪み
        img, draw, jp = _base_board("歴史図解 ①", "アンシャン・レジーム（旧体制）の身分構造と税負担")

        tiers = [
            (
                "第1身分：聖職者（約13万人 ／ 人口の 0.5%）",
                "国土の約10%を所有・平民から『十分の一税』を徴収",
                "直接税：ゼロ（非課税）",
                (180, 142, 54, 235),
                (104, 108, 560, 228),
            ),
            (
                "第2身分：貴族（約40万人 ／ 人口の 1.5%）",
                "国土の約25%を所有・軍や政府の要職を独占・領主裁判権",
                "直接税：ほぼゼロ（免税特権）",
                (62, 104, 168, 235),
                (76, 246, 588, 366),
            ),
            (
                "第3身分：平民（約2,600万人 ／ 人口の 98.0%）",
                "農民（8割）・都市職人・ブルジョワジー（医師・弁護士・商人）",
                "タイユ（直接税）・塩税・封建貢納をすべて負担",
                (164, 48, 48, 235),
                (48, 384, 616, 548),
            ),
        ]
        f_h = ImageFont.truetype(jp, 22)
        f_b = ImageFont.truetype(jp, 17)
        f_tax = ImageFont.truetype(jp, 19)
        for header, desc, tax, col, box in tiers:
            draw_rounded_box(draw, box, radius=14, fill=(28, 33, 46, 245), outline=col, width=3)
            draw_rounded_box(draw, (box[0], box[1], box[2], box[1] + 42), radius=12, fill=col)
            draw.text((box[0] + 16, box[1] + 8), header, font=f_h, fill=(255, 255, 255, 255))
            draw.text((box[0] + 18, box[1] + 54), desc, font=f_b, fill=(225, 230, 240, 255))
            draw.text((box[0] + 18, box[1] + 86), f"▶ {tax}", font=f_tax, fill=(255, 216, 102, 255))

        # Right side: Farmers' harvest breakdown bar chart
        rbox = (646, 108, W - 48, 548)
        draw_rounded_box(draw, rbox, radius=14, fill=(25, 30, 42, 245), outline=(198, 162, 72, 170), width=2)
        draw.text((670, 124), "【農民が収穫した麦100%の行き先】", font=ImageFont.truetype(jp, 23), fill=(255, 218, 110, 255))

        bars = [
            ("国王への税金（タイユ・塩税・間接税）", 35, (192, 58, 58, 240)),
            ("貴族（領主）への封建地代・使用料", 20, (72, 118, 188, 240)),
            ("教会への「十分の一税」", 10, (188, 148, 58, 240)),
            ("翌年の種籾（たねもみ）確保分", 15, (110, 120, 138, 240)),
            ("農民家族の手元に残る食糧・収入", 20, (56, 158, 98, 240)),
        ]
        y_cur = 178
        for label, pct, bcol in bars:
            draw.text((672, y_cur), f"{label} ： 約{pct}%", font=ImageFont.truetype(jp, 18), fill=(235, 240, 248, 255))
            bar_w = int(510 * (pct / 40.0))
            draw_rounded_box(draw, (672, y_cur + 28, 672 + bar_w, y_cur + 54), radius=8, fill=bcol)
            y_cur += 72

        img.save(out_png)
        return

    if diagram_id == "diagram_02":
        # 【諸説比較表①】なぜフランス国家は破産したのか？（通説 vs 最新研究）
        img, draw, jp = _base_board("諸説・真相 ②", "国家破産の真犯人は誰か？ ── 通説 vs 歴史学の実態")

        # Left column: Common Myth (通説)
        lbox = (48, 108, 620, 548)
        draw_rounded_box(draw, lbox, radius=14, fill=(42, 24, 28, 240), outline=(205, 75, 75, 220), width=2)
        draw_rounded_box(draw, (48, 108, 620, 158), radius=12, fill=(165, 42, 42, 245))
        draw.text((70, 120), "【当時の噂・通説】王妃アントワネット原因説", font=ImageFont.truetype(jp, 22), fill=(255, 255, 255, 255))

        myths = [
            ("①「赤字夫人（マダム・デフィシット）」", "王妃のドレス・宝石・賭博・プチトリアノン宮殿の建設で国庫が空になったという当時の中傷ビラ。"),
            ("②「パンがなければお菓子を食べればいい」", "飢える市民を見捨てた冷酷な発言として有名になり、市民の憎悪が王妃一人に集中した。"),
            ("③「首飾り事件（1785年）」", "160万リーヴルのダイヤの首飾りを巡る詐欺事件。王妃は無実だったが国民は「王妃の陰謀」と信じた。"),
        ]
        y = 176
        for h_txt, d_txt in myths:
            draw.text((68, y), h_txt, font=ImageFont.truetype(jp, 20), fill=(255, 205, 110, 255))
            # wrap desc into 2 lines
            line1, line2 = d_txt[:24], d_txt[24:]
            draw.text((68, y + 30), line1, font=ImageFont.truetype(jp, 17), fill=(235, 235, 240, 255))
            draw.text((68, y + 54), line2, font=ImageFont.truetype(jp, 17), fill=(235, 235, 240, 255))
            y += 118

        # Right column: Historical Fact & Budget Breakdown (最新研究の実態)
        rbox = (648, 108, W - 48, 548)
        draw_rounded_box(draw, rbox, radius=14, fill=(22, 36, 48, 240), outline=(78, 168, 225, 220), width=2)
        draw_rounded_box(draw, (648, 108, W - 48, 158), radius=12, fill=(38, 108, 165, 245))
        draw.text((670, 120), "【歴史学の実態】1788年 国家歳出のリアルな内訳", font=ImageFont.truetype(jp, 22), fill=(255, 255, 255, 255))

        facts = [
            ("■ 借金の利払い ： 歳出の 50.5%（最大の原因！）", "ルイ14世・15世からの戦争借金＋『アメリカ独立戦争』への巨額参戦費（約13億リーヴル）の利払い。"),
            ("■ 軍事・外交費 ： 歳出の 26.0%", "イギリスとの覇権争いのため陸海軍に莫大な予算を投入。"),
            ("■ ヴェルサイユ宮廷費 ： わずか 6.0% 前後", "宮廷の浪費も問題だったが、財政破綻の真因は『特権階級に課税できない税制』と『対外戦争の借金』。"),
            ("■ 『お菓子（ブリオッシュ）』発言の真相", "王妃が10歳でオーストリアにいた頃にルソーが書いた『告白』の一節。王妃が言った記録は一切存在しない。"),
        ]
        y = 174
        for h_txt, d_txt in facts:
            draw.text((668, y), h_txt, font=ImageFont.truetype(jp, 19), fill=(125, 225, 255, 255))
            line1, line2 = d_txt[:26], d_txt[26:]
            draw.text((668, y + 26), line1, font=ImageFont.truetype(jp, 16), fill=(230, 238, 245, 255))
            draw.text((668, y + 48), line2, font=ImageFont.truetype(jp, 16), fill=(230, 238, 245, 255))
            y += 92

        img.save(out_png)
        return

    if diagram_id == "diagram_03":
        # 【図解②・諸説】1788年大凶作の気象メカニズムと「パン価格暴騰チャート」
        img, draw, jp = _base_board("気象史学・データ ③", "1788年大凶作の諸説と「パン1個＝日給の9割」暴騰グラフ")

        # Left side: Volcanic eruption & climate chain
        lbox = (48, 108, 560, 548)
        draw_rounded_box(draw, lbox, radius=14, fill=(26, 30, 42, 245), outline=(198, 162, 72, 190), width=2)
        draw.text((68, 124), "【諸説】火山噴火が引き起こした異常気象連鎖", font=ImageFont.truetype(jp, 21), fill=(255, 216, 105, 255))

        steps = [
            ("STEP 1｜1783年 アイスランド「ラキ火山」大噴火", "大量の火山ガスと塵が成層圏を覆い、ヨーロッパ全土で数年にわたる異常気象（厳冬と干ばつ）が発生。"),
            ("STEP 2｜1788年7月13日 壊滅的な「巨大ひょう嵐」", "収穫直前のフランス穀倉地帯を、鶏卵大の巨大な雹（ひょう）が直撃し、小麦の収穫量が激減。"),
            ("STEP 3｜1788年〜1789年冬 記録的な大寒波", "マイナス20度近い厳冬でセーヌ川や水車が凍結。製粉も輸送もストップし、パリで深刻な食糧危機へ。"),
        ]
        y = 176
        for st_h, st_d in steps:
            draw_rounded_box(draw, (66, y, 542, y + 106), radius=10, fill=(36, 42, 58, 245), outline=(120, 150, 200, 160), width=2)
            draw.text((80, y + 12), st_h, font=ImageFont.truetype(jp, 18), fill=(135, 215, 255, 255))
            draw.text((80, y + 42), st_d[:24], font=ImageFont.truetype(jp, 16), fill=(230, 235, 242, 255))
            draw.text((80, y + 66), st_d[24:], font=ImageFont.truetype(jp, 16), fill=(230, 235, 242, 255))
            y += 122

        # Right side: Bread Price vs Daily Wage Chart
        rbox = (588, 108, W - 48, 548)
        draw_rounded_box(draw, rbox, radius=14, fill=(26, 30, 42, 245), outline=(215, 90, 90, 200), width=2)
        draw.text((612, 124), "【パリ労働者の日給に占める「4ポンド黒パン1個」の価格推移】", font=ImageFont.truetype(jp, 19), fill=(255, 216, 105, 255))

        points = [
            ("1787年（平年）", "8〜9 スー", 45, "日給の 約45%", (72, 168, 112, 245)),
            ("1788年8月（凶作直後）", "11 スー", 58, "日給の 約58%", (215, 165, 58, 245)),
            ("1789年2月（厳冬）", "14.5 スー", 75, "日給の 約75%（暴動続発）", (225, 108, 48, 245)),
            ("1789年7月14日（革命当日）", "16〜18 スー", 88, "日給の 88%（最高値！）", (215, 45, 45, 245)),
        ]
        y = 182
        for period, price, pct, label, col in points:
            draw.text((614, y), f"{period}  ［パン価格：{price}］", font=ImageFont.truetype(jp, 18), fill=(240, 244, 250, 255))
            bw = int(560 * (pct / 100.0))
            draw_rounded_box(draw, (614, y + 28, 614 + bw, y + 60), radius=8, fill=col)
            draw.text((626, y + 33), label, font=ImageFont.truetype(jp, 18), fill=(255, 255, 255, 255))
            y += 86

        img.save(out_png)
        return

    if diagram_id == "diagram_04":
        # 【諸説比較表②】三部会の決裂と「バスティーユ牢獄」の意外な真相
        img, draw, jp = _base_board("歴史の皮肉 ④", "三部会のトリックと「バスティーユ牢獄・囚人7人」の真相")

        lbox = (48, 108, 615, 548)
        draw_rounded_box(draw, lbox, radius=14, fill=(26, 32, 46, 245), outline=(198, 162, 72, 200), width=2)
        draw.text((68, 124), "① なぜ「三部会（1789年5月）」は決裂したのか？", font=ImageFont.truetype(jp, 21), fill=(255, 216, 105, 255))

        t_lines = [
            "・議員数は平民代表が約600人で半数を占めていたが、",
            "  特権階級は『1身分につき1票』の旧ルールに固執。",
            "・第1身分（1票）＋第2身分（1票） vs 第3身分（1票）",
            "  ＝ 『2対1』で平民側の課税改革案が必ず否決される仕組み！",
            "・激怒した平民代表（＋一部の開明派貴族・聖職者）が独立し",
            "  『国民議会』を結成 → 球技場（テニスコート）の誓いへ。",
        ]
        y = 172
        for ln in t_lines:
            draw.text((68, y), ln, font=ImageFont.truetype(jp, 18), fill=(235, 240, 248, 255))
            y += 42

        draw_rounded_box(draw, (68, 434, 595, 526), radius=10, fill=(44, 54, 76, 245), outline=(120, 180, 240, 190), width=2)
        draw.text((84, 448), "★ 諸説ポイント：革命を主導したのは誰か？", font=ImageFont.truetype(jp, 18), fill=(135, 215, 255, 255))
        draw.text((84, 480), "議会を動かしたのは貧農ではなく、弁護士（ロベスピエール等）や", font=ImageFont.truetype(jp, 16), fill=(235, 240, 248, 255))
        draw.text((84, 502), "富裕な市民（ブルジョワジー）という「知識層エリート」だった。", font=ImageFont.truetype(jp, 16), fill=(235, 240, 248, 255))

        rbox = (642, 108, W - 48, 548)
        draw_rounded_box(draw, rbox, radius=14, fill=(36, 26, 32, 245), outline=(215, 110, 90, 200), width=2)
        draw.text((664, 124), "② バスティーユ牢獄にいた「実際の囚人」はたった7人！", font=ImageFont.truetype(jp, 20), fill=(255, 205, 110, 255))

        b_rows = [
            ("【イメージ】", "無実の政治犯や思想犯が何百人も鎖に繋がれた地獄の地下牢"),
            ("【実際の収容者】", "陥落時にいた囚人はわずか『7人』のみ！"),
            ("  ・偽造犯 4名", "小切手・手形の偽造で収監されていた一般犯罪者"),
            ("  ・精神疾患 2名", "家族の要請で保護収容されていた人物（1人は自分を神と主張）"),
            ("  ・放蕩貴族 1名", "家族から依頼されて贅沢な部屋に軟禁されていたソラージュ伯爵"),
            ("【市民の真の目的】", "囚人解放ではなく、要塞内に保管されていた『13.6トンの火薬』！"),
        ]
        y = 176
        for k, v in b_rows:
            draw.text((664, y), k, font=ImageFont.truetype(jp, 18), fill=(255, 185, 115, 255))
            draw.text((664, y + 26), v, font=ImageFont.truetype(jp, 16), fill=(238, 240, 246, 255))
            y += 58

        img.save(out_png)
        return

    if diagram_id == "diagram_05":
        # 【歴史マップ】ヴェルサイユ行進（20km）と1791年「ヴァレンヌ逃亡事件」ルート図
        img, draw, jp = _base_board("歴史マップ ⑤", "1791年6月「ヴァレンヌ逃亡事件」ルートと諸説")

        # Left map canvas
        mbox = (48, 108, 720, 548)
        draw_rounded_box(draw, mbox, radius=14, fill=(20, 30, 40, 245), outline=(198, 162, 72, 200), width=2)
        draw.text((68, 122), "【フランス北東部・逃亡ルート図（総移動距離 約240km）】", font=ImageFont.truetype(jp, 20), fill=(255, 218, 105, 255))

        # Stylized route nodes: Versailles -> Paris -> Châlons -> Sainte-Menehould -> Varennes -> Montmédy (Border)
        nodes = [
            (115, 455, "ヴェルサイユ宮殿", "1789年10月 パリへ連行", (160, 168, 185, 255)),
            (205, 395, "パリ（テュイルリー宮殿）", "1791年6月20日 深夜脱出", (88, 185, 255, 255)),
            (370, 330, "シャロン＝シュル＝マルヌ", "大型馬車で数時間の遅れ", (235, 195, 88, 255)),
            (490, 265, "サント＝ムヌー宿場", "宿場長ドルーエが王の顔に気づく", (245, 140, 68, 255)),
            (575, 200, "★ ヴァレンヌ（逮捕地点）", "6月21日夜 国民衛兵が馬車を包囲", (235, 65, 65, 255)),
            (655, 150, "モンメディ要塞（国境）", "あとわずか40kmで到達できず", (150, 160, 175, 255)),
        ]
        # Draw connecting route lines
        for i in range(len(nodes) - 1):
            x1, y1, _, _, _ = nodes[i]
            x2, y2, _, _, _ = nodes[i + 1]
            col = (235, 85, 85, 230) if i < 4 else (130, 140, 155, 160)
            draw.line([(x1, y1), (x2, y2)], fill=col, width=4)

        for x, y, name, sub, col in nodes:
            draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=col, outline=(255, 255, 255, 240), width=2)
            draw.text((x + 16, y - 18), name, font=ImageFont.truetype(jp, 17), fill=col)
            draw.text((x + 16, y + 4), sub, font=ImageFont.truetype(jp, 14), fill=(220, 226, 235, 255))

        # Right column: Why did the escape fail? (諸説)
        rbox = (744, 108, W - 48, 548)
        draw_rounded_box(draw, rbox, radius=14, fill=(28, 32, 46, 245), outline=(198, 162, 72, 200), width=2)
        draw.text((764, 124), "【なぜ逃亡は失敗したのか？ 3つの諸説】", font=ImageFont.truetype(jp, 20), fill=(255, 218, 105, 255))

        theories = [
            ("説①：巨大馬車「ベルリン号」の鈍足説", "小型馬車で別々に逃げる案を拒み、銀食器や衣装を積んだ6頭立て大型馬車を使ったため計画より3時間以上遅れた。"),
            ("説②：紙幣・金貨の「王の横顔」一致説", "宿場長ドルーエが、発行されたばかりのアッシニア紙幣（または金貨）の肖像画と馬車内の男を見比べて正体を見破った。"),
            ("説③：ラ・ファイエット将軍「泳がせ」説", "立憲君主派や急進派の一部が、王の脱出計画を事前に察知しつつ、王の権威を失墜させるためわざと出発させたとする説。"),
        ]
        y = 174
        for th_h, th_d in theories:
            draw_rounded_box(draw, (762, y, W - 66, y + 112), radius=10, fill=(38, 44, 62, 245), outline=(130, 155, 200, 160), width=2)
            draw.text((776, y + 10), th_h, font=ImageFont.truetype(jp, 18), fill=(135, 215, 255, 255))
            draw.text((776, y + 38), th_d[:23], font=ImageFont.truetype(jp, 15), fill=(232, 236, 244, 255))
            draw.text((776, y + 60), th_d[23:46], font=ImageFont.truetype(jp, 15), fill=(232, 236, 244, 255))
            draw.text((776, y + 82), th_d[46:], font=ImageFont.truetype(jp, 15), fill=(232, 236, 244, 255))
            y += 122

        img.save(out_png)
        return

    if diagram_id == "diagram_06":
        # diagram_06: 【総括表】ギロチンの皮肉・恐怖政治・そして「フランス革命は成功か失敗か？」
        img, draw, jp = _base_board("完全総括 ⑥", "ギロチンの皮肉と「フランス革命は成功か失敗か？」2大史観")

        lbox = (48, 108, 620, 548)
        draw_rounded_box(draw, lbox, radius=14, fill=(32, 26, 36, 245), outline=(205, 110, 110, 200), width=2)
        draw.text((68, 124), "【歴史の皮肉】ギロチンと恐怖政治の真実", font=ImageFont.truetype(jp, 21), fill=(255, 210, 110, 255))

        g_items = [
            ("① 実は「人道と平等」のために発明された装置", "当時、貴族は剣で斬首されたが、平民は車裂きや絞首刑で長時間苦しんだ。医師ギヨタンが『身分を問わず一瞬で苦痛なく処刑する平等な装置』として提案。"),
            ("② ルイ16世自身が「斜めの刃」を助言した説", "錠前作りが趣味だった国王ルイ16世自身が設計図を見て『三日月形の刃より斜めの直線刃の方が確実に切れる』と改良を助言し、のちに自らがその刃で処刑された。"),
            ("③ 恐怖政治の犠牲者の「8割以上」は平民だった", "貴族のための処刑具と思われがちだが、処刑された約1万7,000人のうち貴族・聖職者は約15%で、85%は農民・職人・市民だった。"),
        ]
        y = 172
        for gh, gd in g_items:
            draw.text((68, y), gh, font=ImageFont.truetype(jp, 18), fill=(255, 165, 130, 255))
            draw.text((68, y + 26), gd[:27], font=ImageFont.truetype(jp, 15), fill=(235, 238, 245, 255))
            draw.text((68, y + 48), gd[27:54], font=ImageFont.truetype(jp, 15), fill=(235, 238, 245, 255))
            draw.text((68, y + 70), gd[54:], font=ImageFont.truetype(jp, 15), fill=(235, 238, 245, 255))
            y += 118

        rbox = (646, 108, W - 48, 548)
        draw_rounded_box(draw, rbox, radius=14, fill=(22, 34, 46, 245), outline=(95, 185, 235, 200), width=2)
        draw.text((668, 124), "【歴史学の論争】フランス革命は成功だったのか？", font=ImageFont.truetype(jp, 21), fill=(135, 225, 255, 255))

        debates = [
            ("■ 懐疑・保守派の見解（エドマンド・バーク／トクヴィル等）", "・王を処刑して得た共和政は恐怖政治の虐殺に終わり、わずか10年後にはナポレオンという『独裁皇帝』を生んだ。\n・さらにナポレオン没落後にはブルボン王政復古まで起き、20年以上血を流して一周回って王政に戻ったという批判。"),
            ("■ 肯定・近代史学の見解（なぜ世界史最大の転換点なのか）", "・たとえ皇帝や王が復活しても、『生まれによる免税特権』『封建領主への隷属』は二度と元には戻らなかった。\n・『法の下の平等』『個人の所有権』『主権在民』というフランス人権宣言の原則が、ナポレオン法典を通じて全ヨーロッパ・現代世界へ広がった。"),
        ]
        y = 174
        for dh, dd in debates:
            draw_rounded_box(draw, (664, y, W - 66, y + 170), radius=10, fill=(32, 44, 60, 245), outline=(120, 175, 220, 160), width=2)
            draw.text((678, y + 12), dh, font=ImageFont.truetype(jp, 17), fill=(255, 218, 105, 255))
            raw_text = dd.replace("\n", "")
            chunks = [raw_text[i : i + 26] for i in range(0, len(raw_text), 26)]
            for idx_c, ch in enumerate(chunks[:5]):
                draw.text((678, y + 42 + idx_c * 24), ch, font=ImageFont.truetype(jp, 15), fill=(235, 240, 248, 255))
            y += 184

        img.save(out_png)
        return

    if diagram_id == "diagram_07":
        # 【図解⑦】1785年「首飾り事件」の詐欺相関図と啓蒙思想の3大巨頭
        img, draw, jp = _base_board("事件・思想図解 ⑦", "王室の権威を砕いた「首飾り事件」と3大啓蒙思想家")

        lbox = (48, 108, 618, 548)
        draw_rounded_box(draw, lbox, radius=14, fill=(32, 24, 34, 245), outline=(215, 165, 75, 210), width=2)
        draw.text((68, 124), "① 1785年「ダイヤモンド首飾り事件」の構図", font=ImageFont.truetype(jp, 21), fill=(255, 215, 105, 255))

        scam_steps = [
            ("■ 首謀者：ジャンヌ・ド・ヴァロワ（没落貴族の女詐欺師）", "「私は王妃の親友だ」と偽り、出世欲の強いロアン枢機卿に接近。"),
            ("■ トリック：偽造された王妃の手紙と「夜の庭園の替え玉」", "王妃にそっくりな娼婦ニコルを夜のヴェルサイユ庭園に立たせ、枢機卿に「王妃自身が首飾りを欲しがっている」と信じ込ませた。"),
            ("■ 結末：160万リーヴル（現在の数百億円）の首飾りを詐取", "王妃は全く無関係だったが、裁判で枢機卿が無罪になると、国民は「王妃が詐欺師に罪を被せた」と信じ込み、王室への憎悪が決定的に！"),
        ]
        y = 172
        for sh, sd in scam_steps:
            draw.text((68, y), sh, font=ImageFont.truetype(jp, 17), fill=(255, 185, 115, 255))
            chunks = [sd[i : i + 27] for i in range(0, len(sd), 27)]
            for ic, ch in enumerate(chunks[:3]):
                draw.text((68, y + 26 + ic * 22), ch, font=ImageFont.truetype(jp, 15), fill=(235, 238, 245, 255))
            y += 116

        rbox = (644, 108, W - 48, 548)
        draw_rounded_box(draw, rbox, radius=14, fill=(22, 32, 46, 245), outline=(105, 185, 235, 210), width=2)
        draw.text((666, 124), "② なぜ市民は「王権神授説」を疑い始めたのか？", font=ImageFont.truetype(jp, 20), fill=(135, 225, 255, 255))

        thinkers = [
            ("■ モンテスキュー『法の精神』", "王にすべての権力が集中する絶対王政を批判し、立法・行政・司法の『三権分立』を提唱。"),
            ("■ ヴォルテール『哲学書簡』", "カトリック教会の腐敗と不寛容を痛烈に風刺し、『信教の自由』と『言論の自由』を訴えた。"),
            ("■ ジャン＝ジャック・ルソー『社会契約論』", "『国家の主権は王ではなく人民にある（人民主権）』と説き、のちのロベスピエールら革命派の聖書となった。"),
        ]
        y = 172
        for th, td in thinkers:
            draw_rounded_box(draw, (664, y, W - 66, y + 108), radius=10, fill=(32, 44, 62, 245), outline=(120, 175, 220, 160), width=2)
            draw.text((678, y + 12), th, font=ImageFont.truetype(jp, 18), fill=(255, 218, 105, 255))
            chunks = [td[i : i + 26] for i in range(0, len(td), 26)]
            for ic, ch in enumerate(chunks[:3]):
                draw.text((678, y + 40 + ic * 22), ch, font=ImageFont.truetype(jp, 15), fill=(235, 240, 248, 255))
            y += 120

        img.save(out_png)
        return

    # diagram_08: 【図解⑧】革命議会の3大派閥と「ジャコバン派・三巨頭」の末路
    img, draw, jp = _base_board("派閥・人物図解 ⑧", "革命議会の3大派閥（右派・左派の語源）と三巨頭の末路")

    lbox = (48, 108, 615, 548)
    draw_rounded_box(draw, lbox, radius=14, fill=(24, 30, 44, 245), outline=(198, 162, 72, 200), width=2)
    draw.text((68, 124), "① 現代の政治用語「右派・左派」を生んだ議場の配置", font=ImageFont.truetype(jp, 19), fill=(255, 216, 105, 255))

    factions = [
        ("【議長席から見て右側：右派】フイヤン派（穏健王党派）", "ラ・ファイエット将軍ら。国王を残した『立憲君主制』の維持を主張したが、ヴァレンヌ逃亡事件で失脚。"),
        ("【中央〜やや左：穏健共和派】ジロンド派", "地方の富裕な商工業者を代表。対外戦争を推進したが、王の処刑に慎重だったためジャコバン派に粛清された。"),
        ("【議長席から見て左側最上段：急進左派】ジャコバン派（山岳派）", "ロベスピエールら。パリの貧困市民（サン・キュロット）と結びつき、王の処刑と『恐怖政治』を断行。"),
    ]
    y = 172
    for fh, fd in factions:
        draw_rounded_box(draw, (66, y, 596, y + 108), radius=10, fill=(34, 42, 60, 245), outline=(130, 165, 215, 160), width=2)
        draw.text((80, y + 12), fh, font=ImageFont.truetype(jp, 17), fill=(135, 215, 255, 255))
        chunks = [fd[i : i + 26] for i in range(0, len(fd), 26)]
        for ic, ch in enumerate(chunks[:3]):
            draw.text((80, y + 40 + ic * 22), ch, font=ImageFont.truetype(jp, 15), fill=(235, 240, 248, 255))
        y += 120

    rbox = (642, 108, W - 48, 548)
    draw_rounded_box(draw, rbox, radius=14, fill=(36, 24, 30, 245), outline=(215, 95, 95, 210), width=2)
    draw.text((664, 124), "② 革命を動かした「ジャコバン派・三巨頭」の悲劇的末路", font=ImageFont.truetype(jp, 19), fill=(255, 205, 110, 255))

    leaders = [
        ("■ ジャン＝ポール・マラー（過激派ジャーナリスト）", "新聞『人民の友』で処刑を扇動したが、1793年7月、ジロンド派支持の女性シャルロット・コルデーに入浴中の浴槽で刺殺された（享年50）。"),
        ("■ ジョルジュ・ダントン（豪快な演説家・初代司法大臣）", "かつての盟友だったが『もう恐怖政治を終わらせるべきだ』と寛容を訴えたため、1794年4月、ロベスピエールによってギロチンで処刑（享年34）。"),
        ("■ マクシミリアン・ロベスピエール（「清廉の人」・独裁者）", "盟友ダントンすら処刑して孤立を深め、わずか3ヶ月後の1794年7月、テルミドールのクーデターで自らもギロチンで処刑（享年36）。"),
    ]
    y = 172
    for lh, ld in leaders:
        draw_rounded_box(draw, (660, y, W - 66, y + 112), radius=10, fill=(48, 30, 38, 245), outline=(205, 110, 110, 170), width=2)
        draw.text((674, y + 10), lh, font=ImageFont.truetype(jp, 17), fill=(255, 175, 125, 255))
        chunks = [ld[i : i + 26] for i in range(0, len(ld), 26)]
        for ic, ch in enumerate(chunks[:3]):
            draw.text((674, y + 36 + ic * 22), ch, font=ImageFont.truetype(jp, 15), fill=(238, 240, 246, 255))
        y += 120

    img.save(out_png)


QUESTION_SPECS = {
    "q_01": {
        "badge": "歴史の疑問 Q1 • 身分制度のカラクリ",
        "scene": ("scene_02", 2.0),
        "line1": "なぜ人口の「98%」が飢え、",
        "line2": "収穫の65%が消えたのか？",
        "hint": "【解説ポイント】アンシャン・レジーム（旧体制）の身分ピラミッドと税構造を解剖",
    },
    "q_02": {
        "badge": "歴史の疑問 Q2 • 国家破産の真犯人",
        "scene": ("scene_12", 2.5),
        "line1": "なぜ王妃の浪費ではなく、",
        "line2": "「借金」が国を潰したのか？",
        "hint": "【解説ポイント】国家歳出の50.5%が消えた真犯人と『お菓子発言』の真相を検証",
    },
    "q_03": {
        "badge": "歴史の疑問 Q3 • スキャンダルと革命思想",
        "scene": ("scene_24", 6.0),
        "line1": "なぜ無実の王妃が憎まれ、",
        "line2": "「王はいらない」と気づいたのか？",
        "hint": "【解説ポイント】160万リーヴルの首飾り詐欺事件と「3大啓蒙思想家」を解説",
    },
    "q_04": {
        "badge": "歴史の疑問 Q4 • 異常気象とパン暴騰",
        "scene": ("scene_04", 2.5),
        "line1": "なぜパン1個の値段が",
        "line2": "「日給の9割」に暴騰したのか？",
        "hint": "【解説ポイント】アイスランド火山噴火説と「1789年7月14日のパン価格ピーク」を見る",
    },
    "q_05": {
        "badge": "歴史の疑問 Q5 • バスティーユ襲撃の真相",
        "scene": ("scene_15", 3.0),
        "line1": "なぜ巨大なバスティーユ牢獄に",
        "line2": "囚人が「7人」しかいなかったのか？",
        "hint": "【解説ポイント】三部会「2対1の罠」と、市民が本当に狙った「13.6トンの火薬」",
    },
    "q_06": {
        "badge": "歴史の疑問 Q6 • ヴァレンヌ逃亡の謎",
        "scene": ("scene_17", 5.0),
        "line1": "なぜ国境まで「あと40km」で",
        "line2": "国王一家は捕まったのか？",
        "hint": "【解説ポイント】240km逃亡ルートマップと失敗原因をめぐる「3つの諸説」を比較",
    },
    "q_07": {
        "badge": "歴史の疑問 Q7 • 恐怖政治と同士討ち",
        "scene": ("scene_19", 2.5),
        "line1": "なぜ革命のリーダーたちは",
        "line2": "「味方同士」で殺し合ったのか？",
        "hint": "【解説ポイント】現代の「右派・左派」を生んだ議場配置と三巨頭が全員死んだ理由",
    },
    "q_08": {
        "badge": "歴史の疑問 Q8 • 歴史の皮肉と最終評価",
        "scene": ("scene_01", 5.5),
        "line1": "結局、フランス革命は",
        "line2": "「成功」か？それとも「失敗」か？",
        "hint": "【解説ポイント】ルイ16世自身が改良を助言したギロチンの皮肉と「2大史観の論争」",
    },
}


def render_question_card(q_id: str, out_png: Path, flow_dir: Path) -> None:
    """Render a dramatic 1280x720 Question Close-Up Card before a diagram/table."""
    import subprocess
    from PIL import ImageEnhance, ImageFilter

    spec = QUESTION_SPECS[q_id]
    sc_name, sec = spec["scene"]
    mp4 = flow_dir / f"{sc_name}.mp4"
    if not mp4.exists():
        mp4 = flow_dir / "scene_01.mp4"

    tmp_frame = out_png.parent / f"_tmp_{q_id}_bg.png"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{sec:.2f}", "-i", str(mp4), "-frames:v", "1", str(tmp_frame)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    bg_raw = Image.open(tmp_frame).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    tmp_frame.unlink(missing_ok=True)

    # Place portrait on the right with a smooth gradient mask (x=340..720) so there is zero vertical seam
    bg_enh = ImageEnhance.Contrast(bg_raw).enhance(1.22)
    bg_enh = ImageEnhance.Brightness(bg_enh).enhance(0.92).convert("RGBA")
    bg_shifted = Image.new("RGBA", (W, H), (8, 10, 16, 255))
    bg_shifted.paste(bg_enh, (290, 0))

    bg_comp = Image.new("RGBA", (W, H), (8, 10, 18, 255))
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for x in range(W):
        if x < 340:
            v = 0
        elif x < 760:
            v = int(255 * ((x - 340) / 420.0) ** 1.2)
        else:
            v = 255
        md.line([(x, 0), (x, H)], fill=v)
    bg_comp.paste(bg_shifted, (0, 0), mask)

    # Bottom vignette overlay + double gold/crimson cinema frame
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov, "RGBA")
    for y in range(H - 230, H):
        a = int(230 * ((y - (H - 230)) / 230.0) ** 1.2)
        od.line([(0, y), (W, y)], fill=(6, 8, 14, a))

    # Outer & inner decorative frame
    od.rectangle((22, 20, W - 22, H - 132), outline=(218, 178, 72, 210), width=3)
    od.rectangle((30, 28, W - 30, H - 140), outline=(218, 178, 72, 95), width=1)

    jp = find_cjk_font()

    # Giant glowing "?" watermark on left
    f_qmark = ImageFont.truetype(jp, 260)
    od.text((54, 85), "？", font=f_qmark, fill=(218, 175, 55, 38))

    # Question Badge pill
    draw_rounded_box(
        od,
        (58, 56, 620, 118),
        radius=14,
        fill=(175, 20, 26, 245),
        outline=(255, 220, 105, 255),
        width=3,
    )
    f_badge = _fit_font(od, spec["badge"], jp, 28, 18, 530)
    od.text((82, 71), spec["badge"], font=f_badge, fill=(255, 255, 255, 255))

    bg_comp.alpha_composite(ov)

    # Draw giant two-line Question close-up text
    txt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_layer, "RGBA")

    f_l1 = _fit_font(td, spec["line1"], jp, 62, 36, W - 260)
    f_l2 = _fit_font(td, spec["line2"], jp, 72, 40, W - 220)

    td.text(
        (62, 165),
        spec["line1"],
        font=f_l1,
        fill=(255, 255, 255, 255),
        stroke_width=9,
        stroke_fill=(0, 0, 0, 255),
    )
    td.text(
        (58, 258),
        spec["line2"],
        font=f_l2,
        fill=(255, 222, 75, 255),
        stroke_width=10,
        stroke_fill=(145, 12, 18, 255),
    )

    # Next diagram preview bar above the subtitle area
    draw_rounded_box(
        td,
        (58, 392, W - 120, 464),
        radius=12,
        fill=(18, 24, 36, 235),
        outline=(218, 178, 72, 220),
        width=2,
    )
    f_hint = _fit_font(td, spec["hint"], jp, 27, 17, W - 220)
    td.text((82, 413), spec["hint"], font=f_hint, fill=(135, 220, 255, 255))

    bg_comp.alpha_composite(txt_layer)
    bg_comp.save(out_png)


if __name__ == "__main__":
    out_dir = Path("/Users/takahashitomohiro/Desktop/Youtube PJ/assets/flow_history_fr_rev/diagrams")
    flow_dir = Path("/Users/takahashitomohiro/Desktop/Youtube PJ/assets/flow_history_fr_rev")
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 9):
        did = f"diagram_{i:02d}"
        p = out_dir / f"{did}.png"
        render_diagram_board(did, p)
        qid = f"q_{i:02d}"
        qp = out_dir / f"{qid}.png"
        render_question_card(qid, qp, flow_dir)
        print("Rendered:", p.name, "and", qp.name)

