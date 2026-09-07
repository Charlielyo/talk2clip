#!/bin/bash
# talk2clip 启动器 — 双击运行（保证键盘监听权限）
cd "$(dirname "$0")"
# 解释器优先级: 项目 .venv > hermes venv（本机现状）> 系统 python3
if [ -x ".venv/bin/python3" ]; then
  PY=".venv/bin/python3"
elif [ -x "$HOME/.hermes/hermes-agent/venv/bin/python3" ]; then
  PY="$HOME/.hermes/hermes-agent/venv/bin/python3"
else
  PY="python3"
fi
echo "==========================================="
echo "  talk2clip 已启动 ($PY)"
echo "  按住右 ⌘（可在设置中改）说话，松开自动粘贴"
echo "  打开设置: 双击 打开设置.command"
echo "  关闭本窗口 = 退出程序"
echo "==========================================="
"$PY" talk2clip.py
echo ""
echo "程序已退出。"
