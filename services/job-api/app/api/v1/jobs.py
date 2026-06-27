import statistics
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models import (
    Application,
    ApplicationStatus,
    Company,
    Job,
    JobEmbedding,
    JobFilter,
    JobLocation,
    JobSalary,
    NotificationLog,
    Resume,
    SavedJob,
    SkillCatalog,
    User,
)
from app.schemas.job import (
    ApplicationResponse,
    JobDetail,
    JobListItem,
    JobListResponse,
    JobSearchParams,
    NotificationItem,
    ReferralHandoff,
    ResumeResponse,
    SavedJobResponse,
)
from app.services.job_service import JobService
from app.services.notification_service import NotificationService
from app.services.resume_parser import ResumeParserService
from app.utils.salary import salary_for_response

router = APIRouter(prefix="/api/v1", tags=["jobs"])


class ApplyBody(BaseModel):
    notes: str | None = None


class UpdateApplicationBody(BaseModel):
    status: str | None = None
    interview_date: datetime | None = None
    pipeline_order: int | None = None
    notes: str | None = None


class FilterCreate(BaseModel):
    name: str
    filters: dict
    notify: bool = True


class FilterOut(BaseModel):
    id: UUID
    name: str
    filters: dict
    notify: bool

    model_config = {"from_attributes": True}


class SalaryEstimate(BaseModel):
    estimated: bool
    min_salary: int | None = None
    max_salary: int | None = None
    currency: str = "USD"
    period: str = "year"
    sample_size: int = 0
    message: str = ""


class AnalyticsOut(BaseModel):
    total_jobs: int
    total_companies: int
    avg_match_score: float | None = None
    skills_demand: list[dict] = []
    salary_by_experience: list[dict] = []
    remote_job_pct: float = 0
    visa_sponsorship_pct: float = 0
    top_hiring_companies: list[dict] = []
    jobs_by_source: list[dict] = []


# ---------- Health ----------


@router.get("/health")
async def health():
    return {"status": "ok", "service": "job-api", "owner": "dev1"}


