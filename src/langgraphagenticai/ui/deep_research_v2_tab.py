from __future__ import annotations

import re
import time

import pandas as pd
import streamlit as st

from langgraphagenticai.deep_research.context import available_context, collect_app_context
from langgraphagenticai.deep_research.v2_workflow import build_manager, run_decision
from langgraphagenticai.deep_research.quarterly_ttm import METHODOLOGY
from langgraphagenticai.deep_research.manager import failure_reason, finalize_report
from langgraphagenticai.deep_research.models import Evidence, ResearchRequest, dumps, parse_symbols
from langgraphagenticai.deep_research.presentation import build_research_pdf, clean_report_markdown
from langgraphagenticai.deep_research.v2 import (
    MODES, V2ConfigurationError, prompt_diagnostics, research_cache_key, stage_configuration,
)
from langgraphagenticai.ui.deep_research_tab import _render_comparison, _render_crew_decision, _render_sources
from langgraphagenticai.deep_research.v2_timestamps import format_saved_time, saved_result_caption, stamp_saved_result
from langgraphagenticai.utils.safety import sanitize_error
from langgraphagenticai.ui.research_news import render_serper_news_coverage


_manager_v2 = build_manager


def _save_v2(update, *, run_id=None, metadata=None, select=False):
    run_id = update.get("id") or run_id
    if not run_id:
        return
    history = st.session_state.get("drv2_history", [])
    existing = next((dict(item) for item in history if item.get("id") == run_id), {})
    existing.update(update)
    existing.update(metadata or {})
    existing["id"] = run_id
    st.session_state["drv2_history"] = [existing] + [item for item in history if item.get("id") != run_id][:7]
    if select:
        st.session_state["drv2_active_run"] = run_id


def _run_status(result):
    return {
        "complete": ("V2 research ready", "complete"),
        "needs_review": ("Review completed with evidence issues", "error"),
        "review_pending": ("Draft saved; review pending", "error"),
        "incomplete": ("Evidence saved; report incomplete", "error"),
        "evidence_ready": ("V2 evidence saved", "complete"),
    }.get(result.get("status"), ("Research stopped; saved progress available", "error"))


def _safe_failure(exc):
    return str(exc) if isinstance(exc, V2ConfigurationError) else failure_reason(exc)


def _render_quick_decision(decision: dict) -> None:
    ticker = decision.get("preferred_ticker")
    label = f"{decision.get('verdict')} · {ticker}" if ticker else decision.get("verdict", "NO_BUY")
    st.success(f"**{label}** · {decision.get('confidence', 0)}% confidence")
    st.write(decision.get("summary", ""))
    columns = st.columns(3)
    for column, (title, key) in zip(columns, (("Catalysts", "catalysts"), ("Risks", "risks"),
                                                  ("Invalidation", "invalidation_signals"))):
        with column:
            st.markdown(f"**{title}**")
            for value in decision.get(key, []):
                st.markdown(f"- {value}")
    if decision.get("limitations"):
        with st.expander("Evidence limitations"):
            for value in decision["limitations"]:
                st.markdown(f"- {value}")
    st.caption(decision.get("disclaimer", "AI-generated research opinion, not personalized investment advice."))


