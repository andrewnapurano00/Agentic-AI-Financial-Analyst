"""Interactive sector mosaic and explicitly bounded screened industry detail."""
from hashlib import sha256

import altair as alt
import pandas as pd
import streamlit as st

from langgraphagenticai.analysis.sector_heatmap import SECTORS, industry_groups, canonical_sector
from langgraphagenticai.providers.discovery import collect_discovery, finite_number
from langgraphagenticai.providers.sector_heatmap import load_sector_performance, clear_sector_price_cache
from langgraphagenticai.ui.opening_presentation import number, terminal_chart
from langgraphagenticai.utils.safety import sanitize_error


def mosaic_rows(packet, selected):
    rows = []
    for index, (sector, symbol) in enumerate(SECTORS.items()):
        record = packet.get("sectors", {}).get(sector, {})
        day = finite_number(record.get("day"))
        # Direct RGB colors avoid renderer/theme interpolation changing gain/loss hues.
        intensity = min(abs(day or 0) / 3, 1)
        low, high = ((38, 50, 65), (120, 47, 59) if day is not None and day < 0 else (18, 107, 81))
        fill = "#" + "".join(f"{round(a+(b-a)*intensity):02x}" for a, b in zip(low, high))
        rows.append({"sector": sector, "ETF": symbol, "day": day,
                     "display": number(day, "%", True) if day is not None else "Unavailable",
                     "five_day": "5D " + number(record.get("week"), "%", True),
                     "as_of": record.get("as_of") or "Unavailable",
                     "status": "Stale" if record.get("stale", True) else record.get("price_source", "Unavailable"),
                     "size": "Equal area",
                     "basis": packet.get("basis", "Unavailable"),
                     "retrieved": packet.get("retrieved_at") or "Unavailable",
                     "start": record.get("starts", {}).get("day", "Unavailable"),
                     "price": record.get("price"), "previous_adj_close": record.get("previous_adj_close"),
                     "price_source": record.get("price_source", "Unavailable"),
                     "color": max(-3, min(3, day)) if day is not None else None,
                     "fill": fill,
                     "selected": sector == selected,
                     "x": index % 3, "x2": index % 3 + .98,
                     "y": index // 3, "y2": index // 3 + .97,
                     "cx": index % 3 + .49, "cy": index // 3 + .485})
    return rows


def mosaic_chart(packet, selected):
    base = alt.Chart(pd.DataFrame(mosaic_rows(packet, selected)))
    pick = alt.selection_point(name="sector_pick", fields=["sector"], on="click", empty=False)
    position = dict(x=alt.X("x:Q", axis=None, scale=alt.Scale(domain=[0, 3])),
                    x2="x2:Q", y=alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[4, 0])), y2="y2:Q")
    tiles = base.mark_rect(cornerRadius=3, cursor="pointer").encode(
        **position,
        color=alt.Color("fill:N", scale=None, legend=None),
        stroke=alt.condition("datum.selected", alt.value("#D6B36A"), alt.value("#172334")),
        strokeWidth=alt.condition("datum.selected", alt.value(2.5), alt.value(1)),
        tooltip=["sector:N", "ETF:N", "display:N", "price:Q", "previous_adj_close:Q", "price_source:N", "start:N", "as_of:N", "status:N", "size:N", "basis:N", "retrieved:N"],
    ).add_params(pick)
    text = base.encode(x=alt.X("cx:Q", axis=None), y=alt.Y("cy:Q", axis=None))
    return terminal_chart((tiles + text.mark_text(dy=-30, fontSize=11, color="#c1cedd").encode(text="ETF:N")
                           + text.mark_text(dy=-10, fontSize=alt.ExprRef(expr="width < 500 ? 10 : 12"), color="#ffffff", limit=alt.ExprRef(expr="width / 3 - 14")).encode(text="sector:N")
                           + text.mark_text(dy=17, fontSize=alt.ExprRef(expr="width < 500 ? 15 : 23"), fontWeight="bold", color="#ffffff").encode(text="display:N")
                           + text.mark_text(dy=40, fontSize=11, color="#c1cedd").encode(text="five_day:N"))
                          .properties(height=460))


