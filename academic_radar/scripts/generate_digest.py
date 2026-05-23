from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import DIGEST_DIR, clean_text, truncate


SECTION_ORDER = [
    "社会学与理论动态",
    "遗产、旅游与平台研究",
    "生成AI与社会研究",
    "日本社会与中日比较",
]


def write_digest(
    selected: list[dict[str, Any]],
    all_scored: list[dict[str, Any]],
    source_meta: list[dict[str, Any]],
    run_date: str,
) -> tuple[Path, str, str]:
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    markdown = build_full_digest(selected, all_scored, source_meta, run_date)
    digest_path = DIGEST_DIR / f"{run_date}_academic_digest.md"
    digest_path.write_text(markdown, encoding="utf-8")
    mobile = build_mobile_digest(selected, run_date, digest_path)
    return digest_path, markdown, mobile


def build_full_digest(
    selected: list[dict[str, Any]],
    all_scored: list[dict[str, Any]],
    source_meta: list[dict[str, Any]],
    run_date: str,
) -> str:
    candidate_count = sum(int(meta.get("count", 0)) for meta in source_meta if meta.get("enabled", True))
    source_line = "；".join(
        f"{meta.get('source')}={meta.get('count', 0)}" for meta in source_meta if meta.get("enabled", True)
    )
    top_topics = _top_topics(selected)
    best_directions = _best_directions(selected)
    lines = [
        f"# 每日学术雷达 {run_date}",
        "",
        "## 今日概览",
        "",
        f"- 今日检索来源：{source_line or '无'}",
        f"- 候选条目数量：{candidate_count}",
        f"- 最终纳入条目数量：{len(selected)}",
        f"- 今日最值得关注的主题：{top_topics or '暂无明显主题'}",
        f"- 与我研究最相关的方向：{best_directions or '暂无高相关方向'}",
        "",
        "## 一、最值得读的 3 条",
        "",
    ]

    for idx, item in enumerate(selected[:3], start=1):
        lines.extend(_item_block(idx, item))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in selected:
        grouped[item.get("category", "社会学与理论动态")].append(item)

    headings = {
        "社会学与理论动态": "## 二、社会学与理论动态",
        "遗产、旅游与平台研究": "## 三、遗产、旅游与平台研究",
        "生成AI与社会研究": "## 四、生成AI与社会研究",
        "日本社会与中日比较": "## 五、日本社会与中日比较",
    }
    for section in SECTION_ORDER:
        lines.extend(["", headings[section], ""])
        entries = grouped.get(section, [])
        if not entries:
            lines.append("今日未筛出高相关新条目。")
            continue
        for item in entries:
            lines.extend(
                [
                    f"### {_safe_title(item)}",
                    f"- 中文题名：{_title_zh(item)}",
                    f"- 作者：{_authors(item)}",
                    f"- 年份：{item.get('year') or '未知'}",
                    f"- 来源：{item.get('venue') or item.get('source_name') or '未知'}",
                    f"- 链接：{item.get('url') or '无稳定链接'}",
                    f"- 类型：{item.get('item_type') or '未知'}",
                    f"- 关键词：{_keywords(item)}",
                    f"- 原文摘要：{_summary(item)}",
                    f"- 中文速读：{_summary_zh(item)}",
                    f"- 为什么值得我看：{item.get('why_relevant') or '需要人工判断'}",
                    f"- 和我的研究关系：{_research_relation(item)}",
                    f"- 建议阅读优先级：{_priority(item)}",
                    "",
                ]
            )

    lines.extend(
        [
            "## 六、今天可以顺手记录的研究灵感",
            "",
            *_research_ideas(selected),
            "",
            "## 七、后续可追踪文献",
            "",
            "| title | author | source | link | reason |",
            "|---|---|---|---|---|",
        ]
    )
    for item in selected[3:12]:
        lines.append(
            f"| {_escape_table(_safe_title(item))} | {_escape_table(_authors(item, short=True))} | "
            f"{_escape_table(item.get('venue') or item.get('source_name') or '未知')} | "
            f"{_escape_table(item.get('url') or '无稳定链接')} | {_escape_table(item.get('why_relevant') or '')} |"
        )
    if not selected[3:12]:
        lines.append("| 暂无 |  |  |  |  |")

    return "\n".join(lines).strip() + "\n"


