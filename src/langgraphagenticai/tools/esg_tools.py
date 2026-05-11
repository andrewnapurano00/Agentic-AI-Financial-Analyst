from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_esg_tools(fmp_api_key: str):
    """Build MCP-backed ESG ratings, ESG benchmark, and ESG search tools."""

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

    def _mcp_payload(endpoint: str, **params: Any) -> Dict[str, Any]:
        return client.call("ESG", endpoint, **{k: v for k, v in params.items() if v is not None and v != ""})

    def get_esg_ratings(symbol: str) -> str:
        """
        Get ESG ratings for a ticker.
        Use this for environmental, social, governance, and ESG-score questions.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_esg_ratings", "error": "Ticker symbol is required."})
        payload = _mcp_payload("esg-ratings", symbol=symbol)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_esg_ratings", "symbol": symbol, "esg_ratings": rows, "raw": payload if not rows else None})

    def search_esg_investments(symbol: str) -> str:
        """
        Search ESG investment data for a ticker.
        Use this when the user asks for ESG search, ESG investability, or sustainability-related records.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "search_esg_investments", "error": "Ticker symbol is required."})
        payload = _mcp_payload("esg-search", symbol=symbol)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "search_esg_investments", "symbol": symbol, "esg_search": rows, "raw": payload if not rows else None})

    def get_esg_benchmark(year: Optional[int] = None) -> str:
        """
        Get ESG benchmark comparison data, optionally for a specific year.
        Use this to compare ESG ratings across the market or benchmark a company against ESG distributions.
        """
        params: Dict[str, Any] = {}
        if year is not None:
            try:
                params["year"] = int(year)
            except Exception:
                pass
        payload = _mcp_payload("esg-benchmark", **params)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_esg_benchmark", "year": params.get("year"), "row_count": len(rows), "benchmark": rows[:500], "raw": payload if not rows else None})

    def get_esg_bundle(symbol: str, year: Optional[int] = None) -> str:
        """
        Get ESG ratings, ESG search records, and ESG benchmark data for a ticker.
        Use this for sustainability or ESG-aware investment analysis.
        """
        symbol = _clean_symbol(symbol)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_esg_bundle", "error": "Ticker symbol is required."})
        ratings = _extract_rows(_mcp_payload("esg-ratings", symbol=symbol))
        search = _extract_rows(_mcp_payload("esg-search", symbol=symbol))
        benchmark_params: Dict[str, Any] = {}
        if year is not None:
            try:
                benchmark_params["year"] = int(year)
            except Exception:
                pass
        benchmark = _extract_rows(_mcp_payload("esg-benchmark", **benchmark_params))
        return _safe_json_dumps({
            "ok": bool(ratings or search or benchmark),
            "tool": "get_esg_bundle",
            "symbol": symbol,
            "year": benchmark_params.get("year"),
            "esg_ratings": ratings,
            "esg_search": search,
            "esg_benchmark_sample": benchmark[:100],
        })

    return [
        _make_tool(get_esg_ratings),
        _make_tool(search_esg_investments),
        _make_tool(get_esg_benchmark),
        _make_tool(get_esg_bundle),
    ]
