from __future__ import annotations

from typing import Iterable

from langgraphagenticai.portfolio_manager.data_sources import build_reference_universe


def parse_tickers(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        vals = value
    else:
        vals = str(value).replace("\n", " ").replace(",", " ").split()
    return sorted({str(x).upper().strip() for x in vals if str(x).strip()})


def build_analysis_universe(holdings_tickers: Iterable[str], watchlist: str | list[str], benchmark: str) -> list[str]:
    tickers = list(holdings_tickers) + parse_tickers(watchlist)
    return build_reference_universe(tickers, benchmark)
