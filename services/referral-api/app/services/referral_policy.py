from datetime import datetime, timedelta, timezone

DAILY_SEND_LIMIT = 20
FOLLOWUP_DAY_OFFSETS = (3, 7, 14)
ALLOWED_SEND_STATUSES = {"queued", "sent", "failed", "manual_required", "skipped"}


def followup_due_dates(start: datetime | None = None) -> list[datetime]:
    base = start or datetime.now(timezone.utc)
    return [base + timedelta(days=days) for days in FOLLOWUP_DAY_OFFSETS]


def remaining_send_capacity(sent_today: int, limit: int = DAILY_SEND_LIMIT) -> int:
    return max(limit - sent_today, 0)


def is_allowed_send_status(status: str) -> bool:
    return status in ALLOWED_SEND_STATUSES


def score_candidate(candidate: dict, company_name: str, job_title: str) -> tuple[float, list[str]]:
    score = 35.0
    reasons: list[str] = []
    text = " ".join(
        str(candidate.get(key) or "") for key in ("name", "title", "company", "source")
    ).lower()
    company = company_name.lower()
    title = job_title.lower()

    if company and company in text:
        score += 30
        reasons.append("Works at or is strongly associated with the target company")
    if any(word in text for word in ("recruiter", "talent", "hiring")):
        score += 20
        reasons.append("Likely recruiting or talent contact")
    if any(token in text and token in title for token in ("engineer", "product", "design", "data", "sales", "marketing")):
        score += 15
        reasons.append("Function appears relevant to the target role")
    if "linkedin_search_ui:company_match" in text:
        score += 10
        reasons.append("LinkedIn search result matched company context")

    if not reasons:
        reasons.append("Potential contact discovered from LinkedIn search")
    return min(score, 100.0), reasons
