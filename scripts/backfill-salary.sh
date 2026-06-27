#!/usr/bin/env bash
# Parse salary from job descriptions; fix implausible values; enrich from careers pages.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/job-api"
source .venv/bin/activate

python <<'PY'
from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, JobSalary
from app.utils.careers_page import merge_description_with_careers_page
from app.utils.salary import extract_salary_from_text, salary_dict_is_valid, salary_is_valid

engine = create_engine(settings.database_url_sync)
created = updated = skipped = cleared = enriched = 0

with Session(engine) as session:
    jobs = session.execute(select(Job).outerjoin(JobSalary)).scalars().unique().all()

    for job in jobs:
        needs_salary = (
            job.salary is None
            or not salary_dict_is_valid(
                {
                    "min_salary": job.salary.min_salary,
                    "max_salary": job.salary.max_salary,
                    "period": job.salary.period or "year",
                }
            )
        )
        if not needs_salary:
            continue

        desc_html, desc_plain = merge_description_with_careers_page(
            job.description, job.description_plain, job.apply_url
        )
        if desc_plain and desc_plain != (job.description_plain or ""):
            job.description = desc_html
            job.description_plain = desc_plain
            enriched += 1

        parsed = extract_salary_from_text(desc_plain or job.description)
        if not parsed or not salary_is_valid(
            parsed["min_salary"], parsed["max_salary"], parsed.get("period", "year")
        ):
            if job.salary and not salary_dict_is_valid(
                {
                    "min_salary": job.salary.min_salary,
                    "max_salary": job.salary.max_salary,
                    "period": job.salary.period or "year",
                }
            ):
                session.delete(job.salary)
                job.salary = None
                cleared += 1
            skipped += 1
            continue

        if job.salary:
            job.salary.min_salary = parsed["min_salary"]
            job.salary.max_salary = parsed["max_salary"]
            job.salary.currency = parsed.get("currency", "USD")
            job.salary.period = parsed.get("period", "year")
            updated += 1
        else:
            session.add(JobSalary(job_id=job.id, **parsed))
            created += 1

    session.commit()

print(
    f"Salary backfill: {created} created, {updated} updated, {cleared} cleared (bad), "
    f"{enriched} descriptions enriched, {skipped} skipped (no match)"
)
PY
