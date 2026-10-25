"""Consumer-independent facts, provenance and validation states; no network or caches."""
from dataclasses import asdict, dataclass, replace
from types import MappingProxyType
from typing import Literal
import hashlib
import json
import math

MetricStatus = Literal["available", "missing", "stale", "inconsistent", "unverifiable", "unsupported"]


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    label: str
    field: str
    basis: Literal["quarterly", "annual", "TTM"]
    formula: str
    unit: str = "currency"
    scaling: str = "Provider-reported monetary amounts, unchanged; no inferred scaling"
    applicability: str = "Total company earnings across sectors; not EPS, FFO/AFFO or a valuation framework"
    retrieval_max_days: int = 30
    observation_max_days: int = 200


DEFINITIONS = MappingProxyType({d.id: d for d in (
    MetricDefinition("net_income.quarterly", "Quarterly net income", "netIncome", "quarterly", "One reported standalone fiscal quarter"),
    MetricDefinition("net_income.annual", "Annual net income", "netIncome", "annual", "One reported fiscal year", observation_max_days=550),
    MetricDefinition("net_income.ttm", "TTM net income", "netIncome", "TTM", "Sum four unique consecutive standalone fiscal quarters"),
)})


@dataclass(frozen=True)
class MetricInput:
    source_id: str
    provider: str
    route: str
    field: str
    value: float | None
    currency: str | None
    fiscal_year: int
    period: str
    period_end: str
    retrieved_at: str
    filing_date: str | None = None
    accepted_at: str | None = None
    availability_basis: str = "Filing/acceptance retained separately; absent timezone does not establish intraday availability"
    security_id: str | None = None


@dataclass(frozen=True)
class MetricObservation:
    metric_id: str
    ticker: str
    value: float | None
    currency: str | None
    basis: str
    status: MetricStatus
    origin: Literal["provider", "derived"]
    verification: Literal["structural", "reconciled", "unverifiable"]
    as_of: str | None
    evaluated_at: str
    inputs: tuple[MetricInput, ...] = ()
    reasons: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    unit: str = "currency"
    price_adjustment: str = "Not applicable to total company earnings"

    def __post_init__(self):
        if self.metric_id not in DEFINITIONS or self.basis != DEFINITIONS[self.metric_id].basis or self.unit != "currency":
            raise ValueError("Unsupported metric definition/basis/unit")
        if self.status not in {"available", "missing", "stale", "inconsistent", "unverifiable", "unsupported"}:
            raise ValueError("Unsupported observation status")
        if self.value is not None and (isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not math.isfinite(self.value)):
            raise ValueError("Metric values must be finite numbers or missing")

    @property
    def valid_zero(self):
        return self.value == 0 and self.status in {"available", "stale"}

    @property
    def eligible(self):
        return self.status == "available" and self.value is not None

    @property
    def identity(self):
        # Reference time/freshness assessment does not change the underlying fact.
        fact = {k: v for k, v in asdict(self).items()
                if k not in {"evaluated_at", "status", "reasons", "verification", "assumptions"}}
        return hashlib.sha256(json.dumps(fact, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def to_dict(self):
        definition = DEFINITIONS[self.metric_id]
        return {"schema": "axiom-metric-observation-v1", **asdict(self), "identity": self.identity, "valid_zero": self.valid_zero, "eligible": self.eligible,
                "formula": definition.formula, "scaling": definition.scaling, "applicability": definition.applicability}

    def flagged(self, status, reason, *, value=None, preserve_value=True):
        return replace(self, status=status, reasons=(*self.reasons, reason),
                       value=self.value if preserve_value else value,
                       verification=self.verification if status in {"available", "stale"} else "unverifiable")
