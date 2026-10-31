#!/usr/bin/env python3
"""
templars_infographics.py

Bespoke Multi-Step Storyboard Illustrations (Pattern-A / 裏視点物語 style) for Episode 3:
"The Crusades & Knights Templar — Why the Heroes of the Holy War Became the World's
First Mega-Bank and Were Arrested on Friday the 13th".

Instead of using a single static 2-column comparison layout across all 8 diagrams,
each diagram_01..08 has its own custom visual scene archetype AND splits into two
progressive beat frames (`diagram_XX_b1.png` -> `diagram_XX_b2.png`) so the board
dynamically changes/animates in sync with the 1st and 2nd narration beats!
"""

import math
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont

from build_japan_ranking import draw_rounded_box, find_cjk_font
from history_infographics import _base_board, _fit_font
from rome_fall_infographics import (
    _draw_pattern_a_silhouette_1280,
    _draw_stroked_txt,
    render_pattern_a_question_card,
)

W, H = 1280, 720


def _draw_callout(
    draw: ImageDraw.ImageDraw,
    jp: str,
    anchor: Tuple[int, int],
    label_pos: Tuple[int, int],
    text: str,
    color: Tuple[int, int, int, int] = (255, 235, 165, 255),
    pt: int = 21,
) -> None:
    """Draw a signature 裏視点物語 `───` callout line + underlined label."""
    f = _fit_font(draw, text, jp, pt, 14, 460)
    tb = draw.textbbox((0, 0), text, font=f)
    tw = tb[2] - tb[0]
    lx, ly = label_pos
    draw.line([anchor, (lx, ly + 30)], fill=(235, 235, 240, 215), width=2)
    draw.line([(lx, ly + 30), (lx + tw + 12, ly + 30)], fill=(235, 235, 240, 215), width=2)
    _draw_stroked_txt(draw, (lx + 4, ly), text, f, color, sw=3)


