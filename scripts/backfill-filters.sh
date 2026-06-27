#!/usr/bin/env bash
# Backfill experience_level and remote_type from job titles/locations.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/job-api"
source .venv/bin/activate

python <<'PY'
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, JobLocation
from app.utils.experience import infer_experience_level
from app.utils.remote import infer_remote_type

engine = create_engine(settings.database_url_sync)
updated = 0

with Session(engine) as session:
    jobs = session.execute(select(Job)).scalars().all()
    for job in jobs:
        locs = session.execute(select(JobLocation).where(JobLocation.job_id == job.id)).scalars().all()
        loc_name = locs[0].city if locs else None
        new_exp = infer_experience_level(job.title)
        new_remote = infer_remote_type(loc_name, job.title)
        if job.experience_level != new_exp or job.remote_type != new_remote:
            job.experience_level = new_exp
            job.remote_type = new_remote
            updated += 1
    session.commit()

print(f"Backfilled experience/remote on {updated} jobs")
PY
