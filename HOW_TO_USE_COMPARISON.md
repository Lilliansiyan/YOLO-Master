# 如何使用实验对比功能

## 📖 使用指南

### 第一步：启动应用

```bash
cd /Users/lilliansun/RhinoBird/YOLO-Master
source venv/bin/activate
python app.py
```

应用会自动在浏览器中打开（默认 http://localhost:7860）

---

### 第二步：进入 Task Management 标签页

在浏览器中，点击顶部的 **"Task Management"** 标签页。

你会看到：
- 任务提交区域（Train/Predict/Export）
- 📜 **Task History** 表格
- 📊 **Experiment Comparison** 区域（新增）

---

### 第三步：在 Task History 中选择任务

#### Gradio 表格的选择方式：

**方法 1：点击行选择（单选）**
```
直接点击表格中的某一行，该行会高亮显示
```

**方法 2：多选（推荐）**
```
方式 A：按住 Ctrl (Windows/Linux) 或 Cmd (Mac)，然后点击多行
方式 B：点击第一行，按住 Shift，再点击最后一行（选中范围内所有行）
```

#### 示例：

**Task History 表格长这样：**
```
┌─────────────────┬────────────┬─────────┬─────────────────┬───────────┐
│ Job ID          │ Skill      │ Status  │ Submitted At    │ Artifacts │
├─────────────────┼────────────┼─────────┼─────────────────┼───────────┤
│ train-f0792d45  │ yolo.train │ ✅ ok   │ 2026-09-07 11:55│ 17 files  │  ← 点击选中
│ train-e6ceaa6d  │ yolo.train │ ✅ ok   │ 2026-09-07 11:54│ 15 files  │  ← Ctrl+点击
│ train-3b514f73  │ yolo.train │ ✅ ok   │ 2026-09-07 11:52│ 12 files  │  ← Ctrl+点击
│ predict-xxx     │ yolo.pred  │ ✅ ok   │ 2026-09-07 11:50│ 5 files   │  ← 不选（会被自动过滤）
└─────────────────┴────────────┴─────────┴─────────────────┴───────────┘
```

**选中后的效果：**
- 选中的行会有**蓝色背景**或**边框高亮**
- 可以选中 2 个或更多行

**提示**：
- ✅ 只选择 `yolo.train` 类型的任务
- ✅ 只选择 `✅ ok` 状态的任务
- ⚠️ `predict` 和 `export` 任务会被自动过滤（但不会报错）

---

### 第四步：点击 Compare 按钮

选中任务后，向下滚动到 **📊 Experiment Comparison** 区域。

点击蓝色的按钮：
```
🔬 Compare Selected Jobs
```

---

### 第五步：查看对比结果

#### 结果分为两部分：

**1. Comparison Summary（摘要）**
```markdown
## 📊 Experiment Comparison Results

**Best performing model**: train-f0792d45 (mAP50: 0.780)
**Compared jobs**: 3 training tasks

### Key Findings:
- Higher epochs (3) → +147.2% mAP50 improvement
- Lower loss correlates with better mAP50 (correlation: -1.00)
```

**2. Comparison Results Table（详细表格）**
```
Job ID           Epochs  ImgSz  mAP50   mAP50-95  Precision  Recall  Loss
train-f0792d45   4       640    0.780   0.650     0.750      0.720   1.200
train-e6ceaa6d   3       640    0.620   0.510     0.680      0.640   1.800
train-3b514f73   2       640    0.450   0.320     0.520      0.480   2.500
```

**表格说明：**
- 已按 **mAP50** 降序排序（最好的在最上面）
- 可以直接看出哪个模型表现最好
- 可以对比不同超参数的影响

---

## ❓ 常见问题

### Q1: 为什么我看不到 Experiment Comparison 区域？

**A**: 确保你在 **Task Management** 标签页，不是 Inference 标签页。
向下滚动，在 Task History 表格下方就能看到。

---

### Q2: 我点击了表格但没有高亮怎么办？

**A**: Gradio 的交互式表格需要：
1. 确认 app.py 已经包含 `interactive=True`（已实现）
2. 尝试刷新页面 (F5)
3. 点击表格中间的单元格，不要点击边缘

---

### Q3: 点击 Compare 按钮后显示警告怎么办？

**可能的警告消息：**

**警告 1: "No jobs selected"**
```
原因：没有选中任何行
解决：点击表格行使其高亮后再点按钮
```

**警告 2: "Please select at least 2 jobs"**
```
原因：只选中了 1 个任务
解决：至少选择 2 个任务才能对比
```

**警告 3: "No valid training results found"**
```
原因：选中的任务都不是训练任务，或 results.csv 文件缺失
解决：确保选择的是 yolo.train 任务且状态为 ✅ ok
```

