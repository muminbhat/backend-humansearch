from abc import ABC, abstractmethod
from typing import Dict, Any
from ..schemas.search import NormalizedQuery


class BaseScraper(ABC):
    name: str = "base_scraper"

    @abstractmethod
    async def scrape(self, query: NormalizedQuery) -> Dict[str, Any]:
        raise NotImplementedError

