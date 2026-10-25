"""Introduction chart controls and deterministic/explicit-action AI presentation."""
import altair as alt
import pandas as pd
import streamlit as st

from langgraphagenticai.technical_analysis.indicators import (
    IndicatorSettings, calculate_indicators, finite_domain, axis_style,
)
from langgraphagenticai.technical_analysis.evidence import technical_packet, technical_summary
from langgraphagenticai.technical_analysis.agent import analyze_technical
from langgraphagenticai.analysis.executive_text import executive_text
from langgraphagenticai.utils.safety import sanitize_error


def indicator_controls(key, daily_only=False):
    values = {}
    with st.expander("Technical indicators & settings"):
        # Individual controls avoid the lazy-loaded Multiselect frontend chunk.
        # Keep a non-widget copy so navigation preserves the selected indicators.
        preference_key = f"technical_indicator_choices:{key}"
        prior = st.session_state.get(preference_key, st.session_state.get(f"{key}_indicators", ["SMA", "RSI"]))
        st.caption("Indicators")
        choices = st.columns(3)
        selected = [name for index, name in enumerate(("SMA", "EMA", "RSI", "MACD", "Bollinger"))
                    if choices[index % 3].checkbox(name, value=name in prior, key=f"{key}_indicator_{name}")]
        st.session_state[preference_key] = selected
        st.caption("Windows count observed daily bars for this chart. Up to 500 warmup bars are used before display trimming." if daily_only else "Windows count observed bars: five-minute bars for 1D/5D; daily bars for longer ranges. Up to 500 warmup bars are used before display trimming.")
        columns = st.columns(3)
        for i, name in enumerate(selected):
            with columns[i % 3]:
                if name in {"SMA", "EMA", "RSI"}:
                    values[name.lower()] = int(st.number_input(f"{name} window (bars)", min_value=2, max_value=500,
                        value=14 if name == "RSI" else 20, step=1, key=f"{key}_{name.lower()}"))
                elif name == "MACD":
                    for part, default in (("fast", 12), ("slow", 26), ("signal", 9)):
                        values[f"macd_{part}"] = int(st.number_input(f"MACD {part} (bars)", min_value=2, max_value=498,
                            value=default, step=1, key=f"{key}_macd_{part}"))
                else:
                    values["bollinger"] = int(st.number_input("Bollinger window (bars)", min_value=2, max_value=500,
                                                          value=20, step=1, key=f"{key}_bollinger"))
                    values["bollinger_std"] = float(st.number_input("Bollinger standard deviations", min_value=.5,
                            max_value=5., value=2., step=.1, key=f"{key}_bollinger_std"))
    return IndicatorSettings(selected=tuple(selected), **values)


def _plot_frame(frame):
    """Plot provider wall-clock fields on a UTC scale, avoiding browser-zone shifts.

    These UTC projections are only coordinates, never source timestamps. The
    exact original offset/naive timestamp is retained in tooltips and evidence.
    """
    frame = frame.copy()
    frame["Observed timestamp"] = frame.Date.map(lambda value: pd.Timestamp(value).isoformat())
    frame["Date"] = frame.Date.map(lambda value: pd.Timestamp(value).tz_localize(None).tz_localize("UTC"))
    return frame


