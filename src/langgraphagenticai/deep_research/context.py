"""Explicit bridges to app data; never serialize the entire Streamlit session."""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .models import Evidence, json_safe


CONTEXT_FIELDS = {
    "equity_report_payload": ("Equity report", ["combined_scorecard", "technical_scorecard", "ranking_table", "valuation_explanations", "technical_explanations"]),
    "pm_hybrid_bundle_v1": ("Portfolio manager", ["holdings", "position_snapshot", "dataset", "evidence_table", "recommendation_table", "sector_allocation_table", "portfolio_summary"]),
    "stock_screener_payload": ("Stock screener", ["results"]),
    "portfolio_optimizer_payload": ("Portfolio optimizer", ["risk_table", "weights", "regime"]),
}


def available_context(state: Mapping) -> list[str]:
    return [label for key, (label, _) in CONTEXT_FIELDS.items() if isinstance(state.get(key), dict)]


def collect_app_context(state: Mapping, symbols: list[str]) -> list[Evidence]:
    evidence = []
    for key, (label, fields) in CONTEXT_FIELDS.items():
        payload = state.get(key)
        if not isinstance(payload, dict):
            continue
        data = {}
        for name in fields:
            value = payload.get(name)
            if isinstance(value, pd.DataFrame):
                frame = value.copy()
                ticker_col = next((c for c in frame if str(c).lower() in {"symbol", "ticker", "asset"}), None)
                if ticker_col:
                    frame = frame[frame[ticker_col].astype(str).str.upper().isin(symbols)]
                elif str(frame.index.name).lower() in {"ticker", "symbol", "asset"}:
                    frame = frame.loc[frame.index.astype(str).str.upper().isin(symbols)].reset_index()
                if not frame.empty:
                    data[name] = json_safe(frame.head(40).to_dict("records"))
            elif isinstance(value, (dict, list, str)):
                data[name] = json_safe(value)
        if data:
            evidence.append(Evidence(
                id="", symbol=",".join(symbols), category="app_context", title=label,
                provider="Current app session", data=data,
                retrieved_at=payload.get("generated_at") or "Unknown (existing session result)",
                note="Saved app context, not refreshed by research. Portfolio recommendations are prior opinions, not verified facts. Portfolio-level totals may include other holdings.",
            ))
    return evidence
