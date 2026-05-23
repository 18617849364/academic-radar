from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from common import BASE_DIR, clean_text, item_identity, load_json, save_json, stable_hash, truncate


def add_chinese_translations(items: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    translation_config = config.get("translation", {})
    if not translation_config.get("enabled", True):
        return [_fallback_translation(item) for item in items]

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    cache_path = BASE_DIR / "data" / "source_cache" / "translations.json"
    cache = load_json(cache_path, {})
    translated: list[dict[str, Any]] = []
    max_items = int(translation_config.get("max_items_per_run", len(items)))

    for idx, item in enumerate(items):
        item = dict(item)
        key = _translation_key(item)
        if key in cache:
            item.update(cache[key])
            translated.append(item)
            continue
        if not api_key or idx >= max_items:
            item = _fallback_translation(item)
            translated.append(item)
            continue
        result = _translate_with_openai(item, api_key, translation_config)
        if result:
            cache[key] = result
            item.update(result)
        else:
            item = _fallback_translation(item)
        translated.append(item)

    save_json(cache_path, cache)
    return translated


def _translate_with_openai(item: dict[str, Any], api_key: str, translation_config: dict[str, Any]) -> dict[str, str] | None:
    title = clean_text(item.get("title"))
    abstract = clean_text(item.get("abstract"))
    if _mostly_chinese(title) and (not abstract or _mostly_chinese(abstract)):
        return {
            "title_zh": title,
            "summary_zh": truncate(abstract, 220) if abstract else "摘要缺失，需人工查看。",
            "translation_note": "原文已是中文或日文，未调用翻译。",
        }

    prompt = {
        "title": title,
        "abstract_or_summary": truncate(abstract, 1400) if abstract else "",
        "source": item.get("source_name", ""),
        "type": item.get("item_type", ""),
    }
    system = (
        "你是给社会学研究生使用的学术雷达翻译助手。只能根据用户提供的标题、摘要和来源信息翻译，"
        "不得补充论文没有提供的内容，不得声称读过全文。返回严格 JSON："
        '{"title_zh":"中文题名","summary_zh":"不超过180字的中文速读摘要","translation_note":"简短说明"}。'
        "如果没有摘要，summary_zh 必须包含“摘要缺失，需人工查看”。"
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": translation_config.get("model", "gpt-4o-mini"),
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
            },
            timeout=45,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return {
            "title_zh": clean_text(parsed.get("title_zh")) or title,
            "summary_zh": clean_text(parsed.get("summary_zh")) or _fallback_summary(item),
            "translation_note": clean_text(parsed.get("translation_note")) or "由标题和摘要自动翻译。",
        }
    except Exception as exc:
        logging.exception("OpenAI translation failed for %s", title)
        return None


def _fallback_translation(item: dict[str, Any]) -> dict[str, Any]:
    item = dict(item)
    title = clean_text(item.get("title"))
    abstract = clean_text(item.get("abstract"))
    if _mostly_chinese(title):
        item["title_zh"] = title
        item["summary_zh"] = truncate(abstract, 220) if abstract else "摘要缺失，需人工查看。"
        item["translation_note"] = "原文已是中文。"
    else:
        item["title_zh"] = "未启用自动翻译，见原题。"
        item["summary_zh"] = _fallback_summary(item)
        item["translation_note"] = "未配置 OPENAI_API_KEY，仅保留原文摘要。"
    return item


def _fallback_summary(item: dict[str, Any]) -> str:
    abstract = clean_text(item.get("abstract"))
    if not abstract:
        return "摘要缺失，需人工查看。"
    return f"未启用自动翻译；原文摘要摘录：{truncate(abstract, 160)}"


def _translation_key(item: dict[str, Any]) -> str:
    raw = "|".join([item_identity(item), clean_text(item.get("title")), clean_text(item.get("abstract"))])
    return stable_hash(raw)


def _mostly_chinese(text: str) -> bool:
    text = clean_text(text)
    if not text:
        return False
    if any("\u3040" <= ch <= "\u30ff" for ch in text):
        return False
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    letters = sum(1 for ch in text if ch.isalpha())
    return cjk > 0 and cjk >= max(2, letters * 0.3)
