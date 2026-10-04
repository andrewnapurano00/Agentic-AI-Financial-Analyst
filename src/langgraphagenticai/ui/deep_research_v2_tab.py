from __future__ import annotations

import re
import time

import pandas as pd
import streamlit as st

from langgraphagenticai.deep_research.context import available_context, collect_app_context
from langgraphagenticai.deep_research.crew_committee import run_investment_committee
from langgraphagenticai.deep_research.data import FinancialDataSource
from langgraphagenticai.deep_research.manager import ResearchManager, failure_reason
from langgraphagenticai.deep_research.models import ResearchRequest, dumps, parse_symbols
from langgraphagenticai.deep_research.presentation import build_research_pdf, clean_report_markdown
from langgraphagenticai.deep_research.v2 import (
    MODES, build_stage_llm, committee_diagnostics, projected_cost, prompt_diagnostics, research_cache_key, run_quick_decision,
    stage_configuration, validate_report,
)
from langgraphagenticai.tools.finance_tool_registry import get_finance_tools
from langgraphagenticai.tools.serper_tools import SerperClient
from langgraphagenticai.ui.deep_research_tab import _render_comparison, _render_crew_decision, _render_sources
from langgraphagenticai.deep_research.v2_timestamps import format_saved_time, saved_result_caption, stamp_saved_result
from langgraphagenticai.utils.safety import sanitize_error


