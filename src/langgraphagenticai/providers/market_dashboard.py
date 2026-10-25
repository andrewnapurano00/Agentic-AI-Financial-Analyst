"""Bounded cached market dashboard collection; no model calls."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from langgraphagenticai.analysis.sector_heatmap import SECTORS
from langgraphagenticai.analysis.market_dashboard import dashboard_metrics
from langgraphagenticai.providers.fmp_daily_prices import load_fmp_daily_prices
from langgraphagenticai.providers.fmp_http import get_fmp_json

MACROS = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow": "^DJI", "Russell 2000": "^RUT", "VIX": "^VIX",
          "US 10Y yield index": "^TNX", "Gold": "GCUSD", "Oil": "CLUSD", "Bitcoin": "BTCUSD",
          "US Dollar": "DXUSD", "Long Treasuries": "TLT", "Small Caps ETF": "IWM"}


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard(api_key):
    now = datetime.now(timezone.utc)
    instruments = {**MACROS, **SECTORS}
    packet = {"rows": [], "sectors": {}, "warnings": [], "retrieved_at": now.isoformat(),
              "provider": "Financial Modeling Prep", "basis": "Latest dated price / explicit historical adjClose; daily technicals use adjusted closes"}
    histories, quotes = {}, {}
    if api_key.strip():
        try:
            rows = get_fmp_json("https://financialmodelingprep.com/api/v3/quote/"+",".join(instruments.values()), api_key=api_key, timeout=(5,20))
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict) or row.get("symbol") not in instruments.values():
                    continue
                stamp = pd.to_datetime(row.get("timestamp"), unit="s", utc=True, errors="coerce")
                quotes[row["symbol"]] = {"price": row.get("price"), "as_of": stamp.isoformat() if pd.notna(stamp) else None}
        except Exception:
            packet["warnings"].append("Current quotes unavailable; using dated historical closes where available.")
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(load_fmp_daily_prices, symbol, api_key): symbol for symbol in instruments.values()}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    data = future.result()
                    histories[symbol] = data.get("records", [])
                    packet["warnings"].extend(symbol+": "+s for s in data.get("warnings", []))
                except Exception:
                    packet["warnings"].append(symbol+": history unavailable; other instruments preserved.")
    else:
        packet["warnings"].append("Configure FMP to load macro and sector daily evidence.")
    for name, symbol in instruments.items():
        record = dashboard_metrics(histories.get(symbol, []), now, quotes.get(symbol),
                                   quote_timezone="UTC" if symbol == "BTCUSD" else "America/New_York")
        packet["rows"].append({"Instrument": name, "Ticker": symbol, "Group": "Sector" if name in SECTORS else "Macro",
            "Level": record.get("price"), "1D %": record.get("day"), "5D %": record.get("week"), "30D %": record.get("30D"),
            "60D %": record.get("60D"), "1M %": record.get("1M"), "3M %": record.get("3M"), "YTD %": record.get("ytd"),
            **{key: value for key, value in record.items() if key.startswith("vs SMA") or key == "RSI (14)"}, "evidence": record})
        if name in SECTORS:
            packet["sectors"][name] = record
    return packet
