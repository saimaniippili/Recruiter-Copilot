import re
import json
from typing import Optional, List, Tuple
from ..core.schemas import (
    JobDescriptionSchema, RequirementSchema, RoleFamily,
    RequirementType, RequirementImportance
)
from .providers import llm_client


ROLE_FAMILY_PATTERNS = [
    (RoleFamily.UX_UI_DESIGN, [r'\bux\b', r'\bui\b', r'designer', r'product design', r'user experience']),
    (RoleFamily.EMBEDDED_FIRMWARE, [r'embedded', r'firmware', r'microcontroller', r'rtos', r'arm', r'dsp']),
    (RoleFamily.DATA_SCIENCE_ML, [r'data scien', r'machine learning', r'\bml\b', r'\bai\b', r'nlp', r'deep learning']),
    (RoleFamily.DATA_ENGINEERING, [r'data engineer', r'spark', r'hadoop', r'etl', r'dbt', r'snowflake']),
    (RoleFamily.DEVOPS_SRE_CLOUD, [r'devops', r'\bsre\b', r'cloud', r'kubernetes', r'terraform', r'aws', r'docker']),
    (RoleFamily.CYBERSECURITY, [r'security', r'cyber', r'penetration', r'infosec', r'soc']),
    (RoleFamily.PRODUCT_MANAGEMENT, [r'product manager', r'product owner', r'\btpm\b']),
    (RoleFamily.QA_TEST_ENGINEERING, [r'qa', r'quality assurance', r'test automation', r'sdet', r'software tester']),
    (RoleFamily.HARDWARE_ELECTRONICS, [r'hardware', r'pcb', r'fpga', r'circuit', r'asic']),
    (RoleFamily.SOFTWARE_ENGINEERING, [r'software', r'developer', r'engineer', r'backend', r'frontend', r'fullstack'])
]


def detect_role_family(role_title: str, jd_text: str) -> RoleFamily:
    combined = f"{role_title} {jd_text}".lower()
    for family, patterns in ROLE_FAMILY_PATTERNS:
        for p in patterns:
            if re.search(p, combined):
                return family
    return RoleFamily.GENERIC_OTHER


def parse_experience_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    match = re.search(r'(\d{1,2})\s*[\-–to]\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)', text, re.I)
    if match:
        return float(match.group(1)), float(match.group(2))
    
    match_min = re.search(r'(\d{1,2})\s*\+?\s*(?:years?|yrs?)', text, re.I)
    if match_min:
        return float(match_min.group(1)), None

    return None, None


def extract_starred_skills(jd_text: str) -> List[str]:
    """Extracts words or phrases marked with asterisk (*) e.g., *C++, *Figma."""
    raw_matches = re.findall(r'\*([a-zA-Z0-9\+#\.\s\-]{2,30})(?=[,\n\r\t\—\–\-]|$)', jd_text)
    cleaned = []
    for m in raw_matches:
        s = m.strip().strip('*').strip()
        if s and len(s.split()) <= 4:
            cleaned.append(s)
    return cleaned


