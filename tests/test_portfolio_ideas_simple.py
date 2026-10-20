from copy import deepcopy
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from langgraphagenticai.portfolio_ideas.ranking import build_ranked,rank_companies
from langgraphagenticai.portfolio_ideas.simple_ai import refine
from langgraphagenticai.portfolio_ideas.reuse import company_inputs
from langgraphagenticai.providers.company_evidence import credential_scope
from langgraphagenticai.providers import portfolio_ideas as provider


def data():
    now=datetime.now(timezone.utc).isoformat()
    return dict(provider="FMP",retrieved_at=now,news_basis="fixture",warnings=[],rows={s:dict(symbol=s,company=s,sector=sector,price=100,currency="USD",as_of=now,fundamentals=dict(pe_ttm=pe,net_margin_ttm=margin,debt_equity_ttm=.5),technicals=dict(distance_sma200_pct=distance,distance_sma50_pct=-distance),news=[],gaps=[],sources={},evidence_refs={}) for s,sector,pe,margin,distance in [("AAPL","Technology",20,.2,10),("MSFT","Technology",30,.3,20),("JPM","Financial Services",10,.2,0),("XOM","Energy",15,.1,-10)]})


def sdk(monkeypatch,content="",finish="stop",error=None):
    from langgraphagenticai.portfolio_ideas import simple_ai
    call=Mock(side_effect=error,return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=content,refusal=None))],usage=SimpleNamespace(prompt_tokens=100,completion_tokens=50)))
    monkeypatch.setattr(simple_ai,"build_openai_client",Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=call)))))
    return call


def test_local_baskets_no_ai_and_reproducible_ranks():
    result=build_ranked("A quality portfolio",list(data()["rows"]),data())
    assert result["model_calls"]==0 and all(len(v["picks"])==4 for v in result["perspectives"].values())
    assert all(sum(p["weight_pct"] for p in v["picks"])==pytest.approx(100) for v in result["perspectives"].values())
    scores=result["ranking"]
    assert scores["AAPL"]["features"]["value"]==1 and scores["MSFT"]["features"]["value"]==0
    assert scores["AAPL"]["features"]["quality"]==0 and scores["MSFT"]["features"]["quality"]==1
    assert scores["JPM"]["features"]["resilience"] is None


@pytest.mark.parametrize("finish,content",[("length",""),("stop","not a portfolio"),("stop","{}")])
def test_incomplete_or_malformed_ai_cannot_erase_portfolios(monkeypatch,finish,content):
    base=build_ranked("Research",list(data()["rows"]),data(),"gpt-5")
    call=sdk(monkeypatch,content,finish)
    out=refine(base,"fake","gpt-5")
    assert out["perspectives"]==base["perspectives"] and out["model_calls"]==1
    assert out["ai_status"] in {"incomplete","format_unusable"}
    assert "response_format" not in call.call_args.kwargs
    assert call.call_args.kwargs["reasoning_effort"]=="low" and call.call_args.kwargs["max_completion_tokens"]==2400


def test_optional_ai_refines_prompt_without_large_schema(monkeypatch):
    base=build_ranked("Research",list(data()["rows"]),data(),"gpt-5")
    text="\n".join(p+" | MSFT, AAPL, JPM | Focus on supplied quality and diversification." for p in base["perspectives"])
    call=sdk(monkeypatch,text)
    out=refine(base,"fake","gpt-5")
    assert out["ai_status"]=="complete" and call.call_count==1
    for view in out["perspectives"].values():
        assert len(view["picks"])==3 and sum(p["weight_pct"] for p in view["picks"])==pytest.approx(100)
        assert view["selection_basis"]=="AI-refined shortlist"


