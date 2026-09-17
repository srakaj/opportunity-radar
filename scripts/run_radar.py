from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from radar.adapters import collect_direct_sources
from radar.deadline import enrich_deadline_timezone
from radar.enrich import enrich_opportunity
from radar.enrichment_score import reconcile_enrichment_score
from radar.fit import assess_fit
from radar.search import build_queries, search_web
from radar.score import score_opportunity
from radar.source_expansion import (
    annotate_source,
    build_watchlist_queries,
    canonical_url,
    collect_ashby_sources,
    health_summary,
    match_watchlist_organisation,
    merge_opportunities,
    opportunity_identity,
    source_health_from_legacy,
)

DATA_PATH = ROOT / "data" / "opportunities.json"
DOCS_PATH = ROOT / "docs" / "opportunities.json"
SOURCE_HEALTH_PATH = ROOT / "docs" / "source-health.json"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_existing() -> list[dict]:
    if not DATA_PATH.exists():
        return []
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def compact_for_storage(item: dict, description_max_chars: int) -> dict:
    compact = dict(item)
    description = str(compact.get("description", ""))
    if len(description) > description_max_chars:
        compact["description"] = description[:description_max_chars].rstrip() + " …"
        compact["description_truncated"] = True
    else:
        compact.pop("description_truncated", None)
    return compact


def enrich_score_and_fit(item: dict, prefs: dict, profile: dict, source_cfg: dict) -> dict:
    source_annotated = annotate_source(item, source_cfg)
    enriched = enrich_opportunity(source_annotated)
    enriched = enrich_deadline_timezone(enriched)
    scored = score_opportunity(enriched, prefs)
    reconciled = reconcile_enrichment_score(scored, prefs)
    return assess_fit(reconciled, profile)


