# F1 Studio 操作手册 / Operation Manual

## 目录 / Contents

1. [启动 / Getting Started](#getting-started)
   - [Gradio 界面](#启动界面--launch-interface)
   - [REST API + React UI](#rest-api--react-ui-启动--rest-api--react-ui-launch)
2. [任务提交 / Submit Tasks](#submit-tasks)
3. [查看产物 / View Artifacts](#view-artifacts)
4. [环境检查 / Environment Check](#environment-check)
5. [常见错误 / Common Errors](#common-errors)

---

## Getting Started

### 启动界面 / Launch Interface

```bash
cd /path/to/YOLO-Master
python3 app.py
```

界面将在浏览器自动打开: `http://127.0.0.1:7860`

The interface will automatically open in your browser at: `http://127.0.0.1:7860`

### REST API + React UI 启动 / REST API + React UI Launch

FastAPI 后端 + React 前端提供程序化任务提交和状态监控。

**1. 启动 API 服务器 / Start the API server:**

```bash
cd /path/to/YOLO-Master
uvicorn api:app --reload --port 8000
```

API 文档自动生成，访问: `http://127.0.0.1:8000/docs`

**2. 启动 React 开发界面 / Start the React dev UI** (新开终端 / separate terminal):

```bash
cd frontend
npm install   # 首次运行 / first time only
npm run dev   # 启动于 http://localhost:5173
```

**API 端点一览 / API Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/tasks/train` | 提交训练任务 |
| `POST` | `/api/tasks/predict` | 提交推理任务 |
| `POST` | `/api/tasks/export` | 提交导出任务 |
| `POST` | `/api/tasks/system-check` | 系统环境检查（异步，立即返回202）|
| `GET`  | `/api/tasks` | 列出所有任务（支持分页）|
| `GET`  | `/api/tasks/{job_id}` | 查询单个任务状态及产物 |
| `DELETE` | `/api/tasks/{job_id}` | 取消进行中的任务 |
| `GET`  | `/api/tasks/{job_id}/metrics` | 获取训练指标 |
| `GET`  | `/health` | 健康检查 |

---

### 界面导航 / Navigation

- **🖼️ Inference**: 原有推理功能（交互式单张图片推理）
- **📋 Task Management**: F1 Studio任务管理（训练/预测/导出）

---

## Submit Tasks

### 1️⃣ 训练任务 / Train Task

在 **Task Management** tab → **Train** 子tab:

**必填字段 / Required Fields:**
- **Model**: 模型文件名或路径 (例如: `yolo11n.pt`, `models/custom.pt`)
- **Data**: 数据集配置文件 (例如: `coco8.yaml`, `datasets/custom.yaml`)
- **Epochs**: 训练轮数 (建议测试时用 1-3)
- **Image Size**: 图片尺寸 (建议测试时用 32 或 64)

**示例 / Example:**
```
Model: yolo11n.pt
Data: coco8.yaml
Epochs: 1
Image Size: 32
```

点击 **▶️ Submit Train Task**，任务将同步执行（约3-10秒）。

完成后会显示:
- ✅ 任务ID和状态
- 📁 输出目录路径
- 自动刷新任务历史列表

### 2️⃣ 推理任务 / Predict Task

在 **Task Management** tab → **Predict** 子tab:

**必填字段 / Required Fields:**
- **Model**: 模型路径 (例如: `yolo11n.pt`, `runs/agent/train-abc/weights/best.pt`)
- **Source**: 图片/视频路径 (例如: `coco8/images/`, `datasets/test/`)

**示例 / Example:**
```
Model: yolo11n.pt
Source: coco8/images/
```

点击 **▶️ Submit Predict Task**。

产物包括:
- 标注后的图片 (`.jpg`)
- 检测结果 (`.txt`)

### 3️⃣ 导出任务 / Export Task

在 **Task Management** tab → **Export** 子tab:

**必填字段 / Required Fields:**
- **Model**: 模型路径
- **Format**: 导出格式 (onnx / torchscript / coreml / saved_model / tflite)

**示例 / Example:**
```
Model: yolo11n.pt
Format: onnx
```

点击 **▶️ Submit Export Task**。

产物包括:
- 导出的模型文件 (`.onnx` / `.torchscript` 等)
- 文件大小和路径信息

---

## View Artifacts

### 查看任务历史 / View Task History

任务历史表格显示:
- **Job ID**: 任务唯一标识符
- **Skill**: 任务类型 (yolo.train / yolo.predict / yolo.export)
- **Status**: 
  - ✅ ok - 成功
  - ❌ failed - 失败
  - ⏱️ timeout - 超时
- **Submitted At**: 提交时间
- **Artifacts**: 产物文件数量

点击 **🔄 Refresh History** 手动刷新列表。

### 查看产物详情 / View Artifact Details

1. 从任务历史表格复制 **Job ID** (例如: `train-abc12345`)
2. 粘贴到 **Artifact Inspector** 的输入框
3. 点击 **👁️ View Artifacts**

产物按类别显示:
- ⚖️ **Weights**: 模型权重文件 (`.pt`)
  - `best.pt` - 验证集最佳权重
  - `last.pt` - 最后一个epoch的权重
- 📊 **Results**: 训练结果和可视化
  - `results.csv` - 指标数据
  - `results.png` - 训练曲线图
- 📦 **Exports**: 导出的模型
- ⚙️ **Configs**: 配置文件
- 📝 **Logs**: 日志文件

**Quick Downloads** 区域显示最多5个关键文件供快速下载。

### 产物存储位置 / Artifact Storage Location

所有产物保存在: `runs/agent/`

目录结构:
```
runs/agent/
├── yolo-train-abc123/
│   ├── weights/
│   │   ├── best.pt
│   │   └── last.pt
│   ├── results.csv
│   ├── results.png
│   └── skill_manifest.json
├── yolo-predict-def456/
│   └── ...
└── yolo-export-ghi789/
    └── ...
```

---

## Environment Check

### 系统环境检查 / System Environment Check

点击 **🩺 Environment Check** 按钮进行环境诊断。

检查内容:
- ✅ YOLO CLI 是否可用
- ✅ Python环境和版本
- ✅ 可用设备 (CPU / CUDA / MPS)
- ✅ Ultralytics版本
- ✅ 依赖库状态

输出示例:
```json
{
  "skill": "yolo.system",
  "status": "ok",
  "system": {
    "cli_available": true,
    "devices": ["cpu", "mps"],
    "ultralytics_version": "8.x.x"
  }
}
```

---

## Common Errors

### ❌ Path Violation

**错误信息:**
```
Path violation: ../etc/passwd (contains '..' or absolute path)
```

**原因:** 路径不符合安全白名单规则

**解决方案:**
- 只使用相对路径，不要使用 `..` 或绝对路径 (`/`)
- 确保路径在白名单目录内:
  - `models/`
  - `datasets/`
  - `runs/`
  - `ckpts/`
  - `yolo*` (内置模型)
  - `coco*` (内置数据集)

**正确示例:**
```
✅ models/yolo11n.pt
✅ datasets/custom/data.yaml
✅ runs/agent/train-abc/weights/best.pt
✅ yolo11n.pt
✅ coco8.yaml
```

**错误示例:**
```
❌ ../etc/passwd
❌ /usr/local/model.pt
❌ ../../secrets/key.txt
```

---

### ⏱️ Task Timeout

**错误信息:**
```
Task execution exceeded 600 second timeout
```

**原因:** 任务执行超过10分钟限制

**解决方案:**
- 减少训练轮数 (epochs): 测试时用 1-3
- 减小图片尺寸 (imgsz): 测试时用 32 或 64
- 使用更小的数据集: 如 `coco8.yaml` 而非 `coco128.yaml`
- 使用更小的模型: 如 `yolo11n.pt` 而非 `yolo11x.pt`

**P0阶段推荐配置 (快速测试):**
```
Model: yolo11n.pt
Data: coco8.yaml
Epochs: 1
Image Size: 32
```

预计执行时间: 3-10秒

---

### ❌ Model File Not Found

**错误信息:**
```
Failed to load model: [Errno 2] No such file or directory: 'models/custom.pt'
```

**原因:** 模型文件不存在

**解决方案:**
1. 检查文件路径是否正确
2. 使用内置模型进行测试: `yolo11n.pt` / `yolo11s.pt` / `yolo11m.pt`
3. 确保训练任务已完成，权重文件已生成

**查找已训练的模型:**
```bash
ls runs/agent/*/weights/best.pt
```

---

### ❌ Dataset Not Found

**错误信息:**
```
Dataset 'custom.yaml' not found
```

**原因:** 数据集配置文件不存在

**解决方案:**
1. 使用内置数据集进行测试: `coco8.yaml`
2. 确保自定义数据集的 YAML 文件路径正确
3. 检查 YAML 文件中的路径配置

**内置数据集 (无需下载):**
- `coco8.yaml` - 8张图片的COCO子集 (推荐测试用)
- `coco128.yaml` - 128张图片的COCO子集

---

### ❌ Dispatcher Not Found

**错误信息:**
```
Dispatcher not found: agent/scripts/run_yolo_master_skill.py
```

**原因:** 未从YOLO-Master仓库根目录启动

**解决方案:**
```bash
# 确保在正确的目录
cd /path/to/YOLO-Master

# 验证dispatcher存在
ls agent/scripts/run_yolo_master_skill.py

# 启动界面
python3 app.py
```

---

### 🗑️ 清空历史 / Clear History

如果任务历史记录过多，点击 **🗑️ Clear History** 按钮清空所有记录。

**注意:** 此操作只清空数据库记录，不会删除产物文件。产物文件仍保存在 `runs/agent/` 目录。

---

## Tips & Best Practices

### 快速测试流程 / Quick Test Workflow

1. **环境检查**: 点击 🩺 Environment Check 确保系统就绪
2. **训练测试**: 使用 `yolo11n.pt` + `coco8.yaml` + epochs=1 + imgsz=32
3. **查看产物**: 复制 Job ID，点击 👁️ View Artifacts
4. **推理测试**: 使用训练得到的 `runs/agent/train-xxx/weights/best.pt`
5. **导出测试**: 导出为 ONNX 格式

### 性能建议 / Performance Tips

- **P0测试**: epochs=1, imgsz=32-64, coco8数据集
- **快速验证**: 使用 `n` 系列模型 (yolo11n)
- **生产训练**: epochs=100-300, imgsz=640, 完整数据集

### 数据管理 / Data Management

- 任务记录保存在: `f1_studio.db` (SQLite)
- 产物文件保存在: `runs/agent/`
- 定期清理旧产物: `rm -rf runs/agent/yolo-*-old`

---

## Troubleshooting Checklist

遇到问题时，依次检查:

1. ✅ 是否在 YOLO-Master 仓库根目录？
2. ✅ dispatcher 文件是否存在？(`agent/scripts/run_yolo_master_skill.py`)
3. ✅ Python 版本是否 >= 3.8？
4. ✅ 路径是否在白名单内？
5. ✅ 模型文件是否存在？
6. ✅ 数据集文件是否存在？
7. ✅ 是否使用了合理的测试参数？(epochs=1, imgsz=32)

---

## Support & Contact

- 项目仓库 / Repository: `Lilliansiyan/YOLO-Master`
- 分支 / Branch: `siyan/f1-admission-smoke`
- 文档 / Documentation: `F1_STUDIO_README.md`

**F1 Studio 版本**: P0 (最小闭环)
**最后更新**: 2024-08-30
