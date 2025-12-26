from __future__ import annotations
from pathlib import Path
import uuid

BASE = Path("data")
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"

def ensure_dirs() -> None:
    UPLOADS.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

def new_job_id() -> str:
    return uuid.uuid4().hex

def job_dir(job_id: str) -> Path:
    d = OUTPUTS / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def upload_path(job_id: str, filename: str) -> Path:
    safe = filename.replace("/", "_").replace("\\", "_")
    return UPLOADS / f"{job_id}__{safe}"
