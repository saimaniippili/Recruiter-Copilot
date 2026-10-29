import os
import requests
from typing import List, Dict, Any, Optional
from ..core.config import settings
from ..core.schemas import SearchResultSchema


class GitHubSearchProvider:
    """
    Sourcing technical talent directly from GitHub via the GitHub Search API.
    Identifies developers based on language proficiency, geography, and active open-source footprint.
    """
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("GITHUB_TOKEN", "")
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RecruiterCopilot-AI/1.0"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def search_developers(
        self,
        keywords: str = "",
        language: Optional[str] = None,
        location: Optional[str] = None,
        min_followers: int = 2,
        min_repos: int = 3,
        max_results: int = 10,
        timeout: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Executes a targeted search query against GitHub developers.
        Returns rich profiles including bio, public repos, top projects, and links.
        """
        query_parts = []
        if keywords:
            query_parts.append(keywords.strip())
        if language:
            query_parts.append(f"language:{language.strip().lower()}")
        if location:
            query_parts.append(f"location:\"{location.strip()}\"")
        if min_followers > 0:
            query_parts.append(f"followers:>={min_followers}")
        if min_repos > 0:
            query_parts.append(f"repos:>={min_repos}")

        query_str = " ".join(query_parts) if query_parts else "type:user"
        params = {
            "q": query_str,
            "sort": "followers",
            "order": "desc",
            "per_page": min(max_results, 30)
        }

        candidates = []
        try:
            resp = requests.get(
                f"{self.base_url}/search/users",
                headers=self._get_headers(),
                params=params,
                timeout=timeout
            )
            if resp.status_code != 200:
                print(f"[GitHubSearchProvider] API returned {resp.status_code}: {resp.text[:200]}")
                return []

            items = resp.json().get("items", [])
            for item in items[:max_results]:
                username = item.get("login")
                profile_url = item.get("html_url")
                avatar_url = item.get("avatar_url")

                # Enrich with detailed user profile
                user_detail = self._get_user_details(username, timeout=timeout)
                top_repos = self._get_top_repositories(username, timeout=timeout)

                candidate_info = {
                    "username": username,
                    "name": user_detail.get("name") or username,
                    "profile_url": profile_url,
                    "avatar_url": avatar_url,
                    "company": user_detail.get("company") or "Independent / Undisclosed",
                    "location": user_detail.get("location") or location or "Undisclosed",
                    "bio": user_detail.get("bio") or "",
                    "blog": user_detail.get("blog") or "",
                    "email": user_detail.get("email") or "",
                    "public_repos": user_detail.get("public_repos", 0),
                    "followers": user_detail.get("followers", 0),
                    "top_repos": top_repos,
                    "source": "github"
                }
                candidates.append(candidate_info)

        except Exception as e:
            print(f"[GitHubSearchProvider] Error searching GitHub: {e}")

        return candidates

    def _get_user_details(self, username: str, timeout: int = 10) -> Dict[str, Any]:
        """Fetches individual user metadata."""
        try:
            resp = requests.get(
                f"{self.base_url}/users/{username}",
                headers=self._get_headers(),
                timeout=timeout
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def _get_top_repositories(self, username: str, timeout: int = 10) -> List[Dict[str, Any]]:
        """Fetches top 3 repositories by star count."""
        try:
            resp = requests.get(
                f"{self.base_url}/users/{username}/repos",
                headers=self._get_headers(),
                params={"sort": "updated", "per_page": 5},
                timeout=timeout
            )
            if resp.status_code == 200:
                repos = resp.json()
                sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
                return [
                    {
                        "name": r.get("name"),
                        "description": r.get("description") or "No description",
                        "stars": r.get("stargazers_count", 0),
                        "language": r.get("language") or "",
                        "url": r.get("html_url")
                    }
                    for r in sorted_repos[:3]
                ]
        except Exception:
            pass
        return []
