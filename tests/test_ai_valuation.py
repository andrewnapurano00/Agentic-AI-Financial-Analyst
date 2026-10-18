"""Offline annual-basis, provider, AI, UI and navigation valuation contracts."""
from copy import deepcopy
from datetime import date, datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
import json
import math
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.valuation import model, ai
from langgraphagenticai.providers import valuation as provider


def evidence(symbol="AAPL", sector="Technology"):
    now = datetime.now(timezone.utc)
    year = now.year - 1
    source = {k: dict(provider="FMP", retrieved_at=now.isoformat(), status="available", route=provider.JOBS[k][0]) for k in provider.JOBS}
    return dict(symbol=symbol, evidence_version=3, retrieved_at=now.isoformat(), sources=source, warnings=[],
        quote=[dict(symbol=symbol, price=100., timestamp=(now-timedelta(hours=1)).timestamp(), currency="USD")],
        profile=[dict(symbol=symbol, companyName=symbol+" Company", sector=sector, industry="", currency="USD")],
        income=[dict(symbol=symbol, date=f"{y}-12-31", period="FY", reportedCurrency="USD", epsDiluted=5., netIncome=500., weightedAverageShsOutDil=100., revenue=1000.) for y in (year, year-1)],
        balance=[dict(symbol=symbol, date=f"{year}-12-31", period="FY", reportedCurrency="USD", totalStockholdersEquity=2200., preferredStock=200., commonStockSharesOutstanding=100.)],
        estimates=[dict(symbol=symbol, date=f"{now.year+1}-12-31", estimatedEpsAvg=6., numberAnalystEstimatedEps=12)])


def facts(raw=None):
    return model.prepare(raw or evidence(), acknowledge_units=True)


def answer(packet):
    driver="balance:0" if packet["method"]=="P/B" else "income:0"
    eligible=packet["target_eligibility"]
    return dict(ticker=packet["ticker"], fingerprint=packet["fingerprint"], recommendation="Buy" if eligible else "Insufficient evidence",
        thesis="Growth could support value if margins hold, but the exit multiple remains uncertain.", sector_logic="Use the selected sector method.",
        growth_pct=10. if eligible else None, terminal_multiple=20. if eligible else None,
        growth_reason="Growth is a hypothesis based on annual fundamentals.", multiple_reason="The observed multiple is a starting reference, not a peer median.",
        growth_evidence_ids=[driver] if eligible else [], multiple_evidence_ids=[driver,"quote:0"] if eligible else [],
        evidence_ids=[driver], catalysts=["Operating execution could support growth."], risks=["Multiple compression could reduce value."],
        invalidation="Reassess after sustained earnings deterioration.", limitations="Annual evidence is incomplete; no peers or news supplied.", confidence="Low",
        scenarios=[dict(name=n,growth_pct=g,annual_growth_decimal=g/100,terminal_multiple=m,rationale="Conditional execution and valuation case.",evidence_ids=[driver,"quote:0"]) for n,g,m in [("Bear",0.,15.),("Base",10.,20.),("Bull",20.,25.)]] if eligible else [])


def test_industrial_and_bank_numerical_contracts():
    f=facts()
    assert f["eligible"] and f["basis"]==5 and f["current_multiple"]==20
    actual=model.calculate(f,3,.1,20)
    assert actual["Base"]["target"]==pytest.approx(133.1)
    assert actual["Base"]["price_return"]==pytest.approx(.331)
    assert actual["Base"]["cagr"]==pytest.approx(.1)
    assert actual["Base"]["review_price"]==pytest.approx(100.)
    assert actual["Bear"]["target"]==pytest.approx(5*1.06**3*15)
    bank=facts(evidence("JPM","Financial Services"))
    assert bank["eligible"] and bank["basis"]==20 and bank["method"]=="P/B"
    assert model.calculate(bank,5,.05,5)["Base"]["target"]==pytest.approx(20*1.05**5*5)


@pytest.mark.parametrize("edit,reason", [
    (lambda r:r["income"][0].update(epsDiluted=-1),"Positive verified"),
    (lambda r:r["income"][0].update(netIncome=0),"Non-positive"),
    (lambda r:r["income"][0].update(weightedAverageShsOutDil=0),"shares"),
    (lambda r:r["income"][0].update(reportedCurrency="EUR"),"currency mismatch"),
    (lambda r:r["quote"][0].update(currency="EUR"),"currency mismatch"),
    (lambda r:r["quote"][0].update(timestamp=1),"seven UTC"),
    (lambda r:r["quote"][0].update(timestamp=datetime.now(timezone.utc).timestamp()+3600),"future"),
    (lambda r:r["income"].clear(),"annual diluted EPS"),
    (lambda r:r["profile"][0].update(sector=""),"Sector classification"),
    (lambda r:r["profile"][0].update(sector="Real Estate",industry="Mortgage REIT"),"FFO/AFFO"),
    (lambda r:r["profile"][0].update(sector="Energy"),"mid-cycle"),
    (lambda r:r["income"][0].update(date="2020-12-31"),"550-day"),
    (lambda r:r["quote"][0].update(symbol="MSFT"),"identity mismatch"),
    (lambda r:r.update(retrieved_at="2020-01-01T00:00:00Z"),"24 hours"),
    (lambda r:r["sources"]["income"].update(retrieved_at="2020-01-01T00:00:00Z"),"Income source retrieval"),
])
def test_invalid_or_unsupported_evidence_blocks_targets(edit,reason):
    raw=evidence();edit(raw);f=facts(raw)
    assert not f["eligible"] and any(reason in r for r in f["reasons"])
    with pytest.raises(ValueError):model.calculate(f,5,.1,20)


def test_missing_values_not_zero_and_bank_uses_point_in_time_shares():
    raw=evidence("JPM","Financial Services")
    raw["balance"][0]["preferredStock"]=None
    assert not facts(raw)["eligible"]
    raw["balance"][0]["commonStockEquity"]=2000
    assert facts(raw)["basis"]==20
    raw["balance"][0]["commonStockSharesOutstanding"]=None
    assert not facts(raw)["eligible"]
    raw=evidence();raw["income"][0]["epsDiluted"]=0
    assert facts(raw)["basis"]==0 and not facts(raw)["eligible"]


