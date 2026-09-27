from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from langgraphagenticai.providers.fmp_http import get_fmp_json
from langgraphagenticai.tools.serper_tools import SerperClient
from langgraphagenticai.utils.safety import sanitize_error

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
def load_top_movers(fmp_api_key: str, serper_api_key: str = "", limit: int = 12) -> dict[str, Any]:
    if not fmp_api_key.strip():
        raise ValueError("FMP API key is required for the market-wide movers screen.")
    universe = _get(
        "https://financialmodelingprep.com/api/v3/stock-screener", fmp_api_key,
        marketCapMoreThan=2_000_000_000, volumeMoreThan=500_000, country="US",
        isEtf="false", isFund="false", isActivelyTrading="true", limit=500,
    )
    if not isinstance(universe, list) or not universe:
        raise RuntimeError("FMP returned no liquid U.S. equities for the movers universe.")
    base = pd.DataFrame(universe)
    for flag in ("isEtf", "isFund"):
        if flag not in base:
            base[flag] = False
    base = base[(base["isEtf"] != True) & (base["isFund"] != True)].copy()  # noqa: E712
    symbols = base["symbol"].dropna().astype(str).str.upper().unique().tolist()

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
                if isinstance(rows, list):
                    changes.extend(row for row in rows if isinstance(row, dict))
            except Exception as exc:
                failed_chunks.append({
                    "symbols": list(futures[future]),
                    "error": sanitize_error(exc),
                })
    change_frame = pd.DataFrame(changes)
    if change_frame.empty or "5D" not in change_frame:
        raise RuntimeError("FMP returned no five-day performance data.")
    movers = base.merge(change_frame, on="symbol", how="inner")
    for column in ("price", "marketCap", "volume", "avgVolume", "1D", "5D", "1M", "ytd"):
        if column in movers:
            movers[column] = pd.to_numeric(movers[column], errors="coerce")
    movers = movers.dropna(subset=["5D", "price"]).copy()
    movers["liquidityRatio"] = movers["volume"] / movers["avgVolume"].replace(0, pd.NA)
    movers = movers.sort_values("marketCap", ascending=False).drop_duplicates("symbol")

    gainers = movers.nlargest(limit, "5D").reset_index(drop=True)
    losers = movers.nsmallest(limit, "5D").reset_index(drop=True)
    sector = (
        movers.groupby("sector", dropna=False)
        .agg(weekly_return=("5D", "mean"), median_return=("5D", "median"), advancers=("5D", lambda s: int((s > 0).sum())), decliners=("5D", lambda s: int((s < 0).sum())), stocks=("symbol", "count"))
        .reset_index().sort_values("weekly_return", ascending=False)
    )

    focus_symbols = gainers.head(4)["symbol"].tolist() + losers.head(4)["symbol"].tolist()
    news: dict[str, list[dict]] = {symbol: [] for symbol in focus_symbols}
    news_errors: dict[str, str] = {}
    if serper_api_key.strip():
        client = SerperClient(serper_api_key)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(client.search, f"{symbol} stock company news", news=True, days=7, limit=3): symbol
                for symbol in focus_symbols
            }
            for future in as_completed(futures):
                symbol = futures[future]
                result = future.result()
                news[symbol] = result.get("results", []) if result.get("ok") else []
                if result.get("error"):
                    news_errors[symbol] = str(result["error"])

    return {
        "universe": movers, "gainers": gainers, "losers": losers, "sectors": sector,
        "news": news, "news_errors": news_errors, "universe_size": int(len(movers)),
        "requested_universe_size": int(len(symbols)),
        "coverage_pct": round((len(movers) / len(symbols) * 100.0), 2) if symbols else 0.0,
        "partial": bool(failed_chunks or len(movers) < len(symbols)),
        "provider_warnings": [
            f"{len(failed_chunks)} FMP price-change batch(es) failed; rankings use {len(movers)} of {len(symbols)} requested symbols."
        ] if failed_chunks else ([
            f"FMP returned usable five-day data for {len(movers)} of {len(symbols)} requested symbols."
        ] if len(movers) < len(symbols) else []),
        "failed_chunks": failed_chunks,
        "fetched_at": datetime.now(timezone.utc),
        "providers": ["Financial Modeling Prep", "Serper" if serper_api_key else "Serper not configured"],
    }
