from __future__ import annotations

import html
import os
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; OpportunityRadar/0.2; "
        "+https://github.com/srakaj/opportunity-radar)"
    )
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _html_to_text(value: Any) -> str:
    raw = html.unescape(_text(value))
    if not raw:
        return ""
    return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)


def _join(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def fetch_greenhouse_board(board: dict, timeout: int = 25) -> list[dict]:
    token = _text(board.get("token"))
    if not token:
        return []

    organisation = _text(board.get("name")) or token
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    response = requests.get(
        url,
        params={"content": "true"},
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()

    results: list[dict] = []
    for job in payload.get("jobs", []):
        title = _text(job.get("title"))
        location = _text((job.get("location") or {}).get("name"))
        departments = ", ".join(
            _text(item.get("name"))
            for item in job.get("departments", [])
            if item.get("name")
        )
        offices = ", ".join(
            _text(item.get("name"))
            for item in job.get("offices", [])
            if item.get("name")
        )
        body = _html_to_text(job.get("content"))
        job_url = _text(job.get("absolute_url"))
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
                        f"Department: {departments}." if departments else "",
                        f"Office: {offices}." if offices else "",
                        body,
                    ]
                ),
                # Keep classification metadata separate from free-form advert prose.
                "role_context": _join([title, departments]),
                "published": _text(job.get("updated_at")),
                "source": f"greenhouse:{token}",
                "source_type": "job_board",
                "organization": organisation,
                "location": location,
                "structured_opportunity": True,
            }
        )
    return results


def fetch_lever_site(site_cfg: dict, timeout: int = 25) -> list[dict]:
    site = _text(site_cfg.get("site"))
    if not site:
        return []

    organisation = _text(site_cfg.get("name")) or site
    instance = _text(site_cfg.get("instance")).lower() or "global"
    base = "https://api.eu.lever.co" if instance == "eu" else "https://api.lever.co"
    url = f"{base}/v0/postings/{site}"
    response = requests.get(
        url,
        params={"mode": "json"},
        headers={**HEADERS, "Accept": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()

    results: list[dict] = []
    for job in payload if isinstance(payload, list) else []:
        title = _text(job.get("text"))
        categories = job.get("categories") or {}
        location = _text(categories.get("location"))
        commitment = _text(categories.get("commitment"))
        team = _text(categories.get("team"))
        department = _text(categories.get("department"))
        list_text = []
        for section in job.get("lists", []) or []:
            list_text.append(
                _join(
                    [
                        _text(section.get("text")),
                        _html_to_text(section.get("content")),
                    ]
                )
            )
        body = _join(
            [
                _text(job.get("descriptionPlain")),
                _html_to_text(job.get("description")),
                *list_text,
                _text(job.get("additionalPlain")),
                _html_to_text(job.get("additional")),
            ]
        )
        job_url = _text(job.get("hostedUrl")) or _text(job.get("applyUrl"))
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
                        f"Commitment: {commitment}." if commitment else "",
                        f"Team: {team}." if team else "",
                        f"Department: {department}." if department else "",
                        body,
                    ]
                ),
                "role_context": _join([title, team, department]),
                "published": "",
                "source": f"lever:{site}",
                "source_type": "job_board",
                "organization": organisation,
                "location": location,
                "structured_opportunity": True,
            }
        )
    return results


