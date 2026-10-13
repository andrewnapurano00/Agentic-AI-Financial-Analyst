from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.tools.serper_tools import SerperClient
from langgraphagenticai.utils.safety import sanitize_error
from langgraphagenticai.providers.discovery_numbers import finite_number
from langgraphagenticai.analysis.discovery import rank_discovery, sector_summary, PERIODS
from langgraphagenticai.state.research_context import normalize_company_symbol

try:
    import truststore

    truststore.inject_into_ssl()
except (ImportError, NotImplementedError):
    pass


def _get(url: str, api_key: str, **params: Any) -> Any:
    return get_fmp_json(url, api_key=api_key, params=params, timeout=(5, 25))


def _chunks(values: list[str], size: int = 80):
    for index in range(0, len(values), size):
        yield values[index:index + size]


@st.cache_data(ttl=900, show_spinner=False)
def collect_discovery(fmp_api_key: str, serper_api_key: str = "", limit: int = 12) -> dict[str, Any]:
    if not fmp_api_key.strip():
        raise ValueError("FMP API key is required for the market-wide movers screen.")
    universe = _get(
        "https://financialmodelingprep.com/api/v3/stock-screener", fmp_api_key,
        marketCapMoreThan=2_000_000_000, volumeMoreThan=500_000, country="US",
        isEtf="false", isFund="false", isActivelyTrading="true", limit=500,
    )
    if not isinstance(universe, list) or not universe:
        raise RuntimeError("FMP returned no liquid U.S. equities for the movers universe.")
    base = pd.DataFrame([row for row in universe[:500] if isinstance(row, dict)])
    if base.empty or "symbol" not in base:
        raise RuntimeError("FMP returned no valid screened symbols.")
    for flag in ("isEtf", "isFund"):
        if flag not in base:
            base[flag] = False
    base = base[(base["isEtf"] != True) & (base["isFund"] != True)].copy()  # noqa: E712
    def valid_symbol(value):
        try:
            return normalize_company_symbol(value)
        except ValueError:
            return None
    base["symbol"] = base["symbol"].map(valid_symbol)
    base = base.dropna(subset=["symbol"]).drop_duplicates("symbol").head(500)
    if base.empty:
        raise RuntimeError("FMP returned no valid screened symbols.")
    symbols = base["symbol"].dropna().astype(str).str.upper().str.strip().unique().tolist()

    changes: list[dict] = []
    failed_chunks: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_get, f"https://financialmodelingprep.com/api/v3/stock-price-change/{','.join(chunk)}", fmp_api_key): chunk
            for chunk in _chunks(symbols)
        }
        for future in as_completed(futures):
            try:
                rows = future.result()
                if not isinstance(rows, list):
                    raise ValueError("FMP returned an invalid price-change batch.")
                changes.extend(row for row in rows if isinstance(row, dict))
            except Exception as exc:
                failed_chunks.append({
                    "symbols": list(futures[future]),
                    "error": sanitize_error(exc),
                })
    change_frame = pd.DataFrame(changes)
    if change_frame.empty or "symbol" not in change_frame:
        change_frame = pd.DataFrame(columns=["symbol", *PERIODS])
    base["symbol"] = base["symbol"].astype(str).str.upper().str.strip()
    change_frame["symbol"] = change_frame["symbol"].astype(str).str.upper().str.strip()
    change_frame = change_frame.drop_duplicates("symbol")
    movers = base.merge(change_frame[[col for col in ("symbol", "1D", "5D", "1M", "ytd") if col in change_frame]], on="symbol", how="left")
    enrichment_warnings = []
    for column in ("price", "marketCap", "volume", "avgVolume", "1D", "5D", "1M", "ytd", "sector", "companyName"):
        if column not in movers:
            movers[column] = float("nan")
    movers["sector"] = movers["sector"].fillna("Unknown")
    for column in ("price", "marketCap", "volume", "avgVolume", "1D", "5D", "1M", "ytd"):
        if column in movers:
            movers[column] = pd.to_numeric(movers[column].map(finite_number), errors="coerce")
    movers = movers.replace([float("inf"), float("-inf")], float("nan")).copy()
    movers["liquidityRatio"] = movers["volume"] / movers["avgVolume"].where(movers["avgVolume"] > 0)
    movers = movers.sort_values("marketCap", ascending=False).drop_duplicates("symbol")

    if movers.empty:
        raise RuntimeError("No usable prices and five-day returns were returned. Refresh to retry.")

    gainers, _ = rank_discovery(movers, "5D", limit=limit)
    losers, _ = rank_discovery(movers, "5D", direction="Laggards", limit=limit)
    finite_weekly = movers.dropna(subset=["5D"])
    sector = (
        finite_weekly.groupby("sector", dropna=False)
        .agg(weekly_return=("5D", "mean"), median_return=("5D", "median"), advancers=("5D", lambda s: int((s > 0).sum())), decliners=("5D", lambda s: int((s < 0).sum())), stocks=("symbol", "count"))
        .reset_index().sort_values("weekly_return", ascending=False)
    )

    usable = int(movers["5D"].notna().sum())
    news, news_errors = {}, {}
    return {
        "universe": movers, "gainers": gainers, "losers": losers, "sectors": sector,
        "news": news, "news_errors": news_errors, "universe_size": int(movers["5D"].notna().sum()),
        "requested_universe_size": int(len(symbols)),
        "coverage_pct": round((movers["5D"].notna().sum() / len(symbols) * 100.0), 2) if symbols else 0.0,
        "partial": bool(failed_chunks or movers["5D"].notna().sum() < len(symbols)),
        "provider_warnings": enrichment_warnings + ([
            f"{len(failed_chunks)} FMP price-change batch(es) failed; rankings use {usable} of {len(symbols)} requested symbols."
        ] if failed_chunks else ([
            f"FMP returned usable five-day data for {usable} of {len(symbols)} requested symbols."
        ] if movers["5D"].notna().sum() < len(symbols) else [])),
        "failed_chunks": failed_chunks,
        "fetched_at": datetime.now(timezone.utc),
        "providers": ["Financial Modeling Prep"],
        "period_coverage": {period: int(movers[period].notna().sum()) for period in PERIODS},
        "performance_as_of": None, "return_basis": "Provider price change; adjustment basis unavailable",
    }




