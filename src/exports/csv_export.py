import csv
import tempfile
import shutil
from pathlib import Path
from typing import List, Any
from ..core.schemas import CandidateSchema
from ..core.config import settings


def sanitize_csv_cell(value: Any) -> str:
    """Protects against CSV Formula Injection (Excel / Google Sheets execution)."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{text}"
    return text


def export_candidates_to_csv(job_id: str, candidates: List[CandidateSchema]) -> Path:
    """Writes candidates to recruiter_copilot_{job_id}.csv atomically with formula injection protection."""
    target_dir = settings.EXPORTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"recruiter_copilot_{job_id}.csv"

    headers = [
        "Candidate Name",
        "Preliminary Match Score (%)",
        "Eligibility Status",
        "Evidence Completeness",
        "Headline",
        "Profile URL",
        "Experience (Stated)",
        "Experience (Estimated)",
        "Experience Basis",
        "Fit Summary & Notes",
        "Missing Evidence",
        "Source Provider",
        "Retrieved At"
    ]

    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8-sig", delete=False) as tmp:
        writer = csv.writer(tmp)
        writer.writerow(headers)
        for c in candidates:
            writer.writerow([
                sanitize_csv_cell(c.name),
                c.preliminary_match_score,
                c.eligibility.value,
                f"{int(c.evidence_completeness * 100)}%",
                sanitize_csv_cell(c.headline),
                c.profile_url,
                c.experience_years_stated if c.experience_years_stated is not None else "N/A",
                c.experience_years_estimated if c.experience_years_estimated is not None else "N/A",
                c.experience_basis,
                sanitize_csv_cell(c.fit_summary),
                sanitize_csv_cell(", ".join(c.missing_evidence)),
                c.source_provider,
                c.retrieved_at
            ])
        tmp_path = Path(tmp.name)

    shutil.move(str(tmp_path), str(target_file))
    return target_file
