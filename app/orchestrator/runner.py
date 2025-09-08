import uuid
import asyncio
import time
from typing import Optional, Dict, Any
from ..schemas.search import SearchInput, SearchStatusResponse
from ..schemas.common import JobStatus
from ..store.jobs import create_job, get_job, update_job
from ..store.queue import enqueue_background
from ..agent.extractor import extract_with_llm_fallback as extract_normalized_query
from ..connectors.pdl import PeopleDataLabsConnector
from ..connectors.pdl_search import PeopleDataLabsSearchConnector
from ..connectors.pdl_identify import PeopleDataLabsIdentifyConnector
from ..connectors.clearbit import ClearbitConnector
from ..scraper.github import GitHubScraper
from ..aggregator.merge import merge_results
from ..judge.validator import judge_result
from ..core.logging import logger
from ..orchestrator.planner import plan_tools
from ..connectors.search_engine import DuckDuckGoConnector


async def start_search_job(payload: SearchInput) -> str:
    job_id = uuid.uuid4().hex
    create_job(job_id, status=JobStatus.queued, result=None, error=None)
    logger.info({"event": "job_created", "job_id": job_id})
    # Fire-and-forget background task to simulate orchestration
    enqueue_background(_run_job, job_id, payload)
    return job_id


async def get_job_status(job_id: str) -> Optional[SearchStatusResponse]:
    return get_job(job_id)


async def _run_job(job_id: str, payload: SearchInput) -> None:
    start = time.perf_counter()
    try:
        update_job(job_id, status=JobStatus.running)
        logger.info({"event": "job_running", "job_id": job_id})
        # Simulate planning/execution time
        await asyncio.sleep(0.1)

        nq = await extract_normalized_query(payload)
        normalized_query: Dict[str, Any] = nq.model_dump()

        # Planner determines tool sequence under budget
        steps = plan_tools(nq, budget_ms=20000)
        tool_map = {
            "pdl": PeopleDataLabsConnector(),
            "clearbit": ClearbitConnector(),
            "github": GitHubScraper(),
            "pdl_search": PeopleDataLabsSearchConnector(),
            "duckduckgo": DuckDuckGoConnector(),
            "pdl_identify": PeopleDataLabsIdentifyConnector(),
        }
        tasks = []
        used_tools = []
        for s in steps:
            tool = tool_map.get(s["tool"]) if s else None
            if not tool:
                continue
            if s["tool"] == "github":
                tasks.append(tool.scrape(nq))
                used_tools.append("github")
            elif s["tool"] == "pdl":
                tasks.append(tool.fetch(nq))
                used_tools.append("pdl")
            elif s["tool"] == "pdl_search":
                tasks.append(tool.fetch(nq))
                used_tools.append("pdl_search")
            elif s["tool"] == "duckduckgo":
                tasks.append(tool.fetch(nq))
                used_tools.append("duckduckgo")
            elif s["tool"] == "pdl_identify":
                tasks.append(tool.fetch(nq))
                used_tools.append("pdl_identify")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter exceptions and collect dict results
        clean_results = []
        for r in results:
            if isinstance(r, Exception):
                continue
            clean_results.append(r)

        aggregated = merge_results(clean_results)
        final = judge_result({
            "normalized_query": normalized_query,
            **aggregated,
        })

        # Minimal deterministic result stub
        profile: Dict[str, Any] = {
            "names": [payload.name] if payload.name else [],
            "emails": [payload.email] if payload.email else [],
            "phones": [payload.phone] if payload.phone else [],
            "usernames": [payload.username] if payload.username else [],
            "locations": [payload.location] if payload.location else [],
            "employment": [],
            "education": [],
            "links": [],
            "bios": [],
            "skills": [],
            "organizations": [],
            "websites": [],
            "evidences": [],
            "overall_confidence": 0.2,
        }

        # Collect candidates count before constructing metrics
        candidates = final.get("candidates", [])

        result = {
            **final,
            "metrics": {
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "tools_used": used_tools,
                "api_cost_usd": 0.0,
                "diagnostics": {
                    "steps": [s.get("tool") for s in steps],
                    "llm_used": True,
                    "num_candidates": len(candidates),
                },
            },
        }

        # Simple ambiguity heuristic: multiple candidates with close scores and low overall confidence
        candidates = result.get("candidates", [])
        overall = result.get("profile", {}).get("overall_confidence", 0.0)
        needs_disamb = False
        questions = None
        if len(candidates) == 0:
            needs_disamb = True
            questions = [
                "Which company did you most recently work at?",
                "Which school did you attend most recently?",
                "Do you use a public username/handle we can match?",
            ]
        elif len(candidates) == 1 and overall < 0.7:
            needs_disamb = True
            questions = [
                "Does this look like you (name/location)? If yes, confirm your recent employer.",
                "Any other city you’re associated with?",
            ]
        elif len(candidates) >= 2 and overall < 0.6:
            top = sorted((candidates), key=lambda c: c.get("score", 0), reverse=True)
            if len(top) >= 2 and abs(top[0].get("score", 0) - top[1].get("score", 0)) < 0.15:
                needs_disamb = True
                questions = [
                    "Which of these is most correct: your current city or last known city?",
                    "Which company did you most recently work at?",
                ]

        if needs_disamb:
            logger.info({"event": "job_needs_disambiguation", "job_id": job_id})
            update_job(job_id, status=JobStatus.needs_disambiguation, result=result, error=None, questions=questions)
        else:
            logger.info({"event": "job_completed", "job_id": job_id, "latency_ms": result["metrics"]["latency_ms"]})
            update_job(job_id, status=JobStatus.completed, result=result, error=None)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception({"event": "job_failed", "job_id": job_id, "error": str(exc)})
        update_job(job_id, status=JobStatus.failed, error=str(exc))

