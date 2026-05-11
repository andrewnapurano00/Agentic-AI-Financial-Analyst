from __future__ import annotations

import pandas as pd

from langgraphagenticai.portfolio_manager.llm_allocator import build_ticker_decision_explainer
from langgraphagenticai.portfolio_manager.schemas import FinalRecommendation, TickerAnalysisBundle
from langgraphagenticai.portfolio_manager.scoring import (
    action_strength,
    apply_overrides,
    blend_with_peer_score_detailed,
    clip_score,
    composite_score,
    confidence_from_scores,
    data_quality_from_row,
    dominant_decision_reason,
    map_score_to_action,
    one_notch_downgrade,
    one_notch_upgrade,
)
from langgraphagenticai.portfolio_manager.sector_profiles import get_sector_profile


def _mode_adjusted_weights(bundle: TickerAnalysisBundle) -> dict[str, float]:
    weights = dict(get_sector_profile(bundle.sector).get("weights", {}))
    portfolio_mode = bundle.current_weight > 0 or bundle.market_value > 0 or bundle.data.get("portfolio_mode", False)
    comparison_mode = bool(bundle.data.get("comparison_mode", False))
    if portfolio_mode:
        weights["fundamental"] = weights.get("fundamental", 0.32) + 0.03
        weights["risk_fit"] = weights.get("risk_fit", 0.10) + 0.05
        weights["technical"] = max(0.10, weights.get("technical", 0.17) - 0.03)
    elif comparison_mode:
        weights["valuation"] = weights.get("valuation", 0.20) + 0.03
        weights["fundamental"] = weights.get("fundamental", 0.32) + 0.02
    total = sum(max(0.0, float(v)) for v in weights.values())
    if total > 0:
        weights = {k: max(0.0, float(v)) / total for k, v in weights.items()}
    return weights


def _portfolio_action(action_tilt: str, current_weight: float) -> str:
    action_tilt = str(action_tilt or "Hold")
    owned = (current_weight or 0.0) > 0
    if owned:
        if action_tilt in {"Strong Buy", "Buy", "Add", "Start / Rotate In"}:
            return "Add"
        if action_tilt in {"Trim", "Sell", "Exit", "Avoid"}:
            return "Trim" if action_tilt == "Trim" else "Exit"
        return "Hold"
    if action_tilt in {"Strong Buy", "Buy", "Add"}:
        return "Start / Rotate In"
    if action_tilt in {"Sell", "Trim", "Avoid", "Exit"}:
        return "Avoid"
    return "Watchlist"


def _guardrails(bundle: TickerAnalysisBundle, base_action: str, max_weight: float, data_quality_score: float) -> tuple[str, list[str]]:
    notes: list[str] = []
    action = base_action
    if bundle.screening and not bundle.screening.passes_screen:
        notes.append("Failed the investable-universe screen, so the recommendation is capped at Avoid / Exit.")
        action = "Exit" if bundle.current_weight > 0 else "Avoid"
    if (bundle.current_weight or 0.0) >= max_weight and action in {"Add", "Buy", "Start / Rotate In"}:
        notes.append("Position is already at or above the portfolio max-weight guardrail.")
        action = "Hold"
    if bundle.risk and bundle.risk.risk_level in {"elevated", "high"} and action in {"Add", "Start / Rotate In", "Buy"}:
        notes.append("Risk agent flagged elevated volatility / drawdown risk, so sizing is constrained.")
        action = "Hold" if bundle.current_weight > 0 else "Watchlist"
    if data_quality_score < 0.45 and action in {"Add", "Start / Rotate In"}:
        notes.append("Data coverage is too thin for fresh capital; move to Watchlist until the signal is better supported.")
        action = "Watchlist" if bundle.current_weight <= 0 else "Hold"
    return action, notes


