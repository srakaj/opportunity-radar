from __future__ import annotations

import itertools
import time
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


DDG_HTML = "https://html.duckduckgo.com/html/"
BING_RSS = "https://www.bing.com/search?format=rss&q={query}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )
}


def build_queries(config: dict, limit: int = 40) -> list[str]:
    role_terms = config.get("role_terms", [])
    topic_terms = config.get("topic_terms", [])
    location_terms = config.get("location_terms", [])
    source_queries = config.get("source_queries", [])

    queries: list[str] = list(source_queries)

    # High-recall combinations. We deliberately search several naming conventions
    # because niche opportunities are inconsistently labelled across organisations.
    for role, location in itertools.product(role_terms, location_terms):
        queries.append(f'"{role}" {location} 2026')

    for role, topic in itertools.product(role_terms, topic_terms):
        queries.append(f'"{role}" "{topic}"')

    # Preserve order while removing duplicate query strings.
    unique = list(dict.fromkeys(queries))
    return unique[:limit]


def _unwrap_ddg_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return urllib.parse.unquote(query["uddg"][0])
    if url.startswith("//"):
        return "https:" + url
    return url


def search_duckduckgo_html(
    query: str, max_results: int = 10, delay: float = 1.0
) -> list[dict]:
    response = requests.get(
        DDG_HTML,
        params={"q": query},
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict] = []

    for result in soup.select(".result"):
        anchor = result.select_one(".result__a")
        if anchor is None:
            continue

        title = anchor.get_text(" ", strip=True)
        link = _unwrap_ddg_url(anchor.get("href", ""))
        snippet_node = result.select_one(".result__snippet")
        description = snippet_node.get_text(" ", strip=True) if snippet_node else ""

        if link and link.startswith(("http://", "https://")):
            results.append(
                {
                    "title": title,
                    "url": link,
                    "description": description,
                    "published": "",
                    "query": query,
                    "source": "duckduckgo-html",
                }
            )

        if len(results) >= max_results:
            break

    time.sleep(delay)
    return results


def search_bing_rss(
    query: str, max_results: int = 10, delay: float = 0.8
) -> list[dict]:
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
                    "source": "bing-rss-fallback",
                }
            )
    time.sleep(delay)
    return results


def search_web(query: str, max_results: int = 10) -> list[dict]:
    """Search a free public endpoint, falling back if the primary source fails.

    DuckDuckGo's HTML results tend to preserve quoted phrases and site filters much
    better than Bing RSS for niche vacancy searches. Bing remains a fallback so a
    temporary DDG block does not make the daily workflow useless.
    """
    try:
        results = search_duckduckgo_html(query, max_results=max_results)
        if results:
            return results
    except Exception:
        pass

    return search_bing_rss(query, max_results=max_results)
