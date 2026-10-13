from __future__ import annotations

from html import escape
from langgraphagenticai.ui.opening_presentation import opening_styles, heading, cards, observations, number, terminal_chart
from langgraphagenticai.providers.discovery import finite_number
from langgraphagenticai.providers.company_terminal import load_company_terminal, load_terminal_evidence
from langgraphagenticai.analysis.company_terminal import KEY_STATISTICS, GROWTH_STATISTICS, build_metrics
from langgraphagenticai.ui.opening_presentation import quote_header, price_rail, metric_grid, opening_price_chart
from langgraphagenticai.ui.company_terminal import render_earnings, render_peers, render_metric_evidence
from langgraphagenticai.state.discovery import queue_discovery
from langgraphagenticai.ui.market_overview_data import SECTORS, MOVER_UNIVERSE
from langgraphagenticai.ui.app_shell import render_company_header, render_evidence_row, render_executive_cards, render_workspace_state
from langgraphagenticai.ui.workspace_presentation import snapshot_status, source_link, saved_time, market_status

import streamlit as st
import pandas as pd
import altair as alt
from langgraphagenticai.providers.market_history import load_market_chart, RANGES
from langgraphagenticai.providers.symbol_history import load_symbol_history, clear_history_cache
from langgraphagenticai.ui.technical_chart import render_technical_chart

from langgraphagenticai.ui.company_snapshot import (
    generate_company_summary,
    load_company_snapshot,
    normalize_symbol,
    snapshot_json,
)
from langgraphagenticai.ui.market_overview_data import load_market_overview, INDEXES
from langgraphagenticai.utils.safety import sanitize_error


def _interactive_price_chart(frame: pd.DataFrame, value_column: str) -> None:
    chart = alt.Chart(frame.reset_index()).mark_line(color="#19d6f5").encode(
        x=alt.X(f"{frame.index.name}:T", title="Date"),
        y=alt.Y(f"{value_column}:Q", scale=alt.Scale(zero=False), title=value_column),
        tooltip=[alt.Tooltip(f"{frame.index.name}:T", title="Date"),
                 alt.Tooltip(f"{value_column}:Q", format=",.2f")],
    ).properties(height=280).interactive()
    st.altair_chart(terminal_chart(chart), use_container_width=True, theme=None)


def _fmt(value: float | None, decimals: int = 2) -> str:
    return number(value, decimals=decimals)


def _move(snapshot: dict | None) -> tuple[str, str]:
    if not snapshot:
        return "N/A", "flat"
    if finite_number(snapshot.get("percent")) is None:
        return "N/A", "flat"
    pct = float(snapshot["percent"])
    return f"{pct:+.2f}%", "up" if pct >= 0 else "down"


def _line_chart(points: list[tuple[object, float]]) -> str:
    if len(points) < 2:
        return '<div class="chart-empty">Intraday prices are temporarily unavailable.</div>'
    values = [value for _, value in points]
    low, high = min(values), max(values)
    span = high - low or 1.0
    coords = []
    for idx, value in enumerate(values):
        x = idx / (len(values) - 1) * 790
        y = 132 - ((value - low) / span * 112)
        coords.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(coords)
    area = f"0,145 {polyline} 790,145"
    return f'''<svg class="intro-chart" viewBox="0 0 790 150" preserveAspectRatio="none" role="img" aria-label="Live S&amp;P 500 intraday chart">
      <defs><linearGradient id="liveArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#17d9ff" stop-opacity=".24"/><stop offset="1" stop-color="#17d9ff" stop-opacity="0"/></linearGradient></defs>
      <g class="grid"><path d="M0 30H790M0 60H790M0 90H790M0 120H790M100 0V150M200 0V150M300 0V150M400 0V150M500 0V150M600 0V150M700 0V150"/></g>
      <polygon points="{area}" fill="url(#liveArea)"/><polyline points="{polyline}" class="cyan-line"/>
    </svg>'''


def _money(value: float | None) -> str:
    if value is None:
        return "N/A"
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= divisor:
            return f"${value / divisor:,.2f}{suffix}"
    return f"${value:,.2f}"


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:+.1f}%"


def _company_chart(series: list[dict]) -> str:
    points = [(row.get("date"), float(row["close"])) for row in series if row.get("close") is not None]
    return _line_chart(points)


