"""Bounded automatic completion; unchecked AI drafts never become recommendations."""
from copy import deepcopy
import re

from .models import utc_now
from .research_metrics import format_metric, project_sector_row
from .executive import executive_metric_groups
from langgraphagenticai.utils.safety import redact_sensitive_text


def _text(value):
    text = redact_sensitive_text(str(value or ""), max_length=500)
    return re.sub(r"[\n\r|<>]", " ", text).strip()


def evidence_report(result):
    """Only saved deterministic figures and dated news; no recycled failed AI claims."""
    symbols = result.get("request", {}).get("symbols", [])
    lines = ["## Executive Investment Thesis",
             "Research view: No rating. Confidence: Low. The available information supports a financial overview, "
             "but does not establish a defensible investment preference or price target. The figures below describe "
             "business performance and market positioning; they are not a forecast."]
    rows = [project_sector_row(row) for row in result.get("comparison", [])]
    groups = executive_metric_groups(rows)
    for row in rows:
        lines += ["", "## " + _text(row.get("Ticker")) + " — Business and market overview"]
        lines += ["| Metric | Value |", "|---|---|"]
        for key in dict.fromkeys(key for fields in groups.values() for key in fields):
            if row.get(key) is not None:
                lines.append("| " + _text(key) + " | " + _text(format_metric(key, row[key], row)) + " |")
    if not rows:
        lines += ["", "## Company overview", "Company metrics are unavailable for " + ", ".join(map(_text, symbols)) + "."]
    lines += ["", "## News and catalysts"]
    found = False
    for item in result.get("evidence", []):
        if item.get("status") != "ok" or item.get("category") not in {"news", "web"}:
            continue
        data = item.get("data") or []
        for row in data[:3] if isinstance(data,list) else []:
            if isinstance(row, dict) and row.get("title"):
                found = True
                lines.append("- " + _text(item.get("symbol")) + ": " + _text(row["title"]) + " (" + _text(row.get("published") or "publication date unavailable") + ").")
    if not found:
        lines.append("Recent company developments are unavailable; no news sentiment conclusion is assigned.")
    lines += ["", "## Risks and outlook",
              "Coverage is limited. A reliable comparative recommendation, scenario forecast and company-specific "
              "thesis invalidation assessment are unavailable. Missing values have not been estimated."]
    return "\n".join(lines)


def finish_saved(result):
    """A no-network legacy/failure terminal result, retaining the original audit."""
    if result.get("status") == "complete":
        return result
    final = deepcopy(result)
    final["delivery_audit"] = dict(status=result.get("status"), review_status=result.get("review_status"),
                                   report=result.get("report", ""), draft=result.get("draft", ""),
                                   warnings=result.get("warnings", []),
                                   report_warnings=result.get("report_warnings", []),
                                   partial_draft=result.get("partial_draft", ""))
    try:
        report = evidence_report(result)
    except (ValueError, TypeError, KeyError):
        final["delivery_audit"]["fallback_error"] = "invalid_saved_metrics"
        report = ("## Executive Investment Thesis\nResearch view: No rating. Confidence: Low. "
                  "Reliable company metrics are unavailable; no investment recommendation or price target is assigned.")
    final.update(status="complete", delivery_outcome="limited_evidence", review_status="evidence_only",
                 report=report, markdown=report, finalized_at=utc_now())
    return final


def saved_report_drafts(result):
    """Recover distinct unchecked drafts, including legacy automatic deliveries.

    These are audit material, never substitutes for the validated report.
    """
    if result.get("delivery_outcome") != "limited_evidence":
        return []
    records = list(result.get("delivery_drafts", [])) + [result.get("delivery_audit", {})]
    drafts = []
    for record in records:
        for key in ("draft", "report", "partial_draft"):
            text = record.get(key)
            if isinstance(text, str) and text.strip() and text != result.get("report") and text not in drafts:
                drafts.append(text)
    return drafts


def complete_delivery(manager, result):
    """At most one saved-evidence recovery; original model budgets still apply."""
    if manager.single_pass:
        final = executive_saved_result(result)
        manager.checkpoint(final.copy())
        return final
    def check_citations(value):
        from .manager import citation_ids
        if value.get("status") != "complete":
            return value
        known = {e["id"] for e in value.get("evidence", [])}
        references = citation_ids(value.get("report", ""))
        if references - known or (known and not references):
            value = dict(value, status="needs_review")
        return value
    result = check_citations(result)
    if result.get("status") == "complete" or result.get("status") == "evidence_ready":
        return result
    attempts = []
    # A repair may replace a rich original draft with a shorter/failed attempt.
    # Retain both rather than allowing recovery to discard earlier work.
    drafts = list(result.get("delivery_drafts", []))
    drafts.append({key: deepcopy(result.get(key)) for key in
                   ("report", "draft", "partial_draft", "status", "review_status", "report_warnings")})
    if any(e.get("status") == "ok" and e.get("data") for e in result.get("evidence", [])):
        manager.progress("Completing the report from saved research")
        try:
            recovery = result
            if result.get("status") == "needs_review":
                recovery = dict(result, draft="", plan={**result.get("plan", {}),
                    "repair_issues":result.get("report_warnings", []) or result.get("warnings", [])})
            result = check_citations(manager._resume_once(recovery))
            attempts.append(dict(status=result.get("status"), review_status=result.get("review_status")))
        except Exception as exc:
            from .manager import failure_reason
            attempts.append(dict(status="failed", reason=failure_reason(exc)))
    final = finish_saved(result)
    if final.get("delivery_outcome") == "limited_evidence":
        final["delivery_drafts"] = drafts
    final["automatic_recovery"] = attempts
    # Include failed-stage accounting even if recovery stopped at its budget guard.
    final["diagnostics"] = manager.diagnostics.copy()
    costs = [d["estimated_cost_usd"] for d in manager.diagnostics if "estimated_cost_usd" in d]
    final["estimated_model_cost_usd"] = round(sum(costs), 6) if costs else None
    manager.checkpoint(final.copy())
    return final


def executive_saved_result(result):
    """Present the saved memo directly; never invoke review, rewriting or providers.

    Legacy review diagnostics and fallback text stay in the audit. This is a
    presentation migration, not a claim that the earlier report passed review.
    """
    if result.get("report_mode") == "single_pass" or result.get("status") == "evidence_ready":
        return result
    if result.get("status") == "complete" and result.get("delivery_outcome") != "limited_evidence":
        return result
    report = result.get("report", "")
    if result.get("delivery_outcome") == "limited_evidence":
        drafts = saved_report_drafts(result)
        report = drafts[0] if drafts else ""
    elif result.get("status") in {"review_pending", "needs_review"}:
        report = result.get("draft") or report
    final = deepcopy(result)
    final.setdefault("delivery_audit", {key: deepcopy(result.get(key)) for key in
                     ("status", "review_status", "report", "draft", "warnings", "report_warnings")})
    # Keep actual synthesis/collection failure states honest. Do not manufacture
    # a complete thesis from a placeholder or a partial streaming checkpoint.
    has_memo = bool(report and report.strip()) and result.get("status") in {
        "complete", "review_pending", "needs_review"}
    if has_memo:
        final.update(status="complete", report=report, markdown=report,
                     report_mode="single_pass", review_status="not_performed",
                     delivery_outcome="executive_report")
    else:
        final.update(status="incomplete", report=report, markdown=report,
                     report_mode="single_pass", review_status="not_performed",
                     delivery_outcome="incomplete")
    return final
