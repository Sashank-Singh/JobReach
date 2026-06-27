#!/usr/bin/env bash
# Manually trigger job collection (no Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/services/job-api"

source .venv/bin/activate
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a

celery -A app.workers.celery_app call app.workers.tasks.collect_all_jobs
