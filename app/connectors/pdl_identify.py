from typing import Dict, Any, List, Tuple
from ..schemas.search import NormalizedQuery
from ..schemas.profile import EvidenceItem, IdentityCandidate, Provenance
from ..schemas.common import SourceMethod
from ..core.config import settings
from ..core.http import http_get


def _split_name(full_name: str) -> Tuple[str, str]:
    parts = [p for p in (full_name or "").strip().split(" ") if p]
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


class PeopleDataLabsIdentifyConnector:
    name = "people_data_labs_identify"

    async def fetch(self, query: NormalizedQuery) -> Dict[str, Any]:
        if not settings.pdl_api_key:
            return {"evidences": [], "candidates": []}

        if not query.full_name and not query.location:
            return {"evidences": [], "candidates": []}

        url = "https://api.peopledatalabs.com/v5/person/identify"
        headers = {"X-API-Key": settings.pdl_api_key}

        first, last = _split_name(query.full_name or "")
        attempts: List[Dict[str, Any]] = []
        if first or last:
            params = {"first_name": first or None, "last_name": last or None}
            if query.location:
                # PDL docs often use 'region' for city/state string
                params["region"] = query.location
            # remove None
            params = {k: v for k, v in params.items() if v}
            attempts.append(params)
        if first and query.location:
            attempts.append({"first_name": first, "region": query.location})

        data = None
        for params in attempts:
            try:
                resp = await http_get(url, params=params, headers=headers, timeout=10.0, disable_cache=True)
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                # Identify returns matches (array) and sometimes top-level person
                if isinstance(payload, dict) and (payload.get("matches") or payload.get("data") or payload.get("full_name")):
                    data = payload
                    break
            except Exception:
                continue
        if data is None:
            return {"evidences": [], "candidates": []}

        prov = Provenance(source_name=self.name, method=SourceMethod.api, url=None)
        evidences: List[EvidenceItem] = []
        candidates: List[IdentityCandidate] = []

        # The identify API may return top-level fields rather than nested in 'data'
        matches = None
        if isinstance(data, dict) and isinstance(data.get("matches"), list):
            matches = data["matches"]
        person = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else (data if isinstance(data, dict) else None)
        docs = matches if matches is not None else ([person] if person else [])
        if not isinstance(docs, list):
            return {"evidences": evidences, "candidates": candidates}

        for person in docs:
            if not isinstance(person, dict):
                continue
            full_name = person.get("full_name") or f"{person.get('first_name','')} {person.get('last_name','')}".strip()
            emails = []
            if isinstance(person.get("emails"), list):
                emails = [e.get("address") if isinstance(e, dict) else e for e in person["emails"] if e]
                emails = [e for e in emails if isinstance(e, str)]
            phones = []
            if isinstance(person.get("phone_numbers"), list):
                phones = [p.get("number") if isinstance(p, dict) else p for p in person["phone_numbers"] if p]
                phones = [p for p in phones if isinstance(p, str)]
            location = None
            if isinstance(person.get("location_general"), dict):
                location = person["location_general"].get("display")
            elif isinstance(person.get("location_name"), str):
                location = person.get("location_name")

            links = []
            if isinstance(person.get("links"), list):
                for l in person["links"]:
                    if isinstance(l, dict) and isinstance(l.get("url"), str):
                        links.append(l["url"])

            cand = IdentityCandidate(
                display_name=full_name or query.full_name,
                emails=emails,
                phones=phones,
                usernames=[],
                locations=[location] if location else ([query.location] if query.location else []),
                links=links,
                score=0.45,
                top_evidence=[
                    EvidenceItem(field="full_name", value=full_name or query.full_name, confidence=0.65, provenance=prov)
                ] if (full_name or query.full_name) else [],
            )
            candidates.append(cand)

            for url_val in links:
                evidences.append(EvidenceItem(field="link", value=url_val, confidence=0.5, provenance=prov))

        return {"evidences": evidences, "candidates": candidates}

