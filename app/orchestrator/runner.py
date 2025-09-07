import uuid
from typing import Optional
from ..schemas.search import SearchInput, SearchStatusResponse
from ..store.jobs import create_job, get_job


async def start_search_job(payload: SearchInput) -> str:
    job_id = uuid.uuid4().hex
    # For skeleton: mark as queued; future steps will enqueue real work
    create_job(job_id, status="queued", result=None, error=None)
    return job_id


async def get_job_status(job_id: str) -> Optional[SearchStatusResponse]:
    return get_job(job_id)

