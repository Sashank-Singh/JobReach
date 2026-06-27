#!/usr/bin/env bash
# First-time local setup (no Docker). Requires Homebrew on macOS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> JobReach local setup (no Docker)"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install from https://brew.sh"
  exit 1
fi

# Postgres 17 (pgvector Homebrew bottles target @17/@18, not @16)
for pkg in postgresql@17 pgvector redis; do
  if ! brew list "$pkg" >/dev/null 2>&1; then
    echo "==> Installing $pkg..."
    brew install "$pkg"
  fi
done

# Start services
brew services start postgresql@17
brew services start redis

PG_BIN="$(brew --prefix postgresql@17)/bin"
export PATH="$PG_BIN:$PATH"

echo "==> Waiting for Postgres..."
for i in {1..30}; do
  if pg_isready -q 2>/dev/null; then break; fi
  sleep 1
done
pg_isready || { echo "Postgres failed to start. Run: brew services start postgresql@17"; exit 1; }

# Database + user
DB_USER="${JOBREACH_DB_USER:-jobreach}"
DB_PASS="${JOBREACH_DB_PASS:-jobreach}"
DB_NAME="${JOBREACH_DB_NAME:-jobreach}"

if ! psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  echo "==> Creating Postgres role $DB_USER..."
  psql postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS' CREATEDB;"
fi

if ! psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
  echo "==> Creating database $DB_NAME..."
  psql postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
fi

echo "==> Enabling pgvector extension..."
psql "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null \
  || psql "$DB_NAME" -U "$DB_USER" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Root .env
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example"
fi

# Python venv
if [[ ! -d services/job-api/.venv ]]; then
  echo "==> Creating Python venv..."
  python3 -m venv services/job-api/.venv
fi
source services/job-api/.venv/bin/activate
pip install -q -r services/job-api/requirements.txt

# Migrations
cd services/job-api
alembic upgrade head
cd "$ROOT"

# Frontend deps + env
if [[ ! -d apps/web/node_modules ]]; then
  echo "==> Installing frontend dependencies..."
  (cd apps/web && npm install)
fi

echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > apps/web/.env.local

echo ""
echo "Setup complete. Start dev with:"
echo "  ./scripts/dev-local.sh"
echo ""
echo "Or run each service in separate terminals — see docs/LOCAL-DEV.md"
