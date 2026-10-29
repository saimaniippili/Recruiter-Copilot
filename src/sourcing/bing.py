import base64
import urllib.parse
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests

from .base import SearchProvider
from ..core.schemas import SearchResultSchema


def decode_bing_link(href: str) -> str:
    """Decodes Bing redirect link containing base64 target URL."""
    if "/ck/a?" in href:
        parsed = urllib.parse.urlparse(href)
        params = urllib.parse.parse_qs(parsed.query)
        if "u" in params:
            u_val = params["u"][0]
            if u_val.startswith("a1"):
                padding = "=" * ((4 - len(u_val[2:]) % 4) % 4)
                try:
                    return base64.b64decode(u_val[2:] + padding).decode("utf-8", errors="ignore")
                except Exception:
                    pass
    return href


class BingSearchProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "bing"

    def search(self, query: str, max_results: int = 10, timeout: int = 20) -> List[SearchResultSchema]:
        # Adapt Google-specific site syntax for Bing if needed
        clean_q = query.replace("site:uk.linkedin.com/in", "linkedin.com/in").replace("site:nl.linkedin.com/in", "linkedin.com/in").replace("site:linkedin.com/in", "linkedin.com/in")
        if "linkedin" not in clean_q.lower():
            clean_q = f"{clean_q} linkedin"

        results = []
        now_iso = datetime.utcnow().isoformat()
        try:
            r = requests.get(
                "https://www.bing.com/search",
                params={"q": clean_q, "count": max_results},
                timeout=timeout,
                impersonate="chrome120"
            )
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "html.parser")
            for li in soup.find_all("li", class_="b_algo"):
                h2 = li.find("h2")
                p = li.find("p")
                a = h2.find("a") if h2 else None
                if a:
                    title = a.get_text()
                    link = decode_bing_link(a.get("href", ""))
                    snippet = p.get_text() if p else ""
                    if "linkedin.com/in/" in link:
                        results.append(
                            SearchResultSchema(
                                title=title,
                                url=link,
                                snippet=snippet,
                                provider=self.name,
                                query_used=query,
                                retrieved_at=now_iso
                            )
                        )
                    if len(results) >= max_results:
                        break
        except Exception as e:
            print(f"[Warning] BingSearchProvider error: {e}")
        return results
