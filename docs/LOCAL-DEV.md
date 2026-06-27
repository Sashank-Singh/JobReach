# Local Development (No Docker)

Run everything natively on your machine. Docker is only needed for Coolify production deploys.

## Prerequisites

- macOS with [Homebrew](https://brew.sh)
- Node.js 20+
- Python 3.12+

## One-time setup

```bash
chmod +x scripts/*.sh
./scripts/setup-local.sh
```

This installs and starts:

- **PostgreSQL 17** (Homebrew — required for pgvector on macOS)
- **pgvector** extension
- **Redis**
- Python venv + npm packages
- Database migrations

## Start everything

```bash
./scripts/dev-local.sh
```

**First visit:** http://localhost:3000 → redirects to `/register` → create account → dashboard loads with your session persisted in localStorage (same account on reload).

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| Login | http://localhost:3000/login |
| Register | http://localhost:3000/register |
| API + Swagger | http://localhost:8000/docs |

Press `Ctrl+C` to stop all services.

## Run services separately (optional)

Use four terminals if you prefer:

**Terminal 1 — API**
```bash
cd services/job-api
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Celery worker**
```bash
cd services/job-api
source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
```

**Terminal 3 — Celery beat**
```bash
cd services/job-api
source .venv/bin/activate
celery -A app.workers.celery_app beat --loglevel=info
```

**Terminal 4 — Frontend**
```bash
cd apps/web
npm run dev
```

## Collect jobs manually

```bash
./scripts/collect-jobs.sh
```

## Environment

Root `.env` (copy from `.env.example`):

```bash
DATABASE_URL=postgresql+asyncpg://jobreach:jobreach@localhost:5432/jobreach
DATABASE_URL_SYNC=postgresql://jobreach:jobreach@localhost:5432/jobreach
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
GEMINI_API_KEY=your-key-here
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_CHAT_MODEL=gemini-2.0-flash
```

Frontend reads `apps/web/.env.local` (auto-created by setup/dev scripts).

## Troubleshooting

**Postgres not running**
```bash
brew services start postgresql@17
pg_isready
```

**Redis not running**
```bash
brew services start redis
redis-cli ping   # should return PONG
```

**pgvector missing**
```bash
brew install pgvector
psql jobreach -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Reset database**
```bash
dropdb jobreach && createdb jobreach -O jobreach
psql jobreach -c "CREATE EXTENSION vector;"
cd services/job-api && source .venv/bin/activate && alembic upgrade head
```
