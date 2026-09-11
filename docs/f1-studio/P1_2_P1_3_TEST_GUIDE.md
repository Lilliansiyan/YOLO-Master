# P1.2 & P1.3 功能测试指南

## ✅ P1.3: Timeout Configuration UI

### 测试步骤

1. **启动应用**
   ```bash
   python3 app.py
   ```

2. **Train Tab 测试**
   - 打开 "Task Management" → "Train" tab
   - 展开 "⚙️ Advanced Options"
   - 验证默认 timeout = 1800 秒 (30分钟)
   - 尝试输入 30 → 提交后应显示 "⚠️ Timeout must be at least 60 seconds"
   - 尝试输入 10000 → 提交后应显示 "⚠️ Timeout too large"
   - 输入 600 → 正常提交

3. **Predict Tab 测试**
   - 打开 "Predict" tab
   - 展开 "⚙️ Advanced Options"
   - 验证默认 timeout = 600 秒 (10分钟)
   - 测试同样的边界条件

4. **Export Tab 测试**
   - 打开 "Export" tab
   - 展开 "⚙️ Advanced Options"
   - 验证默认 timeout = 600 秒
   - 测试边界条件

### 预期结果
- ✅ 所有 tab 都有 timeout 输入框
- ✅ 默认值合理（训练 30 分钟，其他 10 分钟）
- ✅ 小于 60 秒被拒绝
- ✅ 大于 7200 秒被拒绝
- ✅ 合法值正常提交

---

## ✅ P1.2: Batch Inference Support

### 测试步骤

1. **单文件模式测试**
   - 打开 "Predict" tab
   - 选择 Mode = "Single File/URL"
   - Source 输入: `coco8/images/val/000000000036.jpg`
   - 点击提交 → 应正常执行

2. **批量目录模式测试**
   - Mode 切换到 "Directory (Batch)"
   - Source 输入: `coco8/images/val`
   - 点击提交 → 应显示 "📁 Batch mode: Processing directory with X files"
   - 查看 Task History → 任务完成后查看 Artifacts
   - 应该有多张预测结果图片

3. **错误情况测试 A: 目录模式 + 文件路径**
   - Mode = "Directory (Batch)"
   - Source = `coco8/images/val/000000000036.jpg` (文件，不是目录)
   - 点击提交 → 应显示 "❌ Path is not a directory"

4. **错误情况测试 B: 单文件模式 + 目录路径**
   - Mode = "Single File/URL"
   - Source = `coco8/images/val` (目录)
   - 点击提交 → 应显示 "⚠️ Path is a directory. Please select 'Directory (Batch)' mode"

5. **空目录测试**
   - 创建空目录: `mkdir test_empty_dir`
   - Mode = "Directory (Batch)"
   - Source = `test_empty_dir`
   - 点击提交 → 应显示 "⚠️ Directory is empty"
   - 清理: `rmdir test_empty_dir`

6. **URL 模式测试**
   - Mode = "Single File/URL"
   - Source = `https://ultralytics.com/images/bus.jpg`
   - 点击提交 → 应正常下载并推理

### 预期结果
- ✅ 支持单文件和批量目录两种模式
- ✅ 模式与路径类型匹配时才能提交
- ✅ 批量模式显示文件数量
- ✅ 空目录被正确拒绝
- ✅ URL 绕过路径验证

---

## 🎯 验收标准

### P1.2: Batch Inference
- [x] UI 有批量模式切换
- [x] 支持目录路径批量推理
- [x] 路径验证逻辑正确
- [x] 错误提示清晰

### P1.3: Timeout Configuration
- [x] 所有任务类型有 timeout 输入框
- [x] 默认值合理
- [x] 边界值验证 (60-7200 秒)
- [x] 错误提示清晰

---

## 📝 实现细节

### 修改的文件
- `app.py`: 
  - Train/Predict/Export tabs 增加 timeout 输入
  - Predict tab 增加 batch mode 切换
  - 更新 handler 函数参数
  - 更新事件绑定

### 新增验证逻辑
- **Timeout 验证**: 60 ≤ timeout ≤ 7200
- **Batch mode 验证**:
  - Directory 模式 → 必须是存在的非空目录
  - Single 模式 → 文件或 URL
  - URL 绕过所有路径验证

### 后端支持
- `f1_studio_tasks.py` 已通过 `**kwargs` 支持 timeout
- YOLO dispatcher 原生支持目录批量推理
