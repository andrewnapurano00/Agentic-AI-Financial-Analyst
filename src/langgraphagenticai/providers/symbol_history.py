"""Single-provider chart history; range/settings changes reuse bounded cached data."""
from datetime import datetime, timedelta, timezone
import math
import re

import pandas as pd
import streamlit as st
import yfinance as yf

from .fmp_http import get_fmp_json

RANGES = {"1D": (1, "5m"), "5D": (5, "5m"), "1M": (31, "1d"), "3M": (93, "1d"),
          "1Y": (366, "1d"), "3Y": (1096, "1d"), "5Y": (1827, "1d"), "10Y": (3653, "1d")}
MAX_WARMUP_BARS = 500


def _utc_now():
    return datetime.now(timezone.utc)


def normalize_history(rows, symbol):
    """Exclude future observations before window selection or indicator warmup.

    Aware timestamps are compared as exact instants against the actual UTC clock.
    For unknown-zone naive timestamps, compare calendar dates to the current UTC
    date only: accept today's wall-clock fields, reject later dates, and never
    invent a source timezone. Same-day intraday future-ness is unverifiable for
    naive records and is deliberately not inferred.
    """
    cutoff = pd.Timestamp(_utc_now())
    valid, rejected = [], 0
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("symbol", symbol) != symbol:
            rejected += 1
            continue
        try:
            if not isinstance(row.get("date"), (str, datetime, pd.Timestamp)):
                raise ValueError()
            stamp, value = pd.Timestamp(row.get("date")), float(row.get("close"))
            if pd.isna(stamp) or isinstance(row.get("close"), bool) or not math.isfinite(value) or value <= 0:
                raise ValueError()
            if (stamp.tz is not None and stamp.tz_convert("UTC") > cutoff) or (stamp.tz is None and stamp.date() > cutoff.date()):
                raise ValueError()
            valid.append((stamp, value))
        except (ValueError, TypeError, OverflowError):
            rejected += 1
    if len({str(stamp.tz) for stamp, _ in valid}) > 1:
        return [], rejected + len(valid)
    prices, conflicts = {}, set()
    for stamp, value in valid:
        if stamp in prices and prices[stamp] != value:
            conflicts.add(stamp)
        prices[stamp] = value
    return sorted((stamp, value) for stamp, value in prices.items() if stamp not in conflicts), rejected + len(conflicts)


def _fetch_history(symbol, api_key, intraday):
    now = _utc_now()
    # One adapter call (shared transport retries are bounded), then at most one
    # whole-series Yahoo fallback. 30 intraday days or ten years + warmup.
    start = (now - timedelta(days=30 if intraday else 3653 + 800)).date().isoformat()
    points, warnings, rejected = [], [], 0
    provider, basis, source = "Unavailable", "Unknown", ""
    if api_key.strip():
        source = "https://financialmodelingprep.com/stable/" + ("historical-chart/5min" if intraday else "historical-price-eod/full")
        try:
            raw = get_fmp_json(source, api_key=api_key, params={"symbol": symbol, "from": start,
                               "to": now.date().isoformat()}, timeout=(5, 20))
            rows = raw if isinstance(raw, list) else raw.get("historical", []) if isinstance(raw, dict) else []
            points, rejected = normalize_history(rows, symbol)
            if points:
                provider, basis = "Financial Modeling Prep", "Close; adjustment unverified"
            else:
                warnings.append("FMP history had no usable prices; using a separate Yahoo Finance series.")
        except Exception:
            warnings.append("FMP history request failed; using a separate Yahoo Finance series.")
    if not points:
        try:
            raw = yf.download(symbol, start=start, end=(now.date() + timedelta(days=1)).isoformat(),
                              interval="5m" if intraday else "1d", auto_adjust=True,
                              progress=False, threads=False, timeout=15)
            if not raw.empty and "Close" in raw:
                close = raw["Close"]
                if isinstance(close, pd.DataFrame):
                    if symbol not in close.columns:
                        raise ValueError("Requested security is missing.")
                    close = close[symbol]
                points, fallback_rejected = normalize_history([{"date": stamp, "close": value}
                                                               for stamp, value in close.items()], symbol)
                rejected += fallback_rejected
            provider, basis, source = "Yahoo Finance", "Yahoo auto-adjusted close", "Yahoo download"
            if not points:
                warnings.append("Yahoo Finance returned no usable historical prices.")
                provider = "Unavailable"
        except Exception:
            warnings.append("Yahoo Finance history request failed. Retry the chart to recover.")
    if rejected:
        warnings.append(f"Excluded {rejected} invalid, future-dated or conflicting price records.")
    return {"history": points, "provider": provider, "price_basis": basis, "source": source,
            "retrieved_at": now.isoformat(timespec="seconds"), "warnings": warnings,
            "interval": "5m" if intraday else "1d", "symbol": symbol}


@st.cache_data(ttl=300, show_spinner=False)
def _intraday_history(symbol, api_key):
    return _fetch_history(symbol, api_key, True)


@st.cache_data(ttl=3600, show_spinner=False)
def _daily_history(symbol, api_key):
    return _fetch_history(symbol, api_key, False)


def select_history(history, period):
    if period not in RANGES:
        raise ValueError("Unsupported chart range.")
    if not history:
        return [], [], False
    end = history[-1][0]
    if period in {"1D", "5D"}:
        sessions = sorted({stamp.date() for stamp, _ in history})
        count = 1 if period == "1D" else 5
        allowed = set(sessions[-count:])
        visible = [point for point in history if point[0].date() in allowed]
        partial = len(sessions) < count
    else:
        start = end - pd.Timedelta(days=RANGES[period][0])
        visible = [point for point in history if point[0] >= start]
        partial = history[0][0] > start + pd.Timedelta(days=7)
    if not visible:
        return [], [], True
    before = [point for point in history if point[0] < visible[0][0]][-MAX_WARMUP_BARS:]
    return visible, before + visible, partial


def load_symbol_history(symbol, api_key="", period="1Y", currency=""):
    symbol = str(symbol).strip().upper()
    if not re.fullmatch(r"\^?[A-Z0-9][A-Z0-9.\-]{0,14}", symbol):
        raise ValueError("Enter a valid security symbol.")
    if period not in RANGES:
        raise ValueError("Unsupported chart range.")
    raw = (_intraday_history if period in {"1D", "5D"} else _daily_history)(symbol, api_key)
    points, calculation_points, partial = select_history(raw["history"], period)
    result = {key: value for key, value in raw.items() if key != "history"}
    result.update(points=points, calculation_points=calculation_points, period=period,
                  currency=currency or "Unknown", unit="Index points" if symbol == "^GSPC" else (currency or "Currency unknown"),
                  timezone=str(points[-1][0].tz) if points and points[-1][0].tz else "Unknown (naive provider timestamps)",
                  as_of=points[-1][0].isoformat() if points else "Unavailable", partial=partial,
                  history_start=points[0][0].isoformat() if points else "Unavailable", observations=len(points))
    result["warnings"] = list(result["warnings"])
    if partial:
        result["warnings"].append("Partial coverage: returned history does not span this range; missing bars are not filled.")
    result["stale"] = bool(points and (datetime.now(timezone.utc).date() - points[-1][0].date()).days > 4)
    if result["stale"]:
        result["warnings"].append("History is stale: latest observed session is over four calendar days old.")
    return result


def clear_history_cache():
    _daily_history.clear()
    _intraday_history.clear()
