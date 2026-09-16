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
from radar.search import build_queries, search_web
from radar.score import score_opportunity

DATA_PATH = ROOT / "data" / "opportunities.json"
DOCS_PATH = ROOT / "docs" / "opportunities.json"


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


def canonical_url(url: str) -> str:
    return url.split("#", 1)[0].rstrip("/")


def compact_for_storage(item: dict, description_max_chars: int) -> dict:
    compact = dict(item)
    description = str(compact.get("description", ""))
    if len(description) > description_max_chars:
        compact["description"] = description[:description_max_chars].rstrip() + " …"
        compact["description_truncated"] = True
    else:
        compact.pop("description_truncated", None)
    return compact


def main() -> None:
    prefs = load_yaml(ROOT / "config" / "preferences.yaml")
    query_cfg = load_yaml(ROOT / "config" / "queries.yaml")
    source_cfg = load_yaml(ROOT / "config" / "sources.yaml")

    max_queries = int(prefs.get("max_queries_per_run", 40))
    max_results = int(prefs.get("max_results_per_query", 10))
    minimum_score = int(prefs.get("minimum_score", 25))
    max_stored = int(prefs.get("max_stored_opportunities", 150))
    description_max_chars = int(prefs.get("description_max_chars", 2000))

    existing = load_existing()
    historical_first_seen = {
        canonical_url(item.get("url", "")): item.get("first_seen")
        for item in existing
        if item.get("url") and item.get("first_seen")
    }

    # Re-score history on every run. Improvements to the scoring rules therefore
    # clean old false positives automatically instead of preserving them forever.
    by_url: dict[str, dict] = {}
    pruned = 0
    for item in existing:
        if not item.get("url"):
            continue
        rescored = score_opportunity(item, prefs)
        if rescored["score"] < minimum_score:
            pruned += 1
            continue
        by_url[canonical_url(rescored["url"])] = rescored

    run_time = datetime.now(timezone.utc).isoformat()
    discovered = 0
    errors: list[str] = []

    def ingest(raw: dict) -> None:
        nonlocal discovered
        scored = score_opportunity(raw, prefs)
        if scored["score"] < minimum_score or not scored.get("url"):
            return

        key = canonical_url(scored["url"])
        previous_first_seen = (
            by_url.get(key, {}).get("first_seen")
            or historical_first_seen.get(key)
        )
        if previous_first_seen:
            scored["first_seen"] = previous_first_seen
        else:
            scored["first_seen"] = run_time
            discovered += 1
        scored["last_seen"] = run_time
        by_url[key] = scored

    direct_results, direct_errors, direct_stats = collect_direct_sources(source_cfg)
    errors.extend(direct_errors)
    for raw in direct_results:
        ingest(raw)

    queries = build_queries(query_cfg, limit=max_queries)
    for query in queries:
        try:
            results = search_web(query, max_results=max_results)
        except Exception as exc:
            errors.append(f"web:{query}: {exc}")
            continue
        for raw in results:
            ingest(raw)

    ranked = sorted(
        by_url.values(),
        key=lambda x: (x.get("score", 0), x.get("published", "")),
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

    print("Direct source rows:")
    for source, count in sorted(direct_stats.items()):
        print(f"  - {source}: {count}")
    print(f"Web queries run: {len(queries)}")
    print(f"New opportunities: {discovered}")
    print(f"Pruned old false positives: {pruned}")
    print(f"Eligible before storage cap: {eligible_before_cap}")
    print(f"Stored opportunities: {len(opportunities)}")

    if errors:
        print(f"Source/search errors: {len(errors)}")
        for err in errors[:10]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
