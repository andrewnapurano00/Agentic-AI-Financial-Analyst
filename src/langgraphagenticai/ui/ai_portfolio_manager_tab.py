from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from langgraphagenticai.portfolio_manager.hybrid_workflow import run_hybrid_portfolio_workflow

SAMPLE_FILE = Path("data/sample_holdings.csv")
DEFAULT_HOLDINGS_TEMPLATE = pd.DataFrame(
    [
        {"ticker": "AAPL", "shares": 25},
        {"ticker": "MSFT", "shares": 18},
        {"ticker": "NVDA", "shares": 12},
        {"ticker": "JPM", "shares": 14},
        {"ticker": "XOM", "shares": 16},
    ]
)


def _get_sample_holdings_df() -> pd.DataFrame:
    if SAMPLE_FILE.exists():
        try:
            return pd.read_csv(SAMPLE_FILE)
        except Exception:
            pass
    return DEFAULT_HOLDINGS_TEMPLATE.copy()


def _normalize_holdings_df(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = [str(c).strip().lower() for c in work.columns]
    if "ticker" not in work.columns or "shares" not in work.columns:
        return pd.DataFrame(columns=["ticker", "shares"])
    work["ticker"] = work["ticker"].astype(str).str.upper().str.strip()
    work["shares"] = pd.to_numeric(work["shares"], errors="coerce")
    work = work[(work["ticker"] != "") & work["shares"].notna() & (work["shares"] > 0)].copy()
    if work.empty:
        return pd.DataFrame(columns=["ticker", "shares"])
    return work.groupby("ticker", as_index=False).agg({"shares": "sum"})


def _get_holdings_input() -> pd.DataFrame:
    mode = st.radio(
        "How should the portfolio be entered?",
        ["Use example portfolio", "Type holdings in app", "Upload file"],
        horizontal=True,
        index=0,
    )
    sample_df = _get_sample_holdings_df()
    st.download_button(
        "Download holdings template",
        data=sample_df.to_csv(index=False).encode("utf-8"),
        file_name="portfolio_holdings_template.csv",
        mime="text/csv",
    )

    if mode == "Upload file":
        uploaded = st.file_uploader("Upload holdings CSV/XLSX", type=["csv", "xlsx"])
        if uploaded is None:
            st.info("No file uploaded yet. Using the example portfolio below as a starting point.")
            uploaded_df = sample_df
        else:
            uploaded_df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        edited = st.data_editor(uploaded_df, use_container_width=True, num_rows="dynamic")
        return _normalize_holdings_df(pd.DataFrame(edited))

    seed = sample_df if mode == "Use example portfolio" else sample_df.copy()
    edited = st.data_editor(
        seed,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", required=True),
            "shares": st.column_config.NumberColumn("Shares", min_value=0.0, step=1.0, required=True),
        },
    )
    return _normalize_holdings_df(pd.DataFrame(edited))


def _money(x: Any) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"${float(x):,.0f}"
    except Exception:
        return "NA"


def _pct(x: Any) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "NA"


def _pct_points(x: Any) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x):.1f}%"
    except Exception:
        return "NA"


def _score(x: Any) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x):.1f}"
    except Exception:
        return "NA"


def _format_table(
    df: pd.DataFrame | None,
    pct_decimal_cols: list[str] | None = None,
    pct_point_cols: list[str] | None = None,
    money_cols: list[str] | None = None,
    score_cols: list[str] | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    for col in pct_decimal_cols or []:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_pct)
    for col in pct_point_cols or []:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_pct_points)
    for col in money_cols or []:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_money)
    for col in score_cols or []:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(_score)
    return out


def _render_summary(bundle: dict[str, Any]) -> None:
    summary = bundle.get("portfolio_summary", {}) or {}
    diag = bundle.get("run_diagnostics", {}) or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value", _money(summary.get("portfolio_value", 0)))
    c2.metric("Names analyzed", str(summary.get("analysis_count", 0)))
    c3.metric("AI status", str(diag.get("agentic_ai_status", "unknown")).replace("_", " ").title())
    c4.metric("Target weight sum", _pct(diag.get("target_weight_sum", 0)))
    if diag.get("agentic_ai_error"):
        st.warning(f"OpenAI committee fallback was used: {diag.get('agentic_ai_error')}")
    if diag.get("validator_adjusted_names", 0):
        st.info(f"Constraint validator adjusted {diag.get('validator_adjusted_names')} AI target weight(s) to satisfy max position/sector rules.")


