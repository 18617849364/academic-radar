from __future__ import annotations

import logging
from typing import Any

import requests

from common import clean_text, days_ago, normalize_doi, now_in_timezone


CROSSREF_WORKS_URL = "https://api.crossref.org/works"


def fetch(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_config = config["sources"]["crossref"]
    if not source_config.get("enabled", False):
        return [], {"source": "crossref", "enabled": False, "count": 0}

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    for query in source_config.get("queries", []):
        params = {
            "query.bibliographic": query,
            "filter": (
                f"from-pub-date:{days_ago(config, int(source_config.get('days_back', 30)))},"
                f"until-pub-date:{now_in_timezone(config).date().isoformat()}"
            ),
            "rows": int(source_config.get("per_query", 15)),
            "sort": "published",
            "order": "desc",
        }
        try:
            response = requests.get(CROSSREF_WORKS_URL, params=params, timeout=30)
            response.raise_for_status()
            works = response.json().get("message", {}).get("items", [])
            logging.info("Crossref query=%r returned %s items", query, len(works))
            for work in works:
                items.append(_transform_work(work, query))
        except Exception as exc:
            errors.append(f"{query}: {exc}")
            logging.exception("Crossref failed for query=%r", query)

    return items, {"source": "crossref", "enabled": True, "count": len(items), "errors": errors}


def _first(values: Any) -> str:
    if isinstance(values, list) and values:
        return clean_text(values[0])
    return clean_text(values)


def _date_parts(work: dict[str, Any]) -> str:
    parts = (
        work.get("published-print", {})
        or work.get("published-online", {})
        or work.get("published", {})
        or {}
    ).get("date-parts", [[]])[0]
    if not parts:
        return ""
    year = str(parts[0])
    month = f"{parts[1]:02d}" if len(parts) > 1 else "01"
    day = f"{parts[2]:02d}" if len(parts) > 2 else "01"
    return f"{year}-{month}-{day}"


def _transform_work(work: dict[str, Any], query: str) -> dict[str, Any]:
    authors = []
    for author in work.get("author", [])[:8]:
        name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
        if name:
            authors.append(clean_text(name))
    published = _date_parts(work)
    return {
        "source_name": "Crossref",
        "source_query": query,
        "item_type": "论文",
        "openalex_id": "",
        "doi": normalize_doi(work.get("DOI")),
        "arxiv_id": "",
        "title": _first(work.get("title")) or "Untitled",
        "authors": authors,
        "year": published[:4],
        "published_date": published,
        "venue": _first(work.get("container-title")) or "Crossref",
        "url": work.get("URL", ""),
        "abstract": clean_text(work.get("abstract")),
        "raw_keywords": work.get("subject", []),
    }
