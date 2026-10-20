"""Bounded historical closes; current company facts never enter replay packets."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.paper_trading.engine import finite


@st.cache_data(ttl=21600, max_entries=12, show_spinner=False)
def load_paper_history(universe, benchmark, start, end, api_key):
    names = list(dict.fromkeys([normalize_company_symbol(s) for s in universe] + [normalize_company_symbol(benchmark)]))
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if not 1 <= len(names) <= 9 or not 1 <= (last-first).days <= 366 or last >= date.today() or not api_key.strip():
        raise ValueError("Choose a completed historical period of up to one year and configure FMP.")
    lower = (first-timedelta(days=120)).isoformat()
    def fetch(symbol):
        try:
            raw = get_fmp_json("https://financialmodelingprep.com/stable/historical-price-eod/full", api_key=api_key,
                               params={"symbol": symbol, "from": lower, "to": end}, timeout=(3, 15))
            # Used solely as a currency eligibility check; never sent to agents.
            profile = get_fmp_json("https://financialmodelingprep.com/stable/profile", api_key=api_key,
                                   params={"symbol": symbol}, timeout=(3, 10))
            profiles = [r for r in profile if isinstance(r, dict) and r.get("symbol") == symbol] if isinstance(profile, list) else []
            if len(profiles) != 1 or profiles[0].get("currency") != "USD":
                raise ValueError("USD listing currency unavailable")
            rows = raw if isinstance(raw, list) else raw.get("historical", []) if isinstance(raw, dict) and raw.get("symbol", symbol) == symbol else []
            prices, duplicates = {}, set()
            for row in rows:
                try:
                    if not isinstance(row, dict) or row.get("symbol", symbol) != symbol:
                        continue
                    day = date.fromisoformat(row["date"]).isoformat()
                    price = finite(row["close"])
                    if not lower <= day <= end or price <= 0 or row.get("currency", "USD") != "USD":
                        continue
                    if day in prices:
                        duplicates.add(day)
                    prices[day] = price
                except (ValueError, TypeError, KeyError):
                    continue
            return symbol, {d:p for d,p in sorted(prices.items()) if d not in duplicates}
        except Exception:
            return symbol, {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        series = dict(pool.map(fetch, names))
    return dict(series=series, retrieved_at=datetime.now(timezone.utc).isoformat(), provider="FMP",
                basis="Split-adjusted close; price return, no cash dividends. Retrospective revisions possible.",
                currency="USD", currency_basis="Current USD listing check; historical quote-unit compatibility assumed.",
                warnings=[s+": historical coverage unavailable" for s,p in series.items() if not p])
