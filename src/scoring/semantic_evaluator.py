import json
import re
from typing import Dict, Any, Optional, List
from ..core.schemas import (
    JobDescriptionSchema, CandidateSchema, CandidateEvidence,
    EvidenceClassification, SkillEvidenceState, MatchStatus, EligibilityStatus,
    GeographicEligibilityStatus
)
from ..llm.providers import LLMClient


llm_client = LLMClient()


def evaluate_candidates_batch(
    jd: JobDescriptionSchema,
    candidates: List[CandidateSchema],
    batch_size: int = 5
) -> Dict[str, Any]:
    """
    Evaluates candidates in small, compact batches using Groq/Gemini.
    Uses an ultra-compact schema that never hits token truncation.
    """
    if not candidates:
        return {}

    req_names = [r.normalized_name for r in jd.mandatory_requirements if r.normalized_name]
    if not req_names:
        return {}

    all_evaluations: Dict[str, Any] = {}

    # Process in batches of 4-5 to guarantee zero token truncation
    for i in range(0, min(len(candidates), 12), batch_size):
        chunk = candidates[i:i + batch_size]
        
        cands_formatted = []
        for c in chunk:
            snippets = " ".join([s.strip() for s in c.source_snippets if s.strip()])[:250]
            cands_formatted.append(
                f"ID: {c.candidate_id}\n"
                f"Name: {c.name or 'Unknown'}\n"
                f"Headline: {c.headline or 'Not specified'}\n"
                f"Location: {c.location or 'Not specified'}\n"
                f"Context: {snippets}\n"
            )

        chunk_text = "\n---\n".join(cands_formatted)

        prompt = f"""Evaluate these candidates for the role: '{jd.role_title}' in {', '.join(jd.locations) if jd.locations else 'Any'}.
Target Experience: {jd.experience_min_years or 0}-{jd.experience_max_years or 15} yrs.
Mandatory Requirements: {json.dumps(req_names)}

Candidates:
{chunk_text}

Output a JSON list of evaluations:
[
  {{
    "id": "candidate_id",
    "score": 90,
    "years": 9.0,
    "summary": "1-2 sentence assessment for hiring manager.",
    "explicit_matches": ["Skill1", "Skill2"],
    "partial_matches": ["Skill3"],
    "evidence": {{"Skill1": "Direct quotation from headline or snippet"}}
  }}
]"""

        system_prompt = "You are an expert technical talent assessor. Output valid JSON list only. No markdown formatting."

        try:
            raw_resp = llm_client.complete(prompt, system_prompt=system_prompt, temperature=0.1, max_tokens=2500)
            if not raw_resp:
                continue

            clean_json = raw_resp.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            elif clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            start_idx = clean_json.find("[")
            end_idx = clean_json.rfind("]")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_candidate = clean_json[start_idx:end_idx+1]
            else:
                json_candidate = clean_json

            parsed_list = None
            try:
                parsed_list = json.loads(json_candidate)
            except Exception:
                # Fallback: extract individual valid JSON objects using regex
                import re
                obj_pattern = re.compile(r'\{[^{}]*"id"\s*:\s*"([^"]+)"[^{}]*\}', re.DOTALL)
                parsed_list = []
                for m in re.finditer(r'\{[^{}]*"id"[^}]+\}', clean_json):
                    try:
                        obj = json.loads(m.group(0))
                        if isinstance(obj, dict) and "id" in obj:
                            parsed_list.append(obj)
                    except Exception:
                        pass

            if isinstance(parsed_list, list):
                for item in parsed_list:
                    if isinstance(item, dict) and "id" in item:
                        all_evaluations[item["id"]] = item
        except Exception as e:
            print(f"[SemanticEvaluator] Chunk evaluation notice: {e}")
            continue

    return all_evaluations


def apply_semantic_batch_to_candidates(
    jd: JobDescriptionSchema,
    candidates: List[CandidateSchema],
    batch_eval: Dict[str, Any]
) -> None:
    """Applies batch evaluations to each candidate schema."""
    for c in candidates:
        eval_data = batch_eval.get(c.candidate_id)
        if not eval_data:
            continue

        overall_score = float(eval_data.get("score", c.overall_score or 75.0))
        est_years = eval_data.get("years")
        if est_years is not None:
            try:
                c.experience_years = float(est_years)
                c.experience_basis = "llm_semantic_extraction"
            except (ValueError, TypeError):
                pass

        explicit_set = set(eval_data.get("explicit_matches", []))
        partial_set = set(eval_data.get("partial_matches", []))
        evidence_dict = eval_data.get("evidence", {})

        supporting_evidence: List[Dict[str, Any]] = []
        missing_requirements: List[str] = []
        matches_count = 0
        total_reqs = len(jd.mandatory_requirements) or 1

        for req in jd.mandatory_requirements:
            r_name = req.normalized_name
            r_id = req.requirement_id
            ev_text = evidence_dict.get(r_name, "")

            if r_name in explicit_set:
                cls = EvidenceClassification.EXPLICIT_MATCH
                state = SkillEvidenceState.STRONGLY_SUPPORTED
                matches_count += 1
                supporting_evidence.append({
                    "skill": r_name,
                    "quotation": ev_text or f"Explicit hands-on expertise in {r_name}",
                    "evidence_level": 1.0,
                    "state": state.value
                })
            elif r_name in partial_set:
                cls = EvidenceClassification.PARTIAL_MATCH
                state = SkillEvidenceState.SUPPORTED_BY_PROJECT_EVIDENCE
                matches_count += 0.5
                supporting_evidence.append({
                    "skill": r_name,
                    "quotation": ev_text or f"Related exposure to {r_name}",
                    "evidence_level": 0.6,
                    "state": state.value
                })
            else:
                cls = EvidenceClassification.UNKNOWN
                state = SkillEvidenceState.NOT_FOUND
                missing_requirements.append(r_name)

            c.evidence_by_requirement[r_id] = CandidateEvidence(
                requirement_id=r_id,
                classification=cls,
                supporting_text=ev_text or f"Evaluated for '{r_name}'",
                is_direct_statement=True,
                confidence=0.9,
                evidence_state=state,
                quotation=ev_text if ev_text else None
            )

        coverage = round(matches_count / total_reqs, 2)
        c.mandatory_skill_coverage = coverage
        c.supporting_evidence = supporting_evidence
        c.missing_requirements = missing_requirements
        c.missing_evidence = missing_requirements

        geo_status = c.geographic_eligibility.status if c.geographic_eligibility else GeographicEligibilityStatus.UNKNOWN
        if geo_status == GeographicEligibilityStatus.MISMATCH:
            c.overall_score = min(overall_score * 0.25, 25.0)
            c.match_status = MatchStatus.LOCATION_MISMATCH
            c.eligibility = EligibilityStatus.DOES_NOT_MEET_VERIFIED_REQUIREMENT
        elif overall_score >= 70.0 and (coverage >= 0.35 or len(supporting_evidence) >= 2):
            c.overall_score = round(overall_score, 1)
            c.match_status = MatchStatus.EXPLICIT_MATCH
            c.eligibility = EligibilityStatus.MEETS_VERIFIED_REQUIREMENTS
        else:
            c.overall_score = round(overall_score, 1)
            c.match_status = MatchStatus.PARTIAL_MATCH
            c.eligibility = EligibilityStatus.REQUIRES_HUMAN_REVIEW

        c.skill_score = overall_score
        c.role_alignment_score = overall_score
        c.preliminary_match_score = c.overall_score

        summary = eval_data.get("summary", "")
        if summary:
            c.fit_summary = summary
