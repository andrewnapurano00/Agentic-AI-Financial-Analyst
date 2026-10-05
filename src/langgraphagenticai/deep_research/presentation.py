"""Clean executive presentation and PDF export for saved deep research."""
from __future__ import annotations

import html
import io
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


INTERNAL_REF = re.compile(r"\[([^\]\n]{1,180})\]")
SOURCE_LINE = re.compile(r"^\s*\|?\s*(?:sources?|evidence references?)\s*:", re.IGNORECASE)
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{1,}:?\s*)+\|?\s*$")
REPORT_SECTION_PREFIXES = (
    "executive investment thesis", "executive summary", "investment thesis",
    "business quality", "financial trends", "balance-sheet resilience", "balance sheet resilience",
    "ttm vs latest reported period", "forward estimates", "technical trend", "recent news",
    "news, sentiment & catalysts", "news, sentiment and catalysts", "news and sentiment",
    "near-term catalysts", "comparison snapshot", "bull / base / bear", "bull/base/bear",
    "strongest counterargument", "risks and thesis invalidation", "monitoring checklist",
    "open research questions", "bottom line", "relative preference", "currency/period notes",
)

_FONT_DIR = Path(reportlab.__file__).resolve().parent / "fonts"
try:
    pdfmetrics.registerFont(TTFont("ResearchSans", str(_FONT_DIR / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("ResearchSans-Bold", str(_FONT_DIR / "VeraBd.ttf")))
    pdfmetrics.registerFont(TTFont("ResearchSans-Italic", str(_FONT_DIR / "VeraIt.ttf")))
    pdfmetrics.registerFont(TTFont("ResearchSans-BoldItalic", str(_FONT_DIR / "VeraBI.ttf")))
    pdfmetrics.registerFontFamily(
        "ResearchSans", normal="ResearchSans", bold="ResearchSans-Bold",
        italic="ResearchSans-Italic", boldItalic="ResearchSans-BoldItalic",
    )
    BODY_FONT, BOLD_FONT, ITALIC_FONT = "ResearchSans", "ResearchSans-Bold", "ResearchSans-Italic"
    _SUPPORTED_GLYPHS = set(pdfmetrics.getFont(BODY_FONT).face.charWidths)
except Exception:
    BODY_FONT, BOLD_FONT, ITALIC_FONT = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
    _SUPPORTED_GLYPHS = set(range(32, 127)) | {160, 163, 165, 169, 174, 176, 177, 215, 247, 8364}

_UNICODE_REPLACEMENTS = str.maketrans({
    "\u00a0": " ", "\u2007": " ", "\u202f": " ",
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u2192": "->", "\u2191": "up", "\u2193": "down",
    "\u2264": "<=", "\u2265": ">=", "\u2248": "~", "\u2713": "Yes", "\u2714": "Yes",
    "\u2717": "No", "\u2718": "No", "\ufe0f": "",
})


def _font_safe(value) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).translate(_UNICODE_REPLACEMENTS)
    output = []
    for char in text:
        code = ord(char)
        if char in "\n\t" or code in _SUPPORTED_GLYPHS:
            output.append(char)
        elif unicodedata.category(char).startswith(("L", "N")):
            output.append("?")
        elif char.isspace():
            output.append(" ")
    return "".join(output)


def clean_report_markdown(report: str) -> str:
    """Remove internal evidence notation and model-generated source footer rows."""
    cleaned: list[str] = []
    removed_source_row = False
    for raw_line in str(report or "").splitlines():
        line = raw_line.strip()
        if SOURCE_LINE.match(line) or ("sources:" in line.lower() and re.search(r"\bE\d{3}\b", line)):
            removed_source_row = True
            continue
        if removed_source_row and TABLE_RULE.match(line):
            removed_source_row = False
            continue
        removed_source_row = False
        def remove_internal_reference(match: re.Match) -> str:
            content = match.group(1).strip()
            return "" if re.search(r"\bE\d{3}\b", content, re.IGNORECASE) or content.lower() in {
                "comparison", "evidence", "internal comparison",
            } else match.group(0)

        line = INTERNAL_REF.sub(remove_internal_reference, raw_line)
        line = re.sub(r"[ \t]+([,.;:])", r"\1", line)
        line = re.sub(r" {2,}", " ", line).rstrip()
        stripped = line.strip()
        if (stripped and not re.match(r"^(?:#{1,4}\s+|[-*]>?\s+|\d+[.)]\s+|\||>)", stripped)
                and any(stripped.lower().startswith(prefix) for prefix in REPORT_SECTION_PREFIXES)
                and len(stripped) <= 120):
            line = "## " + stripped
        cleaned.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()


def _plain_inline(value: str) -> str:
    text = html.escape(_font_safe(value), quote=True)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def _format_value(value) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:,.1f}B"
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:,.1f}M"
        return f"{value:,.2f}"
    return _font_safe(value)


