from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_company_overview_tools(fmp_api_key: str):
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

    def _pick(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        return {k: d.get(k) for k in keys if k in d}

    def get_company_profile(symbol: str) -> str:
        """
        Get a normalized company profile for a ticker symbol.
        Use this for business overview, sector, industry, exchange, management,
        market cap, and company description.
        """
        symbol = (symbol or "").upper().strip()
        if not symbol:
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_company_profile",
                    "symbol": symbol,
                    "error": "Ticker symbol is required.",
                }
            )

        row = _first_row(client.profile(symbol))
        quote = _first_row(client.quote(symbol))
        market_cap = _first_row(client.market_cap(symbol))
        float_data = _first_row(client.shares_float(symbol))

        if not row and not quote:
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_company_profile",
                    "symbol": symbol,
                    "error": f"No profile data found for {symbol}.",
                }
            )

        summary = {
            "symbol": symbol,
            "companyName": row.get("companyName") or row.get("companyNameLong") or row.get("name"),
            "sector": row.get("sector"),
            "industry": row.get("industry"),
            "exchange": row.get("exchangeShortName") or row.get("exchange"),
            "country": row.get("country"),
            "currency": row.get("currency"),
            "ceo": row.get("ceo"),
            "website": row.get("website"),
            "ipoDate": row.get("ipoDate"),
            "isEtf": row.get("isEtf"),
            "isActivelyTrading": row.get("isActivelyTrading"),
            "price": quote.get("price") or row.get("price"),
            "beta": row.get("beta"),
            "marketCap": market_cap.get("marketCap") or row.get("mktCap") or row.get("marketCap"),
            "sharesOutstanding": float_data.get("outstandingShares") or row.get("fullTimeEmployees"),
            "description": row.get("description"),
        }

        return _safe_json_dumps(
            {
                "ok": True,
                "tool": "get_company_profile",
                "symbol": symbol,
                "summary": summary,
                "profile_raw": _pick(
                    row,
                    [
                        "symbol",
                        "companyName",
                        "sector",
                        "industry",
                        "exchange",
                        "exchangeShortName",
                        "country",
                        "currency",
                        "ceo",
                        "website",
                        "description",
                        "ipoDate",
                        "beta",
                        "volAvg",
                        "image",
                        "isEtf",
                        "isActivelyTrading",
                    ],
                ),
                "quote_snapshot": _pick(
                    quote,
                    [
                        "symbol",
                        "name",
                        "price",
                        "change",
                        "changesPercentage",
                        "dayLow",
                        "dayHigh",
                        "yearLow",
                        "yearHigh",
                        "marketCap",
                        "volume",
                        "avgVolume",
                        "open",
                        "previousClose",
                        "eps",
                        "pe",
                    ],
                ),
            }
        )

    def get_company_peers(symbol: str) -> str:
        """
        Get peer companies for a ticker symbol.
        Use this when the user asks for comparable companies or peer analysis.
        """
        symbol = (symbol or "").upper().strip()
        if not symbol:
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_company_peers",
                    "symbol": symbol,
                    "error": "Ticker symbol is required.",
                }
            )

        payload = client.peers(symbol)
        rows = _extract_rows(payload)

        peer_list: List[str] = []
        for row in rows:
            if isinstance(row, dict):
                for key in ("peersList", "peers", "symbols"):
                    value = row.get(key)
                    if isinstance(value, list):
                        peer_list.extend([str(x).upper() for x in value if str(x).strip()])
                    elif isinstance(value, str):
                        peer_list.extend([x.strip().upper() for x in value.split(",") if x.strip()])

        if not peer_list and isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                peer_list.extend([str(x).upper() for x in data if str(x).strip()])

        peer_list = sorted(list(dict.fromkeys(peer_list)))

        return _safe_json_dumps(
            {
                "ok": True,
                "tool": "get_company_peers",
                "symbol": symbol,
                "peer_count": len(peer_list),
                "peers": peer_list,
            }
        )

    return [
        _make_tool(get_company_profile),
        _make_tool(get_company_peers),
    ]
