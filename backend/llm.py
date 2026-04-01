import os
import httpx
from dotenv import load_dotenv, find_dotenv

load_dotenv()

found = find_dotenv()
print(f"[ENV] Found .env at: {found}")
load_dotenv(found)
os.environ["LLM_MODEL"] = "llama-3.1-8b-instant"


LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")


LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()

async def chat_completion(messages, temperature: float = 0.2, max_tokens: int = 512) -> str:
    """
    Calls an OpenAI-compatible /v1/chat/completions endpoint (e.g., llama.cpp or vLLM).
    """
    url = f"{LLM_API_BASE}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        
        if r.status_code >= 400:
            print("Groq error:", r.text)
            r.raise_for_status()
        data = r.json()
        # OpenAI-like response shape
        return data["choices"][0]["message"]["content"]
