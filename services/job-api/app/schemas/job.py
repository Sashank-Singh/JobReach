from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CompanySummary(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class CompanyDetail(CompanySummary):
    website: str | None = None
    hiring_velocity: int | None = None
    visa_sponsorship: bool | None = None
    interview_difficulty: float | None = None
    employee_count: int | None = None
    office_locations: list | None = None
    ats_type: str | None = None


class JobLocationOut(BaseModel):
    city: str | None = None
    state: str | None = None
    country: str | None = None
    is_remote: bool = False

    model_config = {"from_attributes": True}


class JobSalaryOut(BaseModel):
    min_salary: int | None = None
    max_salary: int | None = None
    currency: str = "USD"
    period: str = "year"

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: UUID
    title: str
    company: CompanySummary
    department: str | None = None
    experience_level: str | None = None
    remote_type: str | None = None
    visa_sponsorship: bool | None = None
    locations: list[JobLocationOut] = []
    salary: JobSalaryOut | None = None
    skills: list[str] = []
    posted_at: datetime | None = None
    apply_url: str | None = None
    source: str
    match_score: float | None = None

    model_config = {"from_attributes": True}


class JobDetail(JobListItem):
    description: str | None = None
    is_active: bool = True


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class JobSearchParams(BaseModel):
    keyword: str | None = None
    company: str | None = None
    location: str | None = None
    experience: str | None = None
    remote: str | None = None
    visa: bool | None = None
    posted_days: int | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    resume_id: UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SaveJobRequest(BaseModel):
    job_id: UUID
    user_id: UUID


class ApplyJobRequest(BaseModel):
    job_id: UUID
    user_id: UUID
    notes: str | None = None


class SavedJobResponse(BaseModel):
    id: UUID
    job_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationResponse(BaseModel):
    id: UUID
    job_id: UUID
    status: str
    applied_at: datetime

    model_config = {"from_attributes": True}


class ResumeParsedData(BaseModel):
    skills: list[str] = []
    experience: list[dict] = []
    education: list[dict] = []
    companies: list[str] = []
    projects: list[dict] = []


class ResumeResponse(BaseModel):
    id: UUID
    filename: str
    parsed_data: ResumeParsedData | dict
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationItem(BaseModel):
    title: str
    body: str
    job_count: int
    sent_at: datetime

    model_config = {"from_attributes": True}


class ReferralHandoff(BaseModel):
    """Contract payload Dev 2 receives when user clicks Add Referral."""
    job_id: UUID
    user_id: UUID