def main() -> None:
    prefs = load_yaml(ROOT / "config" / "preferences.yaml")
    profile = load_yaml(ROOT / "config" / "profile.yaml")
    query_cfg = load_yaml(ROOT / "config" / "queries.yaml")
    source_cfg = load_yaml(ROOT / "config" / "sources.yaml")

    max_queries = int(prefs.get("max_queries_per_run", 40))
    max_results = int(prefs.get("max_results_per_query", 10))
    minimum_score = int(prefs.get("minimum_score", 25))
    max_stored = int(prefs.get("max_stored_opportunities", 150))
    description_max_chars = int(prefs.get("description_max_chars", 2000))

    existing = load_existing()
    historical_first_seen_by_url = {
        canonical_url(item.get("url", "")): item.get("first_seen")
        for item in existing
        if item.get("url") and item.get("first_seen")
    }
    historical_first_seen_by_identity = {
        opportunity_identity(item): item.get("first_seen")
        for item in existing
        if item.get("url") and item.get("first_seen")
    }
    historical_identities = {
        opportunity_identity(item)
        for item in existing
        if item.get("url")
    }

    # Store one canonical record per role identity, not one record per discovery URL.
    # This lets an official ATS result replace a lower-quality search-engine duplicate.
    by_identity: dict[str, dict] = {}
    pruned = 0
    for item in existing:
        if not item.get("url"):
            continue
        reassessed = enrich_score_and_fit(item, prefs, profile, source_cfg)
        if reassessed["score"] < minimum_score:
            pruned += 1
            continue
        key = opportunity_identity(reassessed)
        if key in by_identity:
            by_identity[key] = merge_opportunities(by_identity[key], reassessed)
        else:
            by_identity[key] = reassessed

    run_time = datetime.now(timezone.utc).isoformat()
    discovered = 0
    errors: list[str] = []
    health_entries: list[dict] = []

    def ingest(raw: dict) -> None:
        nonlocal discovered
        assessed = enrich_score_and_fit(raw, prefs, profile, source_cfg)
        if assessed["score"] < minimum_score or not assessed.get("url"):
            return

        key = opportunity_identity(assessed)
        url_key = canonical_url(assessed["url"])
        previous = by_identity.get(key)
        previous_first_seen = (
            (previous or {}).get("first_seen")
            or historical_first_seen_by_identity.get(key)
            or historical_first_seen_by_url.get(url_key)
        )
        if previous_first_seen:
            assessed["first_seen"] = previous_first_seen
        else:
            assessed["first_seen"] = run_time
            if key not in historical_identities:
                discovered += 1
        assessed["last_seen"] = run_time
        assessed["last_checked"] = run_time
        assessed["opportunity_identity"] = key

        if previous:
            by_identity[key] = merge_opportunities(previous, assessed)
        else:
            by_identity[key] = assessed

    # Existing direct sources: Greenhouse, Lever, ReliefWeb and GitHub Issues.
    direct_results, direct_errors, direct_stats = collect_direct_sources(source_cfg)
    errors.extend(direct_errors)
    health_entries.extend(source_health_from_legacy(direct_stats, direct_errors, run_time))
    for raw in direct_results:
        ingest(raw)

    # V0.6: direct Ashby boards for high-value legal-tech employers.
    ashby_results, ashby_errors, ashby_stats, ashby_health = collect_ashby_sources(source_cfg, run_time)
    errors.extend(ashby_errors)
    health_entries.extend(ashby_health)
    for raw in ashby_results:
        ingest(raw)

    # V0.6: organisation watchlist. Search is constrained to official domains and
    # therefore receives higher source quality than generic web discovery.
    watchlist_queries = build_watchlist_queries(source_cfg)
    for watch in watchlist_queries:
        rows_seen = 0
        source_id = f"watch:{watch['domain']}"
        try:
            results = search_web(watch["query"], max_results=max_results)
            for raw in results:
                if not match_watchlist_organisation(raw.get("url", ""), source_cfg):
                    continue
                raw = dict(raw)
                raw["organization"] = watch["name"]
                raw["source_type"] = "official_site_discovery"
                raw["structured_opportunity"] = False
                raw["watchlist_match"] = True
                rows_seen += 1
                ingest(raw)
            health_entries.append(
                {
                    "id": source_id,
                    "label": watch["name"],
                    "kind": "Official site watch",
                    "status": "healthy",
                    "rows": rows_seen,
                    "checked_at": run_time,
                }
            )
        except Exception as exc:
            errors.append(f"{source_id}: {exc}")
            health_entries.append(
                {
                    "id": source_id,
                    "label": watch["name"],
                    "kind": "Official site watch",
                    "status": "error",
                    "rows": 0,
                    "checked_at": run_time,
                    "error": str(exc)[:240],
                }
            )

    # Generic high-recall web discovery remains useful for opportunities that are not
    # on known ATS platforms or target-organisation sites.
    queries = build_queries(query_cfg, limit=max_queries)
    web_rows = 0
    web_errors = 0
    for query in queries:
        try:
            results = search_web(query, max_results=max_results)
        except Exception as exc:
            web_errors += 1
            errors.append(f"web:{query}: {exc}")
            continue
        web_rows += len(results)
        for raw in results:
            ingest(raw)

    if web_errors == 0:
        web_status = "healthy"
    elif web_rows:
        web_status = "degraded"
    else:
        web_status = "error"
    health_entries.append(
        {
            "id": "web-discovery",
            "label": "General web discovery",
            "kind": "Search discovery",
            "status": web_status,
            "rows": web_rows,
            "checked_at": run_time,
            "queries": len(queries),
            "errors": web_errors,
        }
    )

    # Personal fit is the primary dashboard ordering; thematic relevance remains the
    # tie-breaker so high-signal opportunities rise within each fit band.
    ranked = sorted(
        by_identity.values(),
        key=lambda x: (
            x.get("fit_score", 0),
            x.get("score", 0),
            x.get("source_priority", 0),
            x.get("published", ""),
        ),
        reverse=True,
    )
    eligible_before_cap = len(ranked)
    if max_stored > 0:
        ranked = ranked[:max_stored]
    opportunities = [
        compact_for_storage(item, description_max_chars)
        for item in ranked
    ]

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(opportunities, ensure_ascii=False, indent=2)
    DATA_PATH.write_text(payload + "\n", encoding="utf-8")
    DOCS_PATH.write_text(payload + "\n", encoding="utf-8")

    health_payload = {
        "generated_at": run_time,
        "summary": health_summary(health_entries),
        "sources": health_entries,
        "watchlist_queries": len(watchlist_queries),
        "web_queries": len(queries),
    }
    SOURCE_HEALTH_PATH.write_text(
        json.dumps(health_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Direct source rows:")
    combined_stats = {**direct_stats, **ashby_stats}
    for source, count in sorted(combined_stats.items()):
        print(f"  - {source}: {count}")
    print(f"Watchlist queries run: {len(watchlist_queries)}")
    print(f"Web queries run: {len(queries)}")
    print(f"New opportunities: {discovered}")
    print(f"Pruned old false positives: {pruned}")
    print(f"Eligible before storage cap: {eligible_before_cap}")
    print(f"Stored opportunities: {len(opportunities)}")
    print(
        "Fit bands: "
        + ", ".join(
            f"{label}={sum(1 for item in opportunities if item.get('fit_label') == label)}"
            for label in ("Strong fit", "Stretch", "Probably skip")
        )
    )
    summary = health_payload["summary"]
    print(
        "Source health: "
        f"healthy={summary['healthy']}, degraded={summary['degraded']}, "
        f"error={summary['error']}, total={summary['total']}"
    )

    if errors:
        print(f"Source/search errors: {len(errors)}")
        for err in errors[:15]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