def _financial_basis_table(rows: list[dict], body_style: ParagraphStyle) -> Table | None:
    """Show TTM and the selected reported period side by side without conflating them."""
    basis_fields = (
        "Revenue (TTM)", "Operating margin (TTM)", "Net income (TTM)", "Free cash flow (TTM)",
        "Revenue (latest period)", "Operating margin (latest period)",
        "Net income (latest period)", "Free cash flow (latest period)",
    )
    rows = [row for row in rows if any(row.get(field) is not None for field in basis_fields)]
    if not rows:
        return None

    def amount(value, currency) -> str:
        if value is None:
            return "-"
        try:
            number = float(value)
            prefix = f"{currency} " if currency else ""
            if abs(number) >= 1_000_000_000:
                return f"{prefix}{number / 1_000_000_000:,.1f}B"
            if abs(number) >= 1_000_000:
                return f"{prefix}{number / 1_000_000:,.1f}M"
            return f"{prefix}{number:,.1f}"
        except (TypeError, ValueError):
            return _format_value(value)

    def percent(value, derived=False) -> str:
        if value is None:
            return "-"
        try:
            number = float(value)
            return f"{number * 100 if derived or abs(number) <= 2 else number:,.1f}%"
        except (TypeError, ValueError):
            return _format_value(value)

    table_rows = [["Company", "Basis", "Period end", "Revenue", "Op. margin", "Net income", "Free cash flow"]]
    for row in rows:
        derived = bool(row.get("TTM methodology"))
        def cash_amount(value, ttm):
            if not derived:
                return amount(value, (row.get("TTM currency") or row.get("Statement currency")) if ttm else row.get("Statement currency"))
            currency = row.get("Cash flow TTM currency" if ttm else "Cash flow statement currency")
            through = row.get("Cash flow TTM through" if ttm else "Cash flow statement date")
            text = amount(value, currency)
            return text + f" (through {through or 'unavailable'})" if value is not None else text
        ttm_has_statements = any(row.get(field) is not None for field in
                                 ("Revenue (TTM)", "Net income (TTM)", "Free cash flow (TTM)"))
        table_rows.append([
            row.get("Ticker", ""), "TTM" if ttm_has_statements else "TTM ratios", row.get("TTM through") or "-",
            amount(row.get("Revenue (TTM)"), row.get("TTM currency") or row.get("Statement currency")),
            percent(row.get("Operating margin (TTM)"), derived),
            amount(row.get("Net income (TTM)"), row.get("TTM currency") or row.get("Statement currency")),
            cash_amount(row.get("Free cash flow (TTM)"), True),
        ])
        table_rows.append([
            "", str(row.get("Statement period") or "Reported"), row.get("Statement date") or "-",
            amount(row.get("Revenue (latest period)"), row.get("Statement currency")),
            percent(row.get("Operating margin (latest period)"), derived),
            amount(row.get("Net income (latest period)"), row.get("Statement currency")),
            cash_amount(row.get("Free cash flow (latest period)"), False),
        ])
    header_style = ParagraphStyle("BasisHeader", parent=body_style, fontName=BOLD_FONT,
                                  fontSize=7.2, leading=8.5, textColor=colors.white, alignment=TA_CENTER)
    value_style = ParagraphStyle("BasisValue", parent=body_style, fontName=BODY_FONT,
                                 fontSize=7.2, leading=9, textColor=colors.HexColor("#243746"))
    data = [[Paragraph(_plain_inline(str(cell)), header_style if row_index == 0 else value_style)
             for cell in row] for row_index, row in enumerate(table_rows)]
    table = Table(data, colWidths=[0.75 * inch, 0.7 * inch, 0.88 * inch, 1.15 * inch,
                                  0.82 * inch, 1.2 * inch, 1.2 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), BOLD_FONT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7E0E7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _comparison_table(rows: list[dict], body_style: ParagraphStyle,
                      sector_frameworks: list[dict] | None = None) -> Table | None:
    if not rows:
        return None
    default_metrics = [
        ("Price", "Price", "money"),
        ("Estimate period", "Forward period", "text"),
        ("Forward revenue", "Forward revenue", "money"),
        ("Forward revenue growth (%)", "Forward revenue growth", "percent"),
        ("Forward EPS", "Forward EPS", "money"),
        ("P/E (TTM)", "P/E (TTM)", "multiple"),
        ("Forward P/E", "Forward P/E", "multiple"),
        ("P/S (TTM)", "P/S (TTM)", "multiple"),
        ("Forward P/S", "Forward P/S", "multiple"),
        ("EV/EBITDA (TTM)", "EV/EBITDA", "multiple"),
        ("Analyst target", "Analyst target", "money"),
        ("Target upside (%)", "Target upside", "percent"),
    ]
    metrics = default_metrics
    if sector_frameworks:
        ordered = []
        for framework in sector_frameworks:
            for name in framework.get("must_have", []) + framework.get("preferred", []):
                if name not in ordered and any(row.get(name) is not None for row in rows):
                    ordered.append(name)
        def kind_for(name: str) -> str:
            if name.startswith("Forward Revenue") and "Growth" not in name:
                return "money"
            if name in {"Forward EPS Next FY"}:
                return "money"
            if any(term in name for term in ("Margin", "Yield", "Return", "Growth", "CAGR", "% Revenue",
                                              "to Revenue", "Upside", "% From")):
                return "percent"
            if name in {"ROE", "ROA", "ROIC"}:
                return "percent"
            if any(term in name for term in ("P/E", "P/S", "P/B", "P/FCF", "EV /", "Debt / EBITDA")):
                return "multiple"
            return "text"
        metrics = [(name, name, kind_for(name)) for name in ordered[:18]] or default_metrics

    def metric_value(row: dict, key: str, kind: str) -> str:
        value = row.get(key)
        if value is None or value == "":
            return "-"
        if kind == "percent":
            try:
                number = float(value)
                # Provider margins/yields/returns-on-capital are usually fractions;
                # calculated growth and price changes are already percentage points.
                derived_fraction = row.get("TTM methodology") and (any(term in key for term in ("Margin", "margin")) or key in {"ROE", "ROA", "Earnings Yield", "FCF Yield", "FCF yield (TTM, fraction)"})
                if derived_fraction or (abs(number) <= 2 and any(term in key for term in
                                            ("Margin", "Yield", "ROE", "ROA", "ROIC", "Payout"))):
                    number *= 100
                return f"{number:,.1f}%"
            except (TypeError, ValueError):
                return _format_value(value)
        if kind == "multiple":
            try:
                return f"{float(value):,.1f}x"
            except (TypeError, ValueError):
                return _format_value(value)
        if kind == "money":
            try:
                number = float(value)
                if abs(number) >= 1_000_000_000:
                    return f"${number / 1_000_000_000:,.1f}B"
                if abs(number) >= 1_000_000:
                    return f"${number / 1_000_000:,.1f}M"
                return f"${number:,.2f}"
            except (TypeError, ValueError):
                return _format_value(value)
        return _format_value(value)

    symbols = [str(row.get("Ticker") or f"Company {index + 1}") for index, row in enumerate(rows)]
    header_style = ParagraphStyle("MatrixHeader", parent=body_style, fontName=BOLD_FONT,
                                  fontSize=8.2, leading=10, textColor=colors.white, alignment=TA_CENTER)
    label_style = ParagraphStyle("MatrixLabel", parent=body_style, fontName=BOLD_FONT,
                                 fontSize=8, leading=10, textColor=colors.HexColor("#243746"))
    value_style = ParagraphStyle("MatrixValue", parent=body_style, fontName=BODY_FONT,
                                 fontSize=8.2, leading=10, textColor=colors.HexColor("#243746"), alignment=TA_CENTER)
    data = [[Paragraph("Key metric", header_style)] + [Paragraph(_plain_inline(symbol), header_style) for symbol in symbols]]
    for key, label, kind in metrics:
        if not any(row.get(key) is not None for row in rows):
            continue
        data.append([Paragraph(_plain_inline(label), label_style)] +
                    [Paragraph(_plain_inline(metric_value(row, key, kind)), value_style) for row in rows])
    usable = 7.0 * inch
    widths = [2.25 * inch] + [(usable - 2.25 * inch) / len(rows)] * len(rows)
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")]),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor("#2C7A9B")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#D7E0E7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _markdown_table(lines: list[str], body_style: ParagraphStyle) -> Table | None:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in rows[1]):
        rows.pop(1)
    if not rows or not rows[0]:
        return None
    max_cols = max(len(row) for row in rows)
    normalized = [row + [""] * (max_cols - len(row)) for row in rows]
    header_style = ParagraphStyle("MarkdownHeader", parent=body_style, fontName=BOLD_FONT,
                                  textColor=colors.white, fontSize=7.4, leading=9)
    cell_style = ParagraphStyle("MarkdownCell", parent=body_style, fontName=BODY_FONT,
                                textColor=colors.HexColor("#243746"), fontSize=7.4, leading=9.5)
    data = []
    for row_index, row in enumerate(normalized):
        style = header_style if row_index == 0 else cell_style
        data.append([Paragraph(_plain_inline(cell), style) for cell in row])
    first_width = 1.55 * inch if max_cols > 1 else 7.0 * inch
    widths = [first_width] + ([(7.0 * inch - first_width) / (max_cols - 1)] * (max_cols - 1) if max_cols > 1 else [])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#315C73")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F9")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _markdown_story(markdown: str, styles: dict) -> list:
    story, lines, index = [], markdown.splitlines(), 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            story.append(Spacer(1, 0.05 * inch))
            index += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            table = _markdown_table(table_lines, styles["TableBody"])
            if table:
                story.extend([table, Spacer(1, 0.12 * inch)])
            continue
        if re.fullmatch(r"[-_*]{3,}", line.replace(" ", "")):
            story.extend([HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D7E0E7")),
                          Spacer(1, 0.05 * inch)])
            index += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            level = min(len(heading.group(1)), 3)
            story.append(Paragraph(_plain_inline(heading.group(2)), styles[f"Heading{level}"]))
            index += 1
            continue
        elif re.match(r"^[-*]\s+", line):
            story.append(Paragraph("&bull;&nbsp;" + _plain_inline(re.sub(r"^[-*]\s+", "", line)), styles["BulletBody"]))
        elif re.match(r"^\d+[.)]\s+", line):
            story.append(Paragraph(_plain_inline(line), styles["BulletBody"]))
        elif line.startswith(">"):
            story.append(Paragraph(_plain_inline(line.lstrip("> ")), styles["Callout"]))
        else:
            story.append(Paragraph(_plain_inline(line), styles["BodyText"]))
        story.append(Spacer(1, 0.06 * inch))
        index += 1
    return story


def _extract_executive_section(markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines()
    start = None
    start_level = 2
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
        title = match.group(2).lower() if match else ""
        if match and "executive" in title and ("thesis" in title or "summary" in title):
            start, start_level = index, len(match.group(1))
            break
    if start is None:
        return "", markdown
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,4})\s+", lines[index].strip())
        if match and len(match.group(1)) <= start_level:
            end = index
            break
    executive = "\n".join(lines[start + 1:end]).strip()
    remainder = "\n".join(lines[:start] + lines[end:]).strip()
    return executive, remainder


