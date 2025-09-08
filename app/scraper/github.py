from typing import Dict, Any
from ..core.http import http_get
from ..schemas.search import NormalizedQuery
from ..schemas.profile import EvidenceItem, IdentityCandidate, Provenance
from ..schemas.common import SourceMethod
from .base import BaseScraper


class GitHubScraper(BaseScraper):
    name = "github"

    async def scrape(self, query: NormalizedQuery) -> Dict[str, Any]:
        evidences = []
        candidates = []
        if not query.username:
            return {"evidences": evidences, "candidates": candidates}
        username = query.username
        url = f"https://api.github.com/users/{username}"
        try:
            resp = await http_get(url, headers={"Accept": "application/vnd.github+json"}, timeout=8.0)
            if resp.status_code == 404:
                prov = Provenance(source_name=self.name, method=SourceMethod.scrape, url=None)
                candidates.append(
                    IdentityCandidate(
                        display_name=query.full_name or None,
                        usernames=[username],
                        score=0.2,
                        top_evidence=[EvidenceItem(field="username", value=username, confidence=0.5, provenance=prov)],
                    )
                )
                return {"evidences": evidences, "candidates": candidates}
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # On error, return minimal candidate
            prov = Provenance(source_name=self.name, method=SourceMethod.scrape, url=None)
            candidates.append(
                IdentityCandidate(
                    display_name=query.full_name or None,
                    usernames=[username],
                    score=0.2,
                    top_evidence=[EvidenceItem(field="username", value=username, confidence=0.5, provenance=prov)],
                )
            )
            return {"evidences": evidences, "candidates": candidates}

        prov = Provenance(source_name=self.name, method=SourceMethod.scrape, url=data.get("html_url"))
        display = data.get("name") or query.full_name
        bio = data.get("bio")
        blog = data.get("blog")
        company = data.get("company")
        location = data.get("location")

        cand = IdentityCandidate(
            display_name=display,
            usernames=[username],
            locations=[location] if location else [],
            links=[data.get("html_url")] if data.get("html_url") else [],
            score=0.35,
            top_evidence=[EvidenceItem(field="username", value=username, confidence=0.6, provenance=prov)],
        )
        candidates.append(cand)

        if bio:
            evidences.append(EvidenceItem(field="bio", value=bio, confidence=0.5, provenance=prov))
        if blog:
            evidences.append(EvidenceItem(field="website", value=blog, confidence=0.5, provenance=prov))
        if company:
            evidences.append(EvidenceItem(field="employment", value={"organization": company}, confidence=0.4, provenance=prov))
        if location:
            evidences.append(EvidenceItem(field="location", value=location, confidence=0.5, provenance=prov))

        return {"evidences": evidences, "candidates": candidates}

