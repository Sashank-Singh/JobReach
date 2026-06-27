from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Application, Company, Job, JobEmbedding, JobSalary, JobSkill, Resume, SavedJob
from app.schemas.job import JobDetail, JobListItem, JobListResponse, JobSearchParams
from app.utils.html import decode_job_html, html_to_plain
from app.utils.salary import salary_for_response


def _job_to_list_item(job: Job, match_score: int | None = None) -> JobListItem:
    return JobListItem(
        id=job.id,
        title=job.title,
        company=job.company,
        department=job.department,
        experience_level=job.experience_level,
        remote_type=job.remote_type,
        visa_sponsorship=job.visa_sponsorship
        if job.visa_sponsorship is not None
        else (job.company.visa_sponsorship if job.company else None),
        locations=job.locations,
        salary=salary_for_response(job.salary),
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
        filtered = self._apply_filters(select(Job.id, Job.posted_at).join(Company), params)
        count_query = select(func.count()).select_from(filtered.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0
        offset = (params.page - 1) * params.page_size

        if params.resume_id and total > 0:
            resume_result = await self.db.execute(
                select(Resume.embedding).where(Resume.id == params.resume_id)
            )
            resume_embedding = resume_result.scalar_one_or_none()
            if resume_embedding is not None:
                return await self._search_by_relevance(
                    params, filtered, total, offset, resume_embedding
                )

        query = self._apply_filters(
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
            ),
            params,
        )

        keyword = (params.keyword or "").strip()
        if keyword:
            ts_query = func.plainto_tsquery("english", keyword)
            query = query.order_by(
                func.ts_rank(Job.search_vector, ts_query).desc(),
                Job.posted_at.desc().nullslast(),
                Job.id.desc(),
            )
        else:
            query = query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())

        query = query.offset(offset).limit(params.page_size)
        result = await self.db.execute(query)
        jobs = result.scalars().unique().all()
        items = [_job_to_list_item(j) for j in jobs]

        return JobListResponse(
            jobs=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            has_more=offset + len(items) < total,
            sorted_by_match=False,
        )

    async def _search_by_relevance(
        self,
        params: JobSearchParams,
        filtered: Select,
        total: int,
        offset: int,
        resume_embedding: list[float],
    ) -> JobListResponse:
        """Rank filtered jobs by resume similarity using pgvector (paginated in SQL)."""
        filtered_subq = filtered.subquery()
        emb_table = JobEmbedding.__table__
        dist = emb_table.c.embedding.cosine_distance(resume_embedding)

        ranked = await self.db.execute(
            select(filtered_subq.c.id, dist.label("dist"))
            .select_from(filtered_subq)
            .join(emb_table, emb_table.c.job_id == filtered_subq.c.id)
            .order_by(dist, filtered_subq.c.posted_at.desc().nullslast())
            .offset(offset)
            .limit(params.page_size)
        )
        rows = ranked.all()
        if not rows:
            return JobListResponse(
                jobs=[],
                total=total,
                page=params.page,
                page_size=params.page_size,
                has_more=False,
                sorted_by_match=True,
            )

        page_ids = [row[0] for row in rows]
        match_scores = {
            job_id: max(0, min(100, round((1 - float(distance)) * 100)))
            for job_id, distance in rows
        }

        result = await self.db.execute(
            select(Job)
            .where(Job.id.in_(page_ids))
            .options(
                selectinload(Job.company),
                selectinload(Job.locations),
                selectinload(Job.skills),
                selectinload(Job.salary),
            )
        )
        jobs_by_id = {job.id: job for job in result.scalars().unique().all()}
        items = [
            _job_to_list_item(jobs_by_id[jid], match_scores.get(jid))
            for jid in page_ids
            if jid in jobs_by_id
        ]

        return JobListResponse(
            jobs=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            has_more=offset + len(items) < total,
            sorted_by_match=True,
        )

    def _apply_filters(self, query: Select, params: JobSearchParams) -> Select:
        query = (
            query.where(Job.is_active.is_(True))
            .where(Job.apply_url.isnot(None))
            .where(Job.apply_url != "")
        )

        keyword = (params.keyword or "").strip()
        if keyword:
            ts_query = func.plainto_tsquery("english", keyword)
            query = query.where(Job.search_vector.op("@@")(ts_query))

        if params.skill:
            skill_subq = select(JobSkill.job_id).where(func.lower(JobSkill.skill) == params.skill.lower())
            query = query.where(Job.id.in_(skill_subq))

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
            if params.visa:
                query = query.where(
                    or_(
                        Job.visa_sponsorship.is_(True),
                        and_(Job.visa_sponsorship.is_(None), Company.visa_sponsorship.is_(True)),
                    )
                )
            else:
                query = query.where(
                    or_(
                        Job.visa_sponsorship.is_(False),
                        and_(Job.visa_sponsorship.is_(None), Company.visa_sponsorship.is_(False)),
                    )
                )

        if params.posted_days:
            cutoff = func.now() - func.make_interval(0, 0, 0, params.posted_days)
            query = query.where(Job.posted_at >= cutoff)

        if params.location:
            from app.models import JobLocation
            from app.utils.location import expand_location_search

            loc_terms = expand_location_search(params.location)
            if not loc_terms:
                loc_terms = [params.location.lower()]

            loc_conditions = []
            for term in loc_terms:
                pattern = f"%{term}%"
                loc_conditions.append(
                    or_(
                        func.lower(func.coalesce(JobLocation.city, "")).like(pattern),
                        func.lower(func.coalesce(JobLocation.state, "")).like(pattern),
                        func.lower(func.coalesce(JobLocation.country, "")).like(pattern),
                    )
                )

            location_subq = select(JobLocation.job_id).where(or_(*loc_conditions)).distinct()
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

        return query

    async def get_job(self, job_id: UUID, resume_id: UUID | None = None) -> JobDetail | None:
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

        match_score = None
        if resume_id:
            scores = await self._compute_match_scores(resume_id, [job.id])
            match_score = scores.get(job.id)

        item = _job_to_list_item(job, match_score)
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

    async def _compute_match_scores(self, resume_id: UUID, job_ids: list[UUID]) -> dict[UUID, int]:
        if not job_ids:
            return {}

        resume_result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        resume = resume_result.scalar_one_or_none()
        if not resume or resume.embedding is None:
            return {}

        emb_result = await self.db.execute(
            select(JobEmbedding).where(JobEmbedding.job_id.in_(job_ids))
        )
        scores: dict[UUID, int] = {}
        for job_emb in emb_result.scalars().all():
            if job_emb.embedding is not None:
                scores[job_emb.job_id] = self._cosine_similarity(resume.embedding, job_emb.embedding)

        return scores

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> int:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0
        return round((dot / (norm_a * norm_b)) * 100)


def normalize_job_description(description: str | None) -> tuple[str | None, str | None]:
    """Returns (decoded_html, plain_text) for storage."""
    if not description:
        return None, None
    decoded = decode_job_html(description)
    plain = html_to_plain(decoded)
    return decoded, plain
