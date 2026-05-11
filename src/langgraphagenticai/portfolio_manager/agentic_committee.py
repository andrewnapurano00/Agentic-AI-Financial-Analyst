from __future__ import annotations

from typing import Any
import json
import math
import re

import numpy as np
import pandas as pd

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from langgraphagenticai.portfolio_manager.evidence_builder import compact_evidence_records, safe_float, clean_text

ACTION_LADDER = ["Sell", "Trim", "Hold / Watch", "Hold", "Add", "Strong Buy"]


def _extract_json(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw[start:end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def normalize_action(action: Any, fallback: str = "Hold") -> str:
    value = str(action or fallback).strip()
    aliases = {
        "buy": "Add", "strong add": "Strong Buy", "strong buy": "Strong Buy", "start": "Add",
        "start / rotate in": "Add", "rotate in": "Add", "watch": "Hold / Watch", "watchlist": "Hold / Watch",
        "avoid": "Hold / Watch", "exit": "Sell", "reduce": "Trim", "sell / exit": "Sell",
    }
    lowered = value.lower()
    if lowered in aliases:
        return aliases[lowered]
    for allowed in ACTION_LADDER:
        if lowered == allowed.lower():
            return allowed
    return fallback if fallback in ACTION_LADDER else "Hold"


def _fallback_target_weight(row: pd.Series, max_weight: float, cash_buffer: float, portfolio_mode: bool) -> float:
    current = safe_float(row.get("current_weight"), 0.0) or 0.0
    composite = safe_float(row.get("composite_score"), 5.0) or 5.0
    technical = safe_float(row.get("technical_score"), 5.0) or 5.0
    risk = safe_float(row.get("risk_score"), 5.0) or 5.0
    action = normalize_action(row.get("evidence_action"), "Hold")
    conviction_adj = ((composite - 5.0) * 0.006) + ((technical - 5.0) * 0.003) + ((risk - 5.0) * 0.002)
    if portfolio_mode:
        target = current + conviction_adj
        if action == "Strong Buy": target += 0.025
        elif action == "Add": target += 0.015
        elif action == "Trim": target -= 0.025
        elif action == "Sell": target = 0.0
        elif action == "Hold / Watch": target -= 0.005
    else:
        # In ticker-analysis mode, let high-quality ideas receive more model portfolio weight.
        target = max(0.0, composite - 3.5) ** 1.35
    if current > max_weight and action not in {"Strong Buy", "Add"}:
        target = min(target, max_weight)
    return float(np.clip(target, 0.0, max_weight))


def build_fallback_committee_decision(
    evidence_table: pd.DataFrame,
    portfolio_summary: dict[str, Any],
    max_weight: float,
    cash_buffer: float,
) -> dict[str, Any]:
    portfolio_mode = bool(portfolio_summary.get("portfolio_value", 0) or evidence_table.get("market_value", pd.Series(dtype=float)).sum() > 0)
    recs = []
    for _, row in evidence_table.iterrows():
        action = normalize_action(row.get("evidence_action"), "Hold")
        current = safe_float(row.get("current_weight"), 0.0) or 0.0
        target = _fallback_target_weight(row, max_weight=max_weight, cash_buffer=cash_buffer, portfolio_mode=portfolio_mode)
        if current > max_weight * 1.05 and action in {"Hold", "Add", "Strong Buy"}:
            action = "Trim" if target < current else "Hold"
        recs.append({
            "ticker": clean_text(row.get("ticker"), "").upper(),
            "final_action": action,
            "target_weight": round(target, 5),
            "conviction": clean_text(row.get("evidence_conviction"), "Medium"),
            "committee_reason": clean_text(row.get("evidence_reason"), "Evidence-based fallback decision."),
            "key_risks": clean_text(row.get("key_conflicts"), "Data quality and market risk."),
            "monitoring_triggers": "Watch trend vs 50/200DMA, estimate revisions, valuation compression, and position concentration.",
            "agent_views": {
                "fundamental_agent": clean_text(row.get("fundamental_view"), "mixed"),
                "valuation_agent": clean_text(row.get("valuation_view"), "mixed"),
                "forward_estimates_agent": clean_text(row.get("forward_view"), "mixed"),
                "technical_momentum_agent": clean_text(row.get("technical_view"), "mixed"),
                "risk_agent": clean_text(row.get("risk_view"), "moderate"),
                "portfolio_construction_agent": "constraint-aware fallback sizing",
                "lead_pm_agent": action,
            },
        })
    return {
        "status": "fallback_no_openai",
        "portfolio_committee_summary": (
            "OpenAI committee was not available, so the app used the deterministic evidence layer as a conservative fallback. "
            "Final sizing still runs through the constraint validator, but these are not true LLM committee decisions."
        ),
        "top_adds": [r["ticker"] for r in recs if r["final_action"] in {"Add", "Strong Buy"}][:5],
        "top_trims": [r["ticker"] for r in recs if r["final_action"] in {"Trim", "Sell"}][:5],
        "key_risks": ["Fallback mode: no OpenAI key/model response was available.", "Validate high-conviction actions before trading."],
        "recommendations": recs,
        "openai_calls": 0,
    }


def run_agentic_committee(
    evidence_table: pd.DataFrame,
    portfolio_summary: dict[str, Any],
    openai_api_key: str,
    model_name: str,
    max_weight: float,
    max_sector_weight: float,
    cash_buffer: float,
    risk_profile: str = "Balanced",
) -> dict[str, Any]:
    if evidence_table is None or evidence_table.empty:
        return {"status": "empty", "recommendations": [], "portfolio_committee_summary": "No evidence available."}

    if not openai_api_key or OpenAI is None:
        return build_fallback_committee_decision(evidence_table, portfolio_summary, max_weight, cash_buffer)

    evidence_records = compact_evidence_records(evidence_table, max_rows=35)
    payload = {
        "portfolio_summary": portfolio_summary,
        "risk_profile": risk_profile,
        "constraints": {
            "max_position_weight": max_weight,
            "max_sector_weight": max_sector_weight,
            "cash_buffer": cash_buffer,
            "weights_must_sum_to": 1.0 - cash_buffer,
        },
        "design_rules": [
            "You are the decision-maker. The deterministic scores are evidence only, not a formula for weights.",
            "Do not equal-weight unless the evidence genuinely supports equal sizing.",
            "Do not simply set every strong name to the max weight.",
            "Use sector exposure, current weights, technical trend, momentum, valuation, forward estimates, risk, and portfolio role.",
            "Do not use peer ranking. Peer comparison belongs in the Equity Research tab, not this Portfolio Manager.",
            "For ETFs/funds, do not penalize missing fundamentals; focus on trend, risk, diversification, overlap, and role.",
            "Give explicit target weights for every ticker. The validator may later cap/renormalize only for math constraints.",
            "Return JSON only. No markdown.",
        ],
        "evidence": evidence_records,
        "required_schema": {
            "portfolio_committee_summary": "3-5 sentences explaining what the committee would do and why.",
            "top_adds": ["ticker"],
            "top_trims": ["ticker"],
            "key_risks": ["risk"],
            "recommendations": [
                {
                    "ticker": "symbol",
                    "final_action": "Sell | Trim | Hold / Watch | Hold | Add | Strong Buy",
                    "target_weight": "decimal weight, e.g. 0.12 for 12%",
                    "conviction": "Low | Medium | High",
                    "committee_reason": "concise PM-style reason",
                    "key_risks": "main risks",
                    "monitoring_triggers": "what to watch",
                    "agent_views": {
                        "fundamental_agent": "view",
                        "valuation_agent": "view",
                        "forward_estimates_agent": "view",
                        "technical_momentum_agent": "view",
                        "risk_agent": "view",
                        "portfolio_construction_agent": "view",
                        "lead_pm_agent": "final synthesis"
                    }
                }
            ]
        },
    }
    system = (
        "You are an institutional multi-agent AI portfolio committee. "
        "Your job is to make target-weight and rebalance decisions from supplied evidence. "
        "You are not a generic chatbot. Return valid JSON only."
    )
    try:
        client = OpenAI(api_key=openai_api_key)
        response = client.responses.create(
            model=model_name,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, default=str)},
            ],
        )
        raw = getattr(response, "output_text", "") or ""
        parsed = _extract_json(raw)
        if not parsed or not isinstance(parsed.get("recommendations"), list):
            fallback = build_fallback_committee_decision(evidence_table, portfolio_summary, max_weight, cash_buffer)
            fallback["status"] = "fallback_parse_failed"
            fallback["error"] = "OpenAI returned a response, but valid recommendation JSON could not be parsed."
            fallback["raw_response"] = raw
            return fallback
        parsed["status"] = "ai_committee_applied"
        parsed["raw_response"] = raw
        parsed["openai_calls"] = 1
        return parsed
    except Exception as exc:
        fallback = build_fallback_committee_decision(evidence_table, portfolio_summary, max_weight, cash_buffer)
        fallback["status"] = "fallback_openai_error"
        fallback["error"] = str(exc)
        return fallback


