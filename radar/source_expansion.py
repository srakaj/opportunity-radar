from __future__ import annotations

import html
import re
import unicodedata
from copy import deepcopy
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; OpportunityRadar/0.6; "
        "+https://github.com/srakaj/opportunity-radar)"
    ),
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}

TRACKING_QUERY_KEYS = {
    "source",
    "src",
    "ref",
    "referrer",
    "gh_src",
    "lever-source",
}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _html_to_text(value: Any) -> str:
    raw = html.unescape(_text(value))
    if not raw:
        return ""
    return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)


def _join(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def canonical_url(url: str) -> str:
    """Canonicalise URLs without throwing away query parameters that identify jobs."""
    raw = _text(url)
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
        ]
        path = parsed.path.rstrip("/") or "/"
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                parsed.params,
                urlencode(filtered_query, doseq=True),
                "",
            )
        ).rstrip("?")
    except Exception:
        return raw.split("#", 1)[0].rstrip("/")


def _normalise_identity(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value)).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def opportunity_identity(item: dict) -> str:
    """Build a stable role identity so duplicates from several discovery paths collapse."""
    title = _normalise_identity(item.get("title"))
    organisation = _normalise_identity(item.get("organization"))
    location = _normalise_identity(item.get("location"))
    if title and organisation:
        return f"role::{organisation}::{title}::{location or '*'}"
    return f"url::{canonical_url(_text(item.get('url')))}"


def _source_descriptor(item: dict) -> dict:
    return {
        "source": _text(item.get("source")),
        "url": _text(item.get("url")),
        "quality": _text(item.get("source_quality")),
        "priority": int(item.get("source_priority") or 0),
    }


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def merge_opportunities(existing: dict, candidate: dict) -> dict:
    """Merge duplicate opportunities while keeping the highest-quality source canonical."""
    left = deepcopy(existing)
    right = deepcopy(candidate)

    def rank(item: dict) -> tuple[int, int, int]:
        return (
            int(item.get("source_priority") or 0),
            1 if item.get("structured_opportunity") else 0,
            len(_text(item.get("description"))),
        )

    winner, loser = (right, left) if rank(right) > rank(left) else (left, right)
    merged = deepcopy(winner)

    for key, value in loser.items():
        if not _has_value(merged.get(key)) and _has_value(value):
            merged[key] = deepcopy(value)

    alternatives: list[dict] = []
    for record in [*left.get("alternate_sources", []), _source_descriptor(left), *right.get("alternate_sources", []), _source_descriptor(right)]:
        if not isinstance(record, dict):
            continue
        marker = (record.get("source"), canonical_url(_text(record.get("url"))))
        if not marker[0] and not marker[1]:
            continue
        if any((entry.get("source"), canonical_url(_text(entry.get("url")))) == marker for entry in alternatives):
            continue
        alternatives.append(record)

    merged["alternate_sources"] = alternatives
    merged["duplicate_count"] = max(0, len(alternatives) - 1)

    first_seen = [value for value in (left.get("first_seen"), right.get("first_seen")) if value]
    if first_seen:
        merged["first_seen"] = min(first_seen)
    last_seen = [value for value in (left.get("last_seen"), right.get("last_seen")) if value]
    if last_seen:
        merged["last_seen"] = max(last_seen)
    last_checked = [value for value in (left.get("last_checked"), right.get("last_checked")) if value]
    if last_checked:
        merged["last_checked"] = max(last_checked)

    return merged


def _watchlist_entries(source_cfg: dict) -> list[dict]:
    watchlist = source_cfg.get("watchlist", {}) or {}
    return [entry for entry in watchlist.get("organizations", []) or [] if isinstance(entry, dict)]


def match_watchlist_organisation(url: str, source_cfg: dict) -> dict | None:
    hostname = (urlparse(_text(url)).hostname or "").lower().removeprefix("www.")
    if not hostname:
        return None
    for entry in _watchlist_entries(source_cfg):
        domain = _text(entry.get("domain")).lower().removeprefix("www.")
        if domain and (hostname == domain or hostname.endswith(f".{domain}")):
            return entry
    return None


def annotate_source(item: dict, source_cfg: dict) -> dict:
    """Attach source quality/priority used both for display and deduplication."""
    annotated = dict(item)
    source = _text(annotated.get("source"))
    source_type = _text(annotated.get("source_type"))
    watch_entry = match_watchlist_organisation(_text(annotated.get("url")), source_cfg)

    if source.startswith(("greenhouse:", "lever:", "ashby:")):
        quality, priority, label = "Official ATS", 100, "Direct employer ATS"
    elif source_type == "official_site_discovery" or watch_entry:
        quality, priority, label = "Official site", 90, "Official organisation site"
    elif source.startswith("reliefweb") or source_type == "humanitarian_job_board":
        quality, priority, label = "Curated board", 75, "Curated specialist job board"
    elif source.startswith("github") or source_type == "open_source":
        quality, priority, label = "Open source", 65, "Open-source project"
    else:
        quality, priority, label = "Web discovery", 40, "Search discovery"

    annotated["source_quality"] = quality
    annotated["source_priority"] = priority
    annotated["source_quality_label"] = label

    if watch_entry and not _text(annotated.get("organization")):
        annotated["organization"] = _text(watch_entry.get("name"))
    if watch_entry:
        annotated["watchlist_match"] = True

    return annotated


