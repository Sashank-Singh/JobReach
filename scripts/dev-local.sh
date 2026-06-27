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

echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > apps/web/.env.local

PIDS=()
cleanup() {
  echo ""
  echo "Stopping local services..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Running migrations..."
(
  cd services/job-api
  source .venv/bin/activate
  alembic upgrade head
)

echo "==> Starting Job API on http://localhost:8000"
(
  cd services/job-api
  source .venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &
PIDS+=($!)

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
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

wait
