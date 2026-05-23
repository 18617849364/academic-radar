from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import feedparser
import requests

from common import clean_text, iso_date_or_empty, now_in_timezone, parse_date


def fetch(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_config = config["sources"]["rss"]
    if not source_config.get("enabled", True):
        return [], {"source": "rss", "enabled": False, "count": 0}

    cutoff = now_in_timezone(config).date() - timedelta(days=int(config.get("project", {}).get("days_back", 30)))
    timeout = int(source_config.get("timeout_seconds", 20))
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    feed_counts: dict[str, int] = {}

    for feed_config in source_config.get("feeds", []):
        name = feed_config.get("name", "Unnamed RSS")
        url = feed_config.get("url", "")
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "academic-radar/0.1"})
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.bozo:
                logging.warning("RSS feed parsed with warning: %s (%s)", name, parsed.bozo_exception)
            count = 0
            for entry in parsed.entries:
                published = parse_date(entry.get("published") or entry.get("updated"))
                if published and published < cutoff:
                    continue
                count += 1
                items.append(_transform_entry(entry, feed_config))
            feed_counts[name] = count
            logging.info("RSS feed=%r returned %s recent items", name, count)
        except Exception as exc:
            message = f"{name}: {exc}"
            errors.append(message)
            logging.exception("RSS failed for feed=%r", name)

    meta = {
        "source": "rss",
        "enabled": True,
        "count": len(items),
        "feed_counts": feed_counts,
        "errors": errors,
    }
    return items, meta


def _transform_entry(entry: Any, feed_config: dict[str, Any]) -> dict[str, Any]:
    category = feed_config.get("category", "rss")
    item_type = {
        "journal": "论文",
        "academic_blog": "学术博客",
        "report": "报告",
        "new_book": "新书",
    }.get(category, "RSS")
    authors = []
    if entry.get("author"):
        authors = [clean_text(entry.get("author"))]
    return {
        "source_name": feed_config.get("name", "RSS"),
        "source_query": category,
        "item_type": item_type,
        "openalex_id": "",
        "doi": "",
        "arxiv_id": "",
        "title": clean_text(entry.get("title")) or "Untitled",
        "authors": authors,
        "year": (iso_date_or_empty(entry.get("published") or entry.get("updated")) or "")[:4],
        "published_date": iso_date_or_empty(entry.get("published") or entry.get("updated")),
        "venue": feed_config.get("name", "RSS"),
        "url": entry.get("link", ""),
        "abstract": clean_text(entry.get("summary") or entry.get("description")),
        "raw_keywords": [category],
    }
