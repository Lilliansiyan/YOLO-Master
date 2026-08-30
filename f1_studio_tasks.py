"""
F1 Studio Task Submission Layer - Dispatcher interface for task management
"""
import subprocess
import json
import uuid
import time
from pathlib import Path
from typing import Dict, Any, Optional
from f1_studio_db import F1StudioDB


# Path whitelist for security
ALLOWED_PREFIXES = [
    "models/",
    "datasets/",
    "runs/",
    "ckpts/",
    "yolo",
    "coco",
]


def validate_path(path: str) -> None:
    """Validate path against whitelist."""
    if not path:
        return

    # Block directory traversal
    if ".." in path or path.startswith("/"):
        raise ValueError(f"Path violation: {path} (contains '..' or absolute path)")

    # Check whitelist
    if not any(path.startswith(p) for p in ALLOWED_PREFIXES):
        raise ValueError(f"Path not in whitelist: {path}")


def validate_request(request: Dict[str, Any]) -> None:
    """Validate request inputs against security rules."""
    inputs = request.get("inputs", {})

    # Validate all path-like inputs
    for key in ["model", "data", "source", "imgsz"]:
        if key in inputs:
            value = inputs[key]
            if isinstance(value, str):
                # Skip validation for built-in dataset names (coco8.yaml etc)
                if not value.endswith(".yaml") or "/" in value:
                    validate_path(value)


def submit_task(skill: str, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit a task to the dispatcher and return the result.

    Args:
        skill: Skill name (e.g., "yolo.train", "yolo.predict", "yolo.export")
        inputs: Input parameters (model, data, source, etc.)
        params: Training/inference parameters (epochs, imgsz, conf, etc.)

    Returns:
        Dict with job_id, status, and full response from dispatcher
    """
    # Generate job ID
    job_id = f"{skill.split('.')[-1]}-{uuid.uuid4().hex[:8]}"

    # Build request
    request = {
        "skill": skill,
        "inputs": inputs,
        "params": params
    }

    # Validate paths
    validate_request(request)

    # Call dispatcher
    dispatcher_path = Path(__file__).parent / "agent" / "scripts" / "run_yolo_master_skill.py"

    try:
        result = subprocess.run(
            ["python3", str(dispatcher_path), "--json", json.dumps(request), "--pretty"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        # Parse response
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            response = {
                "skill": skill,
                "status": "failed",
                "error": {
                    "type": "JSONDecodeError",
                    "message": f"Failed to parse dispatcher output: {e}",
                    "stdout": result.stdout[:500],
                    "stderr": result.stderr[:500]
                }
            }

        # Add job_id to response
        response["job_id"] = job_id

        # Save to database
        db = F1StudioDB()
        db.save_job(job_id, skill, response)

        return response

    except subprocess.TimeoutExpired:
        response = {
            "job_id": job_id,
            "skill": skill,
            "status": "timeout",
            "error": {
                "type": "TimeoutError",
                "message": "Task execution exceeded 10 minute timeout"
            }
        }
        db = F1StudioDB()
        db.save_job(job_id, skill, response)
        return response

    except Exception as e:
        response = {
            "job_id": job_id,
            "skill": skill,
            "status": "failed",
            "error": {
                "type": type(e).__name__,
                "message": str(e)
            }
        }
        db = F1StudioDB()
        db.save_job(job_id, skill, response)
        return response


def submit_train(model: str, data: str, epochs: int, imgsz: int, **kwargs) -> Dict[str, Any]:
    """Submit a training task."""
    inputs = {"model": model, "data": data}
    params = {"epochs": epochs, "imgsz": imgsz, **kwargs}
    return submit_task("yolo.train", inputs, params)


def submit_predict(model: str, source: str, **kwargs) -> Dict[str, Any]:
    """Submit a prediction task."""
    inputs = {"model": model, "source": source}
    params = kwargs
    return submit_task("yolo.predict", inputs, params)


def submit_export(model: str, format: str, **kwargs) -> Dict[str, Any]:
    """Submit an export task."""
    inputs = {"model": model}
    params = {"format": format, **kwargs}
    return submit_task("yolo.export", inputs, params)


def submit_system_check() -> Dict[str, Any]:
    """Submit a system.doctor check."""
    return submit_task("yolo.system", {}, {})
