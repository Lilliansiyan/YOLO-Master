# F1（YOLO-Master Studio）准入门禁证据包 —（Lilliansiyan）

## 结论

- **志愿**：F1（YOLO-Master Studio，产品化/工程整合方向）
- **状态**：`success`，train / predict / export 三个真实最小任务均完成，进程退出码 `0`
- **Baseline 锁定**：tag [`YOLO-Master-v26.08`](https://github.com/Tencent/YOLO-Master/releases/tag/YOLO-Master-v26.08)（commit [`43d4011`](https://github.com/Tencent/YOLO-Master/commit/43d4011)），HEAD 固定在该 commit，不基于 `main`；本机原始验证输出：
  ```
  $ git log -1 --oneline
  600a5ab F1准入证据：设计说明改为已验证Dispatcher契约图+六层现状对照表，去除纯展望性描述
  $ git merge-base --is-ancestor 43d4011 HEAD && echo "43d4011 is ancestor of HEAD: yes"
  43d4011 is ancestor of HEAD: yes
  ```
- **本地环境**：macOS + Apple Silicon（MPS），Python 3.13.9，`ultralytics==8.4.101`（本地可编辑安装，`local_repo_active: true`）
- **产出日期**：2026-08-26

## 准入材料索引

| 登记项 | 证据 |
| --- | --- |
| 环境安装 | [`env_doctor.json`](./env_doctor.json)、本页「1. 环境安装」 |
| 基线/最小任务 | 本页「3. 最小任务结果」、[`baseline_run/`](./baseline_run)、[`predict_run/`](./predict_run)、[`export_run/`](./export_run) |
| 复现命令 | 本页「2. 复现命令」 |
| 配置文件 | [`baseline_run/args.yaml`](./baseline_run/args.yaml) |
| 完整日志 | [`baseline_run/train_dispatcher_full_log.json`](./baseline_run/train_dispatcher_full_log.json)、[`predict_run/predict_dispatcher_full_log.json`](./predict_run/predict_dispatcher_full_log.json)、[`export_run/export_dispatcher_full_log.json`](./export_run/export_dispatcher_full_log.json)、[`skill_smoke_test_quick.json`](./skill_smoke_test_quick.json)、[`env_install_run/pip_download_interrupt_excerpt.log`](./env_install_run/pip_download_interrupt_excerpt.log) |
| 结果证据 | [`baseline_run/results.csv`](./baseline_run/results.csv)、[`baseline_run/results.png`](./baseline_run/results.png)、[`baseline_run/weights_meta/checksums.sha256`](./baseline_run/weights_meta/checksums.sha256)、[`predict_run/annotated_output.jpg`](./predict_run/annotated_output.jpg)、[`export_run/checksums.sha256`](./export_run/checksums.sha256) |
| 设计说明 | 本页「4. 设计说明」（已验证的 Dispatcher 契约 + 未定层现状对照） |
| 风险与降级 | 本页「5. 风险与降级」 |
| 代码/方案链接 | [`reports/f1-admission-smoke/`](https://github.com/Lilliansiyan/YOLO-Master/tree/siyan/f1-admission-smoke/reports/f1-admission-smoke) |

## 1. 环境安装

```bash
python -m pip install -e . -i https://pypi.org/simple
yolo version   # -> 8.4.101
```

体检结果见 [`env_doctor.json`](./env_doctor.json)：CLI 可用、本地仓库正确挂载在 `43d4011`、设备自动选中 `mps`（CPU 兜底可用）。

## 2. 复现命令

```bash
git clone https://github.com/Lilliansiyan/YOLO-Master.git
cd YOLO-Master
git checkout siyan/f1-admission-smoke
git log -1 --oneline   # 应落在 43d4011 之上
python -m pip install -e . -i https://pypi.org/simple

# Skill 接口层冒烟测试
python agent/scripts/validate_yolo_master_skill.py --suite quick --pretty --summary-only

# 环境体检（生成 env_doctor.json）
python agent/scripts/run_yolo_master_skill.py --json '{"skill":"yolo.system","action":"doctor","inputs":{},"params":{}}' --pretty

# 训练最小任务
python agent/scripts/run_yolo_master_skill.py --json '{"skill":"yolo.train","inputs":{"model":"yolo11n.pt","data":"coco8.yaml"},"params":{"epochs":1,"imgsz":32}}' --pretty

# 推理最小任务（用上一步产出的 best.pt，本次实际路径：runs/agent/yolo-train-6a3bce0f/weights/best.pt）
python agent/scripts/run_yolo_master_skill.py --json '{"skill":"yolo.predict","inputs":{"model":"runs/agent/yolo-train-6a3bce0f/weights/best.pt","source":"datasets/coco8/images/val/000000000036.jpg"}}' --pretty

# 导出最小任务（ONNX）
python agent/scripts/run_yolo_master_skill.py --json '{"skill":"yolo.export","inputs":{"model":"runs/agent/yolo-train-6a3bce0f/weights/best.pt"},"params":{"format":"onnx"}}' --pretty
```

## 3. 最小任务结果

| 环节 | 命令 | 状态 | 关键信息 |
| --- | --- | --- | --- |
| Skill 接口冒烟测试 | `validate_yolo_master_skill.py --suite quick` | `PASS` | 36/36 用例通过，score 1.0（[`skill_smoke_test_quick.json`](./skill_smoke_test_quick.json)） |
| 训练（train） | `yolo.train`，`coco8` 1 epoch | `ok` / training finished | 设备 `mps`，耗时约 2.5s，产出 `best.pt`/`last.pt`/`results.csv`/[`results.png`](./baseline_run/results.png)，权重哈希见 [`weights_meta/checksums.sha256`](./baseline_run/weights_meta/checksums.sha256) |
| 推理（predict） | `yolo.predict`，对训练产出的 `best.pt` 单图推理 | `ok` / predict finished | 输出标注图见 [`predict_run/annotated_output.jpg`](./predict_run/annotated_output.jpg) |
| 导出（export） | `yolo.export`，`best.pt` → ONNX | `ok` / export finished | 产出 `best.onnx`（约 10.1MB），哈希见 [`export_run/checksums.sha256`](./export_run/checksums.sha256) |

数据均为官方内置 `coco8`（8 张图 mini 集），目的是验证**训练→推理→导出全链路可端到端跑通**，不是精度评估。`mAP50(B)=0` 属预期：4 张验证图、1 轮训练，尚未形成有效检测精度，不能作为方案精度结论；完整 P0 阶段应在真实规模数据集上报告完整验证集指标。

## 4. 设计说明

> 六层架构的完整设计需在P0阶段实现过程中根据实际需求逐步明确；本节只画本次真实跑通、有日志为证的部分（Agent Dispatcher 层），其余五层按"已验证 / 待实现 / 未开始"如实标注，不在准入阶段超前设计尚未实际需要的接口细节。

### 4.1 已验证：Agent Dispatcher 请求/响应契约

`agent/scripts/run_yolo_master_skill.py` 分发器本次通过 train / predict / export 三个真实最小任务验证了同一套契约：固定的请求结构进、固定的响应结构出，中间转调 `yolo` CLI 并把结果收敛成结构化 JSON。三次运行的日志（见第 3 节）里 `skill` / `status` / `job.executor` / `job.device` / `environment.*` 等字段结构完全一致，只有 `skill` 类型和产出内容不同，这说明分发器层的接口是稳定的，可以作为 F1 Studio 上层（WebUI / Gateway）可以依赖的契约面。

```mermaid
flowchart LR
    A["请求方<br/>(本次=CLI 手动调用<br/>未来=F1 Request Gateway)"] -->|"{skill, args, policy}<br/>如 skill=yolo.train"| B["Agent Dispatcher<br/>run_yolo_master_skill.py"]
    B -->|"转调"| C["yolo CLI<br/>(train/predict/export)"]
    C -->|"stdout/产物路径"| B
    B -->|"结构化响应<br/>{status, summary, job, metrics/results,<br/>environment, artifacts}"| A
    B -.->|"device 请求失败时自动降级"| D["MPS → CPU 自动回退"]
    B --> E["Artifact Registry (待建)<br/>本次落地为 runs/agent/*<br/>+ 本报告 checksums"]
```

（字段名逐字取自本次实际日志：`baseline_run/train_dispatcher_full_log.json`、`predict_run/predict_dispatcher_full_log.json`、`export_run/export_dispatcher_full_log.json`，非杜撰示意。）

### 4.2 F1 六层现状对照

| 层 | 本次状态 | 说明 |
|---|---|---|
| Agent Dispatcher | ✅ 已验证 | 复用现有 `agent/` 分发器，train/predict/export 三次真实调用均 status=ok，见第 3 节 |
| Async Jobs | ⏳ 未开始 | 拟复用 `policy.async`，本次三个任务均为 sync 模式（`job.mode=sync`），异步队列未触发，见第 5 节"尚未验证项" |
| Request Gateway | 🔒 待实现 | P0阶段可简化为Gradio callback直接调用dispatcher，暂不需要独立的HTTP API层 |
| WebUI Shell | 🔒 待实现 | 基于现有app.py扩展，新增任务历史、状态查询、产物管理tab |
| Evidence Stream | 🔒 待实现 | P0阶段可通过轮询job状态实现，实时进度流作为P1优化项 |
| Artifact Registry | ⏳ 未开始 | 本次以 `runs/agent/*` 目录 + 本报告内 SHA-256 checksum 作为最小替代，尚无统一注册/索引机制 |

结论：本次证据证明的是"F1 Studio 最底层——现有 Skill 分发器——在训练/推理/导出全链路上是可信的地基"，其上四层的具体设计将在P0实现阶段根据实际需求逐步明确，不在准入阶段编造尚未验证的接口细节。

## 5. 风险与降级

| 风险 | 本次是否发生 | 应对/恢复 | 完整 P0 阶段建议 |
| --- | --- | --- | --- |
| 依赖下载中途超时 | **是**——`pip install` 下载 `polars_runtime_32`（48.6MB）时于 22.5MB 处超时中断 | pip 自动断点续传成功，切换官方源 `-i https://pypi.org/simple` 后全部装完；原始日志见 [`env_install_run/pip_download_interrupt_excerpt.log`](./env_install_run/pip_download_interrupt_excerpt.log) | 大依赖包预计仍会偶发超时，建议 CI/自动化环境固定使用官方源并允许 pip 自动重试，不额外处理 |
| 基线漂移 | 否，已提前核查 | `43d4011` 与 `main` 是分叉的两条线（`43d4011` 不是 `main` 祖先，分叉点后 `main` 又单独推进 62 个提交），本分支后续开发不合并 `main`，只在 `43d4011` 上继续 | 每次提交前用 `git merge-base --is-ancestor 43d4011 HEAD` 校验未偏离基线 |
| 设备兼容性 | 否 | dispatcher 已内置"MPS 训练/推理失败自动回退 CPU，并返回完整重试记录"的机制，本次三个任务均一次在 `mps` 上成功，未触发回退 | 无需额外处理，保留该机制即可 |
| 结果过度解读 | 需持续注意 | 本次训练/推理/导出均为 mini 规模冒烟验证，`mAP50=0` 等指标只证明链路通，不代表方案精度 | 完整 P0 报告需明确区分"链路验证"与"精度实验"，避免用 smoke 结果代替真实评估 |
| 尚未验证项 | — | 异步任务队列（`policy.async`）、真实规模数据集训练、INT8 量化导出、benchmark 目前仅 dry-run 层面验证，未真实执行 | 是下一步要补的证据，纳入下一轮迭代计划 |