def _render_company_snapshot(snapshot: dict, summary: str, fmp_api_key="", openai_api_key="", model_name="gpt-5") -> None:
    symbol, profile, quote = snapshot["symbol"], snapshot.get("profile", {}), snapshot.get("quote", {})
    try:
        terminal = load_company_terminal(symbol, fmp_api_key, snapshot)
    except Exception as exc:
        terminal = {"metrics": build_metrics(snapshot), "earnings": {}, "peers": [], "warnings": ["Company extension unavailable: " + sanitize_error(exc)], "retrieved_at": None}
    quote_header(symbol, snapshot["company"], profile.get("sector"), quote, analyst=terminal.get("analyst", True))
    if terminal.get("analyst"):
        st.caption(terminal["analyst"]["note"] + " Retrieved " + saved_time(terminal["analyst"].get("retrieved_at")))
    st.caption(f"FMP quote as of {saved_time(quote.get('timestamp'))} | retrieved {saved_time(snapshot.get('fetched_at'))} | profile currency {profile.get('currency') or 'Unavailable'} is separate metadata. Extended-session prices unavailable.")
    price_rail(quote)
    chart_column, metrics_column = st.columns([2, 1], gap="medium")
    with chart_column, st.container(border=True):
        st.markdown('<span class="company-price-marker"></span>', unsafe_allow_html=True)
        st.subheader("Price History")
        period = st.segmented_control("Company historical range", list(RANGES), default="1Y", key=f"intro_company_range_{symbol}") or "1Y"
        if st.button("Retry company chart", key=f"intro_company_chart_retry_{symbol}"):
            clear_history_cache()
        try:
            chart = load_symbol_history(symbol, fmp_api_key, period, quote.get("currency") or "")
        except Exception as exc:
            chart = {"points": [], "period": period, "warnings": ["Company chart unavailable: " + sanitize_error(exc)]}
        points = chart.get("points", [])
        if points:
            from langgraphagenticai.ui.technical_chart import price_chart_spec
            frame = pd.DataFrame(points, columns=["Date", "Close"])
            preview = opening_price_chart(frame, period, chart.get("unit", "Currency unknown"), height=385)
            st.altair_chart(preview, use_container_width=True, theme=None)
        else:
            st.info("Company price history unavailable. Retry or choose another range; financial evidence remains readable.")
        st.caption(f"{chart.get('provider', 'Unavailable')} | {chart.get('price_basis', 'Basis unavailable')} | {chart.get('unit', 'Currency unknown')} | timezone {chart.get('timezone', 'Unknown')} | as of {chart.get('as_of', 'Unavailable')} | retrieved {saved_time(chart.get('retrieved_at'))}")
        for warning in chart.get("warnings", []):
            st.caption(warning)
    with chart_column:
        description = profile.get("description") or "Company description unavailable."
        website = source_link(profile.get("website"))
        link = f'<p><a href="{escape(website, quote=True)}" target="_blank" rel="noopener noreferrer">Company website</a></p>' if website else ""
        st.markdown(f'<section class="terminal-panel"><h3>About {escape(snapshot["company"])}</h3><p>{escape(str(description))}</p>{link}</section>', unsafe_allow_html=True)
    with metrics_column:
        metric_grid("Key Statistics", KEY_STATISTICS, terminal["metrics"])
        metric_grid("Growth & Profitability", GROWTH_STATISTICS, terminal["metrics"])
        st.caption("Ratios: latest provider TTM (period dates may be absent). Margins prefer calculated quarterly TTM; provider fallback is labelled in metric evidence. YoY: quarterly TTM; CAGR: annual FY; forward P/E: annual consensus forecast. Hover for basis; full evidence below.")
    earnings_column, peers_column = st.columns([1, 1.25], gap="medium")
    with earnings_column, st.container(border=True):
        render_earnings(terminal.get("earnings", {}), terminal.get("retrieved_at"))
    with peers_column, st.container(border=True):
        render_peers(terminal.get("peers", []), symbol, terminal.get("retrieved_at"))
    action_columns = st.columns(3)
    from langgraphagenticai.ui.workspace_handoff import queue_handoff
    from langgraphagenticai.state.research_context import ResearchContext
    for column, (label, destination) in zip(action_columns, (("Valuation", "Equity Report"), (f"Ask AI about {symbol}", "Research"), ("Deep Research", "Deep Research"))):
        if column.button(label, key=f"intro_drill_{destination}", use_container_width=True):
            queue_handoff(st.session_state, ResearchContext((symbol,), destination, "deep_research" if destination == "Deep Research" else "analyze", "Introduction"))
            st.rerun()
    st.caption("Ask AI opens an editable Research draft for explicit submit. Thesis & Notes / Set Alert: unavailable; saved interpretation remains below.")
    render_metric_evidence(terminal)
    with st.expander("Historical prices and technical analysis"):
        render_technical_chart(chart, key=f"intro_company_technical_{symbol}", openai_api_key=openai_api_key, model_name=model_name, chart_style=terminal_chart)
    with st.expander("Financial metrics, performance and news", expanded=False):
        render_evidence_row(snapshot_status(snapshot))
        for dataset, reason in snapshot.get("source_errors", {}).items():
            st.caption(f"{dataset}: {sanitize_error(reason)}")
        fundamentals, performance = snapshot.get("fundamentals", {}), snapshot.get("performance", {})
        currency = snapshot.get("fundamental_basis", {}).get("currency") or "Currency unknown"
        cards([("Revenue TTM", f"{number(fundamentals.get('revenue_ttm'))} {currency}", "Four consecutive standalone quarters"),
               ("Free cash flow TTM", f"{number(fundamentals.get('free_cash_flow_ttm'))} {currency}", "Matching fiscal-quarter income/cash-flow windows"),
               ("1Y price return", _percent(performance.get("return_1y")), "Legacy snapshot close; adjustment basis unverified"),
               ("Annualized volatility", _percent(performance.get("volatility")), "Up to 252 daily changes; sqrt(252)")])
        st.subheader("Recent News & Evidence")
        st.caption("MarketAux | requested lookback 10 days | snapshot retrieval " + saved_time(snapshot.get("fetched_at")) + ". Publication dates are separate; news does not establish causality.")
        linked = 0
        for item in snapshot.get("news", []):
            url = source_link(item.get("url"))
            if url:
                linked += 1
                st.markdown(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(str(item.get("title") or "Untitled"))}</a>', unsafe_allow_html=True)
                st.caption(f"{item.get('source') or 'Publisher unavailable'} | published {item.get('published_at') or 'Unavailable'}")
        if not linked:
            st.info("No safe linked MarketAux articles are available.")
        st.dataframe(pd.DataFrame([{"Period": label, "Price return": _percent(performance.get(key))} for label, key in (("1 month", "return_1m"), ("3 months", "return_3m"), ("1 year", "return_1y"))]), hide_index=True, use_container_width=True)
    with st.expander("Saved AI interpretation", expanded=True):
        st.markdown(summary)
        st.caption("Saved AI interpretation; verify material claims against dated facts. Ordinary controls do not regenerate it.")



