from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import feedparser
import requests

from common import clean_text, now_in_timezone


ARXIV_API_URL = "https://export.arxiv.org/api/query"


def fetch(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_config = config["sources"]["arxiv"]
    if not source_config.get("enabled", True):
        return [], {"source": "arxiv", "enabled": False, "count": 0}

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    cutoff = now_in_timezone(config).astimezone(timezone.utc) - timedelta(days=int(source_config.get("days_back", 30)))

    for query in source_config.get("queries", []):
        search_query = f'all:"{query}"'
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": int(source_config.get("per_query", 15)),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            response = requests.get(f"{ARXIV_API_URL}?{urlencode(params)}", timeout=30)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            returned = 0
            for entry in feed.entries:
                published = _parse_arxiv_datetime(entry.get("published"))
                if published and published < cutoff:
                    continue
                returned += 1
                items.append(_transform_entry(entry, query))
            logging.info("arXiv query=%r returned %s recent items", query, returned)
        except Exception as exc:
            message = f"{query}: {exc}"
            errors.append(message)
            logging.exception("arXiv failed for query=%r", query)

    meta = {"source": "arxiv", "enabled": True, "count": len(items), "errors": errors}
    return items, meta


def _parse_arxiv_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _arxiv_id(entry_id: str) -> str:
    match = re.search(r"/abs/([^/?#]+)", entry_id or "")
    return match.group(1) if match else entry_id


def _transform_entry(entry: Any, query: str) -> dict[str, Any]:
    authors = [clean_text(author.get("name")) for author in entry.get("authors", []) if author.get("name")]
    categories = [tag.get("term") for tag in entry.get("tags", []) if tag.get("term")]
    entry_id = entry.get("id", "")
    return {
        "source_name": "arXiv",
        "source_query": query,
        "item_type": "预印本",
        "openalex_id": "",
        "doi": clean_text(entry.get("arxiv_doi") or ""),
        "arxiv_id": _arxiv_id(entry_id),
        "title": clean_text(entry.get("title")) or "Untitled",
        "authors": authors,
        "year": (entry.get("published") or "")[:4],
        "published_date": (entry.get("published") or "")[:10],
        "venue": "arXiv",
        "url": entry_id,
        "abstract": clean_text(entry.get("summary")),
        "raw_keywords": categories,
    }
