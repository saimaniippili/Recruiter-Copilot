import re
from typing import List, Dict, Tuple, Optional, Any
from ..core.schemas import (
    JobDescriptionSchema, CandidateSchema, CandidateEvidence,
    EvidenceClassification, EligibilityStatus, MatchStatus,
    SkillEvidenceState, GeographicEligibilityStatus
)
from ..core.config import settings
from .experience import extract_candidate_experience
from ..geography.geographic_resolver import geographic_resolver


# Known Skill Aliases & Taxonomy (Requirement G & 10)
SKILL_TAXONOMY_ALIASES = {
    "sap hana modeling": [
        "hana modeling", "sap hana data modeling", "native sap hana modeling",
        "native sap hana", "native hana", "hana data modeler"
    ],
    "calculation views": [
        "calculation view", "calculation views", "calc views", "calc view",
        "hana calculation views", "hana views", "graphical calculation views"
    ],
    "sqlscript": [
        "sql script", "sqlscript", "hana sqlscript", "sql procedures"
    ],
    "cds views": [
        "core data services", "abap cds", "cds view", "cds views", "cds", "abap on hana cds"
    ],
    "slt": [
        "sap landscape transformation", "sap slt", "slt replication", "sap lt"
    ],
    "sap bods": [
        "bods", "sap businessobjects data services", "businessobjects data services",
        "sap data services", "sap bi/bods"
    ],
    "sap hana cloud": [
        "hana cloud", "sap hana", "s/4hana", "s4hana", "sap btp hana"
    ],
    "ams support": [
        "ams", "application management services", "l2/l3 support", "production support", "ams support"
    ]
}

# Implementation Action Verbs denoting strong hands-on responsibility
STRONG_IMPLEMENTATION_VERBS = [
    r'\barchitect(?:ed|ing|ure)?\b', r'\bdevelop(?:ed|ing|ment)?\b', r'\boptimiz(?:ed|ing|ation)?\b',
    r'\bimplement(?:ed|ing|ation)?\b', r'\bdesign(?:ed|ing)?\b', r'\bbuild(?:ing)?\b',
    r'\bdeploy(?:ed|ing|ment)?\b', r'\btun(?:ed|ing)?\b', r'\bconfigur(?:ed|ing|ation)?\b',
    r'\bmodel(?:ed|ing|er)?\b'
]


def evaluate_requirement_in_text(req_name: str, text: str) -> Tuple[EvidenceClassification, str]:
    """Compatibility wrapper for deterministic requirement evaluation."""
    level, state, note, quotation = extract_skill_evidence(req_name, text)
    if level >= 0.8:
        return EvidenceClassification.EXPLICIT_MATCH, note
    elif level >= 0.4:
        return EvidenceClassification.PARTIAL_MATCH, note
    return EvidenceClassification.UNKNOWN, note


def extract_skill_evidence(req_name: str, text: str) -> Tuple[float, SkillEvidenceState, str, Optional[str]]:
    """
    Evaluates evidence for a skill with alias matching, quotation extraction, and level classification.
    Levels:
    0.0 = NOT_FOUND
    0.5 = MENTIONED (in headline / keyword list without context)
    0.8 = SUPPORTED_BY_PROJECT_EVIDENCE (described in project context)
    1.0 = STRONGLY_SUPPORTED (explicit hands-on implementation responsibility)
    """
    clean_req = req_name.strip().replace("*", "")
    if not clean_req:
        return 0.0, SkillEvidenceState.NOT_FOUND, "No skill specified", None

    text_lower = text.lower()
    req_lower = clean_req.lower()

    # Collect all search terms (canonical + aliases)
    terms = [req_lower]
    if req_lower in SKILL_TAXONOMY_ALIASES:
        terms.extend(SKILL_TAXONOMY_ALIASES[req_lower])
    else:
        for k, aliases in SKILL_TAXONOMY_ALIASES.items():
            if k in req_lower or req_lower in k:
                terms.extend(aliases)

    terms = list(dict.fromkeys(terms))  # deduplicate preserving order

    # Search for term occurrences
    for term in terms:
        # Pattern matching with word boundary
        pattern = r'(?:\b|\W)' + re.escape(term) + r'(?:\b|\W)'
        match = re.search(pattern, text_lower)
        if match:
            # Extract local sentence / fragment for quotation
            start_idx = max(0, match.start() - 40)
            end_idx = min(len(text), match.end() + 50)
            quotation = text[start_idx:end_idx].strip()
            # Clean up quotation boundaries
            quotation = re.sub(r'^[^\w\(\[\'"]+', '', quotation)
            quotation = re.sub(r'[^\w\)\]\'"]+$', '', quotation)

            # Check if accompanied by hands-on implementation verbs
            has_strong_verb = any(re.search(v, quotation, re.IGNORECASE) for v in STRONG_IMPLEMENTATION_VERBS)
            if has_strong_verb:
                return 1.0, SkillEvidenceState.STRONGLY_SUPPORTED, f"Strong implementation evidence for '{clean_req}': \"...{quotation}...\"", quotation

            # Check if in project / experience description
            if len(quotation) > 30 and ("experience" in quotation.lower() or "worked" in quotation.lower() or "model" in quotation.lower()):
                return 0.8, SkillEvidenceState.SUPPORTED_BY_PROJECT_EVIDENCE, f"Project-backed evidence for '{clean_req}': \"...{quotation}...\"", quotation

            return 0.5, SkillEvidenceState.MENTIONED, f"Mentioned '{clean_req}' in profile snippet.", quotation

    # Check for multi-token partial match
    tokens = [t for t in req_lower.split() if len(t) > 2]
    matched_tokens = [t for t in tokens if re.search(r'(?:\b|\W)' + re.escape(t) + r'(?:\b|\W)', text_lower)]
    if len(tokens) > 1 and len(matched_tokens) >= 1:
        return 0.4, SkillEvidenceState.MENTIONED, f"Partial token match for '{clean_req}' (matched: {', '.join(matched_tokens)})", None

    return 0.0, SkillEvidenceState.NOT_FOUND, f"No evidence found for '{clean_req}'.", None


