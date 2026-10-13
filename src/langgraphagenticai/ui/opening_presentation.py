"""Shared opening-page presentation, scoped to the opening workspace marker."""
from html import escape
import streamlit as st
from langgraphagenticai.providers.discovery import finite_number


def opening_styles():
    st.markdown('''<div class="opening-workspace"></div><style>
    .stApp:has(.opening-workspace), [data-testid="stAppViewContainer"]:has(.opening-workspace) {background:#111111;color:#e8edf2;}
    body:has(.opening-workspace) [data-testid="stHeader"] {background:#111111;border-color:#303030;}
    body:has(.opening-workspace) [data-testid="stMain"] {
      --ax-bg:#111111;--ax-panel:#1C1C1C;--ax-panel-2:#232323;--ax-panel-3:#282828;
      --ax-line:#303030;--ax-line-soft:#292929;--ax-text:#e8edf2;--ax-muted:#a7a7a7;
      --ax-dim:#989898;--ax-amber:#e34444;--ax-amber-2:#f1f1f1;--ax-green:#35d07f;--ax-red:#ff5964;
      color:#e8edf2;font-family:"Arial Narrow","Roboto Condensed",Inter,"Segoe UI",sans-serif;
    }
    body:has(.opening-workspace) [data-testid="stMain"] h1,
    body:has(.opening-workspace) [data-testid="stMain"] h2,
    body:has(.opening-workspace) [data-testid="stMain"] h3 {font-family:"Arial Narrow","Roboto Condensed",Inter,"Segoe UI",sans-serif!important;border-left:0;padding-left:0!important;letter-spacing:-.02em;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-baseweb="input"] > div,
    body:has(.opening-workspace) [data-testid="stMain"] [data-baseweb="select"] > div,
    body:has(.opening-workspace) [data-testid="stMain"] textarea {background:#1C1C1C!important;border-radius:5px!important;}
    body:has(.opening-workspace) [data-testid="stMain"] .stButton > button {background:#1C1C1C;border-color:#303030;border-radius:5px;color:#e8edf2;letter-spacing:0;font-size:.82rem;}
    body:has(.opening-workspace) [data-testid="stMain"] .stButton > button[kind="primary"] {background:#e34444;color:#ffffff;border-color:#e34444;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stExpander"] {background:#1C1C1C;border-color:#303030;border-radius:5px;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#303030!important;border-radius:5px!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stButtonGroup"] button {background:#1C1C1C;color:#e8edf2;border-color:#303030;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stButtonGroup"] button[aria-pressed="true"] {background:#e34444;color:#ffffff;}
    body:has(.opening-workspace) [data-testid="stMain"] button[data-variant="segmented_control"][aria-checked="true"] {background:#e34444!important;border-color:#e34444!important;color:#ffffff!important;}
    body:has(.opening-workspace) [data-testid="stMain"] button[data-variant="segmented_control"][aria-checked="true"] p {color:#ffffff!important;}
    body:has(.opening-workspace) [data-testid="stMain"] button[data-variant="segmented_control"]:focus-visible {outline-color:#e34444!important;}
    .opening-title {font-size:1.75rem!important;font-weight:780;letter-spacing:-.035em;line-height:1.15;margin:0;color:#f1f1f1;}
    .opening-subtitle {font-size:.9rem;color:#a7a7a7;margin:.3rem 0 .6rem;}
    .opening-cards {display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px;margin:.5rem 0 .8rem;}
    .opening-card {background:#1C1C1C;border:1px solid #303030;border-radius:5px;padding:10px 12px;min-width:0;}
    .opening-card small {display:block;color:#a7a7a7;font-size:.73rem;margin:4px 0;overflow-wrap:anywhere;}
    .opening-card strong {display:block;font-size:1.3rem;font-family:"Consolas","SFMono-Regular",monospace;font-variant-numeric:tabular-nums;color:#e8edf2;line-height:1.3;}
    .opening-card b {display:block;color:#f1f1f1;font-size:.76rem;letter-spacing:.035em;text-transform:uppercase;}
    .opening-card .positive {color:#35d07f;}.opening-card .negative {color:#ff5964;}
    .opening-notes {display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:.4rem 0 1rem;}
    .opening-notes p {font-size:.85rem;color:#a7a7a7;margin:.45rem 0 0;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stMetricLabel"] p,
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stMetricValue"],
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stTextInput"] input,
    body:has(.opening-workspace) [data-testid="stMain"] [data-baseweb="select"] {color:#e8edf2!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-baseweb="input"],
    body:has(.opening-workspace) [data-testid="stMain"] [data-baseweb="input"] input,
    body:has(.opening-workspace) [data-testid="stMain"] [data-baseweb="select"] > div {background:#1C1C1C!important;color:#e8edf2!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-baseweb="select"] svg {fill:#a7a7a7;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stExpander"] details > summary {color:#e8edf2!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stMetric"] {background:#1C1C1C;border-color:#303030;border-radius:5px;}
    body:has(.opening-workspace) [data-testid="stMain"] label {color:#e8edf2!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stMarkdownContainer"] p {color:#e8edf2;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stAlert"] {background:#1f1b13;color:#e8edf2;border-color:#765a27;border-radius:5px;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stAlert"] p {color:#e8edf2!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stTextInputRootElement"],
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stSelectbox"] [role="group"],
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stNumberInputContainer"],
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stMultiSelect"] [role="group"] {background:#1C1C1C!important;color:#e8edf2!important;border-color:#303030!important;border-radius:5px!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stSelectbox"] input,
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stSelectbox"] [role="group"] *,
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stNumberInputContainer"] input {color:#e8edf2!important;}
    body:has(.opening-workspace) [data-testid="stMain"] .stButton > button[kind="primary"] p,
    body:has(.opening-workspace) [data-testid="stMain"] .stButton > button[kind="primary"] span {color:#ffffff!important;}
    body:has(.opening-workspace) [data-testid="stMain"] .ax-statusbar {background:#1C1C1C;color:#a7a7a7;border-color:#303030;}
    body:has(.opening-workspace) [data-testid="stMain"] .ax-statusbar b {color:#e8edf2;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stCaptionContainer"] {opacity:1!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stCaptionContainer"],
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stCaptionContainer"] p {color:#a7a7a7!important;}
    body:has(.opening-workspace) [data-testid="stMain"] h2,
    body:has(.opening-workspace) [data-testid="stMain"] h3 {color:#f1f1f1!important;text-transform:uppercase;letter-spacing:.055em;font-size:1rem!important;}
    body:has(.opening-workspace) [data-testid="stMain"] [data-testid="stMetricValue"] {font-family:"Consolas","SFMono-Regular",monospace;font-variant-numeric:tabular-nums;}
    body:has(.opening-workspace) [data-testid="stMain"] a {color:#26c6da;}
    .opening-workspace {display:none;}
    body:has(.opening-workspace) [data-testid="stMainBlockContainer"] {padding-top:1.1rem;padding-bottom:2rem;max-width:1920px;}
    body:has(.opening-workspace) [data-testid="stVerticalBlock"] {gap:.7rem;}
    .terminal-quote {border-bottom:1px solid #303030;padding:8px 0 14px;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;}
    .terminal-quote h2 {margin:0 0 7px!important;font-size:1.1rem!important;text-transform:none!important;letter-spacing:0!important;}
    .terminal-quote .badge {background:#303030;border-radius:4px;padding:3px 7px;color:#c3c3c3;font-size:.7rem;margin-left:7px;}
    .terminal-quote strong {font:700 2rem Consolas,monospace;font-variant-numeric:tabular-nums;}
    .terminal-quote small {color:#a7a7a7;font-size:.72rem;}
    .terminal-quote .positive,.terminal-grid .positive {color:#35d07f;}.terminal-quote .negative,.terminal-grid .negative {color:#ff5964;}
    .terminal-quote .consensus {text-align:right;font-size:.78rem;color:#a7a7a7;line-height:1.6;}
    .terminal-rail {height:4px;background:#303030;border-radius:4px;position:relative;margin:9px 0 5px;}
    .terminal-rail i {display:block;position:absolute;top:-3px;height:10px;width:3px;background:#e34444;}
    .terminal-rail-labels {display:flex;justify-content:space-between;font:11px Consolas,monospace;color:#a7a7a7;gap:10px;margin-bottom:12px;}
    .terminal-panel {background:#1C1C1C;border:1px solid #303030;border-radius:5px;padding:12px;margin-bottom:10px;min-width:0;}
    .terminal-panel h3 {margin:0 0 10px!important;padding-bottom:7px;border-bottom:1px solid #303030;font-size:.84rem!important;}
    .terminal-grid {display:grid;grid-template-columns:1fr 1fr;gap:0 16px;}
    .terminal-grid .metric {display:flex;align-items:center;justify-content:space-between;gap:7px;border-bottom:1px solid #292929;padding:7px 0;min-width:0;}
    .terminal-grid .metric span {color:#a7a7a7;font-size:.76rem;overflow-wrap:anywhere;}
    .terminal-grid .metric b {font:12px Consolas,monospace;white-space:normal;overflow-wrap:anywhere;text-align:right;}
    .terminal-panel p {font-size:.82rem;line-height:1.5;margin:0;}
    .company-price-marker {display:none;}
    .peer-scroll {width:100%;overflow-x:auto;margin:8px 0 14px;}
    .terminal-peers {width:100%;min-width:520px;border-collapse:collapse;font-size:11px;}
    .terminal-peers th,.terminal-peers td {border-bottom:1px solid #303030;padding:9px 7px;text-align:right;}
    .terminal-peers thead th {color:#a7a7a7;font-weight:normal;font-size:10px;}
    .terminal-peers th:first-child {text-align:left;}
    .terminal-peers tr.selected {background:#303030;}
    .terminal-peers tr.selected th {border-left:2px solid #e34444;}
    .peer-value {position:relative;font-family:Consolas,monospace;white-space:nowrap;}
    .peer-value i {position:absolute;left:0;bottom:3px;height:14px;background:#777777;opacity:.22;}
    .peer-value span {position:relative;}
    @media(max-width:1100px) {.terminal-grid{gap:0 9px}.terminal-grid .metric b{font-size:11px}.terminal-grid .metric span{font-size:.7rem}}
    @media(max-width:1100px) {
      body:has(.opening-workspace) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .company-price-marker) {flex-wrap:wrap;}
      body:has(.opening-workspace) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .company-price-marker) > [data-testid="stColumn"] {width:100%!important;flex:1 1 100%!important;}
    }
    @media(max-width:640px) {.terminal-quote .consensus{text-align:left}.terminal-grid .metric b{font-size:12px}.terminal-grid .metric span{font-size:.74rem}}
    @media(max-width:640px) {.opening-notes{grid-template-columns:1fr}.opening-title{font-size:1.7rem}.opening-cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
    </style>''', unsafe_allow_html=True)


