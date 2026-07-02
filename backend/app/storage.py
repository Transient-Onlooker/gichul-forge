from __future__ import annotations
import json
from pathlib import Path
from threading import RLock
from typing import Iterable
import orjson
from .models import JobSnapshot, now_iso
from .settings import get_settings


class JobStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.storage_path
        self.jobs_dir = self.root / "jobs"
        self.uploads_dir = self.root / "uploads"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def job_dir(self, job_id: str) -> Path:
        path = self.jobs_dir / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def job_file(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def save(self, job: JobSnapshot) -> JobSnapshot:
        with self._lock:
            job.updatedAt = now_iso()
            data = orjson.dumps(job.model_dump(mode="json"), option=orjson.OPT_INDENT_2)
            self.job_file(job.id).write_bytes(data)
        return job

    def get(self, job_id: str) -> JobSnapshot:
        path = self.job_file(job_id)
        if not path.exists():
            raise FileNotFoundError(job_id)
        return JobSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, job_id: str) -> None:
        import shutil
        with self._lock:
            shutil.rmtree(self.job_dir(job_id), ignore_errors=True)

    def list_jobs(self) -> Iterable[JobSnapshot]:
        for path in self.jobs_dir.glob("*/job.json"):
            try:
                yield JobSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue


store = JobStore()
