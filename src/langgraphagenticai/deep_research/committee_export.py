"""Reader-facing saved committee appendix; no decisions are generated here."""
from langgraphagenticai.utils.safety import redact_sensitive_text


def committee_markdown(result):
    decision = result.get("crewai_decision")
    quick = False
    if not isinstance(decision, dict) or not decision:
        decision = result.get("quick_decision")
        quick = True
    if not isinstance(decision, dict) or not decision:
        if result.get("crewai_error") or result.get("decision_status") == "failed":
            return "## Committee decision unavailable\n\nNo completed decision was saved for this report."
        return ""
    from .executive import executive_prose

    def text(value):
        # Prevent untrusted text from becoming a table cell or Markdown heading.
        if not isinstance(value, (str, int, float)):
            return ""
        value = executive_prose(redact_sensitive_text(str(value or "")))
        return " ".join(value.replace("|", "/").split()).lstrip("#>* ")

    def confidence(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100:
            return f"{value:g}%"
        return "Unavailable"

    symbols = set(result.get("request", {}).get("symbols", []))
    lines = ["## Quick investment decision" if quick else "## CrewAI Committee Decision",
             "", "AI-generated investment opinion based on this saved research."]
    if decision.get("created_at"):
        lines += ["", "Saved decision: " + text(decision["created_at"])]
    preferred = decision.get("preferred_ticker")
    if isinstance(preferred, str) and preferred in symbols:
        lines += ["", "**Preferred company:** " + text(preferred)]
    if decision.get("summary"):
        lines += ["", text(decision["summary"])]
    raw_entries = decision.get("decisions")
    entries = [item for item in raw_entries if isinstance(item, dict)
               and isinstance(item.get("ticker"), str) and item["ticker"] in symbols] if isinstance(raw_entries, list) else []
    if quick:
        verdict = decision.get("verdict")
        if isinstance(verdict, str) and verdict in {"BUY", "WATCH", "NO_BUY"}:
            lines += ["", f"**Decision:** {verdict} | **Confidence:** {confidence(decision.get('confidence'))}"]
    elif entries:
        lines += ["", "| Company | Recommendation | Confidence |", "|---|---|---|"]
        for item in entries:
            rating = item.get("recommendation")
            rating = rating if isinstance(rating, str) and rating in {"BUY", "HOLD", "SELL"} else "Unavailable"
            lines.append(f"| {text(item['ticker'])} | {rating} | {confidence(item.get('confidence'))} |")
    else:
        lines += ["", "Company ratings were not available in the saved decision."]
    for item in entries:
        lines += ["", "### " + text(item["ticker"])]
        if item.get("rationale"):
            lines += ["", text(item["rationale"])]
        for key, label in (("catalysts", "Catalysts"), ("risks", "Risks"), ("invalidation_signals", "Thesis invalidation")):
            if item.get(key):
                lines += ["", "**" + label + ":**"]
                values = item[key] if isinstance(item[key], list) else [item[key]]
                lines += ["- " + text(value) for value in values if text(value)]
    for key, label in (("catalysts", "Catalysts"), ("risks", "Risks"), ("invalidation_signals", "Thesis invalidation"),
                       ("evidence_limitations", "Limitations"), ("limitations", "Limitations")):
        if decision.get(key):
            lines += ["", "### " + label]
            values = decision[key] if isinstance(decision[key], list) else [decision[key]]
            lines += ["- " + text(value) for value in values if text(value)]
    if decision.get("dissent"):
        lines += ["", "### Dissenting view", "", text(decision["dissent"])]
    if result.get("crewai_error") or result.get("decision_status") == "failed":
        lines += ["", "This is the retained saved decision; a later decision attempt did not complete."]
    return "\n".join(lines)
