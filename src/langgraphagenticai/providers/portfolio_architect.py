"""Credential-scoped bounded collection. No model calls or execution dependencies."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.utils.safety import redact_sensitive_text
from langgraphagenticai.portfolio_architect.schemas import EvidenceSnapshot, Fact, SecurityEvidence
from langgraphagenticai.portfolio_architect.universe import UNIVERSE, ETFS, UNIVERSE_VERSION

BASE = "https://financialmodelingprep.com/stable/"
HISTORY_BASIS = "FMP daily close; adjustment basis unverified. Price-return diagnostics, excludes dividend cash flows; corporate actions may distort returns."


def clean(value, key="", limit=200):
    text = str(value or "")
    if key:
        text = text.replace(key, "[REDACTED]")
    return redact_sensitive_text(text)[:limit]


def rows(value, symbol=None):
    if isinstance(value, dict):
        if value.get("symbol", symbol) != symbol:
            return []
        value = value.get("historical", [])
    return [r for r in value if isinstance(r, dict) and (not symbol or r.get("symbol", symbol) == symbol)] if isinstance(value, list) else []


def one(value, symbol):
    matches = [r for r in rows(value) if r.get("symbol") == symbol]
    return matches[0] if len(matches) == 1 else {}


def failure_note(error):
    """Stable diagnostics only; never retain raw exception URLs or key values."""
    status = getattr(error, "status_code", None)
    if status in (402, 403):
        return f"HTTP {status}: endpoint access unavailable for the configured FMP plan."
    if status == 401:
        return "HTTP 401: FMP authentication failed; check the configured key."
    if status == 429:
        return "HTTP 429: FMP rate limit reached; wait before an explicit refresh."
    cause = error
    for _ in range(5):
        if cause is None:
            break
        if type(cause).__name__ in {"SSLError", "SSLCertVerificationError"}:
            return "HTTPS certificate verification failed; configure trusted CA certificates for this Python environment."
        cause = cause.__cause__
    return f"HTTP {status}: FMP service request failed." if status else "Request failed or timed out; no data substituted."


@st.cache_data(ttl=300, max_entries=12, show_spinner=False)
def load_current(names, api_key):
    _validate(names, api_key)
    warnings = []
    fallback_allowed = True
    try:
        quotes = get_fmp_json(BASE+"batch-quote", api_key=api_key, params={"symbols": ",".join(names)}, timeout=(3, 10))
    except Exception as exc:
        quotes = []
        note = failure_note(exc)
        warnings.append("FMP batch-quote: "+note)
        fallback_allowed = getattr(exc,"status_code",None) != 401 and not note.startswith("HTTPS certificate")
    batched = {s:one(quotes,s) for s in names}
    missing = [s for s in names if not batched[s]]
    if missing and fallback_allowed:
        warnings.append(f"Trying individual FMP quote requests for {len(missing)} missing batch quotes; at most one per symbol, concurrency three.")
    def fetch(symbol):
        values = {}
        notices = []
        quote = batched[symbol]
        quote_source = "FMP stable/batch-quote"
        if not quote and fallback_allowed:
            try:
                quote = one(get_fmp_json(BASE+"quote",api_key=api_key,params={"symbol":symbol},timeout=(3,10)),symbol)
                quote_source = "FMP stable/quote"
            except Exception as exc:
                notices.append(symbol+" quote: "+failure_note(exc))
        if not quote:
            notices.append(symbol+": unique dated quote response unavailable.")
        for kind, route in (("profile", "profile"), ("ratios", "ratios-ttm")):
            try:
                values[kind] = one(get_fmp_json(BASE+route, api_key=api_key, params={"symbol": symbol}, timeout=(3, 10)), symbol)
                if not values[kind]:
                    notices.append(symbol+" "+kind+": unique response unavailable.")
            except Exception as exc:
                values[kind] = {}  # Partial failure is retained as missing evidence.
                notices.append(symbol+" "+kind+": "+failure_note(exc))
        return symbol, values, quote, quote_source, notices
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, names))
    facts, quote_rows, quote_sources = {}, {}, {}
    for symbol, values, quote, source, notices in results:
        facts[symbol], quote_rows[symbol], quote_sources[symbol] = values, quote, source
        warnings.extend(notices)
    return {"quotes": quote_rows, "quote_sources":quote_sources, "facts": facts,
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "warnings": warnings}


def _validate(names, api_key):
    if not api_key or not 1 <= len(names) <= 41 or len(set(names)) != len(names) or any(s not in UNIVERSE for s in names):
        raise ValueError("Use unique supported universe symbols and configure FMP.")


def normalize_history(raw, symbol, first, last):
    result, duplicates = {}, set()
    for row in rows(raw, symbol):
        try:
            day = date.fromisoformat(str(row.get("date"))).isoformat()
            price = finite_number(row.get("close"))
            if not first <= day <= last or price is None or price <= 0 or row.get("currency", "USD") != "USD":
                continue
            if day in result:
                duplicates.add(day)
            result[day] = price
        except (ValueError, TypeError):
            continue
    return {d: p for d, p in sorted(result.items()) if d not in duplicates}


@st.cache_data(ttl=21600, max_entries=12, show_spinner=False)
def load_histories(names, api_key, end):
    _validate(names, api_key)
    last = date.fromisoformat(end)
    if last >= datetime.now(timezone.utc).date():
        raise ValueError("Historical diagnostics use completed calendar dates only.")
    first = (last-timedelta(days=400)).isoformat()
    def fetch(symbol):
        try:
            raw = get_fmp_json(BASE+"historical-price-eod/full", api_key=api_key,
                               params={"symbol": symbol, "from": first, "to": end}, timeout=(3, 15))
            return symbol, normalize_history(raw, symbol, first, end)
        except Exception:
            return symbol, {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        values = dict(pool.map(fetch, names))
    return {"series": values, "retrieved_at": datetime.now(timezone.utc).isoformat()}


def normalize_security(symbol, quote, profile, ratios, history, retrieved_at, history_retrieved_at, now, api_key="", quote_source="FMP stable/batch-quote"):
    if not quote:
        raise ValueError("Unique quote unavailable; check provider access or collection warnings.")
    if not profile:
        raise ValueError("Unique company profile unavailable; listing eligibility cannot be checked.")
    price, stamp = finite_number(quote.get("price")), finite_number(quote.get("timestamp"))
    try:
        observed = datetime.fromtimestamp(stamp, timezone.utc)
        if not 0 <= (now-observed).total_seconds() <= 7*86400:
            raise ValueError("Stale/future quote.")
    except (TypeError, OverflowError, OSError):
        raise ValueError("Quote observation time unavailable.") from None
    if price is None or price <= 0 or profile.get("currency") != "USD" or quote.get("currency", "USD") != "USD":
        raise ValueError("Positive USD quote and explicit USD listing required.")
    expected_etf = symbol in ETFS
    if not isinstance(profile.get("isEtf"), bool) or profile["isEtf"] != expected_etf or profile.get("isFund") is True:
        raise ValueError("Asset classification unavailable or incompatible.")
    exchange = profile.get("exchangeShortName") or profile.get("exchange")
    if exchange not in {"NASDAQ", "NYSE", "AMEX", "ARCA", "NYSEARCA", "BATS", "CBOE"}:
        raise ValueError("Supported US listing exchange unavailable.")
    volume = finite_number(profile.get("averageVolume"))
    if volume is None:
        volume = finite_number(quote.get("avgVolume"))
    if volume is None or volume <= 0 or price*volume < 5000000:
        raise ValueError("Average daily USD turnover below five million or unavailable.")
    sector = UNIVERSE[symbol][0] if expected_etf else clean(profile.get("sector"), api_key)
    if not sector:
        raise ValueError("Stock sector unavailable.")
    flags = ["No news, earnings forecasts, valuation targets or fund look-through collected."]
    if quote_source == "FMP stable/quote":
        flags.append("Individual FMP quote used because the batch quote was unavailable; original observation time retained.")
    currency_basis = "Quote USD and listing USD" if quote.get("currency") else "Explicit USD listing; quote unit compatibility assumed"
    if not quote.get("currency"):
        flags.append(currency_basis)
    if not ratios:
        flags.append("TTM ratios unavailable.")
    facts = [Fact(id=symbol+":price", field="price", value=price, unit="USD/share", basis="point-in-time quote",
                  as_of=observed.isoformat(), retrieved_at=retrieved_at, source=quote_source),
             Fact(id=symbol+":turnover", field="turnover", value=price*volume, unit="USD/day proxy",
                  basis="current quote times provider average share volume; averaging window unavailable", as_of=None,
                  retrieved_at=retrieved_at, source="FMP stable/profile + "+quote_source)]
    for field, key, unit in (("pe_ttm", "priceToEarningsRatioTTM", "multiple"),
                             ("margin_ttm", "netProfitMarginTTM", "fraction"),
                             ("debt_equity_ttm", "debtToEquityRatioTTM", "multiple")):
        value = finite_number(ratios.get(key))
        if value is not None:
            facts.append(Fact(id=symbol+":"+field, field=field, value=value, unit=unit, basis="provider TTM, fiscal end unavailable",
                              as_of=None, retrieved_at=retrieved_at, source="FMP stable/ratios-ttm"))
    if not history or (now.date()-date.fromisoformat(max(history))).days > 7:
        history = {}
        flags.append("Recent historical coverage unavailable; no filling or substitution.")
    return SecurityEvidence(ticker=symbol, name=clean(profile.get("companyName") or symbol, api_key), asset="etf" if expected_etf else "stock",
                            sector=sector, themes=UNIVERSE[symbol][1], price=price, currency="USD", currency_basis=currency_basis,
                            quote_as_of=observed.isoformat(), retrieved_at=retrieved_at, provider="FMP", facts=facts, history=history,
                            history_retrieved_at=history_retrieved_at, history_basis=HISTORY_BASIS, flags=flags)


def snapshot_id(data):
    return sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()[:24]


def collect(names, benchmark, api_key, force=False):
    all_names = tuple(sorted(set(names) | {benchmark}))
    _validate(all_names, api_key)
    end = (datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
    if force:
        load_current.clear(all_names, api_key)
        load_histories.clear(all_names, api_key, end)
    current = load_current(all_names, api_key)
    history = load_histories(all_names, api_key, end)
    now = datetime.now(timezone.utc)
    securities, excluded = {}, {}
    for s in all_names:
        try:
            f = current["facts"][s]
            securities[s] = normalize_security(s, current["quotes"][s], f["profile"], f["ratios"], history["series"][s],
                                                current["retrieved_at"], history["retrieved_at"], now, api_key,
                                                quote_source=current.get("quote_sources",{}).get(s,"FMP stable/batch-quote"))
        except ValueError as exc:
            excluded[s] = str(exc)
    packet = dict(mode="FMP live", retrieved_at=current["retrieved_at"], securities=[securities[s].model_dump() for s in names if s in securities],
                  benchmark=securities[benchmark].model_dump() if benchmark in securities else None,
                  warnings=current["warnings"]+["Current curated universe is not point-in-time; no backtest or survivorship correction.", HISTORY_BASIS],
                  excluded=excluded, universe_version=UNIVERSE_VERSION)
    return EvidenceSnapshot(id=snapshot_id(packet), **packet)