def price_chart_spec(frame, period, unit):
    """Testable price/overlay spec with a finite padded axis, independent oscillators."""
    frame = _plot_frame(frame)
    columns = [column for column in ("Close", "SMA", "EMA", "Bollinger mid", "Bollinger upper", "Bollinger lower") if column in frame]
    long = frame.melt(id_vars=["Date", "Observed timestamp"], value_vars=columns, var_name="Series", value_name="Value").dropna()
    return alt.Chart(long).mark_line(point=len(frame) == 1).encode(
        x=alt.X("Date:T", title="Provider wall-clock time" if period in {"1D", "5D"} else "Date", scale=alt.Scale(type="utc"), axis=alt.Axis(**axis_style(period))),
        y=alt.Y("Value:Q", title=unit, scale=alt.Scale(zero=False, domain=finite_domain(long.Value))),
        color=alt.Color("Series:N", scale=alt.Scale(domain=columns, range=["#19d6f5", "#f5c75d", "#bd9bff", "#86baaa", "#ee9fa3", "#ee9fa3"][:len(columns)]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[alt.Tooltip("Observed timestamp:N", title="Source timestamp"), "Series:N", alt.Tooltip("Value:Q", format=",.3f")],
    ).properties(height=280).interactive()


def render_indicator_charts(frame, period, unit, *, chart_style=None):
    def draw(spec):
        if chart_style is None:
            st.altair_chart(spec, width="stretch")
        else:
            st.altair_chart(chart_style(spec), width="stretch", theme=None)
    draw(price_chart_spec(frame, period, unit))
    frame = _plot_frame(frame)
    if "RSI" in frame:
        rsi = alt.Chart(frame).mark_line(color="#f5c75d").encode(
            x=alt.X("Date:T", scale=alt.Scale(type="utc"), axis=alt.Axis(**axis_style(period))),
            y=alt.Y("RSI:Q", scale=alt.Scale(domain=[0, 100]), title="Wilder RSI"),
            tooltip=["Observed timestamp:N", alt.Tooltip("RSI:Q", format=".1f")])
        rules = alt.Chart(pd.DataFrame({"Threshold": [30, 70]})).mark_rule(strokeDash=[4, 4], color="#83909e").encode(y="Threshold:Q")
        draw((rsi + rules).properties(height=140).interactive())
    if "MACD" in frame:
        long = frame.melt(id_vars=["Date", "Observed timestamp"], value_vars=["MACD", "MACD signal"], var_name="Series", value_name="Value")
        chart = alt.Chart(long).mark_line().encode(
            x=alt.X("Date:T", scale=alt.Scale(type="utc"), axis=alt.Axis(**axis_style(period))),
            y=alt.Y("Value:Q", title=f"MACD ({unit})"), color="Series:N",
            tooltip=["Observed timestamp:N", "Series:N", alt.Tooltip("Value:Q", format=".3f")])
        histogram = alt.Chart(frame).mark_bar(opacity=.35).encode(x=alt.X("Date:T", scale=alt.Scale(type="utc")), y="MACD histogram:Q")
        if chart_style is not None:
            histogram = histogram.encode(color=alt.condition(alt.datum["MACD histogram"] >= 0,
                                                              alt.value("#26c6da"), alt.value("#ff5964")))
        draw((histogram + chart).properties(height=150).interactive())


def render_technical_chart(chart, *, key, openai_api_key="", model_name="gpt-5", chart_style=None):
    period = chart.get("period", "1D")
    for warning in chart.get("warnings", []):
        st.warning(warning)
    if not chart.get("points"):
        st.info("Historical prices are unavailable. Retry this chart or choose another range; other results are preserved.")
        return
    configuration_valid = True
    try:
        settings = indicator_controls(key, daily_only=chart.get("daily_only", False))
    except ValueError as exc:
        st.error(str(exc) + " Correct the indicator settings before requesting AI analysis.")
        configuration_valid = False
        settings = IndicatorSettings(selected=())
    frame = calculate_indicators(chart.get("calculation_points", chart["points"]), settings)
    frame = frame[frame.Date >= chart["points"][0][0]].copy()
    unit = chart.get("unit", "Index points" if chart.get("symbol", "^GSPC") == "^GSPC" else "Currency unknown")
    if chart_style is None:
        render_indicator_charts(frame, period, unit)
    else:
        render_indicator_charts(frame, period, unit, chart_style=chart_style)
    st.caption(f"{chart.get('symbol', '^GSPC')} · {period} · {chart.get('provider', 'Unknown')} · {chart.get('price_basis', 'Basis unknown')} · {unit}")
    st.caption(f"As of {chart.get('as_of', str(frame.iloc[-1].Date))} · retrieved {chart.get('retrieved_at', 'Unknown')} · timezone {chart.get('timezone', 'Unknown')} · {chart.get('interval', 'Unknown interval')} · {len(frame)} displayed bars. Axes preserve provider wall-clock fields; tooltips retain source timestamps. Price performance, not total return.")
    st.caption("History cache: up to 5 minutes. Refresh chart history to request new observations. Data gaps and session completeness are not independently verified.")
    if len(frame) == 1:
        st.warning("Only one observed price bar is available; price change and technical AI interpretation are unavailable.")
    packet = technical_packet(chart, frame, settings, model_name)
    st.markdown("**Technical summary · calculated from observed prices**")
    for line in technical_summary(packet):
        st.write(line)
    saved_key = f"technical_ai:{key}"
    if st.button("Analyze technical evidence with AI", key=f"{key}_analyze", disabled=not configuration_valid or not openai_api_key.strip() or len(frame) < 2):
        try:
            with st.spinner("Interpreting saved technical evidence…"):
                st.session_state[saved_key] = analyze_technical(packet, openai_api_key, model_name)
        except Exception as exc:
            st.warning("Technical AI analysis failed; previous analysis is preserved. " + sanitize_error(exc))
    if not openai_api_key.strip():
        st.caption("Configure an OpenAI key to request technical AI interpretation. Indicator and chart changes do not call a model.")
    saved = st.session_state.get(saved_key)
    if saved:
        st.markdown("**Technical AI interpretation**")
        if saved.get("fingerprint") != packet["fingerprint"]:
            st.warning("Saved AI interpretation belongs to earlier chart inputs/settings/model. Re-run analysis to match the current evidence.")
        st.caption(f"{saved['symbol']} · {saved['range']} · evidence as of {saved['as_of']} · outlook {saved['outlook']}")
        st.write(executive_text(saved["summary"]))
        for claim in saved["claims"]:
            st.write(executive_text(claim["interpretation"]))
        for title, field in (("Risks", "risks"), ("Thesis invalidation", "invalidation_conditions"), ("Uncertainty & limitations", "limitations")):
            st.write(title + ": " + executive_text("; ".join(saved[field])))
    with st.expander("Technical evidence & calculation basis"):
        st.dataframe(pd.DataFrame(packet["evidence"]), hide_index=True, width="stretch")
        for limitation in packet["limitations"]:
            st.caption(limitation)
        st.caption(f"Source: {chart.get('source', 'Unknown')} · calculation bars {packet['calculation_bars']} · evidence fingerprint {packet['fingerprint'][:16]}")
