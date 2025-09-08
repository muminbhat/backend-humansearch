from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..schemas.search import NormalizedQuery
from ..schemas.profile import EvidenceItem, IdentityCandidate


class BaseConnector(ABC):
    name: str = "base"
    enabled: bool = True

    @abstractmethod
    async def fetch(self, query: NormalizedQuery) -> Dict[str, Any]:
        """
        Return shape:
        {
            "evidences": List[EvidenceItem],
            "candidates": List[IdentityCandidate]
        }
        """
        raise NotImplementedError


def make_result(
    evidences: List[EvidenceItem] | None = None,
    candidates: List[IdentityCandidate] | None = None,
) -> Dict[str, Any]:
    return {
        "evidences": evidences or [],
        "candidates": candidates or [],
    }

