"""
Requirement Q & 20: Geographic Search Evaluation Harness
Measures and compares candidate sourcing precision, recall, and geographic accuracy
across pipeline configurations.
"""

from typing import List, Dict, Any, Optional
from ..core.schemas import (
    JobDescriptionSchema, CandidateSchema, SearchResultSchema,
    LocationRequirementSchema, RequirementSchema, RoleFamily,
    GeographicEligibilityStatus, MatchStatus
)
from ..sourcing.normalize import normalize_search_results
from ..scoring.engine import score_and_rank_candidates


# Benchmark dataset with known ground truth labels for SAP HANA Cloud Consultant (Eindhoven, NL)
BENCHMARK_PROFILES = [
    {
        "title": "Jan de Vries - Senior SAP HANA Architect | LinkedIn",
        "url": "https://www.linkedin.com/in/jandevries",
        "snippet": "Eindhoven, North Brabant, Netherlands. 10 years experience architecting Native SAP HANA Modeling, Calculation Views, SQLScript, and CDS Views at ASML.",
        "provider": "serpapi",
        "ground_truth_geo": "ELIGIBLE",
        "ground_truth_tech": True
    },
    {
        "title": "Anil Yarramasu - SAP Technical Consultant | LinkedIn",
        "url": "https://nl.linkedin.com/in/yarramasu",
        "snippet": "Netherlands · SAP Technical Consultant · 13+ years experience with SAP HANA, Calculation Views, SQLScript, and SLT replication.",
        "provider": "serpapi",
        "ground_truth_geo": "ELIGIBLE",
        "ground_truth_tech": True
    },
    {
        "title": "Ramesh Kumar - SAP Consultant at Infosys | LinkedIn",
        "url": "https://in.linkedin.com/in/ramesh-kumar",
        "snippet": "Hyderabad, Telangana, India. Implemented SAP solutions for ASML in Eindhoven as offshore lead. Expert in SAP BODS and SLT.",
        "provider": "duckduckgo",
        "ground_truth_geo": "MISMATCH",
        "ground_truth_tech": True
    },
    {
        "title": "Suresh Reddy - Senior SAP HANA Developer | LinkedIn",
        "url": "https://www.linkedin.com/in/suresh-reddy-blr",
        "snippet": "Bengaluru, Karnataka, India. 8 years SAP HANA, Calculation Views, and SQLScript. Supported Netherlands customer accounts remotely.",
        "provider": "duckduckgo",
        "ground_truth_geo": "MISMATCH",
        "ground_truth_tech": True
    },
    {
        "title": "Dennis Bakker - SAP HANA Consultant | LinkedIn",
        "url": "https://www.linkedin.com/in/dennis-bakker",
        "snippet": "Based in Eindhoven. 8 years hands-on with Native SAP HANA Modeling, Calculation Views, and CDS Views.",
        "provider": "bing",
        "ground_truth_geo": "ELIGIBLE",
        "ground_truth_tech": True
    },
    {
        "title": "Priya Sharma - Lead SAP Architect at Philips | LinkedIn",
        "url": "https://www.linkedin.com/in/priyasharma",
        "snippet": "Eindhoven Area, Netherlands. Formerly Senior Consultant at Wipro, Bangalore until 2021. Now Lead SAP Architect in Eindhoven.",
        "provider": "serpapi",
        "ground_truth_geo": "ELIGIBLE",
        "ground_truth_tech": True
    },
    {
        "title": "Kees van Dijk - Keynote Speaker & Agile Coach | LinkedIn",
        "url": "https://www.linkedin.com/in/kees-van-dijk",
        "snippet": "Speaker at Tech Summit Amsterdam 2024. Agile transformation and management.",
        "provider": "duckduckgo",
        "ground_truth_geo": "UNKNOWN",
        "ground_truth_tech": False
    },
    {
        "title": "Duplicate Profile - Jan de Vries | LinkedIn",
        "url": "https://nl.linkedin.com/in/jandevries?utm_source=share",
        "snippet": "Eindhoven, Netherlands. Senior SAP HANA Architect.",
        "provider": "duckduckgo",
        "ground_truth_geo": "ELIGIBLE",
        "ground_truth_tech": True
    }
]


