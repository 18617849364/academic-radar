from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from common import SITE_DIR, clean_text, truncate
from generate_digest import _research_ideas


def write_site(
    selected: list[dict[str, Any]],
    source_meta: list[dict[str, Any]],
    run_date: str,
    digest_path: Path,
    pdf_path: Path,
) -> dict[str, str]:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    digest_site_dir = SITE_DIR / "digests"
    digest_site_dir.mkdir(parents=True, exist_ok=True)

    pdf_target = digest_site_dir / pdf_path.name
    if pdf_path.exists():
        shutil.copy2(pdf_path, pdf_target)

    html = _page_html(selected, source_meta, run_date, pdf_target.name)
    detail_path = digest_site_dir / f"{run_date}.html"
    detail_path.write_text(html, encoding="utf-8")
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")
    (SITE_DIR / "latest.json").write_text(
        json.dumps(
            {
                "date": run_date,
                "html": f"digests/{run_date}.html",
                "pdf": f"digests/{pdf_target.name}",
                "markdown_local_path": str(digest_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    return {
        "site_dir": str(SITE_DIR),
        "index_path": str(SITE_DIR / "index.html"),
        "detail_path": str(detail_path),
        "pdf_path": str(pdf_target),
        "public_url": f"{base_url}/" if base_url else "",
        "public_detail_url": f"{base_url}/digests/{run_date}.html" if base_url else "",
        "public_pdf_url": f"{base_url}/digests/{pdf_target.name}" if base_url else "",
    }


def _page_html(selected: list[dict[str, Any]], source_meta: list[dict[str, Any]], run_date: str, pdf_name: str) -> str:
    top = _picks(selected)
    rest = [item for item in selected if item not in top]
    source_count = sum(int(meta.get("count", 0)) for meta in source_meta if meta.get("enabled", True))
    cards = "\n".join(_top_card(index, item) for index, item in enumerate(top, 1))
    table_rows = "\n".join(_row(item) for item in rest[:9]) or "<tr><td colspan='3'>今日暂无其他高相关条目。</td></tr>"
    ideas = "\n".join(f"<li>{_h(idea.replace('- ', ''))}</li>" for idea in _research_ideas(selected, mobile=True))
    pdf_href = f"digests/{_h(pdf_name)}"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>每日学术雷达 {run_date}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink:#172033;
      --muted:#64748b;
      --line:#d8e0ea;
      --paper:#ffffff;
      --wash:#f6f8fb;
      --accent:#0f766e;
      --accent-soft:#e7f7f4;
      --mark:#a16207;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:var(--wash);
      color:var(--ink);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
      line-height:1.62;
    }}
    main {{
      max-width:980px;
      margin:0 auto;
      padding:28px 18px 44px;
    }}
    header {{
      border-bottom:3px solid var(--accent);
      padding-bottom:18px;
      margin-bottom:22px;
    }}
    h1 {{
      margin:0;
      font-size:clamp(28px,5vw,46px);
      line-height:1.12;
      letter-spacing:0;
    }}
    .date {{ color:var(--muted); font-weight:500; }}
    .metrics {{
      display:grid;
      grid-template-columns:repeat(3,minmax(0,1fr));
      gap:1px;
      background:var(--line);
      border:1px solid var(--line);
      margin:18px 0 0;
    }}
    .metric {{ background:var(--paper); padding:14px; }}
    .metric strong {{ display:block; font-size:24px; line-height:1.1; }}
    .metric span {{ color:var(--muted); font-size:13px; }}
    .toolbar {{
      display:flex;
      flex-wrap:wrap;
      gap:10px;
      margin:18px 0 28px;
    }}
    a.button {{
      color:#fff;
      background:var(--accent);
      text-decoration:none;
      padding:10px 13px;
      border-radius:6px;
      font-weight:700;
    }}
    section {{ margin:26px 0; }}
    h2 {{
      margin:0 0 12px;
      color:var(--accent);
      font-size:22px;
      letter-spacing:0;
    }}
    article {{
      background:var(--paper);
      border:1px solid var(--line);
      border-left:5px solid var(--accent);
      padding:16px;
      margin:14px 0;
    }}
    h3 {{
      margin:0 0 8px;
      font-size:20px;
      line-height:1.35;
      letter-spacing:0;
    }}
    .meta, .link {{
      color:var(--muted);
      font-size:14px;
      overflow-wrap:anywhere;
    }}
    .label {{
      color:var(--accent);
      font-weight:800;
    }}
    .original {{
      color:var(--muted);
      font-size:14px;
      margin:4px 0 10px;
    }}
    p {{ margin:7px 0; }}
    table {{
      width:100%;
      border-collapse:collapse;
      background:var(--paper);
      border:1px solid var(--line);
      table-layout:fixed;
    }}
    th, td {{
      border:1px solid var(--line);
      padding:10px;
      vertical-align:top;
      overflow-wrap:anywhere;
    }}
    th {{
      text-align:left;
      color:var(--accent);
      background:var(--accent-soft);
      font-size:14px;
    }}
    ul {{
      background:var(--paper);
      border:1px solid var(--line);
      padding:14px 18px 14px 34px;
    }}
    footer {{
      color:var(--muted);
      border-top:1px solid var(--line);
      padding-top:16px;
      font-size:13px;
    }}
    @media (max-width:720px) {{
      main {{ padding:20px 12px 34px; }}
      .metrics {{ grid-template-columns:1fr; }}
      article {{ padding:13px; }}
      h3 {{ font-size:18px; }}
      table, thead, tbody, tr, th, td {{ display:block; width:100%; }}
      thead {{ display:none; }}
      tr {{ border-bottom:1px solid var(--line); }}
      td {{ border:0; border-bottom:1px solid #edf1f6; }}
      td::before {{
        content:attr(data-label);
        display:block;
        color:var(--accent);
        font-weight:800;
        margin-bottom:3px;
      }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>每日学术雷达 <span class="date">{run_date}</span></h1>
    <div class="metrics">
      <div class="metric"><strong>{source_count}</strong><span>候选条目</span></div>
      <div class="metric"><strong>{len(selected)}</strong><span>最终纳入</span></div>
      <div class="metric"><strong>{_h(_top_direction(selected))}</strong><span>今日重点</span></div>
    </div>
  </header>
  <div class="toolbar">
    <a class="button" href="{pdf_href}">打开 PDF 简报</a>
  </div>
  <section>
    <h2>Top 3：值得认真看的条目</h2>
    {cards}
  </section>
  <section>
    <h2>其他值得追踪</h2>
    <table>
      <thead><tr><th>条目</th><th>研究了什么</th><th>与你关系</th></tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
  </section>
  <section>
    <h2>今天可以顺手记下</h2>
    <ul>{ideas}</ul>
  </section>
  <footer>由 Academic Radar 自动生成。摘要只基于标题、摘要和来源元数据，不声称已阅读全文。</footer>
</main>
</body>
</html>
"""


def _top_card(index: int, item: dict[str, Any]) -> str:
    title = _title(item, 90)
    original = truncate(clean_text(item.get("title")) or "Untitled", 130)
    source = clean_text(item.get("venue") or item.get("source_name") or "未知来源")
    authors = _authors(item)
    year = clean_text(item.get("year") or "")
    study = _summary(item, 420)
    relation = truncate(clean_text(item.get("why_relevant")) or "需要人工判断。", 240)
    keywords = _keywords(item)
    link = clean_text(item.get("url") or "无稳定链接")
    return f"""<article>
  <h3>{index}. {_h(title)}</h3>
  <div class="original">原题：{_h(original)}</div>
  <p class="meta">{_h(authors)} ｜ {_h(source)} ｜ {_h(year)}</p>
  <p><span class="label">关键词</span>：{_h(keywords)}</p>
  <p><span class="label">研究了什么</span>：{_h(study)}</p>
  <p><span class="label">与你研究的关系</span>：{_h(relation)}</p>
  <p class="link">链接：{_link(link)}</p>
</article>"""


def _row(item: dict[str, Any]) -> str:
    title = _title(item, 72)
    source = truncate(clean_text(item.get("venue") or item.get("source_name") or ""), 42)
    study = _summary(item, 160)
    relation = truncate(clean_text(item.get("why_relevant")) or "需要人工判断。", 120)
    return f"""<tr>
  <td data-label="条目"><strong>{_h(title)}</strong><br><span class="meta">{_h(source)}</span></td>
  <td data-label="研究了什么">{_h(study)}</td>
  <td data-label="与你关系">{_h(relation)}</td>
</tr>"""


def _picks(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = [item for item in selected if not _noise(item)]
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


def _title(item: dict[str, Any], max_chars: int) -> str:
    title = clean_text(item.get("title_zh"))
    if not title or title.startswith("未启用"):
        title = clean_text(item.get("title")) or "Untitled"
    return truncate(title, max_chars)


def _summary(item: dict[str, Any], max_chars: int) -> str:
    summary = clean_text(item.get("summary_zh"))
    if summary and not summary.startswith("未启用自动翻译"):
        return truncate(summary, max_chars)
    abstract = clean_text(item.get("abstract"))
    if abstract:
        return truncate(abstract, max_chars)
    return "摘要缺失，需人工查看。"


def _authors(item: dict[str, Any]) -> str:
    authors = item.get("authors") or []
    if not authors:
        return "未知作者"
    if len(authors) > 4:
        return "，".join(authors[:4]) + " 等"
    return "，".join(authors)


def _keywords(item: dict[str, Any]) -> str:
    kws: list[str] = []
    for terms in (item.get("matched_keywords") or {}).values():
        kws.extend(terms)
    if not kws:
        kws = item.get("raw_keywords") or []
    return "，".join(dict.fromkeys(kws[:8])) or "未标注"


def _top_direction(selected: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in selected:
        category = item.get("category", "未分类")
        counts[category] = counts.get(category, 0) + 1
    if not counts:
        return "暂无"
    return max(counts.items(), key=lambda pair: pair[1])[0].replace("研究", "")


def _noise(item: dict[str, Any]) -> bool:
    text = clean_text(" ".join([item.get("title", ""), item.get("abstract", "")])).lower()
    noise_terms = ["ニュース・メール", "報告申込", "助成", "募集", "newsletter", "call for papers"]
    return item.get("item_type") in {"RSS", "学术动态", "中文学术平台"} and any(term.lower() in text for term in noise_terms)


def _link(link: str) -> str:
    if link.startswith(("http://", "https://")):
        escaped = _h(link)
        return f'<a href="{escaped}">{escaped}</a>'
    return _h(link)


def _h(value: Any) -> str:
    import html

    return html.escape(clean_text(value), quote=True)
