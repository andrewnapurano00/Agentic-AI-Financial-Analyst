from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Callable

import numpy as np
import pandas as pd

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient
from .models import Evidence, ResearchRequest, json_safe


def extract_rows(payload) -> list[dict]:
    """Unwrap FMP responses without turning error envelopes into financial rows."""
    if isinstance(payload, dict):
        if payload.get("ok") is False or payload.get("error") or payload.get("Error Message"):
            return []
        for key in ("data", "historical", "results", "result", "structuredContent", "structured_content"):
            if key in payload:
                return extract_rows(payload[key])
        return [payload] if payload else []
    if isinstance(payload, list):
        return [row for item in payload for row in extract_rows(item)]
    return []


def technical_snapshot(rows: list[dict]) -> dict:
    frame = pd.DataFrame(rows)
    if frame.empty or "date" not in frame:
        return {}
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    # Use a single consistent price basis. Do not mix adjusted and raw closes.
    price_col = next((c for c in ("adjClose", "adjclose", "close", "price")
                      if c in frame and pd.to_numeric(frame[c], errors="coerce").notna().all()), None)
    if price_col is None:
        price_col = next((c for c in ("close", "price") if c in frame and pd.to_numeric(frame[c], errors="coerce").notna().any()), None)
    if price_col is None:
        return {}
    frame["value"] = pd.to_numeric(frame[price_col], errors="coerce")
    frame = frame.dropna(subset=["date", "value"]).sort_values("date").drop_duplicates("date")
    frame = frame[frame["value"] > 0]
    if frame.empty:
        return {}
    close = frame["value"].reset_index(drop=True)
    last = float(close.iloc[-1])
    result = {"as_of": frame["date"].iloc[-1].date().isoformat(), "price_basis": price_col,
              "history_start": frame["date"].iloc[0].date().isoformat(),
              "observations": len(close), "last_close": last,
              "return_note": "Price returns on the stated basis; dividends are not independently included."}
    for window in (20, 50, 200):
        result[f"sma_{window}"] = float(close.tail(window).mean()) if len(close) >= window else None
    for name, days in (("return_1m_pct", 21), ("return_3m_pct", 63), ("return_1y_pct", 252)):
        result[name] = (last / float(close.iloc[-days - 1]) - 1) * 100 if len(close) > days else None
    if len(close) > 14:
        delta = close.diff().dropna()
        gains, losses = delta.clip(lower=0), -delta.clip(upper=0)
        gain, loss = float(gains.iloc[:14].mean()), float(losses.iloc[:14].mean())
        for g, l in zip(gains.iloc[14:], losses.iloc[14:]):
            gain, loss = (gain * 13 + g) / 14, (loss * 13 + l) / 14
        result["rsi_14"] = 50.0 if gain == loss == 0 else (100.0 if loss == 0 else 100 - 100 / (1 + gain / loss))
    if len(close) >= 35:
        macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        result.update(macd=float(macd.iloc[-1]), macd_signal=float(macd.ewm(span=9, adjust=False).mean().iloc[-1]))
    if len(close) >= 21:
        result["annualized_volatility_pct"] = float(close.pct_change().dropna().std() * np.sqrt(252) * 100)
        result["max_drawdown_pct"] = float((close / close.cummax() - 1).min() * 100)
    result["series"] = [{"date": d.date().isoformat(), "close": float(p)} for d, p in zip(frame["date"], frame["value"])]
    return json_safe(result)


