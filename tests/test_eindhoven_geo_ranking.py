import pytest
from src.core.schemas import (
    CandidateSchema, JobDescriptionSchema, LocationRequirementSchema,
    RequirementSchema, RoleFamily, GeographicEligibilityStatus,
    MatchStatus, LocationEvidenceCategory
)
from src.scoring.engine import score_and_rank_candidates


def test_eindhoven_candidate_ranking_prioritizes_verified_residence():
    jd = JobDescriptionSchema(
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

    # 1. Candidate in Eindhoven with Dutch profile card
    c_eindhoven = CandidateSchema(
        candidate_id="c_naveen",
        name="Naveen Rasapalli",
        profile_url="https://nl.linkedin.com/in/naveen-rasapalli",
        headline="SAP HANA Consultant at Accenture",
        source_snippets=[
            "SAP HANA senior Consultant with 12 years of experience as S/4 HANA, SAP Native HANA, BW on HANA Developer. Ervaring: Accenture the Netherlands · Locatie: Eindhoven · 500+ connecties op LinkedIn"
        ]
    )

    # 2. Another candidate verified in Eindhoven
    c_jan = CandidateSchema(
        candidate_id="c_jan",
        name="Jan de Vries",
        profile_url="https://nl.linkedin.com/in/jan-de-vries",
        headline="Senior SAP HANA Consultant - Eindhoven, Netherlands",
        source_snippets=[
            "Based in Eindhoven, Netherlands. 9 years architecting SAP HANA Modeling, Calculation Views, and SQLScript."
        ]
    )

    # 3. Global candidate with high technical keywords but no location evidence
    c_unknown = CandidateSchema(
        candidate_id="c_unknown_global",
        name="Mangaiah Dongari",
        profile_url="https://www.linkedin.com/in/mangaiah-dongari",
        headline="Senior SAP HANA Consultant, S/4 HANA",
        source_snippets=[
            "Senior SAP HANA Consultant, S/4 HANA Central Finance Embedded Analytics CDS Views, HANA Data Modeler, BW/4 HANA, SQLScript, Calculation Views architected and developed."
        ]
    )

    # 4. Offshore candidate in India mentioning ASML client in Eindhoven
    c_offshore = CandidateSchema(
        candidate_id="c_offshore_india",
        name="Ramesh Kumar",
        profile_url="https://in.linkedin.com/in/ramesh-kumar",
        headline="SAP Consultant at Infosys - Hyderabad, India",
        source_snippets=[
            "Hyderabad, Telangana, India · 500+ connections · Implemented SAP solutions for ASML in Eindhoven as offshore lead."
        ]
    )

    ranked = score_and_rank_candidates(jd, [c_unknown, c_offshore, c_eindhoven, c_jan])

    # Rank 1 and 2 must be verified Eindhoven candidates
    assert ranked[0].geographic_eligibility.status == GeographicEligibilityStatus.ELIGIBLE
    assert ranked[1].geographic_eligibility.status == GeographicEligibilityStatus.ELIGIBLE
    assert {ranked[0].candidate_id, ranked[1].candidate_id} == {"c_naveen", "c_jan"}

    # Rank 3 must be the unknown candidate (discounted and lower than eligible)
    assert ranked[2].candidate_id == "c_unknown_global"
    assert ranked[2].geographic_eligibility.status == GeographicEligibilityStatus.UNKNOWN
    assert ranked[2].overall_score < ranked[0].overall_score

    # Rank 4 must be the offshore mismatch candidate
    assert ranked[3].candidate_id == "c_offshore_india"
    assert ranked[3].geographic_eligibility.status == GeographicEligibilityStatus.MISMATCH
    assert ranked[3].match_status == MatchStatus.LOCATION_MISMATCH
    assert ranked[3].overall_score <= 25.0
