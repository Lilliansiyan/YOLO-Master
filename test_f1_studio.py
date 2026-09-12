#!/usr/bin/env python3
"""
Quick smoke test for F1 Studio components
"""
import os
import sys
from pathlib import Path

# Test database layer
print("Testing F1 Studio Database...")
from f1_studio_db import F1StudioDB

# Create test database
test_db = "test_f1_studio.db"
if Path(test_db).exists():
    os.remove(test_db)

db = F1StudioDB(test_db)
print("✓ Database initialized")

# Test saving a job
test_response = {
    "status": "ok",
    "summary": "Test job completed",
    "job": {
        "save_dir": "runs/agent/test-job"
    }
}

db.save_job("test-job-001", "yolo.train", test_response)
print("✓ Job saved")

# Test loading history
history = db.load_job_history()
assert len(history) == 1
assert history[0]["job_id"] == "test-job-001"
print("✓ Job history loaded")

# Test getting specific job
job = db.get_job("test-job-001")
assert job is not None
assert job["status"] == "ok"
print("✓ Job retrieved")

# Clean up
os.remove(test_db)
print("\n✅ All database tests passed!")

# Test task validation
print("\nTesting path validation...")
from f1_studio_tasks import validate_path

try:
    validate_path("models/yolo11n.pt")
    print("✓ Valid path accepted")
except ValueError as e:
    print(f"✗ Should accept valid path: {e}")
    sys.exit(1)

try:
    validate_path("../etc/passwd")
    print("✗ Should reject path traversal")
    sys.exit(1)
except ValueError:
    print("✓ Path traversal blocked")

try:
    validate_path("/etc/passwd")
    print("✗ Should reject absolute path")
    sys.exit(1)
except ValueError:
    print("✓ Absolute path blocked")

try:
    validate_path("unauthorized/path.pt")
    print("✗ Should reject non-whitelisted path")
    sys.exit(1)
except ValueError:
    print("✓ Non-whitelisted path blocked")

print("\n✅ All validation tests passed!")
print("\n" + "="*50)
print("F1 Studio components are ready!")
print("="*50)
