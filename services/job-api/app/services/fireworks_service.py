import json

import httpx

from app.core.config import settings

FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"


class FireworksService:
    def __init__(self):
        self.api_key = settings.fireworks_api_key
        self.embedding_model = settings.fireworks_embedding_model
        self.chat_model = settings.fireworks_chat_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float] | None:
        if not self.enabled or not text.strip():
            return None

        payload = {
            "model": self.embedding_model,
            "input": text[:8000],
            "dimensions": settings.embedding_dimensions,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{FIREWORKS_BASE}/embeddings",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data["data"][0]["embedding"]

    async def generate_json(self, system: str, user: str) -> dict:
        if not self.enabled:
            return {}

        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user[:12000]},
            ],
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{FIREWORKS_BASE}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"]
        return json.loads(text)


fireworks_service = FireworksService()
