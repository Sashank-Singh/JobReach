from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models import Application, Company, JobFilter, NotificationLog, Resume, SavedJob, User
from app.schemas.job import (
    ApplicationResponse,
    JobDetail,
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

router = APIRouter(prefix="/api/v1", tags=["jobs"])


class ApplyBody(BaseModel):
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


@router.get("/health")
async def health():
    return {"status": "ok", "service": "job-api", "owner": "dev1"}


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
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


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


@router.get("/me/saved-jobs")
async def my_saved_jobs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SavedJob).where(SavedJob.user_id == user.id).order_by(SavedJob.created_at.desc())
    )
    return [{"id": s.id, "job_id": s.job_id, "created_at": s.created_at} for s in result.scalars()]


@router.get("/me/applications")
async def my_applications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application).where(Application.user_id == user.id).order_by(Application.applied_at.desc())
    )
    return [
        {"id": a.id, "job_id": a.job_id, "status": a.status, "applied_at": a.applied_at}
        for a in result.scalars()
    ]


@router.get("/me/resume", response_model=ResumeResponse | None)
async def my_latest_resume(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


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


@router.post("/resume/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    resume = await ResumeParserService(db).parse_and_store(user.id, file.filename or "resume.pdf", content)
    return resume


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
