from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProfileIn(BaseModel):
    headline: str | None = None
    summary: str | None = None
    skills: list[str] = []
    schools: list[str] = []
    target_roles: list[str] = []


class ProfileOut(ProfileIn):
    id: UUID
    user_id: UUID

    model_config = {"from_attributes": True}


class StartReferralIn(BaseModel):
    job_id: UUID


class CandidateIn(BaseModel):
    name: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    profile_url: str | None = None
    source: str = "linkedin"


class CandidateBatchIn(BaseModel):
    candidates: list[CandidateIn]


class CandidateOut(CandidateIn):
    id: UUID
    user_id: UUID
    campaign_id: UUID
    score: float
    reasons: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: UUID
    user_id: UUID
    campaign_id: UUID
    candidate_id: UUID | None
    channel: str
    message_type: str
    body: str
    status: str
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FollowupOut(BaseModel):
    id: UUID
    user_id: UUID
    campaign_id: UUID
    candidate_id: UUID
    message_id: UUID | None
    sequence_number: int
    due_at: datetime
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    id: UUID
    user_id: UUID
    campaign_id: UUID
    message_id: UUID | None
    event_type: str
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignOut(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    company_name: str
    job_title: str
    status: str
    job_context: dict
    created_at: datetime
    updated_at: datetime
    candidates: list[CandidateOut] = []
    messages: list[MessageOut] = []
    followups: list[FollowupOut] = []
    events: list[EventOut] = []

    model_config = {"from_attributes": True}


class OutreachPlanIn(BaseModel):
    limit: int = Field(default=10, ge=1, le=20)
    message_type: str = "referral_request"


class SendTaskOut(BaseModel):
    candidate: CandidateOut
    message: MessageOut


class GenerateMessageIn(BaseModel):
    campaign_id: UUID
    candidate_id: UUID
    message_type: str = "referral_request"


class SendStatusIn(BaseModel):
    message_id: UUID
    status: str
    details: dict = {}


class ExtensionEventIn(BaseModel):
    status: str
    version: str | None = None
    details: dict = {}


class ExtensionSessionOut(BaseModel):
    status: str
    version: str | None = None
    last_seen_at: datetime | None = None
    daily_send_limit: int
    sent_today: int
    remaining: int


class ReferralListOut(BaseModel):
    campaigns: list[CampaignOut]
