"""Bounded, source-labelled chart retrieval, independent of narrative generation."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import yfinance as yf

from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.utils.safety import sanitize_error

RANGES = {"1D": (1, "5m"), "5D": (5, "30m"), "1M": (31, "1d"), "3M": (93, "1d"), "1Y": (366, "1d")}


@st.cache_data(ttl=300, show_spinner=False)
def load_market_chart(api_key: str = "", period: str = "1D") -> dict:
    if period not in RANGES:
        raise ValueError("Unsupported chart range.")
    days, interval = RANGES[period]
    warnings = []
    if api_key.strip():
        try:
            intraday = interval != "1d"
            endpoint = "historical-chart/" + ("5min" if period == "1D" else "30min") if intraday else "historical-price-full"
            payload = get_fmp_json(
                f"https://financialmodelingprep.com/api/v3/{endpoint}/%5EGSPC",
                api_key=api_key,
                params={"from": (datetime.now(timezone.utc) - timedelta(days=days + 7)).date().isoformat()},
            )
            rows = payload if isinstance(payload, list) else payload.get("historical", [])
            frame = pd.DataFrame(rows)
            if not frame.empty and {"date", "close"}.issubset(frame.columns):
                frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
                frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
                frame = frame.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
                if not frame.empty:
                    end = frame["date"].max()
                    frame = frame[frame["date"].dt.date == end.date()] if period == "1D" else frame[frame["date"] >= end - timedelta(days=days)]
                    if len(frame) >= 2:
                        return {"points": list(frame[["date", "close"]].itertuples(index=False, name=None)), "provider": "Financial Modeling Prep", "warnings": warnings}
            warnings.append("FMP chart coverage unavailable; showing a separate Yahoo Finance series.")
        except Exception as exc:
            warnings.append(f"FMP chart unavailable: {sanitize_error(exc)}. Showing Yahoo Finance fallback.")
    raw = yf.download("^GSPC", period={"1D": "1d", "5D": "5d", "1M": "1mo", "3M": "3mo", "1Y": "1y"}[period], interval=interval, auto_adjust=True, progress=False, threads=False, timeout=15)
    points = []
    if not raw.empty and "Close" in raw:
        close = raw["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        points = list(pd.to_numeric(close, errors="coerce").dropna().items())
    return {"points": points, "provider": "Yahoo Finance", "warnings": warnings}
