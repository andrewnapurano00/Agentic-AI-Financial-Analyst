"""Bounded, session-owned raw FMP reuse across explicit company workflows."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlsplit

_capture = ContextVar("axiom_company_evidence_capture", default=None)


def credential_scope(api_key):
    return sha256(api_key.encode()).hexdigest()[:16]


@contextmanager
def capture_company_evidence(api_key):
    output = {"scope": credential_scope(api_key), "companies": {}}
    variable = _capture
    token = variable.set(output)
    try:
        yield output
    finally:
        variable.reset(token)


def capture_fmp_response(url, params, data, api_key):
    target = _capture.get()
    if not target or target["scope"] != credential_scope(api_key):
        return
    from .valuation import JOBS, normalize_rows
    location = urlsplit(url)
    if location.scheme != "https" or location.hostname != "financialmodelingprep.com" or location.username:
        return
    path = location.path
    symbol = str(params.get("symbol") or path.rsplit("/", 1)[-1]).upper()
    from langgraphagenticai.state.research_context import normalize_company_symbol
    try:
        symbol = normalize_company_symbol(symbol)
    except ValueError:
        return
    for kind, (route, options, limit) in JOBS.items():
        names = {route.format(symbol=symbol), "/api/v3/" + route.rsplit("/", 1)[-1] + "/" + symbol}
        if path not in names:
            continue
        # Annual requirements never borrow quarterly records. Quarterly feeds
        # are retained separately as contextual evidence, not target anchors.
        period = params.get("period", options.get("period"))
        stored_kind = "quarter_" + kind if period == "quarter" and kind in {"income", "balance", "cashflow", "balance_reported"} else kind
        if options.get("period") == "annual" and period not in {"annual", "quarter"}:
            return
        try:
            rows = normalize_rows(kind, data, symbol, api_key, 8 if stored_kind.startswith("quarter_") else limit)
        except (ValueError, TypeError):
            return
        if not rows:
            return
        company = target["companies"].setdefault(symbol, {"symbol": symbol, "credential_scope":target["scope"], "sources": {}, "warnings": []})
        company[stored_kind] = rows
        company["sources"][stored_kind] = {"provider": "FMP", "route": path, "status": "available",
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "workspace": "Equity Report"}
        return


def save_company_evidence(state, captured):
    store = state.setdefault("company_evidence", {})
    for symbol, value in captured["companies"].items():
        key = captured["scope"] + ":" + symbol
        previous = deepcopy(store.pop(key, {}))
        previous.update({k: deepcopy(v) for k, v in value.items() if k != "sources"})
        previous["sources"] = {**previous.get("sources", {}), **deepcopy(value["sources"])}
        store[key] = previous
    while len(store) > 16:
        del store[next(iter(store))]


def saved_company_evidence(state, symbol, api_key):
    return deepcopy(state.get("company_evidence", {}).get(credential_scope(api_key) + ":" + symbol))
