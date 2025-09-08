from typing import Dict, Any, List
from ..core.http import http_get
from ..schemas.search import NormalizedQuery
from ..schemas.profile import EvidenceItem, IdentityCandidate, Provenance
from ..schemas.common import SourceMethod
from ..core.config import settings
from .base import BaseConnector, make_result


class PeopleDataLabsConnector(BaseConnector):
    name = "people_data_labs"

    async def fetch(self, query: NormalizedQuery) -> Dict[str, Any]:
        # If no API key, fall back to a minimal heuristic result
        if not settings.pdl_api_key:
            prov = Provenance(source_name=self.name, method=SourceMethod.api, url=None)
            evidences: List[EvidenceItem] = []
            candidates: List[IdentityCandidate] = []
            if query.email:
                candidates.append(
                    IdentityCandidate(
                        display_name=query.full_name or None,
                        emails=[query.email],
                        usernames=[query.username] if query.username else [],
                        locations=[query.location] if query.location else [],
                        score=0.3,
                        top_evidence=[
                            EvidenceItem(field="email", value=query.email, confidence=0.6, provenance=prov)
                        ],
                    )
                )
            return make_result(evidences=evidences, candidates=candidates)

        # Real API call path (best-effort)
        url = "https://api.peopledatalabs.com/v5/person/enrich"
        headers = {"X-API-Key": settings.pdl_api_key}
        params: Dict[str, Any] = {}
        if query.email:
            params["email"] = query.email
        if query.phone:
            params["phone"] = query.phone
        if query.full_name:
            params["name"] = query.full_name
        if query.username:
            # PDL supports linkedin/github/twitter handles; we pass generically
            params["username"] = query.username
        if query.location:
            params["location"] = query.location

        try:
            logger_headers = {k: ("***" if k.lower() == "x-api-key" else v) for k, v in (headers or {}).items()}
            resp = await http_get(url, params=params, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # On failure, return empty so aggregator handles gracefully
            return make_result()

        prov = Provenance(source_name=self.name, method=SourceMethod.api, url=None)
        evidences: List[EvidenceItem] = []
        candidates: List[IdentityCandidate] = []

        # Parse a few common fields defensively
        person = data.get("data") or data
        emails = []
        if isinstance(person.get("emails"), list):
            emails = [e.get("address") if isinstance(e, dict) else e for e in person["emails"]]
            emails = [e for e in emails if isinstance(e, str)]
        phones = []
        if isinstance(person.get("phone_numbers"), list):
            phones = [p.get("number") if isinstance(p, dict) else p for p in person["phone_numbers"]]
            phones = [p for p in phones if isinstance(p, str)]
        full_name = person.get("full_name") or query.full_name
        location = None
        if isinstance(person.get("location_general"), dict):
            location = person["location_general"].get("display")

        links = []
        if isinstance(person.get("links"), list):
            for l in person["links"]:
                if isinstance(l, dict) and isinstance(l.get("url"), str):
                    links.append(l["url"])

        employment = []
        if isinstance(person.get("employment"), list):
            for emp in person["employment"]:
                if isinstance(emp, dict):
                    employment.append({
                        "title": emp.get("title"),
                        "organization": emp.get("name") or emp.get("company") or emp.get("employer"),
                        "start": emp.get("start_date"),
                        "end": emp.get("end_date"),
                    })

        education = []
        if isinstance(person.get("education"), list):
            for edu in person["education"]:
                if isinstance(edu, dict):
                    education.append({
                        "school": edu.get("school"),
                        "degree": edu.get("degree"),
                        "start": edu.get("start_date"),
                        "end": edu.get("end_date"),
                    })

        if emails or phones or full_name:
            candidates.append(
                IdentityCandidate(
                    display_name=full_name,
                    emails=emails or ([query.email] if query.email else []),
                    phones=phones or ([query.phone] if query.phone else []),
                    usernames=[query.username] if query.username else [],
                    locations=[location] if location else ([query.location] if query.location else []),
                    links=links,
                    score=0.5,
                    top_evidence=[
                        EvidenceItem(field="full_name", value=full_name, confidence=0.7, provenance=prov)
                    ] if full_name else [],
                )
            )

        # Attach structured fields as evidences for traceability
        for url in links:
            evidences.append(EvidenceItem(field="link", value=url, confidence=0.5, provenance=prov))
        for emp in employment:
            evidences.append(EvidenceItem(field="employment", value=emp, confidence=0.5, provenance=prov))
        for edu in education:
            evidences.append(EvidenceItem(field="education", value=edu, confidence=0.5, provenance=prov))

        return make_result(evidences=evidences, candidates=candidates)

