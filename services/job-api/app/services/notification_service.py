from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobFilter, NotificationLog


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_morning_digest(self, user_id: UUID) -> NotificationLog | None:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        filters_result = await self.db.execute(
            select(JobFilter).where(JobFilter.user_id == user_id, JobFilter.notify.is_(True))
        )
        user_filters = filters_result.scalars().all()

        if not user_filters:
            return None

        total_new = 0
        sections: list[str] = []

        for job_filter in user_filters:
            filter_data = job_filter.filters or {}
            query = select(func.count()).select_from(Job).where(
                Job.is_active.is_(True), Job.created_at >= since
            )

            if keyword := filter_data.get("keyword"):
                query = query.where(func.lower(Job.title).like(f"%{keyword.lower()}%"))

            count = (await self.db.execute(query)).scalar() or 0
            if count > 0:
                total_new += count
                sections.append(f"{count} {job_filter.name} jobs")

        if total_new == 0:
            return None

        body = "\n".join(sections)
        notification = NotificationLog(
            user_id=user_id,
            title=f"{total_new} new matching jobs this morning",
            body=body,
            job_count=total_new,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification
