"""
F1 Studio P1: Async Task Queue
Implements background task execution with real-time progress streaming.
"""

import threading
import queue
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from f1_studio_tasks import submit_task, cancel_task as kill_process
from f1_studio_db import F1StudioDB


@dataclass
class Task:
    """Represents a queued task."""
    job_id: str
    skill: str
    inputs: Dict
    params: Dict
    timeout: int
    submitted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "queued"  # queued, running, completed, failed, cancelled
    worker_thread: Optional[threading.Thread] = None
    cancel_requested: bool = False


class TaskQueue:
    """
    Async task queue with background worker threads.

    Features:
    - Background task execution
    - Task cancellation
    - Real-time progress tracking
    - Thread-safe queue operations
    """

    def __init__(self, db: F1StudioDB, max_workers: int = 2):
        self.db = db
        self.max_workers = max_workers
        self.task_queue: queue.Queue = queue.Queue()
        self.active_tasks: Dict[str, Task] = {}
        self.lock = threading.Lock()
        self.workers = []
        self.running = False

    def start(self):
        """Start worker threads."""
        if self.running:
            return

        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

    def stop(self):
        """Stop worker threads gracefully."""
        self.running = False
        # Wake up workers with sentinel values
        for _ in self.workers:
            self.task_queue.put(None)

    def submit(self, skill: str, inputs: Dict, params: Dict, timeout: int = 600) -> str:
        """
        Submit a task to the queue.
        Returns the job_id immediately.
        """
        import uuid
        job_id = f"{skill.split('.')[-1]}-{uuid.uuid4().hex[:8]}"

        task = Task(
            job_id=job_id,
            skill=skill,
            inputs=inputs,
            params=params,
            timeout=timeout
        )

        with self.lock:
            self.active_tasks[job_id] = task

        # Save to DB with "queued" status
        self.db.save_job(
            job_id=job_id,
            skill=skill,
            response={
                "status": "queued",
                "message": "Task queued for execution",
                "submitted_at": task.submitted_at
            }
        )

        self.task_queue.put(task)
        return job_id

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a task.
        Returns True if cancellation was requested, False if task not found.
        """
        with self.lock:
            task = self.active_tasks.get(job_id)
            if not task:
                return False
            task.cancel_requested = True
            task.status = "cancelled"

        # Persist cancellation to DB immediately (covers queued tasks never picked up by worker)
        self.db.save_job(
            job_id=job_id,
            skill=task.skill,
            response={
                "status": "cancelled",
                "message": "Task was cancelled by user",
                "cancelled_at": datetime.now().isoformat()
            }
        )

        # Kill the running subprocess if it exists
        kill_process(job_id)
        return True

    def get_status(self, job_id: str) -> Optional[str]:
        """Get current status of a task."""
        with self.lock:
            task = self.active_tasks.get(job_id)
            return task.status if task else None

    def _worker_loop(self):
        """Main worker loop - runs in background thread."""
        while self.running:
            try:
                # Block until a task is available
                task = self.task_queue.get(timeout=1.0)
                if task is None:  # Sentinel value for shutdown
                    break

                self._execute_task(task)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")

    def _execute_task(self, task: Task):
        """Execute a single task."""
        job_id = task.job_id

        # Check for cancellation before starting (task may have been cancelled while queued)
        if task.cancel_requested:
            self._handle_cancellation(task)
            return

        # Update status to running
        with self.lock:
            task.status = "running"

        self.db.save_job(
            job_id=job_id,
            skill=task.skill,
            response={
                "status": "running",
                "message": "Task execution started",
                "started_at": datetime.now().isoformat()
            }
        )

        try:
            # Check for cancellation before starting
            if task.cancel_requested:
                self._handle_cancellation(task)
                return

            # Execute the actual task
            response = submit_task(
                skill=task.skill,
                inputs=task.inputs,
                params=task.params,
                timeout=task.timeout,
                job_id=task.job_id,
            )

            # Check for cancellation after execution (edge case)
            if task.cancel_requested:
                self._handle_cancellation(task)
                return

            # Task completed successfully
            with self.lock:
                task.status = "completed"

            self.db.save_job(
                job_id=job_id,
                skill=task.skill,
                response=response
            )

        except Exception as e:
            # Task failed
            with self.lock:
                task.status = "failed"

            self.db.save_job(
                job_id=job_id,
                skill=task.skill,
                response={
                    "status": "failed",
                    "error": str(e),
                    "finished_at": datetime.now().isoformat()
                }
            )

        finally:
            # Clean up
            with self.lock:
                if job_id in self.active_tasks:
                    del self.active_tasks[job_id]

    def _handle_cancellation(self, task: Task):
        """Handle task cancellation."""
        self.db.save_job(
            job_id=task.job_id,
            skill=task.skill,
            response={
                "status": "cancelled",
                "message": "Task was cancelled by user",
                "cancelled_at": datetime.now().isoformat()
            }
        )


class ProgressMonitor:
    """
    Monitors progress.jsonl file for real-time updates.
    """

    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.last_position = 0

    def get_updates(self) -> list:
        """
        Read new lines from progress.jsonl since last check.
        Returns list of progress events.
        """
        if not self.progress_file.exists():
            return []

        updates = []
        try:
            with open(self.progress_file, 'r') as f:
                f.seek(self.last_position)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            updates.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                self.last_position = f.tell()
        except Exception as e:
            print(f"Error reading progress file: {e}")

        return updates

    def reset(self):
        """Reset read position to beginning."""
        self.last_position = 0

