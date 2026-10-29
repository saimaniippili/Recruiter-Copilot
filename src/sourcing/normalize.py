import re
import urllib.parse
from typing import Optional, Tuple, List, Dict, Any
from ..core.schemas import SearchResultSchema, CandidateSchema, CandidateLocationModel
from ..geography.location_extractor import extract_location_evidence


INVALID_NAME_WORDS = [
    "linkedin", "profile", "profiles", "member", "vacatures", "jobs", "hiring", 
    "careers", "directory", "sign in", "top 10", "top 20", "top 100", "over 100", 
    "community", "salary", "salaries", "guide", "tutorial"
]

RECRUITER_KEYWORDS = [
    "recruiter", "talent acquisition", "sourcer", "headhunter", "human resources", 
    "hr specialist", "hr manager", "people operations", "staffing consultant"
]

NON_TECHNICAL_TITLES = [
    "dietetics", "nutrition", "physician", "doctor of medicine",
    "nurse", "real estate", "attorney", "lawyer", "accountant", "sales representative",
    "broker", "pastor", "realtor"
]


def canonicalize_url(url: str) -> str:
    """
    Normalizes public profile URLs to a standard canonical representation.
    Handles LinkedIn (converting country subdomains like nl.linkedin.com to www.linkedin.com),
    stripping trailing slashes, fragments, and tracking parameters.
    """
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url.strip())
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')

    # LinkedIn normalization (Requirement D)
    if "linkedin.com" in netloc:
        # Match /in/username
        in_match = re.search(r'/in/([a-zA-Z0-9_\-%]+)', path, re.IGNORECASE)
        if in_match:
            username = in_match.group(1).lower()
            return f"https://www.linkedin.com/in/{username}"
        return f"https://www.linkedin.com{path}".lower()

    # GitHub normalization
    if "github.com" in netloc:
        parts = [p for p in path.split('/') if p]
        if parts:
            username = parts[0].lower()
            return f"https://github.com/{username}"
        return f"https://github.com{path}".lower()

    clean_path = path.lower()
    return f"{parsed.scheme or 'https'}://{netloc}{clean_path}"


def is_valid_profile_url(url: str) -> bool:
    """Verifies that the URL is a personal professional profile (LinkedIn or GitHub)."""
    if not url:
        return False
    url_lower = url.lower()
    
    if "github.com" in url_lower:
        parsed = urllib.parse.urlparse(url_lower)
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) == 1 and parts[0] not in ("features", "pricing", "topics", "collections", "trending", "explore", "search"):
            return True
        return False

    if not re.search(r'linkedin\.com/in/[a-zA-Z0-9_\-%]+', url, re.IGNORECASE):
        return False
    for forbidden in ["/jobs/", "/company/", "/school/", "/dir/", "/pulse/", "/learning/", "/posts/"]:
        if forbidden in url_lower:
            return False
    return True


def extract_name_and_headline(title: str, snippet: str) -> Tuple[str, str]:
    """Extracts human name and professional headline cleanly from title/snippet."""
    clean = title
    for suffix in [" | LinkedIn", " - LinkedIn", " | Professional Profile"]:
        clean = clean.split(suffix)[0]
    
    parts = clean.split(" - ")
    raw_name = parts[0].strip() if parts else "Candidate"
    
    # Clean up prefixes like Dr., Prof.
    name = re.sub(r'^(?:Dr\.|Prof\.|Mr\.|Ms\.)\s*', '', raw_name).strip()
    
    raw_headline = " - ".join(p.strip() for p in parts[1:] if p.strip()) if len(parts) > 1 else ""
    
    # Remove directory leakage from snippets
    if raw_headline:
        headline = re.split(r'\.\.\.|\b[A-Z][a-z]+\s+[A-Z][a-z]+\s*[-–|:]', raw_headline)[0].strip()
    else:
        headline = ""
    
    # Fallback to snippet preview if headline is short/missing
    if not headline and snippet:
        snippet_clean = re.sub(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s*[-–|:]', '', snippet).strip()
        headline = snippet_clean.split("·")[-1].strip()[:100]
        
    headline = re.sub(r'[\s\-–|]+$', '', headline).strip()
    if not headline:
        headline = "Technical Professional"

    return name, headline


def is_candidate_relevant(name: str, headline: str, snippet: str) -> bool:
    """Filters out non-person entries, recruiters, and non-tech profiles."""
    name_lower = name.lower()
    for bad in INVALID_NAME_WORDS:
        if bad in name_lower:
            return False
    if len(name) < 2 or len(name) > 45 or any(c.isdigit() for c in name):
        return False

    full_text = f"{headline} {snippet}".lower()

    # Anti-recruiter filter
    for rec in RECRUITER_KEYWORDS:
        if rec in full_text:
            if not any(t in headline.lower() for t in ["engineer", "developer", "architect", "programmer", "designer"]):
                return False

    # Anti-non-tech filter
    for bad in NON_TECHNICAL_TITLES:
        if bad in headline.lower():
            return False

    return True


def normalize_search_results(
    results: List[SearchResultSchema],
    expected_subdomain: str = ""
) -> List[CandidateSchema]:
    """
    Converts raw search results into canonical, deduplicated candidate models with
    source provenance and 3-tier geographic extraction.
    """
    candidates_by_canonical: Dict[str, CandidateSchema] = {}

    for r in results:
        if not is_valid_profile_url(r.url):
            continue

        canon_url = canonicalize_url(r.url)
        if not canon_url:
            continue

        netloc = urllib.parse.urlparse(r.url).netloc.lower()

        # Strict country subdomain check for India accounts
        if expected_subdomain and expected_subdomain != 'in' and 'in.linkedin.com' in netloc:
            continue

        # Extract geographic evidence via 3-Tier Layer 2 extractor
        loc_evidence: CandidateLocationModel = extract_location_evidence(r.title, r.snippet, r.url)

        # Merge duplicates if already seen (preserving source provenance)
        if canon_url in candidates_by_canonical:
            existing = candidates_by_canonical[canon_url]
            # Record multi-provider provenance
            existing.sources.append({
                "provider": r.provider,
                "url": r.url,
                "retrieved_at": r.retrieved_at,
                "query_used": r.query_used
            })
            if r.snippet and r.snippet not in existing.source_snippets:
                existing.source_snippets.append(r.snippet)
            # Update location if previous was empty or ambiguous
            if not existing.location and loc_evidence.value:
                existing.location = loc_evidence.value
                existing.current_location = loc_evidence
            continue

        name, headline = extract_name_and_headline(r.title, r.snippet)
        if not is_candidate_relevant(name, headline, r.snippet):
            continue

        c_id = f"cand_{hash(canon_url) & 0xffffffff:08x}"
        
        cand = CandidateSchema(
            candidate_id=c_id,
            name=name,
            profile_url=r.url,
            canonical_profile_url=canon_url,
            headline=headline,
            location=loc_evidence.value,
            current_location=loc_evidence,
            source_snippets=[r.snippet] if r.snippet else [],
            source_provider=r.provider,
            sources=[{
                "provider": r.provider,
                "url": r.url,
                "retrieved_at": r.retrieved_at,
                "query_used": r.query_used
            }],
            retrieved_at=r.retrieved_at,
            last_observed_at=r.retrieved_at
        )

        candidates_by_canonical[canon_url] = cand

    return list(candidates_by_canonical.values())
