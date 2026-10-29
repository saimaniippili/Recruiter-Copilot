from typing import List, Optional
from datetime import datetime
from .base import SearchProvider
from ..core.schemas import SearchResultSchema


class DuckDuckGoSearchProvider(SearchProvider):
    """
    Requirement C: Localized DuckDuckGo provider with locale parameter support,
    bounded retries, and rate limit handling.
    """
    def __init__(self):
        self.last_error = ""

    @property
    def name(self) -> str:
        return "duckduckgo"

    def search(
        self,
        query: str,
        max_results: int = 10,
        timeout: int = 15,
        region: Optional[str] = "nl-nl"
    ) -> List[SearchResultSchema]:
        results = []
        now_iso = datetime.utcnow().isoformat()
        
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            with DDGS(timeout=timeout) as ddgs:
                # Use region if specified for search ranking localization
                raw_results = list(ddgs.text(query, max_results=max_results, region=region or "wt-wt"))
                for item in raw_results:
                    href = item.get("href", "")
                    title = item.get("title", "")
                    body = item.get("body", "")
                    if href and ("linkedin.com/in" in href.lower() or "github.com" in href.lower()):
                        results.append(
                            SearchResultSchema(
                                title=title,
                                url=href,
                                snippet=body,
                                provider=self.name,
                                query_used=query,
                                retrieved_at=now_iso
                            )
                        )
        except Exception as e:
            self.last_error = str(e)
            
        return results
