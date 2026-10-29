from typing import Optional, List, Tuple
from ..core.schemas import (
    LocationRequirementSchema, CandidateLocationModel,
    GeographicEligibilityModel, GeographicEligibilityStatus,
    LocationEvidenceCategory, VerificationStatus
)


class ConservativeGeographicResolver:
    """
    Conservative Geographic Eligibility Resolver (Requirement F).
    Evaluates candidate location evidence against job policy.
    Never assumes eligibility from client projects or subdomains alone.
    """

    def resolve_eligibility(
        self,
        target_city: Optional[str],
        target_country: Optional[str],
        work_mode: str,
        relocation_allowed: bool,
        candidate_loc: CandidateLocationModel
    ) -> GeographicEligibilityModel:
        target_country_norm = (target_country or "").lower().strip()
        target_city_norm = (target_city or "").lower().strip()
        work_mode_norm = (work_mode or "HYBRID").upper().strip()

        # Remote-first jobs without geographic restrictions
        if work_mode_norm == "REMOTE" and not target_country_norm:
            return GeographicEligibilityModel(
                status=GeographicEligibilityStatus.ELIGIBLE,
                reason="Role is 100% remote with no mandatory geographic restriction.",
                supporting_evidence=["Work arrangement: REMOTE"]
            )

        val_lower = (candidate_loc.value or "").lower()

        # 1. No evidence available
        if candidate_loc.evidence_type in (
            LocationEvidenceCategory.NO_LOCATION_EVIDENCE,
            LocationEvidenceCategory.AMBIGUOUS_LOCATION
        ):
            return GeographicEligibilityModel(
                status=GeographicEligibilityStatus.UNKNOWN,
                reason="Insufficient evidence: Profile snippet contains no verifiable residence claim.",
                supporting_evidence=[candidate_loc.explanation or "No location evidence found"]
            )

        # 2. Conflicting / Offshore residency detected (e.g. candidate in India with client project in Netherlands)
        is_in_india = any(c in val_lower for c in ["india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai", "delhi", "noida"])
        target_is_nl = target_country_norm in ("netherlands", "nl") or "eindhoven" in target_city_norm

        if target_is_nl and is_in_india:
            if relocation_allowed and candidate_loc.evidence_type == LocationEvidenceCategory.RELOCATION_REPORTED:
                return GeographicEligibilityModel(
                    status=GeographicEligibilityStatus.ELIGIBLE,
                    reason="Candidate is in India but has documented, accepted relocation intent.",
                    supporting_evidence=[f"Location: {candidate_loc.value}", "Relocation allowed by job policy"]
                )
            return GeographicEligibilityModel(
                status=GeographicEligibilityStatus.MISMATCH,
                reason=f"Location Mismatch: Candidate is located in {candidate_loc.value}; role requires residency in {target_city or target_country or 'Netherlands'}.",
                supporting_evidence=[
                    f"Evidence: {candidate_loc.explanation}",
                    f"Quotation: {candidate_loc.supporting_quotation or 'Confirmed India profile'}"
                ]
            )

        # 3. Client Project Location alone without confirmed residence (does NOT establish residency)
        if candidate_loc.evidence_type == LocationEvidenceCategory.CLIENT_PROJECT_LOCATION:
            return GeographicEligibilityModel(
                status=GeographicEligibilityStatus.UNKNOWN,
                reason=f"Ambiguous evidence: Mention of '{candidate_loc.supporting_quotation}' reflects client project work, not verified candidate residence.",
                supporting_evidence=[
                    f"Quotation: {candidate_loc.supporting_quotation}",
                    "Rule: Client-project location cannot be inferred as current residency."
                ]
            )
        
        if target_is_nl and is_in_india:
            if relocation_allowed and candidate_loc.evidence_type == LocationEvidenceCategory.RELOCATION_REPORTED:
                return GeographicEligibilityModel(
                    status=GeographicEligibilityStatus.ELIGIBLE,
                    reason="Candidate is in India but has documented, accepted relocation intent.",
                    supporting_evidence=[f"Location: {candidate_loc.value}", "Relocation allowed by job policy"]
                )
            return GeographicEligibilityModel(
                status=GeographicEligibilityStatus.MISMATCH,
                reason=f"Location Mismatch: Candidate is located in {candidate_loc.value}; role requires residency in {target_city or target_country or 'Netherlands'}.",
                supporting_evidence=[
                    f"Evidence: {candidate_loc.explanation}",
                    f"Quotation: {candidate_loc.supporting_quotation or 'Confirmed India profile'}"
                ]
            )

        # 4. Target Country / City Match
        is_target_country_match = False
        if target_is_nl:
            is_target_country_match = any(c in val_lower for c in ["netherlands", "nederland", "eindhoven", "amsterdam", "rotterdam", "utrecht", "brabant"])

        if is_target_country_match:
            # Check city-level requirement if strictly enforced
            if target_city_norm and target_city_norm in ("eindhoven",):
                in_eindhoven = any(c in val_lower for c in ["eindhoven", "veldhoven", "brabant", "noord-brabant"])
                if in_eindhoven:
                    return GeographicEligibilityModel(
                        status=GeographicEligibilityStatus.ELIGIBLE,
                        reason=f"Verified City Match: Candidate is located in {candidate_loc.value}.",
                        supporting_evidence=[
                            f"Location: {candidate_loc.value}",
                            f"Quotation: {candidate_loc.supporting_quotation}"
                        ]
                    )
                else:
                    # In Netherlands but different city (e.g. Amsterdam, Utrecht)
                    # Eligible under nationwide commuting / hybrid arrangement
                    return GeographicEligibilityModel(
                        status=GeographicEligibilityStatus.ELIGIBLE,
                        reason=f"Regional / Commuting Match: Candidate is located in {candidate_loc.value} (Netherlands commuting distance).",
                        supporting_evidence=[
                            f"Location: {candidate_loc.value}",
                            f"Quotation: {candidate_loc.supporting_quotation}"
                        ]
                    )

            return GeographicEligibilityModel(
                status=GeographicEligibilityStatus.ELIGIBLE,
                reason=f"Country Match: Candidate is verified in target country ({candidate_loc.value}).",
                supporting_evidence=[
                    f"Location: {candidate_loc.value}",
                    f"Quotation: {candidate_loc.supporting_quotation}"
                ]
            )

        # Fallback to UNKNOWN if country was not matched
        return GeographicEligibilityModel(
            status=GeographicEligibilityStatus.UNKNOWN,
            reason=f"Unresolved location: Detected '{candidate_loc.value}' could not be definitively matched to '{target_city or target_country}'.",
            supporting_evidence=[candidate_loc.explanation or "Location unresolved"]
        )


geographic_resolver = ConservativeGeographicResolver()