def test_annual_basis_order_duplicates_future_and_units_acknowledgement():
    raw=evidence();raw["income"].reverse()
    assert facts(raw)["as_of"]==max(r["date"] for r in raw["income"])
    raw["income"].append(deepcopy(raw["income"][0]))
    assert any("Duplicate" in s for s in facts(raw)["reasons"])
    raw=evidence();raw["income"][0]["date"]="2099-12-31"
    assert facts(raw)["as_of"]!= "2099-12-31"
    assert not model.prepare(evidence())["eligible"]
    raw=evidence();raw["quote"][0].pop("currency")
    assert facts(raw)["eligible"] and any("profile-reported" in x for x in facts(raw)["warnings"])
    raw["profile"][0].pop("currency")
    assert not facts(raw)["eligible"]


@pytest.mark.parametrize("years,growth,multiple",[(2,.1,20),(5,float("nan"),20),(5,.1,float("inf")),(5,-.5,20),(5,.1,0),(True,.1,20)])
def test_bad_calculation_inputs(years,growth,multiple):
    with pytest.raises(ValueError):model.calculate(facts(),years,growth,multiple)


def test_estimates_remain_separate_and_require_coverage():
    raw=evidence();f=facts(raw)
    assert f["estimates"][0]["currency"]=="USD" and "assumed" in f["estimates"][0]["currency_basis"] and f["basis"]==5
    raw["estimates"][0]["numberAnalystEstimatedEps"]=0
    assert not facts(raw)["estimates"]


def test_provider_bounds_cache_identity_partial_failure_and_refresh(monkeypatch):
    provider._collect.clear();calls=[];raw=evidence()
    def get(url,**kw):
        calls.append((url,kw))
        kind=next(k for k,v in provider.JOBS.items() if v[0].split("/{")[0] in url)
        if kind=="balance":raise TimeoutError("apikey=should-not-leak")
        return deepcopy(raw.get(kind,[]))
    monkeypatch.setattr(provider,"get_fmp_json",get)
    result=provider.load_valuation_evidence(" aapl ","synthetic")
    assert len(calls)==10 and len(result["income"])==2 and not result["balance"]
    assert "should-not-leak" not in json.dumps(result)
    assert all(c[1]["timeout"]==(5,20) for c in calls)
    provider.load_valuation_evidence("AAPL","synthetic");assert len(calls)==10
    provider.load_valuation_evidence("AAPL","synthetic",refresh=True);assert len(calls)==20
    with pytest.raises(ValueError):provider.load_valuation_evidence("../AAPL","synthetic")
    with pytest.raises(ValueError):provider.load_valuation_evidence("AAPL","")
    monkeypatch.setattr(provider,"get_fmp_json",lambda *a,**k:[dict(symbol="MSFT")])
    bad=provider.load_valuation_evidence("AAPL","synthetic",refresh=True)
    assert all(s["status"]=="failed" for s in bad["sources"].values())
    provider._collect.clear()


def test_ai_packet_and_validation():
    raw=evidence();packet=ai.evidence_packet(facts(raw),raw)
    view=answer(packet)
    assert ai.validate(view,packet)["growth_pct"]==10
    assert len(json.dumps(packet))<26000
    for change in (dict(ticker="MSFT"),dict(fingerprint="bad"),dict(evidence_ids=["invented"]),dict(growth_evidence_ids=["profile:0"]),dict(multiple_evidence_ids=["income:0"]),dict(growth_pct=999),dict(confidence="99%")):
        with pytest.raises(ValueError):ai.validate({**view,**change},packet)
    blocked=ai.evidence_packet(model.prepare(raw),raw)
    with pytest.raises(ValueError):ai.validate({**answer(blocked),"growth_pct":10},blocked)
    assert ai.validate(answer(blocked),blocked)["recommendation"]=="Insufficient evidence"


def test_ai_bounded_request_and_no_automatic_retries(monkeypatch):
    calls=[]
    def create(**kw):
        calls.append(kw);p=json.loads(kw["messages"][1]["content"])
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=json.dumps(answer(p)),refusal=None))])
    builder=Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(ai,"build_openai_client",builder)
    raw=evidence();result=ai.generate_assumptions(facts(raw),raw,"synthetic","gpt-5")
    assert result["ai"]["recommendation"]=="Buy" and len(calls)==1
    assert builder.call_args.kwargs==dict(timeout=90,max_retries=0)
    assert calls[0]["max_completion_tokens"]==9000 and calls[0]["response_format"]["type"]=="json_schema"
    def timeout(**kw):raise TimeoutError("untrusted error")
    builder.return_value.chat.completions.create=Mock(side_effect=timeout)
    with pytest.raises(TimeoutError):ai.generate_assumptions(facts(raw),raw,"synthetic","gpt-5")
    assert builder.return_value.chat.completions.create.call_count==1


def test_ai_malformed_incomplete_refusal_no_key(monkeypatch):
    raw=evidence()
    client=Mock();monkeypatch.setattr(ai,"build_openai_client",lambda *a,**k:client)
    for content,finish,refusal,code in [("bad json","stop",None,"format"),("{}","length",None,"length"),("{}","stop","refused","refusal")]:
        client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=content,refusal=refusal))])
        with pytest.raises(ValueError) as failure:ai.generate_assumptions(facts(raw),raw,"synthetic","gpt-5")
        from langgraphagenticai.valuation.errors import failure_state
        assert failure_state(failure.value)["code"]==code
    with pytest.raises(ValueError):ai.generate_assumptions(facts(raw),raw,"","gpt-5")


def test_charts_are_calculated_and_labeled_price_not_total_returns():
    from langgraphagenticai.ui.valuation_charts import scenario_chart,sensitivity_chart
    f=facts();result=model.calculate(f,5,.1,20)
    assert "Hypothetical exit price" in json.dumps(scenario_chart(f,result,5).to_dict())
    heat=sensitivity_chart(f,5,.1,20).to_dict()
    assert "Price return %" in json.dumps(heat) and "Growth %" in json.dumps(heat)


def test_typed_company_handoff_single_company_only():
    from langgraphagenticai.state.research_context import ResearchContext
    from langgraphagenticai.ui.workspace_handoff import queue_handoff,apply_pending_handoff
    state={"chat_history":["saved"]}
    queue_handoff(state,ResearchContext(("msft",),"AI Valuation","analyze","Top Movers"))
    apply_pending_handoff(state)
    assert state["valuation_ticker"]=="MSFT" and state["chat_history"]==["saved"] and "dr_tickers" not in state
    with pytest.raises(ValueError):ResearchContext(("AAPL","MSFT"),"AI Valuation","compare","Research")