def build_mobile_digest(selected: list[dict[str, Any]], run_date: str, digest_path: Path) -> str:
    readable = [item for item in selected if not _is_mobile_noise(item)]
    picks: list[dict[str, Any]] = []
    for category in ["遗产、旅游与平台研究", "生成AI与社会研究", "日本社会与中日比较", "社会学与理论动态"]:
        item = _first_by_category(readable, category)
        if item and item not in picks:
            picks.append(item)
        if len(picks) >= 3:
            break
    for item in readable:
        if len(picks) >= 3:
            break
        if item not in picks:
            picks.append(item)

    lines = [f"今日学术雷达 {run_date}", "只推最值得扫的 3 条：", ""]
    if not picks:
        lines.append("今天没有筛出足够干净的高相关条目，建议只看完整日报。")
    for idx, item in enumerate(picks[:3], start=1):
        lines.extend(_mobile_item(idx, item))
    lines.extend(["研究灵感：", *_research_ideas(readable or selected, mobile=True), "", f"完整日报：{digest_path}"])
    return "\n".join(lines).strip()[:1800]


def _item_block(idx: int, item: dict[str, Any]) -> list[str]:
    return [
        f"### {idx}. {_safe_title(item)}",
        f"中文题名：{_title_zh(item)}",
        f"作者：{_authors(item)}",
        f"年份：{item.get('year') or '未知'}",
        f"来源：{item.get('venue') or item.get('source_name') or '未知'}",
        f"链接：{item.get('url') or '无稳定链接'}",
        f"类型：{item.get('item_type') or '未知'}",
        f"关键词：{_keywords(item)}",
        f"原文摘要：{_summary(item)}",
        f"中文速读：{_summary_zh(item)}",
        f"为什么值得我看：{item.get('why_relevant') or '需要人工判断'}",
        f"和我的研究关系：{_research_relation(item)}",
        f"建议阅读优先级：{_priority(item)}",
        "",
    ]


def _mobile_slot(label: str, item: dict[str, Any] | None, include_relation: bool = False) -> list[str]:
    if not item:
        return [label, "今日暂无高相关条目。", ""]
    mobile_title = _title_zh(item)
    if mobile_title.startswith("未启用"):
        mobile_title = _safe_title(item)
    lines = [label, f"《{mobile_title}》", f"一句话：{_summary_zh(item, 130)}"]
    if include_relation:
        lines.append(f"与你研究的关系：{_research_relation(item, 130)}")
    lines.append("")
    return lines


def _mobile_item(idx: int, item: dict[str, Any]) -> list[str]:
    title = _mobile_title(item)
    return [
        f"{idx}. {title}",
        f"看点：{_mobile_summary(item)}",
        f"关系：{_research_relation(item, 90)}",
        "",
    ]


def _mobile_title(item: dict[str, Any], max_chars: int = 54) -> str:
    title_zh = _title_zh(item)
    if title_zh and not title_zh.startswith("未启用"):
        title = title_zh
    else:
        title = _safe_title(item)
    return f"《{truncate(title, max_chars)}》"


def _mobile_summary(item: dict[str, Any]) -> str:
    summary_zh = clean_text(item.get("summary_zh", ""))
    if summary_zh and not summary_zh.startswith("未启用自动翻译"):
        return truncate(summary_zh, 95)
    abstract = clean_text(item.get("abstract", ""))
    if _looks_chinese(abstract):
        return truncate(abstract, 95)
    category = item.get("category", "学术动态")
    item_type = item.get("item_type", "条目")
    return f"{category}方向的{item_type}；当前未配置自动翻译，建议打开完整日报查看原文摘要。"


