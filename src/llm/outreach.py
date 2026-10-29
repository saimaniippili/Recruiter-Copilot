from typing import Dict, Any, Optional
from .providers import llm_client


def generate_outreach_message(
    candidate: Dict[str, Any],
    role_title: str,
    company_name: str = "Our Team",
    tone: str = "Professional & Engaging"
) -> str:
    """
    Drafts an authentic, personalized recruitment outreach message (LinkedIn InMail or Email)
    citing the candidate's exact background and matching skills.
    """
    name = candidate.get("name") or "there"
    headline = candidate.get("headline") or candidate.get("bio") or ""
    score = candidate.get("score") or candidate.get("preliminary_match_score") or 85
    notes = candidate.get("fit_summary") or candidate.get("headline") or ""

    prompt = f"""You are a top technical talent acquisition specialist writing a high-converting candidate outreach message.
Role being hired for: {role_title} at {company_name}
Target Candidate:
- Name: {name}
- Current Headline / Bio: {headline}
- Key Strengths & Fit: {notes}
- Desired Tone: {tone}

Instructions:
1. Write a short, personalized outreach message (max 180 words).
2. Avoid generic recruiter clichés ("I came across your profile and was impressed").
3. Reference specific aspects of their background ({notes or headline}).
4. Include a low-friction call-to-action (e.g. 15-minute sync).
5. Provide a Subject Line and the Body.
"""

    system_prompt = "You write crisp, authentic, high-converting recruitment emails and LinkedIn InMails."
    response = llm_client.complete(prompt, system_prompt=system_prompt, temperature=0.7)

    if response:
        return response.strip()

    # Deterministic fallback if LLM is unavailable
    first_name = name.split()[0] if name else "there"
    return f"""Subject: {role_title} opportunity at {company_name}

Hi {first_name},

I noticed your strong background as {headline}. Given your technical experience, I wanted to reach out regarding our open {role_title} position at {company_name}.

We are building out our team and looking for someone with your specific domain expertise. Would you be open to a brief 15-minute introductory conversation this week to explore if this could be an exciting next step?

Best regards,
Talent Acquisition Team
{company_name}"""
