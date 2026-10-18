"""Question-aware editorial guidance, with no provider or model calls."""
import re


FOCUS_SECTIONS = {
    "valuation": ("Valuation anchors & assumptions", "Bull, base & bear scenarios", "Valuation gap & catalysts"),
    "earnings": ("Earnings & guidance", "Revenue, margins & cash conversion", "Forward outlook & valuation implications"),
    "catalysts": ("Key developments & timing", "Business impact & market expectations", "Catalysts, sentiment & valuation implications"),
    "risk": ("Downside exposures & resilience", "Stress scenarios & financial capacity", "Risk pricing & potential mitigants"),
    "strategy": ("Strategic position & competitive advantage", "Growth drivers & execution", "Financial & valuation implications"),
    "comparison": ("Comparative business quality", "Growth, cash generation & valuation", "Catalysts & relative opportunity"),
    "company": ("Business quality & investment drivers", "Financial performance & valuation", "Outlook & catalysts"),
}
SIGNALS = {
    "valuation": r"\b(?:valuations?|fair value|price targets?|overvalued|undervalued|worth|dcf)\b",
    "earnings": r"\b(?:earnings|guidance|quarterly results|earnings release)\b",
    "catalysts": r"\b(?:news|catalysts?|sentiment|upcoming events?)\b",
    "risk": r"\b(?:downside|stress|bear case|bankruptcy|liquidity|risks?(?![ -]adjusted))\b",
    "strategy": r"\b(?:strategy|strategic|moats?|competitive|supply chain|artificial intelligence|ai)\b",
}


def report_structure(request):
    question = request.question.lower()
    matches = [(match.start(), focus) for focus, pattern in SIGNALS.items()
               if (match := re.search(pattern, question))]
    # Broad investment-case requests commonly list valuation/news/risk together.
    # A narrow request instead leads with its first substantive focus.
    focus = min(matches)[1] if 0 < len(matches) < 3 else (
        "comparison" if len(request.symbols) > 1 else "company")
    return {"version": 1, "focus": focus, "sections": [
        "Executive Investment Thesis", *FOCUS_SECTIONS[focus],
        "Risks, counterargument & thesis invalidation", "Investment conclusion & monitoring",
    ]}


def structure_instruction(request):
    outline = report_structure(request)
    return (
        "\nREPORT ORGANIZATION: Answer the research question directly in the opening thesis. "
        "Use real Markdown ## section headings, ### company/subtopic headings, and blank lines between paragraphs. "
        "Follow this ordered editorial outline: " + " -> ".join(outline["sections"]) + ". "
        "Tailor the three middle headings to the specific issues named in the user's question; "
        "do not force an unrelated generic checklist into every report. Keep the thesis first and conclusion last. "
        "Each section must add new analysis; do not repeat the same thesis or metrics in several sections. "
        "For multiple companies, compare them within each topic using consistent company subheadings or one compact table. "
        "Use a short paragraph for interpretation and at most three bullets for distinct drivers or watchpoints. "
        "Keep fiscal dates, currencies and TTM/FY/forward bases beside material figures. "
        "Material news, technicals and missing inputs belong where they affect the question; "
        "do not invent specialist sections or claims when evidence is unavailable. "
        "Do not include a committee verdict: the separately saved committee decision is appended by the exporter."
    )


def normalize_report_headings(markdown):
    """Improve saved Markdown typography without rearranging or rewriting claims."""
    lines = []
    for raw in str(markdown or "").splitlines():
        line = raw.strip()
        # Models sometimes emit standalone bold labels instead of headings.
        bold = re.fullmatch(r"\*\*([^*\n]{2,110})\*\*\s*:?", line)
        if bold:
            line = "## " + bold[1].rstrip(":")
        # Numbered bold section labels are headings; ordinary numbered prose stays.
        numbered = re.fullmatch(r"\d+[.)]\s+\*\*([^*\n]{2,110})\*\*\s*:?", line)
        if numbered:
            line = "## " + numbered[1].rstrip(":")
        if re.match(r"^#{1,4}\s+", line):
            line = re.sub(r"^(#{1,4})\s+\d+[.)]\s+", r"\1 ", line)
            if lines and lines[-1]:
                lines.append("")
            lines.extend([line, ""])
        else:
            lines.append(raw)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
