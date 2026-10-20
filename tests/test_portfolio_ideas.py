"""Offline evidence, recommendation and cost contracts for the simplified station."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from langgraphagenticai.providers import portfolio_ideas as provider
from langgraphagenticai.portfolio_ideas import agent
from langgraphagenticai.portfolio_ideas.contracts import PERSONAS,universe,export,fingerprint

NAMES=("AAPL","MSFT","JPM","XOM")


def transport(url,*,params,**kwargs):
    if url.endswith("batch-quote"):
        return [dict(symbol=s,price=100.,timestamp=datetime.now(timezone.utc).timestamp()-60,priceAvg50=90,priceAvg200=80) for s in NAMES]
    if url.endswith("news/stock"):
        return [dict(symbol=s,title=s+" latest news",url="https://example.com/"+s,publishedDate=datetime.now(timezone.utc).isoformat()) for s in NAMES]
    if url.endswith("profile"):
        return [dict(symbol=params["symbol"],companyName=params["symbol"],currency="USD",sector="Technology")]
    return [dict(symbol=params["symbol"],priceToEarningsRatioTTM=20.,netProfitMarginTTM=0.,debtToEquityRatioTTM=1.)]


@pytest.fixture
def evidence(monkeypatch):
    provider.load_ideas_evidence.clear()
    mock=Mock(side_effect=transport)
    monkeypatch.setattr(provider,"get_fmp_json",mock)
    value=provider.load_ideas_evidence(NAMES,"fake-key",{})
    yield value,mock
    provider.load_ideas_evidence.clear()


def response(evidence):
    return dict(perspectives=[dict(persona=persona,summary="A differentiated research basket",picks=[dict(symbol=s,thesis="Quality with valuation risk",risk="Margins could decline",monitor="Watch profitability",evidence_refs=[s+":fundamentals"]) for s in NAMES[:3]]) for persona in PERSONAS])


def test_shared_batches_cache_units_and_zero(evidence):
    data,mock=evidence
    assert mock.call_count==10 # 2 batches + 2 calls/company, not four separate agent collections.
    provider.load_ideas_evidence(NAMES,"fake-key",{})
    assert mock.call_count==10 and set(data["rows"])==set(NAMES)
    row=data["rows"]["AAPL"]
    assert row["fundamentals"]["net_margin_ttm"]==0
    assert row["technicals"]["distance_sma50_pct"]==pytest.approx(100*(100/90-1))
    assert len(row["news"])==1 and row["evidence_refs"]["AAPL:fundamentals"]["period_end"] is None


def test_fresh_credential_scoped_equity_components_are_reused(evidence):
    from langgraphagenticai.providers.company_evidence import credential_scope
    data,mock=evidence
    now=datetime.now(timezone.utc).isoformat()
    shared={s:dict(symbol=s,credential_scope=credential_scope("fake-key"),profile=transport("profile",params={"symbol":s}),ratios=transport("ratios",params={"symbol":s}),sources={k:dict(provider="FMP",retrieved_at=now,status="available") for k in ("profile","ratios")}) for s in NAMES}
    mock.reset_mock()
    value=provider.load_ideas_evidence(NAMES,"fake-key",shared)
    assert mock.call_count==2 and value["rows"]["AAPL"]["sources"]["profile"]["reused"]
    shared["AAPL"]["credential_scope"]="wrong"
    mock.reset_mock()
    provider.load_ideas_evidence(NAMES,"fake-key",shared)
    assert mock.call_count==4


@pytest.mark.parametrize("bad",["AAPL,MSFT", "AAPL,MSFT,JPM,../bad", ",".join("A"+str(i) for i in range(13))])
def test_universe_validation_before_calls(bad):
    with pytest.raises(ValueError):universe(bad)


def test_recommendations_are_equal_weight_cited_and_not_crypto_restricted(evidence):
    data,_=evidence
    views,warnings=agent.validate_response(response(data),data)
    assert not warnings and set(views)==set(PERSONAS)
    for view in views.values():assert sum(p["weight_pct"] for p in view["picks"])==pytest.approx(100)
    assert [p["symbol"] for p in views["Cathie"]["picks"]]==list(NAMES[:3])


@pytest.mark.parametrize("edit",[
    lambda p:p["picks"][0].update(symbol="UNKNOWN"),
    lambda p:p["picks"][0].update(evidence_refs=["MSFT:fundamentals"]),
    lambda p:p["picks"][0].update(evidence_refs=["AAPL:news:999"]),
    lambda p:p["picks"].pop(),
    lambda p:p["picks"][0].update(symbol="MSFT"),
])
def test_bad_perspective_isolated_without_replacing_good_ones(evidence,edit):
    data,_=evidence
    value=response(data);edit(value["perspectives"][0])
    views,warnings=agent.validate_response(value,data)
    assert "Warren" not in views and len(views)==3 and warnings


def test_empty_basket_is_explicit_abstention_and_duplicate_personas_rejected(evidence):
    data,_=evidence
    value=response(data);value["perspectives"][0]["picks"]=[]
    views,_=agent.validate_response(value,data)
    assert views["Warren"]["picks"]==[]
    value["perspectives"][1]["persona"]="Warren"
    views,warnings=agent.validate_response(value,data)
    assert set(views)=={"Ray","Cathie"} and len(warnings)==2


def test_one_bounded_request_and_key_redaction(evidence,monkeypatch):
    data,_=evidence
    value=response(data);value["perspectives"][0]["summary"]="literal-private-key apikey=private"
    request=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=json.dumps(value),refusal=None))],usage=SimpleNamespace(prompt_tokens=500,completion_tokens=900)))
    factory=Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=request))))
    monkeypatch.setattr(agent,"build_openai_client",factory)
    result=agent.recommend("A balanced portfolio for research",list(NAMES),data,"literal-private-key","chosen-model")
    assert factory.call_args.kwargs==dict(timeout=90,max_retries=0) and request.call_count==1
    assert request.call_args.kwargs["model"]=="chosen-model" and request.call_args.kwargs["max_completion_tokens"]==4500
    assert result["model_calls"]==1 and result["prompt_tokens"]==500
    assert "literal-private-key" not in json.dumps(result) and "apikey=private" not in json.dumps(result)
    packet=json.loads(request.call_args.kwargs["messages"][1]["content"])
    assert "url" not in packet["evidence"]["rows"]["AAPL"]["news"][0]


def test_stale_or_sparse_evidence_never_calls_model(evidence,monkeypatch):
    data,_=evidence
    factory=Mock(side_effect=AssertionError("No paid call"));monkeypatch.setattr(agent,"build_openai_client",factory)
    old=deepcopy(data);old["retrieved_at"]=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    with pytest.raises(ValueError):agent.recommend("A balanced portfolio",list(NAMES),old,"fake","fake")
    sparse=deepcopy(data);del sparse["rows"]["AAPL"]
    with pytest.raises(ValueError):agent.recommend("A balanced portfolio",list(NAMES),sparse,"fake","fake")
    factory.assert_not_called()


def test_export_safety_and_material_fingerprints(evidence):
    data,_=evidence
    assert json.loads(export(dict(text="token=private",key="exact-secret"),("exact-secret",)))==dict(text="token=[REDACTED]",key="[REDACTED]")
    first=fingerprint("prompt",list(NAMES),data,"model")
    changed=deepcopy(data);changed["rows"]["AAPL"]["price"]+=1
    assert first!=fingerprint("prompt",list(NAMES),changed,"model")


def test_export_budget_rejects_instead_of_truncating_json():
    with pytest.raises(ValueError):export(dict(text="a"*2000001))


def test_partial_provider_failures_retain_quote_and_other_companies(monkeypatch):
    provider.load_ideas_evidence.clear()
    def partial(url,**kwargs):
        if url.endswith("news/stock") or (url.endswith("ratios-ttm") and kwargs["params"]["symbol"]=="JPM"):
            raise RuntimeError("apikey=private")
        return transport(url,**kwargs)
    monkeypatch.setattr(provider,"get_fmp_json",partial)
    data=provider.load_ideas_evidence(NAMES,"fake",{})
    assert len(data["rows"])==4 and "News" in data["rows"]["AAPL"]["gaps"]
    assert "Fundamentals" in data["rows"]["JPM"]["gaps"] and data["rows"]["AAPL"]["fundamentals"]["pe_ttm"]==20
    assert "private" not in str(data)
    provider.load_ideas_evidence.clear()


def test_batch_entitlement_failure_uses_bounded_regular_quotes(monkeypatch):
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    provider.load_ideas_evidence.clear()
    def restricted(url,**kwargs):
        if url.endswith("batch-quote"):raise ProviderRequestError("FMP","Plan required",status_code=402)
        if url.endswith("/quote"):
            return [r for r in transport("batch-quote",params={}) if r["symbol"]==kwargs["params"]["symbol"]]
        return transport(url,**kwargs)
    call=Mock(side_effect=restricted);monkeypatch.setattr(provider,"get_fmp_json",call)
    data=provider.load_ideas_evidence(NAMES,"fake",{})
    assert len(data["rows"])==4 and call.call_count==14
    assert all(row["sources"]["quote"]["route"]=="/stable/quote" for row in data["rows"].values())
    assert any("HTTP 402" in warning for warning in data["warnings"])
    provider.load_ideas_evidence(NAMES,"fake",{})
    assert call.call_count==14
    provider.load_ideas_evidence.clear()


def test_partial_batch_only_fetches_missing_symbols(monkeypatch):
    provider.load_ideas_evidence.clear()
    def partial(url,**kwargs):
        if url.endswith("batch-quote"):return transport(url,**kwargs)[:3]
        if url.endswith("/quote"):return [r for r in transport("batch-quote",params={}) if r["symbol"]==kwargs["params"]["symbol"]]
        return transport(url,**kwargs)
    call=Mock(side_effect=partial);monkeypatch.setattr(provider,"get_fmp_json",call)
    data=provider.load_ideas_evidence(NAMES,"fake",{})
    assert len(data["rows"])==4 and call.call_count==11
    assert [c.kwargs["params"]["symbol"] for c in call.call_args_list if c.args[0].endswith("/quote")]==["XOM"]
    assert data["rows"]["AAPL"]["sources"]["quote"]["route"]=="/stable/batch-quote"
    provider.load_ideas_evidence.clear()


def test_bad_future_quotes_news_and_fundamentals_stay_missing(monkeypatch):
    provider.load_ideas_evidence.clear()
    def bad(url,**kwargs):
        rows=transport(url,**kwargs)
        if url.endswith("batch-quote"):
            rows[0]["timestamp"]=datetime.now(timezone.utc).timestamp()+100
            rows[1]["currency"]="EUR"
        elif url.endswith("news/stock"):
            rows[0]["publishedDate"]="2099-01-01T00:00:00+00:00"
            rows[2]["url"]="https://example.com/?apikey=secret"
        elif url.endswith("ratios-ttm"):rows[0]["date"]="2099-01-01"
        return rows
    monkeypatch.setattr(provider,"get_fmp_json",bad)
    value=provider.load_ideas_evidence(NAMES,"fake",{})
    assert set(value["rows"])=={"JPM","XOM"}
    assert not value["rows"]["JPM"]["news"] and "JPM:fundamentals" not in value["rows"]["JPM"]["evidence_refs"]
    provider.load_ideas_evidence.clear()
