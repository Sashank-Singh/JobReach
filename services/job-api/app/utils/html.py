import html
import re


def decode_job_html(text: str | None) -> str | None:
    """Greenhouse returns entity-encoded HTML; Ashby returns raw HTML — normalize both."""
    if not text:
        return None
    return html.unescape(text)


def html_to_plain(text: str | None) -> str | None:
    if not text:
        return None
    decoded = decode_job_html(text) or ""
    plain = re.sub(r"<[^>]+>", " ", decoded)
    plain = html.unescape(plain)
    return re.sub(r"\s+", " ", plain).strip() or None
