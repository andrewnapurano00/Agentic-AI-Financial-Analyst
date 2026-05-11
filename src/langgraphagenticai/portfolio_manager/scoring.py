from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


_ACTION_TO_STRENGTH = {
    "avoid": 0,
    "exit": 0,
    "sell": 0,
    "trim": 1,
    "watchlist": 2,
    "hold": 2,
    "start / rotate in": 3,
    "add": 3,
    "buy": 3,
    "strong buy": 4,
}

_STRENGTH_TO_ACTION = {
    0: "Sell",
    1: "Trim",
    2: "Hold",
    3: "Buy",
    4: "Strong Buy",
}

CORE_DATA_FIELDS = [
    "last_price",
    "market_cap",
    "ret_3m",
    "price_vs_200dma",
    "rsi_14",
    "ann_vol_3m",
    "max_drawdown_1y",
    "revenue_cagr_3y",
    "operating_margin",
    "profit_margin",
    "return_on_equity",
    "debt_to_equity",
    "forward_pe",
    "forward_ps",
    "analyst_upside_pct",
    "fcf_yield",
]


def clip_score(value: float | None, low: float = 0.0, high: float = 10.0) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 5.0
    return float(np.clip(value, low, high))


def pct_to_score(value: float | None, low: float, high: float, invert: bool = False) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 5.0
    if high <= low:
        return 5.0
    scaled = (float(value) - low) / (high - low)
    scaled = max(0.0, min(1.0, scaled))
    score = scaled * 10.0
    if invert:
        score = 10.0 - score
    return clip_score(score)


def weighted_average(pairs: list[tuple[float | None, float]]) -> float:
    total = 0.0
    weight_sum = 0.0
    for value, weight in pairs:
        if weight <= 0:
            continue
        if value is None or pd.isna(value):
            continue
        total += clip_score(value) * weight
        weight_sum += weight
    if weight_sum <= 0:
        return 5.0
    return clip_score(total / weight_sum)


def composite_score(sub_scores: dict[str, float], weights: dict[str, float]) -> float:
    return weighted_average([(sub_scores.get(key, 5.0), weight) for key, weight in weights.items()])


def normalize_action(action: str | None) -> str:
    text = str(action or "Hold").strip()
    if not text:
        return "Hold"
    lowered = text.lower()
    if lowered == "start / rotate in":
        return "Start / Rotate In"
    return text.title()


def action_strength(action: str | None) -> int:
    return _ACTION_TO_STRENGTH.get(str(action or "Hold").strip().lower(), 2)


def action_from_strength(strength: int) -> str:
    bounded = int(max(0, min(4, strength)))
    return _STRENGTH_TO_ACTION[bounded]


def one_notch_upgrade(action: str) -> str:
    return action_from_strength(action_strength(action) + 1)


def one_notch_downgrade(action: str) -> str:
    return action_from_strength(action_strength(action) - 1)


def map_score_to_action(score: float) -> str:
    score = clip_score(score)
    if score >= 8.35:
        return "Strong Buy"
    if score >= 6.75:
        return "Buy"
    if score >= 5.15:
        return "Hold"
    if score >= 3.65:
        return "Trim"
    return "Sell"


