"""Explicit S&P screen -> bounded research collection; cached separately from AI."""
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.providers.advisor_batches import RequestBatch
from langgraphagenticai.providers.portfolio_architect import BASE, collect, snapshot_id, failure_note, clean
from langgraphagenticai.providers.market_dashboard import load_dashboard, MACROS, SECTORS
from langgraphagenticai.providers.advisor_research import load_issuer_research
from langgraphagenticai.portfolio_architect.schemas import Fact
from langgraphagenticai.portfolio_architect.universe import ETFS
from langgraphagenticai.portfolio_architect.screening import metric_facts, rank_rows, shortlist, macro_assessment
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.deep_research.sector import map_sector_to_framework

LEGACY_MEMBERSHIP = "https://financialmodelingprep.com/api/v3/sp500_constituent"


def unique_rows(payload):
    if not isinstance(payload, list):
        raise ValueError("FMP screen requires JSON rows; bulk data unavailable for this plan/response.")
    result, duplicates = {}, set()
    for row in payload:
        if not isinstance(row, dict):
            continue
        try:
            symbol = normalize_company_symbol(row.get("symbol", ""))
        except ValueError:
            continue
        if symbol in result:
            duplicates.add(symbol)
        result[symbol] = row
    return {s:r for s,r in result.items() if s not in duplicates}


def load_membership(api_key, _budget=None):
    budget = _budget or RequestBatch()
    """One legacy compatibility attempt on endpoint entitlement/availability errors."""
    source, warnings = "FMP stable/sp500-constituent", []
    try:
        members = unique_rows(budget.request(get_fmp_json, BASE+"sp500-constituent", api_key=api_key))
    except Exception as exc:
        primary_note = failure_note(exc)
        if getattr(exc, "status_code", None) not in (402, 403, 404):
            raise ValueError("S&P 500 membership unavailable: "+primary_note+" Previous results remain; refresh explicitly after resolving provider access.") from None
        try:
            members = unique_rows(budget.request(get_fmp_json, LEGACY_MEMBERSHIP, api_key=api_key))
        except Exception as fallback_exc:
            raise ValueError("S&P 500 membership unavailable. Stable endpoint: "+primary_note+
                             " Legacy endpoint: "+failure_note(fallback_exc)+
                             " Previous results remain; check FMP access and refresh explicitly.") from None
        source = "FMP api/v3/sp500_constituent"
        warnings.append("Stable S&P membership: "+primary_note+" Legacy FMP membership used; retrieval time retained.")
    if not 400 <= len(members) <= 550:
        raise ValueError("S&P 500 membership incomplete; no curated-list substitution. Refresh to retry.")
    return members, source, warnings


@st.cache_data(ttl=3600, max_entries=8, show_spinner=False)
def load_screen(api_key, _budget=None):
    budget = _budget or RequestBatch()
    members, membership_source, warnings = load_membership(api_key, _budget=budget)
    stamp = datetime.now(timezone.utc).isoformat()
    data, sources = {}, {}
    for route in ("ratios-ttm-bulk", "key-metrics-ttm-bulk"):
        sources[route] = route
        if budget.stopped.is_set():
            data[route] = {}
            continue
        try:
            data[route] = unique_rows(budget.request(get_fmp_json, BASE+route, api_key=api_key))
        except Exception as exc:
            data[route] = {}
            warnings.append(route+": "+failure_note(exc))
            # A plan restriction alone permits the disclosed standard-endpoint path.
            # Never fan out on authentication, TLS, rate-limit or transient failures.
            if getattr(exc, "status_code", None) in (402, 403):
                sources[route] = route.removesuffix("-bulk")
                warnings.append(route+": standard per-company fallback; at most 550 requests, concurrency three, shared bounded retries.")
                def fetch(symbol):
                    if budget.stopped.is_set():
                        return symbol, {}
                    try:
                        values = unique_rows(budget.request(get_fmp_json, BASE+route.removesuffix("-bulk"), api_key=api_key,
                                                        params={"symbol": symbol}))
                        return symbol, values.get(symbol, {})
                    except Exception:
                        return symbol, {}  # Coverage/exclusion audit exposes missing facts.
                with ThreadPoolExecutor(max_workers=3) as pool:
                    data[route] = dict(pool.map(fetch, sorted(members)))
    if budget.stopped.is_set():
        warnings.append(budget.warning)
    rows = []
    for symbol, member in sorted(members.items()):
        facts = metric_facts(symbol, data["ratios-ttm-bulk"].get(symbol, {}),
                            data["key-metrics-ttm-bulk"].get(symbol, {}), stamp, "-bulk")
        for fact in facts:
            route = fact.source.removeprefix("FMP stable/")
            fact.source = "FMP stable/"+sources[route]
        rows.append({"symbol": symbol, "sector": clean(member.get("sector") or "Unknown", api_key),
                     "facts": [f.model_dump() for f in facts], "values": {f.field:f.value for f in facts}})
    return {"ranked": rank_rows(rows), "retrieved_at": stamp, "membership_source": membership_source,
            "membership_count": len(members), "warnings": warnings, "rate_limited":budget.stopped.is_set(),
            "method": "Equity Report sector-priority weighted metric percentiles (required 2, preferred 1, other applicable 0.5); missing = zero contribution, minimum 60% coverage and three peer-ranked metrics, positive margin/ROA. At least three peers per metric. REITs excluded without specialist evidence. Two leaders per framework then highest scores to 30. ETFs evaluated separately; no best-future-performer guarantee."}


