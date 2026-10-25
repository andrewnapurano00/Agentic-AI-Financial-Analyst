"""Presentation-only intent defaults and projections over saved research."""
import re
from copy import deepcopy

PRESETS = ("Quick Brief", "Deep Dive", "Investment Committee")


def recovery_available(result):
    return (result.get("status") in {"incomplete", "evidence_ready", "review_pending", "needs_review"}
            and bool(result.get("request"))
            and any(e.get("status") == "ok" and e.get("data") for e in result.get("evidence", [])))


def recover_saved(result, manager):
    """Commit only completed recovery; failed attempts cannot replace retained research."""
    from langgraphagenticai.utils.safety import sanitize_error
    try:
        recovered = manager.resume(deepcopy(result))
        if recovered.get("id") != result.get("id"):
            raise ValueError("Recovery returned a different research run.")
        if recovered.get("evidence") != result.get("evidence") or recovered.get("request") != result.get("request"):
            raise ValueError("Recovery changed saved evidence or the research request.")
        if recovered.get("status") == "complete" and recovered.get("report"):
            recovered.pop("continuation_error", None)
            recovered.setdefault("continuation_original", deepcopy(result.get("continuation_original") or {
                key: result.get(key) for key in ("report", "draft", "markdown", "status", "created_at")}))
            return recovered
        reason = "Report continuation did not finish."
    except Exception as exc:
        reason = sanitize_error(exc)
        recovered = {}
    retained = deepcopy(result)
    # Retain attempted usage/reservations even when report generation fails,
    # so repeated explicit attempts cannot reset the pilot's model budget.
    diagnostics = recovered.get("diagnostics", getattr(manager, "diagnostics", None))
    if isinstance(diagnostics, list):
        retained["diagnostics"] = deepcopy(diagnostics)
        costs = [d["estimated_cost_usd"] for d in diagnostics if "estimated_cost_usd" in d]
        if costs:
            retained["estimated_model_cost_usd"] = sum(costs)
    retained["continuation_error"] = reason
    return retained


def render_recovery(result, factory, *, key, enabled=True):
    import streamlit as st
    from langgraphagenticai.utils.safety import sanitize_error
    if result.get("continuation_original"):
        with st.expander("Original report before continuation"):
            st.caption("Retained original text; its original incomplete or partial status still applies.")
            original = result["continuation_original"]
            st.code(original.get("report") or original.get("draft") or "No original report text.", language=None)
    if result.get("continuation_error"):
        st.error("Continuation stopped. " + sanitize_error(result["continuation_error"])
                 + " Original research and downloads are preserved.")
    if not recovery_available(result):
        return None
    with st.expander("Continue saved research"):
        st.caption("Continue report writing from the original evidence without refreshing sources. "
                   "This explicit action may consume model credits. Evidence may be stale; original dates remain unchanged. "
                   "A committee is a separate action after completion.")
        acknowledge = st.checkbox("Use the saved evidence without refreshing, including any legacy or stale inputs",
                                  key=key + "_ack")
        if not enabled:
            st.info("Saved model configuration or credentials are unavailable. Restore them or explicitly start fresh research; no alternative engine was selected.")
        if st.button("Continue report using saved evidence", key=key + "_run",
                     disabled=not (enabled and acknowledge)):
            try:
                with st.spinner("Continuing saved report"):
                    return recover_saved(result, factory())
            except Exception as exc:
                st.error("Continuation stopped. " + sanitize_error(exc)
                         + " Original research and downloads are preserved.")
    return None


def intent_defaults(preset, engine=None):
    if preset not in PRESETS:
        raise ValueError("Unsupported research intent")
    engine = engine or ("Low cost format" if preset == "Quick Brief" else "Standard format")
    if engine not in {"Standard format", "Low cost format"}:
        raise ValueError("Unsupported research engine")
    return {"preset": preset, "engine": engine,
            "depth": "Extended" if preset == "Investment Committee" or (
                engine == "Low cost format" and preset == "Deep Dive") else "Standard",
            "mode": "Economy" if preset == "Quick Brief" else "Balanced",
            "committee": preset == "Investment Committee"}


def saved_sections(result):
    """Extract only named sections, without inventing missing analysis or mutating runs."""
    topics = {
        "Valuation implications": r"valuation|pricing|price target",
        "Competing perspectives": r"competing|contrar|bear case|bull case|debate|dissent",
        "Material risks": r"risk|invalidation|downside",
        "Research gaps": r"gap|limitation|missing|uncertainty",
    }
    report = str(result.get("report") or result.get("draft") or "")
    blocks = re.split(r"(?m)^(?=#{1,6}\s)", report)
    return {title: "\n\n".join(block.strip() for block in blocks
             if re.search(pattern, block.split("\n", 1)[0], re.I))
            for title, pattern in topics.items()}


def render_saved_overview(result, engine, *, api_key="", model="", credentials=()):
    import streamlit as st
    from langgraphagenticai.deep_research.executive import executive_preview
    from langgraphagenticai.ui.app_shell import render_evidence_row
    from langgraphagenticai.ui.workspace_presentation import evidence_status

    st.markdown("### Research overview")
    st.caption(f"Saved lineage: {engine}. Workflow completion does not certify factual accuracy. "
               "Original report, sources, decisions and downloads remain below.")
    from .investment_memo import render_investment_memo
    render_investment_memo(result, credentials=(*credentials, api_key), key="overview")
    if not result.get("report") or result.get("status") != "complete":
        st.warning("Partial or unfinished research. Retained text is not a completed conclusion. Review saved sources below; use a recovery action if offered, otherwise explicitly submit fresh research.")
    from .claim_verification import render_claim_audit
    render_claim_audit(result, credentials=(*credentials, api_key))
    with st.expander("Key evidence and source / freshness information"):
        render_evidence_row(evidence_status(result))
        records = result.get("evidence") or []
        if not records:
            st.info("No saved evidence available.")
        for item in records:
            st.write(f"{item.get('symbol', '')} · {item.get('title', item.get('category', 'Evidence'))} · "
                     f"{item.get('status', 'unknown')} · {item.get('provider', 'Source unavailable')}")
            st.caption("Retrieved: " + str(item.get("retrieved_at") or "Unavailable")
                       + " · Fiscal/quote dates and units remain in Sources.")
    for title, text in saved_sections(result).items():
        with st.expander(title):
            if text:
                st.markdown(text)
            else:
                st.info("No separately titled section in this saved report. Review the full report and sources below; no new analysis was generated.")

    from .earnings_quality import render_earnings_quality
    render_earnings_quality(result)
    from .research_specialists import render_specialists
    render_specialists(result, engine=engine, api_key=api_key, model=model)