class SearchEvaluationHarness:
    """
    Evaluation harness comparing search pipeline configurations and calculating
    Geographic Precision, Technical Precision, and Coverage.
    """

    def __init__(self):
        self.benchmark_jd = JobDescriptionSchema(
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

    def run_evaluation(
        self,
        raw_items: Optional[List[Dict[str, Any]]] = None,
        use_geo_verification: bool = True
    ) -> Dict[str, Any]:
        items = raw_items or BENCHMARK_PROFILES
        total_discovered = len(items)

        # Convert to SearchResultSchema
        raw_results = [
            SearchResultSchema(
                title=item["title"],
                url=item["url"],
                snippet=item["snippet"],
                provider=item["provider"]
            ) for item in items
        ]

        # Normalization & Deduplication
        candidates = normalize_search_results(raw_results, expected_subdomain="nl" if use_geo_verification else "")
        unique_profiles = len(candidates)
        duplicate_rate = round((total_discovered - unique_profiles) / max(1, total_discovered), 2)

        # Scoring & Classification
        ranked = score_and_rank_candidates(self.benchmark_jd, candidates)

        # Metrics calculation
        eligible_count = sum(1 for c in ranked if c.geographic_eligibility.status == GeographicEligibilityStatus.ELIGIBLE)
        mismatch_count = sum(1 for c in ranked if c.geographic_eligibility.status == GeographicEligibilityStatus.MISMATCH)
        unresolved_count = sum(1 for c in ranked if c.geographic_eligibility.status == GeographicEligibilityStatus.UNKNOWN)
        explicit_matches = sum(1 for c in ranked if c.match_status == MatchStatus.EXPLICIT_MATCH)
        partial_matches = sum(1 for c in ranked if c.match_status == MatchStatus.PARTIAL_MATCH)

        # Shortlist: candidates with score >= 50 and not location mismatch
        shortlist = [c for c in ranked if c.match_status in (MatchStatus.EXPLICIT_MATCH, MatchStatus.PARTIAL_MATCH)]
        shortlist_count = len(shortlist)

        # Ground truth mapping for precision
        gt_lookup = {item["url"].split("?")[0].rstrip("/").replace("nl.", "www."): item for item in items}
        
        geo_correct = 0
        tech_correct = 0
        for c in shortlist:
            canon = c.canonical_profile_url or c.profile_url
            gt = gt_lookup.get(canon)
            if gt:
                if gt["ground_truth_geo"] == "ELIGIBLE":
                    geo_correct += 1
                if gt["ground_truth_tech"]:
                    tech_correct += 1

        geo_precision = round(geo_correct / max(1, shortlist_count), 2) if shortlist_count else 0.0
        tech_precision = round(tech_correct / max(1, shortlist_count), 2) if shortlist_count else 0.0
        avg_coverage = round(sum(c.mandatory_skill_coverage or 0.0 for c in shortlist) / max(1, shortlist_count), 2) if shortlist_count else 0.0

        return {
            "total_discovered": total_discovered,
            "unique_profiles": unique_profiles,
            "duplicate_rate": duplicate_rate,
            "eligible_candidates": eligible_count,
            "geographic_mismatches": mismatch_count,
            "unresolved_candidates": unresolved_count,
            "explicit_matches": explicit_matches,
            "partial_matches": partial_matches,
            "shortlist_count": shortlist_count,
            "geographic_precision": geo_precision,
            "technical_precision": tech_precision,
            "avg_mandatory_skill_coverage": avg_coverage
        }

    def print_benchmark_comparison(self):
        print("=" * 65)
        print("RECRUITER COPILOT — GEOGRAPHIC VERIFICATION BENCHMARK")
        print("=" * 65)
        
        res_baseline = self.run_evaluation(use_geo_verification=False)
        res_improved = self.run_evaluation(use_geo_verification=True)

        print(f"{'Metric':<35} | {'Baseline':<12} | {'Improved (3-Tier)':<15}")
        print("-" * 65)
        print(f"{'Discovered Profiles':<35} | {res_baseline['total_discovered']:<12} | {res_improved['total_discovered']:<15}")
        print(f"{'Unique Profiles':<35} | {res_baseline['unique_profiles']:<12} | {res_improved['unique_profiles']:<15}")
        print(f"{'Duplicate Rate':<35} | {res_baseline['duplicate_rate']*100:.0f}%{'':<9} | {res_improved['duplicate_rate']*100:.0f}%")
        print(f"{'Geographic Mismatches Caught':<35} | {res_baseline['geographic_mismatches']:<12} | {res_improved['geographic_mismatches']:<15}")
        print(f"{'Shortlist Count':<35} | {res_baseline['shortlist_count']:<12} | {res_improved['shortlist_count']:<15}")
        print(f"{'Geographic Precision':<35} | {res_baseline['geographic_precision']*100:.0f}%{'':<9} | {res_improved['geographic_precision']*100:.0f}%")
        print(f"{'Technical Precision':<35} | {res_baseline['technical_precision']*100:.0f}%{'':<9} | {res_improved['technical_precision']*100:.0f}%")
        print(f"{'Mandatory Skill Coverage':<35} | {res_baseline['avg_mandatory_skill_coverage']*100:.0f}%{'':<9} | {res_improved['avg_mandatory_skill_coverage']*100:.0f}%")
        print("=" * 65)


if __name__ == "__main__":
    harness = SearchEvaluationHarness()
    harness.print_benchmark_comparison()
