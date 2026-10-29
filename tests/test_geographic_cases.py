import pytest
from src.core.schemas import (
    CandidateSchema, JobDescriptionSchema, LocationRequirementSchema,
    RequirementSchema, RoleFamily, GeographicEligibilityStatus,
    MatchStatus, LocationEvidenceCategory
)
from src.geography.location_extractor import extract_location_evidence
from src.geography.geographic_resolver import geographic_resolver
from src.scoring.engine import score_and_rank_candidates


@pytest.fixture
def sap_hana_eindhoven_jd():
    return JobDescriptionSchema(
        role_title="SAP HANA Cloud Consultant",
        role_family=RoleFamily.SAP_TECHNICAL_CONSULTING,
        locations=["Eindhoven, Netherlands"],
        location_spec=LocationRequirementSchema(
            city="Eindhoven",
            country="Netherlands",
            country_code="NL",
            work_mode="HYBRID",
            relocation_allowed=False
        ),
        mandatory_requirements=[
            RequirementSchema(requirement_id="m1", normalized_name="SAP HANA Modeling"),
            RequirementSchema(requirement_id="m2", normalized_name="Calculation Views"),
            RequirementSchema(requirement_id="m3", normalized_name="SQLScript"),
            RequirementSchema(requirement_id="m4", normalized_name="CDS Views")
        ]
    )


def test_case_1_explicitly_based_in_eindhoven(sap_hana_eindhoven_jd):
    """Case 1: Candidate is explicitly based in Eindhoven."""
    c = CandidateSchema(
        candidate_id="c_eindhoven",
        name="Jan de Vries",
        profile_url="https://www.linkedin.com/in/jandevries",
        headline="Senior SAP HANA Consultant - Eindhoven, Netherlands",
        source_snippets=["Based in Eindhoven, Netherlands. 9 years architecting SAP HANA Modeling, Calculation Views, and SQLScript."]
    )
    ranked = score_and_rank_candidates(sap_hana_eindhoven_jd, [c])
    assert len(ranked) == 1
    cand = ranked[0]
    assert cand.geographic_eligibility.status == GeographicEligibilityStatus.ELIGIBLE
    assert cand.match_status == MatchStatus.EXPLICIT_MATCH
    assert "Eindhoven" in cand.geographic_eligibility.reason


def test_case_2_based_in_hyderabad_with_asml_project(sap_hana_eindhoven_jd):
    """Case 2: Candidate is based in Hyderabad and mentions an ASML project in Eindhoven."""
    c = CandidateSchema(
        candidate_id="c_hyderabad_asml",
        name="Ramesh Kumar",
        profile_url="https://in.linkedin.com/in/ramesh-kumar",
        headline="SAP Consultant at Infosys - Hyderabad, India",
        source_snippets=["Hyderabad, Telangana, India. Implemented SAP solutions for ASML in Eindhoven as offshore lead."]
    )
    ranked = score_and_rank_candidates(sap_hana_eindhoven_jd, [c])
    assert len(ranked) == 1
    cand = ranked[0]
    # ASML project mention must NOT establish Dutch residence!
    assert cand.geographic_eligibility.status == GeographicEligibilityStatus.MISMATCH
    assert cand.match_status == MatchStatus.LOCATION_MISMATCH
    # Hard gate: Overall score must be capped and cannot be rescued by skills
    assert cand.overall_score <= 25.0


def test_case_3_historical_india_verified_current_netherlands(sap_hana_eindhoven_jd):
    """Case 3: Candidate has Indian historical employment but verified current location in Netherlands."""
    c = CandidateSchema(
        candidate_id="c_relocated",
        name="Priya Sharma",
        profile_url="https://www.linkedin.com/in/priyasharma",
        headline="Lead SAP Architect at Philips - Eindhoven Area, Netherlands",
        source_snippets=[
            "Eindhoven, North Brabant, Netherlands. Formerly Senior Consultant at Wipro, Bangalore until 2021. Now Lead SAP Architect in Eindhoven developing Calculation Views and SQLScript."
        ]
    )
    ranked = score_and_rank_candidates(sap_hana_eindhoven_jd, [c])
    assert len(ranked) == 1
    cand = ranked[0]
    # Current Netherlands residence takes precedence over historical India mention
    assert cand.geographic_eligibility.status == GeographicEligibilityStatus.ELIGIBLE
    assert cand.match_status in (MatchStatus.EXPLICIT_MATCH, MatchStatus.PARTIAL_MATCH)