@st.fragment
def render_deep_research_v2_tab(*, openai_api_key: str, fmp_api_key: str, serper_api_key: str = "",
                                marketaux_api_key: str = "", groq_api_key: str = "") -> None:
    st.subheader("Deep Research V2 · Cost Pilot")
    st.caption("A separate experimental workflow for comparing lighter models, smaller prompts, deterministic checks, caching, and bounded spend. Both versions share audited financial calculations; V2 retains separate model routing and cost controls.")
    st.warning("Pilot output may differ from V1. Validate investment conclusions against the Sources tab before relying on them.")

    connections = available_context(st.session_state)
    status = st.columns(4)
    status[0].metric("FMP", "Ready" if fmp_api_key else "Missing")
    status[1].metric("OpenAI", "Ready" if openai_api_key else "Missing")
    status[2].metric("Groq", "Ready" if groq_api_key else "Optional")
    status[3].metric("Saved datasets", len(connections))

    st.caption("Serper news: " + ("Configured" if serper_api_key else "Missing SERPER_API_KEY"))
    if not serper_api_key:
        st.info("Add SERPER_API_KEY in the sidebar, .env, or Streamlit secrets to include news and web research.")

    with st.form("deep_research_v2_form"):
        left, right = st.columns([2, 1])
        with left:
            default = ", ".join(st.session_state.get("equity_report_tickers", [])[:4]) or "AAPL, MSFT"
            tickers_text = st.text_input("Companies", value=st.session_state.get("drv2_tickers", default))
            question = st.text_area(
                "Research question",
                value="Which company offers the strongest risk-adjusted long-term investment case?",
                height=100, max_chars=4000,
            )
        with right:
            mode = st.selectbox("Cost mode", list(MODES), index=0)
            depth = st.selectbox("Research depth", ["Standard", "Extended"])
            horizon = st.selectbox("Investment horizon", ["1–3 years", "3–12 months", "3–5 years"])
            period_label = st.selectbox("Financial statements", ["Annual", "Quarterly"])
        route_cols = st.columns(3)
        light_provider = route_cols[0].selectbox("Light-stage provider", ["OpenAI", "Groq", "Ollama"])
        default_light = "gpt-5-nano" if light_provider == "OpenAI" else "llama-3.3-70b-versatile" if light_provider == "Groq" else "llama3.1:8b"
        light_model = route_cols[1].text_input("Light-stage model", value=default_light)
        budget = route_cols[2].number_input("Maximum estimated model cost (USD)", min_value=0.01, max_value=25.0, value=0.35, step=0.05)
        ollama_base_url = st.text_input("Ollama OpenAI-compatible URL", value="http://localhost:11434/v1",
                                        disabled=light_provider != "Ollama")
        option_cols = st.columns(4)
        use_context = option_cols[0].checkbox("Use saved app data", value=False, disabled=True)
        option_cols[0].caption("Quarterly-derived V2 excludes saved app packets because their financial basis and provider identity are unverified. Saved V2 runs remain available below.")
        include_news = option_cols[1].checkbox("Include news", value=bool(serper_api_key),
                                                   help="Use Serper company news within the requested lookback, plus planner-requested web research.")
        stop_after_evidence = option_cols[2].checkbox("Stop after evidence", value=False)
        st.caption("Stop after evidence includes planning/investigation; report writing and decisions wait for a later explicit action.")
        decision_mode = option_cols[3].selectbox("Decision stage", ["None", "Quick decision", "Full committee"])
        cache_policy = st.radio("Reuse policy", ["Use saved result", "Force fresh research"], horizontal=True)
        news_days = st.select_slider("News lookback", options=[7, 30, 90], value=30)
        submitted = st.form_submit_button("Run V2 pilot", type="primary", width="stretch")

    history = st.session_state.setdefault("drv2_history", [])
    if submitted:
        try:
            try:
                request = ResearchRequest(parse_symbols(tickers_text), question, horizon, depth,
                                          "annual" if period_label == "Annual" else "quarter", news_days, include_news)
            except ValueError as exc:
                raise V2ConfigurationError(str(exc)) from exc
            st.session_state["drv2_tickers"] = tickers_text
            config = stage_configuration(mode, light_provider=light_provider, light_model=light_model)
            runtime = {"budget": float(budget), "ollama_base_url": ollama_base_url if light_provider == "Ollama" else "http://localhost:11434/v1",
                       "decision_mode": decision_mode, "stop_after_evidence": stop_after_evidence,
                       "use_context": use_context}
            context = collect_app_context(st.session_state, request.symbols) if use_context else []
            lookup_key = research_cache_key(request, {"routing": config, "runtime": runtime,
                                                      "app_context": [item.to_dict() for item in context]})
            metadata = {"financial_methodology": METHODOLOGY, "v2_config": config, "request_cache_key": lookup_key, "cost_mode": mode,
                        "v2_runtime": runtime}
            cached = next((item for item in history if item.get("request_cache_key") == lookup_key
                           and item.get("status") in {"complete", "needs_review", "evidence_ready"}), None)
            if cached and cache_policy == "Use saved result":
                st.session_state["drv2_active_run"] = cached["id"]
                st.info("Reused the saved V2 result. No provider or model calls were made.")
            else:
                active_run = None

                def checkpoint(update):
                    nonlocal active_run
                    active_run = update.get("id", active_run)
                    if not active_run:
                        return
                    _save_v2(update, run_id=active_run, metadata=metadata, select=True)

                with st.status("Running Deep Research V2", expanded=True) as run_status:
                    stage, preview = st.empty(), st.empty()
                    started = time.monotonic()
                    manager = _manager_v2(
                        request=request, config=config, openai_api_key=openai_api_key,
                        groq_api_key=groq_api_key, fmp_api_key=fmp_api_key,
                        serper_api_key=serper_api_key, marketaux_api_key=marketaux_api_key,
                        ollama_base_url=ollama_base_url, budget=float(budget),
                        stop_after_evidence=stop_after_evidence,
                        progress=lambda message: stage.write(f"{message} · {int(time.monotonic() - started)}s"),
                        on_text=lambda text: preview.markdown(re.sub(r"(?<!\\)\$", r"\\$", clean_report_markdown(text))),
                        checkpoint=checkpoint,
                    )
                    result = manager.run(request, context)
                    st.session_state["drv2_history"] = stamp_saved_result(
                        result, st.session_state.get("drv2_history", []))
                    result.update(metadata)
                    result["cache_key"] = research_cache_key(request, config, result.get("evidence", []))
                    # Persist/select research before any optional paid decision.
                    _save_v2(result, select=True)
                    result = run_decision(result, openai_api_key=openai_api_key, groq_api_key=groq_api_key)
                    _save_v2(result, select=True)
                    label, state = _run_status(result)
                    run_status.update(label=label, state=state, expanded=state != "complete")

        except Exception as exc:
            st.error("V2 pilot stopped. " + _safe_failure(exc))

    history = st.session_state.get("drv2_history", [])
    if not history:
        st.info("Configure a pilot run above. Paid calls occur only after pressing Run V2 pilot.")
        return
    lookup = {item["id"]: item for item in history}
    selected = st.selectbox("V2 run history", list(lookup), key="drv2_active_run",
                            format_func=lambda key: f"{', '.join(lookup[key]['request']['symbols'])} · {lookup[key].get('cost_mode')} · Run started: {format_saved_time(lookup[key].get('created_at'))} · {key[:6]}")
    result = lookup[selected]
    config = result.get("v2_config", {})
    request = ResearchRequest(**result["request"])

    metrics = st.columns(5)
    metrics[0].metric("Status", result.get("status", "unknown").replace("_", " ").title())
    metrics[1].metric("Mode", result.get("cost_mode", "—"))
    metrics[2].metric("Model calls", len([d for d in result.get("diagnostics", []) if d.get("model") != "python" and d.get("status") != "blocked"]))
    metrics[3].metric("Est. model cost", f"${float(result.get('estimated_model_cost_usd') or 0):.4f}")
    metrics[4].metric("Elapsed", f"{float(result.get('elapsed_seconds') or 0):.1f}s")
    st.caption(saved_result_caption(result))
    session_cost = sum(float(item.get("estimated_model_cost_usd") or 0) for item in history)
    st.caption(f"V2 session estimated model cost: ${session_cost:.4f}")
    st.caption(f"Cache key: {result.get('cache_key', 'pending')} · Reopening, tabs, and downloads make no model calls.")

    render_serper_news_coverage(result)
    label, state = _run_status(result)
    (st.success if state == "complete" else st.warning)(label)
    for warning in dict.fromkeys(result.get("warnings", []) + result.get("report_warnings", [])):
        st.warning(sanitize_error(warning))
    if result.get("gaps"):
        with st.expander("Evidence gaps", expanded=result.get("status") == "incomplete"):
            for gap in result["gaps"]:
                st.write(sanitize_error(gap))
    usable = any(item.get("status") == "ok" and item.get("data") for item in result.get("evidence", []))
    status = result.get("status")
    retry_label = "Generate report from saved evidence" if status == "evidence_ready" else "Retry review" if result.get("draft") else "Retry report writing"
    if status in {"evidence_ready", "incomplete", "review_pending", "collecting", "reviewing"} and usable:
        st.info("Recovery uses saved evidence and drafts. It does not fetch provider data again.")
        legacy = result.get("financial_methodology") != METHODOLOGY
        if legacy:
            st.warning("Legacy saved evidence uses the earlier financial methodology and may contain provider TTM facts. Start fresh research for quarterly-derived TTM.")
        legacy_ack = st.checkbox("Use legacy saved financial evidence for this recovery", key=f"drv2_legacy_{selected}") if legacy else True
        if st.button(retry_label, type="primary", key=f"drv2_recover_{selected}", disabled=not legacy_ack):
            try:
                runtime = result.get("v2_runtime", {})
                manager = _manager_v2(
                    request=request, config=config, openai_api_key=openai_api_key, groq_api_key=groq_api_key,
                    fmp_api_key=fmp_api_key, serper_api_key=serper_api_key, marketaux_api_key=marketaux_api_key,
                    ollama_base_url=runtime.get("ollama_base_url", "http://localhost:11434/v1"),
                    budget=float(runtime.get("budget", 0.35)), stop_after_evidence=False, saved=result,
                    checkpoint=lambda update: _save_v2(update, run_id=selected),
                )
                updated = manager.resume(result)
                st.session_state["drv2_history"] = stamp_saved_result(
                    updated, st.session_state.get("drv2_history", []))
                _save_v2(updated)
                st.rerun()
            except Exception as exc:
                st.error("Recovery stopped. " + _safe_failure(exc) + " Saved evidence and progress remain available.")
    elif status == "incomplete" and not usable:
        st.info("No usable company evidence was collected. Check provider access and tickers, then start fresh research.")
    if status == "needs_review":
        st.info("Review found unresolved issues. Verify warnings and sources before finalizing with caveats.")
        if st.button("Finalize report with caveats", key=f"drv2_finalize_{selected}"):
            _save_v2(finalize_report(result))
            st.rerun()
    decision_mode_saved = result.get("v2_runtime", {}).get("decision_mode", "None")
    if result.get("decision_error"):
        st.warning("Decision stage stopped: " + sanitize_error(result["decision_error"]) + " Your research report is preserved.")
    if status == "complete" and decision_mode_saved != "None" and result.get("decision_status") != "complete":
        decision_label = "Retry decision" if result.get("decision_status") == "failed" else "Run saved decision stage"
        if st.button(decision_label, key=f"drv2_decision_{selected}"):
            _save_v2(run_decision(result, openai_api_key=openai_api_key, groq_api_key=groq_api_key))
            st.rerun()

    report_tab, decision_tab, comparison_tab, sources_tab, diagnostics_tab = st.tabs(
        ["Report", "Decision", "Comparison", "Sources", "Performance"])
    with report_tab:
        if result.get("report"):
            st.markdown(clean_report_markdown(result["report"]))
        else:
            st.info("No report has been generated yet.")
    with decision_tab:
        if result.get("quick_decision"):
            _render_quick_decision(result["quick_decision"])
        elif result.get("crewai_decision"):
            _render_crew_decision(result["crewai_decision"])
        else:
            st.info("Decision waits for a completed report." if decision_mode_saved != "None" else "This run did not request a decision stage.")
    with comparison_tab:
        _render_comparison(result)
    with sources_tab:
        _render_sources(result)
    with diagnostics_tab:
        diagnostics = result.get("diagnostics", [])
        if diagnostics:
            st.dataframe(pd.DataFrame(diagnostics), hide_index=True, width="stretch")
            totals = pd.DataFrame(diagnostics).select_dtypes("number").sum().to_dict()
            st.json({"totals": totals, "routing": config.get("routes", {})}, expanded=False)
        evidence = [Evidence(**item)
                    for item in result.get("evidence", [])]
        if evidence and config.get("contexts"):
            st.markdown("#### Prompt-size estimates")
            st.dataframe(pd.DataFrame(prompt_diagnostics(evidence, config["contexts"], focus=request.question)),
                         hide_index=True, width="stretch")

    if result.get("report"):
        downloads = st.columns(3)
        filename = "research_v2_" + "_".join(request.symbols) + "_" + result["id"]
        downloads[0].download_button("Download PDF", build_research_pdf(result), filename + ".pdf", "application/pdf", on_click="ignore")
        downloads[1].download_button("Download memo", clean_report_markdown(result["report"]), filename + ".md", "text/markdown", on_click="ignore")
        downloads[2].download_button("Download audit JSON", dumps(result), filename + ".json", "application/json", on_click="ignore")
