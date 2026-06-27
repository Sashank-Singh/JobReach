# JobReach

Tuilink-style job search + referral platform, split across two developers with clean API boundaries.

## Architecture

```
Frontend (Next.js)          ← Dev 1 owns left panel
        │
        ├── Job Service (FastAPI)     ← Dev 1
        │       └── PostgreSQL + pgvector + Redis + Celery
        │
        └── Referral Service (FastAPI) ← Dev 2 (future)
                └── PostgreSQL + Playwright + OpenAI
```

## Quick Start

```bash
cp .env.example .env
# Optional: add OPENAI_API_KEY for real embeddings + resume parsing

docker compose up --build
```

| Service | URL |
|---------|-----|
| Job Dashboard | http://localhost:3000 |
| Job API + Swagger | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## Developer 1 — Job Platform

See [docs/DEV1-SCOPE.md](docs/DEV1-SCOPE.md)

- Job aggregation from Greenhouse, Lever, Ashby (hourly)
- Semantic search with resume ↔ job embedding match scores
- Filters: keyword, location, experience, remote, visa, salary, posted date
- Resume upload + parsing
- Company intelligence profiles
- Morning job digest notifications

## Developer 2 — Referral Platform

See [docs/API-CONTRACT.md](docs/API-CONTRACT.md)

- Triggered only by `Add Referral` with a `job_id`
- Employee discovery, AI outreach, browser automation, CRM

## Project Structure

```
JobReach/
├── apps/web/                 # Next.js dashboard (Dev 1 UI)
├── services/job-api/         # FastAPI job service (Dev 1)
├── docs/                     # Scope + API contract
└── docker-compose.yml
```

## Deploy (Coolify)

1. Create Coolify project `JobReach`
2. Deploy PostgreSQL with `pgvector/pgvector:pg16`
3. Deploy Redis
4. Deploy `services/job-api` from GitHub (Dockerfile)
5. Deploy `apps/web` from GitHub (Dockerfile)
6. Set env vars: `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `NEXT_PUBLIC_API_URL`
