from __future__ import annotations

from collections import Counter

from langgraphagenticai.portfolio_manager.schemas import PortfolioFitResult
from langgraphagenticai.portfolio_manager.scoring import clip_score, pct_to_score


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def run_portfolio_fit_agent(ticker: str, data: dict, portfolio_context: dict) -> PortfolioFitResult:
    """
    Portfolio-aware sizing agent.

    This agent should not decide whether the business is good or cheap. Its job is to say whether
    the position can fit in the current portfolio without creating single-name or sector concentration.
    """

    current_weight = _safe_float(data.get("current_weight"), 0.0)
    sector = str(data.get("sector") or "Unknown")
    max_weight = _safe_float(portfolio_context.get("max_weight"), 0.18)
    max_sector_weight = _safe_float(portfolio_context.get("max_sector_weight"), 0.35)
    cash_weight = _safe_float(portfolio_context.get("cash_weight"), 0.0)
    portfolio_mode = bool(portfolio_context.get("portfolio_mode", False))
    sector_exposures = Counter(portfolio_context.get("sector_weights", {}))
    sector_weight = _safe_float(sector_exposures.get(sector), 0.0)

    single_name_headroom = max(0.0, max_weight - current_weight)
    sector_headroom = max(0.0, max_sector_weight - sector_weight)

    concentration_score = pct_to_score(current_weight, 0.0, max_weight, invert=True)
    sector_score = pct_to_score(sector_weight, 0.0, max_sector_weight, invert=True)
    cash_score = pct_to_score(cash_weight, 0.0, 0.12)
    headroom_score = pct_to_score(min(single_name_headroom, sector_headroom), 0.0, max_weight)

    score = clip_score(
        0.34 * concentration_score
        + 0.30 * sector_score
        + 0.20 * headroom_score
        + 0.16 * cash_score
    )

    owned = current_weight > 0
    enough_headroom = single_name_headroom >= max(0.015, max_weight * 0.12) and sector_headroom >= 0.015
    sector_tight = sector_weight >= max_sector_weight * 0.92
    position_tight = current_weight >= max_weight * 0.88

    if not owned:
        if enough_headroom and (cash_weight >= 0.02 or not portfolio_mode):
            action_bias = "start_candidate"
            action_preference = "Add"
            sizing_guidance = "starter"
        elif enough_headroom and portfolio_mode:
            action_bias = "rotate_candidate"
            action_preference = "Hold"
            sizing_guidance = "starter / fund with trims"
        else:
            action_bias = "watchlist_only"
            action_preference = "Watchlist"
            sizing_guidance = "wait"
    elif position_tight or sector_tight:
        action_bias = "hold_or_trim"
        action_preference = "Trim"
        sizing_guidance = "lighten"
    elif score >= 6.4 and enough_headroom:
        action_bias = "hold_or_add"
        action_preference = "Add"
        sizing_guidance = "normal"
    else:
        action_bias = "hold"
        action_preference = "Hold"
        sizing_guidance = "small"

    summary = [
        f"Sector exposure to {sector} is currently about {sector_weight:.1%} versus a {max_sector_weight:.1%} cap.",
        f"Single-name headroom is about {single_name_headroom:.1%} versus the {max_weight:.1%} max position limit.",
    ]
    risks: list[str] = []
    if sector_tight:
        risks.append("Sector concentration is close to the configured cap, so additional sizing needs a stronger thesis.")
    if position_tight:
        risks.append("Current position size is close to the single-name cap.")
    if portfolio_mode and not owned and cash_weight < 0.02:
        risks.append("Little unallocated cash remains, so a new position requires funding from trims or exits.")
    if not enough_headroom:
        risks.append("Portfolio construction headroom is limited.")

    return PortfolioFitResult(
        thesis=("constructive" if score >= 6.7 else "cautious" if score <= 4.4 else "neutral"),
        conviction=("high" if action_preference in {"Add", "Trim", "Watchlist"} else "medium"),
        evidence_for=summary[:3],
        evidence_against=risks[:3],
        action_preference=action_preference,
        challenge_points=["Check concentration and sector overlap before acting on the standalone thesis."],
        data_gaps=[] if sector != "Unknown" else ["Portfolio sector exposure context is incomplete."],
        ticker=ticker,
        score=score,
        verdict=action_bias,
        action_bias=action_bias,
        sizing_guidance=sizing_guidance,
        summary=summary[:3],
        risks=risks[:3],
        metrics={
            "Current Weight": current_weight,
            "Sector Weight": sector_weight,
            "Cash Weight": cash_weight,
            "Max Position Weight": max_weight,
            "Max Sector Weight": max_sector_weight,
            "Single Name Headroom": single_name_headroom,
            "Sector Headroom": sector_headroom,
        },
    )

