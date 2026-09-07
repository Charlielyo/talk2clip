#!/bin/bash
# talk2clip 统一运行器 — 所有入口共用
cd "$(dirname "$0")"
if [ -x ".venv/bin/python3" ]; then
  PY=".venv/bin/python3"
else
  PY="python3"
fi
exec "$PY" "$@" talk2clip.py
