"""Shared fresh-research quarterly collection with independently dated snapshots."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, timedelta

from langgraphagenticai.providers.fmp_http import get_fmp_json
from .data import FinancialDataSource, extract_rows, technical_snapshot
from .models import Evidence, parse_symbols
from .quarterly_ttm import METHODOLOGY, INCOME_FIELDS, CASH_FIELDS, aggregate, window


class QuarterlyFinancialDataSource(FinancialDataSource):
    fetch_json = staticmethod(get_fmp_json)
    def __init__(self, api_key):
        self.api_key = api_key

    def collect(self, request, progress):
        jobs = []
        for symbol in parse_symbols(",".join(request.symbols)):
            for category, route, params in (
                ("profile", "profile", {}), ("quote", "quote", {}),
                ("income_quarterly", "income-statement", {"period": "quarter", "limit": 8}),
                ("balance_quarterly", "balance-sheet-statement", {"period": "quarter", "limit": 8}),
                ("cash_flow_quarterly", "cash-flow-statement", {"period": "quarter", "limit": 8}),
                ("estimates", "analyst-estimates", {"period": "annual", "limit": 20}),
                ("price_targets", "price-target-consensus", {}),
                ("technicals", "historical-price-eod/full", {"from": (date.today()-timedelta(days=550)).isoformat(), "to": date.today().isoformat()}),
            ):
                jobs.append((symbol, category, route, params))
            # Annual history is independent of the selected reported-period view.
            for category, route in (("income", "income-statement"), ("balance", "balance-sheet-statement"), ("cash_flow", "cash-flow-statement")):
                jobs.append((symbol, category+"_annual", route, {"period": "annual", "limit": 5}))

        def fetch(job):
            symbol, category, route, params = job
            url = "https://financialmodelingprep.com/stable/" + route
            try:
                rows = extract_rows(self.fetch_json(url, api_key=self.api_key, params={"symbol": symbol, **params}))
                if category in {"profile", "quote"}:
                    if not rows or any(row.get("symbol") != symbol for row in rows):
                        return Evidence("", symbol, category, f"{symbol} · {category}", "FMP", [], status="missing", url=url,
                                        note="Provider security identity is missing or does not match the requested ticker; records excluded.")
                if category == "estimates":
                    from .research_metrics import future_estimates
                    rows = future_estimates(rows, symbol)
                if category == "technicals":
                    if any(row.get("symbol") != symbol for row in rows):
                        rows = []
                    data = technical_snapshot(rows)
                    if data:
                        data["symbol"] = symbol
                else:
                    rows = [row for row in rows if row.get("symbol") == symbol]
                    rows.sort(key=lambda row: str(row.get("date") or ""), reverse=category != "estimates")
                    data = rows[:params.get("limit", 5)]
                return Evidence("", symbol, category, f"{symbol} · {category}", "FMP", data, url=url,
                                status="ok" if data else "missing", note="" if data else "No usable provider records; coverage or entitlement may be unavailable.")
            except Exception:
                return Evidence("", symbol, category, f"{symbol} · {category}", "FMP", [], status="error", url=url,
                                note="Dataset retrieval failed; successful datasets remain available.")
        with ThreadPoolExecutor(max_workers=5) as pool:
            evidence = list(pool.map(fetch, jobs))
        progress(f"Collected {len(jobs)} bounded quarterly-only financial datasets")
        suffix = "_quarterly" if request.period == "quarter" else "_annual"
        evidence += [replace(e, category=e.category.removesuffix(suffix)) for e in evidence if e.category.endswith(suffix)]
        for symbol in request.symbols:
            sources = {e.category: e for e in evidence if e.symbol == symbol}
            computed = {}
            for category, fields in (("income", INCOME_FIELDS), ("cash_flow", CASH_FIELDS)):
                source = sources[category + "_quarterly"]
                try:
                    computed[category] = aggregate(source.data, symbol, fields)
                    computed[category]["source_records"] = {"category": source.category, "url": source.url, "retrieved_at": source.retrieved_at}
                    try:
                        window(source.data, symbol, count=8)
                        prior = aggregate(source.data, symbol, fields, 4)
                        computed[category]["prior_ttm"] = prior
                        computed[category]["growth_pct"] = {field: (computed[category][field] / prior[field] - 1)*100
                            if computed[category][field] is not None and prior[field] is not None and prior[field] > 0 else None for field in fields}
                    except ValueError as exc:
                        computed[category]["prior_ttm_unavailable_reason"] = str(exc)
                    item = Evidence("", symbol, category + "_ttm", f"{symbol} · calculated TTM {category}", "Calculated from FMP quarterly statements", [computed[category]],
                                    note="Four standardized fiscal quarters summed; this assumes standalone flows unless explicit duration metadata contradicts it. Shares and EPS are not summed; unsupported metrics remain missing. Provider FCF is summed directly; no fabricated OCF/capex substitution.")
                    missing = [field for field in fields if computed[category].get(field) is None]
                    if missing:
                        item.note += " Missing or invalid components: " + ", ".join(missing) + "."
                    if computed[category].get("prior_ttm_unavailable_reason"):
                        item.note += " Prior-TTM growth unavailable: " + computed[category]["prior_ttm_unavailable_reason"]
                except ValueError as exc:
                    item = Evidence("", symbol, category + "_ttm", f"{symbol} · calculated TTM {category}", "Calculated from FMP quarterly statements", [], status="missing", note=str(exc))
                evidence.append(item)
            income, cash = computed.get("income", {}), computed.get("cash_flow", {})
            from .research_metrics import valid_snapshots, match_balance, reconciliation
            snapshots = valid_snapshots(sources["balance_quarterly"].data, symbol)
            latest = snapshots[0] if snapshots else {}
            balance = match_balance(snapshots, income)
            for category, value, note in (
                ("balance_latest", latest, "Latest valid quarterly balance, independent of income availability; never summed."),
                ("balance_ttm", balance, "Matched income TTM-end snapshot; never summed.")):
                value = {**value, "methodology": METHODOLOGY,
                    "source_records": {"category": "balance_quarterly", "url": sources["balance_quarterly"].url,
                                       "retrieved_at": sources["balance_quarterly"].retrieved_at}} if value else {}
                evidence.append(Evidence("", symbol, category, f"{symbol} \u00b7 {category}",
                    "Calculated selection from FMP quarterly statements", [value] if value else [],
                    status="ok" if value else "missing", note=note if value else note + " Matching valid inputs unavailable."))
            diagnostic = reconciliation(sources, symbol)
            evidence.append(Evidence("", symbol, "annual_reconciliation", f"{symbol} \u00b7 quarterly/annual diagnostic",
                "Calculated from FMP statements", diagnostic, note="Differences do not establish a cause and never overwrite quarterly values."))
        return evidence
