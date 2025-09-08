from typing import Dict, Any
from ..schemas.search import NormalizedQuery
from ..schemas.profile import EvidenceItem, IdentityCandidate, Provenance
from ..schemas.common import SourceMethod
from .base import BaseConnector, make_result


class ClearbitConnector(BaseConnector):
    name = "clearbit"

    async def fetch(self, query: NormalizedQuery) -> Dict[str, Any]:
        prov = Provenance(source_name=self.name, method=SourceMethod.api, url=None)
        evidences = []
        candidates = []
        # Stub: if username present, produce a candidate
        if query.username:
            candidates.append(
                IdentityCandidate(
                    display_name=query.full_name or None,
                    usernames=[query.username],
                    emails=[query.email] if query.email else [],
                    locations=[query.location] if query.location else [],
                    score=0.25,
                    top_evidence=[
                        EvidenceItem(field="username", value=query.username, confidence=0.55, provenance=prov)
                    ],
                )
            )
        return make_result(evidences=evidences, candidates=candidates)

