from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_directory_tools(fmp_api_key: str):
    """Build MCP-backed reference/directory tools for symbols, sectors, industries, and symbol changes."""

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

    def _bounded_limit(limit: int, default: int = 100, max_value: int = 5000) -> int:
        try:
            value = int(limit)
        except Exception:
            value = default
        return max(1, min(value, max_value))

    def _mcp_payload(endpoint: str, **params: Any) -> Dict[str, Any]:
        return client.call("directory", endpoint, **{k: v for k, v in params.items() if v is not None and v != ""})

    def get_available_sectors() -> str:
        """
        Get the list of available market sectors from FMP MCP.
        Use this for sector-aware screening, sector classification, and sector comparison setup.
        """
        payload = _mcp_payload("available-sectors")
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_available_sectors", "sectors": rows, "raw": payload if not rows else None})

    def get_available_industries() -> str:
        """
        Get the list of available industries from FMP MCP.
        Use this for industry-aware screening, peer group construction, and industry comparison setup.
        """
        payload = _mcp_payload("available-industries")
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_available_industries", "industries": rows, "raw": payload if not rows else None})

    def get_company_symbols(limit: int = 500, page: int = 0) -> str:
        """
        Get a paginated list of company symbols.
        Use this to discover tradable companies or validate tickers.
        """
        limit = _bounded_limit(limit, default=500)
        try:
            page = max(0, int(page))
        except Exception:
            page = 0
        payload = _mcp_payload("company-symbols-list", limit=limit, page=page)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_company_symbols", "limit": limit, "page": page, "row_count": len(rows), "symbols": rows[:limit], "raw": payload if not rows else None})

    def get_financial_statement_symbols(limit: int = 500, page: int = 0) -> str:
        """
        Get symbols that have financial statement data available.
        Use this to check whether a ticker has FMP financial statement coverage.
        """
        limit = _bounded_limit(limit, default=500)
        try:
            page = max(0, int(page))
        except Exception:
            page = 0
        payload = _mcp_payload("financial-symbols-list", limit=limit, page=page)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_financial_statement_symbols", "limit": limit, "page": page, "row_count": len(rows), "symbols": rows[:limit], "raw": payload if not rows else None})

    def get_symbol_changes(limit: int = 100, page: int = 0) -> str:
        """
        Get recent symbol changes.
        Use this when a ticker may have changed symbol or historical data appears missing under the current ticker.
        """
        limit = _bounded_limit(limit, default=100)
        try:
            page = max(0, int(page))
        except Exception:
            page = 0
        payload = _mcp_payload("symbol-changes-list", limit=limit, page=page)
        rows = _extract_rows(payload)
        return _safe_json_dumps({"ok": bool(rows), "tool": "get_symbol_changes", "limit": limit, "page": page, "row_count": len(rows), "symbol_changes": rows[:limit], "raw": payload if not rows else None})

    def get_reference_data_bundle(limit: int = 250) -> str:
        """
        Get a compact reference-data bundle: sectors, industries, exchanges, and countries.
        Use this when the agent needs to understand available market classifications.
        """
        limit = _bounded_limit(limit, default=250)
        sectors = _extract_rows(_mcp_payload("available-sectors"))
        industries = _extract_rows(_mcp_payload("available-industries"))
        exchanges = _extract_rows(_mcp_payload("available-exchanges"))
        countries = _extract_rows(_mcp_payload("available-countries"))
        return _safe_json_dumps({
            "ok": bool(sectors or industries or exchanges or countries),
            "tool": "get_reference_data_bundle",
            "available_sectors": sectors[:limit],
            "available_industries": industries[:limit],
            "available_exchanges": exchanges[:limit],
            "available_countries": countries[:limit],
        })

    return [
        _make_tool(get_available_sectors),
        _make_tool(get_available_industries),
        _make_tool(get_company_symbols),
        _make_tool(get_financial_statement_symbols),
        _make_tool(get_symbol_changes),
        _make_tool(get_reference_data_bundle),
    ]