def _safe_text(value: Any, fallback: str = "Not provided") -> str:
    """Return display-safe one-line text without leaking NaN/None values."""
    try:
        if value is None or pd.isna(value):
            return fallback
    except Exception:
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return fallback
    return " ".join(text.split())


def _render_committee_decision_summaries(rec: pd.DataFrame) -> None:
    """Render the narrative committee decisions below the grid so long text does not corrupt table layout."""
    if rec is None or rec.empty:
        return

    st.markdown("### Committee Decision Summaries")
    st.caption("Ticker-by-ticker committee decisions are shown below the table so the recommendation grid stays readable.")

    summary_cols = [
        "ticker", "company_name", "final_action", "committee_conviction",
        "current_weight", "target_weight", "delta_weight", "trade_value",
        "committee_reason", "key_risks", "monitoring_triggers", "constraint_flags",
    ]
    available = [c for c in summary_cols if c in rec.columns]
    work = rec[available].copy()

    for _, row in work.iterrows():
        ticker = _safe_text(row.get("ticker"), "UNKNOWN")
        action = _safe_text(row.get("final_action"), "No action")
        conviction = _safe_text(row.get("committee_conviction"), "NA")
        name = _safe_text(row.get("company_name"), "")
        current_w = _pct(row.get("current_weight")) if "current_weight" in work.columns else "NA"
        target_w = _pct(row.get("target_weight")) if "target_weight" in work.columns else "NA"
        delta_w = _pct(row.get("delta_weight")) if "delta_weight" in work.columns else "NA"
        trade_value = _money(row.get("trade_value")) if "trade_value" in work.columns else "NA"
        reason = _safe_text(row.get("committee_reason"), "No committee rationale returned.")
        risks = _safe_text(row.get("key_risks"), "No specific risks returned.")
        triggers = _safe_text(row.get("monitoring_triggers"), "No monitoring triggers returned.")
        flags = _safe_text(row.get("constraint_flags"), "None")

        with st.expander(f"{ticker} — {action} | Target {target_w} | Conviction: {conviction}", expanded=False):
            if name:
                st.markdown(f"**Company:** {name}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Current weight", current_w)
            m2.metric("Target weight", target_w)
            m3.metric("Weight change", delta_w)
            m4.metric("Trade value", trade_value)

            st.markdown("**Committee decision**")
            st.write(reason)

            st.markdown("**Key risks**")
            st.write(risks)

            st.markdown("**Monitoring triggers**")
            st.write(triggers)

            if flags != "None":
                st.markdown("**Constraint notes**")
                st.write(flags)


def _render_main_recommendations(bundle: dict[str, Any]) -> None:
    rec = bundle.get("recommendation_table", pd.DataFrame())
    if rec is None or rec.empty:
        st.info("No recommendations available.")
        return

    st.markdown("### Recommendation Grid")
    st.caption("The table is intentionally compact. Full committee reasoning is summarized below by ticker.")

    cols = [
        "ticker", "company_name", "sector", "asset_type", "final_action", "committee_conviction",
        "current_weight", "target_weight", "delta_weight", "trade_value", "share_change",
        "constraint_flags",
    ]
    display = _format_table(
        rec[[c for c in cols if c in rec.columns]],
        pct_decimal_cols=["current_weight", "target_weight", "delta_weight"],
        money_cols=["trade_value"],
    )
    st.dataframe(display, use_container_width=True, hide_index=True)

    _render_committee_decision_summaries(rec)

    st.download_button(
        "Download recommendation table CSV",
        data=rec.to_csv(index=False).encode("utf-8"),
        file_name="hybrid_ai_portfolio_recommendations.csv",
        mime="text/csv",
    )


