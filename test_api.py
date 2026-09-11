"""Tests for the F1 Studio FastAPI backend (api.py).

Uses FastAPI's TestClient against an isolated sqlite db (cwd chdir'd to a
tmp_path per test) so tests never touch the real f1_studio.db. submit_task
is mocked so tests exercise the endpoint/DB-write logic without actually
shelling out to the YOLO dispatcher.
"""
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Force a fresh import so F1StudioDB()'s default relative path resolves
    # against tmp_path instead of a module cached from a previous test/run.
    for mod in ("api", "f1_studio_db", "f1_studio_tasks"):
        sys.modules.pop(mod, None)
    import api as api_module

    with patch.object(api_module, "submit_task") as mock_submit:
        mock_submit.return_value = {"status": "ok", "job_id": "unused"}
        yield TestClient(api_module.app), mock_submit


def test_health(client):
    c, _ = client
    resp = c.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_train_submission_returns_queued_immediately(client):
    c, mock_submit = client
    resp = c.post(
        "/api/tasks/train",
        json={"model": "yolo11n.pt", "data": "coco8.yaml", "epochs": 1, "imgsz": 32, "timeout": 60},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["job_id"].startswith("train-")
    assert "submitted_at" in body
    mock_submit.assert_called_once()
    # (skill, inputs, params, timeout, job_id) — positional args passed to submit_task
    args = mock_submit.call_args.args
    assert args[0] == "yolo.train"
    assert args[1] == {"model": "yolo11n.pt", "data": "coco8.yaml"}
    assert args[2] == {"epochs": 1, "imgsz": 32}
    assert args[3] == 60
    assert args[4] == body["job_id"]


def test_predict_submission_returns_queued_immediately(client):
    c, mock_submit = client
    resp = c.post(
        "/api/tasks/predict",
        json={"model": "yolo11n.pt", "source": "bus.jpg", "conf": 0.3, "timeout": 60},
    )
    assert resp.status_code == 202
    assert resp.json()["job_id"].startswith("predict-")
    mock_submit.assert_called_once()


def test_export_submission_returns_queued_immediately(client):
    c, mock_submit = client
    resp = c.post(
        "/api/tasks/export",
        json={"model": "yolo11n.pt", "format": "onnx", "timeout": 60},
    )
    assert resp.status_code == 202
    assert resp.json()["job_id"].startswith("export-")
    mock_submit.assert_called_once()


def test_get_unknown_task_404(client):
    c, _ = client
    resp = c.get("/api/tasks/does-not-exist")
    assert resp.status_code == 404


def test_list_tasks_after_submission(client):
    c, _ = client
    c.post("/api/tasks/predict", json={"model": "yolo11n.pt", "source": "bus.jpg", "timeout": 60})
    resp = c.get("/api/tasks?limit=10&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["skill"] == "yolo.predict"
    assert body["limit"] == 10
    assert body["offset"] == 0


def test_list_tasks_pagination_offset(client):
    c, _ = client
    for _ in range(3):
        c.post("/api/tasks/export", json={"model": "yolo11n.pt", "format": "onnx", "timeout": 60})
    resp = c.get("/api/tasks?limit=1&offset=1")
    assert resp.status_code == 200
    assert len(resp.json()["jobs"]) == 1


def test_cancel_unknown_task_404(client):
    c, _ = client
    resp = c.delete("/api/tasks/does-not-exist")
    assert resp.status_code == 404


def test_cancel_finished_task_409(client):
    c, _ = client
    resp = c.post("/api/tasks/export", json={"model": "yolo11n.pt", "format": "onnx", "timeout": 60})
    job_id = resp.json()["job_id"]

    # Simulate the background task having already completed and overwritten
    # the DB row with a terminal status (mocked submit_task never does this
    # itself, so we do it directly).
    from f1_studio_db import F1StudioDB
    F1StudioDB().save_job(job_id, "yolo.export", {"status": "ok", "job_id": job_id})

    resp = c.delete(f"/api/tasks/{job_id}")
    assert resp.status_code == 409


def test_metrics_unknown_task_404(client):
    c, _ = client
    resp = c.get("/api/tasks/does-not-exist/metrics")
    assert resp.status_code == 404


def test_metrics_not_a_train_job_404(client):
    c, _ = client
    resp = c.post("/api/tasks/export", json={"model": "yolo11n.pt", "format": "onnx", "timeout": 60})
    job_id = resp.json()["job_id"]
    resp = c.get(f"/api/tasks/{job_id}/metrics")
    assert resp.status_code == 404


def test_system_check_submission_returns_queued_immediately(client):
    c, mock_submit = client
    resp = c.post("/api/tasks/system-check")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["job_id"].startswith("syscheck-")
    assert "submitted_at" in body
    mock_submit.assert_called_once()
    args = mock_submit.call_args.args
    assert args[0] == "yolo.system"
    assert args[1] == {}
    assert args[2] == {}


def test_system_check_job_visible_in_list(client):
    c, _ = client
    c.post("/api/tasks/system-check")
    resp = c.get("/api/tasks")
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["skill"] == "yolo.system"
