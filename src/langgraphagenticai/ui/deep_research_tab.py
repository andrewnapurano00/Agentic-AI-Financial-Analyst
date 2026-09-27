from __future__ import annotations

import pandas as pd
import re
import time
import streamlit as st

from langgraphagenticai.LLMS.openaillm import OpenAILLM
from langgraphagenticai.utils.safety import sanitize_error
from langgraphagenticai.deep_research.context import available_context, collect_app_context
from langgraphagenticai.deep_research.crew_committee import clean_committee_text, run_investment_committee
from langgraphagenticai.deep_research.data import FinancialDataSource
from langgraphagenticai.deep_research.manager import ResearchManager, failure_reason, finalize_report
from langgraphagenticai.deep_research.models import ResearchRequest, dumps, parse_symbols, safe_url
from langgraphagenticai.deep_research.presentation import build_research_pdf, clean_report_markdown
from langgraphagenticai.tools.finance_tool_registry import get_finance_tools
from langgraphagenticai.tools.serper_tools import SerperClient


def _manager(openai_api_key, model_name, fmp_api_key, serper_api_key, marketaux_api_key,
             progress=None, on_text=None, checkpoint=None):
    controls = {"OPENAI_API_KEY": openai_api_key, "selected_model": model_name,
                "timeout": 150, "max_retries": 0, "stream_usage": True}
    if model_name in {"gpt-5", "gpt-5-mini", "gpt-5-nano"}:
        controls["reasoning_effort"] = "low"
    llm = OpenAILLM(controls).get_llm_model()
    utility_llm = llm
    if model_name == "gpt-5":
        utility_controls = dict(controls, selected_model="gpt-5-mini", reasoning_effort="minimal")
        utility_llm = OpenAILLM(utility_controls).get_llm_model()
    return ResearchManager(
        llm, FinancialDataSource(fmp_api_key), SerperClient(serper_api_key),
        get_finance_tools(fmp_api_key, openai_api_key, marketaux_api_key), progress,
        on_text=on_text, checkpoint=checkpoint, utility_llm=utility_llm,
    )


def _import_tickers(key):
    if key == "equity":
        symbols = st.session_state.get("equity_report_tickers", [])
    else:
        payload = st.session_state.get("stock_screener_payload") or {}
        rows = payload.get("results")
        symbols = rows["Ticker"].head(4).tolist() if isinstance(rows, pd.DataFrame) and "Ticker" in rows else []
    if symbols:
        st.session_state["dr_tickers"] = ", ".join(symbols[:4])


def _display_metric(metric: str, value, row: dict) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, (int, float)):
        if any(term in metric for term in ("margin", "Margin", "Yield", "ROE", "ROA", "ROIC", "Payout")):
            number = float(value) * 100 if abs(float(value)) <= 2 else float(value)
            return f"{number:,.1f}%"
        if any(term in metric for term in ("growth", "Growth", "return", "Return", "upside", "Upside", "% From", "% revenue", "% Revenue")):
            return f"{float(value):,.1f}%"
        if any(term in metric for term in ("P/E", "P/S", "P/B", "P/FCF", "EV/", "EV /", "Debt / EBITDA")):
            return f"{float(value):,.1f}x"
        if any(term in metric for term in ("Revenue", "revenue", "income", "Income", "EBITDA", "cash flow", "Cash flow",
                                           "expenditure", "FCF", "Market cap", "target", "Target", "Price")):
            currency = row.get("Statement currency") if any(term in metric for term in
                ("Revenue", "revenue", "income", "Income", "EBITDA", "cash flow", "Cash flow", "expenditure", "FCF")) else row.get("Quote currency")
            prefix = f"{currency} " if currency else ""
            number = float(value)
            if abs(number) >= 1_000_000_000:
                return f"{prefix}{number / 1_000_000_000:,.1f}B"
            if abs(number) >= 1_000_000:
                return f"{prefix}{number / 1_000_000:,.1f}M"
            return f"{prefix}{number:,.2f}"
        return f"{float(value):,.2f}"
    return str(value)


