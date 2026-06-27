#!/usr/bin/env bash
# Decode HTML entities and rebuild description_plain for all existing jobs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/job-api"
source .venv/bin/activate

python <<'PY'
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job
from app.services.job_service import normalize_job_description

engine = create_engine(settings.database_url_sync)
updated = 0

with Session(engine) as session:
    jobs = session.execute(select(Job)).scalars().all()
    for job in jobs:
        html, plain = normalize_job_description(job.description)
        if html != job.description or plain != job.description_plain:
            job.description = html
            job.description_plain = plain
            updated += 1
    session.commit()

print(f"Backfilled {updated} job descriptions")
PY
