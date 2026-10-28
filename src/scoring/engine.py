import re
from typing import List, Dict, Tuple
from ..core.schemas import (
    JobDescriptionSchema, CandidateSchema, CandidateEvidence,
    EvidenceClassification, EligibilityStatus, RequirementImportance
)
from ..core.config import settings
from .experience import extract_candidate_experience, evaluate_experience_alignment


CLASSIFICATION_VALUES = {
    EvidenceClassification.EXPLICIT_MATCH: 1.0,
    EvidenceClassification.PARTIAL_MATCH: 0.6,
    EvidenceClassification.EXPLICIT_MISMATCH: 0.0,
    EvidenceClassification.UNKNOWN: 0.0,
    EvidenceClassification.CONTRADICTORY: 0.0
}


def evaluate_requirement_in_text(req_name: str, text: str) -> Tuple[EvidenceClassification, str]:
    """Deterministic keyword & token matcher for evidence classification."""
    clean_req = req_name.strip().replace("*", "")
    if not clean_req:
        return EvidenceClassification.UNKNOWN, ""

    text_lower = text.lower()
    req_lower = clean_req.lower()

    # Exact phrase or word boundary match
    pattern = r'(?:\b|\W)' + re.escape(req_lower) + r'(?:\b|\W)'
    if re.search(pattern, text_lower):
        return EvidenceClassification.EXPLICIT_MATCH, f"Explicitly found '{clean_req}' in profile."

    # Partial / sub-token match for multi-word skills (e.g. "Test Automation" matching "Automation")
    tokens = [t for t in req_lower.split() if len(t) > 2]
    matched_tokens = [t for t in tokens if re.search(r'(?:\b|\W)' + re.escape(t) + r'(?:\b|\W)', text_lower)]
    if len(tokens) > 1 and len(matched_tokens) >= 1:
        return EvidenceClassification.PARTIAL_MATCH, f"Partial match for '{clean_req}' (matched: {', '.join(matched_tokens)})."

    return EvidenceClassification.UNKNOWN, f"No public mention of '{clean_req}'."