UI="from langgraphagenticai.ui.ai_valuation_tab import render_ai_valuation_tab; render_ai_valuation_tab('synthetic','synthetic','gpt-5')"


def _fixture_forward_target(years, growth):
    quoted = (datetime.now(timezone.utc)-timedelta(hours=1)).date()
    target = quoted.replace(year=quoted.year+years)
    remaining = (target-date(datetime.now(timezone.utc).year+1,12,31)).days/365.25
    return f"{6*(1+growth)**remaining*20:,.2f}"


def test_ui_explicit_actions_saved_tickers_review_and_recovery(monkeypatch):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    counts={"load":0,"ai":0};fail={"load":False,"ai":False}
    def load(symbol,*a,**k):
        counts["load"]+=1
        if fail["load"]:raise TimeoutError("apikey=never-show")
        return evidence(symbol)
    def generate(f,raw,*a):
        counts["ai"]+=1
        if fail["ai"]:raise TimeoutError("never-show")
        p=ai.evidence_packet(f,raw)
        return dict(ai=answer(p),packet=p,generated_at=datetime.now(timezone.utc).isoformat(),model="gpt-5")
    monkeypatch.setattr(ui,"load_valuation_evidence",load);monkeypatch.setattr(ui,"generate_assumptions",generate)
    app=AppTest.from_string(UI,default_timeout=30).run()
    assert not app.exception and counts==dict(load=0,ai=0)
    app.button(key="valuation_generate").click().run()
    assert not app.exception and counts==dict(load=1,ai=1)
    assert not app.checkbox and any(m.label=="Bear price target" and "90.00" in m.value for m in app.metric)
    assert any(m.label=="Base price target" and _fixture_forward_target(5,.10) in m.value for m in app.metric)
    assert any("downside" in m.delta for m in app.metric)
    app.selectbox(key="valuation_horizon").set_value(3).run()
    assert any(m.label=="Base price target" and _fixture_forward_target(3,.10) in m.value for m in app.metric)
    assert counts==dict(load=1,ai=1)
    app.text_input(key="valuation_ticker").set_value("MSFT").run()
    assert not app.exception and not any("Growth could" in m.value for m in app.markdown)
    app.text_input(key="valuation_ticker").set_value("AAPL").run()
    assert not app.exception and counts==dict(load=1,ai=1)
    assert any(m.label=="Base price target" for m in app.metric)
    fail["ai"]=True
    app.button(key="valuation_generate").click().run()
    assert any("Previous analysis remains saved" in e.value for e in app.error)
    assert any("Growth could" in m.value for m in app.markdown)
    fail["load"]=True
    app.button(key="valuation_load").click().run()
    assert not app.exception and any("Previous analysis remains saved" in e.value for e in app.error)
    assert "never-show" not in str(app)


def test_main_navigation_passes_shared_settings_without_calls(monkeypatch):
    from langgraphagenticai import main
    from langgraphagenticai.ui import ai_valuation_tab as ui
    captured=[]
    monkeypatch.setattr(main.LoadStreamlitUI,"load_streamlit_ui",lambda self:dict(active_page="AI Valuation",FMP_API_KEY="fmp",OPENAI_API_KEY="openai",selected_model="gpt-5",MARKETAUX_API_KEY=""))
    monkeypatch.setattr(ui,"render_ai_valuation_tab",lambda **kw:captured.append(kw))
    app=AppTest.from_string("from langgraphagenticai.main import load_langgraph_agenticai_app; load_langgraph_agenticai_app()",default_timeout=30).run()
    assert not app.exception and captured==[dict(fmp_api_key="fmp",openai_api_key="openai",model_name="gpt-5")]


def test_executive_prose_hides_source_ids_and_strict_drivers():
    from langgraphagenticai.ui.ai_valuation_tab import _prose
    assert _prose("Margins matter [income:0].") == "Margins matter."
    raw=evidence();packet=ai.evidence_packet(facts(raw),raw)
    with pytest.raises(ValueError):ai.validate({**answer(packet),"growth_pct":True},packet)


def test_missing_keys_and_invalid_ticker_do_not_request_evidence(monkeypatch):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    forbidden=Mock(side_effect=AssertionError("No network"))
    monkeypatch.setattr(ui,"load_valuation_evidence",forbidden)
    app=AppTest.from_string("from langgraphagenticai.ui.ai_valuation_tab import render_ai_valuation_tab; render_ai_valuation_tab()",default_timeout=30).run()
    assert not app.exception and app.button(key="valuation_load").disabled
    app.text_input(key="valuation_ticker").set_value("../AAPL").run()
    assert not app.exception and not app.button and forbidden.call_count==0
    monkeypatch.setattr(ui,"load_valuation_evidence",lambda *a,**k:evidence("PLD","Real Estate"))
    app=AppTest.from_string(UI,default_timeout=30)
    app.session_state["valuation_ticker"]="PLD"
    app.run().button(key="valuation_load").click().run()
    assert not app.exception and any("FFO/AFFO" in w.value for w in app.info)
    assert any("Observed annual P/E"==m.label for m in app.metric)


def test_partial_refresh_retains_original_component_time(monkeypatch):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    first=evidence();new=evidence();new["income"]=[]
    new["sources"]["income"]["status"]="failed"
    load=Mock(side_effect=[first,new])
    monkeypatch.setattr(ui,"load_valuation_evidence",load)
    app=AppTest.from_string(UI,default_timeout=30).run()
    app.button(key="valuation_load").click().run()
    app.button(key="valuation_load").click().run()
    stored=next(iter(app.session_state["valuation_evidence"].values()))
    assert stored["income"]==first["income"]
    assert stored["sources"]["income"]["retrieved_at"]==first["sources"]["income"]["retrieved_at"]
    assert not app.checkbox and not app.exception


def test_compatibility_is_preflight_before_any_model_request(monkeypatch):
    from langgraphagenticai.valuation.errors import ValuationResponseError
    client=Mock(side_effect=AssertionError("Must not build a client"))
    monkeypatch.setattr(ai,"build_openai_client",client)
    raw=evidence()
    with pytest.raises(ValuationResponseError) as failure:
        ai.generate_assumptions(model.prepare(raw),raw,"synthetic","gpt-5")
    assert failure.value.code=="compatibility" and not client.called


