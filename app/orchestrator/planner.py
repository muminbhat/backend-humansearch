from typing import List, Dict, Any
from ..schemas.search import NormalizedQuery


def plan_tools(query: NormalizedQuery, budget_ms: int) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    time_left = budget_ms
    # Simple rules: email -> PDL enrich; username -> GitHub; name+location -> PDL search
    # Context-only (no name/email/phone/username/location): try search engine first
    if not (query.full_name or query.email or query.phone or query.username or query.location):
        steps.append({"tool": "duckduckgo", "timeout_ms": min(6000, time_left)})
        time_left -= steps[-1]["timeout_ms"]
        return steps
    if query.email:
        steps.append({"tool": "pdl", "timeout_ms": min(5000, time_left)})
        time_left -= steps[-1]["timeout_ms"]
    elif query.full_name and query.location and time_left > 0:
        steps.append({"tool": "pdl_identify", "timeout_ms": min(5000, time_left)})
        time_left -= steps[-1]["timeout_ms"]
        if time_left > 0:
            steps.append({"tool": "pdl_search", "timeout_ms": min(5000, time_left)})
            time_left -= steps[-1]["timeout_ms"]
        if time_left > 0:
            steps.append({"tool": "duckduckgo", "timeout_ms": min(5000, time_left)})
            time_left -= steps[-1]["timeout_ms"]
    if query.username and time_left > 0:
        steps.append({"tool": "github", "timeout_ms": min(4000, time_left)})
        time_left -= steps[-1]["timeout_ms"]
    if not steps and time_left > 0:
        steps.append({"tool": "pdl", "timeout_ms": min(5000, time_left)})
        time_left -= steps[-1]["timeout_ms"]
    return steps