def _render_rebalance(bundle: dict[str, Any]) -> None:
    rb = bundle.get("rebalance_table", pd.DataFrame())
    if rb is None or rb.empty:
        st.info("No rebalance table available.")
        return
    cols = [
        "ticker", "final_action", "rebalance_action", "trade_direction", "current_weight", "target_weight",
        "delta_weight", "current_value", "target_value", "trade_value", "current_shares", "target_shares",
        "share_change", "last_price", "trade_priority", "constraint_flags", "rebalance_reason",
    ]
    display = _format_table(
        rb[[c for c in cols if c in rb.columns]],
        pct_decimal_cols=["current_weight", "target_weight", "delta_weight"],
        money_cols=["current_value", "target_value", "trade_value", "last_price"],
    )
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button(
        "Download rebalance table CSV",
        data=rb.to_csv(index=False).encode("utf-8"),
        file_name="hybrid_ai_rebalance_table.csv",
        mime="text/csv",
    )


def _render_agent_debate(bundle: dict[str, Any]) -> None:
    rec = bundle.get("recommendation_table", pd.DataFrame())
    if rec is None or rec.empty:
        st.info("No agent views available.")
        return
    cols = [
        "ticker", "fundamental_agent_view", "valuation_agent_view", "forward_agent_view",
        "technical_agent_view", "risk_agent_view", "portfolio_construction_agent_view", "lead_pm_view",
        "committee_reason",
    ]
    st.dataframe(rec[[c for c in cols if c in rec.columns]], use_container_width=True, hide_index=True)


def _render_evidence(bundle: dict[str, Any]) -> None:
    ev = bundle.get("evidence_table", pd.DataFrame())
    if ev is None or ev.empty:
        st.info("No evidence table available.")
        return
    cols = [
        "ticker", "sector", "asset_type", "evidence_action", "composite_score", "fundamental_score",
        "valuation_score", "forward_score", "technical_score", "risk_score", "analyst_upside_pct",
        "forward_revenue_growth", "forward_eps_growth", "forward_pe", "price_to_sales", "price_to_book",
        "debt_to_equity", "rsi_14", "price_vs_50dma", "price_vs_200dma", "ret_1m", "ret_3m",
        "ret_6m", "ret_12m", "key_supports", "key_conflicts",
    ]
    display = _format_table(
        ev[[c for c in cols if c in ev.columns]],
        pct_point_cols=["analyst_upside_pct", "forward_revenue_growth", "forward_eps_growth", "price_vs_50dma", "price_vs_200dma", "ret_1m", "ret_3m", "ret_6m", "ret_12m"],
        score_cols=["composite_score", "fundamental_score", "valuation_score", "forward_score", "technical_score", "risk_score"],
    )
    st.dataframe(display, use_container_width=True, hide_index=True)


def _render_sector(bundle: dict[str, Any]) -> None:
    sector = bundle.get("sector_allocation_table", pd.DataFrame())
    if sector is None or sector.empty:
        st.info("No sector allocation available.")
        return
    display = _format_table(
        sector,
        pct_decimal_cols=["current_weight", "target_weight", "delta_weight"],
        money_cols=["current_value", "target_value"],
    )
    st.dataframe(display, use_container_width=True, hide_index=True)


def _render_monitoring(bundle: dict[str, Any]) -> None:
    mon = bundle.get("monitoring_table", pd.DataFrame())
    if mon is None or mon.empty:
        st.info("No monitoring table available.")
        return
    st.dataframe(mon, use_container_width=True, hide_index=True)


def _render_diagnostics(bundle: dict[str, Any]) -> None:
    with st.expander("Run diagnostics", expanded=True):
        st.json(bundle.get("run_diagnostics", {}), expanded=False)
    with st.expander("Raw AI committee result", expanded=False):
        result = dict(bundle.get("agentic_ai_committee_result", {}) or {})
        if "raw_response" in result:
            result["raw_response"] = str(result["raw_response"])[:4000]
        st.json(result, expanded=False)
    if bundle.get("position_snapshot") is not None and not bundle["position_snapshot"].empty:
        with st.expander("Current portfolio snapshot", expanded=False):
            snap = _format_table(bundle["position_snapshot"], pct_decimal_cols=["current_weight"], money_cols=["market_value"])
            st.dataframe(snap, use_container_width=True, hide_index=True)


