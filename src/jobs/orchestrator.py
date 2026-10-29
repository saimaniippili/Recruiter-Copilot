import uuid
import threading
from typing import Callable, Optional, List, Dict, Any
from ..core.schemas import (
    JobDescriptionSchema, CandidateSchema, SearchResultSchema,
    JobStateEnum, MatchStatus, GeographicEligibilityStatus
)
from ..core.config import settings
from ..storage.db import repo
from ..llm.extraction import extract_job_description
from ..sourcing.serpapi import SerpApiSearchProvider
from ..sourcing.ddg import DuckDuckGoSearchProvider
from ..sourcing.bing import BingSearchProvider
from ..sourcing.query_builder import build_search_queries
from ..sourcing.normalize import normalize_search_results
from ..scoring.engine import score_and_rank_candidates
from ..exports.csv_export import export_candidates_to_csv


class JobOrchestrator:
    def __init__(self):
        self.serpapi_provider = SerpApiSearchProvider()
        self.ddg_provider = DuckDuckGoSearchProvider()
        self.bing_provider = BingSearchProvider()

    def run_sourcing_pipeline(
        self,
        job_id: str,
        chat_id: int,
        raw_jd_text: str,
        progress_callback: Optional[Callable[[str], None]] = None,
        override_role_title: Optional[str] = None,
        override_location: Optional[str] = None,
        override_mandatory_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end recruitment sourcing pipeline with full audit telemetry (Requirement 21 & 22):
        1. Parse JD -> 2. Query Portfolio -> 3. Localized Search Providers (Cache -> SerpApi -> DDG -> Bing)
        -> 4. Canonicalize & Deduplicate -> 5. 3-Tier Geographic Verification & ATS Scoring
        -> 6. Export CSV & Database Persistence.
        """
        providers_attempted = []
        providers_succeeded = []
        providers_failed = []
        queries_executed_count = 0

        try:
            # 1. Parsing
            repo.update_job_state(job_id, JobStateEnum.PARSING)
            if progress_callback:
                progress_callback("[STAGE 1/4] Extracting structured job requirements...")

            jd: JobDescriptionSchema = extract_job_description(raw_jd_text)

            # Apply user overrides if provided from the Web UI
            if override_role_title and override_role_title.strip():
                jd.role_title = override_role_title.strip()
            if override_location is not None:
                cleaned_loc = override_location.strip()
                jd.locations = [cleaned_loc] if cleaned_loc and cleaned_loc.lower() not in ("global", "any", "remote") else []
            if override_mandatory_skills:
                from ..core.schemas import RequirementSchema, RequirementImportance
                jd.mandatory_requirements = [
                    RequirementSchema(
                        requirement_id=f"req_m_{idx+1}",
                        normalized_name=name.strip(),
                        importance=RequirementImportance.MANDATORY
                    ) for idx, name in enumerate(override_mandatory_skills) if name.strip()
                ]
            repo.update_job_state(
                job_id,
                JobStateEnum.PARSING,
                role_title=jd.role_title,
                structured_jd_json=jd.model_dump_json()
            )

            # 2. Query Planning
            queries = build_search_queries(jd, max_queries=settings.MAX_SEARCH_QUERIES_PER_JOB)
            repo.update_job_state(job_id, JobStateEnum.SEARCHING)

            mand_summary = ", ".join([r.normalized_name for r in jd.mandatory_requirements[:4]]) or "Core competencies"
            exp_summary = f"{jd.experience_min_years or ''}-{jd.experience_max_years or ''} yrs" if jd.experience_min_years else "Industry aligned"
            if progress_callback:
                progress_callback(
                    f"[REQUIREMENTS PARSED]\n"
                    f"Role: {jd.role_title} ({jd.role_family.value.replace('_', ' ').title()})\n"
                    f"Experience Target: {exp_summary}\n"
                    f"Must-Haves: {mand_summary}\n\n"
                    f"[STAGE 2/4] Querying search indexes ({len(queries)} query variations)..."
                )

            # 3. Search Provider Orchestration (with Cache & Fallback)
            raw_results: List[SearchResultSchema] = []
            target_country = "nl" if any("netherlands" in l.lower() or "eindhoven" in l.lower() for l in jd.locations) else "us"
            target_loc = jd.locations[0] if jd.locations else None

            for q in queries:
                queries_executed_count += 1
                # Check Cache
                cached = repo.get_cached_search("serpapi", q) or repo.get_cached_search("duckduckgo", q)
                valid_cached = [r for r in (cached or []) if "linkedin.com/in" in (r.url or "").lower() or "github.com" in (r.url or "").lower()]
                if valid_cached:
                    raw_results.extend(valid_cached)
                    if "cache" not in providers_succeeded:
                        providers_succeeded.append("cache")
                    continue

                # Try SerpApi (Localized)
                if "serpapi" not in providers_attempted:
                    providers_attempted.append("serpapi")
                provider_res = self.serpapi_provider.search(
                    q,
                    max_results=settings.MAX_RESULTS_PER_QUERY,
                    timeout=settings.SEARCH_TIMEOUT_SECONDS,
                    target_country=target_country,
                    target_location=target_loc
                )
                valid_provider_res = [r for r in (provider_res or []) if "linkedin.com/in" in (r.url or "").lower()]
                if valid_provider_res:
                    if "serpapi" not in providers_succeeded:
                        providers_succeeded.append("serpapi")
                    repo.cache_search_results("serpapi", q, valid_provider_res)
                    raw_results.extend(valid_provider_res)
                else:
                    if self.serpapi_provider.last_error and "serpapi" not in providers_failed:
                        providers_failed.append(f"serpapi: {self.serpapi_provider.last_error}")

                    # Fallback to secondary provider (DuckDuckGo localized)
                    if "duckduckgo" not in providers_attempted:
                        providers_attempted.append("duckduckgo")
                    ddg_region = "nl-nl" if target_country == "nl" else "wt-wt"
                    ddg_res = self.ddg_provider.search(q, max_results=settings.MAX_RESULTS_PER_QUERY, region=ddg_region)
                    valid_ddg_res = [r for r in (ddg_res or []) if "linkedin.com/in" in (r.url or "").lower() or "github.com" in (r.url or "").lower()]
                    if valid_ddg_res:
                        if "duckduckgo" not in providers_succeeded:
                            providers_succeeded.append("duckduckgo")
                        repo.cache_search_results("duckduckgo", q, valid_ddg_res)
                        raw_results.extend(valid_ddg_res)
                    else:
                        if self.ddg_provider.last_error and "duckduckgo" not in providers_failed:
                            providers_failed.append(f"duckduckgo: {self.ddg_provider.last_error}")

                        # Fallback to tertiary provider (Bing)
                        if "bing" not in providers_attempted:
                            providers_attempted.append("bing")
                        bing_res = self.bing_provider.search(q, max_results=settings.MAX_RESULTS_PER_QUERY)
                        valid_bing_res = [r for r in (bing_res or []) if "linkedin.com/in" in (r.url or "").lower()]
                        if valid_bing_res:
                            if "bing" not in providers_succeeded:
                                providers_succeeded.append("bing")
                            repo.cache_search_results("bing", q, valid_bing_res)
                            raw_results.extend(valid_bing_res)

                if len(raw_results) >= settings.MAX_CANDIDATES_EVALUATED * 2:
                    break

            # 4. Normalization & Deduplication with 3-Tier Geo-Fencing
            expected_subdomain = ""
            if jd.locations:
                import re
                from ..sourcing.query_builder import COUNTRY_SUBDOMAINS
                loc_lower = jd.locations[0].lower()
                for name, code in COUNTRY_SUBDOMAINS.items():
                    if re.search(r'\b' + re.escape(name) + r'\b', loc_lower):
                        expected_subdomain = code
                        break

            candidates = normalize_search_results(raw_results, expected_subdomain=expected_subdomain)

            if not candidates:
                if getattr(self.serpapi_provider, "quota_exhausted", False):
                    err_msg = "Search quota exhausted: SerpApi monthly search limit reached (HTTP 429). Please update SERPAPI_KEY in .env."
                    repo.update_job_state(job_id, JobStateEnum.FAILED, error_message=err_msg)
                    raise RuntimeError(err_msg)
                repo.update_job_state(job_id, JobStateEnum.FAILED, error_message="No matching candidates found in target location.")
                return {
                    "job_id": job_id,
                    "status": "FAILED",
                    "retrieval": {
                        "providers_attempted": providers_attempted,
                        "providers_succeeded": providers_succeeded,
                        "providers_failed": providers_failed,
                        "queries_executed": queries_executed_count,
                        "raw_results": len(raw_results),
                        "unique_candidates": 0
                    },
                    "summary": {
                        "explicit_matches": 0,
                        "partial_matches": 0,
                        "location_mismatches": 0,
                        "insufficient_evidence": 0
                    },
                    "candidates": []
                }

            # 5. Deterministic Scoring with Hard Geographic Gate
            repo.update_job_state(job_id, JobStateEnum.EVALUATING)
            if progress_callback:
                progress_callback(f"[STAGE 3/4] Evaluating {len(candidates)} candidate profiles against evidence rubric...")

            ranked_candidates = score_and_rank_candidates(jd, candidates[:settings.MAX_CANDIDATES_EVALUATED])

            # 6. Export to CSV & Storage
            repo.update_job_state(job_id, JobStateEnum.EXPORTING)
            export_candidates_to_csv(job_id, ranked_candidates)
            repo.save_candidates(job_id, ranked_candidates)
            repo.update_job_state(job_id, JobStateEnum.COMPLETED)

            # 7. Summary metrics (Requirement 22)
            summary_metrics = {
                "explicit_matches": sum(1 for c in ranked_candidates if c.match_status == MatchStatus.EXPLICIT_MATCH),
                "partial_matches": sum(1 for c in ranked_candidates if c.match_status == MatchStatus.PARTIAL_MATCH),
                "location_mismatches": sum(1 for c in ranked_candidates if c.match_status == MatchStatus.LOCATION_MISMATCH),
                "insufficient_evidence": sum(1 for c in ranked_candidates if c.match_status == MatchStatus.INSUFFICIENT_EVIDENCE)
            }

            return {
                "job_id": job_id,
                "status": "COMPLETED",
                "retrieval": {
                    "providers_attempted": providers_attempted,
                    "providers_succeeded": providers_succeeded,
                    "providers_failed": providers_failed,
                    "queries_executed": queries_executed_count,
                    "raw_results": len(raw_results),
                    "unique_candidates": len(candidates)
                },
                "summary": summary_metrics,
                "candidates": ranked_candidates
            }

        except Exception as e:
            repo.update_job_state(job_id, JobStateEnum.FAILED, error_message=str(e))
            raise e

    def submit_job_async(
        self,
        chat_id: int,
        raw_jd_text: str,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str, List[CandidateSchema]], None]] = None,
        on_error: Optional[Callable[[str, Exception], None]] = None
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        repo.create_job(job_id, chat_id, raw_jd_text)

        def worker():
            try:
                res = self.run_sourcing_pipeline(job_id, chat_id, raw_jd_text, progress_callback=on_progress)
                if on_complete:
                    on_complete(job_id, res.get("candidates", []) if isinstance(res, dict) else res)
            except Exception as e:
                if on_error:
                    on_error(job_id, e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return job_id


orchestrator = JobOrchestrator()
