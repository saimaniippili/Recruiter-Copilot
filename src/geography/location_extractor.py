import re
from typing import Optional, Tuple, List, Dict, Any
from ..core.schemas import LocationEvidenceCategory, VerificationStatus, CandidateLocationModel


# Known Indian IT hubs & terms
INDIAN_GEO_TOKENS = {
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai",
    "delhi", "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad", "karnataka",
    "telangana", "tamil nadu", "maharashtra", "andhra pradesh"
}

# Known Dutch locations & terms
DUTCH_GEO_TOKENS = {
    "netherlands", "nederland", "eindhoven", "amsterdam", "rotterdam", "utrecht",
    "hague", "den haag", "'s-hertogenbosch", "den bosch", "veldhoven", "tilburg",
    "breda", "noord-brabant", "north brabant", "zuid-holland", "randstad", "dutch"
}

# Well-known enterprise clients where offshore consultants frequently list project work
DUTCH_CLIENT_COMPANIES = {
    "asml", "philips", "shell", "heineken", "ing", "abn amro", "akzonobel",
    "asml netherlands", "philips healthcare", "dsm", "kpn", "nn group"
}

# Indian IT service firms known for offshore AMS
INDIAN_CONSULTING_COMPANIES = {
    "infosys", "tcs", "tata consultancy", "wipro", "cognizant", "hcl", "tech mahindra",
    "l&t", "lti", "ltimindtree", "capgemini india", "accenture india", "zensar"
}


