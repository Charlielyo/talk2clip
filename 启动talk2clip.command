#!/bin/bash
# talk2clip 启动器 — 双击运行，自动在终端里启动（保证键盘监听权限）
cd "$(dirname "$0")"
echo "==========================================="
echo "  talk2clip 已启动"
echo "  按住右 ⌘/⌥（可在设置中改）说话，松开自动粘贴"
echo "  或点击菜单栏 🎙️ 图标"
echo "  打开设置: ./settings.py   （词库/热键/选项）"
echo "  关闭本窗口 = 退出程序"
echo "==========================================="
/Users/charlie/.hermes/hermes-agent/venv/bin/python3 talk2clip.py
echo ""
echo "程序已退出。"
