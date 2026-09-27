"""Small, balanced model inputs; the original evidence remains in the export."""
from __future__ import annotations

from .models import Evidence, dumps


COMMON = {"date", "symbol", "fiscalYear", "calendarYear", "period", "reportedCurrency", "currency"}
FIELDS = {
    "profile": {"companyName", "sector", "industry", "description", "country", "exchange", "ceo", "beta", "website"},
    "quote": {"name", "price", "marketCap", "timestamp", "eps", "pe", "volume", "yearHigh", "yearLow"},
    "income": {"revenue", "grossProfit", "operatingIncome", "netIncome", "epsDiluted", "ebitda", "researchAndDevelopmentExpenses", "interestExpense", "weightedAverageShsOutDil"},
    "balance": {"cashAndCashEquivalents", "cashAndShortTermInvestments", "totalDebt", "netDebt", "totalAssets", "totalLiabilities", "totalStockholdersEquity", "totalCurrentAssets", "totalCurrentLiabilities"},
    "cash_flow": {"netCashProvidedByOperatingActivities", "capitalExpenditure", "freeCashFlow", "stockBasedCompensation", "commonStockRepurchased", "commonDividendsPaid", "netIncome"},
    "income_ttm": {"revenue", "grossProfit", "operatingIncome", "netIncome", "epsDiluted", "ebitda", "researchAndDevelopmentExpenses", "interestExpense", "weightedAverageShsOutDil"},
    "balance_ttm": {"cashAndCashEquivalents", "cashAndShortTermInvestments", "totalDebt", "netDebt", "totalAssets", "totalLiabilities", "totalStockholdersEquity", "totalCurrentAssets", "totalCurrentLiabilities"},
    "cash_flow_ttm": {"netCashProvidedByOperatingActivities", "capitalExpenditure", "freeCashFlow", "stockBasedCompensation", "commonStockRepurchased", "commonDividendsPaid", "netIncome"},
    # URLs remain in saved evidence; omit them from model context to spend tokens on dates and substance.
    "news": {"title", "snippet", "published", "publisher"},
    "web": {"title", "snippet", "published", "publisher"},
}

FOCUS_TERMS = {
    "income": ("revenue", "earnings", "margin", "growth", "profit", "fundamental"),
    "balance": ("balance sheet", "debt", "liquidity", "solvency", "cash", "leverage", "risk"),
    "cash_flow": ("cash flow", "free cash", "capex", "conversion", "buyback", "dividend"),
    "income_ttm": ("ttm", "revenue", "earnings", "margin", "profit", "fundamental"),
    "balance_ttm": ("ttm", "balance sheet", "debt", "liquidity", "cash", "leverage", "risk"),
    "cash_flow_ttm": ("ttm", "cash flow", "free cash", "capex", "conversion", "buyback", "dividend"),
    "ratios_ttm": ("valuation", "multiple", "ratio", "margin", "return on", "roe", "roic"),
    "metrics_ttm": ("valuation", "enterprise value", "yield", "capital", "quality"),
    "estimates": ("estimate", "forecast", "forward", "expectation", "growth", "earnings"),
    "price_targets": ("price target", "upside", "downside", "analyst"),
    "technicals": ("technical", "momentum", "trend", "rsi", "moving average", "volatility", "drawdown"),
    "news": ("news", "catalyst", "recent", "event", "risk"),
    "web": ("news", "catalyst", "recent", "event", "risk"),
    "investigation": ("transcript", "guidance", "management", "earnings", "peer", "valuation", "risk"),
}


def compact(value, *, list_limit=6, string_limit=2400):
    if isinstance(value, dict):
        return {k: compact(v, list_limit=list_limit, string_limit=string_limit)
                for k, v in value.items() if k not in {"series", "raw", "profile_raw", "raw_keys"}}
    if isinstance(value, list):
        rows = [compact(v, list_limit=list_limit, string_limit=string_limit) for v in value[:list_limit]]
        if len(value) > list_limit:
            rows.append({"omitted_rows": len(value) - list_limit})
        return rows
    if isinstance(value, str) and len(value) > string_limit:
        return value[:string_limit] + " [excerpt truncated]"
    return value


def evidence_context(evidence: list[Evidence], max_chars: int = 48000, *, focus: str = "") -> list[dict]:
    """Return JSON objects, not a JSON string embedded inside another JSON string.

    Allocate each source an equal data allowance; keep every ID/company even in
    a four-company run. Explicitly mark excerpts instead of presenting them as full data.
    """
    records = []
    for item in evidence:
        data = item.to_dict()["data"]
        if item.category in FIELDS and isinstance(data, list):
            keep = COMMON | FIELDS[item.category]
            data = [{k: v for k, v in row.items() if k in keep} for row in data if isinstance(row, dict)]
        records.append({"id": item.id, "symbol": item.symbol, "category": item.category,
                        "status": item.status, "retrieved_at": item.retrieved_at,
                        "note": item.note[:350], "data": compact(data)})
    if not records:
        return []
    metadata_size = len(dumps([{k: v for k, v in r.items() if k != "data"} for r in records]))
    weights = {"financial_trends": 3, "income": 2, "balance": 2, "cash_flow": 2,
               "income_ttm": 2, "balance_ttm": 2, "cash_flow_ttm": 2,
               "news": 4, "web": 2, "investigation": 2, "app_context": 2}
    focus_text = focus.lower()
    focused = {category for category, terms in FOCUS_TERMS.items()
               if any(term in focus_text for term in terms)}
    record_weights = [weights.get(r["category"], 1) + (2 if r["category"] in focused else 0)
                      for r in records]
    total_weight = sum(record_weights)
    unit = max(0, (max_chars - metadata_size - len(records) * 80) // total_weight)
    for record, weight in zip(records, record_weights):
        allowance = unit * weight
        body = dumps(record["data"])
        if len(body) > allowance:
            # Explicitly labelled text excerpt, never misrepresented as complete JSON.
            record["data"] = {"excerpt": body[:allowance // 2], "truncated": True}
    return records
