import re
from typing import List, Optional, Dict, Any
from ..core.schemas import JobDescriptionSchema, RoleFamily


COUNTRY_SUBDOMAINS = {
    "netherlands": "nl", "amsterdam": "nl", "rotterdam": "nl", "eindhoven": "nl", "utrecht": "nl",
    "united kingdom": "uk", "uk": "uk", "london": "uk",
    "germany": "de", "berlin": "de", "munich": "de", "frankfurt": "de",
    "france": "fr", "paris": "fr",
    "canada": "ca", "toronto": "ca", "vancouver": "ca",
    "australia": "au", "sydney": "au", "melbourne": "au",
    "spain": "es", "madrid": "es", "barcelona": "es",
    "italy": "it", "milan": "it",
    "switzerland": "ch", "zurich": "ch",
    "belgium": "be", "brussels": "be",
    "sweden": "se", "stockholm": "se",
    "ireland": "ie", "dublin": "ie",
    "singapore": "sg",
    "uae": "ae", "dubai": "ae",
    "india": "in", "bengaluru": "in", "bangalore": "in", "hyderabad": "in", "chennai": "in", "pune": "in", "mumbai": "in", "delhi": "in"
}

ROLE_FAMILY_TITLE_VARIANTS = {
    RoleFamily.UX_UI_DESIGN: ['"UX Designer"', '"UI/UX Designer"', '"Product Designer"'],
    RoleFamily.EMBEDDED_FIRMWARE: ['"Embedded Software Engineer"', '"Firmware Engineer"', '"Embedded Systems Developer"'],
    RoleFamily.SOFTWARE_ENGINEERING: ['"Software Engineer"', '"Software Developer"', '"Backend Engineer"'],
    RoleFamily.DEVOPS_SRE_CLOUD: ['"DevOps Engineer"', '"Site Reliability Engineer"', '"Cloud Engineer"'],
    RoleFamily.DATA_SCIENCE_ML: ['"Data Scientist"', '"Machine Learning Engineer"', '"AI Engineer"'],
    RoleFamily.DATA_ENGINEERING: ['"Data Engineer"', '"Big Data Engineer"'],
    RoleFamily.CYBERSECURITY: ['"Security Engineer"', '"Information Security"', '"Cybersecurity Analyst"'],
    RoleFamily.PRODUCT_MANAGEMENT: ['"Product Manager"', '"Technical Product Manager"'],
    RoleFamily.QA_TEST_ENGINEERING: ['"QA Engineer"', '"Test Automation Engineer"', '"Software Test Engineer"'],
    RoleFamily.SAP_TECHNICAL_CONSULTING: ['"SAP HANA Consultant"', '"SAP Technical Consultant"', '"SAP Developer"', '"SAP Data Engineer"']
}


def sanitize_term(term: str) -> str:
    return re.sub(r'[^\w\s\+\#\.\-]', ' ', term).strip()


def get_title_search_variants(title: str) -> List[str]:
    """Generates flexible search variants for job titles."""
    clean = sanitize_term(title)
    words = clean.split()
    if len(words) <= 2:
        return [f'"{clean}"']
    
    variants = [f'"{clean}"']
    seniority = {"senior", "lead", "principal", "junior", "staff", "head", "chief", "sr"}
    if words[0].lower() in seniority and len(words) >= 2:
        base_role = " ".join(words[1:])
        variants.append(f'"{base_role}"')
    elif len(words) >= 3:
        variants.append(f'"{words[0]} {words[1]}" {words[-1]}')
        variants.append(f'"{words[0]} {words[1]}"')
    return variants


def format_skill_keyword(skill: str) -> str:
    """Formats skill into concise quoted keywords."""
    clean = sanitize_term(skill)
    words = clean.split()
    if not words:
        return ""
    if len(words) <= 2:
        return f'"{clean}"'
    return f'"{words[0]} {words[1]}"'


