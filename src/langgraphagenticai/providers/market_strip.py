"""Five index quotes, cached independently of research and model work."""
from datetime import datetime, timezone
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.discovery_numbers import finite_number

INDEXES = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "RUSSELL 2000": "^RUT", "VIX": "^VIX"}


def normalize_quotes(rows, *, now=None):
    now = now or datetime.now(timezone.utc)
    result = {}
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict) or row.get("symbol") not in INDEXES.values():
            continue
        symbol = row["symbol"]
        price = finite_number(row.get("price"))
        if price is None or price <= 0:
            continue
        stamp = finite_number(row.get("timestamp"))
        as_of = None
        if stamp is not None:
            try:
                instant = datetime.fromtimestamp(stamp, timezone.utc)
                if instant > now:
                    continue
                as_of = instant.isoformat()
            except (ValueError, OverflowError, OSError):
                continue
        percent = next((finite_number(row.get(key)) for key in ("changePercentage", "changesPercentage") if finite_number(row.get(key)) is not None), None)
        basis = "Provider daily percentage change"
        if percent is None:
            previous = finite_number(row.get("previousClose"))
            if previous is not None and previous > 0:
                percent = finite_number((price / previous - 1) * 100)
                basis = "Calculated (quote / previous close - 1) * 100"
        candidate = dict(symbol=symbol, price=price, percent=percent, as_of=as_of, provider="FMP", unit="index points", change_basis=basis if percent is not None else "Daily change unavailable")
        # Prefer the latest observation, never a different instrument or a stitched quote.
        current = result.get(symbol)
        if current is None or (as_of or "") > (current.get("as_of") or ""):
            result[symbol] = candidate
    return result


@st.cache_data(ttl=300, max_entries=16, show_spinner=False)
def load_market_strip(api_key):
    now = datetime.now(timezone.utc)
    packet = dict(rows={}, retrieved_at=now.isoformat(), status="unavailable")
    if not api_key.strip():
        packet["status"] = "unconfigured"
        return packet
    # Primary index endpoint; bounded legacy batch fallback for omitted symbols/entitlements.
    routes = [("https://financialmodelingprep.com/stable/batch-index-quotes", {}),
              ("https://financialmodelingprep.com/api/v3/quote/" + ",".join(INDEXES.values()), {})]
    for route, params in routes:
        try:
            response = get_fmp_json(route, api_key=api_key, params=params, timeout=(3, 8))
            retrieved = datetime.now(timezone.utc)
            packet["retrieved_at"] = retrieved.isoformat()
            rows = normalize_quotes(response, now=retrieved)
            for symbol, row in rows.items():
                if symbol not in packet["rows"]:
                    packet["rows"][symbol] = {**row, "retrieved_at": packet["retrieved_at"]}
            if len(packet["rows"]) == len(INDEXES):
                break
        except Exception:
            # Fixed structured state; provider/credential-bearing messages are never retained.
            continue
    packet["status"] = "available" if len(packet["rows"]) == len(INDEXES) else "partial" if packet["rows"] else "unavailable"
    return packet
