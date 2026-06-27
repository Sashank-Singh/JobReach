#!/usr/bin/env bash
# Backfill job_embeddings for jobs missing vectors (required for AI match %).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/job-api"
source .venv/bin/activate

python <<'PY'
import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job, JobEmbedding
from app.services.embedding_service import EmbeddingService

engine = create_engine(settings.database_url_sync)
embedding_service = EmbeddingService()
created = 0
skipped = 0
errors = 0

async def embed_job(session: Session, job: Job) -> bool:
    text = f"{job.title}\n{job.description_plain or job.description or ''}"[:8000]
    if not text.strip():
        return False
    vector = await embedding_service.embed_text(text)
    if not vector:
        return False
    session.add(JobEmbedding(job_id=job.id, embedding=vector, model=settings.embedding_model))
    return True

async def main():
    global created, skipped, errors
    with Session(engine) as session:
        jobs = session.execute(
            select(Job).where(Job.is_active.is_(True)).order_by(Job.posted_at.desc().nullslast())
        ).scalars().all()
        existing = {
            row[0]
            for row in session.execute(select(JobEmbedding.job_id)).all()
        }

        for i, job in enumerate(jobs, 1):
            if job.id in existing:
                skipped += 1
                continue
            try:
                if await embed_job(session, job):
                    created += 1
                    if created % 25 == 0:
                        session.commit()
                        print(f"  ... {created} embeddings saved ({i}/{len(jobs)})")
                else:
                    errors += 1
            except Exception as exc:
                errors += 1
                print(f"  skip {job.id}: {exc}")

        session.commit()

asyncio.run(main())
print(f"Done: {created} created, {skipped} already had embeddings, {errors} failed")
PY