def _brief(data: dict):
    indexes = data.get("indexes", {})
    sp, nasdaq, vix = (indexes.get(key) or {} for key in ("S&P 500", "NASDAQ", "VIX"))
    valid = [(name, snap) for name, snap in data.get("sectors", {}).items() if snap and finite_number(snap.get("percent")) is not None]
    leader = max(valid, key=lambda item: item[1]["percent"], default=None)
    return "Deterministic observations from available quote changes; dates and providers may differ.", [
        ("Index direction", f"S&P 500 {number(sp.get('percent'), '%', True)}; Nasdaq {number(nasdaq.get('percent'), '%', True)}. Prior-close quote changes, not a live session claim."),
        ("Sector ETF leadership", f"{leader[0]} ({SECTORS.get(leader[0], 'ETF')}) has the highest available ETF quote change: {number(leader[1]['percent'], '%', True)}." if leader else "Sector ETF changes are unavailable. No leader is inferred."),
        ("Volatility context", f"VIX level {number(vix.get('price'))}; quote change {number(vix.get('percent'), '%', True)}. This is an observation, not a risk forecast."),
    ]


def _render_market_chart(fmp_api_key: str, openai_api_key="", model_name="gpt-5") -> None:
    period = st.segmented_control("S&P 500 historical range", list(RANGES), default="1D", key="intro_chart_range") or "1D"
    if st.button("Retry market chart", key="intro_market_chart_retry"):
        load_market_chart.clear()
        clear_history_cache()
    try:
        chart = load_market_chart(fmp_api_key, period)
    except Exception as exc:
        chart = {"points": [], "warnings": [f"Historical chart unavailable: {sanitize_error(exc)}"], "provider": "Unavailable"}
    chart.setdefault("period", period)
    if chart.get("points"):
        from langgraphagenticai.ui.technical_chart import price_chart_spec
        frame = pd.DataFrame(chart["points"], columns=["Date", "Close"])
        preview = opening_price_chart(frame, period, chart.get("unit", "Index points"), height=250)
        st.altair_chart(preview, theme=None, width="stretch")
        st.caption(f"{chart.get('provider', 'Unavailable')} | {chart.get('price_basis', 'Basis unavailable')} | As of {chart.get('as_of', chart['points'][-1][0])} | retrieved {saved_time(chart.get('retrieved_at'))}")
        st.caption(f"{len(chart['points'])} observed bars | {chart.get('unit', 'Index points')} | timezone {chart.get('timezone', 'Unknown')} | price performance; session coverage is unverified.")
    else:
        st.info("Market history is unavailable. Retry or choose another range.")
    with st.expander("Technical analysis & full chart evidence"):
        render_technical_chart(chart, key="intro_market_technical", openai_api_key=openai_api_key, model_name=model_name, chart_style=terminal_chart)


