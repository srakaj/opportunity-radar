from __future__ import annotations

import itertools
import time
import urllib.parse
import xml.etree.ElementTree as ET

import requests


BING_RSS = "https://www.bing.com/search?format=rss&q={query}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OpportunityRadar/0.1; +https://github.com/srakaj/opportunity-radar)"}


def build_queries(config: dict, limit: int = 40) -> list[str]:
    role_terms = config.get("role_terms", [])
    topic_terms = config.get("topic_terms", [])
    location_terms = config.get("location_terms", [])
    source_queries = config.get("source_queries", [])

    queries: list[str] = list(source_queries)

    # High-recall combinations, deliberately broader than a normal job search.
    for role, location in itertools.product(role_terms, location_terms):
        queries.append(f'"{role}" {location} 2026')

    for role, topic in itertools.product(role_terms, topic_terms):
        queries.append(f'"{role}" "{topic}"')

    # Preserve order while removing duplicate query strings.
    unique = list(dict.fromkeys(queries))
    return unique[:limit]


def search_bing_rss(query: str, max_results: int = 10, delay: float = 0.8) -> list[dict]:
    encoded = urllib.parse.quote_plus(query)
    url = BING_RSS.format(query=encoded)
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    results: list[dict] = []
    for item in root.findall(".//item")[:max_results]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        description = item.findtext("description") or ""
        pub_date = item.findtext("pubDate") or ""
        if link:
            results.append(
                {
                    "title": title.strip(),
                    "url": link.strip(),
                    "description": description.strip(),
                    "published": pub_date.strip(),
                    "query": query,
                    "source": "bing-rss",
                }
            )
    time.sleep(delay)
    return results
