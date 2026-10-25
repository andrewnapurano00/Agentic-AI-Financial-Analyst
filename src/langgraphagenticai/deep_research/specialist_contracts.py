"""AX-03 pilot contracts; provider facts and model interpretation stay separate."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EvidenceRef(Contract):
    id: str
    ticker: str
    metric: str
    value: float
    unit: str
    currency: str | None
    period: str
    sources: list[dict]
    formula: str


class Task(Contract):
    id: str
    ticker: str
    role: Literal["fundamentals", "valuation_risk"]
    question: str
    evidence_ids: list[str]
    tool_allowlist: list[Literal["saved_metric_lookup"]]
    timeout_seconds: float = Field(gt=0, le=25)
    output_tokens: int = Field(gt=0, le=1200)


class Observation(Contract):
    evidence_id: str
    value: float
    unit: str
    currency: str | None
    period: str


class AgentResult(Contract):
    task_id: str = Field(max_length=60)
    ticker: str = Field(max_length=15)
    stance: Literal["constructive", "balanced", "cautious"]
    summary: str = Field(min_length=10, max_length=600)
    observations: list[Observation] = Field(min_length=1, max_length=4)
    risks: list[str] = Field(min_length=1, max_length=3)
    missing_metrics: list[str] = Field(max_length=2)


class ReviewFinding(Contract):
    task_id: str
    severity: Literal["error", "warning"]
    code: str
    detail: str


class FinalDecision(Contract):
    status: Literal["complete", "partial", "unavailable"]
    agreement: Literal["aligned", "disputed", "incomplete"]
    summary: str
    disagreements: list[str]
    limitations: list[str]
