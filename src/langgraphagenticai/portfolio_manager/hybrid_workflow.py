from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from langgraphagenticai.portfolio_manager.analytics import compute_market_regime, compute_position_snapshot
from langgraphagenticai.portfolio_manager.data_sources import build_multi_agent_dataset, fetch_company_info, fetch_price_history
from langgraphagenticai.portfolio_manager.fmp_screener import fmp_company_screener
from langgraphagenticai.portfolio_manager.portfolio_actions import split_recommendation_buckets
from langgraphagenticai.portfolio_manager.evidence_builder import build_evidence_table, clean_text
from langgraphagenticai.portfolio_manager.agentic_committee import run_agentic_committee, committee_result_to_table
from langgraphagenticai.portfolio_manager.constraint_validator import validate_agentic_weights


def _normalize_tickers(text: str) -> list[str]:
    parts = str(text or "").replace("\n", ",").replace(";", ",").replace("|", ",").split(",")
    return sorted({p.strip().upper() for p in parts if p.strip()})


def _normalize_holdings_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["ticker", "shares"])
    work = df.copy()
    work.columns = [str(c).strip().lower() for c in work.columns]
    if "ticker" not in work.columns or "shares" not in work.columns:
        raise ValueError("Holdings input must contain ticker and shares columns.")
    work["ticker"] = work["ticker"].astype(str).str.upper().str.strip()
    work["shares"] = pd.to_numeric(work["shares"], errors="coerce")
    work = work[(work["ticker"] != "") & work["shares"].notna() & (work["shares"] > 0)].copy()
    if work.empty:
        return pd.DataFrame(columns=["ticker", "shares"])
    return work.groupby("ticker", as_index=False).agg({"shares": "sum"})


