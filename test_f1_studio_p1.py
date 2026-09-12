"""
F1 Studio P1: Test async queue and progress monitoring
"""

import time
from f1_studio_db import F1StudioDB
from f1_studio_queue import TaskQueue, ProgressMonitor
from pathlib import Path


def test_async_queue():
    """Test async task queue with real skill and assertions."""
    print("=" * 60)
    print("TEST: Async Task Queue")
    print("=" * 60)

    test_db_path = "test_f1_studio.db"
    db = F1StudioDB(db_path=test_db_path)
    queue = TaskQueue(db, max_workers=2)
    queue.start()

    try:
        job_ids = []
        for i in range(3):
            job_id = queue.submit(
                skill="yolo.system",
                inputs={},
                params={},
                timeout=60
            )
            job_ids.append(job_id)
            print(f"Submitted task: {job_id}")

        # Immediately after submit: each task must be queued or already running
        for job_id in job_ids:
            status = queue.get_status(job_id)
            assert status in ("queued", "running", None), \
                f"Expected queued/running after submit, got {status!r} for {job_id}"
        print("✅ Initial statuses valid (queued/running)")

        # Wait for all tasks to reach a terminal state
        deadline = time.time() + 60
        while time.time() < deadline:
            statuses = [queue.get_status(j) for j in job_ids]
            if all(s is None for s in statuses):
                break
            time.sleep(1)

        # All tasks must have a terminal DB status
        terminal = {"ok", "failed", "cancelled", "timeout"}
        for job_id in job_ids:
            job = db.get_job(job_id)
            assert job is not None, f"Job {job_id} not in DB"
            assert job["status"] in terminal, \
                f"Expected terminal status, got {job['status']!r} for {job_id}"
        print("✅ All tasks reached terminal status in DB")

        # Cancellation test: submit a new task and cancel it immediately
        cancel_id = queue.submit(skill="yolo.system", inputs={}, params={}, timeout=60)
        success = queue.cancel(cancel_id)
        assert success, f"cancel() returned False for {cancel_id}"

        # Wait briefly then check DB status
        time.sleep(1)
        job = db.get_job(cancel_id)
        assert job is not None, f"Cancelled job {cancel_id} not in DB"
        assert job["status"] == "cancelled", \
            f"Expected cancelled, got {job['status']!r} for {cancel_id}"
        print("✅ Cancelled task DB status == cancelled")

        print("\n✅ Async queue test passed")

    finally:
        queue.stop()
        if Path(test_db_path).exists():
            Path(test_db_path).unlink()


def test_progress_monitor():
    """Test progress file monitoring with assertions."""
    print("\n" + "=" * 60)
    print("TEST: Progress Monitor")
    print("=" * 60)

    test_file = Path("test_progress.jsonl")

    try:
        with open(test_file, 'w') as f:
            f.write('{"step": 1, "message": "Starting"}\n')

        monitor = ProgressMonitor(test_file)

        updates = monitor.get_updates()
        assert len(updates) == 1, f"Expected 1 event, got {len(updates)}"
        assert updates[0]["step"] == 1, f"Expected step 1, got {updates[0]}"
        print("✅ First read: 1 event, step==1")

        with open(test_file, 'a') as f:
            f.write('{"step": 2, "message": "Processing"}\n')
            f.write('{"step": 3, "message": "Finalizing"}\n')

        updates = monitor.get_updates()
        assert len(updates) == 2, f"Expected 2 new events, got {len(updates)}"
        assert updates[0]["step"] == 2
        assert updates[1]["step"] == 3
        print("✅ Second read: 2 new events, steps 2 and 3")

        updates = monitor.get_updates()
        assert len(updates) == 0, f"Expected 0 events on repeat read, got {len(updates)}"
        print("✅ Third read: 0 events (no new data)")

        print("\n✅ Progress monitor test passed")

    finally:
        if test_file.exists():
            test_file.unlink()


def test_database_statuses():
    """Test database with P1 statuses and submitted_at immutability."""
    print("\n" + "=" * 60)
    print("TEST: Database with P1 Statuses")
    print("=" * 60)

    test_db_path = "test_f1_studio_statuses.db"
    db = F1StudioDB(db_path=test_db_path)

    try:
        statuses = ["queued", "running", "ok", "cancelled", "failed"]
        for i, status in enumerate(statuses):
            job_id = f"test-job-{i}"
            db.save_job(
                job_id=job_id,
                skill="test.skill",
                response={"status": status, "message": f"Test {status}"}
            )

        jobs = db.load_job_history(limit=10)
        assert len(jobs) == 5, f"Expected 5 jobs, got {len(jobs)}"
        print("✅ Loaded 5 jobs from history")

        jobs_by_id = {j["job_id"]: j for j in jobs}
        for i, status in enumerate(statuses):
            job_id = f"test-job-{i}"
            assert jobs_by_id[job_id]["status"] == status, \
                f"Expected status {status!r}, got {jobs_by_id[job_id]['status']!r}"
            assert jobs_by_id[job_id]["submitted_at"], \
                f"submitted_at is empty for {job_id}"
        print("✅ All statuses match, submitted_at populated")

        # P1-1 fix: re-saving a job must not overwrite submitted_at
        first_submitted = jobs_by_id["test-job-0"]["submitted_at"]
        db.save_job("test-job-0", "test.skill", {"status": "running", "message": "updated"})
        updated_job = db.get_job("test-job-0")
        assert updated_job["submitted_at"] == first_submitted, \
            f"submitted_at changed on update: {first_submitted!r} → {updated_job['submitted_at']!r}"
        print("✅ submitted_at unchanged after re-save (P1-1 fix verified)")

        print("\n✅ Database status test passed")

    finally:
        if Path(test_db_path).exists():
            Path(test_db_path).unlink()


if __name__ == "__main__":
    try:
        test_async_queue()
        test_progress_monitor()
        test_database_statuses()

        print("\n" + "=" * 60)
        print("✅ ALL P1 TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