def fetch_ashby_board(board_cfg: dict, timeout: int = 25) -> list[dict]:
    board = _text(board_cfg.get("board"))
    if not board:
        return []
    organisation = _text(board_cfg.get("name")) or board
    endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    response = requests.get(endpoint, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []

    results: list[dict] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        title = _text(job.get("title"))
        location = _text(job.get("location"))
        department = _text(job.get("department"))
        team = _text(job.get("team"))
        employment_type = _text(job.get("employmentType"))
        workplace_type = _text(job.get("workplaceType")) or _text(job.get("locationType"))
        body = _html_to_text(job.get("descriptionHtml")) or _text(job.get("description"))
        job_url = _text(job.get("jobUrl")) or _text(job.get("applyUrl"))
        if not job_url:
            continue

        results.append(
            {
                "title": title,
                "url": job_url,
                "description": _join(
                    [
                        f"Organisation: {organisation}.",
                        f"Location: {location}." if location else "",
                        f"Department: {department}." if department else "",
                        f"Team: {team}." if team else "",
                        f"Commitment: {employment_type}." if employment_type else "",
                        f"Work model: {workplace_type}." if workplace_type else "",
                        body,
                    ]
                ),
                "role_context": _join([title, department, team, employment_type]),
                "published": _text(job.get("publishedAt")) or _text(job.get("updatedAt")),
                "source": f"ashby:{board}",
                "source_type": "job_board",
                "organization": organisation,
                "location": location,
                "structured_opportunity": True,
            }
        )
    return results


def collect_ashby_sources(config: dict, checked_at: str) -> tuple[list[dict], list[str], dict[str, int], list[dict]]:
    results: list[dict] = []
    errors: list[str] = []
    stats: dict[str, int] = {}
    health: list[dict] = []

    ashby = config.get("ashby", {}) or {}
    if not ashby.get("enabled", False):
        return results, errors, stats, health

    total = 0
    for board_cfg in ashby.get("boards", []) or []:
        board = _text(board_cfg.get("board"))
        organisation = _text(board_cfg.get("name")) or board
        source_id = f"ashby:{board}"
        try:
            rows = fetch_ashby_board(board_cfg)
            results.extend(rows)
            total += len(rows)
            health.append(
                {
                    "id": source_id,
                    "label": f"{organisation} · Ashby",
                    "kind": "Official ATS",
                    "status": "healthy",
                    "rows": len(rows),
                    "checked_at": checked_at,
                }
            )
        except Exception as exc:
            errors.append(f"{source_id}: {exc}")
            health.append(
                {
                    "id": source_id,
                    "label": f"{organisation} · Ashby",
                    "kind": "Official ATS",
                    "status": "error",
                    "rows": 0,
                    "checked_at": checked_at,
                    "error": str(exc)[:240],
                }
            )
    stats["ashby"] = total
    return results, errors, stats, health


def build_watchlist_queries(source_cfg: dict) -> list[dict]:
    watchlist = source_cfg.get("watchlist", {}) or {}
    if not watchlist.get("enabled", False):
        return []
    limit = int(watchlist.get("max_queries_per_run", 12))
    entries = _watchlist_entries(source_cfg)
    queries: list[dict] = []

    default_terms = _text(
        watchlist.get(
            "query_terms",
            '(legal OR privacy OR compliance OR policy OR governance OR "legal tech") '
            '(job OR career OR fellowship OR internship OR trainee OR "working student")',
        )
    )

    for entry in entries:
        name = _text(entry.get("name"))
        domain = _text(entry.get("domain"))
        if not name or not domain:
            continue
        query = _text(entry.get("query")) or f"site:{domain} {default_terms}"
        queries.append({"name": name, "domain": domain, "query": query})
        if len(queries) >= limit:
            break
    return queries


def source_health_from_legacy(direct_stats: dict[str, int], direct_errors: list[str], checked_at: str) -> list[dict]:
    labels = {
        "greenhouse": ("Greenhouse boards", "Official ATS"),
        "lever": ("Lever sites", "Official ATS"),
        "reliefweb": ("ReliefWeb", "Curated board"),
        "github": ("GitHub Issues", "Open source"),
    }
    health: list[dict] = []
    for source, count in sorted(direct_stats.items()):
        relevant_errors = [err for err in direct_errors if err.startswith(f"{source}:")]
        if relevant_errors and count:
            status = "degraded"
        elif relevant_errors:
            status = "error"
        else:
            status = "healthy"
        label, kind = labels.get(source, (source.title(), "Direct source"))
        entry = {
            "id": source,
            "label": label,
            "kind": kind,
            "status": status,
            "rows": int(count),
            "checked_at": checked_at,
        }
        if relevant_errors:
            entry["error"] = relevant_errors[0][:240]
        health.append(entry)
    return health


def health_summary(entries: list[dict]) -> dict:
    total = len(entries)
    healthy = sum(1 for entry in entries if entry.get("status") == "healthy")
    degraded = sum(1 for entry in entries if entry.get("status") == "degraded")
    errors = sum(1 for entry in entries if entry.get("status") == "error")
    return {
        "total": total,
        "healthy": healthy,
        "degraded": degraded,
        "error": errors,
    }