def _manager_v2(*, request: ResearchRequest, config: dict, openai_api_key: str, groq_api_key: str,
                fmp_api_key: str, serper_api_key: str, marketaux_api_key: str,
                ollama_base_url: str, budget: float, stop_after_evidence: bool,
                progress=None, on_text=None, checkpoint=None) -> ResearchManager:
    routes = config["routes"]
    models = {}
    for stage in ("plan", "draft", "review", "follow_up"):
        route = routes[stage]
        models[stage] = build_stage_llm(
            route["provider"], route["model"], openai_api_key=openai_api_key,
            groq_api_key=groq_api_key, ollama_base_url=ollama_base_url,
        )
    limits = dict(config["limits"])
    limits["draft"] = (150, config["depth_draft_tokens"][request.depth])
    return ResearchManager(
        models["draft"], FinancialDataSource(fmp_api_key), SerperClient(serper_api_key),
        get_finance_tools(fmp_api_key, openai_api_key, marketaux_api_key), progress,
        on_text=on_text, checkpoint=checkpoint, utility_llm=models["plan"], stage_llms=models,
        stage_limits=limits, context_limits=config["contexts"],
        deterministic_validator=validate_report, interpretive_review=config["interpretive_review"],
        max_estimated_cost_usd=budget, stop_after_evidence=stop_after_evidence,
    )


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
    st.caption("A separate experimental workflow for comparing lighter models, smaller prompts, deterministic checks, caching, and bounded spend. Deep Research V1 is unchanged.")
    st.warning("Pilot output may differ from V1. Validate investment conclusions against the Sources tab before relying on them.")

    connections = available_context(st.session_state)
    status = st.columns(4)
    status[0].metric("FMP", "Ready" if fmp_api_key else "Missing")
    status[1].metric("OpenAI", "Ready" if openai_api_key else "Missing")
    status[2].metric("Groq", "Ready" if groq_api_key else "Optional")
    status[3].metric("Saved datasets", len(connections))

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
        use_context = option_cols[0].checkbox("Use saved app data", value=True)
        include_news = option_cols[1].checkbox("Include news", value=bool(serper_api_key))
        stop_after_evidence = option_cols[2].checkbox("Stop after evidence", value=False)
        decision_mode = option_cols[3].selectbox("Decision stage", ["None", "Quick decision", "Full committee"])
        cache_policy = st.radio("Reuse policy", ["Use saved result", "Force fresh research"], horizontal=True)
        news_days = st.select_slider("News lookback", options=[7, 30, 90], value=30)
        submitted = st.form_submit_button("Run V2 pilot", type="primary", width="stretch")

    history = st.session_state.setdefault("drv2_history", [])
    if submitted:
        try:
            request = ResearchRequest(parse_symbols(tickers_text), question, horizon, depth,
                                      "annual" if period_label == "Annual" else "quarter", news_days, include_news)
            st.session_state["drv2_tickers"] = tickers_text
            config = stage_configuration(mode, light_provider=light_provider, light_model=light_model)
            lookup_key = research_cache_key(request, config)
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
                    current = st.session_state.get("drv2_history", [])
                    existing = next((item for item in current if item.get("id") == active_run), {})
                    existing.update(update)
                    existing.update({"v2_config": config, "request_cache_key": lookup_key, "cost_mode": mode,
                                     "v2_runtime": {"budget": float(budget), "ollama_base_url": ollama_base_url}})
                    st.session_state["drv2_history"] = [existing] + [item for item in current if item.get("id") != active_run][:7]

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
                    context = collect_app_context(st.session_state, request.symbols) if use_context else []
                    result = manager.run(request, context)
                    st.session_state["drv2_history"] = stamp_saved_result(
                        result, st.session_state.get("drv2_history", []))
                    result.update({"v2_config": config, "request_cache_key": lookup_key, "cost_mode": mode,
                                   "cache_key": research_cache_key(request, config, result.get("evidence", [])),
                                   "v2_runtime": {"budget": float(budget), "ollama_base_url": ollama_base_url}})
                    if result.get("report") and decision_mode == "Quick decision":
                        route = config["routes"]["crew_lead"]
                        projected = projected_cost(route["model"], input_characters=config["contexts"]["committee"], output_tokens=900)
                        if float(result.get("estimated_model_cost_usd") or 0) + projected > float(budget):
                            raise RuntimeError("The quick decision would exceed the configured model-cost budget.")
                        llm = build_stage_llm(route["provider"], route["model"], openai_api_key=openai_api_key)
                        decision, diagnostic = run_quick_decision(
                            result, llm, model=route["model"], max_chars=config["contexts"]["committee"])
                        result["quick_decision"] = decision
                        result.setdefault("diagnostics", []).append(diagnostic)
                        result["estimated_model_cost_usd"] = round(
                            float(result.get("estimated_model_cost_usd") or 0) + float(diagnostic.get("estimated_cost_usd") or 0), 6)
                    elif result.get("report") and decision_mode == "Full committee":
                        specialist = config["routes"]["crew_specialists"]
                        lead = config["routes"]["crew_lead"]
                        projected = projected_cost(lead["model"], input_characters=config["contexts"]["committee"], output_tokens=1200)
                        if specialist["provider"] == "OpenAI":
                            projected += 2 * projected_cost(specialist["model"], input_characters=config["contexts"]["committee"], output_tokens=1000)
                        if float(result.get("estimated_model_cost_usd") or 0) + projected > float(budget):
                            raise RuntimeError("The full committee would exceed the configured model-cost budget.")
                        result["crewai_decision"] = run_investment_committee(
                            result, openai_api_key=openai_api_key, model_name=lead["model"],
                            specialist_model=specialist["model"], specialist_provider=specialist["provider"],
                            groq_api_key=groq_api_key, packet_max_chars=config["contexts"]["committee"],
                        )
                        crew_diagnostics = committee_diagnostics(result["crewai_decision"])
                        result.setdefault("diagnostics", []).extend(crew_diagnostics)
                        result["estimated_model_cost_usd"] = round(
                            float(result.get("estimated_model_cost_usd") or 0)
                            + sum(float(item.get("estimated_cost_usd") or 0) for item in crew_diagnostics), 6)
                    current = st.session_state.get("drv2_history", [])
                    st.session_state["drv2_history"] = [result] + [item for item in current if item.get("id") != result["id"]][:7]
                    st.session_state["drv2_active_run"] = result["id"]
                    run_status.update(label="V2 evidence saved" if result["status"] == "evidence_ready" else "V2 research ready",
                                      state="complete", expanded=False)
        except Exception as exc:
            st.error("V2 pilot could not complete. " + failure_reason(exc))

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
    metrics[2].metric("Model calls", len([d for d in result.get("diagnostics", []) if d.get("model") != "python"]))
    metrics[3].metric("Est. model cost", f"${float(result.get('estimated_model_cost_usd') or 0):.4f}")
    metrics[4].metric("Elapsed", f"{float(result.get('elapsed_seconds') or 0):.1f}s")
    st.caption(saved_result_caption(result))
    session_cost = sum(float(item.get("estimated_model_cost_usd") or 0) for item in history)
    st.caption(f"V2 session estimated model cost: ${session_cost:.4f}")
    st.caption(f"Cache key: {result.get('cache_key', 'pending')} · Reopening, tabs, and downloads make no model calls.")

    if result.get("status") == "evidence_ready":
        st.info("Evidence collection is complete. Generate the report later without recollecting provider data.")
        if st.button("Generate report from saved evidence", type="primary", key=f"drv2_generate_{selected}"):
            try:
                runtime = result.get("v2_runtime", {})
                manager = _manager_v2(
                    request=request, config=config, openai_api_key=openai_api_key, groq_api_key=groq_api_key,
                    fmp_api_key=fmp_api_key, serper_api_key=serper_api_key, marketaux_api_key=marketaux_api_key,
                    ollama_base_url=runtime.get("ollama_base_url", "http://localhost:11434/v1"),
                    budget=float(runtime.get("budget", 0.35)), stop_after_evidence=False,
                )
                updated = manager.resume(result)
                st.session_state["drv2_history"] = stamp_saved_result(
                    updated, st.session_state.get("drv2_history", []))
                updated.update({"v2_config": config, "request_cache_key": result.get("request_cache_key"),
                                "cache_key": result.get("cache_key"), "cost_mode": result.get("cost_mode")})
                st.session_state["drv2_history"] = [updated if item["id"] == selected else item for item in history]
                st.rerun()
            except Exception as exc:
                st.error("Saved evidence could not be synthesized. " + sanitize_error(exc))

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
            st.info("This run did not request a decision stage.")
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
        evidence = [__import__("langgraphagenticai.deep_research.models", fromlist=["Evidence"]).Evidence(**item)
                    for item in result.get("evidence", [])]
        if evidence and config.get("contexts"):
            st.markdown("#### Prompt-size estimates")
            st.dataframe(pd.DataFrame(prompt_diagnostics(evidence, config["contexts"], focus=request.question)),
                         hide_index=True, width="stretch")

    if result.get("report"):
        downloads = st.columns(3)
        filename = "research_v2_" + "_".join(request.symbols) + "_" + result["id"]
        downloads[0].download_button("Download PDF", build_research_pdf(result), filename + ".pdf", "application/pdf")
        downloads[1].download_button("Download memo", clean_report_markdown(result["report"]), filename + ".md", "text/markdown")
        downloads[2].download_button("Download audit JSON", dumps(result), filename + ".json", "application/json")
