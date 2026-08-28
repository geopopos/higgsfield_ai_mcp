"""
Resumable Asynchronous Job System for AI MV Director Platform
Provides state checkpoints, retry policies, cancellation, and job queue management.
"""

from __future__ import annotations
import time
import uuid
import threading
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable


class JobState(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


@dataclass
class JobCheckpoint:
    checkpoint_id: str
    timestamp: float
    step_name: str
    progress: float  # 0.0 to 1.0
    intermediate_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobRetryPolicy:
    max_retries: int = 3
    initial_backoff_sec: float = 2.0
    backoff_multiplier: float = 2.0
    retryable_error_codes: List[str] = field(default_factory=lambda: ["RATE_LIMIT", "TIMEOUT", "SERVER_UNAVAILABLE"])


@dataclass
class Job:
    job_id: str
    shot_id: str
    project_id: str
    payload: Dict[str, Any]
    state: JobState = JobState.PENDING
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    checkpoints: List[JobCheckpoint] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_checkpoint(self, step_name: str, progress: float, data: Optional[Dict[str, Any]] = None) -> None:
        cp = JobCheckpoint(
            checkpoint_id=f"cp_{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            step_name=step_name,
            progress=progress,
            intermediate_data=data or {},
        )
        self.checkpoints.append(cp)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        return d


class JobQueue:
    """Thread-safe persistent job registry and queue."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.RLock()

    def enqueue(self, shot_id: str, project_id: str, payload: Dict[str, Any], max_retries: int = 3) -> Job:
        with self._lock:
            job_id = f"job_{uuid.uuid4().hex[:10]}"
            job = Job(
                job_id=job_id,
                shot_id=shot_id,
                project_id=project_id,
                payload=payload,
                state=JobState.QUEUED,
                max_retries=max_retries,
            )
            job.add_checkpoint("enqueued", 0.0)
            self._jobs[job_id] = job
            return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_by_project(self, project_id: str) -> List[Job]:
        with self._lock:
            return [j for j in self._jobs.values() if j.project_id == project_id]

    def update_state(self, job_id: str, state: JobState, error: Optional[str] = None, result: Optional[Dict[str, Any]] = None) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.state = state
                if error:
                    job.error = error
                if result:
                    job.result = result
                job.updated_at = time.time()
            return job

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.state not in (JobState.COMPLETED, JobState.FAILED):
                job.state = JobState.CANCELLED
                job.add_checkpoint("cancelled", job.checkpoints[-1].progress if job.checkpoints else 0.0)
                return True
            return False


class JobRunner:
    """Executes jobs with automatic retry policy and checkpoint resumption."""

    def __init__(self, queue: JobQueue, retry_policy: Optional[JobRetryPolicy] = None):
        self.queue = queue
        self.retry_policy = retry_policy or JobRetryPolicy()

    def execute_job_sync(self, job_id: str, task_fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        job = self.queue.get(job_id)
        if not job:
            raise KeyError(f"Job {job_id} not found")

        self.queue.update_state(job_id, JobState.RUNNING)
        job.add_checkpoint("running", 0.2)

        while job.retry_count <= job.max_retries:
            try:
                # Execute underlying generation / task
                res = task_fn(job.payload)
                job.add_checkpoint("completed", 1.0, data={"output": str(res)})
                self.queue.update_state(job_id, JobState.COMPLETED, result=res)
                return res
            except Exception as e:
                job.retry_count += 1
                if job.retry_count <= job.max_retries:
                    self.queue.update_state(job_id, JobState.RETRYING, error=str(e))
                    job.add_checkpoint(f"retrying_attempt_{job.retry_count}", 0.5, data={"error": str(e)})
                    time.sleep(self.retry_policy.initial_backoff_sec * (self.retry_policy.backoff_multiplier ** (job.retry_count - 1)))
                else:
                    self.queue.update_state(job_id, JobState.FAILED, error=str(e))
                    job.add_checkpoint("failed", 0.0, data={"fatal_error": str(e)})
                    raise RuntimeError(f"Job {job_id} failed after {job.max_retries} retries: {e}")

        return {}
