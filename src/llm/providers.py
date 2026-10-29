import json
import time
import requests
import urllib.request
from typing import Optional, List, Dict, Any
from ..core.config import settings


class LLMClient:
    def __init__(self):
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.groq_api_key = settings.GROQ_API_KEY
        self.groq_models = [settings.GROQ_PRIMARY_MODEL, settings.GROQ_FALLBACK_MODEL, "openai/gpt-oss-20b"]
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.ollama_models = [settings.OLLAMA_MODEL, "gemma3:4b", "mistral:latest", "phi3:mini"]

    def complete(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1, max_tokens: int = 1500) -> Optional[str]:
        """
        Unified completion across multiple tiers:
        1. Google Gemini API (fastest, high context, ideal for Render)
        2. Groq Cloud API
        3. Local Ollama (if running on desktop/workstation)
        """
        # 1. Try Gemini API
        if self.gemini_api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
                payload: Dict[str, Any] = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens
                    }
                }
                if system_prompt:
                    payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

                resp = requests.post(url, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        if text:
                            return text
            except Exception as e:
                print(f"[LLMClient] Gemini error: {e}")

        # 2. Try Groq Cloud API
        if self.groq_api_key:
            groq_messages = []
            if system_prompt:
                groq_messages.append({"role": "system", "content": system_prompt})
            groq_messages.append({"role": "user", "content": prompt})

            for model in self.groq_models:
                try:
                    headers = {
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model,
                        "messages": groq_messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=15
                    )
                    if resp.status_code == 200:
                        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if content:
                            return content
                    else:
                        print(f"[Groq Error] status {resp.status_code}: {resp.text[:150]}")
                except Exception as e:
                    print(f"[Groq Exception] {e}")
                    continue

        # 3. Try Local Ollama
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        for model in self.ollama_models:
            try:
                data = {
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": temperature}
                }
                req = urllib.request.Request(
                    self.ollama_url,
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                # Short timeout for local ollama so it doesn't hang if offline
                with urllib.request.urlopen(req, timeout=3) as response:
                    res = json.loads(response.read().decode("utf-8"))
                    text = res.get("response", "").strip()
                    if text:
                        return text
            except Exception:
                continue

        return None


llm_client = LLMClient()
