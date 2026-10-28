#!/bin/bash
# ==============================================================================
# setup_mac_scheduler.sh
# Mac標準の `launchd` で毎日 深夜 02:30 AM (JST) に `auto_publish_japan_ranking.py`
# をバックグラウンド低負荷モード（Nice=15, LowPriorityIO）で自動実行し、
# API無料枠上限（1日3セット＝本編3本＋Shorts 3本＝計6本, 9,900/10,000 units）を
# 海外3大ゴールデンタイム（欧州夜・北米東海岸夜・北米西海岸夜）に予約公開します。
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.tom.youtube-japan-ranking-autopublish"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

if [ -x "${PROJECT_DIR}/.venv/bin/python" ]; then
    PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
else
    PYTHON_BIN="$(which python3)"
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "${PROJECT_DIR}/output"

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/caffeinate</string>
        <string>-i</string>
        <string>${PYTHON_BIN}</string>
        <string>${PROJECT_DIR}/auto_publish_japan_ranking.py</string>
        <string>--midnight-batch</string>
        <string>--daily-sets</string>
        <string>3</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>Nice</key>
    <integer>15</integer>
    <key>LowPriorityIO</key>
    <true/>
    <key>ProcessType</key>
    <string>Background</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <!-- 毎日 深夜 02:30 JST に一括生成＆海外ゴールデンタイム予約アップロード -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/output/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/output/launchd_stderr.log</string>
</dict>
</plist>
EOF

chmod +x "${PROJECT_DIR}/auto_publish_japan_ranking.py"
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✅ Mac標準スケジューラ (launchd) への深夜バッチ自動生成＆海外時間予約公開ジョブ登録が完了しました！"
echo "  設定ファイル : $PLIST_PATH"
echo "  実行時刻     : 毎日 深夜 02:30 AM JST（バックグラウンド低負荷モード: Nice=15 / LowPriorityIO）"
echo "  投稿本数     : 1日3セット（本編3本＋Shorts 3本＝計6本 / API無料枠 9,900/10,000 units 使い切り）"
echo "  予約公開枠   : ①04:00 JST (欧州・英国20時) / ②09:00 JST (NY 20時) / ③13:00 JST (LA 21時)"