def committee_result_to_table(evidence_table: pd.DataFrame, committee_result: dict[str, Any]) -> pd.DataFrame:
    base = evidence_table.copy() if evidence_table is not None else pd.DataFrame()
    if base.empty:
        return base
    recommendations = committee_result.get("recommendations", []) if committee_result else []
    by_ticker: dict[str, dict[str, Any]] = {}
    for item in recommendations:
        if isinstance(item, dict):
            ticker = clean_text(item.get("ticker"), "").upper()
            if ticker:
                by_ticker[ticker] = item

    rows = []
    for _, row in base.iterrows():
        ticker = clean_text(row.get("ticker"), "").upper()
        item = by_ticker.get(ticker, {})
        action = normalize_action(item.get("final_action"), normalize_action(row.get("evidence_action"), "Hold"))
        target = safe_float(item.get("target_weight"), np.nan)
        if pd.isna(target):
            target = safe_float(row.get("current_weight"), 0.0) or 0.0
        agent_views = item.get("agent_views", {}) if isinstance(item.get("agent_views"), dict) else {}
        out = row.to_dict()
        out.update({
            "final_action": action,
            "target_weight_proposed": float(np.clip(target, 0.0, 1.0)),
            "committee_conviction": clean_text(item.get("conviction"), clean_text(row.get("evidence_conviction"), "Medium")),
            "committee_reason": clean_text(item.get("committee_reason"), clean_text(row.get("evidence_reason"), "No committee reason returned.")),
            "key_risks": clean_text(item.get("key_risks"), clean_text(row.get("key_conflicts"), "Market risk.")),
            "monitoring_triggers": clean_text(item.get("monitoring_triggers"), "Watch momentum, valuation, concentration, and estimate revisions."),
            "fundamental_agent_view": clean_text(agent_views.get("fundamental_agent"), clean_text(row.get("fundamental_view"), "mixed")),
            "valuation_agent_view": clean_text(agent_views.get("valuation_agent"), clean_text(row.get("valuation_view"), "mixed")),
            "forward_agent_view": clean_text(agent_views.get("forward_estimates_agent"), clean_text(row.get("forward_view"), "mixed")),
            "technical_agent_view": clean_text(agent_views.get("technical_momentum_agent"), clean_text(row.get("technical_view"), "mixed")),
            "risk_agent_view": clean_text(agent_views.get("risk_agent"), clean_text(row.get("risk_view"), "moderate")),
            "portfolio_construction_agent_view": clean_text(agent_views.get("portfolio_construction_agent"), "constraint-aware sizing"),
            "lead_pm_view": clean_text(agent_views.get("lead_pm_agent"), action),
        })
        rows.append(out)
    return pd.DataFrame(rows)
