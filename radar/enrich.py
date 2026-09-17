from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable


WS_RE = re.compile(r"\s+")
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December|"
    "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
DATE_PATTERN = rf"(?:\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[./]\d{{1,2}}[./]\d{{2,4}}|\d{{1,2}}\s+(?:{MONTHS})\s+\d{{4}}|(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?[,]?\s+\d{{4}})"


def _clean(value: object) -> str:
    return WS_RE.sub(" ", str(value or "")).strip()


def _first_match(text: str, patterns: Iterable[str], flags: int = re.IGNORECASE) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=flags)
        if match:
            value = match.group(1) if match.lastindex else match.group(0)
            return _clean(value).strip(" .,:;–—-")
    return ""


def _sentence_with(text: str, pattern: str, max_chars: int = 220) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = max(text.rfind(". ", 0, match.start()) + 2, 0)
    end = text.find(". ", match.end())
    if end < 0:
        end = min(len(text), start + max_chars)
    sentence = _clean(text[start:end])
    return sentence[:max_chars].rstrip()


def extract_opportunity_type(title: str, text: str, source_type: str = "") -> str:
    haystack = f"{title} {text[:700]}"
    patterns = [
        ("Fellowship", r"\bfellow(?:ship)?\b"),
        ("Traineeship", r"\btrainee(?:ship)?\b"),
        ("Internship", r"\bintern(?:ship)?\b"),
        ("Working student", r"\bworking student\b|\bwerkstudent(?:in|:in|en)?\b"),
        ("Graduate programme", r"\bgraduate (?:programme|program|scheme)\b"),
        ("Junior professional programme", r"\b(?:junior|young) professional(?:s)? (?:programme|program)\b"),
        ("Volunteer", r"\bvolunteer(?:ing)?\b|\bpro[ -]?bono\b"),
        ("Research role", r"\bresearch (?:assistant|associate|fellow|intern|trainee)\b"),
    ]
    if source_type == "open_source":
        return "Open-source contribution"
    for label, pattern in patterns:
        if re.search(pattern, haystack, flags=re.IGNORECASE):
            return label
    return "Early-career role"


def extract_work_model(location: str, text: str) -> str:
    combined = f"{location} {text[:1400]}".lower()
    has_remote = bool(re.search(r"\b(remote|remote-first|fully remote|work from home|virtual)\b", combined))
    has_hybrid = bool(re.search(r"\bhybrid\b", combined))
    has_onsite = bool(re.search(r"\b(on[- ]?site|onsite|in[- ]office|office-based)\b", combined))
    if has_remote and has_hybrid:
        return "Remote / hybrid"
    if has_hybrid:
        return "Hybrid"
    if has_remote:
        return "Remote"
    if has_onsite:
        return "On-site"
    return "Unspecified"


def extract_compensation(text: str) -> tuple[str, str]:
    lower = text.lower()
    unpaid = _first_match(
        text,
        [
            r"\b(unpaid(?: internship| fellowship| role)?)\b",
            r"\b(without (?:pay|compensation|remuneration))\b",
            r"\b(no (?:salary|compensation|remuneration|stipend))\b",
        ],
    )
    if unpaid:
        return "unpaid", unpaid

    funding = _first_match(
        text,
        [
            r"\b(funding (?:may be|is)?\s*(?:available|possible))\b",
            r"\b(receiv(?:e|ing) funding)\b",
            r"\b(external funding)\b",
            r"\b(academic credits? and/or receiving funding)\b",
        ],
    )
    if funding:
        return "funding_possible", funding

    money = _first_match(
        text,
        [
            r"((?:€|£|\$)\s?[\d,.]+(?:\s*(?:-|–|to)\s*(?:€|£|\$)?\s?[\d,.]+)?(?:\s*(?:per|/)\s*(?:hour|week|month|year))?)",
            r"([\d,.]+\s?(?:EUR|USD|GBP)(?:\s*(?:-|–|to)\s*[\d,.]+\s?(?:EUR|USD|GBP))?(?:\s*(?:per|/)\s*(?:hour|week|month|year))?)",
            r"\b(stipend (?:of )?[^.;]{0,80}(?:€|£|\$|EUR|USD|GBP)[^.;]{0,40})",
            r"\b(salary (?:of |range )?[^.;]{0,100}(?:€|£|\$|EUR|USD|GBP)[^.;]{0,40})",
        ],
    )
    if money:
        return "paid", money

    paid_label = _first_match(
        text,
        [
            r"\b(paid (?:internship|fellowship|traineeship|position|role))\b",
            r"\b(remunerated (?:internship|fellowship|traineeship|position|role))\b",
            r"\b(monthly (?:stipend|allowance))\b",
        ],
    )
    if paid_label:
        return "paid", paid_label

    # Avoid treating generic words such as "compensation" or "grant" as proof of pay.
    return "unknown", ""


def extract_duration(text: str) -> str:
    unit = r"(?:weeks?|months?|years?)"
    return _first_match(
        text,
        [
            rf"\bduration (?:of|is|:)\s*((?:\d+\s*(?:-|–|to)\s*)?\d+\s*{unit})",
            rf"\b((?:\d+\s*(?:-|–|to)\s*)?\d+\s*{unit})\s+(?:fellowship|internship|traineeship|programme|program|placement)\b",
            rf"\b(?:for|minimum of|minimum|at least)\s+((?:\d+\s*(?:-|–|to)\s*)?\d+\s*{unit})\b",
            rf"\b((?:\d+\s*(?:-|–|to)\s*)?\d+)[ -](week|month|year)(?:-long)?\b",
            rf"\b(?:dauer|laufzeit)\s*:?(?: von)?\s*((?:\d+\s*(?:-|–|bis)\s*)?\d+\s*(?:wochen?|monate?|jahre?))",
        ],
    )


