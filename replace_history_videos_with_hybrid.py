#!/usr/bin/env python3
"""
replace_history_videos_with_hybrid.py

Replaces the previously uploaded non-hybrid World History videos on YouTube (`UCr2Imf3_AwavgtvfjoWdcOg`)
with the newly built Hybrid Master Format editions (`35mm Live-Action + Pattern-A Diagrams + VOICEVOX Multi-Cast`)
and also uploads any remaining Music channel Shorts (`music_004_short`, `real_mix_003_short`).

Modes:
  python3 replace_history_videos_with_hybrid.py --step rome_long
  python3 replace_history_videos_with_hybrid.py --step templar_long
  python3 replace_history_videos_with_hybrid.py --step shorts_and_music
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_rome_fall_shorts import ROME_SHORTS_OUT_DIR, ROME_SHORTS_SPECS
from build_templars_shorts import TEMPLAR_SHORTS_OUT_DIR, TEMPLAR_SHORTS_SPECS
from schedule_remaining_history_shorts import (
    BASE,
    FR_LONG_ID,
    JST,
    OUTPUT_DIR,
    find_google_drive_archive_root,
    get_yt,
    get_yt_music,
    load_state,
    save_state,
    upload_one_video,
)


def replace_rome_long() -> None:
    st = load_state()
    yt = get_yt()
    old_id = st.get("rome_long_id") or st.get("uploaded", {}).get("rome_complete_long")

    rome_long_title = (
        "【AI実写・完全保存版】ローマ帝国はなぜ滅亡したのか？｜210の仮説と最新科学が暴く真実！"
        "鉛中毒説のウソ・銀貨98%→2%の崩壊から1000年退行まで"
    )
    rome_long_desc = (
        "世界人口の4分の1（約6,000万人）を統治し、水道橋・水洗トイレ・高層住宅・総延長8万kmの舗装道路を誇った人類史上最大の超大国「ローマ帝国」は、"
        "なぜ跡形もなく崩壊し、ヨーロッパはその後1000年間も屋根瓦すら作れない時代へと退行したのか？\n\n"
        "ドイツの歴史学者アレクサンダー・デマンドが集計した「210種類の滅亡原因説」から、"
        "テレビや雑学本で有名な『鉛製の水道管で鉛中毒になり滅びた説』の科学的検証（2014年・米国科学アカデミー紀要PNAS論文）、"
        "デナリウス銀貨の銀純度98%→2%への暴落と小麦価格200倍のハイパーインフレ、"
        "ギボン『道徳退廃・キリスト教原因説』の致命的な矛盾（東ローマ1000年繁栄の謎）、"
        "カイル・ハーパー教授の『気候変動＆2大パンデミック説』と2018年ハルドン教授らの学術的反論、"
        "フン族の西進とハドリアノポリスの惨敗、西ローマに本当の致命傷を与えた『439年・北アフリカ穀倉地帯の喪失』と『468年・ボン岬沖1100隻の大艦隊炎上』、"
        "そしてオックスフォード大学ウォード＝パーキンス教授の考古学データとグリーンランド氷床コアが証明した『1000年の物質文明退行』まで、"
        "25シーンのAI実写映像とシルエット図解・VOICEVOX掛け合いで徹底解説します。\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📖 目次（チャプター）\n"
        "━━━━━━━━━━━━━━━\n"
        "00:00 プロローグ：西暦117年 人口6000万人・100万都市ローマの絶頂と「210の滅亡原因説」\n"
        "01:12 【歴史の疑問 Q1・図解①】なぜローマ滅亡の理由だけで「210種類」もの仮説があるのか？\n"
        "01:55 第1章：有名な都市伝説「鉛の水道管でローマ滅亡説」の科学的検証（2014年PNAS論文）\n"
        "03:25 【歴史の疑問 Q2・科学検証②】水道管の石灰バリアと、真の毒源『サパ（鉛鍋ブドウ糖蜜）』\n"
        "04:09 第2章：デナリウス銀貨の純度「98%→2%」への暴落と小麦価格200倍のハイパーインフレ\n"
        "06:08 【歴史の疑問 Q3・経済データ③】出土硬貨の冶金分析チャートと301年『最高価格令』の失敗\n"
        "06:50 第3章：ギボン『ローマ帝国衰亡史』の「パンとサーカス・キリスト教原因説」の矛盾\n"
        "07:50 【歴史の疑問 Q4・学説比較④】なぜ同じキリスト教の「東ローマ帝国」はその後1000年も繁栄したのか？\n"
        "08:30 第4章：ローマ温暖期の終焉と「アントニヌスの疫病」・2018年の学術論争\n"
        "10:12 【歴史の疑問 Q5・最新争点⑤】気候＆パンデミック決定論（2017年）vs ハルドン教授らの反論（2018年）\n"
        "10:56 第5章：ローマが400年かけて育てた「ゲルマン超部族連合」とフン族の襲来・ハドリアノポリスの惨劇\n"
        "13:03 【歴史の疑問 Q6・地政学図解⑥】フン族の玉突き衝突と406年ライン川防衛線の決壊\n"
        "13:38 第6章：西ローマに本当の致命傷を与えた「439年 北アフリカ喪失」と「468年 ボン岬沖・1100隻の大艦隊炎上」\n"
        "15:21 【歴史の疑問 Q7・財政データ⑦】税収喪失×軍事崩壊の悪魔のスパイラルと476年・少年皇帝の退位\n"
        "16:05 最終章：ローマは「ゆるやかに変容」したのか、それとも「文明が1000年退行」したのか？\n"
        "17:36 【歴史の疑問 Q8・最終結論⑧】屋根瓦の消滅・牛の小型化・グリーンランド氷床コアが示す「1000年の産業停止」\n\n"
        "#ローマ帝国 #世界史 #歴史解説 #今更聞けない世界史の深層 #古代ローマ #歴史ミステリー #大人の教養 #ドキュメンタリー"
    )
    rome_long_tags = [
        "ローマ帝国",
        "世界史",
        "ローマ帝国滅亡",
        "古代ローマ",
        "東ローマ帝国",
        "ビザンツ帝国",
        "ゲルマン人の大移動",
        "歴史解説",
        "歴史の真実",
        "諸説",
        "今更聞けない世界史の深層",
        "大人の教養",
    ]

    mp4_path = OUTPUT_DIR / "history_rome_fall_complete_long.mp4"
    thumb_path = OUTPUT_DIR / "history_rome_fall_thumb.jpg"
    new_id = upload_one_video(
        yt=yt,
        mp4_path=mp4_path,
        title=rome_long_title,
        description=rome_long_desc,
        tags=rome_long_tags,
        publish_at_iso=None,
        thumb_path=thumb_path,
    )
    print(f"[HYBRID REPLACED] Uploaded NEW Hybrid Master Rome Long -> https://youtu.be/{new_id}", flush=True)

    if old_id and old_id != new_id:
        try:
            yt.videos().delete(id=old_id).execute()
            print(f"[CLEANUP] Deleted old non-hybrid Rome Long ({old_id})", flush=True)
        except Exception as e:
            print(f"[WARN] Could not delete old Rome Long {old_id}: {e}", flush=True)

    st["rome_long_id"] = new_id
    st["uploaded"]["rome_complete_long"] = new_id
    save_state(st)


def replace_templar_long() -> None:
    st = load_state()
    yt = get_yt()
    old_id = st.get("templar_long_id") or st.get("uploaded", {}).get("templar_complete_long")

    templar_long_title = (
        "【AI実写・完全保存版】十字軍とテンプル騎士団の真実｜なぜ「聖戦の英雄」は世界初の巨大銀行になり、"
        "13日の金曜日に一斉逮捕・処刑されたのか？"
    )
    templar_long_desc = (
        "個人の財産を一切禁じられた「9人の貧しき修道騎士」が、なぜヨーロッパ〜中東に9,000箇所の要塞を持ち、"
        "王侯貴族を借金漬けにする『世界初の多国籍メガバンク』へと変貌したのか？\n"
        "そして1307年10月13日（金曜日）、なぜ彼らは突如として「悪魔バフォメットを崇拝する異端者」として一斉逮捕され、"
        "最後の総長ジャック・ド・モレーはパリの火刑台で処刑されたのか？\n\n"
        "1095年クレルモン公会議と第1回十字軍の「4つの本当の動機」、1139年教皇大勅書による超法規的な非課税特権と暗号小切手（トラベラーズチェック）の発明、"
        "船代の借金返済のために同じキリスト教の首都コンスタンティノープルを滅ぼした「第4回十字軍の暴走」、"
        "フランス王フィリップ4世の国家破産と「借金踏み倒し計画」、言語学が解明した『悪魔バフォメット＝ムハンマドの古語訛り』の真相、"
        "2001年にバチカン秘密文書館で700年ぶりに発見された『シノン羊皮紙（教皇による無罪・赦免記録）』、"
        "そして火刑台の総長が放った予言のあと1年以内に教皇とフランス王が相次いで急死し、カペー朝断絶から英仏百年戦争へ至る歴史の結末まで、"
        "25シーンのAI実写映像とシルエット図解・VOICEVOX掛け合いで徹底解説します。\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📖 目次（チャプター）\n"
        "━━━━━━━━━━━━━━━\n"
        "00:00 プロローグ：1307年10月13日（金曜日）夜明けのパリ・テンプル塔包囲と総長モレーの逮捕\n"
        "01:02 【歴史の疑問 Q1・図解①】なぜ「清貧の修道士」が国家を超える「世界初の巨大銀行」になったのか？\n"
        "01:42 第1章：1095年クレルモン公会議と「デウス・ウルト」・1099年エルサレム陥落の真実\n"
        "03:11 【歴史の疑問 Q2・歴史検証②】十字軍を動かした「免罪特権」と次男・三男の土地争奪戦\n"
        "03:51 第2章：1119年「9人の貧しき騎士」と1139年教皇大勅書・暗号化された『巡礼小切手』の発明\n"
        "05:56 【歴史の疑問 Q3・金融図解③】キリスト教の「利子禁止」をどう突破して巨万の富を築いたのか？\n"
        "06:42 第3章：なぜ第4回十字軍（1204年）は同じキリスト教の首都コンスタンティノープルを略奪したのか？\n"
        "08:06 【歴史の疑問 Q4・歴史の暴走④】ヴェネツィアへの「8万5000マルクの借金」と1291年アッコン陥落\n"
        "09:08 第4章：フランス王フィリップ4世の財政破綻・パリ暴動と「13日の金曜日」極秘逮捕作戦\n"
        "10:43 【歴史の疑問 Q5・国家犯罪⑤】1307年10月13日は「一斉逮捕の日」・借金踏み倒し計画の全貌\n"
        "11:32 第5章：異端審問の拷問室と捏造された「悪魔バフォメット崇拝」の正体\n"
        "12:23 【歴史の疑問 Q6・言語学検証⑥】山羊頭の悪魔像は19世紀の創作！バフォメット＝「ムハンマド」の訛り\n"
        "13:07 第6章：2001年バチカン秘密文書館で700年ぶりに発見された『シノン羊皮紙』の衝撃\n"
        "14:07 【歴史の疑問 Q7・一次史料⑦】実はローマ教皇は1308年にテンプル騎士団を「無罪・赦免」にしていた！\n"
        "15:20 最終章：1314年3月18日 総長ジャック・ド・モレーの自白全面撤回とセーヌ川・シテ島での火刑\n"
        "17:13 【歴史の疑問 Q8・最終結論⑧】1年以内に教皇と国王が急死！カペー朝断絶と百年戦争への転落\n\n"
        "#テンプル騎士団 #十字軍 #世界史 #歴史解説 #今更聞けない世界史の深層 #中世ヨーロッパ #13日の金曜日 #歴史ミステリー #大人の教養"
    )
    templar_long_tags = [
        "テンプル騎士団",
        "十字軍",
        "世界史",
        "13日の金曜日",
        "バフォメット",
        "ジャックドモレー",
        "中世ヨーロッパ",
        "歴史解説",
        "歴史の真実",
        "今更聞けない世界史の深層",
        "歴史ミステリー",
        "大人の教養",
    ]

    mp4_path = OUTPUT_DIR / "history_templars_complete_long.mp4"
    thumb_path = OUTPUT_DIR / "history_templars_thumb.jpg"
    publish_at = "2026-11-01T19:00:00+09:00"
    new_id = upload_one_video(
        yt=yt,
        mp4_path=mp4_path,
        title=templar_long_title,
        description=templar_long_desc,
        tags=templar_long_tags,
        publish_at_iso=publish_at,
        thumb_path=thumb_path,
    )
    print(f"[HYBRID REPLACED] Uploaded NEW Hybrid Master Templar Long -> https://youtu.be/{new_id} (publishAt={publish_at})", flush=True)

    if old_id and old_id != new_id:
        try:
            yt.videos().delete(id=old_id).execute()
            print(f"[CLEANUP] Deleted old non-hybrid Templar Long ({old_id})", flush=True)
        except Exception as e:
            print(f"[WARN] Could not delete old Templar Long {old_id}: {e}", flush=True)

    st["templar_long_id"] = new_id
    st["uploaded"]["templar_complete_long"] = new_id
    save_state(st)


def replace_shorts_and_music() -> None:
    st = load_state()
    st["real_mix_003_long_id"] = "6XsTqnKjt50"
    st["uploaded"]["real_mix_003_long"] = "6XsTqnKjt50"
    save_state(st)

    # 1. Upload pending Music Shorts (`music_004_short`, `real_mix_003_short`)
    arch_root = find_google_drive_archive_root()
    ready_q_root = (
        arch_root / "00_Music_Midnight_Cockpit" / "ready_queue"
        if arch_root is not None
        else BASE / "output" / "music_ready_queue"
    )
    yt_m = get_yt_music()
    for m_id in ("music_004", "real_mix_003"):
        key = f"{m_id}_short"
        if key in st["uploaded"]:
            continue
        m_dir = ready_q_root / m_id
        meta_f = m_dir / "metadata.json"
        mp4_f = m_dir / "output_short_medley.mp4"
        if meta_f.exists() and mp4_f.exists():
            m_data = json.loads(meta_f.read_text(encoding="utf-8"))
            long_vid = st.get(f"{m_id}_long_id") or ""
            s_desc = (
                f"🎧 本編フル動画はこちら 👉 https://youtu.be/{long_vid}\n\n{m_data['description']}"
                if long_vid
                else m_data["description"]
            )
            vid = upload_one_video(
                yt=yt_m,
                mp4_path=mp4_f,
                title=m_data["medley_short_title"],
                description=s_desc,
                tags=m_data["tags"] + ["Shorts", "YouTubeShorts", "サビメドレー"],
                publish_at_iso=None,
                category_id="10",
            )
            st["uploaded"][key] = vid
            save_state(st)
            print(f"[SUCCESS] Uploaded Music Short ({m_id}) -> https://youtube.com/shorts/{vid}", flush=True)

    # 2. Replace Rome Shorts 04..05 and Templar Shorts 01..05 with Hybrid Master versions & update descriptions on 01..03
    yt = get_yt()
    rome_by_id = {m["short_id"]: m for m in ROME_SHORTS_SPECS}
    templar_by_id = {m["short_id"]: m for m in TEMPLAR_SHORTS_SPECS}
    r_long = st.get("rome_long_id") or FR_LONG_ID
    t_long = st.get("templar_long_id") or r_long

    rome_sched = {
        "short_rome_01": None,
        "short_rome_02": None,
        "short_rome_03": "2026-11-01T12:15:00+09:00",
        "short_rome_04": "2026-11-01T18:00:00+09:00",
        "short_rome_05": "2026-11-01T20:00:00+09:00",
    }
    for sid, pub_iso in rome_sched.items():
        old_sid = st.get("uploaded", {}).get(sid)
        sm = rome_by_id[sid]
        desc = (
            f"▼ 全18分【完全保存版】ローマ帝国はなぜ滅亡したのか？（本編フル動画）はこちら！\n"
            f"https://www.youtube.com/watch?v={r_long}\n\n"
            f"{sm['hook_line1']} {sm['hook_line2']}\n"
            f"#ローマ帝国 #世界史 #今更聞けない世界史の深層 #歴史ミステリー #雑学 #Shorts"
        )
        mp4_p = ROME_SHORTS_OUT_DIR / f"{sid}.mp4"
        if mp4_p.exists():
            new_sid = upload_one_video(
                yt=yt,
                mp4_path=mp4_p,
                title=sm["title"],
                description=desc,
                tags=["ローマ帝国", "世界史", "今更聞けない世界史の深層", "歴史の真実", "Shorts"],
                publish_at_iso=pub_iso,
            )
            print(f"[HYBRID SHORT] {sid} -> https://youtube.com/shorts/{new_sid}", flush=True)
            if old_sid and old_sid != new_sid:
                try:
                    yt.videos().delete(id=old_sid).execute()
                except Exception:
                    pass
            st["uploaded"][sid] = new_sid
            save_state(st)

    templar_sched = {
        "short_templars_01": "2026-11-01T21:00:00+09:00",
        "short_templars_02": "2026-11-02T07:30:00+09:00",
        "short_templars_03": "2026-11-02T12:15:00+09:00",
        "short_templars_04": "2026-11-02T19:00:00+09:00",
        "short_templars_05": "2026-11-02T21:00:00+09:00",
    }
    for sid, pub_iso in templar_sched.items():
        old_sid = st.get("uploaded", {}).get(sid)
        sm = templar_by_id[sid]
        desc = (
            f"▼ 全18分【完全保存版】十字軍とテンプル騎士団の真実（本編フル動画）はこちら！\n"
            f"https://www.youtube.com/watch?v={t_long}\n\n"
            f"{sm['hook_line1']} {sm['hook_line2']}\n"
            f"#テンプル騎士団 #十字軍 #世界史 #今更聞けない世界史の深層 #13日の金曜日 #歴史ミステリー #Shorts"
        )
        mp4_p = TEMPLAR_SHORTS_OUT_DIR / f"{sid}.mp4"
        if mp4_p.exists():
            new_sid = upload_one_video(
                yt=yt,
                mp4_path=mp4_p,
                title=sm["title"],
                description=desc,
                tags=["テンプル騎士団", "十字軍", "世界史", "13日の金曜日", "今更聞けない世界史の深層", "Shorts"],
                publish_at_iso=pub_iso,
            )
            print(f"[HYBRID SHORT] {sid} -> https://youtube.com/shorts/{new_sid}", flush=True)
            if old_sid and old_sid != new_sid:
                try:
                    yt.videos().delete(id=old_sid).execute()
                except Exception:
                    pass
            st["uploaded"][sid] = new_sid
            save_state(st)


def watch_all() -> None:
    import time
    start_ts = time.time()
    print("[WATCHER] Uploading pending Music Shorts first...", flush=True)
    st = load_state()
    st["real_mix_003_long_id"] = "6XsTqnKjt50"
    st["uploaded"]["real_mix_003_long"] = "6XsTqnKjt50"
    save_state(st)

    arch_root = find_google_drive_archive_root()
    ready_q_root = (
        arch_root / "00_Music_Midnight_Cockpit" / "ready_queue"
        if arch_root is not None
        else BASE / "output" / "music_ready_queue"
    )
    yt_m = get_yt_music()
    for m_id in ("music_004", "real_mix_003"):
        key = f"{m_id}_short"
        if key in st["uploaded"]:
            continue
        m_dir = ready_q_root / m_id
        meta_f = m_dir / "metadata.json"
        mp4_f = m_dir / "output_short_medley.mp4"
        if meta_f.exists() and mp4_f.exists():
            try:
                import shutil, tempfile
                m_data = json.loads(meta_f.read_text(encoding="utf-8"))
                long_vid = st.get(f"{m_id}_long_id") or ""
                s_desc = (
                    f"🎧 本編フル動画はこちら 👉 https://youtu.be/{long_vid}\n\n{m_data['description']}"
                    if long_vid
                    else m_data["description"]
                )
                tmp_mp4 = Path(tempfile.gettempdir()) / f"tmp_{m_id}_short.mp4"
                shutil.copy2(mp4_f, tmp_mp4)
                vid = upload_one_video(
                    yt=yt_m,
                    mp4_path=tmp_mp4,
                    title=m_data["medley_short_title"],
                    description=s_desc,
                    tags=m_data["tags"] + ["Shorts", "YouTubeShorts", "サビメドレー"],
                    publish_at_iso=None,
                    category_id="10",
                )
                tmp_mp4.unlink(missing_ok=True)
                st["uploaded"][key] = vid
                save_state(st)
                print(f"[SUCCESS] Uploaded Music Short ({m_id}) -> https://youtube.com/shorts/{vid}", flush=True)
            except Exception as e:
                print(f"[WARN] Music Short ({m_id}) upload skipped/retried: {e}", flush=True)

    rome_p = OUTPUT_DIR / "history_rome_fall_complete_long.mp4"
    templar_p = OUTPUT_DIR / "history_templars_complete_long.mp4"
    last_short_p = TEMPLAR_SHORTS_OUT_DIR / "short_templars_05.mp4"

    done_rome = False
    done_templar = False
    done_shorts = False

    while not (done_rome and done_templar and done_shorts):
        try:
            if not done_rome and rome_p.exists() and rome_p.stat().st_mtime >= start_ts - 600 and rome_p.stat().st_size > 50_000_000:
                replace_rome_long()
                done_rome = True
            if not done_templar and templar_p.exists() and templar_p.stat().st_mtime >= start_ts - 600 and templar_p.stat().st_size > 50_000_000:
                replace_templar_long()
                done_templar = True
            if done_rome and done_templar and not done_shorts and last_short_p.exists() and last_short_p.stat().st_mtime >= start_ts - 600:
                replace_shorts_and_music()
                done_shorts = True
        except Exception as e:
            print(f"[WATCHER RETRY] {e}", flush=True)
        if not (done_rome and done_templar and done_shorts):
            time.sleep(15)

    print("[ALL HYBRID REPLACEMENTS COMPLETE!]", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", required=True, choices=["rome_long", "templar_long", "shorts_and_music", "watch_all"])
    args = parser.parse_args()
    if args.step == "rome_long":
        replace_rome_long()
    elif args.step == "templar_long":
        replace_templar_long()
    elif args.step == "shorts_and_music":
        replace_shorts_and_music()
    elif args.step == "watch_all":
        watch_all()

