#!/bin/bash
# 临时使用官方 PyPI 源安装 YOLO

source venv/bin/activate

# 保存当前配置
pip config list > pip_config_backup.txt

# 临时切换到官方源
export PIP_INDEX_URL=https://pypi.org/simple

# 安装依赖
echo "📦 安装 Ultralytics..."
pip install --no-cache-dir ultralytics

echo "✅ 验证安装..."
python -c "from ultralytics import YOLO; print('Ultralytics installed successfully')"
yolo version

echo ""
echo "🎉 YOLO 环境配置完成！"
echo "现在可以重新启动 F1 Studio 测试任务了"
