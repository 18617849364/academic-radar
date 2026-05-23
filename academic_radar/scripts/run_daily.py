from __future__ import annotations

import json
import logging
from typing import Any, Callable

from common import BASE_DIR, clean_text, load_config, load_environment, load_json, save_json, setup_logging, today_string, truncate
from fetch_arxiv import fetch as fetch_arxiv
from fetch_crossref import fetch as fetch_crossref
from fetch_openalex import fetch as fetch_openalex
from fetch_rss import fetch as fetch_rss
from fetch_web_pages import fetch as fetch_web_pages
from generate_digest import write_digest
from generate_pdf_brief import write_pdf_brief
from generate_site import write_site
from rank_items import dedupe_items, score_and_rank, update_seen_items
from send_notification import send_notification
from translate_items import add_chinese_translations


Fetcher = Callable[[dict[str, Any]], tuple[list[dict[str, Any]], dict[str, Any]]]


def main() -> int:
    load_environment()
    config = load_config()
    run_date = today_string(config)
    log_path = setup_logging(run_date)
    logging.info("每日学术雷达开始运行: %s", run_date)

    fetchers: list[tuple[str, Fetcher]] = [
        ("openalex", fetch_openalex),
        ("arxiv", fetch_arxiv),
        ("rss", fetch_rss),
        ("web_pages", fetch_web_pages),
        ("crossref", fetch_crossref),
    ]

    candidates: list[dict[str, Any]] = []
    source_meta: list[dict[str, Any]] = []
    for name, fetcher in fetchers:
        try:
            items, meta = fetcher(config)
            candidates.extend(items)
            source_meta.append(meta)
        except Exception as exc:
            logging.exception("Source failed unexpectedly: %s", name)
            source_meta.append({"source": name, "enabled": True, "count": 0, "errors": [str(exc)]})

    deduped = dedupe_items(candidates)
    seen_path = BASE_DIR / "data" / "seen_items.json"
    seen_items = load_json(seen_path, {"items": {}})
    selected, all_scored = score_and_rank(deduped, config, seen_items)
    selected = add_chinese_translations(selected, config)

    digest_path, _markdown, mobile_message = write_digest(selected, all_scored, source_meta, run_date)
    pdf_path = write_pdf_brief(selected, source_meta, run_date, digest_path)
    site_info = write_site(selected, source_meta, run_date, digest_path, pdf_path)
    notify_message = _notification_message(selected, pdf_path, digest_path, site_info)
    notify_result = send_notification(notify_message, title=f"每日学术雷达 手机版 {run_date}")
    updated_seen = update_seen_items(seen_items, selected, run_date)
    save_json(seen_path, updated_seen)

    logging.info("候选条目数量: %s", len(candidates))
    logging.info("去重后条目数量: %s", len(deduped))
    logging.info("最终纳入条目数量: %s", len(selected))
    logging.info("日报路径: %s", digest_path)
    logging.info("PDF 简报路径: %s", pdf_path)
    logging.info("静态网页目录: %s", site_info.get("site_dir"))
    logging.info("公网网页: %s", site_info.get("public_detail_url") or "未配置 PUBLIC_BASE_URL")
    logging.info("推送结果: %s", json.dumps(notify_result, ensure_ascii=False))
    logging.info("日志路径: %s", log_path)

    print(json.dumps(
        {
            "run_date": run_date,
            "candidate_count": len(candidates),
            "deduped_count": len(deduped),
            "selected_count": len(selected),
            "digest_path": str(digest_path),
            "pdf_path": str(pdf_path),
            "site": site_info,
            "log_path": str(log_path),
            "notification": notify_result,
            "sources": source_meta,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def _notification_message(selected: list[dict[str, Any]], pdf_path, digest_path, site_info: dict[str, str]) -> str:
    lines = ["今日手机版日报", ""]
    if site_info.get("public_detail_url"):
        lines.append(f"公网网页：{site_info['public_detail_url']}")
    if site_info.get("public_pdf_url"):
        lines.append(f"公网 PDF：{site_info['public_pdf_url']}")
    if site_info.get("public_detail_url") or site_info.get("public_pdf_url"):
        lines.append("")
    picks = _notification_picks(selected)
    if not picks:
        lines.append("今天没有筛出足够干净的高相关条目。")
    for index, item in enumerate(picks[:3], 1):
        lines.extend(_notification_item(index, item, expanded=True))
    rest = [item for item in selected if item not in picks]
    if rest:
        lines.append("其他值得扫一眼")
        for index, item in enumerate(rest[:7], 1):
            title = _notification_title(item, 42)
            study = _notification_summary(item, 95)
            relation = truncate(clean_text(item.get("why_relevant")) or "需要人工判断。", 70)
            lines.append(f"{index}. 《{title}》")
            lines.append(f"研究了什么：{study}")
            lines.append(f"与你关系：{relation}")
            lines.append("")
    lines.append("")
    if not site_info.get("public_detail_url"):
        lines.append("公网 URL 未配置；当前只生成本地网页和 PDF。")
        lines.append(f"本地网页：{site_info.get('index_path', '')}")
    lines.append("PDF 同步生成，用于归档和精读。")
    lines.append(f"电脑 PDF：{pdf_path}")
    lines.append(f"完整 Markdown：{digest_path}")
    return "\n".join(lines)


def _notification_picks(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = [item for item in selected if not _notification_noise(item)]
    picks: list[dict[str, Any]] = []
    for category in ["遗产、旅游与平台研究", "生成AI与社会研究", "日本社会与中日比较", "社会学与理论动态"]:
        for item in clean:
            if item.get("category") == category and item not in picks:
                picks.append(item)
                break
        if len(picks) >= 3:
            break
    for item in clean:
        if len(picks) >= 3:
            break
        if item not in picks:
            picks.append(item)
    return picks[:3]


def _notification_item(index: int, item: dict[str, Any], expanded: bool = False) -> list[str]:
    title = _notification_title(item, 62)
    original_title = truncate(clean_text(item.get("title")) or "Untitled", 92)
    study = _notification_summary(item, 260 if expanded else 130)
    relation = truncate(clean_text(item.get("why_relevant")) or "需要人工判断。", 170 if expanded else 90)
    source = clean_text(item.get("venue") or item.get("source_name") or "未知来源")
    link = clean_text(item.get("url") or "无稳定链接")
    return [
        f"Top {index}. 《{title}》",
        f"原题：{original_title}",
        f"来源：{source}",
        f"研究了什么：{study}",
        f"与你研究的关系：{relation}",
        f"链接：{link}",
        "",
    ]


def _notification_title(item: dict[str, Any], max_chars: int) -> str:
    title = clean_text(item.get("title_zh"))
    if not title or title.startswith("未启用"):
        title = clean_text(item.get("title")) or "Untitled"
    return truncate(title, max_chars)


def _notification_summary(item: dict[str, Any], max_chars: int) -> str:
    summary = clean_text(item.get("summary_zh"))
    if summary and not summary.startswith("未启用自动翻译"):
        return truncate(summary, max_chars)
    abstract = clean_text(item.get("abstract"))
    if abstract:
        return truncate(abstract, max_chars)
    return "摘要缺失，需人工查看。"


def _notification_noise(item: dict[str, Any]) -> bool:
    text = clean_text(" ".join([item.get("title", ""), item.get("abstract", "")])).lower()
    noise_terms = ["ニュース・メール", "報告申込", "助成", "募集", "newsletter", "call for papers"]
    return item.get("item_type") in {"RSS", "学术动态", "中文学术平台"} and any(term.lower() in text for term in noise_terms)


if __name__ == "__main__":
    raise SystemExit(main())
