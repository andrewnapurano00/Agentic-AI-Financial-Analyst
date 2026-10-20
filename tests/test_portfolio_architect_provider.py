"""Mocked FMP response contracts; no external entitlements assumed."""
from datetime import datetime,timezone,timedelta
import pytest
from langgraphagenticai.providers import portfolio_architect as provider

NOW=datetime(2026,10,19,12,tzinfo=timezone.utc)


def records():
    q={"symbol":"MSFT","price":100.,"timestamp":NOW.timestamp(),"currency":"USD"}
    p={"symbol":"MSFT","companyName":"Microsoft fixture","currency":"USD","sector":"Technology",
       "isEtf":False,"exchange":"NASDAQ","averageVolume":1000000}
    ratios={"netProfitMarginTTM":0.,"priceToEarningsRatioTTM":None,"debtToEquityRatioTTM":.3}
    h={"2026-10-16":99.}
    return q,p,ratios,h


def norm(q,p,r,h):
    return provider.normalize_security("MSFT",q,p,r,h,NOW.isoformat(),NOW.isoformat(),NOW,"fixture-secret")


def test_zero_missing_source_and_original_dates():
    s=norm(*records())
    f={f.field:f for f in s.facts}
    assert f["margin_ttm"].value == 0 and "pe_ttm" not in f
    assert f["margin_ttm"].as_of is None and "TTM" in f["margin_ttm"].basis
    assert s.retrieved_at == NOW.isoformat() and s.history_retrieved_at == NOW.isoformat()


@pytest.mark.parametrize("field,value",[("price",None),("price",-1),("price",0),("price",True),
                                       ("price",float("nan")),("currency","EUR"),("timestamp",None),
                                       ("timestamp",(NOW-timedelta(days=8)).timestamp()),
                                       ("timestamp",(NOW+timedelta(seconds=1)).timestamp())])
def test_bad_quotes_block(field,value):
    q,p,r,h=records();q[field]=value
    with pytest.raises(ValueError): norm(q,p,r,h)


@pytest.mark.parametrize("field,value",[("currency",None),("currency","EUR"),("isEtf",None),("isEtf",True),
                                       ("isFund",True),("exchange","LSE"),("averageVolume",None),("averageVolume",1),
                                       ("sector","")])
def test_ineligible_profile_blocks(field,value):
    q,p,r,h=records();p[field]=value
    with pytest.raises(ValueError): norm(q,p,r,h)


def test_profile_only_currency_disclosed_and_secrets_filtered():
    q,p,r,h=records();q.pop("currency");p["companyName"]="fixture-secret"
    s=norm(q,p,r,h)
    assert "assumed" in s.currency_basis and s.name == "[REDACTED]"


def test_history_shapes_duplicate_bad_dates_wrong_symbol_currency():
    raw=[{"symbol":"MSFT","date":"2026-10-16","close":100},
         {"symbol":"MSFT","date":"2026-10-16","close":101},
         {"symbol":"MSFT","date":"2026-10-15","close":99},
         {"symbol":"OTHER","date":"2026-10-14","close":50},
         {"symbol":"MSFT","date":"2026-10-13","close":100,"currency":"EUR"},
         {"date":"2026-10-20","close":200},{"date":"bad","close":1},{"date":"2026-10-12","close":-1}]
    expected={"2026-10-15":99.}
    assert provider.normalize_history(raw,"MSFT","2026-10-01","2026-10-19") == expected
    assert provider.normalize_history({"symbol":"MSFT","historical":raw},"MSFT","2026-10-01","2026-10-19") == expected
    assert not provider.normalize_history({"symbol":"OTHER","historical":raw},"MSFT","2026-10-01","2026-10-19")


def test_missing_stale_history_keeps_successful_facts():
    q,p,r,h=records();s=norm(q,p,r,{"2025-01-01":99})
    assert not s.history and s.facts


def test_quote_duplicates_removed():
    q,*_=records()
    assert provider.one([q,q],"MSFT") == {}


