from __future__ import annotations

import re


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
    "fellowship": [r"fellowship", r"fellow"],
    "traineeship": [r"traineeship", r"trainee", r"graduate programme", r"graduate program"],
    "leadership": [r"leadership", r"lead a", r"manage", r"mentor"],
}

NEGATIVE_PATTERNS = {
    "event_only": [r"event volunteer", r"event helper"],
    "membership_only": [r"membership only", r"join our community"],
    "us_only": [r"u\.s\. residents only", r"us residents only", r"must reside in the united states"],
    "qualified_lawyer_only": [r"qualified lawyer required", r"bar admission required"],
    "expired": [r"applications closed", r"deadline passed", r"no longer accepting applications"],
    "unpaid_full_time": [r"unpaid"],
}


def _matches(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def score_opportunity(item: dict, config: dict) -> dict:
    text = " ".join(
        str(item.get(key, ""))
        for key in ("title", "description", "query", "source")
    )

    score = 0
    reasons: list[dict] = []

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
