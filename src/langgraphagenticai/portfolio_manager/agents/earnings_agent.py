from __future__ import annotations

from langgraphagenticai.portfolio_manager.schemas import EarningsResult
from langgraphagenticai.portfolio_manager.scoring import clip_score, pct_to_score


def run_earnings_agent(ticker: str, data: dict) -> EarningsResult:
    rev_growth = data.get("revenue_growth")
    eps_growth = data.get("earnings_growth")
    op_margin = data.get("operating_margin")
    analyst_upside = data.get("analyst_upside_pct")

    score = clip_score(
        (
            pct_to_score(rev_growth, -0.10, 0.25)
            + pct_to_score(eps_growth, -0.15, 0.30)
            + pct_to_score(op_margin, 0.00, 0.35)
            + pct_to_score(analyst_upside, -0.10, 0.25)
        ) / 4.0
    )

    tone = "confident" if score >= 7.0 else "balanced" if score >= 5.0 else "cautious"
    guidance_quality = "credible" if analyst_upside is not None and analyst_upside > 0 else "mixed"

    summary = []
    risks = []
    if eps_growth is not None and eps_growth > 0.10:
        summary.append("Earnings growth remains supportive of the forward story.")
    if op_margin is not None and op_margin > 0.15:
        summary.append("Margins suggest management is still executing efficiently.")
    if analyst_upside is not None and analyst_upside < 0:
        risks.append("The sell-side setup is not currently pointing to upside.")
    if rev_growth is not None and rev_growth < 0:
        risks.append("Recent top-line trajectory does not support an aggressive stance.")
    if not summary:
        summary.append("Execution signals are mixed, so earnings should reinforce rather than dominate the decision.")

    return EarningsResult(
        thesis=("constructive" if score >= 6.7 else "cautious" if score <= 4.4 else "neutral"),
        conviction=("high" if op_margin is not None and op_margin > 0.18 else "medium"),
        evidence_for=summary[:3],
        evidence_against=risks[:3],
        action_preference=("Buy" if score >= 6.8 else "Hold" if score >= 4.8 else "Avoid"),
        challenge_points=["Check whether earnings strength is broad-based or dependent on one unusually strong quarter."],
        data_gaps=[] if rev_growth is not None and eps_growth is not None else ["Recent earnings trend inputs are incomplete."],
        ticker=ticker,
        score=score,
        verdict=tone,
        management_tone=tone,
        guidance_quality=guidance_quality,
        summary=summary[:3],
        risks=risks[:3],
        metrics={
            "revenue_growth": rev_growth,
            "earnings_growth": eps_growth,
            "operating_margin": op_margin,
            "analyst_upside_pct": analyst_upside,
        },
    )
