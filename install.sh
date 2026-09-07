#!/bin/bash
# talk2clip 一键安装（macOS）
# 用法: ./install.sh   创建项目内 .venv + 安装依赖 + 生成 config.json
set -e
cd "$(dirname "$0")"

echo "== 1/3 创建虚拟环境 (.venv) =="
if [ ! -x ".venv/bin/python3" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
echo "✅ .venv 就绪"

echo "== 2/3 安装依赖 =="
.venv/bin/pip install -q -r requirements.txt
echo "✅ 依赖安装完成"

echo "== 3/3 生成配置 =="
if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo "✅ 已生成 config.json（从示例）"
fi

echo ""
echo "==========================================="
echo "  安装完成！接着做两件事："
echo ""
echo "  1. 下载模型（约 250MB，离线识别用）:"
echo "     方法A(推荐): 从 Azure CDN 下载 small.pt 后用转换器:"
echo "       curl -L -o /tmp/small.pt 'https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt'"
echo "       .venv/bin/python3 convert_pt_to_ct2.py /tmp/small.pt models/faster-whisper-small"
echo "     方法B(需能直连 huggingface): 把 models/ 下放 Systran/faster-whisper-small 的模型文件"
echo "     （或设置 config.json 的 model 为 other，首次识别时自动下载）"
echo ""
echo "  2. 授权（首次使用）:"
echo "     系统设置 → 隐私与安全性 → 输入监控: 添加 Terminal"
echo "     系统设置 → 隐私与安全性 → 辅助功能: 添加 Terminal 和 osascript"
echo ""
echo "  然后: ./启动talk2clip.command  或  python3 talk2clip.py"
echo "==========================================="
