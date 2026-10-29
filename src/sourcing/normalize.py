import re
import urllib.parse
from typing import Optional, Tuple, List
from ..core.schemas import SearchResultSchema, CandidateSchema


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
    """Strips tracking query parameters and trailing slashes from URLs."""
    parsed = urllib.parse.urlparse(url)
    clean_path = parsed.path.rstrip('/')
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}".lower()


def is_valid_profile_url(url: str) -> bool:
    """Verifies that the URL is a personal LinkedIn profile."""
    if not url:
        return False
    if not re.search(r'linkedin\.com/in/[a-zA-Z0-9_\-%]+', url, re.IGNORECASE):
        return False
    for forbidden in ["/jobs/", "/company/", "/school/", "/dir/", "/pulse/", "/learning/", "/posts/"]:
        if forbidden in url.lower():
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
    
    # Remove directory leakage from snippets (e.g., "...Aditya Sehrawat - SAP Technical Architect...")
    if raw_headline:
        # Cut off at ellipses or subsequent person names
        headline = re.split(r'\.\.\.|\b[A-Z][a-z]+\s+[A-Z][a-z]+\s*[-–|:]', raw_headline)[0].strip()
    else:
        headline = ""
    
    # Fallback to snippet preview if headline is short/missing
    if not headline and snippet:
        # Clean leading noise from snippet
        snippet_clean = re.sub(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s*[-–|:]', '', snippet).strip()
        headline = snippet_clean.split("·")[-1].strip()[:100]
        
    # Final cleanups: strip trailing dashes or punctuation
    headline = re.sub(r'[\s\-–|]+$', '', headline).strip()
    if not headline:
        headline = "Technical Professional"

    return name, headline


def is_candidate_relevant(name: str, headline: str, snippet: str) -> bool:
    """Filters out non-person entries, recruiters, and obvious non-tech profiles."""
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
            # Allow only if headline explicitly indicates technical/engineering role
            if not any(t in headline.lower() for t in ["engineer", "developer", "architect", "programmer", "designer"]):
                return False

    # Anti-non-tech filter
    for bad in NON_TECHNICAL_TITLES:
        if bad in headline.lower():
            return False

    return True


def normalize_search_results(results: List[SearchResultSchema], expected_subdomain: str = "") -> List[CandidateSchema]:
    """Converts raw search results into canonical, deduplicated candidate models."""
    candidates = []
    seen_urls = set()

    for r in results:
        if not is_valid_profile_url(r.url):
            continue

        # Geo-fencing: reject profiles whose country subdomain explicitly conflicts with target
        if expected_subdomain:
            netloc = urllib.parse.urlparse(r.url).netloc.lower()
            subparts = netloc.split('.')
            if len(subparts) >= 3 and subparts[0] not in ('www', 'linkedin'):
                cand_sub = subparts[0]
                if cand_sub != expected_subdomain:
                    continue

        canon_url = canonicalize_url(r.url)
        if canon_url in seen_urls:
            continue

        name, headline = extract_name_and_headline(r.title, r.snippet)
        if not is_candidate_relevant(name, headline, r.snippet):
            continue

        seen_urls.add(canon_url)
        c_id = f"cand_{hash(canon_url) & 0xffffffff:08x}"
        
        candidates.append(
            CandidateSchema(
                candidate_id=c_id,
                name=name,
                profile_url=r.url,
                headline=headline,
                source_snippets=[r.snippet] if r.snippet else [],
                source_provider=r.provider,
                retrieved_at=r.retrieved_at
            )
        )

    return candidates
