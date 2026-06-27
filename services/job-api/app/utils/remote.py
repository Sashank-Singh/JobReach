import re

REMOTE = re.compile(r"\bremote\b", re.IGNORECASE)
HYBRID = re.compile(r"\bhybrid\b", re.IGNORECASE)


def infer_remote_type(location: str | None, title: str | None = None) -> str:
    text = " ".join(filter(None, [location, title])).lower()
    if not text:
        return "onsite"
    if REMOTE.search(text) and HYBRID.search(text):
        return "hybrid"
    if REMOTE.search(text):
        return "remote"
    if HYBRID.search(text):
        return "hybrid"
    return "onsite"
