"""Immutable saved model and explicit offline evidence; no credentials or AI calls."""
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from langgraphagenticai.portfolio_architect.optimizer import validate_weights
from langgraphagenticai.portfolio_architect.export import scrub
from langgraphagenticai.portfolio_architect.schemas import PortfolioRecommendation, utc_stamp


def encoded(value):
    return json.dumps(value,sort_keys=True,allow_nan=False,separators=(",",":"))


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Position(Frozen):
    ticker: str
    sector: str
    asset: Literal["stock","etf"]
    weight: float = Field(gt=0,le=1)
    price: float = Field(gt=0)
    currency: Literal["USD"]
    source: str
    as_of: str
    retrieved_at: str


class ModelSnapshot(Frozen):
    schema_version: Literal["monitor-model-v1"] = "monitor-model-v1"
    result_id: str
    fingerprint: str
    created_at: str
    mode: str
    benchmark: str
    positions: tuple[Position,...]
    cash: float = Field(ge=0,le=1)
    position_cap: float = Field(gt=0,le=1)
    sector_cap: float = Field(gt=0,le=1)
    minimum_cash: float = Field(ge=0,le=1)
    historical_volatility_cap: float | None = None
    thesis: tuple[str,...]
    risk_policy_json: str


def snapshot_model(result, *, reference_time=None, credentials=()):
    result = PortfolioRecommendation.model_validate(result.model_dump() if isinstance(result,PortfolioRecommendation) else result)
    reference = reference_time or datetime.now(timezone.utc).isoformat()
    utc_stamp(reference)
    weights = {h.ticker:h.weight for h in result.holdings}
    securities = [next(s for s in result.snapshot.securities if s.ticker==h.ticker) for h in result.holdings]
    validate_weights(securities,weights,result.cash,result.mandate)
    positions = tuple(Position(ticker=s.ticker,sector=s.sector,asset=s.asset,weight=weights[s.ticker],price=s.price,
        currency=s.currency,source=s.provider,as_of=s.quote_as_of,retrieved_at=s.retrieved_at) for s in securities)
    for p in positions:
        if utc_stamp(p.as_of)>utc_stamp(p.retrieved_at) or utc_stamp(p.retrieved_at)>utc_stamp(reference):
            raise ValueError("Saved quote chronology is unavailable or inconsistent.")
    values = dict(result_id=result.id,created_at=reference,mode=result.snapshot.mode,benchmark=result.mandate.benchmark,
        positions=[p.model_dump() for p in positions],cash=result.cash,position_cap=result.mandate.position_cap,
        sector_cap=result.mandate.sector_cap,minimum_cash=result.mandate.cash,historical_volatility_cap=result.mandate.historical_volatility_cap,
        thesis=["Saved model opinion: "+str(h.ai_analysis.get("thesis") or "; ".join(h.pros)) for h in result.holdings],
        risk_policy_json=encoded(result.risk_policy))
    values = scrub(values,credentials)
    if len(encoded(values).encode())>120000:
        raise ValueError("Monitoring plan exceeds the saved-data budget.")
    return ModelSnapshot(**values,fingerprint=hashlib.sha256(encoded(values).encode()).hexdigest())


class Quote(Frozen):
    ticker: str
    price: float = Field(gt=0)
    currency: Literal["USD"]
    provider: str
    as_of: str
    retrieved_at: str
    status: Literal["available","missing","failed","expired"] = "available"
    share_basis: Literal["verified_same_share_basis","unknown"] = "unknown"
    adjustment_evidence_id: str = ""


class PriceEvent(Frozen):
    event_id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
    credential_scope: str = Field(pattern=r"^[a-f0-9]{64}$")
    quotes: tuple[Quote,...] = Field(max_length=15)


def concentration_advisory(model, event, reference):
    """Revalue a fixed saved mix, with cash unchanged; no share/order execution."""
    clock = utc_stamp(reference)
    quotes = {q.ticker:q for q in event.quotes}
    if len(quotes)!=len(event.quotes) or set(quotes)!={p.ticker for p in model.positions}:
        raise ValueError("Partial, duplicate or cross-company refresh; no concentration signal.")
    values = {}
    evidence = []
    for p in model.positions:
        q = quotes[p.ticker]
        as_of,retrieved = utc_stamp(q.as_of),utc_stamp(q.retrieved_at)
        if (q.status!="available" or q.currency!=p.currency or q.provider!=p.source
                or q.share_basis!="verified_same_share_basis" or not q.adjustment_evidence_id
                or not utc_stamp(p.as_of)<=as_of<=retrieved<=clock
                or (clock-retrieved).total_seconds()>900 or (clock-as_of).total_seconds()>7*86400):
            raise ValueError("Failed/stale/currency/provider/share-basis evidence; no concentration signal.")
        values[p.ticker]=p.weight*q.price/p.price
        evidence.append({"ticker":p.ticker,"old_price":p.price,"old_as_of":p.as_of,"new_price":q.price,
                         "new_as_of":q.as_of,"retrieved_at":q.retrieved_at,"adjustment_evidence_id":q.adjustment_evidence_id})
    total=sum(values.values())+model.cash
    if not math.isfinite(total) or not total>0 or any(not math.isfinite(v) for v in values.values()):
        raise ValueError("Invalid model valuation.")
    weights={t:v/total for t,v in values.items()}
    cash=model.cash/total
    sectors={}
    for p in model.positions: sectors[p.sector]=sectors.get(p.sector,0)+weights[p.ticker]
    breaches=[t+" position cap" for t,w in weights.items() if w>model.position_cap+1e-9]
    breaches += [s+" sector/category cap" for s,w in sectors.items() if w>model.sector_cap+1e-9]
    if cash<model.minimum_cash-1e-9: breaches.append("minimum cash")
    if not breaches:
        return None
    return {"kind":"concentration_drift","event_id":event.event_id,"model_fingerprint":model.fingerprint,
        "old_weights":{p.ticker:p.weight for p in model.positions},"new_weights":weights,"new_cash":cash,"sectors":sectors,
        "breaches":breaches,"evidence":evidence,"benchmark":model.benchmark,
        "proposed_target_weights":{**{p.ticker:p.weight for p in model.positions},"CASH":model.cash},
        "proposed_action":"Review drift and consider restoring the original saved mix only after fresh risk, price, cost and suitability review.",
        "verification":"Deterministic arithmetic over supplied price observations; provider truth, entitlement and share-basis proof are not independently certified.",
        "limitations":["Fixed saved quantities represented by relative weights; cash unchanged; no fees, taxes, dividends or cash flows.",
            "ETF underlying exposure and benchmark-relative holdings remain unknown. Category caps are not look-through limits.",
            "No expected return, forecast loss, transaction-cost estimate, executable shares or brokerage orders. Historical volatility must be rechecked before any simulated change."],
        "model_calls":0,"estimated_model_cost_usd":0,"execution":"unavailable"}