def render_sector_heatmap(fmp_api_key=""):
    st.subheader("Sector Heatmap")
    st.caption("Size: equal-area fallback; constituent sector market caps unavailable. Color: latest price versus previous trading day's adjClose, symmetric ±3% clipping; charcoal = zero/unavailable. Gold outline = selected.")
    if st.button("Refresh sector evidence", key="heatmap_refresh"):
        clear_sector_price_cache()
        st.session_state.pop("heatmap_screen", None)
        collect_discovery.clear()
    packet = load_sector_performance(fmp_api_key)
    for warning in packet.get("warnings", []):
        st.warning(warning)
    st.caption(f"{packet.get('provider', 'Unavailable')} | retrieved {packet.get('retrieved_at') or 'Unavailable'} | cache up to 5 minutes. Day = (latest FMP price / previous trading day's adjClose - 1) × 100. Hover for prices and dates; session completion is unverified.")
    st.session_state.setdefault("heatmap_sector", "Technology")
    event = st.altair_chart(mosaic_chart(packet, st.session_state.heatmap_sector),
                            use_container_width=True, theme=None, key=f"heatmap_mosaic_{st.session_state.get('heatmap_chart_epoch', 0)}",
                            on_select="rerun", selection_mode="sector_pick")
    picks = event.selection.get("sector_pick", [])
    clicked = picks[0].get("sector") if picks else None
    if clicked in SECTORS and clicked != st.session_state.get("heatmap_last_pick"):
        st.session_state.heatmap_last_pick = clicked
        st.session_state.heatmap_sector = clicked
        st.rerun()
    def keyboard_selection():
        # Reset Vega's old selection so clicking that tile again is a new event.
        st.session_state.heatmap_chart_epoch = st.session_state.get("heatmap_chart_epoch", 0) + 1
        st.session_state.pop("heatmap_last_pick", None)
    selected = st.selectbox("Selected sector", list(SECTORS), key="heatmap_sector", on_change=keyboard_selection)
    left, right = st.columns([3, 2], gap="medium")
    with right, st.container(border=True):
        st.subheader("Sector Performance")
        st.caption("Day · Week · YTD | FMP price versus historical adjusted-close baselines")
        sort = st.selectbox("Sort performance", ["Sector", "Day", "Week", "YTD"], key="heatmap_sort")
        rows = []
        for sector, symbol in SECTORS.items():
            record = packet.get("sectors", {}).get(sector, {})
            rows.append({"Sector": f"{sector} · {symbol}", "Day": record.get("day"), "Week": record.get("week"),
                         "YTD": record.get("ytd")})
        frame = pd.DataFrame(rows).sort_values(sort, ascending=sort == "Sector", na_position="last")
        styled = frame.style.format({col: lambda value: number(value, "%", True) if finite_number(value) is not None else "Unavailable" for col in ("Day", "Week", "YTD")}, na_rep="Unavailable")
        styled = styled.map(lambda value: "color: #37B68C" if finite_number(value) is not None and value > 0 else "color: #E2747E" if finite_number(value) is not None and value < 0 else "", subset=["Day", "Week", "YTD"])
        st.dataframe(styled, hide_index=True, use_container_width=True)
        st.caption("Day: latest FMP quote price (dated historical close if unavailable) versus previous trading day's adjClose, at most 4 calendar days apart. Week: five prior observed trading dates, at most 10 days. YTD: final prior-year adjClose within 7 days of year end. Missing adjusted baselines stay unavailable; not certified total returns.")
        stale = [name for name, row in packet.get("sectors", {}).items() if row.get("stale", True)]
        if stale:
            st.warning("Stale or unavailable daily observations: " + ", ".join(stale))
        with st.expander("Return input dates"):
            st.json({sector: record for sector, record in packet.get("sectors", {}).items()})
    with left, st.container(border=True):
        st.subheader(f"Industries · {selected}")
        st.caption("Drill-down detail · capped screened U.S. stocks, not full-sector holdings")
        fingerprint = sha256(fmp_api_key.strip().encode()).hexdigest()
        saved = st.session_state.get("heatmap_screen")
        if saved and saved.get("identity") != fingerprint:
            st.session_state.pop("heatmap_screen", None)
            saved = None
        if st.button("Load screened industry detail", key="heatmap_load", disabled=not bool(fmp_api_key.strip())):
            try:
                with st.spinner("Loading bounded stock screen…"):
                    data = collect_discovery(fmp_api_key)
                saved = {"identity": fingerprint, "data": data}
                st.session_state.heatmap_screen = saved
            except Exception as exc:
                message = sanitize_error(exc)
                if fmp_api_key.strip():
                    message = message.replace(fmp_api_key.strip(), "[REDACTED]")
                st.warning("Industry screen unavailable: " + message)
                if saved:
                    st.caption("Showing previously loaded screened evidence; refresh failed.")
        if not saved:
            st.info("Load the existing FMP stock screen to explore available industries. FMP configuration is required. ETF performance remains independently available.")
        else:
            data = saved["data"]
            universe = data.get("universe", pd.DataFrame())
            st.caption(f"FMP | retrieved {data.get('fetched_at') or 'Unavailable'} | at most 500 active U.S. stocks, market cap >2B and volume >500K. Exact-symbol duplicates removed; share classes retained. No sector capitalization aggregation.")
            for warning in data.get("provider_warnings", []):
                st.warning(sanitize_error(warning).replace(fmp_api_key.strip(), "[REDACTED]") if fmp_api_key.strip() else sanitize_error(warning))
            groups = industry_groups(universe, selected)
            if "sector" in universe:
                unmapped = int((~universe["sector"].map(canonical_sector).isin(SECTORS)).sum())
                if unmapped:
                    st.caption(f"{unmapped} screened records have unmapped sector membership and are excluded from sector detail.")
            st.caption(f"{sum(len(rows) for rows in groups.values())} screened companies in {len(groups)} available industries. Industry returns unavailable: compatible dated constituent evidence is not established. Price currency and market-cap currency/date are unverified.")
            if not groups:
                st.info("No industry membership is available for this sector in the loaded screen.")
            more = st.checkbox("Show all screened constituents", key="heatmap_more")
            columns = st.columns(2)
            for index, (industry, members) in enumerate(groups.items()):
                with columns[index % 2], st.container(border=True):
                    st.markdown(f"**{industry}**")
                    st.caption("Industry return unavailable")
                    display = [{"Ticker": row["symbol"], "Price (currency unknown)": finite_number(row.get("price")),
                                "Provider 1D % (undated)": finite_number(row.get("1D"))} for row in (members if more else members[:5])]
                    st.dataframe(pd.DataFrame(display), hide_index=True, use_container_width=True)
                    if not more and len(members) > 5:
                        st.caption(f"Showing 5 of {len(members)}; ordered by provider market cap, then ticker. Currency/date unverified.")
            symbols = [row["symbol"] for members in groups.values() for row in members]
            if symbols:
                # Widget options can change with sector and refreshed membership.
                if st.session_state.get("heatmap_company") not in symbols:
                    st.session_state.heatmap_company = symbols[0]
                symbol = st.selectbox("Open constituent", symbols, key="heatmap_company")
                if st.button("Open company snapshot", key="heatmap_open"):
                    from langgraphagenticai.state.research_context import ResearchContext
                    from langgraphagenticai.ui.workspace_handoff import queue_handoff
                    queue_handoff(st.session_state, ResearchContext((symbol,), "Introduction", "analyze", "Introduction"))
                    st.rerun()
        if st.button("View sector movers", key="heatmap_movers"):
            from langgraphagenticai.state.discovery import queue_discovery
            aliases = {"Financial Services": "Financial Services", "Materials": "Basic Materials"}
            queue_discovery(st.session_state, aliases.get(selected, canonical_sector(selected)))
            st.rerun()
