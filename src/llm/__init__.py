from .extraction import extract_job_description, extract_starred_skills, parse_experience_range, detect_role_family
from .providers import llm_client

# Backward compatibility wrappers
def ai_parse_jd(jd_text: str):
    jd = extract_job_description(jd_text)
    mand_str = ", ".join([r.normalized_name for r in jd.mandatory_requirements])
    pref_str = ", ".join([r.normalized_name for r in jd.preferred_requirements])
    exp_str = f"{jd.experience_min_years or ''}-{jd.experience_max_years or ''} years" if jd.experience_min_years else ""
    loc_str = ", ".join(jd.locations) if jd.locations else "Netherlands"
    return jd.role_title, loc_str, mand_str, pref_str, exp_str
