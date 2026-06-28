import re
from typing import TypedDict

import httpx

from app.utils.html import html_to_plain

_BOARD_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "ashby.com")


class SalaryData(TypedDict):
    min_salary: int
    max_salary: int
    currency: str
    period: str


def _amount(prefix: str) -> str:
    return (
        rf"(?P<{prefix}_num>\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?|\d+(?:\.\d+)?)"
        rf"\s*(?P<{prefix}_sfx>[kKmM])?"
    )


_CURRENCY = r"(?P<cur>[\$£€]|USD|EUR|GBP|CAD|AUD)"
_HOURLY = re.compile(r"\b(per\s+hour|/hr|hourly|an\s+hour)\b", re.IGNORECASE)

# High-confidence: explicit pay language (checked first)
_LABELED_RANGE_PATTERNS = [
    re.compile(
        rf"(?:annual\s+)?(?:US\s+)?base\s+salary\s+range(?:\s+for\s+this\s+role)?\s+is\s*"
        rf"(?P<c1>[\$£€])?\s*{_amount('min')}\s*[-–—]\s*(?P<c2>[\$£€])?\s*{_amount('max')}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:salary|compensation|pay)\s+range(?:\s+for\s+this\s+role)?\s+is\s*"
        rf"(?P<c1>[\$£€])?\s*{_amount('min')}\s*[-–—]\s*(?P<c2>[\$£€])?\s*{_amount('max')}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<c1>[\$£€])\s*{_amount('min')}\s*[-–—]\s*(?P<c2>[\$£€])?\s*{_amount('max')}"
        rf"(?:\s*\.|\s+For\s+sales)",
        re.IGNORECASE,
    ),
]

# Requires currency symbol or k/M suffix — avoids "4-6 teams"
_RANGE_PATTERNS = [
    re.compile(
        rf"(?P<c1>[\$£€]|USD|EUR|GBP|CAD|AUD)\s*{_amount('min')}\s*"
        rf"(?:[-–—]|to)\s*"
        rf"(?P<c2>[\$£€]|USD|EUR|GBP|CAD|AUD)?\s*{_amount('max')}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"{_amount('min')}\s*[-–—]\s*{_amount('max')}\s*(?:{_CURRENCY}|k|K|M)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"{_amount('min')}\s*[-–—]\s*{_amount('max')}\s*(?:per\s+year|/yr|annually|USD|GBP|EUR)",
        re.IGNORECASE,
    ),
]

_SINGLE_PATTERNS = [
    re.compile(
        rf"(?:annual\s+)?(?:base\s+)?salary\s+(?:of|is|:)\s*(?P<c1>[\$£€]|USD|EUR|GBP|CAD|AUD)?\s*{_amount('amt')}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:pay\s+range|compensation)\s*(?:of|:)?\s*"
        rf"(?P<c1>[\$£€]|USD|EUR|GBP|CAD|AUD)?\s*{_amount('amt')}",
        re.IGNORECASE,
    ),
]

_SYMBOL_TO_CODE = {"$": "USD", "£": "GBP", "€": "EUR"}

_MIN_ANNUAL = 20_000
_MAX_ANNUAL = 2_000_000
_MIN_HOURLY = 10
_MAX_HOURLY = 500


def _parse_amount(num_str: str, suffix: str | None) -> int:
    value = float(num_str.replace(",", ""))
    if suffix:
        mult = suffix.lower()
        if mult == "k":
            value *= 1_000
        elif mult == "m":
            value *= 1_000_000
    return int(value)


def _normalize_currency(raw: str | None) -> str:
    if not raw:
        return "USD"
    token = raw.strip().upper()
    if token in _SYMBOL_TO_CODE:
        return _SYMBOL_TO_CODE[token]
    if len(token) == 3:
        return token
    return "USD"


def _pick_currency(*tokens: str | None) -> str:
    for token in tokens:
        if token:
            return _normalize_currency(token)
    return "USD"


def _is_plausible(min_salary: int, max_salary: int, period: str) -> bool:
    lo = min(min_salary, max_salary)
    hi = max(min_salary, max_salary)
    if period == "hour":
        return _MIN_HOURLY <= lo <= _MAX_HOURLY and hi <= _MAX_HOURLY
    return _MIN_ANNUAL <= lo <= _MAX_ANNUAL and hi <= _MAX_ANNUAL


