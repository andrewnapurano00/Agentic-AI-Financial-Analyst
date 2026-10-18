"""FMP daily close/adjClose contract shared by Market Brief and charts."""
from datetime import datetime, timedelta, timezone
import re

import pandas as pd
import streamlit as st

from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.providers.fmp_http import get_fmp_json

BASE = "https://financialmodelingprep.com/api/v3/historical-price-full/"


def normalize_daily_prices(payload, symbol, now):
    """Keep missing prices as dated missing records, never older baselines."""
    if not isinstance(payload, dict) or payload.get("symbol") != symbol or not isinstance(payload.get("historical"), list):
        return [], ["FMP daily history has no matching security/history envelope."]
    records, duplicates, rejected = {}, set(), 0
    for row in payload["historical"]:
        if not isinstance(row, dict) or row.get("symbol", symbol) != symbol:
            rejected += 1
            continue
        date = row.get("date")
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            rejected += 1
            continue
        stamp = pd.to_datetime(date, errors="coerce")
        if pd.isna(stamp) or stamp.date() > pd.Timestamp(now).date():
            rejected += 1
            continue
        record = {"date": date}
        for source, target in (("close", "close"), ("adjClose", "adj_close")):
            value = finite_number(row.get(source))
            record[target] = value if value is not None and value > 0 else None
        if date in records:
            duplicates.add(date)
        records[date] = record
    for date in duplicates:
        records[date].update(close=None, adj_close=None)
    warnings = []
    if rejected or duplicates:
        warnings.append(f"Excluded {rejected} invalid/future-dated records; {len(duplicates)} ambiguous duplicate dates have unavailable prices.")
    return [records[date] for date in sorted(records)], warnings


@st.cache_data(ttl=300, show_spinner=False)
def load_fmp_daily_prices(symbol, api_key):
    symbol = str(symbol).strip().upper()
    if not re.fullmatch(r"\^?[A-Z0-9][A-Z0-9.\-]{0,14}", symbol):
        raise ValueError("Enter a valid security symbol.")
    now = datetime.now(timezone.utc)
    result = {"symbol": symbol, "records": [], "provider": "Financial Modeling Prep",
              "source": BASE + symbol, "retrieved_at": now.isoformat(), "warnings": []}
    if not api_key.strip():
        result["warnings"] = ["FMP configuration is required for daily adjusted prices."]
        return result
    try:
        payload = get_fmp_json(BASE + symbol, api_key=api_key,
                               params={"from": (now - timedelta(days=3653+800)).date().isoformat(),
                                       "to": now.date().isoformat()}, timeout=(5, 20))
        result["records"], result["warnings"] = normalize_daily_prices(payload, symbol, now)
    except Exception:
        # Provider exceptions can embed request URLs; keep them out of packets.
        result["warnings"] = ["FMP daily history request failed. Retry to recover; no other provider was substituted."]
    return result