@pytest.mark.parametrize("status,expected",[(400,"request"),(401,"authentication"),(403,"model_access"),(404,"model_access"),(429,"rate_limit"),(500,"provider")])
def test_sdk_errors_are_actionable_and_never_echo_response_bodies(status,expected):
    import httpx
    from openai import APIStatusError
    from langgraphagenticai.valuation.errors import failure_state
    request=httpx.Request("POST","https://api.openai.com/v1/chat/completions",headers={"Authorization":"Bearer sk-never-render-this-credential"})
    response=httpx.Response(status,request=request)
    error=APIStatusError("apikey=never-show private model response",response=response,body={"code":"invalid_json_schema","param":"response_format","message":"sk-never-render-this-credential"})
    result=failure_state(error)
    assert result["code"]==expected and result["http_status"]==status
    assert result["api_code"]=="invalid_json_schema" and result["parameter"]=="response_format"
    assert "never" not in json.dumps(result) and "private model" not in json.dumps(result)


def test_failure_categories_preserve_distinct_validation_reasons():
    from langgraphagenticai.valuation.errors import failure_state,ValuationResponseError
    for code in ("identity","citations","eligibility","refusal","length","budget"):
        assert failure_state(ValuationResponseError(code))["code"]==code
    assert failure_state(TimeoutError("apikey=never-show"))["code"]=="timeout"
    assert failure_state(ValueError("apikey=never-show"))["code"]=="format"
    assert "never-show" not in str(failure_state(RuntimeError("apikey=never-show")))


