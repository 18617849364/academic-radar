from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from common import DIGEST_DIR, clean_text, truncate
from generate_digest import _research_ideas


FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"


def write_pdf_brief(
    selected: list[dict[str, Any]],
    source_meta: list[dict[str, Any]],
    run_date: str,
    digest_path: Path,
) -> Path:
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = DIGEST_DIR / f"{run_date}_academic_brief.pdf"
    _register_fonts()

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"每日学术雷达 {run_date}",
        author="Academic Radar",
    )
    styles = _styles()
    story: list[Any] = []

    story.append(Paragraph(f"每日学术雷达 <font color='#64748B'>{run_date}</font>", styles["Title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(_rule("#0F766E", 1.2))
    story.append(Spacer(1, 5 * mm))

    overview = _overview_table(selected, source_meta, styles)
    story.append(overview)
    story.append(Spacer(1, 7 * mm))

    story.append(Paragraph("Top 3 - 值得认真看的条目", styles["Section"]))
    story.append(Spacer(1, 2.5 * mm))
    for index, item in enumerate(_mobile_picks(selected), 1):
        story.append(_item_card(index, item, styles))
        story.append(Spacer(1, 3 * mm))

    trackers = [item for item in selected if item not in _mobile_picks(selected)]
    if trackers:
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph("其他值得追踪", styles["Section"]))
        story.append(_tracker_table(trackers[:7], styles))
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("今天可以顺手记下", styles["Section"]))
    ideas = _research_ideas(selected, mobile=True)
    for idea in ideas:
        story.append(Paragraph(idea.replace("- ", "• "), styles["Idea"]))

    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            f"完整 Markdown 日报：{clean_text(str(digest_path))}",
            styles["Footer"],
        )
    )

    doc.build(story)
    return pdf_path


def _register_fonts() -> None:
    if "RadarSong" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("RadarSong", FONT_PATH, subfontIndex=0))
    if "RadarSongBold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("RadarSongBold", FONT_PATH, subfontIndex=1))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "RadarTitle",
            parent=base["Title"],
            fontName="RadarSongBold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "Section": ParagraphStyle(
            "RadarSection",
            fontName="RadarSongBold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#0F766E"),
            spaceAfter=2,
        ),
        "Metric": ParagraphStyle(
            "RadarMetric",
            fontName="RadarSongBold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0F172A"),
        ),
        "MetricLabel": ParagraphStyle(
            "RadarMetricLabel",
            fontName="RadarSong",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        ),
        "ItemTitle": ParagraphStyle(
            "RadarItemTitle",
            fontName="RadarSongBold",
            fontSize=10.6,
            leading=13.4,
            textColor=colors.HexColor("#111827"),
            spaceAfter=2,
        ),
        "Body": ParagraphStyle(
            "RadarBody",
            fontName="RadarSong",
            fontSize=8.2,
            leading=11,
            textColor=colors.HexColor("#334155"),
        ),
        "Meta": ParagraphStyle(
            "RadarMeta",
            fontName="RadarSong",
            fontSize=7.4,
            leading=9.5,
            textColor=colors.HexColor("#64748B"),
        ),
        "Idea": ParagraphStyle(
            "RadarIdea",
            fontName="RadarSong",
            fontSize=8.8,
            leading=11.5,
            textColor=colors.HexColor("#334155"),
            leftIndent=4,
            spaceBefore=1,
        ),
        "Footer": ParagraphStyle(
            "RadarFooter",
            fontName="RadarSong",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748B"),
        ),
    }


