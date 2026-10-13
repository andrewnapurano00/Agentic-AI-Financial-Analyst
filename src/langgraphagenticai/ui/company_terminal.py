"""Compact earnings, peer and metric evidence presentation (no provider calls)."""
from html import escape
import altair as alt
import pandas as pd
import streamlit as st

from langgraphagenticai.ui.opening_presentation import terminal_chart, number
from langgraphagenticai.ui.workspace_presentation import saved_time


def render_earnings(earnings, retrieved):
    st.subheader("Earnings History")
    reported = earnings.get("reported", [])
    if not reported:
        st.info("Reported EPS events unavailable. Other company evidence remains usable.")
    else:
        bars = []
        for event in reversed(reported):
            for series, key in (("Estimate", "estimate"), ("Actual", "actual")):
                if event.get(key) is not None:
                    bars.append({"Announcement": event["date"], "EPS": event[key], "Series": series,
                                 "Comparison": "Estimate" if series == "Estimate" else event.get("comparison", "Unavailable comparison"),
                                 "Last updated": event.get("last_updated") or "Unavailable"})
        if bars:
            chart = alt.Chart(pd.DataFrame(bars)).mark_bar(size=23).encode(
                x=alt.X("Announcement:N", title=None, sort=None), xOffset="Series:N",
                y=alt.Y("EPS:Q", title="Provider EPS (basis unverified)"),
                color=alt.Color("Comparison:N", scale=alt.Scale(domain=["Estimate", "Beat", "Miss", "Equal", "Unavailable comparison"],
                                  range=["#858585", "#35d07f", "#ff5964", "#b8b8b8", "#b8b8b8"]), title=None),
                tooltip=["Announcement", "Series", alt.Tooltip("EPS:Q", format=".2f"), "Comparison", "Last updated"],
            ).properties(height=210)
            st.altair_chart(terminal_chart(chart), use_container_width=True, theme=None)
        latest = reported[0]
        st.caption(f"Latest EPS surprise {number(latest.get('surprise') * 100 if latest.get('surprise') is not None else None, '%', True)} | announcement {latest['date']} | provider updated {latest.get('last_updated') or 'Unavailable'}")
    next_event = earnings.get("next_event")
    st.caption(f"Next earnings announcement: {next_event['date'] if next_event else 'Unavailable'} | FMP retrieved {saved_time(retrieved)}")
    st.caption(earnings.get("basis") or "EPS currency, adjustment basis and fiscal-quarter labels unavailable. Dates describe announcements.")


def render_peers(peers, symbol, retrieved):
    st.subheader("Peer Comparison")
    labels = {"revenue_growth": "Revenue Growth YoY", "gross_margin": "Gross Margin", "operating_margin": "Operating Margin", "pe_ttm": "P/E", "roic": "ROIC"}
    rows = []
    for peer in peers:
        rows.append({"Ticker": peer["symbol"], **{label: peer.get("metrics", {}).get(key, {}).get("value") for key, label in labels.items()}})
    if not rows:
        st.info("Verified peers unavailable.")
        return
    scales = {label: max((abs(float(row[label])) for row in rows if row[label] is not None), default=0) for label in labels.values()}
    body = []
    for row in rows:
        cells = []
        for label in labels.values():
            value = row[label]
            text = "Unavailable" if value is None else number(value) + (" (loss/zero)" if value <= 0 else "") if label == "P/E" else number(value * 100, "%", True, 1)
            width = min(100, abs(value) / scales[label] * 100) if value is not None and scales[label] and label not in {"P/E", "ROIC"} else 0
            cells.append(f'<td class="peer-value"><i style="width:{width:.2f}%"></i><span>{escape(text)}</span></td>')
        selected_class = "selected" if row["Ticker"] == symbol else ""
        peer = next(item for item in peers if item["symbol"] == row["Ticker"])
        period = peer.get("metrics", {}).get("gross_margin", {})
        through = escape(str(period.get("as_of") or "Provider undated"))
        body.append(f'<tr class="{selected_class}"><th scope="row">{escape(row["Ticker"])}</th><td>{through}</td>{"".join(cells)}</tr>')
    headers = "".join(f'<th scope="col">{escape(label)}</th>' for label in labels.values())
    st.markdown(f'<div class="peer-scroll"><table class="terminal-peers"><thead><tr><th scope="col">Ticker</th><th scope="col">Margin TTM through</th>{headers}</tr></thead><tbody>{"".join(body)}</tbody></table></div>', unsafe_allow_html=True)
    st.caption(f"Selected company + {max(0, len(peers) - 1)} / 4 verified FMP-listed peers | retrieved {saved_time(retrieved)}")
    st.caption("Neutral bars show signed magnitude, not investment scores. Latest available TTM ratios: fiscal dates can differ and are shown per row; provider fallback margins are undated. P/E and ROIC are provider TTM snapshots with valuation/period dates not supplied. No same-date audit or currency-amount aggregation. P/E ≤ 0 indicates losses/zero earnings.")
    with st.expander("Peer basis & partial coverage"):
        for peer in peers:
            for key, item in peer.get("metrics", {}).items():
                st.caption(f"{peer['symbol']} / {labels.get(key, key)}: {item.get('basis')} | through {item.get('as_of') or 'Unavailable'} | {item.get('currency') or 'Currency unavailable'} | {item.get('reason') or item.get('note') or 'Latest available evidence'}")


def render_metric_evidence(terminal):
    with st.expander("Metric definitions, source dates & missing coverage"):
        rows = []
        for key, item in terminal.get("metrics", {}).items():
            rows.append({"Metric": key, "Value": item.get("value"), "Raw provider": item.get("raw"), "Unit": item.get("unit"),
                         "Basis": item.get("basis"), "As of": item.get("as_of") or "Unavailable", "Currency": item.get("currency") or "Unavailable", "Listing currency metadata": item.get("listing_currency") or "Unavailable",
                         "Source fields": ", ".join(item.get("fields", [])), "Missing reason": item.get("reason"), "Assumptions": item.get("note", ""), "Retrieved": saved_time(item.get("retrieved_at"))})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("FMP facts and local calculations. TTM sums four validated consecutive standalone fiscal quarters; filings/availability dates remain separate from period ends. Annual CAGR uses consecutive positive same-currency FY revenue. FMP ROIC/ROE/ROA/dividend-yield ratios are fractions, displayed as percentages. Provider TTM observation dates may be absent. Forward P/E uses the next future annual EPS estimate, with currency/adjustment assumptions shown explicitly. Quote currency is not inferred from profile currency.")
        for warning in terminal.get("warnings", []):
            st.caption(warning)
