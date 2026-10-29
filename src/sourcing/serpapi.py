import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import SearchProvider
from ..core.schemas import SearchResultSchema
from ..core.config import settings


class SerpApiSearchProvider(SearchProvider):
    """
    Requirement C & 6: Localized Google Search Provider via SerpApi.
    Supports engine localization (gl, hl, location, google_domain) without hardcoded assumptions.
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.SERPAPI_API_KEY
        self.quota_exhausted = False
        self.last_error = ""

    @property
    def name(self) -> str:
        return "serpapi"

    def search(
        self,
        query: str,
        max_results: int = 10,
        timeout: int = 15,
        target_country: str = "nl",
        target_location: Optional[str] = None
    ) -> List[SearchResultSchema]:
        if not self.api_key:
            return []

        # Localized parameters for targeted European/Global search
        gl = target_country.lower() if target_country else "nl"
        google_domain = f"google.{gl}" if gl in ("nl", "de", "uk", "fr", "es", "it") else "google.com"

        params: Dict[str, Any] = {
            "engine": "google",
            "q": query,
            "api_key": self.api_key,
            "num": max_results,
            "gl": gl,
            "hl": "en",
            "google_domain": google_domain
        }
        if target_location:
            params["location"] = target_location

        try:
            resp = requests.get("https://serpapi.com/search", params=params, timeout=timeout)
            if resp.status_code == 429:
                self.quota_exhausted = True
                self.last_error = "HTTP 429: SerpApi monthly quota exhausted"
                return []
            if resp.status_code != 200:
                try:
                    err_json = resp.json()
                    err_msg = str(err_json.get("error", ""))
                    if "run out of searches" in err_msg.lower():
                        self.quota_exhausted = True
                    self.last_error = err_msg
                except Exception:
                    self.last_error = f"HTTP {resp.status_code}"
                return []

            resp.encoding = 'utf-8'
            data = resp.json()
            organic = data.get("organic_results", [])
            results = []
            now_iso = datetime.utcnow().isoformat()

            for item in organic:
                link = item.get("link", "")
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                if link:
                    results.append(
                        SearchResultSchema(
                            title=title,
                            url=link,
                            snippet=snippet,
                            provider=self.name,
                            query_used=query,
                            retrieved_at=now_iso,
                            metadata={"position": item.get("position"), "source": "organic"}
                        )
                    )
            return results
        except Exception as e:
            self.last_error = str(e)
            return []
