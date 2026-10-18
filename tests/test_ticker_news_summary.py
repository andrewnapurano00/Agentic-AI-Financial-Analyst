"""Offline ticker-news provider, AI validation and explicit-action session contracts."""
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis import ticker_news_ai as ai
from langgraphagenticai.providers import ticker_news as provider


def news(symbol="AAPL"):
    return dict(symbol=symbol,company="Apple" if symbol=="AAPL" else "Microsoft",retrieved_at=datetime.now(timezone.utc).isoformat(),lookback_days=7,warnings=[],
        articles=[dict(title=symbol+" product launch",url="https://example.com/"+symbol,snippet="A new product was announced; demand remains uncertain.",published="2026-10-17",providers=["FMP"],publisher="Example")])


def result(packet):
    return dict(ticker=packet["ticker"],fingerprint=packet["fingerprint"],overview="Product news supports the outlook, with demand uncertainty. [N1]",sentiment="Mixed",
        sentiment_reason="A catalyst is balanced by uncertain demand.",sentiment_evidence_ids=["N1"],stories=[dict(development="A product was announced.",implication="Demand will determine its impact.",evidence_ids=["N1"])],limitations="Headline coverage is narrow; article context is incomplete.")


def mock_client(monkeypatch,edit=lambda r:r,finish="stop",refusal=None):
    calls=[]
    def create(**kwargs):
        calls.append(kwargs)
        packet=json.loads(kwargs["messages"][1]["content"])
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=json.dumps(edit(result(packet))),refusal=refusal))])
    builder=Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(ai,"build_openai_client",builder)
    return calls,builder


def test_ticker_scope_changes_fingerprint_and_client_is_bounded(monkeypatch):
    first=ai.ticker_evidence(news());second=ai.ticker_evidence(news("MSFT"))
    assert first["fingerprint"]!=second["fingerprint"] and first["ticker"]=="AAPL"
    calls,builder=mock_client(monkeypatch)
    saved=ai.summarize_ticker_news(news(),"synthetic","gpt-5")
    assert saved["result"]["sentiment"]=="Mixed" and saved["generated_at"]
    builder.assert_called_once_with("synthetic",timeout=75,max_retries=0)
    assert len(calls)==1 and calls[0]["max_completion_tokens"]==6000
    assert "synthetic" not in str(saved)
    assert "untrusted" in calls[0]["messages"][0]["content"]


@pytest.mark.parametrize("edit",[
    lambda r:{**r,"ticker":"MSFT"},lambda r:{**r,"fingerprint":"wrong"},
    lambda r:{**r,"sentiment":"Guaranteed buy"},lambda r:{**r,"sentiment_evidence_ids":["N999"]},
    lambda r:{**r,"stories":[{**r["stories"][0],"evidence_ids":["N999"]}]},
    lambda r:{**r,"overview":"word "*170,"limitations":"word "*100},
])
def test_wrong_ticker_evidence_tone_reference_or_budget_rejected(monkeypatch,edit):
    calls,_=mock_client(monkeypatch,edit)
    with pytest.raises(ValueError):ai.summarize_ticker_news(news(),"synthetic","gpt-5")
    assert len(calls)==1


@pytest.mark.parametrize("finish,refusal",[("length",None),("stop","Refused")])
def test_incomplete_refusal_no_retry(monkeypatch,finish,refusal):
    calls,_=mock_client(monkeypatch,finish=finish,refusal=refusal)
    with pytest.raises(ValueError):ai.summarize_ticker_news(news(),"synthetic","gpt-5")
    assert len(calls)==1


def test_empty_news_or_missing_key_never_calls_model(monkeypatch):
    calls,_=mock_client(monkeypatch)
    for packet,key in (({**news(),"articles":[]},"synthetic"),(news(),"")):
        with pytest.raises(ValueError):ai.summarize_ticker_news(packet,key,"gpt-5")
    assert not calls