def _draw_templar_knight(
    draw: ImageDraw.ImageDraw,
    cx: int,
    base_y: int,
    scale: float = 1.0,
    chained: bool = False,
) -> None:
    """Draw a distinct Pattern-A Templar Knight silhouette (white mantle + red cross)."""
    head_r = int(36 * scale)
    head_cy = base_y - int(162 * scale)
    torso_top = head_cy + head_r - int(4 * scale)
    torso_w = int(86 * scale)

    # White Templar mantle with warm gold rim
    draw.polygon(
        [
            (cx - torso_w // 2, torso_top),
            (cx + torso_w // 2, torso_top),
            (cx + int(torso_w * 0.72), base_y),
            (cx - int(torso_w * 0.72), base_y),
        ],
        fill=(238, 236, 228, 255),
        outline=(215, 190, 125, 255),
        width=3,
    )
    # Dark inner tunic
    draw.polygon(
        [
            (cx - int(torso_w * 0.24), torso_top),
            (cx + int(torso_w * 0.24), torso_top),
            (cx + int(torso_w * 0.30), base_y),
            (cx - int(torso_w * 0.30), base_y),
        ],
        fill=(32, 34, 42, 255),
    )
    # Red Templar Cross on chest
    cy_c = torso_top + int(52 * scale)
    arm = int(20 * scale)
    thk = max(3, int(6 * scale))
    draw.rectangle([cx - thk, cy_c - arm, cx + thk, cy_c + arm], fill=(195, 32, 32, 255))
    draw.rectangle([cx - arm, cy_c - thk, cx + arm, cy_c + thk], fill=(195, 32, 32, 255))

    # Great Helm / Head
    draw.ellipse(
        [cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
        fill=(245, 244, 240, 255),
        outline=(190, 175, 140, 255),
        width=3,
    )
    # Visor slit
    draw.rectangle([cx - int(head_r * 0.55), head_cy - 3, cx + int(head_r * 0.55), head_cy + 3], fill=(25, 28, 36, 255))

    if chained:
        # Iron chains across torso
        draw.line([(cx - int(45 * scale), torso_top + 20), (cx + int(48 * scale), base_y - 25)], fill=(155, 165, 180, 255), width=5)
        draw.line([(cx + int(45 * scale), torso_top + 20), (cx - int(48 * scale), base_y - 25)], fill=(155, 165, 180, 255), width=5)


def _draw_fortress_tower(
    draw: ImageDraw.ImageDraw,
    cx: int,
    base_y: int,
    w: int = 120,
    h: int = 175,
    label: str = "",
    jp: str = "",
    gold_glow: bool = False,
) -> None:
    """Draw a medieval stone fortress / Temple Tower with battlements and red cross banner."""
    x0, y0 = cx - w // 2, base_y - h
    x1, y1 = cx + w // 2, base_y
    if gold_glow:
        draw.ellipse([cx - w, y0 - 30, cx + w, y1 + 10], fill=(225, 180, 55, 55))
    draw.rectangle([x0, y0 + 18, x1, y1], fill=(42, 46, 58, 255), outline=(195, 175, 125, 255), width=3)
    # Battlements (crenellations)
    bw = w // 5
    for i in range(0, 5, 2):
        bx = x0 + i * bw
        draw.rectangle([bx, y0, bx + bw, y0 + 20], fill=(42, 46, 58, 255), outline=(195, 175, 125, 255), width=2)
    # Arch gate
    gw, gh = w // 3, h // 3
    draw.rectangle([cx - gw // 2, base_y - gh, cx + gw // 2, base_y], fill=(16, 18, 24, 255), outline=(150, 135, 95, 255), width=2)
    # Red cross shield on tower
    sy = y0 + 58
    draw.rectangle([cx - 6, sy - 18, cx + 6, sy + 18], fill=(205, 38, 38, 255))
    draw.rectangle([cx - 18, sy - 6, cx + 18, sy + 6], fill=(205, 38, 38, 255))
    if label and jp:
        f = _fit_font(draw, label, jp, 18, 13, w + 90)
        tb = draw.textbbox((0, 0), label, font=f)
        _draw_stroked_txt(draw, (cx - (tb[2] - tb[0]) // 2, y0 - 30), label, f, (255, 230, 145, 255), sw=3)


def _draw_parchment_scroll(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    title: str,
    lines: List[str],
    jp: str,
    seals: int = 1,
    stamp_text: str = "",
) -> None:
    """Draw a warm medieval parchment scroll with wax seal(s)."""
    x0, y0, x1, y1 = box
    # Roll ends
    draw_rounded_box(draw, (x0 - 10, y0, x1 + 10, y0 + 22), radius=10, fill=(195, 165, 110, 255), outline=(120, 90, 45, 255), width=2)
    draw_rounded_box(draw, (x0 - 10, y1 - 22, x1 + 10, y1), radius=10, fill=(195, 165, 110, 255), outline=(120, 90, 45, 255), width=2)
    # Main parchment body
    draw.rectangle([x0, y0 + 18, x1, y1 - 18], fill=(238, 222, 182, 255), outline=(145, 112, 62, 255), width=3)

    f_t = _fit_font(draw, title, jp, 24, 15, (x1 - x0) - 36)
    tb = draw.textbbox((0, 0), title, font=f_t)
    draw.text(((x0 + x1 - (tb[2] - tb[0])) // 2, y0 + 30), title, font=f_t, fill=(95, 24, 18, 255))
    draw.line([(x0 + 24, y0 + 66), (x1 - 24, y0 + 66)], fill=(155, 120, 70, 200), width=2)

    y_cur = y0 + 70
    line_step = 28 if len(lines) >= 6 else 29
    for ln in lines:
        f_l = _fit_font(draw, ln, jp, 18, 13, (x1 - x0) - 44)
        draw.text((x0 + 22, y_cur), ln, font=f_l, fill=(38, 30, 22, 255))
        y_cur += line_step

    # Red wax seals at bottom
    for s_idx in range(seals):
        sx = x1 - 48 - s_idx * 54
        sy = y1 - 38
        # Ribbon
        draw.polygon([(sx - 7, sy), (sx + 7, sy), (sx + 12, sy + 30), (sx - 12, sy + 30)], fill=(175, 28, 28, 255))
        draw.ellipse([sx - 18, sy - 18, sx + 18, sy + 18], fill=(195, 25, 25, 255), outline=(255, 205, 110, 255), width=2)
        draw.ellipse([sx - 11, sy - 11, sx + 11, sy + 11], outline=(130, 12, 12, 255), width=2)

    if stamp_text:
        f_st = _fit_font(draw, stamp_text, jp, 19, 13, (x1 - x0) - 180)
        stb = draw.textbbox((0, 0), stamp_text, font=f_st)
        sw_box = stb[2] - stb[0] + 22
        sx0 = x0 + 24
        sy0 = y1 - 54
        draw_rounded_box(draw, (sx0, sy0, sx0 + sw_box, sy0 + 32), radius=7, fill=(195, 22, 22, 242), outline=(255, 230, 140, 255), width=2)
        draw.text((sx0 + 11, sy0 + 5), stamp_text, font=f_st, fill=(255, 255, 255, 255))


def render_templar_diagram_board(diagram_id: str, out_png: Path, step: int = 2) -> None:
    """
    Render progressive storyboard diagrams (`step=1` for Beat 1, `step=2` for Beat 2).
    Every diagram_01..08 has a distinct visual layout matching the reference video (`裏視点物語`)!
    """
    hy = int(H * 0.76)  # 547 ground line

    # =========================================================================
    # DIAGRAM 01: Split-Stage Curtain Reveal (表の顔：清貧の戦闘修道士 → 裏の顔：欧州9,000拠点の国際メガバンク)
    # =========================================================================
    if diagram_id == "diagram_01":
        img, draw, jp = _base_board(
            "歴史図解 ①",
            "テンプル騎士団「2つの顔」── 清貧の修道士か、世界初の巨大銀行か？",
        )
        # Theatrical curtain valence at top (like 裏視点物語 row 3 center)
        for cx_c in range(0, W, 80):
            draw.arc([cx_c - 10, 58, cx_c + 90, 96], start=0, end=180, fill=(135, 28, 34, 210), width=6)

        # Left Half (Always visible in Step 1 & Step 2): Humble combat monk
        draw_rounded_box(draw, (46, 98, 590, 218), radius=14, fill=(32, 24, 28, 235), outline=(215, 75, 75, 225), width=2)
        _draw_stroked_txt(draw, (68, 110), "【表の顔】聖地を守る「清貧の戦闘修道士」", _fit_font(draw, "【表の顔】聖地を守る「清貧の戦闘修道士」", jp, 22, 15, 510), (255, 215, 130, 255), sw=3)
        draw.text((68, 148), "・1119年 わずか9人の貧しい騎士が巡礼者保護で創設", font=_fit_font(draw, "・1119年 わずか9人の貧しい騎士が巡礼者保護で創設", jp, 18, 13, 505), fill=(240, 242, 248, 255))
        draw.text((68, 180), "・個人の財産・結婚は一切禁止 ／ 3対1でも退却厳禁", font=_fit_font(draw, "・個人の財産・結婚は一切禁止 ／ 3対1でも退却厳禁", jp, 18, 13, 505), fill=(255, 185, 185, 255))

        # Two knights sharing one emblem / standing in humility
        _draw_templar_knight(draw, 225, hy, scale=1.02)
        _draw_templar_knight(draw, 355, hy, scale=0.92)
        _draw_callout(draw, jp, (225, hy - 170), (66, 250), "ユーグ・ド・パイヤンら9人の創設騎士", (255, 235, 165, 255), 20)

        if step == 1:
            # Step 1: Mystery silhouette curtain on the right ("裏の顔：？？？")
            draw_rounded_box(draw, (650, 118, 1220, 515), radius=18, fill=(16, 20, 28, 215), outline=(120, 130, 155, 140), width=2)
            f_q = ImageFont.truetype(jp, 92)
            _draw_stroked_txt(draw, (895, 235), "？", f_q, (225, 195, 100, 190), sw=5)
            f_sub = _fit_font(draw, "なぜ「無一文の修道士」が国家を超える富を築いたのか？", jp, 21, 14, 520)
            _draw_stroked_txt(draw, (682, 385), "なぜ「無一文の修道士」が国家を超える富を築いたのか？", f_sub, (210, 220, 235, 230), sw=3)
        else:
            # Step 2: Golden arrow + Full Mega-Bank Fortress Network reveal on right!
            f_arr = ImageFont.truetype(jp, 52)
            _draw_stroked_txt(draw, (598, 295), "⇒", f_arr, (255, 215, 75, 255), sw=5)

            draw_rounded_box(draw, (656, 98, 1234, 218), radius=14, fill=(20, 32, 48, 240), outline=(85, 185, 255, 235), width=2)
            _draw_stroked_txt(draw, (678, 110), "【裏の顔】欧州9,000拠点「世界初の多国籍銀行」", _fit_font(draw, "【裏の顔】欧州9,000拠点「世界初の多国籍銀行」", jp, 22, 15, 540), (135, 230, 255, 255), sw=3)
            draw.text((678, 148), "・1139年 教皇大勅書で「全税金免除・国王の干渉不可」", font=_fit_font(draw, "・1139年 教皇大勅書で「全税金免除・国王の干渉不可」", jp, 18, 13, 540), fill=(240, 245, 250, 255))
            draw.text((678, 180), "・暗号小切手と9,000箇所の要塞網で王侯貴族に巨額融資", font=_fit_font(draw, "・暗号小切手と9,000箇所の要塞網で王侯貴族に巨額融資", jp, 18, 13, 540), fill=(255, 225, 115, 255))

            # 3 Fortress towers connected by glowing gold lines
            _draw_fortress_tower(draw, 760, hy, w=96, h=148, label="ロンドン支部", jp=jp, gold_glow=True)
            _draw_fortress_tower(draw, 945, hy, w=116, h=182, label="パリ・テンプル塔", jp=jp, gold_glow=True)
            _draw_fortress_tower(draw, 1130, hy, w=96, h=148, label="聖地エルサレム", jp=jp, gold_glow=True)
            draw.line([(808, hy - 95), (887, hy - 115)], fill=(255, 215, 75, 235), width=4)
            draw.line([(1003, hy - 115), (1082, hy - 95)], fill=(255, 215, 75, 235), width=4)

        img.save(out_png)
        return

    # =========================================================================
    # DIAGRAM 02: Pope Urban II's Pulpit vs 3 Hidden Motives Convergence Map
    # =========================================================================
    if diagram_id == "diagram_02":
        img, draw, jp = _base_board(
            "歴史検証 ②",
            "1095年クレルモン公会議と「第1回十字軍」を動かした本当の動機",
        )
        # Left: Pope Urban II on raised pulpit + Indulgence Scroll ("過去の罪をすべて赦す")
        draw.rectangle([90, hy - 55, 290, hy], fill=(52, 42, 34, 255), outline=(195, 165, 95, 255), width=2)
        _draw_pattern_a_silhouette_1280(draw, 190, hy - 55, "right_power", (245, 200, 75, 255))
        _draw_callout(draw, jp, (190, hy - 225), (48, 96), "教皇ウルバヌス2世（1095年）", (255, 230, 145, 255), 20)

        _draw_parchment_scroll(
            draw,
            (48, 152, 535, 382),
            "【建前】教皇の宣言「デウス・ウルト！」",
            [
                "① 聖地エルサレムをイスラムから奪還せよ",
                "② 従軍すれば「過去のすべての罪」が帳消し",
                "③ 1099年陥落時、神殿で凄惨な大虐殺が発生",
            ],
            jp,
            seals=1,
            stamp_text="天国への切符（贖宥）",
        )

        if step == 1:
            # Step 1: Crowd of zealous knights on the right shouting "Deus Vult!"
            for idx_k, kx in enumerate([720, 835, 950, 1065, 1170]):
                _draw_templar_knight(draw, kx, hy, scale=0.82 if idx_k % 2 else 0.90)
            draw_rounded_box(draw, (650, 155, 1210, 295), radius=16, fill=(145, 28, 28, 235), outline=(255, 215, 90, 255), width=3)
            _draw_stroked_txt(draw, (682, 176), "『デウス・ウルト（神が望まれる）！』", _fit_font(draw, "『デウス・ウルト（神が望まれる）！』", jp, 28, 18, 500), (255, 240, 150, 255), sw=4)
            draw.text((682, 232), "全ヨーロッパの騎士・民衆約6万人が熱狂し進軍開始", font=_fit_font(draw, "全ヨーロッパの騎士・民衆約6万人が熱狂し進軍開始", jp, 20, 14, 500), fill=(255, 255, 255, 255))
        else:
            # Step 2: Reveal the 3 Realistic Political/Economic Motives Cards on the right!
            motives = [
                ("裏の動機 ①：ローマ教皇の覇権拡大", "1054年に分裂した「東方正教会」を助け、ローマ教皇の傘下に置く政治的野心", (185, 135, 35, 240)),
                ("裏の動機 ②：「長子相続制」であぶれた次男・三男", "ヨーロッパで親の領地を継げない過剰な若手騎士たちが「東方の新領土」を渇望", (185, 52, 52, 240)),
                ("裏の動機 ③：イタリア海洋都市の「貿易独占」", "ヴェネツィア・ジェノヴァ商人が東地中海の香辛料・絹ルートを独占するビジネス", (38, 118, 175, 240)),
            ]
            y_m = 112
            for m_title, m_desc, m_col in motives:
                draw_rounded_box(draw, (578, y_m, 1232, y_m + 124), radius=14, fill=(22, 28, 40, 242), outline=m_col, width=3)
                draw_rounded_box(draw, (578, y_m, 1232, y_m + 42), radius=12, fill=m_col)
                draw.text((600, y_m + 8), m_title, font=_fit_font(draw, m_title, jp, 21, 14, 620), fill=(255, 255, 255, 255))
                draw.text((600, y_m + 56), m_desc[:31], font=_fit_font(draw, m_desc[:31], jp, 18, 13, 620), fill=(238, 242, 248, 255))
                if len(m_desc) > 31:
                    draw.text((600, y_m + 84), m_desc[31:], font=_fit_font(draw, m_desc[31:], jp, 18, 13, 620), fill=(255, 225, 130, 255))
                y_m += 140

        img.save(out_png)
        return

    # =========================================================================
    # DIAGRAM 03: 3-Panel Flow Card (Paris Deposit -> Encrypted Scroll -> Jerusalem Cash) + Usury Bypass
    # =========================================================================
    if diagram_id == "diagram_03":
        img, draw, jp = _base_board(
            "金融システム図解 ③",
            "世界初の国際小切手（トラベラーズチェック）と「利子禁止」突破のカラクリ",
        )
        # Top half (Always visible): 3-Stage Visual Pipeline (like 裏視点物語 row 4 right)
        stages = [
            (52, 406, "STEP 1｜パリ・ロンドン支部", "巡礼者が重い金貨を要塞金庫へ預ける", "山賊・海賊に襲われるリスクをゼロに", (48, 115, 175, 240)),
            (450, 830, "STEP 2｜暗号化された羊皮紙", "金額と「秘密の封蝋印」入りの信用状", "手ぶら（羊皮紙1枚）で3,000kmを移動", (195, 145, 38, 240)),
            (874, 1228, "STEP 3｜聖地エルサレム支部", "暗号を照合し現地通貨を即座に引き出し", "12世紀に実現した「世界初の国際送金網」", (42, 138, 92, 240)),
        ]
        for x0, x1, s_head, s_l1, s_l2, s_col in stages:
            draw_rounded_box(draw, (x0, 96, x1, 292), radius=14, fill=(22, 26, 38, 242), outline=s_col, width=3)
            draw_rounded_box(draw, (x0, 96, x1, 140), radius=12, fill=s_col)
            draw.text((x0 + 16, 106), s_head, font=_fit_font(draw, s_head, jp, 20, 14, (x1 - x0) - 28), fill=(255, 255, 255, 255))
            draw.text((x0 + 18, 162), s_l1, font=_fit_font(draw, s_l1, jp, 19, 13, (x1 - x0) - 32), fill=(245, 248, 252, 255))
            draw.text((x0 + 18, 212), f"→ {s_l2}", font=_fit_font(draw, f"→ {s_l2}", jp, 18, 13, (x1 - x0) - 32), fill=(255, 225, 120, 255))

        f_ar = ImageFont.truetype(jp, 34)
        _draw_stroked_txt(draw, (411, 174), "⇒", f_ar, (255, 215, 85, 255), sw=4)
        _draw_stroked_txt(draw, (835, 174), "⇒", f_ar, (255, 215, 85, 255), sw=4)

        if step == 1:
            # Step 1: Show visual fortress & pilgrim silhouettes along the bottom horizon
            _draw_fortress_tower(draw, 220, hy, w=110, h=165, label="パリのテンプル要塞", jp=jp, gold_glow=True)
            _draw_pattern_a_silhouette_1280(draw, 640, hy, "left_hero", (255, 220, 110, 255))
            _draw_callout(draw, jp, (640, hy - 175), (490, 325), "羊皮紙1枚で旅をする巡礼者", (255, 235, 165, 255), 20)
            _draw_fortress_tower(draw, 1050, hy, w=110, h=165, label="エルサレム本部", jp=jp, gold_glow=True)
        else:
            # Step 2: Reveal the Church Usury Ban vs Templar Loophole Equation on the bottom half!
            draw_rounded_box(draw, (52, 320, 560, 526), radius=14, fill=(46, 22, 26, 242), outline=(215, 68, 68, 235), width=3)
            _draw_stroked_txt(draw, (74, 336), "× カトリック教会の鉄則：「利子は大罪」", _fit_font(draw, "× カトリック教会の鉄則：「利子は大罪」", jp, 22, 15, 480), (255, 155, 155, 255), sw=3)
            draw.text((74, 386), "・聖書の教えでお金に利子（ウスラ）をつける", font=_fit_font(draw, "・聖書の教えでお金に利子（ウスラ）をつける", jp, 18, 13, 470), fill=(240, 240, 245, 255))
            draw.text((74, 418), "  高利貸しは「地獄落ちの大罪」として厳禁", font=_fit_font(draw, "  高利貸しは「地獄落ちの大罪」として厳禁", jp, 18, 13, 470), fill=(240, 240, 245, 255))
            draw.text((74, 464), "→ 通常のキリスト教徒は銀行業ができなかった", font=_fit_font(draw, "→ 通常のキリスト教徒は銀行業ができなかった", jp, 19, 13, 470), fill=(255, 215, 110, 255))

            _draw_stroked_txt(draw, (582, 398), "⇒", ImageFont.truetype(jp, 48), (255, 220, 80, 255), sw=5)

            draw_rounded_box(draw, (650, 320, 1228, 526), radius=14, fill=(20, 38, 34, 242), outline=(72, 215, 145, 235), width=3)
            _draw_stroked_txt(draw, (674, 336), "◎ 騎士団の錬金術：「手数料＆領地担保」", _fit_font(draw, "◎ 騎士団の錬金術：「手数料＆領地担保」", jp, 22, 15, 535), (135, 250, 185, 255), sw=3)
            draw.text((674, 386), "① 利子ではなく「両替・警備・輸送の手数料」で10%徴収", font=_fit_font(draw, "① 利子ではなく「両替・警備・輸送の手数料」で10%徴収", jp, 18, 13, 535), fill=(245, 248, 252, 255))
            draw.text((674, 424), "② 貸付の担保に「貴族の領地の徴税権」を丸ごと獲得", font=_fit_font(draw, "② 貸付の担保に「貴族の領地の徴税権」を丸ごと獲得", jp, 18, 13, 535), fill=(245, 248, 252, 255))
            draw.text((674, 464), "③ フランス王の「王冠」すら担保としてテンプル塔に保管！", font=_fit_font(draw, "③ フランス王の「王冠」すら担保としてテンプル塔に保管！", jp, 19, 13, 535), fill=(255, 225, 110, 255))

        img.save(out_png)
        return

    # =========================================================================
    # DIAGRAM 04: 1204 Fourth Crusade Detour Map & Venetian Debt Breakdown
    # =========================================================================
    if diagram_id == "diagram_04":
        img, draw, jp = _base_board(
            "歴史の暴走 ④",
            "1204年 第4回十字軍──「8万5000マルクの借金」が招いたキリスト教首都略奪",
        )
        # Left: Venetian Debt Bar Chart (Expected 33,500 troops vs Actual 12,000 troops)
        draw_rounded_box(draw, (48, 100, 595, 520), radius=14, fill=(24, 28, 40, 242), outline=(215, 90, 90, 225), width=2)
        _draw_stroked_txt(draw, (70, 116), "① ヴェネツィアへの「船代借金」の悲劇", _fit_font(draw, "① ヴェネツィアへの「船代借金」の悲劇", jp, 23, 15, 510), (255, 220, 120, 255), sw=3)

        draw.text((70, 168), "■ 契約した兵力：33,500人分（船代 85,000銀マルク）", font=_fit_font(draw, "■ 契約した兵力：33,500人分（船代 85,000銀マルク）", jp, 18, 13, 505), fill=(230, 235, 245, 255))
        draw_rounded_box(draw, (70, 198, 565, 234), radius=8, fill=(65, 125, 195, 240))
        draw.text((84, 204), "ヴェネツィアが500隻の大艦隊を建造（仏・英の年収2倍！）", font=_fit_font(draw, "ヴェネツィアが500隻の大艦隊を建造（仏・英の年収2倍！）", jp, 16, 12, 470), fill=(255, 255, 255, 255))

        draw.text((70, 254), "■ 実際に集まった兵力：わずか 12,000人（3分の1！）", font=_fit_font(draw, "■ 実際に集まった兵力：わずか 12,000人（3分の1！）", jp, 18, 13, 505), fill=(255, 150, 150, 255))
        draw_rounded_box(draw, (70, 284, 245, 320), radius=8, fill=(215, 55, 55, 240))
        draw_rounded_box(draw, (252, 284, 565, 320), radius=8, fill=(60, 25, 28, 230), outline=(215, 55, 55, 200), width=2)
        draw.text((266, 290), "未払い借金：34,000マルク発生！", font=_fit_font(draw, "未払い借金：34,000マルク発生！", jp, 17, 12, 290), fill=(255, 215, 110, 255))

        draw_rounded_box(draw, (70, 344, 565, 500), radius=12, fill=(38, 22, 28, 240), outline=(225, 165, 65, 210), width=2)
        draw.text((88, 358), "【90歳の盲目の元首エンリコ・ダンドロの要求】", font=_fit_font(draw, "【90歳の盲目の元首エンリコ・ダンドロの要求】", jp, 19, 13, 460), fill=(255, 220, 115, 255))
        draw.text((88, 394), "『借金を待ってほしければ、ヴェネツィアの商売敵", font=_fit_font(draw, "『借金を待ってほしければ、ヴェネツィアの商売敵", jp, 18, 13, 460), fill=(245, 245, 250, 255))
        draw.text((88, 424), "  であるキリスト教都市ザダルをまず攻め落とせ！』", font=_fit_font(draw, "  であるキリスト教都市ザダルをまず攻め落とせ！』", jp, 18, 13, 460), fill=(245, 245, 250, 255))
        draw.text((88, 462), "→ 1202年 ザダル襲撃でローマ教皇が十字軍全員を「破門」", font=_fit_font(draw, "→ 1202年 ザダル襲撃でローマ教皇が十字軍全員を「破門」", jp, 17, 12, 460), fill=(255, 145, 145, 255))

        if step == 1:
            # Step 1: Show Doge Dandolo silhouette & Fleet waiting on right
            _draw_pattern_a_silhouette_1280(draw, 920, hy, "right_power", (235, 65, 65, 255))
            _draw_callout(draw, jp, (920, hy - 175), (675, 145), "90歳の盲目の元首エンリコ・ダンドロ", (255, 225, 135, 255), 22)
            draw_rounded_box(draw, (660, 225, 1215, 340), radius=14, fill=(24, 32, 48, 235), outline=(120, 185, 245, 215), width=2)
            draw.text((685, 245), "十字軍は借金のカタにヴェネツィアの「傭兵」と化し、", font=_fit_font(draw, "十字軍は借金のカタにヴェネツィアの「傭兵」と化し、", jp, 20, 14, 520), fill=(245, 248, 252, 255))
            draw.text((685, 285), "本来の目的地（エジプト・聖地）から大きく進路を逸れる…", font=_fit_font(draw, "本来の目的地（エジプト・聖地）から大きく進路を逸れる…", jp, 20, 14, 520), fill=(255, 215, 115, 255))
        else:
            # Step 2: Show the Trajectory Map of the Detour & Fall of Constantinople on right!
            draw_rounded_box(draw, (625, 100, 1232, 520), radius=14, fill=(20, 26, 38, 242), outline=(85, 185, 255, 225), width=2)
            _draw_stroked_txt(draw, (648, 116), "② 進路変更マップ：なぜコンスタンティノープルへ？", _fit_font(draw, "② 進路変更マップ：なぜコンスタンティノープルへ？", jp, 22, 15, 570), (135, 230, 255, 255), sw=3)

            # Visual Nodes: Venice -> Zadar -> Constantinople (vs X Jerusalem)
            nodes = [
                (720, 210, "ヴェネツィア出発", (65, 135, 205, 255)),
                (720, 320, "① ザダル襲撃（破門）", (215, 140, 45, 255)),
                (1055, 250, "② 1204年 コンスタンティノープル陥落！", (215, 42, 42, 255)),
                (1055, 365, "× 聖地エルサレム（一歩も届かず解散）", (110, 118, 135, 255)),
            ]
            # Arrows
            draw.line([(720, 235), (720, 295)], fill=(255, 215, 80, 240), width=4)
            draw.line([(790, 315), (960, 260)], fill=(255, 75, 75, 255), width=5)
            # Dashed crossed-out line to Jerusalem
            draw.line([(720, 335), (960, 365)], fill=(120, 125, 140, 160), width=3)

            for nx, ny, n_lbl, ncol in nodes:
                draw.ellipse([nx - 14, ny - 14, nx + 14, ny + 14], fill=ncol, outline=(255, 255, 255, 255), width=2)
                f_n = _fit_font(draw, n_lbl, jp, 19, 13, 340)
                _draw_stroked_txt(draw, (nx - 65 if nx < 850 else nx - 165, ny - 42), n_lbl, f_n, (255, 245, 200, 255), sw=3)

            draw_rounded_box(draw, (648, 428, 1210, 496), radius=10, fill=(52, 20, 24, 240), outline=(235, 75, 75, 220), width=2)
            draw.text((664, 448), "東ローマ皇子の「20万マルク報酬」の約束が破られ総攻撃・3日間大略奪！", font=_fit_font(draw, "東ローマ皇子の「20万マルク報酬」の約束が破られ総攻撃・3日間大略奪！", jp, 17, 12, 535), fill=(255, 225, 130, 255))

        img.save(out_png)
        return

    # =========================================================================
    # DIAGRAM 05: Timeline Scroll & Fact-Check Stamp (1307.10.13 Arrest vs 1314.3.18 Execution)
    # =========================================================================
    if diagram_id == "diagram_05":
        img, draw, jp = _base_board(
            "国家犯罪の全貌 ⑤",
            "1307年10月13日（金曜日）一斉逮捕作戦と「処刑日」のファクトチェック",
        )
        # Top Horizontal Scroll Timeline (like 裏視点物語 row 4 left)
        _draw_parchment_scroll(
            draw,
            (64, 92, 1216, 304),
            "【歴史ファクトチェック年表】「13日の金曜日に処刑された」は後世の混同！",
            [
                "● 1306年：仏王フィリップ4世が銀貨の銀を3分の1に減らす通貨改悪 → パリ暴動でテンプル塔へ逃げ込む",
                "● 1307年9月14日：宰相ノガレが「10月13日夜明け前に開封せよ」という二重封印の極秘命令書を全国へ配布",
                "● 1307年10月13日（金）：フランス全土で【一斉逮捕・資産凍結】（※火刑は7年後の1314年3月18日）",
            ],
            jp,
            seals=2,
            stamp_text="10月13日(金)＝一斉逮捕の日",
        )

        if step == 1:
            # Step 1: Focus on the Dawn Raid on the Paris Temple Tower
            _draw_fortress_tower(draw, 640, hy, w=140, h=195, label="1307年10月13日（金）パリ・テンプル塔包囲", jp=jp)
            _draw_templar_knight(draw, 460, hy, scale=0.95, chained=True)
            _draw_pattern_a_silhouette_1280(draw, 820, hy, "right_power", (235, 55, 55, 255))
            _draw_callout(draw, jp, (460, hy - 165), (110, 340), "無抵抗で鎖に繋がれたモレー総長", (255, 230, 150, 255), 20)
            _draw_callout(draw, jp, (820, hy - 165), (875, 340), "借金まみれの国王フィリップ4世", (255, 165, 165, 255), 20)
        else:
            # Step 2: Reveal Why the King Had to Fabricate the "Heresy / Devil Worship" Scandal!
            draw_rounded_box(draw, (64, 322, 610, 524), radius=14, fill=(44, 22, 26, 242), outline=(225, 75, 75, 235), width=3)
            _draw_stroked_txt(draw, (86, 338), "① 国王フィリップ4世の「本当の狙い」", _fit_font(draw, "① 国王フィリップ4世の「本当の狙い」", jp, 22, 15, 505), (255, 215, 120, 255), sw=3)
            draw.text((86, 386), "・英・フランドル戦争で破産し騎士団に巨額の借金", font=_fit_font(draw, "・英・フランドル戦争で破産し騎士団に巨額の借金", jp, 18, 13, 505), fill=(242, 245, 250, 255))
            draw.text((86, 420), "・テンプル塔に逃げ込んだ際、地下金庫の金銀を目撃", font=_fit_font(draw, "・テンプル塔に逃げ込んだ際、地下金庫の金銀を目撃", jp, 18, 13, 505), fill=(242, 245, 250, 255))
            draw.text((86, 464), "→ 借金を踏み倒し、騎士団の全資産を奪う「国家強盗」", font=_fit_font(draw, "→ 借金を踏み倒し、騎士団の全資産を奪う「国家強盗」", jp, 19, 13, 505), fill=(255, 155, 155, 255))

            _draw_stroked_txt(draw, (620, 398), "⇒", ImageFont.truetype(jp, 44), (255, 215, 80, 255), sw=4)

            draw_rounded_box(draw, (670, 322, 1216, 524), radius=14, fill=(22, 32, 48, 242), outline=(95, 190, 255, 235), width=3)
            _draw_stroked_txt(draw, (692, 338), "② なぜ「悪魔崇拝」を捏造したのか？", _fit_font(draw, "② なぜ「悪魔崇拝」を捏造したのか？", jp, 22, 15, 505), (135, 230, 255, 255), sw=3)
            draw.text((692, 386), "・騎士団は「教皇直属」のため国王に逮捕権はなかった", font=_fit_font(draw, "・騎士団は「教皇直属」のため国王に逮捕権はなかった", jp, 18, 13, 505), fill=(242, 245, 250, 255))
            draw.text((692, 420), "・唯一、国王が介入できる口実が「異端・悪魔崇拝」", font=_fit_font(draw, "・唯一、国王が介入できる口実が「異端・悪魔崇拝」", jp, 18, 13, 505), fill=(242, 245, 250, 255))
            draw.text((692, 464), "→ 宰相ノガレが前代未聞のスキャンダルを捏造！", font=_fit_font(draw, "→ 宰相ノガレが前代未聞のスキャンダルを捏造！", jp, 19, 13, 505), fill=(255, 225, 115, 255))

        img.save(out_png)
        return

    # =========================================================================
    # DIAGRAM 06: Baphomet Linguistic Truth (1856 Goat Myth Crossed Out -> "Mahomet" Corruption)
    # =========================================================================
    if diagram_id == "diagram_06":
        img, draw, jp = _base_board(
            "異端審問のカラクリ ⑥",
            "悪魔「バフォメット」の正体──拷問が生んだ冤罪と言語学の結論",
        )
        # Left Card: The Fabricated Charges & Torture (36 knights tortured to death in Paris)
        draw_rounded_box(draw, (48, 102, 590, 520), radius=14, fill=(42, 20, 24, 242), outline=(225, 68, 68, 235), width=3)
        draw_rounded_box(draw, (48, 102, 590, 150), radius=12, fill=(175, 38, 38, 245))
        draw.text((70, 112), "× 審問官が拷問で強要した「異端の罪状リスト」", font=_fit_font(draw, "× 審問官が拷問で強要した「異端の罪状リスト」", jp, 21, 14, 510), fill=(255, 255, 255, 255))

        charges = [
            ("罪状①「入団儀式でキリストの十字架に3回唾を吐いた」", "キリスト教徒が最も嫌悪する背教行為を組織的に行ったと告発"),
            ("罪状②「謎の偶像『バフォメット』に祈りを捧げた」", "髭を生やした生首や猫の偶像を崇拝していたという証言を強要"),
            ("残酷な拷問：パリだけで「36人の騎士」が拷問死", "滑車で関節を外す・足の裏を火で炙る拷問でモレー総長も一時自白"),
        ]
        yc = 172
        for ch_h, ch_d in charges:
            draw.text((68, yc), ch_h, font=_fit_font(draw, ch_h, jp, 19, 13, 500), fill=(255, 215, 115, 255))
            draw.text((68, yc + 32), ch_d, font=_fit_font(draw, ch_d, jp, 17, 12, 500), fill=(235, 238, 245, 255))
            yc += 108

        if step == 1:
            # Step 1: Chained knight under interrogation on the right
            _draw_templar_knight(draw, 910, hy, scale=1.08, chained=True)
            _draw_callout(draw, jp, (910, hy - 180), (675, 165), "拷問で嘘の自白を強いられた騎士たち", (255, 195, 145, 255), 22)
        else:
            # Step 2: Linguistic Equation & 19th-Century Eliphas Levi Myth Debunked!
            draw_rounded_box(draw, (625, 102, 1232, 520), radius=14, fill=(20, 32, 46, 242), outline=(85, 195, 255, 235), width=3)
            draw_rounded_box(draw, (625, 102, 1232, 150), radius=12, fill=(35, 110, 175, 245))
            draw.text((648, 112), "◎ 現代言語学・歴史学が暴いた「バフォメット」の正体", font=_fit_font(draw, "◎ 現代言語学・歴史学が暴いた「バフォメット」の正体", jp, 21, 14, 575), fill=(255, 255, 255, 255))

            # Big Linguistic Equation Box
            draw_rounded_box(draw, (648, 170, 1208, 282), radius=12, fill=(14, 22, 32, 245), outline=(255, 215, 80, 240), width=2)
            _draw_stroked_txt(draw, (670, 184), "古仏語 Baphomet ＝ Mahomet（ムハンマド）の訛り！", _fit_font(draw, "古仏語 Baphomet ＝ Mahomet（ムハンマド）の訛り！", jp, 22, 14, 520), (255, 230, 110, 255), sw=3)
            draw.text((670, 232), "中世の南仏・十字軍記録ではイスラム預言者を「バフォメット」と表記", font=_fit_font(draw, "中世の南仏・十字軍記録ではイスラム預言者を「バフォメット」と表記", jp, 17, 12, 520), fill=(230, 240, 250, 255))

            # 1856 Eliphas Levi Goat Idol Debunk Box
            draw_rounded_box(draw, (648, 302, 1208, 404), radius=12, fill=(38, 24, 32, 240), outline=(225, 95, 95, 220), width=2)
            draw.text((670, 316), "【重要】有名な「山羊の頭の悪魔像」は550年後の創作！", font=_fit_font(draw, "【重要】有名な「山羊の頭の悪魔像」は550年後の創作！", jp, 20, 14, 520), fill=(255, 165, 165, 255))
            draw.text((670, 354), "1856年にフランスの魔術師エリファス・レヴィが描いたイラストに過ぎない", font=_fit_font(draw, "1856年にフランスの魔術師エリファス・レヴィが描いたイラストに過ぎない", jp, 17, 12, 520), fill=(235, 238, 245, 255))

            # Zero confessions outside France
            draw_rounded_box(draw, (648, 422, 1208, 502), radius=12, fill=(20, 44, 36, 240), outline=(75, 215, 145, 220), width=2)
            draw.text((670, 436), "◎ 決定的な証拠：拷問を使わなかったイギリス・スペイン等では", font=_fit_font(draw, "◎ 決定的な証拠：拷問を使わなかったイギリス・スペイン等では", jp, 18, 13, 520), fill=(145, 250, 195, 255))
            draw.text((670, 466), "   バフォメット像は1つも見つからず「全員が無罪」とされた！", font=_fit_font(draw, "   バフォメット像は1つも見つからず「全員が無罪」とされた！", jp, 18, 13, 520), fill=(255, 255, 255, 255))

        img.save(out_png)
        return

    # =========================================================================
    # DIAGRAM 07: The 2001 Chinon Parchment Discovery (3 Wax Seals + Absolution vs Dissolution)
    # =========================================================================
    if diagram_id == "diagram_07":
        img, draw, jp = _base_board(
            "2001年の大発見 ⑦",
            "バチカン秘密文書館から発見された『シノン羊皮紙（1308年）』の衝撃",
        )
        # Left: Giant Chinon Parchment Scroll with 3 Cardinal Wax Seals
        _draw_parchment_scroll(
            draw,
            (52, 100, 625, 524),
            "『シノン羊皮紙』（1308年8月17〜20日）",
            [
                "● 2001年9月：バルバラ・フラーレ博士が",
                "   バチカン秘密文書館の誤分類箱から原本を発見！",
                "● 教皇クレメンス5世が派遣した3人の枢機卿が",
                "   シノン城でモレー総長らを拷問なしで直接尋問",
                "● 結論：「異端（悪魔崇拝）の罪は存在しない」",
                "● 教皇が総長らに【正式な赦免（無罪）】を授与！",
            ],
            jp,
            seals=3,
            stamp_text="教皇公式認定：異端は無罪",
        )

        if step == 1:
            # Step 1: Spotlight on the 2001 Vatican Discovery & Pope's Secret Absolution
            _draw_templar_knight(draw, 930, hy, scale=1.05, chained=False)
            _draw_callout(draw, jp, (930, hy - 180), (685, 165), "700年越しに無実が証明されたモレー総長", (255, 235, 155, 255), 21)
            draw_rounded_box(draw, (675, 240, 1215, 345), radius=14, fill=(22, 38, 34, 240), outline=(80, 220, 155, 230), width=2)
            draw.text((698, 260), "2007年にバチカンが公式出版し、", font=_fit_font(draw, "2007年にバチカンが公式出版し、", jp, 21, 15, 495), fill=(255, 255, 255, 255))
            draw.text((698, 298), "ローマ教皇自身が騎士団を赦免していた事実が確定", font=_fit_font(draw, "ローマ教皇自身が騎士団を赦免していた事実が確定", jp, 20, 14, 495), fill=(145, 250, 195, 255))
        else:
            # Step 2: Answer "Then why were they dissolved in 1312?" & Where did the money go?
            draw_rounded_box(draw, (660, 100, 1230, 524), radius=14, fill=(22, 28, 42, 242), outline=(225, 175, 65, 235), width=3)
            _draw_stroked_txt(draw, (684, 120), "なぜ「無罪」なのに1312年に解散させられたのか？", _fit_font(draw, "なぜ「無罪」なのに1312年に解散させられたのか？", jp, 22, 15, 525), (255, 225, 115, 255), sw=3)

            reasons = [
                ("① フィリップ4世が軍隊でヴィエンヌ公会議を包囲・脅迫", "「騎士団を解散させなければ、前教皇を異端として墓から暴く」と教皇を脅迫"),
                ("② 「有罪判決」ではなく「教皇の行政権」による解散", "大勅書『ウォクス・イン・エクスケルソ』は裁判の有罪ではなく行政処分として解散"),
                ("③ 騎士団の莫大な資産は「聖ヨハネ騎士団」へ移管！", "教皇は最後の抵抗として資産を別の騎士団へ移し、仏王の独占を阻止した"),
            ]
            yr = 180
            for r_h, r_d in reasons:
                draw_rounded_box(draw, (682, yr, 1208, yr + 96), radius=10, fill=(32, 38, 56, 245), outline=(110, 165, 235, 190), width=2)
                draw.text((700, yr + 12), r_h, font=_fit_font(draw, r_h, jp, 19, 13, 490), fill=(135, 225, 255, 255))
                draw.text((700, yr + 48), r_d, font=_fit_font(draw, r_d, jp, 17, 12, 490), fill=(238, 242, 248, 255))
                yr += 110

        img.save(out_png)
        return

    # =========================================================================
    # DIAGRAM 08: Curse of the Accursed Kings Domino Timeline -> 100 Years' War
    # =========================================================================
    if diagram_id == "diagram_08":
        img, draw, jp = _base_board(
            "歴史の皮肉 ⑧",
            "1314年モレー総長の火刑と「呪われた王たち」連鎖急死・カペー朝断絶年表",
        )
        # Top Timeline Nodes: 1314.3.18 -> +33 days -> +8 months -> 3 Sons Dead in 14 Years
        events = [
            (56, 316, "1314年3月18日", "モレー総長が火刑台で予言", "「1年以内に神の法廷へ召喚する！」", (215, 95, 35, 245)),
            (356, 616, "わずか 33日後（4月20日）", "教皇クレメンス5世 急死", "激しい腹痛と血便で苦しみ死去", (195, 42, 42, 245)),
            (656, 916, "8ヶ月後（11月29日）", "仏王フィリップ4世 急死", "46歳で狩りの最中に脳卒中で死亡", (195, 42, 42, 245)),
            (956, 1224, "その後14年間（〜1328年）", "息子3人が全員若くして急死", "ルイ10世・フィリップ5世・シャルル4世", (145, 32, 165, 245)),
        ]
        for x0, x1, e_date, e_title, e_sub, e_col in events:
            draw_rounded_box(draw, (x0, 98, x1, 265), radius=14, fill=(24, 26, 38, 245), outline=e_col, width=3)
            draw_rounded_box(draw, (x0, 98, x1, 140), radius=12, fill=e_col)
            draw.text((x0 + 14, 107), e_date, font=_fit_font(draw, e_date, jp, 19, 13, (x1 - x0) - 24), fill=(255, 255, 255, 255))
            draw.text((x0 + 14, 158), e_title, font=_fit_font(draw, e_title, jp, 20, 13, (x1 - x0) - 24), fill=(255, 230, 125, 255))
            draw.text((x0 + 14, 206), e_sub, font=_fit_font(draw, e_sub, jp, 16, 12, (x1 - x0) - 24), fill=(235, 240, 248, 255))

        for ax in [321, 621, 921]:
            _draw_stroked_txt(draw, (ax, 162), "⇒", ImageFont.truetype(jp, 28), (255, 215, 80, 255), sw=3)

        if step == 1:
            # Step 1: Silhouettes of the 3 sons / fallen crowns on the horizon
            for idx_s, (sx, s_lbl) in enumerate([(320, "長男ルイ10世（26歳没）"), (640, "次男フィリップ5世（28歳没）"), (960, "三男シャルル4世（33歳没）")]):
                _draw_pattern_a_silhouette_1280(draw, sx, hy, "right_power", (215, 55, 55, 255))
                _draw_callout(draw, jp, (sx, hy - 175), (sx - 125, 300), s_lbl, (255, 215, 145, 255), 19)
        else:
            # Step 2: Dynasty Extinction -> 100 Years' War Consequence Banner!
            draw_rounded_box(draw, (56, 305, 1224, 522), radius=16, fill=(42, 18, 24, 245), outline=(255, 195, 70, 240), width=3)
            _draw_stroked_txt(
                draw,
                (88, 326),
                "【歴史の結末】300年続いた「カペー朝直系」がわずか14年で完全断絶！",
                _fit_font(draw, "【歴史の結末】300年続いた「カペー朝直系」がわずか14年で完全断絶！", jp, 26, 16, 1100),
                (255, 230, 110, 255),
                sw=4,
            )
            draw.text(
                (88, 386),
                "■ 王位継承権をめぐり、フィリップ4世の娘イザベラの子（英国王エドワード3世）がフランス王位を主張",
                font=_fit_font(draw, "■ 王位継承権をめぐり、フィリップ4世の娘イザベラの子（英国王エドワード3世）がフランス王位を主張", jp, 20, 14, 1100),
                fill=(245, 248, 252, 255),
            )
            draw.text(
                (88, 434),
                "■ 目先の借金を踏み倒すためにテンプル騎士団を滅ぼした代償として、フランスは「英仏百年戦争」の地獄へ転落した",
                font=_fit_font(draw, "■ 目先の借金を踏み倒すためにテンプル騎士団を滅ぼした代償として、フランスは「英仏百年戦争」の地獄へ転落した", jp, 20, 14, 1100),
                fill=(255, 165, 165, 255),
            )

        img.save(out_png)
        return


TEMPLAR_QUESTION_SPECS: Dict[str, Dict[str, object]] = {
    "q_01": {
        "scene": "scene_01",
        "sec": 2.0,
        "badge": "歴史の疑問 Q1 ／ 聖戦の英雄か金融帝国か",
        "line1": "なぜ個人の財産を禁じられた「清貧の修道士」が、",
        "line2": "国家を超える「世界初の巨大銀行」になったのか？",
        "hint": "【次の図解】9人の貧しい騎士からヨーロッパ9,000箇所の要塞・金融ネットワークへの変貌",
    },
    "q_02": {
        "scene": "scene_03",
        "sec": 2.0,
        "badge": "歴史の疑問 Q2 ／ 十字軍の本当の動機",
        "line1": "十字軍は本当に「純粋な信仰心」だけで",
        "line2": "3000キロ先のエルサレムを目指したのか？",
        "hint": "【次の図解】「すべての罪の赦し（贖宥）」と、長子相続であぶれた騎士たちの領土・利権争い",
    },
    "q_03": {
        "scene": "scene_08",
        "sec": 2.0,
        "badge": "歴史の疑問 Q3 ／ 中世の錬金術システム",
        "line1": "キリスト教で「利子（高利貸し）」が禁じられていた時代に、",
        "line2": "どうやって暗号小切手と巨額融資で儲けたのか？",
        "hint": "【次の図解】1139年教皇大勅書の「非課税特権」と、世界初のトラベラーズチェックの仕組み",
    },
    "q_04": {
        "scene": "scene_11",
        "sec": 2.0,
        "badge": "歴史の疑問 Q4 ／ 史上最悪の十字軍暴走",
        "line1": "なぜイスラムと戦うはずの「第4回十字軍」は、",
        "line2": "同じキリスト教の首都コンスタンティノープルを略奪したのか？",
        "hint": "【次の図解】ヴェネツィアへの船代借金「8万5000マルク」が引き起こした前代未聞の略奪劇",
    },
    "q_05": {
        "scene": "scene_14",
        "sec": 2.0,
        "badge": "歴史の疑問 Q5 ／ 13日の金曜日の真犯人",
        "line1": "1307年10月13日（金曜日）の一斉逮捕劇──",
        "line2": "フランス王フィリップ4世の「本当の目的」とは？",
        "hint": "【次の図解】通貨偽造でも破産を免れなかった国王による「借金踏み倒し＆資産強奪計画」",
    },
    "q_06": {
        "scene": "scene_18",
        "sec": 2.0,
        "badge": "歴史の疑問 Q6 ／ 悪魔バフォメットの正体",
        "line1": "騎士団が崇拝したとされた「悪魔バフォメット」とは、",
        "line2": "実は拷問と「ある言葉の誤記」から生まれた冤罪だった？",
        "hint": "【次の図解】古フランス語の「Mahomet（ムハンマド）」の訛りと、19世紀に描かれた山羊頭イラスト",
    },
    "q_07": {
        "scene": "scene_20",
        "sec": 2.0,
        "badge": "歴史の疑問 Q7 ／ 2001年バチカン秘密文書館の発見",
        "line1": "700年間眠っていた極秘文書『シノン羊皮紙』が暴いた",
        "line2": "ローマ教皇の「隠された無罪判決」とは？",
        "hint": "【次の図解】2001年バルバラ・フラーレ博士が発見した「教皇によるテンプル騎士団赦免」の原本",
    },
    "q_08": {
        "scene": "scene_23",
        "sec": 2.0,
        "badge": "歴史の疑問 Q8 ／ 炎の中の呪いと王朝の滅亡",
        "line1": "火あぶりにされた最後の総長ジャック・ド・モレーの「呪い」で、",
        "line2": "なぜ教皇とフランス王家は次々と急死したのか？",
        "hint": "【次の図解】処刑33日後の教皇死去・8ヶ月後の国王急死・カペー朝断絶と百年戦争への連鎖",
    },
}


def render_templar_question_card(q_id: str, out_png: Path, flow_dir: Path) -> None:
    render_pattern_a_question_card(TEMPLAR_QUESTION_SPECS[q_id], out_png)


def render_all_templar_diagrams(flow_dir: Path, diag_dir: Path) -> None:
    diag_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 9):
        did = f"diagram_{i:02d}"
        # Render both progressive steps (`_b1.png` for Beat 1, `_b2.png` and `.png` for Beat 2)
        render_templar_diagram_board(did, diag_dir / f"{did}_b1.png", step=1)
        render_templar_diagram_board(did, diag_dir / f"{did}_b2.png", step=2)
        render_templar_diagram_board(did, diag_dir / f"{did}.png", step=2)
        qid = f"q_{i:02d}"
        render_templar_question_card(qid, diag_dir / f"{qid}.png", flow_dir)


if __name__ == "__main__":
    fdir = Path("/Users/takahashitomohiro/Desktop/Youtube PJ/assets/flow_history_templars")
    ddir = fdir / "diagrams"
    render_all_templar_diagrams(fdir, ddir)
    print("Rendered all 8 bespoke multi-step Knights Templar diagrams (16 progressive boards) and 8 Question cards!")
