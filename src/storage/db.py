import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from ..core.config import settings
from ..core.schemas import SearchResultSchema, JobStateEnum


class DatabaseRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    chat_id INTEGER,
                    state TEXT,
                    role_title TEXT,
                    raw_jd TEXT,
                    structured_jd_json TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            # Query Cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    provider TEXT,
                    query_text TEXT,
                    results_json TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            # Candidates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_candidates (
                    candidate_id TEXT,
                    job_id TEXT,
                    name TEXT,
                    profile_url TEXT,
                    headline TEXT,
                    score REAL,
                    eligibility TEXT,
                    evidence_json TEXT,
                    pipeline_stage TEXT DEFAULT 'discovered',
                    notes TEXT DEFAULT '',
                    outreach_draft TEXT DEFAULT '',
                    created_at TIMESTAMP,
                    PRIMARY KEY (candidate_id, job_id)
                )
            """)
            # Backward-compatible migrations for existing databases
            for col, col_type in [("pipeline_stage", "TEXT DEFAULT 'discovered'"), ("notes", "TEXT DEFAULT ''"), ("outreach_draft", "TEXT DEFAULT ''")]:
                try:
                    cursor.execute(f"ALTER TABLE job_candidates ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass  # column already exists
            conn.commit()

            # Auto-seed database if fresh deployment has no jobs
            cursor.execute("SELECT COUNT(*) FROM jobs")
            if cursor.fetchone()[0] == 0:
                try:
                    import os
                    seed_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
                    if os.path.exists(seed_path):
                        with open(seed_path, "r", encoding="utf-8") as f:
                            seed = json.load(f)
                        j = seed.get("job", {})
                        if j:
                            cursor.execute(
                                """
                                INSERT INTO jobs (job_id, chat_id, state, role_title, raw_jd, structured_jd_json, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    j.get("job_id"),
                                    j.get("chat_id", 0),
                                    j.get("state", "COMPLETED"),
                                    j.get("role_title", "SAP HANA Cloud Consultant"),
                                    j.get("raw_jd", ""),
                                    j.get("structured_jd_json", ""),
                                    j.get("created_at"),
                                    j.get("updated_at")
                                )
                            )
                        for c in seed.get("candidates", []):
                            cursor.execute(
                                """
                                INSERT INTO job_candidates 
                                (candidate_id, job_id, name, profile_url, headline, score, eligibility, evidence_json, pipeline_stage, notes, outreach_draft, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    c.get("candidate_id"),
                                    c.get("job_id"),
                                    c.get("name"),
                                    c.get("profile_url"),
                                    c.get("headline"),
                                    c.get("score"),
                                    c.get("eligibility"),
                                    c.get("evidence_json"),
                                    c.get("pipeline_stage", "discovered"),
                                    c.get("notes", ""),
                                    c.get("outreach_draft", ""),
                                    c.get("created_at")
                                )
                            )
                        conn.commit()
                except Exception as e:
                    print("Seed loading notice:", e)

    # --- Job State Operations ---
    def create_job(self, job_id: str, chat_id: int, raw_jd: str) -> None:
        now = datetime.utcnow()
        with self._get_connection() as conn:
            conn.cursor().execute(
                """
                INSERT INTO jobs (job_id, chat_id, state, raw_jd, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, chat_id, JobStateEnum.QUEUED.value, raw_jd, now, now)
            )
            conn.commit()

    def update_job_state(self, job_id: str, state: JobStateEnum, error_message: Optional[str] = None, role_title: Optional[str] = None, structured_jd_json: Optional[str] = None) -> None:
        now = datetime.utcnow()
        updates = ["state = ?", "updated_at = ?"]
        params = [state.value, now]
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if role_title is not None:
            updates.append("role_title = ?")
            params.append(role_title)
        if structured_jd_json is not None:
            updates.append("structured_jd_json = ?")
            params.append(structured_jd_json)
        params.append(job_id)

        with self._get_connection() as conn:
            conn.cursor().execute(f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", params)
            conn.commit()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.cursor().execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    # --- Search Cache Operations ---
    def get_cached_search(self, provider: str, query_text: str) -> Optional[List[SearchResultSchema]]:
        cache_key = hashlib.sha256(f"{provider}:{query_text.strip().lower()}".encode()).hexdigest()
        now = datetime.utcnow()
        with self._get_connection() as conn:
            row = conn.cursor().execute(
                "SELECT results_json, expires_at FROM search_cache WHERE cache_key = ?",
                (cache_key,)
            ).fetchone()
            if row:
                expires_at = datetime.fromisoformat(row["expires_at"])
                if expires_at > now:
                    raw_data = json.loads(row["results_json"])
                    return [SearchResultSchema(**item) for item in raw_data]
        return None

    def cache_search_results(self, provider: str, query_text: str, results: List[SearchResultSchema], ttl_hours: Optional[int] = None) -> None:
        cache_key = hashlib.sha256(f"{provider}:{query_text.strip().lower()}".encode()).hexdigest()
        ttl = ttl_hours if ttl_hours is not None else settings.CACHE_TTL_HOURS
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=ttl)
        serialized = json.dumps([r.model_dump() for r in results])
        with self._get_connection() as conn:
            conn.cursor().execute(
                """
                INSERT OR REPLACE INTO search_cache (cache_key, provider, query_text, results_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cache_key, provider, query_text, serialized, now.isoformat(), expires_at.isoformat())
            )
            conn.commit()

    # --- Candidate Storage ---
    def save_candidates(self, job_id: str, candidates: List[Any]) -> None:
        now = datetime.utcnow()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for c in candidates:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO job_candidates 
                    (candidate_id, job_id, name, profile_url, headline, score, eligibility, evidence_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c.candidate_id,
                        job_id,
                        c.name or "Unknown",
                        c.profile_url,
                        c.headline or "",
                        c.preliminary_match_score,
                        c.eligibility.value,
                        json.dumps(c.model_dump()),
                        now
                    )
                )
            conn.commit()

    def get_candidates(self, job_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT * FROM job_candidates WHERE job_id = ? ORDER BY score DESC",
                (job_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent sourcing jobs with candidate counts for the web dashboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                SELECT j.job_id, j.role_title, j.state, j.raw_jd, j.created_at, j.updated_at,
                       COUNT(c.candidate_id) as candidate_count
                FROM jobs j
                LEFT JOIN job_candidates c ON j.job_id = c.job_id
                GROUP BY j.job_id
                ORDER BY j.created_at DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_candidate(self, job_id: str, candidate_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT * FROM job_candidates WHERE job_id = ? AND candidate_id = ?",
                (job_id, candidate_id)
            ).fetchone()
            return dict(row) if row else None

    def update_candidate_stage(self, job_id: str, candidate_id: str, stage: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE job_candidates SET pipeline_stage = ? WHERE job_id = ? AND candidate_id = ?",
                (stage, job_id, candidate_id)
            )
            conn.commit()

    def update_candidate_outreach(self, job_id: str, candidate_id: str, draft: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE job_candidates SET outreach_draft = ? WHERE job_id = ? AND candidate_id = ?",
                (draft, job_id, candidate_id)
            )
            conn.commit()

    def delete_job(self, job_id: str) -> None:
        """Deletes a job and its associated candidates."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM job_candidates WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            conn.commit()


repo = DatabaseRepository()
