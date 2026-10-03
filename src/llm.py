import json
import urllib.request
from .config import OLLAMA_URL, OLLAMA_MODEL

def ai_parse_jd(jd_text):
    prompt = f"""
    You are an elite Technical Recruiter. You must STRICTLY and CAREFULLY analyze the following Job Description to extract the exact Role, Location, and Core Skills for candidate sourcing.
    Do NOT guess, hallucinate, or make mistakes. Extract only what is explicitly required in the text.
    
    Job Description Text:
    {jd_text[:3000]}
    
    Output EXACTLY in this format with no other text, no markdown, no intro:
    ROLE: [Extract a simplified core Job Title (MAX 3 WORDS). Do NOT include hybrid titles with slashes. Example: 'Product Owner' or 'Staff Engineer']
    LOCATION: [The specific City and Country mentioned, e.g. 'Best, Netherlands'. If absolutely none is mentioned, write 'Anywhere']
    KEYWORDS: [3 to 5 mandatory technical skills separated by spaces, e.g. 'C++ DirectX OpenGL']
    """
    data = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            text = result.get("response", "").strip()
            
            role = "Unknown"
            location = "India"
            keywords = ""
            
            for line in text.split('\n'):
                if line.upper().startswith("ROLE:"):
                    role = line.split(":", 1)[1].strip()
                elif line.upper().startswith("LOCATION:"):
                    location = line.split(":", 1)[1].strip()
                elif line.upper().startswith("KEYWORDS:"):
                    keywords = line.split(":", 1)[1].strip()
                    
            if location.lower() == "onshore":
                location = "United States OR Europe"
                
            return role, location, keywords
    except Exception as e:
        print(f"Error parsing JD locally: {e}")
        return "ERROR", "ERROR", str(e)