def _summary(item: dict[str, Any], max_chars: int = 180) -> str:
    abstract = clean_text(item.get("abstract", ""))
    if not abstract:
        return "摘要缺失，需人工查看。"
    return truncate(abstract, max_chars)


def _title_zh(item: dict[str, Any]) -> str:
    return clean_text(item.get("title_zh")) or "未启用自动翻译，见原题。"


def _summary_zh(item: dict[str, Any], max_chars: int = 180) -> str:
    summary = clean_text(item.get("summary_zh"))
    if summary:
        return truncate(summary, max_chars)
    return "中文摘要缺失，需人工查看。"


def _looks_chinese(text: str) -> bool:
    text = clean_text(text)
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff") >= 8


def _is_mobile_noise(item: dict[str, Any]) -> bool:
    text = clean_text(" ".join([item.get("title", ""), item.get("abstract", "")])).lower()
    noise_terms = [
        "ニュース・メール",
        "報告申込",
        "大会の報告募集",
        "助成",
        "募集",
        "公募",
        "newsletter",
        "call for papers",
        "annual meeting application",
    ]
    return item.get("item_type") in {"RSS", "学术动态", "中文学术平台"} and any(term.lower() in text for term in noise_terms)


def _research_relation(item: dict[str, Any], max_chars: int = 180) -> str:
    relation = item.get("why_relevant") or "需要人工判断与当前研究的关系。"
    return truncate(relation, max_chars)


def _safe_title(item: dict[str, Any]) -> str:
    return clean_text(item.get("title")) or "Untitled"


def _authors(item: dict[str, Any], short: bool = False) -> str:
    authors = item.get("authors") or []
    if not authors:
        return "未知作者"
    if short:
        return authors[0] + (" et al." if len(authors) > 1 else "")
    if len(authors) > 5:
        return "，".join(authors[:5]) + " 等"
    return "，".join(authors)


def _keywords(item: dict[str, Any]) -> str:
    kws = []
    for terms in (item.get("matched_keywords") or {}).values():
        kws.extend(terms)
    if not kws:
        kws = item.get("raw_keywords") or []
    return "，".join(dict.fromkeys(kws[:10])) or "未标注"


def _priority(item: dict[str, Any]) -> str:
    score = item.get("relevance_score", 0)
    if score >= 10:
        return "高"
    if score >= 6:
        return "中"
    return "低"


def _first_by_category(items: list[dict[str, Any]], category: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("category") == category:
            return item
    return None


def _top_topics(items: list[dict[str, Any]]) -> str:
    counter = Counter()
    for item in items:
        for terms in (item.get("matched_keywords") or {}).values():
            counter.update(terms[:3])
    return "，".join(term for term, _ in counter.most_common(6))


def _best_directions(items: list[dict[str, Any]]) -> str:
    counter = Counter(item.get("category", "未分类") for item in items)
    return "，".join(name for name, _ in counter.most_common(3))


def _research_ideas(items: list[dict[str, Any]], mobile: bool = False) -> list[str]:
    if not items:
        return ["- 今天没有足够强的新材料，可以回看既有文献笔记并补关键词。"]
    ideas = []
    categories = {item.get("category") for item in items}
    if "遗产、旅游与平台研究" in categories:
        ideas.append("- 比较平台评论中的“遗产真实性”与“旅游体验便利性”如何共同塑造目的地形象。")
    if "生成AI与社会研究" in categories:
        ideas.append("- 记录生成AI使用/非使用背后的付费门槛、信任关系和求助对象变化。")
    if "日本社会与中日比较" in categories:
        ideas.append("- 留意日本语境中的记忆政治、青年经验或大学制度如何影响技术与遗产叙事。")
    if not ideas:
        ideas.append("- 从今日条目的理论词汇中挑一个概念，写一段它如何连接你的论文问题。")
    return ideas[:2] if mobile else (ideas + ["- 把高相关条目的关键词加入下一轮检索词，观察一周内是否形成稳定议题。"])[:3]


def _escape_table(value: str) -> str:
    return clean_text(value).replace("|", "\\|")
