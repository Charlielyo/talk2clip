#!/bin/bash
# 设置界面启动器
cd "$(dirname "$0")"
PY="python3"
[ -x ".venv/bin/python3" ] && PY=".venv/bin/python3"
exec "$PY" settings.py
