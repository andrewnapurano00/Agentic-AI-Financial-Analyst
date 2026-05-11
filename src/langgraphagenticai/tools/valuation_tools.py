from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_valuation_tools(fmp_api_key: str):
    """Build MCP-backed DCF and valuation tools."""

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

    def _clean_symbol(symbol: str) -> str:
        return (symbol or "").strip().upper()

    def _mcp_payload(tool_name: str, endpoint: str, **params: Any) -> Dict[str, Any]:
        return client.call(tool_name, endpoint, **{k: v for k, v in params.items() if v is not None and v != ""})

    def get_dcf_valuation(symbol: str) -> str:
        """
        Get the standard advanced DCF valuation for a ticker.
        Use this for intrinsic value, DCF value, and undervalued/overvalued questions.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_dcf_valuation", "error": "Ticker symbol is required."})
        payload = _mcp_payload("discountedCashFlow", "dcf-advanced", symbol=symbol)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_dcf_valuation", "symbol": symbol, "dcf_advanced": rows, "raw": payload if not rows else None})

    def get_levered_dcf(symbol: str) -> str:
        """
        Get levered DCF valuation for a ticker.
        Use this to compare standard DCF and levered DCF intrinsic value.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_levered_dcf", "error": "Ticker symbol is required."})
        payload = _mcp_payload("discountedCashFlow", "dcf-levered", symbol=symbol)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_levered_dcf", "symbol": symbol, "dcf_levered": rows, "raw": payload if not rows else None})

    def get_custom_dcf_valuation(
        symbol: str,
        revenueGrowthPct: Optional[float] = None,
        ebitdaPct: Optional[float] = None,
        taxRate: Optional[float] = None,
        longTermGrowthRate: Optional[float] = None,
        costOfDebt: Optional[float] = None,
        costOfEquity: Optional[float] = None,
        marketRiskPremium: Optional[float] = None,
        beta: Optional[float] = None,
        riskFreeRate: Optional[float] = None,
    ) -> str:
        """
        Get a custom advanced DCF valuation using optional assumptions.
        Use this when the user provides assumptions such as revenue growth, tax rate, WACC inputs, beta, or risk-free rate.
        Numeric assumptions should be passed as percentages where the FMP MCP endpoint expects percentages.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_custom_dcf_valuation", "error": "Ticker symbol is required."})
        params = {
            "symbol": symbol,
            "revenueGrowthPct": revenueGrowthPct,
            "ebitdaPct": ebitdaPct,
            "taxRate": taxRate,
            "longTermGrowthRate": longTermGrowthRate,
            "costOfDebt": costOfDebt,
            "costOfEquity": costOfEquity,
            "marketRiskPremium": marketRiskPremium,
            "beta": beta,
            "riskFreeRate": riskFreeRate,
        }
        payload = _mcp_payload("discountedCashFlow", "custom-dcf-advanced", **params)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_custom_dcf_valuation", "symbol": symbol, "custom_dcf_advanced": rows, "assumptions": params, "raw": payload if not rows else None})

    def get_valuation_bundle(symbol: str) -> str:
        """
        Get a valuation bundle for a ticker: quote, key valuation ratios, enterprise values, DCF, levered DCF, and analyst price target consensus.
        Use this for broad valuation comparisons and investment analysis prompts.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_valuation_bundle", "error": "Ticker symbol is required."})
        quote = _extract_rows(client.quote(symbol))
        ratios_ttm = _extract_rows(client.metrics_ratios_ttm(symbol))
        key_metrics_ttm = _extract_rows(client.key_metrics_ttm(symbol))
        enterprise_values = _extract_rows(client.enterprise_values(symbol, limit=4, period="annual"))
        dcf = _extract_rows(_mcp_payload("discountedCashFlow", "dcf-advanced", symbol=symbol))
        levered_dcf = _extract_rows(_mcp_payload("discountedCashFlow", "dcf-levered", symbol=symbol))
        price_target = _extract_rows(client.price_target_consensus(symbol))
        return _safe_json_dumps({
            "ok": bool(quote or ratios_ttm or key_metrics_ttm or enterprise_values or dcf or levered_dcf or price_target),
            "tool": "get_valuation_bundle",
            "symbol": symbol,
            "quote": quote[:1],
            "ratios_ttm": ratios_ttm[:1],
            "key_metrics_ttm": key_metrics_ttm[:1],
            "enterprise_values": enterprise_values[:4],
            "dcf_advanced": dcf,
            "dcf_levered": levered_dcf,
            "price_target_consensus": price_target,
            "mcp_endpoints_used": [
                "quote:quote",
                "statements:metrics-ratios-ttm",
                "statements:key-metrics-ttm",
                "statements:enterprise-values",
                "discountedCashFlow:dcf-advanced",
                "discountedCashFlow:dcf-levered",
                "analyst:price-target-consensus",
            ],
        })

    return [
        _make_tool(get_dcf_valuation),
        _make_tool(get_levered_dcf),
        _make_tool(get_custom_dcf_valuation),
        _make_tool(get_valuation_bundle),
    ]
