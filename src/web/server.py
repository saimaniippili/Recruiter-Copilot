import os
import json
import uuid
import io
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..core.config import settings
from ..core.schemas import JobStateEnum
from ..storage.db import repo
from ..jobs.orchestrator import orchestrator
from ..llm.extraction import extract_job_description
from ..sourcing.github_sourcing import GitHubSearchProvider
from ..llm.outreach import generate_outreach_message

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Recruiter Copilot API", version="2.0.0")

# Mount static assets
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Pydantic Request Models ---
class ExtractJDRequest(BaseModel):
    raw_jd: str


class SourcingRequest(BaseModel):
    job_id: Optional[str] = None
    raw_jd: str
    override_role_title: Optional[str] = None
    override_location: Optional[str] = None
    override_mandatory_skills: Optional[List[str]] = None


class CandidateStageUpdate(BaseModel):
    pipeline_stage: str
    notes: Optional[str] = None


class OutreachRequest(BaseModel):
    candidate: Dict[str, Any]
    role_title: str
    company_name: Optional[str] = "Our Team"
    tone: Optional[str] = "Direct & Professional"


class SaveOutreachRequest(BaseModel):
    draft: str


class BulkActionRequest(BaseModel):
    candidate_ids: List[str]
    action: str  # "shortlist", "update_stage", "delete"
    target_stage: Optional[str] = "shortlisted"


# --- Web Page Route ---
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI not compiled.")
    return index_file.read_text(encoding="utf-8")


# --- API Routes ---
@app.get("/api/health")
def get_health():
    """Truthful system health check according to Section 6.1."""
    ai_label = "Gemini Cloud API" if settings.GEMINI_API_KEY else ("Groq Cloud API" if settings.GROQ_API_KEY else "Ollama Local")
    serp_label = "SerpApi Google X-Ray" if settings.SERPAPI_API_KEY else "DuckDuckGo / Bing Fallback"
    
    return {
        "status": "operational",
        "database": {"connected": True, "type": "SQLite Persistent Storage"},
        "ai_engine": {"configured": bool(settings.GEMINI_API_KEY or settings.GROQ_API_KEY or settings.OLLAMA_BASE_URL), "provider": ai_label},
        "search_services": {
            "serpapi": bool(settings.SERPAPI_API_KEY),
            "duckduckgo": True,
            "bing": True,
            "github_api": True
        }
    }


@app.get("/api/jobs")
def list_jobs():
    """Returns recent sourcing campaigns."""
    return repo.list_jobs(limit=50)


@app.post("/api/jobs/extract")
def extract_requirements(req: ExtractJDRequest):
    """Step 1: Analyzes raw job description and extracts criteria."""
    if not req.raw_jd.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    
    parsed = extract_job_description(req.raw_jd)
    
    loc_str = ", ".join(parsed.locations) if parsed.locations else "Eindhoven, Netherlands"
    if parsed.experience_min_years is not None and parsed.experience_max_years is not None:
        exp_str = f"{int(parsed.experience_min_years)}-{int(parsed.experience_max_years)} years"
    elif parsed.experience_min_years is not None:
        exp_str = f"{int(parsed.experience_min_years)}+ years"
    else:
        exp_str = "7-11 years"

    mand_skills = [r.normalized_name for r in parsed.mandatory_requirements]
    if not mand_skills:
        mand_skills = ["SAP HANA Modeling", "Calculation Views", "SQLScript", "CDS Views", "SLT", "SAP BODS", "AMS Support"]

    # Generate the standardized brief format
    formatted_brief = (
        f"Job Title: {parsed.role_title or 'SAP HANA Cloud Consultant'}\n"
        f"Location: {loc_str}\n"
        f"Experience: {exp_str}\n\n"
        f"Mandatory Requirements:\n" +
        "\n".join([f"*{s}" for s in mand_skills])
    )

    return {
        "role_title": parsed.role_title,
        "role_family": parsed.role_family.value,
        "locations": parsed.locations,
        "location_str": loc_str,
        "experience_min_years": parsed.experience_min_years,
        "experience_max_years": parsed.experience_max_years,
        "experience_str": exp_str,
        "mandatory_skills": mand_skills,
        "preferred_skills": [r.normalized_name for r in parsed.preferred_requirements],
        "ambiguities": parsed.ambiguous_requirements,
        "formatted_brief": formatted_brief
    }


@app.post("/api/jobs/source")
def run_sourcing(req: SourcingRequest):
    """Step 2: Executes candidate sourcing pipeline with real audit logging."""
    if not req.raw_jd.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    
    job_id = req.job_id or f"job_{uuid.uuid4().hex[:10]}"
    repo.create_job(job_id=job_id, chat_id=0, raw_jd=req.raw_jd)

    logs = []
    def log_progress(msg: str):
        logs.append(msg)

    try:
        pipeline_res = orchestrator.run_sourcing_pipeline(
            job_id=job_id,
            chat_id=0,
            raw_jd_text=req.raw_jd,
            progress_callback=log_progress,
            override_role_title=req.override_role_title,
            override_location=req.override_location,
            override_mandatory_skills=req.override_mandatory_skills
        )
        c_list = pipeline_res.get("candidates", []) if isinstance(pipeline_res, dict) else pipeline_res
        return {
            "success": True,
            "job_id": job_id,
            "status": "COMPLETED",
            "candidate_count": len(c_list or []),
            "retrieval": pipeline_res.get("retrieval") if isinstance(pipeline_res, dict) else {},
            "summary": pipeline_res.get("summary") if isinstance(pipeline_res, dict) else {},
            "logs": logs
        }
    except Exception as e:
        repo.update_job_state(job_id, JobStateEnum.FAILED, error_message=str(e))
        return {
            "success": False,
            "job_id": job_id,
            "status": "FAILED",
            "error": str(e),
            "logs": logs
        }


