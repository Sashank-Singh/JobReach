#!/usr/bin/env bash
# Backfill company and job visa_sponsorship from seed company metadata.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/job-api"
source .venv/bin/activate

python <<'PY'
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.data.seed_companies import SEED_COMPANIES
from app.models import Company, Job

seed_by_slug = {c["slug"]: c["visa_sponsorship"] for c in SEED_COMPANIES if "visa_sponsorship" in c}
engine = create_engine(settings.database_url_sync)
companies_updated = 0
jobs_updated = 0

with Session(engine) as session:
    companies = session.execute(select(Company)).scalars().all()
    for company in companies:
        if company.slug in seed_by_slug and company.visa_sponsorship != seed_by_slug[company.slug]:
            company.visa_sponsorship = seed_by_slug[company.slug]
            companies_updated += 1

    session.flush()

    jobs = session.execute(select(Job).where(Job.is_active.is_(True))).scalars().all()
    company_map = {c.id: c for c in companies}
    for job in jobs:
        company = company_map.get(job.company_id)
        if not company:
            continue
        effective = job.visa_sponsorship if job.visa_sponsorship is not None else company.visa_sponsorship
        if job.visa_sponsorship != effective:
            job.visa_sponsorship = effective
            jobs_updated += 1

    session.commit()

print(f"Backfilled visa on {companies_updated} companies and {jobs_updated} jobs")
PY
