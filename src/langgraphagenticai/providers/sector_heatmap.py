"""Eleven FMP ETF histories plus one bounded batch of current quote prices."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from langgraphagenticai.analysis.sector_heatmap import SECTORS, sector_returns
from langgraphagenticai.providers.fmp_daily_prices import load_fmp_daily_prices
from langgraphagenticai.providers.fmp_http import get_fmp_json


@st.cache_data(ttl=300, show_spinner=False)
def load_sector_performance(fmp_api_key=""):
    now = datetime.now(timezone.utc)
    result = {"sectors": {}, "retrieved_at": now.isoformat(), "warnings": [],
              "provider": "Financial Modeling Prep",
              "basis": "Latest FMP price / prior trading day's adjClose - 1; percentage points"}
    quotes, histories = {}, {}
    if fmp_api_key.strip():
        try:
            rows = get_fmp_json("https://financialmodelingprep.com/api/v3/quote/" + ",".join(SECTORS.values()),
                                api_key=fmp_api_key, timeout=(5, 20))
            if not isinstance(rows, list):
                raise ValueError("No quote rows")
            for row in rows:
                if not isinstance(row, dict) or row.get("symbol") not in SECTORS.values():
                    continue
                stamp = pd.to_datetime(row.get("timestamp"), unit="s", utc=True, errors="coerce")
                quotes[row["symbol"]] = {"price": row.get("price"), "as_of": stamp.isoformat() if pd.notna(stamp) else None}
        except Exception:
            result["warnings"].append("FMP quotes unavailable; daily changes use the latest historical close when available.")
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(load_fmp_daily_prices, symbol, fmp_api_key): symbol for symbol in SECTORS.values()}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    packet = future.result()
                    histories[symbol] = packet.get("records", [])
                    result["warnings"].extend(f"{symbol}: {warning}" for warning in packet.get("warnings", []))
                except Exception:
                    result["warnings"].append(f"{symbol}: FMP history unavailable; other sectors remain usable.")
    else:
        result["warnings"].append("Configure FMP to load sector prices and previous trading day adjusted closes.")
    for name, symbol in SECTORS.items():
        result["sectors"][name] = sector_returns(histories.get(symbol, []), now, quotes.get(symbol))
        result["sectors"][name]["history_source"] = "https://financialmodelingprep.com/api/v3/historical-price-full/" + symbol
    return result


def clear_sector_price_cache():
    load_sector_performance.clear()
    load_fmp_daily_prices.clear()
