from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_calendar_tools(fmp_api_key: str):
    """Build MCP-backed market calendar, earnings, dividend, IPO, and split tools."""

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

    def _bounded_limit(limit: int, default: int = 50, max_value: int = 500) -> int:
        try:
            value = int(limit)
        except Exception:
            value = default
        return max(1, min(value, max_value))

    def _default_dates(from_date: Optional[str], to_date: Optional[str], days_forward: int = 60) -> Dict[str, str]:
        start = from_date or date.today().isoformat()
        end = to_date or (date.today() + timedelta(days=days_forward)).isoformat()
        return {"from": start, "to": end}

    def _mcp_payload(endpoint: str, **params: Any) -> Dict[str, Any]:
        return client.call("calendar", endpoint, **{k: v for k, v in params.items() if v is not None and v != ""})

    def get_earnings_calendar(from_date: Optional[str] = None, to_date: Optional[str] = None, limit: int = 100) -> str:
        """
        Get earnings calendar events for a date range.
        Use this for upcoming earnings reports, reporting dates, and earnings-calendar questions.
        from_date and to_date should be YYYY-MM-DD. Defaults to today through the next 60 days.
        """
        dates = _default_dates(from_date, to_date, days_forward=60)
        limit = _bounded_limit(limit, default=100)
        payload = _mcp_payload("earnings-calendar", **dates, limit=limit)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_earnings_calendar", "from": dates["from"], "to": dates["to"], "row_count": len(rows), "events": rows[:limit], "raw": payload if not rows else None})

    def get_company_earnings(symbol: str, limit: int = 20) -> str:
        """
        Get company-specific earnings report history/details for a ticker.
        Use this to answer when a company reports earnings or review past EPS/revenue surprises.
        """
        symbol = _clean_symbol(symbol)
        limit = _bounded_limit(limit, default=20)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_company_earnings", "error": "Ticker symbol is required."})
        payload = _mcp_payload("earnings-company", symbol=symbol, limit=limit)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_company_earnings", "symbol": symbol, "row_count": len(rows), "earnings": rows[:limit], "raw": payload if not rows else None})

    def get_dividend_history(symbol: str, limit: int = 50) -> str:
        """
        Get company dividend history for a ticker.
        Use this for dividend amount, ex-dividend date, payment date, and dividend history questions.
        """
        symbol = _clean_symbol(symbol)
        limit = _bounded_limit(limit, default=50)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_dividend_history", "error": "Ticker symbol is required."})
        payload = _mcp_payload("dividends-company", symbol=symbol, limit=limit)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_dividend_history", "symbol": symbol, "row_count": len(rows), "dividends": rows[:limit], "raw": payload if not rows else None})

    def get_splits_history(symbol: str, limit: int = 50) -> str:
        """
        Get company stock split history for a ticker.
        Use this for split ratio, split date, and historical split questions.
        """
        symbol = _clean_symbol(symbol)
        limit = _bounded_limit(limit, default=50)
        if not symbol:
            return _safe_json_dumps({"ok": False, "tool": "get_splits_history", "error": "Ticker symbol is required."})
        payload = _mcp_payload("splits-company", symbol=symbol, limit=limit)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_splits_history", "symbol": symbol, "row_count": len(rows), "splits": rows[:limit], "raw": payload if not rows else None})

    def get_market_calendar_bundle(from_date: Optional[str] = None, to_date: Optional[str] = None, limit: int = 100) -> str:
        """
        Get a market calendar bundle for a date range: earnings, dividends, IPOs, and splits.
        Use this for market-event calendar prompts and weekly/monthly event planning.
        """
        dates = _default_dates(from_date, to_date, days_forward=30)
        limit = _bounded_limit(limit, default=100)
        earnings = _extract_rows(_mcp_payload("earnings-calendar", **dates, limit=limit))
        dividends = _extract_rows(_mcp_payload("dividends-calendar", **dates, limit=limit))
        ipos = _extract_rows(_mcp_payload("ipos-calendar", **dates, limit=limit))
        splits = _extract_rows(_mcp_payload("splits-calendar", **dates, limit=limit))
        return _safe_json_dumps({
            "ok": bool(earnings or dividends or ipos or splits),
            "tool": "get_market_calendar_bundle",
            "from": dates["from"],
            "to": dates["to"],
            "earnings_calendar": earnings[:limit],
            "dividends_calendar": dividends[:limit],
            "ipos_calendar": ipos[:limit],
            "splits_calendar": splits[:limit],
        })

    return [
        _make_tool(get_earnings_calendar),
        _make_tool(get_company_earnings),
        _make_tool(get_dividend_history),
        _make_tool(get_splits_history),
        _make_tool(get_market_calendar_bundle),
    ]
