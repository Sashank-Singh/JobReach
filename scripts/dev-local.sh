#!/usr/bin/env bash
# Run all JobReach services locally without Docker.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — run ./scripts/setup-local.sh first"
  exit 1
fi

if [[ ! -d services/job-api/.venv ]]; then
  echo "Missing Python venv — run ./scripts/setup-local.sh first"
  exit 1
fi

VENV_VERSION="$(
  services/job-api/.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true
)"
if [[ "$VENV_VERSION" != "3.12" && "$VENV_VERSION" != "3.13" ]]; then
  echo "Unsupported services/job-api/.venv Python version: ${VENV_VERSION:-unknown}"
  echo "Run ./scripts/setup-local.sh to rebuild it with Python 3.12."
  exit 1
fi

# Ensure Postgres + Redis are up
if ! pg_isready -q 2>/dev/null; then
  echo "Postgres is not running. Start it with:"
  echo "  brew services start postgresql@17"
  exit 1
fi

if ! redis-cli ping >/dev/null 2>&1; then
  echo "Redis is not running. Start it with:"
  echo "  brew services start redis"
  exit 1
fi

# Load env for child processes
set -a
# shellcheck disable=SC1091
source .env
set +a

{
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000"
  echo "NEXT_PUBLIC_REFERRAL_API_URL=http://localhost:8001"
} > apps/web/.env.local

PIDS=()
CLEANED_UP=0
cleanup() {
  if [[ "$CLEANED_UP" == "1" ]]; then
    return
  fi
  CLEANED_UP=1

  echo ""
  echo "Stopping local services..."
  if [[ ${#PIDS[@]} -gt 0 ]]; then
    for pid in "${PIDS[@]}"; do
      kill "$pid" 2>/dev/null || true
    done
  fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Running migrations..."
(
  cd services/job-api
  source .venv/bin/activate
  alembic upgrade head
)
(
  cd services/referral-api
  ../../services/job-api/.venv/bin/alembic upgrade head
)

echo "==> Packaging Chrome extension for local referral testing"
PUBLIC_WEB_ORIGIN=http://localhost:3000 \
NEXT_PUBLIC_REFERRAL_API_URL=http://localhost:8001 \
node apps/chrome-extension/scripts/package-extension.mjs

echo "==> Starting Job API on http://localhost:8000"
(
  cd services/job-api
  source .venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
) &
PIDS+=($!)

echo "==> Starting Referral API on http://localhost:8001"
(
  cd services/referral-api
  ../../services/job-api/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app
) &
PIDS+=($!)

if [[ "${JOBREACH_RUN_WORKERS:-0}" == "1" ]]; then
  echo "==> Starting Celery worker"
  (
    cd services/job-api
    source .venv/bin/activate
    celery -A app.workers.celery_app worker --loglevel=info
  ) &
  PIDS+=($!)

  echo "==> Starting Celery beat (hourly job collection)"
  (
    cd services/job-api
    source .venv/bin/activate
    celery -A app.workers.celery_app beat --loglevel=info
  ) &
  PIDS+=($!)
fi

echo "==> Starting Next.js on http://localhost:3000"
(
  cd apps/web
  npm run dev
) &
PIDS+=($!)

echo ""
echo "JobReach running locally (no Docker):"
echo "  Dashboard : http://localhost:3000"
echo "  API docs  : http://localhost:8000/docs"
echo "  Referral  : http://localhost:8001/docs"
echo "  Extension : dist/chrome-extension"
echo ""
echo "Workers are off by default. To run job collection workers:"
echo "  JOBREACH_RUN_WORKERS=1 ./scripts/dev-local.sh"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

wait