def _overview_table(selected: list[dict[str, Any]], source_meta: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    source_count = sum(int(meta.get("count", 0)) for meta in source_meta if meta.get("enabled", True))
    cells = [
        _metric("候选", str(source_count), styles),
        _metric("纳入", str(len(selected)), styles),
        _metric("重点", _top_direction(selected), styles),
    ]
    table = Table([cells], colWidths=[45 * mm, 45 * mm, 70 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _metric(label: str, value: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [Paragraph(value, styles["Metric"]), Paragraph(label, styles["MetricLabel"])]


def _item_card(index: int, item: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    title = _title(item)
    original_title = truncate(clean_text(item.get("title")), 110)
    summary = _summary(item)
    relation = truncate(clean_text(item.get("why_relevant")) or "需要人工判断。", 185)
    authors = _authors(item)
    keywords = _keywords(item)
    link = clean_text(item.get("url") or item.get("doi") or "无稳定链接")
    meta = " · ".join(
        part
        for part in [
            item.get("item_type") or "条目",
            item.get("venue") or item.get("source_name") or "",
            str(item.get("year") or ""),
        ]
        if part
    )
    content = [
        Paragraph(f"{index}. {_e(title)}", styles["ItemTitle"]),
        Paragraph(f"<font color='#64748B'>原题</font>：{_e(original_title)}", styles["Meta"]),
        Paragraph(f"<font color='#0F766E'>作者/来源</font>：{_e(authors)} ｜ {_e(meta)}", styles["Body"]),
        Paragraph(f"<font color='#0F766E'>关键词</font>：{_e(keywords)}", styles["Body"]),
        Paragraph(f"<font color='#0F766E'>研究了什么</font>：{_e(summary)}", styles["Body"]),
        Paragraph(f"<font color='#0F766E'>与你研究的关系</font>：{_e(relation)}", styles["Body"]),
        Paragraph(f"链接：{_e(link)}", styles["Meta"]),
    ]
    table = Table([[content]], colWidths=[166 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#CBD5E1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _tracker_table(items: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[
        Paragraph("条目", styles["Meta"]),
        Paragraph("研究了什么", styles["Meta"]),
        Paragraph("与你关系", styles["Meta"]),
    ]]
    for item in items:
        title = _title(item)
        source = " ｜ ".join(
            part
            for part in [
                clean_text(item.get("venue") or item.get("source_name")),
                clean_text(item.get("item_type")),
            ]
            if part
        )
        rows.append(
            [
                Paragraph(_e(truncate(f"{title}\n{source}", 82)), styles["Body"]),
                Paragraph(_e(_short_study(item)), styles["Body"]),
                Paragraph(_e(truncate(clean_text(item.get("why_relevant")), 72)), styles["Body"]),
            ]
        )
    table = Table(rows, colWidths=[58 * mm, 66 * mm, 42 * mm], hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECFDF5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _mobile_picks(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = [item for item in selected if not _is_noise(item)]
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


def _title(item: dict[str, Any]) -> str:
    title_zh = clean_text(item.get("title_zh"))
    if title_zh and not title_zh.startswith("未启用"):
        return truncate(title_zh, 88)
    return truncate(clean_text(item.get("title")) or "Untitled", 88)


def _summary(item: dict[str, Any]) -> str:
    summary_zh = clean_text(item.get("summary_zh"))
    if summary_zh and not summary_zh.startswith("未启用自动翻译"):
        return truncate(summary_zh, 330)
    abstract = clean_text(item.get("abstract"))
    if _looks_chinese(abstract):
        return truncate(abstract, 330)
    if abstract:
        return f"原文摘要摘录：{truncate(abstract, 305)}"
    return f"{item.get('category', '学术动态')}方向；摘要缺失，需人工查看。"


def _short_study(item: dict[str, Any]) -> str:
    text = _summary(item)
    text = text.replace("原文摘要摘录：", "")
    return truncate(text, 105)


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
    return "，".join(dict.fromkeys(kws[:7])) or "未标注"


def _top_direction(selected: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in selected:
        category = item.get("category", "未分类")
        counts[category] = counts.get(category, 0) + 1
    if not counts:
        return "暂无"
    return max(counts.items(), key=lambda pair: pair[1])[0].replace("研究", "")


def _looks_chinese(text: str) -> bool:
    return sum(1 for ch in clean_text(text) if "\u4e00" <= ch <= "\u9fff") >= 8


def _is_noise(item: dict[str, Any]) -> bool:
    text = clean_text(" ".join([item.get("title", ""), item.get("abstract", "")])).lower()
    noise_terms = ["ニュース・メール", "報告申込", "助成", "募集", "newsletter", "call for papers"]
    return item.get("item_type") in {"RSS", "学术动态", "中文学术平台"} and any(term.lower() in text for term in noise_terms)


def _rule(color: str, height: float) -> Flowable:
    class Rule(Flowable):
        def __init__(self) -> None:
            super().__init__()
            self.height = height

        def draw(self) -> None:
            self.canv.setStrokeColor(colors.HexColor(color))
            self.canv.setLineWidth(height)
            self.canv.line(0, 0, 162 * mm, 0)

    return Rule()


def _e(text: str) -> str:
    return escape(clean_text(text))
