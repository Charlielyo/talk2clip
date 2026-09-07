#!/bin/bash
# 设置界面启动器 — 双击打开（无需终端命令）
cd "$(dirname "$0")"
if [ -x ".venv/bin/python3" ]; then
  PY=".venv/bin/python3"
elif [ -x "$HOME/.hermes/hermes-agent/venv/bin/python3" ]; then
  PY="$HOME/.hermes/hermes-agent/venv/bin/python3"
else
  PY="python3"
fi
"$PY" settings.py
