"""Offline fund assessment contracts; no model/provider calls."""
from math import sqrt
from statistics import stdev
import pytest
from langgraphagenticai.portfolio_architect.research import demo_snapshot, candidates
from langgraphagenticai.portfolio_architect.etf_assessment import assess_etf
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
from langgraphagenticai.portfolio_architect.analyst_packet import research_packet
from langgraphagenticai.portfolio_architect.screening import position_tradeoffs
from langgraphagenticai.providers import portfolio_architect as provider


def test_fund_risk_arithmetic_and_separate_roles():
    snapshot=demo_snapshot(("SPY","GLD","IEF"),"SPY")
    roles=[]
    for security in snapshot.securities:
        fund=assess_etf(security)
        roles.append(fund["role"])
        prices=[v for _,v in sorted(security.history.items())]
        returns=[b/a-1 for a,b in zip(prices,prices[1:])]
        peak=prices[0]; worst=0
        for price in prices:
            peak=max(peak,price); worst=min(worst,price/peak-1)
        assert fund["observed_history"]["annualized_volatility"] == pytest.approx(stdev(returns)*sqrt(252))
        assert fund["observed_history"]["maximum_drawdown"] == pytest.approx(worst)
        assert "Unavailable" in fund["valuation_status"]
        assert fund["missing_required"]
        risks,drivers=position_tradeoffs(security,{})
        assert any(fund["role"] in v for v in drivers)
        assert not any("multiple exceeds" in v for v in risks)
    assert len(set(roles))==3


def test_short_history_and_company_ratios_cannot_create_fund_valuation():
    security=demo_snapshot(("GLD",),"SPY").securities[0]
    security.history={"2026-10-01":100,"2026-10-02":0,"bad":100}
    fund=assess_etf(security)
    assert not fund["observed_history"]
    assert "company P/E" in fund["valuation_status"]


def test_fund_thesis_reaches_ranking_and_model_packet():
    mandate=InvestorMandate(objective="Diversified fund allocation",assets="etfs",holdings=5)
    snapshot=demo_snapshot(("SPY","GLD","IEF","QQQ","SCHD"),"SPY")
    securities,scores,_=candidates(snapshot,mandate)
    assert all(any("Portfolio role hypothesis" in p for p in score.pros) for score in scores)
    packet=research_packet(securities,scores,mandate)
    assert all(row["fund_assessment"]["role"] for row in packet["candidates"])


def test_funds_do_not_request_company_ratios(monkeypatch):
    calls=[]
    def request(url,**kwargs):
        calls.append(url)
        return [{"symbol":"GLD","price":100}]
    monkeypatch.setattr(provider,"get_fmp_json",request)
    provider.load_current.clear()
    result=provider.load_current(("GLD",),"fixture-key")
    assert not any(url.endswith("ratios-ttm") for url in calls)
    assert result["facts"]["GLD"]["ratios"] == {}
    assert not any("ratios" in note for note in result["warnings"])
    provider.load_current.clear()
