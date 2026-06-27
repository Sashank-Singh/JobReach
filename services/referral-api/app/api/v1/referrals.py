from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.referral import (
    CandidateBatchIn,
    CandidateOut,
    CampaignOut,
    ExtensionEventIn,
    ExtensionSessionOut,
    GenerateMessageIn,
    MessageOut,
    OutreachPlanIn,
    ProfileIn,
    ProfileOut,
    ReferralListOut,
    SendStatusIn,
    SendTaskOut,
    StartReferralIn,
)
from app.services.referral_service import ReferralService

router = APIRouter(tags=["referrals"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "referral-api", "owner": "dev2"}


@router.post("/referrals/start", response_model=CampaignOut)
async def start_referral(
    body: StartReferralIn,
    authorization: str | None = Header(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    try:
      return await ReferralService(db).start_campaign(user.id, body.job_id, token)
    except Exception as exc:
      raise HTTPException(400, detail=str(exc))


@router.get("/referrals", response_model=ReferralListOut)
async def list_referrals(user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    campaigns = await ReferralService(db).list_campaigns(user.id)
    return ReferralListOut(campaigns=campaigns)


@router.get("/referrals/{campaign_id}", response_model=CampaignOut)
async def get_referral(campaign_id: UUID, user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        return await ReferralService(db).get_campaign(user.id, campaign_id)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))


@router.post("/referrals/{campaign_id}/candidates", response_model=list[CandidateOut])
async def add_candidates(
    campaign_id: UUID,
    body: CandidateBatchIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ReferralService(db).add_candidates(user.id, campaign_id, body.candidates)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))


@router.post("/referrals/{campaign_id}/outreach-plan", response_model=list[SendTaskOut])
async def create_outreach_plan(
    campaign_id: UUID,
    body: OutreachPlanIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tasks = await ReferralService(db).create_outreach_plan(user.id, campaign_id, body.limit, body.message_type)
    return [SendTaskOut(candidate=candidate, message=message) for candidate, message in tasks]


@router.post("/messages/generate", response_model=MessageOut)
async def generate_message(
    body: GenerateMessageIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tasks = await ReferralService(db).create_outreach_plan(user.id, body.campaign_id, 1, body.message_type)
    if not tasks:
        raise HTTPException(400, detail="No eligible candidate for message generation")
    return tasks[0][1]


@router.post("/messages/send-status", response_model=MessageOut)
async def send_status(
    body: SendStatusIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ReferralService(db).update_send_status(user.id, body.message_id, body.status, body.details)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))


@router.post("/followups/run", response_model=list[SendTaskOut])
async def run_followups(user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tasks = await ReferralService(db).run_due_followups(user.id)
    return [SendTaskOut(candidate=candidate, message=message) for candidate, message in tasks]


@router.get("/extension/session", response_model=ExtensionSessionOut)
async def extension_session(user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReferralService(db).get_extension_session(user.id)


@router.post("/extension/events")
async def extension_events(
    body: ExtensionEventIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ReferralService(db).record_extension_event(user.id, body.status, body.version, body.details)
    return {"ok": True}


@router.get("/profile", response_model=ProfileOut | None)
async def get_profile(user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReferralService(db).get_profile(user.id)


@router.post("/profile", response_model=ProfileOut)
async def save_profile(body: ProfileIn, user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReferralService(db).upsert_profile(user.id, body)