---

### Q4: 对比结果显示 mAP50 = 0.000 正常吗？

**A**: 是的，这是正常的，可能原因：
1. **训练轮数太少**：epochs=1 或 2 通常不足以学习
2. **图片尺寸太小**：imgsz=32 只是快速测试用的
3. **数据集太小**：coco8 只有 8 张图片

**建议**：运行一个正式训练来测试对比功能
```
Model: yolo11n.pt
Data: coco8.yaml
Epochs: 10          ← 增加轮数
Image Size: 640     ← 使用正常尺寸
```

---

### Q5: 如何取消选择？

**A**: 
- 再次点击已选中的行即可取消选择
- 或者刷新页面重新开始

---

## 🎬 完整演示流程

### 场景：对比 3 个不同 epochs 的训练结果

1. **启动应用**
   ```bash
   python app.py
   ```

2. **提交 3 个训练任务**（如果还没有）
   ```
   任务 1: epochs=1, imgsz=640
   任务 2: epochs=5, imgsz=640
   任务 3: epochs=10, imgsz=640
   ```
   等待它们完成（状态变为 ✅ ok）

3. **进入 Task Management 标签页**

4. **在 Task History 中选择这 3 个任务**
   - 点击第一个任务行
   - 按住 Ctrl/Cmd 点击第二个任务行
   - 按住 Ctrl/Cmd 点击第三个任务行
   - 3 行都应该高亮显示

5. **滚动到 Experiment Comparison 区域**

6. **点击 "🔬 Compare Selected Jobs"**

7. **查看结果**
   - Summary 显示最佳模型
   - Table 显示详细对比
   - Key Findings 显示自动分析

---

## 🎥 视频演示（概念）

```
┌─────────────────────────────────────────┐
│  [Inference] [Task Management]          │  ← 点击这里
├─────────────────────────────────────────┤
│                                         │
│  Task History:                          │
│  ┌───────────────────────────────────┐ │
│  │ [✓] train-001  ✅ ok              │ │  ← 选中
│  │ [✓] train-002  ✅ ok              │ │  ← 选中
│  │ [✓] train-003  ✅ ok              │ │  ← 选中
│  │ [ ] predict-01 ✅ ok              │ │  ← 不选
│  └───────────────────────────────────┘ │
│                                         │
│  📊 Experiment Comparison               │
│  ┌───────────────────────────────────┐ │
│  │ [🔬 Compare Selected Jobs]        │ │  ← 点击这里
│  └───────────────────────────────────┘ │
│                                         │
│  Results appear here ↓                  │
│  ┌───────────────────────────────────┐ │
│  │ Best model: train-003             │ │
│  │ Key findings: ...                 │ │
│  └───────────────────────────────────┘ │
│  ┌───────────────────────────────────┐ │
│  │ Comparison Table                  │ │
│  │ Job     Epochs  mAP50             │ │
│  │ train-3   10    0.850             │ │
│  │ train-2    5    0.620             │ │
│  │ train-1    1    0.320             │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 💡 使用技巧

### 技巧 1: 对比相同参数的不同 epochs
```
选择 3 个任务，都是 imgsz=640，但 epochs 分别是 1, 5, 10
→ 可以看出训练轮数的影响
```

### 技巧 2: 对比不同图片尺寸
```
选择 2 个任务，都是 epochs=5，但 imgsz 分别是 320, 640
→ 可以看出图片尺寸的影响
```

### 技巧 3: 快速找到最佳模型
```
选择多个实验，点击对比
→ 第一行就是最佳模型，直接用它的 best.pt
```

---

## 🐛 如果还是不行

如果按照上述步骤仍然无法选择：

1. **检查浏览器控制台**
   - 按 F12 打开开发者工具
   - 查看 Console 标签页是否有错误

2. **重启应用**
   ```bash
   # 终止当前运行 (Ctrl+C)
   # 重新启动
   python app.py
   ```

3. **检查代码版本**
   ```bash
   git log --oneline | head -3
   # 应该看到：
   # 4bfdb5b - M1: add completion report
   # 0c29283 - Task 1.3: add verification report
   # 698d087 - Task 1.3: add experiment comparison UI
   ```

4. **查看测试**
   ```bash
   python test_task_1_3.py
   # 应该显示：✅ ALL TESTS PASSED
   ```

---

## 📞 需要帮助？

如果你尝试了上述所有方法仍然无法使用：

1. 截图当前的 UI 界面
2. 说明你点击了什么，看到了什么
3. 我可以帮你诊断问题

记住：
- ✅ 一定要选中**至少 2 行**
- ✅ 选中的行会**高亮显示**
- ✅ 然后点击下方的 **Compare 按钮**

---

*祝你使用愉快！🎉*
