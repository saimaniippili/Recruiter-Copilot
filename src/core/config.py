import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    
    # LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_PRIMARY_MODEL: str = os.getenv("GROQ_MODEL", os.getenv("GROQ_PRIMARY_MODEL", "openai/gpt-oss-120b"))
    GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "qwen/qwen3.8-27b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate"))
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    
    # Sourcing Tokens
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    
    # Search Provider Settings
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_KEY", os.getenv("SERPAPI_API_KEY", ""))
    EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")
    
    # Storage & Cache
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "recruiter_copilot.db"))
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "48"))
    
    # Execution & Sourcing Budgets
    SEARCH_TIMEOUT_SECONDS: int = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "10"))
    MAX_SEARCH_QUERIES_PER_JOB: int = int(os.getenv("MAX_SEARCH_QUERIES_PER_JOB", "3"))
    MAX_RESULTS_PER_QUERY: int = int(os.getenv("MAX_RESULTS_PER_QUERY", "10"))
    MAX_CANDIDATES_EVALUATED: int = int(os.getenv("MAX_CANDIDATES_EVALUATED", "15"))
    
    # Scoring Weights (Must sum to 1.0)
    WEIGHT_MANDATORY: float = float(os.getenv("WEIGHT_MANDATORY", "0.40"))
    WEIGHT_TECHNICAL_SKILLS: float = float(os.getenv("WEIGHT_TECHNICAL_SKILLS", "0.25"))
    WEIGHT_ROLE_ALIGNMENT: float = float(os.getenv("WEIGHT_ROLE_ALIGNMENT", "0.15"))
    WEIGHT_EXPERIENCE: float = float(os.getenv("WEIGHT_EXPERIENCE", "0.10"))
    WEIGHT_PREFERRED: float = float(os.getenv("WEIGHT_PREFERRED", "0.10"))

    # Exports
    EXPORTS_DIR: Path = BASE_DIR / "exports_data"

    def validate(self):
        errors = []
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_TOKEN is missing.")
        total_weight = (
            self.WEIGHT_MANDATORY +
            self.WEIGHT_TECHNICAL_SKILLS +
            self.WEIGHT_ROLE_ALIGNMENT +
            self.WEIGHT_EXPERIENCE +
            self.WEIGHT_PREFERRED
        )
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"Scoring weights must sum to 1.0 (current sum: {total_weight:.2f})")
        return errors


settings = Settings()
settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
