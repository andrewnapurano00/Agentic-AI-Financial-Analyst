from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import StructuredTool

from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient


def build_price_data_tools(fmp_api_key: str):
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
        """
        Generic row extractor for quote/indicator style MCP responses.

        The MCP client returns a compatibility wrapper like:
            {"ok": True, "data": ...}

        The inner `data` may itself be a row list, a single row dict, or another
        nested wrapper such as {"data": [...]}, {"result": [...]}, or
        {"content": [{"text": "{...}"}]}. This recursively peels wrappers so
        live quote calls do not show false N/A values.
        """
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
                if isinstance(item, dict) and "text" in item:
                    rows.extend(_extract_rows(item.get("text")))
                elif hasattr(item, "text"):
                    rows.extend(_extract_rows(getattr(item, "text", None)))
                elif isinstance(item, dict):
                    # If this item is a wrapper, peel it; otherwise keep it as a row.
                    wrapper_keys = {"data", "result", "results", "output", "content", "structured_content", "structuredContent"}
                    if any(k in item for k in wrapper_keys) and not any(k in item for k in ("symbol", "date", "price", "close")):
                        rows.extend(_extract_rows(item))
                    else:
                        rows.append(item)
            return rows

        if isinstance(payload, dict):
            for key in ("data", "result", "results", "output", "content", "structured_content", "structuredContent"):
                if key in payload and payload.get(key) is not None:
                    nested_rows = _extract_rows(payload.get(key))
                    if nested_rows:
                        return nested_rows

            # Single quote/profile/indicator row.
            if any(k in payload for k in ("symbol", "date", "price", "close", "adjClose", "value")):
                return [payload]

        return []

    def _extract_history_rows(payload: Any) -> List[Dict[str, Any]]:
        """
        Historical chart responses from the current FMP MCP server can come back in
        more than one shape, commonly either:

            {"ok": true, "data": [{"date": ..., "close": ...}, ...]}

        or:

            {"ok": true, "data": {"symbol": "AAPL", "historical": [...]}}

        The old app treated only the first shape as valid, which caused the chat
        agent to show N/A for multi-year return questions even when the MCP call
        succeeded. This function flattens both shapes into actual daily price rows.
        """
        if payload is None:
            return []

        # Peel the compatibility wrapper returned by FMPMCPClient.
        if isinstance(payload, dict) and "data" in payload:
            payload = payload.get("data")

        if isinstance(payload, dict):
            # FMP historical-price-eod-full often returns this nested shape.
            historical = payload.get("historical")
            if isinstance(historical, list):
                return [x for x in historical if isinstance(x, dict)]

            # Defensive fallback for possible nested data wrappers.
            nested = payload.get("data")
            if isinstance(nested, list):
                return [x for x in nested if isinstance(x, dict)]
            if isinstance(nested, dict):
                historical = nested.get("historical")
                if isinstance(historical, list):
                    return [x for x in historical if isinstance(x, dict)]

            # If the payload itself is one price row.
            if payload.get("date") and (payload.get("close") is not None or payload.get("adjClose") is not None):
                return [payload]

        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]

        return []

    def _first_row(payload: Any) -> Dict[str, Any]:
        rows = _extract_rows(payload)
        return rows[0] if rows else {}

    def _clean_limit(limit: int, default: int = 252, max_value: int = 2000) -> int:
        try:
            limit = int(limit)
        except Exception:
            limit = default
        return max(1, min(limit, max_value))

    def _clean_years(years: int, default: int = 5) -> int:
        try:
            years = int(years)
        except Exception:
            years = default
        return max(1, min(years, 30))

    def _default_date_window(years: int = 5) -> Tuple[str, str]:
        years = _clean_years(years)
        end = date.today()
        # Use 366 days/year to cover leap years and weekends/market holidays.
        start = end - timedelta(days=years * 366 + 10)
        return start.isoformat(), end.isoformat()

    def _price_value(row: Dict[str, Any]) -> Optional[float]:
        for key in ("adjClose", "adjclose", "adj_close", "close", "price"):
            value = row.get(key)
            if value is None or value == "":
                continue
            try:
                return float(value)
            except Exception:
                continue
        return None

    def _history_rows(
        symbol: str,
        limit: int = 1500,
        years: int = 5,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        symbol = (symbol or "").upper().strip()
        years = _clean_years(years)
        limit = _clean_limit(limit, default=years * 260, max_value=8000)

        if not from_date or not to_date:
            default_from, default_to = _default_date_window(years)
            from_date = from_date or default_from
            to_date = to_date or default_to

        payload = client.historical_price_full(symbol, from_date=from_date, to_date=to_date)
        rows = _extract_history_rows(payload)
        if not rows:
            return []

        rows = [r for r in rows if isinstance(r, dict) and r.get("date")]
        rows = sorted(rows, key=lambda x: str(x.get("date", "")), reverse=True)
        return rows[:limit]

    def _return_summary(symbol: str, rows: List[Dict[str, Any]], years: int) -> Dict[str, Any]:
        if len(rows) < 2:
            return {
                "ticker": symbol,
                "ok": False,
                "years": years,
                "error": "Historical price data unavailable or insufficient rows returned.",
            }

        latest = rows[0]
        oldest = rows[-1]
        latest_price = _price_value(latest)
        oldest_price = _price_value(oldest)

        if latest_price is None or oldest_price is None or oldest_price == 0:
            return {
                "ticker": symbol,
                "ok": False,
                "years": years,
                "latest_date": latest.get("date"),
                "oldest_date": oldest.get("date"),
                "error": "Could not compute return because close/adjusted close values were missing.",
            }

        total_return = (latest_price / oldest_price) - 1.0
        return {
            "ticker": symbol,
            "ok": True,
            "years": years,
            "latest_date": latest.get("date"),
            "oldest_date": oldest.get("date"),
            "latest_price": latest_price,
            "oldest_price": oldest_price,
            "total_return_decimal": total_return,
            "total_return_pct": total_return * 100.0,
            "row_count": len(rows),
        }

    def get_price_snapshot(symbol: str) -> str:
        """
        Get current quote and short-term quote change snapshot for a ticker symbol.
        Use this for current price, day move, volume, 52-week range, and quick market context.

        This version tries multiple current-quote MCP endpoints and then falls back
        to the latest historical close so the chat agent does not return N/A when
        only the live quote endpoint is temporarily empty.
        """
        symbol = (symbol or "").upper().strip()
        if not symbol:
            return _safe_json_dumps(
                {"ok": False, "tool": "get_price_snapshot", "symbol": symbol, "error": "Ticker symbol is required."}
            )

        quote_rows = _extract_rows(client.quote(symbol))
        quote_short_rows = _extract_rows(client.quote_short(symbol))
        batch_quote_rows = _extract_rows(client.batch_quote(symbol))
        batch_quote_short_rows = _extract_rows(client.batch_quote_short(symbol))
        quote_change_rows = _extract_rows(client.quote_change(symbol))
        after_hours_rows = _extract_rows(client.aftermarket_quote(symbol))

        quote = quote_rows[0] if quote_rows else {}
        quote_short = quote_short_rows[0] if quote_short_rows else {}
        batch_quote = batch_quote_rows[0] if batch_quote_rows else {}
        batch_quote_short = batch_quote_short_rows[0] if batch_quote_short_rows else {}
        quote_change = quote_change_rows[0] if quote_change_rows else {}
        after_hours = after_hours_rows[0] if after_hours_rows else {}

        # Best current/live quote row available.
        current = quote or batch_quote or quote_short or batch_quote_short
        live_quote_ok = bool(current)

        # Fallback to latest historical close when live quote endpoints return no rows.
        latest_close_row: Dict[str, Any] = {}
        if not current:
            hist_rows = _history_rows(symbol, limit=10, years=1)
            latest_close_row = hist_rows[0] if hist_rows else {}
            if latest_close_row:
                current = {
                    "symbol": symbol,
                    "price": _price_value(latest_close_row),
                    "close": latest_close_row.get("close"),
                    "adjClose": latest_close_row.get("adjClose") or latest_close_row.get("adjclose"),
                    "volume": latest_close_row.get("volume"),
                    "date": latest_close_row.get("date"),
                    "source": "historical-price-eod-full fallback",
                }

        if not current:
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_price_snapshot",
                    "symbol": symbol,
                    "error": f"No quote or latest historical close data found for {symbol}.",
                    "debug": {
                        "quote_rows": len(quote_rows),
                        "quote_short_rows": len(quote_short_rows),
                        "batch_quote_rows": len(batch_quote_rows),
                        "batch_quote_short_rows": len(batch_quote_short_rows),
                        "quote_change_rows": len(quote_change_rows),
                    },
                }
            )

        return _safe_json_dumps(
            {
                "ok": True,
                "tool": "get_price_snapshot",
                "symbol": symbol,
                "live_quote_ok": live_quote_ok,
                "fallback_close_used": bool(latest_close_row),
                "summary": {
                    "price": current.get("price") or current.get("close") or current.get("adjClose"),
                    "change": current.get("change") or quote_change.get("change"),
                    "changesPercentage": current.get("changesPercentage") or quote_change.get("changesPercentage"),
                    "open": current.get("open"),
                    "previousClose": current.get("previousClose"),
                    "dayLow": current.get("dayLow"),
                    "dayHigh": current.get("dayHigh"),
                    "yearLow": current.get("yearLow"),
                    "yearHigh": current.get("yearHigh"),
                    "volume": current.get("volume"),
                    "avgVolume": current.get("avgVolume"),
                    "marketCap": current.get("marketCap"),
                    "pe": current.get("pe"),
                    "eps": current.get("eps"),
                    "date": current.get("date"),
                    "source": current.get("source", "FMP MCP quote endpoint"),
                },
                "quote": quote,
                "quote_short": quote_short,
                "batch_quote": batch_quote,
                "batch_quote_short": batch_quote_short,
                "quote_change": quote_change,
                "aftermarket_quote": after_hours,
                "latest_historical_close": latest_close_row,
            }
        )

    def get_price_history_bundle(symbol: str, years: int = 5, limit: int = 1500, from_date: str = "", to_date: str = "") -> str:
        """
        Get historical daily price rows for a ticker over a multi-year window.
        Use this for 1-year, 3-year, 5-year, or custom price-return calculations.
        Args:
            symbol: Ticker symbol, such as AAPL.
            years: Number of years of history to request when from_date/to_date are not provided.
            limit: Maximum daily rows returned to the LLM.
            from_date: Optional YYYY-MM-DD start date.
            to_date: Optional YYYY-MM-DD end date.
        """
        symbol = (symbol or "").upper().strip()
        years = _clean_years(years, default=5)
        limit = _clean_limit(limit, default=years * 260, max_value=8000)
        history = _history_rows(
            symbol,
            limit=limit,
            years=years,
            from_date=from_date or None,
            to_date=to_date or None,
        )

        if not history:
            return _safe_json_dumps(
                {
                    "ok": False,
                    "tool": "get_price_history_bundle",
                    "symbol": symbol,
                    "years": years,
                    "error": f"No historical price data found for {symbol}.",
                }
            )

        latest = history[0]
        oldest = history[-1]
        summary = _return_summary(symbol, history, years)

        return _safe_json_dumps(
            {
                "ok": True,
                "tool": "get_price_history_bundle",
                "symbol": symbol,
                "years": years,
                "row_count": len(history),
                "latest_date": latest.get("date"),
                "oldest_date": oldest.get("date"),
                "return_summary": summary,
                "latest_summary": {
                    "date": latest.get("date"),
                    "open": latest.get("open"),
                    "high": latest.get("high"),
                    "low": latest.get("low"),
                    "close": latest.get("close"),
                    "adjClose": latest.get("adjClose") or latest.get("adjclose"),
                    "volume": latest.get("volume"),
                    "changePercent": latest.get("changePercent"),
                },
                "history": history,
            }
        )

    def compare_price_returns(symbols: str, years: int = 5) -> str:
        """
        Compare multi-year price returns across multiple tickers.
        Use this when the user asks to compare 1-year, 3-year, 5-year, or other
        price returns for two or more stocks.
        Args:
            symbols: Comma-separated ticker symbols, such as "AAPL,MSFT,NVDA".
            years: Number of years for the price return comparison. Default is 5.
        """
        years = _clean_years(years, default=5)
        ticker_list = [s.strip().upper() for s in str(symbols or "").replace(";", ",").split(",") if s.strip()]
        ticker_list = list(dict.fromkeys(ticker_list))

        if not ticker_list:
            return _safe_json_dumps(
                {"ok": False, "tool": "compare_price_returns", "error": "At least one ticker symbol is required."}
            )

        results: List[Dict[str, Any]] = []
        for ticker in ticker_list:
            rows = _history_rows(ticker, limit=years * 270, years=years)
            results.append(_return_summary(ticker, rows, years))

        successful = [r for r in results if r.get("ok")]
        successful_sorted = sorted(successful, key=lambda r: float(r.get("total_return_pct", float("-inf"))), reverse=True)

        leader = successful_sorted[0]["ticker"] if successful_sorted else None
        return _safe_json_dumps(
            {
                "ok": bool(successful),
                "tool": "compare_price_returns",
                "years": years,
                "leader": leader,
                "results": results,
                "ranking": [r["ticker"] for r in successful_sorted],
                "note": "Returns use adjusted close when available, otherwise close price.",
            }
        )

    def get_technical_indicator_bundle(symbol: str, timeframe: str = "daily") -> str:
        """
        Get a compact technical indicator snapshot for a ticker using endpoints exposed
        by the current FMP MCP technicalIndicators catalog.

        Current supported MCP endpoints include SMA, EMA, DEMA, TEMA, WMA, RSI,
        ADX, Williams %R, and standard deviation. MACD and ATR are intentionally
        not requested because they are not exposed in the current MCP catalog.
        """
        symbol = (symbol or "").upper().strip()
        timeframe = (timeframe or "daily").strip().lower()

        sma20 = _extract_rows(client.sma(symbol, period_length=20, timeframe=timeframe))
        sma50 = _extract_rows(client.sma(symbol, period_length=50, timeframe=timeframe))
        ema20 = _extract_rows(client.ema(symbol, period_length=20, timeframe=timeframe))
        rsi14 = _extract_rows(client.rsi(symbol, period_length=14, timeframe=timeframe))
        adx14 = _extract_rows(client.adx(symbol, period_length=14, timeframe=timeframe))
        williams14 = _extract_rows(client.williams(symbol, period_length=14, timeframe=timeframe))
        std20 = _extract_rows(client.standard_deviation(symbol, period_length=20, timeframe=timeframe))
        wma20 = _extract_rows(client.wma(symbol, period_length=20, timeframe=timeframe))

        def latest_value(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
            if not rows:
                return {}
            rows = sorted(rows, key=lambda x: str(x.get("date", "")), reverse=True)
            return rows[0]

        latest = {
            "sma20": latest_value(sma20),
            "sma50": latest_value(sma50),
            "ema20": latest_value(ema20),
            "wma20": latest_value(wma20),
            "rsi14": latest_value(rsi14),
            "adx14": latest_value(adx14),
            "williams14": latest_value(williams14),
            "standard_deviation20": latest_value(std20),
        }

        payload = {
            "ok": any(bool(v) for v in latest.values()),
            "tool": "get_technical_indicator_bundle",
            "symbol": symbol,
            "timeframe": timeframe,
            "latest": latest,
            "unsupported_in_current_mcp_catalog": ["macd", "atr"],
            "mcp_note": "Uses only endpoints exposed by the current FMP MCP technicalIndicators schema.",
        }
        return _safe_json_dumps(payload)

    return [
            _make_tool(get_price_snapshot),
            _make_tool(get_price_history_bundle),
            _make_tool(compare_price_returns),
            _make_tool(get_technical_indicator_bundle),
        ]
