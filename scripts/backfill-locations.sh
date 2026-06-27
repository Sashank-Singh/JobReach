#!/usr/bin/env bash
# Parse job_locations.city strings into country/state fields.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/job-api"
source .venv/bin/activate

python <<'PY'
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import JobLocation
from app.utils.location import parse_location

engine = create_engine(settings.database_url_sync)
updated = 0

with Session(engine) as session:
    locs = session.execute(select(JobLocation)).scalars().all()
    for loc in locs:
        raw = loc.city or ""
        parsed = parse_location(raw)
        changed = (
            loc.country != parsed["country"]
            or loc.state != parsed["state"]
            or (parsed["country"] and loc.country is None)
        )
        if parsed["country"]:
            loc.country = parsed["country"]
        if parsed["state"]:
            loc.state = parsed["state"]
        if parsed["is_remote"]:
            loc.is_remote = True
        if changed or parsed["country"] or parsed["state"]:
            updated += 1
    session.commit()

print(f"Parsed locations on {updated} rows")

# Show country breakdown
with Session(engine) as session:
    from sqlalchemy import func
    rows = session.execute(
        select(JobLocation.country, func.count())
        .where(JobLocation.country.isnot(None))
        .group_by(JobLocation.country)
        .order_by(func.count().desc())
    ).all()
    print("\nJobs by country:")
    for country, cnt in rows:
        print(f"  {country}: {cnt}")
PY
