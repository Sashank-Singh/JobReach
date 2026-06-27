import asyncio
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User
from app.services.job_ingestion import JobIngestionService
from app.services.notification_service import NotificationService
from app.workers.celery_app import celery_app

sync_engine = create_engine(settings.database_url_sync)


@celery_app.task(name="app.workers.tasks.collect_all_jobs")
def collect_all_jobs() -> dict:
    service = JobIngestionService()
    return service.run_all()


@celery_app.task(name="app.workers.tasks.send_morning_digests")
def send_morning_digests() -> dict:
    sent = 0
    with Session(sync_engine) as session:
        users = session.execute(select(User)).scalars().all()
        for user in users:
            notification = asyncio.run(NotificationService(_AsyncSessionWrapper(session)).generate_morning_digest(user.id))
            if notification:
                sent += 1
    return {"notifications_sent": sent}


class _AsyncSessionWrapper:
    """Minimal wrapper so NotificationService can use sync session in Celery."""

    def __init__(self, session: Session):
        self._session = session

    async def execute(self, stmt):
        return self._session.execute(stmt)

    async def commit(self):
        self._session.commit()

    async def refresh(self, obj):
        self._session.refresh(obj)

    def add(self, obj):
        self._session.add(obj)
