"""Small, balanced model inputs; the original evidence remains in the export."""
from __future__ import annotations

from .models import Evidence, dumps


COMMON = {"date", "symbol", "fiscalYear", "calendarYear", "period", "reportedCurrency", "currency", "methodology", "quarters", "formula", "source_records", "growth_pct", "limitations", "quote_as_of", "units", "prior_ttm_unavailable_reason", "duration_assumption", "duration", "periodType", "reportingBasis", "startDate"}
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

    Keep balanced substantive company records under the actual serialized budget.
    Omitted source records stay in saved audit evidence; never emit empty excerpts.
    """
    from .sector import map_sector_to_framework, SECTOR_METRIC_REGISTRY
    from .quarterly_ttm import METHODOLOGY
    profiles = {item.symbol: item.data[0] for item in evidence if item.category=="profile"
                and item.status=="ok" and isinstance(item.data,list) and item.data}
    raw_field_metrics = {"grossProfit":"Latest Gross Margin", "ebitda":"Latest EBITDA Margin", "freeCashFlow":"FCF Margin",
                         "researchAndDevelopmentExpenses":"R&D as % Revenue", "stockBasedCompensation":"Stock-Based Comp % Revenue"}
    records = []
    for item in evidence:
        data = item.to_dict()["data"]
        if item.category in FIELDS and isinstance(data, list):
            keep = COMMON | FIELDS[item.category]
            data = [{k: v for k, v in row.items() if k in keep} for row in data if isinstance(row, dict)]
        profile=profiles.get(item.symbol,{})
        framework=map_sector_to_framework(profile.get("sector"),profile.get("industry"))
        avoids=set(SECTOR_METRIC_REGISTRY[framework]["avoid_or_downweight"])
        excluded=[field for field,metric in raw_field_metrics.items() if metric in avoids and isinstance(data,list) and any(isinstance(row,dict) and field in row for row in data)]
        if isinstance(data,list):
            data=[{key:value for key,value in row.items() if key not in excluded} if isinstance(row,dict) else row for row in data]
        basis = ("snapshot_stocks" if item.category.startswith("balance") else
                 ("TTM_standalone_quarter_sum" if isinstance(data,list) and data and data[0].get("methodology")==METHODOLOGY else "legacy_TTM_duration_unverified") if item.category in {"income_ttm","cash_flow_ttm"} else
                 "reported_period" if item.category.startswith(("income","cash_flow")) else
                 "provider_or_consensus")
        records.append({"id": item.id, "symbol": item.symbol, "category": item.category,
                        "status": item.status, "retrieved_at": item.retrieved_at,
                        "note": item.note[:100], "financial_basis": basis,
                        "sector_framework": framework, "excluded_downweighted_fields": excluded,
                        "data": compact(data)})
    if not records:
        return []
    records[0]["context_policy"] = "TTM_standalone_quarter_sum: four fiscal quarter flows; snapshot_stocks: never summed. Statement amounts: reported currency units; EPS: currency/share. Ratios, source assumptions and sector applicability: audited comparison."
    # Raw annual/quarterly source duplicates and reconciliation remain in the audit.
    # Model-facing selected periods and calculated TTM already carry their basis.
    preferred = [r for r in records if not r["category"].endswith(("_quarterly","_annual"))
                 and r["category"] != "annual_reconciliation"]
    if not preferred: preferred=records
    return bounded_evidence_records(preferred,max_chars)


def bounded_evidence_records(records,max_chars):
    """Balanced source selection with real structured values, never blank excerpts."""
    from .quarterly_ttm import flow_duration
    priority={name:i for i,name in enumerate(("income_ttm","cash_flow_ttm","balance_latest","quote","profile","balance_ttm",
        "income","cash_flow","estimates","news","web","financial_trends","technicals","investigation"))}
    core={"symbol","date","reportedCurrency","currency","revenue","netIncome","ebitda","grossProfit","operatingIncome",
          "netCashProvidedByOperatingActivities","freeCashFlow","totalAssets","totalStockholdersEquity","totalDebt","cashAndCashEquivalents",
          "price","marketCap","timestamp","sector","industry","companyName","epsAvg","revenueAvg","title","snippet","published","publisher"}
    def small_data(record):
        data=record["data"]
        category=record["category"]
        # Financial statement excerpts use a known field inventory. Research tools,
        # narratives and derived observations have different schemas; recursively
        # retain their actual payload rather than applying the statement whitelist.
        if category in {"income", "cash_flow", "income_ttm", "cash_flow_ttm",
                        "balance", "balance_ttm", "balance_latest", "quote", "profile", "estimates"}:
            keep=core | {"fiscalYear", "period", "duration", "periodType", "reportingBasis", "startDate", "excluded"}
            if isinstance(data,list):
                return [{k:v for k,v in row.items() if k in keep}
                        for row in data[:1] if isinstance(row,dict)]
            if isinstance(data,dict):
                return {k:v for k,v in data.items() if k in keep}
        return compact(data,list_limit=2,string_limit=700)
    groups={}
    for r in records:
        # Explicit nonstandalone selected periods are source facts, not comparable flows.
        if r["category"] in {"income","cash_flow"} and isinstance(r["data"],list) and r["data"]:
            valid,reason=flow_duration(r["data"][0])
            if not valid:
                r=dict(r);r["data"]={"excluded":reason,"date":r["data"][0].get("date"),"duration":r["data"][0].get("duration")}
                r["financial_basis"]="excluded_unverified_duration"
        groups.setdefault(r["symbol"],[]).append(r)
    for group in groups.values():group.sort(key=lambda r:priority.get(r["category"],99))
    selected=[]
    rounds=max((len(group) for group in groups.values()),default=0)
    for rank in range(rounds):
        for symbol,group in groups.items():
            if rank>=len(group):continue
            record=group[rank]
            minimal={k:v for k,v in record.items() if k not in {"context_policy","excluded_downweighted_fields","sector_framework","note"}}
            minimal["data"]=small_data(record)
            minimal["excerpted"]=True
            # Reserve capacity for useful numeric bodies and an omission marker.
            if len(dumps(selected+[minimal])) <= max_chars-120:
                selected.append(minimal)
    if selected:
        selected[0]["omitted_sources"]=len(records)-len(selected)
        selected[0]["context_policy"]="Statements: reported currency units; EPS/share; standalone TTM flows, unsummed snapshots; exclusions and omitted source details remain in saved audit."
        # Metadata addition is accounted for in the whole serialized payload.
        while len(dumps(selected))>max_chars and len(selected)>len(groups):
            selected.pop();selected[0]["omitted_sources"]=len(records)-len(selected)
        if len(dumps(selected))>max_chars:
            selected[0].pop("context_policy",None)
    return selected if len(dumps(selected))<=max_chars else []
