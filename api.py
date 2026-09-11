"""FastAPI backend for F1 Studio — wraps task logic as REST endpoints."""
from datetime import datetime
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from f1_studio_db import F1StudioDB
from f1_studio_tasks import cancel_task, submit_task

app = FastAPI(title="F1 Studio API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:7860",
                   "http://127.0.0.1:5173", "http://127.0.0.1:7860"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TrainRequest(BaseModel):
    model: str
    data: str
    epochs: int
    imgsz: int = 640
    timeout: int = 600


class PredictRequest(BaseModel):
    model: str
    source: str
    conf: float = 0.25
    timeout: int = 300


class ExportRequest(BaseModel):
    model: str
    format: str
    timeout: int = 300


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/tasks/train", status_code=202)
def train(req: TrainRequest, background_tasks: BackgroundTasks):
    job_id = f"train-{uuid.uuid4().hex[:8]}"
    submitted_at = datetime.now().isoformat()
    F1StudioDB().save_job(job_id, "yolo.train", {"status": "queued", "job_id": job_id})
    background_tasks.add_task(
        submit_task,
        "yolo.train",
        {"model": req.model, "data": req.data},
        {"epochs": req.epochs, "imgsz": req.imgsz},
        req.timeout,
        job_id,
    )
    return {"job_id": job_id, "status": "queued", "submitted_at": submitted_at}


@app.post("/api/tasks/predict", status_code=202)
def predict(req: PredictRequest, background_tasks: BackgroundTasks):
    job_id = f"predict-{uuid.uuid4().hex[:8]}"
    submitted_at = datetime.now().isoformat()
    F1StudioDB().save_job(job_id, "yolo.predict", {"status": "queued", "job_id": job_id})
    background_tasks.add_task(
        submit_task,
        "yolo.predict",
        {"model": req.model, "source": req.source},
        {"conf": req.conf},
        req.timeout,
        job_id,
    )
    return {"job_id": job_id, "status": "queued", "submitted_at": submitted_at}


@app.post("/api/tasks/export", status_code=202)
def export_task(req: ExportRequest, background_tasks: BackgroundTasks):
    job_id = f"export-{uuid.uuid4().hex[:8]}"
    submitted_at = datetime.now().isoformat()
    F1StudioDB().save_job(job_id, "yolo.export", {"status": "queued", "job_id": job_id})
    background_tasks.add_task(
        submit_task,
        "yolo.export",
        {"model": req.model},
        {"format": req.format},
        req.timeout,
        job_id,
    )
    return {"job_id": job_id, "status": "queued", "submitted_at": submitted_at}


@app.get("/api/tasks")
def list_tasks(limit: int = 50, offset: int = 0):
    jobs = F1StudioDB().load_job_history(limit=limit, offset=offset)
    return {"jobs": jobs, "limit": limit, "offset": offset}


@app.get("/api/tasks/{job_id}")
def get_task(job_id: str):
    job = F1StudioDB().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@app.delete("/api/tasks/{job_id}")
def cancel(job_id: str):
    if not cancel_task(job_id):
        job = F1StudioDB().get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        raise HTTPException(status_code=409, detail=f"Job {job_id} is already {job['status']}, cannot cancel")
    return {"job_id": job_id, "status": "cancelled"}