def _render_ai_chat(bundle: dict[str, Any], openai_api_key: str, model_name: str) -> None:
    st.caption("Ask a question about this run. This uses a compact context from the latest recommendations; it does not pull news articles.")
    question = st.text_area("Question", value="Why did the committee recommend these target weights?", height=80)
    if st.button("Ask Portfolio Manager", type="secondary"):
        if not openai_api_key:
            st.warning("OpenAI key is not loaded, so the chat answer is unavailable.")
            return
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            rec = bundle.get("recommendation_table", pd.DataFrame())
            context_cols = ["ticker", "final_action", "current_weight", "target_weight", "delta_weight", "committee_reason", "key_risks", "constraint_flags"]
            context = rec[[c for c in context_cols if c in rec.columns]].head(30).to_dict(orient="records") if rec is not None and not rec.empty else []
            prompt = {
                "question": question,
                "portfolio_summary": bundle.get("portfolio_summary", {}),
                "recommendations": context,
                "rules": ["Use only this run context.", "Be concise and portfolio-manager style."]
            }
            response = client.responses.create(
                model=model_name,
                input=[
                    {"role": "system", "content": "You answer questions about an AI portfolio committee run using only supplied context."},
                    {"role": "user", "content": str(prompt)},
                ],
            )
            st.write(getattr(response, "output_text", "") or "No response text returned.")
        except Exception as exc:
            st.error(f"AI chat failed: {exc}")


