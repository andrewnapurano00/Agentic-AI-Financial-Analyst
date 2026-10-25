"""Paginated, local-only Equity Report exports from saved evidence and opinions."""
from __future__ import annotations

import io
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, CondPageBreak, Table, TableStyle
from langgraphagenticai.deep_research.presentation import BODY_FONT, BOLD_FONT, _plain_inline
from langgraphagenticai.utils.safety import redact_sensitive_text


def build_equity_pdf(*, tickers, peer_group, executive_summary, gpt_note,
                     committee=None, generated_at="", secrets=()):
    """Never collect evidence or invoke models; escape all saved/provider text."""
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter,
                            leftMargin=47, rightMargin=47, topMargin=45, bottomMargin=45,
                            title="Equity Research Brief", author="Axiom Research")
    base = getSampleStyleSheet()
    styles = {
        "BodyText": ParagraphStyle("EquityBody", parent=base["BodyText"], fontName=BODY_FONT,
            fontSize=9.5, leading=14, spaceAfter=7, textColor=colors.HexColor("#243746")),
        "Heading2": ParagraphStyle("EquityHeading", parent=base["Heading2"], fontName=BOLD_FONT,
            fontSize=12, leading=16, spaceBefore=13, spaceAfter=6,
            textColor=colors.HexColor("#16324F"), keepWithNext=True),
        "Heading3": ParagraphStyle("EquitySubheading", parent=base["Heading3"], fontName=BOLD_FONT,
            fontSize=10, leading=14, spaceBefore=9, spaceAfter=4,
            textColor=colors.HexColor("#1F5A7A"), keepWithNext=True),
        "Bullet": ParagraphStyle("EquityBullet", parent=base["BodyText"], fontName=BODY_FONT,
            fontSize=9.5, leading=14, spaceAfter=5, leftIndent=13, firstLineIndent=-8,
            textColor=colors.HexColor("#243746")),
        "Meta": ParagraphStyle("EquityMeta", parent=base["Normal"], fontName=BODY_FONT,
            fontSize=8, leading=11, spaceAfter=5, textColor=colors.HexColor("#64748B")),
        "Header": ParagraphStyle("EquityHeader", fontName=BOLD_FONT, fontSize=22, leading=28,
            textColor=colors.white),
        "Kicker": ParagraphStyle("EquityKicker", fontName=BOLD_FONT, fontSize=8, leading=12,
            textColor=colors.HexColor("#8FD3E8")),
    }
    story = []

    def clean(value):
        text = str(value if value is not None else "")
        for secret in secrets:
            if secret:
                text = text.replace(secret, "[REDACTED]")
        return _plain_inline(redact_sensitive_text(text))

    def heading(value):
        story.append(Paragraph(clean(value), styles["Heading2"]))

    note_headings = {
        "final recommendation by ticker", "final recommendation", "best idea and why", "best idea",
        "key supporting evidence", "key drivers", "biggest risks or watch-items",
        "biggest risks / watch items", "biggest risks", "main risks", "analyst conclusion",
        "investment conclusion", "valuation", "growth", "profitability and cash flow",
        "profitability & cash flow", "cash flow and profitability", "balance sheet",
        "balance sheet / leverage", "leverage", "momentum and analyst support",
        "momentum & analyst support", "momentum",
    }

    def prose(value):
        # Render saved prose locally; headings and emphasis never become literal markup.
        for raw in str(value or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            if re.fullmatch(r"[-_*]{3,}", line):
                continue
            match = re.match(r"^#{1,6}\s+(.+)$", line)
            bold_heading = re.fullmatch(r"\*\*(.+?)\*\*:?", line)
            if match or bold_heading or line.lower().rstrip(":") in note_headings:
                text = (match or bold_heading).group(1) if match or bold_heading else line.rstrip(":")
                story.append(Paragraph(clean(text), styles["Heading3"]))
            elif re.match(r"^[-*?]\s+", line):
                text = re.sub(r"^[-*?]\s+", "", line)
                story.append(Paragraph("&bull; " + clean(text), styles["Bullet"]))
            else:
                # Existing saved notes may already have had Markdown emphasis removed.
                ticker_line = re.match(r"^([A-Z][A-Z0-9.-]{0,9}):\s*(.*)$", line)
                formatted = ("<b>" + clean(ticker_line.group(1)) + ":</b> " + clean(ticker_line.group(2))) if ticker_line else clean(line)
                story.append(Paragraph(formatted, styles["BodyText"]))

    header = Table([
        [Paragraph("AXIOM RESEARCH | EXECUTIVE EQUITY BRIEF", styles["Kicker"])],
        [Paragraph(clean(" / ".join(tickers)), styles["Header"])],
    ], colWidths=[doc.width])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#16324F")),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
    ]))
    story.extend([header, Spacer(1, 12)])
    story.append(Paragraph(clean("Framework: " + peer_group), styles["Meta"]))
    story.append(Paragraph(clean("Report generated: " + (generated_at or "Unavailable (legacy saved report)")), styles["Meta"]))
    heading("Executive summary")
    prose(executive_summary or "No saved executive summary available.")
    if gpt_note:
        heading("Investment perspective")
        prose(gpt_note)
    story.append(CondPageBreak(150))
    heading("Investment committee decision")
    if committee:
        prose(f"{committee.get('verdict', '')} | Candidate: {committee.get('best_buy') or 'None'} | Confidence: {committee.get('confidence', 'Unavailable')}%")
        prose(f"Decision generated: {committee.get('created_at', 'Unavailable')} | Model: {committee.get('model', 'Unavailable')}")
        prose(committee.get("summary"))
        heading("What agents debated")
        prose(committee.get("debate_summary"))
        if committee.get("runner_up"):
            prose("Runner-up: " + committee["runner_up"])
        for view in committee.get("specialist_views", []):
            heading(str(view.get("role", "Specialist")).title())
            prose("Preferred ticker: " + str(view.get("preferred_ticker") or "None"))
            prose(view.get("argument"))
            for challenge in view.get("challenges", []):
                prose("Challenge: " + str(challenge))
        for key, label in (("catalysts", "Catalysts"), ("risks", "Risks"),
                           ("invalidation_signals", "Thesis invalidation"),
                           ("evidence_limitations", "Evidence limitations")):
            heading(label)
            values = committee.get(key, [])
            for value in values:
                prose("- " + str(value))
            if not values:
                prose("None supplied in the saved decision.")
        story.append(Paragraph(clean("Decision reference: " + str(committee.get("input_fingerprint", "Unavailable"))), styles["Meta"]))
    else:
        prose("No completed CrewAI decision matches this saved scorecard. Run the debate explicitly in the app to include a decision; exporting does not run it.")
    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D6DEE6"))
        canvas.line(47, 33, 565, 33)
        canvas.setFont(BODY_FONT, 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(47, 21, "Axiom Research | General research, not personalized financial advice")
        canvas.drawRightString(565, 21, f"Page {document.page}")
        if document.page > 1:
            canvas.setFont(BOLD_FONT, 7)
            canvas.drawString(47, 769, "EQUITY RESEARCH | EXECUTIVE BRIEF")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
