"""Session-owned, explicit, purpose-limited numerical reuse. No IO or global cache."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import secrets
from urllib.parse import urlsplit
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .research_context import normalize_company_symbol
from langgraphagenticai.analysis.claim_verification import Fact, saved_facts
from langgraphagenticai.analysis.earnings_metrics import instant
from langgraphagenticai.analysis.scenarios import saved_inputs
from langgraphagenticai.analysis.investment_brief import _safe_packet

HISTORIES = {"Standard V1":"dr_history", "Low cost V2 pilot":"drv2_history"}


class VerifiedResearchSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["verified-research-v1"] = "verified-research-v1"
    purpose: Literal["local_earnings_sensitivity"] = "local_earnings_sensitivity"
    run_id: str
    engine: Literal["Standard V1", "Low cost V2 pilot"]
    ticker: str
    session_id: str
    credential_scope: str
    created_at: str
    entitlement: Literal["originating FMP credential; session-only; no redistribution grant"] = "originating FMP credential; session-only; no redistribution grant"
    observations_json: str = Field(max_length=40000)
    evidence_json: str = Field(max_length=240000)
    validation: tuple[str, ...]
    source_fingerprint: str
    fingerprint: str

    @field_validator("observations_json")
    @classmethod
    def typed_observations(cls, value):
        facts = [Fact.model_validate(f) for f in json.loads(value)]
        if len(facts)!=2 or {(f.metric,f.basis) for f in facts}!={("net_income","TTM"),("market_cap","point_in_time")}:
            raise ValueError("Unsupported typed financial observations")
        return value


def _json(value):
    return json.dumps(value,sort_keys=True,allow_nan=False,separators=(",",":"))


def _payload(saved, ticker):
    rows = [r for r in saved.get("comparison",[]) if r.get("Ticker") == ticker]
    keys = ("Ticker","Sector","Industry","Net income (TTM)","Market cap","TTM through","TTM currency","TTM fiscal quarters","Quote as of")
    selected = [{k:deepcopy(row.get(k)) for k in keys} for row in rows]
    for target,row in zip(selected, rows):
        target["Metric contracts"] = {k:deepcopy(row.get("Metric contracts",{}).get(k)) for k in ("Net income (TTM)","Market cap")}
    evidence = [deepcopy(e) for e in saved.get("evidence",[]) if e.get("symbol") == ticker and e.get("category") in {"income_quarterly","income_ttm","quote","profile"}]
    return {"id":saved.get("id"),"financial_methodology":saved.get("financial_methodology"),"request":{"symbols":[ticker]},"comparison":selected,"evidence":evidence}


def _fingerprint(saved, ticker):
    return sha256(_json(_payload(saved,ticker)).encode()).hexdigest()


def _scope(secret, key):
    if not key:
        raise ValueError("FMP credential is unavailable; ticker-only navigation remains available.")
    return hmac.new(secret.encode(),key.encode(),"sha256").hexdigest()


def bind_collected_run(state, saved, engine, api_key):
    """Only call after a new explicit provider collection, never on saved-result render."""
    if engine not in HISTORIES or not api_key or not saved.get("id"):
        return
    secret = state.setdefault("_verified_research_secret",secrets.token_hex(32))
    session_id = state.setdefault("_verified_research_session",secrets.token_hex(24))
    bindings = state.setdefault("_verified_research_bindings",{})
    for ticker in saved.get("request",{}).get("symbols",[])[:4]:
        try:
            symbol = normalize_company_symbol(ticker)
            bindings[engine+":"+str(saved["id"])+":"+symbol] = {"scope":_scope(secret,api_key),"session_id":session_id,"fingerprint":_fingerprint(saved,symbol)}
        except (ValueError,TypeError,KeyError,AttributeError):
            continue
    while len(bindings)>40:
        del bindings[next(iter(bindings))]


def _binding(state, saved, ticker, engine, api_key):
    secret = state.get("_verified_research_secret")
    binding = state.get("_verified_research_bindings",{}).get(engine+":"+str(saved.get("id"))+":"+ticker)
    if not secret or not binding:
        raise ValueError("Legacy/unbound research has no originating credential lineage. Explicitly run fresh research; ticker navigation is still available.")
    if (binding["session_id"] != state.get("_verified_research_session")
            or not hmac.compare_digest(binding["scope"],_scope(secret,api_key))
            or not hmac.compare_digest(binding["fingerprint"],_fingerprint(saved,ticker))):
        raise ValueError("Research session, credential or source lineage changed. Reuse rejected; explicitly collect fresh evidence.")
    return binding


def _validate(saved, ticker, reference):
    inputs = saved_inputs(saved,ticker,reference)
    if not inputs.eligible:
        raise ValueError("Saved financial inputs are not reusable: "+"; ".join(inputs.reasons))
    facts, _ = saved_facts(saved,reference)
    selected = [f for f in facts if f.ticker == ticker and (f.metric,f.basis) in {("net_income","TTM"),("market_cap","point_in_time")}]
    if len(selected)!=2 or any(f.status != "available" or f.currency != inputs.currency for f in selected):
        raise ValueError("Verified earnings and capitalization require compatible currencies and fresh source observations; refresh research explicitly.")
    raw = [e for e in saved["evidence"] if e.get("symbol")==ticker and e.get("category") in {"income_quarterly","quote","profile"}]
    if len(raw)!=3 or any(e.get("provider") != "FMP" or urlsplit(str(e.get("url") or "")).scheme != "https" or urlsplit(str(e.get("url") or "")).hostname != "financialmodelingprep.com" for e in raw):
        raise ValueError("This pilot accepts directly identified FMP quarterly earnings, quote and profile sources only.")
    profiles = [e for e in raw if e.get("category")=="profile"]
    profile = profiles[0] if len(profiles)==1 else {}
    data = profile.get("data")
    rows = data if isinstance(data,list) else [data]
    comparison = next(r for r in saved["comparison"] if r.get("Ticker")==ticker)
    if (len(rows)!=1 or not isinstance(rows[0],dict) or rows[0].get("symbol")!=ticker
            or profile.get("status")!="ok" or not rows[0].get("sector") or rows[0].get("sector")!=comparison.get("Sector")
            or rows[0].get("industry")!=comparison.get("Industry")
            or not 0 <= (instant(reference)-instant(profile.get("retrieved_at"))).total_seconds() <= 30*86400):
        raise ValueError("Sector applicability requires a matching, dated originating FMP profile.")
    return inputs, [f.model_dump() for f in selected]


def create_snapshot(state, saved, ticker, engine, api_key, *, reference_time=None):
    reference = reference_time or datetime.now(timezone.utc).isoformat()
    instant(reference)
    ticker = normalize_company_symbol(ticker)
    binding = _binding(state,saved,ticker,engine,api_key)
    _, facts = _validate(saved,ticker,reference)
    payload = _safe_packet(_payload(saved,ticker),(api_key,))
    _, sanitized_facts = _validate(payload,ticker,reference)
    # Sanitization may clean URLs; numeric identities and timestamps must survive unchanged.
    def numeric(items):
        return [(f["metric"],f["value"],f["currency"],f["basis"],f["period_end"],f["status"]) for f in items]
    if numeric(facts) != numeric(sanitized_facts):
        raise ValueError("Safe packet cannot preserve validated numerical inputs.")
    values = dict(run_id=str(saved["id"]),engine=engine,ticker=ticker,session_id=binding["session_id"],credential_scope=binding["scope"],
        created_at=reference,observations_json=_json(sanitized_facts),evidence_json=_json(payload),
        validation=("raw-quarter earnings reconciliation","compatible explicit currency","dated capitalization","sector applicability","session and originating credential"),source_fingerprint=binding["fingerprint"])
    fingerprint = hmac.new(state["_verified_research_secret"].encode(),_json(values).encode(),"sha256").hexdigest()
    return VerifiedResearchSnapshot(**values,fingerprint=fingerprint)


def accept_snapshot(state, snapshot, ticker, api_key, *, reference_time=None):
    """Revalidate every render/edit. Returned inputs are for local calculation only."""
    if not isinstance(snapshot,VerifiedResearchSnapshot):
        raise ValueError("Unsupported or legacy financial snapshot; ticker navigation remains available.")
    snapshot = VerifiedResearchSnapshot.model_validate(snapshot.model_dump())
    if snapshot.ticker != normalize_company_symbol(ticker) or snapshot.session_id != state.get("_verified_research_session"):
        raise ValueError("Snapshot company/session mismatch; no financial data imported.")
    secret = state.get("_verified_research_secret","")
    if not secret or not hmac.compare_digest(snapshot.credential_scope,_scope(secret,api_key)):
        raise ValueError("Snapshot credential scope changed; no financial data imported.")
    values = {k:getattr(snapshot,k) for k in ("run_id","engine","ticker","session_id","credential_scope","created_at","observations_json","evidence_json","validation","source_fingerprint")}
    expected = hmac.new(secret.encode(),_json(values).encode(),"sha256").hexdigest()
    if not hmac.compare_digest(expected,snapshot.fingerprint):
        raise ValueError("Snapshot integrity check failed; no financial data imported.")
    current = [r for r in state.get(HISTORIES[snapshot.engine],[]) if r.get("id")==snapshot.run_id]
    if len(current)!=1:
        raise ValueError("Originating saved research is no longer uniquely available in this session.")
    binding = _binding(state,current[0],snapshot.ticker,snapshot.engine,api_key)
    if binding["fingerprint"] != snapshot.source_fingerprint:
        raise ValueError("Saved research was refreshed or changed; explicitly prepare a new snapshot.")
    reference = reference_time or datetime.now(timezone.utc).isoformat()
    if instant(reference) < instant(snapshot.created_at):
        raise ValueError("Snapshot creation time is in the future.")
    payload = json.loads(snapshot.evidence_json)
    inputs, facts = _validate(payload,ticker,reference)
    if _json(facts) != snapshot.observations_json:
        raise ValueError("Observation identity changed during revalidation.")
    return inputs
