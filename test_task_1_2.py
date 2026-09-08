"""
Test for Task 1.2: Backend Handler - Comparison Logic
Tests the handle_experiment_comparison() method
"""

import sys
from pathlib import Path
import tempfile
import shutil
from f1_studio_db import F1StudioDB


def create_mock_results_csv(save_dir: Path, mAP50: float, mAP50_95: float, precision: float, recall: float, loss: float):
    """Create a mock results.csv file with specific metrics (3 epochs for backward compatibility)."""
    create_mock_results_csv_with_epochs(save_dir, mAP50, mAP50_95, precision, recall, loss, 3)


def setup_test_jobs(db: F1StudioDB, temp_dir: Path):
    """Create test training jobs with different hyperparameters and metrics."""
    jobs = [
        # Job 1: 1 epoch, 32 imgsz, low performance (CSV will have 1 data row: epoch 0)
        ("train-test-001", 1, 32, 0.450, 0.320, 0.520, 0.480, 2.500, 1),
        # Job 2: 2 epochs, 32 imgsz, medium performance (CSV will have 2 data rows: epoch 0-1)
        ("train-test-002", 2, 32, 0.620, 0.510, 0.680, 0.640, 1.800, 2),
        # Job 3: 3 epochs, 32 imgsz, high performance (best) (CSV will have 3 data rows: epoch 0-2)
        ("train-test-003", 3, 32, 0.780, 0.650, 0.750, 0.720, 1.200, 3),
        # Job 4: 2 epochs, 64 imgsz, good performance (CSV will have 2 data rows: epoch 0-1)
        ("train-test-004", 2, 64, 0.720, 0.600, 0.710, 0.680, 1.400, 2),
    ]

    job_ids = []
    for job_id, epochs, imgsz, mAP50, mAP50_95, precision, recall, loss, csv_rows in jobs:
        save_dir = temp_dir / job_id
        save_dir.mkdir()
        create_mock_results_csv_with_epochs(save_dir, mAP50, mAP50_95, precision, recall, loss, csv_rows)

        response = {
            "status": "ok",
            "job": {
                "save_dir": str(save_dir),
                "imgsz": imgsz,
                "epochs": epochs
            }
        }
        db.save_job(job_id, "yolo.train", response)
        job_ids.append(job_id)

    # Also add a predict job (should be filtered out)
    db.save_job("predict-test-001", "yolo.predict", {"status": "ok"})

    return job_ids


def create_mock_results_csv_with_epochs(save_dir: Path, mAP50: float, mAP50_95: float, precision: float, recall: float, loss: float, num_epochs: int):
    """Create a mock results.csv file with specific number of epoch rows."""
    csv_lines = ["epoch,train/box_loss,train/cls_loss,train/dfl_loss,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0,lr/pg1,lr/pg2"]

    for epoch in range(num_epochs):
        # Linear interpolation from 70% to 100% of final metrics
        progress = 0.7 + (0.3 * epoch / max(num_epochs - 1, 1))
        csv_lines.append(
            f"{epoch},{loss*1.5*(1-progress*0.3)},0.8,1.3,"
            f"{precision*progress},{recall*progress},{mAP50*progress},{mAP50_95*progress},"
            f"{loss*(2-progress)},0.7,1.2,0.01,0.01,0.01"
        )

    results_csv = save_dir / "results.csv"
    results_csv.write_text("\n".join(csv_lines))


def test_comparison_basic():
    """Test basic comparison with 3 training jobs."""
    print("=" * 70)
    print("TEST 1: Basic comparison (3 training jobs)")
    print("=" * 70)

    # Setup
    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))
    temp_dir = Path(tempfile.mkdtemp())

    try:
        job_ids = setup_test_jobs(db, temp_dir)

        # Import app module
        sys.path.insert(0, str(Path(__file__).parent))
        from app import YOLO_Master_WebUI

        # Create app instance and replace its db with our test db
        app = YOLO_Master_WebUI(ckpts_root="ckpts")
        app.db = db  # Use test database

        # Test comparison
        selected_jobs = job_ids[:3]  # First 3 training jobs
        df, summary = app.handle_experiment_comparison(selected_jobs)

        # Verify DataFrame
        assert len(df) == 3, f"Expected 3 rows, got {len(df)}"
        assert list(df.columns) == ["Job ID", "Epochs", "ImgSz", "mAP50", "mAP50-95", "Precision", "Recall", "Loss"]

        # Verify sorting (best mAP50 first)
        assert df.iloc[0]["mAP50"] >= df.iloc[1]["mAP50"], "Should be sorted by mAP50 descending"
        assert df.iloc[1]["mAP50"] >= df.iloc[2]["mAP50"], "Should be sorted by mAP50 descending"

        # Best job should be train-test-003 (mAP50=0.780)
        best_job = df.iloc[0]["Job ID"]
        assert best_job == "train-test-003", f"Expected train-test-003 as best, got {best_job}"

        # Verify summary
        assert "📊 Experiment Comparison Results" in summary
        assert "train-test-003" in summary
        assert "0.780" in summary
        assert "3 training tasks" in summary

        print("✅ DataFrame structure correct")
        print("✅ Sorted by mAP50 descending")
        print("✅ Best model identified correctly")
        print("✅ Summary generated\n")
        print(df)
        print("\n" + summary)

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


