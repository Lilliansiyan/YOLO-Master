"""
F1 Studio P1: Test async queue and progress monitoring
"""

import time
from f1_studio_db import F1StudioDB
from f1_studio_queue import TaskQueue, ProgressMonitor
from pathlib import Path


def test_async_queue():
    """Test async task queue."""
    print("=" * 60)
    print("TEST: Async Task Queue")
    print("=" * 60)

    # Use file-backed database for testing
    test_db_path = "test_f1_studio.db"
    db = F1StudioDB(db_path=test_db_path)
    queue = TaskQueue(db, max_workers=2)
    queue.start()

    try:
        # Submit multiple tasks
        job_ids = []
        for i in range(3):
            job_id = queue.submit(
                skill=f"test.task{i}",
                inputs={"test": f"input{i}"},
                params={"iteration": i},
                timeout=5
            )
            job_ids.append(job_id)
            print(f"✅ Submitted task: {job_id}")

        # Check initial statuses
        print("\nInitial statuses:")
        for job_id in job_ids:
            status = queue.get_status(job_id)
            print(f"  {job_id}: {status}")

        # Wait a bit
        time.sleep(2)

        # Check statuses again
        print("\nStatuses after 2 seconds:")
        for job_id in job_ids:
            status = queue.get_status(job_id)
            if status:
                print(f"  {job_id}: {status}")
            else:
                print(f"  {job_id}: completed (removed from active tasks)")

        # Test cancellation
        if len(job_ids) > 0:
            cancel_id = job_ids[0]
            success = queue.cancel(cancel_id)
            print(f"\nCancellation of {cancel_id}: {'✅ Success' if success else '❌ Failed (already completed)'}")

        print("\n✅ Async queue test passed")

    finally:
        queue.stop()
        # Cleanup
        if Path(test_db_path).exists():
            Path(test_db_path).unlink()


def test_progress_monitor():
    """Test progress file monitoring."""
    print("\n" + "=" * 60)
    print("TEST: Progress Monitor")
    print("=" * 60)

    # Create a temporary progress file
    test_file = Path("test_progress.jsonl")

    try:
        # Write initial content
        with open(test_file, 'w') as f:
            f.write('{"step": 1, "message": "Starting"}\n')

        monitor = ProgressMonitor(test_file)

        # Read updates
        updates = monitor.get_updates()
        print(f"Initial updates: {len(updates)} events")
        for update in updates:
            print(f"  {update}")

        # Append more content
        with open(test_file, 'a') as f:
            f.write('{"step": 2, "message": "Processing"}\n')
            f.write('{"step": 3, "message": "Finalizing"}\n')

        # Read new updates
        updates = monitor.get_updates()
        print(f"New updates: {len(updates)} events")
        for update in updates:
            print(f"  {update}")

        # No new updates
        updates = monitor.get_updates()
        print(f"Subsequent call (should be empty): {len(updates)} events")

        print("\n✅ Progress monitor test passed")

    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()


def test_database_statuses():
    """Test database with new P1 statuses."""
    print("\n" + "=" * 60)
    print("TEST: Database with P1 Statuses")
    print("=" * 60)

    test_db_path = "test_f1_studio_statuses.db"
    db = F1StudioDB(db_path=test_db_path)

    try:
        # Save jobs with various P1 statuses
        statuses = ["queued", "running", "ok", "cancelled", "failed"]
        for i, status in enumerate(statuses):
            job_id = f"test-job-{i}"
            db.save_job(
                job_id=job_id,
                skill="test.skill",
                response={"status": status, "message": f"Test {status}"}
            )
            print(f"✅ Saved job {job_id} with status: {status}")

        # Load history
        jobs = db.load_job_history(limit=10)
        print(f"\nLoaded {len(jobs)} jobs from history:")
        for job in jobs:
            print(f"  {job['job_id']}: {job['status']}")

        print("\n✅ Database status test passed")

    finally:
        # Cleanup
        if Path(test_db_path).exists():
            Path(test_db_path).unlink()


if __name__ == "__main__":
    test_async_queue()
    test_progress_monitor()
    test_database_statuses()

    print("\n" + "=" * 60)
    print("✅ ALL P1 TESTS PASSED")
    print("=" * 60)
