"""Selected company and analyst evidence, maximum 18 dispatches / four workers.

The existing snapshot budget is separate. No history, news or models are loaded
for peers; Streamlit controls reuse six-hour evidence caches. Retries remain in
the shared safe FMP transport and can add bounded HTTP attempts.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import streamlit as st

from langgraphagenticai.analysis.company_terminal import build_metrics, compatible_peer_metrics, earnings_events, matching_rows, analyst_summary
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.utils.safety import sanitize_error

BASE = "https://financialmodelingprep.com/stable/"


def _request(route, symbol, api_key, **params):
    return get_fmp_json(BASE + route, api_key=api_key, params={"symbol": symbol, **params}, timeout=(5, 20))


def _collect(jobs, api_key):
    results, warnings = {}, []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_request, route, symbol, api_key, **params): name for name, (route, symbol, params) in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                payload = future.result()
                if not isinstance(payload, list):
                    raise ValueError("Expected a list of provider records")
                results[name] = payload
            except Exception as exc:
                results[name] = []
                warnings.append(f"{name}: {sanitize_error(exc)}")
    return results, warnings


@st.cache_data(ttl=21600, show_spinner=False)
def load_terminal_evidence(symbol, api_key):
    symbol = normalize_company_symbol(symbol)
    if not api_key.strip():
        return {"symbol": symbol, "annual": [], "earnings": [], "peers": [], "warnings": ["Company extension unavailable: FMP is not configured."], "retrieved_at": None}
    retrieved = datetime.now(timezone.utc).isoformat()
    initial, warnings = _collect({
        "annual": ("income-statement", symbol, {"period": "annual", "limit": 6}),
        "earnings": ("earnings", symbol, {}),
        "peers": ("stock-peers", symbol, {}),
        "estimates": ("analyst-estimates", symbol, {"period": "annual", "limit": 12, "page": 0}),
        "targets": ("price-target-consensus", symbol, {}),
        "grades": ("grades-consensus", symbol, {}),
    }, api_key)
    peer_symbols = []
    for row in initial["peers"]:
        try:
            peer = normalize_company_symbol(row.get("symbol"))
        except (ValueError, AttributeError):
            continue
        if peer != symbol and peer not in peer_symbols:
            peer_symbols.append(peer)
        if len(peer_symbols) == 4:
            break
    jobs = {}
    for peer in peer_symbols:
        for label, route, params in (("income", "income-statement", {"period": "quarter", "limit": 8}),
                                     ("ratios", "ratios-ttm", {}), ("metrics", "key-metrics-ttm", {})):
            jobs[f"{peer}:{label}"] = (route, peer, params)
    bundles, peer_warnings = _collect(jobs, api_key) if jobs else ({}, [])
    warnings.extend(peer_warnings)
    peers = []
    for peer in peer_symbols:
        evidence = {}
        for label in ("income", "ratios", "metrics"):
            raw = bundles.get(f"{peer}:{label}", [])
            matched = matching_rows(raw, peer)
            if raw and len(matched) != len(raw):
                warnings.append(f"{peer}:{label}: excluded nonmatching provider identities")
            evidence[label] = matched if label == "income" else matched[0] if matched else {}
        peers.append({"symbol": peer, "terminal_evidence": evidence})
    for label in ("annual", "earnings", "estimates", "targets", "grades"):
        raw = initial[label]
        initial[label] = matching_rows(raw, symbol)
        if raw and len(raw) != len(initial[label]):
            warnings.append(f"{label}: excluded nonmatching provider identities")
    initial["annual"] = initial["annual"][:6]
    initial["earnings"] = initial["earnings"][:100]
    initial["estimates"] = initial["estimates"][:12]
    if len(peers) < 4:
        warnings.append(f"Partial peer coverage: {len(peers)} of four distinct provider-listed peers.")
    return {"symbol": symbol, "annual": initial["annual"], "earnings": initial["earnings"],
            "estimates": initial["estimates"], "targets": initial["targets"][0] if initial["targets"] else {},
            "grades": initial["grades"][0] if initial["grades"] else {},
            "peers": peers, "warnings": warnings, "retrieved_at": retrieved}


def load_company_terminal(symbol, api_key, snapshot):
    symbol = normalize_company_symbol(symbol)
    if snapshot.get("symbol") != symbol:
        raise ValueError("Company evidence identity does not match selected ticker")
    evidence = load_terminal_evidence(symbol, api_key)
    metrics = build_metrics(snapshot, evidence["annual"], evidence.get("estimates", []))
    for item in metrics.values():
        item["retrieved_at"] = evidence["retrieved_at"] if item["basis"].startswith(("Calculated annual", "Calculated quote /")) else snapshot.get("fetched_at")
    peers = [{"symbol": symbol, "metrics": {key: metrics[key] for key in ("revenue_growth", "gross_margin", "operating_margin", "pe_ttm", "roic")}, "selected": True}]
    for peer in evidence["peers"]:
        peer_metrics = compatible_peer_metrics(metrics, build_metrics(peer))
        for item in peer_metrics.values():
            item["retrieved_at"] = evidence["retrieved_at"]
        peers.append({"symbol": peer["symbol"], "metrics": peer_metrics, "selected": False})
    return {"symbol": symbol, "metrics": metrics, "analyst": analyst_summary(snapshot, evidence), "earnings": earnings_events(evidence["earnings"]), "peers": peers,
            "warnings": evidence["warnings"], "retrieved_at": evidence["retrieved_at"]}