def financial_trends(evidence: list[Evidence], symbols: list[str]) -> list[Evidence]:
    """Calculate like-for-like growth; quarterly comparisons require prior-year peers."""
    results = []
    for symbol in symbols:
        metrics = []
        for category, fields in (("income", ("revenue", "netIncome", "operatingIncome")),
                                 ("cash_flow", ("netCashProvidedByOperatingActivities", "freeCashFlow"))):
            source = next((e for e in evidence if e.symbol == symbol and e.category == category and e.status == "ok"), None)
            if source is None or not isinstance(source.data, list) or not source.data:
                continue
            rows = sorted(source.data, key=lambda r: str(r.get("date") or ""), reverse=True)
            latest = rows[0]
            try:
                year = int(latest.get("fiscalYear") or latest.get("calendarYear") or str(latest.get("date", ""))[:4])
            except (TypeError, ValueError):
                continue
            previous = next((r for r in rows[1:]
                             if str(r.get("fiscalYear") or r.get("calendarYear") or str(r.get("date", ""))[:4]) == str(year - 1)
                             and r.get("period") == latest.get("period")
                             and r.get("reportedCurrency") == latest.get("reportedCurrency")), None)
            if previous is None:
                continue
            for field in fields:
                try:
                    current, prior = float(latest[field]), float(previous[field])
                    if not np.isfinite(current) or not np.isfinite(prior):
                        continue
                except (KeyError, TypeError, ValueError):
                    continue
                metrics.append({"metric": field, "latest": current, "prior_year": prior,
                                "latest_date": latest.get("date"), "prior_date": previous.get("date"),
                                "period": latest.get("period"), "currency": latest.get("reportedCurrency"),
                                "change": current - prior,
                                "direction": "increase" if current > prior else "decrease" if current < prior else "unchanged",
                                "yoy_pct": (current / prior - 1) * 100 if prior > 0 else None,
                                "source_id": source.id})
        if metrics:
            results.append(Evidence("", symbol, "financial_trends", f"{symbol} · calculated financial trends",
                                    "Calculated from FMP statements", metrics,
                                    note="Same fiscal period and currency, prior-year comparison. Percentage growth is omitted for a nonpositive base."))
    return results


class FinancialDataSource:
    """Use the app's FMP transport; isolate failures by company and dataset."""
    def __init__(self, api_key: str):
        self.client = FMPMCPClient(api_key, retries=0, timeout_seconds=25) if api_key else None

    def collect(self, request: ResearchRequest, progress: Callable[[str], None]) -> list[Evidence]:
        if self.client is None:
            return [Evidence("", s, "financials", "FMP data unavailable", "FMP", {}, status="missing",
                             note="FMP_API_KEY is not configured; use available session context or add the key.") for s in request.symbols]
        client = self.client
        start, end = (date.today() - timedelta(days=550)).isoformat(), date.today().isoformat()
        jobs = []
        for symbol in request.symbols:
            for category, method, kwargs in (
                ("profile", client.profile, {}), ("quote", client.quote, {}),
                ("income", client.income_statement, {"limit": 5, "period": request.period}),
                ("balance", client.balance_sheet, {"limit": 5, "period": request.period}),
                ("cash_flow", client.cashflow_statement, {"limit": 5, "period": request.period}),
                ("income_ttm", client.income_statement_ttm, {}),
                ("balance_ttm", client.balance_sheet_ttm, {}),
                ("cash_flow_ttm", client.cashflow_statement_ttm, {}),
                ("ratios_ttm", client.metrics_ratios_ttm, {}),
                ("metrics_ttm", client.key_metrics_ttm, {}),
                ("estimates", client.analyst_estimates, {"period": request.period, "limit": 4}),
                ("price_targets", client.price_target_consensus, {}),
                ("technicals", client.historical_price_full, {"from_date": start, "to_date": end}),
            ):
                jobs.append((symbol, category, method, kwargs))

        def fetch(job):
            symbol, category, method, kwargs = job
            try:
                payload = method(symbol, **kwargs)
                rows = extract_rows(payload)
                data = technical_snapshot(rows) if category == "technicals" else rows[:5]
                note = "" if data else "No usable data returned. The symbol, provider coverage, or plan entitlement may be unavailable."
                if not data and isinstance(payload, dict):
                    error = str(payload.get("error") or "").lower()
                    if "certificate" in error:
                        note = "FMP HTTPS certificate verification failed. Configure a trusted CA bundle for this Python environment."
                    elif "timeout" in error or "timed out" in error:
                        note = "FMP request timed out. Retry research when the provider is available."
                return Evidence("", symbol, category, f"{symbol} · {category.replace('_', ' ')}", "FMP", data,
                                status="ok" if data else "missing", note=note)
            except Exception:
                return Evidence("", symbol, category, f"{symbol} · {category}", "FMP", {}, status="error",
                                note="This dataset could not be retrieved or normalized.")

        results = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(fetch, job): i for i, job in enumerate(jobs)}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
                progress(f"Collected {len(results)}/{len(jobs)} financial datasets")
        return [results[i] for i in range(len(jobs))]


