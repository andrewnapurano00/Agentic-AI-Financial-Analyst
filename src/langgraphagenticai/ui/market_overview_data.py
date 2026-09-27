from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf

from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.utils.safety import sanitize_error

try:
    # Use the Windows certificate store. This is important on managed machines
    # whose trusted proxy/root certificate is not bundled by certifi.
    import truststore

    truststore.inject_into_ssl()
except (ImportError, NotImplementedError):
    pass


INDEXES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
    "RUSSELL 2000": "^RUT",
    "VIX": "^VIX",
}
SECTORS = {
    "Technology": "XLK", "Communication": "XLC", "Cons. Cyclical": "XLY",
    "Financials": "XLF", "Industrials": "XLI", "Healthcare": "XLV",
    "Cons. Staples": "XLP", "Energy": "XLE", "Utilities": "XLU",
    "Real Estate": "XLRE", "Materials": "XLB",
}
CROSS_ASSETS = {
    "US 10Y": "^TNX", "Gold": "GC=F", "Oil": "CL=F", "Bitcoin": "BTC-USD",
    "US Dollar": "DX-Y.NYB", "Long Treasuries": "TLT", "Small Caps": "IWM",
}
MOVER_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "LLY", "AVGO"]


def _close_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            out = raw["Close"].copy()
        elif "Close" in raw.columns.get_level_values(-1):
            out = raw.xs("Close", axis=1, level=-1).copy()
        else:
            return pd.DataFrame()
    elif "Close" in raw.columns:
        out = raw[["Close"]].copy()
    else:
        return pd.DataFrame()
    if isinstance(out, pd.Series):
        out = out.to_frame()
    return out.dropna(how="all")


def _snapshots(prices: pd.DataFrame) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for symbol in prices.columns:
        values = pd.to_numeric(prices[symbol], errors="coerce").dropna()
        if values.empty:
            continue
        last = float(values.iloc[-1])
        previous = float(values.iloc[-2]) if len(values) > 1 else last
        change = last - previous
        result[str(symbol)] = {
            "price": last,
            "change": change,
            "percent": (change / previous * 100.0) if previous else 0.0,
        }
    return result


def _load_fmp_market_overview(api_key: str) -> dict[str, Any]:
    symbols = list(INDEXES.values()) + list(SECTORS.values()) + list(CROSS_ASSETS.values()) + MOVER_UNIVERSE
    url_symbols = ",".join(sorted(set(symbols)))
    rows = get_fmp_json(
        f"https://financialmodelingprep.com/api/v3/quote/{url_symbols}",
        api_key=api_key,
        timeout=(5, 25),
    )
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("FMP returned no quote rows.")
    snapshots = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        price = row.get("price")
        if not symbol or price is None:
            continue
        change = float(row.get("change") or 0.0)
        percent = row.get("changesPercentage")
        if percent is None:
            previous = float(row.get("previousClose") or 0.0)
            percent = change / previous * 100.0 if previous else 0.0
        snapshots[symbol] = {"price": float(price), "change": change, "percent": float(percent)}

    warnings: list[str] = []
    try:
        chart_rows = get_fmp_json(
            "https://financialmodelingprep.com/api/v3/historical-chart/5min/%5EGSPC",
            api_key=api_key,
            timeout=(5, 25),
        )
    except Exception as exc:
        chart_rows = []
        warnings.append(f"Intraday S&P 500 chart unavailable: {sanitize_error(exc)}")
    latest_date = str(rows[0].get("timestamp") or "")
    chart: list[tuple[object, float]] = []
    if isinstance(chart_rows, list) and chart_rows:
        newest_day = str(chart_rows[0].get("date", ""))[:10]
        day_rows = [row for row in chart_rows if str(row.get("date", ""))[:10] == newest_day]
        for row in reversed(day_rows):
            if row.get("close") is not None:
                chart.append((row.get("date"), float(row["close"])))
        latest_date = day_rows[0].get("date") if day_rows else latest_date
    market_stamp = pd.to_datetime(latest_date, unit="s", utc=True) if str(latest_date).isdigit() else pd.to_datetime(latest_date, utc=True)
    movers = sorted(
        ((symbol, snapshots[symbol]) for symbol in MOVER_UNIVERSE if symbol in snapshots),
        key=lambda row: abs(row[1]["percent"]), reverse=True,
    )[:5]
    return {
        "indexes": {label: snapshots.get(symbol) for label, symbol in INDEXES.items()},
        "sectors": {label: snapshots.get(symbol) for label, symbol in SECTORS.items()},
        "cross_assets": {label: snapshots.get(symbol) for label, symbol in CROSS_ASSETS.items()},
        "movers": movers, "chart": chart, "as_of": market_stamp,
        "fetched_at": datetime.now(timezone.utc), "provider": "Financial Modeling Prep",
        "warnings": warnings,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_market_overview(fmp_api_key: str = "") -> dict[str, Any]:
    if fmp_api_key.strip():
        return _load_fmp_market_overview(fmp_api_key.strip())
    symbols = list(INDEXES.values()) + list(SECTORS.values()) + list(CROSS_ASSETS.values()) + MOVER_UNIVERSE
    raw = yf.download(
        tickers=sorted(set(symbols)), period="5d", interval="1d", auto_adjust=True,
        progress=False, group_by="column", threads=True,
    )
    prices = _close_frame(raw)
    snapshots = _snapshots(prices)

    intraday_raw = yf.download(
        tickers="^GSPC", period="1d", interval="5m", auto_adjust=True,
        progress=False, group_by="column", threads=False,
    )
    intraday = _close_frame(intraday_raw)
    if not intraday.empty:
        series = pd.to_numeric(intraday.iloc[:, 0], errors="coerce").dropna()
        chart = [(stamp, float(value)) for stamp, value in series.items()]
        market_stamp = series.index[-1]
    else:
        fallback = pd.to_numeric(prices.get("^GSPC", pd.Series(dtype=float)), errors="coerce").dropna()
        chart = [(stamp, float(value)) for stamp, value in fallback.items()]
        market_stamp = fallback.index[-1] if not fallback.empty else datetime.now(timezone.utc)

    movers = sorted(
        ((symbol, snapshots[symbol]) for symbol in MOVER_UNIVERSE if symbol in snapshots),
        key=lambda row: abs(row[1]["percent"]), reverse=True,
    )[:5]
    return {
        "indexes": {label: snapshots.get(symbol) for label, symbol in INDEXES.items()},
        "sectors": {label: snapshots.get(symbol) for label, symbol in SECTORS.items()},
        "cross_assets": {label: snapshots.get(symbol) for label, symbol in CROSS_ASSETS.items()},
        "movers": movers,
        "chart": chart,
        "as_of": market_stamp,
        "fetched_at": datetime.now(timezone.utc),
        "provider": "Yahoo Finance", "warnings": [],
    }