def test_ui_persists_safe_failure_until_success(monkeypatch):
    import httpx
    from openai import BadRequestError
    from langgraphagenticai.ui import ai_valuation_tab as ui
    raw=evidence("NVDA");count={"ai":0};fail={"active":True}
    monkeypatch.setattr(ui,"load_valuation_evidence",lambda *a,**k:raw)
    def generate(f,raw,*args):
        count["ai"]+=1
        if fail["active"]:
            response=httpx.Response(400,request=httpx.Request("POST","https://api.openai.com/v1/chat/completions"))
            raise BadRequestError("apikey=never-show",response=response,body={"code":"invalid_json_schema","param":"response_format"})
        p=ai.evidence_packet(f,raw)
        return dict(ai=answer(p),packet=p,model="gpt-5",generated_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(ui,"generate_assumptions",generate)
    app=AppTest.from_string(UI,default_timeout=30)
    app.session_state["valuation_ticker"]="NVDA"
    app.run()
    assert count["ai"]==0 and not app.button(key="valuation_generate").disabled
    app.button(key="valuation_generate").click().run()
    assert not app.exception and count["ai"]==1
    assert any("OpenAI rejected the valuation request settings" in e.value for e in app.error)
    saved=next(iter(app.session_state["valuation_failures"].values()))
    assert saved["api_code"]=="invalid_json_schema" and saved["code"]=="request"
    app.selectbox(key="valuation_horizon").set_value(3).run()
    assert app.error and count["ai"]==1
    app.text_input(key="valuation_ticker").set_value("MSFT").run()
    assert not app.error and count["ai"]==1
    app.text_input(key="valuation_ticker").set_value("NVDA").run()
    assert app.error and count["ai"]==1
    fail["active"]=False
    app.button(key="valuation_generate").click().run()
    assert not app.exception and not app.error and count["ai"]==2
    assert not app.session_state["valuation_failures"]
    assert "never-show" not in str(app)


def rich_evidence(symbol="AAPL"):
    import pandas as pd
    raw=evidence(symbol)
    year=datetime.now(timezone.utc).year-1
    raw["income"]=[dict(symbol=symbol,date=f"{year-i}-12-31",period="FY",fiscalYear=year-i,reportedCurrency="USD",epsDiluted=5/(1.1**i),weightedAverageShsOutDil=100.,netIncome=500/(1.1**i),revenue=1000/(1.08**i),grossProfit=550/(1.08**i),operatingIncome=300/(1.08**i)) for i in range(5)]
    raw["cashflow"]=[dict(symbol=symbol,date=f"{year}-12-31",period="FY",reportedCurrency="USD",freeCashFlow=200.)]
    raw["estimates"]=[dict(symbol=symbol,date=f"{year+2}-12-31",epsAvg=6.,revenueAvg=1200.,numAnalystsEps=12)]
    raw["ratios"]=[dict(symbol=symbol,priceToEarningsRatioTTM=18.,grossProfitMarginTTM=.55,operatingProfitMarginTTM=.30,netProfitMarginTTM=.25,debtToEquityRatioTTM=.4)]
    raw["metrics"]=[dict(symbol=symbol,returnOnInvestedCapitalTTM=.2,returnOnEquityTTM=.3,evToEBITDATTM=15.)]
    raw["targets"]=[dict(symbol=symbol,lastMonthAvgPriceTarget=110.,lastMonthCount=5,lastQuarterAvgPriceTarget=120.,lastQuarterCount=10)]
    dates=pd.bdate_range(end=datetime.now(timezone.utc).date()-timedelta(days=1),periods=280)
    raw["history"]=[dict(symbol=symbol,date=d.date().isoformat(),adjClose=70+30*i/279,close=70+30*i/279) for i,d in enumerate(dates)]
    return raw


def test_rich_metrics_reuse_app_calculations_and_forecast_aliases():
    from langgraphagenticai.valuation.metrics import company_metrics
    raw=rich_evidence();f=model.prepare(raw,use_disclosed_assumptions=True)
    assert f["eligible"] and f["estimates"][0]["eps"]==6
    assert f["estimates"][0]["analysts"]==12 and f["compatibility_basis"]=="disclosed scenario assumptions"
    context=company_metrics(raw,f);m=context["fundamentals"]
    assert m["pe_ttm"]["value"]==18 and m["pe_forward"]["value"]==pytest.approx(100/6)
    assert m["annual_net_margin"]["value"]==.5
    assert m["annual_fcf_margin"]["value"]==.2
    assert m["annual_per_share_growth"]["value"]==pytest.approx(.1)
    assert m["revenue_cagr_3y"]["value"]==pytest.approx(.08)
    assert context["technicals"]["price_basis"]=="adjClose" and "rsi_14" in context["technicals"]
    assert "series" not in context["technicals"] and len(context["analyst_targets"])==2
    packet=ai.evidence_packet(f,raw)
    assert len(json.dumps(packet))<36000
    assert any(r["id"]=="metric:pe_forward" for r in packet["evidence"])
    assert any(r["id"]=="technicals:0" for r in packet["evidence"])


@pytest.mark.parametrize("eps_key,count_key",[("epsAvg","numAnalystsEps"),("estimatedEpsAvg","numberAnalystEstimatedEps"),("estimatedEps","numberAnalystsEstimatedEps")])
def test_forward_aliases_and_unknown_currency_are_disclosed_not_discarded(eps_key,count_key):
    raw=evidence();stamp=raw["estimates"][0]["date"]
    raw["quote"][0].pop("currency")
    raw["estimates"]=[dict(symbol="AAPL",date=stamp,**{eps_key:7.,count_key:10})]
    f=model.prepare(raw,use_disclosed_assumptions=True)
    assert f["eligible"] and f["estimates"][0]["eps"]==7
    assert "assumed" in f["estimates"][0]["currency_basis"]
    raw["quote"][0]["currency"]="EUR"
    assert not model.prepare(raw,use_disclosed_assumptions=True)["eligible"]


def test_ai_selects_three_independent_cases_and_calculations_match():
    raw=rich_evidence();f=facts(raw);p=ai.evidence_packet(f,raw);view=answer(p)
    valid=ai.validate(view,p)
    result=model.calculate_ai_cases(f,5,valid["scenarios"])
    assert result["Bear"]["target"]==75 and result["Bear"]["price_return"]==-.25
    assert result["Base"]["target"]==pytest.approx(161.051)
    assert result["Bull"]["target"]==pytest.approx(311.04)
    assert result["Base"]["cagr"]==pytest.approx(.1)
    for mutate in (lambda v:v.update(scenarios=[]),lambda v:v["scenarios"][0].update(name="Base"),lambda v:v["scenarios"][0].update(growth_pct=60.,terminal_multiple=300.),lambda v:v["scenarios"][0].update(evidence_ids=["unknown:0"]),lambda v:v.update(growth_pct=11.)):
        invalid=deepcopy(view);mutate(invalid)
        with pytest.raises(ValueError):ai.validate(invalid,p)


def test_forecast_currency_and_fiscal_mismatch_still_excluded():
    raw=evidence();raw["estimates"][0]["reportedCurrency"]="EUR"
    assert not facts(raw)["estimates"]
    raw=evidence();raw["estimates"][0]["date"]=f"{datetime.now(timezone.utc).year+1}-06-30"
    assert not facts(raw)["estimates"]


def test_legacy_saved_shell_upgrades_explicitly_and_prose_has_no_artifacts(monkeypatch):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    assert ui._prose("Demand improved (income:0, income:1).") == "Demand improved."
    assert ui._prose("Growth supports value [metric:annual_net_margin, income:0].") == "Growth supports value."
    load=Mock(return_value=rich_evidence())
    monkeypatch.setattr(ui,"load_valuation_evidence",load)
    def generate(f,r,*args):
        p=ai.evidence_packet(f,r)
        return dict(ai=answer(p),packet=p,model="gpt-5",generated_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(ui,"generate_assumptions",generate)
    app=AppTest.from_string(UI,default_timeout=30)
    from hashlib import sha256
    scope=sha256(b"synthetic").hexdigest()[:16];key=f"{scope}:AAPL"
    legacy=evidence();legacy.pop("evidence_version")
    app.session_state["valuation_evidence"]={key:legacy}
    app.session_state["valuation_scenarios"]={key:dict(signature="legacy",result={})}
    app.run()
    assert not app.exception and not load.called
    app.button(key="valuation_generate").click().run()
    assert not app.exception and load.call_count==1
    assert any(m.label=="Base price target" for m in app.metric)


def test_provider_historical_envelope_identity_and_field_aliases(monkeypatch):
    provider._collect.clear()
    def get(url,**kwargs):
        if "historical-price-full" in url:
            return dict(symbol="AAPL",historical=[dict(date="2026-01-02",adjClose=100.,close=101.)])
        if "analyst-estimates" in url:
            return [dict(symbol="AAPL",date=f"{datetime.now(timezone.utc).year+1}-12-31",epsAvg=7.,numAnalystsEps=15)]
        return []
    monkeypatch.setattr(provider,"get_fmp_json",get)
    raw=provider.load_valuation_evidence("AAPL","synthetic",refresh=True)
    assert raw["history"][0]["symbol"]=="AAPL" and raw["history"][0]["adjClose"]==100
    assert raw["estimates"][0]["epsAvg"]==7 and raw["estimates"][0]["numAnalystsEps"]==15
    monkeypatch.setattr(provider,"get_fmp_json",lambda url,**k:dict(symbol="AAPL",historical=[dict(symbol="MSFT",date="2026-01-02",adjClose=100)]))
    raw=provider.load_valuation_evidence("AAPL","synthetic",refresh=True)
    assert not raw["history"] and raw["sources"]["history"]["status"]=="failed"
    provider._collect.clear()


def test_scenario_adjustments_recalculate_locally_and_preserve_ai_call_count(monkeypatch):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    count={"ai":0,"load":0}
    def load(symbol,*a,**k):count["load"]+=1;return rich_evidence(symbol)
    def generate(f,r,*args):
        count["ai"]+=1;p=ai.evidence_packet(f,r)
        return dict(ai=answer(p),packet=p,model="gpt-5",generated_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(ui,"load_valuation_evidence",load);monkeypatch.setattr(ui,"generate_assumptions",generate)
    app=AppTest.from_string(UI,default_timeout=30).run()
    app.button(key="valuation_generate").click().run()
    base=next(n for n in app.number_input if n.label=="Base annual growth (%)")
    base.set_value(12.).run()
    app.button(key="valuation_calculate").click().run()
    assert not app.exception and count==dict(ai=1,load=1)
    assert any(m.label=="Base price target" and _fixture_forward_target(5,.12) in m.value for m in app.metric)
    assert any("not been re-reviewed by AI" in notice.value for notice in app.info)
    bad=next(n for n in app.number_input if n.label=="Bear annual growth (%)")
    bad.set_value(60.).run()
    app.button(key="valuation_calculate").click().run()
    assert not app.exception and app.error and count==dict(ai=1,load=1)
    assert any(m.label=="Base price target" and _fixture_forward_target(5,.12) in m.value for m in app.metric)


def test_derived_metric_references_match_the_selected_forward_year():
    from langgraphagenticai.valuation.metrics import company_metrics
    raw=rich_evidence();row=deepcopy(raw["estimates"][0]);row["date"]=f"{datetime.now(timezone.utc).year+2}-12-31";row["epsAvg"]=8.
    raw["estimates"].insert(0,row)
    context=company_metrics(raw,facts(raw))
    assert context["fundamentals"]["pe_forward"]["source_ids"]==["estimates:1"]
    assert context["fundamentals"]["annual_fcf_margin"]["source_ids"]==["income:0","cashflow:0"]


def test_metric_and_forward_citations_support_cases_without_raw_prefixes():
    raw=rich_evidence();packet=ai.evidence_packet(facts(raw),raw);view=answer(packet)
    view["growth_evidence_ids"]=["metric:annual_per_share_growth"]
    view["multiple_evidence_ids"]=["metric:pe_ttm"]
    for case in view["scenarios"]:
        case["evidence_ids"]=["metric:annual_net_margin","metric:pe_forward"]
    assert ai.validate(view,packet)["scenarios"]
    view["growth_evidence_ids"]=["estimates:0"]
    view["multiple_evidence_ids"]=["metric:pe_forward"]
    assert ai.validate(view,packet)["growth_pct"]==10


def test_request_schema_uses_only_supplied_role_appropriate_ids():
    from langgraphagenticai.valuation.citations import schema_for_packet
    raw=rich_evidence();packet=ai.evidence_packet(facts(raw),raw)
    schema=schema_for_packet(ai.ValuationView.model_json_schema(),packet)
    props=schema["properties"];ids={r["id"] for r in packet["evidence"]}
    assert set(props["evidence_ids"]["items"]["enum"])==ids
    assert "metric:annual_net_margin" in props["growth_evidence_ids"]["items"]["enum"]
    assert "metric:pe_forward" in props["multiple_evidence_ids"]["items"]["enum"]
    assert "profile:0" not in props["multiple_evidence_ids"]["items"]["enum"]
    assert props["growth_evidence_ids"]["minItems"]==1 and props["scenarios"]["minItems"]==3
    scenario_ids=schema["$defs"]["ScenarioDriver"]["properties"]["evidence_ids"]["items"]["enum"]
    assert "technicals:0" not in scenario_ids and "profile:0" not in scenario_ids


def test_unresolved_metric_and_technical_only_citations_still_fail_with_safe_reason():
    from langgraphagenticai.valuation.errors import failure_state
    from langgraphagenticai.valuation.citations import CitationFailure
    raw=rich_evidence();packet=ai.evidence_packet(facts(raw),raw);view=answer(packet)
    view["growth_evidence_ids"]=["metric:annual_net_margin"]
    record=next(r for r in packet["evidence"] if r["id"]=="metric:annual_net_margin")
    record["fields"]["source_ids"]=["income:999"]
    with pytest.raises(CitationFailure) as failure:ai.validate(view,packet)
    status=failure_state(failure.value)
    assert status["source_check"]["field"]=="growth_evidence_ids"
    assert status["source_check"]["reason"]=="missing_growth_support"
    record["fields"]["source_ids"]=[record["id"]]
    with pytest.raises(CitationFailure):ai.validate(view,packet)
    view=answer(packet);view["scenarios"][0]["evidence_ids"]=["technicals:0"]
    with pytest.raises(CitationFailure) as failure:ai.validate(view,packet)
    assert failure.value.diagnostics["reason"]=="missing_financial_support"
    view=answer(packet);view["evidence_ids"]=["apikey=never-render-this"]
    with pytest.raises(CitationFailure) as failure:ai.validate(view,packet)
    assert failure.value.diagnostics["unknown_source_count"]==1
    assert "never-render" not in json.dumps(failure_state(failure.value))


def test_coverage_table_shows_actual_values_bases_and_correct_quote_currency():
    from langgraphagenticai.valuation.coverage import coverage_rows,display_value
    raw=rich_evidence();packet=ai.evidence_packet(facts(raw),raw);rows=coverage_rows(packet)
    assert {r["Category"] for r in rows}=={"Fundamentals","Valuation","Technicals","Analyst expectations"}
    assert next(r for r in rows if r["Metric"]=="Net margin (annual)")["Value"]=="50.0%"
    assert next(r for r in rows if r["Metric"]=="P/E (FWD)")["Value"]=="16.67x"
    assert display_value(0.,"fraction")=="0.0%"
    packet["quote_currency"]="EUR"
    assert next(r for r in coverage_rows(packet) if r["Metric"]=="Current price")["Value"]=="100.00 EUR"


def test_real_generation_path_accepts_metric_backed_response(monkeypatch):
    calls=[]
    def create(**kwargs):
        calls.append(kwargs);packet=json.loads(kwargs["messages"][1]["content"])
        view=answer(packet);view["growth_evidence_ids"]=["metric:annual_per_share_growth"];view["multiple_evidence_ids"]=["metric:pe_ttm"]
        for case in view["scenarios"]:case["evidence_ids"]=["metric:annual_net_margin","metric:pe_forward"]
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=json.dumps(view),refusal=None))])
    monkeypatch.setattr(ai,"build_openai_client",lambda *a,**k:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    raw=rich_evidence();result=ai.generate_assumptions(facts(raw),raw,"synthetic","gpt-5")
    assert len(calls)==1 and result["ai"]["scenarios"][0]["evidence_ids"]==["metric:annual_net_margin","metric:pe_forward"]
    assert "enum" in calls[0]["response_format"]["json_schema"]["schema"]["properties"]["evidence_ids"]["items"]


def test_actual_openai_sdk_serialization_and_metric_only_response(monkeypatch):
    import httpx
    from openai import OpenAI
    requests_seen=[]
    transport_client=httpx.Client()
    def send(request,**kwargs):
        requests_seen.append(request)
        payload=json.loads(request.content)
        packet=json.loads(payload["messages"][1]["content"])
        schema=payload["response_format"]["json_schema"]["schema"]
        assert "metric:annual_per_share_growth" in schema["properties"]["growth_evidence_ids"]["items"]["enum"]
        view=answer(packet);view["growth_evidence_ids"]=["metric:annual_per_share_growth"];view["multiple_evidence_ids"]=["metric:pe_ttm"]
        for case in view["scenarios"]:case["evidence_ids"]=["metric:annual_net_margin","metric:pe_forward"]
        return httpx.Response(200,request=request,json={"id":"chatcmpl-fixture","object":"chat.completion","created":1,"model":"gpt-5","choices":[{"index":0,"finish_reason":"stop","message":{"role":"assistant","content":json.dumps(view),"refusal":None}}],"usage":{"prompt_tokens":100,"completion_tokens":100,"total_tokens":200}})
    # Instance-only in-memory response replaces the suite's forbidden send; no socket/HTTP transport runs.
    transport_client.send=send
    client=OpenAI(api_key="synthetic",http_client=transport_client,max_retries=0)
    monkeypatch.setattr(ai,"build_openai_client",lambda *a,**k:client)
    raw=rich_evidence()
    try:
        result=ai.generate_assumptions(facts(raw),raw,"synthetic","gpt-5")
        assert len(requests_seen)==1 and result["ai"]["multiple_evidence_ids"]==["metric:pe_ttm"]
    finally:
        client.close()


def test_forecast_source_role_matches_value_coverage_and_currency_not_just_date():
    from langgraphagenticai.valuation.citations import source_roles
    raw=rich_evidence();packet=ai.evidence_packet(facts(raw),raw)
    original=next(r for r in packet["evidence"] if r["id"]=="estimates:0")
    assert "growth" in source_roles(packet)["estimates:0"]
    for field,value in (("epsAvg",99.),("numAnalystsEps",0),("reportedCurrency","EUR")):
        bad=deepcopy(original);bad["id"]="estimates:invalid";bad["fields"][field]=value
        packet["evidence"].append(bad)
        assert not source_roles(packet)["estimates:invalid"]
        packet["evidence"].pop()


def test_dated_projection_uses_supported_consensus_and_quote_relative_exit():
    from langgraphagenticai.valuation.projection import projection_basis
    f=dict(eligible=True,basis=4.9,price=214.13,method="P/E",currency="USD",
           as_of="2025-01-25",quote_as_of="2026-10-16T20:00:00+00:00",
           projection_method="dated-consensus-v1",forecast_anchor_eligible=True,
           estimates=[dict(date="2027-01-25",eps=8.,analysts=30.,currency="USD"),
                      dict(date="2028-01-25",eps=10.,analysts=20.,currency="USD")])
    anchor=projection_basis(f,5)
    remaining=(date(2031,10,16)-date(2027,1,25)).days/365.25
    assert anchor["value"]==8 and anchor["date"]=="2027-01-25"
    assert anchor["target_date"]=="2031-10-16" and anchor["years"]==pytest.approx(remaining)
    row=model.calculate(f,5,.12,25)["Base"]
    expected=8*1.12**remaining*25
    assert row["target"]==pytest.approx(expected)
    assert row["end_basis"]==pytest.approx(expected/25)
    assert row["price_return"]==pytest.approx(expected/214.13-1)
    assert row["cagr"]==pytest.approx((expected/214.13)**.2-1)
    # The previous method used old EPS and exactly five growth years.
    legacy=model.calculate({**f,"projection_method":"legacy-annual"},5,.12,25)["Base"]
    assert legacy["target"]==pytest.approx(4.9*1.12**5*25)
    assert row["target"]!=legacy["target"]


@pytest.mark.parametrize("change", [dict(analysts=2.),dict(currency="EUR"),dict(eps=-1.),dict(date="2030-01-25")])
def test_dated_projection_rejects_sparse_incompatible_or_distant_anchor(change):
    from langgraphagenticai.valuation.projection import projection_basis
    f=dict(basis=5.,price=100.,method="P/E",currency="USD",as_of="2025-12-31",
           quote_as_of="2026-10-16T20:00:00+00:00",projection_method="dated-consensus-v1",forecast_anchor_eligible=True,
           estimates=[dict(date="2027-12-31",eps=8.,analysts=12.,currency="USD",**{})])
    f["estimates"][0].update(change)
    anchor=projection_basis(f,5)
    assert anchor["kind"]=="historical annual"
    assert anchor["years"]==pytest.approx((date(2031,10,16)-date(2025,12,31)).days/365.25)


def test_dated_projection_bank_duplicate_forecast_and_leap_year_contracts():
    from langgraphagenticai.valuation.projection import projection_basis
    f=dict(basis=5.,method="P/E",currency="USD",as_of="2023-12-31",
           quote_as_of="2024-02-29T20:00:00+00:00",projection_method="dated-consensus-v1",forecast_anchor_eligible=True,
           estimates=[dict(date="2024-12-31",eps=8.,analysts=12.,currency="USD")])
    assert projection_basis(f,3)["target_date"]=="2027-02-28"
    assert projection_basis({**f,"method":"P/B"},3)["kind"]=="historical annual"
    f["estimates"]*=2
    assert projection_basis(f,3)["kind"]=="historical annual"


def test_model_request_includes_exact_projection_and_forecast_growth_guides(monkeypatch):
    from langgraphagenticai.valuation.projection import consensus_growth_path
    raw=rich_evidence()
    raw["estimates"].append({**raw["estimates"][0],"date":f"{datetime.now(timezone.utc).year+2}-12-31","epsAvg":9.})
    f=model.prepare(raw,acknowledge_units=True,dated_projection=True)
    p=ai.evidence_packet(f,raw)
    assert p["projection_bases"]["5"]["kind"]=="annual consensus forecast"
    assert p["consensus_growth_path"]==consensus_growth_path(f)
    assert p["consensus_growth_path"][0]["implied_annual_growth_pct"]==pytest.approx(50.,abs=.2)
    sent={}
    def create(**kw):
        sent.update(kw)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=json.dumps(answer(p)),refusal=None))])
    monkeypatch.setattr(ai,"build_openai_client",lambda *a,**k:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    result=ai.generate_assumptions(f,raw,"synthetic","gpt-5")
    assert result["packet"]["projection_bases"]==p["projection_bases"]
    assert "growth AFTER that anchor" in sent["messages"][0]["content"]


def test_stale_or_undated_forecasts_do_not_anchor_new_price_targets():
    from langgraphagenticai.valuation.projection import projection_basis
    raw=rich_evidence()
    for timestamp in (None,(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()):
        raw["sources"]["estimates"]["retrieved_at"]=timestamp
        f=model.prepare(raw,acknowledge_units=True,dated_projection=True)
        assert f["eligible"] and not f["forecast_anchor_eligible"]
        assert projection_basis(f,5)["kind"]=="historical annual"
        assert any("excluded from the numeric earnings anchor" in w for w in f["warnings"])


def test_growth_units_crosscheck_twenty_percent_and_genuine_small_growth():
    p=ai.evidence_packet(facts(),evidence());view=answer(p)
    assert ai.validate(view,p)["scenarios"][2]["annual_growth_decimal"]==.20
    # Reproduce the plausible 100x unit error without silently guessing intent.
    view["scenarios"][2]["growth_pct"]=.20
    with pytest.raises(ai.ValuationResponseError) as err:ai.validate(view,p)
    assert err.value.code=="growth_units"
    # A genuinely low-growth, consistently represented scenario remains valid.
    for case,growth in zip(view["scenarios"],(.1,.2,.3)):
        case["growth_pct"]=growth;case["annual_growth_decimal"]=growth/100
    view["growth_pct"]=.2
    assert ai.validate(view,p)["growth_pct"]==.2


def test_growth_schema_describes_units_and_requires_decimal_confirmation():
    p=ai.evidence_packet(facts(),evidence())
    schema=ai.schema_for_packet(ai.ValuationView.model_json_schema(),p)
    driver=schema["$defs"]["ScenarioDriver"]
    assert "annual_growth_decimal" in driver["required"]
    assert "20.0 means 20%" in driver["properties"]["growth_pct"]["description"]
    assert "growth_pct / 100" in driver["properties"]["annual_growth_decimal"]["description"]


def test_doubling_requirements_reproduce_screenshot_without_forcing_targets():
    from langgraphagenticai.valuation.diagnostics import target_requirements
    f=dict(eligible=True,basis=4.9,price=214.13,method="P/E",currency="USD",
           as_of="2026-01-25",quote_as_of="2026-10-16T20:00:00+00:00",
           projection_method="dated-consensus-v1",forecast_anchor_eligible=True,
           estimates=[dict(date="2027-01-25",eps=9.28,analysts=32.,currency="USD")])
    cases=[dict(name=n,terminal_multiple=m) for n,m in (("Bear",18.),("Base",22.),("Bull",25.))]
    rows=target_requirements(f,cases,5)
    assert all(r["Hypothetical target"]==pytest.approx(428.26) for r in rows)
    expected_years=(date(2031,10,16)-date(2027,1,25)).days/365.25
    required=(428.26/22/9.28)**(1/expected_years)-1
    assert rows[1]["Required exit EPS / BVPS"]==pytest.approx(428.26/22)
    assert rows[1]["Required annual growth (%)"]==pytest.approx(required*100)
    assert 16 < required*100 < 18
    # Recalculate the target from independently derived required earnings growth.
    assert model.calculate(f,5,required,22)["Base"]["target"]==pytest.approx(428.26)
    assert model.calculate(f,5,.002,22)["Base"]["target"]==pytest.approx(9.28*1.002**expected_years*22)
    assert model.calculate(f,5,.20,22)["Base"]["target"]>428.26


def test_growth_diagnostics_flag_discrepancy_but_do_not_rewrite_assumptions():
    from langgraphagenticai.valuation.diagnostics import driver_diagnostics
    raw=rich_evidence();raw["estimates"].append({**raw["estimates"][0],"date":f"{datetime.now(timezone.utc).year+2}-12-31","epsAvg":9.})
    f=model.prepare(raw,acknowledge_units=True,dated_projection=True)
    cases=answer(ai.evidence_packet(f,raw))["scenarios"]
    for c,g in zip(cases,(.1,.2,.3)):c.update(growth_pct=g,annual_growth_decimal=g/100)
    original=deepcopy(cases)
    diagnostic=driver_diagnostics(f,cases,5)
    assert diagnostic["near_flat"] and cases==original
    assert diagnostic["forecast_comparison"]["implied_annual_growth_pct"]==pytest.approx(50.,abs=.2)
    for c,g in zip(cases,(10.,20.,30.)):c.update(growth_pct=g,annual_growth_decimal=g/100)
    assert not driver_diagnostics(f,cases,5)["near_flat"]


def test_ui_shows_growth_reconciliation_and_reverse_target_without_new_calls(monkeypatch):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    count={"load":0,"ai":0};bad={"units":False}
    def load(symbol,*a,**k):
        count["load"]+=1;raw=rich_evidence(symbol)
        raw["estimates"].append({**raw["estimates"][0],"date":f"{datetime.now(timezone.utc).year+2}-12-31","epsAvg":9.})
        return raw
    def generate(f,raw,*a):
        count["ai"]+=1;p=ai.evidence_packet(f,raw);view=answer(p)
        for c,g in zip(view["scenarios"],(.1,.2,.3)):c.update(growth_pct=g,annual_growth_decimal=g/100)
        view["growth_pct"]=.2
        if bad["units"]:view["scenarios"][0]["annual_growth_decimal"]=.1
        return dict(ai=ai.validate(view,p),packet=p,model="gpt-5",generated_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(ui,"load_valuation_evidence",load);monkeypatch.setattr(ui,"generate_assumptions",generate)
    app=AppTest.from_string(UI,default_timeout=30).run()
    app.button(key="valuation_generate").click().run()
    assert not app.exception and count==dict(load=1,ai=1)
    assert any("All three cases assume at most 1%" in w.value for w in app.warning)
    assert any("Growth rationale:" in m.value for m in app.markdown)
    assert any(e.label=="What would it take for the stock to double?" for e in app.expander)
    assert any("Required annual growth (%)" in df.value.columns for df in app.dataframe)
    app.selectbox(key="valuation_horizon").set_value(3).run()
    assert not app.exception and count==dict(load=1,ai=1)

    previous=next(m.value for m in app.metric if m.label=="Base price target")
    bad["units"]=True
    app.button(key="valuation_generate").click().run()
    assert not app.exception and count==dict(load=1,ai=2)
    assert any("inconsistent growth units" in e.value and "Previous analysis remains saved" in e.value for e in app.error)
    assert next(m.value for m in app.metric if m.label=="Base price target")==previous


def test_duplicate_future_year_is_excluded_from_growth_comparison():
    from langgraphagenticai.valuation.projection import consensus_growth_path
    raw=rich_evidence();later={**raw["estimates"][0],"date":f"{datetime.now(timezone.utc).year+2}-12-31","epsAvg":9.}
    raw["estimates"].extend([later,{**later,"epsAvg":12.}])
    f=model.prepare(raw,acknowledge_units=True,dated_projection=True)
    assert consensus_growth_path(f)==[]


@pytest.mark.parametrize("factor", [0.,-1.,float("nan"),float("inf")])
def test_reverse_target_rejects_invalid_price_factors(factor):
    from langgraphagenticai.valuation.diagnostics import target_requirements
    with pytest.raises(ValueError):target_requirements(facts(),[],5,price_factor=factor)
