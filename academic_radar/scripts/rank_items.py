from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta
from typing import Any

from common import clean_text, item_identity, normalize_doi, normalize_title, now_in_timezone, parse_date


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        identity = item_identity(item)
        if identity not in buckets:
            buckets[identity] = item
            buckets[identity]["identity"] = identity
            continue
        buckets[identity] = _merge_items(buckets[identity], item)
        buckets[identity]["identity"] = identity

    # Repository deposits can mint several DOIs for the same title/version.
    # A second exact-title pass prevents those from crowding out real variety.
    title_buckets: dict[str, dict[str, Any]] = {}
    for item in buckets.values():
        title_key = normalize_title(item.get("title", "")) or item.get("identity", "")
        if title_key not in title_buckets:
            title_buckets[title_key] = item
            continue
        title_buckets[title_key] = _merge_items(title_buckets[title_key], item)
    return list(title_buckets.values())


def score_and_rank(
    items: list[dict[str, Any]],
    config: dict[str, Any],
    seen_items: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored = [score_item(item, config) for item in dedupe_items(items)]
    scored.sort(key=lambda item: (item.get("relevance_score", 0), item.get("published_date", "")), reverse=True)

    project = config.get("project", {})
    min_score = int(project.get("min_score", 3))
    max_items = int(project.get("max_items", 12))
    min_items = int(project.get("min_items", 8))
    fresh_days = int(project.get("fresh_days", 7))
    today = now_in_timezone(config).date()

    unseen = [item for item in scored if item.get("identity") not in seen_items.get("items", {})]
    selected = [item for item in unseen if item.get("relevance_score", 0) >= min_score]

    if len(selected) < min_items:
        recent_unseen = []
        for item in unseen:
            published = parse_date(item.get("published_date"))
            if published and today - published <= timedelta(days=fresh_days):
                recent_unseen.append(item)
        for item in recent_unseen:
            if item not in selected:
                selected.append(item)
            if len(selected) >= min_items:
                break

    return selected[:max_items], scored


def score_item(item: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    item = dict(item)
    text = " ".join(
        [
            item.get("title", ""),
            item.get("abstract", ""),
            " ".join(item.get("raw_keywords", []) or []),
        ]
    )
    text_clean = clean_text(text)
    text_lower = text_clean.lower()

    score = 0
    matched_by_group: dict[str, list[str]] = defaultdict(list)
    for group_name, group in config.get("keyword_groups", {}).items():
        terms = group.get("terms", [])
        group_hit = False
        for term in terms:
            if _contains_term(text_clean, text_lower, term):
                matched_by_group[group_name].append(term)
                group_hit = True
        if group_hit:
            weight = int(group.get("weight", 1))
            lowered_hits = set(term.lower() for term in matched_by_group[group_name])
            if group_name == "sociology_core":
                broad_hits = {"identity", "power", "inequality"}
                if lowered_hits.issubset(broad_hits):
                    weight = 1
            if group_name == "japan_china":
                broad_hits = {"japan", "china", "east asia"}
                if lowered_hits.issubset(broad_hits):
                    weight = 1
            if group_name == "generative_ai_society" and not _has_ai_anchor(text_lower):
                broad_hits = {"social support", "help-seeking", "digital intimacy"}
                if lowered_hits.issubset(broad_hits):
                    weight = 1
            score += weight

    ranking = config.get("ranking", {})
    if any(_contains_term(text_clean, text_lower, term) for term in ranking.get("theory_method_terms", [])):
        score += 1
        item["has_method_or_theory_signal"] = True
    else:
        item["has_method_or_theory_signal"] = False

    if normalize_doi(item.get("doi")) or item.get("url"):
        score += 1

    today = now_in_timezone(config).date()
    published = parse_date(item.get("published_date"))
    if published:
        age = today - published
        if age.days <= 7:
            score += 2
        elif age.days <= 30:
            score += 1

    has_social_signal = any(
        matched_by_group.get(group)
        for group in [
            "sociology_core",
            "heritage_research",
            "japan_china",
            "generative_ai_society",
            "japanese_terms",
            "chinese_terms",
        ]
    )
    has_ai_or_technical = any(term in text_lower for term in ["ai", "llm", "machine learning", "deep learning", "neural"])
    if item.get("source_name") == "arXiv" and has_ai_or_technical and not has_social_signal:
        score -= 4

    if any(term.lower() in text_lower for term in ranking.get("commercial_penalty_terms", [])):
        score -= 5

    repository_noise_terms = [
        "top 10 read",
        "toolkit",
        "dataset :",
        "dataset:",
        "copyright",
        "licensed under",
        "source code",
        "github repository",
        "development research artifact",
    ]
    if any(term in text_lower for term in repository_noise_terms):
        score -= 5

    announcement_terms = [
        "ニュース・メール",
        "シンポジウム",
        "助成",
        "募集",
        "公募",
        "報告申込",
        "大会の報告募集",
        "annual meeting application",
        "call for papers",
        "newsletter",
    ]
    if item.get("item_type") in {"RSS", "学术动态", "中文学术平台"} and any(term.lower() in text_lower for term in announcement_terms):
        score -= 10

    abstract = clean_text(item.get("abstract", ""))
    if not abstract:
        score -= 2

    technical_hits = [term for term in ranking.get("technical_penalty_terms", []) if term.lower() in text_lower]
    if technical_hits and not (matched_by_group.get("heritage_research") or _has_ai_anchor(text_lower)):
        score -= 4

    item["relevance_score"] = score
    item["matched_keywords"] = {
        group: terms[:8] for group, terms in matched_by_group.items() if terms
    }
    item["category"] = classify_item(item)
    item["why_relevant"] = why_relevant(item)
    item["identity"] = item.get("identity") or item_identity(item)
    return item


def classify_item(item: dict[str, Any]) -> str:
    groups = item.get("matched_keywords", {})
    if groups.get("heritage_research"):
        return "遗产、旅游与平台研究"
    text_lower = clean_text(" ".join([item.get("title", ""), item.get("abstract", "")])).lower()
    if groups.get("generative_ai_society") and _has_ai_anchor(text_lower):
        return "生成AI与社会研究"
    if groups.get("japan_china") or groups.get("japanese_terms"):
        return "日本社会与中日比较"
    return "社会学与理论动态"


def why_relevant(item: dict[str, Any]) -> str:
    groups = item.get("matched_keywords", {})
    text_lower = clean_text(" ".join([item.get("title", ""), item.get("abstract", "")])).lower()
    pieces = []
    if groups.get("heritage_research"):
        pieces.append("命中遗产、旅游、平台表征或军舰岛相关关键词")
    if groups.get("generative_ai_society") and _has_ai_anchor(text_lower):
        pieces.append("涉及生成AI、教育、非使用、人机关系或社会支持")
    if groups.get("japan_china") or groups.get("japanese_terms"):
        pieces.append("包含日本、东亚或中日比较线索")
    if groups.get("sociology_core") or groups.get("chinese_terms"):
        pieces.append("具有社会学核心议题信号")
    if item.get("has_method_or_theory_signal"):
        pieces.append("可能包含理论或方法启发")
    return "；".join(pieces) or "相关性较弱，建议仅快速扫读"


def update_seen_items(seen_items: dict[str, Any], selected: list[dict[str, Any]], run_date: str) -> dict[str, Any]:
    seen_items.setdefault("items", {})
    for item in selected:
        identity = item.get("identity") or item_identity(item)
        seen_items["items"][identity] = {
            "title": item.get("title", ""),
            "doi": normalize_doi(item.get("doi")),
            "openalex_id": item.get("openalex_id", ""),
            "arxiv_id": item.get("arxiv_id", ""),
            "url": item.get("url", ""),
            "source_name": item.get("source_name", ""),
            "relevance_score": item.get("relevance_score", 0),
            "last_included": run_date,
        }
    return seen_items


def _contains_term(text: str, text_lower: str, term: str) -> bool:
    term = str(term).strip()
    if not term:
        return False
    if any("\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff" for ch in term):
        return term in text
    if re_matchable_single_word(term):
        return bool(re.search(rf"\b{re.escape(term.lower())}\b", text_lower))
    return term.lower() in text_lower


def _has_ai_anchor(text_lower: str) -> bool:
    anchors = [
        "generative ai",
        "chatgpt",
        "large language model",
        " llm",
        "artificial intelligence",
        "human-ai",
        "ai use",
        "ai education",
        "ai non-use",
        "ai-assisted",
        "生成ai",
        "人工智能",
    ]
    return any(anchor in text_lower for anchor in anchors)


def re_matchable_single_word(term: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]*", term))


def _merge_items(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    merged = dict(a)
    for field in ["doi", "openalex_id", "arxiv_id", "url", "abstract", "venue", "published_date", "year"]:
        if not merged.get(field) and b.get(field):
            merged[field] = b[field]
    if len(clean_text(b.get("abstract", ""))) > len(clean_text(merged.get("abstract", ""))):
        merged["abstract"] = b.get("abstract", "")
    merged["source_name"] = " / ".join(sorted(set(filter(None, [a.get("source_name"), b.get("source_name")]))))
    merged["raw_keywords"] = sorted(set((a.get("raw_keywords") or []) + (b.get("raw_keywords") or [])))
    if not merged.get("title") or len(normalize_title(b.get("title", ""))) > len(normalize_title(merged.get("title", ""))):
        merged["title"] = b.get("title", merged.get("title", ""))
    return merged