def _metric_matrix(frame: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    rows = frame.to_dict("records")
    available = [field for field in fields if field in frame.columns and frame[field].notna().any()]
    values = {str(row.get("Ticker")): [_display_metric(field, row.get(field), row) for field in available]
              for row in rows}
    return pd.DataFrame(values, index=available)


def _show_metric_matrix(frame: pd.DataFrame, fields: list[str], caption: str) -> None:
    matrix = _metric_matrix(frame, fields)
    st.caption(caption)
    if matrix.empty:
        st.info("No provider data is available for this section.")
        return
    st.dataframe(matrix, width="stretch",
                 column_config={"_index": st.column_config.TextColumn("Metric", width="large")})


def _render_comparison(result):
    frame = pd.DataFrame(result["comparison"])
    if frame.empty:
        st.info("No normalized company comparison is available.")
        return
    frameworks = result.get("sector_frameworks", [])

    st.markdown("#### Company snapshot")
    cards = st.columns(len(frame.index))
    for card, row in zip(cards, frame.to_dict("records")):
        with card:
            with st.container(border=True):
                st.markdown(f"**{row.get('Ticker', '')}**")
                st.caption(str(row.get("Company") or row.get("Sector") or "Company overview"))
                st.metric("Price", _display_metric("Price", row.get("Price"), row))
                st.write(f"Forward P/E  **{_display_metric('Forward P/E', row.get('Forward P/E'), row)}**")
                st.write(f"Target upside  **{_display_metric('Target upside (%)', row.get('Target upside (%)'), row)}**")

    snapshot, ttm_tab, statement_tab, forward_tab, sector_tab, trend_tab = st.tabs([
        "Overview", "TTM performance", "Reported period", "Forward & valuation", "Sector metrics", "Price trend",
    ])
    with snapshot:
        _show_metric_matrix(frame, [
            "Company", "Sector", "Industry", "Sector framework", "Price", "Market cap", "Quote currency",
            "TTM through", "Statement date", "Statement period", "Statement currency", "Balance sheet date",
        ], "Dates and currencies are shown explicitly so unlike periods are not mixed.")
    with ttm_tab:
        _show_metric_matrix(frame, [
            "TTM through", "TTM currency", "Revenue (TTM)", "Gross profit (TTM)", "Operating income (TTM)",
            "EBITDA (TTM)", "Net income (TTM)", "Operating cash flow (TTM)", "Capital expenditure (TTM)",
            "Free cash flow (TTM)", "Gross margin (TTM)", "Operating margin (TTM)", "EBITDA margin (TTM)",
            "Net margin (TTM)", "OCF margin (TTM)", "FCF margin (TTM)", "Cash conversion (TTM)",
            "R&D as % revenue (TTM)", "Stock-based comp % revenue (TTM)", "Capex to revenue (TTM)",
        ], "Trailing twelve months from the dedicated provider statement endpoints. TTM is the latest four-quarter operating view.")
    with statement_tab:
        _show_metric_matrix(frame, [
            "Statement date", "Statement period", "Statement currency", "Revenue (latest period)",
            "Gross profit (latest period)", "Operating income (latest period)", "EBITDA (latest period)",
            "Net income (latest period)", "Operating cash flow (latest period)", "Capital expenditure (latest period)",
            "Free cash flow (latest period)", "Gross margin (latest period)", "Operating margin (latest period)",
            "EBITDA margin (latest period)", "Net margin (latest period)", "OCF margin (latest period)",
            "FCF margin (latest period)", "Cash conversion (latest period)", "R&D as % revenue (latest period)",
            "Stock-based comp % revenue (latest period)", "Capex to revenue (latest period)",
        ], "Selected annual or quarterly statement. Differences from TTM are not growth rates unless matched-period evidence supports that conclusion.")
    with forward_tab:
        _show_metric_matrix(frame, [
            "Estimate period", "Forward revenue", "Forward revenue next period", "Forward revenue growth (%)",
            "Forward EPS", "Forward EBITDA", "Forward net income", "P/E (TTM)", "Forward P/E", "P/S (TTM)",
            "Forward P/S", "P/B (TTM)", "EV/EBITDA (TTM)", "EV/Sales (TTM)", "FCF yield (TTM, fraction)",
            "Analyst target", "Target upside (%)",
        ], "Consensus estimates and market valuation. TTM multiples use trailing fundamentals; forward multiples use consensus estimates.")
    with sector_tab:
        if frameworks:
            columns = st.columns(min(len(frameworks), 2))
            for index, item in enumerate(frameworks):
                with columns[index % len(columns)]:
                    with st.container(border=True):
                        st.markdown(f"**{item['symbol']} · {item['framework']}**")
                        st.caption(f"{item.get('sector', 'Unknown')} · {item.get('industry', 'Unknown')}")
                        st.write(item.get("description", ""))
            fields = ["Sector framework"]
            for item in frameworks:
                for metric in item.get("must_have", []) + item.get("preferred", []):
                    if metric not in fields:
                        fields.append(metric)
            _show_metric_matrix(frame, fields, "Metrics are selected by sector. Downweighted metrics are excluded from the primary view.")
            with st.expander("Coverage gaps and specialist KPIs"):
                for item in frameworks:
                    st.markdown(f"**{item['symbol']}**")
                    st.write("Unavailable core metrics: " + (", ".join(item.get("unavailable_priority_metrics", [])) or "None"))
                    st.write("Specialist KPIs to verify: " + (", ".join(item.get("missing_but_useful", [])) or "None"))
        else:
            st.info("Sector frameworks are unavailable for this saved report.")
    with trend_tab:
        _show_metric_matrix(frame, [
            "Price date", "1Y price return (%)", "3M price return (%)", "RSI (14)", "SMA 50", "SMA 200",
            "% From SMA 50", "% From SMA 200",
        ], "Price trend and momentum use the recorded market-data date and are not total returns.")
        series = {}
        for item in result["evidence"]:
            if item["category"] == "technicals" and item["status"] == "ok":
                rows = item["data"].get("series", [])
                if rows:
                    data = pd.DataFrame(rows).set_index("date")["close"]
                    series[item["symbol"]] = data
        if series:
            prices = pd.DataFrame(series).sort_index().dropna()
            if not prices.empty:
                st.markdown("##### Indexed price performance")
                st.caption("Indexed to 100 at the first shared observation. Price basis is recorded in each technical dataset; this is not a total-return comparison.")
                prices.index = pd.to_datetime(prices.index)
                st.line_chart(prices.div(prices.iloc[0]).mul(100), width="stretch")


def _render_sources(result):
    evidence = result["evidence"]
    categories = sorted({e["category"] for e in evidence})
    selected = st.multiselect("Filter evidence", categories, key=f"dr_filter_{result['id']}")
    filtered = [e for e in evidence if not selected or e["category"] in selected]
    options = {e["id"]: e for e in filtered}
    if not options:
        st.info("No evidence matches these filters.")
        return
    selected_id = st.selectbox("Evidence item", list(options),
                              format_func=lambda key: f"[{key}] {options[key]['title']} · {options[key]['status']}",
                              key=f"dr_source_{result['id']}")
    item = options[selected_id]
    if item:
        with st.expander(f"[{item['id']}] {item['title']} · {item['status']}"):
            st.caption(f"{item['provider']} · Retrieved: {item['retrieved_at']}")
            if safe_url(item.get("url")):
                st.link_button("Open original source", item["url"])
            if item["note"]:
                st.caption(item["note"])
            st.json(item["data"], expanded=False)


def _render_crew_decision(decision: dict) -> None:
    def executive_text(value) -> str:
        text = clean_committee_text(str(value or ""))
        return re.sub(r"(?<!\\)\$", r"\\$", text)

    preferred = decision.get("preferred_ticker")
    if preferred:
        st.success(f"Committee preference: **{preferred}**")
    st.markdown(executive_text(decision.get("summary", "")))
    calls = decision.get("decisions", [])
    if not calls:
        st.info("No structured committee calls are available.")
        return
    columns = st.columns(min(len(calls), 3))
    for index, call in enumerate(calls):
        with columns[index % len(columns)]:
            with st.container(border=True):
                st.markdown(f"### {call.get('ticker', 'Ticker')} · {call.get('recommendation', '—')}")
                st.metric("Confidence", f"{call.get('confidence', 0)}%")
                st.markdown(executive_text(call.get("rationale", "")))
                for label, key in (("Catalysts", "catalysts"), ("Risks", "risks"),
                                   ("Thesis invalidation", "invalidation_signals")):
                    values = call.get(key, [])
                    if values:
                        st.markdown(f"**{label}**")
                        for value in values:
                            st.markdown(f"- {executive_text(value)}")
    if decision.get("dissent"):
        st.markdown("#### Committee dissent")
        st.markdown(executive_text(decision["dissent"]))
    if decision.get("evidence_limitations"):
        with st.expander("Evidence limitations"):
            for limitation in decision["evidence_limitations"]:
                st.markdown(f"- {executive_text(limitation)}")
    st.caption(decision.get("disclaimer", "AI-generated research opinion, not personalized investment advice."))


@st.fragment
def render_deep_research_tab(*, openai_api_key: str, model_name: str, fmp_api_key: str,
                             serper_api_key: str = "", marketaux_api_key: str = "") -> None:
    st.subheader("Deep Research")
    st.caption("From company evidence to an investment thesis. Investigate one business or compare up to four.")
    connections = available_context(st.session_state)
    c1, c2, c3 = st.columns(3)
    c1.metric("Financial data", "Configured" if fmp_api_key else "Not configured")
    c2.metric("Serper news", "Configured" if serper_api_key else "Not configured")
    c3.metric("Saved app datasets", str(len(connections)))
    if connections:
        st.caption("Available context: " + " · ".join(connections))
    if not serper_api_key:
        st.info("Add SERPER_API_KEY in the sidebar, .env, or Streamlit secrets to include news and web research.")

    import_cols = st.columns(2)
    import_cols[0].button("Use equity report tickers", key="dr_import_equity", on_click=_import_tickers,
                          args=("equity",), disabled=not st.session_state.get("equity_report_tickers"))
    import_cols[1].button("Use top screener results", key="dr_import_screener", on_click=_import_tickers,
                          args=("screener",), disabled=not isinstance(st.session_state.get("stock_screener_payload"), dict))
    if "dr_tickers" not in st.session_state:
        st.session_state["dr_tickers"] = ", ".join(st.session_state.get("equity_report_tickers", [])[:4]) or "AAPL, MSFT"
    with st.form("deep_research_form"):
        left, right = st.columns([2, 1])
        with left:
            ticker_text = st.text_input("Companies", key="dr_tickers", help="One to four ticker symbols, separated by commas.")
            question = st.text_area("Research question", value="Which company offers the stronger long-term investment case? Examine business quality, fundamentals, valuation, technicals, recent news sentiment, catalysts, and downside risks.", height=125, max_chars=4000)
        with right:
            horizon = st.selectbox("Investment horizon", ["1–3 years", "3–12 months", "3–5 years"])
            depth = st.selectbox("Research depth", ["Standard", "Extended"], help="Both collect the core datasets. Standard adds up to 4 targeted tool investigations; Extended adds up to 8.")
            period_label = st.selectbox("Financial statements", ["Annual", "Quarterly"])
            news_days = st.selectbox("News lookback (days)", [7, 30, 90], index=1)
        options = st.columns(3)
        use_context = options[0].checkbox("Include saved data from other tabs", value=True)
        include_news = options[1].checkbox("Include Serper news and web research", value=bool(serper_api_key))
        use_crewai = options[2].checkbox(
            "Enable CrewAI investment committee",
            value=False,
            help="After research, three agents debate fundamentals, valuation, and risk before issuing BUY/HOLD/SELL calls.",
        )
        st.caption("The draft appears as it is written. Evidence and completed drafts are saved during the run, so retries resume from the saved work. Results stay in this session.")
        submitted = st.form_submit_button("Start deep research", type="primary", width="stretch")

    factory_args = (openai_api_key, model_name, fmp_api_key, serper_api_key, marketaux_api_key)

    active_run = None
    def checkpoint(update):
        nonlocal active_run
        active_run = update.get("id", active_run)
        if not active_run:
            return
        history = st.session_state.get("dr_history", [])
        existing = next((r for r in history if r["id"] == active_run), {})
        existing.update(update)
        existing["model"] = model_name
        st.session_state["dr_history"] = [existing] + [r for r in history if r["id"] != active_run][:4]

    if submitted:
        try:
            request = ResearchRequest(parse_symbols(ticker_text), question, horizon, depth,
                                      "annual" if period_label == "Annual" else "quarter", news_days, include_news)
            context = collect_app_context(st.session_state, request.symbols) if use_context else []
            with st.status("Starting research", expanded=True) as status:
                stage = st.empty()
                preview = st.empty()
                started = time.monotonic()

                def progress(message):
                    stage.write(f"{message} · {int(time.monotonic() - started)}s elapsed")

                def on_text(text):
                    preview.markdown(re.sub(r"(?<!\\)\$", r"\\$", clean_report_markdown(text)))

                result = _manager(*factory_args, progress=progress, on_text=on_text, checkpoint=checkpoint).run(request, context)
                result["model"] = model_name
                result["crewai_enabled"] = use_crewai
                if use_crewai and result.get("report") and result.get("status") in {"complete", "needs_review"}:
                    stage.write("CrewAI committee is debating the investment decision")
                    try:
                        result["crewai_decision"] = run_investment_committee(
                            result, openai_api_key=openai_api_key, model_name=model_name,
                        )
                        result.pop("crewai_error", None)
                    except Exception as exc:
                        result["crewai_error"] = failure_reason(exc)
                history = st.session_state.get("dr_history", [])
                st.session_state["dr_history"] = [result] + [r for r in history if r["id"] != result["id"]][:4]
                st.session_state["dr_active_run"] = result["id"]
                ready = result["status"] in {"complete", "needs_review"}
                status.update(label="Review complete; evidence issues remain" if result["status"] == "needs_review" else "Research ready" if ready else "Draft ready; review pending" if result["status"] == "review_pending" else "Evidence saved; report incomplete",
                              state="complete" if ready else "error", expanded=False)
        except ValueError as exc:
            st.error(sanitize_error(exc))
        except Exception as exc:
            st.error("Research could not start. " + failure_reason(exc) + " Any earlier reports remain available.")

    history = st.session_state.get("dr_history", [])
    if not history:
        st.divider()
        for col, title, body in zip(st.columns(3),
                                   ["01 · Gather evidence", "02 · Challenge the thesis", "03 · Make the case"],
                                   ["Financial statements, valuation, price history, news, and saved app results.",
                                    "Investigate earnings, company disclosures, peer differences, and contradictory evidence.",
                                    "A sourced research memo with scenarios, risks, thesis invalidation signals, and downloads."]):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.write(body)
        return

    for saved in history:
        if saved.get("status") == "review_pending" and saved.get("review_status") == "needs_review":
            saved["status"] = "needs_review"
    st.divider()
    lookup = {r["id"]: r for r in history}
    chosen = st.selectbox("Research history", list(lookup), key="dr_active_run",
                          format_func=lambda key: f"{', '.join(lookup[key]['request']['symbols'])} · {lookup[key]['created_at']} · {lookup[key]['status']}")
    result = lookup[chosen]
    symbols = ", ".join(result["request"]["symbols"])
    status_label = ("Complete · Caveats disclosed" if result.get("finalized_with_caveats") else
                    str(result.get("status", "unknown")).replace("_", " ").title())
    st.markdown(f"### {symbols} Research Brief")
    summary = st.columns(4)
    summary[0].metric("Review status", status_label)
    summary[1].metric("Investment horizon", result["request"].get("horizon", "—"))
    summary[2].metric("Evidence records", len(result.get("evidence", [])))
    cost = result.get("estimated_model_cost_usd")
    summary[3].metric("Model cost", f"${cost:.4f}" if cost is not None else "—")
    details = [result.get("created_at", ""), result.get("model", model_name)]
    if result.get("elapsed_seconds"):
        details.append(f"{result['elapsed_seconds']:.0f}s run time")
    if cost is not None and result.get("token_counts_estimated"):
        details.append("cost estimated from text size")
    st.caption(" · ".join(str(value) for value in details if value))
    if result.get("request", {}).get("include_news"):
        news_records = [item for item in result.get("evidence", [])
                        if item.get("category") == "news" and item.get("provider") == "Serper"
                        and item.get("status") == "ok"]
        news_items = sum(len(item.get("data", [])) for item in news_records if isinstance(item.get("data"), list))
        if news_items:
            covered = len({item.get("symbol") for item in news_records if item.get("symbol")})
            st.caption(f"Serper news coverage · {news_items} results · {covered}/{len(result['request']['symbols'])} companies · {result['request'].get('news_days', 30)}-day lookback")
        else:
            st.warning("Serper news was requested, but no usable news results were saved. Check the data-coverage details and SERPER_API_KEY.")
    for warning in result["warnings"]:
        st.warning(re.sub(r"(?<!\\)\$", r"\\$", warning))
    if result["gaps"]:
        with st.expander(f"Data coverage: {len(result['gaps'])} unavailable datasets or searches"):
            for gap in result["gaps"]:
                st.write(gap)
    if result["status"] == "needs_review":
        with st.container(border=True):
            st.markdown("**Review is complete, with unresolved evidence limitations.**")
            st.caption("Finalize when you accept the disclosed limitations. Warnings remain attached to the report and its exports.")
            if st.button("Finalize report", type="primary", key=f"dr_finalize_{chosen}"):
                finalized = finalize_report(result)
                st.session_state["dr_history"] = [finalized if item["id"] == chosen else item for item in history]
                st.rerun()
    if result["status"] not in {"complete", "needs_review"} and st.button("Retry review" if result.get("draft") else "Retry report writing", key=f"dr_retry_{chosen}"):
        active_run = chosen
        try:
            with st.status("Resuming saved research", expanded=True) as retry_status:
                stage, preview = st.empty(), st.empty()
                resumed = _manager(*factory_args, progress=stage.write,
                                   on_text=lambda text: preview.markdown(
                                       re.sub(r"(?<!\\)\$", r"\\$", clean_report_markdown(text))),
                                   checkpoint=checkpoint).resume(result)
                result.update(resumed)
                checkpoint(result)
                reviewed = result["status"] in {"complete", "needs_review"}
                retry_status.update(label="Research ready" if result["status"] == "complete" else "Review complete; evidence issues remain" if reviewed else "Saved work retained; another retry may be needed",
                                    state="complete" if reviewed else "error", expanded=False)
                st.rerun()
        except Exception as exc:
            st.error("Retry stopped. " + failure_reason(exc) + " Your saved evidence is unchanged; retrying never recollects market data.")

    memo, compare, committee, sources, notebook = st.tabs(
        ["Investment thesis", "Company comparison", "CrewAI decision", "Sources & evidence", "Research notebook"],
        key=f"dr_result_tabs_{chosen}", on_change="rerun",
    )
    with memo:
        if memo.open:
            if result.get("finalized_with_caveats"):
                st.info("Finalized with disclosed review limitations. The original warnings remain attached above.")
            elif result["status"] == "needs_review":
                st.info("Review completed and flagged evidence issues. Check the warnings and sources before relying on the thesis. Start a new run when fresh source data is available.")
            elif result["status"] != "complete":
                st.info("This is saved draft text. Review has not completed." if result.get("draft") else "Report generation has not completed. You can retry using the saved evidence.")
            with st.container(border=True):
                st.caption(f"EXECUTIVE EQUITY RESEARCH · {symbols}")
                st.divider()
                st.markdown(re.sub(r"(?<!\\)\$", r"\\$", clean_report_markdown(result["report"])))
    with compare:
        if compare.open:
            _render_comparison(result)
    with committee:
        if committee.open:
            decision = result.get("crewai_decision")
            if decision:
                _render_crew_decision(decision)
            else:
                committee_ready = bool(result.get("report")) and result.get("status") in {"complete", "needs_review"}
                if result.get("crewai_error"):
                    st.warning("The prior CrewAI attempt did not complete: " + result["crewai_error"])
                st.caption("Run the committee over this saved report. It reuses existing evidence and does not fetch market data again."
                           if committee_ready else "Complete the research review before requesting a committee decision.")
                if st.button("Run CrewAI investment committee", type="primary", key=f"dr_crew_{chosen}",
                             disabled=not committee_ready):
                    try:
                        with st.spinner("CrewAI agents are debating fundamentals, valuation, and risk..."):
                            result["crewai_decision"] = run_investment_committee(
                                result, openai_api_key=openai_api_key, model_name=model_name,
                            )
                        result.pop("crewai_error", None)
                        st.session_state["dr_history"] = [result if item["id"] == chosen else item for item in history]
                        st.rerun()
                    except Exception as exc:
                        result["crewai_error"] = failure_reason(exc)
                        st.error("CrewAI could not complete the decision. " + result["crewai_error"] + " The saved research is unchanged.")
    with sources:
        if sources.open:
            _render_sources(result)
    with notebook:
        if notebook.open:
            with st.expander("Research plan", expanded=True):
                st.json(result["plan"], expanded=False)
            if result.get("diagnostics"):
                with st.expander("Run details"):
                    st.dataframe(pd.DataFrame(result["diagnostics"]), hide_index=True, width="stretch")
            st.caption("Ask about this saved research. Follow-ups use its evidence without fetching new market data.")
            with st.form(f"dr_followup_{chosen}", clear_on_submit=True):
                question = st.text_input("Follow-up question", max_chars=4000)
                ask = st.form_submit_button("Ask about this research")
            if ask and question.strip():
                try:
                    with st.spinner("Reviewing the research..."):
                        answer = _manager(*factory_args).follow_up(result, question)
                    result.setdefault("follow_ups", []).append({"question": question, "answer": answer})
                except Exception:
                    st.error("Could not answer the follow-up. The saved research is unchanged.")
            for item in result.get("follow_ups", []):
                st.markdown(f"**{item['question']}**")
                st.markdown(re.sub(r"(?<!\\)\$", r"\\$", clean_report_markdown(item["answer"])))

    st.divider()
    downloads = st.columns(4)
    filename = "research_" + "_".join(result["request"]["symbols"]) + "_" + result["id"]
    clean_markdown = clean_report_markdown(result.get("report", ""))
    downloads[0].download_button("Download executive PDF", build_research_pdf(result), filename + ".pdf",
                                 "application/pdf", key=f"dr_pdf_{chosen}")
    downloads[1].download_button("Download research memo", clean_markdown, filename + ".md", "text/markdown", key=f"dr_md_{chosen}")
    downloads[2].download_button("Download evidence & report", dumps(result), filename + ".json", "application/json", key=f"dr_json_{chosen}")
    downloads[3].download_button("Download comparison CSV", pd.DataFrame(result["comparison"]).to_csv(index=False), filename + ".csv", "text/csv", key=f"dr_csv_{chosen}")
