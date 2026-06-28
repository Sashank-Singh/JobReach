import os

from app.utils.html import html_to_plain
from app.utils.salary import fetch_careers_page_supplement

_FOOTER_JUNK_MARKERS = ("Germany Deutsch", "Powered by Greenhouse", "Similar jobs")


def _has_pay_section(plain: str) -> bool:
    lower = plain.lower()
    return "pay and benefits" in lower or "pay & benefits" in lower


def _has_careers_footer_junk(plain: str) -> bool:
    return any(marker in plain for marker in _FOOTER_JUNK_MARKERS)


def merge_description_with_careers_page(
    description: str | None,
    description_plain: str | None,
    apply_url: str | None,
) -> tuple[str | None, str | None]:
    """Append pay/compensation section from company careers page when ATS API omits it."""
    plain = description_plain or html_to_plain(description) or ""

    if _has_pay_section(plain) and not _has_careers_footer_junk(plain):
        return description, plain or description_plain

    if os.getenv("JOBREACH_FETCH_CAREERS_SUPPLEMENT") != "1":
        return description, plain or description_plain

    supplement = fetch_careers_page_supplement(apply_url)
    if not supplement:
        return description, plain or description_plain

    if supplement.lower() in plain.lower():
        return description, plain or description_plain

    merged_plain = f"{plain}\n\n{supplement}".strip() if plain else supplement
    merged_html = description
    if description:
        merged_html = f"{description}\n<hr/>\n<p>{_escape_for_html(supplement)}</p>"
    else:
        merged_html = f"<p>{_escape_for_html(supplement)}</p>"

    return merged_html, merged_plain


def _escape_for_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