def render_ai_portfolio_manager_tab(
    openai_api_key: str,
    model_name: str,
    marketaux_api_key: str = "",
    fmp_api_key: str = "",
) -> None:
    st.subheader("Agentic AI Portfolio Manager")
    st.caption(
        "AI-powered portfolio recommendations that evaluate each holding across fundamentals, valuation, forward estimates, "
        "technical momentum, risk, and portfolio fit. The system produces target weights, trade actions, committee rationale, "
        "and monitoring priorities, then validates allocations against position limits, sector exposure, cash targets, and trade math."
    )

    analysis_mode = st.radio(
        "Choose analysis mode",
        ["Analyze portfolio / uploaded holdings", "Analyze entered tickers", "Screen companies"],
        horizontal=True,
        index=0,
    )

    with st.sidebar:
        st.header("Agentic AI Portfolio Manager")
        benchmark = st.text_input("Benchmark", value="SPY").upper().strip()
        period = st.selectbox("Price history window", ["1y", "2y", "5y"], index=1)
        risk_profile = st.selectbox("Risk profile", ["Conservative", "Balanced", "Aggressive"], index=1)
        max_weight = st.slider("Maximum position weight", 0.08, 0.30, 0.18, 0.01)
        max_sector_weight = st.slider("Maximum sector weight", 0.20, 0.60, 0.35, 0.01)
        cash_buffer = st.slider("Target cash buffer", 0.00, 0.20, 0.00, 0.01)
        min_trade_weight_change = st.slider("Ignore trades smaller than", 0.001, 0.02, 0.0025, 0.001)
        run_button = st.button("Run hybrid AI committee", type="primary")
        st.divider()
        st.caption(f'FMP key loaded: {"Yes" if bool(fmp_api_key) else "No"}')
        st.caption(f'OpenAI key loaded: {"Yes" if bool(openai_api_key) else "No"}')
        st.caption("MarketAux/news overlay: Disabled in Portfolio Manager")
        if marketaux_api_key:
            st.caption("MarketAux key detected but intentionally unused here.")

    holdings_df = None
    tickers_text = ""
    screen_filters = None
    selected_screen_tickers = None

    if analysis_mode == "Analyze portfolio / uploaded holdings":
        st.markdown("### Portfolio Input")
        holdings_df = _get_holdings_input()
        tickers_text = st.text_area(
            "Optional watchlist tickers to analyze alongside holdings",
            value="LLY, GOOGL, AVGO, COST, XLF, XLK",
            height=80,
        )
        mode_key = "holdings"
    elif analysis_mode == "Analyze entered tickers":
        st.markdown("### Enter Tickers")
        tickers_text = st.text_area("Tickers", value="AAPL, MSFT, NVDA, META", height=80)
        mode_key = "manual"
    else:
        st.markdown("### FMP Stock Screener")
        c1, c2, c3 = st.columns(3)
        with c1:
            sector = st.text_input("Sector", value="Technology")
            market_cap_more_than = st.number_input("Market cap more than", min_value=0.0, value=10_000_000_000.0, step=1_000_000_000.0)
            price_more_than = st.number_input("Price more than", min_value=0.0, value=5.0, step=1.0)
        with c2:
            exchange = st.text_input("Exchange", value="NASDAQ")
            beta_lower_than = st.number_input("Beta lower than", min_value=0.0, value=2.5, step=0.1)
            volume_more_than = st.number_input("Volume more than", min_value=0.0, value=500000.0, step=100000.0)
        with c3:
            country = st.text_input("Country", value="US")
            limit = st.slider("Server page size", 25, 250, 100, 25)
            analyze_top_n = st.slider("Analyze top N returned names", 5, 30, 12, 1)
        screen_filters = {
            "sector": sector or None,
            "exchange": exchange or None,
            "country": country or None,
            "marketCapMoreThan": market_cap_more_than or None,
            "priceMoreThan": price_more_than or None,
            "volumeMoreThan": volume_more_than or None,
            "betaLowerThan": beta_lower_than or None,
            "isActivelyTrading": True,
            "isEtf": False,
            "isFund": False,
            "limit": limit,
            "analyze_top_n": analyze_top_n,
            "max_pages": 3,
        }
        mode_key = "screen"

    if run_button:
        try:
            with st.spinner("Running hybrid agentic portfolio workflow..."):
                bundle = run_hybrid_portfolio_workflow(
                    mode=mode_key,
                    benchmark=benchmark,
                    period=period,
                    openai_api_key=openai_api_key,
                    model_name=model_name,
                    fmp_api_key=fmp_api_key,
                    max_weight=max_weight,
                    max_sector_weight=max_sector_weight,
                    cash_buffer=cash_buffer,
                    min_trade_weight_change=min_trade_weight_change,
                    holdings_df=holdings_df,
                    tickers_text=tickers_text,
                    screen_filters=screen_filters,
                    selected_screen_tickers=selected_screen_tickers,
                    risk_profile=risk_profile,
                )
            st.session_state["pm_hybrid_bundle_v1"] = bundle
            st.success("AI portfolio review completed. Review target weights, trades, committee rationale, and validator notes below.")
        except Exception as exc:
            st.error(str(exc))

    bundle = st.session_state.get("pm_hybrid_bundle_v1")
    if not bundle:
        st.info("Run the hybrid AI committee to generate recommendations.")
        return

    if bundle.get("screen_df") is not None and not bundle["screen_df"].empty:
        with st.expander("Preview screened candidates", expanded=False):
            st.dataframe(bundle["screen_df"], use_container_width=True, hide_index=True)
            if bundle.get("screen_meta"):
                st.caption(f"Pages fetched: {bundle['screen_meta'].get('pages', 0)}")

    _render_summary(bundle)
    st.markdown("## AI Committee Summary")
    st.write(bundle.get("portfolio_committee_summary") or "No summary available.")

    tabs = st.tabs([
        "Recommendations",
        "Rebalance Trades",
        "Agent Debate",
        "Evidence Scores",
        "Sector Exposure",
        "Monitoring",
        "Diagnostics",
        "AI Chat",
    ])
    with tabs[0]:
        _render_main_recommendations(bundle)
    with tabs[1]:
        _render_rebalance(bundle)
    with tabs[2]:
        _render_agent_debate(bundle)
    with tabs[3]:
        _render_evidence(bundle)
    with tabs[4]:
        _render_sector(bundle)
    with tabs[5]:
        _render_monitoring(bundle)
    with tabs[6]:
        _render_diagnostics(bundle)
    with tabs[7]:
        _render_ai_chat(bundle, openai_api_key, model_name)
