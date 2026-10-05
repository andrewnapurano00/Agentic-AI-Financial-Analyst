"""V2 quarterly-only financial collection; V1 retains its provider TTM path."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, timedelta

from langgraphagenticai.providers.fmp_http import get_fmp_json
from .data import FinancialDataSource, extract_rows, technical_snapshot, comparison_rows
from .models import Evidence, parse_symbols
from .quarterly_ttm import METHODOLOGY, INCOME_FIELDS, CASH_FIELDS, aggregate, derived_ratios, number, same_window, window


class QuarterlyFinancialDataSource(FinancialDataSource):
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
                ("estimates", "analyst-estimates", {"period": request.period, "limit": 4}),
                ("price_targets", "price-target-consensus", {}),
                ("technicals", "historical-price-eod/full", {"from": (date.today()-timedelta(days=550)).isoformat(), "to": date.today().isoformat()}),
            ):
                jobs.append((symbol, category, route, params))
            if request.period == "annual":
                for category, route in (("income", "income-statement"), ("balance", "balance-sheet-statement"), ("cash_flow", "cash-flow-statement")):
                    jobs.append((symbol, category, route, {"period": "annual", "limit": 5}))

        def fetch(job):
            symbol, category, route, params = job
            url = "https://financialmodelingprep.com/stable/" + route
            try:
                rows = extract_rows(get_fmp_json(url, api_key=self.api_key, params={"symbol": symbol, **params}))
                if category in {"profile", "quote"}:
                    if not rows or any(row.get("symbol") != symbol for row in rows):
                        return Evidence("", symbol, category, f"{symbol} · {category}", "FMP", [], status="missing", url=url,
                                        note="Provider security identity is missing or does not match the requested ticker; records excluded.")
                data = technical_snapshot(rows) if category == "technicals" else rows[:params.get("limit", 5)]
                return Evidence("", symbol, category, f"{symbol} · {category}", "FMP", data, url=url,
                                status="ok" if data else "missing", note="" if data else "No usable provider records; coverage or entitlement may be unavailable.")
            except Exception:
                return Evidence("", symbol, category, f"{symbol} · {category}", "FMP", [], status="error", url=url,
                                note="Dataset retrieval failed; successful datasets remain available.")
        with ThreadPoolExecutor(max_workers=5) as pool:
            evidence = list(pool.map(fetch, jobs))
        progress(f"Collected {len(jobs)} bounded quarterly-only financial datasets")
        if request.period == "quarter":
            evidence += [replace(e, category=e.category.removesuffix("_quarterly")) for e in evidence if e.category.endswith("_quarterly")]
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
                                    note="Four fiscal quarters summed. Shares and EPS are not summed; unsupported metrics remain missing.")
                    missing = [field for field in fields if computed[category].get(field) is None]
                    if missing:
                        item.note += " Missing or invalid components: " + ", ".join(missing) + "."
                    if computed[category].get("prior_ttm_unavailable_reason"):
                        item.note += " Prior-TTM growth unavailable: " + computed[category]["prior_ttm_unavailable_reason"]
                except ValueError as exc:
                    item = Evidence("", symbol, category + "_ttm", f"{symbol} · calculated TTM {category}", "Calculated from FMP quarterly statements", [], status="missing", note=str(exc))
                evidence.append(item)
            income, cash = computed.get("income", {}), computed.get("cash_flow", {})
            # Use one unambiguous end-of-window balance snapshot, never summed balances.
            latest_quarter = next(iter(income.get("quarters", [])), {})
            latest_year = latest_quarter.get("fiscalYear") or latest_quarter.get("calendarYear")
            balances = [r for r in sources["balance_quarterly"].data if r.get("date") == income.get("date") and r.get("symbol") == symbol and r.get("reportedCurrency") == income.get("reportedCurrency") and r.get("period") == latest_quarter.get("period") and str(r.get("fiscalYear") or r.get("calendarYear")) == str(latest_year)]
            balance = dict(balances[0]) if balances and all(r == balances[0] for r in balances) else {}
            balance_available = bool(balance)
            balance["methodology"] = METHODOLOGY
            balance["source_records"] = {"category": "balance_quarterly", "url": sources["balance_quarterly"].url, "retrieved_at": sources["balance_quarterly"].retrieved_at}
            evidence.append(Evidence("", symbol, "balance_ttm", f"{symbol} · matched balance snapshot", "Calculated selection from FMP quarterly statements", [balance] if balance_available else [], status="ok" if balance_available else "missing", note="Point-in-time balance at income TTM end; balances are not additive."))
            quote = next(iter(sources["quote"].data), {})
            profile = next(iter(sources["profile"].data), {})
            prior_balances = [r for r in sources["balance_quarterly"].data if r.get("symbol") == symbol and r.get("reportedCurrency") == income.get("reportedCurrency") and r.get("period") == latest_quarter.get("period") and str(r.get("fiscalYear") or r.get("calendarYear")) == str(int(latest_year)-1)] if latest_year else []
            prior_balance = dict(prior_balances[0]) if prior_balances and all(r == prior_balances[0] for r in prior_balances) else {}
            ratios, metrics = derived_ratios(income, cash, balance, quote, quote.get("currency") or profile.get("currency"), prior_balance)
            for category, data in (("ratios_ttm", ratios), ("metrics_ttm", metrics)):
                data.update(methodology=METHODOLOGY, date=income.get("date"), reportedCurrency=income.get("reportedCurrency"), quarters=income.get("quarters"),
                    source_records={k: {"url": v.url, "retrieved_at": v.retrieved_at} for k, v in sources.items() if k in {"income_quarterly", "cash_flow_quarterly", "balance_quarterly", "quote", "profile"}},
                    formula="Positive-denominator ratios of calculated TTM flows / matched end balances; valuation uses quote market capitalization.", quote_as_of=quote.get("timestamp"),
                    limitations="Simplified EV = market cap + total debt - cash equivalents; excludes preferred/minority interests. Quote and statement dates differ. No EPS/per-share/ROIC/provider formula equivalence.")
                available = any(number(v) is not None for k, v in data.items() if k not in {"date", "quote_as_of"})
                evidence.append(Evidence("", symbol, category, f"{symbol} · calculated {category}", "Calculated from FMP quarterly statements and quote", [data],
                                         status="ok" if available else "missing", note="" if available else "No defensible ratios: check aligned statements, quote currency and positive denominators."))
        return evidence


def quarterly_comparison_rows(evidence, symbols):
    """Prevent the legacy comparison fallback from inventing missing balance inputs."""
    rows = comparison_rows(evidence, symbols)
    for row in rows:
        def first(category):
            e = next((e for e in evidence if e.symbol == row["Ticker"] and e.category == category and e.status == "ok"), None)
            return e.data[0] if e and isinstance(e.data, list) and e.data else {}
        income, cash, balance = first("income_ttm"), first("cash_flow_ttm"), first("balance_ttm")
        debt, cash_eq, equity = (number(balance.get(k)) for k in ("totalDebt", "cashAndCashEquivalents", "totalStockholdersEquity"))
        aligned = bool(balance.get("date") and balance.get("date") == income.get("date") and balance.get("reportedCurrency") == income.get("reportedCurrency"))
        from .quarterly_ttm import divide
        for field, label, alias in (("grossProfit", "Gross margin", "Latest Gross Margin"),
                                    ("operatingIncome", "Operating margin", "Latest Operating Margin"),
                                    ("ebitda", "EBITDA margin", "Latest EBITDA Margin"),
                                    ("netIncome", "Net margin", "Latest Net Margin")):
            row[label + " (TTM)"] = divide(income.get(field), income.get("revenue"))
            latest = first("income")
            row[label + " (latest period)"] = divide(latest.get(field), latest.get("revenue"))
            row[alias] = row[label + " (latest period)"]
        row["Net margin (TTM, fraction)"] = row["Net margin (TTM)"]
        research = divide(income.get("researchAndDevelopmentExpenses"), income.get("revenue"))
        row["R&D as % revenue (TTM)"] = research * 100 if research is not None else None
        latest_research = divide(first("income").get("researchAndDevelopmentExpenses"), first("income").get("revenue"))
        row["R&D as % revenue (latest period)"] = latest_research * 100 if latest_research is not None else None
        row["R&D as % Revenue"] = row["R&D as % revenue (TTM)"] if income else row["R&D as % revenue (latest period)"]
        for category in ("income", "cash_flow"):
            source = first(category + "_ttm")
            for metric, value in source.get("growth_pct", {}).items():
                row[f"{metric} TTM growth (%)"] = value
        row["TTM fiscal quarters"] = income.get("quarters")
        row["Cash flow TTM through"] = cash.get("date")
        row["Cash flow TTM currency"] = cash.get("reportedCurrency")
        # Latest-period cash flows must also match the latest income period.
        latest_income, latest_cash = first("income"), first("cash_flow")
        row["Cash flow statement date"] = latest_cash.get("date")
        row["Cash flow statement currency"] = latest_cash.get("reportedCurrency")
        latest_aligned = bool(latest_income.get("date") and latest_income.get("date") == latest_cash.get("date") and latest_income.get("reportedCurrency") == latest_cash.get("reportedCurrency") and latest_income.get("period") == latest_cash.get("period"))
        if not latest_aligned:
            for key in ("OCF margin (latest period)", "FCF margin (latest period)", "Cash conversion (latest period)", "Stock-based comp % revenue (latest period)", "Capex to revenue (latest period)"):
                row[key] = None
        row["Debt / Capital"] = divide(debt, debt + equity) if aligned and debt is not None and equity is not None else None
        row["Net Debt / EBITDA"] = divide(debt - cash_eq, income.get("ebitda")) if aligned and debt is not None and cash_eq is not None else None
        row["Debt / Assets"] = divide(debt, balance.get("totalAssets")) if aligned else None
        row["Liabilities to Assets"] = divide(balance.get("totalLiabilities"), balance.get("totalAssets")) if aligned else None
        flow_aligned = same_window(income, cash)
        ocf = cash.get("netCashProvidedByOperatingActivities")
        if ocf is None:
            ocf = cash.get("operatingCashFlow")
        capex = number(cash.get("capitalExpenditure"))
        derived = {
            "OCF margin (TTM)": divide(ocf, income.get("revenue")),
            "FCF margin (TTM)": divide(cash.get("freeCashFlow"), income.get("revenue")),
            "Cash conversion (TTM)": divide(ocf, income.get("netIncome")),
            "Stock-based comp % revenue (TTM)": divide(cash.get("stockBasedCompensation"), income.get("revenue")),
            "Capex to revenue (TTM)": divide(abs(capex) if capex is not None else None, income.get("revenue")),
        }
        for key, value in derived.items():
            is_percent = "%" in key or key == "Capex to revenue (TTM)"
            row[key] = value * 100 if value is not None and is_percent else value
        for key, ttm in (("OCF Margin", "OCF margin (TTM)"), ("FCF Margin", "FCF margin (TTM)"), ("Cash Conversion", "Cash conversion (TTM)"),
                         ("Income Quality", "Cash conversion (TTM)"), ("Stock-Based Comp % Revenue", "Stock-based comp % revenue (TTM)"), ("Capex to Revenue", "Capex to revenue (TTM)")):
            row[key] = row[ttm] if flow_aligned else None
        if not same_window(income, cash):
            for key in ("OCF margin (TTM)", "FCF margin (TTM)", "Cash conversion (TTM)", "Stock-based comp % revenue (TTM)", "Capex to revenue (TTM)", "OCF Margin", "FCF Margin", "Cash Conversion", "Income Quality", "Stock-Based Comp % Revenue", "Capex to Revenue"):
                row[key] = None
        row["TTM methodology"] = METHODOLOGY
        for category, field, label in (("income", "revenue", "Revenue CAGR 3Y"), ("income", "netIncome", "Net Income CAGR 3Y"), ("cash_flow", "freeCashFlow", "FCF CAGR 3Y")):
            source = next((e for e in evidence if e.symbol == row["Ticker"] and e.category == category and e.status == "ok"), None)
            annual = [r for r in source.data if isinstance(r, dict) and r.get("period") in {"FY", "ANNUAL"}] if source and isinstance(source.data, list) else []
            currencies = {r.get("reportedCurrency") for r in annual}
            if not annual or len(currencies) != 1 or None in currencies or "" in currencies:
                row[label] = None
    return rows
