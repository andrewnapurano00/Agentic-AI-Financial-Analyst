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
# FMP uses its own commodity/crypto symbols, not Yahoo futures aliases.
FMP_ALIASES = {"GC=F": "GCUSD", "CL=F": "CLUSD", "BTC-USD": "BTCUSD", "DX-Y.NYB": "DXUSD"}
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
    url_symbols = ",".join(sorted({FMP_ALIASES.get(symbol, symbol) for symbol in symbols}))
    reverse_aliases = {value: key for key, value in FMP_ALIASES.items()}
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
        symbol = reverse_aliases.get(symbol, symbol)
        price = row.get("price")
        if not symbol or price is None:
            continue
        change = float(row.get("change") or 0.0)
        percent = row.get("changesPercentage")
        if percent is None:
            previous = float(row.get("previousClose") or 0.0)
            percent = change / previous * 100.0 if previous else 0.0
        snapshots[symbol] = {"price": float(price), "change": change, "percent": float(percent),
                             "as_of": str(pd.to_datetime(row.get("timestamp"), unit="s", utc=True, errors="coerce"))}

    warnings: list[str] = []
    for snap in snapshots.values():
        snap["provider"] = "Financial Modeling Prep"
    missing = [symbol for symbol in symbols if symbol not in snapshots]
    if missing:
        try:
            fallback_raw = yf.download(tickers=sorted(set(missing)), period="5d", interval="1d", auto_adjust=True, progress=False, group_by="column", threads=False, timeout=15)
            fallback_prices = _close_frame(fallback_raw)
            if len(set(missing)) == 1 and list(fallback_prices.columns) == ["Close"]:
                fallback_prices.columns = missing
            for symbol, snap in _snapshots(fallback_prices).items():
                snap["provider"] = "Yahoo Finance (daily close fallback)"
                snap["as_of"] = str(fallback_prices[symbol].dropna().index[-1])
                snapshots[symbol] = snap
            warnings.append("Missing FMP quotes use labelled Yahoo Finance daily closes; these may differ from live quotes.")
        except Exception as exc:
            warnings.append(f"Missing-quote fallback unavailable: {sanitize_error(exc)}")
    unavailable = sorted(set(symbols) - snapshots.keys())
    if unavailable:
        warnings.append("No quote coverage for: " + ", ".join(unavailable))
    market_stamp = pd.to_datetime(rows[0].get("timestamp"), unit="s", utc=True, errors="coerce")
    if pd.isna(market_stamp):
        market_stamp = datetime.now(timezone.utc)
    chart = []  # Historical chart is loaded separately for the selected range.
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
    warnings = []
    if fmp_api_key.strip():
        try:
            return _load_fmp_market_overview(fmp_api_key.strip())
        except Exception as exc:
            warnings.append(f"FMP overview unavailable: {sanitize_error(exc)}. Showing Yahoo Finance daily closes.")
    symbols = list(INDEXES.values()) + list(SECTORS.values()) + list(CROSS_ASSETS.values()) + MOVER_UNIVERSE
    raw = yf.download(
        tickers=sorted(set(symbols)), period="5d", interval="1d", auto_adjust=True,
        progress=False, group_by="column", threads=False, timeout=15,
    )
    prices = _close_frame(raw)
    snapshots = _snapshots(prices)
    for symbol, snap in snapshots.items():
        snap["provider"] = "Yahoo Finance (daily close)"
        snap["as_of"] = str(prices[symbol].dropna().index[-1])

    fallback = pd.to_numeric(prices.get("^GSPC", pd.Series(dtype=float)), errors="coerce").dropna()
    chart = []
    market_stamp = fallback.index[-1] if not fallback.empty else datetime.now(timezone.utc)
    missing = sorted(set(symbols) - snapshots.keys())
    if missing:
        warnings.append("No quote coverage for: " + ", ".join(missing))

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
        "provider": "Yahoo Finance (daily closes)", "warnings": warnings,
    }
