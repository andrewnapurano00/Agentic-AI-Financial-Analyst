"""Executive presentation over saved evidence; no recalculation or model calls."""
import re
from .sector import SECTOR_METRIC_REGISTRY, map_sector_to_framework
from .research_metrics import project_sector_row

MOMENTUM = ("Price date", "Price basis", "3M price return (%)", "1Y price return (%)", "% From SMA 50", "% From SMA 200", "RSI 14", "SMA 50", "SMA 200")
VALUATION = ("Forward P/E", "Forward P/S", "P/E TTM", "P/S TTM", "P/B TTM", "P/FCF TTM", "EV / EBITDA", "EV / Sales", "EV / FCF", "FCF Yield", "Dividend Yield", "Price Target Upside")
FUNDAMENTALS = ("Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Latest Gross Margin", "Latest Operating Margin", "ROE", "ROA", "FCF CAGR 3Y", "Debt to Equity", "Net Debt / EBITDA", "Income Quality")
EXECUTIVE_STYLE = ("Write for a stakeholder presentation: clear plain English, short paragraphs, no raw metric dump. "
    "Open with one executive thesis paragraph of at most 100 words. Highlight sector-relevant fundamentals, valuation, "
    "momentum/technicals and news catalysts, plus the material risk. Follow Equity Report sector priorities, "
    "preserving fiscal basis, units and unavailable values. Keep detailed dated news, contrary developments, sentiment "
    "and implications in the body. Internal citations are required in the saved report for audit, but must not drive "
    "the prose or refer to datasets, packets, evidence IDs or agent workflow. Never mention financial statements, "
    "statement names or fields, filings, data providers, calculation methodology or source attribution anywhere in the "
    "reader-facing report. State business conclusions directly; retain provenance in citation fields and the audit only. Never tell the reader to retry, finalize or check an internal workflow. End with a concise investment conclusion. The presentation removes references.")


def executive_prose(value):
    """Hide source notation only in presentation; retain original saved audit text."""
    from .presentation import clean_report_markdown
    from .crew_committee import clean_committee_text
    from .summary_text import clean_summary_references
    value = clean_summary_references(value)
    original = re.sub(r"\[(?:sources?|references?|citations?)[^]\n]*\]", "", str(value or ""), flags=re.I)
    text = clean_committee_text(clean_report_markdown(original))
    text = re.sub(r"\[([^]\n]+)\]\(https?://[^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[(?:sources?|references?|citations?)[^]\n]*\]", "", text, flags=re.I)
    text = re.sub(r"\bE\d{3}\b", "", text)
    return re.sub(r"[ \t]+([,.;:])", r"\1", re.sub(r"[ \t]{2,}", " ", text)).strip()


def short_prose(value, limit):
    text = re.sub(r"[\r\n]+", " ", executive_prose(value))
    text = re.sub(r"(?:^|\s)[#*>]+\s*", " ", text).strip()
    text = text.replace("**", "").replace("`", "")
    words = text.split()
    result = " ".join(words[:limit]).rstrip(",;:") + ("..." if len(words) > limit else "")
    return result if not result or result.endswith((".", "!", "?")) else result + "."


def executive_preview(report):
    from .presentation import clean_report_markdown, _extract_executive_section
    clean = clean_report_markdown(report)
    thesis, _ = _extract_executive_section(clean)
    return short_prose(thesis or clean.split("\n\n")[0], 100)


def decision_sections(decision):
    """Three inline sections in a single bounded paragraph for old and new runs."""
    calls = decision.get("decisions", [])
    ratings = "; ".join(f"{c.get('ticker', '')}: {c.get('recommendation', 'Unspecified')} ({c.get('confidence', 0)}% confidence)" for c in calls)
    if ratings and decision.get("preferred_ticker"):
        ratings = "Preference: " + str(decision["preferred_ticker"]) + ". " + ratings
    if not ratings:
        ratings = str(decision.get("verdict") or "No structured recommendation")
        if decision.get("preferred_ticker"):
            ratings += " - " + str(decision["preferred_ticker"])
        if "confidence" in decision:
            ratings += f" ({decision['confidence']}% confidence)"
    drivers = str(decision.get("summary") or "No decision summary saved.")
    catalysts = decision.get("catalysts", []) or [v for c in calls for v in c.get("catalysts", [])]
    if catalysts:
        drivers += " Catalyst: " + str(catalysts[0])
    risks = decision.get("risks", []) or [v for c in calls for v in c.get("risks", [])]
    invalidation = decision.get("invalidation_signals", []) or [v for c in calls for v in c.get("invalidation_signals", [])]
    limitations = decision.get("evidence_limitations", decision.get("limitations", []))
    watch = ("Risk: " + str(risks[0]).rstrip(".; ") + ". ") if risks else ""
    if invalidation:
        watch += "Thesis check: " + str(invalidation[0]).rstrip(".; ") + ". "
    if limitations:
        from .summary_text import REFERENCE
        limitation = str(limitations[0])
        if re.search(REFERENCE, limitation, re.I) or re.search(r"dataset|provider|methodology|retriev", limitation, re.I):
            limitation = "The investment case remains uncertain"
        watch += "Limitation: " + limitation.rstrip(".; ") + ". "
    if decision.get("dissent"):
        watch += "Dissent: " + str(decision["dissent"])
    return [("Decision", short_prose(ratings, 35)), ("Key drivers", short_prose(drivers, 50)),
            ("Risks & watchpoints", short_prose(watch or "No specific risks were saved; review evidence before acting.", 45))]


def executive_metric_groups(comparison):
    """Equity Report sector priorities, with protected space for technicals."""
    rows = [project_sector_row(row) for row in comparison]
    priorities = []
    company_priorities = []
    for row in rows:
        framework = row.get("Sector framework") or map_sector_to_framework(row.get("Sector"), row.get("Industry"))
        registry = SECTOR_METRIC_REGISTRY.get(framework, SECTOR_METRIC_REGISTRY["General / Cross-Sector"])
        company_priorities.append([key for key in registry["must_have"] + registry["preferred"] if row.get(key) is not None])
    # Interleave company priorities so the first sector cannot occupy every slot.
    for index in range(max((len(keys) for keys in company_priorities), default=0)):
        for keys in company_priorities:
            if index < len(keys) and keys[index] not in priorities:
                priorities.append(keys[index])
    def available(keys):
        return [key for key in dict.fromkeys(keys) if any(row.get(key) is not None for row in rows)]
    # Canonical registry aliases retain their audited units and period labels.
    technical_aliases = {"1Y Return", "YTD Return", "% From SMA 50", "% From SMA 200", "RSI 14"}
    fundamentals = [key for key in priorities if key not in VALUATION and key not in technical_aliases]
    fundamental_fields = available(fundamentals or FUNDAMENTALS)
    if not fundamental_fields:
        fundamental_fields = available(("Revenue (TTM)", "Operating margin (TTM)", "Net income (TTM)", "Free cash flow (TTM)", "ROE", "ROA"))
    return {"Fundamentals": fundamental_fields[:10],
            "Valuation": available([key for key in priorities if key in VALUATION])[:8],
            "Momentum & technicals": available(MOMENTUM)}
