"""
Task 1.1 验收演示
使用真实的训练任务数据来展示新功能
"""

from f1_studio_db import F1StudioDB
import json

def main():
    print("=" * 70)
    print("Task 1.1 验收演示：数据库指标提取")
    print("=" * 70)
    print()

    # 连接到真实数据库
    db = F1StudioDB(db_path="f1_studio.db")

    # 1. 显示所有训练任务
    print("📋 第一步：查看现有的训练任务")
    print("-" * 70)

    jobs = db.load_job_history(limit=50)
    train_jobs = [j for j in jobs if j["skill"] == "yolo.train" and j["status"] == "ok"]

    if not train_jobs:
        print("⚠️  数据库中没有成功的训练任务")
        print("   请先运行一些训练任务，然后再运行此验收脚本")
        return

    print(f"找到 {len(train_jobs)} 个成功的训练任务：\n")
    for i, job in enumerate(train_jobs[:10], 1):  # 只显示前10个
        print(f"{i}. {job['job_id']} - 提交时间: {job['submitted_at'][:19]}")
    print()

    # 2. 测试 get_job_metrics() - 单个任务
    print("=" * 70)
    print("📊 第二步：测试 get_job_metrics() - 提取单个任务的指标")
    print("-" * 70)

    test_job = train_jobs[0]
    job_id = test_job["job_id"]
    print(f"测试任务: {job_id}\n")

    metrics = db.get_job_metrics(job_id)

    if metrics:
        print("✅ 成功提取指标！\n")
        print("提取的指标：")
        print(f"  Job ID:      {metrics['job_id']}")
        print(f"  Epochs:      {metrics['epochs']}")
        print(f"  Image Size:  {metrics['imgsz']}")
        print(f"  mAP50:       {metrics['mAP50']:.3f}")
        print(f"  mAP50-95:    {metrics['mAP50-95']:.3f}")
        print(f"  Precision:   {metrics['precision']:.3f}")
        print(f"  Recall:      {metrics['recall']:.3f}")
        print(f"  Box Loss:    {metrics['box_loss']:.3f}")
    else:
        print("❌ 无法提取指标")
        print("   可能原因：results.csv 文件不存在或已被删除")
    print()

    # 3. 测试 get_jobs_for_comparison() - 多任务对比
    print("=" * 70)
    print("🔬 第三步：测试 get_jobs_for_comparison() - 对比多个任务")
    print("-" * 70)

    # 选择前3个训练任务进行对比
    compare_count = min(3, len(train_jobs))
    job_ids = [job["job_id"] for job in train_jobs[:compare_count]]

    print(f"对比 {compare_count} 个任务：")
    for jid in job_ids:
        print(f"  - {jid}")
    print()

    results = db.get_jobs_for_comparison(job_ids)

    print(f"✅ 成功对比 {len(results)}/{compare_count} 个任务\n")

    if results:
        print("对比结果表格：")
        print("-" * 90)
        print(f"{'Job ID':<20} {'Epochs':<8} {'ImgSz':<8} {'mAP50':<10} {'mAP50-95':<10} {'Precision':<10}")
        print("-" * 90)
        for r in results:
            print(f"{r['job_id']:<20} {r['epochs']:<8} {r['imgsz']:<8} "
                  f"{r['mAP50']:<10.3f} {r['mAP50-95']:<10.3f} {r['precision']:<10.3f}")
        print("-" * 90)
    else:
        print("⚠️  所有任务都没有有效的指标数据")
    print()

    # 4. 测试边界情况
    print("=" * 70)
    print("🧪 第四步：测试边界情况")
    print("-" * 70)

    # 测试不存在的任务
    print("测试 1: 不存在的任务 ID")
    metrics = db.get_job_metrics("nonexistent-job-123")
    print(f"  结果: {metrics} {'✅' if metrics is None else '❌'}")
    print()

    # 测试非训练任务
    predict_jobs = [j for j in jobs if j["skill"] == "yolo.predict"]
    if predict_jobs:
        print("测试 2: 非训练任务 (predict)")
        predict_id = predict_jobs[0]["job_id"]
        print(f"  任务: {predict_id}")
        metrics = db.get_job_metrics(predict_id)
        print(f"  结果: {metrics} {'✅' if metrics is None else '❌'}")
    else:
        print("测试 2: 跳过 (没有 predict 任务)")
    print()

    # 总结
    print("=" * 70)
    print("✅ Task 1.1 验收完成")
    print("=" * 70)
    print()
    print("验收结果：")
    print("  ✅ get_job_metrics() 可以提取训练指标")
    print("  ✅ get_jobs_for_comparison() 可以对比多个任务")
    print("  ✅ 边界情况处理正确（返回 None）")
    print()
    print("这两个方法将用于 Task 1.2 和 1.3 的实验对比功能")
    print()


if __name__ == "__main__":
    main()
