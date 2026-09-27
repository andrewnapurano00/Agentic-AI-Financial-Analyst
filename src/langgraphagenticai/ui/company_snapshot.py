from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage

from langgraphagenticai.LLMS.openaillm import OpenAILLM
from langgraphagenticai.portfolio_manager.data_sources import fetch_recent_news
from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.utils.safety import sanitize_error

try:
    import truststore

    truststore.inject_into_ssl()
except (ImportError, NotImplementedError):
    pass


def normalize_symbol(value: str) -> str:
    symbol = re.sub(r"[^A-Za-z0-9.\-]", "", str(value or "").upper().strip())
    if not symbol or len(symbol) > 12:
        raise ValueError("Enter a valid ticker, such as AAPL, MSFT, or BRK.B.")
    return symbol


def _get(url: str, api_key: str, **params: Any) -> Any:
    return get_fmp_json(url, api_key=api_key, params=params, timeout=(5, 20))


def _first(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return payload if isinstance(payload, dict) else {}


def _number(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        try:
            value = float(row.get(key))
            if pd.notna(value):
                return value
        except (TypeError, ValueError):
            continue
    return None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    return numerator / denominator if numerator is not None and denominator not in (None, 0) else None


def _validated_quarters(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    """Return consecutive, deduplicated quarterly rows newest first."""
    normalized: list[tuple[pd.Timestamp, str, dict[str, Any]]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        period = str(row.get("period") or "").upper().strip()
        if period not in {"Q1", "Q2", "Q3", "Q4"}:
            continue
        stamp = pd.to_datetime(row.get("date") or row.get("fillingDate"), errors="coerce")
        if pd.isna(stamp):
            continue
        key = f"{row.get('fiscalYear') or stamp.year}:{period}"
        if key in seen:
            continue
        seen.add(key)
        normalized.append((stamp, key, row))
    normalized.sort(key=lambda item: item[0], reverse=True)
    selected = normalized[:limit]
    currencies = {str(item[2].get("reportedCurrency") or "").upper() for item in selected if item[2].get("reportedCurrency")}
    if len(currencies) > 1:
        return []
    for current, following in zip(selected, selected[1:]):
        gap = (current[0] - following[0]).days
        if gap < 60 or gap > 130:
            return []
        current_row, following_row = current[2], following[2]
        try:
            current_rank = int(current_row.get("fiscalYear")) * 4 + int(str(current_row.get("period"))[1:])
            following_rank = int(following_row.get("fiscalYear")) * 4 + int(str(following_row.get("period"))[1:])
        except (TypeError, ValueError):
            return []
        if current_rank - following_rank != 1:
            return []
    return [row for _, _, row in selected]


def _sum_quarters(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_number(row, key) for row in rows]
    return sum(value for value in values if value is not None) if rows and all(value is not None for value in values) else None


def _quote_timestamp(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value) if value else None


def _performance(history: pd.DataFrame) -> dict[str, Any]:
    if history.empty:
        return {"series": []}
    frame = history.sort_values("date").dropna(subset=["close"])
    close = frame["close"].astype(float).reset_index(drop=True)
    last = float(close.iloc[-1])
    result: dict[str, Any] = {
        "series": frame[["date", "close"]].tail(260).to_dict("records"),
        "as_of": str(frame.iloc[-1]["date"]),
        "last_close": last,
        "high_52w": float(close.tail(252).max()),
        "low_52w": float(close.tail(252).min()),
    }
    for label, window in (("return_1m", 21), ("return_3m", 63), ("return_1y", 252)):
        result[label] = (last / float(close.iloc[-window - 1]) - 1) if len(close) > window else None
    result["sma_50"] = float(close.tail(50).mean()) if len(close) >= 50 else None
    result["sma_200"] = float(close.tail(200).mean()) if len(close) >= 200 else None
    result["volatility"] = float(close.pct_change().dropna().tail(252).std() * (252 ** 0.5)) if len(close) > 21 else None
    return result


@st.cache_data(ttl=900, show_spinner=False)
def load_company_snapshot(symbol: str, fmp_api_key: str, marketaux_api_key: str = "") -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    if not fmp_api_key.strip():
        raise ValueError("FMP API key is required for company search.")
    start = (date.today() - timedelta(days=430)).isoformat()
    jobs = {
        "profile": (f"https://financialmodelingprep.com/api/v3/profile/{symbol}", {}),
        "quote": (f"https://financialmodelingprep.com/api/v3/quote/{symbol}", {}),
        "income": (f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}", {"period": "quarter", "limit": 8}),
        "cashflow": (f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{symbol}", {"period": "quarter", "limit": 8}),
        "ratios": ("https://financialmodelingprep.com/stable/ratios-ttm", {"symbol": symbol}),
        "metrics": ("https://financialmodelingprep.com/stable/key-metrics-ttm", {"symbol": symbol}),
        "history": (f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}", {"from": start, "to": date.today().isoformat()}),
    }
    payloads: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_get, url, fmp_api_key, **params): name for name, (url, params) in jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                payloads[name] = future.result()
            except Exception as exc:
                payloads[name] = {"_error": sanitize_error(exc)}

    quote, profile = _first(payloads.get("quote")), _first(payloads.get("profile"))
    if not quote and not profile:
        raise ValueError(f"No company data was returned for {symbol}.")
    income_rows = payloads.get("income") if isinstance(payloads.get("income"), list) else []
    cash_rows = payloads.get("cashflow") if isinstance(payloads.get("cashflow"), list) else []
    ratios, metrics = _first(payloads.get("ratios")), _first(payloads.get("metrics"))
    history_payload = payloads.get("history", {})
    history_rows = history_payload.get("historical", []) if isinstance(history_payload, dict) else []
    history = pd.DataFrame(history_rows)
    if not history.empty:
        history["date"] = pd.to_datetime(history["date"], errors="coerce").dt.date.astype(str)
        history["close"] = pd.to_numeric(history["close"], errors="coerce")

    validated_income = _validated_quarters(income_rows, limit=8)
    validated_cash = _validated_quarters(cash_rows, limit=4)
    latest_income = validated_income[:4] if len(validated_income) >= 4 else []
    prior_income = validated_income[4:8] if len(validated_income) >= 8 else []
    latest_cash = validated_cash[:4] if len(validated_cash) >= 4 else []
    revenue = _sum_quarters(latest_income, "revenue")
    operating_income = _sum_quarters(latest_income, "operatingIncome")
    net_income = _sum_quarters(latest_income, "netIncome")
    free_cash_flow = _sum_quarters(latest_cash, "freeCashFlow")
    prior_revenue = _sum_quarters(prior_income, "revenue")
    news = fetch_recent_news([symbol], marketaux_api_key, lookback_days=10, max_articles=5)
    articles = [] if news.empty else news[["title", "summary", "source", "url", "published_at", "effective_sentiment", "theme_labels"]].fillna("").to_dict("records")

    return {
        "symbol": symbol,
        "company": profile.get("companyName") or quote.get("name") or symbol,
        "profile": {"sector": profile.get("sector"), "industry": profile.get("industry"), "description": profile.get("description"), "website": profile.get("website")},
        "quote": {
            "price": _number(quote, "price"), "change": _number(quote, "change"),
            "change_pct": _number(quote, "changesPercentage"), "market_cap": _number(quote, "marketCap"),
            "volume": _number(quote, "volume"), "avg_volume": _number(quote, "avgVolume"),
            "day_low": _number(quote, "dayLow"), "day_high": _number(quote, "dayHigh"),
            "year_low": _number(quote, "yearLow"), "year_high": _number(quote, "yearHigh"),
            "timestamp": _quote_timestamp(quote.get("timestamp")),
        },
        "fundamentals": {
            "revenue_ttm": revenue, "revenue_growth": (_ratio(revenue, prior_revenue) - 1) if _ratio(revenue, prior_revenue) is not None else None,
            "operating_margin": _ratio(operating_income, revenue), "net_margin": _ratio(net_income, revenue),
            "free_cash_flow_ttm": free_cash_flow, "pe_ttm": _number(ratios, "priceToEarningsRatioTTM", "priceEarningsRatioTTM"),
            "price_to_sales": _number(ratios, "priceToSalesRatioTTM"), "price_to_book": _number(ratios, "priceToBookRatioTTM"),
            "roe": _number(ratios, "returnOnEquityTTM"), "roic": _number(metrics, "returnOnInvestedCapitalTTM"),
            "debt_to_equity": _number(ratios, "debtToEquityRatioTTM"), "fcf_yield": _number(metrics, "freeCashFlowYieldTTM"),
        },
        "performance": _performance(history), "news": articles,
        "fundamental_basis": {
            "period": "TTM" if latest_income else "Unavailable",
            "through": str(latest_income[0].get("date")) if latest_income else None,
            "currency": latest_income[0].get("reportedCurrency") if latest_income else None,
            "status": "complete" if latest_income and latest_cash else "partial",
        },
        "source_errors": {key: value["_error"] for key, value in payloads.items() if isinstance(value, dict) and value.get("_error")},
        "fetched_at": datetime.now(timezone.utc).isoformat(), "providers": ["Financial Modeling Prep", "MarketAux" if marketaux_api_key else "MarketAux not configured"],
    }


@st.cache_data(ttl=1800, show_spinner=False)
def generate_company_summary(snapshot_json: str, openai_api_key: str, model_name: str) -> str:
    if not openai_api_key.strip():
        return "OpenAI is not configured. Financial and price data are available, but the evidence-based AI summary cannot be generated."
    snapshot = json.loads(snapshot_json)
    evidence = {
        "symbol": snapshot["symbol"], "company": snapshot["company"], "profile": snapshot["profile"],
        "quote": snapshot["quote"], "fundamentals": snapshot["fundamentals"],
        "performance": {key: value for key, value in snapshot["performance"].items() if key != "series"},
        "news": snapshot["news"], "fetched_at": snapshot["fetched_at"], "providers": snapshot["providers"],
    }
    llm = OpenAILLM({"OPENAI_API_KEY": openai_api_key, "selected_model": model_name, "timeout": 75, "max_retries": 1, "reasoning_effort": "low"}).get_llm_model()
    response = llm.invoke([
        SystemMessage(content="You are a careful equity research analyst. Use only the supplied evidence. Never invent missing facts. Distinguish facts from interpretation. Be concise and balanced; this is research, not personalized investment advice."),
        HumanMessage(content=(
            "Write a compact company snapshot of no more than 450 words. Use exactly these Markdown headings, each prefixed with ###: Investment view, Fundamentals, Recent performance, News and catalysts, Risks, Data caveats. "
            "Use concrete figures when present, cite news inline as [Source — date](URL), and explicitly say when evidence is unavailable.\n\nEVIDENCE:\n" + json.dumps(evidence, default=str)
        )),
    ])
    return str(response.content).strip()


def snapshot_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, default=str, sort_keys=True)
