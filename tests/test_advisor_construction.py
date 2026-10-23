"""Independent covariance/allocation references and bounded sector model packets."""
import json
import numpy as np
import pytest
from langgraphagenticai.portfolio_architect.construction import (
    project_weights, risk_budget_weights, minimum_variance_weights, allocation_analytics, quantitative_weights)
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
from langgraphagenticai.portfolio_architect.screening import metric_weights, sector_lens, metric_facts
from langgraphagenticai.portfolio_architect.analyst_packet import research_packet
from langgraphagenticai.portfolio_architect.research import demo_snapshot, candidates
from langgraphagenticai.portfolio_architect.universe import eligible_names
from langgraphagenticai.portfolio_architect.workflow import build


def test_diagonal_risk_budget_matches_inverse_volatility_and_risk_shares():
    cov = np.diag([1.,4.,9.])
    w = risk_budget_weights(cov, [1,1,1])
    expected = np.array([1.,.5,1/3]); expected /= expected.sum()
    assert w == pytest.approx(expected, abs=1e-7)
    shares = w*(cov@w)/(w@cov@w)
    assert shares == pytest.approx([1/3]*3, abs=1e-7)
    tilted = risk_budget_weights(cov, [.8,1.,1.2])
    assert tilted*(cov@tilted)/(tilted@cov@tilted) == pytest.approx(np.array([.8,1.,1.2])/3, abs=1e-7)


def test_minimum_variance_matches_analytical_inverse_variance():
    cov = np.diag([1.,2.,3.,4.,5.])
    m = InvestorMandate(objective="Diversified five stock portfolio", cash=.1, position_cap=.9, sector_cap=1., method="min_variance", holdings=5)
    w = minimum_variance_weights(cov, ["A","B","C","D","E"], m)
    expected = 1/np.diag(cov); expected *= .9/expected.sum()
    assert w == pytest.approx(expected, abs=1e-6)
    assert w@cov@w < np.full(5,.18)@cov@np.full(5,.18)


def test_minimum_variance_enforces_sector_and_position_caps():
    cov = np.diag([1.,1.,4.,5.,6.])
    m = InvestorMandate(objective="Diversified capped portfolio", cash=.1, position_cap=.3, sector_cap=.4, holdings=5, method="min_variance")
    w = minimum_variance_weights(cov, ["A","A","B","C","D"], m)
    assert sum(w) == pytest.approx(.9, abs=1e-9)
    assert max(w) <= .3+1e-9 and sum(w[:2]) <= .4+1e-9 and min(w) > 0
    # A feasible grid independently bounds the optimum from above.
    for a in np.linspace(.05,.3,6):
        for b in np.linspace(.05,.3,6):
            rest = (.9-a-b)/3
            if a+b <= .4 and 0 < rest <= .3:
                trial = np.array([a,b,rest,rest,rest])
                assert w@cov@w <= trial@cov@trial+1e-7


def test_projection_is_idempotent_and_respects_group_budget():
    sectors = ["A","A","B","C","D"]
    w = project_weights([.7,.2,.05,.03,.02], sectors, .9,.3,.4)
    assert sum(w) == pytest.approx(.9, abs=1e-9)
    assert sum(w[:2]) <= .4+1e-9 and max(w) <= .3+1e-9
    assert project_weights(w,sectors,.9,.3,.4) == pytest.approx(w,abs=1e-9)
    with pytest.raises(ValueError, match="capacity"):
        project_weights([.5,.5],["A","A"],.9,.3,.4)


def test_covariance_analytics_reconciles_and_keeps_cash_out_of_risk_shares():
    m = InvestorMandate(objective="Build a diversified research portfolio")
    snapshot = demo_snapshot(eligible_names(m),m.benchmark)
    result = build(snapshot,m)
    audit = result.allocation_audit
    assert audit["status"] == "available"
    assert sum(audit["risk_contributions"].values()) == pytest.approx(1)
    assert sum(audit["target_risk_budgets"].values()) == pytest.approx(1)
    assert "CASH" not in audit["risk_contributions"]
    assert 1 <= audit["effective_holdings"] <= len(result.holdings)+1e-9
    weights = {h.ticker:h.weight for h in result.holdings}
    securities = [s for s in snapshot.securities if s.ticker in weights]
    from langgraphagenticai.portfolio_architect.risk import aligned_returns, shrunk_covariance
    returns,_ = aligned_returns(securities)
    cov = shrunk_covariance(returns); w = np.array([weights[n] for n in returns.columns])
    assert audit["sizing_annualized_volatility"] == pytest.approx(np.sqrt(w@cov@w*252))


