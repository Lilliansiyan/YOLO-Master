# F1 Studio 快速启动指南 / Quick Start Guide

## 方法 1: 使用启动脚本 (推荐)

```bash
./start_f1_studio.sh
```

脚本会自动：
- 创建/激活虚拟环境
- 安装所需依赖
- 启动 Gradio 界面

## 方法 2: 手动启动

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 如果首次运行，安装依赖
pip install gradio pandas opencv-python pillow pyyaml numpy torch torchvision ultralytics

# 3. 启动界面
python app.py
```

## 访问界面

启动后，浏览器会自动打开: `http://127.0.0.1:7860`

进入 **📋 Task Management** tab 即可使用 F1 Studio 功能。

## 快速测试

提交一个训练任务：
- Model: `yolo11n.pt`
- Data: `coco8.yaml`
- Epochs: `1`
- Image Size: `32`

点击 **▶️ Submit Train Task**，等待约 3-10 秒完成。

## 故障排查

### 如果遇到 "No module named 'gradio'" 错误

确保你在虚拟环境中：
```bash
source venv/bin/activate
pip install gradio
```

### 如果遇到 YOLO 相关错误

安装完整依赖：
```bash
source venv/bin/activate
pip install -r requirements.txt
pip install ultralytics
```

## 文档位置

- 操作手册: `docs/F1_STUDIO_MANUAL.md`
- 技术文档: `F1_STUDIO_README.md`
- 项目总结: `F1_STUDIO_P0_SUMMARY.md`
