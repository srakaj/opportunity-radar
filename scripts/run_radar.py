from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from radar.search import build_queries, search_bing_rss
from radar.score import score_opportunity

DATA_PATH = ROOT / "data" / "opportunities.json"
DOCS_PATH = ROOT / "docs" / "opportunities.json"


def load_yaml(path: Path) -> dict:
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


def main() -> None:
    prefs = load_yaml(ROOT / "config" / "preferences.yaml")
    query_cfg = load_yaml(ROOT / "config" / "queries.yaml")

    max_queries = int(prefs.get("max_queries_per_run", 40))
    max_results = int(prefs.get("max_results_per_query", 10))
    minimum_score = int(prefs.get("minimum_score", 25))

    existing = load_existing()
    by_url = {canonical_url(item.get("url", "")): item for item in existing if item.get("url")}

    run_time = datetime.now(timezone.utc).isoformat()
    queries = build_queries(query_cfg, limit=max_queries)

    discovered = 0
    errors: list[str] = []

    for query in queries:
        try:
            results = search_bing_rss(query, max_results=max_results)
        except Exception as exc:
            errors.append(f"{query}: {exc}")
            continue

        for raw in results:
            scored = score_opportunity(raw, prefs)
            if scored["score"] < minimum_score:
                continue

            key = canonical_url(scored["url"])
            if key in by_url:
                by_url[key]["last_seen"] = run_time
                by_url[key]["score"] = scored["score"]
                by_url[key]["reasons"] = scored["reasons"]
            else:
                scored["first_seen"] = run_time
                scored["last_seen"] = run_time
                by_url[key] = scored
                discovered += 1

    opportunities = sorted(by_url.values(), key=lambda x: x.get("score", 0), reverse=True)

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(opportunities, ensure_ascii=False, indent=2)
    DATA_PATH.write_text(payload + "\n", encoding="utf-8")
    DOCS_PATH.write_text(payload + "\n", encoding="utf-8")

    print(f"Queries run: {len(queries)}")
    print(f"New opportunities: {discovered}")
    print(f"Stored opportunities: {len(opportunities)}")
    if errors:
        print(f"Search errors: {len(errors)}")
        for err in errors[:5]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
