import pytest
from src.sourcing.normalize import (
    canonicalize_url, is_valid_profile_url, normalize_search_results
)
from src.core.schemas import SearchResultSchema


def test_url_canonicalization():
    # Strip tracking parameters and trailing slashes
    url1 = "https://www.linkedin.com/in/aditya-sehrawat/?utm_source=share&utm_medium=member_desktop"
    assert canonicalize_url(url1) == "https://www.linkedin.com/in/aditya-sehrawat"

    # Country subdomain normalization to canonical global domain
    url2 = "https://nl.linkedin.com/in/erikpross/"
    assert canonicalize_url(url2) == "https://www.linkedin.com/in/erikpross"

    # Fragment removal
    url3 = "https://www.linkedin.com/in/johndoe#experience"
    assert canonicalize_url(url3) == "https://www.linkedin.com/in/johndoe"

    # GitHub normalization
    url4 = "https://github.com/torvalds/repositories?tab=stars"
    assert canonicalize_url(url4) == "https://github.com/torvalds"


def test_profile_url_validation():
    # Valid personal profiles
    assert is_valid_profile_url("https://www.linkedin.com/in/sarah-connor") is True
    assert is_valid_profile_url("https://nl.linkedin.com/in/sarah-connor") is True
    assert is_valid_profile_url("https://github.com/sarahconnor") is True

    # Invalid non-profile paths
    assert is_valid_profile_url("https://www.linkedin.com/jobs/view/123456") is False
    assert is_valid_profile_url("https://www.linkedin.com/company/google") is False
    assert is_valid_profile_url("https://www.linkedin.com/school/tudelft/") is False
    assert is_valid_profile_url("https://www.linkedin.com/dir/John/Doe") is False
    assert is_valid_profile_url("https://github.com/features") is False
    assert is_valid_profile_url("") is False


def test_duplicate_merging_with_source_provenance():
    # Same person discovered across 2 providers (e.g. SerpApi and DuckDuckGo)
    res1 = SearchResultSchema(
        title="Erik Pross - SAP Consultant | LinkedIn",
        url="https://nl.linkedin.com/in/erikpross",
        snippet="Based in Netherlands. SAP HANA Specialist.",
        provider="serpapi",
        query_used='site:nl.linkedin.com/in "SAP HANA"'
    )
    res2 = SearchResultSchema(
        title="Erik Pross - SAP Consultant at SUPERP | LinkedIn",
        url="https://www.linkedin.com/in/erikpross/?utm_source=share",
        snippet="Expert in Calculation Views and SQLScript.",
        provider="duckduckgo",
        query_used='site:www.linkedin.com/in "Calculation Views"'
    )

    candidates = normalize_search_results([res1, res2])
    # Must be deduplicated to 1 candidate
    assert len(candidates) == 1
    c = candidates[0]
    assert c.canonical_profile_url == "https://www.linkedin.com/in/erikpross"
    # Source provenance must retain both search providers
    assert len(c.sources) == 2
    providers = {s["provider"] for s in c.sources}
    assert "serpapi" in providers
    assert "duckduckgo" in providers
    # Snippets merged
    assert len(c.source_snippets) == 2
