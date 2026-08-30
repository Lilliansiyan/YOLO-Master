"""
F1 Studio Database Layer - SQLite persistence for task management
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


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

        for file_path in save_dir.rglob("*"):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            rel_path = file_path.relative_to(save_dir)

            # Categorize by extension
            if suffix in [".pt", ".pth"]:
                category = "weight"
            elif suffix in [".log", ".json", ".txt"]:
                category = "log"
            elif suffix in [".csv", ".png", ".jpg", ".jpeg"]:
                category = "result"
            elif suffix in [".onnx", ".torchscript", ".engine"]:
                category = "export"
            else:
                category = "other"

            artifacts.append({
                "path": str(file_path),
                "rel_path": str(rel_path),
                "category": category,
                "size": file_path.stat().st_size
            })

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
