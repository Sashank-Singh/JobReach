from openai import AsyncOpenAI

from app.core.config import settings


class EmbeddingService:
    async def embed_text(self, text: str) -> list[float] | None:
        if not settings.openai_api_key or not text.strip():
            return self._fallback_embedding(text)

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=text[:8000],
        )
        return response.data[0].embedding

    def _fallback_embedding(self, text: str) -> list[float]:
        """Deterministic hash-based embedding for local dev without OpenAI."""
        dim = settings.embedding_dimensions
        vec = [0.0] * dim
        tokens = text.lower().split()
        for i, token in enumerate(tokens[:500]):
            idx = hash(token) % dim
            vec[idx] += 1.0 / (i + 1)
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]
