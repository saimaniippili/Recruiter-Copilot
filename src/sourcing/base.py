from abc import ABC, abstractmethod
from typing import List
from ..core.schemas import SearchResultSchema


class SearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def search(self, query: str, max_results: int = 10, timeout: int = 35) -> List[SearchResultSchema]:
        """Executes search query and returns normalized search results."""
        pass
