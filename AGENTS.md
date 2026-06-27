## Learned User Preferences

- Prefer local native development; do not run the stack in Docker locally (Docker is for Coolify production deploys only).
- User is Developer 1 and owns the Job Platform vertical exclusively; Developer 2 owns the referral/outreach vertical.
- Split work by vertical with communication only through well-defined APIs, not shared database tables or overlapping APIs.
- Use Fireworks API for AI features (not OpenAI); chat model is `accounts/fireworks/models/minimax-m3`.
- Has Coolify access for deploying open-source infrastructure.

## Learned Workspace Facts

- JobReach is a Tuilink-inspired monorepo: `apps/web` (Next.js dashboard) and `services/job-api` (FastAPI + Celery workers).
- Job collectors ingest from Greenhouse, Lever, and Ashby ATS boards.
- Local dev flow: `./scripts/setup-local.sh` then `./scripts/dev-local.sh` (Homebrew Postgres 17 + pgvector, Redis, native Python/Node).
- Production deploys target Coolify with pgvector Postgres and Redis.
- Auth is email/password against the JobReach Postgres database with JWT sessions (`/register`, `/login`).
- Embeddings use Fireworks `qwen3-embedding-8b` (768 dimensions); resume parsing uses Fireworks `minimax-m3`.
- Dev 1 roadmap and Dev 2 handoff criteria are documented in `docs/DEV1-ROADMAP.md`.
