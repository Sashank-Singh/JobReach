import re

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.collectors import get_collector
from app.core.config import settings
from app.data.seed_companies import SEED_COMPANIES, enrich_company_stats
from app.models import Company, Job, JobEmbedding, JobLocation, JobSalary, JobSkill
from app.services.embedding_service import EmbeddingService
from app.services.job_service import normalize_job_description
from app.utils.experience import infer_experience_level
from app.utils.remote import infer_remote_type

sync_engine = create_engine(settings.database_url_sync)


class JobIngestionService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def run_all(self) -> dict:
        stats = {"companies": 0, "jobs_created": 0, "jobs_updated": 0, "errors": []}
        with Session(sync_engine) as session:
            self._ensure_seed_companies(session)
            companies = session.execute(
                select(Company).where(Company.ats_board_token.isnot(None))
            ).scalars().all()

            for company in companies:
                stats["companies"] += 1
                try:
                    created, updated = self._ingest_company(session, company)
                    stats["jobs_created"] += created
                    stats["jobs_updated"] += updated
                    enrich_company_stats(session, company)
                except Exception as e:
                    stats["errors"].append(f"{company.slug}: {e}")

            session.commit()
        return stats

    def _ensure_seed_companies(self, session: Session) -> None:
        for seed in SEED_COMPANIES:
            existing = session.execute(select(Company).where(Company.slug == seed["slug"])).scalar_one_or_none()
            if not existing:
                session.add(Company(**seed))
            else:
                for key, val in seed.items():
                    if val is not None and getattr(existing, key, None) in (None, ""):
                        setattr(existing, key, val)
        session.flush()

    def _ingest_company(self, session: Session, company: Company) -> tuple[int, int]:
        collector = get_collector(company.ats_type or "")
        if not collector or not company.ats_board_token:
            return 0, 0

        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        raw_jobs = loop.run_until_complete(collector.fetch_jobs(company.ats_board_token))
        created, updated = 0, 0

        for raw in raw_jobs:
            existing = session.execute(
                select(Job).where(Job.company_id == company.id, Job.external_id == raw.external_id)
            ).scalar_one_or_none()

            if existing:
                self._update_job(existing, raw)
                updated += 1
                job = existing
            else:
                job = self._create_job(session, company, raw, collector.source)
                created += 1

            loop.run_until_complete(self._ensure_embedding(session, job))

        return created, updated

    def _create_job(self, session: Session, company: Company, raw, source: str) -> Job:
        desc_html, desc_plain = normalize_job_description(raw.description)
        loc_name = raw.locations[0].get("city") if raw.locations else None
        experience = raw.experience_level or infer_experience_level(raw.title)
        remote = raw.remote_type or infer_remote_type(loc_name, raw.title)
        job = Job(
            company_id=company.id,
            external_id=raw.external_id,
            title=raw.title,
            description=desc_html,
            description_plain=desc_plain,
            department=raw.department,
            experience_level=experience,
            remote_type=remote,
            visa_sponsorship=raw.visa_sponsorship or company.visa_sponsorship,
            apply_url=raw.apply_url,
            posted_at=raw.posted_at,
            source=source,
        )
        session.add(job)
        session.flush()
        self._sync_relations(session, job, raw)
        return job

    def _update_job(self, job: Job, raw) -> None:
        desc_html, desc_plain = normalize_job_description(raw.description)
        loc_name = raw.locations[0].get("city") if raw.locations else None
        job.title = raw.title
        job.description = desc_html
        job.description_plain = desc_plain
        job.department = raw.department
        job.experience_level = raw.experience_level or infer_experience_level(raw.title)
        job.remote_type = raw.remote_type or infer_remote_type(loc_name, raw.title)
        job.apply_url = raw.apply_url
        job.posted_at = raw.posted_at
        job.is_active = True

    def _sync_relations(self, session: Session, job: Job, raw) -> None:
        for loc in raw.locations:
            session.add(
                JobLocation(
                    job_id=job.id,
                    **{k: v for k, v in loc.items() if k in ("city", "state", "country", "is_remote")},
                )
            )
        for skill in raw.skills:
            session.add(JobSkill(job_id=job.id, skill=skill))
        if raw.salary:
            session.add(JobSalary(job_id=job.id, **raw.salary))
        for skill in self._extract_skills(job.description_plain or raw.description or ""):
            session.add(JobSkill(job_id=job.id, skill=skill))

    async def _ensure_embedding(self, session: Session, job: Job) -> None:
        existing = session.execute(select(JobEmbedding).where(JobEmbedding.job_id == job.id)).scalar_one_or_none()
        if existing:
            return
        text = f"{job.title}\n{job.description_plain or job.description or ''}"[:8000]
        embedding = await self.embedding_service.embed_text(text)
        if embedding:
            session.add(JobEmbedding(job_id=job.id, embedding=embedding, model=settings.embedding_model))

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        pattern = r"\b(Python|JavaScript|TypeScript|React|Node\.js|Go|Rust|Java|AWS|Docker|Kubernetes|SQL|PostgreSQL|Machine Learning|AI|LLM)\b"
        return list(set(re.findall(pattern, text, re.IGNORECASE)))[:15]