def test_case_4_nl_subdomain_without_location_context(sap_hana_eindhoven_jd):
    """Case 4: LinkedIn URL uses nl.linkedin.com/in/, but current location is unknown."""
    loc = extract_location_evidence(
        title="Alex M. - SAP Consultant | LinkedIn",
        snippet="SAP Consultant with expertise in Calculation Views and SQLScript.",
        url="https://nl.linkedin.com/in/alex-m"
    )
    # The subdomain alone must not establish eligibility
    geo = geographic_resolver.resolve_eligibility(
        target_city="Eindhoven",
        target_country="Netherlands",
        work_mode="HYBRID",
        relocation_allowed=False,
        candidate_loc=loc
    )
    assert geo.status == GeographicEligibilityStatus.UNKNOWN


def test_case_5_global_subdomain_verified_in_eindhoven(sap_hana_eindhoven_jd):
    """Case 5: Candidate uses www.linkedin.com/in/ and is verified living in Eindhoven."""
    c = CandidateSchema(
        candidate_id="c_global_eindhoven",
        name="Dennis Bakker",
        profile_url="https://www.linkedin.com/in/dennis-bakker",
        headline="SAP Technical Consultant - Eindhoven",
        source_snippets=["Based in Eindhoven. 8 years hands-on with Native SAP HANA Modeling, Calculation Views, and CDS Views."]
    )
    ranked = score_and_rank_candidates(sap_hana_eindhoven_jd, [c])
    assert len(ranked) == 1
    cand = ranked[0]
    # Global domain must not cause rejection when resident in Eindhoven
    assert cand.geographic_eligibility.status == GeographicEligibilityStatus.ELIGIBLE
    assert cand.match_status == MatchStatus.EXPLICIT_MATCH


def test_case_6_mentions_amsterdam_without_residence_evidence(sap_hana_eindhoven_jd):
    """Case 6: Candidate profile mentions Amsterdam but provides no evidence of current residence."""
    loc = extract_location_evidence(
        title="Sander K. - Keynote Speaker on Cloud Computing | LinkedIn",
        snippet="Speaker at Tech Summit Amsterdam 2024. Expert in enterprise data warehousing.",
        url="https://www.linkedin.com/in/sander-k"
    )
    geo = geographic_resolver.resolve_eligibility(
        target_city="Eindhoven",
        target_country="Netherlands",
        work_mode="HYBRID",
        relocation_allowed=False,
        candidate_loc=loc
    )
    # UNKNOWN unless sufficient additional evidence resolves ambiguity
    assert geo.status == GeographicEligibilityStatus.UNKNOWN


def test_case_7_relocation_arrangement(sap_hana_eindhoven_jd):
    """Case 7: Candidate lives outside Eindhoven but has an accepted relocation arrangement."""
    # Modify JD policy to allow relocation
    sap_hana_eindhoven_jd.location_spec.relocation_allowed = True
    
    # Candidate location model with explicit RELOCATION_REPORTED
    c = CandidateSchema(
        candidate_id="c_relocating",
        name="Amit Patel",
        profile_url="https://www.linkedin.com/in/amit-patel",
        headline="SAP HANA Specialist (Relocating to Netherlands)",
        source_snippets=["Currently based in India, actively relocating to Netherlands in Q1 2027."]
    )
    c.current_location.value = "India (Relocating to Netherlands)"
    c.current_location.evidence_type = LocationEvidenceCategory.RELOCATION_REPORTED
    
    ranked = score_and_rank_candidates(sap_hana_eindhoven_jd, [c])
    assert len(ranked) == 1
    cand = ranked[0]
    assert cand.geographic_eligibility.status == GeographicEligibilityStatus.ELIGIBLE
    assert "relocation" in cand.geographic_eligibility.reason.lower()


def test_case_8_conflicting_location_evidence(sap_hana_eindhoven_jd):
    """Case 8: Current location evidence is ambiguous or conflicting across sources."""
    loc = extract_location_evidence(
        title="Consultant Profile | LinkedIn",
        snippet="Client Project in Netherlands ... Location: ambiguous office address",
        url="https://www.linkedin.com/in/ambiguous-candidate"
    )
    geo = geographic_resolver.resolve_eligibility(
        target_city="Eindhoven",
        target_country="Netherlands",
        work_mode="HYBRID",
        relocation_allowed=False,
        candidate_loc=loc
    )
    # Must return UNKNOWN rather than silently assuming eligibility
    assert geo.status == GeographicEligibilityStatus.UNKNOWN
