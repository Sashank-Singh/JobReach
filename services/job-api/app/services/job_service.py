from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Application, Company, Job, JobEmbedding, JobSalary, JobSkill, Resume, SavedJob
from app.schemas.job import JobDetail, JobListItem, JobListResponse, JobSearchParams
from app.utils.html import decode_job_html, html_to_plain


def _job_to_list_item(job: Job, match_score: float | None = None) -> JobListItem:
    return JobListItem(
        id=job.id,
        title=job.title,
        company=job.company,
        department=job.department,
        experience_level=job.experience_level,
        remote_type=job.remote_type,
        visa_sponsorship=job.visa_sponsorship,
        locations=job.locations,
        salary=job.salary,
        skills=[s.skill for s in job.skills],
        posted_at=job.posted_at,
        apply_url=job.apply_url,
        source=job.source,
        match_score=match_score,
    )


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_jobs(self, params: JobSearchParams) -> JobListResponse:
        query = (
            select(Job)
            .join(Company)
            .where(Job.is_active.is_(True))
            .where(Job.apply_url.isnot(None))
            .where(Job.apply_url != "")
            .options(
                selectinload(Job.company),
                selectinload(Job.locations),
                selectinload(Job.skills),
                selectinload(Job.salary),
            )
        )

        keyword = (params.keyword or "").strip()
        terms = [t for t in keyword.lower().split() if len(t) >= 2]

        if terms:
            for term in terms:
                pattern = f"%{term}%"
                query = query.where(
                    or_(
                        func.lower(Job.title).like(pattern),
                        func.lower(func.coalesce(Job.description_plain, "")).like(pattern),
                        func.lower(Company.name).like(pattern),
                        func.lower(func.coalesce(Job.department, "")).like(pattern),
                    )
                )

        if params.company:
            query = query.where(
                or_(
                    func.lower(Company.slug) == params.company.lower(),
                    func.lower(Company.name).like(f"%{params.company.lower()}%"),
                )
            )

        if params.experience:
            query = query.where(Job.experience_level == params.experience)

        if params.remote:
            query = query.where(Job.remote_type == params.remote)

        if params.visa is not None:
            query = query.where(Job.visa_sponsorship == params.visa)

        if params.posted_days:
            cutoff = func.now() - func.make_interval(0, 0, 0, params.posted_days)
            query = query.where(Job.posted_at >= cutoff)

        if params.location:
            from app.models import JobLocation
            from app.utils.location import expand_location_search

            terms = expand_location_search(params.location)
            if not terms:
                terms = [params.location.lower()]

            loc_conditions = []
            for term in terms:
                pattern = f"%{term}%"
                loc_conditions.append(
                    or_(
                        func.lower(func.coalesce(JobLocation.city, "")).like(pattern),
                        func.lower(func.coalesce(JobLocation.state, "")).like(pattern),
                        func.lower(func.coalesce(JobLocation.country, "")).like(pattern),
                    )
                )

            location_subq = (
                select(JobLocation.job_id)
                .where(or_(*loc_conditions))
                .distinct()
            )
            query = query.where(Job.id.in_(location_subq))

        if params.salary_min or params.salary_max:
            query = query.join(JobSalary, isouter=True)
            if params.salary_min:
                query = query.where(
                    or_(JobSalary.max_salary >= params.salary_min, JobSalary.max_salary.is_(None))
                )
            if params.salary_max:
                query = query.where(
                    or_(JobSalary.min_salary <= params.salary_max, JobSalary.min_salary.is_(None))
                )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        offset = (params.page - 1) * params.page_size

        if keyword:
            title_pattern = f"%{keyword.lower()}%"
            query = query.order_by(
                case((func.lower(Job.title).like(title_pattern), 0), else_=1),
                Job.posted_at.desc().nullslast(),
            )
        else:
            query = query.order_by(Job.posted_at.desc().nullslast())

        query = query.offset(offset).limit(params.page_size)

        result = await self.db.execute(query)
        jobs = result.scalars().unique().all()

        match_scores: dict[UUID, float] = {}
        if params.resume_id:
            match_scores = await self._compute_match_scores(params.resume_id, [j.id for j in jobs])

        items = [_job_to_list_item(j, match_scores.get(j.id)) for j in jobs]

        if match_scores:
            items.sort(key=lambda x: x.match_score or 0, reverse=True)

        return JobListResponse(
            jobs=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            has_more=offset + len(items) < total,
        )

    async def get_job(self, job_id: UUID) -> JobDetail | None:
        result = await self.db.execute(
            select(Job)
            .where(Job.id == job_id)
            .options(
                selectinload(Job.company),
                selectinload(Job.locations),
                selectinload(Job.skills),
                selectinload(Job.salary),
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            return None
        item = _job_to_list_item(job)
        description = decode_job_html(job.description) if job.description else None
        return JobDetail(**item.model_dump(), description=description, is_active=job.is_active)

    async def save_job(self, user_id: UUID, job_id: UUID) -> SavedJob:
        existing = await self.db.execute(
            select(SavedJob).where(and_(SavedJob.user_id == user_id, SavedJob.job_id == job_id))
        )
        saved = existing.scalar_one_or_none()
        if saved:
            return saved

        saved = SavedJob(user_id=user_id, job_id=job_id)
        self.db.add(saved)
        await self.db.commit()
        await self.db.refresh(saved)
        return saved

    async def apply_to_job(self, user_id: UUID, job_id: UUID, notes: str | None = None) -> Application:
        app = Application(user_id=user_id, job_id=job_id, notes=notes)
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def _compute_match_scores(self, resume_id: UUID, job_ids: list[UUID]) -> dict[UUID, float]:
        resume_result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        resume = resume_result.scalar_one_or_none()
        if not resume or not resume.embedding:
            return {}

        scores: dict[UUID, float] = {}
        for job_id in job_ids:
            emb_result = await self.db.execute(
                select(JobEmbedding).where(JobEmbedding.job_id == job_id)
            )
            job_emb = emb_result.scalar_one_or_none()
            if job_emb and job_emb.embedding:
                scores[job_id] = self._cosine_similarity(resume.embedding, job_emb.embedding)

        return scores

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return round((dot / (norm_a * norm_b)) * 100, 1)


def normalize_job_description(description: str | None) -> tuple[str | None, str | None]:
    """Returns (decoded_html, plain_text) for storage."""
    if not description:
        return None, None
    decoded = decode_job_html(description)
    plain = html_to_plain(decoded)
    return decoded, plain
