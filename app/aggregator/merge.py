from typing import List, Dict, Any
from ..schemas.profile import EvidenceItem, IdentityCandidate, PersonProfile


def merge_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    evidences: List[EvidenceItem] = []
    candidates: List[IdentityCandidate] = []
    for r in results:
        evidences.extend(r.get("evidences", []))
        candidates.extend(r.get("candidates", []))

    # Naive aggregation for MVP: pick highest-score candidate as primary
    primary = max(candidates, key=lambda c: c.score, default=None)

    profile = PersonProfile(
        names=[primary.display_name] if (primary and primary.display_name) else [],
        emails=list({e for c in candidates for e in c.emails}),
        phones=list({p for c in candidates for p in c.phones}),
        usernames=list({u for c in candidates for u in c.usernames}),
        locations=list({l for c in candidates for l in c.locations}),
        links=[*{*([l for c in candidates for l in c.links])}],
        evidences=evidences,
        overall_confidence=max((c.score for c in candidates), default=0.0),
    )

    return {
        "profile": profile.model_dump(),
        "candidates": [c.model_dump() for c in candidates],
    }

