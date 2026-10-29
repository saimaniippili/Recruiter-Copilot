import re
from typing import Optional, Tuple, List
from datetime import datetime


CURRENT_YEAR = 2026


def parse_explicit_years(text: str) -> Optional[float]:
    """Finds explicitly stated years of experience in text."""
    # Match patterns like "8 years of experience", "6+ years experience", "7 years C++ experience", "8-10 yrs"
    match = re.search(r'\b(\d{1,2})(?:\s*[\-–to]\s*(\d{1,2}))?\s*\+?\s*(?:years?|yrs?)(?:[^\n\r,\.]{0,25})?\s+experience\b', text, re.I)
    if match:
        min_yr = float(match.group(1))
        max_yr = float(match.group(2)) if match.group(2) else min_yr
        return (min_yr + max_yr) / 2.0

    match_prefix = re.search(r'\b(?:over|more than)\s+(\d{1,2})\s*(?:years?|yrs?)\b', text, re.I)
    if match_prefix:
        return float(match_prefix.group(1))

    return None


def parse_date_ranges_and_career_start(text: str) -> Optional[float]:
    """Estimates career duration from earliest mentioned employment/graduation year."""
    years = [int(y) for y in re.findall(r'\b(19[89]\d|20[012]\d)\b', text)]
    if not years:
        return None

    # Filter out impossible years
    valid_years = [y for y in years if 1980 <= y <= CURRENT_YEAR]
    if not valid_years:
        return None

    earliest_year = min(valid_years)
    # If the text has a range like 2018 - Present, duration is CURRENT_YEAR - earliest
    duration = CURRENT_YEAR - earliest_year
    return float(max(0, duration))


def extract_candidate_experience(headline: str, snippets: List[str]) -> Tuple[Optional[float], Optional[float], str]:
    """
    Returns:
    (stated_years, estimated_years, basis)
    basis: 'explicit_statement' | 'date_range' | 'unknown'
    """
    full_text = f"{headline} " + " ".join(snippets)

    stated = parse_explicit_years(full_text)
    if stated is not None:
        return stated, stated, "explicit_statement"

    estimated = parse_date_ranges_and_career_start(full_text)
    if estimated is not None:
        return None, estimated, "date_range_estimation"

    return None, None, "unknown"


def evaluate_experience_alignment(
    cand_years: Optional[float],
    min_years: Optional[float],
    max_years: Optional[float]
) -> Tuple[float, str]:
    """
    Calculates deterministic experience alignment score (0.0 to 1.0) and note.
    Does not assume missing evidence means unqualified.
    """
    if cand_years is None:
        return 0.5, "Experience not explicitly verified from public snippet (requires review)."

    if min_years is not None and max_years is not None:
        if min_years <= cand_years <= max_years:
            return 1.0, f"Exactly aligns with required range ({cand_years:.1f} yrs vs {min_years}-{max_years} target)."
        elif cand_years < min_years:
            gap = min_years - cand_years
            score = max(0.2, 1.0 - (gap * 0.25))
            return score, f"Slightly below target range ({cand_years:.1f} yrs vs min {min_years} yrs)."
        else: # cand_years > max_years
            excess = cand_years - max_years
            score = max(0.3, 1.0 - (excess * 0.08))
            return score, f"Senior candidate ({cand_years:.1f} yrs vs target {min_years}-{max_years} yrs)."

    if min_years is not None:
        if cand_years >= min_years:
            return 1.0, f"Meets minimum experience ({cand_years:.1f} yrs >= {min_years} yrs)."
        else:
            return 0.3, f"Below minimum experience ({cand_years:.1f} yrs < {min_years} yrs)."

    return 0.8, f"Candidate has ~{cand_years:.1f} years experience."
