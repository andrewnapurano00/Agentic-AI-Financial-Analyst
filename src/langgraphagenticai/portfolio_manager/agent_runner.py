from __future__ import annotations

from typing import Any

import pandas as pd

from langgraphagenticai.portfolio_manager.agents import (
    run_catalyst_agent,
    run_debate_orchestrator,
    run_earnings_agent,
    run_fundamental_agent,
    run_lead_pm_agent,
    run_portfolio_fit_agent,
    run_risk_agent,
    run_screening_agent,
    run_technical_agent,
    run_valuation_agent,
)
from langgraphagenticai.portfolio_manager.schemas import TickerAnalysisBundle
from langgraphagenticai.portfolio_manager.sector_profiles import get_sector_profile


def _row_to_data(row: pd.Series) -> dict[str, Any]:
    return {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}


def run_single_ticker_agents(
    row: pd.Series,
    portfolio_context: dict[str, Any],
    openai_api_key: str,
    model_name: str,
) -> TickerAnalysisBundle:
    data = _row_to_data(row)
    ticker = str(data.get("ticker"))
    sector = str(data.get("sector") or "Unknown")
    industry = str(data.get("industry") or "Unknown")
    profile = get_sector_profile(sector)

    bundle = TickerAnalysisBundle(
        ticker=ticker,
        sector=sector,
        industry=industry,
        current_weight=float(data.get("current_weight") or 0.0),
        shares=float(data.get("shares") or 0.0),
        last_price=float(data.get("last_price") or 0.0),
        market_value=float(data.get("market_value") or 0.0),
        data=data,
    )

    bundle.screening = run_screening_agent(ticker, data, min_market_cap=profile["thresholds"]["min_market_cap"])
    bundle.fundamentals = run_fundamental_agent(ticker, data)
    bundle.valuation = run_valuation_agent(ticker, data)
    bundle.technicals = run_technical_agent(ticker, data)
    bundle.catalysts = run_catalyst_agent(ticker, data)
    bundle.earnings = run_earnings_agent(ticker, data)
    bundle.risk = run_risk_agent(ticker, data)
    bundle.portfolio_fit = run_portfolio_fit_agent(ticker, data, portfolio_context)
    bundle.debate = run_debate_orchestrator(bundle)
    bundle.final = run_lead_pm_agent(
        bundle,
        openai_api_key=openai_api_key,
        model_name=model_name,
        max_weight=float(portfolio_context.get("max_weight", 0.18)),
    )
    return bundle


def run_portfolio_agents(
    dataset: pd.DataFrame,
    portfolio_context: dict[str, Any],
    openai_api_key: str,
    model_name: str,
) -> dict[str, TickerAnalysisBundle]:
    bundles: dict[str, TickerAnalysisBundle] = {}
    if dataset is None or dataset.empty:
        return bundles
    for _, row in dataset.iterrows():
        bundle = run_single_ticker_agents(
            row=row,
            portfolio_context=portfolio_context,
            openai_api_key=openai_api_key,
            model_name=model_name,
        )
        bundles[bundle.ticker] = bundle
    return bundles