def fetch_reliefweb_jobs(cfg: dict, timeout: int = 20) -> list[dict]:
    endpoint = "https://api.reliefweb.int/v2/jobs"
    appname = _text(cfg.get("appname")) or "opportunity-radar"
    per_query = int(cfg.get("max_results_per_query", 20))
    queries = cfg.get("queries", []) or []

    results: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        params = {
            "appname": appname,
            "profile": "full",
            "preset": "latest",
            "limit": min(per_query, 100),
            "query[value]": _text(query),
        }
        try:
            response = requests.get(endpoint, params=params, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException:
            # A single slow ReliefWeb query should not discard successful queries.
            continue
        payload = response.json()

        for item in payload.get("data", []):
            fields = item.get("fields") or {}
            job_url = _text(fields.get("url")) or _text(fields.get("url_alias"))
            if not job_url or job_url in seen:
                continue
            seen.add(job_url)
            title = _text(fields.get("title"))
            sources = fields.get("source") or []
            organisation = ", ".join(
                _text(source.get("name"))
                for source in sources
                if isinstance(source, dict) and source.get("name")
            )
            countries = fields.get("country") or []
            location = ", ".join(
                _text(country.get("name"))
                for country in countries
                if isinstance(country, dict) and country.get("name")
            )
            body = _text(fields.get("body")) or _html_to_text(fields.get("body-html"))
            date = fields.get("date") or {}
            published = _text(date.get("created")) if isinstance(date, dict) else ""
            deadline = _text(date.get("closing")) if isinstance(date, dict) else ""
            career_categories = fields.get("career_categories") or []
            categories = ", ".join(
                _text(category.get("name"))
                for category in career_categories
                if isinstance(category, dict) and category.get("name")
            )
            results.append(
                {
                    "title": title,
                    "url": job_url,
                    "description": _join(
                        [
                            f"Organisation: {organisation}." if organisation else "",
                            f"Location: {location}." if location else "",
                            f"Career categories: {categories}." if categories else "",
                            f"Application deadline: {deadline}." if deadline else "",
                            body,
                        ]
                    ),
                    "role_context": _join([title, categories]),
                    "published": published,
                    "deadline": deadline,
                    "source": "reliefweb-api-v2",
                    "source_type": "humanitarian_job_board",
                    "organization": organisation,
                    "location": location,
                    "structured_opportunity": True,
                }
            )
    return results


def fetch_github_issues(cfg: dict, timeout: int = 25) -> list[dict]:
    endpoint = "https://api.github.com/search/issues"
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {
        **HEADERS,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    per_query = int(cfg.get("max_results_per_query", 20))
    results: list[dict] = []
    seen: set[str] = set()
    for configured_query in cfg.get("queries", []) or []:
        query = _text(configured_query)
        if "is:issue" not in query:
            query += " is:issue"
        if "is:open" not in query:
            query += " is:open"
        response = requests.get(
            endpoint,
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": min(per_query, 100),
            },
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        for issue in payload.get("items", []):
            issue_url = _text(issue.get("html_url"))
            if not issue_url or issue_url in seen:
                continue
            seen.add(issue_url)
            title = _text(issue.get("title"))
            repo_api_url = _text(issue.get("repository_url"))
            repo_name = urlparse(repo_api_url).path.removeprefix("/repos/").strip("/")
            labels = ", ".join(
                _text(label.get("name"))
                for label in issue.get("labels", [])
                if isinstance(label, dict) and label.get("name")
            )
            results.append(
                {
                    "title": title,
                    "url": issue_url,
                    "description": _join(
                        [
                            "Open-source contribution opportunity.",
                            f"Repository: {repo_name}." if repo_name else "",
                            f"Labels: {labels}." if labels else "",
                            _text(issue.get("body")),
                        ]
                    ),
                    "role_context": _join([title, repo_name, labels]),
                    "published": _text(issue.get("updated_at")),
                    "source": "github-issues-api",
                    "source_type": "open_source",
                    "organization": repo_name,
                    "location": "Remote / open source",
                    "structured_opportunity": True,
                }
            )
    return results


def collect_direct_sources(config: dict) -> tuple[list[dict], list[str], dict[str, int]]:
    results: list[dict] = []
    errors: list[str] = []
    stats: dict[str, int] = {}

    greenhouse = config.get("greenhouse", {}) or {}
    if greenhouse.get("enabled", False):
        count = 0
        for board in greenhouse.get("boards", []) or []:
            token = _text(board.get("token"))
            try:
                rows = fetch_greenhouse_board(board)
                results.extend(rows)
                count += len(rows)
            except Exception as exc:
                errors.append(f"greenhouse:{token}: {exc}")
        stats["greenhouse"] = count

    lever = config.get("lever", {}) or {}
    if lever.get("enabled", False):
        count = 0
        for site in lever.get("sites", []) or []:
            site_name = _text(site.get("site"))
            try:
                rows = fetch_lever_site(site)
                results.extend(rows)
                count += len(rows)
            except Exception as exc:
                errors.append(f"lever:{site_name}: {exc}")
        stats["lever"] = count

    reliefweb = config.get("reliefweb", {}) or {}
    if reliefweb.get("enabled", False):
        try:
            rows = fetch_reliefweb_jobs(reliefweb)
            results.extend(rows)
            stats["reliefweb"] = len(rows)
        except Exception as exc:
            errors.append(f"reliefweb: {exc}")
            stats["reliefweb"] = 0

    github = config.get("github", {}) or {}
    if github.get("enabled", False):
        try:
            rows = fetch_github_issues(github)
            results.extend(rows)
            stats["github"] = len(rows)
        except Exception as exc:
            errors.append(f"github: {exc}")
            stats["github"] = 0

    return results, errors, stats
