from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_financial_statement_tools(fmp_api_key: str):
    def _make_tool(func):
        return StructuredTool.from_function(
            func=func,
            name=func.__name__,
            description=(func.__doc__ or "").strip(),
        )

    client = FMPMCPClient(fmp_api_key)

    def _safe_json_dumps(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False, default=str)

    def _extract_rows(payload: Any) -> List[Dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            if isinstance(data, dict):
                return [data]
            return []
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        return []

    def _first_row(payload: Any) -> Dict[str, Any]:
        rows = _extract_rows(payload)
        return rows[0] if rows else {}

    def _clean_limit(limit: int, default: int = 4, max_value: int = 8) -> int:
        try:
            limit = int(limit)
        except Exception:
            limit = default
        return max(1, min(limit, max_value))

    def _clean_period(period: str) -> str:
        p = (period or "annual").strip().lower()
        if p == "quarterly":
            return "quarter"
        return "quarter" if p == "quarter" else "annual"

    def _pick(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        return {k: d.get(k) for k in keys if k in d}

    def _rows(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        return rows[:limit]

    def get_income_statement_bundle(symbol: str, period: str = "annual", limit: int = 4) -> str:
        """
        Get income statement history and income-statement growth metrics.
        Good for revenue, margins, EPS, operating income, and profitability trend analysis.
        """
        symbol = (symbol or "").upper().strip()
        period = _clean_period(period)
        limit = _clean_limit(limit)

        statements = _extract_rows(client.income_statement(symbol, limit=limit, period=period))
        growth = _extract_rows(client.income_statement_growth(symbol, limit=limit, period=period))
        latest = statements[0] if statements else {}

        payload = {
            "ok": True,
            "tool": "get_income_statement_bundle",
            "symbol": symbol,
            "period": period,
            "statement_count": len(statements),
            "growth_count": len(growth),
            "latest_summary": _pick(
                latest,
                [
                    "date",
                    "fiscalYear",
                    "period",
                    "reportedCurrency",
                    "revenue",
                    "grossProfit",
                    "grossProfitRatio",
                    "operatingIncome",
                    "operatingIncomeRatio",
                    "ebitda",
                    "ebitdaratio",
                    "netIncome",
                    "netIncomeRatio",
                    "eps",
                    "epsDiluted",
                    "researchAndDevelopmentExpenses",
                    "sellingGeneralAndAdministrativeExpenses",
                ],
            ),
            "statements": _rows(statements, limit),
            "growth": _rows(growth, limit),
        }
        return _safe_json_dumps(payload)

    def get_balance_sheet_bundle(symbol: str, period: str = "annual", limit: int = 4) -> str:
        """
        Get balance sheet history and balance-sheet growth metrics.
        Good for debt, liquidity, working capital, equity, and balance sheet strength.
        """
        symbol = (symbol or "").upper().strip()
        period = _clean_period(period)
        limit = _clean_limit(limit)

        statements = _extract_rows(client.balance_sheet(symbol, limit=limit, period=period))
        growth = _extract_rows(client.balance_sheet_growth(symbol, limit=limit, period=period))
        latest = statements[0] if statements else {}

        payload = {
            "ok": True,
            "tool": "get_balance_sheet_bundle",
            "symbol": symbol,
            "period": period,
            "statement_count": len(statements),
            "growth_count": len(growth),
            "latest_summary": _pick(
                latest,
                [
                    "date",
                    "fiscalYear",
                    "period",
                    "reportedCurrency",
                    "cashAndCashEquivalents",
                    "cashAndShortTermInvestments",
                    "inventory",
                    "totalCurrentAssets",
                    "totalAssets",
                    "accountPayables",
                    "shortTermDebt",
                    "longTermDebt",
                    "totalDebt",
                    "totalLiabilities",
                    "totalStockholdersEquity",
                    "netDebt",
                    "workingCapital",
                ],
            ),
            "statements": _rows(statements, limit),
            "growth": _rows(growth, limit),
        }
        return _safe_json_dumps(payload)

    def get_cashflow_bundle(symbol: str, period: str = "annual", limit: int = 4) -> str:
        """
        Get cash flow statement history and cash-flow growth metrics.
        Good for operating cash flow, capex, free cash flow, buybacks, and dividends.
        """
        symbol = (symbol or "").upper().strip()
        period = _clean_period(period)
        limit = _clean_limit(limit)

        statements = _extract_rows(client.cashflow_statement(symbol, limit=limit, period=period))
        growth = _extract_rows(client.cashflow_growth(symbol, limit=limit, period=period))
        owner_earnings = _extract_rows(client.owner_earnings(symbol))
        latest = statements[0] if statements else {}

        payload = {
            "ok": True,
            "tool": "get_cashflow_bundle",
            "symbol": symbol,
            "period": period,
            "statement_count": len(statements),
            "growth_count": len(growth),
            "owner_earnings_count": len(owner_earnings),
            "latest_summary": _pick(
                latest,
                [
                    "date",
                    "fiscalYear",
                    "period",
                    "reportedCurrency",
                    "netIncome",
                    "depreciationAndAmortization",
                    "stockBasedCompensation",
                    "changeInWorkingCapital",
                    "netCashProvidedByOperatingActivities",
                    "capitalExpenditure",
                    "freeCashFlow",
                    "commonStockRepurchased",
                    "commonDividendsPaid",
                    "debtRepayment",
                    "debtIssued",
                ],
            ),
            "statements": _rows(statements, limit),
            "growth": _rows(growth, limit),
            "owner_earnings": _rows(owner_earnings, min(limit, 4)),
        }
        return _safe_json_dumps(payload)

    def get_financial_metrics_bundle(symbol: str, period: str = "annual", limit: int = 4) -> str:
        """
        Get key metrics, ratios, TTM metrics/ratios, financial scores,
        enterprise values, ratings snapshot, and price target summary.
        Good for valuation, profitability, liquidity, leverage, and efficiency analysis.
        """
        symbol = (symbol or "").upper().strip()
        period = _clean_period(period)
        limit = _clean_limit(limit)

        key_metrics = _extract_rows(client.key_metrics(symbol, limit=limit, period=period))
        ratios = _extract_rows(client.metrics_ratios(symbol, limit=limit, period=period))
        key_metrics_ttm = _first_row(client.key_metrics_ttm(symbol))
        ratios_ttm = _first_row(client.metrics_ratios_ttm(symbol))
        scores = _first_row(client.financial_scores(symbol))
        enterprise_values = _extract_rows(client.enterprise_values(symbol, limit=limit, period=period))
        ratings_snapshot = _first_row(client.ratings_snapshot(symbol))
        price_target_summary = _first_row(client.price_target_summary(symbol))

        latest_key_metrics = key_metrics[0] if key_metrics else {}
        latest_ratios = ratios[0] if ratios else {}

        payload = {
            "ok": True,
            "tool": "get_financial_metrics_bundle",
            "symbol": symbol,
            "period": period,
            "highlights": {
                "valuation": {
                    "priceEarningsRatio": latest_ratios.get("priceEarningsRatio"),
                    "priceToSalesRatio": latest_ratios.get("priceToSalesRatio"),
                    "priceToBookRatio": latest_ratios.get("priceToBookRatio"),
                    "enterpriseValueMultiple": latest_ratios.get("enterpriseValueMultiple"),
                    "evToSales": latest_key_metrics.get("evToSales"),
                    "evToOperatingCashFlow": latest_key_metrics.get("evToOperatingCashFlow"),
                },
                "profitability": {
                    "grossProfitMargin": latest_ratios.get("grossProfitMargin"),
                    "operatingProfitMargin": latest_ratios.get("operatingProfitMargin"),
                    "netProfitMargin": latest_ratios.get("netProfitMargin"),
                    "returnOnEquity": latest_ratios.get("returnOnEquity"),
                    "returnOnAssets": latest_ratios.get("returnOnAssets"),
                    "roic": latest_key_metrics.get("roic"),
                },
                "liquidity_and_leverage": {
                    "currentRatio": latest_ratios.get("currentRatio"),
                    "quickRatio": latest_ratios.get("quickRatio"),
                    "cashRatio": latest_ratios.get("cashRatio"),
                    "debtEquityRatio": latest_ratios.get("debtEquityRatio"),
                    "debtRatio": latest_ratios.get("debtRatio"),
                    "interestCoverage": latest_ratios.get("interestCoverage"),
                },
                "efficiency": {
                    "assetTurnover": latest_ratios.get("assetTurnover"),
                    "inventoryTurnover": latest_ratios.get("inventoryTurnover"),
                    "receivablesTurnover": latest_ratios.get("receivablesTurnover"),
                    "cashConversionCycle": latest_key_metrics.get("cashConversionCycle"),
                    "daysOfSalesOutstanding": latest_key_metrics.get("daysOfSalesOutstanding"),
                },
                "ttm_selected": {
                    "priceToSalesRatioTTM": ratios_ttm.get("priceToSalesRatioTTM"),
                    "priceToBookRatioTTM": ratios_ttm.get("priceToBookRatioTTM"),
                    "currentRatioTTM": ratios_ttm.get("currentRatioTTM"),
                    "debtEquityRatioTTM": ratios_ttm.get("debtEquityRatioTTM"),
                    "returnOnEquityTTM": ratios_ttm.get("returnOnEquityTTM"),
                    "roicTTM": key_metrics_ttm.get("roicTTM"),
                    "revenuePerShareTTM": key_metrics_ttm.get("revenuePerShareTTM"),
                    "freeCashFlowPerShareTTM": key_metrics_ttm.get("freeCashFlowPerShareTTM"),
                },
            },
            "key_metrics": _rows(key_metrics, limit),
            "ratios": _rows(ratios, limit),
            "key_metrics_ttm": key_metrics_ttm,
            "ratios_ttm": ratios_ttm,
            "financial_scores": scores,
            "enterprise_values": _rows(enterprise_values, limit),
            "ratings_snapshot": ratings_snapshot,
            "price_target_summary": price_target_summary,
        }
        return _safe_json_dumps(payload)

    def get_financial_growth_bundle(symbol: str, period: str = "annual", limit: int = 4) -> str:
        """
        Get the combined financial growth view plus statement-specific growth tables.
        Good for revenue growth, EPS growth, FCF growth, asset growth, and debt growth analysis.
        """
        symbol = (symbol or "").upper().strip()
        period = _clean_period(period)
        limit = _clean_limit(limit)

        combined = _extract_rows(client.financial_statement_growth(symbol, limit=limit, period=period))
        income_growth = _extract_rows(client.income_statement_growth(symbol, limit=limit, period=period))
        balance_growth = _extract_rows(client.balance_sheet_growth(symbol, limit=limit, period=period))
        cashflow_growth = _extract_rows(client.cashflow_growth(symbol, limit=limit, period=period))
        latest = combined[0] if combined else {}

        payload = {
            "ok": True,
            "tool": "get_financial_growth_bundle",
            "symbol": symbol,
            "period": period,
            "summary": _pick(
                latest,
                [
                    "date",
                    "fiscalYear",
                    "revenueGrowth",
                    "grossProfitGrowth",
                    "ebitdagrowth",
                    "operatingIncomeGrowth",
                    "netIncomeGrowth",
                    "epsgrowth",
                    "freeCashFlowGrowth",
                    "operatingCashFlowGrowth",
                    "assetGrowth",
                    "debtGrowth",
                    "bookValueperShareGrowth",
                ],
            ),
            "combined_growth": _rows(combined, limit),
            "income_statement_growth": _rows(income_growth, limit),
            "balance_sheet_growth": _rows(balance_growth, limit),
            "cashflow_growth": _rows(cashflow_growth, limit),
        }
        return _safe_json_dumps(payload)

    def get_financial_fundamentals_bundle(symbol: str, period: str = "annual", limit: int = 4) -> str:
        """
        Full fundamentals bundle.
        This is the main broad fundamentals tool for holistic company analysis.
        """
        symbol = (symbol or "").upper().strip()
        period = _clean_period(period)
        limit = _clean_limit(limit)

        income = _extract_rows(client.income_statement(symbol, limit=limit, period=period))
        balance = _extract_rows(client.balance_sheet(symbol, limit=limit, period=period))
        cashflow = _extract_rows(client.cashflow_statement(symbol, limit=limit, period=period))
        metrics = _extract_rows(client.key_metrics(symbol, limit=limit, period=period))
        ratios = _extract_rows(client.metrics_ratios(symbol, limit=limit, period=period))
        growth = _extract_rows(client.financial_statement_growth(symbol, limit=limit, period=period))
        scores = _first_row(client.financial_scores(symbol))
        price_target_summary = _first_row(client.price_target_summary(symbol))
        ratings_snapshot = _first_row(client.ratings_snapshot(symbol))

        latest_income = income[0] if income else {}
        latest_balance = balance[0] if balance else {}
        latest_cashflow = cashflow[0] if cashflow else {}
        latest_metrics = metrics[0] if metrics else {}
        latest_ratios = ratios[0] if ratios else {}
        latest_growth = growth[0] if growth else {}

        payload = {
            "ok": True,
            "tool": "get_financial_fundamentals_bundle",
            "symbol": symbol,
            "period": period,
            "summary": {
                "reportedCurrency": latest_income.get("reportedCurrency") or latest_balance.get("reportedCurrency"),
                "income_statement": _pick(
                    latest_income,
                    ["date", "revenue", "grossProfit", "operatingIncome", "ebitda", "netIncome", "eps", "epsDiluted"],
                ),
                "balance_sheet": _pick(
                    latest_balance,
                    [
                        "cashAndCashEquivalents",
                        "inventory",
                        "totalAssets",
                        "shortTermDebt",
                        "longTermDebt",
                        "totalDebt",
                        "totalLiabilities",
                        "totalStockholdersEquity",
                        "workingCapital",
                        "netDebt",
                    ],
                ),
                "cashflow": _pick(
                    latest_cashflow,
                    [
                        "netCashProvidedByOperatingActivities",
                        "capitalExpenditure",
                        "freeCashFlow",
                        "stockBasedCompensation",
                        "commonStockRepurchased",
                        "commonDividendsPaid",
                    ],
                ),
                "ratios_and_metrics": {
                    "currentRatio": latest_ratios.get("currentRatio"),
                    "quickRatio": latest_ratios.get("quickRatio"),
                    "debtEquityRatio": latest_ratios.get("debtEquityRatio"),
                    "grossProfitMargin": latest_ratios.get("grossProfitMargin"),
                    "operatingProfitMargin": latest_ratios.get("operatingProfitMargin"),
                    "netProfitMargin": latest_ratios.get("netProfitMargin"),
                    "returnOnEquity": latest_ratios.get("returnOnEquity"),
                    "returnOnAssets": latest_ratios.get("returnOnAssets"),
                    "roic": latest_metrics.get("roic"),
                    "priceEarningsRatio": latest_ratios.get("priceEarningsRatio"),
                    "priceToSalesRatio": latest_ratios.get("priceToSalesRatio"),
                    "priceToBookRatio": latest_ratios.get("priceToBookRatio"),
                },
                "growth": _pick(
                    latest_growth,
                    [
                        "revenueGrowth",
                        "grossProfitGrowth",
                        "operatingIncomeGrowth",
                        "netIncomeGrowth",
                        "epsgrowth",
                        "freeCashFlowGrowth",
                        "operatingCashFlowGrowth",
                        "assetGrowth",
                        "debtGrowth",
                    ],
                ),
            },
            "income_statement": _rows(income, limit),
            "balance_sheet": _rows(balance, limit),
            "cashflow_statement": _rows(cashflow, limit),
            "key_metrics": _rows(metrics, limit),
            "ratios": _rows(ratios, limit),
            "financial_growth": _rows(growth, limit),
            "financial_scores": scores,
            "ratings_snapshot": ratings_snapshot,
            "price_target_summary": price_target_summary,
        }
        return _safe_json_dumps(payload)

    return [
            _make_tool(get_income_statement_bundle),
            _make_tool(get_balance_sheet_bundle),
            _make_tool(get_cashflow_bundle),
            _make_tool(get_financial_metrics_bundle),
            _make_tool(get_financial_growth_bundle),
            _make_tool(get_financial_fundamentals_bundle),
        ]