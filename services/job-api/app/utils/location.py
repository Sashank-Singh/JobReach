import re

# User search term → strings to match in city / state / country
LOCATION_ALIASES: dict[str, list[str]] = {
    "united states": ["united states", "usa", "u.s.", "u.s.a.", "us", "america", "north america"],
    "united kingdom": ["united kingdom", "uk", "u.k.", "england", "scotland", "wales", "britain", "london"],
    "ireland": ["ireland", "eire", "dublin"],
    "canada": ["canada", "toronto", "vancouver", "montreal"],
    "india": ["india", "bengaluru", "bangalore", "mumbai", "delhi", "hyderabad"],
    "singapore": ["singapore"],
    "japan": ["japan", "tokyo", "osaka"],
    "australia": ["australia", "sydney", "melbourne"],
    "germany": ["germany", "berlin", "munich"],
    "france": ["france", "paris"],
    "mexico": ["mexico", "mexico city"],
    "brazil": ["brazil", "são paulo", "sao paulo"],
    "netherlands": ["netherlands", "amsterdam", "holland"],
    "spain": ["spain", "madrid", "barcelona"],
    "remote": ["remote", "work from home", "wfh", "distributed"],
}

US_STATES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in", "ia",
    "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt",
    "va", "wa", "wv", "wi", "wy", "dc",
}

KNOWN_COUNTRIES = [
    "United States", "United Kingdom", "Ireland", "Canada", "India", "Singapore", "Japan",
    "Australia", "Germany", "France", "Mexico", "Brazil", "Netherlands", "Spain", "Italy",
    "Switzerland", "Sweden", "Poland", "Israel", "South Korea", "China", "Hong Kong",
    "Taiwan", "New Zealand", "Belgium", "Austria", "Denmark", "Norway", "Finland",
    "Portugal", "Argentina", "Colombia", "Chile", "South Africa", "UAE", "Indonesia",
    "Philippines", "Thailand", "Vietnam", "Malaysia", "England", "Scotland", "Wales",
]

_COUNTRY_LOWER = {c.lower(): c for c in KNOWN_COUNTRIES}


def expand_location_search(query: str) -> list[str]:
    """Expand user input into match terms (e.g. 'US' → united states, usa, us)."""
    q = query.strip().lower()
    if not q:
        return []

    terms = {q}
    for _canonical, aliases in LOCATION_ALIASES.items():
        if q in aliases or q == _canonical:
            terms.update(aliases)
            terms.add(_canonical)

    for country in KNOWN_COUNTRIES:
        if q in country.lower() or country.lower() in q:
            terms.add(country.lower())

    return list(terms)


def parse_location(raw: str | None) -> dict:
    """
    Parse ATS location strings into structured fields.
    Returns: city, state, country, display, is_remote
    """
    if not raw or raw.strip().upper() in ("N/A", "NA", "-"):
        return {"city": None, "state": None, "country": None, "display": raw, "is_remote": False}

    display = raw.strip()
    lower = display.lower()
    is_remote = "remote" in lower

    # Multi-location: "SF, CA • NY, NY • United States" — country often last segment
    segments = [s.strip() for s in re.split(r"\s*[•|]\s*", display) if s.strip()]
    primary = segments[0]
    country = _detect_country(display, segments)

    city, state = _parse_city_state(primary, country)

    # Single-token countries/cities: "Singapore", "Dublin"
    if not city and not country and len(segments) == 1:
        token = segments[0]
        if token.lower() in _COUNTRY_LOWER:
            country = _COUNTRY_LOWER[token.lower()]
        else:
            city = token

    return {
        "city": city,
        "state": state,
        "country": country,
        "display": display,
        "is_remote": is_remote,
    }


def _detect_country(full: str, segments: list[str]) -> str | None:
    lower_full = full.lower()

    for segment in reversed(segments):
        seg_lower = segment.lower()
        for country in KNOWN_COUNTRIES:
            if country.lower() in seg_lower:
                return country
        if seg_lower in _COUNTRY_LOWER:
            return _COUNTRY_LOWER[seg_lower]

    if any(x in lower_full for x in ("united states", "u.s.a", " usa", " us-", "remote in the us")):
        return "United States"
    if "us-remote" in lower_full or lower_full in ("us", "usa"):
        return "United States"
    if any(x in lower_full for x in ("united kingdom", " england", " uk")):
        return "United Kingdom"
    if "ireland" in lower_full or "dublin" in lower_full:
        return "Ireland"
    if "canada" in lower_full or "toronto" in lower_full:
        return "Canada"
    if "india" in lower_full or "bengaluru" in lower_full or "bangalore" in lower_full:
        return "India"
    if "singapore" in lower_full:
        return "Singapore"
    if "japan" in lower_full or "tokyo" in lower_full:
        return "Japan"
    if "australia" in lower_full or "sydney" in lower_full:
        return "Australia"
    if "germany" in lower_full or "berlin" in lower_full:
        return "Germany"
    if "france" in lower_full or "paris" in lower_full:
        return "France"
    if "mexico" in lower_full:
        return "Mexico"
    if "north america" in lower_full:
        return "United States"

    return None


def _parse_city_state(segment: str, country: str | None) -> tuple[str | None, str | None]:
    if "," not in segment:
        return segment if segment else None, None

    parts = [p.strip() for p in segment.split(",")]
    city = parts[0]
    second = parts[1] if len(parts) > 1 else None

    if not second:
        return city, None

    second_lower = second.lower()
    if len(second) == 2 and second_lower in US_STATES:
        return city, second.upper()

    if second_lower in _COUNTRY_LOWER:
        return city, None

    # "London, England" → city=London, country handled separately
    if second_lower in ("england", "scotland", "wales"):
        return city, None

    # "San Francisco, California" or "New York, New York"
    if country == "United States" and len(second) > 2:
        return city, None

    return city, second
