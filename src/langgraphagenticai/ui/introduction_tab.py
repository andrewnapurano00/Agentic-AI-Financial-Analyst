from __future__ import annotations

from html import escape

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
from langgraphagenticai.ui.market_overview_data import load_market_overview
from langgraphagenticai.utils.safety import sanitize_error


def _interactive_price_chart(frame: pd.DataFrame, value_column: str) -> None:
    chart = alt.Chart(frame.reset_index()).mark_line(color="#19d6f5").encode(
        x=alt.X(f"{frame.index.name}:T", title="Date"),
        y=alt.Y(f"{value_column}:Q", scale=alt.Scale(zero=False), title=value_column),
        tooltip=[alt.Tooltip(f"{frame.index.name}:T", title="Date"),
                 alt.Tooltip(f"{value_column}:Q", format=",.2f")],
    ).properties(height=280).interactive()
    st.altair_chart(chart, use_container_width=True)


def _fmt(value: float | None, decimals: int = 2) -> str:
    return "N/A" if value is None else f"{value:,.{decimals}f}"


def _move(snapshot: dict | None) -> tuple[str, str]:
    if not snapshot:
        return "N/A", "flat"
    pct = float(snapshot.get("percent", 0.0))
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


def _spark(percent: float) -> str:
    color = "#20e7ad" if percent >= 0 else "#ff4f78"
    points = "0,22 14,19 27,20 40,13 52,15 66,8 77,10 88,4" if percent >= 0 else "0,5 14,9 27,8 40,14 52,12 66,20 77,18 88,24"
    return f'<svg viewBox="0 0 88 28" class="spark" aria-hidden="true"><polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/></svg>'


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
    quote, fundamentals, performance = snapshot["quote"], snapshot["fundamentals"], snapshot["performance"]
    pct = quote.get("change_pct") or 0.0
    state = "up" if pct >= 0 else "down"
    profile = snapshot["profile"]
    metric_rows = [
        ("Revenue (TTM)", _money(fundamentals.get("revenue_ttm"))),
        ("Revenue growth", _percent(fundamentals.get("revenue_growth"))),
        ("Operating margin", _percent(fundamentals.get("operating_margin"))),
        ("Net margin", _percent(fundamentals.get("net_margin"))),
        ("Free cash flow", _money(fundamentals.get("free_cash_flow_ttm"))),
        ("P / E (TTM)", _fmt(fundamentals.get("pe_ttm"), 1)),
        ("Price / Sales", _fmt(fundamentals.get("price_to_sales"), 1)),
        ("ROIC", _percent(fundamentals.get("roic"))),
    ]
    metrics_html = "".join(f'<div class="company-metric"><span>{escape(label)}</span><b>{escape(value)}</b></div>' for label, value in metric_rows)
    perf_rows = [
        ("1 month", _percent(performance.get("return_1m"))), ("3 months", _percent(performance.get("return_3m"))),
        ("1 year", _percent(performance.get("return_1y"))), ("52W high", _fmt(performance.get("high_52w"))),
        ("52W low", _fmt(performance.get("low_52w"))), ("Volatility", _percent(performance.get("volatility"))),
    ]
    performance_html = "".join(f'<div class="market-table-row"><b>{label}</b><span></span><em>{value}</em></div>' for label, value in perf_rows)
    news_html = "".join(
        f'<li><time>{escape(str(item.get("published_at", ""))[:10])}</time><i></i><a href="{escape(str(item.get("url", "")))}" target="_blank">{escape(str(item.get("title", "Untitled")))}</a><small>{escape(str(item.get("source", "")))}</small></li>'
        for item in snapshot["news"]
    ) or '<li><span>No recent MarketAux articles were returned.</span></li>'
    source_errors = snapshot.get("source_errors") or {}
    error_note = f'<div class="source-warning">Unavailable datasets: {escape(", ".join(source_errors))}</div>' if source_errors else ""

    st.subheader(f"{snapshot['symbol']} historical prices")
    period = st.segmented_control("Company historical range", list(RANGES), default="1Y", key=f"intro_company_range_{snapshot['symbol']}") or "1Y"
    if st.button("Retry company chart", key=f"intro_company_chart_retry_{snapshot['symbol']}"):
        clear_history_cache()
    try:
        chart = load_symbol_history(snapshot["symbol"], fmp_api_key, period, profile.get("currency", ""))
    except Exception as exc:
        chart = {"points": [], "warnings": ["Company chart unavailable: " + sanitize_error(exc)]}
    render_technical_chart(chart, key=f"intro_company_technical_{snapshot['symbol']}", openai_api_key=openai_api_key, model_name=model_name)
    st.markdown(f'''
      <div class="company-head terminal-card"><div><small>COMPANY SNAPSHOT / {escape(snapshot['symbol'])}</small><h2>{escape(snapshot['company'])}</h2><p>{escape(str(profile.get('sector') or 'N/A'))} · {escape(str(profile.get('industry') or 'N/A'))}</p></div>
        <div class="company-price"><span>LAST PRICE</span><strong>${_fmt(quote.get('price'))}</strong><em class="{state}">{pct:+.2f}%</em></div><div class="company-price"><span>MARKET CAP</span><strong>{_money(quote.get('market_cap'))}</strong><em>FMP</em></div></div>
      <div class="company-layout">
        <div class="company-main">
          <div class="company-subgrid"><section class="terminal-card"><h3>FINANCIAL QUALITY &amp; VALUATION</h3><div class="company-metrics">{metrics_html}</div></section><section class="terminal-card live-table"><h3>RECENT PERFORMANCE</h3>{performance_html}</section></div>
          <section class="updates terminal-card company-news"><h3>RECENT NEWS &amp; EVIDENCE <small>MARKETAUX · 10 DAYS</small></h3><ul>{news_html}</ul></section>
        </div>
      </div>{error_note}
    ''', unsafe_allow_html=True)
    st.markdown('<div class="company-ai-title">AI RESEARCH SUMMARY</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(summary)
        st.caption(f"Grounded in {', '.join(snapshot['providers'])} data fetched {snapshot['fetched_at']}. Verify material facts before making investment decisions.")


def _brief(data: dict) -> tuple[str, list[tuple[str, str, str]]]:
    indexes = data["indexes"]
    sp, nasdaq, vix = (indexes.get(key) or {} for key in ("S&P 500", "NASDAQ", "VIX"))
    if not all((sp, nasdaq, vix)):
        return "Market coverage is partial. Available quotes remain visible; missing index data is excluded from interpretation.", []
    sp_pct, ndx_pct, vix_pct = (float(x.get("percent", 0.0)) for x in (sp, nasdaq, vix))
    direction = "higher" if sp_pct >= 0 else "lower"
    leader = "technology-heavy growth" if ndx_pct > sp_pct else "the broader market"
    text = (
        f"U.S. equities are trading {direction}, with {leader} leading. The S&P 500 is "
        f"{sp_pct:+.2f}% and the Nasdaq is {ndx_pct:+.2f}% versus the prior close; volatility "
        f"is {vix_pct:+.2f}%. Sources and daily-close fallbacks are labelled on the quote cards."
    )
    valid_sectors = [item for item in data["sectors"].items() if item[1]]
    strongest = max(valid_sectors, key=lambda x: x[1]["percent"], default=("N/A", {"percent": 0}))
    weakest = min(valid_sectors, key=lambda x: x[1]["percent"], default=("N/A", {"percent": 0}))
    return text, [
        ("green", "Momentum", f"{strongest[0]} leads sectors at {strongest[1]['percent']:+.2f}%"),
        ("red", "Risk", f"{weakest[0]} trails sectors at {weakest[1]['percent']:+.2f}%"),
        ("amber", "Volatility", f"VIX is {_fmt(vix.get('price'), 2)} ({vix_pct:+.2f}%)"),
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
    render_technical_chart(chart, key="intro_market_technical", openai_api_key=openai_api_key, model_name=model_name)


def _dashboard(data: dict, mode: str, fmp_api_key: str = "", openai_api_key="", model_name="gpt-5") -> None:
    indexes = data["indexes"]
    sp = indexes.get("S&P 500") or {}
    as_of = data["as_of"]
    if hasattr(as_of, "to_pydatetime"):
        as_of = as_of.to_pydatetime()
    if getattr(as_of, "tzinfo", None):
        as_of = as_of.astimezone()
    stamp = as_of.strftime("%b %d, %Y  %I:%M %p %Z")
    fetched = data["fetched_at"].astimezone().strftime("%I:%M:%S %p %Z")
    brief, insights = _brief(data)

    ticker_cells = []
    for label, snap in indexes.items():
        pct, state = _move(snap)
        ticker_cells.append(f'<div><small>{escape(label)}</small><strong>{_fmt(snap.get("price") if snap else None)}</strong><em class="{state}">{pct}</em><small>{escape(str((snap or {}).get("provider", "No coverage")))} | As of {escape(str((snap or {}).get("as_of", "unavailable")))}</small></div>')
    mover_rows = []
    for symbol, snap in data["movers"]:
        pct, state = _move(snap)
        mover_rows.append(f'<div class="row"><b>{symbol}</b><span>{_fmt(snap["price"])}</span><em class="{state}">{pct}</em>{_spark(snap["percent"])}</div>')
    index_rows = []
    for label, snap in indexes.items():
        pct, state = _move(snap)
        index_rows.append(f'<div class="market-table-row"><b>{escape(label)}</b><span>{_fmt(snap.get("price") if snap else None)}</span><em class="{state}">{pct}</em><small>{escape(str((snap or {}).get("provider", "No coverage")))} | As of {escape(str((snap or {}).get("as_of", "unavailable")))}</small></div>')
    sector_cells = []
    for label, snap in data["sectors"].items():
        pct = float(snap.get("percent", 0.0)) if snap else 0.0
        display_pct = f"{pct:+.2f}%" if snap else "Unavailable"
        strength = min(1.0, abs(pct) / 2.5)
        color = f"rgba(20,154,99,{0.28 + strength * .58:.2f})" if pct >= 0 else f"rgba(177,50,72,{0.28 + strength * .58:.2f})"
        sector_cells.append(f'<div style="background:{color}">{escape(label)}<br><b>{display_pct}</b></div>')
    asset_rows = []
    for label, snap in data["cross_assets"].items():
        pct, state = _move(snap)
        asset_rows.append(f'<div class="market-table-row"><b>{escape(label)}</b><span>{_fmt(snap.get("price") if snap else None)}</span><em class="{state}">{pct}</em><small>{escape(str((snap or {}).get("provider", "No coverage")))} | As of {escape(str((snap or {}).get("as_of", "unavailable")))}</small></div>')
    insight_html = "".join(f'<div class="insight {kind}"><b>{title}</b><span>{escape(text)}</span></div>' for kind, title, text in insights)
    updates = "".join(
        f'<li><time>{fetched.split()[0]}</time><i class="{"" if snap["percent"] >= 0 else "pink"}"></i>{symbol} moves {snap["percent"]:+.2f}% to {_fmt(snap["price"])}</li>'
        for symbol, snap in data["movers"]
    )

    st.markdown(f'''
      <div class="intro-topline"><div><span class="intro-title">MARKET OVERVIEW</span><b>5-MIN DATA CACHE</b></div><span>MARKET AS OF &nbsp; {escape(stamp)}</span></div>
      <div class="ticker-row intro-five">{''.join(ticker_cells)}</div>''', unsafe_allow_html=True)
    chart_col, brief_col = st.columns([2.1, 1])
    with chart_col:
        st.markdown(f"**S&P 500 (^GSPC)** &nbsp; {_fmt(sp.get('price'))} &nbsp; {_move(sp)[0]}")
        _render_market_chart(fmp_api_key, openai_api_key, model_name)
    with brief_col:
        st.markdown(f'''<aside class="ai-brief terminal-card"><div class="brief-head"><b>MARKET PULSE / RULE-BASED</b><small>{escape(fetched)}</small></div><p>{escape(brief)}</p>{insight_html}</aside>''', unsafe_allow_html=True)
    st.markdown(f'''<div class="intro-grid">
        <section class="mini-grid">
          <div class="terminal-card table-card"><h3>TOP MOVERS <small>WATCHLIST</small></h3>{''.join(mover_rows) or '<p>No market data available.</p>'}</div>
          <div class="terminal-card live-table"><h3>KEY INDICES</h3>{''.join(index_rows)}</div>
          <div class="terminal-card live-table"><h3>CROSS ASSETS</h3>{''.join(asset_rows[:4])}</div>
        </section>
        <section class="heat terminal-card intro-sector"><h3>SECTOR PERFORMANCE</h3><div class="heatmap">{''.join(sector_cells)}</div></section>
        <section class="world terminal-card live-table intro-assets"><h3>GLOBAL &amp; CROSS-ASSET MARKETS</h3>{''.join(asset_rows)}</section>
        <aside class="updates terminal-card"><h3>LATEST MARKET MOVES <small>LIVE SNAPSHOT</small></h3><ul>{updates}</ul><div class="source-line">Derived from current quote changes; not editorial headlines.</div></aside>
      </div>''', unsafe_allow_html=True)


def render_introduction_tab(
    fmp_api_key: str = "", openai_api_key: str = "", model_name: str = "gpt-5",
    marketaux_api_key: str = "",
) -> None:
    st.markdown('<div class="intro-controls-anchor"></div>', unsafe_allow_html=True)
    search_col, analyze_col, back_col = st.columns([5.2, 1.4, 1.4], vertical_alignment="bottom")
    with search_col:
        company_query = st.text_input("Company search", value=st.session_state.get("intro_company_query", ""), placeholder="Search a company ticker — AAPL, MSFT, NVDA…", label_visibility="collapsed", key="intro_company_search")
    with analyze_col:
        analyze = st.button("ANALYZE COMPANY", type="primary", use_container_width=True, key="intro_company_analyze")
    with back_col:
        back = st.button("MARKET OVERVIEW", use_container_width=True, key="intro_company_back")
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
            with st.spinner(f"Building current research snapshot for {selected_symbol}…"):
                snapshot = load_company_snapshot(selected_symbol, fmp_api_key, marketaux_api_key)
                summary_key = f"intro_summary:{selected_symbol}:{model_name}"
                if analyze:
                    try:
                        st.session_state[summary_key] = generate_company_summary(snapshot_json(snapshot), openai_api_key, model_name)
                    except Exception as exc:
                        st.warning(f"AI summary unavailable; company data is preserved: {sanitize_error(exc)}")
                summary = st.session_state.get(summary_key, "Select Analyze Company to generate an AI summary from the current evidence.")
            _render_company_snapshot(snapshot, summary, fmp_api_key, openai_api_key, model_name)
        except Exception as exc:
            st.error(f"Company analysis could not be completed: {sanitize_error(exc)}")
            st.info("Check the ticker and provider configuration, then try again. No stale company data is shown.")
        return

    mode_col, refresh_col, status_col = st.columns([2.1, 1.1, 4.8], vertical_alignment="center")
    with mode_col:
        mode = st.segmented_control("Dashboard view", ["Market Pulse", "AI Insights"], default="AI Insights", label_visibility="collapsed", key="intro_mode")
    with refresh_col:
        if st.button("REFRESH DATA", use_container_width=True, key="intro_refresh"):
            load_market_overview.clear()
            load_market_chart.clear()
            clear_history_cache()
            st.rerun()
    with status_col:
        st.caption("Quotes may be delayed by the provider. Cached for 5 minutes; use Refresh Data for a new request.")
    try:
        with st.spinner("Loading current market data…"):
            data = load_market_overview(fmp_api_key)
        if not any(data["indexes"].values()):
            raise RuntimeError("The market provider returned no index quotes.")
        for warning in data.get("warnings", []):
            st.warning(warning)
        _dashboard(data, mode or "AI Insights", fmp_api_key, openai_api_key, model_name)
    except Exception as exc:
        st.error(f"Live market data is temporarily unavailable: {sanitize_error(exc)}")
        st.info("No stale fallback values are displayed. Use Refresh Data to retry the provider.")

    st.markdown('<div class="ask-label">ASK THE AI ANALYST</div>', unsafe_allow_html=True)
    prompt_col, send_col = st.columns([8, 1])
    with prompt_col:
        prompt = st.text_input("Ask about the markets", placeholder="Ask about today’s markets…", label_visibility="collapsed", key="intro_question")
    with send_col:
        submitted = st.button("ASK AI ↗", type="primary", use_container_width=True, key="intro_ask")
    if submitted and prompt.strip():
        st.session_state["pending_research_query"] = prompt.strip()
        st.session_state["next_workspace"] = "Research"
        st.rerun()
