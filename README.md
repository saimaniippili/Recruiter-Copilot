# Recruiter Copilot — AI Talent Intelligence Platform

Recruiter Copilot is a full-stack, AI-driven talent sourcing and intelligence platform designed to replace manual X-Ray searches and clunky spreadsheets with a fast, evidence-first recruiter workspace. 

Recruiters paste or upload raw, unstructured job descriptions, verify extracted sourcing rules, discover candidate profiles across search indexes and GitHub, and generate personalized cold outreach drafts with a single click.

---

## Open Source Projects & GitHub Repositories Used

The sourcing and intelligence engine builds upon and adapts leading open-source projects across scraping, technical candidate evaluation, search aggregation, and semantic parsing:

| GitHub Repository | Focus / Category | Role in Recruiter Copilot |
| :--- | :--- | :--- |
| [**PyGithub/PyGithub**](https://github.com/PyGithub/PyGithub) | Technical Talent Discovery | Integrated directly (`src/sourcing/github_sourcing.py`) to query the GitHub Users and Search API. Identifies active open-source contributors filtered by primary programming languages, repository stars, commit activity, and public profile emails. |
| [**deedy5/duckduckgo_search** / `ddgs`](https://github.com/deedy5/duckduckgo_search) | Resilient Meta-Search Engine | Integrated directly (`src/sourcing/ddg.py`) to provide free, anti-bot resilient LinkedIn and web search without requiring paid API tokens or hitting strict rate limits. |
| [**cullenwatson/JobSpy**](https://github.com/cullenwatson/JobSpy) | Multi-Platform Sourcing | Architectural blueprint for scraping and structuring multi-source professional profiles and job board metadata (LinkedIn, Indeed, Glassdoor) with anti-detection headers. |
| [**TomQuirk/linkedin-api**](https://github.com/TomQuirk/linkedin-api) | LinkedIn Profile Modeling | Sourcing schema reference for modeling candidate profiles, work histories, exact technical skills, and education attributes from public professional profiles. |
| [**srbhr/Resume-Matcher**](https://github.com/srbhr/Resume-Matcher) | Semantic Matching & ATS Scoring | Core matching concept used in `src/scoring/evaluator.py`: deterministic, evidence-based rubric scoring that matches candidate experience against mandatory and preferred requirements rather than naive keyword counting. |
| [**unclecode/crawl4ai**](https://github.com/unclecode/crawl4ai) | LLM-Ready Web Scraping | Scraping and extraction model for turning messy web search snippets and developer portfolio pages into clean markdown/JSON for LLM evaluation. |
| [**searxng/searxng**](https://github.com/searxng/searxng) | Meta Search Aggregation | Inspired our multi-provider fallback architecture: queries are automatically routed across SerpApi Google X-Ray, DuckDuckGo, and Bing to guarantee candidate discoveries even when a single provider experiences rate limits. |

---

## Key Features

- **ChatGPT-Style Minimalist Workspace:** Clean, distraction-free interface built with dark mode design system tokens (`#0B0F19`), responsive layouts, and zero visual clutter.
- **2-Box Job Intake Canvas:**
  - **Box 1 (Left):** Paste raw job descriptions, drag-and-drop `.txt` or `.md` files, or load 1-click presets (*SAP HANA*, *Embedded C++*, *Cloud Platform Architect*).
  - **Box 2 (Right):** Verified sourcing criteria with editable Target Title, Locations, Experience Range, and interactive tag chips for mandatory and preferred skills.
- **Multi-Source Sourcing Pipeline:**
  - Inverted Boolean X-Ray queries (`"Must Have 1" "Must Have 2" site:linkedin.com/in`) optimized for search engine precision.
  - Live GitHub technical candidate sourcing by repository stars, commits, and languages.
  - Multi-tier fallback (SerpApi Google -> DuckDuckGo -> Bing).
- **Deterministic Match Scoring:**
  - Explainable scoring algorithm (Mandatory Requirements: 40%, Technical Skills: 25%, Role Alignment: 15%, Experience: 10%, Evidence: 10%).
  - Semantic eligibility classifications: `MEETS REQUIREMENTS` vs. `REQUIRES HUMAN REVIEW`.
- **Candidate Evidence & Outreach Drawer:**
  - Click any candidate to view their verified match evidence.
  - Generates personalized cold outreach drafts citing candidate projects and skills with a 1-click **"Copy Outreach"** button.
- **Search History & CSV Export:**
  - Instant access to recent sourcing searches in the sidebar.
  - One-click ATS-compatible CSV export for Greenhouse, Lever, Ashby, etc.

---

## Tech Stack

- **Backend:** Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, SQLite
- **Frontend:** Vanilla JavaScript, [Tailwind CSS](https://tailwindcss.com/), [Lucide Icons](https://lucide.dev/), Inter font
- **AI & LLM Providers:** Google Gemini API (`gemini-2.5-flash`), Groq Cloud API (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`), with local Ollama fallback
- **Sourcing Engines:** `PyGithub`, `duckduckgo_search` / `ddgs`, SerpApi Google X-Ray

---

## Project Structure

```
Recruiter Copilot/
├── run.py                       # Application entrypoint (starts FastAPI web server)
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render Infrastructure-as-Code Blueprint
├── Dockerfile                   # Container specification for cloud deployment
├── src/
│   ├── web/                     # FastAPI backend & web assets
│   │   ├── server.py            # REST API endpoints & dashboard routes
│   │   └── static/              # Clean single-page frontend (HTML, CSS, JS)
│   │       ├── index.html       # 2-box ChatGPT-style workspace
│   │       ├── styles.css       # Enterprise dark tokens (#0B0F19)
│   │       └── app.js           # Interactive state, sourcing, & outreach client
│   ├── sourcing/                # Sourcing adapters (GitHub, SerpApi, DDG, Bing)
│   │   ├── github_sourcing.py   # GitHub Users & Repos API integration
│   │   ├── serpapi.py           # Google X-Ray search provider
│   │   ├── ddg.py               # DuckDuckGo fallback provider
│   │   └── query_builder.py     # Boolean search query generator
│   ├── scoring/                 # Deterministic scoring & evidence engine
│   │   └── evaluator.py         # Rubric-based scoring & qualification logic
│   ├── llm/                     # Multi-tier LLM integrations
│   │   ├── providers.py         # Gemini, Groq, & Ollama completion routing
│   │   ├── extraction.py        # Structured criteria extraction from raw JDs
│   │   └── outreach.py          # Personalized message generation
│   ├── storage/                 # Database & persistence
│   │   └── db.py                # SQLite repository & schema migrations
│   └── jobs/                    # Orchestrator
│       └── orchestrator.py      # Sourcing pipeline coordination
└── tests/                       # Unit & integration test suites
```

---

## Local Setup & Development

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Clone & Install
```bash
git clone <your-repo-url>
cd "Recruiter Copilot"
pip install -r requirements.txt
```

### 3. Configure Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
# AI Engine (Choose at least one)
GROQ_API_KEY=your_groq_api_key
# or GEMINI_API_KEY=your_gemini_api_key
# or OLLAMA_URL=http://localhost:11434/api/generate

# Search Providers (Optional: DDG fallback works without keys)
SERPAPI_KEY=your_serpapi_key

# GitHub Technical Sourcing (Optional: Increases GitHub rate limits)
GITHUB_TOKEN=your_github_token
```

### 4. Run the Application
```bash
python run.py
```
Open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

---

## Deploying to Render

### Option 1: Automatic Blueprint (`render.yaml`)
1. Push this repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** -> **Blueprint**.
3. Connect your repository. Render will automatically read `render.yaml` and configure the web service with:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python run.py`
4. Add your environment variables (`GROQ_API_KEY` or `GEMINI_API_KEY`, etc.) in the Render Environment tab.

### Option 2: Docker Container
The included `Dockerfile` builds a production container running `uvicorn src.web.server:app --host 0.0.0.0 --port $PORT`.

---

## Running Tests
Run the offline test suite:
```bash
python -m pytest tests/
```
All 30 unit and integration tests validate requirement extraction, query generation, normalization, and scoring offline without external network dependencies.