def calculate_seniority_score(stated_yr: Optional[float], est_yr: Optional[float], min_yr: Optional[float], max_yr: Optional[float]) -> Tuple[float, str]:
    """
    Requirement H & 11:
    7-11 years: 100
    Below min: subtract 20 points per year below minimum, floor 0
    Above max: subtract 10 points per year above maximum, floor 0
    If experience unknown: 50.0
    """
    effective_yr = stated_yr if stated_yr is not None else est_yr
    if effective_yr is None:
        return 50.0, "Experience years not explicitly stated (neutral benchmark 50.0 assigned)."

    target_min = min_yr if min_yr is not None else 7.0
    target_max = max_yr if max_yr is not None else 11.0

    if target_min <= effective_yr <= target_max:
        return 100.0, f"Experience ({effective_yr} yrs) squarely aligns with target {target_min}-{target_max} yrs."
    elif effective_yr < target_min:
        deficit = target_min - effective_yr
        score = max(0.0, 100.0 - (deficit * 20.0))
        return round(score, 1), f"Experience ({effective_yr} yrs) is {deficit:.1f} yrs below target minimum ({target_min} yrs)."
    else:
        surplus = effective_yr - target_max
        score = max(0.0, 100.0 - (surplus * 10.0))
        return round(score, 1), f"Experience ({effective_yr} yrs) exceeds target maximum ({target_max} yrs)."


def calculate_role_alignment_score(role_title: str, headline: str, snippets: List[str]) -> Tuple[float, str]:
    """
    Requirement H: Evaluates role alignment between target job title and candidate's professional profile.
    """
    combined = f"{headline or ''} {' '.join(snippets)}".lower()
    role_clean = role_title.lower()
    role_tokens = [t for t in role_clean.split() if len(t) > 2 and t not in ("senior", "junior", "lead", "staff", "principal")]

    # Exact or near-exact title match in headline
    if role_clean in (headline or "").lower():
        return 100.0, f"Direct title match: candidate headline reflects '{role_title}'."

    matched_tokens = [t for t in role_tokens if t in (headline or "").lower()]
    if role_tokens and len(matched_tokens) == len(role_tokens):
        return 100.0, f"Full role match: candidate headline matches all core role tokens ({', '.join(matched_tokens)})."
    elif role_tokens and len(matched_tokens) >= max(1, len(role_tokens) - 1):
        return 85.0, f"Strong role alignment: candidate headline matches {len(matched_tokens)}/{len(role_tokens)} tokens."

    # Domain-specific fallbacks (e.g. SAP HANA)
    if "hana" in role_clean:
        if "hana" in combined and any(t in combined for t in ["developer", "architect", "modeler", "engineer", "consultant"]):
            return 100.0, "Direct SAP HANA technical development/architecture role alignment."
        if any(t in combined for t in ["data engineer", "data warehouse", "bi architect", "bw/4hana", "btp"]):
            return 80.0, "Closely related enterprise data engineering/BI alignment."
        if "sap" in combined and any(t in combined for t in ["functional", "consultant", "analyst"]):
            return 50.0, "SAP functional consulting role alignment with secondary technical focus."

    if any(t in combined for t in ["software engineer", "developer", "backend", "programmer", "architect"]):
        return 70.0, "Software engineering background alignment."
        
    return 30.0, "Partial role alignment."