def extract_commitment(text: str, existing: str = "") -> str:
    if existing:
        return _clean(existing)
    hour_match = _first_match(
        text,
        [
            r"\b((?:\d{1,2}\s*(?:-|–|to)\s*)?\d{1,2}\s*(?:hours?|hrs?|h)\s*(?:per|/)\s*week)\b",
            r"\b((?:\d{1,2}\s*(?:-|–|bis)\s*)?\d{1,2}\s*(?:stunden?)\s*(?:pro|/)\s*woche)\b",
        ],
    )
    mode = ""
    if re.search(r"\bfull[- ]time\b|\bvollzeit\b", text, flags=re.IGNORECASE):
        mode = "Full-time"
    elif re.search(r"\bpart[- ]time\b|\bteilzeit\b", text, flags=re.IGNORECASE):
        mode = "Part-time"
    if mode and hour_match:
        return f"{mode} · {hour_match}"
    return mode or hour_match


def extract_deadline(item: dict, text: str) -> str:
    existing = _clean(item.get("deadline"))
    if existing:
        return existing
    return _first_match(
        text,
        [
            rf"\b(?:application deadline|deadline|apply by|applications? close(?:s)?(?: on)?)\s*:?[ ]*({DATE_PATTERN})",
            rf"\b(?:bewerbungsfrist|bewerben bis|bewerbungsschluss)(?: endet)?(?: am)?\s*:?[ ]*({DATE_PATTERN})",
        ],
    )


def extract_start_date(text: str) -> str:
    return _first_match(
        text,
        [
            rf"\b(?:start date|starting|starts|start)\s*:?(?: on)?\s*({DATE_PATTERN})",
            rf"\b(?:beginn|start)(?: ist| am)?\s*:?[ ]*({DATE_PATTERN})",
        ],
    )


def extract_languages(title: str, text: str) -> list[str]:
    languages = [
        "English", "German", "French", "Spanish", "Italian", "Dutch", "Portuguese",
        "Arabic", "Albanian", "Polish", "Romanian", "Ukrainian", "Russian",
    ]
    combined = f"{title}. {text}"
    found: list[str] = []
    for language in languages:
        contextual = [
            rf"\b{language}[- ]speaking\b",
            rf"\b(?:fluent|fluency|proficient|proficiency|native|excellent|strong|working knowledge)\b[^.;]{{0,55}}\b{language}\b",
            rf"\b{language}\b[^.;]{{0,55}}\b(?:required|preferred|fluency|proficiency|speaking|spoken|written|language)\b",
        ]
        if any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in contextual):
            found.append(language)
    return found


def extract_eligibility(title: str, text: str) -> list[str]:
    combined = f"{title}. {text}"
    rules = [
        ("Current law students", r"\bcurrent law students?\b|\blaw students?\b"),
        ("Current students", r"\bcurrently enrolled students?\b|\bcurrent students?\b|\benrolled (?:university )?students?\b"),
        ("Recent graduates", r"\brecent (?:law school )?graduates?\b|\brecently graduated\b"),
        ("Rechtsreferendar:innen", r"\brechtsreferendar(?:in|:in|innen|:innen)?\b|\brechtsreferendariat\b"),
        ("First State Exam", r"\b(?:first|erstes?) (?:legal )?state exam\b|\berstes staatsexamen\b|\berste juristische prüfung\b"),
        ("Degree required", r"\b(?:bachelor'?s?|master'?s?|university) degree required\b|\brequires? (?:a )?(?:bachelor'?s?|master'?s?) degree\b"),
        ("Bar admission required", r"\bbar admission required\b|\bmust be (?:a )?qualified lawyer\b"),
    ]
    return [label for label, pattern in rules if re.search(pattern, combined, flags=re.IGNORECASE)]


def extract_work_authorization(text: str) -> str:
    return _sentence_with(
        text,
        r"\b(?:authori[sz]ed to work|right to work|work permit|visa sponsorship|sponsorship (?:is|will|cannot|can)|must reside|must be based|must be located)\b",
    )


def _parse_deadline(value: str) -> datetime | None:
    raw = _clean(value).replace("Sept ", "Sep ")
    if not raw:
        return None
    raw = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", raw, flags=re.IGNORECASE)
    formats = [
        "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d/%m/%y",
        "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y",
        "%B %d %Y", "%b %d %Y",
    ]
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def deadline_status(deadline: str, now: datetime | None = None) -> str:
    parsed = _parse_deadline(deadline)
    if not parsed:
        return "unknown"
    current = now or datetime.now(timezone.utc)
    days = (parsed.date() - current.date()).days
    if days < 0:
        return "expired"
    if days <= 7:
        return "closing_soon"
    return "open"


def enrich_opportunity(item: dict) -> dict:
    enriched = dict(item)
    title = _clean(enriched.get("title"))
    description = _clean(enriched.get("description"))
    location = _clean(enriched.get("location"))
    source_type = _clean(enriched.get("source_type"))

    compensation_status, compensation = extract_compensation(description)
    commitment = extract_commitment(description, _clean(enriched.get("commitment")))
    deadline = extract_deadline(enriched, description)

    enriched.update(
        {
            "opportunity_type": extract_opportunity_type(title, description, source_type),
            "work_model": extract_work_model(location, description),
            "compensation_status": compensation_status,
            "compensation": compensation,
            "duration": extract_duration(description),
            "commitment": commitment,
            "deadline": deadline,
            "deadline_status": deadline_status(deadline),
            "start_date": extract_start_date(description),
            "languages": extract_languages(title, description),
            "eligibility": extract_eligibility(title, description),
            "work_authorization": extract_work_authorization(description),
            "enrichment_version": "0.3",
        }
    )
    return enriched