def heading(title, subtitle):
    st.markdown(f'<h1 class="opening-title">{escape(title)}</h1><p class="opening-subtitle">{escape(subtitle)}</p>', unsafe_allow_html=True)


def number(value, suffix="", signed=False, decimals=2):
    value = finite_number(value)
    return "Unavailable" if value is None else (f"{value:+,.{decimals}f}" if signed else f"{value:,.{decimals}f}") + suffix


def cards(items):
    st.markdown('<div class="opening-cards">' + ''.join(
        f'<div class="opening-card"><b>{escape(str(label))}</b><strong>{escape(str(value))}</strong><small>{escape(str(note))}</small></div>'
        for label, value, note in items) + '</div>', unsafe_allow_html=True)


def observations(items):
    st.markdown('<div class="opening-notes">' + ''.join(
        f'<div class="opening-card"><b>{escape(title)}</b><p>{escape(text)}</p></div>'
        for title, text in items) + '</div>', unsafe_allow_html=True)


def terminal_chart(chart):
    """Style only the supplied opening chart, preserving data/encoding/axes."""
    return (chart.configure(background="#1C1C1C", font="Consolas")
            .configure_view(stroke="#303030")
            .configure_axis(labelColor="#a7a7a7", titleColor="#a7a7a7", gridColor="#292929",
                            domainColor="#303030", tickColor="#303030", labelFontSize=11,
                            titleFontSize=11, gridOpacity=.65)
            .configure_legend(labelColor="#c6d2dd", titleColor="#a7a7a7")
            .configure_title(color="#f1f1f1", anchor="start")
            .configure_range(category=["#26c6da", "#e34444", "#bd9bff", "#35d07f", "#ff5964"]))


