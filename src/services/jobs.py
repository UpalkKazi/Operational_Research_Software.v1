"""Background job runner so solves, downloads and AI calls never block the UI script."""

from __future__ import annotations

import threading
import time
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="orstudio-job")
_JOBS: Dict[str, "Job"] = {}
_LOCK = threading.Lock()


@dataclass
class Job:
    id: str
    kind: str
    label: str
    cancellable: bool
    cancel_event: threading.Event = field(default_factory=threading.Event)
    handle: Dict[str, Any] = field(default_factory=dict)
    progress: Dict[str, Any] = field(default_factory=lambda: {"stage": "Queued", "fraction": None, "detail": ""})
    started: float = field(default_factory=time.time)
    finished: Optional[float] = None
    future: Optional[Future] = None
    result: Any = None
    error: Optional[str] = None

    @property
    def done(self) -> bool:
        return self.future is not None and self.future.done()

    def set_progress(self, stage: str, fraction: Optional[float] = None, detail: str = "") -> None:
        self.progress = {"stage": stage, "fraction": fraction, "detail": detail}

    def cancel(self) -> bool:
        if not self.cancellable or self.done:
            return False
        self.cancel_event.set()
        interrupt = self.handle.get("interrupt")
        if callable(interrupt):
            try:
                interrupt()
            except Exception:
                pass
        return True

    @property
    def elapsed(self) -> float:
        return (self.finished or time.time()) - self.started


def submit(kind: str, label: str, fn: Callable[["Job"], Any], cancellable: bool = False) -> Job:
    job = Job(id=uuid.uuid4().hex[:10], kind=kind, label=label, cancellable=cancellable)

    def run() -> Any:
        job.started = time.time()
        job.set_progress("Running")
        try:
            job.result = fn(job)
            return job.result
        except Exception as exc:
            job.error = f"{type(exc).__name__}: {exc}"
            job.handle["traceback"] = traceback.format_exc()
            raise
        finally:
            job.finished = time.time()

    with _LOCK:
        _JOBS[job.id] = job
    job.future = _EXECUTOR.submit(run)
    return job


def get(job_id: Optional[str]) -> Optional[Job]:
    if not job_id:
        return None
    with _LOCK:
        return _JOBS.get(job_id)


def forget(job_id: str) -> None:
    with _LOCK:
        _JOBS.pop(job_id, None)


def wait(job_id: str, timeout: float = 120.0) -> Optional[Job]:
    job = get(job_id)
    if job and job.future:
        try:
            job.future.result(timeout=timeout)
        except Exception:
            pass
    return job
