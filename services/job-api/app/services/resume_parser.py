import re
from io import BytesIO

from openai import AsyncOpenAI
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Resume
from app.services.embedding_service import EmbeddingService


class ResumeParserService:
    SKILL_PATTERNS = [
        r"\b(python|javascript|typescript|react|node\.?js|fastapi|postgresql|aws|docker|kubernetes|java|go|rust|c\+\+|sql|machine learning|ai|llm)\b",
    ]

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    async def parse_and_store(self, user_id, filename: str, content: bytes) -> Resume:
        raw_text = self._extract_text(content, filename)
        parsed_data = await self._parse_structured(raw_text)
        embedding = await self.embedding_service.embed_text(raw_text[:8000])

        resume = Resume(
            user_id=user_id,
            filename=filename,
            raw_text=raw_text,
            parsed_data=parsed_data,
            embedding=embedding,
        )
        self.db.add(resume)
        await self.db.commit()
        await self.db.refresh(resume)
        return resume

    def _extract_text(self, content: bytes, filename: str) -> str:
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        return content.decode("utf-8", errors="ignore")

    async def _parse_structured(self, text: str) -> dict:
        if settings.openai_api_key:
            return await self._parse_with_openai(text)
        return self._parse_heuristic(text)

    def _parse_heuristic(self, text: str) -> dict:
        skills = set()
        for pattern in self.SKILL_PATTERNS:
            skills.update(re.findall(pattern, text, re.IGNORECASE))

        companies = re.findall(
            r"(?:at|@)\s+([A-Z][A-Za-z0-9&\s]+(?:Inc\.?|LLC|Corp\.?|Ltd\.?)?)",
            text,
        )

        return {
            "skills": sorted(set(s.lower() for s in skills)),
            "experience": [],
            "education": [],
            "companies": list(set(companies))[:10],
            "projects": [],
        }

    async def _parse_with_openai(self, text: str) -> dict:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract resume data as JSON with keys: skills (list), experience (list of "
                        "{title, company, duration, description}), education (list), companies (list), "
                        "projects (list). Return only valid JSON."
                    ),
                },
                {"role": "user", "content": text[:12000]},
            ],
            response_format={"type": "json_object"},
        )
        import json

        return json.loads(response.choices[0].message.content or "{}")