def opening_price_chart(frame, period, unit, *, height=280):
    """Thin price line + restrained area using the same dated wall-clock contract."""
    import altair as alt
    from langgraphagenticai.ui.technical_chart import price_chart_spec
    base = price_chart_spec(frame, period, unit).encode(color=alt.value("#e34444"))
    domain = list(base.to_dict()["encoding"]["y"]["scale"]["domain"])
    # Area baseline is the existing finite padded domain, never an invented zero.
    area = base.copy(deep=True).mark_area(opacity=.12, color="#e34444").encode(y2=alt.datum(domain[0]))
    # Keep one interactive selection, shared by the two layers.
    area.params = alt.Undefined
    return terminal_chart((area + base).properties(height=height))


def compact_number(value, currency=""):
    value = finite_number(value)
    if value is None:
        return "Unavailable"
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= divisor:
            return f"{value / divisor:,.2f}{suffix}" + (f" {currency}" if currency else "")
    return number(value) + (f" {currency}" if currency else "")


def quote_header(symbol, company, sector, quote, *, analyst=True):
    """Shared quote treatment; currency must come from this quote, not profile."""
    price, change, percent = (finite_number(quote.get(key)) for key in ("price", "change", "change_pct"))
    css = "positive" if percent is not None and percent > 0 else "negative" if percent is not None and percent < 0 else ""
    daily = "Daily change unavailable" if change is None and percent is None else number(percent, "%", True) if change is None else number(change, signed=True) if percent is None else f'{number(change, signed=True)} ({number(percent, "%", True)})'
    if isinstance(analyst, dict):
        rating = escape(str(analyst.get("consensus") or "Unavailable"))
        count = number(analyst.get("count"), decimals=0)
        target = number(analyst.get("target"))
        upside = finite_number(analyst.get("upside"))
        upside = number(upside * 100, "%", True) if upside is not None else "Unavailable"
        note = escape(str(analyst.get("note") or ""), quote=True)
        estimate_date = escape(str(analyst.get("estimate_date") or "Unavailable"))
        currency = escape(str(analyst.get("currency") or (str(analyst["listing_currency"]) + " listing basis" if analyst.get("listing_currency") else "Currency unknown")))
        consensus = f'<div class="consensus" title="{note}"><b>Analyst consensus: {rating}</b><br>EPS analysts: {count} (FY {estimate_date})<br>Price target: {target} {currency} / upside: {upside}<br><small>Provider snapshot; observation dates not supplied</small></div>'
    else:
        consensus = '<div class="consensus"><b>Analyst consensus: Unavailable</b><br>Analyst count / price target / upside: Unavailable<br><small>Analyst evidence unavailable</small></div>' if analyst else ""
    currency_label = quote.get("currency") or (str(quote["listing_currency"]) + " listing metadata" if quote.get("listing_currency") else "Unknown quote currency")
    st.markdown(f'<div class="terminal-quote"><div><h2>{escape(str(symbol))} <span>{escape(str(company))}</span><span class="badge">{escape(str(sector or "Sector unavailable"))}</span></h2>'
                f'<strong>{escape(number(price))}</strong> <small>{escape(str(currency_label))}</small> '
                f'<span class="{css}">{escape(daily)}</span></div>{consensus}</div>', unsafe_allow_html=True)


