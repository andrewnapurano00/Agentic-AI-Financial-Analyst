"""Selected-mover social evidence: explicit collection and local chart controls."""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import altair as alt
import pandas as pd
import streamlit as st
from langgraphagenticai.analysis.social_sentiment import daily_statistics, METRICS, WINDOWS
from langgraphagenticai.analysis.trading_calendar import last_trading_dates
from zoneinfo import ZoneInfo
from langgraphagenticai.providers.social_sentiment import load_social_sentiment
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.ui.opening_presentation import terminal_chart
from langgraphagenticai.utils.safety import sanitize_error


def sentiment_chart(rows, metric, statistic):
    frame = pd.DataFrame([r for r in rows if r["Metric"] == metric])
    return terminal_chart(alt.Chart(frame).mark_line(point=True).encode(
        x=alt.X("Date:O", title="NYSE trading date", axis=alt.Axis(labelAngle=-35)),
        y=alt.Y(f"{statistic}:Q", title=f"{statistic} {metric.lower()} · active snapshots", scale=alt.Scale(zero=False)),
        color=alt.Color("Platform:N", scale=alt.Scale(domain=["Stocktwits", "Twitter"], range=["#37B68C", "#C8AA73"]), legend=alt.Legend(orient="bottom")),
        strokeDash=alt.StrokeDash("Platform:N", legend=None),
        tooltip=["Date:N", "Platform:N", alt.Tooltip(f"{statistic}:Q", format=",.4f"), "Observations:Q", "Active snapshots:Q", "Excluded snapshots:Q", "Snapshots:Q"],
    ).properties(height=300))