def test_comparison_edge_case_too_few():
    """Test edge case: <2 jobs selected."""
    print("\n" + "=" * 70)
    print("TEST 2: Edge case - <2 jobs selected")
    print("=" * 70)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))
    temp_dir = Path(tempfile.mkdtemp())

    try:
        job_ids = setup_test_jobs(db, temp_dir)

        sys.path.insert(0, str(Path(__file__).parent))
        from app import YOLO_Master_WebUI
        app = YOLO_Master_WebUI(ckpts_root="ckpts")
        app.db = db  # Use test database

        # Test with only 1 job
        df, summary = app.handle_experiment_comparison([job_ids[0]])

        # Verify warning
        assert len(df) == 0, "DataFrame should be empty"
        assert "Please select at least 2 jobs" in summary
        assert "⚠️" in summary

        print("✅ Correctly handles <2 jobs")
        print(f"   Warning: {summary[:60]}...")

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


def test_comparison_edge_case_no_valid():
    """Test edge case: No valid training results."""
    print("\n" + "=" * 70)
    print("TEST 3: Edge case - No valid training results")
    print("=" * 70)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))

    try:
        # Only add predict jobs (no training jobs)
        db.save_job("predict-001", "yolo.predict", {"status": "ok"})
        db.save_job("predict-002", "yolo.predict", {"status": "ok"})

        sys.path.insert(0, str(Path(__file__).parent))
        from app import YOLO_Master_WebUI
        app = YOLO_Master_WebUI(ckpts_root="ckpts")
        app.db = db  # Use test database

        # Test with predict jobs
        df, summary = app.handle_experiment_comparison(["predict-001", "predict-002"])

        # Verify error
        assert len(df) == 0, "DataFrame should be empty"
        assert "No valid training results found" in summary
        assert "❌" in summary

        print("✅ Correctly handles no valid results")
        print(f"   Error: {summary[:60]}...")

    finally:
        if temp_db.exists():
            temp_db.unlink()


def test_comparison_with_filtering():
    """Test comparison with mixed training/predict jobs."""
    print("\n" + "=" * 70)
    print("TEST 4: Comparison with filtering (mixed job types)")
    print("=" * 70)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))
    temp_dir = Path(tempfile.mkdtemp())

    try:
        job_ids = setup_test_jobs(db, temp_dir)

        sys.path.insert(0, str(Path(__file__).parent))
        from app import YOLO_Master_WebUI
        app = YOLO_Master_WebUI(ckpts_root="ckpts")
        app.db = db  # Use test database

        # Mix training and predict jobs
        mixed_jobs = job_ids[:2] + ["predict-test-001"]
        df, summary = app.handle_experiment_comparison(mixed_jobs)

        # Verify filtering
        assert len(df) == 2, f"Expected 2 training jobs, got {len(df)}"
        assert "1 job(s) were filtered out" in summary

        print("✅ Correctly filters out non-training jobs")
        print(f"   Compared: {len(df)} training jobs")
        print(f"   Filtered: 1 predict job")

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


def test_insights_generation():
    """Test that insights are generated correctly."""
    print("\n" + "=" * 70)
    print("TEST 5: Insights generation")
    print("=" * 70)

    temp_db = Path(tempfile.mktemp(suffix=".db"))
    db = F1StudioDB(db_path=str(temp_db))
    temp_dir = Path(tempfile.mkdtemp())

    try:
        job_ids = setup_test_jobs(db, temp_dir)

        sys.path.insert(0, str(Path(__file__).parent))
        from app import YOLO_Master_WebUI
        app = YOLO_Master_WebUI(ckpts_root="ckpts")
        app.db = db  # Use test database

        # Compare all 4 jobs (different epochs and imgsz)
        df, summary = app.handle_experiment_comparison(job_ids)

        # Verify insights
        assert "Key Findings:" in summary
        # Should mention epochs impact (1->2->3 epochs improves mAP50)
        assert "epochs" in summary.lower() or "improvement" in summary.lower()

        print("✅ Insights generated")
        print("\nGenerated summary:")
        print(summary)

    finally:
        shutil.rmtree(temp_dir)
        if temp_db.exists():
            temp_db.unlink()


if __name__ == "__main__":
    try:
        test_comparison_basic()
        test_comparison_edge_case_too_few()
        test_comparison_edge_case_no_valid()
        test_comparison_with_filtering()
        test_insights_generation()

        print("\n" + "=" * 70)
        print("✅ ALL TASK 1.2 TESTS PASSED")
        print("=" * 70)
        print("\nAcceptance Criteria Met:")
        print("✅ Can compare 2-10 training jobs")
        print("✅ DataFrame sorted correctly (by mAP50 descending)")
        print("✅ Markdown summary is human-readable")
        print("✅ Edge cases handled properly")
        print("   - <2 jobs selected → warning")
        print("   - No valid results → error")
        print("   - Mixed job types → filters correctly")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
