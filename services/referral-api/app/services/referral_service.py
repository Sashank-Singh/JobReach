from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import (
    ConversationEvent,
    ExtensionSession,
    Followup,
    OutreachMessage,
    ReferralCampaign,
    ReferralCandidate,
    ReferralProfile,
)
from app.schemas.referral import CandidateIn, ProfileIn
from app.services.referral_policy import (
    DAILY_SEND_LIMIT,
    followup_due_dates,
    is_allowed_send_status,
    remaining_send_capacity,
    score_candidate,
)


class ReferralService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_campaign(self, user_id: UUID, job_id: UUID, token: str | None = None) -> ReferralCampaign:
        existing = await self.db.scalar(
            select(ReferralCampaign)
            .where(ReferralCampaign.user_id == user_id, ReferralCampaign.job_id == job_id)
            .options(
                selectinload(ReferralCampaign.candidates),
                selectinload(ReferralCampaign.messages),
                selectinload(ReferralCampaign.followups),
                selectinload(ReferralCampaign.events),
            )
        )
        if existing:
            return existing

        job = await self._fetch_job(job_id, token)
        company_name = job.get("company", {}).get("name") or "Unknown company"
        campaign = ReferralCampaign(
            user_id=user_id,
            job_id=job_id,
            company_name=company_name,
            job_title=job.get("title") or "Unknown role",
            status="created",
            job_context=job,
        )
        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)
        await self.record_event(user_id, campaign.id, "campaign_started", {"job_id": str(job_id)})
        return await self.get_campaign(user_id, campaign.id)

    async def get_campaign(self, user_id: UUID, campaign_id: UUID) -> ReferralCampaign:
        campaign = await self.db.scalar(
            select(ReferralCampaign)
            .where(ReferralCampaign.user_id == user_id, ReferralCampaign.id == campaign_id)
            .options(
                selectinload(ReferralCampaign.candidates),
                selectinload(ReferralCampaign.messages),
                selectinload(ReferralCampaign.followups),
                selectinload(ReferralCampaign.events),
            )
        )
        if not campaign:
            raise ValueError("Campaign not found")
        return campaign

    async def list_campaigns(self, user_id: UUID) -> list[ReferralCampaign]:
        result = await self.db.execute(
            select(ReferralCampaign)
            .where(ReferralCampaign.user_id == user_id)
            .order_by(ReferralCampaign.created_at.desc())
            .options(
                selectinload(ReferralCampaign.candidates),
                selectinload(ReferralCampaign.messages),
                selectinload(ReferralCampaign.followups),
                selectinload(ReferralCampaign.events),
            )
        )
        return result.scalars().all()

    async def upsert_profile(self, user_id: UUID, body: ProfileIn) -> ReferralProfile:
        profile = await self.db.scalar(select(ReferralProfile).where(ReferralProfile.user_id == user_id))
        if not profile:
            profile = ReferralProfile(user_id=user_id)
            self.db.add(profile)
        profile.headline = body.headline
        profile.summary = body.summary
        profile.skills = body.skills
        profile.schools = body.schools
        profile.target_roles = body.target_roles
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_profile(self, user_id: UUID) -> ReferralProfile | None:
        return await self.db.scalar(select(ReferralProfile).where(ReferralProfile.user_id == user_id))

    async def add_candidates(self, user_id: UUID, campaign_id: UUID, candidates: list[CandidateIn]) -> list[ReferralCandidate]:
        campaign = await self.get_campaign(user_id, campaign_id)
        added: list[ReferralCandidate] = []
        for item in candidates:
            score, reasons = score_candidate(item.model_dump(), campaign.company_name, campaign.job_title)
            existing = None
            if item.profile_url:
                existing = await self.db.scalar(
                    select(ReferralCandidate).where(
                        ReferralCandidate.campaign_id == campaign_id,
                        ReferralCandidate.profile_url == item.profile_url,
                    )
                )
            if existing:
                existing.score = score
                existing.reasons = reasons
                candidate = existing
            else:
                candidate = ReferralCandidate(
                    user_id=user_id,
                    campaign_id=campaign_id,
                    score=score,
                    reasons=reasons,
                    **item.model_dump(),
                )
                self.db.add(candidate)
            added.append(candidate)
        campaign.status = "candidates_found"
        await self.db.commit()
        for candidate in added:
            await self.db.refresh(candidate)
        await self.record_event(user_id, campaign_id, "candidates_added", {"count": len(added)})
        return added

    async def create_outreach_plan(self, user_id: UUID, campaign_id: UUID, limit: int, message_type: str) -> list[tuple[ReferralCandidate, OutreachMessage]]:
        campaign = await self.get_campaign(user_id, campaign_id)
        sent_today = await self.sent_today(user_id)
        capacity = remaining_send_capacity(sent_today, settings.daily_linkedin_send_limit)
        limit = min(limit, capacity)
        if limit <= 0:
            return []

        existing_candidate_ids = {
            row[0]
            for row in (
                await self.db.execute(
                    select(OutreachMessage.candidate_id).where(
                        OutreachMessage.campaign_id == campaign_id,
                        OutreachMessage.message_type == message_type,
                    )
                )
            ).all()
        }
        candidates = sorted(
            [c for c in campaign.candidates if c.id not in existing_candidate_ids],
            key=lambda c: c.score,
            reverse=True,
        )[:limit]
        tasks: list[tuple[ReferralCandidate, OutreachMessage]] = []
        for candidate in candidates:
            message = OutreachMessage(
                user_id=user_id,
                campaign_id=campaign_id,
                candidate_id=candidate.id,
                channel="linkedin",
                message_type=message_type,
                body=await self.generate_body(user_id, campaign, candidate, message_type),
                status="queued",
                metadata_={"score": candidate.score, "reasons": candidate.reasons},
            )
            self.db.add(message)
            tasks.append((candidate, message))
            if message_type == "referral_request":
                for sequence, due_at in enumerate(followup_due_dates(), start=1):
                    self.db.add(
                        Followup(
                            user_id=user_id,
                            campaign_id=campaign_id,
                            candidate_id=candidate.id,
                            message_id=message.id,
                            sequence_number=sequence,
                            due_at=due_at,
                            status="scheduled",
                        )
                    )
        campaign.status = "outreach_queued"
        await self.db.commit()
        for _, message in tasks:
            await self.db.refresh(message)
        await self.record_event(user_id, campaign_id, "outreach_plan_created", {"count": len(tasks)})
        return tasks

    async def generate_body(self, user_id: UUID, campaign: ReferralCampaign, candidate: ReferralCandidate, message_type: str) -> str:
        profile = await self.get_profile(user_id)
        intro = f"Hi {candidate.name.split()[0]},"
        context = f"I saw your work around {campaign.company_name} and I'm interested in the {campaign.job_title} role."
        background = ""
        if profile and (profile.headline or profile.skills):
            skills = ", ".join((profile.skills or [])[:4])
            background = f" My background: {profile.headline or skills}."
        ask = "Would you be open to pointing me to the right person or sharing any referral advice?"
        if message_type.startswith("followup"):
            ask = "Just following up in case this got buried. Any guidance would help."
        return " ".join([intro, context, background, ask]).replace("  ", " ").strip()

    async def update_send_status(self, user_id: UUID, message_id: UUID, status: str, details: dict) -> OutreachMessage:
        if not is_allowed_send_status(status):
            raise ValueError("Unsupported message status")
        message = await self.db.scalar(
            select(OutreachMessage).where(OutreachMessage.user_id == user_id, OutreachMessage.id == message_id)
        )
        if not message:
            raise ValueError("Message not found")
        if status == "sent" and remaining_send_capacity(await self.sent_today(user_id), settings.daily_linkedin_send_limit) <= 0:
            raise ValueError("Daily LinkedIn send limit reached")
        message.status = status
        message.metadata_ = {**(message.metadata_ or {}), "send_details": details}
        if status == "sent":
            message.sent_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(message)
        await self.record_event(user_id, message.campaign_id, f"message_{status}", details, message.id)
        return message

    async def get_extension_session(self, user_id: UUID) -> dict:
        session = await self.db.scalar(select(ExtensionSession).where(ExtensionSession.user_id == user_id))
        sent_today = await self.sent_today(user_id)
        limit = settings.daily_linkedin_send_limit
        return {
            "status": session.status if session else "not_connected",
            "version": session.version if session else None,
            "last_seen_at": session.last_seen_at if session else None,
            "daily_send_limit": limit,
            "sent_today": sent_today,
            "remaining": remaining_send_capacity(sent_today, limit),
        }

    async def record_extension_event(self, user_id: UUID, status: str, version: str | None, details: dict) -> None:
        session = await self.db.scalar(select(ExtensionSession).where(ExtensionSession.user_id == user_id))
        if not session:
            session = ExtensionSession(user_id=user_id)
            self.db.add(session)
        session.status = status if status == "connected" else "connected"
        session.version = version or session.version
        session.last_seen_at = datetime.now(timezone.utc)
        campaign_id = details.get("campaignId")
        if campaign_id:
            await self.record_event(user_id, UUID(campaign_id), status, details)
        await self.db.commit()

    async def run_due_followups(self, user_id: UUID) -> list[tuple[ReferralCandidate, OutreachMessage]]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Followup).where(
                Followup.user_id == user_id,
                Followup.status == "scheduled",
                Followup.due_at <= now,
            )
        )
        tasks = []
        for followup in result.scalars().all():
            candidate = await self.db.get(ReferralCandidate, followup.candidate_id)
            campaign = await self.db.get(ReferralCampaign, followup.campaign_id)
            if not candidate or not campaign:
                continue
            message = OutreachMessage(
                user_id=user_id,
                campaign_id=campaign.id,
                candidate_id=candidate.id,
                channel="linkedin",
                message_type=f"followup_{followup.sequence_number}",
                body=await self.generate_body(user_id, campaign, candidate, f"followup_{followup.sequence_number}"),
                status="queued",
                metadata_={"followup_id": str(followup.id)},
            )
            followup.status = "queued"
            self.db.add(message)
            tasks.append((candidate, message))
        await self.db.commit()
        return tasks

    async def sent_today(self, user_id: UUID) -> int:
        today = datetime.now(timezone.utc).date()
        return await self.db.scalar(
            select(func.count()).select_from(OutreachMessage).where(
                OutreachMessage.user_id == user_id,
                OutreachMessage.status == "sent",
                func.date(OutreachMessage.sent_at) == today,
            )
        ) or 0

    async def record_event(self, user_id: UUID, campaign_id: UUID, event_type: str, details: dict, message_id: UUID | None = None) -> None:
        self.db.add(
            ConversationEvent(
                user_id=user_id,
                campaign_id=campaign_id,
                message_id=message_id,
                event_type=event_type,
                details=details,
            )
        )
        await self.db.commit()

    async def _fetch_job(self, job_id: UUID, token: str | None) -> dict:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.job_api_url}/api/v1/jobs/{job_id}", headers=headers)
        response.raise_for_status()
        return response.json()