def test_multi_provider_merge_safe_links_dates_identity_and_partial_failures(monkeypatch):
    now=datetime.now(timezone.utc)
    today=now.isoformat();old=(now-timedelta(days=10)).isoformat();future=(now+timedelta(days=1)).isoformat()
    def fmp(url,**kwargs):
        assert url==provider.ENDPOINT and kwargs["params"]=={"tickers":"AAPL","limit":12}
        return [dict(symbol="AAPL",title="Launch",url="https://example.com/a?utm_source=fmp",text="Preview",publishedDate=today),
                dict(symbol="MSFT",title="Other company",url="https://example.com/other",publishedDate=today),
                dict(symbol="AAPL",title="Old",url="https://example.com/old",publishedDate=old),
                dict(symbol="AAPL",title="Future",url="https://example.com/future",publishedDate=future),
                dict(symbol="AAPL",title="Secret link",url="https://example.com/private?apikey=hidden",publishedDate=today)]
    monkeypatch.setattr(provider,"get_fmp_json",fmp)
    monkeypatch.setattr(provider.SerperClient,"search",lambda *a,**k:dict(ok=True,results=[dict(title="Launch",url="https://example.com/a",snippet="Search preview",published="2 hours ago")]))
    def marketaux(*a,**k):
        assert k["params"]["symbols"]=="AAPL"
        raise ValueError("synthetic secret provider error")
    monkeypatch.setattr(provider.requests,"get",marketaux)
    data=provider._collect.__wrapped__("AAPL","Apple","synthetic","synthetic","synthetic")
    assert len(data["articles"])==1
    assert data["articles"][0]["providers"]==["FMP","Serper"]
    assert any("Marketaux company news unavailable" in w for w in data["warnings"])
    assert "hidden" not in str(data) and "synthetic secret" not in str(data)


def test_symbol_validation_before_news_network(monkeypatch):
    collect=Mock();monkeypatch.setattr(provider,"_collect",collect)
    with pytest.raises(ValueError):provider.load_ticker_news("../AAPL","Apple","synthetic")
    with pytest.raises(ValueError):provider.load_ticker_news("AAPL","Apple")
    collect.assert_not_called()


def test_marketaux_entity_filter_and_cache(monkeypatch):
    provider._collect.clear()
    count=[]
    def marketaux(*a,**k):
        count.append(1)
        return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{"data":[
            dict(title="Apple",url="https://example.com/a",published_at=datetime.now(timezone.utc).isoformat(),entities=[{"symbol":"AAPL"}]),
            dict(title="Other",url="https://example.com/m",entities=[{"symbol":"MSFT"}]) ]})
    monkeypatch.setattr(provider.requests,"get",marketaux)
    data=provider.load_ticker_news("AAPL","Apple","","synthetic","")
    assert len(data["articles"])==1
    provider.load_ticker_news("AAPL","Apple","","synthetic","")
    assert len(count)==1
    provider.load_ticker_news("AAPL","Apple","","synthetic","",refresh=True)
    assert len(count)==2
    provider._collect.clear()


