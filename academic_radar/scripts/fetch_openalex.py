from __future__ import annotations

import logging
import os
from typing import Any

import requests

from common import abstract_from_openalex, clean_text, days_ago, normalize_doi, now_in_timezone


OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def fetch(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_config = config["sources"]["openalex"]
    if not source_config.get("enabled", True):
        return [], {"source": "openalex", "enabled": False, "count": 0}

    email = os.getenv("OPENALEX_EMAIL", "").strip()
    params_base = {
        "per-page": int(source_config.get("per_query", 20)),
        "filter": (
            f"from_publication_date:{days_ago(config, int(source_config.get('days_back', 30)))},"
            f"to_publication_date:{now_in_timezone(config).date().isoformat()}"
        ),
        "sort": "publication_date:desc",
    }
    if email:
        params_base["mailto"] = email

    items: list[dict[str, Any]] = []
    errors: list[str] = []

    for query in source_config.get("queries", []):
        params = dict(params_base)
        params["search"] = query
        try:
            response = requests.get(OPENALEX_WORKS_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
            logging.info("OpenAlex query=%r returned %s items", query, len(results))
            for work in results:
                items.append(_transform_work(work, query))
        except Exception as exc:
            message = f"{query}: {exc}"
            errors.append(message)
            logging.exception("OpenAlex failed for query=%r", query)

    meta = {"source": "openalex", "enabled": True, "count": len(items), "errors": errors}
    return items, meta


def _transform_work(work: dict[str, Any], query: str) -> dict[str, Any]:
    authorships = work.get("authorships") or []
    authors = [
        clean_text((authorship.get("author") or {}).get("display_name"))
        for authorship in authorships[:8]
        if (authorship.get("author") or {}).get("display_name")
    ]
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    concepts = [c.get("display_name") for c in work.get("concepts", [])[:8] if c.get("display_name")]
    topics = []
    for topic in work.get("topics", [])[:5]:
        if topic.get("display_name"):
            topics.append(topic["display_name"])

    doi = normalize_doi(work.get("doi"))
    return {
        "source_name": "OpenAlex",
        "source_query": query,
        "item_type": "论文",
        "openalex_id": work.get("id") or "",
        "doi": doi,
        "arxiv_id": "",
        "title": clean_text(work.get("display_name")) or "Untitled",
        "authors": authors,
        "year": work.get("publication_year") or "",
        "published_date": work.get("publication_date") or "",
        "venue": clean_text(source.get("display_name")) or clean_text(work.get("host_venue", {}).get("display_name")) or "未知来源",
        "url": work.get("doi") or primary_location.get("landing_page_url") or work.get("id") or "",
        "abstract": clean_text(abstract_from_openalex(work.get("abstract_inverted_index"))),
        "raw_keywords": [*concepts, *topics],
    }
