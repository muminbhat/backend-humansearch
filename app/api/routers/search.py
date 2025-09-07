from fastapi import APIRouter, HTTPException
from ...schemas.search import SearchInput, SearchStartResponse, SearchStatusResponse
from ...orchestrator.runner import start_search_job, get_job_status


router = APIRouter()


@router.post("/start", response_model=SearchStartResponse)
async def start_search(payload: SearchInput) -> SearchStartResponse:
    job_id = await start_search_job(payload)
    return SearchStartResponse(job_id=job_id, status="queued")


@router.get("/{job_id}", response_model=SearchStatusResponse)
async def get_status(job_id: str) -> SearchStatusResponse:
    status = await get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="job not found")
    return status

