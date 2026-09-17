from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


BERLIN = ZoneInfo("Europe/Berlin")
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December|"
    "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
DATE_PATTERN = rf"(?:\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[./]\d{{1,2}}[./]\d{{2,4}}|\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}}|(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?[,]?\s+\d{{4}})"
DEADLINE_MARKERS = (
    r"application deadline", r"deadline", r"apply by", r"applications? close(?:s|d)?",
    r"applications? (?:are )?(?:accepted )?until", r"no later than",
    r"bewerbungsfrist", r"bewerben bis", r"bewerbungsschluss",
)

# Important: test the 12-hour form before bare HH:MM. Otherwise "6:00 PM"
# is consumed as 06:00 before the AM/PM suffix can be interpreted.
TIME_RE = re.compile(
    r"\b(?:(?P<h12>0?[1-9]|1[0-2])(?::(?P<m12>[0-5]\d))?\s*(?P<ampm>a\.?m\.?|p\.?m\.?)|"
    r"(?P<h24>[01]?\d|2[0-3]):(?P<m24>[0-5]\d)|"
    r"(?P<word>midnight|noon))\b",
    re.IGNORECASE,
)
TZ_TOKEN_RE = re.compile(
    r"\b(UTC|GMT|CET|CEST|BST|ET|EST|EDT|CT|CST|CDT|MT|MST|MDT|PT|PST|PDT)\b",
    re.IGNORECASE,
)

EXPLICIT_FIXED_TZ = {
    "UTC": timezone.utc, "GMT": timezone.utc,
    "CET": timezone(timedelta(hours=1)), "CEST": timezone(timedelta(hours=2)),
    "BST": timezone(timedelta(hours=1)),
    "EST": timezone(timedelta(hours=-5)), "EDT": timezone(timedelta(hours=-4)),
    "CST": timezone(timedelta(hours=-6)), "CDT": timezone(timedelta(hours=-5)),
    "MST": timezone(timedelta(hours=-7)), "MDT": timezone(timedelta(hours=-6)),
    "PST": timezone(timedelta(hours=-8)), "PDT": timezone(timedelta(hours=-7)),
}
EXPLICIT_REGIONAL_TZ = {
    "ET": "America/New_York", "CT": "America/Chicago",
    "MT": "America/Denver", "PT": "America/Los_Angeles",
}

