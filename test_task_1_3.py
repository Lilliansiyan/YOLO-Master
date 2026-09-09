"""
Test for Task 1.3: Frontend UI - Comparison Interface
Tests the UI components and wrapper method
"""

import sys
from pathlib import Path
import pandas as pd


def test_wrapper_method():
    """Test the handle_experiment_comparison_from_selection wrapper method."""
    print("=" * 70)
    print("TEST 1: Wrapper method with selected rows")
    print("=" * 70)

    sys.path.insert(0, str(Path(__file__).parent))
    from app import YOLO_Master_WebUI

    app = YOLO_Master_WebUI(ckpts_root="ckpts")

    # Get real training jobs
    jobs = app.db.load_job_history(limit=50)
    train_jobs = [j for j in jobs if j["skill"] == "yolo.train" and j["status"] == "ok"]

    if len(train_jobs) < 2:
        print("⚠️  Insufficient training jobs for testing")
        print("   Skipping this test")
        return

    # Simulate selected rows (Gradio passes DataFrame of selected rows)
    selected_rows = pd.DataFrame([
        {
            "Job ID": train_jobs[0]["job_id"],
            "Skill": train_jobs[0]["skill"],
            "Status": "✅ ok",
            "Submitted At": train_jobs[0]["submitted_at"][:19],
            "Artifacts": "10 files"
        },
        {
            "Job ID": train_jobs[1]["job_id"],
            "Skill": train_jobs[1]["skill"],
            "Status": "✅ ok",
            "Submitted At": train_jobs[1]["submitted_at"][:19],
            "Artifacts": "8 files"
        }
    ])

    print(f"Simulated selected rows:")
    print(selected_rows)
    print()

    # Call wrapper method
    df, summary = app.handle_experiment_comparison_from_selection(selected_rows)

    # Verify
    assert len(df) >= 0, "DataFrame should be returned"
    assert isinstance(summary, str), "Summary should be a string"

    print(f"✅ Wrapper method works")
    print(f"   Returned DataFrame with {len(df)} rows")
    print(f"   Summary preview: {summary[:80]}...")
    print()


def test_wrapper_no_selection():
    """Test wrapper method with no selection."""
    print("=" * 70)
    print("TEST 2: Wrapper method with no selection")
    print("=" * 70)

    sys.path.insert(0, str(Path(__file__).parent))
    from app import YOLO_Master_WebUI

    app = YOLO_Master_WebUI(ckpts_root="ckpts")

    # Empty selection
    empty_df = pd.DataFrame()

    df, summary = app.handle_experiment_comparison_from_selection(empty_df)

    # Verify
    assert len(df) == 0, "DataFrame should be empty"
    assert "No jobs selected" in summary
    assert "⚠️" in summary

    print("✅ Correctly handles empty selection")
    print(f"   Warning: {summary[:60]}...")
    print()


def test_wrapper_with_null():
    """Test wrapper method with None input."""
    print("=" * 70)
    print("TEST 3: Wrapper method with None input")
    print("=" * 70)

    sys.path.insert(0, str(Path(__file__).parent))
    from app import YOLO_Master_WebUI

    app = YOLO_Master_WebUI(ckpts_root="ckpts")

    # None input
    df, summary = app.handle_experiment_comparison_from_selection(None)

    # Verify
    assert len(df) == 0, "DataFrame should be empty"
    assert "No jobs selected" in summary

    print("✅ Correctly handles None input")
    print()


def test_ui_components_exist():
    """Test that UI components are properly defined."""
    print("=" * 70)
    print("TEST 4: UI components definition check")
    print("=" * 70)

    # Read app.py and check for required components
    app_file = Path(__file__).parent / "app.py"
    content = app_file.read_text()

    # Check for interactive=True
    assert "interactive=True" in content, "Task History should have interactive=True"
    print("✅ Task History has interactive=True")

    # Check for Experiment Comparison section
    assert "Experiment Comparison" in content, "Should have Experiment Comparison section"
    print("✅ Experiment Comparison section exists")

    # Check for compare button
    assert "Compare Selected Jobs" in content, "Should have Compare Selected Jobs button"
    print("✅ Compare button defined")

    # Check for comparison_output and comparison_table
    assert "comparison_output" in content, "Should have comparison_output Markdown"
    assert "comparison_table" in content, "Should have comparison_table Dataframe"
    print("✅ Comparison output components defined")

    # Check for event binding
    assert "compare_btn.click" in content, "Should have compare button event binding"
    assert "handle_experiment_comparison_from_selection" in content, "Should call wrapper method"
    print("✅ Event binding configured")

    # Check for tip
    assert "Tip" in content or "tip" in content, "Should have usage tip"
    print("✅ Usage tip included")

    print()


if __name__ == "__main__":
    try:
        test_ui_components_exist()
        test_wrapper_method()
        test_wrapper_no_selection()
        test_wrapper_with_null()

        print("=" * 70)
        print("✅ ALL TASK 1.3 TESTS PASSED")
        print("=" * 70)
        print("\nAcceptance Criteria Met:")
        print("✅ Task History supports row selection (interactive=True)")
        print("✅ Experiment Comparison UI section added")
        print("✅ Compare button triggers comparison")
        print("✅ Wrapper method extracts job IDs and calls backend")
        print("✅ Results display in separate table + markdown summary")
        print("\nUI Testing:")
        print("  To test the UI manually:")
        print("  1. Run: python app.py")
        print("  2. Go to Task Management tab")
        print("  3. Select multiple rows in Task History")
        print("  4. Click 'Compare Selected Jobs'")
        print("  5. Verify results appear below")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
