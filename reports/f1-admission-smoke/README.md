# F1（YOLO-Master Studio）准入门禁证据包 — 孙思俨（Lilliansiyan）

- **志愿**：F1（YOLO-Master Studio，产品化/工程整合方向）
- **Baseline 锁定**：tag `YOLO-Master-v26.08`（commit `43d4011`）——**HEAD 已固定在该 commit，非 main/HEAD**
- **本地环境**：macOS + Apple Silicon（MPS），Python 3.13.9，`ultralytics==8.4.101`（本地可编辑安装，`local_repo_active: true`）
- **产出日期**：2026-08-25

## 1. 环境安装

```bash
python -m pip install -e . -i https://pypi.org/simple
yolo version   # -> 8.4.101
```

体检结果见 [`env_doctor.json`](./env_doctor.json)：CLI 可用、本地仓库正确挂载在 `43d4011`、设备自动选中 `mps`（CPU 兜底可用）。

## 2. Skill 接口层冒烟测试

```bash
python agent/scripts/validate_yolo_master_skill.py --suite quick --pretty --summary-only
```

结果见 [`skill_smoke_test_quick.json`](./skill_smoke_test_quick.json)：**36/36 用例通过（score 1.0）**，覆盖 train/val/predict/export/benchmark 的 dry-run 与协议契约校验。

## 3. 基线最小任务（复现命令）

```bash
python agent/scripts/run_yolo_master_skill.py --json '{"skill":"yolo.train","inputs":{"model":"yolo11n.pt","data":"coco8.yaml"},"params":{"epochs":1,"imgsz":32}}' --pretty
```

- 数据：官方内置 `coco8`（8 张图 mini 集，仅用于验证训练管线可跑通，不用于评估精度）
- 设备：自动选中 `mps`，`workers=0`（macOS 自动降级）
- 结果：`status: ok`，`summary: training finished`，单 epoch 耗时约 2.5s
- 完整配置：[`baseline_run/args.yaml`](./baseline_run/args.yaml)
- 训练曲线：[`baseline_run/results.csv`](./baseline_run/results.csv) / [`baseline_run/results.png`](./baseline_run/results.png)
- 完整 dispatcher 日志（含实际执行的 CLI 命令、stdout、产物清单）：[`baseline_run/train_dispatcher_full_log.json`](./baseline_run/train_dispatcher_full_log.json)
- 权重产物未入库（`.pt` 文件较大，仓库 `.gitignore` 也排除了 `runs/`），改用哈希留痕以保证可复现性核验：[`baseline_run/weights_meta/checksums.sha256`](./baseline_run/weights_meta/checksums.sha256)、[`baseline_run/weights_meta/sizes.txt`](./baseline_run/weights_meta/sizes.txt)

> `mAP50(B)=0` 属预期：4 张验证图、1 轮训练，本阶段目的仅为验证"训练管线端到端可跑通"，非精度评估。

## 4. 设计说明（草稿，待完善）

> ⚠️ 以下为初步理解，非最终设计，需在接口冻结（8.24）后与其他 F1 组员对齐后再定稿。

F1 Studio 的定位是在现有 `agent/` Skill 接口层（`run_yolo_master_skill.py` 分发器，已验证可用）之上，把 `app.py` 现有的单图推理 Demo 升级为训练/推理/部署一体化任务工作台。初步理解的六层架构：WebUI Shell / Request Gateway / Agent Dispatcher（复用现有 `agent/` 分发器）/ Async Jobs（复用 `policy.async` 异步任务机制）/ Evidence Stream / Artifact Registry。目前尚未进入具体页面/接口设计阶段。

## 5. 风险与降级（草稿，待完善）

- **基线漂移风险**：`43d4011` 与 `main` 是分叉的两条线，后续开发若不小心 `merge`/`rebase` 到 `main`，会引入未经门禁审核的变更——本分支往后所有操作都应基于 `43d4011`，不合并 `main`。
- **网络不稳定**：本机访问 GitHub / PyPI 曾出现连接超时（依赖本地代理是否在线），已验证的降级方案：pip 显式切换官方源（`-i https://pypi.org/simple`）、git 视代理状态切换直连或代理。
- **设备兼容性**：训练/推理默认 `device=mps`，dispatcher 已内置"MPS 失败自动回退 CPU 并返回完整重试记录"的机制，无需额外处理。
- **尚未验证项**：真实数据集规模下的训练任务、异步任务队列（`policy.async`）、导出/部署链路（ONNX/INT8/benchmark）目前仅在 dry-run 层面验证，未做真实执行，是下一步要补的证据。

## 复现方式一览

```bash
git clone https://github.com/Lilliansiyan/YOLO-Master.git
cd YOLO-Master
git checkout siyan/f1-admission-smoke
git log -1 --oneline   # 应落在 43d4011 之上
python -m pip install -e . -i https://pypi.org/simple
python agent/scripts/validate_yolo_master_skill.py --suite quick --pretty --summary-only
python agent/scripts/run_yolo_master_skill.py --json '{"skill":"yolo.train","inputs":{"model":"yolo11n.pt","data":"coco8.yaml"},"params":{"epochs":1,"imgsz":32}}' --pretty
```
