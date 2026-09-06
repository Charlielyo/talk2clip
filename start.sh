#!/bin/bash
# 一键启动 talk2clip（从项目目录）
cd "$(dirname "$0")"
exec /Users/charlie/.hermes/hermes-agent/venv/bin/python3 talk2clip.py "$@"
