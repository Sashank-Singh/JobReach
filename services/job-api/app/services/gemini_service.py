import json

import httpx

from app.core.config import settings

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.embedding_model = settings.gemini_embedding_model
        self.chat_model = settings.gemini_chat_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float] | None:
        if not self.enabled or not text.strip():
            return None

        url = f"{GEMINI_BASE}/models/{self.embedding_model}:embedContent"
        payload = {
            "model": f"models/{self.embedding_model}",
            "content": {"parts": [{"text": text[:8000]}]},
            "taskType": task_type,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
            data = response.json()

        embedding = data.get("embedding", {}).get("values")
        return embedding

    async def generate_json(self, system: str, user: str) -> dict:
        if not self.enabled:
            return {}

        url = f"{GEMINI_BASE}/models/{self.chat_model}:generateContent"
        prompt = f"{system}\n\n{user[:12000]}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
            data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)


gemini_service = GeminiService()