# ---------- Jobs ----------


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    keyword: str | None = None,
    company: str | None = None,
    location: str | None = None,
    experience: str | None = None,
    remote: str | None = None,
    visa: bool | None = None,
    posted_days: int | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    skill: str | None = None,
    resume_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    if resume_id is None and user:
        latest = await _latest_resume_id(db, user.id)
        if latest:
            resume_id = latest

    params = JobSearchParams(
        keyword=keyword,
        company=company,
        location=location,
        experience=experience,
        remote=remote,
        visa=visa,
        posted_days=posted_days,
        salary_min=salary_min,
        salary_max=salary_max,
        resume_id=resume_id,
        page=page,
        page_size=page_size,
    )
    return await JobService(db).search_jobs(params)


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: UUID,
    resume_id: UUID | None = None,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    if resume_id is None and user:
        latest = await _latest_resume_id(db, user.id)
        if latest:
            resume_id = latest
    job = await JobService(db).get_job(job_id, resume_id=resume_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ---------- Similar jobs ----------


@router.get("/jobs/{job_id}/similar", response_model=list[JobListItem])
async def similar_jobs(
    job_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Find similar jobs using pgvector cosine distance."""
    result = await db.execute(select(JobEmbedding).where(JobEmbedding.job_id == job_id))
    source_emb = result.scalar_one_or_none()
    if not source_emb:
        return []

    emb_table = JobEmbedding.__table__
    similar = await db.execute(
        select(JobEmbedding.job_id, emb_table.c.embedding.op("<=>")(source_emb.embedding).label("dist"))
        .where(JobEmbedding.job_id != job_id)
        .order_by(text("dist"))
        .limit(limit)
    )
    similar_ids = [row[0] for row in similar.all()]

    if not similar_ids:
        return []

    jobs_result = await db.execute(
        select(Job)
        .where(Job.id.in_(similar_ids), Job.is_active.is_(True))
        .options(
            selectinload(Job.company),
            selectinload(Job.locations),
            selectinload(Job.skills),
            selectinload(Job.salary),
        )
    )
    jobs_map = {j.id: j for j in jobs_result.scalars().unique().all()}
    items = []
    for sid in similar_ids:
        if sid in jobs_map:
            items.append(_job_to_list_item(jobs_map[sid]))
    return items


# ---------- Salary estimate ----------


@router.get("/jobs/{job_id}/salary-estimate", response_model=SalaryEstimate)
async def salary_estimate(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Estimate salary for a job based on similar roles."""
    result = await db.execute(
        select(Job, Company)
        .join(Company)
        .where(Job.id == job_id)
        .options(selectinload(Job.salary))
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    job, company = row

    # If job already has salary, return it
    if job.salary and job.salary.min_salary and job.salary.max_salary:
        return SalaryEstimate(
            estimated=False,
            min_salary=job.salary.min_salary,
            max_salary=job.salary.max_salary,
            currency=job.salary.currency,
            period=job.salary.period,
            sample_size=1,
            message="Actual salary from listing",
        )

    # Find similar job salaries by title+experience
    title_words = job.title.lower().split()[:3]
    like_patterns = [f"%{w}%" for w in title_words if len(w) > 2]
    if not like_patterns:
        return SalaryEstimate(estimated=True, message="Insufficient data to estimate")

    conditions = [JobSalary.max_salary.isnot(None), JobSalary.min_salary.isnot(None)]
    title_conditions = [func.lower(Job.title).like(p) for p in like_patterns]
    conditions.append(or_(*title_conditions))
    if job.experience_level:
        conditions.append(Job.experience_level == job.experience_level)

    salary_result = await db.execute(
        select(JobSalary.min_salary, JobSalary.max_salary, JobSalary.currency, JobSalary.period)
        .join(Job, JobSalary.job_id == Job.id)
        .where(and_(*conditions))
        .where(Job.id != job_id)
        .limit(50)
    )
    rows = salary_result.all()
    if not rows:
        return SalaryEstimate(estimated=True, message="Insufficient data to estimate")

    min_sals = [r[0] for r in rows if r[0]]
    max_sals = [r[1] for r in rows if r[1]]
    if not min_sals or not max_sals:
        return SalaryEstimate(estimated=True, message="Insufficient data to estimate")

    return SalaryEstimate(
        estimated=True,
        min_salary=round(statistics.median(min_sals) / 1000) * 1000,
        max_salary=round(statistics.median(max_sals) / 1000) * 1000,
        currency=rows[0][2] or "USD",
        period=rows[0][3] or "year",
        sample_size=len(rows),
        message=f"Estimated from {len(rows)} similar roles",
    )


# ---------- Save / Apply / Referral ----------


@router.post("/jobs/{job_id}/save", response_model=SavedJobResponse)
async def save_job(job_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    saved = await JobService(db).save_job(user.id, job_id)
    return saved


@router.post("/jobs/{job_id}/apply", response_model=ApplicationResponse)
async def apply_job(
    job_id: UUID,
    body: ApplyBody = ApplyBody(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app = await JobService(db).apply_to_job(user.id, job_id, body.notes)
    return app


@router.post("/jobs/{job_id}/referral-handoff", response_model=ReferralHandoff)
async def referral_handoff(job_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    job = await JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ReferralHandoff(job_id=job_id, user_id=user.id)


# ---------- Application pipeline ----------


@router.patch("/applications/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: UUID,
    body: UpdateApplicationBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if body.status is not None:
        app.status = body.status
    if body.interview_date is not None:
        app.interview_date = body.interview_date
    if body.pipeline_order is not None:
        app.pipeline_order = body.pipeline_order
    if body.notes is not None:
        app.notes = body.notes
    app.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(app)
    return app


# ---------- User data ----------


@router.get("/me/saved-jobs")
async def my_saved_jobs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SavedJob).where(SavedJob.user_id == user.id).order_by(SavedJob.created_at.desc())
    )
    return [{"id": s.id, "job_id": s.job_id, "created_at": s.created_at} for s in result.scalars()]


@router.get("/me/applications")
async def my_applications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application)
        .where(Application.user_id == user.id)
        .options(selectinload(Application.job).selectinload(Job.company))
        .order_by(Application.pipeline_order.asc().nullslast(), Application.applied_at.desc())
    )
    apps = []
    for a in result.scalars().unique().all():
        job_data = None
        if a.job:
            job_data = {
                "id": str(a.job.id),
                "title": a.job.title,
                "company_name": a.job.company.name if a.job.company else None,
            }
        apps.append({
            "id": a.id,
            "job_id": a.job_id,
            "status": a.status,
            "applied_at": a.applied_at,
            "interview_date": a.interview_date,
            "pipeline_order": a.pipeline_order,
            "notes": a.notes,
            "job": job_data,
        })
    return apps


@router.get("/me/resume", response_model=ResumeResponse | None)
async def my_latest_resume(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


# ---------- Companies ----------


@router.get("/companies/{company_id}")
async def get_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    return await _company_payload(db, company_id=company_id)


@router.get("/companies/slug/{slug}")
async def get_company_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.slug == slug))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return await _company_payload(db, company=company)


# ---------- Resume ----------


@router.post("/resume/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    resume = await ResumeParserService(db).parse_and_store(user.id, file.filename or "resume.pdf", content)
    return resume


# ---------- Filters ----------


@router.get("/filters", response_model=list[FilterOut])
async def list_filters(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobFilter).where(JobFilter.user_id == user.id))
    return result.scalars().all()


@router.post("/filters", response_model=FilterOut)
async def create_filter(body: FilterCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    f = JobFilter(user_id=user.id, name=body.name, filters=body.filters, notify=body.notify)
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


# ---------- Notifications ----------


@router.get("/notifications", response_model=list[NotificationItem])
async def get_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == user.id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.post("/notifications/digest")
async def trigger_digest(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    notification = await NotificationService(db).generate_morning_digest(user.id)
    if not notification:
        return {"message": "No new matching jobs"}
    return notification


# ---------- Skills catalog ----------


@router.get("/skills")
async def list_skills(
    category: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(SkillCatalog).order_by(SkillCatalog.name)
    if category:
        query = query.where(SkillCatalog.category == category)
    if search:
        query = query.where(SkillCatalog.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    return [
        {"id": str(s.id), "name": s.name, "category": s.category}
        for s in result.scalars().all()
    ]


@router.get("/skills/categories")
async def list_skill_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SkillCatalog.category, func.count(SkillCatalog.id))
        .where(SkillCatalog.category.isnot(None))
        .group_by(SkillCatalog.category)
        .order_by(SkillCatalog.category)
    )
    return [{"category": row[0], "count": row[1]} for row in result.all()]


# ---------- Analytics ----------


@router.get("/analytics", response_model=AnalyticsOut)
async def get_analytics(db: AsyncSession = Depends(get_db)):
    # Total counts
    total_jobs = (await db.execute(select(func.count(Job.id)).where(Job.is_active.is_(True)))).scalar() or 0
    total_companies = (await db.execute(select(func.count(Company.id)))).scalar() or 0

    # Remote percentage
    remote_count = (await db.execute(
        select(func.count(Job.id)).where(Job.is_active.is_(True), Job.remote_type == "remote")
    )).scalar() or 0
    remote_job_pct = round(remote_count / total_jobs * 100, 1) if total_jobs > 0 else 0

    # Visa sponsorship percentage
    visa_count = (await db.execute(
        select(func.count(Job.id)).where(Job.is_active.is_(True), Job.visa_sponsorship.is_(True))
    )).scalar() or 0
    visa_sponsorship_pct = round(visa_count / total_jobs * 100, 1) if total_jobs > 0 else 0

    # Skill demand
    skill_result = await db.execute(
        text("""
            SELECT js.skill, COUNT(*) as cnt
            FROM job_skills js
            JOIN jobs j ON j.id = js.job_id
            WHERE j.is_active = true
            GROUP BY js.skill
            ORDER BY cnt DESC
            LIMIT 30
        """)
    )
    skills_demand = [{"skill": row[0], "count": row[1]} for row in skill_result.all()]

    # Salary by experience level
    salary_result = await db.execute(
        text("""
            SELECT j.experience_level,
                   ROUND(AVG(js.min_salary)) as avg_min,
                   ROUND(AVG(js.max_salary)) as avg_max,
                   COUNT(*) as cnt
            FROM job_salary js
            JOIN jobs j ON j.id = js.job_id
            WHERE j.is_active = true AND j.experience_level IS NOT NULL
            GROUP BY j.experience_level
            ORDER BY j.experience_level
        """)
    )
    salary_by_experience = [
        {"level": row[0], "avg_min": row[1], "avg_max": row[2], "count": row[3]}
        for row in salary_result.all()
    ]

    # Top hiring companies
    company_result = await db.execute(
        text("""
            SELECT c.name, c.slug, COUNT(*) as cnt
            FROM jobs j
            JOIN companies c ON c.id = j.company_id
            WHERE j.is_active = true
            GROUP BY c.name, c.slug
            ORDER BY cnt DESC
            LIMIT 10
        """)
    )
    top_hiring_companies = [
        {"name": row[0], "slug": row[1], "active_jobs": row[2]}
        for row in company_result.all()
    ]

    # Jobs by source
    source_result = await db.execute(
        text("""
            SELECT source, COUNT(*) as cnt
            FROM jobs
            WHERE is_active = true
            GROUP BY source
            ORDER BY cnt DESC
        """)
    )
    jobs_by_source = [{"source": row[0], "count": row[1]} for row in source_result.all()]

    return AnalyticsOut(
        total_jobs=total_jobs,
        total_companies=total_companies,
        skills_demand=skills_demand,
        salary_by_experience=salary_by_experience,
        remote_job_pct=remote_job_pct,
        visa_sponsorship_pct=visa_sponsorship_pct,
        top_hiring_companies=top_hiring_companies,
        jobs_by_source=jobs_by_source,
    )


# ---------- Helpers ----------


def _job_to_list_item(job: Job) -> JobListItem:
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
    )


async def _latest_resume_id(db: AsyncSession, user_id: UUID) -> UUID | None:
    result = await db.execute(
        select(Resume.id).where(Resume.user_id == user_id).order_by(Resume.created_at.desc()).limit(1)
    )
    row = result.scalar_one_or_none()
    return row


async def _company_payload(db: AsyncSession, company_id: UUID | None = None, company: Company | None = None):
    if company is None:
        result = await db.execute(
            select(Company).where(Company.id == company_id).options(selectinload(Company.jobs))
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
    else:
        result = await db.execute(select(Company).where(Company.id == company.id).options(selectinload(Company.jobs)))
        company = result.scalar_one()

    active_jobs = [j for j in company.jobs if j.is_active]
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "website": company.website,
        "logo_url": company.logo_url,
        "hiring_velocity": company.hiring_velocity or len(active_jobs),
        "visa_sponsorship": company.visa_sponsorship,
        "interview_difficulty": company.interview_difficulty,
        "employee_count": company.employee_count,
        "office_locations": company.office_locations or [],
        "active_jobs": len(active_jobs),
        "ats_type": company.ats_type,
    }
