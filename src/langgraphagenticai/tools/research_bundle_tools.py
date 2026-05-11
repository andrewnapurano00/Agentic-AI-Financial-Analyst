from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_research_bundle_tools(fmp_api_key: str):
    """Build broad MCP-backed stock research bundle tools for complex prompts."""

    def _make_tool(func):
        return StructuredTool.from_function(
            func=func,
            name=func.__name__,
            description=(func.__doc__ or "").strip() or func.__name__,
        )

    client = FMPMCPClient(fmp_api_key)

    def _safe_json_dumps(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False, default=str)

    def _extract_rows(payload: Any) -> List[Dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, str):
            try:
                return _extract_rows(json.loads(payload))
            except Exception:
                return []
        if isinstance(payload, list):
            rows: List[Dict[str, Any]] = []
            for item in payload:
                rows.extend(_extract_rows(item))
            return rows
        if isinstance(payload, dict):
            for key in ("data", "result", "results", "output", "content", "structured_content", "structuredContent"):
                if key in payload and payload.get(key) is not None:
                    nested = _extract_rows(payload.get(key))
                    if nested:
                        return nested
            return [payload]
        return []

    def _clean_symbols(symbols: str) -> List[str]:
        if not symbols:
            return []
        return [s.strip().upper() for s in str(symbols).replace(";", ",").split(",") if s.strip()]

    def _first(payload: Any) -> Dict[str, Any]:
        rows = _extract_rows(payload)
        return rows[0] if rows else {}

    def get_full_stock_analysis_bundle(symbol: str, period: str = "annual") -> str:
        """
        Get a broad stock analysis bundle for one ticker: quote, profile, peers, financial statements, TTM ratios, analyst estimates,
        ratings, price targets, DCF, company earnings, dividends, and ESG ratings.
        Use this for full investment analysis prompts where the agent needs many data categories at once.
        """
        symbol = (symbol or "").strip().upper()
        period = "quarter" if str(period).lower() in {"quarter", "quarterly", "q"} else "annual"
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_full_stock_analysis_bundle", "error": "Ticker symbol is required."})

        payload = {
            "ok": True,
            "tool": "get_full_stock_analysis_bundle",
            "symbol": symbol,
            "period": period,
            "quote": _first(client.quote(symbol)),
            "profile": _first(client.profile(symbol)),
            "peers": _extract_rows(client.peers(symbol)),
            "market_cap": _extract_rows(client.market_cap(symbol)),
            "shares_float": _extract_rows(client.shares_float(symbol)),
            "income_statement": _extract_rows(client.income_statement(symbol, limit=4, period=period))[:4],
            "balance_sheet": _extract_rows(client.balance_sheet(symbol, limit=4, period=period))[:4],
            "cash_flow_statement": _extract_rows(client.cashflow_statement(symbol, limit=4, period=period))[:4],
            "ratios_ttm": _extract_rows(client.metrics_ratios_ttm(symbol))[:1],
            "key_metrics_ttm": _extract_rows(client.key_metrics_ttm(symbol))[:1],
            "financial_scores": _extract_rows(client.financial_scores(symbol))[:1],
            "income_growth": _extract_rows(client.income_statement_growth(symbol, limit=4, period=period))[:4],
            "analyst_estimates": _extract_rows(client.analyst_estimates(symbol, period=period, limit=8))[:8],
            "ratings_snapshot": _extract_rows(client.ratings_snapshot(symbol)),
            "price_target_consensus": _extract_rows(client.price_target_consensus(symbol)),
            "price_target_summary": _extract_rows(client.price_target_summary(symbol)),
            "grades_summary": _extract_rows(client.grades_summary(symbol)),
            "dcf_advanced": _extract_rows(client.call("discountedCashFlow", "dcf-advanced", symbol=symbol)),
            "dcf_levered": _extract_rows(client.call("discountedCashFlow", "dcf-levered", symbol=symbol)),
            "earnings_history": _extract_rows(client.call("calendar", "earnings-company", symbol=symbol, limit=12))[:12],
            "dividend_history": _extract_rows(client.call("calendar", "dividends-company", symbol=symbol, limit=12))[:12],
            "esg_ratings": _extract_rows(client.call("ESG", "esg-ratings", symbol=symbol)),
            "mcp_note": "Large bundle; use targeted tools for deeper/raw detail if needed.",
        }
        payload["ok"] = any(bool(v) for k, v in payload.items() if k not in {"ok", "tool", "symbol", "period", "mcp_note"})
        return _safe_json_dumps(payload)

    def compare_stocks_research_bundle(symbols: str, period: str = "annual") -> str:
        """
        Compare multiple stocks across quote, company profile, TTM valuation/profitability, analyst estimates, ratings, price targets, and DCF.
        Input symbols as a comma-separated string, for example 'AAPL,MSFT,NVDA'.
        Use this for complex stock comparison prompts.
        """
        symbols_list = _clean_symbols(symbols)
        period = "quarter" if str(period).lower() in {"quarter", "quarterly", "q"} else "annual"
        if not symbols_list:
            return _safe_json_dumps({"ok": False, "tool": "compare_stocks_research_bundle", "error": "At least one ticker symbol is required."})
        symbols_list = symbols_list[:8]
        results: List[Dict[str, Any]] = []
        for symbol in symbols_list:
            quote = _first(client.quote(symbol))
            profile = _first(client.profile(symbol))
            ratios = _first(client.metrics_ratios_ttm(symbol))
            key_metrics = _first(client.key_metrics_ttm(symbol))
            estimates = _extract_rows(client.analyst_estimates(symbol, period=period, limit=4))[:4]
            price_target = _extract_rows(client.price_target_consensus(symbol))
            ratings = _extract_rows(client.ratings_snapshot(symbol))
            dcf = _extract_rows(client.call("discountedCashFlow", "dcf-advanced", symbol=symbol))
            results.append({
                "symbol": symbol,
                "companyName": profile.get("companyName") or quote.get("name"),
                "sector": profile.get("sector"),
                "industry": profile.get("industry"),
                "price": quote.get("price"),
                "marketCap": quote.get("marketCap") or profile.get("mktCap"),
                "pe": quote.get("pe") or ratios.get("priceEarningsRatioTTM") or ratios.get("peRatioTTM"),
                "eps": quote.get("eps"),
                "revenuePerShareTTM": key_metrics.get("revenuePerShareTTM"),
                "netProfitMarginTTM": ratios.get("netProfitMarginTTM"),
                "operatingMarginTTM": ratios.get("operatingProfitMarginTTM") or ratios.get("operatingMarginTTM"),
                "returnOnEquityTTM": ratios.get("returnOnEquityTTM"),
                "debtToEquityTTM": ratios.get("debtEquityRatioTTM") or ratios.get("debtToEquityTTM"),
                "analyst_estimates": estimates,
                "price_target_consensus": price_target,
                "ratings_snapshot": ratings,
                "dcf_advanced": dcf,
            })
        return _safe_json_dumps({
            "ok": True,
            "tool": "compare_stocks_research_bundle",
            "symbols": symbols_list,
            "period": period,
            "comparison": results,
            "mcp_note": "Use this bundle as the primary source for multi-stock investment comparisons.",
        })

    return [
        _make_tool(get_full_stock_analysis_bundle),
        _make_tool(compare_stocks_research_bundle),
    ]
