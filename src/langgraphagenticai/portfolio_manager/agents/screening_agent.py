from __future__ import annotations

from langgraphagenticai.portfolio_manager.schemas import ScreeningResult
from langgraphagenticai.portfolio_manager.scoring import clip_score


def _safe_num(x):
    try:
        return None if x is None else float(x)
    except (TypeError, ValueError):
        return None


def run_screening_agent(ticker: str, data: dict, min_market_cap: float = 1_000_000_000) -> ScreeningResult:
    notes: list[str] = []
    passes = True
    market_cap = _safe_num(data.get("market_cap"))
    avg_volume = _safe_num(data.get("average_volume"))
    last_price = _safe_num(data.get("last_price"))

    if market_cap is not None and market_cap < min_market_cap:
        passes = False
        notes.append("Market capitalization is below the preferred floor.")
    else:
        notes.append("Market capitalization is large enough for the core universe.")

    if avg_volume is not None and avg_volume < 500_000:
        notes.append("Liquidity is lighter than ideal.")
    else:
        notes.append("Average daily liquidity looks acceptable.")

    if last_price is not None and last_price < 3:
        passes = False
        notes.append("Price level is too low for the preferred investable universe.")

    data_quality = data.get("data_completeness", 1.0)
    score = 8.0 if passes else 4.0
    score = clip_score(score * data_quality)
    return ScreeningResult(
        thesis=("constructive" if passes else "cautious"),
        conviction=("high" if not passes else "medium"),
        evidence_for=notes[:2] if passes else [],
        evidence_against=notes[:2] if not passes else [],
        action_preference=("Hold" if passes else "Avoid"),
        challenge_points=["Do not let weak universe quality pass through simply because other agents are positive."],
        data_gaps=[] if market_cap is not None else ["Screening inputs are incomplete."],
        ticker=ticker,
        score=score,
        verdict="pass" if passes else "fail",
        summary=notes[:3],
        passes_screen=passes,
        screen_notes=notes,
        metrics={
            "market_cap": market_cap,
            "average_volume": avg_volume,
            "last_price": last_price,
            "data_completeness": data_quality,
        },
    )
