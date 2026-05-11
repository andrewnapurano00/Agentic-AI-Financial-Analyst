from __future__ import annotations

from typing import Iterable

from langgraphagenticai.portfolio_manager.schemas import AgentResult, DebateResult, TickerAnalysisBundle
from langgraphagenticai.portfolio_manager.scoring import action_strength


def _conviction_rank(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(str(value).lower(), 2)


def _conviction_weight(value: str) -> float:
    return {"low": 0.85, "medium": 1.00, "high": 1.20}.get(str(value).lower(), 1.00)


def _collect_agents(bundle: TickerAnalysisBundle) -> list[AgentResult]:
    agents: Iterable[AgentResult | None] = [
        bundle.fundamentals,
        bundle.valuation,
        bundle.technicals,
        bundle.catalysts,
        bundle.earnings,
        bundle.risk,
        bundle.portfolio_fit,
    ]
    return [a for a in agents if a is not None]


def _score_agent_direction(agent: AgentResult) -> float:
    thesis = str(agent.thesis or "neutral").lower()
    action_bias = action_strength(agent.action_preference) - 2
    conviction = _conviction_weight(agent.conviction)

    thesis_component = 0.0
    if thesis in {"bullish", "supportive", "constructive"}:
        thesis_component = 1.1
    elif thesis in {"bearish", "cautious", "defensive"}:
        thesis_component = -1.1

    score_component = (float(agent.score or 5.0) - 5.0) / 2.35
    raw = 0.55 * thesis_component + 0.30 * action_bias + 0.15 * score_component
    return raw * conviction


def _debate_action_from_score(net_score: float, owned: bool, bullish_count: int, bearish_count: int) -> tuple[str, str]:
    if net_score >= 2.60 and bullish_count >= max(4, bearish_count + 2):
        return ("Add" if owned else "Strong Buy"), "aligned bullish"
    if net_score >= 1.00 and bullish_count > bearish_count:
        return ("Add" if owned else "Buy"), "constructive but debated"
    if net_score <= -2.60 and bearish_count >= max(3, bullish_count + 1):
        return ("Exit" if owned else "Avoid"), "defensive / bearish"
    if net_score <= -1.00 and bearish_count > bullish_count:
        return ("Trim" if owned else "Watchlist"), "cautious / mixed"
    return "Hold", "mixed"


def run_debate_orchestrator(bundle: TickerAnalysisBundle) -> DebateResult:
    agents = _collect_agents(bundle)
    support_reasons: list[str] = []
    conflict_reasons: list[str] = []
    open_questions: list[str] = []
    support_count = oppose_count = neutral_count = 0
    strongest_conviction = "medium"
    weighted_direction = 0.0

    for agent in agents:
        strongest_conviction = max(strongest_conviction, agent.conviction, key=_conviction_rank)
        thesis = str(agent.thesis or "neutral").lower()

        if thesis in {"bullish", "supportive", "constructive"}:
            support_count += 1
            support_reasons.extend(agent.evidence_for[:2] or agent.summary[:1])
        elif thesis in {"bearish", "cautious", "defensive"}:
            oppose_count += 1
            conflict_reasons.extend(agent.evidence_against[:2] or agent.risks[:2] or agent.summary[:1])
        else:
            neutral_count += 1
            support_reasons.extend(agent.evidence_for[:1])
            conflict_reasons.extend(agent.evidence_against[:1])

        weighted_direction += _score_agent_direction(agent)
        open_questions.extend(agent.challenge_points[:1])
        open_questions.extend(agent.data_gaps[:1])

    owned = (bundle.current_weight or 0.0) > 0
    action_tilt, consensus_state = _debate_action_from_score(
        net_score=weighted_direction,
        owned=owned,
        bullish_count=support_count,
        bearish_count=oppose_count,
    )

    if action_tilt in {"Strong Buy", "Buy", "Add"}:
        sizing_hint = "full" if strongest_conviction == "high" and consensus_state == "aligned bullish" else "normal"
    elif action_tilt in {"Trim", "Exit", "Avoid"}:
        sizing_hint = "small / defensive"
    elif strongest_conviction == "high" and support_count > oppose_count:
        sizing_hint = "starter"
    else:
        sizing_hint = "normal"

    alignment_gap = abs(support_count - oppose_count)
    confidence = 5.4 + min(1.4, alignment_gap * 0.35) + (0.5 if strongest_conviction == "high" else 0.0)
    if consensus_state == "mixed":
        confidence -= 0.4
    confidence = float(max(4.8, min(8.6, confidence)))

    return DebateResult(
        ticker=bundle.ticker,
        consensus_state=consensus_state,
        support_count=support_count,
        oppose_count=oppose_count,
        neutral_count=neutral_count,
        highest_conviction=strongest_conviction,
        action_tilt=action_tilt,
        support_reasons=[x for x in support_reasons if x][:5],
        conflict_reasons=[x for x in conflict_reasons if x][:5],
        open_questions=[x for x in open_questions if x][:5],
        sizing_hint=sizing_hint,
        confidence=confidence,
    )
