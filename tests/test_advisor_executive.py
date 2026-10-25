from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
from langgraphagenticai.portfolio_architect.research import demo_snapshot
from langgraphagenticai.portfolio_architect.universe import eligible_names
from langgraphagenticai.portfolio_architect import workflow, committee
from langgraphagenticai.portfolio_architect.screening import sector_lens
from langgraphagenticai.portfolio_architect.executive import holding_review, recommendation_rows


def fixture():
    m=InvestorMandate(objective="Build a diversified AI research portfolio", themes=["AI"])
    return m, demo_snapshot(eligible_names(m),m.benchmark)


def explanation(securities, *args, **kwargs):
    picks=[]
    for s in reversed(securities):
        picks.append(committee.AnalystPick(ticker=s.ticker, conviction="high", reason="diversification",
            evidence_ids=[s.facts[0].id], analysis=committee.AnalystAnalysis(
                framework=sector_lens(s)["framework"], thesis="Saved sector evidence supports this conditional research thesis.",
                conviction_summary="Profitability is supportive; durability remains uncertain.",
                risks=["Margins could deteriorate."], thesis_breaker="Reassess if dated profitability deteriorates.",
                portfolio_role="core", missing_inputs=["Forward estimates are unavailable."])))
    return committee.SpecialistOutput(picks=picks, concerns=["concentration","missing_data","valuation_uncertainty"],rejected=[]), {"status":"completed","attempts":1}


def test_explanation_cannot_reorder_select_or_resize_even_with_high_conviction(monkeypatch):
    m,s=fixture()
    local=workflow.build(s,m)
    review=Mock(side_effect=explanation)
    monkeypatch.setattr(workflow,"review",review)
    result=workflow.build(s,m,"fixture","synthetic",True,explanation_only=True)
    assert result.ai_review_status["state"]=="completed"
    assert [(h.ticker,h.weight,h.dollars) for h in result.holdings]==[(h.ticker,h.weight,h.dollars) for h in local.holdings]
    assert result.cash==local.cash and result.sectors==local.sectors
    assert review.call_args.kwargs["explanation_only"] is True
    assert {s.ticker for s in review.call_args.args[0]}=={h.ticker for h in local.holdings}
    assert all(h.ai_analysis and h.conviction=="explanation only" for h in result.holdings)
    assert result.usage[0]["role"]=="explanation_only"


def test_explanation_rejects_missing_holdings_and_preserves_local_result(monkeypatch):
    m,s=fixture()
    def missing(*args,**kwargs):
        output,usage=explanation(*args,**kwargs)
        output.picks.pop()
        return output,usage
    monkeypatch.setattr(workflow,"review",missing)
    local=workflow.build(s,m)
    result=workflow.build(s,m,"fixture","synthetic",True,explanation_only=True)
    assert result.ai_review_status["state"]=="failed"
    assert result.usage[0]["status"]=="validation_failed"
    assert [(h.ticker,h.weight) for h in result.holdings]==[(h.ticker,h.weight) for h in local.holdings]


def test_sector_projection_keeps_exact_values_periods_and_etf_separation():
    m,s=fixture()
    result=workflow.build(s,m)
    before=result.model_dump()
    stock=next(h for h in result.holdings if h.asset=="stock")
    review=holding_review(result,stock)
    assert review["score"] is None and review["coverage"] is None
    assert all(r["Source"] and r["Basis"] and r["Evidence ID"] for r in review["metrics"])
    security=next(v for v in s.securities if v.ticker==stock.ticker)
    margin=next(f for f in security.facts if f.field=="margin_ttm")
    assert next(r for r in review["metrics"] if r["Metric"]=="Latest Net Margin")["Saved value"]==f"{margin.value:.1%}"
    for holding in result.holdings:
        if holding.asset=="etf":
            fund=holding_review(result,holding)
            assert fund["framework"]=="ETF allocation" and fund["metrics"]==[] and fund["score"] is None
    assert result.model_dump()==before


def test_reader_selects_holding_without_provider_model_calls(monkeypatch):
    from langgraphagenticai.ui import portfolio_architect_tab as ui
    m,s=fixture()
    result=workflow.build(s,m)
    collect=Mock(); build=Mock()
    monkeypatch.setattr(ui,"collect",collect);monkeypatch.setattr(ui,"build",build)
    app=AppTest.from_string('from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect\nrender_portfolio_architect()',default_timeout=30)
    app.session_state["architect_result"]=result.model_dump(mode="json")
    app.run()
    assert not app.exception
    table=next(d.value for d in app.dataframe if "Main support" in d.value.columns)
    assert {"Sector score / 100","Main concern","Evidence coverage"} <= set(table)
    app.selectbox(key="architect_executive_ticker").set_value(result.holdings[-1].ticker).run()
    assert not app.exception
    assert app.session_state["architect_result"]==result.model_dump(mode="json")
    collect.assert_not_called();build.assert_not_called()


def test_real_review_contract_receives_only_fixed_holdings_and_exact_citations(monkeypatch):
    m,s=fixture()
    local=workflow.build(s,m)
    selected=[v for v in s.securities if v.ticker in {h.ticker for h in local.holdings}]
    captured=[]
    def structured(contract,packet,*args,**kwargs):
        captured.append((packet,args))
        picks=[]
        for row in packet["candidates"]:
            fact=next((v for v in row["facts"] if v["field"]=="margin_ttm"),row["facts"][0])
            picks.append(dict(ticker=row["ticker"],conviction="high",reason="diversification",evidence_ids=[fact["id"]],
                analysis=dict(framework=row["sector_lens"]["framework"],thesis="Saved evidence supports this conditional sector research thesis.",
                conviction_summary="Saved evidence is supportive; the outlook remains uncertain.",risks=["Margins may weaken."],
                thesis_breaker="Reassess if the saved profitability trend deteriorates.",portfolio_role="core",missing_inputs=["Forecast inputs missing."])))
        return contract.model_validate(dict(picks=picks,concerns=["concentration","missing_data","valuation_uncertainty"],rejected=[])),dict(status="completed",attempts=1)
    monkeypatch.setattr(committee,"structured_call",structured)
    output,_=committee.review(selected,[],m,"fixture","synthetic",required_tickers={v.ticker for v in selected},explanation_only=True)
    assert len(output.picks)==len(selected)
    assert {r["ticker"] for r in captured[0][0]["candidates"]}=={v.ticker for v in selected}
    assert "do not add, replace, reorder or resize" in captured[0][1][-1]


def test_metric_formatting_preserves_zero_negative_and_units():
    from langgraphagenticai.portfolio_architect.executive import formatted
    assert formatted(SimpleNamespace(value=0., unit="fraction"))=="0.0%"
    assert formatted(SimpleNamespace(value=-.1, unit="fraction"))=="-10.0%"
    assert formatted(SimpleNamespace(value=12.3, unit="multiple"))=="12.3x"
