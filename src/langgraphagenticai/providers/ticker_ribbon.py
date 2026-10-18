"""Cached S&P membership and bounded batch quote collection."""
from datetime import datetime, timezone
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.state.research_context import normalize_company_symbol


@st.cache_data(ttl=86400, show_spinner=False)
def load_members(api_key):
    rows = get_fmp_json("https://financialmodelingprep.com/api/v3/sp500_constituent", api_key=api_key)
    if not isinstance(rows, list):
        raise ValueError("S&P membership unavailable")
    symbols = set()
    for row in rows:
        try:
            symbol = normalize_company_symbol(row.get("symbol", "")) if isinstance(row, dict) else ""
            if symbol:
                symbols.add(symbol)
        except ValueError:
            continue
    return sorted(symbols)[:550]


@st.cache_data(ttl=300, show_spinner=False)
def load_ribbon(api_key):
    packet = {"rows": [], "warnings": [], "retrieved_at": datetime.now(timezone.utc).isoformat(), "requested": 0}
    if not api_key.strip():
        return packet
    try:
        symbols = load_members(api_key)
    except Exception:
        packet["warnings"].append("S&P 500 membership unavailable. Refresh market evidence to retry.")
        return packet
    packet["requested"] = len(symbols)
    for start in range(0, len(symbols), 100):
        batch = symbols[start:start + 100]
        try:
            rows = get_fmp_json("https://financialmodelingprep.com/api/v3/quote/" + ",".join(batch), api_key=api_key)
            if not isinstance(rows, list):
                raise ValueError("Invalid quotes")
            seen = set()
            for row in rows:
                if not isinstance(row, dict) or row.get("symbol") not in batch or row["symbol"] in seen:
                    continue
                seen.add(row["symbol"])
                price, change = finite_number(row.get("price")), finite_number(row.get("changesPercentage"))
                stamp = finite_number(row.get("timestamp"))
                as_of = None
                if stamp is not None:
                    try:
                        instant = datetime.fromtimestamp(stamp, timezone.utc)
                        if instant <= datetime.now(timezone.utc):
                            as_of = instant.isoformat()
                    except (ValueError, OverflowError, OSError):
                        pass
                if price is not None and price > 0:
                    packet["rows"].append({"symbol": row["symbol"], "price": price, "change": change, "as_of": as_of})
        except Exception:
            packet["warnings"].append("A batch of constituent quotes is unavailable; successful quotes retained.")
    packet["rows"].sort(key=lambda row: row["symbol"])
    return packet