def test_sector_priorities_and_new_provider_fields_preserve_missing_and_zero():
    tech = metric_weights("Technology"); bank = metric_weights("Financial Services")
    assert tech["gross_margin_ttm"] == 2 and "pb_ttm" not in tech
    assert bank["pb_ttm"] == 2 and "gross_margin_ttm" not in bank and "pfcf_ttm" not in bank
    facts = metric_facts("AAA", {"grossProfitMarginTTM":0, "priceToSalesRatioTTM":3.2}, {}, "2026-10-21T00:00:00+00:00")
    assert {f.field:f.value for f in facts} == {"gross_margin_ttm":0,"ps_ttm":3.2}
    assert all(f.as_of is None and "not independently audited" in f.basis for f in facts)


def test_sector_packet_contains_provenance_risk_and_explicit_omissions():
    m = InvestorMandate(objective="Build a diversified research portfolio")
    snapshot = demo_snapshot(eligible_names(m), m.benchmark)
    securities, scores,_ = candidates(snapshot,m)
    from langgraphagenticai.portfolio_architect.analyst_packet import review_pool
    from langgraphagenticai.portfolio_architect.optimizer import select
    packet = research_packet(review_pool(securities,scores,select(securities,scores,m)),scores,m)
    from langgraphagenticai.portfolio_architect.analyst_packet import encode_packet
    assert len(encode_packet(packet).encode()) <= 42000
    assert packet["historical_risk"]["status"] == "available"
    for row in packet["candidates"]:
        assert "omitted_facts" in row and "missing_required" in row["sector_lens"]
        assert row["facts"]
        assert all(set(("id","unit","value","provenance_id")) <= set(f) and
                   set(("source","retrieved_at","as_of","basis")) <= set(packet["provenance"][f["provenance_id"]]) for f in row["facts"])
    bank = next(s for s in securities if s.ticker == "JPM")
    lens = sector_lens(bank)
    assert "CET1 Ratio" in lens["specialist_gaps"]


def test_quantitative_failure_and_sparse_history_return_explicit_fallback(monkeypatch):
    m = InvestorMandate(objective="Build a diversified research portfolio", method="risk_parity")
    snapshot = demo_snapshot(eligible_names(m), m.benchmark)
    for s in snapshot.securities: s.history = {}
    weights, note = quantitative_weights(snapshot.securities[:5],m)
    assert weights is None and "61" in note
    assert allocation_analytics(snapshot.securities[:5],{},m)["status"] == "unavailable"


def test_legacy_saved_result_accepts_absent_new_audit_and_thesis_fields():
    from langgraphagenticai.portfolio_architect.schemas import PortfolioRecommendation
    m=InvestorMandate(objective="Build a diversified research portfolio",method="risk")
    result=build(demo_snapshot(eligible_names(m),m.benchmark),m).model_dump()
    result.pop("allocation_audit")
    for h in result["holdings"]: h.pop("ai_analysis")
    saved=PortfolioRecommendation.model_validate(result)
    assert not saved.allocation_audit and not saved.holdings[0].ai_analysis


def test_nonconvergent_quantitative_solver_uses_disclosed_capped_equal_fallback(monkeypatch):
    from langgraphagenticai.portfolio_architect import construction
    m=InvestorMandate(objective="Build a diversified research portfolio",method="risk_parity")
    snapshot=demo_snapshot(eligible_names(m),m.benchmark)
    def fail(*args,**kwargs): raise ValueError("Fixture nonconvergence")
    monkeypatch.setattr(construction,"risk_budget_weights",fail)
    result=build(snapshot,m)
    assert result.method_used.startswith("equal (")
    assert any("did not converge" in w for w in result.warnings)
    assert not result.allocation_audit["target_risk_budgets"]
    assert sum(h.weight for h in result.holdings)+result.cash==pytest.approx(1,abs=1e-9)
    assert max(h.weight for h in result.holdings)<=m.position_cap+1e-9
