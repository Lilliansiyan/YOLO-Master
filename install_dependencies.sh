#!/bin/bash
# F1 Studio 完整依赖安装脚本
# Full dependency installation script for F1 Studio

set -e

echo "════════════════════════════════════════════════════════════"
echo "F1 Studio 依赖安装 / Dependency Installation"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境 / Creating virtual environment..."
    python3 -m venv venv
    echo "✅ 虚拟环境已创建"
fi

# Activate venv
echo "🔧 激活虚拟环境 / Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📥 更新 pip..."
pip install --upgrade pip setuptools wheel --quiet

# Install core dependencies
echo "📦 安装核心依赖 / Installing core dependencies..."
echo "   (这可能需要 5-10 分钟，请耐心等待)"
echo "   (This may take 5-10 minutes, please be patient)"
echo ""

pip install numpy pandas pillow pyyaml opencv-python

echo "🔥 安装 PyTorch / Installing PyTorch..."
pip install -i https://pypi.org/simple torch torchvision

echo "🎨 安装 Gradio / Installing Gradio..."
pip install -i https://pypi.org/simple gradio

echo "🚀 安装 Ultralytics / Installing Ultralytics..."
pip install -i https://pypi.org/simple ultralytics

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ 所有依赖安装完成 / All dependencies installed!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "现在可以启动 F1 Studio:"
echo "  ./start_f1_studio.sh"
echo ""
echo "或手动启动 / Or launch manually:"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
