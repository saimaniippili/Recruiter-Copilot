import requests
from .config import SERPAPI_KEY

def extract_name_and_role(title, snippet):
    clean_title = title.split(" | LinkedIn")[0].split(" | Professional Profile")[0].split(" - LinkedIn")[0]
    parts = clean_title.split(" - ")
    name = parts[0].strip() if len(parts) > 0 else "Unknown Candidate"
    
    role = parts[1].strip() if len(parts) > 1 else ""
    
    if not role or "Netherlands" in role or "India" in role or "United States" in role or "Region" in role or len(role.split(",")) >= 2:
        role = snippet.split("·")[-1].strip()[:80] + "..." if snippet else "See Profile for details"
        
    return name, role

def find_candidates(job_title, location, keywords, max_results=15):
    safe_title = job_title.replace("/", " ").replace("\\", " ").replace("(", " ").replace(")", " ")
    safe_location = location.replace("/", " ").replace("\\", " ").replace("(", " ").replace(")", " ")
    
    strict_keywords = " ".join([f'"{k.strip()}"' for k in keywords.replace(",", " ").split() if k.strip()])
    query = f'site:linkedin.com/in/ intitle:"{safe_title}" {safe_location} {strict_keywords}'
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": max_results
    }
    
    candidates = []
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        
        if "organic_results" not in data or len(data["organic_results"]) == 0:
            fallback_query = f'site:linkedin.com/in/ intitle:"{safe_title}" {safe_location}'
            params["q"] = fallback_query
            response = requests.get("https://serpapi.com/search", params=params)
            data = response.json()
            query = fallback_query
            
        results = data.get("organic_results", [])
        for r in results:
            title = r.get("title", "")
            link = r.get("link", "")
            snippet = r.get("snippet", "")
            
            if "/in/" in link and "/dir/" not in link:
                name, role = extract_name_and_role(title, snippet)
                candidates.append({
                    "Name": name,
                    "Headline": role,
                    "Profile": link,
                    "Snippet": snippet
                })
        return candidates, query
    except Exception as e:
        print(f"Error with SerpApi: {e}")
        return [], query
