from fastapi import APIRouter, HTTPException
from ...schemas.search import SearchInput, SearchStartResponse, SearchStatusResponse
from ...orchestrator.runner import start_search_job, get_job_status
from ...schemas.search import ChooseCandidateRequest, AnswerInput
from ...store.jobs import _JOBS, update_job
from ...schemas.common import JobStatus


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


@router.post("/{job_id}/choose-candidate", response_model=SearchStatusResponse)
async def choose_candidate(job_id: str, selection: ChooseCandidateRequest) -> SearchStatusResponse:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.needs_disambiguation:
        raise HTTPException(status_code=400, detail="job does not require disambiguation")
    result = job.result or {}
    cands = result.get("candidates", [])
    if selection.index < 0 or selection.index >= len(cands):
        raise HTTPException(status_code=400, detail="invalid candidate index")
    chosen = cands[selection.index]
    # Rebuild a minimal profile from chosen candidate; aggregator will improve later
    profile = result.get("profile", {})
    profile.update({
        "names": [n for n in ([chosen.get("display_name")] if chosen.get("display_name") else [])],
        "emails": list({*profile.get("emails", []), *chosen.get("emails", [])}),
        "phones": list({*profile.get("phones", []), *chosen.get("phones", [])}),
        "usernames": list({*profile.get("usernames", []), *chosen.get("usernames", [])}),
        "locations": list({*profile.get("locations", []), *chosen.get("locations", [])}),
    })
    result["profile"] = profile
    update_job(job_id, status=JobStatus.completed, result=result, questions=None)
    return await get_job_status(job_id)


# Placeholder: choose-candidate endpoint (to be implemented in Phase 1 continuation)
# @router.post("/{job_id}/choose-candidate")
# async def choose_candidate(job_id: str, selection: ChooseCandidateRequest) -> SearchStatusResponse:
#     ...


@router.post("/{job_id}/answer", response_model=SearchStatusResponse)
async def answer(job_id: str, payload: AnswerInput) -> SearchStatusResponse:
	job = _JOBS.get(job_id)
	if job is None:
		raise HTTPException(status_code=404, detail="job not found")
	# Merge new hints into normalized_query and mark as queued to rerun in a fresh job in the future.
	# For now, we just update the result's normalized_query for visibility.
	res = job.result or {}
	nq = res.get("normalized_query", {})
	for k in ["full_name", "email", "phone", "username", "location", "context_text"]:
		val = getattr(payload, k if k != "full_name" else "name", None)
		if val:
			nq[k] = val
	res["normalized_query"] = nq
	update_job(job_id, status=JobStatus.needs_disambiguation, result=res)
	return await get_job_status(job_id)

