from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_earnings_transcript_tools(fmp_api_key: str):
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
                for key in ("transcripts", "items", "results", "historical"):
                    value = data.get(key)
                    if isinstance(value, list):
                        return [x for x in value if isinstance(x, dict)]
                return [data]
            return []
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        return []

    def _normalize_transcript_item(symbol: str, item: Dict[str, Any]) -> Dict[str, Any]:
        content = item.get("content") or item.get("transcript") or item.get("text") or ""
        return {
            "symbol": (item.get("symbol") or symbol or "").upper(),
            "year": item.get("year") or item.get("fiscalYear"),
            "quarter": item.get("quarter") or item.get("period"),
            "date": item.get("date") or item.get("dateReported") or item.get("publishedDate"),
            "title": item.get("title"),
            "content": content,
            "content_length": len(content),
            "has_content": bool(str(content).strip()),
            "raw_keys": sorted(list(item.keys())),
        }

    def _periods(rows: List[Dict[str, Any]], symbol: str) -> List[Dict[str, Any]]:
        out = []
        for row in rows:
            norm = _normalize_transcript_item(symbol, row)
            out.append(
                {
                    "year": norm.get("year"),
                    "quarter": norm.get("quarter"),
                    "date": norm.get("date"),
                    "has_content": norm.get("has_content", False),
                    "content_length": norm.get("content_length", 0),
                }
            )
        return sorted(out, key=lambda x: (x.get("year") or 0, x.get("quarter") or 0, x.get("date") or ""), reverse=True)

    def get_available_earnings_transcript_periods(symbol: str, limit: int = 8) -> str:
        """
        Get recent available earnings transcript periods for a ticker using FMP MCP.
        Use this when the user asks for a transcript or transcript summary but has
        not specified both quarter and year.
        """
        symbol = (symbol or "").upper().strip()
        limit = max(1, min(int(limit), 20))

        # Current MCP catalog: earningsTranscript -> transcripts-dates-by-symbol
        rows = _extract_rows(client.transcript_dates_by_symbol(symbol))
        if not rows:
            rows = _extract_rows(client.latest_transcripts(symbol=symbol, limit=limit))

        periods = _periods(rows[:limit], symbol)
        return _safe_json_dumps(
            {
                "ok": bool(periods),
                "tool": "get_available_earnings_transcript_periods",
                "symbol": symbol,
                "period_count": len(periods),
                "periods": periods,
                "instruction_for_agent": (
                    "If the user did not specify quarter and year, ask which period they want. "
                    "If they explicitly ask for the latest transcript, use get_latest_earnings_transcript."
                ),
                "mcp_endpoint_used": "transcripts-dates-by-symbol",
            }
        )

    def get_latest_earnings_transcript(symbol: str, max_chars: int = 30000) -> str:
        """
        Fetch the latest available earnings transcript for a ticker using FMP MCP.
        """
        symbol = (symbol or "").upper().strip()
        max_chars = max(1000, min(int(max_chars), 120000))

        rows = _extract_rows(client.latest_transcripts(symbol=symbol, limit=5))
        # Some MCP implementations return latest transcripts globally even when symbol is passed.
        rows = [r for r in rows if str(r.get("symbol", symbol)).upper() == symbol] or rows

        normalized = [_normalize_transcript_item(symbol, r) for r in rows]
        row = next((r for r in normalized if r.get("has_content")), normalized[0] if normalized else {})
        if not row or not row.get("content"):
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_latest_earnings_transcript",
                    "symbol": symbol,
                    "error": f"No latest earnings transcript content found for {symbol} from MCP.",
                    "transcript": None,
                    "mcp_endpoint_used": "latest-transcripts",
                }
            )

        full_content = row.get("content", "")
        content = full_content[:max_chars]
        return _safe_json_dumps(
            {
                "ok": True,
                "tool": "get_latest_earnings_transcript",
                "symbol": symbol,
                "mcp_endpoint_used": "latest-transcripts",
                "transcript": {
                    "year": row.get("year"),
                    "quarter": row.get("quarter"),
                    "date": row.get("date"),
                    "content": content,
                    "content_length": len(content),
                    "truncated": len(full_content) > len(content),
                },
            }
        )

    def get_earnings_transcript(symbol: str, year: int, quarter: int, max_chars: int = 30000) -> str:
        """
        Fetch a specific earnings transcript for a ticker, year, and quarter using FMP MCP.
        """
        symbol = (symbol or "").upper().strip()
        year = int(year)
        quarter = int(quarter)
        max_chars = max(1000, min(int(max_chars), 120000))

        if quarter not in (1, 2, 3, 4):
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_earnings_transcript",
                    "symbol": symbol,
                    "year": year,
                    "quarter": quarter,
                    "error": "Quarter must be 1, 2, 3, or 4.",
                    "transcript": None,
                }
            )

        rows = _extract_rows(client.search_transcripts(symbol=symbol, year=year, quarter=quarter))
        normalized = [_normalize_transcript_item(symbol, r) for r in rows]
        row = next((r for r in normalized if r.get("has_content")), normalized[0] if normalized else {})

        if not row or not row.get("content"):
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_earnings_transcript",
                    "symbol": symbol,
                    "year": year,
                    "quarter": quarter,
                    "error": f"No earnings transcript content found for {symbol} Q{quarter} {year} from MCP.",
                    "transcript": None,
                    "mcp_endpoint_used": "search-transcripts",
                }
            )

        full_content = row.get("content", "")
        content = full_content[:max_chars]
        return _safe_json_dumps(
            {
                "ok": True,
                "tool": "get_earnings_transcript",
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "mcp_endpoint_used": "search-transcripts",
                "transcript": {
                    "date": row.get("date"),
                    "content": content,
                    "content_length": len(content),
                    "truncated": len(full_content) > len(content),
                },
            }
        )

    return [
            _make_tool(get_available_earnings_transcript_periods),
            _make_tool(get_latest_earnings_transcript),
            _make_tool(get_earnings_transcript),
        ]