def _peer_reliability(bundle: TickerAnalysisBundle) -> float:
    explicit = bundle.data.get("peer_reliability")
    if explicit is not None and not pd.isna(explicit):
        try:
            return float(explicit)
        except Exception:
            pass

    peer_count = bundle.data.get("peer_count")
    peer_group_type = str(bundle.data.get("peer_group_type") or "").lower()
    metric_count = bundle.data.get("peer_metric_count")
    if peer_count is None or pd.isna(peer_count):
        return 0.0
    peer_count = float(peer_count)
    metric_count = 0.0 if metric_count is None or pd.isna(metric_count) else float(metric_count)

    if peer_count >= 12:
        count_score = 1.0
    elif peer_count >= 8:
        count_score = 0.84
    elif peer_count >= 5:
        count_score = 0.68
    elif peer_count >= 3:
        count_score = 0.50
    else:
        count_score = 0.25

    if "industry" in peer_group_type:
        group_score = 0.86
    elif "sector" in peer_group_type:
        group_score = 0.64
    else:
        group_score = 0.38

    metric_score = min(1.0, max(0.0, metric_count / 4.0))
    return float(max(0.15, min(1.0, 0.55 * group_score + 0.30 * count_score + 0.15 * metric_score)))


def _normalize_debate_action(action: str, owned: bool) -> str:
    text = str(action or "Hold")
    if text in {"Add", "Start / Rotate In"}:
        return "Buy"
    if text == "Watchlist":
        return "Hold"
    if text in {"Avoid", "Exit"}:
        return "Sell"
    if text == "Trim" and not owned:
        return "Hold"
    return text


