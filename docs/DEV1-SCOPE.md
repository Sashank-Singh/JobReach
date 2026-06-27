# JobReach — Developer 1 Scope

You own the **entire Job Platform**. Developer 2 never touches this code.

## Responsibilities

| Module | Status | Location |
|--------|--------|----------|
| Job Collection (Greenhouse, Lever, Ashby) | ✅ Scaffolded | `services/job-api/app/collectors/` |
| Hourly Celery worker | ✅ Scaffolded | `services/job-api/app/workers/` |
| Database (companies, jobs, skills, salary, filters) | ✅ Migrated | `services/job-api/app/models/` |
| GET /jobs with filters | ✅ Live | `services/job-api/app/api/v1/jobs.py` |
| AI embedding match | ✅ Scaffolded | `services/job-api/app/services/embedding_service.py` |
| Resume parser | ✅ Scaffolded | `services/job-api/app/services/resume_parser.py` |
| Job dashboard (left panel) | ✅ Live | `apps/web/src/components/` |
| Notification digest | ✅ Scaffolded | `services/job-api/app/services/notification_service.py` |
| Company profiles | ✅ API ready | `GET /api/v1/companies/{id}` |

## APIs You Expose (Dev 2 consumes these)

```
GET  /api/v1/jobs
GET  /api/v1/jobs/{id}
POST /api/v1/jobs/save
POST /api/v1/jobs/apply
POST /api/v1/jobs/{id}/referral-handoff   ← handoff to Dev 2
POST /api/v1/resume/upload
GET  /api/v1/companies/{id}
GET  /api/v1/notifications
```

## Database A (Your tables only)

- users, companies, jobs, job_locations, job_skills, job_salary, job_embeddings
- job_filters, saved_jobs, applications, resumes, notification_logs

## Do NOT Touch

- `services/referral-api/` (Dev 2 — future)
- Right panel referral UI logic (placeholder only; Dev 2 replaces)

## Local Dev (No Docker)

```bash
./scripts/setup-local.sh   # first time
./scripts/dev-local.sh
```

See [LOCAL-DEV.md](LOCAL-DEV.md).

## Trigger job collection manually

```bash
./scripts/collect-jobs.sh
```
