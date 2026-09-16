from __future__ import annotations

import re
from urllib.parse import urlparse


SIGNAL_PATTERNS = {
    "legal": [r"\blegal\b", r"\blaw\b"],
    "legal_tech": [r"legal tech", r"legal technology", r"legal engineer", r"computational law"],
    "legal_operations": [r"legal operations", r"contract management", r"document governance"],
    "privacy": [r"privacy", r"data protection", r"gdpr"],
    "compliance": [r"compliance", r"regulatory"],
    "ai_governance": [r"ai governance", r"artificial intelligence", r"ai act"],
    "policy": [r"\bpolicy\b", r"public policy"],
    "governance": [r"governance", r"rule of law"],
    "human_rights": [r"human rights", r"refugee", r"asylum"],
    "international_law": [r"international law", r"humanitarian law", r"international criminal"],
    "research_writing": [r"research", r"writing", r"drafting", r"publication", r"policy brief"],
    "published_output": [r"published", r"publication", r"byline", r"author"],
    "international": [r"international", r"global", r"worldwide"],
    "remote": [r"remote", r"work from home", r"virtual"],
    "berlin": [r"berlin"],
    "paid": [r"paid", r"salary", r"stipend", r"grant", r"€", r"£", r"\$"],
    "fellowship": [r"fellowship", r"\bfellow\b"],
    "traineeship": [r"traineeship", r"\btrainee\b", r"graduate programme", r"graduate program"],
    "leadership": [r"leadership", r"lead a", r"manage", r"mentor"],
}

OPPORTUNITY_PATTERNS = [
    r"internship",
    r"\bintern\b",
    r"traineeship",
    r"\btrainee\b",
    r"fellowship",
    r"\bfellow\b",
    r"graduate programme",
    r"graduate program",
    r"young professional",
    r"junior professional",
    r"working student",
    r"werkstudent",
    r"volunteer",
    r"pro[ -]?bono",
    r"research assistant",
    r"research associate",
    r"researcher vacancy",
    r"policy analyst",
    r"policy associate",
    r"legal analyst",
    r"legal researcher",
    r"legal assistant",
    r"legal associate",
    r"open call",
    r"applications? (?:are )?open",
    r"apply (?:now|by|before)",
    r"vacanc(?:y|ies)",
    r"we(?:'re| are) hiring",
    r"contribution opportunity",
    r"help wanted",
    r"good first issue",
    r"working group",
]

NEGATIVE_PATTERNS = {
    "event_only": [r"event volunteer", r"event helper"],
    "membership_only": [r"membership only", r"join our community"],
    "us_only": [r"u\.s\. residents only", r"us residents only", r"must reside in the united states"],
    "qualified_lawyer_only": [r"qualified lawyer required", r"bar admission required"],
    "expired": [r"applications closed", r"deadline passed", r"no longer accepting applications"],
    "unpaid_full_time": [r"unpaid"],
}

# These title penalties are applied only when the title does not itself contain an
# internship/trainee/fellow/junior-style signal. This prevents a normal senior job
# from outranking an actual early-career opportunity merely because its description
# contains many relevant legal and governance keywords.
ADVANCED_TITLE_PATTERNS = [
    r"\bsenior\b",
    r"\bdirector\b",
    r"\bprincipal\b",
    r"\bvice president\b",
    r"\bvp\b",
    r"\bhead of\b",
    r"\bmanager\b",
    r"\blead counsel\b",
]

QUALIFIED_PROFESSIONAL_TITLE_PATTERNS = [
    r"\bcounsel\b",
    r"\battorney\b",
    r"\bsolicitor\b",
    r"\blawyer\b",
]

REFERENCE_HOSTS = {
    "wikipedia.org",
    "en.wikipedia.org",
    "en.m.wikipedia.org",
    "merriam-webster.com",
    "dictionary.cambridge.org",
    "thefreedictionary.com",
    "dictionary.com",
    "vocabulary.com",
    "researchgate.net",
}


def _matches(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def score_opportunity(item: dict, config: dict) -> dict:
    # Score only evidence supplied by the result itself. Never score the search query.
    text = " ".join(str(item.get(key, "")) for key in ("title", "description"))
    title = str(item.get("title", ""))
    url = str(item.get("url", ""))
    structured = bool(item.get("structured_opportunity"))

    score = 0
    reasons: list[dict] = []

    if _host(url) in REFERENCE_HOSTS:
        score -= 100
        reasons.append({"signal": "reference_page", "points": -100})

    looks_like_opportunity = _matches(text, OPPORTUNITY_PATTERNS)
    title_has_opportunity_signal = _matches(title, OPPORTUNITY_PATTERNS)

    if structured:
        weight = int(config.get("positive_signals", {}).get("structured_source", 10))
        score += weight
        reasons.append({"signal": "structured_source", "points": weight})
    elif not looks_like_opportunity:
        score -= 100
        reasons.append({"signal": "not_an_opportunity", "points": -100})

    if title_has_opportunity_signal:
        score += 12
        reasons.append({"signal": "opportunity_in_title", "points": 12})

    if not title_has_opportunity_signal:
        if _matches(title, ADVANCED_TITLE_PATTERNS):
            weight = int(config.get("negative_signals", {}).get("advanced_role", -50))
            score += weight
            reasons.append({"signal": "advanced_role", "points": weight})
        if _matches(title, QUALIFIED_PROFESSIONAL_TITLE_PATTERNS):
            weight = int(
                config.get("negative_signals", {}).get("qualified_professional_title", -35)
            )
            score += weight
            reasons.append({"signal": "qualified_professional_title", "points": weight})

    for signal, patterns in SIGNAL_PATTERNS.items():
        if _matches(text, patterns):
            weight = int(config.get("positive_signals", {}).get(signal, 0))
            if weight:
                score += weight
                reasons.append({"signal": signal, "points": weight})

    for signal, patterns in NEGATIVE_PATTERNS.items():
        if _matches(text, patterns):
            weight = int(config.get("negative_signals", {}).get(signal, 0))
            if weight:
                score += weight
                reasons.append({"signal": signal, "points": weight})

    item = dict(item)
    item["score"] = score
    item["reasons"] = sorted(reasons, key=lambda r: abs(r["points"]), reverse=True)
    return item
