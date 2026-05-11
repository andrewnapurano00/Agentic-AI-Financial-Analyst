from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_analyst_tools(fmp_api_key: str):
    """Build MCP-backed analyst estimate, rating, grade, and price target tools."""

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

    def _clean_period(period: str) -> str:
        period = (period or "annual").strip().lower()
        if period in {"quarter", "quarterly", "q"}:
            return "quarter"
        return "annual"

    def _bounded_limit(limit: int, default: int = 8, max_value: int = 100) -> int:
        try:
            value = int(limit)
        except Exception:
            value = default
        return max(1, min(value, max_value))

    def _mcp_payload(tool_name: str, endpoint: str, **params: Any) -> Dict[str, Any]:
        return client.call(tool_name, endpoint, **{k: v for k, v in params.items() if v is not None and v != ""})

    def get_analyst_estimates(symbol: str, period: str = "annual", limit: int = 8) -> str:
        """
        Get analyst financial estimates for a ticker, including expected revenue and EPS.
        Use this for forward revenue, forward EPS, next-year estimates, and analyst forecast questions.
        period should be 'annual' or 'quarter'.
        """
        symbol = _clean_symbol(symbol)
        period = _clean_period(period)
        limit = _bounded_limit(limit, default=8)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_analyst_estimates", "error": "Ticker symbol is required."})
        payload = _mcp_payload("analyst", "financial-estimates", symbol=symbol, period=period, limit=limit)
        rows = _extract_rows(payload)
        return _safe_json_dumps({
            "ok": bool(rows),
            "tool": "get_analyst_estimates",
            "symbol": symbol,
            "period": period,
            "row_count": len(rows),
            "estimates": rows[:limit],
            "raw": payload if not rows else None,
        })

    def get_price_target_consensus(symbol: str) -> str:
        """
        Get analyst price target consensus for a ticker.
        Use this for average, high, low, median target, and upside/downside questions.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_price_target_consensus", "error": "Ticker symbol is required."})
        payload = _mcp_payload("analyst", "price-target-consensus", symbol=symbol)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_price_target_consensus", "symbol": symbol, "consensus": rows, "raw": payload if not rows else None})

    def get_price_target_summary(symbol: str) -> str:
        """
        Get analyst price target summary for a ticker.
        Use this for recent target changes and analyst price-target activity.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_price_target_summary", "error": "Ticker symbol is required."})
        payload = _mcp_payload("analyst", "price-target-summary", symbol=symbol)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_price_target_summary", "symbol": symbol, "summary": rows, "raw": payload if not rows else None})

    def get_ratings_snapshot(symbol: str) -> str:
        """
        Get current analyst rating snapshot for a ticker.
        Use this for buy/hold/sell consensus and overall Wall Street sentiment.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_ratings_snapshot", "error": "Ticker symbol is required."})
        payload = _mcp_payload("analyst", "ratings-snapshot", symbol=symbol)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_ratings_snapshot", "symbol": symbol, "ratings_snapshot": rows, "raw": payload if not rows else None})

    def get_stock_grades(symbol: str, limit: int = 20) -> str:
        """
        Get current and recent analyst grade actions for a ticker.
        Use this for upgrades, downgrades, and broker grade history.
        """
        symbol = _clean_symbol(symbol)
        limit = _bounded_limit(limit, default=20)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_stock_grades", "error": "Ticker symbol is required."})
        grades = _extract_rows(_mcp_payload("analyst", "grades", symbol=symbol, limit=limit))
        summary = _extract_rows(_mcp_payload("analyst", "grades-summary", symbol=symbol))
        historical_ratings = _extract_rows(_mcp_payload("analyst", "historical-ratings", symbol=symbol, limit=limit))
        return _safe_json_dumps({
            "ok": bool(grades or summary or historical_ratings),
            "tool": "get_stock_grades",
            "symbol": symbol,
            "grades_summary": summary,
            "recent_grades": grades[:limit],
            "historical_ratings": historical_ratings[:limit],
        })

    def get_analyst_bundle(symbol: str, period: str = "annual", limit: int = 8) -> str:
        """
        Get a complete analyst bundle for a ticker: estimates, price targets, ratings snapshot, and grades.
        Use this for complicated prompts about analyst expectations, forward EPS/revenue, target upside, and rating sentiment.
        """
        symbol = _clean_symbol(symbol)
        period = _clean_period(period)
        limit = _bounded_limit(limit, default=8)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_analyst_bundle", "error": "Ticker symbol is required."})
        estimates = _extract_rows(_mcp_payload("analyst", "financial-estimates", symbol=symbol, period=period, limit=limit))
        pt_consensus = _extract_rows(_mcp_payload("analyst", "price-target-consensus", symbol=symbol))
        pt_summary = _extract_rows(_mcp_payload("analyst", "price-target-summary", symbol=symbol))
        ratings = _extract_rows(_mcp_payload("analyst", "ratings-snapshot", symbol=symbol))
        grades_summary = _extract_rows(_mcp_payload("analyst", "grades-summary", symbol=symbol))
        grades = _extract_rows(_mcp_payload("analyst", "grades", symbol=symbol, limit=20))
        return _safe_json_dumps({
            "ok": bool(estimates or pt_consensus or pt_summary or ratings or grades_summary or grades),
            "tool": "get_analyst_bundle",
            "symbol": symbol,
            "period": period,
            "analyst_estimates": estimates[:limit],
            "price_target_consensus": pt_consensus,
            "price_target_summary": pt_summary,
            "ratings_snapshot": ratings,
            "grades_summary": grades_summary,
            "recent_grades": grades[:20],
            "mcp_endpoints_used": [
                "analyst:financial-estimates",
                "analyst:price-target-consensus",
                "analyst:price-target-summary",
                "analyst:ratings-snapshot",
                "analyst:grades-summary",
                "analyst:grades",
            ],
        })

    return [
        _make_tool(get_analyst_estimates),
        _make_tool(get_price_target_consensus),
        _make_tool(get_price_target_summary),
        _make_tool(get_ratings_snapshot),
        _make_tool(get_stock_grades),
        _make_tool(get_analyst_bundle),
    ]
