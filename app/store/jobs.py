from typing import Dict, Optional, Any, Literal
from pydantic import BaseModel
from ..schemas.search import SearchStatusResponse


JobStatus = Literal["queued", "running", "completed", "failed"]


class InMemoryJob(BaseModel):
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


_JOBS: Dict[str, InMemoryJob] = {}


def create_job(job_id: str, status: JobStatus, result=None, error=None) -> None:
    _JOBS[job_id] = InMemoryJob(job_id=job_id, status=status, result=result, error=error)


def update_job(job_id: str, **kwargs) -> None:
    if job_id in _JOBS:
        _JOBS[job_id] = _JOBS[job_id].model_copy(update=kwargs)


def get_job(job_id: str) -> Optional[SearchStatusResponse]:
    job = _JOBS.get(job_id)
    if not job:
        return None
    return SearchStatusResponse(
        job_id=job.job_id,
        status=job.status,
        result=job.result,
        error=job.error,
    )

