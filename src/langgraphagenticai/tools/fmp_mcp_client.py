from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Dict, Optional

from fastmcp import Client as MCPClient


class FMPMCPClient:
    """
    Synchronous compatibility wrapper around FMP's hosted MCP server.

    Current FMP MCP calls use a grouped tool + endpoint shape, for example:
        await client.call_tool("quote", {"endpoint": "quote", "symbol": "AAPL"})
        await client.call_tool("company", {"endpoint": "profile-symbol", "symbol": "AAPL"})
        await client.call_tool("statements", {"endpoint": "income-statement", "symbol": "AAPL"})

    The rest of this app can keep calling simple sync methods such as:
        client.quote("AAPL")
        client.profile("AAPL")
        client.key_metrics_ttm("AAPL")
    """

    MCP_URL_TEMPLATE = "https://financialmodelingprep.com/mcp?apikey={api_key}"

    def __init__(self, api_key: str, retries: int = 2, retry_sleep: float = 0.8, timeout_seconds: int = 45) -> None:
        if not api_key:
            raise ValueError("FMP_API_KEY is required")
        self.api_key = str(api_key).strip().strip('"').strip("'")
        self.retries = max(0, int(retries))
        self.retry_sleep = max(0.1, float(retry_sleep))
        self.timeout_seconds = max(10, int(timeout_seconds))
        self.mcp_url = self.MCP_URL_TEMPLATE.format(api_key=self.api_key)

    # ------------------------------------------------------------------
    # General helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_symbol(symbol: str) -> str:
        return (symbol or "").strip().upper()

    @staticmethod
    def _clean_period(period: str) -> str:
        p = (period or "annual").strip().lower()
        if p in {"annual", "annually", "fy", "year"}:
            return "annual"
        if p in {"quarter", "quarterly", "q"}:
            return "quarter"
        return "annual"

    @staticmethod
    def _clean_timeframe(timeframe: str) -> str:
        tf = (timeframe or "daily").strip().lower().replace("_", "-")
        mapping = {
            "day": "daily", "daily": "daily", "1d": "daily", "d": "daily",
            "1min": "1min", "1m": "1min", "1-min": "1min",
            "5min": "5min", "5m": "5min", "5-min": "5min",
            "15min": "15min", "15m": "15min", "15-min": "15min",
            "30min": "30min", "30m": "30min", "30-min": "30min",
            "1hour": "1hour", "1h": "1hour", "hour": "1hour", "1-hour": "1hour",
            "4hour": "4hour", "4h": "4hour", "4-hour": "4hour",
        }
        return mapping.get(tf, "daily")

    @staticmethod
    def _bounded_limit(limit: int, default: int = 4, min_value: int = 1, max_value: int = 100) -> int:
        try:
            value = int(limit)
        except Exception:
            value = default
        return max(min_value, min(value, max_value))

    @staticmethod
    def _strip_empty(params: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in params.items() if v is not None and v != ""}

    def _normalize_response(self, tool_name: str, endpoint: str, params: Dict[str, Any], data: Any, error: Optional[str] = None) -> Dict[str, Any]:
        return {
            "ok": error is None,
            "tool": endpoint or tool_name,
            "mcp_tool_name": tool_name,
            "endpoint": endpoint,
            "params": params,
            "data": data if error is None else [],
            "error": error,
        }

    @staticmethod
    def _extract_structured_content(result: Any) -> Any:
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            return structured
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            return structured
        return getattr(result, "content", None)

    @staticmethod
    def _extract_data(payload: Any) -> Any:
        """Normalize FastMCP/FMP payloads into the useful data body."""
        if isinstance(payload, list):
            parsed = []
            for item in payload:
                text = getattr(item, "text", None)
                if text is None and isinstance(item, dict):
                    text = item.get("text")
                if isinstance(text, str):
                    try:
                        parsed.append(json.loads(text))
                    except Exception:
                        parsed.append(text)
                else:
                    parsed.append(item)
            if len(parsed) == 1:
                return FMPMCPClient._extract_data(parsed[0])
            return parsed

        if isinstance(payload, dict):
            if "structured_content" in payload:
                return FMPMCPClient._extract_data(payload.get("structured_content"))
            if "structuredContent" in payload:
                return FMPMCPClient._extract_data(payload.get("structuredContent"))
            if "data" in payload:
                return payload.get("data")
        return payload

    @staticmethod
    def _run_coro_sync(coro):
        try:
            asyncio.get_running_loop()
            loop_is_running = True
        except RuntimeError:
            loop_is_running = False

        if not loop_is_running:
            return asyncio.run(coro)

        result_box: Dict[str, Any] = {}
        error_box: Dict[str, BaseException] = {}

        def runner():
            try:
                result_box["result"] = asyncio.run(coro)
            except BaseException as exc:  # noqa: BLE001
                error_box["error"] = exc

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("result")

    def _call_mcp(self, tool_name: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = self._strip_empty(dict(params or {}))
        args = {"endpoint": endpoint, **params}

        async def _call_once() -> Dict[str, Any]:
            async with MCPClient(self.mcp_url) as client:
                result = await client.call_tool(tool_name, args)
                structured = self._extract_structured_content(result)
                data = self._extract_data(structured)
                return self._normalize_response(tool_name, endpoint, args, data)

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                return self._run_coro_sync(_call_once())
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if attempt < self.retries:
                    try:
                        import time
                        time.sleep(self.retry_sleep * (attempt + 1))
                    except Exception:
                        pass
        return self._normalize_response(tool_name, endpoint, args, [], error=last_error or "Unknown MCP error")

    def call(self, tool_name: str, endpoint: str, **params: Any) -> Dict[str, Any]:
        return self._call_mcp(tool_name, endpoint, params)

    def list_tools(self) -> Any:
        async def _list_once() -> Any:
            async with MCPClient(self.mcp_url) as client:
                return await client.list_tools()
        return self._run_coro_sync(_list_once())

    # ------------------------------------------------------------------
    # Quote / market data: tool_name="quote"
    # ------------------------------------------------------------------
    def quote(self, symbol: str):
        return self._call_mcp("quote", "quote", {"symbol": self._clean_symbol(symbol)})

    def quote_short(self, symbol: str):
        return self._call_mcp("quote", "quote-short", {"symbol": self._clean_symbol(symbol)})

    def quote_change(self, symbol: str):
        return self._call_mcp("quote", "quote-change", {"symbol": self._clean_symbol(symbol)})

    def batch_quote(self, symbols: str):
        return self._call_mcp("quote", "batch-quote", {"symbols": symbols})

    def batch_quote_short(self, symbols: str):
        return self._call_mcp("quote", "batch-quote-short", {"symbols": symbols})

    def aftermarket_trade(self, symbol: str):
        return self._call_mcp("quote", "aftermarket-trade", {"symbol": self._clean_symbol(symbol)})

    def aftermarket_quote(self, symbol: str):
        return self._call_mcp("quote", "aftermarket-quote", {"symbol": self._clean_symbol(symbol)})

    # ------------------------------------------------------------------
    # Company data: tool_name="company"
    # ------------------------------------------------------------------
    def profile(self, symbol: str):
        return self._call_mcp("company", "profile-symbol", {"symbol": self._clean_symbol(symbol)})

    def profile_cik(self, cik: str):
        return self._call_mcp("company", "profile-cik", {"cik": str(cik).strip()})

    def peers(self, symbol: str):
        return self._call_mcp("company", "peers", {"symbol": self._clean_symbol(symbol)})

    def market_cap(self, symbol: str):
        return self._call_mcp("company", "market-cap", {"symbol": self._clean_symbol(symbol)})

    def batch_market_cap(self, symbols: str):
        return self._call_mcp("company", "batch-market-cap", {"symbols": symbols})

    def historical_market_cap(self, symbol: str, limit: int = 10):
        return self._call_mcp("company", "historical-market-cap", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit, default=10, max_value=250)})

    def shares_float(self, symbol: str):
        return self._call_mcp("company", "shares-float", {"symbol": self._clean_symbol(symbol)})

    def all_shares_float(self, limit: int = 100):
        return self._call_mcp("company", "all-shares-float", {"limit": self._bounded_limit(limit, default=100, max_value=1000)})

    def company_executives(self, symbol: str):
        return self._call_mcp("company", "company-executives", {"symbol": self._clean_symbol(symbol)})

    def company_notes(self, symbol: str):
        return self._call_mcp("company", "company-notes", {"symbol": self._clean_symbol(symbol)})

    # ------------------------------------------------------------------
    # Statements / ratios / fundamentals: tool_name="statements"
    # ------------------------------------------------------------------
    def income_statement(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "income-statement", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def balance_sheet(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "balance-sheet-statement", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def cashflow_statement(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "cashflow-statement", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def latest_financial_statements(self, symbol: str):
        return self._call_mcp("statements", "latest-financial-statements", {"symbol": self._clean_symbol(symbol)})

    def income_statement_ttm(self, symbol: str):
        return self._call_mcp("statements", "income-statements-ttm", {"symbol": self._clean_symbol(symbol)})

    def balance_sheet_ttm(self, symbol: str):
        return self._call_mcp("statements", "balance-sheet-statements-ttm", {"symbol": self._clean_symbol(symbol)})

    def cashflow_statement_ttm(self, symbol: str):
        return self._call_mcp("statements", "cashflow-statements-ttm", {"symbol": self._clean_symbol(symbol)})

    def key_metrics(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "key-metrics", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def metrics_ratios(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "metrics-ratios", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def key_metrics_ttm(self, symbol: str):
        return self._call_mcp("statements", "key-metrics-ttm", {"symbol": self._clean_symbol(symbol)})

    def metrics_ratios_ttm(self, symbol: str):
        return self._call_mcp("statements", "metrics-ratios-ttm", {"symbol": self._clean_symbol(symbol)})

    def financial_scores(self, symbol: str):
        return self._call_mcp("statements", "financial-scores", {"symbol": self._clean_symbol(symbol)})

    def owner_earnings(self, symbol: str):
        return self._call_mcp("statements", "owner-earnings", {"symbol": self._clean_symbol(symbol)})

    def enterprise_values(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "enterprise-values", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def income_statement_growth(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "income-statement-growth", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def balance_sheet_growth(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "balance-sheet-statement-growth", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def cashflow_growth(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "cashflow-statement-growth", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def financial_statement_growth(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "financial-statement-growth", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def revenue_product_segmentation(self, symbol: str):
        return self._call_mcp("statements", "revenue-product-segmentation", {"symbol": self._clean_symbol(symbol)})

    def revenue_geographic_segmentation(self, symbol: str):
        return self._call_mcp("statements", "revenue-geographic-segments", {"symbol": self._clean_symbol(symbol)})

    def as_reported_income_statements(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "as-reported-income-statements", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def as_reported_balance_sheet_statements(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "as-reported-balance-statements", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    def as_reported_cash_flow_statements(self, symbol: str, limit: int = 4, period: str = "annual"):
        return self._call_mcp("statements", "as-reported-cashflow-statements", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit), "period": self._clean_period(period)})

    # ------------------------------------------------------------------
    # Analyst data: tool_name="analyst"
    # ------------------------------------------------------------------
    def ratings_snapshot(self, symbol: str):
        return self._call_mcp("analyst", "ratings-snapshot", {"symbol": self._clean_symbol(symbol)})

    def price_target_summary(self, symbol: str):
        return self._call_mcp("analyst", "price-target-summary", {"symbol": self._clean_symbol(symbol)})

    def price_target_consensus(self, symbol: str):
        return self._call_mcp("analyst", "price-target-consensus", {"symbol": self._clean_symbol(symbol)})

    def analyst_estimates(self, symbol: str, period: str = "annual", limit: int = 8):
        return self._call_mcp("analyst", "financial-estimates", {"symbol": self._clean_symbol(symbol), "period": self._clean_period(period), "limit": self._bounded_limit(limit, default=8)})

    def grades(self, symbol: str, limit: int = 20):
        return self._call_mcp("analyst", "grades", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit, default=20)})

    def grades_summary(self, symbol: str):
        return self._call_mcp("analyst", "grades-summary", {"symbol": self._clean_symbol(symbol)})

    def historical_ratings(self, symbol: str, limit: int = 20):
        return self._call_mcp("analyst", "historical-ratings", {"symbol": self._clean_symbol(symbol), "limit": self._bounded_limit(limit, default=20)})

    # ------------------------------------------------------------------
    # Historical prices: tool_name="chart"
    # ------------------------------------------------------------------
    def historical_price_full(self, symbol: str, from_date: Optional[str] = None, to_date: Optional[str] = None, nonadjusted: Optional[bool] = None):
        params: Dict[str, Any] = {"symbol": self._clean_symbol(symbol)}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if nonadjusted is not None:
            params["nonadjusted"] = bool(nonadjusted)
        return self._call_mcp("chart", "historical-price-eod-full", params)

    def historical_price_light(self, symbol: str, from_date: Optional[str] = None, to_date: Optional[str] = None):
        params: Dict[str, Any] = {"symbol": self._clean_symbol(symbol)}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._call_mcp("chart", "historical-price-eod-light", params)

    # ------------------------------------------------------------------
    # Technical indicators: tool_name="technicalIndicators"
    # ------------------------------------------------------------------
    def sma(self, symbol: str, period_length: int = 20, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "simple-moving-average", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def ema(self, symbol: str, period_length: int = 20, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "exponential-moving-average", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def rsi(self, symbol: str, period_length: int = 14, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "relative-strength-index", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def adx(self, symbol: str, period_length: int = 14, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "average-directional-index", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def williams(self, symbol: str, period_length: int = 14, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "williams", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def standard_deviation(self, symbol: str, period_length: int = 20, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "standard-deviation", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def wma(self, symbol: str, period_length: int = 20, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "weighted-moving-average", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def dema(self, symbol: str, period_length: int = 20, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "double-exponential-moving-average", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def tema(self, symbol: str, period_length: int = 20, timeframe: str = "daily"):
        return self._call_mcp("technicalIndicators", "triple-exponential-moving-average", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)})

    def macd(self, symbol: str, timeframe: str = "daily"):
        return self._normalize_response("technicalIndicators", "moving-average-convergence-divergence", {"symbol": self._clean_symbol(symbol), "timeframe": self._clean_timeframe(timeframe)}, [], error="MACD is not exposed in the current FMP MCP technicalIndicators catalog.")

    def atr(self, symbol: str, period_length: int = 14, timeframe: str = "daily"):
        return self._normalize_response("technicalIndicators", "average-true-range", {"symbol": self._clean_symbol(symbol), "periodLength": int(period_length), "timeframe": self._clean_timeframe(timeframe)}, [], error="ATR is not exposed in the current FMP MCP technicalIndicators catalog.")

    # ------------------------------------------------------------------
    # News: tool_name="news"
    # ------------------------------------------------------------------
    def stock_news(self, symbol: str, limit: int = 10):
        return self._call_mcp("news", "search-stock-news", {"symbols": self._clean_symbol(symbol), "limit": self._bounded_limit(limit, default=10, max_value=100)})

    def general_news(self, limit: int = 10):
        return self._call_mcp("news", "general-news", {"limit": self._bounded_limit(limit, default=10, max_value=100)})

    def press_releases(self, symbol: str, limit: int = 10):
        return self._call_mcp("news", "search-press-releases", {"symbols": self._clean_symbol(symbol), "limit": self._bounded_limit(limit, default=10, max_value=100)})

    # ------------------------------------------------------------------
    # Earnings transcripts: tool_name="earningsTranscript"
    # ------------------------------------------------------------------
    def available_transcript_symbols(self, limit: int = 100):
        return self._call_mcp("earningsTranscript", "available-transcript-symbols", {"limit": self._bounded_limit(limit, default=100, max_value=1000)})

    def latest_transcripts(self, symbol: Optional[str] = None, limit: int = 20):
        params: Dict[str, Any] = {"limit": self._bounded_limit(limit, default=20, max_value=100)}
        if symbol:
            params["symbol"] = self._clean_symbol(symbol)
        return self._call_mcp("earningsTranscript", "latest-transcripts", params)

    def search_transcripts(self, symbol: str, year: Optional[int] = None, quarter: Optional[int] = None):
        params: Dict[str, Any] = {"symbol": self._clean_symbol(symbol)}
        if year is not None:
            params["year"] = int(year)
        if quarter is not None:
            params["quarter"] = int(quarter)
        return self._call_mcp("earningsTranscript", "search-transcripts", params)

    def transcript_dates_by_symbol(self, symbol: str):
        return self._call_mcp("earningsTranscript", "transcripts-dates-by-symbol", {"symbol": self._clean_symbol(symbol)})
