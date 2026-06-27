from app.core.config import settings
from app.services.fireworks_service import fireworks_service


class EmbeddingService:
    async def embed_text(self, text: str) -> list[float] | None:
        if fireworks_service.enabled and text.strip():
            embedding = await fireworks_service.embed_text(text, task_type="RETRIEVAL_DOCUMENT")
            if embedding:
                return embedding

        if not text.strip():
            return None
        return self._fallback_embedding(text)

    async def embed_query(self, text: str) -> list[float] | None:
        """Resume / search queries use RETRIEVAL_QUERY task type."""
        if fireworks_service.enabled and text.strip():
            embedding = await fireworks_service.embed_text(text, task_type="RETRIEVAL_QUERY")
            if embedding:
                return embedding
        return await self.embed_text(text)

    def _fallback_embedding(self, text: str) -> list[float]:
        """Deterministic hash-based embedding when no Fireworks API key is set."""
        dim = settings.embedding_dimensions
        vec = [0.0] * dim
        tokens = text.lower().split()
        for i, token in enumerate(tokens[:500]):
            idx = hash(token) % dim
            vec[idx] += 1.0 / (i + 1)
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]