def calculate_evidence_quality_score(sources: List[Dict[str, Any]], supporting_quotations: List[str], has_profile_url: bool) -> float:
    """
    Requirement I & 12: Evaluates source reliability, quotation specificity, freshness, and multi-source corroboration.
    """
    score = 65.0  # Base score for valid indexed profile
    if has_profile_url:
        score += 10.0
    if len(sources) > 1:
        score += 15.0  # Multi-source corroboration
    if len(supporting_quotations) >= 2:
        score += 10.0  # Rich explicit quotations
    return min(100.0, score)


def score_and_rank_candidates(jd: JobDescriptionSchema, candidates: List[CandidateSchema]) -> List[CandidateSchema]:
    """
    Applies the full ATS Evidence Scoring & Conservative Geographic Evaluation Architecture.
    Overall Score:
    S_overall = 0.55 * S_skills + 0.20 * S_seniority + 0.15 * S_role + 0.10 * S_evidence
    Geographic eligibility is an independent hard gate.
    """
    scored = []

    target_city = jd.location_spec.city if jd.location_spec else (jd.locations[0].split(',')[0].strip() if jd.locations else "")
    target_country = jd.location_spec.country if jd.location_spec else (jd.locations[0].split(',')[-1].strip() if jd.locations else "Netherlands")
    work_mode = jd.location_spec.work_mode if jd.location_spec else (jd.work_arrangement or "HYBRID")
    relocation_allowed = jd.location_spec.relocation_allowed if jd.location_spec else False

    for c in candidates:
        full_text = f"{c.headline or ''} " + " ".join(c.source_snippets)
        evidence_dict: Dict[str, CandidateEvidence] = {}
        missing_evidence: List[str] = []
        supporting_evidence_records: List[Dict[str, Any]] = []
        supporting_quotations: List[str] = []

        # If location evidence was not pre-populated, extract it from headline & snippets
        if not c.current_location.value or c.current_location.evidence_type.value == "NO_LOCATION_EVIDENCE":
            from ..geography.location_extractor import extract_location_evidence
            c.current_location = extract_location_evidence(c.headline or "", " ".join(c.source_snippets), c.profile_url)
            if not c.location:
                c.location = c.current_location.value

        # 1. Evaluate Mandatory Technical Skills
        mand_levels = []
        for req in jd.mandatory_requirements:
            level, state, note, quotation = extract_skill_evidence(req.normalized_name, full_text)
            mand_levels.append(level)
            
            # Map to legacy EvidenceClassification for backwards compatibility
            legacy_cls = EvidenceClassification.EXPLICIT_MATCH if level >= 0.8 else (EvidenceClassification.PARTIAL_MATCH if level >= 0.4 else EvidenceClassification.UNKNOWN)
            
            evidence_dict[req.requirement_id] = CandidateEvidence(
                requirement_id=req.requirement_id,
                classification=legacy_cls,
                supporting_text=note,
                evidence_state=state,
                quotation=quotation
            )
            if quotation:
                supporting_quotations.append(quotation)
                supporting_evidence_records.append({
                    "skill": req.normalized_name,
                    "quotation": quotation,
                    "evidence_level": level,
                    "state": state.value
                })
            if level < 0.4:
                missing_evidence.append(req.normalized_name)

        # Calculate Skill Score (S_skills, 0-100 scale)
        if mand_levels:
            if len(mand_levels) <= 3:
                s_skills = round((sum(mand_levels) / len(mand_levels)) * 100.0, 1)
                coverage = round(sum(1 for l in mand_levels if l >= 0.4) / len(mand_levels), 2)
            else:
                # Calibrated for search snippet brevity:
                # In short search snippets, matching 2-3 core skills is strong.
                sorted_levels = sorted(mand_levels, reverse=True)
                core_k = min(2, len(sorted_levels))
                core_mand = sum(sorted_levels[:core_k]) / core_k
                breadth_mand = sum(sorted_levels[core_k:]) / (len(sorted_levels) - core_k)
                calibrated_mand = (0.75 * core_mand) + (0.25 * breadth_mand)
                s_skills = round(calibrated_mand * 100.0, 1)
                coverage = round(sum(1 for l in mand_levels if l >= 0.4) / len(mand_levels), 2)
                if core_mand >= 0.7:
                    coverage = max(coverage, 0.75)
        else:
            s_skills = 75.0
            coverage = 1.0

        c.skill_score = s_skills
        c.mandatory_skill_coverage = coverage
        c.evidence_by_requirement = evidence_dict
        c.missing_evidence = missing_evidence
        c.missing_requirements = missing_evidence
        c.supporting_evidence = supporting_evidence_records

        # 2. Seniority & Experience Scoring (S_seniority, 0-100 scale)
        stated_yr, est_yr, basis = extract_candidate_experience(c.headline or "", c.source_snippets)
        c.experience_years_stated = stated_yr
        c.experience_years_estimated = est_yr
        c.experience_basis = basis
        c.experience_years = stated_yr if stated_yr is not None else est_yr
        s_seniority, exp_note = calculate_seniority_score(stated_yr, est_yr, jd.experience_min_years, jd.experience_max_years)
        c.seniority_score = s_seniority

        # 3. Role Alignment Scoring (S_role, 0-100 scale)
        s_role, role_note = calculate_role_alignment_score(jd.role_title, c.headline or "", c.source_snippets)
        c.role_alignment_score = s_role

        # 4. Evidence Quality Scoring (S_evidence, 0-100 scale)
        s_evidence = calculate_evidence_quality_score(c.sources, supporting_quotations, bool(c.canonical_profile_url))
        c.evidence_quality_score = s_evidence

        # 5. Overall Score Calculation (Requirement I & 12)
        # S_overall = 0.55 * S_skills + 0.20 * S_seniority + 0.15 * S_role + 0.10 * S_evidence
        overall_score = round(
            0.55 * s_skills +
            0.20 * s_seniority +
            0.15 * s_role +
            0.10 * s_evidence,
            1
        )

        # 6. Conservative Geographic Eligibility Resolution (Requirement F & 9)
        geo_elig = geographic_resolver.resolve_eligibility(
            target_city=target_city,
            target_country=target_country,
            work_mode=work_mode,
            relocation_allowed=relocation_allowed,
            candidate_loc=c.current_location
        )
        c.geographic_eligibility = geo_elig

        # 7. Exact Classification States (Requirement J & 13)
        if geo_elig.status == GeographicEligibilityStatus.MISMATCH:
            # Geographic mismatch can NEVER be overridden by high technical score
            c.match_status = MatchStatus.LOCATION_MISMATCH
            c.eligibility = EligibilityStatus.DOES_NOT_MEET_VERIFIED_REQUIREMENT
            overall_score = min(overall_score * 0.25, 25.0)
            c.review_flags.append(f"Geographic Mismatch: {geo_elig.reason}")
        elif geo_elig.status == GeographicEligibilityStatus.ELIGIBLE and overall_score >= 75.0 and coverage >= 0.70 and s_evidence >= 60.0:
            c.match_status = MatchStatus.EXPLICIT_MATCH
            c.eligibility = EligibilityStatus.MEETS_VERIFIED_REQUIREMENTS
        elif geo_elig.status == GeographicEligibilityStatus.ELIGIBLE and (coverage >= 0.20 or overall_score >= 40.0):
            c.match_status = MatchStatus.PARTIAL_MATCH
            c.eligibility = EligibilityStatus.REQUIRES_HUMAN_REVIEW
        elif geo_elig.status == GeographicEligibilityStatus.UNKNOWN and (target_country or target_city):
            # Location is unconfirmed for a role requiring physical or hybrid presence
            overall_score = round(min(overall_score * 0.70, 60.0), 1)
            c.review_flags.append(f"Unverified Location: {geo_elig.reason}")
            if coverage >= 0.40 or overall_score >= 50.0:
                c.match_status = MatchStatus.PARTIAL_MATCH
                c.eligibility = EligibilityStatus.REQUIRES_HUMAN_REVIEW
            else:
                c.match_status = MatchStatus.INSUFFICIENT_EVIDENCE
                c.eligibility = EligibilityStatus.INSUFFICIENT_EVIDENCE
        elif coverage >= 0.40 or overall_score >= 50.0:
            c.match_status = MatchStatus.PARTIAL_MATCH
            c.eligibility = EligibilityStatus.REQUIRES_HUMAN_REVIEW
        else:
            c.match_status = MatchStatus.INSUFFICIENT_EVIDENCE
            c.eligibility = EligibilityStatus.INSUFFICIENT_EVIDENCE

        c.overall_score = overall_score
        c.preliminary_match_score = overall_score

        # Fit summary
        c.fit_summary = (
            f"[{c.match_status.value}] Skills: {s_skills}% (Coverage: {int(coverage*100)}%) | "
            f"Exp: {c.experience_years or 'Unstated'} yrs ({s_seniority}%) | "
            f"Geo: {geo_elig.status.value} ({geo_elig.reason})"
        )

        scored.append(c)

    # Sort candidates prioritizing verified geographic eligibility, then overall score
    def get_candidate_sort_key(c: CandidateSchema) -> Tuple[int, float]:
        # Primary Tier: Verified ELIGIBLE > UNKNOWN > MISMATCH
        geo_priority = {
            GeographicEligibilityStatus.ELIGIBLE: 2,
            GeographicEligibilityStatus.UNKNOWN: 1,
            GeographicEligibilityStatus.MISMATCH: 0
        }.get(c.geographic_eligibility.status, 0)
        return (geo_priority, c.overall_score or 0.0)

    scored.sort(key=get_candidate_sort_key, reverse=True)
    return scored
