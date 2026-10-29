import pytest
from src.sourcing.normalize import extract_name_and_headline
from src.sourcing.query_builder import build_search_queries
from src.core.schemas import JobDescriptionSchema, RequirementSchema, RoleFamily, CandidateSchema, EligibilityStatus
from src.scoring.engine import score_and_rank_candidates
from src.main import format_candidate_page, build_pagination_keyboard


def test_headline_multi_part_preservation():
    raw_title = "Marc Smeehuijzen - Freelance UX/UI Designer - Easytech - Netherlands | LinkedIn"
    name, headline = extract_name_and_headline(raw_title, "")
    assert name == "Marc Smeehuijzen"
    assert "Freelance UX/UI Designer" in headline
    assert "Easytech" in headline
    assert "Netherlands" in headline


def test_query_diversification_for_multi_skills():
    jd = JobDescriptionSchema(
        role_title="Embedded Software Engineer",
        role_family=RoleFamily.EMBEDDED_FIRMWARE,
        locations=["Eindhoven"],
        mandatory_requirements=[
            RequirementSchema(requirement_id="m1", normalized_name="C++"),
            RequirementSchema(requirement_id="m2", normalized_name="Embedded Systems"),
            RequirementSchema(requirement_id="m3", normalized_name="Test Automation"),
            RequirementSchema(requirement_id="m4", normalized_name="DFSS")
        ]
    )
    queries = build_search_queries(jd, max_queries=4)
    assert len(queries) >= 3
    # Check that diverse combinations are present
    combined = " ".join(queries)
    assert "C++" in combined
    assert "Embedded Systems" in combined
    assert "DFSS" in combined or "Test Automation" in combined


def test_calibrated_scoring_for_many_requirements():
    jd = JobDescriptionSchema(
        role_title="Embedded Software Engineer",
        role_family=RoleFamily.EMBEDDED_FIRMWARE,
        locations=["Eindhoven"],
        experience_min_years=6.0,
        experience_max_years=8.0,
        mandatory_requirements=[
            RequirementSchema(requirement_id="m1", normalized_name="C++"),
            RequirementSchema(requirement_id="m2", normalized_name="Embedded"),
            RequirementSchema(requirement_id="m3", normalized_name="Test Automation"),
            RequirementSchema(requirement_id="m4", normalized_name="Verification"),
            RequirementSchema(requirement_id="m5", normalized_name="DFSS"),
            RequirementSchema(requirement_id="m6", normalized_name="V-model"),
        ]
    )

    # Candidate snippet matches core technical stack (C++ & Embedded) with 7 yrs exp
    c = CandidateSchema(
        candidate_id="c_embedded",
        name="John Doe",
        profile_url="https://linkedin.com/in/john-doe",
        headline="Senior Embedded Software Engineer - C++ specialist",
        source_snippets=["Senior Embedded Engineer with 7 years C++ experience in Eindhoven."]
    )

    scored = score_and_rank_candidates(jd, [c])
    assert len(scored) == 1
    # Under calibrated scoring, matching the top core skills in snippet should preserve a strong score (>60%)
    # rather than penalizing candidate down to 25% due to unobserved process acronyms (DFSS, V-model).
    assert scored[0].preliminary_match_score >= 60.0


def test_format_candidate_page_no_emojis():
    c = CandidateSchema(
        candidate_id="c1",
        name="Jane Smith",
        profile_url="https://linkedin.com/in/janesmith",
        headline="Senior Product Designer",
        preliminary_match_score=88.5,
        eligibility=EligibilityStatus.MEETS_VERIFIED_REQUIREMENTS
    )
    text = format_candidate_page("job_test", [c], page=0)
    assert "Jane Smith" in text
    assert "88.5%" in text
    assert "RECRUITER COPILOT | CANDIDATE SOURCING" in text
    # Verify zero emojis
    for char in text:
        assert ord(char) < 0x1F000 or ord(char) > 0x1FAFF