@st.cache_data(ttl=900, show_spinner=False)
def load_selected_news(symbol, serper_api_key):
    symbol = normalize_company_symbol(symbol)
    if not serper_api_key.strip():
        return {"symbol": symbol, "results": [], "retrieved_at": None, "error": "Serper is not configured."}
    try:
        result = SerperClient(serper_api_key).search(f"{symbol} stock company news", news=True, days=7, limit=3)
        return {"symbol": symbol, "results": result.get("results", []) if result.get("ok") else [],
                "retrieved_at": result.get("retrieved_at"), "error": sanitize_error(result["error"]) if result.get("error") else None}
    except Exception as exc:
        return {"symbol": symbol, "results": [], "retrieved_at": None, "error": sanitize_error(exc)}


@st.cache_data(ttl=300, show_spinner=False)
def load_selected_quote(symbol, api_key):
    symbol = normalize_company_symbol(symbol)
    retrieved = datetime.now(timezone.utc).isoformat()
    if not api_key.strip():
        return {"symbol": symbol, "error": "FMP is not configured.", "retrieved_at": None}
    try:
        rows = _get(f"https://financialmodelingprep.com/api/v3/quote/{symbol}", api_key)
        row = next((item for item in rows if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol), None) if isinstance(rows, list) else None
        if row is None:
            raise ValueError("FMP returned no matching quote.")
        stamp = pd.to_datetime(row.get("timestamp"), unit="s", utc=True, errors="coerce")
        return {"symbol": symbol, "price": finite_number(row.get("price")),
                "change": finite_number(row.get("change")), "change_pct": finite_number(row.get("changesPercentage")) if finite_number(row.get("changesPercentage")) is not None else finite_number(row.get("changePercentage")),
                "year_low": finite_number(row.get("yearLow")), "year_high": finite_number(row.get("yearHigh")),
                "volume": finite_number(row.get("volume")), "avg_volume": finite_number(row.get("avgVolume")),
                "currency": row.get("currency") or "Unknown currency", "as_of": stamp.isoformat() if pd.notna(stamp) else None,
                "retrieved_at": retrieved, "provider": "Financial Modeling Prep", "error": None}
    except Exception as exc:
        return {"symbol": symbol, "error": sanitize_error(exc), "retrieved_at": retrieved}
