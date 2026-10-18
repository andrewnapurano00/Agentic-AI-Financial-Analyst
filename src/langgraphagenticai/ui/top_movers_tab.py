from __future__ import annotations

from html import escape
from math import isfinite

import pandas as pd
import streamlit as st

from langgraphagenticai.ui.top_movers_data import load_top_movers
from langgraphagenticai.providers.discovery_numbers import finite_number


def ranked_display(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    """D12: selected period, finite prices/volumes and no duplicate 1D column."""
    columns = {"symbol": "Ticker", "companyName": "Company", "sector": "Sector", "price": "Last Price", "1D": "1D change (%)"}
    if period != "1D":
        columns[period] = f"{period} change (%)"
    columns.update(marketCap="Market Cap", volume="Volume", avgVolume="Avg Volume")
    result = pd.DataFrame(index=frame.index)
    result["Rank"] = range(1, len(frame) + 1)
    for raw, label in columns.items():
        values = frame[raw] if raw in frame else pd.Series(None, index=frame.index, dtype=object)
        result[label] = values if raw in {"symbol", "companyName", "sector"} else pd.to_numeric(values.map(finite_number), errors="coerce")
    return result.reset_index(drop=True)


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


def _rows(frame: pd.DataFrame, period="5D") -> str:
    html = []
    for rank, row in frame.iterrows():
        weekly = finite_number(row.get(period))
        daily = finite_number(row.get("1D"))
        state = "up" if weekly is not None and weekly > 0 else "down" if weekly is not None and weekly < 0 else "flat"
        html.append(f'''<div class="mover-row">
          <span class="mover-rank">{rank + 1:02d}</span><div><b>{escape(str(row.get('symbol', '')))}</b><small>{escape(str(row.get('companyName')) if pd.notna(row.get('companyName')) else str(row.get('symbol', '')))}</small></div>
          <span>{escape(str(row.get('sector') or 'Unavailable'))}</span><span>{_numeric(row.get('price'))}</span>
          <em class="{'up' if daily is not None and daily > 0 else 'down' if daily is not None and daily < 0 else 'flat'}">{_numeric(daily, '%', signed=True)}</em><em class="{state}">{_numeric(weekly, '%', signed=True)}</em>
          <span>{_money(row.get('marketCap'))}</span><span>{_numeric(row.get('liquidityRatio'), 'x', decimals=1)}</span></div>''')
    return "".join(html)


def render_top_movers_tab(*, fmp_api_key: str, serper_api_key: str, openai_api_key: str = "", model_name: str = "gpt-5", marketaux_api_key: str = "") -> None:
    from langgraphagenticai.ui.opening_presentation import opening_styles, heading, cards, number, terminal_chart, quote_header, opening_price_chart
    from langgraphagenticai.providers.discovery import rank_discovery, sector_summary, PERIODS, load_selected_news, load_selected_quote
    from langgraphagenticai.providers.symbol_history import load_symbol_history, clear_history_cache
    from langgraphagenticai.state.discovery import DiscoveryState, apply_discovery, queue_discovery_research
    from langgraphagenticai.ui.workspace_presentation import saved_time, source_link
    from langgraphagenticai.ui.app_shell import render_evidence_row
    from langgraphagenticai.utils.safety import sanitize_error
    import altair as alt

    apply_discovery(st.session_state)
    restored = st.session_state.get("discovery_state")
    if isinstance(restored, DiscoveryState):
        st.session_state.setdefault("movers_sector_filter", restored.sector)
        st.session_state.setdefault("movers_period", restored.period)
        st.session_state.setdefault("movers_direction", restored.direction)
    opening_styles()
    st.markdown(
        '<style>body:has(.opening-workspace) .terminal-quote strong{display:inline-block;margin-right:8px}'
        'body:has(.opening-workspace) .terminal-quote small{display:inline-block;margin:0 8px 0 0}'
        'body:has(.opening-workspace) .terminal-quote span.positive,'
        'body:has(.opening-workspace) .terminal-quote span.negative{display:inline-block}</style>',
        unsafe_allow_html=True,
    )
    heading("Top Movers", "Discover the move. Understand the evidence.")
    refresh_col, info_col = st.columns([1, 4], vertical_alignment="center")
    with refresh_col:
        if st.button("Refresh movers", key="movers_refresh", use_container_width=True):
            load_top_movers.clear()
            load_selected_news.clear()
            load_selected_quote.clear()
            clear_history_cache()
            st.rerun()
    with info_col:
        st.caption("FMP screened U.S. equities | market cap > 2B and volume > 500K provider units | up to 500 requested stocks. Ranking cache: up to 15 minutes; Refresh makes a new request.")
    try:
        with st.spinner("Loading screened price-change evidence..."):
            data = load_top_movers(fmp_api_key, "")
    except Exception as exc:
        st.error("Movers evidence is unavailable: " + sanitize_error(exc))
        st.info("Check FMP configuration and refresh. No illustrative rankings are displayed.")
        return
    universe = data["universe"]
    render_evidence_row([
        ("Ranking source", "FMP capped U.S. equity screen"),
        ("Retrieved", saved_time(data.get("fetched_at"))),
        ("Requested symbols", data.get("requested_universe_size", len(universe))),
    ])
    sectors = sorted(universe["sector"].dropna().astype(str).unique())
    options = ["All sectors", *sectors]
    if st.session_state.get("movers_sector_filter", "All sectors") not in options:
        # Keep incoming sector explicit even when this capped universe has no matches.
        options.append(st.session_state["movers_sector_filter"])
    direction_col, sector_col, period_col = st.columns([1.4, 1.6, 1])
    with direction_col:
        direction = st.segmented_control("Direction", ["Leaders", "Laggards"], default=st.session_state.get("movers_direction", "Leaders"), key="movers_direction") or "Leaders"
    with sector_col:
        sector = st.selectbox("Sector", options, index=options.index(st.session_state.get("movers_sector_filter", "All sectors")), key="movers_sector_filter")
    with period_col:
        period = st.selectbox("Performance period", PERIODS, index=PERIODS.index(st.session_state.get("movers_period", "5D")), key="movers_period")
    prior_discovery = st.session_state.get("discovery_state")
    retained_ticker = prior_discovery.selected_ticker if isinstance(prior_discovery, DiscoveryState) else ""
    st.session_state["discovery_state"] = DiscoveryState(sector, period, direction, retained_ticker, "Top Movers")
    from langgraphagenticai.analysis.discovery import expanded_ranking, sector_participation, RANKING_SIZES
    size = st.selectbox("Ranking size", RANKING_SIZES, index=RANKING_SIZES.index(st.session_state.get("movers_saved_ranking_size", RANKING_SIZES[0])), key="movers_ranking_size",
                        help="Top 10% rounds up from usable stocks after the sector filter. Top 50 shows up to 50 available stocks.")
    st.session_state.movers_saved_ranking_size = size
    frame, stats = expanded_ranking(universe, period, sector, direction, size)
    st.caption(f"{size}: showing {len(frame)} of {stats['usable']} usable filtered stocks. Leaders/laggards rank relative returns; a ranking can include both gains and losses.")
    requested = data.get("requested_universe_size", len(universe))
    _, full_stats = rank_discovery(universe, period, limit=len(universe))
    cards([("Usable filtered universe", stats["usable"], sector),
           (f"Advancing ({period})", number(stats["advancing"], "%", decimals=1), "Positive returns / finite filtered observations; unchanged included in denominator"),
           (f"Median {period} price change", number(stats["median"], "%", True), "Filtered screened stocks; provider price-change basis")])
    st.caption(f"FMP ranking evidence retrieved {saved_time(data.get('fetched_at'))} | {full_stats['usable']} / {requested} requested symbols usable for {period} ({number(full_stats['usable'] / requested * 100 if requested else None, '%', decimals=1)}). Performance observation dates and adjustment basis unavailable; no total-return or session-completeness claim.")
    for warning in data.get("provider_warnings", []):
        st.warning(warning)
    from langgraphagenticai.ui.movers_heatmap import concentration_rows, concentration_chart
    st.subheader("Sector concentration heatmap")
    st.caption(f"{direction} · {period} · {sector}. Equal-size tiles show stock count and share of the displayed top {len(frame)} ranking; color and signed value = equal-weight mean price change. Capped screened equities, not sector ETF returns. Dates and adjustment basis unavailable.")
    heatmap_rows = concentration_rows(frame, period)
    if heatmap_rows:
        st.altair_chart(concentration_chart(heatmap_rows), use_container_width=True, theme=None, key="movers_concentration")
    else:
        st.info("No usable movers for this period and filter. Choose another filter to see sector concentration.")
    from langgraphagenticai.ui.movers_heatmap import participation_chart
    st.subheader("Top movers as a share of each sector")
    st.caption(f"{period} · {direction} · {size}. In top movers versus other stocks with finite {period} observations in each screened sector. Missing-period observations are excluded. This is the available capped screen, not all sector constituents. Hover for counts and percentages.")
    participation = sector_participation(universe, frame, period, sector)
    if not participation.empty:
        st.altair_chart(participation_chart(participation), use_container_width=True, theme=None, key="movers_participation")
    else:
        st.info("No usable sector stocks for this period and filter.")
    left, right = st.columns([1.86, 1], gap="medium")
    with left, st.container(border=True):
        st.subheader(f"{sector if sector != 'All sectors' else 'Screened equity'} {direction.lower()}")
        if frame.empty:
            st.info(f"No finite {period} performance observations in this sector. Choose another period or sector; other saved work is preserved.")
        else:
            display = ranked_display(frame, period)
            return_columns = [col for col in display if col.endswith("change (%)")]
            styled = display.style.format({**{col: "{:+.2f}" for col in return_columns}, "Last Price": "{:,.2f}", "Market Cap": "{:,.0f}", "Volume": "{:,.0f}", "Avg Volume": "{:,.0f}"}, na_rep="Unavailable")
            styled = styled.map(lambda value: "color:#37B68C" if pd.notna(value) and value > 0 else "color:#E2747E" if pd.notna(value) and value < 0 else "", subset=return_columns)
            retained = st.session_state.get("discovery_state")
            selected = st.session_state.get("movers_focus", retained.selected_ticker if isinstance(retained, DiscoveryState) else "")
            options_for_style = frame["symbol"].tolist()
            if selected not in options_for_style:
                selected = options_for_style[0]
            table_key = f"movers_table_{sector}_{period}_{direction}_{size}"
            pending_rows = st.session_state.get(table_key, {}).get("selection", {}).get("rows", [])
            pending_marker = (sector, period, direction, size, tuple(pending_rows))
            if pending_rows and st.session_state.get("movers_last_selection") != pending_marker and 0 <= pending_rows[0] < len(frame):
                selected = options_for_style[pending_rows[0]]
            styled = styled.apply(lambda row: ["background-color:#172334;font-weight:bold" if row["Ticker"] == selected else "" for _ in row], axis=1)
            event = st.dataframe(styled, hide_index=True, use_container_width=True, height=430,
                                 on_select="rerun", selection_mode="single-row", key=table_key,
                                 column_config={"Rank": st.column_config.NumberColumn(width="small"), "Ticker": st.column_config.TextColumn(width="small"), "Company": st.column_config.TextColumn(width="medium"),
                                                **{col: st.column_config.NumberColumn(format="%+.2f", width="small") for col in return_columns}})
            st.caption("Signed percentage-point price changes; last price / cap currency unavailable in the screener. Volume units and average window are provider-defined. Scroll table horizontally for size and activity columns.")
            focus_options = frame["symbol"].tolist()
            saved = st.session_state.get("discovery_state")
            previous = st.session_state.get("movers_focus", saved.selected_ticker if isinstance(saved, DiscoveryState) else "")
            focus_default = previous if previous in focus_options else focus_options[0]
            if "movers_focus" in st.session_state and previous not in focus_options:
                st.session_state["movers_focus"] = focus_default
            row_applied = False
            selected_rows = event.selection.rows
            # A table event is applied once, so the accessible selector can override it.
            marker = (sector, period, direction, size, tuple(selected_rows))
            if selected_rows and st.session_state.get("movers_last_selection") != marker:
                index = selected_rows[0]
                if 0 <= index < len(frame):
                    st.session_state["movers_focus"] = focus_options[index]
                    focus_default = focus_options[index]
                    row_applied = True
                st.session_state["movers_last_selection"] = marker
            # The frontend remounts this widget after an empty result. Its protobuf
            # default must agree with the retained identity, not the first ranked row.
            # Existing row events send an explicit widget value; a remounted widget
            # instead receives its retained identity solely through its default.
            focus_index = 0 if row_applied else focus_options.index(focus_default)
            focus = st.selectbox("Selected company (keyboard alternative to table rows)", focus_options,
                                 index=focus_index, key="movers_focus")
            discovery = DiscoveryState(sector, period, direction, focus, "Top Movers")
            st.session_state["discovery_state"] = discovery
    if not frame.empty:
        with right, st.container(border=True):
            row = frame[frame["symbol"] == focus].iloc[0]
            st.caption("Selected company")
            quote = load_selected_quote(focus, fmp_api_key)
            quote_header(focus, row.get('companyName') or focus, row.get("sector"), quote, analyst=False)
            if quote.get("error"):
                st.info("Selected quote unavailable: " + sanitize_error(quote["error"]))
            st.caption(f"FMP quote as of {saved_time(quote.get('as_of'))} | retrieved {saved_time(quote.get('retrieved_at'))}. Currency is unavailable unless supplied by this quote.")
            st.metric(f"Provider {period} price change", number(row.get(period), "%", True))
            st.caption("Ranking dates unavailable. Chart observations below have separate dated evidence and must not be subtracted from this undated ranking.")
            history_period = "YTD" if period == "ytd" else period
            try:
                history = load_symbol_history(focus, fmp_api_key, history_period)
                points = history.get("points", [])
                if points:
                    prices = pd.DataFrame(points, columns=["Date", "Close"])
                    from langgraphagenticai.ui.technical_chart import price_chart_spec
                    chart = opening_price_chart(prices, history_period, history.get("unit", "Currency unknown"), height=190)
                    st.altair_chart(chart, use_container_width=True, theme=None)
                else:
                    st.info("Selected price history unavailable; rankings remain usable.")
                st.caption(f"Chart {history_period} | {history.get('provider', 'Unavailable')} | {history.get('price_basis', 'Basis unavailable')} | {history.get('unit', 'Currency unknown')} | {len(points)} observed bars")
                st.caption(f"As of {history.get('as_of', 'Unavailable')} | retrieved {saved_time(history.get('retrieved_at'))} | timezone {history.get('timezone', 'Unknown')}")
                for warning in history.get("warnings", []):
                    st.warning(warning)
            except Exception as exc:
                st.warning("Selected history unavailable; rankings preserved: " + sanitize_error(exc))
            st.caption("Benchmark / sector excess return: unavailable. Compatible dated return bases have not been established. Completed-session volume ratio: unavailable.")
            st.markdown("**Related news & potential catalysts**")
            news = load_selected_news(focus, serper_api_key)
            st.caption(f"Serper | requested lookback 7 days | retrieved {saved_time(news.get('retrieved_at'))}. Publication text is supplied by the source; related coverage does not establish a cause.")
            if news.get("error"):
                st.info("Selected news unavailable: " + sanitize_error(news["error"]))
            safe_count = 0
            for item in news.get("results", [])[:3]:
                url = source_link(item.get("url"))
                if url:
                    safe_count += 1
                    st.markdown(f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(str(item.get("title") or "Untitled"))}</a>', unsafe_allow_html=True)
                    st.caption(f"{item.get('publisher') or 'Publisher unavailable'} | publication: {item.get('published') or 'Unavailable'}")
            if not safe_count and not news.get("error"):
                st.info("No safe related news links returned for this company.")
            if st.button("Research this move", key="movers_research", type="primary", use_container_width=True):
                queue_discovery_research(st.session_state, discovery)
                st.rerun()
            if st.button("Open daily chart", key="movers_open_snapshot", use_container_width=True):
                from langgraphagenticai.ui.workspace_handoff import queue_handoff
                from langgraphagenticai.state.research_context import ResearchContext
                queue_handoff(st.session_state, ResearchContext((focus,), "Introduction", "analyze", "Top Movers"))
                st.rerun()
            with st.expander("More research workspaces"):
                from langgraphagenticai.ui.workspace_handoff import render_company_handoffs
                render_company_handoffs(focus, "Top Movers", key="movers_handoff")
        with left, st.container(border=True):
            from langgraphagenticai.ui.social_sentiment import render_social_sentiment
            render_social_sentiment(focus, fmp_api_key)
        with left, st.container(border=True):
            from langgraphagenticai.ui.analyst_consensus import render_analyst_consensus
            render_analyst_consensus(focus_options, focus, fmp_api_key)
        with left, st.container(border=True):
            from langgraphagenticai.ui.price_targets import render_price_targets
            render_price_targets(st.session_state.get("movers_consensus_stock", focus), fmp_api_key)
        with left, st.container(border=True):
            from langgraphagenticai.ui.ticker_news_summary import render_ticker_news_summary
            news_symbol=st.session_state.get("movers_consensus_stock",focus)
            names=frame.loc[frame["symbol"]==news_symbol,"companyName"] if "companyName" in frame else pd.Series(dtype=str)
            company=str(names.iloc[0]) if not names.empty and pd.notna(names.iloc[0]) else news_symbol
            render_ticker_news_summary(news_symbol,company,fmp_api_key=fmp_api_key,serper_api_key=serper_api_key,
                                      marketaux_api_key=marketaux_api_key,openai_api_key=openai_api_key,model_name=model_name)
    st.subheader("Screened sector context")
    summary = sector_summary(universe, period)
    if sector != "All sectors":
        summary = summary[summary["sector"] == sector]
    if summary.empty:
        st.info("No usable sector aggregates for this period and filter.")
    else:
        st.dataframe(summary.rename(columns={"sector": "Sector", "mean_return": f"Equal-weight mean {period} (%)", "median_return": f"Median {period} (%)", "stocks": "Usable stocks"}), hide_index=True, use_container_width=True)
    with st.expander("Coverage & methodology"):
        st.write("Screened U.S. equities; provider-requested cap > 2B, volume > 500K, active trading, no ETFs/funds, maximum 500 records. This capped screen is not the whole market. Counts and statistics include only finite observations for the selected period and sector. Leaders/laggards rank relative performance; zero is valid and missing is excluded.")
        st.write("FMP legacy stock-price-change supplies percent price changes (1D, 5D, 1M, ytd) without observation dates or confirmed adjustment basis. No benchmark or ETF excess-return subtraction is performed. Sector means weight usable screened stocks equally; they are not sector ETF returns. Current volume / provider average is not a verified completed-session measure and is withheld.")
        st.write("Ranking, history and selected news caches are independent. Filters reuse ranking evidence; only the selected company requests history/news. No models run when selecting, filtering, navigating or refreshing. Research opens an editable draft requiring explicit submission.")