def salary_is_valid(min_salary: int | None, max_salary: int | None, period: str = "year") -> bool:
    if not min_salary and not max_salary:
        return False
    mn = min_salary or max_salary or 0
    mx = max_salary or min_salary or 0
    return _is_plausible(mn, mx, period)


def salary_dict_is_valid(data: dict | None) -> bool:
    if not data:
        return False
    return salary_is_valid(
        data.get("min_salary"),
        data.get("max_salary"),
        data.get("period", "year"),
    )


def _amount_from_groups(groups: dict, prefix: str) -> int:
    return _parse_amount(groups[f"{prefix}_num"], groups.get(f"{prefix}_sfx"))


def _match_to_salary(match: re.Match, sample: str) -> SalaryData | None:
    groups = match.groupdict()
    if groups.get("min_num"):
        min_salary = _amount_from_groups(groups, "min")
        max_salary = _amount_from_groups(groups, "max")
    elif groups.get("amt_num"):
        min_salary = max_salary = _amount_from_groups(groups, "amt")
    else:
        return None

    if min_salary > max_salary:
        min_salary, max_salary = max_salary, min_salary

    period = "hour" if _HOURLY.search(sample[match.start() : match.end() + 80]) else "year"
    if not salary_is_valid(min_salary, max_salary, period):
        return None

    currency = _pick_currency(groups.get("c1"), groups.get("c2"), groups.get("cur"))
    return {
        "min_salary": min_salary,
        "max_salary": max_salary,
        "currency": currency,
        "period": period,
    }


def extract_salary_from_text(text: str | None) -> SalaryData | None:
    """Extract salary range or single amount from job description text."""
    if not text:
        return None

    sample = text
    all_patterns = _LABELED_RANGE_PATTERNS + _RANGE_PATTERNS + _SINGLE_PATTERNS

    for pattern in all_patterns:
        for match in pattern.finditer(sample):
            result = _match_to_salary(match, sample)
            if result:
                return result

    return None


def salary_for_response(job_salary) -> dict | None:
    """Return salary payload for API responses, or None when values are missing/implausible."""
    if job_salary is None:
        return None
    period = job_salary.period or "year"
    if not salary_is_valid(job_salary.min_salary, job_salary.max_salary, period):
        return None
    return {
        "min_salary": job_salary.min_salary,
        "max_salary": job_salary.max_salary,
        "currency": job_salary.currency,
        "period": job_salary.period,
    }


def _is_external_careers_url(apply_url: str | None) -> bool:
    if not apply_url:
        return False
    return not any(host in apply_url for host in _BOARD_HOSTS)


def extract_pay_section(plain: str) -> str | None:
    """Pull Pay/Compensation and location metadata from full careers page text."""
    start_markers = [
        "Pay and benefits",
        "Pay & benefits",
        "Compensation",
        "Salary range",
    ]
    end_markers = [
        "Apply for this role",
        "Apply for the role",
        "Please find our California",
        "Powered by Greenhouse",
        "Similar jobs",
    ]

    lower = plain.lower()
    best_idx = -1
    for marker in start_markers:
        idx = lower.find(marker.lower())
        if idx >= 0 and (best_idx < 0 or idx < best_idx):
            best_idx = idx
    if best_idx < 0:
        return None

    end_idx = len(plain)
    for marker in end_markers:
        idx = lower.find(marker.lower(), best_idx + 1)
        if idx >= 0:
            end_idx = min(end_idx, idx)

    chunk = plain[best_idx:end_idx].strip()
    return chunk or None


def fetch_careers_page_supplement(apply_url: str | None) -> str | None:
    """Fetch pay/comp section from company-hosted apply page (e.g. stripe.com/jobs)."""
    if not _is_external_careers_url(apply_url):
        return None
    try:
        timeout = httpx.Timeout(4.0, connect=2.0)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(
                apply_url,
                headers={"User-Agent": "JobReach/1.0 (+https://github.com/Sashank-Singh/JobReach)"},
            )
            response.raise_for_status()
            plain = html_to_plain(response.text)
            if not plain:
                return None
            return extract_pay_section(plain)
    except Exception:
        return None
