from __future__ import annotations

from langgraphagenticai.portfolio_manager.schemas import RiskResult
from langgraphagenticai.portfolio_manager.scoring import clip_score, pct_to_score


def _safe_num(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def run_risk_agent(ticker: str, data: dict) -> RiskResult:
    beta = _safe_num(data.get("beta"))
    vol = _safe_num(data.get("ann_vol_3m"))
    dd = _safe_num(data.get("max_drawdown_1y"))
    current_weight = _safe_num(data.get("current_weight"))

    score = clip_score(
        (
            pct_to_score(beta, 0.7, 1.8, invert=True)
            + pct_to_score(vol, 0.10, 0.60, invert=True)
            + pct_to_score(abs(dd) if dd is not None else None, 0.05, 0.45, invert=True)
            + pct_to_score(current_weight, 0.00, 0.18, invert=True)
        ) / 4.0
    )

    risk_level = "low" if score >= 7.0 else "moderate" if score >= 5.0 else "high"
    summary = []
    risks = []
    if beta is not None and beta > 1.3:
        risks.append("Beta is elevated, so the stock may amplify broad-market swings.")
    if vol is not None and vol > 0.35:
        risks.append("Recent realized volatility is high.")
    if current_weight is not None and current_weight > 0.12:
        risks.append("Existing position size already contributes meaningful concentration.")
    if not risks:
        summary.append("Standalone market-risk profile is manageable.")

    return RiskResult(
        thesis=("cautious" if score <= 4.8 else "neutral" if score < 6.4 else "constructive"),
        conviction=("high" if risk_level in {"elevated", "high"} else "medium"),
        evidence_for=summary[:3],
        evidence_against=risks[:3],
        action_preference=("Hold" if score >= 5.0 else "Trim" if (current_weight or 0.0) > 0 else "Avoid"),
        challenge_points=["Stress-test the view against a higher-volatility market regime before sizing up."],
        data_gaps=[] if beta is not None and vol is not None else ["Risk measures are incomplete for this ticker."],
        ticker=ticker,
        score=score,
        verdict=risk_level,
        risk_level=risk_level,
        summary=summary[:3],
        risks=risks[:3],
        metrics={
            "beta": beta,
            "ann_vol_3m": vol,
            "max_drawdown_1y": dd,
            "current_weight": current_weight,
        },
    )
