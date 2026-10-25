"""Deterministic executive-first PDF rendering of the shared memo projection."""
from html import escape
from io import BytesIO
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepInFrame, Table, TableStyle

from langgraphagenticai.deep_research.presentation import BODY_FONT, BOLD_FONT


def validate_pdf_size(memo):
    if sum(len(text) for _, text in memo.appendices) > 2_000_000:
        raise ValueError("Saved memo exceeds the two-million-character PDF limit. Use the retained original report and evidence downloads.")


def deferred_pdf(memo):
    """Session-owned pure callback; heavy layout starts only on explicit download."""
    from functools import lru_cache
    validate_pdf_size(memo)
    @lru_cache(maxsize=1)
    def generate():
        return pdf_bytes(memo)
    return generate


def pdf_bytes(memo):
    validate_pdf_size(memo)
    buffer = BytesIO()
    body = ParagraphStyle("Memo", fontName=BODY_FONT, fontSize=9, leading=12, spaceAfter=7, wordWrap="CJK")
    heading = ParagraphStyle("Heading", parent=body, fontName=BOLD_FONT, fontSize=11, leading=14)
    title = ParagraphStyle("Title", parent=heading, fontSize=18, leading=22)
    glyphs = pdfmetrics.getFont(BODY_FONT).face.charWidths
    def paragraph(text, style=body):
        safe = "".join(c if ord(c) in glyphs or c in "\n\t" else f"[U+{ord(c):04X}]" for c in str(text))
        return Paragraph(escape(safe).replace("\n", "<br/>"), style)
    story = [paragraph(memo.title, title), paragraph(memo.lineage), paragraph("Thesis · saved interpretation / allocation", heading), paragraph(memo.thesis)]
    for label, text in memo.sections:
        if label.startswith("Allocation - ticker |"):
            story.append(paragraph("Portfolio allocation", heading))
            rows=[[paragraph(v, heading) for v in ("Ticker","Name","Weight","Why selected")]]
            rows.extend([[paragraph(cell.strip()) for cell in line.split(" | ",3)] for line in text.splitlines()])
            table=Table(rows,colWidths=[52,110,58,308],hAlign="LEFT")
            table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,0),.5,colors.grey),
                                       ("BOTTOMPADDING",(0,0),(-1,-1),6)]))
            story.extend([table,Spacer(1,8)])
        else:
            story.extend([paragraph(label, heading), paragraph(text)])
    story.append(paragraph("Supporting investment detail follows. Research software; not personalized financial advice."))
    # Font fallbacks can expand rare Unicode text. Keep the executive page bounded
    # even then, while leaving full-size, unabridged appendix flowables separate.
    story = [KeepInFrame(528, 705, story, mode="shrink"), PageBreak()]
    for label, text in memo.appendices:
        story.append(paragraph(label, heading))
        # Small flowables allow arbitrarily long prose/JSON without unsplittable cells.
        for line in text.splitlines():
            for chunk in wrap(line, width=1800, break_long_words=False,
                              break_on_hyphens=False, replace_whitespace=False,
                              drop_whitespace=False) or [" "]:
                story.append(paragraph(chunk))
        story.append(Spacer(1, 12))
    def footer(canvas, doc):
        canvas.setFont(BODY_FONT, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(42, 24, f"Axiom Research | Saved investment memo | Page {doc.page}")
    SimpleDocTemplate(buffer, pagesize=letter, leftMargin=42, rightMargin=42, topMargin=35, bottomMargin=40).build(
        story, onFirstPage=footer, onLaterPages=footer,
        canvasmaker=lambda *a, **kw: Canvas(*a, **{**kw, "invariant": 1}))
    return buffer.getvalue()
