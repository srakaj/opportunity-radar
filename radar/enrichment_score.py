from __future__ import annotations


def reconcile_enrichment_score(item: dict, config: dict) -> dict:
    """Keep explainable ranking consistent with structured enrichment fields.

    The legacy scorer uses broad text patterns such as "grant" and "stipend" for the
    paid signal. Once v0.3 has extracted compensation explicitly, prefer the
    structured result and remove false paid boosts such as "funding may be available".
    Also apply the configured expiry penalty when a parseable deadline has passed.
    """
    adjusted = dict(item)
    reasons = [dict(reason) for reason in adjusted.get("reasons", [])]
    score = int(adjusted.get("score", 0))

    compensation_status = str(adjusted.get("compensation_status", ""))
    paid_reasons = [reason for reason in reasons if reason.get("signal") == "paid"]
    paid_points = sum(int(reason.get("points", 0)) for reason in paid_reasons)

    if compensation_status and compensation_status != "paid" and paid_points:
        score -= paid_points
        reasons = [reason for reason in reasons if reason.get("signal") != "paid"]
    elif compensation_status == "paid" and not paid_reasons:
        weight = int(config.get("positive_signals", {}).get("paid", 0))
        if weight:
            score += weight
            reasons.append({"signal": "paid", "points": weight})

    if adjusted.get("deadline_status") == "expired":
        has_expired = any(reason.get("signal") == "expired" for reason in reasons)
        if not has_expired:
            penalty = int(config.get("negative_signals", {}).get("expired", -100))
            score += penalty
            reasons.append({"signal": "expired", "points": penalty})

    adjusted["score"] = score
    adjusted["reasons"] = sorted(reasons, key=lambda r: abs(int(r.get("points", 0))), reverse=True)
    return adjusted
