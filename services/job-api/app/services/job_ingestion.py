import re
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.collectors import get_collector
from app.core.config import settings
from app.data.seed_companies import SEED_COMPANIES, enrich_company_stats
from app.data.skills_catalog import SKILLS_CATALOG
from app.models import Company, Job, JobEmbedding, JobLocation, JobSalary, JobSkill, SkillCatalog
from app.services.embedding_service import EmbeddingService
from app.services.job_service import normalize_job_description
from app.utils.experience import infer_experience_level
from app.utils.remote import infer_remote_type
from app.utils.careers_page import merge_description_with_careers_page
from app.utils.salary import extract_salary_from_text, salary_dict_is_valid

sync_engine = create_engine(settings.database_url_sync)

# Build efficient skill matcher from catalog
_SKILL_PATTERNS = []
for skill in SKILLS_CATALOG:
    name = skill["name"]
    _SKILL_PATTERNS.append(re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE))
    for alias in (skill.get("aliases") or []):
        _SKILL_PATTERNS.append(re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE))

# Normalize title for deduplication
_TITLE_NORM_RE = re.compile(r"\b(sr\.?|senior|jr\.?|junior|staff|principal|lead|ii|iii|iv)\b", re.IGNORECASE)


def normalize_title(title: str) -> str:
    """Normalize a job title for dedup comparison."""
    t = title.lower().strip()
    t = _TITLE_NORM_RE.sub("", t)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def extract_skills_from_text(text: str) -> list[str]:
    """Extract known skills from text using compiled catalog patterns."""
    if not text:
        return []
    found: list[str] = []
    seen = set()
    for pattern in _SKILL_PATTERNS:
        m = pattern.search(text)
        if m:
            name = m.group(0).strip()
            if name.lower() not in seen:
                seen.add(name.lower())
                found.append(name)
    return found[:20]


class JobIngestionService:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def run_all(self) -> dict:
        stats = {"companies": 0, "jobs_created": 0, "jobs_updated": 0, "errors": []}
        with Session(sync_engine) as session:
            self._ensure_seed_companies(session)
            self._seed_skill_catalog(session)
            session.commit()
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
                    session.commit()
                except Exception as e:
                    session.rollback()
                    slug = getattr(company, "slug", "unknown")
                    stats["errors"].append(f"{slug}: {e}")

            self._deduplicate_jobs(session)
            session.commit()
        return stats

    def _seed_skill_catalog(self, session: Session) -> None:
        """Seed the skill catalog table if empty."""
        existing = session.execute(select(SkillCatalog).limit(1)).scalar_one_or_none()
        if existing:
            return
        for skill in SKILLS_CATALOG:
            s = SkillCatalog(name=skill["name"], category=skill.get("category"), aliases=skill.get("aliases"))
            session.add(s)
        session.flush()

    def _ensure_seed_companies(self, session: Session) -> None:
        for seed in SEED_COMPANIES:
            existing = session.execute(select(Company).where(Company.slug == seed["slug"])).scalar_one_or_none()
            if not existing:
                session.add(Company(**seed))
            else:
                for key, val in seed.items():
                    if key == "visa_sponsorship":
                        continue
                    if val is not None and getattr(existing, key, None) in (None, ""):
                        setattr(existing, key, val)
                if "visa_sponsorship" in seed:
                    existing.visa_sponsorship = seed["visa_sponsorship"]
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
                self._update_job(session, existing, raw, company)
                updated += 1
                job = existing
            else:
                job = self._create_job(session, company, raw, collector.source)
                created += 1

            loop.run_until_complete(self._ensure_embedding(session, job))

        return created, updated

    def _create_job(self, session: Session, company: Company, raw, source: str) -> Job:
        desc_html, desc_plain = normalize_job_description(raw.description)
        desc_html, desc_plain = merge_description_with_careers_page(
            desc_html, desc_plain, raw.apply_url
        )
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
            visa_sponsorship=raw.visa_sponsorship
            if raw.visa_sponsorship is not None
            else company.visa_sponsorship,
            apply_url=raw.apply_url,
            posted_at=raw.posted_at,
            source=source,
        )
        session.add(job)
        session.flush()
        self._sync_relations(session, job, raw)
        return job

    def _update_job(self, session: Session, job: Job, raw, company: Company) -> None:
        desc_html, desc_plain = normalize_job_description(raw.description)
        desc_html, desc_plain = merge_description_with_careers_page(
            desc_html, desc_plain, raw.apply_url
        )
        loc_name = raw.locations[0].get("city") if raw.locations else None
        job.title = raw.title
        job.description = desc_html
        job.description_plain = desc_plain
        job.department = raw.department
        job.experience_level = raw.experience_level or infer_experience_level(raw.title)
        job.remote_type = raw.remote_type or infer_remote_type(loc_name, raw.title)
        job.visa_sponsorship = (
            raw.visa_sponsorship if raw.visa_sponsorship is not None else company.visa_sponsorship
        )
        job.apply_url = raw.apply_url
        job.posted_at = raw.posted_at
        job.is_active = True
        self._ensure_salary(session, job, raw, desc_plain)

    def _sync_relations(self, session: Session, job: Job, raw) -> None:
        for loc in raw.locations:
            session.add(
                JobLocation(
                    job_id=job.id,
                    city=(loc.get("city") or "")[:255] if loc.get("city") else None,
                    state=(loc.get("state") or "")[:100] if loc.get("state") else None,
                    country=(loc.get("country") or "")[:100] if loc.get("country") else None,
                    is_remote=loc.get("is_remote", False),
                )
            )
        for skill in raw.skills:
            session.add(JobSkill(job_id=job.id, skill=skill))
        self._ensure_salary(session, job, raw, job.description_plain)
        for skill in self._extract_skills(job.description_plain or raw.description or ""):
            session.add(JobSkill(job_id=job.id, skill=skill))

    def _ensure_salary(self, session: Session, job: Job, raw, desc_plain: str | None) -> None:
        salary_data = raw.salary if salary_dict_is_valid(raw.salary) else None
        if not salary_data:
            salary_data = extract_salary_from_text(desc_plain or raw.description or job.description_plain)

        # Replace implausible stored salary (e.g. "4-6 teams" misparsed as $4–$6)
        if job.salary and not salary_dict_is_valid(
            {
                "min_salary": job.salary.min_salary,
                "max_salary": job.salary.max_salary,
                "period": job.salary.period or "year",
            }
        ):
            session.delete(job.salary)
            session.flush()
            job.salary = None

        if not salary_data:
            return

        if job.salary:
            job.salary.min_salary = salary_data["min_salary"]
            job.salary.max_salary = salary_data["max_salary"]
            job.salary.currency = salary_data.get("currency", "USD")
            job.salary.period = salary_data.get("period", "year")
        else:
            session.add(JobSalary(job_id=job.id, **salary_data))

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
        return extract_skills_from_text(text)

    def _deduplicate_jobs(self, session: Session) -> None:
        """Detect and mark duplicate jobs across different ATS sources."""
        jobs = session.execute(
            select(Job).where(Job.is_active.is_(True)).where(Job.duplicate_group_id.is_(None))
        ).scalars().all()

        groups: dict[str, list[Job]] = {}
        for job in jobs:
            key = f"{job.company_id}:{job.title.strip().lower()}"
            if key not in groups:
                groups[key] = []
            groups[key].append(job)

        for key, group in groups.items():
            if len(group) < 2:
                continue
            dup_id = uuid.uuid4()
            for i, job in enumerate(group):
                job.duplicate_group_id = dup_id
                job.is_primary_duplicate = i == 0
