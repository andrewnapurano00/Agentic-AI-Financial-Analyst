"""Bounded legacy FMP social pagination; no model calls or key-bearing output."""
from datetime import datetime, timezone
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.analysis.social_sentiment import normalize_snapshots

ENDPOINT = "https://financialmodelingprep.com/api/v4/historical/social-sentiment"
MAX_PAGES = 10
MAX_RECORDS = 5000


@st.cache_data(ttl=900, max_entries=64, show_spinner=False)
def _collect(symbol, api_key, pages):
    now = datetime.now(timezone.utc)
    packet = {"symbol": symbol, "records": [], "provider": "Financial Modeling Prep",
              "retrieved_at": now.isoformat(), "warnings": [], "pages_requested": 0,
              "pages_received": 0, "pagination_end": "page_limit", "status": "unavailable"}
    packet["page_budget"] = pages
    rows, seen_pages = [], set()
    for page in range(pages):
        packet["pages_requested"] += 1
        try:
            payload = get_fmp_json(ENDPOINT, api_key=api_key, params={"symbol": symbol, "page": page}, timeout=(5, 20))
            if not isinstance(payload, list):
                raise ValueError("Invalid social response")
        except Exception:
            packet["warnings"].append("A social-sentiment page is unavailable. Check legacy endpoint access or refresh to retry; successful pages retained.")
            packet["pagination_end"] = "page_failure"
            break
        packet["pages_received"] += 1
        if not payload:
            packet["pagination_end"] = "empty_page"
            break
        # Repeat detection uses the full serialized page; repeated pages must not loop.
        import json
        from hashlib import sha256
        identity = sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        if identity in seen_pages:
            packet["pagination_end"] = "repeated_page"
            break
        seen_pages.add(identity)
        room = MAX_RECORDS - len(rows)
        rows.extend(payload[:room])
        if len(rows) >= MAX_RECORDS:
            packet["pagination_end"] = "record_limit"
            break
    packet["records"], packet["diagnostics"] = normalize_snapshots(rows, symbol, now)
    if packet["pagination_end"] != "empty_page":
        packet["warnings"].append("Pagination is bounded or incomplete; daily statistics cover returned observations only. Five complete days are not guaranteed.")
    if any(packet["diagnostics"].values()):
        packet["warnings"].append("Some rows/values were invalid, duplicated or conflicting. Conflicting timestamps are excluded; see diagnostics.")
    packet["status"] = "partial" if packet["warnings"] and packet["records"] else "available" if packet["records"] else "unavailable"
    return packet


def load_social_sentiment(symbol, api_key, pages=5, *, refresh=False):
    symbol = normalize_company_symbol(symbol)
    if not api_key.strip():
        raise ValueError("Configure FMP to load social sentiment.")
    if isinstance(pages, bool) or not isinstance(pages, int) or not 1 <= pages <= MAX_PAGES:
        raise ValueError("Social history must request 1–10 pages.")
    if refresh:
        _collect.clear(symbol, api_key, pages)
    return _collect(symbol, api_key, pages)
