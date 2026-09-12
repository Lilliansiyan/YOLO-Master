"""Integration tests for F1 Studio FastAPI backend.

Unlike test_api.py (which mocks submit_task entirely), these tests patch
submit_task with a realistic side-effect that actually writes results to
the DB — exercising the full submit → background-task → poll lifecycle.

TestClient runs background tasks synchronously after each response, so
assertions on DB state can be made immediately after the POST returns.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def int_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for mod in ("api", "f1_studio_db", "f1_studio_tasks"):
        sys.modules.pop(mod, None)
    import api as api_module
    yield TestClient(api_module.app), api_module


def _make_completing_submit(extra_fields=None):
    """Return a submit_task side-effect that writes 'ok' to the DB."""
    def _submit(skill, inputs, params, timeout=600, job_id=None):
        from f1_studio_db import F1StudioDB
        result = {"status": "ok", "job_id": job_id, "skill": skill}
        if extra_fields:
            result.update(extra_fields)
        F1StudioDB().save_job(job_id, skill, result)
        return result
    return _submit


# ---------------------------------------------------------------------------
# Scenario 1: train submit → queued → background task completes → status ok
# ---------------------------------------------------------------------------

def test_integration_train_lifecycle(int_client):
    c, api_mod = int_client
    completing = _make_completing_submit({"save_dir": "runs/detect/train"})
    with patch.object(api_mod, "submit_task", side_effect=completing):
        resp = c.post("/api/tasks/train", json={
            "model": "yolo11n.pt", "data": "coco8.yaml",
            "epochs": 1, "imgsz": 32, "timeout": 60,
        })
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert resp.json()["status"] == "queued"

    # Background task ran synchronously — DB row should already be updated.
    resp = c.get(f"/api/tasks/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # response dict is stored as-is and returned under "response"
    assert body["response"]["save_dir"] == "runs/detect/train"


# ---------------------------------------------------------------------------
# Scenario 2: predict submit → background task completes with artifacts
# ---------------------------------------------------------------------------

def test_integration_predict_artifacts(int_client):
    c, api_mod = int_client
    artifact_paths = ["runs/detect/predict/bus.jpg"]
    completing = _make_completing_submit({"artifacts": artifact_paths})
    with patch.object(api_mod, "submit_task", side_effect=completing):
        resp = c.post("/api/tasks/predict", json={
            "model": "yolo11n.pt", "source": "bus.jpg",
            "conf": 0.25, "timeout": 60,
        })
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    resp = c.get(f"/api/tasks/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # artifact paths stored inside response dict; DB-level artifacts require real files on disk
    assert body["response"]["artifacts"] == artifact_paths


# ---------------------------------------------------------------------------
# Scenario 3: submit → cancel while still queued → 200 cancelled
# ---------------------------------------------------------------------------

def test_integration_cancel_queued_task(int_client):
    c, api_mod = int_client
    import f1_studio_tasks as tasks_mod

    # Simulate a long-running task: register a fake process so cancel_task
    # finds it in _running_processes, but don't update the DB row to "ok".
    fake_proc = MagicMock()
    fake_proc.pid = 99999  # non-existent PID → getpgid raises ProcessLookupError, caught by cancel_task

    def _slow_submit(skill, inputs, params, timeout=600, job_id=None):
        tasks_mod._running_processes[job_id] = fake_proc
        # Intentionally leave DB row at "queued" (submitted before this BG task ran)

    with patch.object(api_mod, "submit_task", side_effect=_slow_submit):
        resp = c.post("/api/tasks/train", json={
            "model": "yolo11n.pt", "data": "coco8.yaml",
            "epochs": 1, "imgsz": 32, "timeout": 600,
        })
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    resp = c.delete(f"/api/tasks/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Scenario 4: system-check → queued → completes → visible in task list
# ---------------------------------------------------------------------------

def test_integration_system_check_lifecycle(int_client):
    c, api_mod = int_client
    completing = _make_completing_submit()
    with patch.object(api_mod, "submit_task", side_effect=completing):
        resp = c.post("/api/tasks/system-check")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert job_id.startswith("syscheck-")

    resp = c.get(f"/api/tasks/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = c.get("/api/tasks")
    jobs = resp.json()["jobs"]
    assert any(j["job_id"] == job_id for j in jobs)
