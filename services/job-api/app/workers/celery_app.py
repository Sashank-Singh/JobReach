from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("jobreach", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "collect-jobs-hourly": {
            "task": "app.workers.tasks.collect_all_jobs",
            "schedule": crontab(minute=0, hour=f"*/{settings.job_collector_interval_hours}"),
        },
        "morning-notifications": {
            "task": "app.workers.tasks.send_morning_digests",
            "schedule": crontab(minute=0, hour=8),
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
