from __future__ import annotations

import re


HARD_BLOCKER_SIGNALS = {
    "qualified_lawyer_only": "Qualified-lawyer requirement",
    "restricted_work_authorization": "Work-authorisation restriction",
    "outside_target_geography": "Outside target geography",
    "us_only": "US-only role",
    "expired": "Application appears expired",
}

SOFT_GAP_SIGNALS = {
    "advanced_role": "Role appears more senior than the target career stage",
    "qualified_professional_title": "Title suggests a qualified professional role",
}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _lower(value: object) -> str:
    return _clean(value).lower()


def _reason_signals(item: dict) -> set[str]:
    return {
        str(reason.get("signal", ""))
        for reason in item.get("reasons", [])
        if reason.get("signal")
    }


def _append_unique(target: list[str], value: str) -> None:
    if value and value not in target:
        target.append(value)


def _domain_fit(item: dict, profile: dict) -> tuple[int, list[str]]:
    signals = _reason_signals(item)
    weights = profile.get("target_domains", {}) or {}
    matched: list[tuple[str, int]] = []
    for signal, weight in weights.items():
        if signal in signals:
            matched.append((signal, int(weight)))

    matched.sort(key=lambda pair: pair[1], reverse=True)
    points = min(sum(weight for _, weight in matched), 38)
    reasons = [f"Strong {signal.replace('_', ' ')} relevance" for signal, _ in matched[:3]]
    return points, reasons


def _type_fit(item: dict, profile: dict) -> tuple[int, str]:
    opportunity_type = _clean(item.get("opportunity_type"))
    weights = profile.get("preferred_types", {}) or {}
    points = int(weights.get(opportunity_type, 0))
    if not points:
        return 0, ""
    return points, f"{opportunity_type} matches the target career stage"


def _location_fit(item: dict) -> tuple[int, str]:
    location = _lower(item.get("location"))
    work_model = _lower(item.get("work_model"))
    if "berlin" in location:
        return 12, "Berlin-based"
    if "remote" in work_model or "remote" in location:
        return 10, "Remote-friendly"
    if "germany" in location or "deutschland" in location:
        return 8, "Germany-based"
    if any(term in location for term in ("europe", "eu", "european union")):
        return 6, "European location"
    return 0, ""


def _language_fit(item: dict, profile: dict) -> tuple[int, list[str], list[str]]:
    required = [str(value) for value in item.get("languages", []) if value]
    known = {str(value).lower() for value in profile.get("languages", [])}
    if not required:
        return 0, [], []

    reasons: list[str] = []
    gaps: list[str] = []
    points = 0
    for language in required:
        if language.lower() in known:
            points += 4
            reasons.append(f"Meets {language} language signal")
        else:
            points -= 12
            gaps.append(f"Check required {language} proficiency")
    return max(points, -24), reasons, gaps


def _eligibility_fit(item: dict, profile: dict) -> tuple[int, list[str], list[str], list[str]]:
    eligibility = {str(value) for value in item.get("eligibility", [])}
    education = profile.get("education", {}) or {}
    points = 0
    reasons: list[str] = []
    gaps: list[str] = []
    blockers: list[str] = []

    if "Current law students" in eligibility and education.get("law_student"):
        points += 16
        reasons.append("Explicitly open to current law students")
    elif "Current students" in eligibility and education.get("law_student"):
        points += 12
        reasons.append("Explicitly open to current students")

    if "Recent graduates" in eligibility:
        points += 2
        gaps.append("Recent-graduate wording appears; verify current-student eligibility")

    if "Rechtsreferendar:innen" in eligibility:
        if education.get("first_state_exam"):
            points += 5
            reasons.append("Rechtsreferendariat eligibility is compatible")
        else:
            points -= 8
            gaps.append("Rechtsreferendariat is mentioned; verify whether a student track is available")

    if "First State Exam" in eligibility and not education.get("first_state_exam"):
        points -= 35
        blockers.append("First State Exam appears required")

    if "Bar admission required" in eligibility and not education.get("bar_admission"):
        points -= 60
        blockers.append("Bar admission appears required")

    if "Degree required" in eligibility:
        points -= 10
        gaps.append("Completed degree may be required")

    return points, reasons, gaps, blockers


def _work_authorization_fit(item: dict) -> tuple[int, list[str]]:
    text = _lower(item.get("work_authorization"))
    if not text:
        return 0, []

    restricted_markers = (
        "united states",
        "u.s.",
        "usa",
        "without sponsorship",
        "no visa sponsorship",
        "cannot sponsor",
        "must be authorized to work",
        "right to work in the uk",
        "right to work in the united kingdom",
    )
    if any(marker in text for marker in restricted_markers):
        return -45, [f"Work-authorisation restriction: {_clean(item.get('work_authorization'))}"]
    return -6, [f"Verify work-authorisation wording: {_clean(item.get('work_authorization'))}"]


