from __future__ import annotations


def reconcile_enrichment_score(item: dict, config: dict) -> dict:
    """Keep explainable ranking consistent with structured enrichment fields.

    The legacy scorer intentionally searches the full advert for broad discovery
    signals. Once v0.3 has extracted structured facts, those facts should win when
    they conflict with incidental wording in the body (for example a Working Student
    advert that also mentions a separate trainee track).
    """
    adjusted = dict(item)
    reasons = [dict(reason) for reason in adjusted.get("reasons", [])]
    score = int(adjusted.get("score", 0))
    positive_weights = config.get("positive_signals", {}) or {}

    compensation_status = str(adjusted.get("compensation_status", ""))
    paid_reasons = [reason for reason in reasons if reason.get("signal") == "paid"]
    paid_points = sum(int(reason.get("points", 0)) for reason in paid_reasons)

    if compensation_status and compensation_status != "paid" and paid_points:
        score -= paid_points
        reasons = [reason for reason in reasons if reason.get("signal") != "paid"]
    elif compensation_status == "paid" and not paid_reasons:
        weight = int(positive_weights.get("paid", 0))
        if weight:
            score += weight
            reasons.append({"signal": "paid", "points": weight})

    # Fellowship / traineeship are legacy free-text signals. Structured role type is
    # more reliable because the enrichment layer gives the actual title precedence.
    opportunity_type = str(adjusted.get("opportunity_type", ""))
    expected_role_signal = {
        "Fellowship": "fellowship",
        "Traineeship": "traineeship",
    }.get(opportunity_type)

    for signal in ("fellowship", "traineeship"):
        matching = [reason for reason in reasons if reason.get("signal") == signal]
        points = sum(int(reason.get("points", 0)) for reason in matching)
        if signal != expected_role_signal and points:
            score -= points
            reasons = [reason for reason in reasons if reason.get("signal") != signal]

    if expected_role_signal and not any(
        reason.get("signal") == expected_role_signal for reason in reasons
    ):
        weight = int(positive_weights.get(expected_role_signal, 0))
        if weight:
            score += weight
            reasons.append({"signal": expected_role_signal, "points": weight})

    if adjusted.get("deadline_status") == "expired":
        has_expired = any(reason.get("signal") == "expired" for reason in reasons)
        if not has_expired:
            penalty = int(config.get("negative_signals", {}).get("expired", -100))
            score += penalty
            reasons.append({"signal": "expired", "points": penalty})

    adjusted["score"] = score
    adjusted["reasons"] = sorted(reasons, key=lambda r: abs(int(r.get("points", 0))), reverse=True)
    return adjusted
