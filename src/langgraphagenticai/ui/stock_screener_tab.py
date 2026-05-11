import os
import time
import numpy as np
import pandas as pd
import requests
import streamlit as st
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================================================================
# CONFIG
# ==============================================================================
FMP_API_KEY = ""

FMP_BATCH_SIZE = 50
FMP_BATCH_SLEEP = float(os.getenv("FMP_BATCH_SLEEP", "1.0"))

MAX_SERVER_LIMIT = 500
MAX_SERVER_PAGES = 25
MAX_ENRICH_TICKERS = 2000

# ==============================================================================
# SHARED STYLES
# ==============================================================================
def _render_screener_styles():
    st.markdown(
        """
        <style>
        .cardbox{
            background:#f8f9fb;
            border:1px solid #e7e8ef;
            border-radius:14px;
            padding:14px;
            margin-bottom:16px;
        }
        .subtle{
            color:#4b5563;
            font-size:13px;
            margin-bottom:6px;
        }
        .scrollarea{
            white-space:pre-wrap;
            line-height:1.38;
            max-height:220px;
            overflow:auto;
            background:white;
            border:1px solid #ececf3;
            border-radius:10px;
            padding:12px;
            font-variant-ligatures:none;
            word-break:normal;
            overflow-wrap:anywhere;
            letter-spacing:normal;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# HTTP HELPERS
# ==============================================================================
def _session():
    s = requests.Session()
    s.mount(
        "https://",
        HTTPAdapter(
            max_retries=Retry(
                total=5,
                backoff_factor=0.7,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"],
                raise_on_status=False,
            )
        ),
    )
    return s


SESSION = _session()


def _get_json(url, params=None, timeout=25):
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _today_utc_date():
    return datetime.now(timezone.utc).date()


def _try_variants(symbol: str):
    sym = (symbol or "").strip().upper()
    seen = set()
    for s in [sym, sym.replace("-", "."), sym.replace(".", "-")]:
        if s not in seen:
            seen.add(s)
            yield s


def _batch_pause(i: int, batch_size: int = FMP_BATCH_SIZE, sleep_s: float = FMP_BATCH_SLEEP):
    if batch_size > 0 and i % batch_size == 0:
        time.sleep(max(0.0, sleep_s))


# ==============================================================================
# SCREENER
# ==============================================================================
SERVER_KEYS = {
    "country", "exchange", "sector", "industry", "isActivelyTrading",
    "marketCapMoreThan", "marketCapLowerThan",
    "priceMoreThan", "priceLowerThan",
    "volumeMoreThan", "volumeLowerThan",
    "betaMoreThan", "betaLowerThan",
    "dividendMoreThan", "dividendLowerThan",
    "limit", "page", "isEtf", "isFund"
}


def _sanitize_params(filters):
    p = {k: v for k, v in (filters or {}).items() if k in SERVER_KEYS and v not in (None, "", [])}
    for bkey in ["isActivelyTrading", "isEtf", "isFund"]:
        if bkey in p and isinstance(p[bkey], bool):
            p[bkey] = "true" if p[bkey] else "false"
    p["limit"] = max(1, min(int(p.get("limit", 500)), MAX_SERVER_LIMIT))
    return p


@st.cache_data(ttl=3600, show_spinner=False)
def fmp_company_screener_safe(filters, timeout=20, max_pages=10):
    url = "https://financialmodelingprep.com/stable/company-screener"
    params_base = _sanitize_params(filters) | {"apikey": FMP_API_KEY}

    all_rows = []
    meta = {"errors": [], "warnings": [], "pages": 0}

    for page in range(max_pages):
        try:
            r = SESSION.get(url, params={**params_base, "page": page}, timeout=timeout)
            if r.status_code == 429:
                time.sleep(1.0)
                continue
            if r.status_code != 200:
                meta["errors"].append({"page": page, "status": r.status_code})
                break

            data = r.json() or []
            if not data:
                break

            df = pd.DataFrame(data)
            if "symbol" in df.columns:
                df = df.rename(columns={"symbol": "ticker"})

            all_rows.append(df)
            meta["pages"] = page + 1

            if len(df) < params_base["limit"]:
                break

        except Exception as e:
            meta["warnings"].append({"page": page, "msg": repr(e)})
            break

    out = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()

    if "ticker" not in out.columns:
        out["ticker"] = pd.Series(dtype=str)

    if not out.empty:
        out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()

        for col in ["isEtf", "isFund"]:
            if col in out.columns:
                out = out[out[col].astype(str).str.lower().isin(["false", "0", "nan"])]

        out = out.drop_duplicates(subset=["ticker"]).reset_index(drop=True)

    if "marketCap" in out.columns:
        out["marketCap"] = pd.to_numeric(out["marketCap"], errors="coerce")
        out = out.sort_values("marketCap", ascending=False, na_position="last").reset_index(drop=True)

    return out, meta


# ==============================================================================
# PROFILE + METRICS
# ==============================================================================
def _safe_pct(num, den):
    num = pd.to_numeric(num, errors="coerce")
    den = pd.to_numeric(den, errors="coerce")
    return np.where((pd.notna(den)) & (den != 0), num / den, np.nan)


def _to_date_series(df, col):
    return (
        pd.to_datetime(df[col], errors="coerce", utc=True).dt.date
        if col in df.columns
        else pd.Series([pd.NaT] * len(df), index=df.index)
    )


def _latest_one_row(df, date_col=None):
    if df is None or df.empty:
        return df
    if date_col and date_col in df.columns:
        return df.sort_values(date_col).tail(1)
    return df.head(1)


def _coalesce_columns(df, mapping):
    df = df.copy()
    for canon, candidates in mapping.items():
        avail = [c for c in candidates if c in df.columns]
        if not avail:
            continue
        if canon not in df.columns:
            df[canon] = np.nan
        for c in avail:
            df[canon] = df[canon].combine_first(df[c])
        for c in avail:
            if c != canon and c in df.columns:
                df.drop(columns=[c], inplace=True, errors="ignore")
    return df


def _fetch_profile(sym):
    payload = None
    for v in _try_variants(sym):
        data = _get_json(
            f"https://financialmodelingprep.com/api/v3/profile/{v}",
            params={"apikey": FMP_API_KEY},
        )
        if isinstance(data, list) and data:
            payload = data[0]
            break

    if not payload:
        return pd.DataFrame(
            columns=[
                "symbol", "companyName", "sector", "industry", "description",
                "marketCap", "price_profile", "beta", "as_of_profile"
            ]
        )

    df = pd.DataFrame([payload])
    df["symbol"] = sym
    df["as_of_profile"] = _today_utc_date()

    keep = [
        "symbol", "companyName", "sector", "industry", "description",
        "marketCap", "price", "beta", "as_of_profile"
    ]
    df = df[[c for c in keep if c in df.columns]].copy()
    if "price" in df.columns:
        df = df.rename(columns={"price": "price_profile"})
    return df


def _fetch_quote(sym):
    payload = None
    for v in _try_variants(sym):
        data = _get_json(
            f"https://financialmodelingprep.com/api/v3/quote/{v}",
            params={"apikey": FMP_API_KEY},
        )
        if isinstance(data, list) and data:
            payload = data[0]
            break

    if not payload:
        return pd.DataFrame(
            columns=[
                "symbol", "as_of_quote", "yearHigh", "yearLow",
                "priceAvg50", "priceAvg200", "price", "volume"
            ]
        )

    df = pd.DataFrame([payload])
    df["symbol"] = sym
    df["as_of_quote"] = _today_utc_date()

    keep = ["symbol", "as_of_quote", "yearHigh", "yearLow", "priceAvg50", "priceAvg200", "price", "volume"]
    return df[[c for c in keep if c in df.columns]]


def _fetch_ratios_ttm(sym):
    payload = None
    for v in _try_variants(sym):
        data = _get_json(
            f"https://financialmodelingprep.com/api/v3/ratios-ttm/{v}",
            params={"apikey": FMP_API_KEY},
        )
        if isinstance(data, list) and data:
            payload = data
            break

    if not payload:
        return pd.DataFrame(columns=["symbol", "as_of_ratios"])

    df = pd.DataFrame(payload)
    df["symbol"] = sym
    df = _coalesce_columns(
        df,
        {
            "priceToSalesRatioTTM": ["priceToSalesRatioTTM", "priceSalesRatioTTM"],
            "debtToEquityRatioTTM": ["debtToEquityRatioTTM", "debtEquityRatioTTM"],
            "peRatioTTM": ["peRatioTTM"],
        },
    )
    df["as_of_ratios"] = _to_date_series(df, "date")
    df = _latest_one_row(df, "date")

    keep = [
        "symbol", "as_of_ratios",
        "priceToSalesRatioTTM", "priceEarningsToGrowthRatioTTM",
        "priceToFreeCashFlowsRatioTTM", "priceToBookRatioTTM",
        "debtToEquityRatioTTM", "returnOnEquityTTM", "returnOnAssetsTTM",
        "peRatioTTM", "currentRatioTTM",
        "operatingProfitMarginTTM", "netProfitMarginTTM"
    ]
    return df[[c for c in keep if c in df.columns]]


def _fetch_key_metrics_ttm(sym):
    payload = None
    for v in _try_variants(sym):
        data = _get_json(
            f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{v}",
            params={"apikey": FMP_API_KEY},
        )
        if isinstance(data, list) and data:
            payload = data
            break

    if not payload:
        return pd.DataFrame(columns=["symbol", "as_of_km"])

    df = pd.DataFrame(payload)
    df["symbol"] = sym
    df["as_of_km"] = _to_date_series(df, "date")
    df = _latest_one_row(df, "date")

    keep = ["symbol", "as_of_km", "dividendYieldTTM", "roicTTM", "debtToAssetsTTM", "evToSalesTTM"]
    return df[[c for c in keep if c in df.columns]]


def _fetch_rsi_latest_multi(symbols, period=21, interval="1day"):
    frames = []

    for i, s in enumerate(symbols, start=1):
        payload = None
        for v in _try_variants(s):
            data = _get_json(
                f"https://financialmodelingprep.com/api/v3/technical_indicator/{interval}/{v}",
                params={"type": "rsi", "period": period, "apikey": FMP_API_KEY},
            )
            if isinstance(data, list) and data:
                payload = data
                break

        if payload:
            df = pd.DataFrame(payload)
            df["symbol"] = s
            df["as_of_rsi"] = _to_date_series(df, "date")
            frames.append(df[["symbol", "as_of_rsi", "rsi"]])

        time.sleep(0.03)
        _batch_pause(i, batch_size=50)

    if not frames:
        return pd.DataFrame(columns=["symbol", "as_of_rsi", "RSI"])

    all_df = pd.concat(frames, ignore_index=True)
    latest = all_df.sort_values(["symbol", "as_of_rsi"]).groupby("symbol", as_index=False).tail(1)
    latest = latest.rename(columns={"rsi": "RSI"})
    return latest[["symbol", "as_of_rsi", "RSI"]]


def _merge_one_symbol(sym, blocks):
    prof = blocks["profile"].get(sym)
    quot = blocks["quote"].get(sym)
    ratio = blocks["ratios"].get(sym)
    km = blocks["km"].get(sym)
    rsi_all = blocks["rsi"]
    screener_map = blocks.get("screener_marketcap_map", {})

    rsi = rsi_all[rsi_all["symbol"] == sym] if rsi_all is not None and not rsi_all.empty else pd.DataFrame()

    parts = [p for p in [prof, quot, ratio, km] if p is not None and not p.empty]

    base = pd.DataFrame({"symbol": [sym]})
    for p in parts:
        base = base.merge(p, on="symbol", how="left")

    if rsi is not None and not rsi.empty:
        base = base.merge(rsi, on="symbol", how="left")

    required_numeric_cols = [
        "price", "price_profile", "yearHigh", "yearLow",
        "priceAvg50", "priceAvg200", "marketCap", "volume", "beta"
    ]
    for col in required_numeric_cols:
        if col not in base.columns:
            base[col] = np.nan

    base["screener_marketCap"] = pd.to_numeric(screener_map.get(sym, np.nan), errors="coerce")

    base["price"] = pd.to_numeric(base["price"], errors="coerce")
    base["price_profile"] = pd.to_numeric(base["price_profile"], errors="coerce")
    base["price"] = base["price"].combine_first(base["price_profile"])

    for col in ["yearHigh", "yearLow", "priceAvg50", "priceAvg200", "marketCap", "volume", "beta"]:
        base[col] = pd.to_numeric(base[col], errors="coerce")

    base["marketCap"] = base["marketCap"].combine_first(base["screener_marketCap"])

    base["pct_from_high"] = _safe_pct(base["price"] - base["yearHigh"], base["yearHigh"])
    base["pct_above_50ma"] = _safe_pct(base["price"] - base["priceAvg50"], base["priceAvg50"])
    base["pct_above_200ma"] = _safe_pct(base["price"] - base["priceAvg200"], base["priceAvg200"])

    pct_cols = [
        "pct_from_high", "pct_above_50ma", "pct_above_200ma",
        "dividendYieldTTM", "returnOnEquityTTM", "returnOnAssetsTTM",
        "roicTTM", "operatingProfitMarginTTM", "netProfitMarginTTM"
    ]
    for c in pct_cols:
        if c in base.columns:
            base[c] = pd.to_numeric(base[c], errors="coerce") * 100.0

    return base


def _pretty_rename(df):
    if df.empty:
        return df

    mapping = {
        "symbol": "Ticker",
        "companyName": "Company Name",
        "description": "Company Description",
        "sector": "Sector",
        "industry": "Industry",
        "marketCap": "Market Cap",
        "price": "Price",
        "volume": "Volume",
        "beta": "Beta",
        "yearHigh": "52W High",
        "yearLow": "52W Low",
        "priceAvg50": "50D MA",
        "priceAvg200": "200D MA",
        "RSI": "RSI",
        "pct_from_high": "% From 52W High",
        "pct_above_50ma": "% Above 50D MA",
        "pct_above_200ma": "% Above 200D MA",
        "dividendYieldTTM": "Dividend Yield (%)",
        "returnOnEquityTTM": "ROE (%)",
        "returnOnAssetsTTM": "ROA (%)",
        "roicTTM": "ROIC (%)",
        "operatingProfitMarginTTM": "Operating Margin (%)",
        "netProfitMarginTTM": "Net Margin (%)",
        "priceToSalesRatioTTM": "Price to Sales (TTM)",
        "priceToBookRatioTTM": "Price to Book (TTM)",
        "priceToFreeCashFlowsRatioTTM": "Price to FCF (TTM)",
        "priceEarningsToGrowthRatioTTM": "PEG (TTM)",
        "debtToEquityRatioTTM": "Debt to Equity (TTM)",
        "currentRatioTTM": "Current Ratio (TTM)",
        "peRatioTTM": "P/E (TTM)",
        "debtToAssetsTTM": "Debt to Assets (TTM)",
        "evToSalesTTM": "EV to Sales (TTM)",
    }
    return df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_all_metrics(symbols, screener_df, rsi_period=21):
    if not symbols:
        return pd.DataFrame(columns=["Ticker"])

    profile_blocks = {}
    quote_blocks = {}
    ratios_blocks = {}
    km_blocks = {}

    screener_marketcap_map = {}
    if screener_df is not None and not screener_df.empty:
        tmp = screener_df.copy()
        if "ticker" in tmp.columns:
            tmp["ticker"] = tmp["ticker"].astype(str).str.upper().str.strip()
        if "marketCap" in tmp.columns:
            tmp["marketCap"] = pd.to_numeric(tmp["marketCap"], errors="coerce")
            screener_marketcap_map = dict(zip(tmp["ticker"], tmp["marketCap"]))

    for i, s in enumerate(symbols, start=1):
        profile_blocks[s] = _fetch_profile(s)
        quote_blocks[s] = _fetch_quote(s)
        ratios_blocks[s] = _fetch_ratios_ttm(s)
        km_blocks[s] = _fetch_key_metrics_ttm(s)

        time.sleep(0.02)
        _batch_pause(i, batch_size=50)

    rsi_block = _fetch_rsi_latest_multi(symbols, period=rsi_period)
    blocks = {
        "profile": profile_blocks,
        "quote": quote_blocks,
        "ratios": ratios_blocks,
        "km": km_blocks,
        "rsi": rsi_block,
        "screener_marketcap_map": screener_marketcap_map,
    }

    rows = []
    for i, sym in enumerate(symbols, start=1):
        merged = _merge_one_symbol(sym, blocks)
        if merged is not None and not merged.empty:
            rows.append(merged)
        time.sleep(0.01)
        if i % 200 == 0:
            time.sleep(0.5)

    if not rows:
        return pd.DataFrame(columns=["Ticker"])

    df = pd.concat(rows, ignore_index=True)

    if "marketCap" in df.columns:
        df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce")
        df = df.sort_values("marketCap", ascending=False, na_position="last").reset_index(drop=True)

    df = _pretty_rename(df)

    if "Market Cap" in df.columns:
        df["Market Cap"] = pd.to_numeric(df["Market Cap"], errors="coerce")

    return df


# ==============================================================================
# FILTER HELPERS
# ==============================================================================
def apply_metric_filters(df, ignore_missing, filter_map):
    if df.empty:
        return df

    mask = np.ones(len(df), dtype=bool)

    for col, (lo, hi) in filter_map.items():
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        cond = (s >= lo) & (s <= hi)
        if ignore_missing:
            cond = cond | s.isna()
        mask &= cond.values

    return df.loc[mask].copy()


def format_output_df(df):
    out = df.copy()

    percent_cols = [
        "% From 52W High", "% Above 50D MA", "% Above 200D MA",
        "Dividend Yield (%)", "ROE (%)", "ROA (%)", "ROIC (%)",
        "Operating Margin (%)", "Net Margin (%)"
    ]
    money_cols = ["Price", "52W High", "52W Low", "50D MA", "200D MA"]
    integer_cols = ["Volume"]
    ratio_cols = [
        "Beta", "RSI", "Price to Sales (TTM)", "Price to Book (TTM)",
        "Price to FCF (TTM)", "PEG (TTM)", "Debt to Equity (TTM)",
        "Current Ratio (TTM)", "P/E (TTM)", "Debt to Assets (TTM)",
        "EV to Sales (TTM)"
    ]

    for c in percent_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").map(
                lambda x: f"{x:.1f}%" if pd.notna(x) else ""
            )

    for c in money_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").map(
                lambda x: f"${x:,.2f}" if pd.notna(x) else ""
            )

    for c in integer_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").map(
                lambda x: f"{int(x):,}" if pd.notna(x) else ""
            )

    if "Market Cap" in out.columns:
        out["Market Cap"] = pd.to_numeric(out["Market Cap"], errors="coerce").map(
            lambda x: f"${x / 1_000_000_000:,.1f}B" if pd.notna(x) else ""
        )

    for c in ratio_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").map(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            )

    return out


# ==============================================================================
# TAB RENDERER
# ==============================================================================
def render_stock_screener_tab(fmp_api_key: str) -> None:
    global FMP_API_KEY
    FMP_API_KEY = (fmp_api_key or "").strip()

    st.subheader("Stock Screener")
    st.caption("Rule-based FMP screener with optional post-screen metric enrichment. No LLM workflow is used on this page.")
    _render_screener_styles()

    if not FMP_API_KEY:
        st.error("Please enter your FMP API key in the sidebar first.")
        return

    with st.form("stock_screener_form"):
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        with r1c1:
            country = st.selectbox("Country", ["US"], index=0)
        with r1c2:
            exchange = st.selectbox("Exchange", ["Any", "NASDAQ", "NYSE", "AMEX"], index=0)
        with r1c3:
            sector = st.selectbox(
                "Sector",
                [
                    "Any", "Technology", "Energy", "Financial Services", "Industrials",
                    "Healthcare", "Utilities", "Materials", "Consumer Defensive",
                    "Consumer Cyclical", "Real Estate", "Communication Services"
                ],
                index=0,
            )
        with r1c4:
            industry_text = st.text_input("Industry contains", value="")

        with st.expander("Server-side range filters", expanded=True):
            wide_open = st.checkbox("Wide open server-side defaults", value=True)

            a1, a2, a3 = st.columns(3)
            with a1:
                cap_b_min, cap_b_max = st.slider("Market Cap Range ($B)", 0, 10000, (0, 10000), 1)
                if wide_open:
                    price_default = (0.0, 5000.0)
                else:
                    price_default = (0.0, 1000.0)
                price_min, price_max = st.slider("Price Range ($)", 0.0, 5000.0, price_default, 1.0)

            with a2:
                if wide_open:
                    volume_default = (0, 500_000_000)
                else:
                    volume_default = (0, 20_000_000)
                volume_min, volume_max = st.slider("Volume Range", 0, 500_000_000, volume_default, 100_000)
                beta_min, beta_max = st.slider("Beta Range", -5.0, 10.0, (-5.0, 10.0), 0.1)

            with a3:
                dividend_min, dividend_max = st.slider("Dividend Range", 0.0, 20.0, (0.0, 20.0), 0.1)
                limit = st.slider("Page size / API limit", 50, MAX_SERVER_LIMIT, 500, 50)
                max_pages_default = 10 if wide_open else 3
                max_pages = st.slider("Max pages to request", 1, MAX_SERVER_PAGES, max_pages_default, 1)

        with st.expander("Enrichment + final output controls", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                metrics_max_default = 1000 if wide_open else 200
                metrics_max = st.slider(
                    "Max tickers to enrich with metrics",
                    50,
                    MAX_ENRICH_TICKERS,
                    metrics_max_default,
                    50,
                )
            with c2:
                final_display_limit = st.slider(
                    "Final max companies to display",
                    25,
                    MAX_ENRICH_TICKERS,
                    min(metrics_max_default, 500),
                    25,
                )
            with c3:
                rsi_period = st.slider("RSI period", 7, 50, 21, 1)

        with st.expander("Post-screen metric filters", expanded=False):
            b0c1, b0c2 = st.columns(2)
            with b0c1:
                enable_metric_filters = st.checkbox("Enable post-screen metric filters", value=False)
            with b0c2:
                ignore_missing = st.checkbox("Ignore missing metric values", value=True)

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                pe_min, pe_max = st.slider("P/E (TTM)", -100.0, 800.0, (-100.0, 800.0))
                ps_min, ps_max = st.slider("Price to Sales (TTM)", 0.0, 800.0, (0.0, 800.0))
                pb_min, pb_max = st.slider("Price to Book (TTM)", -100.0, 800.0, (-100.0, 800.0))
                de_min, de_max = st.slider("Debt to Equity (TTM)", 0.0, 500.0, (0.0, 500.0))
            with b2:
                cr_min, cr_max = st.slider("Current Ratio (TTM)", 0.0, 100.0, (0.0, 100.0))
                rsi_min, rsi_max = st.slider("RSI", 0.0, 100.0, (0.0, 100.0))
                roe_min, roe_max = st.slider("ROE (%)", -50.0, 800.0, (-50.0, 800.0))
                roa_min, roa_max = st.slider("ROA (%)", -30.0, 500.0, (-30.0, 500.0))
            with b3:
                roic_min, roic_max = st.slider("ROIC (%)", -30.0, 800.0, (-30.0, 800.0))
                opm_min, opm_max = st.slider("Operating Margin (%)", -50.0, 100.0, (-50.0, 100.0))
                npm_min, npm_max = st.slider("Net Margin (%)", -50.0, 100.0, (-50.0, 100.0))
                divy_min, divy_max = st.slider("Dividend Yield (%)", 0.0, 100.0, (0.0, 100.0))
            with b4:
                from_high_min, from_high_max = st.slider("% From 52W High", -100.0, 100.0, (-100.0, 100.0))
                p50_min, p50_max = st.slider("% Above 50D MA", -100.0, 100.0, (-100.0, 100.0))
                p200_min, p200_max = st.slider("% Above 200D MA", -100.0, 100.0, (-100.0, 100.0))

        run_screener = st.form_submit_button("Run Screener", type="primary")

    if not run_screener:
        st.info("Set the screener filters, then click Run Screener.")
        return

    with st.spinner("Running FMP screener..."):
        filters = {
            "country": country,
            "isActivelyTrading": "true",
            "isEtf": "false",
            "isFund": "false",
            "marketCapMoreThan": int(cap_b_min) * 1_000_000_000,
            "marketCapLowerThan": int(cap_b_max) * 1_000_000_000,
            "priceMoreThan": float(price_min),
            "priceLowerThan": float(price_max),
            "volumeMoreThan": int(volume_min),
            "volumeLowerThan": int(volume_max),
            "betaMoreThan": float(beta_min),
            "betaLowerThan": float(beta_max),
            "dividendMoreThan": float(dividend_min),
            "dividendLowerThan": float(dividend_max),
            "limit": int(limit),
        }

        if exchange != "Any":
            filters["exchange"] = exchange
        if sector != "Any":
            filters["sector"] = sector

        screen_df, meta = fmp_company_screener_safe(filters=filters, max_pages=max_pages)

    if screen_df.empty:
        st.warning("No companies returned. Try widening the filters.")
        return

    if industry_text.strip() and "industry" in screen_df.columns:
        screen_df = screen_df[
            screen_df["industry"].fillna("").str.contains(industry_text.strip(), case=False, na=False)
        ].copy()

    if screen_df.empty:
        st.warning("No companies remain after the industry text filter.")
        return

    if "marketCap" in screen_df.columns:
        screen_df["marketCap"] = pd.to_numeric(screen_df["marketCap"], errors="coerce")
        screen_df = screen_df.sort_values("marketCap", ascending=False, na_position="last").reset_index(drop=True)

    all_screened_tickers = (
        screen_df["ticker"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
        .unique()
        .tolist()
    )

    tickers = all_screened_tickers[:metrics_max]

    st.success(
        f"Initial screener returned {len(screen_df):,} rows across {meta.get('pages', 0)} page(s). "
        f"Enriching up to {len(tickers):,} tickers."
    )

    if meta.get("errors"):
        st.caption(f"API errors encountered: {meta['errors']}")
    if meta.get("warnings"):
        st.caption(f"API warnings encountered: {meta['warnings']}")

    with st.spinner("Fetching company profiles and advanced metrics..."):
        metrics_df = fetch_all_metrics(tickers, screener_df=screen_df, rsi_period=rsi_period)

    if metrics_df.empty:
        st.warning("No enriched metric rows were returned.")
        return

    if enable_metric_filters:
        filter_map = {
            "P/E (TTM)": (pe_min, pe_max),
            "Price to Sales (TTM)": (ps_min, ps_max),
            "Price to Book (TTM)": (pb_min, pb_max),
            "Debt to Equity (TTM)": (de_min, de_max),
            "Current Ratio (TTM)": (cr_min, cr_max),
            "RSI": (rsi_min, rsi_max),
            "ROE (%)": (roe_min, roe_max),
            "ROA (%)": (roa_min, roa_max),
            "ROIC (%)": (roic_min, roic_max),
            "Operating Margin (%)": (opm_min, opm_max),
            "Net Margin (%)": (npm_min, npm_max),
            "Dividend Yield (%)": (divy_min, divy_max),
            "% From 52W High": (from_high_min, from_high_max),
            "% Above 50D MA": (p50_min, p50_max),
            "% Above 200D MA": (p200_min, p200_max),
        }
        metrics_df = apply_metric_filters(metrics_df, ignore_missing=ignore_missing, filter_map=filter_map)

    if metrics_df.empty:
        st.warning("No companies remain after applying the advanced metric filters.")
        return

    if "Market Cap" in metrics_df.columns:
        metrics_df["Market Cap"] = pd.to_numeric(metrics_df["Market Cap"], errors="coerce")
        metrics_df = metrics_df.sort_values("Market Cap", ascending=False, na_position="last").reset_index(drop=True)

    final_df = metrics_df.head(final_display_limit).copy()

    st.subheader("Final Screener Output")
    st.caption(
        f"Showing top {len(final_df):,} companies sorted by Market Cap descending "
        f"from {len(metrics_df):,} enriched rows."
    )

    display_cols = [
        "Ticker", "Company Name", "Sector", "Industry", "Market Cap", "Price", "Volume",
        "Beta", "P/E (TTM)", "Price to Sales (TTM)", "Price to Book (TTM)",
        "ROE (%)", "ROA (%)", "ROIC (%)", "Operating Margin (%)", "Net Margin (%)",
        "Dividend Yield (%)", "Debt to Equity (TTM)", "Current Ratio (TTM)",
        "RSI", "% From 52W High", "% Above 50D MA", "% Above 200D MA",
        "Company Description",
    ]
    display_cols = [c for c in display_cols if c in final_df.columns]

    formatted_df = format_output_df(final_df[display_cols])
    st.dataframe(formatted_df, use_container_width=True, height=520)

    st.download_button(
        "Download Results CSV",
        data=final_df.to_csv(index=False).encode("utf-8"),
        file_name="stock_screener_results.csv",
        mime="text/csv",
    )