def extract_job_description(jd_text: str) -> JobDescriptionSchema:
    """
    Extracts structured requirements using Groq/Ollama LLM with schema validation,
    with a deterministic regex fallback.
    """
    prompt = f"""You are a Principal Technical Talent Acquisition Architect.
Analyze the following Job Description and output ONLY valid JSON matching this schema:

{{
  "role_title": "Simplified job title, max 4 words (e.g. 'Senior Embedded Software Engineer' or 'UX Designer')",
  "locations": ["City, Country (e.g. 'Eindhoven, Netherlands')"],
  "seniority": "Senior / Lead / Mid / Junior",
  "experience_min_years": 6.0,
  "experience_max_years": 8.0,
  "mandatory_skills": ["List of core mandatory technical skills. Starred (*) items MUST be included"],
  "preferred_skills": ["List of nice-to-have skills"],
  "ambiguities": ["Any ambiguous points in the JD"]
}}

Job Description:
{jd_text[:3000]}"""

    response = llm_client.complete(
        prompt,
        system_prompt="You extract structured recruitment data. Output valid JSON only, no markdown.",
        temperature=0.1
    )

    title = ""
    locations = []
    min_yrs = None
    max_yrs = None
    mandatory = []
    preferred = []
    ambiguities = []

    if response:
        try:
            cleaned_json = re.sub(r'^```(?:json)?\s*', '', response.strip(), flags=re.MULTILINE)
            cleaned_json = re.sub(r'```\s*$', '', cleaned_json.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned_json)
            title = data.get("role_title", "").strip()
            loc_val = data.get("locations", [])
            if isinstance(loc_val, list):
                locations = [str(l).strip() for l in loc_val if str(l).strip()]
            elif loc_val:
                locations = [str(loc_val).strip()]
            min_yrs = data.get("experience_min_years")
            max_yrs = data.get("experience_max_years")
            mandatory = data.get("mandatory_skills", [])
            preferred = data.get("preferred_skills", [])
            ambiguities = data.get("ambiguities", [])
        except Exception:
            pass

    # Merge with explicit starred requirements from raw text to ensure no asterisks are lost
    starred = extract_starred_skills(jd_text)
    for s in starred:
        if s.lower() not in [m.lower() for m in mandatory]:
            mandatory.insert(0, s)

    # Experience fallback parsing
    if min_yrs is None and max_yrs is None:
        min_yrs, max_yrs = parse_experience_range(jd_text)

    # Location fallback parsing if LLM returned empty
    if not locations:
        loc_match = re.search(r'(?:location|based in|city|workplace)\s*[:\-]\s*([^\n\r]+)', jd_text, re.IGNORECASE)
        if loc_match:
            loc_raw = loc_match.group(1).strip()
            # Clean up trailing parens or notes
            loc_clean = re.split(r'\(|–|;', loc_raw)[0].strip()
            if loc_clean:
                locations = [loc_clean]

    # Smart Title extraction fallback if LLM returned empty or generic
    if not title or title.lower() in ("software engineer", "candidate", "generic"):
        # 1. Look for explicit role/title labels
        title_match = re.search(r'(?:role|title|position|job title|opening)\s*[:\-]\s*([^\n\r,]+)', jd_text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            # 2. Check for domain terms in text (e.g. SAP HANA, React, Embedded, etc.)
            tech_match = re.search(r'\b(SAP\s+(?:HANA|BW|BODS|FICO|SD)|Embedded|DevOps|Data\s+Engineer|Firmware|Cloud|Fullstack|Frontend|Backend|QA|Machine\s+Learning)\b', jd_text, re.IGNORECASE)
            if tech_match:
                title = f"{tech_match.group(1)} Specialist"
            elif starred:
                title = f"{starred[0]} Specialist"
            else:
                first_line = jd_text.strip().split("\n")[0].strip()
                if len(first_line) < 40 and not first_line.startswith("*"):
                    title = first_line
                else:
                    title = "Technical Specialist"

    role_fam = detect_role_family(title, jd_text)

    mand_reqs = [
        RequirementSchema(
            requirement_id=f"req_m_{idx+1}",
            normalized_name=name,
            importance=RequirementImportance.MANDATORY
        ) for idx, name in enumerate(mandatory[:8])
    ]

    pref_reqs = [
        RequirementSchema(
            requirement_id=f"req_p_{idx+1}",
            normalized_name=name,
            importance=RequirementImportance.PREFERRED
        ) for idx, name in enumerate(preferred[:6])
    ]

    return JobDescriptionSchema(
        role_title=title,
        role_family=role_fam,
        locations=locations if isinstance(locations, list) else [str(locations)],
        experience_min_years=min_yrs,
        experience_max_years=max_yrs,
        mandatory_requirements=mand_reqs,
        preferred_requirements=pref_reqs,
        ambiguous_requirements=ambiguities,
        raw_jd_text=jd_text
    )