def _merge_numeric_and_debate_actions(
    thesis_action: str,
    debate_action: str,
    debate_state: str,
    owned: bool,
    support_count: int,
    oppose_count: int,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    merged = thesis_action
    debate_base = _normalize_debate_action(debate_action, owned=owned)
    debate_state = str(debate_state or "mixed").lower()

    # If debate strongly disagrees with numeric output, move one notch toward the debate rather than fully overriding.
    if action_strength(debate_base) >= action_strength(merged) + 2 and support_count >= oppose_count + 2:
        merged = one_notch_upgrade(merged)
        notes.append("Cross-agent debate was materially more bullish, so the PM layer upgrades the call by one notch.")
    elif action_strength(debate_base) <= action_strength(merged) - 2 and oppose_count >= support_count:
        merged = one_notch_downgrade(merged)
        notes.append("Cross-agent debate was materially more cautious, so the PM layer downgrades the call by one notch.")

    if debate_state == "aligned bullish" and support_count >= max(4, oppose_count + 2):
        if action_strength(merged) <= action_strength("Buy"):
            upgraded = one_notch_upgrade(merged)
            if upgraded != merged:
                notes.append("Cross-agent alignment upgrades the recommendation by one notch.")
                merged = upgraded
    elif debate_state in {"constructive but debated"}:
        if merged == "Strong Buy":
            notes.append("Debate is constructive but not unanimous, so the strongest call is tempered to Buy.")
            merged = "Buy"
    elif debate_state in {"cautious / mixed"}:
        while action_strength(merged) > action_strength("Hold"):
            merged = one_notch_downgrade(merged)
        notes.append("Mixed agent debate caps the name at Hold until more evidence lines up.")
    elif debate_state in {"defensive / bearish"}:
        target = "Trim" if owned else "Sell"
        if action_strength(merged) > action_strength(target):
            notes.append("Cross-agent downside concerns push the call down to a defensive stance.")
            merged = target

    return merged, notes


def _decision_confidence_label(score_conf: float, debate_conf: float, data_quality_score: float, consensus_label: str) -> str:
    raw = 0.50 * score_conf + 0.25 * debate_conf + 0.25 * data_quality_score
    consensus_label = str(consensus_label or "").lower()
    if consensus_label in {"aligned bullish", "aligned", "strong"}:
        raw += 0.06
    elif consensus_label in {"cautious / mixed", "defensive / bearish", "conflicted"}:
        raw -= 0.08
    raw = float(max(0.0, min(1.0, raw)))
    if raw >= 0.78:
        return "high"
    if raw >= 0.56:
        return "medium"
    return "low"


def _sizing_hint(final_action: str, composite: float, risk_fit: float, current_weight: float, max_weight: float, debate_sizing: str = "normal") -> str:
    debate_sizing = str(debate_sizing or "normal").lower()
    if final_action in {"Avoid", "Exit"}:
        return "zero"
    if final_action in {"Trim"}:
        return "small / defensive"
    if final_action in {"Watchlist"}:
        return "watchlist"
    if current_weight >= max_weight * 0.90:
        return "small / defensive"
    if risk_fit < 4.0:
        return "small / defensive"
    if final_action in {"Add", "Start / Rotate In"} and composite >= 8.1 and risk_fit >= 5.5:
        return "large" if debate_sizing not in {"starter", "small"} else "medium"
    if final_action in {"Add", "Start / Rotate In"} and composite >= 6.7:
        return "medium" if debate_sizing not in {"starter"} else "normal"
    if final_action == "Hold":
        return "normal"
    return debate_sizing if debate_sizing in {"starter", "small", "normal", "medium", "large", "overweight"} else "normal"


def _plain_pm_summary(action: str, reason: str, data_quality_label: str, peer_note: str) -> str:
    parts = [f"{action} is driven by {reason}."]
    if peer_note:
        parts.append(peer_note)
    parts.append(f"Data quality is {data_quality_label}.")
    return " ".join(parts)


def run_lead_pm_agent(bundle: TickerAnalysisBundle, openai_api_key: str, model_name: str, max_weight: float = 0.18) -> FinalRecommendation:
    weights = _mode_adjusted_weights(bundle)
    sub_scores = {
        "screening": getattr(bundle.screening, "score", 5.0),
        "fundamental": getattr(bundle.fundamentals, "score", 5.0),
        "valuation": getattr(bundle.valuation, "score", 5.0),
        "technical": getattr(bundle.technicals, "score", 5.0),
        "catalyst": getattr(bundle.catalysts, "score", 5.0),
        "earnings": getattr(bundle.earnings, "score", 5.0),
        "risk_fit": (getattr(bundle.risk, "score", 5.0) + getattr(bundle.portfolio_fit, "score", 5.0)) / 2.0,
    }

    data_quality_score, data_quality_label, missing_fields = data_quality_from_row(bundle.data)

    absolute_score = composite_score({k: v for k, v in sub_scores.items() if k != "screening"}, weights)
    screening_score = sub_scores["screening"]
    absolute_score = clip_score(0.92 * absolute_score + 0.08 * screening_score)

    comparison_mode = bool(bundle.data.get("comparison_mode", False))
    peer_score_raw = bundle.data.get("peer_total_score")
    peer_score = None if peer_score_raw is None or pd.isna(peer_score_raw) else clip_score(float(peer_score_raw))
    peer_reliability = _peer_reliability(bundle)
    composite, peer_blend_note, peer_weight = blend_with_peer_score_detailed(
        absolute_score=absolute_score,
        peer_score=peer_score,
        peer_reliability=peer_reliability,
        max_peer_weight=0.26 if comparison_mode else 0.12,
    )

    thesis_action = map_score_to_action(composite)
    screening_pass = bool(getattr(bundle.screening, "passes_screen", True))
    thesis_action, override_notes = apply_overrides(
        thesis_action,
        sub_scores=sub_scores,
        current_weight=bundle.current_weight,
        max_weight=max_weight,
        screening_pass=screening_pass,
        comparison_mode=comparison_mode,
        peer_score=peer_score,
        data_quality_score=data_quality_score,
    )

    debate = bundle.debate
    owned = (bundle.current_weight or 0.0) > 0
    if debate is not None:
        thesis_action, debate_notes = _merge_numeric_and_debate_actions(
            thesis_action=thesis_action,
            debate_action=debate.action_tilt,
            debate_state=debate.consensus_state,
            owned=owned,
            support_count=debate.support_count,
            oppose_count=debate.oppose_count,
        )
    else:
        debate_notes = []

    final_action = _portfolio_action(thesis_action, bundle.current_weight)
    final_action, guardrail_notes = _guardrails(bundle, final_action, max_weight=max_weight, data_quality_score=data_quality_score)

    why, risks = [], []
    for result in [
        bundle.screening,
        bundle.fundamentals,
        bundle.valuation,
        bundle.technicals,
        bundle.catalysts,
        bundle.earnings,
        bundle.risk,
        bundle.portfolio_fit,
    ]:
        if result is None:
            continue
        why.extend([x for x in result.summary if x])
        risks.extend([x for x in result.risks if x])

    peer_rank = bundle.data.get("peer_rank_overall") if comparison_mode else None
    peer_pct = bundle.data.get("peer_percentile_overall") if comparison_mode else None

    key_supports = (debate.support_reasons if debate else []) or why[:4]
    key_conflicts = (debate.conflict_reasons if debate else []) or risks[:4]
    missing = (debate.open_questions if debate else [])[:4]
    missing = list(dict.fromkeys(missing + [f"Missing {x}" for x in missing_fields[:4]]))

    decision_notes = [x for x in [peer_blend_note] if x] + override_notes + debate_notes + guardrail_notes
    decision_reason = dominant_decision_reason(sub_scores, peer_score=peer_score)
    monitor_triggers = [
        "Reassess after the next earnings update or major guidance change.",
        "Watch relative strength and risk metrics for confirmation.",
    ]
    if peer_weight > 0 and peer_reliability < 0.65:
        monitor_triggers.append("Peer comparison is based on a lighter comparison set, so refresh the ranking as coverage expands.")
    if bundle.catalysts and bundle.catalysts.metrics.get("usable_news_count", 0) < 2:
        monitor_triggers.append("Refresh the news overlay as more full-text coverage becomes available.")
    if data_quality_label != "high":
        monitor_triggers.append("Improve confidence by refreshing fundamentals, analyst estimates, and full-text news coverage.")

    score_conf = confidence_from_scores(sub_scores, data_quality_score=data_quality_score)
    debate_conf = float(debate.confidence) / 10.0 if debate else 0.62
    decision_confidence = _decision_confidence_label(
        score_conf=score_conf,
        debate_conf=debate_conf,
        data_quality_score=data_quality_score,
        consensus_label=(debate.consensus_state if debate else "mixed"),
    )
    blended_conf = clip_score((0.60 * score_conf + 0.25 * debate_conf + 0.15 * data_quality_score) * 10.0)
    suggested_sizing = _sizing_hint(
        final_action=final_action,
        composite=composite,
        risk_fit=sub_scores["risk_fit"],
        current_weight=bundle.current_weight,
        max_weight=max_weight,
        debate_sizing=(debate.sizing_hint if debate else "normal"),
    )

    pm_decision_summary = _plain_pm_summary(final_action, decision_reason, data_quality_label, peer_blend_note)

    explanation = build_ticker_decision_explainer(
        ticker=bundle.ticker,
        sector=bundle.sector,
        industry=bundle.industry,
        current_weight=bundle.current_weight,
        final_action=final_action,
        action_bias=thesis_action,
        why=key_supports,
        risks=key_conflicts + decision_notes,
        next_steps=monitor_triggers,
        composite_score=composite,
        sub_scores={
            **sub_scores,
            "data_quality_score": round(data_quality_score * 10, 2),
            "peer_score": peer_score,
        },
        openai_api_key=openai_api_key,
        model_name=model_name,
    )

    raw_metrics = dict(bundle.data)
    raw_metrics.update(
        {
            "data_quality_score": data_quality_score,
            "data_quality_label": data_quality_label,
            "decision_reason": decision_reason,
            "peer_blend_weight": peer_weight,
            "peer_blend_note": peer_blend_note,
        }
    )

    return FinalRecommendation(
        ticker=bundle.ticker,
        sector=bundle.sector,
        industry=bundle.industry,
        current_weight=bundle.current_weight,
        composite_score=composite,
        absolute_score=absolute_score,
        peer_score=peer_score,
        peer_rank=peer_rank,
        peer_percentile=peer_pct,
        confidence=blended_conf,
        final_action=final_action,
        action_bias=thesis_action,
        suggested_sizing=suggested_sizing,
        consensus_state=(debate.consensus_state if debate else "mixed"),
        decision_confidence=decision_confidence,
        data_quality_score=data_quality_score,
        data_quality_label=data_quality_label,
        decision_reason=decision_reason,
        pm_decision_summary=pm_decision_summary,
        key_supports=key_supports[:5],
        key_conflicts=key_conflicts[:5],
        missing_evidence=missing[:5],
        monitor_triggers=monitor_triggers[:5],
        triggered_guardrails=decision_notes[:6],
        why=why[:6],
        risks=(risks + decision_notes)[:6],
        next_steps=monitor_triggers[:5],
        explanation=explanation,
        sub_scores=sub_scores,
        raw_metrics=raw_metrics,
    )

