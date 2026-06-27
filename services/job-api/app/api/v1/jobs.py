from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Company, NotificationLog, User
from app.schemas.job import (
    ApplicationResponse,
    ApplyJobRequest,
    JobDetail,
    JobListResponse,
    JobSearchParams,
    NotificationItem,
    ReferralHandoff,
    ResumeResponse,
    SaveJobRequest,
    SavedJobResponse,
)
from app.services.job_service import JobService
from app.services.notification_service import NotificationService
from app.services.resume_parser import ResumeParserService

router = APIRouter(prefix="/api/v1", tags=["jobs"])

# Demo user until shared auth is wired
DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def ensure_demo_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == DEMO_USER_ID))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=DEMO_USER_ID, email="dev1@jobreach.local", name="Developer 1")
        db.add(user)
        await db.commit()
    return user


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
    db: AsyncSession = Depends(get_db),
):
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


@router.post("/jobs/save", response_model=SavedJobResponse)
async def save_job(body: SaveJobRequest, db: AsyncSession = Depends(get_db)):
    saved = await JobService(db).save_job(body.user_id, body.job_id)
    return saved


@router.post("/jobs/apply", response_model=ApplicationResponse)
async def apply_job(body: ApplyJobRequest, db: AsyncSession = Depends(get_db)):
    app = await JobService(db).apply_to_job(body.user_id, body.job_id, body.notes)
    return app


@router.post("/jobs/{job_id}/referral-handoff", response_model=ReferralHandoff)
async def referral_handoff(job_id: UUID, user_id: UUID = DEMO_USER_ID, db: AsyncSession = Depends(get_db)):
    """Dev 1 → Dev 2 contract: only job_id crosses the boundary."""
    job = await JobService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ReferralHandoff(job_id=job_id, user_id=user_id)


@router.get("/companies/{company_id}")
async def get_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.jobs))
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "website": company.website,
        "logo_url": company.logo_url,
        "hiring_velocity": company.hiring_velocity,
        "visa_sponsorship": company.visa_sponsorship,
        "interview_difficulty": company.interview_difficulty,
        "employee_count": company.employee_count,
        "office_locations": company.office_locations,
        "active_jobs": len([j for j in company.jobs if j.is_active]),
    }


@router.post("/resume/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: UUID = DEMO_USER_ID,
    db: AsyncSession = Depends(get_db),
):
    await ensure_demo_user(db)
    content = await file.read()
    resume = await ResumeParserService(db).parse_and_store(user_id, file.filename or "resume.pdf", content)
    return resume


@router.get("/notifications", response_model=list[NotificationItem])
async def get_notifications(user_id: UUID = DEMO_USER_ID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == user_id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.post("/notifications/digest")
async def trigger_digest(user_id: UUID = DEMO_USER_ID, db: AsyncSession = Depends(get_db)):
    await ensure_demo_user(db)
    notification = await NotificationService(db).generate_morning_digest(user_id)
    if not notification:
        return {"message": "No new matching jobs"}
    return notification