def _run_fmp_screen(filters: dict[str, Any], fmp_api_key: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not fmp_api_key:
        raise ValueError("FMP API key is required for Screen companies mode.")
    screen_df, meta = fmp_company_screener(filters=filters, api_key=fmp_api_key, max_pages=filters.get("max_pages", 3))
    if screen_df is None or screen_df.empty:
        return pd.DataFrame(), meta or {}
    rename = {"symbol": "ticker"}
    screen_df = screen_df.rename(columns=rename)
    if "ticker" not in screen_df.columns and "symbol" in screen_df.columns:
        screen_df["ticker"] = screen_df["symbol"]
    return screen_df, meta or {}


def _fallback_dataset_from_prices(tickers: list[str], prices: pd.DataFrame, company_info: dict[str, dict[str, Any]], position_snapshot: pd.DataFrame) -> pd.DataFrame:
    rows = []
    returns = prices.pct_change()
    for ticker in tickers:
        if ticker not in prices.columns:
            continue
        series = prices[ticker].dropna()
        if series.empty:
            continue
        info = company_info.get(ticker, {}) if isinstance(company_info, dict) else {}
        row = {
            "ticker": ticker,
            "company_name": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector") or "Unclassified",
            "industry": info.get("industry") or "",
            "last_price": float(series.iloc[-1]),
            "ret_1m": float(series.iloc[-1] / series.iloc[-21] - 1) if len(series) > 21 else np.nan,
            "ret_3m": float(series.iloc[-1] / series.iloc[-63] - 1) if len(series) > 63 else np.nan,
            "ret_6m": float(series.iloc[-1] / series.iloc[-126] - 1) if len(series) > 126 else np.nan,
            "ret_12m": float(series.iloc[-1] / series.iloc[-252] - 1) if len(series) > 252 else np.nan,
            "price_vs_50dma": float(series.iloc[-1] / series.rolling(50).mean().iloc[-1] - 1) if len(series) >= 50 else np.nan,
            "price_vs_200dma": float(series.iloc[-1] / series.rolling(200).mean().iloc[-1] - 1) if len(series) >= 200 else np.nan,
            "ann_vol_3m": float(returns[ticker].tail(63).std() * np.sqrt(252)) if ticker in returns else np.nan,
            "beta": info.get("beta"),
        }
        if position_snapshot is not None and not position_snapshot.empty and ticker in position_snapshot["ticker"].astype(str).values:
            pos = position_snapshot[position_snapshot["ticker"].astype(str) == ticker].iloc[0]
            row["shares"] = pos.get("shares", 0.0)
            row["market_value"] = pos.get("market_value", 0.0)
            row["current_weight"] = pos.get("current_weight", 0.0)
        else:
            row["shares"] = 0.0
            row["market_value"] = 0.0
            row["current_weight"] = 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def _technical_signal_table(evidence_table: pd.DataFrame) -> pd.DataFrame:
    cols = ["ticker", "technical_view", "technical_score", "rsi_14", "price_vs_50dma", "price_vs_200dma", "ret_1m", "ret_3m", "ret_6m", "ret_12m", "relative_strength_3m"]
    return evidence_table[[c for c in cols if c in evidence_table.columns]].copy() if evidence_table is not None and not evidence_table.empty else pd.DataFrame()


def _decision_audit_table(recommendation_table: pd.DataFrame) -> pd.DataFrame:
    cols = ["ticker", "final_action", "committee_conviction", "current_weight", "target_weight", "target_weight_raw_ai", "composite_score", "fundamental_score", "valuation_score", "forward_score", "technical_score", "risk_score", "constraint_flags", "committee_reason"]
    return recommendation_table[[c for c in cols if c in recommendation_table.columns]].copy() if recommendation_table is not None and not recommendation_table.empty else pd.DataFrame()


def _monitoring_table(recommendation_table: pd.DataFrame) -> pd.DataFrame:
    cols = ["ticker", "final_action", "committee_conviction", "key_risks", "monitoring_triggers", "technical_view", "risk_view"]
    return recommendation_table[[c for c in cols if c in recommendation_table.columns]].copy() if recommendation_table is not None and not recommendation_table.empty else pd.DataFrame()


def _weight_explanations(recommendation_table: pd.DataFrame) -> pd.DataFrame:
    if recommendation_table is None or recommendation_table.empty:
        return pd.DataFrame()
    out = recommendation_table[[c for c in ["ticker", "current_weight", "target_weight", "delta_weight", "trade_value", "committee_reason", "constraint_flags"] if c in recommendation_table.columns]].copy()
    return out


def run_hybrid_portfolio_workflow(
    mode: str,
    benchmark: str,
    period: str,
    openai_api_key: str,
    model_name: str,
    fmp_api_key: str = "",
    max_weight: float = 0.18,
    max_sector_weight: float = 0.35,
    cash_buffer: float = 0.00,
    min_trade_weight_change: float = 0.0025,
    holdings_df: pd.DataFrame | None = None,
    tickers_text: str = "",
    screen_filters: dict[str, Any] | None = None,
    selected_screen_tickers: list[str] | None = None,
    risk_profile: str = "Balanced",
    **_: Any,
) -> dict[str, Any]:
    benchmark = (benchmark or "SPY").upper().strip()
    holdings = pd.DataFrame(columns=["ticker", "shares"])
    input_tickers: list[str] = []
    screen_df = pd.DataFrame()
    screen_meta: dict[str, Any] = {}

    if mode == "holdings":
        holdings = _normalize_holdings_df(holdings_df)
        input_tickers = holdings["ticker"].tolist() + _normalize_tickers(tickers_text)
        if not input_tickers:
            raise ValueError("Enter at least one holding or watchlist ticker.")
    elif mode == "manual":
        input_tickers = _normalize_tickers(tickers_text)
        if not input_tickers:
            raise ValueError("Enter at least one ticker.")
    elif mode == "screen":
        screen_df, screen_meta = _run_fmp_screen(screen_filters or {}, fmp_api_key)
        if screen_df.empty:
            raise ValueError("The FMP screener returned no names. Adjust filters and try again.")
        selected = selected_screen_tickers or []
        input_tickers = [str(x).upper().strip() for x in selected if str(x).strip()]
        if not input_tickers:
            analyze_top_n = int((screen_filters or {}).get("analyze_top_n", 12))
            input_tickers = screen_df["ticker"].astype(str).str.upper().head(analyze_top_n).tolist()
    else:
        raise ValueError("Unsupported Portfolio Manager mode.")

    input_tickers = sorted({t for t in input_tickers if t})
    fetch_tickers = sorted(set(input_tickers + [benchmark]))
    prices = fetch_price_history(fetch_tickers, period=period)
    if prices is None or prices.empty:
        raise ValueError("No price history was returned for the selected tickers.")
    if benchmark not in prices.columns:
        benchmark = prices.columns[0]
    analysis_tickers = [t for t in input_tickers if t in prices.columns and t != benchmark]
    if not analysis_tickers:
        raise ValueError("None of the selected tickers returned usable price history.")

    company_info = fetch_company_info(analysis_tickers + [benchmark])

    if not holdings.empty:
        held = [t for t in holdings["ticker"].tolist() if t in prices.columns]
        latest = prices[held].iloc[-1] if held else pd.Series(dtype=float)
        position_snapshot = compute_position_snapshot(holdings[holdings["ticker"].isin(held)], latest, company_info)
    else:
        position_snapshot = pd.DataFrame(columns=["ticker", "shares", "market_value", "current_weight", "sector", "industry", "company_name"])

    try:
        dataset = build_multi_agent_dataset(
            tickers=analysis_tickers,
            prices=prices[[c for c in analysis_tickers + [benchmark] if c in prices.columns]],
            company_info=company_info,
            benchmark_col=benchmark,
            news_summary=pd.DataFrame(),
            position_snapshot=position_snapshot,
            fmp_api_key=fmp_api_key,
            comparison_mode=False,
        )
        dataset = dataset[dataset["ticker"].astype(str).str.upper().isin(analysis_tickers)].copy()
    except Exception:
        dataset = _fallback_dataset_from_prices(analysis_tickers, prices, company_info, position_snapshot)

    if dataset is None or dataset.empty:
        dataset = _fallback_dataset_from_prices(analysis_tickers, prices, company_info, position_snapshot)
    if dataset.empty:
        raise ValueError("The Portfolio Manager could not build an evidence dataset.")

    evidence_table = build_evidence_table(dataset, max_weight=max_weight, max_sector_weight=max_sector_weight)
    portfolio_value = float(position_snapshot["market_value"].sum()) if position_snapshot is not None and not position_snapshot.empty else 0.0
    regime_info = compute_market_regime(prices[[benchmark]]) if benchmark in prices.columns else compute_market_regime(prices)
    portfolio_summary = {
        "mode": mode,
        "portfolio_value": portfolio_value,
        "benchmark": benchmark,
        "risk_profile": risk_profile,
        "regime": regime_info.get("regime"),
        "cash_buffer": cash_buffer,
        "max_position_weight": max_weight,
        "max_sector_weight": max_sector_weight,
        "holding_count": int(len(position_snapshot)) if position_snapshot is not None else 0,
        "analysis_count": int(len(evidence_table)),
        "news_removed_from_pm": True,
        "peer_ranking_removed_from_pm": True,
        "workflow": "Hybrid Option C: deterministic evidence + AI committee decisions + constraint validation",
    }

    committee_result = run_agentic_committee(
        evidence_table=evidence_table,
        portfolio_summary=portfolio_summary,
        openai_api_key=openai_api_key,
        model_name=model_name,
        max_weight=max_weight,
        max_sector_weight=max_sector_weight,
        cash_buffer=cash_buffer,
        risk_profile=risk_profile,
    )
    committee_table = committee_result_to_table(evidence_table, committee_result)
    recommendation_table, rebalance_table, sector_table, validation_diag = validate_agentic_weights(
        recommendation_table=committee_table,
        portfolio_value=portfolio_value,
        max_position_weight=max_weight,
        max_sector_weight=max_sector_weight,
        cash_buffer=cash_buffer,
        min_trade_weight_change=min_trade_weight_change,
    )

    action_buckets = split_recommendation_buckets(recommendation_table.rename(columns={}).assign(final_action=recommendation_table.get("final_action", "Hold")))
    summary = committee_result.get("portfolio_committee_summary") or "Hybrid portfolio workflow completed."
    if validation_diag.get("validator_adjusted_names", 0):
        summary += f" Validator adjusted {validation_diag['validator_adjusted_names']} target weight(s) to satisfy position/sector constraints."

    return {
        "mode": mode,
        "holdings": holdings,
        "screen_df": screen_df,
        "screen_meta": screen_meta,
        "benchmark": benchmark,
        "prices": prices,
        "company_info": company_info,
        "position_snapshot": position_snapshot,
        "dataset": dataset,
        "evidence_table": evidence_table,
        "recommendation_table": recommendation_table,
        "committee_table": committee_table,
        "decision_audit_table": _decision_audit_table(recommendation_table),
        "technical_signal_table": _technical_signal_table(evidence_table),
        "rebalance_table": rebalance_table,
        "sector_allocation_table": sector_table,
        "target_weight_explanations": _weight_explanations(recommendation_table),
        "monitoring_table": _monitoring_table(recommendation_table),
        "portfolio_committee_summary": summary,
        "run_diagnostics": {
            "engine_version": "hybrid_agentic_option_c_v1",
            "input_tickers": input_tickers,
            "analysis_tickers": analysis_tickers,
            "price_columns_returned": list(prices.columns),
            "missing_price_tickers": sorted(set(input_tickers) - set(analysis_tickers)),
            "fmp_key_loaded": bool(fmp_api_key),
            "openai_key_loaded": bool(openai_api_key),
            "agentic_ai_status": committee_result.get("status"),
            "agentic_ai_error": committee_result.get("error"),
            "openai_calls_during_run": committee_result.get("openai_calls", 0),
            "news_removed_from_pm": True,
            "peer_ranking_removed_from_pm": True,
            **validation_diag,
        },
        "regime_info": regime_info,
        "portfolio_summary": portfolio_summary,
        "agentic_ai_committee_result": committee_result,
        "pm_note": summary,
        "bucket_add": action_buckets.get("add", pd.DataFrame()),
        "bucket_hold": action_buckets.get("hold", pd.DataFrame()),
        "bucket_trim": action_buckets.get("trim", pd.DataFrame()),
        "bucket_sell": action_buckets.get("sell", pd.DataFrame()),
        "bucket_watchlist": action_buckets.get("watchlist", pd.DataFrame()),
        "bucket_avoid": action_buckets.get("avoid", pd.DataFrame()),
    }

# Compatibility alias so existing imports can use the new hybrid workflow immediately.
run_portfolio_decision_workflow = run_hybrid_portfolio_workflow
