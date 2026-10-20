"""Small shared FMP evidence snapshot for all four paper accounts."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import streamlit as st

from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.paper_trading.safety import safe_text
from langgraphagenticai.paper_trading.engine import snapshot_id


@st.cache_data(ttl=300, max_entries=16, show_spinner=False)
def load_paper_market(universe, benchmark, api_key):
    universe = tuple(normalize_company_symbol(s) for s in universe)
    benchmark = normalize_company_symbol(benchmark)
    if not 1 <= len(universe) <= 8 or len(set(universe)) != len(universe) or not api_key.strip():
        raise ValueError("Configure FMP and one to eight unique symbols.")
    names = list(dict.fromkeys([*universe, benchmark]))
    base = "https://financialmodelingprep.com/stable/"
    warnings, facts = [], {}
    try:
        quotes = get_fmp_json(base+"batch-quote", api_key=api_key, params={"symbols": ",".join(names)}, timeout=(3, 10))
    except Exception:
        quotes = []
        warnings.append("Quote batch unavailable; refresh to retry.")
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {}
        for symbol in names:
            for kind, route in (("profile", "profile"), ("ratios", "ratios-ttm")):
                if kind == "ratios" and symbol not in universe:
                    continue
                jobs[pool.submit(get_fmp_json, base+route, api_key=api_key, params={"symbol": symbol}, timeout=(3, 10))] = (symbol, kind)
        for future in as_completed(jobs):
            symbol, kind = jobs[future]
            try:
                response = future.result()
                rows = [r for r in response if isinstance(r, dict) and r.get("symbol") == symbol] if isinstance(response, list) else []
                if len(rows) == 1:
                    facts[(symbol, kind)] = rows[0]
            except Exception:
                warnings.append(symbol+": "+kind+" unavailable.")
    now = datetime.now(timezone.utc)
    packet = dict(mode="FMP + AI", rows={}, retrieved_at=now.isoformat(), warnings=warnings, provider="FMP")
    seen = set()
    for row in quotes if isinstance(quotes, list) else []:
        if not isinstance(row, dict) or row.get("symbol") not in names:
            continue
        symbol = row["symbol"]
        if symbol in seen:
            packet["rows"].pop(symbol, None)
            warnings.append(symbol+": duplicate quote excluded.")
            continue
        seen.add(symbol)
        profile, ratios = facts.get((symbol, "profile"), {}), facts.get((symbol, "ratios"), {})
        price, stamp = finite_number(row.get("price")), finite_number(row.get("timestamp"))
        currencies = {c for c in (row.get("currency"), profile.get("currency")) if c}
        try:
            dated = datetime.fromtimestamp(stamp, timezone.utc)
            valid_date = 0 <= (now-dated).total_seconds() <= 7*86400
        except (ValueError, TypeError, OSError, OverflowError):
            valid_date = False
        if price is None or price <= 0 or currencies != {"USD"} or not valid_date:
            warnings.append(symbol+": valid dated USD quote/listing currency unavailable.")
            continue
        def safe(value, length=240):
            return safe_text(str(value or "").replace(api_key, "[REDACTED]"), max_length=length)
        packet["rows"][symbol] = dict(
            symbol=symbol, price=price, as_of=dated.isoformat(), currency="USD",
            currency_basis="quote reported" if row.get("currency") else "profile listing currency; quote units assumed compatible",
            company=safe(profile.get("companyName") or symbol), sector=safe(profile.get("sector") or "Unknown"),
            description=safe(profile.get("description"), 450),
            change_pct=finite_number(row.get("changePercentage", row.get("changesPercentage"))),
            sma50=finite_number(row.get("priceAvg50")), sma200=finite_number(row.get("priceAvg200")),
            pe_ttm=finite_number(ratios.get("priceToEarningsRatioTTM")),
            margin_ttm=finite_number(ratios.get("netProfitMarginTTM")),
            debt_equity_ttm=finite_number(ratios.get("debtToEquityRatioTTM")),
            ratio_basis="provider TTM; period end may be unavailable", provider="FMP",
        )
    packet["id"] = snapshot_id(packet)
    return packet
