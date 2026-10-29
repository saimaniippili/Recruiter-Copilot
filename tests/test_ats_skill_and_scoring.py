import pytest
from src.core.schemas import (
    CandidateSchema, JobDescriptionSchema, RequirementSchema,
    RoleFamily, MatchStatus, GeographicEligibilityStatus
)
from src.scoring.engine import (
    extract_skill_evidence, calculate_seniority_score,
    score_and_rank_candidates, SKILL_TAXONOMY_ALIASES
)


def test_skill_aliases_matching():
    """Verify that domain aliases match the canonical requirement."""
    text1 = "Extensive experience designing HANA Calculation Views and graphical views in enterprise analytics."
    lvl1, state1, note1, q1 = extract_skill_evidence("Calculation Views", text1)
    assert lvl1 >= 0.8
    assert "Calculation Views" in note1

    text2 = "Hands-on implementation of ABAP CDS views and core data services."
    lvl2, state2, note2, q2 = extract_skill_evidence("CDS Views", text2)
    assert lvl2 >= 0.8

    text3 = "Configured SAP Landscape Transformation (SLT) replication server."
    lvl3, state3, note3, q3 = extract_skill_evidence("SLT", text3)
    assert lvl3 >= 0.8

    text4 = "Senior ETL architect specializing in SAP BusinessObjects Data Services."
    lvl4, state4, note4, q4 = extract_skill_evidence("SAP BODS", text4)
    assert lvl4 >= 0.8


def test_distinguish_mentioned_vs_strongly_supported():
    """Verify level 0.5 for simple mention vs 1.0 for action-verb implementation."""
    snippet_mention = "Skills: SAP HANA, Calculation Views, SQLScript, Java."
    lvl_m, state_m, _, _ = extract_skill_evidence("Calculation Views", snippet_mention)
    assert lvl_m == 0.5

    snippet_strong = "Architected and optimized high-performance Calculation Views handling millions of financial records."
    lvl_s, state_s, _, _ = extract_skill_evidence("Calculation Views", snippet_strong)
    assert lvl_s == 1.0


def test_seniority_scoring_bounds():
    """Test 7-11 years rubric with exact deduction boundaries."""
    # Within 7-11 years -> 100.0
    score, _ = calculate_seniority_score(8.0, None, 7.0, 11.0)
    assert score == 100.0

    # Below 7: 100 - (7 - 5)*20 = 60.0
    score_low, _ = calculate_seniority_score(5.0, None, 7.0, 11.0)
    assert score_low == 60.0

    # Above 11: 100 - (13 - 11)*10 = 80.0
    score_high, _ = calculate_seniority_score(13.0, None, 7.0, 11.0)
    assert score_high == 80.0

    # Unknown experience: returns 50.0 neutral benchmark
    score_unk, _ = calculate_seniority_score(None, None, 7.0, 11.0)
    assert score_unk == 50.0


def test_hard_geographic_gate_prevents_high_tech_override():
    """A candidate with perfect 100% technical skills in India CANNOT get EXPLICIT_MATCH for Eindhoven role."""
    jd = JobDescriptionSchema(
        role_title="SAP HANA Cloud Consultant",
        role_family=RoleFamily.SAP_TECHNICAL_CONSULTING,
        locations=["Eindhoven, Netherlands"],
        mandatory_requirements=[
            RequirementSchema(requirement_id="m1", normalized_name="SAP HANA Modeling"),
            RequirementSchema(requirement_id="m2", normalized_name="Calculation Views"),
            RequirementSchema(requirement_id="m3", normalized_name="SQLScript"),
            RequirementSchema(requirement_id="m4", normalized_name="CDS Views")
        ]
    )

    c = CandidateSchema(
        candidate_id="c_india_expert",
        name="Sunil Rao",
        profile_url="https://in.linkedin.com/in/sunilrao",
        headline="Principal SAP HANA Architect - Bengaluru, India",
        source_snippets=[
            "Bengaluru, Karnataka, India. 10 years experience. Architected Native SAP HANA Modeling, Calculation Views, SQLScript, and CDS Views."
        ]
    )

    ranked = score_and_rank_candidates(jd, [c])
    cand = ranked[0]

    # Technical skills are strong
    assert cand.skill_score >= 80.0
    assert cand.mandatory_skill_coverage == 1.0
    # BUT geographic mismatch must gate the status
    assert cand.geographic_eligibility.status == GeographicEligibilityStatus.MISMATCH
    assert cand.match_status == MatchStatus.LOCATION_MISMATCH
    assert cand.overall_score <= 25.0


def test_scoring_determinism():
    """Scoring identical inputs must produce exact identical outputs."""
    jd = JobDescriptionSchema(
        role_title="SAP HANA Consultant",
        locations=["Netherlands"],
        mandatory_requirements=[
            RequirementSchema(requirement_id="m1", normalized_name="Calculation Views")
        ]
    )
    c = CandidateSchema(
        candidate_id="c_det",
        name="Test Candidate",
        profile_url="https://www.linkedin.com/in/test",
        headline="SAP Consultant in Eindhoven",
        source_snippets=["Based in Eindhoven. 8 years developing Calculation Views."]
    )

    run1 = score_and_rank_candidates(jd, [c])[0]
    run2 = score_and_rank_candidates(jd, [c])[0]

    assert run1.overall_score == run2.overall_score
    assert run1.skill_score == run2.skill_score
    assert run1.match_status == run2.match_status
