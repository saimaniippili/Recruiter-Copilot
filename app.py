import os
import sys
import uuid
import json
import pandas as pd
import streamlit as st
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.core.config import settings
from src.core.schemas import CandidateSchema, JobStateEnum
from src.storage.db import repo
from src.jobs.orchestrator import orchestrator
from src.llm.extraction import extract_job_description
from src.sourcing.github_sourcing import GitHubSearchProvider
from src.sourcing.query_builder import build_search_queries
from src.llm.outreach import generate_outreach_message

# Set Page Config
st.set_page_config(
    page_title="Recruiter Copilot | AI Talent Sourcing",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast, Modern Enterprise CSS
st.markdown("""
<style>
    /* Global Typography & Spacing */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94A3B8;
        margin-bottom: 1.8rem;
    }
    
    /* Sleek Cards */
    .pro-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 12px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
    }
    .candidate-card-v2 {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 14px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .candidate-card-v2:hover {
        border-color: #3B82F6;
    }

    /* Badges */
    .badge-green {
        background-color: #064E3B;
        color: #6EE7B7;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-yellow {
        background-color: #78350F;
        color: #FCD34D;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-red {
        background-color: #7F1D1D;
        color: #FCA5A5;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .skill-chip {
        background-color: rgba(59, 130, 246, 0.15);
        color: #93C5FD;
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 3px 10px;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 500;
        display: inline-block;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .sidebar-status-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = None
if "active_job_title" not in st.session_state:
    st.session_state.active_job_title = "No active job"
if "parsed_jd" not in st.session_state:
    st.session_state.parsed_jd = None
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "github_results" not in st.session_state:
    st.session_state.github_results = []
if "last_queries_attempted" not in st.session_state:
    st.session_state.last_queries_attempted = []

# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown("### 🎯 Recruiter Copilot")
    st.caption("AI-Powered Multi-Source Talent Intelligence")
    st.markdown("---")

    st.markdown("#### ⚡ System Health")
    db_status = "🟢 Connected (SQLite)"
    ai_status = "🟢 Gemini / Groq Cloud" if (settings.GEMINI_API_KEY or settings.GROQ_API_KEY) else "🟡 Local Ollama"
    serp_status = "🟢 Active" if settings.SERPAPI_API_KEY else "⚪ DDG / Bing Fallback"

    st.markdown(f"""
    <div class="sidebar-status-box">
        <div style="font-size:0.85rem; margin-bottom:4px;"><b>Database:</b> {db_status}</div>
        <div style="font-size:0.85rem; margin-bottom:4px;"><b>AI Engine:</b> {ai_status}</div>
        <div style="font-size:0.85rem;"><b>Search Index:</b> {serp_status}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### ⚙️ Sourcing Mode")
    source_channel = st.radio(
        "Candidate Channel",
        ["LinkedIn Profiles (X-Ray)", "GitHub Developers (Open Source)", "Multi-Platform Search"],
        index=0
    )

    st.markdown("---")
    st.caption("🚀 Render Cloud Ready | Antigravity AI")

# --- Main App Header ---
st.markdown('<div class="hero-title">Technical Talent Intelligence Copilot</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Automated Job Description Analysis, Multi-Channel Sourcing, Semantic Evidence Scoring & Outreach</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "📥 1. Job Description & Sourcing",
    "👥 2. Candidate Talent Pool",
    "🐙 3. GitHub Developer Sourcing",
    "✉️ 4. AI Outreach Drafter",
    "📁 5. Sourcing Campaigns"
])

# ==========================================
# TAB 1: New Search & Job Analyzer
# ==========================================
with tabs[0]:
    st.subheader("1. Extract Job Criteria & Sourcing Rules")

    col_jd_main, col_jd_samples = st.columns([3, 1])

    with col_jd_samples:
        st.markdown("**Example Templates**")
        if st.button("📋 SAP HANA / BODS", use_container_width=True):
            st.session_state.raw_jd_text = """Role: SAP HANA Architect
Location: Global / Remote
Experience: 7-11 years

Must-Have Requirements:
*SLT
*SAP BODS
*AMS Support

Nice to Have:
SAP BW/4HANA, SAP BW on HANA, SAP FI / SD integration, Jenkins, Jira, Agile / Scrum

Experience:
*7-11 years of professional SAP HANA architecture, data modeling, and production support experience."""

        if st.button("📋 Embedded C++ Firmware", use_container_width=True):
            st.session_state.raw_jd_text = """Senior Embedded Software Engineer
Location: Eindhoven, Netherlands
Experience: 6 - 8 years

Must-Have Requirements:
* Proven experience with *C++17 and *C in safety-critical firmware
* Hands-on RTOS experience (FreeRTOS or Zephyr)
* Hardware communication protocols: I2C, SPI, CAN bus
* Microcontroller platforms: ARM Cortex-M

Preferred:
* Experience with Python for hardware test automation
* Knowledge of ISO 26262 functional safety standards"""

    with col_jd_main:
        initial_text = st.session_state.get("raw_jd_text", "")
        uploaded_doc = st.file_uploader("Upload Job Description (.txt, .md)", type=["txt", "md"])
        if uploaded_doc is not None:
            initial_text = uploaded_doc.read().decode("utf-8")

        jd_text_area = st.text_area(
            "Paste Raw Job Description",
            value=initial_text,
            height=220,
            placeholder="Paste complete Job Description here. Asterisk (*) items indicate mandatory requirements..."
        )

    col_btn_parse, col_btn_quick = st.columns([1, 2])
    with col_btn_parse:
        parse_btn = st.button("⚡ 1. Extract Requirements", use_container_width=True)
    with col_btn_quick:
        quick_source_btn = st.button("🚀 Fast 1-Click Source Candidates", type="primary", use_container_width=True)

    # Handle Extraction
    if parse_btn:
        if not jd_text_area.strip():
            st.warning("Please paste a Job Description first.")
        else:
            with st.spinner("Extracting structured criteria with AI..."):
                parsed = extract_job_description(jd_text_area)
                st.session_state.parsed_jd = parsed
                st.session_state.raw_jd_text = jd_text_area
                st.success("Extracted requirements below! You can review or adjust them before launching search.")

    # Show editable criteria if parsed
    current_parsed = st.session_state.parsed_jd
    if current_parsed or quick_source_btn:
        if not current_parsed and quick_source_btn:
            current_parsed = extract_job_description(jd_text_area)
            st.session_state.parsed_jd = current_parsed
            st.session_state.raw_jd_text = jd_text_area

        st.markdown("---")
        st.subheader("2. Review & Refine Sourcing Criteria")

        col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
        with col_c1:
            ui_role_title = st.text_input(
                "Role Title / Primary Focus",
                value=current_parsed.role_title if current_parsed else "Technical Specialist"
            )
        with col_c2:
            current_loc = current_parsed.locations[0] if current_parsed and current_parsed.locations else ""
            ui_location = st.text_input(
                "Target Location (Leave empty or 'Global' for worldwide)",
                value=current_loc,
                placeholder="e.g. India, United States, Netherlands, or leave blank"
            )
        with col_c3:
            ui_min_exp = st.number_input(
                "Min Experience (Yrs)",
                min_value=0.0,
                max_value=30.0,
                value=float(current_parsed.experience_min_years or 5.0),
                step=1.0
            )

        extracted_mand = [r.normalized_name for r in current_parsed.mandatory_requirements] if current_parsed else []
        ui_mandatory_str = st.text_input(
            "Must-Have Skills (Comma-separated)",
            value=", ".join(extracted_mand) if extracted_mand else "SAP BODS, SLT, AMS Support"
        )

        st.markdown("**Active Skill Tags:**")
        parsed_skills_list = [s.strip() for s in ui_mandatory_str.split(",") if s.strip()]
        for s in parsed_skills_list:
            st.markdown(f'<span class="skill-chip">⭐ {s}</span>', unsafe_allow_html=True)

        col_launch1, col_launch2 = st.columns([1, 3])
        with col_launch1:
            launch_search = st.button("🔍 Launch Search Pipeline", type="primary", use_container_width=True)

        # Trigger Pipeline Execution
        if launch_search or quick_source_btn:
            job_id = f"job_{uuid.uuid4().hex[:10]}"
            repo.create_job(job_id=job_id, chat_id=0, raw_jd=jd_text_area)

            status_container = st.status("🚀 Running Multi-Source Sourcing Pipeline...", expanded=True)
            status_container.write(f"Targeting: **{ui_role_title}** | Location: **{ui_location or 'Worldwide (No geo-fence)'}**")
            status_container.write(f"Key Skills: **{', '.join(parsed_skills_list)}**")

            def on_progress(msg: str):
                status_container.write(msg)

            try:
                candidates = orchestrator.run_sourcing_pipeline(
                    job_id=job_id,
                    chat_id=0,
                    raw_jd_text=jd_text_area,
                    progress_callback=on_progress,
                    override_role_title=ui_role_title,
                    override_location=ui_location,
                    override_mandatory_skills=parsed_skills_list
                )

                st.session_state.active_job_id = job_id
                st.session_state.active_job_title = ui_role_title
                st.session_state.candidates = repo.get_candidates(job_id)

                if candidates:
                    status_container.update(label=f"✅ Found & Scored {len(candidates)} Candidates!", state="complete", expanded=False)
                    st.success(f"🎉 Successfully discovered and scored **{len(candidates)}** candidate profiles! Switch to the **Candidate Talent Pool** tab to view them.")
                else:
                    status_container.update(label="⚠️ Search returned 0 candidates", state="error", expanded=True)
                    st.warning("No candidates matched your exact criteria. Suggestions:")
                    st.write("- Clear the Location field to search globally across all regions.")
                    st.write("- Reduce the number of mandatory skills (e.g. search for 1 or 2 core skills).")

            except Exception as e:
                status_container.update(label="❌ Pipeline Execution Error", state="error", expanded=True)
                st.error(f"Error during execution: {e}")

# ==========================================
# TAB 2: Candidate Pipeline
# ==========================================
with tabs[1]:
    st.subheader(f"Candidate Talent Pool | {st.session_state.active_job_title}")

    if st.session_state.active_job_id:
        st.session_state.candidates = repo.get_candidates(st.session_state.active_job_id)

    candidates_list = st.session_state.candidates

    if not candidates_list:
        st.info("No candidates loaded yet. Run a search in Tab 1, or select a previous campaign from Tab 5.")
    else:
        # Export Bar
        df_export = pd.DataFrame([
            {
                "Candidate ID": c.get("candidate_id"),
                "Name": c.get("name"),
                "Headline": c.get("headline"),
                "Match Score (%)": c.get("score"),
                "Eligibility": c.get("eligibility"),
                "Profile URL": c.get("profile_url")
            }
            for c in candidates_list
        ])
        csv_data = df_export.to_csv(index=False).encode("utf-8")

        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
        with col_f1:
            min_score = st.slider("Filter by Minimum Match Score", 0, 100, 30)
        with col_f2:
            status_filter = st.multiselect(
                "Filter Eligibility",
                options=["meets_verified_requirements", "requires_human_review", "insufficient_evidence", "does_not_meet_verified_requirement"],
                default=["meets_verified_requirements", "requires_human_review", "insufficient_evidence"]
            )
        with col_f3:
            st.download_button(
                label="📥 Download Pipeline (CSV)",
                data=csv_data,
                file_name=f"{st.session_state.active_job_id or 'recruiter_copilot'}_candidates.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Apply Filters
        filtered_candidates = [
            c for c in candidates_list
            if (c.get("score") or 0) >= min_score and (c.get("eligibility") in status_filter or not status_filter)
        ]

        st.caption(f"Showing **{len(filtered_candidates)}** of **{len(candidates_list)}** candidates")

        for idx, c in enumerate(filtered_candidates, 1):
            score = c.get("score", 0.0)
            if score >= 75:
                badge_html = f'<span class="badge-green">Match Score: {score:.1f}%</span>'
            elif score >= 50:
                badge_html = f'<span class="badge-yellow">Match Score: {score:.1f}%</span>'
            else:
                badge_html = f'<span class="badge-red">Match Score: {score:.1f}%</span>'

            eligibility = str(c.get("eligibility", "REQUIRES_REVIEW")).replace("_", " ").upper()
            evidence = {}
            if c.get("evidence_json"):
                try:
                    evidence = json.loads(c["evidence_json"])
                except Exception:
                    evidence = {}

            with st.container():
                st.markdown(f"""
                <div class="candidate-card-v2">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <h3 style="margin-top:0; margin-bottom:4px;">{idx}. {c.get('name') or 'Candidate'}</h3>
                            <p style="color:#CBD5E1; margin-bottom:8px; font-size:0.95rem;"><b>Headline:</b> {c.get('headline') or 'N/A'}</p>
                            <div>{badge_html} &nbsp; <span class="skill-chip">Status: {eligibility}</span></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_btn_view, col_btn_outreach = st.columns([1, 4])
                with col_btn_view:
                    profile_url = c.get("profile_url", "")
                    if profile_url:
                        st.link_button("🔗 View Profile", profile_url, use_container_width=True)

                fit_summary = evidence.get("fit_summary") or evidence.get("headline") or ""
                if fit_summary:
                    st.info(f"💡 **Evaluation Summary:** {fit_summary}")

                # Detailed evidence dropdown
                with st.expander("🔍 View Detailed Evidence & Requirements Verification"):
                    ev_map = evidence.get("evidence_by_requirement", {})
                    if ev_map:
                        for req_id, ev_data in ev_map.items():
                            classification = ev_data.get("classification", "unknown").replace("_", " ").title()
                            support = ev_data.get("supporting_text") or "No direct quote found"
                            st.write(f"- **{req_id}**: `{classification}` — *\"{support}\"*")
                    else:
                        st.write("No granular breakdown available.")

                st.markdown("---")

# ==========================================
# TAB 3: GitHub Technical Sourcing
# ==========================================
with tabs[2]:
    st.subheader("Direct GitHub Developer Sourcing")
    st.caption("Identify software engineers by programming language, location, star count, and verified open-source commits.")

    col_gh1, col_gh2, col_gh3, col_gh4 = st.columns(4)
    with col_gh1:
        gh_role = st.text_input("Specialty / Keywords", value="SAP OR Python OR Backend")
    with col_gh2:
        gh_lang = st.selectbox("Primary Language", ["Python", "C++", "Go", "Rust", "TypeScript", "Java", "All Languages"], index=0)
    with col_gh3:
        gh_loc = st.text_input("Location (Optional)", value="")
    with col_gh4:
        gh_followers = st.number_input("Min Followers", min_value=0, value=2, step=1)

    gh_search_btn = st.button("🐙 Search GitHub Developers", type="primary")

    if gh_search_btn:
        with st.spinner("Querying GitHub User & Repository Search API..."):
            gh_provider = GitHubSearchProvider()
            selected_lang = None if gh_lang == "All Languages" else gh_lang
            results = gh_provider.search_developers(
                keywords=gh_role,
                language=selected_lang,
                location=gh_loc if gh_loc.strip() else None,
                min_followers=int(gh_followers),
                max_results=15
            )
            st.session_state.github_results = results

    if st.session_state.github_results:
        st.success(f"Surfaced **{len(st.session_state.github_results)}** GitHub developers matching criteria!")

        for dev in st.session_state.github_results:
            with st.container():
                col_g1, col_g2, col_g3 = st.columns([1, 4, 2])
                with col_g1:
                    if dev.get("avatar_url"):
                        st.image(dev["avatar_url"], width=80)
                with col_g2:
                    st.markdown(f"#### [{dev['name']} (@{dev['username']})]({dev['profile_url']})")
                    if dev.get("bio"):
                        st.write(f"*{dev['bio']}*")
                    st.write(f"🏢 **Company:** {dev.get('company')} &nbsp;|&nbsp; 📍 **Location:** {dev.get('location')}")
                    st.write(f"📦 Public Repos: **{dev.get('public_repos')}** &nbsp;|&nbsp; 👥 Followers: **{dev.get('followers')}**")
                with col_g3:
                    st.link_button("🐙 View GitHub", dev["profile_url"], use_container_width=True)

                top_repos = dev.get("top_repos", [])
                if top_repos:
                    st.markdown("**Top Open Source Repositories:**")
                    r_cols = st.columns(len(top_repos))
                    for i, r in enumerate(top_repos):
                        with r_cols[i]:
                            st.markdown(f"⭐ **[{r['name']}]({r['url']})** ({r['stars']} stars)")
                            st.caption(f"{r['language']} — {r['description'][:70]}...")

                st.markdown("---")

# ==========================================
# TAB 4: AI Outreach & InMail Drafter
# ==========================================
with tabs[3]:
    st.subheader("Generate Personalized Candidate Outreach")
    st.caption("Draft authentic, high-converting cold emails and LinkedIn InMails citing verified background points.")

    all_active_candidates = st.session_state.candidates
    candidate_options = {c.get("name", "Unknown"): c for c in all_active_candidates} if all_active_candidates else {}

    col_o1, col_o2 = st.columns([2, 1])

    with col_o1:
        if candidate_options:
            selected_name = st.selectbox("Select Candidate to Contact", list(candidate_options.keys()))
            selected_candidate = candidate_options[selected_name]
        else:
            selected_candidate = {
                "name": "Alex Johnson",
                "headline": "Senior SAP HANA / BODS Architect",
                "fit_summary": "Extensive experience with SLT data replication, SAP BODS ETL pipelines, and AMS production support."
            }
            st.info("Loaded sample candidate template.")

        target_role = st.text_input("Role Title", value=st.session_state.active_job_title or "SAP HANA Specialist")
        company = st.text_input("Company / Client Name", value="Global Tech Solutions")
        tone = st.selectbox("Message Tone", ["Professional & Direct", "Enthusiastic & Casual", "Technical & Peer-to-Peer", "Executive"])

        generate_msg_btn = st.button("✨ Draft Personalized Message", type="primary")

    with col_o2:
        st.markdown("**Candidate Summary**")
        st.write(f"**Name:** {selected_candidate.get('name')}")
        st.write(f"**Headline:** {selected_candidate.get('headline') or selected_candidate.get('bio')}")
        if selected_candidate.get("fit_summary"):
            st.write(f"**Fit Highlights:** {selected_candidate['fit_summary']}")

    if generate_msg_btn:
        with st.spinner("Generating outreach with AI..."):
            draft = generate_outreach_message(
                candidate=selected_candidate,
                role_title=target_role,
                company_name=company,
                tone=tone
            )
            st.subheader("Generated Message Draft")
            st.text_area("Editable Draft", value=draft, height=240)

# ==========================================
# TAB 5: Sourcing History & Jobs
# ==========================================
with tabs[4]:
    st.subheader("Past Sourcing Campaigns & Archives")
    jobs = repo.list_jobs(limit=25)

    if not jobs:
        st.info("No saved sourcing jobs found in database.")
    else:
        for j in jobs:
            col_j1, col_j2, col_j3, col_j4 = st.columns([3, 2, 2, 2])
            with col_j1:
                st.markdown(f"**{j.get('role_title') or 'Untitled Role'}**")
                st.caption(f"ID: `{j.get('job_id')}`")
            with col_j2:
                st.write(f"Candidates: **{j.get('candidate_count', 0)}**")
                st.caption(f"Status: {j.get('state', '').upper()}")
            with col_j3:
                created = str(j.get("created_at", ""))[:19]
                st.write(f"Date: {created}")
            with col_j4:
                col_load, col_del = st.columns(2)
                with col_load:
                    if st.button("📂 Load", key=f"load_{j['job_id']}"):
                        st.session_state.active_job_id = j["job_id"]
                        st.session_state.active_job_title = j.get("role_title") or "Selected Job"
                        st.session_state.candidates = repo.get_candidates(j["job_id"])
                        st.success(f"Loaded {len(st.session_state.candidates)} candidates! Check the **Candidate Talent Pool** tab.")
                with col_del:
                    if st.button("🗑️", key=f"del_{j['job_id']}"):
                        repo.delete_job(j["job_id"])
                        st.warning("Deleted campaign.")
                        st.rerun()
            st.markdown("---")