class MultiQuerySearchPlanner:
    """
    Requirement B & 5: Generates targeted query families for different search providers.
    Supports city-level, country-wide, subdomain, technical-evidence, and GitHub discovery.
    """

    def generate_plan(
        self,
        jd: JobDescriptionSchema,
        max_queries: int = 5,
        enable_negative_geo: bool = True
    ) -> List[str]:
        queries: List[str] = []
        
        loc_str = jd.locations[0] if jd.locations else ""
        if jd.location_spec and jd.location_spec.city:
            city = jd.location_spec.city
            country = jd.location_spec.country or "Netherlands"
        else:
            parts = [sanitize_term(p) for p in re.split(r'[,/]', loc_str) if sanitize_term(p)]
            city = parts[0] if parts else ""
            country = parts[-1] if len(parts) > 1 else (city or "")

        all_loc_text = f"{jd.role_title} {loc_str} {city} {country}".lower()
        is_india = any(c in all_loc_text for c in ["india", "hyderabad", "bangalore", "bengaluru", "chennai", "pune", "mumbai", "delhi", "noida"])
        is_nl = any(c in all_loc_text for c in ["netherlands", "nederland", "eindhoven", "amsterdam", "rotterdam", "utrecht"])

        # Determine target LinkedIn country subdomain (Requirement B & 5)
        target_subdomain = ""
        for name, code in COUNTRY_SUBDOMAINS.items():
            if re.search(r'\b' + re.escape(name) + r'\b', all_loc_text):
                target_subdomain = code
                break

        # Note: Use site:linkedin.com/in globally without forcing country subdomains,
        # as Google indexes all profiles under linkedin.com/in and localizes via regional parameters.
        primary_site = "site:linkedin.com/in"
        alt_site = "site:linkedin.com/in"

        # Negative geo exclusion clause
        if enable_negative_geo and not is_india and is_nl:
            neg_clause = " -India -Bengaluru -Bangalore -Hyderabad -Pune -Chennai"
        else:
            neg_clause = ""

        mand_skills = [sanitize_term(r.normalized_name) for r in jd.mandatory_requirements if r.normalized_name]
        titles = get_title_search_variants(jd.role_title)
        primary_title = titles[0]
        flex_title = titles[1] if len(titles) > 1 else primary_title

        # Query Family 1: Core Technical Skill + Location Anchor
        loc_anchor = city if city else (country if country else "")
        if mand_skills:
            q1 = f'{primary_site} {format_skill_keyword(mand_skills[0])} {loc_anchor}'.strip()
            queries.append(q1)

        # Query Family 2: Role Title + Location Anchor
        q2 = f'{primary_site} {flex_title} {loc_anchor}'.strip()
        queries.append(q2)

        # Query Family 3: Secondary Skill + Location Anchor
        if len(mand_skills) >= 2:
            q3 = f'{primary_site} {format_skill_keyword(mand_skills[1])} {loc_anchor}'.strip()
            queries.append(q3)
        elif primary_title != flex_title:
            q3 = f'{primary_site} {primary_title} {loc_anchor}'.strip()
            queries.append(q3)

        # Query Family 4: Regional Expansion
        if country and country.lower() != (city or "").lower():
            q4 = f'{primary_site} {format_skill_keyword(mand_skills[0]) if mand_skills else primary_title} {country}'.strip()
            queries.append(q4)

        # Query Family 5: GitHub Technical Evidence Query
        if mand_skills and loc_anchor:
            q5 = f'site:github.com {format_skill_keyword(mand_skills[0])} "{loc_anchor}"'.strip()
            queries.append(q5)

        # Deduplicate while preserving order
        seen = set()
        final_queries = []
        for q in queries:
            norm = q.lower().strip()
            if norm not in seen:
                seen.add(norm)
                final_queries.append(q)
                if len(final_queries) >= max_queries:
                    break

        return final_queries


def build_search_queries(
    jd: JobDescriptionSchema,
    max_queries: int = 4,
    enable_negative_geo: bool = True
) -> List[str]:
    """Compatibility entry point for query generation."""
    planner = MultiQuerySearchPlanner()
    return planner.generate_plan(jd, max_queries=max_queries, enable_negative_geo=enable_negative_geo)
