#!/usr/bin/env python3
"""
F1 Studio P0 验收检查脚本
Verification script for F1 Studio P0 deliverables
"""
import os
import sys
from pathlib import Path

print("=" * 60)
print("F1 Studio P0 验收检查 / Acceptance Verification")
print("=" * 60)

# Check file existence
required_files = {
    "核心代码 / Core Code": [
        "app.py",
        "f1_studio_db.py",
        "f1_studio_tasks.py",
    ],
    "测试 / Tests": [
        "test_f1_studio.py",
    ],
    "文档 / Documentation": [
        "F1_STUDIO_README.md",
        "F1_STUDIO_P0_SUMMARY.md",
        "docs/F1_STUDIO_MANUAL.md",
    ],
    "Dispatcher": [
        "agent/scripts/run_yolo_master_skill.py",
    ]
}

all_ok = True

for category, files in required_files.items():
    print(f"\n{category}:")
    for file_path in files:
        exists = Path(file_path).exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path}")
        if not exists:
            all_ok = False

# Check database can be imported
print("\n模块导入 / Module Imports:")
try:
    from f1_studio_db import F1StudioDB
    print("  ✅ f1_studio_db.F1StudioDB")
except ImportError as e:
    print(f"  ❌ f1_studio_db.F1StudioDB: {e}")
    all_ok = False

try:
    from f1_studio_tasks import submit_train, submit_predict, submit_export, validate_path
    print("  ✅ f1_studio_tasks (all functions)")
except ImportError as e:
    print(f"  ❌ f1_studio_tasks: {e}")
    all_ok = False

# Check Python version
print("\n环境 / Environment:")
import sys
python_version = sys.version_info
print(f"  Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
if python_version >= (3, 8):
    print("  ✅ Python version >= 3.8")
else:
    print("  ❌ Python version < 3.8 (not supported)")
    all_ok = False

# Check if we're in the right directory
cwd = Path.cwd()
if (cwd / "app.py").exists() and (cwd / "agent").exists():
    print(f"  ✅ Working directory: {cwd.name}")
else:
    print(f"  ⚠️  Not in YOLO-Master root? CWD: {cwd}")

# Summary
print("\n" + "=" * 60)
if all_ok:
    print("✅ 所有检查通过 / All checks passed!")
    print("\n可以启动界面 / Ready to launch:")
    print("  python3 app.py")
    sys.exit(0)
else:
    print("❌ 部分检查失败 / Some checks failed")
    print("请检查缺失的文件或依赖 / Please check missing files or dependencies")
    sys.exit(1)
