#!/usr/bin/env python3
"""
build_rome_fall_shorts.py

Generates 5 high-impact vertical 9:16 Shorts (1080x1920, ~45-58s each) from the Roman Empire Complete Edition.
Each Short features:
1. Top persistent Mystery Hook Header (crimson badge + 2-line giant question hook)
2. Center 9:16 AI Live-Action Cinema Viewport with multi-camera cuts + pop-up "Evidence / 諸説 Data Card" on the reveal beat
3. Bottom giant high-contrast Japanese subtitles + funnel CTA bar pointing to the 16-minute Complete Edition
4. Audible Baroque harpsichord + cello BGM + dramatic sound effects (`question_sting`, `blade_glint`, `low_timpani`, `page_turn`)
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from build_japan_ranking import OUTPUT_DIR, get_duration
from build_rome_fall_cinema import resolve_rome_scene_mp4
from build_world_history_cinema import build_narration_beat_wav, generate_cinematic_history_bgm
from build_world_history_shorts import render_short_beat_mp4, render_short_overlay_9x16

ROME_SHORTS_OUT_DIR = OUTPUT_DIR / "history_shorts_rome_fall"

ROME_SHORTS_SPECS: List[Dict[str, Any]] = [
    {
        "short_id": "short_rome_01",
        "title": "「ローマ帝国は鉛の水道管で鉛中毒になり滅びた」はウソ！？2014年の化学分析が暴いた真犯人 #Shorts #世界史 #ローマ帝国",
        "top_badge": "【AI実写】有名雑学のウソ？世界史ミステリー ①",
        "hook_line1": "「鉛の水道管でローマ滅亡」",
        "hook_line2": "実は科学的に否定されていた！？",
        "beats": [
            {
                "scene_id": "scene_03",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "『ローマ帝国は鉛の水道管を使って水道水を飲んでいたせいで、市民や貴族が鉛中毒になって滅びた』。テレビや雑学本で有名なこの説、実は最新の科学調査で否定されていることをご存知でしょうか？",
                "sub_top": "テレビや雑学本で定番の「鉛中毒で滅亡説」",
                "sub_main": "実は2014年の最新科学調査によって\n「水道水犯人説」は否定されている",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_04",
                "cam": "close",
                "clip_window": (0.0, 5.8),
                "se": "page_turn",
                "narration": "2014年、フランスの研究チームが古代ローマの水道管と堆積物を化学分析した結果、硬水に含まれる石灰がパイプの内側に分厚い皮膜を作り、鉛が水に溶け出すのを防いでいたことが判明しました。",
                "sub_top": "2014年 科学誌『PNAS』の化学分析結果",
                "sub_main": "硬水の「石灰（炭酸カルシウム）皮膜」が\nパイプ内壁を覆い、鉛の溶出を防いでいた",
                "evidence_card": {
                    "title": "【科学証拠①】2014年 デリルらの水道管分析",
                    "row1": "× 俗説：鉛の水道管から致死量の鉛が溶出した",
                    "row2": "◎ 真実：石灰の皮膜＋24時間かけ流しで水は無害",
                    "note": "水道水の鉛濃度は人体に中毒を起こすレベルではなかった",
                },
            },
            {
                "scene_id": "scene_05",
                "cam": "close",
                "clip_window": (0.0, 5.8),
                "se": "low_timpani",
                "narration": "ではなぜ貴族の骨から鉛が検出されたのか？本当の犯人は水道水ではなく、ワインを甘くするために鉛の鍋でブドウ果汁を煮詰めた高級甘味料『サパ』に含まれる酢酸鉛でした。",
                "sub_top": "貴族の骨から出た鉛の「本当の犯人」",
                "sub_main": "鉛の鍋でブドウ果汁を煮詰めた甘味料\n『サパ（酢酸鉛）』を貴族が好んで飲んでいた",
                "evidence_card": {
                    "title": "【科学証拠②】本当の鉛発生源は「サパ」",
                    "row1": "・ブドウ果汁を鉛鍋で煮詰めると甘い「酢酸鉛」が生成",
                    "row2": "・高級ワインの甘味料として富裕層が日常的に摂取",
                    "note": "ただし鉛使用のピークは1〜2世紀で、5世紀の滅亡原因ではない",
                },
            },
            {
                "scene_id": "scene_01",
                "cam": "close",
                "clip_window": (4.5, 9.8),
                "se": "blade_glint",
                "narration": "しかも鉛が最も使われたのはローマの絶頂期であり、5世紀の滅亡とは300年もズレています。ローマを本当に滅ぼした210の仮説と最新科学の結論は、画面下の関連動画から本編をご覧ください。",
                "sub_top": "ではローマ帝国を本当に滅ぼした「真犯人」は？",
                "sub_main": "210の仮説と最新科学で解き明かす本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_rome_02",
        "title": "銀貨の純度が「98%→2%」へ大暴落！？ローマ帝国が国家ぐるみの通貨偽造で自滅した真相 #Shorts #世界史 #ローマ帝国",
        "top_badge": "【AI実写】国家ぐるみの通貨偽造ミステリー ②",
        "hook_line1": "銀貨の純度が「98%→2%」へ！",
        "hook_line2": "ローマ帝国・通貨偽造の末路とは？",
        "beats": [
            {
                "scene_id": "scene_06",
                "cam": "close",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "世界最強の軍事力と経済を誇ったローマ帝国。しかしその心臓部だったデナリウス銀貨が、国家ぐるみの改ざんによって『ただの銅貨』に転落したことをご存知でしょうか？",
                "sub_top": "ローマ経済を支えた「デナリウス銀貨」",
                "sub_main": "初代皇帝アウグストゥスの時代には\n「銀純度98%」を誇る世界の基軸通貨だった",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_07",
                "cam": "close",
                "clip_window": (0.0, 5.8),
                "se": "page_turn",
                "narration": "銀山の枯渇と戦争で財源が足りなくなると、歴代の皇帝は銀貨を溶かして銅を混ぜ、枚数を水増ししました。その結果、西暦268年には銀の含有率がたったの2パーセントまで暴落したのです。",
                "sub_top": "銀含有率が「98% → 2%」へ大暴落",
                "sub_main": "中身はただの銅貨で、表面を薄く銀で\nコーティングしただけの「メッキ硬貨」に転落",
                "evidence_card": {
                    "title": "【出土硬貨データ】デナリウス銀貨の純度推移",
                    "row1": "・初代アウグストゥス帝：銀純度 98.0%（ほぼ純銀）",
                    "row2": "・268年 クラウディウス2世：銀純度 約1.5〜2.0%",
                    "note": "指で擦るとすぐ下の黒い銅が露出する粗悪なメッキ硬貨",
                },
            },
            {
                "scene_id": "scene_08",
                "cam": "wide",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "当然、商人は偽物の銀貨を見抜き、小麦の値段は約200倍に暴騰。革袋いっぱいの銅貨を積まなければパンひとつ買えない猛烈なハイパーインフレが帝国を襲いました。",
                "sub_top": "小麦価格「約200倍」のハイパーインフレ",
                "sub_main": "通貨の信用が完全に崩壊し、税金も\n「食糧や衣類の現物徴収」へと逆戻りした",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_09",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "301年には皇帝が『値上げした商人は死刑』という最高価格令を出しますが、市場から商品が消えて経済はさらに麻痺しました。全16分の完全保存版は画面下の関連動画からご覧いただけます。",
                "sub_top": "301年『最高価格令』の失敗と農奴制の誕生",
                "sub_main": "全16分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_rome_03",
        "title": "「市民の贅沢とキリスト教でローマが滅びた」説の致命的な矛盾とは？東ローマ1000年繁栄の謎 #Shorts #歴史 #ローマ帝国",
        "top_badge": "【AI実写】教科書の通説を覆す歴史検証 ③",
        "hook_line1": "「贅沢とキリスト教で滅亡説」に",
        "hook_line2": "隠された「致命的な矛盾」とは？",
        "beats": [
            {
                "scene_id": "scene_10",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "『ローマ帝国が滅びたのは、パンとサーカスに溺れた市民の堕落と、キリスト教の平和主義で兵士が弱くなったからだ』。イギリスの歴史家ギボンが唱えたこの有名な説には、実は致命的な矛盾があります。",
                "sub_top": "ギボン『ローマ帝国衰亡史』の有名な通説",
                "sub_main": "「パンとサーカスの堕落」と「キリスト教」で\nローマが滅びたという説の致命的な矛盾",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_11",
                "cam": "wide",
                "clip_window": (0.0, 5.8),
                "se": "page_turn",
                "narration": "もしキリスト教や都市の娯楽が滅亡の原因なら、西ローマよりもはるかにキリスト教化が進み、同じように戦車競技や大浴場に熱狂していた『東ローマ帝国』も一緒に滅びていなければおかしいのです。",
                "sub_top": "東ローマ（ビザンツ）帝国という最大の反証",
                "sub_main": "西よりキリスト教化が進んでいた東ローマは\nその後も「1000年間」繁栄し続けた",
                "evidence_card": {
                    "title": "【歴史の比較】なぜ東ローマは1000年続いたのか？",
                    "row1": "× 旧通説：キリスト教と市民の道徳退廃で滅亡",
                    "row2": "◎ 現代史学：東西の「防衛ラインと税収構造」の差",
                    "note": "東ローマは1453年までさらに約1,000年間も超大国として存続",
                },
            },
            {
                "scene_id": "scene_14",
                "cam": "close",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "東ローマが1000年生き残った本当の理由は、道徳ではなく『財布と地形』でした。東ローマは難攻不落の城壁で首都を守り、無傷のエジプトから莫大な税金と小麦を確保し続けていたのです。",
                "sub_top": "勝敗を分けたのは「道徳」ではなく「税収と地形」",
                "sub_main": "東ローマは豊かなエジプトの税収を守り抜き、\n西ローマは長大な国境と財源喪失で破産した",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_19",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "一方、西ローマは439年に最大の財布である北アフリカを奪われて破産しました。東西ローマの運命を分けた全16分の完全保存版は、画面下の関連動画から今すぐご覧いただけます。",
                "sub_top": "西ローマに止めを刺した「439年の悲劇」とは？",
                "sub_main": "全16分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_rome_04",
        "title": "西ローマ帝国に本当の致命傷を与えた「439年の穀倉喪失」と1100隻の大艦隊炎上とは？ #Shorts #世界史 #ローマ帝国",
        "top_badge": "【AI実写】西ローマ滅亡・真の決定打 ④",
        "hook_line1": "西ローマを本当に殺したのは",
        "hook_line2": "「1100隻の大艦隊炎上」だった！？",
        "beats": [
            {
                "scene_id": "scene_19",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "西ローマ帝国に本当の致命傷を与えた事件は何か？現代の歴史学者が最も重視するのは、410年のローマ略奪ではなく、439年にヴァンダル族によって『北アフリカのカルタゴ』を奪われた事件です。",
                "sub_top": "現代の歴史学者が重視する「西暦439年の致命傷」",
                "sub_main": "首都ローマの胃袋と最大の税収を支えていた\n「北アフリカ（現チュニジア）」の陥落",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_20",
                "cam": "wide",
                "clip_window": (0.0, 5.8),
                "se": "cannon_boom",
                "narration": "最大の税収源と小麦を失い破産寸前となったローマは468年、東西ローマの全財産である金6万4000ポンドを投じ、軍船1100隻・兵士10万人という史上最大の奪還艦隊をカルタゴへ派遣しました。",
                "sub_top": "西暦468年 軍船1,100隻・兵力10万人の大遠征",
                "sub_main": "北アフリカを取り戻すため、東西ローマが\n国家予算数年分の全財産を投じた最終決戦",
                "evidence_card": {
                    "title": "【歴史データ】西暦468年 ボン岬沖の海戦",
                    "row1": "・ローマ連合艦隊：軍船1,100隻 ／ 兵員約10万人",
                    "row2": "・遠征費用：金6万4,000ポンド＋銀70万ポンド",
                    "note": "東西ローマの国家財政のすべてを賭けた乾坤一擲の作戦",
                },
            },
            {
                "scene_id": "scene_20",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "cannon_boom",
                "narration": "しかしヴァンダル王ガイセリックは休戦交渉で油断させ、風向きが変わった深夜に油を満載した火船を突入させました。密集していたローマ艦隊は大炎上し、一夜にして壊滅してしまったのです。",
                "sub_top": "深夜の「火船奇襲」でローマ大艦隊が大炎上",
                "sub_main": "復活の最後の資金と艦隊が海の藻屑と消え、\n西ローマの財政破綻が決定づけられた",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_21",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "この敗戦で給料を払えなくなった西ローマは、わずか8年後の476年、傭兵隊長オドアケルによって滅ぼされました。全16分の完全保存版は画面下の関連動画リンクからご覧いただけます。",
                "sub_top": "わずか8年後の西暦476年、西ローマ帝国が滅亡",
                "sub_main": "全16分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_rome_05",
        "title": "ローマ滅亡で人類の文明は「1000年退行」した！？屋根瓦の消滅と北極の氷が示す衝撃データ #Shorts #世界史 #ローマ帝国",
        "top_badge": "【AI実写】考古学と北極の氷が暴く真実 ⑤",
        "hook_line1": "ローマ滅亡で人類の文明は",
        "hook_line2": "「1000年退行」していた！？",
        "beats": [
            {
                "scene_id": "scene_22",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "『ローマ帝国は崩壊したのではなく、中世ヨーロッパへゆるやかに変容しただけだ』。そんな穏やかな学説に対し、オックスフォード大学の考古学者が発掘データから衝撃の反証を突きつけました。",
                "sub_top": "「ゆるやかな変容説」を覆す考古学の証拠",
                "sub_main": "オックスフォード大学ウォード＝パーキンス教授が\n発掘データから「文明の崩壊」を実証",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_23",
                "cam": "close",
                "clip_window": (0.0, 5.8),
                "se": "page_turn",
                "narration": "ローマ時代には農村の家まで当たり前だった『粘土の屋根瓦』と『ろくろ製の陶器』が、5世紀以降ヨーロッパから完全に消滅し、さらに栄養状態の悪化で家畜の牛の体格が15センチも縮んでいたのです。",
                "sub_top": "屋根瓦と陶器が消え、牛の体高が15cm縮小",
                "sub_main": "西ヨーロッパの一般市民の生活水準は\n文字通り「1000年前の鉄器時代」へ逆戻りした",
                "evidence_card": {
                    "title": "【考古学証拠】ローマ滅亡後の「3大退行データ」",
                    "row1": "① 粘土製の屋根瓦・ろくろ製陶器の技術が消滅",
                    "row2": "② 飼料と品種改良の喪失で牛の体高が10〜15cm縮小",
                    "note": "③ 流通網の消滅で貨幣経済と識字率が劇的に低下",
                },
            },
            {
                "scene_id": "scene_24",
                "cam": "wide",
                "clip_window": (0.0, 5.8),
                "se": "low_timpani",
                "narration": "さらに決定的なのが北極圏グリーンランドの氷床コアです。氷の中に記録されたローマ時代の銀や銅の製錬による大気データは、滅亡とともにゼロ近くへ急落し、16世紀まで1000年間も戻りませんでした。",
                "sub_top": "グリーンランド氷床コアが記録した「1000年の空白」",
                "sub_main": "ローマ時代の金属製錬・工業生産の規模は\n16世紀のルネサンス期まで1000年間超えられなかった",
                "evidence_card": {
                    "title": "【北極氷床コア】大気中の鉛・銅排出量データ",
                    "row1": "・西暦1〜2世紀：産業革命前としては人類史上最高値",
                    "row2": "・西暦500〜1500年：排出量がほぼゼロへ急落・停滞",
                    "note": "地球の氷そのものが「1000年間の産業崩壊」を記録していた",
                },
            },
            {
                "scene_id": "scene_25",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "なぜこれほど高度な文明が崩れ落ちたのか？210の仮説と最新科学を完全網羅した全16分の本編動画は、画面下の関連動画リンクから今すぐご覧いただけます。",
                "sub_top": "ローマ帝国滅亡のすべてを1本で完全解説！",
                "sub_main": "全16分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
]


def build_all_rome_shorts() -> List[Path]:
    ROME_SHORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    built_files: List[Path] = []

    with tempfile.TemporaryDirectory(prefix="rome_shorts_") as tmp:
        work_dir = Path(tmp)
        bgm_wav = work_dir / "bgm_short.wav"
        generate_cinematic_history_bgm(16.0, bgm_wav)

        for s_idx, spec in enumerate(ROME_SHORTS_SPECS, start=1):
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
                flow_mp4 = resolve_rome_scene_mp4(beat["scene_id"])
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
            out_mp4 = ROME_SHORTS_OUT_DIR / f"{short_id}.mp4"
            tmp_out_mp4 = work_dir / f"final_{short_id}.mp4"
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
                    f"[0:a]volume=1.18[va];[1:a]atrim=0:{s_dur+0.5:.2f},volume=0.28,afade=t=out:st={max(0.0, s_dur-2.0):.2f}:d=2.0[ba];[va][ba]amix=inputs=2:duration=first:dropout_transition=0[a]",
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
                    str(tmp_out_mp4),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            tmp_out_mp4.replace(out_mp4)
            print(f"[ROME SHORT DONE] {out_mp4.name} ({s_dur:.1f}s) | {spec['hook_line1']} {spec['hook_line2']}", flush=True)
            built_files.append(out_mp4)

    return built_files


if __name__ == "__main__":
    build_all_rome_shorts()
