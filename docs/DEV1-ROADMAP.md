# Dev 1 Roadmap → Dev 2 Handoff

Your dashboard shows **0 jobs** because job collection has not successfully run yet (there was also a Greenhouse parser bug — now fixed). Run `./scripts/collect-jobs.sh` after pulling latest.

---

## Phase 1 — Make the job board real (this week)

**Goal:** Left panel fully works with real data. Dev 2 can click a job and get a valid `job_id`.

| # | Task | Why | Done when |
|---|------|-----|-----------|
| 1 | **Fix + run job collectors** | Without jobs, nothing else matters | `./scripts/collect-jobs.sh` → 500+ jobs in DB |
| 2 | **Verify filters work** | keyword, remote, location, posted_days | Each filter changes results in UI |
| 3 | **Job detail panel polish** | HTML descriptions, apply link, company name | Click any job → full detail loads |
| 4 | **Save + Apply buttons** | Track user intent before referral | POST save/apply returns 200, rows in DB |
| 5 | **Seed more companies** | Expand beyond Stripe/Figma/Notion/Linear/Netflix | Add 20+ companies in `job_ingestion.py` |

**Commands:**
```bash
./scripts/dev-local.sh
./scripts/collect-jobs.sh
curl "http://localhost:8000/api/v1/jobs?page_size=5"
```

---

## Phase 2 — AI matching + resume (Dev 1 differentiator)

**Goal:** Upload resume → jobs re-rank by match %.

| # | Task | Why |
|---|------|-----|
| 6 | Add `FIREWORKS_API_KEY` to `.env` | Real embeddings beat hash fallback |
| 7 | Backfill job embeddings on collect | Every new job gets embedded |
| 8 | Resume upload UX | Show parsed skills + "matching..." state |
| 9 | Match score in UI | Already wired — needs embeddings populated |
| 10 | Resume optimizer (stretch) | Tailor resume text per job before apply |

---

## Phase 3 — Company intelligence + notifications

**Goal:** Tuilink-level company pages + proactive alerts.

| # | Task | Why |
|---|------|-----|
| 11 | Company profile page | hiring velocity, visa, interview difficulty |
| 12 | Enrich company metadata | Scrape Levels.fyi / Glassdoor / H1B data |
| 13 | Job filters saved per user | "AI Engineer", "PM", etc. |
| 14 | Morning digest | Celery beat at 8am → notification_logs |
| 15 | Email/push delivery | Wire LangFuse/Postal already on Coolify |

---

## Phase 4 — Shared auth (both devs need this)

**Goal:** Real users instead of `DEMO_USER_ID`.

| # | Task | Owner |
|---|------|-------|
| 16 | Supabase Auth or Clerk | **Both** — pick one, Dev 1 integrates first |
| 17 | JWT middleware on job-api | Dev 1 |
| 18 | Pass `user_id` from session to all API calls | Dev 1 frontend |
| 19 | Dev 2 reads same JWT | Dev 2 |

Until auth ships, handoff uses the demo user UUID: `00000000-0000-0000-0000-000000000001`.

---

## Phase 5 — Dev 2 handoff (your exit criteria)

**Do not start Dev 2 work until these are green:**

### Dev 1 deliverables checklist

- [ ] `GET /api/v1/jobs` returns jobs with filters
- [ ] `GET /api/v1/jobs/{id}` returns full job + company
- [ ] `POST /api/v1/jobs/save` persists saved jobs
- [ ] `POST /api/v1/jobs/apply` creates application row
- [ ] `POST /api/v1/jobs/{id}/referral-handoff` returns `{ job_id, user_id }`
- [ ] `POST /api/v1/resume/upload` returns parsed resume (Dev 2 needs this for message personalization)
- [ ] `GET /api/v1/companies/{id}` returns company intel
- [ ] Frontend "Add Referral" button calls handoff endpoint
- [ ] API deployed on Coolify with stable URL
- [ ] `docs/API-CONTRACT.md` reviewed by Dev 2

### What Dev 2 receives

```
┌─────────────────────────────────────────────────────────┐
│  Dev 1 hands off ONLY:                                  │
│                                                         │
│  1. job_id (UUID)                                       │
│  2. user_id (UUID)                                      │
│  3. Stable API base URL                                 │
│  4. API contract doc                                    │
└─────────────────────────────────────────────────────────┘
```

Dev 2 **pulls context** from your APIs — never duplicates job data:

| Dev 2 calls | Gets |
|-------------|------|
| `GET /api/v1/jobs/{id}` | title, description, company, skills, apply_url |
| `GET /api/v1/companies/{id}` | company intel |
| User's latest resume | via shared auth + `GET /resume` (you add this) |

### Dev 2 builds (you never touch)

```
services/referral-api/
├── POST /referrals/start     ← receives job_id
├── Employee discovery        ← Apollo, Proxycurl, etc.
├── Employee ranking
├── AI message writer
├── Playwright / Browserbase
├── Follow-up scheduler
├── CRM (messages, pipeline)
└── Right panel UI
```

### Integration smoke test (run together)

1. Dev 1: collect jobs, open dashboard, pick a Stripe role
2. Dev 1: click **Add Referral** → handoff returns `job_id`
3. Dev 2: `POST /referrals/start { "job_id": "..." }`
4. Dev 2: `GET http://job-api/api/v1/jobs/{job_id}` → confirms job context
5. Dev 2: discovers employees, shows them in right panel
6. Dev 2: generates referral message using job + resume from Dev 1

---

## Suggested split timeline

| Week | Dev 1 | Dev 2 (starts after handoff checklist) |
|------|-------|----------------------------------------|
| 1 | Phase 1 — jobs flowing, filters, save/apply | Read API contract, scaffold `referral-api` |
| 2 | Phase 2 — resume + embeddings | `POST /referrals/start` + employee discovery |
| 3 | Phase 3 — company intel + notifications | AI messages + CRM schema |
| 4 | Phase 4 — shared auth | Playwright automation + right panel UI |

---

## Immediate next action (today)

```bash
# 1. Pull Greenhouse fix
git pull

# 2. Collect jobs
./scripts/collect-jobs.sh

# 3. Refresh dashboard — should show hundreds of jobs
open http://localhost:3000
```

If still 0 jobs, run ingestion directly:
```bash
cd services/job-api && source .venv/bin/activate
python -c "from app.services.job_ingestion import JobIngestionService; print(JobIngestionService().run_all())"
```

Then pick **one job**, test Save → Apply → Add Referral, and share the `job_id` with Dev 2 to start their service.
