"""
F1 Studio Database Layer - SQLite persistence for task management
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd


class F1StudioDB:
    """Simple SQLite database for F1 Studio task management."""

    def __init__(self, db_path: str = "f1_studio.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                skill TEXT NOT NULL,
                status TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                finished_at TEXT,
                response_json TEXT,
                artifacts_json TEXT,
                error_message TEXT
            )
        """)

        conn.commit()
        conn.close()

    def save_job(self, job_id: str, skill: str, response: Dict) -> None:
        """Save a job record to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        status = response.get("status", "unknown")
        finished_at = datetime.now().isoformat()
        response_json = json.dumps(response)

        # Extract artifacts if available
        artifacts = []
        if status == "ok" and "job" in response and "save_dir" in response["job"]:
            save_dir = Path(response["job"]["save_dir"])
            if save_dir.exists():
                artifacts = self._scan_artifacts(save_dir)

        artifacts_json = json.dumps(artifacts) if artifacts else None
        error_message = None

        if status == "failed" and "error" in response:
            error_message = response["error"].get("type", "Unknown error")

        cursor.execute("""
            INSERT OR REPLACE INTO jobs
            (job_id, skill, status, submitted_at, finished_at, response_json, artifacts_json, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, skill, status, datetime.now().isoformat(), finished_at,
              response_json, artifacts_json, error_message))

        conn.commit()
        conn.close()

    def _scan_artifacts(self, save_dir: Path) -> List[Dict]:
        """Scan save_dir for artifacts and categorize them."""
        artifacts = []

        if not save_dir.exists():
            return artifacts

        for file_path in save_dir.rglob("*"):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            rel_path = file_path.relative_to(save_dir)
            file_name = file_path.name

            # Categorize by extension and file name patterns
            if suffix in [".pt", ".pth"]:
                category = "weight"
                # Prioritize best.pt
                priority = 0 if file_name == "best.pt" else 1 if file_name == "last.pt" else 2
            elif suffix in [".csv"]:
                category = "result"
                priority = 0 if "results" in file_name.lower() else 1
            elif suffix in [".png", ".jpg", ".jpeg"]:
                category = "result"
                # Results images higher priority than prediction outputs
                priority = 0 if "results" in file_name.lower() else 2
            elif suffix in [".log"]:
                category = "log"
                priority = 1
            elif suffix in [".json"]:
                # Manifest and config files are logs
                category = "log"
                priority = 0 if "manifest" in file_name.lower() else 1
            elif suffix in [".txt"]:
                category = "log"
                priority = 2
            elif suffix in [".onnx", ".torchscript", ".engine", ".tflite", ".pb"]:
                category = "export"
                priority = 0
            elif suffix in [".yaml", ".yml"]:
                category = "config"
                priority = 1
            else:
                category = "other"
                priority = 3

            artifacts.append({
                "path": str(file_path),
                "rel_path": str(rel_path),
                "category": category,
                "size": file_path.stat().st_size,
                "priority": priority,
                "name": file_name
            })

        # Sort by category priority and then by file priority
        category_order = {"weight": 0, "result": 1, "export": 2, "config": 3, "log": 4, "other": 5}
        artifacts.sort(key=lambda x: (category_order.get(x["category"], 99), x["priority"], x["name"]))

        return artifacts

    def load_job_history(self, limit: int = 100) -> List[Dict]:
        """Load job history from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT job_id, skill, status, submitted_at, finished_at, artifacts_json, error_message
            FROM jobs
            ORDER BY submitted_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        jobs = []
        for row in rows:
            job_id, skill, status, submitted_at, finished_at, artifacts_json, error_message = row
            jobs.append({
                "job_id": job_id,
                "skill": skill,
                "status": status,
                "submitted_at": submitted_at,
                "finished_at": finished_at,
                "artifacts": json.loads(artifacts_json) if artifacts_json else [],
                "error_message": error_message
            })

        return jobs

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a specific job by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT job_id, skill, status, submitted_at, finished_at, response_json, artifacts_json, error_message
            FROM jobs
            WHERE job_id = ?
        """, (job_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        job_id, skill, status, submitted_at, finished_at, response_json, artifacts_json, error_message = row
        return {
            "job_id": job_id,
            "skill": skill,
            "status": status,
            "submitted_at": submitted_at,
            "finished_at": finished_at,
            "response": json.loads(response_json) if response_json else {},
            "artifacts": json.loads(artifacts_json) if artifacts_json else [],
            "error_message": error_message
        }

    def clear_history(self) -> int:
        """Clear all job history. Returns number of deleted records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM jobs")
        conn.commit()
        conn.close()

        return count

    def get_job_metrics(self, job_id: str) -> Optional[Dict]:
        """
        Extract training metrics from a job's results.csv file.

        Args:
            job_id: The job ID to extract metrics from

        Returns:
            Dict with keys: job_id, epochs, imgsz, mAP50, mAP50-95, precision, recall, box_loss
            Returns None if job not found, not a training job, or results.csv missing/malformed
        """
        # Get job from database
        job = self.get_job(job_id)
        if not job:
            return None

        # Only training jobs have results.csv
        if job["skill"] != "yolo.train":
            return None

        # Check if job was successful
        if job["status"] != "ok":
            return None

        # Extract save_dir from response
        response = job.get("response", {})
        job_data = response.get("job", {})
        save_dir = job_data.get("save_dir")

        if not save_dir:
            return None

        save_dir_path = Path(save_dir)
        if not save_dir_path.exists():
            return None

        # Look for results.csv
        results_csv = save_dir_path / "results.csv"
        if not results_csv.exists():
            return None

        try:
            # Parse results.csv
            df = pd.read_csv(results_csv)

            # Get last row (final epoch)
            if len(df) == 0:
                return None

            last_row = df.iloc[-1]

            # Extract metrics (handle missing columns gracefully)
            metrics = {
                "job_id": job_id,
                "epochs": int(last_row.get("epoch", -1)) + 1,  # epoch is 0-indexed
                "imgsz": job_data.get("imgsz", -1),  # From job params
                "mAP50": float(last_row.get("metrics/mAP50(B)", 0.0)),
                "mAP50-95": float(last_row.get("metrics/mAP50-95(B)", 0.0)),
                "precision": float(last_row.get("metrics/precision(B)", 0.0)),
                "recall": float(last_row.get("metrics/recall(B)", 0.0)),
                "box_loss": float(last_row.get("val/box_loss", 0.0))
            }

            return metrics

        except Exception as e:
            # Malformed CSV or parsing error - fail gracefully
            print(f"Warning: Failed to parse results.csv for {job_id}: {e}")
            return None

    def get_jobs_for_comparison(self, job_ids: List[str]) -> List[Dict]:
        """
        Get metrics for multiple jobs for comparison.

        Args:
            job_ids: List of job IDs to compare

        Returns:
            List of dicts with job metadata + metrics
            Filters out jobs where metrics extraction failed
        """
        results = []

        for job_id in job_ids:
            metrics = self.get_job_metrics(job_id)
            if metrics is not None:
                results.append(metrics)

        return results