def comparison_rows(evidence: list[Evidence], symbols: list[str]) -> list[dict]:
    def first(symbol, category):
        item = next((e for e in evidence if e.symbol == symbol and e.category == category and e.status == "ok"), None)
        if item is None:
            return {}
        return item.data[0] if isinstance(item.data, list) and item.data else item.data

    def pick(row, *keys):
        return next((row[k] for k in keys if row.get(k) is not None), None)

    def rows_for(symbol, category):
        item = next((e for e in evidence if e.symbol == symbol and e.category == category and e.status == "ok"), None)
        return [row for row in (item.data if item and isinstance(item.data, list) else []) if isinstance(row, dict)]

    def forward_rows(symbol):
        item = next((e for e in evidence if e.symbol == symbol and e.category == "estimates"
                     and e.status == "ok" and isinstance(e.data, list)), None)
        rows = [row for row in (item.data if item else []) if isinstance(row, dict)]
        rows.sort(key=lambda row: str(row.get("date") or row.get("fiscalYear") or ""))
        future = [row for row in rows if str(row.get("date") or "")[:10] >= date.today().isoformat()]
        selected = future or rows[-2:]
        return (selected + [{}, {}])[:2]

    def ratio(numerator, denominator):
        try:
            top, bottom = float(numerator), float(denominator)
            return top / bottom if np.isfinite(top) and np.isfinite(bottom) and bottom != 0 else None
        except (TypeError, ValueError):
            return None

    def percent_ratio(numerator, denominator):
        value = ratio(numerator, denominator)
        return value * 100 if value is not None else None

    def cagr(symbol, category, field):
        rows = rows_for(symbol, category)
        dated = []
        for row in rows:
            # A multi-year CAGR is meaningful only for annual observations.
            if str(row.get("period") or "").upper() not in {"FY", "ANNUAL"}:
                continue
            try:
                year = int(row.get("fiscalYear") or row.get("calendarYear") or str(row.get("date", ""))[:4])
                value = float(row[field])
                if np.isfinite(value) and value > 0:
                    dated.append((year, value))
            except (KeyError, TypeError, ValueError):
                continue
        dated = sorted(dict(dated).items())
        if len(dated) < 3:
            return None
        latest_year, latest = dated[-1]
        candidates = [(year, value) for year, value in dated[:-1] if 2 <= latest_year - year <= 3]
        if not candidates:
            return None
        first_year, first = candidates[0]
        return ((latest / first) ** (1 / (latest_year - first_year)) - 1) * 100

    result = []
    for symbol in symbols:
        profile, quote, income, balance, cash_flow, income_ttm, balance_ttm, cash_flow_ttm, ratios, metrics, targets, tech = [
            first(symbol, c) for c in
            ("profile", "quote", "income", "balance", "cash_flow", "income_ttm", "balance_ttm", "cash_flow_ttm",
             "ratios_ttm", "metrics_ttm", "price_targets", "technicals")
        ]
        estimate, next_estimate = forward_rows(symbol)
        forward_revenue = pick(estimate, "estimatedRevenueAvg", "revenueAvg", "estimatedRevenue")
        next_revenue = pick(next_estimate, "estimatedRevenueAvg", "revenueAvg", "estimatedRevenue")
        forward_eps = pick(estimate, "estimatedEpsAvg", "epsAvg", "estimatedEps")
        price, market_cap = quote.get("price"), quote.get("marketCap")
        analyst_target = pick(targets, "targetConsensus", "targetMedian", "targetPrice", "priceTarget")
        revenue = income.get("revenue")
        net_income = income.get("netIncome")
        operating_income = income.get("operatingIncome")
        gross_profit = income.get("grossProfit")
        ebitda = pick(income, "ebitda", "EBITDA")
        operating_cash = pick(cash_flow, "netCashProvidedByOperatingActivities", "operatingCashFlow")
        free_cash_flow = cash_flow.get("freeCashFlow")
        capex = pick(cash_flow, "capitalExpenditure", "capitalExpenditures")
        research = pick(income, "researchAndDevelopmentExpenses", "researchAndDevelopment")
        stock_comp = pick(cash_flow, "stockBasedCompensation", "stockBasedCompensationExpense")
        current_balance = balance_ttm or balance
        total_debt = pick(current_balance, "totalDebt", "shortTermDebt")
        total_assets = current_balance.get("totalAssets")
        total_liabilities = current_balance.get("totalLiabilities")
        equity = pick(current_balance, "totalStockholdersEquity", "totalEquity", "stockholdersEquity")
        cash = pick(current_balance, "cashAndShortTermInvestments", "cashAndCashEquivalents", "cashAndCashEquivalentsAtCarryingValue")

        ttm_revenue = income_ttm.get("revenue")
        ttm_gross_profit = income_ttm.get("grossProfit")
        ttm_operating_income = income_ttm.get("operatingIncome")
        ttm_ebitda = pick(income_ttm, "ebitda", "EBITDA")
        ttm_net_income = income_ttm.get("netIncome")
        ttm_operating_cash = pick(cash_flow_ttm, "netCashProvidedByOperatingActivities", "operatingCashFlow")
        ttm_free_cash_flow = cash_flow_ttm.get("freeCashFlow")
        ttm_capex = pick(cash_flow_ttm, "capitalExpenditure", "capitalExpenditures")
        ttm_research = pick(income_ttm, "researchAndDevelopmentExpenses", "researchAndDevelopment")
        ttm_stock_comp = pick(cash_flow_ttm, "stockBasedCompensation", "stockBasedCompensationExpense")

        statement_gross_margin = ratio(gross_profit, revenue)
        statement_operating_margin = ratio(operating_income, revenue)
        statement_net_margin = ratio(net_income, revenue)
        statement_ebitda_margin = ratio(ebitda, revenue)
        statement_ocf_margin = ratio(operating_cash, revenue)
        statement_fcf_margin = ratio(free_cash_flow, revenue)
        statement_cash_conversion = ratio(operating_cash, net_income)
        statement_research_intensity = percent_ratio(research, revenue)
        statement_stock_comp_intensity = percent_ratio(stock_comp, revenue)
        statement_capex_intensity = percent_ratio(abs(capex) if isinstance(capex, (int, float)) else capex, revenue)
        ttm_gross_margin = ratio(ttm_gross_profit, ttm_revenue)
        ttm_operating_margin = ratio(ttm_operating_income, ttm_revenue)
        ttm_net_margin = ratio(ttm_net_income, ttm_revenue)
        ttm_ebitda_margin = ratio(ttm_ebitda, ttm_revenue)
        ttm_ocf_margin = ratio(ttm_operating_cash, ttm_revenue)
        ttm_fcf_margin = ratio(ttm_free_cash_flow, ttm_revenue)
        ttm_cash_conversion = ratio(ttm_operating_cash, ttm_net_income)
        ttm_research_intensity = percent_ratio(ttm_research, ttm_revenue)
        ttm_stock_comp_intensity = percent_ratio(ttm_stock_comp, ttm_revenue)
        ttm_capex_intensity = percent_ratio(abs(ttm_capex) if isinstance(ttm_capex, (int, float)) else ttm_capex, ttm_revenue)
        # Ratio endpoints remain a useful fallback when the provider does not return TTM statements.
        ttm_gross_margin = ttm_gross_margin if ttm_gross_margin is not None else pick(ratios, "grossProfitMarginTTM", "grossMarginTTM")
        ttm_operating_margin = ttm_operating_margin if ttm_operating_margin is not None else pick(ratios, "operatingProfitMarginTTM", "operatingMarginTTM")
        ttm_net_margin = ttm_net_margin if ttm_net_margin is not None else pick(ratios, "netProfitMarginTTM", "netMarginTTM")
        ttm_ebitda_margin = ttm_ebitda_margin if ttm_ebitda_margin is not None else pick(ratios, "ebitdaMarginTTM")
        debt_assets = pick(ratios, "debtToAssetsRatioTTM", "debtToAssetsTTM")
        debt_assets = debt_assets if debt_assets is not None else ratio(total_debt, total_assets)
        debt_capital = pick(ratios, "debtToCapitalRatioTTM", "debtToCapitalTTM")
        debt_capital = debt_capital if debt_capital is not None else ratio(total_debt, (total_debt or 0) + (equity or 0))
        latest_price = tech.get("last_close") or price
        row = {
            "Ticker": symbol, "Company": profile.get("companyName"), "Sector": profile.get("sector"),
            "Industry": profile.get("industry"),
            "Quote currency": profile.get("currency"), "Statement currency": income.get("reportedCurrency"),
            "Price": price, "Market cap": market_cap,
            "Statement date": income.get("date"), "Statement period": income.get("period"),
            "TTM through": income_ttm.get("date") or cash_flow_ttm.get("date"),
            "TTM currency": income_ttm.get("reportedCurrency") or cash_flow_ttm.get("reportedCurrency"),
            "Balance sheet date": current_balance.get("date"),
            "Revenue (latest period)": revenue, "Gross profit (latest period)": gross_profit,
            "Operating income (latest period)": operating_income, "EBITDA (latest period)": ebitda,
            "Net income (latest period)": net_income, "Operating cash flow (latest period)": operating_cash,
            "Capital expenditure (latest period)": capex, "Free cash flow (latest period)": free_cash_flow,
            "Gross margin (latest period)": statement_gross_margin,
            "Operating margin (latest period)": statement_operating_margin,
            "EBITDA margin (latest period)": statement_ebitda_margin,
            "Net margin (latest period)": statement_net_margin,
            "OCF margin (latest period)": statement_ocf_margin,
            "FCF margin (latest period)": statement_fcf_margin,
            "Cash conversion (latest period)": statement_cash_conversion,
            "R&D as % revenue (latest period)": statement_research_intensity,
            "Stock-based comp % revenue (latest period)": statement_stock_comp_intensity,
            "Capex to revenue (latest period)": statement_capex_intensity,
            "Revenue (TTM)": ttm_revenue, "Gross profit (TTM)": ttm_gross_profit,
            "Operating income (TTM)": ttm_operating_income, "EBITDA (TTM)": ttm_ebitda,
            "Net income (TTM)": ttm_net_income, "Operating cash flow (TTM)": ttm_operating_cash,
            "Capital expenditure (TTM)": ttm_capex, "Free cash flow (TTM)": ttm_free_cash_flow,
            "Gross margin (TTM)": ttm_gross_margin, "Operating margin (TTM)": ttm_operating_margin,
            "EBITDA margin (TTM)": ttm_ebitda_margin, "Net margin (TTM)": ttm_net_margin,
            "OCF margin (TTM)": ttm_ocf_margin, "FCF margin (TTM)": ttm_fcf_margin,
            "Cash conversion (TTM)": ttm_cash_conversion,
            "R&D as % revenue (TTM)": ttm_research_intensity,
            "Stock-based comp % revenue (TTM)": ttm_stock_comp_intensity,
            "Capex to revenue (TTM)": ttm_capex_intensity,
            "P/E (TTM)": pick(ratios, "priceToEarningsRatioTTM", "priceEarningsRatioTTM", "peRatioTTM"),
            "P/S (TTM)": pick(ratios, "priceToSalesRatioTTM", "priceSalesRatioTTM", "priceToSalesTTM"),
            "P/B (TTM)": pick(ratios, "priceToBookRatioTTM", "priceBookValueRatioTTM", "priceToBookTTM"),
            "EV/EBITDA (TTM)": pick(metrics, "enterpriseValueOverEBITDATTM", "evToEBITDATTM", "evToEBITDA",
                                      "enterpriseValueMultipleTTM", "enterpriseValueMultiple"),
            "EV/Sales (TTM)": pick(metrics, "evToSalesTTM", "enterpriseValueOverRevenueTTM", "evToSales"),
            "FCF yield (TTM, fraction)": pick(ratios, "freeCashFlowYieldTTM", "freeCashFlowYield"),
            "Net margin (TTM, fraction)": ttm_net_margin,
            "Debt/equity (TTM)": pick(ratios, "debtToEquityRatioTTM", "debtEquityRatioTTM", "debtToEquityTTM"),
            "Estimate period": estimate.get("date") or estimate.get("fiscalYear"),
            "Forward revenue": forward_revenue,
            "Forward revenue next period": next_revenue,
            "Forward revenue growth (%)": (ratio(next_revenue, forward_revenue) - 1) * 100
            if ratio(next_revenue, forward_revenue) is not None else None,
            "Forward EPS": forward_eps,
            "Forward EBITDA": pick(estimate, "estimatedEbitdaAvg", "ebitdaAvg", "estimatedEbitda"),
            "Forward net income": pick(estimate, "estimatedNetIncomeAvg", "netIncomeAvg", "estimatedNetIncome"),
            "Forward P/E": ratio(price, forward_eps),
            "Forward P/S": ratio(market_cap, forward_revenue),
            "Analyst target": analyst_target,
            "Target upside (%)": (ratio(analyst_target, price) - 1) * 100
            if ratio(analyst_target, price) is not None else None,
            "Price date": tech.get("as_of"), "RSI (14)": tech.get("rsi_14"), "SMA 50": tech.get("sma_50"),
            "SMA 200": tech.get("sma_200"), "3M price return (%)": tech.get("return_3m_pct"),
            "1Y price return (%)": tech.get("return_1y_pct"),
            # Names below intentionally match the Equity Research sector registry.
            "Revenue CAGR 3Y": cagr(symbol, "income", "revenue"),
            "Net Income CAGR 3Y": cagr(symbol, "income", "netIncome"),
            "FCF CAGR 3Y": cagr(symbol, "cash_flow", "freeCashFlow"),
            "Forward Revenue Growth FY+1": (ratio(next_revenue, forward_revenue) - 1) * 100
            if ratio(next_revenue, forward_revenue) is not None else None,
            "Forward Revenue Next FY": forward_revenue,
            "Forward EPS Next FY": forward_eps,
            "Forward EBITDA Next FY": pick(estimate, "estimatedEbitdaAvg", "ebitdaAvg", "estimatedEbitda"),
            "Forward Net Income Next FY": pick(estimate, "estimatedNetIncomeAvg", "netIncomeAvg", "estimatedNetIncome"),
            "Latest Gross Margin": statement_gross_margin,
            "Latest Operating Margin": statement_operating_margin,
            "Latest EBITDA Margin": statement_ebitda_margin,
            "Latest Net Margin": statement_net_margin,
            "OCF Margin": ttm_ocf_margin if ttm_ocf_margin is not None else statement_ocf_margin,
            "FCF Margin": ttm_fcf_margin if ttm_fcf_margin is not None else statement_fcf_margin,
            "Cash Conversion": ttm_cash_conversion if ttm_cash_conversion is not None else statement_cash_conversion,
            "Income Quality": ttm_cash_conversion if ttm_cash_conversion is not None else statement_cash_conversion,
            "R&D as % Revenue": ttm_research_intensity if ttm_research_intensity is not None else statement_research_intensity,
            "Stock-Based Comp % Revenue": ttm_stock_comp_intensity if ttm_stock_comp_intensity is not None else statement_stock_comp_intensity,
            "Capex to Revenue": ttm_capex_intensity if ttm_capex_intensity is not None else statement_capex_intensity,
            "ROE": pick(ratios, "returnOnEquityTTM", "returnOnEquity"),
            "ROA": pick(ratios, "returnOnAssetsTTM", "returnOnAssets"),
            "ROIC": pick(ratios, "returnOnInvestedCapitalTTM", "returnOnCapitalEmployedTTM", "returnOnInvestedCapital"),
            "Current Ratio": pick(ratios, "currentRatioTTM", "currentRatio"),
            "Debt to Equity": pick(ratios, "debtToEquityRatioTTM", "debtEquityRatioTTM", "debtToEquityTTM"),
            "Debt / Assets": debt_assets,
            "Debt / Capital": debt_capital,
            "Liabilities to Assets": ratio(total_liabilities, total_assets),
            "Net Debt / EBITDA": ratio((total_debt or 0) - (cash or 0), ttm_ebitda),
            "Debt Service Coverage": pick(ratios, "debtServiceCoverageRatioTTM", "debtServiceCoverageRatio"),
            "Book Value / Share": pick(metrics, "bookValuePerShareTTM", "bookValuePerShare"),
            "Tangible Book Value / Share": pick(metrics, "tangibleBookValuePerShareTTM", "tangibleBookValuePerShare"),
            "Dividend Yield": pick(ratios, "dividendYieldTTM", "dividendYield"),
            "Dividend Payout Ratio": pick(ratios, "dividendPayoutRatioTTM", "payoutRatioTTM", "payoutRatio"),
            "Inventory Days": pick(ratios, "daysOfInventoryOutstandingTTM", "inventoryDaysTTM"),
            "Cash Conversion Cycle Days": pick(ratios, "cashConversionCycleTTM", "cashConversionCycle"),
            "P/E TTM": pick(ratios, "priceToEarningsRatioTTM", "priceEarningsRatioTTM", "peRatioTTM"),
            "P/B TTM": pick(ratios, "priceToBookRatioTTM", "priceBookValueRatioTTM", "priceToBookTTM"),
            "P/S TTM": pick(ratios, "priceToSalesRatioTTM", "priceSalesRatioTTM", "priceToSalesTTM"),
            "P/FCF TTM": pick(ratios, "priceToFreeCashFlowsRatioTTM", "priceToFreeCashFlowRatioTTM", "pfcfRatioTTM"),
            "Forward P/E": ratio(price, forward_eps),
            "Forward P/S": ratio(market_cap, forward_revenue),
            "Earnings Yield": pick(ratios, "earningsYieldTTM", "earningsYield"),
            "FCF Yield": pick(ratios, "freeCashFlowYieldTTM", "freeCashFlowYield"),
            "EV / EBITDA": pick(metrics, "enterpriseValueOverEBITDATTM", "evToEBITDATTM", "evToEBITDA",
                                "enterpriseValueMultipleTTM", "enterpriseValueMultiple"),
            "EV / Sales": pick(metrics, "evToSalesTTM", "enterpriseValueOverRevenueTTM", "evToSales"),
            "EV / FCF": pick(metrics, "evToFreeCashFlowTTM", "enterpriseValueOverFreeCashFlowTTM"),
            "Price Target Upside": (ratio(analyst_target, price) - 1) * 100
            if ratio(analyst_target, price) is not None else None,
            "1Y Return": tech.get("return_1y_pct"),
            "% From SMA 50": (ratio(latest_price, tech.get("sma_50")) - 1) * 100
            if ratio(latest_price, tech.get("sma_50")) is not None else None,
            "% From SMA 200": (ratio(latest_price, tech.get("sma_200")) - 1) * 100
            if ratio(latest_price, tech.get("sma_200")) is not None else None,
            "RSI 14": tech.get("rsi_14"),
        }
        from .sector import map_sector_to_framework
        row["Sector framework"] = map_sector_to_framework(profile.get("sector"), profile.get("industry"))
        result.append(row)
    return json_safe(result)