def _seniority_and_status(item: dict) -> tuple[int, list[str], list[str]]:
    signals = _reason_signals(item)
    gaps: list[str] = []
    blockers: list[str] = []
    points = 0

    for signal, label in HARD_BLOCKER_SIGNALS.items():
        if signal in signals:
            blockers.append(label)
            points -= 50

    for signal, label in SOFT_GAP_SIGNALS.items():
        if signal in signals:
            gaps.append(label)
            points -= 18

    if item.get("deadline_status") == "expired" and "Application appears expired" not in blockers:
        blockers.append("Application appears expired")
        points -= 50

    return points, gaps, blockers


def _experience_fit(item: dict, profile: dict) -> tuple[int, list[str]]:
    text = " ".join(
        [
            _clean(item.get("title")),
            _clean(item.get("role_context")),
            _clean(item.get("description"))[:1500],
        ]
    ).lower()
    experience = [str(value) for value in profile.get("experience_signals", [])]
    matches = []
    for signal in experience:
        pattern = re.escape(signal.lower()).replace(r"\ ", r"[\s-]+")
        if re.search(pattern, text):
            matches.append(signal)

    points = min(len(matches) * 3, 12)
    reasons = [f"Relevant experience overlap: {signal}" for signal in matches[:3]]
    return points, reasons


def assess_fit(item: dict, profile: dict) -> dict:
    """Add a transparent personal-fit assessment to an enriched opportunity.

    This is deliberately deterministic and explainable. It does not decide whether
    someone should apply; it surfaces fit signals, gaps and blockers so the user can.
    """
    assessed = dict(item)
    score = 32
    reasons: list[str] = []
    gaps: list[str] = []
    blockers: list[str] = []

    domain_points, domain_reasons = _domain_fit(item, profile)
    score += domain_points
    reasons.extend(domain_reasons)

    type_points, type_reason = _type_fit(item, profile)
    score += type_points
    _append_unique(reasons, type_reason)

    location_points, location_reason = _location_fit(item)
    score += location_points
    _append_unique(reasons, location_reason)

    language_points, language_reasons, language_gaps = _language_fit(item, profile)
    score += language_points
    reasons.extend(language_reasons)
    gaps.extend(language_gaps)

    eligibility_points, eligibility_reasons, eligibility_gaps, eligibility_blockers = _eligibility_fit(item, profile)
    score += eligibility_points
    reasons.extend(eligibility_reasons)
    gaps.extend(eligibility_gaps)
    blockers.extend(eligibility_blockers)

    work_auth_points, work_auth_notes = _work_authorization_fit(item)
    score += work_auth_points
    if work_auth_points <= -40:
        blockers.extend(work_auth_notes)
    else:
        gaps.extend(work_auth_notes)

    status_points, status_gaps, status_blockers = _seniority_and_status(item)
    score += status_points
    gaps.extend(status_gaps)
    blockers.extend(status_blockers)

    compensation_status = _clean(item.get("compensation_status"))
    if compensation_status == "paid":
        score += 4
        _append_unique(reasons, "Explicit compensation signal")
    elif compensation_status == "unpaid" and "full-time" in _lower(item.get("commitment")):
        score -= 18
        _append_unique(gaps, "Unpaid full-time commitment")

    # Experience overlap is useful context, but explicit eligibility and compensation
    # are more decision-relevant and should remain visible before generic overlap.
    experience_points, experience_reasons = _experience_fit(item, profile)
    score += experience_points
    reasons.extend(experience_reasons)

    # Deduplicate while preserving order. Keep enough reasons to surface eligibility
    # and pay signals without turning the UI back into a wall of text.
    reasons = list(dict.fromkeys(reasons))[:8]
    gaps = list(dict.fromkeys(gaps))[:6]
    blockers = list(dict.fromkeys(blockers))[:4]

    score = max(0, min(100, score))
    thresholds = profile.get("fit_thresholds", {}) or {}
    strong_threshold = int(thresholds.get("strong_fit", 75))
    stretch_threshold = int(thresholds.get("stretch", 55))

    if blockers:
        label = "Probably skip"
        score = min(score, stretch_threshold - 1)
    elif score >= strong_threshold:
        label = "Strong fit"
    elif score >= stretch_threshold:
        label = "Stretch"
    else:
        label = "Probably skip"

    assessed.update(
        {
            "fit_score": score,
            "fit_label": label,
            "fit_reasons": reasons,
            "fit_gaps": gaps,
            "fit_blockers": blockers,
            "fit_version": "0.4",
        }
    )
    return assessed
