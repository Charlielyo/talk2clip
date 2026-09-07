#!/bin/bash
# talk2clip 启动器 — 双击运行
cd "$(dirname "$0")"
PY="python3"
[ -x ".venv/bin/python3" ] && PY=".venv/bin/python3"
echo "==========================================="
echo "  talk2clip 已启动（解释器: $PY）"
echo "  按住右 ⌘（可在设置中改）说话，松开自动粘贴"
echo "  打开设置: 双击 打开设置.command"
echo "  关闭本窗口 = 退出程序"
echo "==========================================="
"$PY" talk2clip.py
echo ""
echo "程序已退出。"