def data_quality_from_row(data: dict[str, Any] | pd.Series | None) -> tuple[float, str, list[str]]:
    """Return a 0-1 data-quality score, label, and missing-field list."""
    if data is None:
        return 0.0, "low", CORE_DATA_FIELDS.copy()
    if isinstance(data, pd.Series):
        data = data.to_dict()

    available = []
    missing = []
    for col in CORE_DATA_FIELDS:
        val = data.get(col)
        ok = val is not None and not pd.isna(val)
        if col in {"last_price", "market_cap"} and ok:
            try:
                ok = float(val) > 0
            except Exception:
                ok = False
        available.append(1.0 if ok else 0.0)
        if not ok:
            missing.append(col)

    base_score = float(np.mean(available)) if available else 0.0

    news_bonus = 0.0
    try:
        usable_news = float(data.get("usable_news_count") or 0.0)
        if usable_news >= 3:
            news_bonus = 0.04
        elif usable_news >= 1:
            news_bonus = 0.02
    except Exception:
        pass

    peer_bonus = 0.0
    try:
        peer_rel = float(data.get("peer_reliability") or 0.0)
        peer_bonus = min(0.06, max(0.0, peer_rel) * 0.06)
    except Exception:
        pass

    score = float(np.clip(base_score + news_bonus + peer_bonus, 0.0, 1.0))
    if score >= 0.78:
        label = "high"
    elif score >= 0.55:
        label = "medium"
    else:
        label = "low"
    return score, label, missing


def confidence_from_scores(scores: dict[str, float], data_quality_score: float | None = None) -> float:
    vals = [clip_score(v) for v in scores.values() if v is not None and not pd.isna(v)]
    if not vals:
        return 0.5
    dispersion = float(np.std(vals))
    avg_strength = float(np.mean(vals))
    confidence = 0.50 + min(0.16, avg_strength / 100.0) + max(0.0, 0.28 - min(0.28, dispersion / 9.5))
    if data_quality_score is not None and not pd.isna(data_quality_score):
        confidence *= 0.72 + 0.28 * float(np.clip(data_quality_score, 0.0, 1.0))
    return float(np.clip(confidence, 0.35, 0.94))


def blend_with_peer_score_detailed(
    absolute_score: float | None,
    peer_score: float | None,
    peer_reliability: float | None,
    max_peer_weight: float = 0.24,
) -> tuple[float, str, float]:
    """Blend absolute score with peer-relative score only when the peer set is reliable enough."""
    abs_score = clip_score(absolute_score)
    if peer_score is None or pd.isna(peer_score) or peer_reliability is None or pd.isna(peer_reliability):
        return abs_score, "", 0.0
    rel = float(np.clip(peer_reliability, 0.0, 1.0))
    if rel < 0.35:
        return abs_score, "Peer-relative data was too thin to materially change the score.", 0.0
    peer = clip_score(float(peer_score))
    weight = float(np.clip(max_peer_weight * rel, 0.0, max_peer_weight))
    blended = clip_score((1.0 - weight) * abs_score + weight * peer)
    direction = "supports" if peer >= abs_score else "tempers"
    return blended, f"Peer-relative ranking {direction} the absolute score with {rel:.0%} peer reliability.", weight


def blend_with_peer_score(
    absolute_score: float | None,
    peer_score: float | None,
    peer_reliability: float | None,
    max_peer_weight: float = 0.24,
) -> tuple[float, str]:
    """Backward-compatible two-value peer blend helper used by existing agents."""
    blended, note, _weight = blend_with_peer_score_detailed(
        absolute_score=absolute_score,
        peer_score=peer_score,
        peer_reliability=peer_reliability,
        max_peer_weight=max_peer_weight,
    )
    return blended, note


def dominant_decision_reason(sub_scores: dict[str, float], peer_score: float | None = None) -> str:
    readable = {
        "fundamental": "quality/fundamentals",
        "valuation": "valuation",
        "technical": "technical trend",
        "catalyst": "catalyst/news",
        "earnings": "earnings outlook",
        "risk_fit": "portfolio fit/risk",
    }
    pairs = [(k, clip_score(v)) for k, v in sub_scores.items() if k in readable and v is not None and not pd.isna(v)]
    if not pairs:
        return "balanced"
    best_key, best_val = max(pairs, key=lambda x: x[1])
    worst_key, worst_val = min(pairs, key=lambda x: x[1])
    if best_val >= 7.25 and best_val - worst_val >= 1.75:
        return readable[best_key]
    if worst_val <= 3.75 and best_val - worst_val >= 2.0:
        return f"risk from {readable[worst_key]}"
    if peer_score is not None and not pd.isna(peer_score) and float(peer_score) >= 7.5:
        return "peer-relative strength"
    return "balanced multi-factor profile"


