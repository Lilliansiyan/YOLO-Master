# F1 Studio P1: Async Task Queue

## 概述 Overview

F1 Studio P1 在 P0 的基础上增加了异步任务队列和任务控制功能。

F1 Studio P1 adds async task queue and task control features on top of P0.

## 新功能 New Features

### 1. 异步任务队列 Async Task Queue

**特性 Features:**
- 后台执行任务，UI 不阻塞 (Tasks run in background, UI doesn't block)
- 最多 2 个并发 worker (Up to 2 concurrent workers)
- 任务状态：queued → running → ok/failed/cancelled
- 线程安全的队列操作 (Thread-safe queue operations)

**使用 Usage:**
```python
# Enable async mode in UI
async_mode_checkbox = True  # ⚡ Async Mode enabled

# Tasks are queued immediately
job_id = queue.submit(skill="yolo.train", inputs={...}, params={...})
# Returns immediately with job_id, task runs in background
```

### 2. 任务取消 Task Cancellation

**特性 Features:**
- 取消正在运行或排队的任务 (Cancel running or queued tasks)
- 优雅关闭机制 (Graceful shutdown)
- 取消状态持久化 (Cancellation persisted to database)

**使用 Usage:**
```python
# In UI: Task Control section
Job ID: train-abc123
[🛑 Cancel Task]

# Programmatically
success = queue.cancel(job_id)
```

### 3. 进度监控基础设施 Progress Monitor Infrastructure

**状态 Status:** 基础设施已就绪，数据源待接入 (Infrastructure ready, data source not yet wired)

`ProgressMonitor` 类已实现并测试，支持读取 `progress.jsonl` 增量事件。但当前无任何代码向该文件写入数据——ultralytics 训练回调尚未接入——所以 `get_updates()` 在实际运行中始终返回空列表。

The `ProgressMonitor` class is implemented and tested, capable of reading incremental events from `progress.jsonl`. However, no production code currently writes to that file — the ultralytics training callback is not yet wired — so `get_updates()` always returns `[]` in real usage.

**接入方式 To enable (P2 work):**
```python
# Wire a ultralytics callback to write progress events:
def on_train_epoch_end(trainer):
    with open(progress_file, "a") as f:
        json.dump({"step": trainer.epoch, "message": f"epoch {trainer.epoch}"}, f)
        f.write("\n")
```

## 架构 Architecture

### 组件图 Component Diagram

```
┌─────────────┐
│ Gradio UI   │
└──────┬──────┘
       │ submit_task()
       ↓
┌──────────────────┐
│  TaskQueue       │ ← 异步队列 Async Queue
│  - max_workers:2 │
│  - task_queue    │
│  - active_tasks  │
└────┬─────┬───────┘
     │     │
     │     └─ worker threads (background execution)
     ↓
┌──────────────────┐
│  F1StudioDB      │ ← 持久化 Persistence
│  - jobs table    │
│  - statuses      │
└──────────────────┘
```

### 状态流转 State Transitions

```
[User submits] → queued → running → ok
                                   → failed
                                   → timeout
                                   → cancelled
```

## UI 变化 UI Changes

### P0 → P1 Comparison

**P0 (Synchronous):**
```
[Submit Train Task] → ⏳ Waiting... → ✅ Result shown immediately
```

**P1 (Async):**
```
☑️ ⚡ Async Mode (enabled)
[Submit Train Task] → 🔄 Task queued → Continue using UI
                                     → Refresh to see result
```

### New UI Elements

1. **Async Mode Toggle**
   - Location: Top of Task Submission section
   - Default: Enabled ✅
   - Effect: Queues task vs. blocks until complete

2. **Task Control Section**
   - Cancel Task button 🛑
   - Input: Job ID to cancel
   - Output: Cancellation status

3. **New Status Indicators**
   - 🔄 queued - Task waiting in queue
   - ⚙️ running - Task currently executing
   - 🛑 cancelled - Task was cancelled

## 代码示例 Code Examples

### 提交异步任务 Submit Async Task

```python
# In app.py
def handle_train_submit(self, model, data, epochs, imgsz, async_mode=True):
    if async_mode:
        # P1: Submit to queue
        job_id = self.task_queue.submit(
            skill="yolo.train",
            inputs={"model": model, "data": data},
            params={"epochs": epochs, "imgsz": imgsz},
            timeout=600
        )
        return f"🔄 Task {job_id} queued", self.load_task_history()
    else:
        # P0: Synchronous execution
        response = submit_train(model, data, epochs, imgsz)
        # ... handle response
```

### 取消任务 Cancel Task

```python
def handle_cancel_task(self, job_id):
    success = self.task_queue.cancel(job_id)
    if success:
        return f"🛑 Task {job_id} cancelled"
    else:
        return f"⚠️ Task {job_id} not found or already completed"
```

### 监控进度 Monitor Progress (P2)

```python
# NOTE: get_updates() returns [] until a progress writer is wired (see P2 roadmap)
progress_file = Path("runs/agent/yolo-train-xxx/progress.jsonl")
monitor = ProgressMonitor(progress_file)
updates = monitor.get_updates()  # currently always []
```

## 性能指标 Performance Metrics

| Metric | P0 (Sync) | P1 (Async) |
|--------|-----------|------------|
| Task submission latency | Blocks until done | Non-blocking, returns immediately |
| Concurrent tasks | 1 | 2 |
| UI responsiveness | Blocked | Responsive |
| Task cancellation | ❌ Not supported | ✅ Supported |

## 测试 Testing

### 运行 P1 测试 Run P1 Tests

```bash
python test_f1_studio_p1.py
```

### 测试覆盖 Test Coverage

- ✅ Async queue submission
- ✅ Task status tracking
- ✅ Task cancellation
- ✅ Progress file monitoring
- ✅ Database with P1 statuses

## 限制 Limitations

### P1 范围内 Within P1 Scope

- 最多 2 个并发 worker (Max 2 concurrent workers)
- 取消请求不保证立即生效 (Cancellation not immediate)
- 进度监控需手动轮询 (Progress requires manual polling)

### 不在 P1 范围 Not in P1 Scope

- 批量推理 (Batch inference) → P2
- 产物预览 (Artifact preview) → P2
- 实时进度流 WebSocket (Real-time progress via WebSocket) → P2
- 优先级队列 (Priority queue) → P2

## 迁移指南 Migration Guide

### From P0 to P1

**数据库兼容 Database Compatibility:**
- P1 数据库向后兼容 P0 (P1 database is backward compatible with P0)
- 新增状态：queued, running, cancelled (New statuses: queued, running, cancelled)
- 旧记录仍可查看 (Old records still viewable)

**UI 兼容 UI Compatibility:**
- 异步模式默认开启 (Async mode enabled by default)
- 可关闭异步模式回退到 P0 行为 (Can disable async mode to revert to P0 behavior)

**代码变更 Code Changes:**
```python
# P0
response = submit_train(...)
# Blocks until complete

# P1
job_id = queue.submit(...)
# Returns immediately
```

## 故障排查 Troubleshooting

### 任务卡在 queued 状态 Task Stuck in Queued

**原因 Cause:**
- 所有 worker 都在忙 (All workers busy — queue is unbounded, never "full")

**解决 Solution:**
- 等待当前任务完成 (Wait for current tasks)
- 取消不需要的任务 (Cancel unwanted tasks)
- 增加 max_workers (Increase max_workers in code)

### 取消任务不生效 Cancel Not Working

**原因 Cause:**
- 任务已经完成 (Task already completed)
- Job ID 错误 (Wrong job ID)

**解决 Solution:**
- 检查任务状态 (Check task status in history)
- 复制正确的 Job ID (Copy correct Job ID from history)

### Worker 线程崩溃 Worker Thread Crashed

**症状 Symptoms:**
- 任务永远停在 running (Tasks stuck in running forever)
- 新任务不执行 (New tasks not executing)

**解决 Solution:**
```bash
# Restart the app
python app.py
```

## 下一步 Next Steps

### P2 计划 P2 Roadmap

1. **批量推理 Batch Inference**
   - 一次提交多个图片/视频 (Submit multiple images/videos at once)
   - 并行处理 (Parallel processing)

2. **产物预览 Artifact Preview**
   - 在线查看图片/图表 (View images/charts online)
   - 结果可视化 (Result visualization)

3. **实时进度 Real-time Progress**
   - WebSocket 推送 (WebSocket push)
   - 无需刷新页面 (No page refresh needed)

4. **高级队列 Advanced Queue**
   - 优先级队列 (Priority queue)
   - 任务依赖 (Task dependencies)
   - 资源限制 (Resource limits)

---

**版本信息 Version:**
- F1 Studio P1
- 实施时间 Implementation: 2026-09-01
- 基于 Based on: F1 Studio P0
