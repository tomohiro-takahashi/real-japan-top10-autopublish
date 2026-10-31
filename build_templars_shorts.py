#!/usr/bin/env python3
"""
build_templars_shorts.py

Generates 5 high-impact vertical 9:16 Shorts (1080x1920, ~55-60s each) from the Crusades & Knights Templar Complete Edition.
Each Short features:
1. Top persistent Mystery Hook Header (crimson badge + 2-line giant question hook)
2. Center 9:16 AI Live-Action Cinema Viewport with multi-camera cuts + pop-up "Evidence / 諸説 Data Card" on the reveal beat
3. Bottom giant high-contrast Japanese subtitles + funnel CTA bar pointing to the 18-minute Complete Edition
4. Audible Baroque harpsichord + cello BGM + dramatic sound effects (`question_sting`, `blade_glint`, `low_timpani`, `page_turn`)
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from build_japan_ranking import OUTPUT_DIR, get_duration
from build_templars_cinema import resolve_templar_scene_mp4
from build_world_history_cinema import build_narration_beat_wav, generate_cinematic_history_bgm
from build_world_history_shorts import render_short_beat_mp4, render_short_overlay_9x16

TEMPLAR_SHORTS_OUT_DIR = OUTPUT_DIR / "history_shorts_templars"

TEMPLAR_SHORTS_SPECS: List[Dict[str, Any]] = [
    {
        "short_id": "short_templars_01",
        "title": "なぜ13日の金曜日にテンプル騎士団は一斉逮捕されたのか？悪魔崇拝の裏に隠された「フランス王の借金踏み倒し」 #Shorts #世界史 #テンプル騎士団",
        "top_badge": "【AI実写】13日の金曜日のミステリー ①",
        "hook_line1": "「13日の金曜日」一斉逮捕の真相",
        "hook_line2": "悪魔崇拝ではなく借金踏み倒し！？",
        "beats": [
            {
                "scene_id": "scene_01",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "1307年10月13日の金曜日、聖戦の英雄だったはずのテンプル騎士団が、悪魔を崇拝する異端者としてフランス全土で一斉に逮捕されました。しかしその本当の理由をご存知でしょうか？",
                "sub_top": "1307年10月13日（金曜日）夜明けの電撃逮捕",
                "sub_main": "なぜキリスト教最強の「テンプル騎士団」が\n一夜にして異端者として全員逮捕されたのか？",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_14",
                "cam": "close",
                "clip_window": (0.0, 5.8),
                "se": "page_turn",
                "narration": "実は当時のテンプル騎士団は、ヨーロッパ中に9000箇所の拠点を持つ世界最大の銀行であり、フランス国王フィリップ4世に莫大な戦争資金を貸し付ける最大の債権者だったのです。",
                "sub_top": "本当の理由：フランス王フィリップ4世の「国家破産」",
                "sub_main": "イギリスとの長期戦争で破産した国王は、\nテンプル騎士団に莫大な借金を背負っていた",
                "evidence_card": {
                    "title": "【歴史の真実】フィリップ4世の借金踏み倒し計画",
                    "row1": "× 表向きの理由：悪魔バフォメット崇拝・異端の摘発",
                    "row2": "【真実】最大の債権者である騎士団を潰し借金を帳消しに",
                    "note": "1ヶ月前に「10月13日夜明け前に開封せよ」と極秘命令書を配布",
                },
            },
            {
                "scene_id": "scene_17",
                "cam": "close",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "借金を返せないフィリップ4世は、10月13日の夜明けに総長以下を一斉逮捕して金庫を差し押さえ、過酷な拷問によって『悪魔バフォメットを拝んだ』という嘘の自白を強要しました。",
                "sub_top": "過酷な拷問で捏造された「悪魔バフォメット崇拝」",
                "sub_main": "パリだけで36人の騎士が拷問死し、\n国家ぐるみの強盗を正当化するため冤罪が作られた",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_02",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "そして7年後の火刑台で総長が放った呪いの予言と、2001年にバチカンで発見された極秘文書の真実は、画面下の関連動画から全18分の本編をご覧ください。",
                "sub_top": "700年後にバチカンで発見された「無罪の証拠」とは？",
                "sub_main": "全18分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_templars_02",
        "title": "無一文の修道士が「世界初の国際メガバンク」を作った錬金術！暗号小切手と非課税特権の秘密 #Shorts #世界史 #テンプル騎士団",
        "top_badge": "【AI実写】中世最大のマネー革命 ②",
        "hook_line1": "個人の財産を禁じられた修道士が",
        "hook_line2": "なぜ「世界初の巨大銀行」に！？",
        "beats": [
            {
                "scene_id": "scene_06",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "1頭の馬に2人で乗るほど貧しかった9人の修道騎士が、なぜわずか100年でヨーロッパの王族を借金漬けにする『世界初の国際メガバンク』になれたのでしょうか？",
                "sub_top": "1119年 たった9人の貧しい騎士からスタート",
                "sub_main": "個人の所有を一切禁じられた「清貧の修道士」が\nなぜヨーロッパ最大の金融帝国になったのか？",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_08",
                "cam": "close",
                "clip_window": (0.0, 5.8),
                "se": "page_turn",
                "narration": "彼らが発明したのが、世界初のトラベラーズチェック『巡礼小切手』でした。ロンドンやパリの支部で金貨を預けて暗号入りの羊皮紙を受け取れば、山賊に襲われることなく聖地エルサレムで現金を引き出せたのです。",
                "sub_top": "世界初の国際小切手「トラベラーズチェック」の発明",
                "sub_main": "パリやロンドンで金貨を預け、暗号入りの羊皮紙1枚で\n聖地エルサレムの支部から現金を引き出す仕組み",
                "evidence_card": {
                    "title": "【金融史の革命】テンプル騎士団の銀行システム",
                    "row1": "① 暗号と封蝋印を使った「国際送金・小切手」を発明",
                    "row2": "② 1139年教皇大勅書で「すべての税金・関税が免除」",
                    "note": "欧州〜中東の約9,000箇所の武装要塞が24時間体制で金庫を警備",
                },
            },
            {
                "scene_id": "scene_09",
                "cam": "wide",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "さらに中世キリスト教では利子を取ることが禁じられていましたが、騎士団は『為替・警備手数料』という名目でこれを突破し、フランス王国の国庫まで預かる超巨大銀行へと成長しました。",
                "sub_top": "教会の「利子禁止」を「警備・為替手数料」で突破",
                "sub_main": "パリのテンプル塔はフランス王国の事実上の国庫となり\nイギリス王の王冠すら借金の担保として保管した",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_14",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "しかし、あまりにも巨大になりすぎた富が、やがてフランス王による『13日の金曜日の惨劇』を招くことになります。全18分の完全保存版は画面下の関連動画からご覧ください。",
                "sub_top": "国家を超えた巨大銀行を襲った「1307年の悲劇」",
                "sub_main": "全18分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_templars_03",
        "title": "聖地奪還のはずが「同じキリスト教の首都」を大略奪！？第4回十字軍が借金返済で暴走した黒歴史 #Shorts #世界史 #十字軍",
        "top_badge": "【AI実写】教科書が詳しく語らない黒歴史 ③",
        "hook_line1": "聖地奪還の「第4回十字軍」が",
        "hook_line2": "同じキリスト教の首都を滅ぼした！？",
        "beats": [
            {
                "scene_id": "scene_10",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "イスラム教徒から聖地エルサレムを取り戻すはずの『第4回十字軍』が、聖地へ一歩も行くことなく、同じキリスト教の超大国・東ローマ帝国の首都を滅ぼしてしまったことをご存知でしょうか？",
                "sub_top": "世界史最大の暴走「第4回十字軍（1202〜1204年）」",
                "sub_main": "なぜ聖戦の十字軍が、イスラムではなく\n「同じキリスト教の首都」を襲撃・略奪したのか？",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_11",
                "cam": "wide",
                "clip_window": (0.0, 5.8),
                "se": "cannon_boom",
                "narration": "原因は『船代の借金』でした。ヴェネツィアに3万3500人分の大艦隊を発注した十字軍は、兵士が3分の1しか集まらずに破産し、借金を返すためにヴェネツィア元首の言いなりとなってキリスト教都市を次々と襲ったのです。",
                "sub_top": "原因はヴェネツィアへの「8万5,000マルクの借金」",
                "sub_main": "船代が払えず、90歳の盲目の元首ダンドロに操られ\nローマ教皇から「破門」されながら暴走を続けた",
                "evidence_card": {
                    "title": "【歴史データ】1204年 第4回十字軍の暴走",
                    "row1": "・造船契約：兵33,500人分（銀85,000マルク）を発注",
                    "row2": "・実際の集結：約12,000人（34,000マルクの未払い債務）",
                    "note": "借金帳消しと報酬20万マルクを目当てに東ローマ首都を総攻撃",
                },
            },
            {
                "scene_id": "scene_12",
                "cam": "close",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "1204年4月、ついにコンスタンティノープルを陥落させた十字軍は、聖ソフィア大聖堂の祭壇まで叩き割って3日間略奪し、そのままエルサレムへは行かずに解散してしまいました。",
                "sub_top": "1204年4月 コンスタンティノープル陥落と3日間の大略奪",
                "sub_main": "900年蓄えられた美術品と金銀を根こそぎ強奪し、\n聖地エルサレムには一歩も到達せず解散した",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_03",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "信仰と強欲が絡み合った十字軍とテンプル騎士団の全18分・完全保存版は、画面下の関連動画リンクから今すぐご覧いただけます。",
                "sub_top": "十字軍とテンプル騎士団・200年の真実を完全解説！",
                "sub_main": "全18分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_templars_04",
        "title": "700年間隠されていた『シノン羊皮紙』を2001年にバチカンで発見！テンプル騎士団は実は無罪だった #Shorts #歴史 #ミステリー",
        "top_badge": "【AI実写】2001年バチカン世紀の大発見 ④",
        "hook_line1": "700年眠っていた『シノン羊皮紙』",
        "hook_line2": "教皇は騎士団を「無罪」にしていた！",
        "beats": [
            {
                "scene_id": "scene_20",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "悪魔バフォメットを崇拝した罪で滅ぼされたテンプル騎士団。しかし逮捕から約700年後の2001年、バチカン秘密文書館で発見された1枚の古文書が、世界史の定説を根底から覆しました。",
                "sub_top": "2001年9月 バチカン秘密文書館での世紀の大発見",
                "sub_main": "イタリアの古文書学者バルバラ・フラーレ博士が\n「誤分類された箱」から700年前の原本を発見",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_19",
                "cam": "close",
                "clip_window": (0.0, 5.8),
                "se": "page_turn",
                "narration": "発見された1308年8月付の『シノン羊皮紙』には、ローマ教皇クレメンス5世が総長ジャック・ド・モレーらを直接調査し、『異端の罪はなく無実である』として正式に赦免していたことが記録されていたのです。",
                "sub_top": "1308年8月付『シノン羊皮紙』に記された衝撃の真実",
                "sub_main": "ローマ教皇はテンプル騎士団の悪魔崇拝を否定し、\n3人の枢機卿の封蝋印とともに「正式な赦免」を与えていた",
                "evidence_card": {
                    "title": "【一次史料】2001年発見『シノン羊皮紙』の結論",
                    "row1": "① 悪魔バフォメット＝「ムハンマド」の古語訛り（冤罪）",
                    "row2": "② 教皇クレメンス5世は1308年に騎士団を「赦免（無罪）」",
                    "note": "2007年にバチカンが公式出版し、700年越しに名誉回復",
                },
            },
            {
                "scene_id": "scene_18",
                "cam": "close",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "しかも悪魔とされた『バフォメット』の正体は、イスラムの預言者ムハンマドの中世フランス語訛りであり、有名な山羊の頭の悪魔像は550年後の19世紀に描かれた創作だったことも判明しました。",
                "sub_top": "有名な「山羊頭のバフォメット像」は19世紀の創作",
                "sub_main": "当時の審問官が「ムハンマド（Mahomet）」の訛りを\n謎の悪魔の偶像だとこじつけた完全な冤罪だった",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_21",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "ではなぜ無罪だったはずの総長モレーは1314年に火あぶりにされたのか？全18分の完全保存版は画面下の関連動画リンクから今すぐご覧いただけます。",
                "sub_top": "なぜ教皇が赦免したのに、総長は火刑にされたのか？",
                "sub_main": "全18分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
    {
        "short_id": "short_templars_05",
        "title": "火刑台の総長が放った「呪いの予言」！1年以内に教皇とフランス王が急死し王家が絶滅した衝撃の実話 #Shorts #世界史 #テンプル騎士団",
        "top_badge": "【AI実写】歴史上最も不気味な予言と結末 ⑤",
        "hook_line1": "火刑台の総長が放った「呪いの予言」",
        "hook_line2": "1年以内に教皇と国王が相次ぎ急死！",
        "beats": [
            {
                "scene_id": "scene_22",
                "cam": "wide",
                "clip_window": (0.0, 5.0),
                "se": "question_sting",
                "narration": "1314年3月18日、パリのノートルダム大聖堂前。7年間の投獄の末に終身刑を言い渡されたテンプル騎士団の最後の総長ジャック・ド・モレーは、突然立ち上がって拷問による自白を全面撤回しました。",
                "sub_top": "1314年3月18日 最後の総長ジャック・ド・モレーの覚悟",
                "sub_main": "終身刑で命が助かるはずだった瞬間に立ち上がり、\n「騎士団は無実だ！嘘の自白をした私に罪がある」と絶叫",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_23",
                "cam": "wide",
                "clip_window": (0.0, 5.8),
                "se": "cannon_boom",
                "narration": "面目を潰されたフランス王フィリップ4世は、その日の夕暮れ、セーヌ川の中州でモレーを火あぶりの刑に処しました。その炎の中でモレーは『教皇クレメンスと国王フィリップよ、1年以内に神の法廷へお前たちを召喚する！』と叫んだのです。",
                "sub_top": "セーヌ川・シテ島の火刑台から放たれた「最期の予言」",
                "sub_main": "『教皇クレメンスと国王フィリップよ！\n1年以内に神の法廷へお前たちを召喚する！』",
                "evidence_card": {
                    "title": "【歴史年表】処刑直後に起きた「呪われた王たち」の連鎖死",
                    "row1": "・33日後（1314年4月20日）：教皇クレメンス5世が急死",
                    "row2": "・8ヶ月後（1314年11月29日）：仏王フィリップ4世が急死",
                    "note": "さらに14年以内に王の息子3人が全員若死にしカペー朝が断絶",
                },
            },
            {
                "scene_id": "scene_24",
                "cam": "close",
                "clip_window": (0.0, 5.5),
                "se": "low_timpani",
                "narration": "するとわずか33日後に教皇クレメンス5世が急死し、8ヶ月後には46歳の国王フィリップ4世も脳卒中で死亡しました。さらに王の3人の息子も次々と若死にし、300年続いたカペー朝はわずか14年で絶滅してしまったのです。",
                "sub_top": "1年以内に教皇と国王が死亡・14年でカペー朝が断絶",
                "sub_main": "借金踏み倒しで騎士団を滅ぼしたフランス王家は絶滅し、\nそのまま「英仏百年戦争」の地獄へと転落した",
                "evidence_card": None,
            },
            {
                "scene_id": "scene_25",
                "cam": "close",
                "clip_window": (4.0, 9.8),
                "se": "blade_glint",
                "narration": "十字軍の誕生から世界初の巨大銀行、そして13日の金曜日の真実までを完全網羅した全18分の本編動画は、画面下の関連動画リンクから今すぐご覧いただけます。",
                "sub_top": "十字軍とテンプル騎士団のすべてを1本で完全解説！",
                "sub_main": "全18分の【完全保存版】本編は\n画面下の関連動画リンクから今すぐ視聴！",
                "evidence_card": None,
            },
        ],
    },
]


def build_all_templar_shorts() -> List[Path]:
    TEMPLAR_SHORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    built_files: List[Path] = []

    with tempfile.TemporaryDirectory(prefix="templar_shorts_") as tmp:
        work_dir = Path(tmp)
        bgm_wav = work_dir / "bgm_short.wav"
        generate_cinematic_history_bgm(16.0, bgm_wav)

        for s_idx, spec in enumerate(TEMPLAR_SHORTS_SPECS, start=1):
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
                flow_mp4 = resolve_templar_scene_mp4(beat["scene_id"])
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
            out_mp4 = TEMPLAR_SHORTS_OUT_DIR / f"{short_id}.mp4"
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
            print(f"[TEMPLAR SHORT DONE] {out_mp4.name} ({s_dur:.1f}s) | {spec['hook_line1']} {spec['hook_line2']}", flush=True)
            built_files.append(out_mp4)

    return built_files


if __name__ == "__main__":
    build_all_templar_shorts()
