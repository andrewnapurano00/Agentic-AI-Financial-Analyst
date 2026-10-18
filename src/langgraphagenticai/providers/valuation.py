"""Bounded valuation evidence through the existing FMP transport; no model calls."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from datetime import timedelta
import math
import streamlit as st

from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.state.research_context import normalize_company_symbol
from langgraphagenticai.utils.safety import redact_sensitive_text

BASE = "https://financialmodelingprep.com"
JOBS = {
    "balance_reported": ("/stable/balance-sheet-statement-as-reported", {"period": "annual", "limit": 5}, 5),
    "quote": ("/stable/quote", {}, 1),
    "profile": ("/stable/profile", {}, 1),
    "income": ("/stable/income-statement", {"period": "annual", "limit": 5}, 5),
    "balance": ("/stable/balance-sheet-statement", {"period": "annual", "limit": 5}, 5),
    "estimates": ("/api/v3/analyst-estimates/{symbol}", {"period": "annual", "limit": 6}, 6),
    "ratios": ("/stable/ratios-ttm", {}, 1),
    "metrics": ("/stable/key-metrics-ttm", {}, 1),
    "cashflow": ("/stable/cash-flow-statement", {"period": "annual", "limit": 5}, 5),
    "targets": ("/api/v4/price-target-summary", {}, 1),
    "history": ("/api/v3/historical-price-full/{symbol}", {}, 400),
}
FIELDS = {
    "quote": ("symbol", "price", "timestamp", "currency", "marketCap"),
    "profile": ("symbol", "companyName", "sector", "industry", "currency", "description", "beta"),
    "income": ("symbol", "date", "period", "fiscalYear", "calendarYear", "reportedCurrency", "revenue", "netIncome", "epsDiluted", "weightedAverageShsOutDil", "acceptedDate", "filingDate", "grossProfit", "operatingIncome"),
    "balance": ("symbol", "date", "period", "fiscalYear", "calendarYear", "reportedCurrency", "totalStockholdersEquity", "commonStockEquity", "preferredStock", "commonStockSharesOutstanding", "acceptedDate", "filingDate", "totalAssets", "totalDebt", "cashAndCashEquivalents"),
    "balance_reported": ("symbol", "date", "period", "fiscalYear", "reportedCurrency", "acceptedDate", "filingDate", "commonstocksharesoutstanding", "commonstocksharesissued", "treasurystockcommonshares", "stockholdersequity"),
    "estimates": ("symbol", "date", "period", "reportedCurrency", "currency", "estimatedEpsAvg", "epsAvg", "estimatedEps", "estimatedRevenueAvg", "revenueAvg", "numberAnalystEstimatedEps", "numberAnalystsEstimatedEps", "numAnalystsEps", "numberAnalystsEstimatedRevenue", "numAnalystsRevenue"),
    "ratios": ("symbol", "date", "priceToEarningsRatioTTM", "peRatioTTM", "priceToEarningsGrowthRatioTTM", "priceToSalesRatioTTM", "priceToBookRatioTTM", "debtToEquityRatioTTM", "currentRatioTTM", "grossProfitMarginTTM", "operatingProfitMarginTTM", "netProfitMarginTTM", "dividendYieldTTM"),
    "metrics": ("symbol", "date", "enterpriseValueTTM", "evToEBITDATTM", "enterpriseValueOverEBITDATTM", "returnOnInvestedCapitalTTM", "returnOnEquityTTM", "returnOnAssetsTTM", "bookValuePerShareTTM", "bookValuePerShare", "roicTTM", "roeTTM"),
    "cashflow": ("symbol", "date", "period", "fiscalYear", "reportedCurrency", "freeCashFlow", "operatingCashFlow", "capitalExpenditure"),
    "targets": ("symbol", "currency", "lastMonthAvgPriceTarget", "lastMonthCount", "lastQuarterAvgPriceTarget", "lastQuarterCount"),
    "history": ("symbol", "date", "adjClose", "close"),
}
for _kind in ("income", "balance", "cashflow", "balance_reported"):
    FIELDS["quarter_" + _kind] = FIELDS[_kind]


def normalize_rows(kind, rows, symbol, api_key, limit):
    if kind == "history" and isinstance(rows, dict) and rows.get("symbol") == symbol:
        rows = [{**row, "symbol": row.get("symbol", symbol)} for row in rows.get("historical", []) if isinstance(row, dict)]
    if not isinstance(rows, list):
        raise ValueError("Unexpected provider shape")
    selected = []
    for row in rows[:limit]:
        if not isinstance(row, dict) or str(row.get("symbol", "")).strip().upper() != symbol:
            raise ValueError("Provider identity mismatch")
        data = {**(row.get("data") if isinstance(row.get("data"), dict) else {}), **{k:v for k,v in row.items() if k != "data"}} if kind.endswith("balance_reported") else row
        item = {}
        for field in FIELDS[kind]:
            value = data.get(field)
            if isinstance(value, float) and not math.isfinite(value):
                value = None
            if isinstance(value, str):
                value = redact_sensitive_text(value.replace(api_key, "[REDACTED]") if api_key else value, max_length=1800 if field == "description" else 160)
            if value is None or isinstance(value, (str, int, float)) and not isinstance(value, bool):
                item[field] = value
        item["symbol"] = symbol
        selected.append(item)
    return selected


def reusable_component(shared, kind, symbol, now=None):
    now = now or datetime.now(timezone.utc)
    if not shared or shared.get("symbol") != symbol or not shared.get(kind):
        return False
    source = shared.get("sources", {}).get(kind, {})
    ttl = 300 if kind in {"quote", "ratios", "metrics"} else 3600 if kind in {"estimates", "history"} else 86400
    try:
        stamp = datetime.fromisoformat(str(source.get("retrieved_at", "")).replace("Z", "+00:00"))
        return source.get("provider") == "FMP" and source.get("status") == "available" and stamp.tzinfo is not None and 0 <= (now-stamp).total_seconds() <= ttl
    except (ValueError, TypeError):
        return False


@st.cache_data(ttl=300, max_entries=32, show_spinner=False)
def _collect(symbol, api_key, shared=None):
    from copy import deepcopy
    result = {"symbol": symbol, "warnings": [], "sources": {}, "evidence_version": 3}

    def fetch(kind):
        if reusable_component(shared, kind, symbol):
            return normalize_rows(kind, shared[kind], symbol, api_key, JOBS[kind][2])
        route, options, limit = JOBS[kind]
        params = dict(options)
        if "{symbol}" not in route:
            params["symbol"] = symbol
        if kind == "history":
            params.update({"from": (datetime.now(timezone.utc).date()-timedelta(days=550)).isoformat(), "to": datetime.now(timezone.utc).date().isoformat()})
        rows = get_fmp_json(BASE + route.format(symbol=symbol), api_key=api_key, params=params, timeout=(5, 20))
        return normalize_rows(kind, rows, symbol, api_key, limit)

    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = {pool.submit(fetch, kind): kind for kind in JOBS if kind != "balance_reported"}
        for future in as_completed(tasks):
            kind = tasks[future]
            try:
                result[kind] = future.result()
                status = "available" if result[kind] else "empty"
            except Exception:
                result[kind] = []
                status = "failed"
                result["warnings"].append(f"{kind.title()} unavailable: provider response failed validation or retrieval; other sources retained.")
            result["sources"][kind] = {"provider": "FMP", "route": JOBS[kind][0].format(symbol=symbol), "retrieved_at": datetime.now(timezone.utc).isoformat(), "status": status}
            if status == "available" and reusable_component(shared, kind, symbol):
                result["sources"][kind] = {**deepcopy(shared["sources"][kind]), "reused": True}
    from langgraphagenticai.deep_research.sector import map_sector_to_framework
    profile = (result.get("profile") or [{}])[0]
    if map_sector_to_framework(profile.get("sector"), profile.get("industry")) == "Banks / Financials" and any(not row.get("commonStockSharesOutstanding") for row in result.get("balance", [])):
        try:
            result["balance_reported"] = fetch("balance_reported")
            result["sources"]["balance_reported"] = deepcopy(shared["sources"]["balance_reported"]) if reusable_component(shared, "balance_reported", symbol) else {"provider":"FMP", "route":JOBS["balance_reported"][0], "retrieved_at":datetime.now(timezone.utc).isoformat(), "status":"available" if result["balance_reported"] else "empty"}
            if reusable_component(shared, "balance_reported", symbol):
                result["sources"]["balance_reported"]["reused"] = True
        except Exception:
            result["balance_reported"] = []
            result["sources"]["balance_reported"] = {"provider":"FMP", "route":JOBS["balance_reported"][0], "retrieved_at":datetime.now(timezone.utc).isoformat(), "status":"failed"}
            result["warnings"].append("Year-end common shares could not be retrieved from as-reported annual evidence.")
    for kind in ("quarter_income", "quarter_cashflow", "quarter_balance"):
        if reusable_component(shared, kind, symbol):
            try:
                result[kind] = normalize_rows(kind, shared[kind], symbol, api_key, 8 if kind == "quarter_income" else 4 if kind == "quarter_cashflow" else 2)
                result["sources"][kind] = {**deepcopy(shared["sources"][kind]), "reused":True}
            except (ValueError, TypeError):
                result["warnings"].append("A saved quarterly component failed identity/shape checks and was excluded; fresh annual evidence retained.")
    result["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    return result


def load_valuation_evidence(symbol, api_key, *, refresh=False, shared=None):
    symbol = normalize_company_symbol(symbol)
    if not str(api_key).strip():
        raise ValueError("Configure FMP to load valuation evidence.")
    from .company_evidence import credential_scope
    if shared and shared.get("credential_scope") != credential_scope(api_key):
        shared = None
    if refresh:
        _collect.clear(symbol, api_key, shared)
    return _collect(symbol, api_key, shared)
