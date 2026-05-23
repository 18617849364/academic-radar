from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from common import clean_text


def fetch(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_config = config["sources"].get("web_pages", {})
    if not source_config.get("enabled", False):
        return [], {"source": "web_pages", "enabled": False, "count": 0}

    timeout = int(source_config.get("timeout_seconds", 20))
    max_links = int(source_config.get("max_links_per_page", 30))
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    page_counts: dict[str, int] = {}

    for page in source_config.get("pages", []):
        name = page.get("name", "Unnamed page")
        url = page.get("url", "")
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "academic-radar/0.1"})
            if response.status_code >= 400 and page.get("fallback_url"):
                logging.warning("Web page %s returned %s, trying fallback", name, response.status_code)
                response = requests.get(page["fallback_url"], timeout=timeout, headers={"User-Agent": "academic-radar/0.1"})
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding
            parsed = BeautifulSoup(response.text, "lxml")
            count = 0
            seen_urls: set[str] = set()
            for link in parsed.find_all("a", href=True):
                title = clean_text(link.get_text(" "))
                href = urljoin(response.url, link["href"])
                if not _is_candidate(title, href, response.url) or href in seen_urls:
                    continue
                seen_urls.add(href)
                items.append(
                    {
                        "source_name": name,
                        "source_query": page.get("category", "web_page"),
                        "item_type": _item_type(page.get("category", "")),
                        "openalex_id": "",
                        "doi": "",
                        "arxiv_id": "",
                        "title": title,
                        "authors": [],
                        "year": "",
                        "published_date": "",
                        "venue": name,
                        "url": href,
                        "abstract": "",
                        "raw_keywords": [page.get("category", "web_page"), "中文平台"],
                    }
                )
                count += 1
                if count >= max_links:
                    break
            page_counts[name] = count
            logging.info("Web page=%r returned %s candidate links", name, count)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            logging.exception("Web page failed for %r", name)

    meta = {
        "source": "web_pages",
        "enabled": True,
        "count": len(items),
        "page_counts": page_counts,
        "errors": errors,
    }
    return items, meta


def _is_candidate(title: str, href: str, base_url: str) -> bool:
    if len(title) < 6:
        return False
    if href.startswith("javascript:") or href.startswith("mailto:"):
        return False
    blocked = ["#", ".jpg", ".png", ".gif", ".css", ".js"]
    if any(href.lower().endswith(ext) for ext in blocked):
        return False
    return True


def _item_type(category: str) -> str:
    if "book" in category:
        return "新书"
    if "platform" in category or "news" in category:
        return "中文学术平台"
    return "学术动态"