def test_ui_load_generate_rerun_switch_model_stale_and_recovery(monkeypatch):
    from langgraphagenticai.ui import ticker_news_summary as ui
    counts={"news":0,"model":0}
    def load(symbol,*args,**kwargs):
        counts["news"]+=1
        return news(symbol) if counts["news"]<3 else {**news(symbol),"articles":[]}
    def generate(packet,*args):
        counts["model"]+=1
        if counts["model"]==3:raise ValueError("Synthetic model failure")
        evidence=ai.ticker_evidence(packet)
        return dict(result=result(evidence),evidence=evidence,model=args[-1],generated_at="2026-10-17T12:00:00Z")
    monkeypatch.setattr(ui,"load_ticker_news",load);monkeypatch.setattr(ui,"summarize_ticker_news",generate)
    app=AppTest.from_string('''
import streamlit as st
from langgraphagenticai.ui.ticker_news_summary import render_ticker_news_summary
render_ticker_news_summary(st.session_state.get("symbol","AAPL"),"Company",fmp_api_key="synthetic",openai_api_key="synthetic",model_name=st.session_state.get("model","gpt-5"))
''',default_timeout=30).run()
    assert not app.exception and counts=={"news":0,"model":0}
    assert app.button(key="movers_news_generate").disabled
    app.button(key="movers_news_load").click().run()
    assert counts=={"news":1,"model":0}
    app.button(key="movers_news_generate").click().run()
    assert not app.exception and counts=={"news":1,"model":1}
    assert any("News sentiment: Mixed" in w.value for w in app.warning)
    assert all("N1" not in t.value for t in app.text)
    app.run();assert counts=={"news":1,"model":1}
    app.session_state["symbol"]="MSFT";app.run()
    assert app.button(key="movers_news_generate").disabled and not app.text
    app.button(key="movers_news_load").click().run();app.button(key="movers_news_generate").click().run()
    assert counts=={"news":2,"model":2}
    app.session_state["symbol"]="AAPL";app.run()
    assert app.text and counts=={"news":2,"model":2}
    app.button(key="movers_news_load").click().run()
    assert any("saved news retained" in w.value for w in app.warning)
    app.button(key="movers_news_generate").click().run()
    assert app.text and any("previous summary preserved" in w.value for w in app.warning)
    app.session_state["model"]="gpt-5-mini";app.run()
    assert any("earlier news or model" in w.value for w in app.warning)
    assert counts=={"news":3,"model":3}


def test_actual_main_passes_news_settings_without_generating(monkeypatch):
    from langgraphagenticai import main
    from langgraphagenticai.ui.streamlitui import loadui
    render=Mock();monkeypatch.setattr(main,"render_top_movers_tab",render)
    monkeypatch.setattr(loadui,"_resolve_secret",lambda value,key,env:"synthetic" if key in {"FMP_API_KEY","OPENAI_API_KEY","MARKETAUX_API_KEY","SERPER_API_KEY"} else "")
    app=AppTest.from_string("from langgraphagenticai.main import load_langgraph_agenticai_app;load_langgraph_agenticai_app()",default_timeout=30)
    app.session_state["active_workspace"]="Top Movers"
    app.run()
    assert not app.exception and render.call_count==1
    assert render.call_args.kwargs["openai_api_key"]=="synthetic"
    assert render.call_args.kwargs["marketaux_api_key"]=="synthetic"
    assert render.call_args.kwargs["serper_api_key"]=="synthetic"
    assert render.call_args.kwargs["model_name"]


def test_model_timeout_is_one_attempt_and_never_retries(monkeypatch):
    calls,builder=mock_client(monkeypatch)
    create=Mock(side_effect=TimeoutError("Synthetic timeout"))
    builder.return_value.chat.completions.create=create
    with pytest.raises(TimeoutError):ai.summarize_ticker_news(news(),"synthetic","gpt-5")
    assert create.call_count==1
    assert builder.call_args.kwargs["max_retries"]==0


def test_evidence_preparation_failure_keeps_page_usable_without_ai(monkeypatch):
    from langgraphagenticai.ui import ticker_news_summary as ui
    monkeypatch.setattr(ui,"load_ticker_news",lambda *a,**k:news())
    monkeypatch.setattr(ui,"ticker_evidence",Mock(side_effect=ValueError("Synthetic budget limit")))
    generate=Mock();monkeypatch.setattr(ui,"summarize_ticker_news",generate)
    app=AppTest.from_string('''
from langgraphagenticai.ui.ticker_news_summary import render_ticker_news_summary
render_ticker_news_summary("AAPL","Apple",fmp_api_key="synthetic",openai_api_key="synthetic")
''',default_timeout=30).run()
    app.button(key="movers_news_load").click().run()
    assert not app.exception and app.button(key="movers_news_generate").disabled
    assert any("evidence limits" in w.value for w in app.warning)
    generate.assert_not_called()
