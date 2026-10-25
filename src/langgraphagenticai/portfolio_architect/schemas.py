"""Versioned contracts; all weights are fractions of total account equity."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from langgraphagenticai.state.research_context import normalize_company_symbol

VERSION = "architect-2.1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class InvestorMandate(Contract):
    objective: str = Field(min_length=10, max_length=1800)
    investment_style: Literal["balanced", "growth"] = "balanced"
    horizon: Literal[1, 3, 5, 10] = 5
    risk: Literal["conservative", "moderate", "aggressive"] = "moderate"
    amount: float = Field(default=100000, ge=100, le=100000000)
    holdings: int = Field(default=10, ge=5, le=15)
    assets: Literal["stocks", "etfs", "both"] = "both"
    cash: float = Field(default=.10, ge=0, le=.8)
    historical_volatility_cap: float | None = Field(default=None, ge=.01, le=1.)
    position_cap: float = Field(default=.20, gt=0, le=1)
    sector_cap: float = Field(default=.40, gt=0, le=1)
    forbidden: list[str] = Field(default_factory=list, max_length=40)
    excluded_sectors: list[str] = Field(default_factory=list, max_length=15)
    themes: list[str] = Field(default_factory=list, max_length=5)
    benchmark: str = "SPY"
    method: Literal["equal", "risk", "conviction_risk", "risk_parity", "min_variance", "ai_risk_budget"] = "ai_risk_budget"

    @field_validator("benchmark")
    @classmethod
    def symbol(cls, v):
        return normalize_company_symbol(v)

    @field_validator("forbidden")
    @classmethod
    def symbols(cls, values):
        names = [normalize_company_symbol(v) for v in values]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate forbidden tickers.")
        return names

    @model_validator(mode="after")
    def capacity(self):
        from .universe import UNIVERSE, SECTORS, THEMES
        if self.investment_style == "growth":
            self.themes = [t for t in self.themes if t != "growth"]
        if self.benchmark not in UNIVERSE or any(s not in SECTORS for s in self.excluded_sectors) or any(t not in THEMES for t in self.themes):
            raise ValueError("Unsupported benchmark, sector or curated theme; revise the mandate explicitly.")
        if self.holdings * min(self.position_cap, self.sector_cap) < 1-self.cash-1e-9:
            raise ValueError("Holdings and position/sector caps cannot fund the requested non-cash allocation.")
        return self


class Fact(Contract):
    id: str
    field: str
    value: float
    unit: str
    basis: str
    as_of: str | None
    retrieved_at: str
    source: str


class SecurityEvidence(Contract):
    ticker: str
    name: str
    asset: Literal["stock", "etf"]
    sector: str
    themes: list[str]
    news: list[dict] = Field(default_factory=list)
    business_summary: str = "Issuer business description unavailable."
    price: float = Field(gt=0)
    currency: Literal["USD"]
    currency_basis: str
    quote_as_of: str
    retrieved_at: str
    provider: str
    facts: list[Fact]
    history: dict[str, float]
    history_retrieved_at: str
    history_basis: str
    flags: list[str]

    @field_validator("ticker")
    @classmethod
    def symbol(cls, v):
        return normalize_company_symbol(v)

    @field_validator("history")
    @classmethod
    def valid_history(cls, values):
        import math
        from datetime import date
        for day, price in values.items():
            date.fromisoformat(day)
            if not math.isfinite(price) or price <= 0:
                raise ValueError("History contains an invalid close.")
        return values


class EvidenceSnapshot(Contract):
    id: str
    mode: Literal["SYNTHETIC DEMO", "FMP live"]
    retrieved_at: str
    securities: list[SecurityEvidence]
    benchmark: SecurityEvidence | None
    warnings: list[str]
    excluded: dict[str, str]
    screening: dict = Field(default_factory=dict)
    macro: dict = Field(default_factory=dict)
    universe_version: str

    @model_validator(mode="after")
    def unique(self):
        names = [s.ticker for s in self.securities]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate evidence tickers.")
        return self


class CandidateScore(Contract):
    ticker: str
    score: float
    citations: list[str]
    pros: list[str]
    cons: list[str]


class RiskDiagnostics(Contract):
    status: Literal["available", "unavailable"]
    observations: int
    start: str | None
    end: str | None
    annualized_volatility: float | None
    max_drawdown: float | None
    benchmark_return: float | None
    portfolio_return: float | None
    high_correlations: list[str]
    warnings: list[str]
    convention: str


class HoldingRecommendation(Contract):
    ticker: str
    name: str
    sector: str
    asset: str
    weight: float = Field(gt=0, le=1)
    dollars: float = Field(ge=0)
    conviction: str
    pros: list[str]
    cons: list[str]
    sizing: str
    ai_analysis: dict = Field(default_factory=dict)
    citations: list[str]
    catalysts: list[str] = Field(default_factory=list)
    thesis_breakers: list[str]


class CommitteeReview(Contract):
    source: str
    initial_weights: dict[str, float]
    changes: list[str]
    vulnerabilities: list[str]
    disagreements: list[str]
    rejected: dict[str, str]
    roles: dict[str, str]


class PortfolioRecommendation(Contract):
    version: str = VERSION
    id: str
    snapshot: EvidenceSnapshot
    mandate: InvestorMandate
    holdings: list[HoldingRecommendation]
    cash: float
    cash_dollars: float
    sectors: dict[str, float]
    risk: RiskDiagnostics
    committee: CommitteeReview
    warnings: list[str]
    binding_constraints: list[str]
    method_used: str
    model: str | None
    usage: list[dict]
    risk_policy: dict = Field(default_factory=dict)
    allocation_audit: dict = Field(default_factory=dict)
    ai_review_status: dict = Field(default_factory=dict)


class WorkflowError(Contract):
    status: Literal["blocked", "partial"]
    stage: str
    message: str
    recoverable: bool = True


def utc_stamp(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Evidence requires a timezone-aware timestamp.")
    return stamp
