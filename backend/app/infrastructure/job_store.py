from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass


@dataclass
class VideoJob:
    id: str
    state: str = "queued"
    progress: float = 0
    filename: str = ""
    model_id: str = ""
    result_url: str | None = None
    avatar_url: str | None = None
    skeleton_url: str | None = None
    avatar_preview_url: str | None = None
    skeleton_preview_url: str | None = None
    avatar_preview_kind: str | None = None
    skeleton_preview_kind: str | None = None
    error: str | None = None
    cancelled: bool = False

    def public(self) -> dict:
        result = asdict(self)
        result.pop("cancelled", None)
        return result


class InMemoryJobStore:
    def __init__(self):
        self._jobs: dict[str, VideoJob] = {}
        self._lock = threading.Lock()

    def create(self, filename: str, model_id: str) -> VideoJob:
        job = VideoJob(id=uuid.uuid4().hex, filename=filename, model_id=model_id)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> VideoJob | None:
        return self._jobs.get(job_id)

    def update(self, job_id: str, **changes) -> VideoJob:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            return job

    def cancel(self, job_id: str) -> VideoJob:
        return self.update(job_id, cancelled=True, state="cancelled")
