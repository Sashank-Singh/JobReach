# Shared API Contract

This document defines the boundary between Developer 1 (Job Service) and Developer 2 (Referral Service).

## Developer 1 → Developer 2

When user clicks **Add Referral**, Dev 1 calls:

```
POST /api/v1/jobs/{job_id}/referral-handoff
```

Response:

```json
{
  "job_id": "uuid",
  "user_id": "uuid"
}
```

Dev 2 receives **only `job_id`** (and resolves job details via Dev 1's API).

Dev 2 then calls Dev 1 to enrich context:

```
GET /api/v1/jobs/{job_id}
```

## Developer 2 Exposes (Dev 1 does NOT implement)

```
POST /referrals/start      { "job_id": "uuid" }
GET  /referrals
GET  /messages
POST /messages/send
POST /followups/run
```

## Database Separation

| Database A (Dev 1) | Database B (Dev 2) |
|--------------------|--------------------|
| users | employees |
| companies | messages |
| jobs | referrals |
| applications | conversation_history |
| saved_jobs | campaigns |
| resumes | followups |

No shared tables. Auth layer is shared (future: Supabase/Clerk).

## Integration Flow

```
User finds job (Dev 1 UI)
       ↓
Clicks "Add Referral"
       ↓
Dev 1: POST /referral-handoff → returns job_id
       ↓
Dev 2: POST /referrals/start { job_id }
       ↓
Dev 2: GET /jobs/{id} from Dev 1 for job + company context
       ↓
Dev 2: employee discovery, ranking, outreach, CRM
```
