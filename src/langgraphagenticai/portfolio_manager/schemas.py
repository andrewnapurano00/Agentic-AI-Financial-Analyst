from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AgentResult:
    ticker: str
    score: float = 0.0
    verdict: str = "unknown"
    summary: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    thesis: str = "neutral"
    conviction: str = "medium"
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    action_preference: str = "Hold"
    challenge_points: list[str] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScreeningResult(AgentResult):
    passes_screen: bool = True
    screen_notes: list[str] = field(default_factory=list)


@dataclass
class FundamentalResult(AgentResult):
    pillar_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class ValuationResult(AgentResult):
    valuation_status: str = "unknown"


@dataclass
class TechnicalResult(AgentResult):
    trend: str = "neutral"
    momentum: str = "neutral"
    timing: str = "neutral"


@dataclass
class CatalystResult(AgentResult):
    sentiment: str = "neutral"
    catalyst_view: str = "neutral"


@dataclass
class EarningsResult(AgentResult):
    management_tone: str = "neutral"
    guidance_quality: str = "mixed"


@dataclass
class RiskResult(AgentResult):
    risk_level: str = "moderate"


@dataclass
class PortfolioFitResult(AgentResult):
    action_bias: str = "hold"
    sizing_guidance: str = "normal"


@dataclass
class DebateResult:
    ticker: str
    consensus_state: str = "mixed"
    support_count: int = 0
    oppose_count: int = 0
    neutral_count: int = 0
    highest_conviction: str = "medium"
    action_tilt: str = "Hold"
    support_reasons: list[str] = field(default_factory=list)
    conflict_reasons: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    sizing_hint: str = "normal"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinalRecommendation:
    ticker: str
    sector: str = "Unknown"
    industry: str = "Unknown"
    current_weight: float = 0.0
    composite_score: float = 0.0
    absolute_score: float = 0.0
    peer_score: float | None = None
    peer_rank: float | None = None
    peer_percentile: float | None = None
    confidence: float = 0.0
    final_action: str = "Hold"
    action_bias: str = "Hold"
    suggested_sizing: str = "normal"
    consensus_state: str = "mixed"
    decision_confidence: str = "medium"
    data_quality_score: float = 0.0
    data_quality_label: str = "medium"
    decision_reason: str = "balanced"
    pm_decision_summary: str = ""
    key_supports: list[str] = field(default_factory=list)
    key_conflicts: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    monitor_triggers: list[str] = field(default_factory=list)
    triggered_guardrails: list[str] = field(default_factory=list)
    why: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    explanation: str = ""
    sub_scores: dict[str, float] = field(default_factory=dict)
    raw_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TickerAnalysisBundle:
    ticker: str
    sector: str
    industry: str
    current_weight: float
    shares: float
    last_price: float
    market_value: float
    data: dict[str, Any] = field(default_factory=dict)
    screening: ScreeningResult | None = None
    fundamentals: FundamentalResult | None = None
    valuation: ValuationResult | None = None
    technicals: TechnicalResult | None = None
    catalysts: CatalystResult | None = None
    earnings: EarningsResult | None = None
    risk: RiskResult | None = None
    portfolio_fit: PortfolioFitResult | None = None
    debate: DebateResult | None = None
    final: FinalRecommendation | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
