import re
from typing import List
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
    RoleFamily.QA_TEST_ENGINEERING: ['"QA Engineer"', '"Test Automation Engineer"', '"Software Test Engineer"']
}


def sanitize_term(term: str) -> str:
    return re.sub(r'[^\w\s\+\#\.\-]', ' ', term).strip()


def get_title_search_variants(title: str) -> List[str]:
    """Generates flexible search variants for long or specific job titles."""
    clean = sanitize_term(title)
    words = clean.split()
    if len(words) <= 2:
        return [f'"{clean}"']
    
    variants = [f'"{clean}"']
    seniority = {"senior", "lead", "principal", "junior", "staff", "head", "chief"}
    if words[0].lower() in seniority and len(words) >= 2:
        base_role = " ".join(words[1:])
        variants.append(f'"{base_role}"')
    elif len(words) >= 3:
        # e.g. "SAP HANA Cloud Consultant" -> '"SAP HANA" Consultant', '"SAP HANA Cloud"'
        variants.append(f'"{words[0]} {words[1]}" {words[-1]}')
        variants.append(f'"{words[0]} {words[1]}"')
    return variants


def format_skill_keyword(skill: str) -> str:
    """Formats skill into concise quoted keywords avoiding over-constraint."""
    clean = sanitize_term(skill)
    words = clean.split()
    if not words:
        return ""
    if len(words) <= 2:
        return f'"{clean}"'
    return f'"{words[0]} {words[1]}"'


def build_search_queries(jd: JobDescriptionSchema, max_queries: int = 4) -> List[str]:
    queries = []
    
    loc = jd.locations[0] if jd.locations else ""
    loc_clean = sanitize_term(loc) if loc and loc.lower() not in ("anywhere", "remote") else ""
    
    # Subdomain check
    subdomain = ""
    if loc_clean:
        for name, code in COUNTRY_SUBDOMAINS.items():
            if re.search(r'\b' + re.escape(name) + r'\b', loc_clean.lower()):
                subdomain = code
                break

    # Smart location clause
    loc_clause = ""
    if loc_clean:
        parts = [sanitize_term(p) for p in re.split(r'[,/]', loc) if sanitize_term(p)]
        if len(parts) > 1 and subdomain:
            loc_clause = parts[0]
        elif len(parts) > 1:
            loc_clause = f'{parts[0]} {parts[1]}'
        else:
            loc_clause = loc_clean

    mandatory_skills = [sanitize_term(r.normalized_name) for r in jd.mandatory_requirements if r.normalized_name]
    title_variants = get_title_search_variants(jd.role_title)
    primary_title = title_variants[0]
    flexible_title = title_variants[1] if len(title_variants) > 1 else primary_title
    
    # Base site target placed at the END of the query with trailing slash for 100% LinkedIn precision
    site_suffix = 'site:linkedin.com/in/'

    # 1. Skill-Combination Query (Pairs of top mandatory skills)
    if len(mandatory_skills) >= 2:
        q1 = f'{format_skill_keyword(mandatory_skills[0])} {format_skill_keyword(mandatory_skills[1])}'
    elif mandatory_skills:
        q1 = f'{format_skill_keyword(mandatory_skills[0])} {flexible_title}'
    else:
        q1 = f'{flexible_title}'
    if loc_clause:
        q1 += f' {loc_clause}'
    q1 += f' {site_suffix}'
    queries.append(q1.strip())

    # 2. Targeted Role + Primary Skill Query
    if mandatory_skills:
        q2 = f'{flexible_title} {format_skill_keyword(mandatory_skills[0])}'
    else:
        q2 = f'{flexible_title}'
    if loc_clause:
        q2 += f' {loc_clause}'
    q2 += f' {site_suffix}'
    queries.append(q2.strip())

    # 3. Third Skill or Standalone Core Skill
    if len(mandatory_skills) >= 3:
        q3 = f'{format_skill_keyword(mandatory_skills[0])} {format_skill_keyword(mandatory_skills[2])}'
    elif mandatory_skills:
        q3 = f'{format_skill_keyword(mandatory_skills[0])}'
    else:
        q3 = f'{primary_title}'
    if loc_clause:
        q3 += f' {loc_clause}'
    q3 += f' {site_suffix}'
    queries.append(q3.strip())

    # 4. Broad Role Query
    q4 = f'{primary_title}'
    if loc_clause:
        q4 += f' {loc_clause}'
    q4 += f' {site_suffix}'
    queries.append(q4.strip())

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
