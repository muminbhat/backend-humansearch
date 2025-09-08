from typing import Dict, Any, List
from ..schemas.search import NormalizedQuery
from ..schemas.profile import EvidenceItem, IdentityCandidate, Provenance
from ..schemas.common import SourceMethod
from ..core.config import settings
from ..core.http import http_get


class PeopleDataLabsSearchConnector:
    name = "people_data_labs_search"

    async def fetch(self, query: NormalizedQuery) -> Dict[str, Any]:
        if not settings.pdl_api_key:
            return {"evidences": [], "candidates": []}

        # Prefer name + location for search
        if not query.full_name and not query.location:
            return {"evidences": [], "candidates": []}

        url = "https://api.peopledatalabs.com/v5/person/search"
        headers = {"X-API-Key": settings.pdl_api_key}
        # Build multiple attempts: (name+location), (name only), (first name + location)
        attempts: List[dict] = []
        if query.full_name and query.location:
            q = f"full_name:\"{query.full_name}\" AND (location_name:\"{query.location}\" OR location_country:\"{query.location}\")"
            attempts.append({"query": q, "size": 5})
        if query.full_name:
            q = f"full_name:\"{query.full_name}\""
            attempts.append({"query": q, "size": 5})
        # First name heuristic
        if query.full_name and query.location:
            first = query.full_name.split(" ")[0]
            q = f"full_name:\"{first}\" AND location_name:\"{query.location}\""
            attempts.append({"query": q, "size": 5})

        data = None
        for params in attempts:
            try:
                resp = await http_get(url, params=params, headers=headers, timeout=10.0, disable_cache=True)
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                if payload and isinstance(payload, dict) and payload.get("data"):
                    data = payload
                    break
            except Exception:
                continue
        if data is None:
            return {"evidences": [], "candidates": []}

        prov = Provenance(source_name=self.name, method=SourceMethod.api, url=None)
        candidates: List[IdentityCandidate] = []
        evidences: List[EvidenceItem] = []

        docs = data.get("data") if isinstance(data, dict) else None
        if not isinstance(docs, list):
            return {"evidences": evidences, "candidates": candidates}

        for doc in docs[:5]:
            if not isinstance(doc, dict):
                continue
            full_name = doc.get("full_name")
            emails = []
            if isinstance(doc.get("emails"), list):
                emails = [e.get("address") if isinstance(e, dict) else e for e in doc["emails"] if e]
                emails = [e for e in emails if isinstance(e, str)]
            phones = []
            if isinstance(doc.get("phone_numbers"), list):
                phones = [p.get("number") if isinstance(p, dict) else p for p in doc["phone_numbers"] if p]
                phones = [p for p in phones if isinstance(p, str)]
            location = None
            if isinstance(doc.get("location_general"), dict):
                location = doc["location_general"].get("display")
            links = []
            if isinstance(doc.get("links"), list):
                for l in doc["links"]:
                    if isinstance(l, dict) and isinstance(l.get("url"), str):
                        links.append(l["url"])

            cand = IdentityCandidate(
                display_name=full_name,
                emails=emails,
                phones=phones,
                usernames=[],
                locations=[location] if location else [],
                links=links,
                score=0.4,
                top_evidence=[
                    EvidenceItem(field="full_name", value=full_name, confidence=0.6, provenance=prov)
                ] if full_name else [],
            )
            candidates.append(cand)

        for c in candidates:
            for url_candidate in c.links:
                evidences.append(EvidenceItem(field="link", value=url_candidate, confidence=0.4, provenance=prov))

        return {"evidences": evidences, "candidates": candidates}

