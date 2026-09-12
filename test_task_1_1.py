"""
Test for Task 1.1: Database Layer - Metrics Extraction
Tests the get_job_metrics() and get_jobs_for_comparison() methods
"""

from pathlib import Path
import tempfile
import shutil
from f1_studio_db import F1StudioDB


def create_mock_results_csv(save_dir: Path):
    """Create a mock results.csv file for testing."""
    csv_content = """epoch,train/box_loss,train/cls_loss,train/dfl_loss,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0,lr/pg1,lr/pg2
0,1.2345,0.5678,1.1234,0.456,0.567,0.678,0.345,1.234,0.567,1.123,0.01,0.01,0.01
1,1.1234,0.4567,1.0123,0.567,0.678,0.789,0.456,1.123,0.456,1.012,0.009,0.009,0.009
2,1.0123,0.3456,0.9012,0.678,0.789,0.890,0.567,1.012,0.345,0.901,0.008,0.008,0.008"""

    results_csv = save_dir / "results.csv"
    results_csv.write_text(csv_content)


def test_get_job_metrics():
    """Test extracting metrics from a training job."""
    print("=" * 60)
    print("TEST: get_job_metrics()")
    print("=" * 60)

    # Create temporary database file
    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))

    # Create temporary save directory with mock results.csv
    temp_dir = Path(tempfile.mkdtemp())
    try:
        save_dir = temp_dir / "train-test-001"
        save_dir.mkdir()
        create_mock_results_csv(save_dir)

        # Save a mock training job
        job_id = "train-test-001"
        response = {
            "status": "ok",
            "job": {
                "save_dir": str(save_dir),
                "imgsz": 640,
                "epochs": 3
            },
            "summary": "Training complete"
        }
        db.save_job(job_id, "yolo.train", response)

        # Extract metrics
        metrics = db.get_job_metrics(job_id)

        # Verify
        assert metrics is not None, "Metrics should not be None for valid training job"
        assert metrics["job_id"] == job_id
        assert metrics["epochs"] == 3, f"Expected epochs=3, got {metrics['epochs']}"
        assert metrics["imgsz"] == 640, f"Expected imgsz=640, got {metrics['imgsz']}"
        assert metrics["mAP50"] == 0.890, f"Expected mAP50=0.890, got {metrics['mAP50']}"
        assert metrics["mAP50-95"] == 0.567, f"Expected mAP50-95=0.567, got {metrics['mAP50-95']}"
        assert metrics["precision"] == 0.678
        assert metrics["recall"] == 0.789
        assert metrics["box_loss"] == 1.012

        print("✅ Successfully extracted metrics from training job")
        print(f"   Metrics: {metrics}")

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


def test_get_job_metrics_missing_csv():
    """Test that get_job_metrics returns None when results.csv is missing."""
    print("\n" + "=" * 60)
    print("TEST: get_job_metrics() with missing results.csv")
    print("=" * 60)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))

    # Create temporary save directory WITHOUT results.csv
    temp_dir = Path(tempfile.mkdtemp())
    try:
        save_dir = temp_dir / "train-test-002"
        save_dir.mkdir()

        # Save a mock training job
        job_id = "train-test-002"
        response = {
            "status": "ok",
            "job": {
                "save_dir": str(save_dir),
                "imgsz": 640,
                "epochs": 3
            }
        }
        db.save_job(job_id, "yolo.train", response)

        # Try to extract metrics
        metrics = db.get_job_metrics(job_id)

        # Verify
        assert metrics is None, "Metrics should be None when results.csv is missing"
        print("✅ Correctly returns None for missing results.csv")

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


def test_get_job_metrics_non_training_job():
    """Test that get_job_metrics returns None for non-training jobs."""
    print("\n" + "=" * 60)
    print("TEST: get_job_metrics() with non-training job")
    print("=" * 60)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))

    try:
        # Save a predict job
        job_id = "predict-test-001"
        response = {
            "status": "ok",
            "job": {
                "save_dir": "/some/path"
            }
        }
        db.save_job(job_id, "yolo.predict", response)

        # Try to extract metrics
        metrics = db.get_job_metrics(job_id)

        # Verify
        assert metrics is None, "Metrics should be None for non-training jobs"
        print("✅ Correctly returns None for predict job")

    finally:
        if temp_db.exists():
            temp_db.unlink()


def test_get_jobs_for_comparison():
    """Test comparing multiple jobs."""
    print("\n" + "=" * 60)
    print("TEST: get_jobs_for_comparison()")
    print("=" * 60)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))

    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Create 3 training jobs with different metrics
        jobs = [
            ("train-compare-001", 32, 1),
            ("train-compare-002", 32, 2),
            ("train-compare-003", 64, 2),
        ]

        for job_id, imgsz, epochs in jobs:
            save_dir = temp_dir / job_id
            save_dir.mkdir()
            create_mock_results_csv(save_dir)

            response = {
                "status": "ok",
                "job": {
                    "save_dir": str(save_dir),
                    "imgsz": imgsz,
                    "epochs": epochs
                }
            }
            db.save_job(job_id, "yolo.train", response)

        # Also add a predict job (should be filtered out)
        db.save_job("predict-001", "yolo.predict", {"status": "ok"})

        # Get comparison
        job_ids = ["train-compare-001", "train-compare-002", "train-compare-003", "predict-001"]
        results = db.get_jobs_for_comparison(job_ids)

        # Verify
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        assert all("job_id" in r for r in results), "All results should have job_id"
        assert all("mAP50" in r for r in results), "All results should have mAP50"

        print(f"✅ Successfully compared {len(results)} training jobs")
        for r in results:
            print(f"   {r['job_id']}: epochs={r['epochs']}, imgsz={r['imgsz']}, mAP50={r['mAP50']}")

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


def test_malformed_csv():
    """Test that malformed CSV doesn't crash."""
    print("\n" + "=" * 60)
    print("TEST: get_job_metrics() with malformed CSV")
    print("=" * 60)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))

    temp_dir = Path(tempfile.mkdtemp())
    try:
        save_dir = temp_dir / "train-test-003"
        save_dir.mkdir()

        # Create empty CSV (will cause pandas to fail or return empty dataframe)
        results_csv = save_dir / "results.csv"
        results_csv.write_text("")

        job_id = "train-test-003"
        response = {
            "status": "ok",
            "job": {
                "save_dir": str(save_dir),
                "imgsz": 640,
                "epochs": 3
            }
        }
        db.save_job(job_id, "yolo.train", response)

        # Try to extract metrics
        metrics = db.get_job_metrics(job_id)

        # Verify
        assert metrics is None, "Metrics should be None for empty CSV"
        print("✅ Correctly handles empty CSV without crashing")

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


if __name__ == "__main__":
    try:
        test_get_job_metrics()
        test_get_job_metrics_missing_csv()
        test_get_job_metrics_non_training_job()
        test_get_jobs_for_comparison()
        test_malformed_csv()

        print("\n" + "=" * 60)
        print("✅ ALL TASK 1.1 TESTS PASSED")
        print("=" * 60)
        print("\nAcceptance Criteria Met:")
        print("✅ Can extract metrics from training jobs")
        print("✅ Returns None for jobs without results.csv")
        print("✅ Doesn't crash on missing/malformed files")
        print("✅ Filters out non-training jobs in comparison")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