def build_research_pdf(result: dict) -> bytes:
    """Create a polished, citation-free executive PDF while retaining audit data elsewhere."""
    buffer = io.BytesIO()
    symbols = result.get("request", {}).get("symbols", [])
    title = "Investment Research Brief"
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, leftMargin=0.65 * inch, rightMargin=0.65 * inch,
        topMargin=0.62 * inch, bottomMargin=0.62 * inch,
        title=f"{title}: {', '.join(symbols)}", author="Agentic AI Financial Analyst",
    )
    base = getSampleStyleSheet()
    styles = {
        "Kicker": ParagraphStyle("Kicker", parent=base["Normal"], fontName=BOLD_FONT, fontSize=7.5, leading=10,
                                 textColor=colors.HexColor("#8FD3E8")),
        "HeaderTitle": ParagraphStyle("HeaderTitle", parent=base["Title"], fontName=BOLD_FONT,
                                      fontSize=21, leading=25, textColor=colors.white, alignment=TA_LEFT),
        "HeaderMeta": ParagraphStyle("HeaderMeta", parent=base["Normal"], fontName=BODY_FONT,
                                     fontSize=8.3, leading=11, textColor=colors.HexColor("#D7E7EF")),
        "Subtitle": ParagraphStyle("ExecutiveSubtitle", parent=base["Normal"], fontName=BODY_FONT,
                                   fontSize=8.5, leading=12, textColor=colors.HexColor("#52677B")),
        "Heading1": ParagraphStyle("H1", parent=base["Heading1"], fontName=BOLD_FONT, fontSize=14, leading=18,
                                   spaceBefore=13, spaceAfter=5, textColor=colors.HexColor("#16324F"), keepWithNext=1),
        "Heading2": ParagraphStyle("H2", parent=base["Heading2"], fontName=BOLD_FONT, fontSize=11.2, leading=14,
                                   spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1F5A7A"), keepWithNext=1),
        "Heading3": ParagraphStyle("H3", parent=base["Heading3"], fontName=BOLD_FONT, fontSize=9.6, leading=12.5,
                                   spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#315C73"), keepWithNext=1),
        "BodyText": ParagraphStyle("ExecutiveBody", parent=base["BodyText"], fontName=BODY_FONT,
                                   fontSize=9.2, leading=13.4, textColor=colors.HexColor("#243746"), alignment=TA_LEFT),
        "BulletBody": ParagraphStyle("ExecutiveBullet", parent=base["BodyText"], fontName=BODY_FONT,
                                     fontSize=9, leading=12.8, leftIndent=14, firstLineIndent=-9,
                                     textColor=colors.HexColor("#243746")),
        "Callout": ParagraphStyle("ExecutiveCallout", parent=base["BodyText"], fontName=BODY_FONT,
                                  fontSize=8.6, leading=12.3,
                                  leftIndent=10, rightIndent=10, borderColor=colors.HexColor("#7AA6C2"),
                                  borderWidth=0.8, borderPadding=7, backColor=colors.HexColor("#EFF6FA")),
        "TableBody": ParagraphStyle("ExecutiveTable", parent=base["BodyText"], fontName=BODY_FONT,
                                    fontSize=7.4, leading=9.2,
                                    textColor=colors.HexColor("#243746")),
    }

    def footer(canvas, document):
        canvas.saveState()
        if document.page > 1:
            canvas.setFont(BOLD_FONT, 7.5)
            canvas.setFillColor(colors.HexColor("#315C73"))
            canvas.drawString(0.65 * inch, 10.62 * inch, "EQUITY RESEARCH")
            canvas.setFont(BODY_FONT, 7.5)
            canvas.setFillColor(colors.HexColor("#64748B"))
            canvas.drawRightString(7.85 * inch, 10.62 * inch, _font_safe(", ".join(symbols)))
            canvas.setStrokeColor(colors.HexColor("#D6DEE6"))
            canvas.line(0.65 * inch, 10.5 * inch, 7.85 * inch, 10.5 * inch)
        canvas.setStrokeColor(colors.HexColor("#D6DEE6"))
        canvas.line(0.65 * inch, 0.43 * inch, 7.85 * inch, 0.43 * inch)
        canvas.setFont(BODY_FONT, 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(0.65 * inch, 0.25 * inch, "Research support only | Validate before making investment decisions")
        canvas.drawRightString(7.85 * inch, 0.25 * inch, f"Page {document.page}")
        canvas.restoreState()

    report = clean_report_markdown(result.get("report", ""))
    executive, remainder = _extract_executive_section(report)
    prepared = datetime.now().strftime("%B %d, %Y")
    status = str(result.get("status") or "complete").replace("_", " ").title()
    horizon = result.get("request", {}).get("horizon") or "Not specified"

    header = Table([
        [Paragraph("INSTITUTIONAL EQUITY RESEARCH", styles["Kicker"])],
        [Paragraph(_plain_inline(" / ".join(symbols) or title), styles["HeaderTitle"])],
        [Paragraph(_plain_inline(f"Comparative investment report  |  Prepared {prepared}"), styles["HeaderMeta"])],
    ], colWidths=[7.0 * inch])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#16324F")),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("TOPPADDING", (0, 1), (-1, 1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 3),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 14),
    ]))

    meta_label = ParagraphStyle("MetaLabel", parent=styles["Subtitle"], fontName=BOLD_FONT,
                                fontSize=7, leading=9, textColor=colors.HexColor("#52677B"))
    meta_value = ParagraphStyle("MetaValue", parent=styles["BodyText"], fontName=BOLD_FONT,
                                fontSize=8.5, leading=11, textColor=colors.HexColor("#16324F"))
    meta = Table([
        [Paragraph("COVERAGE", meta_label), Paragraph("INVESTMENT HORIZON", meta_label), Paragraph("REVIEW STATUS", meta_label)],
        [Paragraph(_plain_inline(", ".join(symbols)), meta_value), Paragraph(_plain_inline(horizon), meta_value),
         Paragraph(_plain_inline(status), meta_value)],
    ], colWidths=[2.5 * inch, 2.5 * inch, 2.0 * inch])
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F6F8")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7E0E7")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7E0E7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
    ]))
    story = [header, Spacer(1, 0.12 * inch), meta, Spacer(1, 0.18 * inch)]

    if executive:
        panel_kicker = ParagraphStyle("PanelKicker", parent=styles["Kicker"],
                                      textColor=colors.HexColor("#1F5A7A"), spaceAfter=5)
        # A list inside one table cell is unsplittable and raises LayoutError when a
        # detailed thesis is taller than a page. One flowable per row lets ReportLab
        # split the panel cleanly while repeating the panel title on continuation pages.
        panel_rows = [[Paragraph("INVESTMENT THESIS", panel_kicker)]]
        panel_rows.extend([[flowable] for flowable in _markdown_story(executive, styles)])
        panel = Table(panel_rows, colWidths=[7.0 * inch], repeatRows=1, splitByRow=1, hAlign="LEFT")
        panel.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF3F7")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#8DB7C9")),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, 0), 11),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ("TOPPADDING", (0, 1), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 1), (-1, -2), 1),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ]))
        story.extend([panel, Spacer(1, 0.18 * inch)])

    frameworks = result.get("sector_frameworks", [])
    framework_names = list(dict.fromkeys(str(item.get("framework")) for item in frameworks if item.get("framework")))
    if frameworks:
        focus_header = ParagraphStyle("FocusHeader", parent=styles["TableBody"], fontName=BOLD_FONT,
                                      fontSize=7.2, leading=8.5, textColor=colors.white)
        focus_rows = [[Paragraph("COMPANY", focus_header), Paragraph("SECTOR FRAMEWORK", focus_header),
                       Paragraph("PRIMARY ANALYTICAL FOCUS", focus_header)]]
        for item in frameworks:
            focus_rows.append([
                Paragraph(_plain_inline(item.get("symbol", "")), styles["TableBody"]),
                Paragraph(_plain_inline(item.get("framework", "")), styles["TableBody"]),
                Paragraph(_plain_inline(item.get("description", "")), styles["TableBody"]),
            ])
        focus = Table(focus_rows, colWidths=[0.8 * inch, 1.75 * inch, 4.45 * inch], repeatRows=1)
        focus.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7E0E7")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([Paragraph("Sector Lens", styles["Heading1"]), focus, Spacer(1, 0.12 * inch)])

    basis = _financial_basis_table(result.get("comparison", []), styles["TableBody"])
    if basis:
        story.extend([
            Paragraph("TTM vs Latest Reported Period", styles["Heading1"]),
            Paragraph("TTM reflects the latest four-quarter operating view. The reported row reflects the selected annual or quarterly statement; differences between these bases are not growth rates.",
                      styles["Subtitle"]),
            Spacer(1, 0.07 * inch), basis, Spacer(1, 0.14 * inch),
        ])

    comparison = _comparison_table(result.get("comparison", []), styles["TableBody"], frameworks)
    if comparison:
        story.extend([KeepTogether([
            Paragraph("Sector Metrics, Estimates & Valuation", styles["Heading1"]),
            Paragraph("Priority metrics for " + _plain_inline(", ".join(framework_names) if framework_names else "the covered companies") +
                      ". Blank values indicate unavailable provider data.",
                      styles["Subtitle"]),
            Spacer(1, 0.07 * inch), comparison,
        ]), Spacer(1, 0.14 * inch)])

    story.extend(_markdown_story(remainder if executive else report, styles))
    story.extend([Spacer(1, 0.14 * inch), Paragraph(
        "This document is generated from the saved research record. Source evidence remains available in the application's Sources & Evidence view and JSON export.",
        styles["Callout"],
    )])
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    value = buffer.getvalue()
    buffer.close()
    return value