def apply_overrides(
    action: str,
    sub_scores: dict[str, float],
    current_weight: float = 0.0,
    max_weight: float = 0.18,
    screening_pass: bool = True,
    comparison_mode: bool = False,
    peer_score: float | None = None,
    data_quality_score: float | None = None,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    action = normalize_action(action)
    fundamentals = clip_score(sub_scores.get("fundamental"))
    valuation = clip_score(sub_scores.get("valuation"))
    technical = clip_score(sub_scores.get("technical"))
    catalyst = clip_score(sub_scores.get("catalyst"))
    earnings = clip_score(sub_scores.get("earnings"))
    risk_fit = clip_score(sub_scores.get("risk_fit"))
    screening = clip_score(sub_scores.get("screening", 5.0))
    data_quality = 0.65 if data_quality_score is None or pd.isna(data_quality_score) else float(np.clip(data_quality_score, 0.0, 1.0))

    if action == "Hold" and fundamentals >= 7.25 and valuation >= 6.35 and (technical >= 5.0 or catalyst >= 5.35 or earnings >= 6.0):
        action = "Buy"
        notes.append("Quality, valuation, and at least one confirmation signal promote the name from Hold to Buy.")

    if action == "Buy" and fundamentals >= 8.0 and valuation >= 6.85 and technical >= 6.25 and earnings >= 6.0 and risk_fit >= 5.0:
        action = "Strong Buy"
        notes.append("Broad-based strength across quality, valuation, tape, and earnings supports a top-tier call.")

    if not screening_pass and action in {"Strong Buy", "Buy"}:
        action = "Hold"
        notes.append("The name fails a core screen check, so conviction is capped at Hold until the quality gate improves.")

    if fundamentals < 3.4 and action in {"Buy", "Strong Buy"}:
        action = "Hold"
        notes.append("Weak fundamentals cap the recommendation at Hold.")

    if technical < 2.5 and catalyst < 3.0 and action in {"Buy", "Strong Buy"}:
        action = "Hold"
        notes.append("Weak tape and limited catalyst support reduce conviction to Hold.")

    if valuation < 2.7 and action == "Strong Buy":
        action = "Buy"
        notes.append("Rich valuation tempers the strongest call by one notch.")

    if current_weight > 0 and current_weight >= max_weight * 0.98 and action in {"Strong Buy", "Buy"}:
        action = "Hold"
        notes.append("The position is already near the max-weight constraint, so fresh buying should be limited.")

    if risk_fit < 2.8 and action in {"Strong Buy", "Buy"}:
        action = "Hold"
        notes.append("Portfolio fit and concentration risk reduce the action to Hold.")

    if data_quality < 0.45 and action in {"Strong Buy", "Buy"}:
        action = "Hold"
        notes.append("Data quality is low, so the recommendation is capped at Hold until more evidence is available.")
    elif data_quality < 0.60 and action == "Strong Buy":
        action = "Buy"
        notes.append("Medium-low data coverage tempers Strong Buy to Buy.")

    if comparison_mode and peer_score is not None:
        peer_score = clip_score(peer_score)
        if peer_score < 3.4 and action in {"Strong Buy", "Buy"}:
            action = "Hold"
            notes.append("Peer-relative ranking is weak versus the selected comparison set, so the action is capped at Hold.")
        elif peer_score >= 7.8 and action == "Hold" and fundamentals >= 6.2 and valuation >= 5.2 and risk_fit >= 4.5 and data_quality >= 0.55:
            action = "Buy"
            notes.append("Strong peer-relative ranking upgrades a fundamentally acceptable Hold to Buy.")

    if screening < 3.8 and action == "Hold" and current_weight <= 0:
        action = "Avoid"
        notes.append("Screen quality is too weak for fresh capital today.")

    return action, notes