def clean_snippet_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def extract_location_evidence(
    title: str,
    snippet: str,
    url: str
) -> CandidateLocationModel:
    """
    Extracts location claim, evidence category, supporting quotation, and verification status
    from a candidate's search result snippet and URL.
    """
    combined_text = f"{title} {snippet}"
    cleaned = clean_snippet_text(combined_text)
    url_lower = (url or '').lower()

    # 1. Check for hard country subdomains on LinkedIn
    is_in_subdomain = "in.linkedin.com" in url_lower
    is_nl_subdomain = "nl.linkedin.com" in url_lower

    # 2. Search snippet structure (LinkedIn snippet format: "Location · Role · Company" or "City, Country. Summary...")
    parts = [p.strip() for p in re.split(r'[\.·|•\-–—]', snippet) if p.strip()]
    first_part = parts[0] if parts else ""
    first_part_lower = first_part.lower()

    # 3. Check for explicit client-project mentions
    # e.g. "Worked on ASML Eindhoven project", "Client: ASML Netherlands", "Consultant for Philips", "Project in Netherlands"
    project_match = re.search(
        r'(?:client|project|account|offshore\s+for|consultant\s+for|supporting|implementation\s+for)\s*[:\-–]?\s*([a-zA-Z0-9\s]{2,25}(?:asml|philips|shell|heineken|netherlands|eindhoven)[a-zA-Z0-9\s]{0,20})',
        cleaned,
        re.IGNORECASE
    ) or re.search(r'\b(?:client\s+project|offshore\s+project)\s+in\s+(?:netherlands|eindhoven)\b', cleaned, re.IGNORECASE)

    # 4. Check for LinkedIn standard card location header: "[Location] · 500+ connections/connecties" or "Locatie: [City]"
    card_loc_match = re.search(
        r'(?:(?:locatie|location)\s*[:\-–]\s*)?([a-zA-Z\s,]{2,35}?)\s*[·•]\s*\d+\+?\s*(?:connections|connecties)',
        cleaned,
        re.IGNORECASE
    )
    if card_loc_match:
        extracted_card_loc = card_loc_match.group(1).strip()
        card_loc_lower = extracted_card_loc.lower()
        non_loc_tokens = ['speaker', 'summit', 'conference', 'developer', 'engineer', 'architect', 'project', 'client', 'event', 'keynote', 'meetup', 'talk', 'university']
        if not any(tok in card_loc_lower for tok in non_loc_tokens):
            if any(tok in card_loc_lower for tok in INDIAN_GEO_TOKENS):
                q = card_loc_match.group(0).strip()
                if project_match or any(tok in cleaned.lower() for tok in DUTCH_GEO_TOKENS):
                    return CandidateLocationModel(
                        value=f"India (Client Project: Netherlands)",
                        evidence_type=LocationEvidenceCategory.CLIENT_PROJECT_LOCATION,
                        verification_status=VerificationStatus.INFERRED,
                        source_url=url,
                        supporting_quotation=q,
                        explanation=f"Candidate is based in India ({extracted_card_loc}) but snippet references Dutch client/project: '{q}'."
                    )
                return CandidateLocationModel(
                    value=extracted_card_loc,
                    evidence_type=LocationEvidenceCategory.CURRENT_WORK_LOCATION,
                    verification_status=VerificationStatus.SELF_REPORTED,
                    source_url=url,
                    supporting_quotation=card_loc_match.group(0).strip(),
                    explanation=f"LinkedIn card indicates candidate location in India: '{extracted_card_loc}'."
                )
            elif any(tok in card_loc_lower for tok in DUTCH_GEO_TOKENS):
                return CandidateLocationModel(
                    value=extracted_card_loc,
                    evidence_type=LocationEvidenceCategory.CURRENT_RESIDENCE,
                    verification_status=VerificationStatus.SELF_REPORTED,
                    source_url=url,
                    supporting_quotation=card_loc_match.group(0).strip(),
                    explanation=f"LinkedIn profile card verifies residence in Netherlands: '{extracted_card_loc}'."
                )

    # 5. Check for current residence or headline location markers (English and Dutch)
    residence_match = re.search(
        r'(?:based\s+in|living\s+in|located\s+in|(?:location|locatie)\s*[:\-–]|residing\s+in|woonachtig\s+in)\s*([a-zA-Z\s,]{3,35})',
        cleaned,
        re.IGNORECASE
    )

    # --- CLASSIFICATION LOGIC ---

    # Case A: Offshore consultant with India residence/registration
    if is_in_subdomain or any(tok in first_part_lower for tok in INDIAN_GEO_TOKENS):
        q = project_match.group(0).strip() if project_match else first_part
        if project_match or any(tok in cleaned.lower() for tok in DUTCH_GEO_TOKENS):
            return CandidateLocationModel(
                value="India (Client Project: Netherlands)",
                evidence_type=LocationEvidenceCategory.CLIENT_PROJECT_LOCATION,
                verification_status=VerificationStatus.INFERRED,
                source_url=url,
                supporting_quotation=q,
                explanation=f"Candidate is based in India but snippet references Dutch client/project: '{q}'."
            )
        return CandidateLocationModel(
            value="India",
            evidence_type=LocationEvidenceCategory.CURRENT_WORK_LOCATION,
            verification_status=VerificationStatus.SELF_REPORTED,
            source_url=url,
            supporting_quotation=first_part or "in.linkedin.com profile",
            explanation=f"Candidate profile is located in India ({first_part})."
        )

    # Case B: Explicit Client project mention without confirmed employee residence
    if project_match:
        quotation = project_match.group(0).strip()
        return CandidateLocationModel(
            value="Ambiguous (Client Project)",
            evidence_type=LocationEvidenceCategory.CLIENT_PROJECT_LOCATION,
            verification_status=VerificationStatus.UNVERIFIED,
            source_url=url,
            supporting_quotation=quotation,
            explanation=f"Snippet mentions client project: '{quotation}', but does not establish employee residence."
        )

    # Case C: Confirmed Current Residence in Netherlands / Eindhoven
    if residence_match and any(tok in residence_match.group(1).lower() for tok in DUTCH_GEO_TOKENS):
        loc_str = residence_match.group(1).strip()
        return CandidateLocationModel(
            value=loc_str,
            evidence_type=LocationEvidenceCategory.CURRENT_RESIDENCE,
            verification_status=VerificationStatus.SELF_REPORTED,
            source_url=url,
            supporting_quotation=residence_match.group(0),
            explanation=f"Explicit self-reported current residence: '{residence_match.group(0)}'."
        )

    # Case D: LinkedIn snippet leading location indicates Netherlands
    non_loc_tokens = ['speaker', 'summit', 'conference', 'developer', 'engineer', 'architect', 'project', 'client', 'event', 'keynote', 'meetup', 'talk']
    if any(tok in first_part_lower for tok in DUTCH_GEO_TOKENS):
        if not any(comp in first_part_lower for comp in DUTCH_CLIENT_COMPANIES) and not any(tok in first_part_lower for tok in non_loc_tokens):
            return CandidateLocationModel(
                value=first_part,
                evidence_type=LocationEvidenceCategory.CURRENT_WORK_LOCATION,
                verification_status=VerificationStatus.SELF_REPORTED,
                source_url=url,
                supporting_quotation=first_part,
                explanation=f"Profile snippet header location indicates Netherlands: '{first_part}'."
            )

    # Case E: Contextual preposition or regional match (e.g. "...systems in Eindhoven", "Eindhoven Area", "Eindhoven en omgeving", "Regio Eindhoven")
    city_compound_match = re.search(
        r'\b(eindhoven|amsterdam|rotterdam|utrecht|veldhoven|delft)\s*(?:,\s*(?:noord-brabant|north\s+brabant|zuid-holland|nederland|netherlands)|\s+(?:area|region|en\s+omgeving))\b',
        cleaned,
        re.IGNORECASE
    )
    if city_compound_match:
        city_found = city_compound_match.group(1).title()
        return CandidateLocationModel(
            value=f"{city_found} Area",
            evidence_type=LocationEvidenceCategory.CURRENT_WORK_LOCATION,
            verification_status=VerificationStatus.SELF_REPORTED,
            source_url=url,
            supporting_quotation=city_compound_match.group(0),
            explanation=f"Profile specifies verified city presence: '{city_compound_match.group(0)}'."
        )

    regio_match = re.search(r'\b(?:regio\s+(eindhoven|amsterdam|rotterdam|utrecht)|(eindhoven|amsterdam|rotterdam|utrecht)\s+en\s+omgeving)\b', cleaned, re.IGNORECASE)
    if regio_match:
        city_found = (regio_match.group(1) or regio_match.group(2)).title()
        return CandidateLocationModel(
            value=f"{city_found} Area",
            evidence_type=LocationEvidenceCategory.CURRENT_WORK_LOCATION,
            verification_status=VerificationStatus.SELF_REPORTED,
            source_url=url,
            supporting_quotation=regio_match.group(0),
            explanation=f"Profile specifies regional presence: '{regio_match.group(0)}'."
        )

    in_loc_match = re.search(r'\b(?:in|near|around)\s+(eindhoven|amsterdam|rotterdam|utrecht|netherlands|nederland|brabant|veldhoven|delft)\b', cleaned, re.IGNORECASE)
    if in_loc_match:
        loc_found = in_loc_match.group(1).title()
        return CandidateLocationModel(
            value=loc_found,
            evidence_type=LocationEvidenceCategory.CURRENT_WORK_LOCATION,
            verification_status=VerificationStatus.SELF_REPORTED,
            source_url=url,
            supporting_quotation=in_loc_match.group(0),
            explanation=f"Profile mentions working in {loc_found} ('{in_loc_match.group(0)}')."
        )

    # Case D: LinkedIn snippet leading location indicates India
    if is_in_subdomain or any(tok in first_part_lower for tok in INDIAN_GEO_TOKENS):
        # Extract quotation
        q = first_part if any(tok in first_part_lower for tok in INDIAN_GEO_TOKENS) else "in.linkedin.com profile registration"
        return CandidateLocationModel(
            value="India",
            evidence_type=LocationEvidenceCategory.CURRENT_WORK_LOCATION if not is_in_subdomain else LocationEvidenceCategory.SELF_REPORTED_LOCATION,
            verification_status=VerificationStatus.SELF_REPORTED,
            source_url=url,
            supporting_quotation=q,
            explanation=f"Candidate profile is located in India ({q})."
        )

    # Case E: Client project mention without clear location
    if project_match:
        quotation = project_match.group(0).strip()
        return CandidateLocationModel(
            value="Ambiguous (Client Project)",
            evidence_type=LocationEvidenceCategory.CLIENT_PROJECT_LOCATION,
            verification_status=VerificationStatus.UNVERIFIED,
            source_url=url,
            supporting_quotation=quotation,
            explanation=f"Snippet mentions client project: '{quotation}', but does not establish employee residence."
        )

    # Case F: nl.linkedin.com subdomain alone without textual evidence
    if is_nl_subdomain:
        return CandidateLocationModel(
            value="Netherlands (Subdomain only)",
            evidence_type=LocationEvidenceCategory.AMBIGUOUS_LOCATION,
            verification_status=VerificationStatus.INFERRED,
            source_url=url,
            supporting_quotation="nl.linkedin.com/in URL",
            explanation="LinkedIn country subdomain indicates Netherlands account, but snippet provides no current residence context."
        )

    # Case G: Inconclusive / No Location Evidence
    return CandidateLocationModel(
        value=None,
        evidence_type=LocationEvidenceCategory.NO_LOCATION_EVIDENCE,
        verification_status=VerificationStatus.UNKNOWN,
        source_url=url,
        supporting_quotation=None,
        explanation="No conclusive geographic residence evidence found in profile snippet."
    )