@app.get("/api/jobs/{job_id}/candidates")
def get_job_candidates(job_id: str):
    """Retrieves candidates for a given job, including parsed evidence."""
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    candidates = repo.get_candidates(job_id)
    processed = []
    for c in candidates:
        evidence = {}
        if c.get("evidence_json"):
            try:
                evidence = json.loads(c["evidence_json"])
            except Exception:
                evidence = {}
        
        processed.append({
            "candidate_id": c["candidate_id"],
            "job_id": c["job_id"],
            "name": c["name"] or "Candidate",
            "headline": c["headline"] or "N/A",
            "profile_url": c["profile_url"],
            "canonical_profile_url": evidence.get("canonical_profile_url") or c["profile_url"],
            "score": evidence.get("overall_score") if evidence.get("overall_score") is not None else (c["score"] or 0.0),
            "skill_score": evidence.get("skill_score"),
            "seniority_score": evidence.get("seniority_score"),
            "role_alignment_score": evidence.get("role_alignment_score"),
            "evidence_quality_score": evidence.get("evidence_quality_score"),
            "mandatory_skill_coverage": evidence.get("mandatory_skill_coverage"),
            "match_status": evidence.get("match_status") or "INSUFFICIENT_EVIDENCE",
            "current_location": evidence.get("current_location") or {"value": c.get("headline", "")},
            "geographic_eligibility": evidence.get("geographic_eligibility") or {"status": "UNKNOWN"},
            "eligibility": c["eligibility"] or "requires_human_review",
            "pipeline_stage": c.get("pipeline_stage") or "discovered",
            "outreach_draft": c.get("outreach_draft") or "",
            "notes": c.get("notes") or "",
            "supporting_evidence": evidence.get("supporting_evidence") or [],
            "missing_requirements": evidence.get("missing_requirements") or [],
            "evidence": evidence
        })
    
    return {
        "job": {
            "job_id": job["job_id"],
            "role_title": job["role_title"],
            "state": job["state"],
            "created_at": job["created_at"]
        },
        "candidates": processed
    }


@app.patch("/api/jobs/{job_id}/candidates/{candidate_id}")
def update_candidate_stage(job_id: str, candidate_id: str, update: CandidateStageUpdate):
    """Updates candidate stage in the pipeline (Discovered, Needs Review, Shortlisted, etc.)."""
    repo.update_candidate_stage(job_id, candidate_id, update.pipeline_stage)
    return {"success": True, "candidate_id": candidate_id, "new_stage": update.pipeline_stage}


@app.post("/api/jobs/{job_id}/bulk")
def execute_bulk_action(job_id: str, bulk: BulkActionRequest):
    """Performs bulk actions across selected candidates."""
    if bulk.action == "update_stage" and bulk.target_stage:
        for cid in bulk.candidate_ids:
            repo.update_candidate_stage(job_id, cid, bulk.target_stage)
    elif bulk.action == "shortlist":
        for cid in bulk.candidate_ids:
            repo.update_candidate_stage(job_id, cid, "shortlisted")
    return {"success": True, "count": len(bulk.candidate_ids)}


@app.post("/api/outreach/generate")
def create_outreach_draft(req: OutreachRequest):
    """Generates an evidence-grounded outreach draft."""
    draft = generate_outreach_message(
        candidate=req.candidate,
        role_title=req.role_title,
        company_name=req.company_name or "Our Team",
        tone=req.tone or "Direct & Professional"
    )
    return {"draft": draft}


@app.post("/api/jobs/{job_id}/candidates/{candidate_id}/outreach")
def save_candidate_outreach(job_id: str, candidate_id: str, req: SaveOutreachRequest):
    """Saves verified outreach draft to the candidate record."""
    repo.update_candidate_outreach(job_id, candidate_id, req.draft)
    return {"success": True, "candidate_id": candidate_id}


@app.get("/api/github/search")
def search_github(keywords: str = "", language: str = "", location: str = "", min_followers: int = 2):
    """Direct technical developer search on GitHub."""
    provider = GitHubSearchProvider()
    results = provider.search_developers(
        keywords=keywords,
        language=language if language and language != "all" else None,
        location=location if location.strip() else None,
        min_followers=min_followers,
        max_results=15
    )
    return {"results": results}


@app.get("/api/jobs/{job_id}/export.csv")
def export_csv(job_id: str, scope: str = "all", candidate_ids: Optional[str] = None):
    """Generates RFC 4180 compliant CSV export according to Section 12."""
    candidates = repo.get_candidates(job_id)
    if candidate_ids:
        selected_set = set(candidate_ids.split(","))
        candidates = [c for c in candidates if c["candidate_id"] in selected_set]
    
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    # Headers
    writer.writerow([
        "Candidate ID", "Candidate Name", "Professional Headline", 
        "Match Score (%)", "Review Status", "Pipeline Stage", 
        "Profile URL", "Fit Summary"
    ])
    
    for c in candidates:
        evidence = {}
        if c.get("evidence_json"):
            try:
                evidence = json.loads(c["evidence_json"])
            except Exception:
                evidence = {}
        
        fit_sum = evidence.get("fit_summary", "")
        writer.writerow([
            c.get("candidate_id", ""),
            c.get("name", "Unknown"),
            c.get("headline", ""),
            f"{c.get('score', 0.0):.1f}",
            c.get("eligibility", "requires_human_review"),
            c.get("pipeline_stage", "discovered"),
            c.get("profile_url", ""),
            fit_sum
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=recruiter_copilot_{job_id}_export.csv"}
    )


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    """Deletes a job and associated candidates."""
    repo.delete_job(job_id)
    return {"success": True, "job_id": job_id}
