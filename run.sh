#!/bin/bash
# talk2clip 统一运行器 — 所有入口共用
#   ./run.sh              → 启动 talk2clip
#   ./run.sh settings.py  → 打开设置界面
#   ./run.sh quit         → 退出（读 pidfile 优雅终止）
cd "$(dirname "$0")"

if [ "$1" = "quit" ]; then
  if [ -f .talk2clip.pid ]; then
    PID=$(cat .talk2clip.pid 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      kill "$PID" && echo "✅ 已退出 (pid $PID)"
    else
      echo "ℹ️ 进程未在运行（pidfile 过期），直接清理"
      rm -f .talk2clip.pid
    fi
  else
    echo "ℹ️ 没有 pidfile，talk2clip 可能未在运行"
  fi
  exit 0
fi

if [ -x ".venv/bin/python3" ]; then
  PY=".venv/bin/python3"
else
  PY="python3"
fi
if [ -n "$1" ] && [ "$1" != "talk2clip.py" ]; then
  exec "$PY" "$@"
fi
exec "$PY" talk2clip.py
