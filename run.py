import os
import sys
import uvicorn
from pathlib import Path

# Fix Windows console UTF-8 encoding for emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def main():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 60)
    print("RECRUITER COPILOT - ENTERPRISE TALENT INTELLIGENCE PLATFORM")
    print(f"Running web application at: http://localhost:{port}")
    print("=" * 60)
    
    uvicorn.run("src.web.server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