def test_partial_ai_unknown_symbols_or_duplicate_names_preserve_local(monkeypatch):
    base=build_ranked("Research",list(data()["rows"]),data())
    sdk(monkeypatch,"Warren | AAPL, MSFT, JPM | Quality\nGeorge | AAPL, MSFT, FAKE | Unknown\nRay | AAPL, MSFT, JPM | One\nRay | AAPL, MSFT, JPM | Two")
    out=refine(base,"fake","gpt-4.1")
    assert out["ai_status"]=="partial" and len(out["perspectives"]["Warren"]["picks"])==3
    assert out["perspectives"]["George"]==base["perspectives"]["George"] and out["perspectives"]["Ray"]==base["perspectives"]["Ray"]


def test_sdk_error_or_missing_key_safe_and_never_retry(monkeypatch):
    base=build_ranked("Research",list(data()["rows"]),data())
    call=sdk(monkeypatch,error=RuntimeError("apikey=private"))
    out=refine(base,"fake","gpt-5")
    assert out["perspectives"]==base["perspectives"] and out["ai_status"]=="failed" and "private" not in str(out) and call.call_count==1
    refine(base,"","gpt-5");assert call.call_count==1


def test_missing_values_and_zero_never_default_to_fabricated_quality():
    value=data();value["rows"]["AAPL"]["fundamentals"]["net_margin_ttm"]=0
    value["rows"]["MSFT"]["fundamentals"]={};value["rows"]["MSFT"]["technicals"]={}
    ranked=rank_companies(value)
    assert "MSFT" not in ranked and ranked["AAPL"]["features"]["quality"]==.5


def test_raw_cross_workspace_reuse_and_no_summary_bridge():
    scope=credential_scope("key");now=datetime.now(timezone.utc).isoformat()
    source=dict(symbol="AAPL",profile=[dict(symbol="AAPL",currency="USD")],ratios=[dict(symbol="AAPL",netProfitMarginTTM=.2)],quote=[dict(symbol="AAPL",price=100,timestamp=datetime.now(timezone.utc).timestamp()-60)],sources={k:dict(provider="FMP",status="available",retrieved_at=now) for k in ("profile","ratios","quote")})
    state=dict(valuation_evidence={scope+":AAPL":source},equity_report_payload=dict(executive_summary="Do not use opinions as facts"))
    out=company_inputs(state,["AAPL"],"key")
    assert out["AAPL"]["quote"][0]["price"]==100 and "Do not use" not in str(out)
    assert company_inputs(state,["AAPL"],"other")=={}


def test_equity_quote_capture_retains_moving_averages_without_scored_summary():
    from langgraphagenticai.providers.company_evidence import capture_company_evidence,capture_fmp_response
    with capture_company_evidence("key") as captured:
        capture_fmp_response("https://financialmodelingprep.com/stable/quote",{"symbol":"AAPL"},[dict(symbol="AAPL",price=100,priceAvg50=90,priceAvg200=80)],"key")
    assert captured["companies"]["AAPL"]["quote"][0]["priceAvg200"]==80


def test_saved_three_feeds_eliminate_all_but_one_news_request(monkeypatch):
    provider.load_ideas_evidence.clear()
    names=("AAPL","MSFT","JPM","XOM");scope=credential_scope("key");now=datetime.now(timezone.utc).isoformat()
    shared={s:dict(symbol=s,credential_scope=scope,profile=[dict(symbol=s,currency="USD")],ratios=[dict(symbol=s,netProfitMarginTTM=.2)],quote=[dict(symbol=s,price=100,timestamp=datetime.now(timezone.utc).timestamp()-60,priceAvg50=90,priceAvg200=80)],sources={k:dict(provider="FMP",status="available",retrieved_at=now) for k in ("profile","ratios","quote")}) for s in names}
    call=Mock(return_value=[]);monkeypatch.setattr(provider,"get_fmp_json",call)
    out=provider.load_ideas_evidence(names,"key",shared)
    assert len(out["rows"])==4 and call.call_count==1 and call.call_args.args[0].endswith("news/stock")
    assert out["rows"]["AAPL"]["technicals"]["sma200"]==80 and out["rows"]["AAPL"]["sources"]["quote"]["retrieved_at"]==now
    provider.load_ideas_evidence.clear()