def test_partial_provider_failure_and_cache_scope(monkeypatch):
    calls=[]
    q,p,r,h=records()
    def fake(url,**kw):
        calls.append((url,kw["api_key"]))
        if url.endswith("batch-quote"):return [q]
        if url.endswith("profile"):return [p]
        raise TimeoutError("fixture-secret: network failed")
    monkeypatch.setattr(provider,"get_fmp_json",fake)
    provider.load_current.clear()
    a=provider.load_current(("MSFT",),"fixture-one")
    b=provider.load_current(("MSFT",),"fixture-one")
    assert a == b and len(calls) == 3 and a["facts"]["MSFT"]["ratios"] == {}
    provider.load_current(("MSFT",),"fixture-two")
    assert len(calls) == 6
    provider.load_current.clear()


def test_all_failed_collection_is_structured(monkeypatch):
    monkeypatch.setattr(provider,"get_fmp_json",lambda *a,**k: (_ for _ in ()).throw(TimeoutError("fixture-secret")))
    provider.load_current.clear();provider.load_histories.clear()
    s=provider.collect(("MSFT",),"SPY","fixture-secret")
    assert not s.securities and s.excluded and s.warnings and s.benchmark is None
    assert "fixture-secret" not in s.model_dump_json()
    provider.load_current.clear();provider.load_histories.clear()


def test_unknown_symbols_rejected_before_network():
    with pytest.raises(ValueError):provider.load_current(("UNSUPPORTED",),"fixture")
    with pytest.raises(ValueError):provider.load_current(("MSFT",),"")


def test_batch_entitlement_failure_uses_single_quote_and_preserves_source(monkeypatch):
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    calls=[];q,p,r,h=records()
    def fake(url,**kw):
        calls.append(url.rsplit('/',1)[-1])
        if url.endswith('batch-quote'):raise ProviderRequestError('FMP','fixture-secret',status_code=402)
        if url.endswith('/quote'):return [q]
        if url.endswith('/profile'):return [p]
        return []
    monkeypatch.setattr(provider,'get_fmp_json',fake)
    provider.load_current.clear()
    current=provider.load_current(('MSFT',),'fixture-secret')
    assert calls.count('batch-quote') == calls.count('quote') == 1 and len(calls) == 4
    assert current['quotes']['MSFT']['timestamp'] == q['timestamp']
    assert current['quote_sources']['MSFT'] == 'FMP stable/quote'
    assert any('HTTP 402' in s for s in current['warnings'])
    assert 'fixture-secret' not in str(current)
    s=provider.normalize_security('MSFT',q,p,r,h,NOW.isoformat(),NOW.isoformat(),NOW,quote_source=current['quote_sources']['MSFT'])
    assert next(f for f in s.facts if f.field=='price').source == 'FMP stable/quote'
    provider.load_current.clear()


def test_partial_batch_only_requests_missing_symbols(monkeypatch):
    q,p,_,_=records();calls=[]
    def fake(url,**kw):
        symbol=kw['params'].get('symbol')
        calls.append((url.rsplit('/',1)[-1],symbol))
        if url.endswith('batch-quote'):return [q]
        if url.endswith('/quote'):return [{**q,'symbol':symbol}]
        if url.endswith('/profile'):return [{**p,'symbol':symbol}]
        return []
    monkeypatch.setattr(provider,'get_fmp_json',fake);provider.load_current.clear()
    result=provider.load_current(('MSFT','NVDA'),'fixture')
    assert [('quote','NVDA')] == [v for v in calls if v[0]=='quote']
    assert result['quote_sources']['MSFT']=='FMP stable/batch-quote'
    assert result['quote_sources']['NVDA']=='FMP stable/quote'
    provider.load_current.clear()


def test_invalid_auth_does_not_fan_out_quote_requests(monkeypatch):
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    calls=[]
    def fake(url,**kw):
        calls.append(url.rsplit('/',1)[-1])
        raise ProviderRequestError('FMP','unsafe fixture-secret',status_code=401)
    monkeypatch.setattr(provider,'get_fmp_json',fake);provider.load_current.clear()
    result=provider.load_current(('MSFT','NVDA'),'fixture-secret')
    assert 'quote' not in calls and any('HTTP 401' in s for s in result['warnings'])
    assert 'fixture-secret' not in str(result)
    provider.load_current.clear()


def test_null_profile_average_volume_can_use_explicit_quote_average():
    q,p,r,h=records();p['averageVolume']=None;q['avgVolume']=1000000
    s=norm(q,p,r,h)
    assert next(f for f in s.facts if f.field=='turnover').value==100000000