def render_social_sentiment(symbol, api_key):
    symbol = normalize_company_symbol(symbol)
    st.subheader(f"{symbol} · Social sentiment")
    st.caption("Stocktwits and Twitter · FMP legacy social data. Select a ranked company, then load its social history. No AI calls.")
    credential_id = sha256(api_key.strip().encode()).hexdigest()
    identity = (credential_id, symbol)
    results = dict(st.session_state.get("movers_social_results", {}))
    preferences = dict(st.session_state.get("movers_social_preferences", {}))
    pages = st.selectbox("Social history page limit", [3, 5, 10], index=[3, 5, 10].index(preferences.get("pages", 5)), key="movers_social_pages",
                         help="Page size is set by FMP. More pages can improve coverage but take longer; up to 5,000 returned records are retained.")
    preferences["pages"] = pages
    st.session_state.movers_social_preferences = preferences
    if st.button(f"Load / refresh {symbol} social history", key="movers_social_load", disabled=not api_key.strip()):
        try:
            with st.spinner(f"Loading {symbol} social snapshots..."):
                packet = load_social_sentiment(symbol, api_key, pages, refresh=True)
            if packet.get("symbol") != symbol:
                raise ValueError("Social evidence did not match the selected ticker.")
            if packet.get("records") or identity not in results:
                results.pop(identity, None)
                results[identity] = packet
            else:
                previous = dict(results[identity])
                previous["refresh_warnings"] = ["Refresh returned no usable observations; showing previously saved evidence.", *packet.get("warnings", [])]
                results[identity] = previous
            while len(results) > 8:
                results.pop(next(iter(results)))
            st.session_state.movers_social_results = results
        except Exception as exc:
            st.warning("Social history unavailable; saved evidence preserved. " + sanitize_error(exc))
    packet = results.get(identity)
    if not packet:
        st.info("Load social history for this company to view daily average or median sentiment and activity. Other tickers' evidence stays saved in this session.")
        return
    if packet.get("page_budget") != pages:
        st.caption("Page limit changed. Load / refresh social history to apply it; the chart still uses saved observations.")
    now = datetime.now(timezone.utc)
    records = packet.get("records", [])
    latest = max((r["day"] for r in records), default=None)
    st.caption(f"Source: FMP · {symbol} · retrieved {packet.get('retrieved_at', 'Unknown')} · latest observation date {latest or 'Unavailable'} · {packet.get('pages_received', 0)} pages received / {packet.get('pages_requested', 0)} attempted · {len(records)} unique usable snapshots.")
    for warning in dict.fromkeys([*packet.get("warnings", []), *packet.get("refresh_warnings", [])]):
        st.warning(warning)
    try:
        recent_dates = last_trading_dates(now.astimezone(ZoneInfo("America/New_York")).date())
    except (ImportError, ValueError, RuntimeError) as exc:
        st.warning("Trading calendar unavailable; saved social evidence is preserved. " + sanitize_error(exc))
        return
    if latest and latest < recent_dates[0]:
        st.warning("Available social evidence is older than the last five trading days. It is historical, not current sentiment.")
    # Migrate older calendar-window preferences without recollecting saved evidence.
    old_window = preferences.get("window")
    if old_window not in WINDOWS:
        preferences["window"] = WINDOWS[1] if old_window == "Latest 5 reported dates" else WINDOWS[0]
    if st.session_state.get("movers_social_window") not in (*WINDOWS, None):
        st.session_state.movers_social_window = preferences["window"]
    window = st.selectbox("Social date window", WINDOWS, index=WINDOWS.index(preferences.get("window", WINDOWS[0])), key="movers_social_window")
    metric_col, stat_col = st.columns(2)
    with metric_col:
        metric = st.selectbox("Social metric", list(METRICS), index=list(METRICS).index(preferences.get("metric", "Sentiment score")), key="movers_social_metric")
    with stat_col:
        statistic = st.radio("Daily statistic", ["Average", "Median"], index=["Average", "Median"].index(preferences.get("statistic", "Average")), horizontal=True, key="movers_social_statistic")
    with st.expander("Activity filters"):
        min_posts = int(st.number_input("Minimum posts per platform snapshot", min_value=1, max_value=10000,
                        value=preferences.get("min_posts", 1), key="movers_social_min_posts"))
        hide_zero = st.checkbox("Hide zero sentiment scores", value=preferences.get("hide_zero", True), key="movers_social_hide_zero",
                               help="Default view excludes zero scores as a display policy. Original provider values are retained; turn off to include zero scores when posts qualify.")
    st.session_state.movers_social_preferences = dict(pages=pages, window=window, metric=metric, statistic=statistic, min_posts=min_posts, hide_zero=hide_zero)
    rows = daily_statistics(records, now, window, min_posts=min_posts, hide_zero_sentiment=hide_zero)
    selected = [r for r in rows if r["Metric"] == metric]
    st.caption(f"Trading days only · at least {min_posts} post(s) per platform snapshot · zero sentiment scores {'excluded' if hide_zero else 'included when posts qualify'}. No-post hours do not dilute the average or median.")
    for platform, column in zip(("Stocktwits", "Twitter"), st.columns(2)):
        usable = [r for r in selected if r["Platform"] == platform and r[statistic] is not None]
        last = usable[-1] if usable else None
        with column:
            st.metric(platform, f"{last[statistic]:,.4f}" if last else "Unavailable")
            st.caption(f"{last['Date']} · {last['Observations']} eligible snapshots" if last else "No eligible observations in this window")
    if any(r[statistic] is not None for r in selected):
        st.altair_chart(sentiment_chart(rows, metric, statistic), width="stretch", theme=None, key="movers_social_chart")
    else:
        st.info("No eligible values for this metric and trading-day window. Try another metric, Latest 5 reported trading dates, or reload with a larger page limit.")
    if rows:
        with st.expander("Daily social statistics & coverage"):
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption("Observations counts eligible finite values; Active snapshots meet the platform post threshold; Snapshots includes all returned usable records for that trading date. Excluded snapshots fail the activity/value filters. A real zero score is retained in raw evidence and can be included by disabling the zero-score filter; zero likes/comments remain valid when posts qualify.")
            st.caption("Calendar: XNYS (NYSE), excluding weekends, holidays and recorded exceptional closures. Current trading date can be partial. Aware timestamps group by New York date; naive timestamps retain unverified provider dates. This filters trading dates, not market hours; after-hours social snapshots on a session date remain eligible.")
            st.caption("Average/median weight eligible snapshots equally, not posts/users. Activity values are per snapshot, not daily totals; interval/cumulative meanings and complete-day coverage are unverified. Raw sentiment calibration/neutral threshold is unavailable; no percentage conversion or bullish/bearish threshold is inferred.")
            st.json({"pagination_end": packet.get("pagination_end"), "diagnostics": packet.get("diagnostics", {})})
