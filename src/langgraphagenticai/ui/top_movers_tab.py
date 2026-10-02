from __future__ import annotations

from html import escape
from math import isfinite

import pandas as pd
import streamlit as st

from langgraphagenticai.ui.top_movers_data import load_top_movers


def _money(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not isfinite(number):
        return "Unavailable"
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(number) >= divisor:
            return f"${number / divisor:,.1f}{suffix}"
    return f"${number:,.2f}"


def _numeric(value, suffix="", decimals=2, signed=False):
    try:
        number = float(value)
        if isfinite(number):
            return f"{number:+,.{decimals}f}{suffix}" if signed else f"{number:,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        pass
    return "Unavailable"


def _rows(frame: pd.DataFrame) -> str:
    html = []
    for rank, row in frame.iterrows():
        weekly = float(row.get("5D", 0.0))
        daily = float(row.get("1D", 0.0))
        state = "up" if weekly >= 0 else "down"
        html.append(f'''<div class="mover-row">
          <span class="mover-rank">{rank + 1:02d}</span><div><b>{escape(str(row.get('symbol', '')))}</b><small>{escape(str(row.get('companyName')) if pd.notna(row.get('companyName')) else str(row.get('symbol', '')))}</small></div>
          <span>{escape(str(row.get('sector') or 'N/A'))}</span><span>${float(row.get('price', 0)):,.2f}</span>
          <em class="{'up' if daily >= 0 else 'down'}">{_numeric(daily, '%', signed=True)}</em><em class="{state}">{weekly:+.2f}%</em>
          <span>{_money(row.get('marketCap'))}</span><span>{_numeric(row.get('liquidityRatio'), 'x', decimals=1)}</span></div>''')
    return "".join(html)


def _sector_heatmap(frame: pd.DataFrame) -> str:
    cells = []
    for _, row in frame.iterrows():
        value = float(row["weekly_return"])
        strength = min(abs(value) / 4.0, 1.0)
        color = f"rgba(20,154,99,{.30 + strength * .60:.2f})" if value >= 0 else f"rgba(177,50,72,{.30 + strength * .60:.2f})"
        cells.append(f'<div style="background:{color}"><b>{escape(str(row["sector"] or "Unknown"))}</b><strong>{value:+.2f}%</strong><small>{int(row["advancers"])} up / {int(row["decliners"])} down</small></div>')
    return "".join(cells)


def _news_panel(news: dict[str, list[dict]], symbols: list[str]) -> str:
    groups = []
    for symbol in symbols:
        articles = news.get(symbol, [])
        links = "".join(
            f'<a href="{escape(str(item.get("url", "")))}" target="_blank" rel="noopener noreferrer"><b>{escape(str(item.get("title", "Untitled")))}</b><span>{escape(str(item.get("publisher") or "Source not supplied"))} &middot; {escape(str(item.get("published") or "Date not supplied"))}</span></a>'
            for item in articles
        ) or '<span class="mover-no-news">No current Serper headlines returned.</span>'
        groups.append(f'<div class="mover-news-group"><h4>{escape(symbol)}</h4>{links}</div>')
    return "".join(groups)


def render_top_movers_tab(*, fmp_api_key: str, serper_api_key: str) -> None:
    control_a, control_b, control_c = st.columns([2.2, 2.2, 1.2], vertical_alignment="bottom")
    with control_a:
        direction = st.segmented_control("Direction", ["Leaders", "Laggards"], default="Leaders", label_visibility="collapsed", key="movers_direction")
    with control_b:
        st.caption("Ranks refresh every 15 minutes from live providers.")
    with control_c:
        if st.button("REFRESH", use_container_width=True, key="movers_refresh"):
            load_top_movers.clear()
            st.rerun()

    try:
        with st.spinner("Ranking the liquid U.S. equity universe and collecting current news..."):
            data = load_top_movers(fmp_api_key, serper_api_key)
    except Exception as exc:
        from langgraphagenticai.utils.safety import sanitize_error
        st.error(f"Top movers data is temporarily unavailable: {sanitize_error(exc)}")
        st.info("No demo rankings are shown. Check FMP connectivity and retry.")
        return

    all_sectors = sorted(str(value) for value in data["universe"]["sector"].dropna().unique())
    for warning in data.get("provider_warnings", []):
        st.warning(warning)
    # Replace the initial lightweight selector after data arrives without another provider call.
    selected_sector = st.selectbox("Filter ranked table by sector", ["All sectors", *all_sectors], key="movers_sector_filter")
    frame = data["gainers"] if direction == "Leaders" else data["losers"]
    if selected_sector != "All sectors":
        pool = data["universe"]
        pool = pool[pool["sector"].astype(str) == selected_sector]
        frame = pool.nlargest(12, "5D") if direction == "Leaders" else pool.nsmallest(12, "5D")
        frame = frame.reset_index(drop=True)

    breadth = float((data["universe"]["5D"] > 0).mean() * 100)
    top = data["gainers"].iloc[0]
    bottom = data["losers"].iloc[0]
    fetched = data["fetched_at"].astimezone().strftime("%b %d, %Y %I:%M %p %Z")
    st.markdown(f'''
      <div class="movers-head terminal-card"><div><small>WEEKLY MARKET LEADERSHIP</small><h2>Top Movers</h2><p>Liquid U.S. equities &middot; $2B+ market cap &middot; 500K+ daily volume</p></div>
      <div><span>UNIVERSE</span><b>{data['universe_size']}</b></div><div><span>ADVANCING</span><b>{breadth:.1f}%</b></div><div><span>TOP GAINER</span><b class="up">{escape(str(top['symbol']))} {float(top['5D']):+.1f}%</b></div><div><span>TOP LAGGARD</span><b class="down">{escape(str(bottom['symbol']))} {float(bottom['5D']):+.1f}%</b></div></div>
      <div class="movers-grid"><section class="terminal-card movers-table"><h3>{'TOP WEEKLY GAINERS' if direction == 'Leaders' else 'TOP WEEKLY LAGGARDS'} <small>5 TRADING DAYS</small></h3>
      <div class="mover-row mover-header"><span>#</span><span>COMPANY</span><span>SECTOR</span><span>PRICE</span><span>1D</span><span>5D</span><span>MARKET CAP</span><span>VOL / AVG</span></div>{_rows(frame)}</section>
      <section class="terminal-card movers-sector"><h3>SECTOR LEADERSHIP <small>UNIVERSE AVERAGE</small></h3><div class="mover-sector-grid">{_sector_heatmap(data['sectors'])}</div></section>
      <aside class="terminal-card movers-news"><h3>NEWS DRIVING THE MOVERS <small>SERPER &middot; 7 DAYS</small></h3>{_news_panel(data['news'], data['gainers'].head(4)['symbol'].tolist() + data['losers'].head(4)['symbol'].tolist())}</aside></div>
      <div class="source-line">Sources: {' &middot; '.join(data['providers'])} &middot; Refreshed {escape(fetched)} &middot; Rankings use FMP 5D price performance and exclude ETFs/funds. Unavailable means provider coverage is missing; VOL / AVG compares current volume with provider average volume.</div>
    ''', unsafe_allow_html=True)

    focus_options = frame["symbol"].astype(str).tolist()
    if focus_options:
        focus_col, open_col, spacer = st.columns([2, 1.25, 4.75], vertical_alignment="bottom")
        with focus_col:
            focus = st.selectbox("Open a company snapshot", focus_options, key="movers_focus")
        with open_col:
            if st.button("OPEN SNAPSHOT", type="primary", use_container_width=True, key="movers_open_snapshot"):
                st.session_state["intro_company_symbol"] = focus
                st.session_state["intro_company_query"] = focus
                st.session_state["next_workspace"] = "Introduction"
                st.rerun()
