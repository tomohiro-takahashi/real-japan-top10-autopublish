#!/usr/bin/env python3
"""
build_world_history_shorts.py

Generates 5 high-impact vertical 9:16 Shorts (1080x1920, ~45-58s each) from the French Revolution Complete Edition.
Each Short features:
1. Top persistent Mystery Hook Header (crimson badge + 2-line giant question hook)
2. Center 9:16 AI Live-Action Cinema Viewport with multi-camera cuts + pop-up "Evidence / 諸説 Data Card" on the reveal beat
3. Bottom giant high-contrast Japanese subtitles + funnel CTA bar pointing to the 16-minute Complete Edition
4. Audible Baroque harpsichord + cello BGM + dramatic sound effects (`question_sting`, `blade_glint`, `low_timpani`, `page_turn`)
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from build_japan_ranking import BASE_DIR, OUTPUT_DIR, draw_rounded_box, find_cjk_font, get_duration
from build_world_history_cinema import (
    FLOW_DIR,
    build_narration_beat_wav,
    fit_font_w,
    generate_cinematic_history_bgm,
    resolve_scene_mp4,
)

SW, SH = 1080, 1920
FPS = 25
SHORTS_OUT_DIR = OUTPUT_DIR / "history_shorts_fr_rev"


# ---------------------------------------------------------------------------
# 5 High-Impact Japanese World History Shorts (French Revolution Series)
# ---------------------------------------------------------------------------

HISTORY_SHORTS_SPECS: List[Dict[str, Any]] = [
    {
        "short_id": "short_fr_01",
        "title": "「パンがなければお菓子を食べればいい」実は王妃は言っていなかった！？フランス革命・国家破産の真犯人 #Shorts #歴史 #フランス革命",
        "top_badge": "【AI実写】教科書のウソ？世界史ミステリー ①",
        "hook_line1": "「お菓子を食べればいい」",
        "hook_line2": "実は王妃は言っていなかった！？",
        "beats": [
            {
                "scene_id": "scene_01",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "se": "question_sting",
                "narration": "『パンがなければお菓子を食べればいいじゃない』。マリー・アントワネットのこの有名なセリフ、実は彼女が言った記録は歴史上ひとつも存在しないことをご存知でしょうか？",
                "sub_top": "歴史上でもっとも有名な「冤罪セリフ」",
                "sub_main": "実は王妃がこの言葉を言った記録は\n歴史上ひとつも存在しない",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_11",
                "cam": "wide",
                "clip_window": (0.0, 5.5),
                "se": "page_turn",
                "narration": "この言葉の本当の出典は、思想家ルソーが1765年頃に書いた自伝『告白』の一節です。なんとその時、マリー・アントワネットはまだオーストリアにいる10歳の少女でした。",
                "sub_top": "本当の出典はルソーの著書『告白』",
                "sub_main": "ルソーがこの一節を書いた時、\n彼女はオーストリアにいる10歳の少女だった",
                "evidence_card": {
                    "title": "【証拠データ①】『お菓子発言』の真相",
                    "row1": "× 通説：王妃が飢えた市民を嘲笑して発言",
                    "row2": "◎ 真実：ルソー『告白』（1765年執筆）の引用",
                    "note": "当時アントワネットはまだ10歳（結婚前）で物理的に不可能",
                },
            },
            {
                "scene_id": "scene_12",
                "cam": "close",
                "clip_window": (0.0, 6.0),
                "se": "low_timpani",
                "narration": "さらに『王妃の浪費でフランスが破産した』というのも誤解です。1788年の国家予算を見ると、ヴェルサイユ宮廷費は全体のわずか6パーセントに過ぎませんでした。",
                "sub_top": "1788年 フランス国家予算の真実",
                "sub_main": "王妃の浪費を含む宮廷費は\n国家予算全体の「わずか6%」だった",
                "evidence_card": {
                    "title": "【証拠データ②】1788年 国家歳出の内訳",
                    "row1": "・過去の戦争借金の利払い：50.5%（真犯人）",
                    "row2": "・陸海軍の軍事費：26.0% ／ 宮廷費：約6.0%",
                    "note": "アメリカ独立戦争への13億リーヴル参戦が財政にとどめを刺した",
                },
            },
            {
                "scene_id": "scene_03",
                "cam": "wide",
                "clip_window": (0.0, 5.5),
                "se": "blade_glint",
                "narration": "国家破産の本当の犯人は、アメリカ独立戦争につぎ込んだ13億リーヴルの借金でした。しかし目に見える贅沢をしていた王妃が、国民のすべての怒りのスケープゴートにされたのです。",
                "sub_top": "真犯人は「13億リーヴルの戦争借金」",
                "sub_main": "目に見える贅沢をしていた王妃が\nすべての怒りのスケープゴートにされた",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_fr_02",
        "title": "バスティーユ牢獄を襲撃したら囚人が「たった7人」しかいなかった真相とは？ #Shorts #世界史 #フランス革命",
        "top_badge": "【AI実写】教科書のウソ？世界史ミステリー ②",
        "hook_line1": "バスティーユ牢獄を襲ったら",
        "hook_line2": "囚人が「7人」しかいなかった！？",
        "beats": [
            {
                "scene_id": "scene_05",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "cannon_boom",
                "narration": "1789年7月14日、フランス革命の始まりとなったバスティーユ牢獄襲撃。数万人の市民が『圧政で苦しむ無実の政治犯を解放しろ！』と巨大な要塞へ突撃しました。",
                "sub_top": "1789年7月14日 バスティーユ牢獄襲撃",
                "sub_main": "「無実の政治犯を解放しろ！」と\n数万人のパリ市民が要塞へ突撃した",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_15",
                "cam": "close",
                "clip_window": (0.0, 6.0),
                "se": "question_sting",
                "narration": "しかし、激しい銃撃戦の末に地下牢の扉をこじ開けた市民たちは唖然とします。なんとあの巨大な牢獄に収容されていた囚人は、全部でたったの7人しかいなかったのです。",
                "sub_top": "地下牢の扉を開けた市民が見た光景",
                "sub_main": "巨大な要塞にいた囚人は\nなんと「たったの7人」だけだった",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_15",
                "cam": "wide",
                "clip_window": (3.0, 9.5),
                "se": "page_turn",
                "narration": "しかもその7人の内訳は、小切手の偽造犯が4人、精神疾患の人物が2人、そして家族の依頼で贅沢な部屋に軟禁されていた放蕩貴族が1人。政治犯はひとりもいませんでした。",
                "sub_top": "バスティーユ「7人の囚人」の実際の内訳",
                "sub_main": "偽造犯4人・精神疾患2人・放蕩貴族1人\n政治犯はひとりもいなかった",
                "evidence_card": {
                    "title": "【証拠データ】バスティーユ「7人の囚人」内訳",
                    "row1": "・小切手等の偽造犯：4名 ／ 精神疾患：2名",
                    "row2": "・家族の依頼で軟禁された放蕩貴族：1名",
                    "note": "思想犯・政治犯は0人（維持費が高すぎ閉鎖寸前だった）",
                },
            },
            {
                "scene_id": "scene_05",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "se": "low_timpani",
                "narration": "ではなぜ市民はバスティーユを襲ったのか？本当の目的は囚人の解放ではなく、要塞の地下に保管されていた13.6トンもの大量の火薬を奪い、国王軍と戦うことだったのです。",
                "sub_top": "市民の真の狙いは「13.6トンの火薬」",
                "sub_main": "囚人解放ではなく、国王軍と戦うための\n「13.6トンの火薬」を奪うのが真の目的だった",
                "evidence_card": {
                    "title": "【歴史の真実】なぜバスティーユを襲ったのか？",
                    "row1": "× 通説：圧政に苦しむ政治犯を救出するため",
                    "row2": "◎ 真実：地下の「火薬13.6トン」を奪取するため",
                    "note": "前日に奪った3万丁のマスケット銃に詰める火薬が必要だった",
                },
            },
        ],
    },
    {
        "short_id": "short_fr_03",
        "title": "700部屋のヴェルサイユ宮殿に「トイレがほぼ無かった」衝撃の日常とは？ #Shorts #世界史 #フランス革命",
        "top_badge": "【AI実写】もしも18世紀パリに生まれたら ③",
        "hook_line1": "700部屋のヴェルサイユ宮殿に",
        "hook_line2": "「トイレがほぼ無かった」衝撃の真実",
        "beats": [
            {
                "scene_id": "scene_03",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "黄金のシャンデリアが輝くヴェルサイユ宮殿。しかしもしあなたが18世紀の宮殿に足を踏み入れたら、まずその凄まじい悪臭に衝撃を受けるはずです。",
                "sub_top": "華やかなヴェルサイユ宮殿の「裏の顔」",
                "sub_main": "黄金の宮殿に足を踏み入れると\nまず凄まじい「悪臭」に衝撃を受ける",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_10",
                "cam": "close",
                "clip_window": (0.0, 5.5),
                "se": "page_turn",
                "narration": "当時、宮殿には貴族や召使いなど毎日1万人近くが出入りしていましたが、700以上ある部屋に水洗トイレはほぼ存在せず、王族以外は廊下の隅のおまるを使っていました。",
                "sub_top": "700部屋に1万人が密集する宮殿",
                "sub_main": "トイレはほぼ存在せず、廊下の隅や\n中庭に汚物が捨てられていた",
                "evidence_card": {
                    "title": "【当時の衛生実態】ヴェルサイユ宮殿の裏側",
                    "row1": "・700部屋に常時約1万人が滞在・出入り",
                    "row2": "・入浴は「毛穴から病気が入る」と避けられた",
                    "note": "体臭と汚物の臭いを消すため「強烈な香水と白粉」が発達した",
                },
            },
            {
                "scene_id": "scene_09",
                "cam": "wide",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "一方、パリの庶民の暮らしはさらに過酷でした。水道がないため早朝5時に凍てつくセーヌ川の濁った水をバケツで汲み、収穫の65パーセントを税金と領主へ奪われていました。",
                "sub_top": "早朝5時・パリ市民の過酷なルーティン",
                "sub_main": "凍るセーヌ川の濁った水を汲み、\n収穫の65%を税金と領主に奪われていた",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_04",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "さらに1788年の異常気象でパン1個の値段が日給の9割に暴騰。『このままでは子供が餓死する』という極限の飢えが、1000年続いた王政を吹き飛ばす導火線となったのです。",
                "sub_top": "パン1個＝労働者の日給の9割へ暴騰",
                "sub_main": "「子供が餓死する」という極限の飢えが\n1000年続いた王政を吹き飛ばした",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_fr_04",
        "title": "なぜ国境まで「あと40km」で国王一家の深夜逃亡はバレたのか？ヴァレンヌ事件3つの諸説 #Shorts #歴史 #フランス革命",
        "top_badge": "【AI実写】世界史最大の逃亡劇ミステリー ④",
        "hook_line1": "国境まで「あと40km」で",
        "hook_line2": "なぜ国王一家の逃亡はバレたのか？",
        "beats": [
            {
                "scene_id": "scene_17",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "1791年6月20日の深夜、パリに軟禁されていた国王ルイ16世とマリー・アントワネットは、家庭教師と召使いに変装して宮殿を脱出し、国境の要塞へ向けて240キロを疾走しました。",
                "sub_top": "1791年6月「ヴァレンヌ逃亡事件」",
                "sub_main": "召使いに変装した国王一家が\n深夜のパリを脱出し240kmを疾走した",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_17",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "se": "low_timpani",
                "narration": "しかし目的地まであとわずか40キロの宿場町ヴァレンヌで、宿場長ドルーエに紙幣の肖像画と顔を見比べられ、その場で逮捕されてしまいます。なぜ寸前で失敗したのでしょうか？",
                "sub_top": "目的地まで「あと40km」で逮捕",
                "sub_main": "ランタンの光の下で紙幣の肖像画と\n顔を見比べられ、その場で逮捕された",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_16",
                "cam": "wide",
                "clip_window": (0.0, 5.5),
                "se": "page_turn",
                "narration": "第1の説は『馬車の遅れ説』。小型馬車2台で別々に逃げる案を王が拒み、銀食器やワインまで積んだ6頭立ての豪華馬車ベルリン号を使ったため、予定より3時間以上遅れました。",
                "sub_top": "【諸説①】豪華馬車ベルリン号の遅れ説",
                "sub_main": "銀食器まで積んだ6頭立て大型馬車を使い\n予定より3時間以上遅れて護衛と合流失敗",
                "evidence_card": {
                    "title": "【ヴァレンヌ逃亡】なぜあと40kmで失敗したのか？",
                    "row1": "説①：6頭立て大型馬車に固執し3時間以上遅延",
                    "row2": "説②：発行直後のアッシニア紙幣の顔と一致",
                    "note": "説③：王の権威を潰すため急進派がわざと泳がせた説",
                },
            },
            {
                "scene_id": "scene_18",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "この逃亡未遂によって『王は外国軍と組んで国民を攻撃するつもりだ』と判明し、信頼は完全に崩壊。ルイ16世と王妃は自ら断頭台への道を決定づけてしまったのです。",
                "sub_top": "逃亡失敗が招いた王政の終焉",
                "sub_main": "「国民を見捨てた裏切り者」として\n国王夫妻の処刑を決定づける事件となった",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_fr_05",
        "title": "実はルイ16世自身が改良を助言していた！？ギロチン誕生の皮肉と恐怖政治の末路 #Shorts #世界史 #フランス革命",
        "top_badge": "【AI実写】教科書が教えない歴史の皮肉 ⑤",
        "hook_line1": "ルイ16世自身が改良を助言！？",
        "hook_line2": "「ギロチン」に隠された歴史の皮肉",
        "beats": [
            {
                "scene_id": "scene_18",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "フランス革命の恐怖の象徴となった断頭台、ギロチン。しかしこの装置が、もともとは『人道と平等』のために開発されたものだったことをご存知でしょうか？",
                "sub_top": "恐怖の象徴「ギロチン」誕生の意外な理由",
                "sub_main": "実は残酷な見せしめではなく\n「人道と平等」のために開発された装置だった",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_12",
                "cam": "close",
                "clip_window": (3.5, 9.5),
                "se": "page_turn",
                "narration": "さらに歴史の諸説では、錠前作りが趣味で手先が器用だった国王ルイ16世自身が設計図を見て、『三日月形の刃より、斜めの直線刃にした方が確実に切れる』と改良を助言したと言われています。",
                "sub_top": "【歴史の皮肉】斜めの刃を提案したのは誰か？",
                "sub_main": "手先が器用だったルイ16世自身が\n「斜めの直線刃」への改良を助言したという説",
                "evidence_card": {
                    "title": "【ギロチンの皮肉】3つの歴史的真実",
                    "row1": "① 身分を問わず一瞬で苦痛なく処刑する「平等の装置」",
                    "row2": "② ルイ16世自身が「斜め刃」への改良を助言した説",
                    "note": "③ 10ヶ月後、王自身がその改良された刃で処刑された",
                },
            },
            {
                "scene_id": "scene_07",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "low_timpani",
                "narration": "そのわずか10ヶ月後、ルイ16世は自らが改良したギロチンで処刑されました。さらに独裁者ロベスピエールは1年余りで1万7000人以上を処刑し、かつての盟友ダントンすら断頭台へ送ります。",
                "sub_top": "1万7,000人を呑み込んだ「恐怖政治」",
                "sub_main": "王だけでなく、革命のリーダーたちも\n味方同士で次々とギロチンへ送り合った",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_19",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "そして最後はロベスピエール自身も同じギロチンで処刑されました。通説と諸説をすべて網羅した全16分の完全保存版は、画面下の関連動画リンクから今すぐご覧いただけます。",
                "sub_top": "独裁者ロベスピエールも同じ断頭台へ",
                "sub_main": "全16分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
]


def render_short_overlay_9x16(
    top_badge: str,
    hook_line1: str,
    hook_line2: str,
    sub_top: str,
    sub_main: str,
    evidence_card: Optional[Dict[str, str]],
    out_png: Path,
) -> None:
    """Render a 1080x1920 transparent overlay with top persistent hook, optional evidence card, and bottom subtitle."""
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    jp = find_cjk_font()

    # 1. Top & Bottom dark cinema gradients (drawn on separate layer first)
    grad = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad, "RGBA")
    for y in range(0, 420):
        if y < 310:
            a = 242
        else:
            a = int(242 * (1.0 - (y - 310) / 110.0))
        gd.line([(0, y), (SW, y)], fill=(8, 10, 16, a))

    for y in range(1320, SH):
        if y < 1450:
            a = int(242 * ((y - 1320) / 130.0))
        else:
            a = 242
        gd.line([(0, y), (SW, y)], fill=(8, 10, 16, a))
    img.alpha_composite(grad)

    # 2. Top persistent Mystery Hook Header (y=75..330)
    hdr = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hdr, "RGBA")

    # Gold border lines framing the 9:16 video viewport
    hd.line([(0, 338), (SW, 338)], fill=(218, 178, 72, 235), width=4)
    hd.line([(0, 1395), (SW, 1395)], fill=(218, 178, 72, 235), width=4)

    # Top crimson pill
    f_badge = fit_font_w(hd, top_badge, jp, 30, 20, SW - 120)
    bb_b = hd.textbbox((0, 0), top_badge, font=f_badge)
    bw = bb_b[2] - bb_b[0]
    draw_rounded_box(
        hd,
        ((SW - bw) // 2 - 28, 76, (SW + bw) // 2 + 28, 134),
        radius=26,
        fill=(180, 18, 24, 248),
        outline=(255, 220, 100, 255),
        width=3,
    )
    hd.text(((SW - bw) // 2, 88), top_badge, font=f_badge, fill=(255, 255, 255, 255))

    # Hook Line 1 (White with black stroke)
    f_h1 = fit_font_w(hd, hook_line1, jp, 54, 34, SW - 64)
    bb1 = hd.textbbox((0, 0), hook_line1, font=f_h1)
    w1 = bb1[2] - bb1[0]
    hd.text(
        ((SW - w1) // 2, 150),
        hook_line1,
        font=f_h1,
        fill=(255, 255, 255, 255),
        stroke_width=8,
        stroke_fill=(0, 0, 0, 255),
    )

    # Hook Line 2 (Yellow with crimson/black stroke)
    f_h2 = fit_font_w(hd, hook_line2, jp, 62, 36, SW - 56)
    bb2 = hd.textbbox((0, 0), hook_line2, font=f_h2)
    w2 = bb2[2] - bb2[0]
    hd.text(
        ((SW - w2) // 2, 224),
        hook_line2,
        font=f_h2,
        fill=(255, 225, 72, 255),
        stroke_width=9,
        stroke_fill=(150, 12, 18, 255),
    )

    # 3. Hybrid Master Format: Thin Callout Pointer Line in Viewport OR Clean Visual Comparison Card
    if evidence_card:
        draw_rounded_box(
            hd,
            (42, 1110, SW - 42, 1368),
            radius=20,
            fill=(12, 16, 26, 232),
            outline=(235, 190, 75, 245),
            width=3,
        )
        f_et = fit_font_w(hd, evidence_card["title"], jp, 30, 20, SW - 130)
        hd.text((68, 1126), evidence_card["title"], font=f_et, fill=(255, 220, 95, 255), stroke_width=3, stroke_fill=(0, 0, 0, 240))
        hd.line([(66, 1170), (SW - 66, 1170)], fill=(235, 190, 75, 130), width=2)

        f_er1 = fit_font_w(hd, evidence_card["row1"], jp, 31, 19, SW - 136)
        f_er2 = fit_font_w(hd, evidence_card["row2"], jp, 31, 19, SW - 136)
        hd.text((68, 1192), evidence_card["row1"], font=f_er1, fill=(255, 150, 150, 255), stroke_width=3, stroke_fill=(0, 0, 0, 240))
        hd.text((68, 1262), evidence_card["row2"], font=f_er2, fill=(135, 245, 175, 255), stroke_width=3, stroke_fill=(0, 0, 0, 240))
    elif sub_top:
        # Clean thin `───` callout pointer line inside the 35mm viewport (no heavy box!)
        f_st = fit_font_w(hd, sub_top, jp, 28, 18, SW - 220)
        line_x0, line_x1, line_y = 64, 148, 412
        hd.line([(line_x0, line_y), (line_x1, line_y)], fill=(0, 0, 0, 210), width=7)
        hd.line([(line_x0, line_y), (line_x1, line_y)], fill=(255, 255, 255, 248), width=3)
        r_dot = 5
        hd.ellipse((line_x0 - r_dot, line_y - r_dot, line_x0 + r_dot, line_y + r_dot), fill=(255, 232, 120, 255), outline=(0, 0, 0, 230), width=2)
        hd.text(
            (line_x1 + 14, line_y - 16),
            sub_top,
            font=f_st,
            fill=(255, 255, 255, 255),
            stroke_width=5,
            stroke_fill=(0, 0, 0, 245),
        )

    # 4. Bottom Clean 2-Line White Subtitle Section (y=1445..1635)
    lines = sub_main.split("\n")
    y_sub = 1455
    for ln in lines[:2]:
        f_sm = fit_font_w(hd, ln, jp, 52, 28, SW - 64)
        bb_m = hd.textbbox((0, 0), ln, font=f_sm)
        wm = bb_m[2] - bb_m[0]
        hd.text(
            ((SW - wm) // 2, y_sub),
            ln,
            font=f_sm,
            fill=(255, 255, 255, 255),
            stroke_width=8,
            stroke_fill=(0, 0, 0, 255),
        )
        y_sub += 76

    # Related video funnel bar at bottom (above YouTube Shorts UI safe zone)
    cta_txt = "▲ 【完全保存版】本編は画面下の関連動画から ▲"
    f_cta = fit_font_w(hd, cta_txt, jp, 28, 18, SW - 120)
    bb_c = hd.textbbox((0, 0), cta_txt, font=f_cta)
    wc = bb_c[2] - bb_c[0]
    draw_rounded_box(
        hd,
        ((SW - wc) // 2 - 26, 1675, (SW + wc) // 2 + 26, 1732),
        radius=14,
        fill=(218, 172, 52, 245),
    )
    hd.text(((SW - wc) // 2, 1688), cta_txt, font=f_cta, fill=(14, 12, 8, 255))

    img.alpha_composite(hdr)
    img.save(out_png)


def render_short_beat_mp4(
    flow_mp4: Path,
    overlay_png: Path,
    beat_wav: Path,
    dur: float,
    cam_mode: str,
    clip_window: Tuple[float, float],
    out_mp4: Path,
) -> None:
    """Render a single 1080x1920 vertical Short beat segment."""
    t_start, t_end = clip_window
    slice_dur = max(2.0, t_end - t_start)
    pts_factor = max(1.0, dur / slice_dur)

    # Center viewport is 1080x1060 placed at y=338, with full 1080x1920 blurred background behind
    if cam_mode == "wide":
        fg_scale = "scale=1080:1060:force_original_aspect_ratio=increase,crop=1080:1060:(iw-1080)/2:(ih-1060)/2"
    else:
        fg_scale = "scale=1280:1250:force_original_aspect_ratio=increase,crop=1080:1060:(iw-1080)*0.48:(ih-1060)*0.35"

    vf = (
        f"[0:v]setpts={pts_factor:.4f}*(PTS-STARTPTS),fps={FPS},split=2[v1][v2];"
        f"[v1]scale={SW}:{SH}:force_original_aspect_ratio=increase,crop={SW}:{SH},boxblur=20:2,eq=brightness=-0.25[bg];"
        f"[v2]{fg_scale},eq=contrast=1.08:saturation=1.08[fg];"
        f"[bg][fg]overlay=0:338,format=rgba[base];"
        f"[1:v]format=rgba[ov];"
        f"[base][ov]overlay=0:0:format=auto,format=yuv420p[v]"
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


def build_all_shorts() -> List[Path]:
    SHORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    built_files: List[Path] = []

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        bgm_wav = work_dir / "bgm_short.wav"
        generate_cinematic_history_bgm(16.0, bgm_wav)

        for s_idx, spec in enumerate(HISTORY_SHORTS_SPECS, start=1):
            short_id = spec["short_id"]
            segs: List[Path] = []

            for b_idx, beat in enumerate(spec["beats"], start=1):
                uid = s_idx * 100 + b_idx
                beat_wav = work_dir / f"s_{uid}.wav"
                dur = build_narration_beat_wav(
                    text=beat["narration"],
                    se_kind=beat["se"],
                    out_wav=beat_wav,
                    work_dir=work_dir,
                    beat_idx=uid,
                )
                ov_png = work_dir / f"ov_{uid}.png"
                render_short_overlay_9x16(
                    top_badge=spec["top_badge"],
                    hook_line1=spec["hook_line1"],
                    hook_line2=spec["hook_line2"],
                    sub_top=beat["sub_top"],
                    sub_main=beat["sub_main"],
                    evidence_card=beat.get("evidence_card"),
                    out_png=ov_png,
                )
                seg_mp4 = work_dir / f"seg_{uid}.mp4"
                flow_mp4 = resolve_scene_mp4(beat["scene_id"])
                render_short_beat_mp4(
                    flow_mp4=flow_mp4,
                    overlay_png=ov_png,
                    beat_wav=beat_wav,
                    dur=dur,
                    cam_mode=beat["cam"],
                    clip_window=beat["clip_window"],
                    out_mp4=seg_mp4,
                )
                segs.append(seg_mp4)

            concat_txt = work_dir / f"concat_{short_id}.txt"
            concat_txt.write_text("\n".join(f"file '{p}'" for p in segs))
            raw_mp4 = work_dir / f"raw_{short_id}.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(raw_mp4)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            s_dur = get_duration(raw_mp4)
            out_mp4 = SHORTS_OUT_DIR / f"{short_id}.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(raw_mp4),
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(bgm_wav),
                    "-filter_complex",
                    f"[0:a]volume=1.55[va];[1:a]atrim=0:{s_dur+0.5:.2f},volume=0.45,afade=t=out:st={max(0.0, s_dur-2.0):.2f}:d=2.0[ba];[va][ba]amix=inputs=2:duration=first:dropout_transition=0[a]",
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
                    str(out_mp4),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[SHORT DONE] {out_mp4.name} ({s_dur:.1f}s) | {spec['hook_line1']} {spec['hook_line2']}")
            built_files.append(out_mp4)

    return built_files


if __name__ == "__main__":
    build_all_shorts()