def price_rail(quote):
    low, high, price = (finite_number(quote.get(key)) for key in ("year_low", "year_high", "price"))
    if low is None or high is None or price is None or low >= high:
        st.caption("52-week range position: Unavailable (missing or invalid endpoints).")
        return
    position = max(0, min(100, (price - low) / (high - low) * 100))
    note = "Current price outside provider 52-week endpoints" if price < low or price > high else "Current quote position"
    st.markdown(f'<div class="terminal-rail"><i style="left:{position:.3f}%"></i></div><div class="terminal-rail-labels"><span>52W LOW {escape(number(low))}</span><span>{note}</span><span>52W HIGH {escape(number(high))}</span></div>', unsafe_allow_html=True)


def metric_value(key, item):
    from langgraphagenticai.analysis.company_terminal import PERCENT_METRICS
    value = finite_number(item.get("value"))
    if value is None:
        return "Unavailable"
    if key in PERCENT_METRICS:
        return number(value * 100, "%", key == "revenue_growth", 1)
    if key in {"market_cap", "enterprise_value"}:
        currency = item.get("currency") or (str(item["listing_currency"]) + " listing basis" if item.get("listing_currency") else "Currency ?")
        return compact_number(value, currency)
    if key in {"volume", "avg_volume"}:
        return compact_number(value)
    if key == "pe_ttm" and value <= 0:
        return f"{number(value)} (loss/zero)"
    return number(value)


def metric_grid(title, layout, metrics):
    rows = []
    for label, key in layout:
        item = metrics.get(key, {})
        detail = f'{item.get("basis", "Unavailable")} | as of {item.get("as_of") or "Unavailable"} | {item.get("reason") or item.get("note") or "Provider fact / deterministic calculation; see metric evidence"}'
        rows.append(f'<div class="metric" title="{escape(detail, quote=True)}"><span>{escape(label)}</span><b>{escape(metric_value(key, item))}</b></div>')
    st.markdown(f'<section class="terminal-panel"><h3>{escape(title)}</h3><div class="terminal-grid">{"".join(rows)}</div></section>', unsafe_allow_html=True)
