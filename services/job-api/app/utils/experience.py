import re

ENTRY = re.compile(
    r"\b(intern(ship)?|junior|entry[- ]?level|new grad|graduate|early career|campus)\b",
    re.IGNORECASE,
)
STAFF = re.compile(
    r"\b(staff|principal|distinguished|fellow|distinguished engineer)\b",
    re.IGNORECASE,
)
SENIOR = re.compile(
    r"\b(senior|sr\.?)\b",
    re.IGNORECASE,
)
LEAD = re.compile(
    r"\b(lead|manager|director|head of|vp |vice president)\b",
    re.IGNORECASE,
)


def infer_experience_level(title: str | None) -> str:
    """Infer entry / mid / senior / staff from job title."""
    if not title:
        return "mid"
    if ENTRY.search(title):
        return "entry"
    if STAFF.search(title):
        return "staff"
    if SENIOR.search(title):
        return "senior"
    if LEAD.search(title):
        return "senior"
    return "mid"