def collect_advisor(mandate, api_key, force=False):
    budget = RequestBatch()
    if not api_key:
        raise ValueError("Configure FMP in Settings to screen and research current S&P 500 members.")
    if force:
        load_screen.clear(api_key)
        load_dashboard.clear(api_key)
    screen = load_screen(api_key, _budget=budget) if mandate.assets != "etfs" else {
        "ranked": [], "retrieved_at": datetime.now(timezone.utc).isoformat(), "membership_count": 0,
        "method": "ETF-only mandate; company screening inapplicable.", "warnings": []}
    if screen.get("rate_limited"):
        budget.stopped.set()
        raise ValueError(budget.warning)
    stocks = shortlist(screen["ranked"], mandate) if mandate.assets != "etfs" else ()
    if mandate.assets == "stocks" and len(stocks) < mandate.holdings:
        raise ValueError("Too few S&P 500 companies pass quality/coverage requirements. Check endpoint access; no unverified stocks substituted. "+" ".join(screen["warnings"]))
    funds = tuple(s for s in sorted(ETFS) if s not in mandate.forbidden) if mandate.assets != "stocks" else ()
    names = stocks+funds
    if not names:
        raise ValueError("No eligible research candidates remain.")
    snapshot = collect(names, mandate.benchmark, api_key, force, _budget=budget)
    if force:
        load_issuer_research.clear(stocks, api_key)
    research = load_issuer_research(stocks, api_key, _budget=budget) if snapshot.securities and not budget.stopped.is_set() else {}
    # Snapshot preserves the exact screen inputs used for eligibility and relative ranking.
    by_symbol = {r["symbol"]:r for r in screen["ranked"]}
    for security in snapshot.securities:
        row = by_symbol.get(security.ticker)
        if row and security.asset == "stock":
            if map_sector_to_framework(security.sector) != row["framework"]:
                security.flags.append("Sector classification conflicts with the screening membership; not eligible for construction.")
                continue
            security.facts = [f for f in security.facts if f.field not in row["values"]]
            security.facts += [Fact.model_validate(f) for f in row["facts"]]
            security.facts.append(Fact(id=security.ticker+":screen_score", field="screen_score", value=row["score"],
                unit="score/100", basis="sector-relative screen; Equity Report priority weights (2/1/0.5); missing penalized",
                as_of=None, retrieved_at=screen["retrieved_at"], source="Local calculation from saved FMP screening inputs"))
            issuer = research.get(security.ticker, {})
            security.facts += [Fact.model_validate(f) for f in issuer.get("facts", [])]
            security.news = issuer.get("news", [])
            security.flags = [f for f in security.flags if not f.startswith("No news,")]
            security.flags += issuer.get("warnings", [])
            if not security.news:
                security.flags.append("No usable dated company news within 30 calendar days; no event catalyst verified.")
            if not issuer.get("facts"):
                security.flags.append("Comparable four-year annual revenue history unavailable; growth not inferred.")
            security.flags.append("Forward earnings, price targets and company-specific catalyst impact are unverified.")
    try:
        # Reserve the shared dashboard's bounded quote + per-instrument history budget.
        budget.reserve(1+len(MACROS)+len(SECTORS))
        macro = macro_assessment(load_dashboard(api_key))
    except Exception as exc:
        macro = {"status": "unavailable", "risks": [], "upside": [], "observations": [],
                 "warnings": ["Market context: "+failure_note(exc)]}
    if budget.stopped.is_set() and budget.warning not in snapshot.warnings:
        snapshot.warnings.append(budget.warning)
    snapshot.screening = {**screen, "shortlisted": list(stocks), "researched": len(snapshot.securities),
                          "shortlist_policy":"Growth/AI: up to 20 sector-proxy candidates plus quality alternatives; issuer theme relevance and positive annual growth checked after research." if mandate.investment_style == "growth" and "AI" in mandate.themes else "Two sector-framework leaders, then best remaining quality scores."}
    snapshot.macro = macro
    snapshot.warnings += screen["warnings"] + ["Current S&P membership is not point-in-time; survivor bias applies. ETFs are a separate curated universe."]
    snapshot.universe_version = "sp500-current-plus-etfs-v2"
    snapshot.id = snapshot_id(snapshot.model_dump(exclude={"id"}))
    return snapshot
