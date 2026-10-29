import pytest
from pathlib import Path
from src.core.schemas import (
    JobDescriptionSchema, RequirementSchema, RoleFamily,
    RequirementImportance, EvidenceClassification, EligibilityStatus,
    CandidateSchema, SearchResultSchema
)
from src.llm.extraction import detect_role_family, parse_experience_range, extract_starred_skills
from src.sourcing.query_builder import build_search_queries
from src.sourcing.normalize import (
    canonicalize_url, is_valid_profile_url, is_candidate_relevant,
    extract_name_and_headline, normalize_search_results
)
from src.scoring.experience import (
    parse_explicit_years, parse_date_ranges_and_career_start,
    extract_candidate_experience, evaluate_experience_alignment
)
from src.scoring.engine import evaluate_requirement_in_text, score_and_rank_candidates
from src.exports.csv_export import sanitize_csv_cell, export_candidates_to_csv
from src.storage.db import DatabaseRepository


def test_schema_instantiation():
    req = RequirementSchema(requirement_id="req_1", normalized_name="C++", importance=RequirementImportance.MANDATORY)
    jd = JobDescriptionSchema(
        role_title="Embedded Engineer",
        role_family=RoleFamily.EMBEDDED_FIRMWARE,
        locations=["Eindhoven"],
        experience_min_years=6.0,
        experience_max_years=8.0,
        mandatory_requirements=[req]
    )
    assert jd.role_title == "Embedded Engineer"
    assert len(jd.mandatory_requirements) == 1
    assert jd.mandatory_requirements[0].normalized_name == "C++"


def test_role_family_detection():
    assert detect_role_family("Senior UX Designer", "") == RoleFamily.UX_UI_DESIGN
    assert detect_role_family("Firmware Developer", "working on microcontrollers") == RoleFamily.EMBEDDED_FIRMWARE
    assert detect_role_family("DevOps Specialist", "Kubernetes cluster") == RoleFamily.DEVOPS_SRE_CLOUD
    assert detect_role_family("Data Scientist", "NLP and deep learning") == RoleFamily.DATA_SCIENCE_ML
    assert detect_role_family("Unknown Consultant", "general business") == RoleFamily.GENERIC_OTHER


def test_starred_skills_and_experience_extraction():
    jd_sample = """
    Job Title: Embedded Software Development Engineer
    Requirements:
    *C++
    *Test Automation
    *Verification Testing
    Experience: 6-8 years
    """
    starred = extract_starred_skills(jd_sample)
    assert "C++" in starred
    assert "Test Automation" in starred
    assert "Verification Testing" in starred

    min_y, max_y = parse_experience_range(jd_sample)
    assert min_y == 6.0
    assert max_y == 8.0


def test_query_generation_portfolio():
    jd = JobDescriptionSchema(
        role_title="UX Designer",
        role_family=RoleFamily.UX_UI_DESIGN,
        locations=["Netherlands"],
        mandatory_requirements=[
            RequirementSchema(requirement_id="1", normalized_name="UX Design"),
            RequirementSchema(requirement_id="2", normalized_name="Figma")
        ]
    )
    queries = build_search_queries(jd, max_queries=3)
    assert len(queries) >= 2
    assert any("UX Designer" in q for q in queries)
    assert any("Figma" in q or "UX Design" in q for q in queries)


def test_url_canonicalization_and_validation():
    valid_url = "https://www.linkedin.com/in/john-doe-12345/?utm_source=share"
    job_url = "https://www.linkedin.com/jobs/view/123456"
    company_url = "https://www.linkedin.com/company/google"

    assert is_valid_profile_url(valid_url) is True
    assert is_valid_profile_url(job_url) is False
    assert is_valid_profile_url(company_url) is False
    assert canonicalize_url(valid_url) == "https://www.linkedin.com/in/john-doe-12345"


def test_anti_recruiter_and_relevance():
    assert is_candidate_relevant("Alice Smith", "Senior C++ Engineer", "Designing real-time systems") is True
    assert is_candidate_relevant("Bob Recruiter", "Technical Recruiter | Talent Partner", "Hiring engineers") is False
    assert is_candidate_relevant("Dr. James", "Doctor of Medicine", "Hospital care") is False


def test_experience_parsing():
    stated = parse_explicit_years("Senior Developer with 7 years of experience in backend systems.")
    assert stated == 7.0

    range_stated = parse_explicit_years("UX Designer with 8-10 years experience.")
    assert range_stated == 9.0

    est = parse_date_ranges_and_career_start("Working since 2018 in Amsterdam.")
    assert est is not None and est >= 6.0

    score_aligned, note = evaluate_experience_alignment(7.0, 6.0, 8.0)
    assert score_aligned == 1.0

    score_senior, note_senior = evaluate_experience_alignment(22.0, 6.0, 8.0)
    assert score_senior < 0.6  # Penalized alignment for 22 yrs on 6-8 yr JD


def test_deterministic_scoring_formula():
    jd = JobDescriptionSchema(
        role_title="Embedded Engineer",
        locations=["Netherlands"],
        experience_min_years=6.0,
        experience_max_years=8.0,
        mandatory_requirements=[
            RequirementSchema(requirement_id="m1", normalized_name="C++"),
            RequirementSchema(requirement_id="m2", normalized_name="Embedded")
        ]
    )

    c1 = CandidateSchema(
        candidate_id="c1",
        name="Mark Jansen",
        profile_url="https://linkedin.com/in/mark-jansen",
        headline="Senior Embedded Engineer - C++ & Firmware",
        source_snippets=["7 years of experience developing robust C++ embedded systems in Eindhoven."]
    )

    c2 = CandidateSchema(
        candidate_id="c2",
        name="Junior Dev",
        profile_url="https://linkedin.com/in/junior-dev",
        headline="Junior Web Developer",
        source_snippets=["HTML and CSS enthusiast, 1 year experience."]
    )

    ranked = score_and_rank_candidates(jd, [c1, c2])
    assert ranked[0].name == "Mark Jansen"
    assert ranked[0].preliminary_match_score > 75.0
    assert ranked[0].eligibility == EligibilityStatus.MEETS_VERIFIED_REQUIREMENTS
    assert ranked[1].preliminary_match_score < 50.0


def test_csv_formula_injection_sanitization(tmp_path):
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("@SUM(A1:B1)") == "'@SUM(A1:B1)"
    assert sanitize_csv_cell("+44 7911") == "'+44 7911"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"

    cand = CandidateSchema(
        candidate_id="c_test",
        name="=HYPERLINK('http://evil.com')",
        profile_url="https://linkedin.com/in/test",
        headline="Software Engineer",
        preliminary_match_score=85.0
    )

    csv_path = export_candidates_to_csv("test_job_1", [cand])
    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8-sig")
    assert "'=HYPERLINK" in content


def test_sqlite_repository_and_cache(tmp_path):
    test_db = tmp_path / "test.db"
    db = DatabaseRepository(db_path=str(test_db))

    db.create_job("job_99", 12345, "Raw JD Text")
    job = db.get_job("job_99")
    assert job is not None
    assert job["job_id"] == "job_99"

    # Search cache test
    results = [
        SearchResultSchema(title="T1", url="https://linkedin.com/in/1", snippet="S1", query_used="test query")
    ]
    db.cache_search_results("serpapi", "test query", results, ttl_hours=2)
    cached = db.get_cached_search("serpapi", "test query")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].url == "https://linkedin.com/in/1"

    # Miss test
    assert db.get_cached_search("serpapi", "nonexistent query") is None