def score_and_rank_candidates(jd: JobDescriptionSchema, candidates: List[CandidateSchema]) -> List[CandidateSchema]:
    """
    Applies deterministic scoring formula:
    Match Score = 100 * (W_mand * M_mand + W_tech * M_tech + W_role * M_role + W_exp * M_exp + W_pref * M_pref)
    """
    scored = []

    for c in candidates:
        full_text = f"{c.headline or ''} " + " ".join(c.source_snippets)
        evidence_dict = {}
        missing_evidence = []
        mandatory_scores = []
        preferred_scores = []

        # 1. Evaluate Mandatory Requirements
        for req in jd.mandatory_requirements:
            cls, reason = evaluate_requirement_in_text(req.normalized_name, full_text)
            evidence_dict[req.requirement_id] = CandidateEvidence(
                requirement_id=req.requirement_id,
                classification=cls,
                supporting_text=reason
            )
            val = CLASSIFICATION_VALUES[cls]
            mandatory_scores.append(val)
            if cls == EvidenceClassification.UNKNOWN:
                missing_evidence.append(req.normalized_name)

        # 2. Evaluate Preferred Requirements
        for req in jd.preferred_requirements:
            cls, reason = evaluate_requirement_in_text(req.normalized_name, full_text)
            evidence_dict[req.requirement_id] = CandidateEvidence(
                requirement_id=req.requirement_id,
                classification=cls,
                supporting_text=reason
            )
            preferred_scores.append(CLASSIFICATION_VALUES[cls])

        c.evidence_by_requirement = evidence_dict
        c.missing_evidence = missing_evidence

        # 3. Experience Evaluation
        stated_yr, est_yr, basis = extract_candidate_experience(c.headline or "", c.source_snippets)
        c.experience_years_stated = stated_yr
        c.experience_years_estimated = est_yr
        c.experience_basis = basis
        effective_yrs = stated_yr if stated_yr is not None else est_yr
        exp_score, exp_note = evaluate_experience_alignment(effective_yrs, jd.experience_min_years, jd.experience_max_years)

        # 4. Role Alignment
        role_score = 0.5
        if c.headline:
            role_tokens = [t for t in jd.role_title.lower().split() if len(t) > 2]
            matches = sum(1 for t in role_tokens if t in c.headline.lower())
            role_score = max(0.4, min(1.0, matches / max(1, len(role_tokens))))

        # Sub-scores
        if not mandatory_scores:
            m_mand = 0.8
        elif len(mandatory_scores) <= 3:
            m_mand = sum(mandatory_scores) / len(mandatory_scores)
        else:
            # Calibrate for search snippet brevity:
            # In short search snippets, a candidate matching 2-3 core skills is strong.
            # Weight top matched skills higher so unobserved secondary acronyms don't severely penalize.
            sorted_scores = sorted(mandatory_scores, reverse=True)
            core_k = min(2, len(sorted_scores))
            core_mand = sum(sorted_scores[:core_k]) / core_k
            breadth_mand = sum(sorted_scores[core_k:]) / (len(sorted_scores) - core_k)
            m_mand = (0.75 * core_mand) + (0.25 * breadth_mand)

        m_tech = m_mand  # technical skill mastery aligns with mandatory technical stack
        m_pref = (sum(preferred_scores) / len(preferred_scores)) if preferred_scores else 0.5
        m_role = role_score
        m_exp = exp_score

        # Weighted calculation
        total_score = 100.0 * (
            settings.WEIGHT_MANDATORY * m_mand +
            settings.WEIGHT_TECHNICAL_SKILLS * m_tech +
            settings.WEIGHT_ROLE_ALIGNMENT * m_role +
            settings.WEIGHT_EXPERIENCE * m_exp +
            settings.WEIGHT_PREFERRED * m_pref
        )

        # Geographic Prioritization (e.g. Hyderabad & Bangalore -> Chennai -> Other States)
        geo_bonus = 0.0
        candidate_text = f"{c.headline or ''} " + " ".join(c.source_snippets)
        cand_text_lower = candidate_text.lower()
        
        jd_locs_str = ' '.join(jd.locations).lower() if jd.locations else ""
        tier1_cities = ["hyderabad", "bangalore", "bengaluru"]
        tier2_cities = ["chennai"]
        
        has_tier1_in_jd = any(re.search(r'\b' + city + r'\b', jd_locs_str) for city in tier1_cities)
        has_tier2_in_jd = any(re.search(r'\b' + city + r'\b', jd_locs_str) for city in tier2_cities)

        if has_tier1_in_jd or has_tier2_in_jd:
            if any(re.search(r'\b' + city + r'\b', cand_text_lower) for city in tier1_cities):
                geo_bonus = 15.0  # Top focus: Hyderabad and Bangalore
                c.fit_summary = f"[PRIMARY FOCUS: Hyderabad/Bangalore] {c.fit_summary}"
            elif any(re.search(r'\b' + city + r'\b', cand_text_lower) for city in tier2_cities):
                geo_bonus = 10.0  # Secondary focus: Chennai
                c.fit_summary = f"[TIER-2 FOCUS: Chennai] {c.fit_summary}"
            else:
                c.fit_summary = f"[FALLBACK: Other States] {c.fit_summary}"

        c.preliminary_match_score = round(max(0.0, min(100.0, total_score + geo_bonus)), 1)

        # Evidence completeness
        total_mand = len(jd.mandatory_requirements)
        verified_mand = sum(1 for s in mandatory_scores if s > 0)
        c.evidence_completeness = round(verified_mand / max(1, total_mand), 2) if total_mand > 0 else 1.0

        # Eligibility Status
        if total_mand == 0:
            c.eligibility = EligibilityStatus.MEETS_VERIFIED_REQUIREMENTS if role_score >= 0.7 else EligibilityStatus.REQUIRES_HUMAN_REVIEW
        elif verified_mand == total_mand:
            c.eligibility = EligibilityStatus.MEETS_VERIFIED_REQUIREMENTS
        elif verified_mand > 0:
            c.eligibility = EligibilityStatus.REQUIRES_HUMAN_REVIEW
        else:
            c.eligibility = EligibilityStatus.INSUFFICIENT_EVIDENCE

        # Fit summary
        confirmed_skills = [
            req.normalized_name for req in jd.mandatory_requirements
            if evidence_dict.get(req.requirement_id) and evidence_dict[req.requirement_id].classification in (EvidenceClassification.EXPLICIT_MATCH, EvidenceClassification.PARTIAL_MATCH)
        ]
        unverified_skills = [
            req.normalized_name for req in jd.mandatory_requirements
            if req.normalized_name not in confirmed_skills
        ]

        status_tag = c.eligibility.value.replace('_', ' ').upper()
        conf_str = ", ".join(confirmed_skills) if confirmed_skills else "General role alignment"
        unver_str = f" | Unverified in snippet: {', '.join(unverified_skills[:3])}" if unverified_skills else ""
        c.fit_summary = f"[{status_tag}] Confirmed: ({conf_str}){unver_str}. {exp_note}"

        scored.append(c)

    # Sort descending by match score
    scored.sort(key=lambda x: x.preliminary_match_score, reverse=True)
    return scored
