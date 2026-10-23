"""Growth intent, feasible ranked selection, cited conviction and honest fallback."""
from types import SimpleNamespace as NS
from unittest.mock import Mock
import json
import pytest
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate, Fact, CandidateScore
from langgraphagenticai.portfolio_architect.mandate import default_mandate, infer_style
from langgraphagenticai.portfolio_architect.mandate_fit import mandate_priority, growth_fit
from langgraphagenticai.portfolio_architect.optimizer import select
from langgraphagenticai.portfolio_architect.research import demo_snapshot, candidates
from langgraphagenticai.portfolio_architect.universe import eligible_names
from langgraphagenticai.portfolio_architect.workflow import build
from langgraphagenticai.portfolio_architect.export import allocation_rows, conviction_text
from langgraphagenticai.portfolio_architect import committee


def test_growth_prompt_becomes_explicit_style_without_expanding_universe():
    m,_=default_mandate("Build an aggressive five-year growth portfolio focused on AI with diversified risk.")
    assert m.investment_style=="growth" and m.themes==["AI"]
    assert infer_style("not a growth portfolio")=="balanced"
    assert m.assets=="both" and not m.forbidden


def test_supported_ai_growth_beats_unrelated_high_quality_value_name():
    m,_=default_mandate("Build a growth portfolio focused on AI")
    snap=demo_snapshot(eligible_names(m),m.benchmark)
    tech=next(s for s in snap.securities if s.ticker=="MSFT").model_copy(deep=True)
    other=next(s for s in snap.securities if s.ticker=="XOM").model_copy(deep=True)
    tech.business_summary="Develops artificial intelligence software and cloud services."
    for f in tech.facts:
        if f.field=="revenue_cagr_3y":f.value=.15
    for f in other.facts:
        if f.field=="revenue_cagr_3y":f.value=.30
    a=mandate_priority(tech,m,.65);b=mandate_priority(other,m,1.)
    assert a[0] and b[0] and a[1]>b[1]
    assert a[2]["theme_relevance"]==1 and "unquantified" in a[2]["theme_basis"]


@pytest.mark.parametrize("value",[None,0,-.1])
def test_missing_or_nonpositive_growth_is_not_filled_by_quality(value):
    m,_=default_mandate("Build a growth portfolio")
    s=demo_snapshot(eligible_names(m),m.benchmark).securities[0].model_copy(deep=True)
    s.asset="stock"
    s.facts=[f for f in s.facts if f.field!="revenue_cagr_3y"]
    if value is not None:
        s.facts.append(Fact(id=s.ticker+":revenue_cagr_3y",field="revenue_cagr_3y",value=value,unit="fraction",basis="synthetic annual",as_of=None,retrieved_at=s.retrieved_at,source="fixture"))
    assert not growth_fit(s,m)[0]


def test_diversification_does_not_force_a_lower_ranked_sector_if_capacity_is_feasible():
    m=InvestorMandate(objective="Build a growth research portfolio",holdings=5,cash=.1,position_cap=.3,sector_cap=.6)
    names=[NS(ticker="T1",sector="Technology"),NS(ticker="T2",sector="Technology"),NS(ticker="T3",sector="Technology"),
           NS(ticker="H1",sector="Healthcare"),NS(ticker="H2",sector="Healthcare"),NS(ticker="V1",sector="Materials")]
    scores=[CandidateScore(ticker=s.ticker,score=100-i,citations=[],pros=[],cons=[]) for i,s in enumerate(names)]
    chosen=select(names,scores,m)
    assert {s.ticker for s in chosen}=={"T1","T2","T3","H1","H2"}


def test_shortlist_reserves_collection_for_ai_sector_proxies_without_fixed_names():
    from langgraphagenticai.portfolio_architect.screening import shortlist
    m,_=default_mandate("Build a growth portfolio focused on AI")
    rows=[{"symbol":f"V{i}","sector":"Basic Materials","framework":"Materials","exclusion":"","score":100-i} for i in range(30)]
    rows += [{"symbol":f"T{i}","sector":"Technology","framework":"Technology / Software / Semis","exclusion":"","score":50-i} for i in range(20)]
    chosen=shortlist(rows,m)
    assert len(chosen)==30 and all(f"T{i}" in chosen for i in range(20))


def test_conviction_summary_is_visible_in_shared_allocation_rows_without_model_calls():
    m=InvestorMandate(objective="Build a diversified portfolio")
    r=build(demo_snapshot(eligible_names(m),m.benchmark),m)
    r.holdings[0].conviction="high"
    r.holdings[0].ai_analysis={"conviction_summary":"Positive annual growth and AI relevance support conviction; valuation remains uncertain."}
    text=allocation_rows(r)[0]["Conviction (subjective)"]
    assert text.startswith("High - ") and "AI relevance" in text
    r.holdings[0].ai_analysis={}
    assert "no validated AI" in conviction_text(r.holdings[0])


def test_ai_failure_is_saved_as_sanitized_status_and_no_false_rationale(monkeypatch):
    m=InvestorMandate(objective="Build a diversified portfolio")
    snapshot=demo_snapshot(eligible_names(m),m.benchmark)
    call=Mock(side_effect=RuntimeError("fixture-secret https://unsafe.invalid/?api_key=fixture-secret"))
    monkeypatch.setattr(committee,"structured_call",call)
    r=build(snapshot,m,"fixture-secret","fixture-model",True)
    assert r.ai_review_status["state"]=="failed"
    assert "fixture-secret" not in json.dumps(r.ai_review_status)
    assert all(not h.ai_analysis and h.conviction=="not AI rated" for h in r.holdings)
    call.assert_called_once()


def test_ai_interpretation_cannot_drop_explicit_growth_and_ai_intent(monkeypatch):
    from langgraphagenticai.portfolio_architect.mandate import interpret
    value=InvestorMandate(objective="Build a growth portfolio focused on AI",themes=[],investment_style="balanced")
    monkeypatch.setattr(committee,"structured_call",Mock(return_value=(value,{"attempts":1})))
    m,_,_=interpret("Build a growth portfolio focused on AI","fixture","model",True)
    assert m.investment_style=="growth" and "AI" in m.themes