def _dashboard(data: dict, mode: str, fmp_api_key: str = "", openai_api_key="", model_name="gpt-5") -> None:
    indexes = data.get("indexes", {})
    sectors = [(label, snap) for label, snap in data.get("sectors", {}).items() if snap and finite_number(snap.get("percent")) is not None]
    sectors.sort(key=lambda item: item[1]["percent"], reverse=True)
    items = []
    for label in ("S&P 500", "NASDAQ", "VIX"):
        snap = indexes.get(label) or {}
        items.append((label, number(snap.get("price")), f"{number(snap.get('percent'), '%', True)} | {snap.get('provider') or 'Source unavailable'} | As of {snap.get('as_of') or 'Unavailable'}"))
    leader = sectors[0] if sectors else None
    items.append(("Leading sector ETF", leader[0] if leader else "Unavailable", f"{SECTORS.get(leader[0])} {number(leader[1]['percent'], '%', True)} | {leader[1].get('provider') or 'Source unavailable'} | As of {leader[1].get('as_of') or 'Unavailable'}" if leader else "No usable sector ETF changes"))
    candidates = [(symbol, snap) for symbol, snap in data.get("movers", []) if finite_number(snap.get("percent")) is not None]
    breadth = sum(snap["percent"] > 0 for _, snap in candidates) / len(candidates) * 100 if candidates else None
    # The provider returns the largest absolute moves, not the full fixed universe;
    # do not call those sampled candidates market breadth.
    items.append(("Discovery coverage", f"{len(candidates)} candidates", "Observed largest moves in a fixed 10-company list; market breadth unavailable"))
    cards(items)
    st.caption(f"Overview retrieved: {saved_time(data.get('fetched_at'))}. Quote dates are evidence dates; cache TTL does not establish freshness or an exchange session.")
    chart_col, sector_col = st.columns([1.85, 1], gap="medium")
    with chart_col, st.container(border=True):
        st.subheader("S&P 500")
        _render_market_chart(fmp_api_key, openai_api_key, model_name)
    with sector_col, st.container(border=True):
        st.subheader("Explore sectors")
        st.caption("Sector ETF quote changes; distinct from screened-stock averages in Top Movers.")
        if sectors:
            table = pd.DataFrame([{"Sector": label, "ETF": SECTORS.get(label), "Quote change (%)": snap["percent"]} for label, snap in sectors])
            chart = alt.Chart(table).mark_bar().encode(
                y=alt.Y("Sector:N", sort="-x", title=None), x=alt.X("Quote change (%):Q"),
                color=alt.condition(alt.datum['Quote change (%)'] >= 0, alt.value('#35d07f'), alt.value('#ff5964')),
                tooltip=["Sector", "ETF", alt.Tooltip("Quote change (%):Q", format="+.2f")],
            ).properties(height=285)
            st.altair_chart(terminal_chart(chart), use_container_width=True, theme=None)
            selected = st.selectbox("Explore a sector", [label for label, _ in sectors], key="intro_discovery_sector")
            if st.button("View sector movers", key="intro_sector_movers", use_container_width=True):
                queue_discovery(st.session_state, selected)
                st.rerun()
            with st.expander("ETF evidence dates"):
                for label, snap in sectors:
                    st.caption(f"{label} / {SECTORS.get(label)}: {snap.get('provider') or 'Unavailable'}; as of {snap.get('as_of') or 'Unavailable'}")
        else:
            st.info("Sector ETF performance is unavailable. Refresh to retry.")
    st.subheader("The market in 30 seconds")
    brief, insight = _brief(data)
    observations(insight)
    st.caption(brief)
    st.subheader("Research candidates")
    st.caption("Up to three largest absolute available quote changes from AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, LLY and AVGO. Discovery candidates, not recommendations; mixed quote dates/bases may differ.")
    if candidates:
        for col, (symbol, snap) in zip(st.columns(min(3, len(candidates))), candidates[:3]):
            with col, st.container(border=True):
                st.subheader(symbol)
                st.metric("Prior-close quote change", number(snap.get("percent"), "%", True))
                st.caption(f"{snap.get('provider') or 'Unavailable'} | As of {snap.get('as_of') or 'Unavailable'}")
                if st.button("Open company snapshot", key=f"intro_candidate_{symbol}", use_container_width=True):
                    from langgraphagenticai.ui.workspace_handoff import queue_handoff
                    from langgraphagenticai.state.research_context import ResearchContext
                    queue_handoff(st.session_state, ResearchContext((symbol,), "Introduction", "analyze", "Introduction"))
                    st.rerun()
                if st.button("Research this company", key=f"intro_candidate_research_{symbol}", use_container_width=True):
                    from langgraphagenticai.ui.workspace_handoff import queue_handoff
                    from langgraphagenticai.state.research_context import ResearchContext
                    queue_handoff(st.session_state, ResearchContext((symbol,), "Research", "analyze", "Introduction"))
                    st.rerun()
    else:
        st.info("No finite company quote changes are available in the fixed discovery list.")
    with st.expander("Macro context"):
        rows = []
        for label, snap in data.get("cross_assets", {}).items():
            snap = snap or {}
            rows.append({"Instrument": label, "Provider level (units unverified)": number(snap.get("price")), "Quote change": number(snap.get("percent"), "%", True), "Source": snap.get("provider") or "Unavailable", "As of": snap.get("as_of") or "Unavailable"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("Raw cross-asset quote levels are not normalized yields or comparable currency amounts.")


def render_introduction_tab(
    fmp_api_key: str = "", openai_api_key: str = "", model_name: str = "gpt-5",
    marketaux_api_key: str = "",
) -> None:
    opening_styles()
    heading("Company Overview" if st.session_state.get("intro_company_symbol") else "Market Brief", "Company evidence, in context." if st.session_state.get("intro_company_symbol") else "What matters. Where to look next.")
    search_col, analyze_col, back_col, refresh_col = st.columns([5.2, 1.4, 1.2, 1.2], vertical_alignment="bottom")
    with search_col:
        st.session_state.setdefault("intro_company_search", st.session_state.get("intro_company_query", ""))
        company_query = st.text_input("Company search", placeholder="Search a company ticker — AAPL, MSFT, NVDA…", label_visibility="collapsed", key="intro_company_search")
    with analyze_col:
        analyze = st.button("ANALYZE COMPANY", type="primary", use_container_width=True, key="intro_company_analyze")
    with back_col:
        back = st.button("Market Brief", use_container_width=True, key="intro_company_back")
    with refresh_col:
        if st.session_state.get("intro_company_symbol") and st.button("Refresh company evidence", key="intro_company_refresh", use_container_width=True):
            if hasattr(load_company_snapshot, "clear"):
                load_company_snapshot.clear()
            load_terminal_evidence.clear()
            clear_history_cache()
            st.rerun()
    if back:
        st.session_state.pop("intro_company_symbol", None)
        st.rerun()
    if analyze:
        try:
            st.session_state["intro_company_symbol"] = normalize_symbol(company_query)
            st.session_state["intro_company_query"] = company_query
        except ValueError as exc:
            st.error(sanitize_error(exc))

    selected_symbol = st.session_state.get("intro_company_symbol")
    if selected_symbol:
        try:
            with st.spinner(f"Building current research snapshot for {selected_symbol}..."):
                snapshot = load_company_snapshot(selected_symbol, fmp_api_key, marketaux_api_key)
            from langgraphagenticai.analysis.saved_interpretation import save_interpretation, interpretation_matches
            summary_key = f"intro_interpretation:{selected_symbol}"
            legacy = st.session_state.get(f"intro_summary:{selected_symbol}:{model_name}")
            saved = st.session_state.get(summary_key)
            if saved is None and legacy:
                saved = {"text": legacy, "symbol": selected_symbol, "model": model_name}
                st.session_state[summary_key] = saved
            summary = saved.get("text") if saved else "Use Generate / regenerate company interpretation to request AI analysis of this snapshot."
            _render_company_snapshot(snapshot, summary, fmp_api_key, openai_api_key, model_name)
            with st.expander("Company interpretation controls & saved status", expanded=True):
                if saved and not interpretation_matches(saved, snapshot, model_name):
                    st.warning("Saved interpretation belongs to different or unverified evidence/model settings. It remains readable; explicitly regenerate to use this snapshot.")
                if saved:
                    st.caption(f"Interpretation generated: {saved_time(saved.get('generated_at'))}; model: {saved.get('model', 'Unavailable')}")
                if not openai_api_key:
                    st.caption("Company data is available. Add an OpenAI key to generate the AI summary.")
                regenerate = st.button("Generate / regenerate company interpretation", key="intro_summary_generate", disabled=not bool(openai_api_key), type="primary")
                if regenerate:
                    try:
                        if hasattr(generate_company_summary, "clear"):
                            generate_company_summary.clear()
                        text = generate_company_summary(snapshot_json(snapshot), openai_api_key, model_name)
                        st.session_state[summary_key] = save_interpretation(snapshot, model_name, text)
                        st.rerun()
                    except Exception as exc:
                        st.warning(f"AI summary unavailable; previous interpretation and company evidence preserved: {sanitize_error(exc)}")
            with st.expander("Other research workspaces"):
                from langgraphagenticai.ui.workspace_handoff import render_company_handoffs
                render_company_handoffs(selected_symbol, "Introduction", key="intro_handoff")
        except Exception as exc:
            render_workspace_state(f"Company analysis could not be completed: {sanitize_error(exc)}", state="failure")
            st.info("Check the ticker and provider configuration, then try again. No stale company data is shown.")
        return

    refresh_col, status_col = st.columns([1, 4], vertical_alignment="center")
    with refresh_col:
        if st.button("Refresh market evidence", use_container_width=True, key="intro_refresh"):
            load_market_overview.clear()
            load_market_chart.clear()
            clear_history_cache()
            st.rerun()
    with status_col:
        st.caption("Quotes may be delayed. Overview cache: up to 5 minutes; Refresh requests new evidence. Exchange session status is unavailable.")
    try:
        with st.spinner("Loading current market data…"):
            data = load_market_overview(fmp_api_key)
        if not market_status(data, INDEXES)["usable_quotes"]:
            render_evidence_row([("Market coverage", "Missing"), ("Market retrieved", saved_time(data.get("fetched_at")))])
            raise RuntimeError("The market provider returned no usable index quotes.")
        for warning in data.get("warnings", []):
            st.warning(warning)
        _dashboard(data, "Market Brief", fmp_api_key, openai_api_key, model_name)
    except Exception as exc:
        st.error(f"Live market data is temporarily unavailable: {sanitize_error(exc)}")
        st.info("No stale fallback values are displayed. Use Refresh market evidence to retry the provider.")

    st.markdown('<div class="ask-label">ASK THE AI ANALYST</div>', unsafe_allow_html=True)
    prompt_col, send_col = st.columns([8, 1])
    with prompt_col:
        prompt = st.text_input("Ask about the markets", placeholder="Ask about today’s markets…", label_visibility="collapsed", key="intro_question")
    with send_col:
        submitted = st.button("Open research draft", type="primary", use_container_width=True, key="intro_ask")
    if submitted and prompt.strip():
        st.session_state["pending_research_query"] = prompt.strip()
        st.session_state["next_workspace"] = "Research"
        st.rerun()
