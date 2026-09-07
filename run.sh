#!/bin/bash
# talk2clip 统一运行器 — 所有入口共用
#   ./run.sh              → 启动 talk2clip
#   ./run.sh settings.py  → 打开设置界面（或 ./run.sh --once 等）
cd "$(dirname "$0")"
if [ -x ".venv/bin/python3" ]; then
  PY=".venv/bin/python3"
else
  PY="python3"
fi
if [ -n "$1" ] && [ "$1" != "talk2clip.py" ]; then
  exec "$PY" "$@"
fi
exec "$PY" talk2clip.py
