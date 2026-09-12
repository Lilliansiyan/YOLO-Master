#!/bin/bash
# F1 Studio 快速启动脚本 / Quick Start Script

set -e

echo "════════════════════════════════════════════════════════════"
echo "F1 Studio 启动脚本 / Launch Script"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境 / Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔧 激活虚拟环境 / Activating virtual environment..."
source venv/bin/activate

# Check if gradio is installed
if ! python -c "import gradio" 2>/dev/null; then
    echo "📥 安装依赖 / Installing dependencies..."
    echo "   这可能需要几分钟 / This may take a few minutes..."
    pip install --upgrade pip setuptools wheel --quiet
    pip install gradio pandas opencv-python pillow pyyaml numpy torch torchvision ultralytics --quiet
    echo "✅ 依赖安装完成 / Dependencies installed"
fi

echo ""
echo "🚀 启动 F1 Studio..."
echo "   界面将在浏览器自动打开 / Interface will open in browser"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""

# Launch app
python app.py