CITY_TIMEZONES = {
    "berlin": "Europe/Berlin", "munich": "Europe/Berlin", "münchen": "Europe/Berlin",
    "hamburg": "Europe/Berlin", "frankfurt": "Europe/Berlin", "cologne": "Europe/Berlin",
    "köln": "Europe/Berlin", "london": "Europe/London", "paris": "Europe/Paris",
    "zurich": "Europe/Zurich", "zürich": "Europe/Zurich", "vienna": "Europe/Vienna",
    "wien": "Europe/Vienna", "brussels": "Europe/Brussels", "amsterdam": "Europe/Amsterdam",
    "madrid": "Europe/Madrid", "barcelona": "Europe/Madrid", "rome": "Europe/Rome",
    "milan": "Europe/Rome", "warsaw": "Europe/Warsaw",
    "new york": "America/New_York", "boston": "America/New_York",
    "washington, dc": "America/New_York", "washington dc": "America/New_York",
    "miami": "America/New_York", "atlanta": "America/New_York",
    "chicago": "America/Chicago", "dallas": "America/Chicago", "houston": "America/Chicago",
    "austin": "America/Chicago", "denver": "America/Denver", "phoenix": "America/Phoenix",
    "los angeles": "America/Los_Angeles", "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles", "portland": "America/Los_Angeles",
    "vancouver": "America/Vancouver", "toronto": "America/Toronto", "montreal": "America/Toronto",
    "montréal": "America/Toronto", "honolulu": "Pacific/Honolulu", "anchorage": "America/Anchorage",
}
US_STATE_TIMEZONES = {
    "CA": "America/Los_Angeles", "WA": "America/Los_Angeles",
    "NY": "America/New_York", "NJ": "America/New_York", "MA": "America/New_York",
    "PA": "America/New_York", "MD": "America/New_York", "VA": "America/New_York",
    "NC": "America/New_York", "SC": "America/New_York", "GA": "America/New_York",
    "IL": "America/Chicago", "TX": "America/Chicago", "WI": "America/Chicago", "MN": "America/Chicago",
    "CO": "America/Denver", "UT": "America/Denver", "AZ": "America/Phoenix",
    "AK": "America/Anchorage", "HI": "Pacific/Honolulu",
}
COUNTRY_TIMEZONES = {
    "germany": "Europe/Berlin", "deutschland": "Europe/Berlin",
    "united kingdom": "Europe/London", "uk": "Europe/London", "france": "Europe/Paris",
    "switzerland": "Europe/Zurich", "austria": "Europe/Vienna", "belgium": "Europe/Brussels",
    "netherlands": "Europe/Amsterdam", "spain": "Europe/Madrid", "italy": "Europe/Rome",
    "poland": "Europe/Warsaw",
}


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _parse_date(raw: str) -> datetime | None:
    value = _clean(raw).replace("Sept ", "Sep ")
    value = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", value, flags=re.IGNORECASE)
    for fmt in (
        "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d/%m/%y",
        "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _extract_deadline_context(description: str, existing_deadline: str = "") -> tuple[str, str]:
    text = _clean(description)
    marker_re = re.compile("(?:" + "|".join(DEADLINE_MARKERS) + ")", re.IGNORECASE)
    for marker in marker_re.finditer(text):
        context = text[max(0, marker.start() - 20): min(len(text), marker.end() + 180)]
        date_match = re.search(DATE_PATTERN, context, re.IGNORECASE)
        if date_match:
            return context, date_match.group(0)
    if existing_deadline:
        raw = _clean(existing_deadline)
        date_match = re.search(DATE_PATTERN, raw, re.IGNORECASE)
        if date_match:
            return raw, date_match.group(0)
    return "", ""


def _parse_time(context: str) -> tuple[time | None, str]:
    match = TIME_RE.search(context)
    if not match:
        return None, ""
    if match.group("word"):
        word = match.group("word").lower()
        # In an application-deadline context, "until/by midnight" conventionally
        # means the end of the named date. Represent that as 23:59 to avoid the
        # dangerous beginning-of-day interpretation of 00:00.
        return (time(23, 59) if word == "midnight" else time(12, 0)), match.group(0)
    if match.group("h12") is not None:
        hour = int(match.group("h12"))
        minute = int(match.group("m12") or 0)
        ampm = re.sub(r"[^apm]", "", match.group("ampm").lower())
        if ampm.startswith("p") and hour != 12:
            hour += 12
        if ampm.startswith("a") and hour == 12:
            hour = 0
        return time(hour, minute), match.group(0)
    return time(int(match.group("h24")), int(match.group("m24"))), match.group(0)


def _explicit_timezone(context: str):
    match = TZ_TOKEN_RE.search(context)
    if not match:
        return None, ""
    token = match.group(1).upper()
    if token in EXPLICIT_FIXED_TZ:
        return EXPLICIT_FIXED_TZ[token], token
    zone_name = EXPLICIT_REGIONAL_TZ.get(token)
    return (ZoneInfo(zone_name), token) if zone_name else (None, "")


def infer_timezone_from_location(location: str) -> str:
    original = _clean(location)
    value = original.lower()
    if not value or value in {"remote", "worldwide", "global", "anywhere"}:
        return ""
    for city, zone in CITY_TIMEZONES.items():
        if city in value:
            return zone
    state_match = re.search(r",\s*([A-Z]{2})(?:\b|$)", original)
    if state_match and state_match.group(1) in US_STATE_TIMEZONES:
        return US_STATE_TIMEZONES[state_match.group(1)]
    for country, zone in COUNTRY_TIMEZONES.items():
        if country in value:
            return zone
    return ""


def _status(deadline_utc: datetime | None, now: datetime | None = None) -> str:
    if not deadline_utc:
        return "unknown"
    remaining = deadline_utc - (now or datetime.now(timezone.utc))
    if remaining.total_seconds() < 0:
        return "expired"
    if remaining <= timedelta(days=7):
        return "closing_soon"
    return "open"


def enrich_deadline_timezone(item: dict, now: datetime | None = None) -> dict:
    """Normalize deadline timing to Europe/Berlin while preserving uncertainty.

    Confidence values:
    explicit_timezone: time and timezone supplied by source
    location_inferred: time supplied; timezone inferred from opportunity location
    date_only: only a date supplied; 23:59 Europe/Berlin assumed
    timezone_unknown: time supplied but source timezone unknown; treated as Berlin
    """
    enriched = dict(item)
    description = _clean(enriched.get("description"))
    existing_deadline = _clean(enriched.get("deadline"))
    context, raw_date = _extract_deadline_context(description, existing_deadline)
    parsed_date = _parse_date(raw_date)

    if not parsed_date:
        enriched.update({
            "deadline_berlin_iso": "", "deadline_utc_iso": "",
            "deadline_time_confidence": "unknown", "deadline_source_timezone": "",
            "deadline_original": existing_deadline,
        })
        return enriched

    parsed_time, raw_time = _parse_time(context)
    explicit_tz, tz_label = _explicit_timezone(context)

    if parsed_time is None:
        parsed_time = time(23, 59)
        source_tz, source_tz_label, confidence = BERLIN, "Europe/Berlin", "date_only"
    elif explicit_tz is not None:
        source_tz, source_tz_label, confidence = explicit_tz, tz_label, "explicit_timezone"
    else:
        inferred_zone = infer_timezone_from_location(_clean(enriched.get("location")))
        if inferred_zone:
            source_tz, source_tz_label, confidence = ZoneInfo(inferred_zone), inferred_zone, "location_inferred"
        else:
            source_tz, source_tz_label, confidence = BERLIN, "Europe/Berlin (fallback)", "timezone_unknown"

    source_dt = datetime.combine(parsed_date.date(), parsed_time, tzinfo=source_tz)
    berlin_dt = source_dt.astimezone(BERLIN)
    utc_dt = source_dt.astimezone(timezone.utc)

    original_bits = [raw_date]
    if raw_time:
        original_bits.append(raw_time)
    if tz_label:
        original_bits.append(tz_label)

    enriched.update({
        "deadline": raw_date,
        "deadline_berlin_iso": berlin_dt.isoformat(),
        "deadline_utc_iso": utc_dt.isoformat().replace("+00:00", "Z"),
        "deadline_time_confidence": confidence,
        "deadline_source_timezone": source_tz_label,
        "deadline_original": " ".join(original_bits).strip(),
        "deadline_status": _status(utc_dt, now),
        "deadline_time_explicit": bool(raw_time),
        "deadline_timezone_explicit": bool(tz_label),
        "deadline_timezone_version": "0.5.2",
    })
    return enriched
