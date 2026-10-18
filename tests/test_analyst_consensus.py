"""Offline analyst consensus arithmetic, provider and saved-control contracts."""
from copy import deepcopy
from datetime import datetime,timezone
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis.analyst_consensus import consensus_distribution,FIELDS
from langgraphagenticai.providers import analyst_consensus as provider
from langgraphagenticai.ui.analyst_consensus import consensus_gauge

SAMPLE={"symbol":"AAPL","strongBuy":1,"buy":70,"hold":32,"sell":9,"strongSell":0,"consensus":"Buy"}


def test_sample_three_categories_and_denominator():
    saved=deepcopy(SAMPLE)
    data=consensus_distribution([SAMPLE],"AAPL")
    assert data["total"]==112 and data["leading_category"]=="Buy"
    assert [r["count"] for r in data["categories"]]==[71,32,9]
    assert [r["percent"] for r in data["categories"]]==pytest.approx([63.3928571429,28.5714285714,8.0357142857])
    assert sum(r["percent"] for r in data["categories"])==pytest.approx(100)
    assert SAMPLE==saved and data["as_of"] is None


@pytest.mark.parametrize("bad",[None,-1,1.5,True,"bad",float("inf"),float("nan")])
def test_invalid_or_missing_counts_are_never_zero(bad):
    with pytest.raises(ValueError):
        consensus_distribution([{**SAMPLE,"strongSell":bad}],"AAPL")


def test_zero_and_tie_no_invented_preference():
    tie={"symbol":"AAPL",**{k:0 for k in FIELDS},"buy":3,"sell":3}
    data=consensus_distribution([tie],"AAPL")
    assert data["leading_category"] is None
    assert data["categories"][1]["percent"]==0
    assert "Mixed" in consensus_gauge(data)
    with pytest.raises(ValueError):
        consensus_distribution([{**tie,"buy":0,"sell":0}],"AAPL")


def test_identity_conflicts_and_error_envelopes():
    for payload in ([],{"error":"Unavailable"},[{**SAMPLE,"symbol":"MSFT"}],[SAMPLE,{**SAMPLE,"buy":71}]):
        with pytest.raises(ValueError):
            consensus_distribution(payload,"AAPL")
    assert consensus_distribution([SAMPLE,SAMPLE],"AAPL")["total"]==112


def test_provider_cache_contract_and_safe_failures(monkeypatch):
    provider._collect.clear()
    fetch=Mock(return_value=[SAMPLE]);monkeypatch.setattr(provider,"get_fmp_json",fetch)
    packet=provider.load_analyst_consensus(" aapl ","synthetic")
    assert packet["status"]=="available" and packet["provider"]=="Financial Modeling Prep"
    assert "synthetic" not in str(packet) and "apikey" not in str(packet)
    assert fetch.call_args.args==(provider.ENDPOINT,)
    assert fetch.call_args.kwargs["params"]=={"symbol":"AAPL"}
    provider.load_analyst_consensus("AAPL","synthetic")
    assert fetch.call_count==1
    provider.load_analyst_consensus("AAPL","synthetic",refresh=True)
    assert fetch.call_count==2
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    fetch.side_effect=ProviderRequestError("FMP","secret-error",status_code=403)
    failure=provider.load_analyst_consensus("AAPL","synthetic",refresh=True)
    assert failure["status"]=="unavailable" and failure["data"] is None
    assert "403" in failure["warnings"][0] and "secret-error" not in str(failure)
    provider._collect.clear()


@pytest.mark.parametrize("symbol",["../AAPL","AAPL?apikey=secret","",None])
def test_invalid_symbol_never_calls_provider(monkeypatch,symbol):
    fetch=Mock();monkeypatch.setattr(provider,"get_fmp_json",fetch)
    with pytest.raises(ValueError):
        provider.load_analyst_consensus(symbol,"synthetic")
    fetch.assert_not_called()


def test_ui_explicit_load_ticker_switch_failure_and_reuse(monkeypatch):
    from langgraphagenticai.ui import analyst_consensus as ui
    calls=[]
    def load(symbol,key,**kwargs):
        calls.append((symbol,key))
        if len(calls)==3:
            return dict(symbol=symbol,data=None,warnings=["Unavailable"],status="unavailable")
        row={**SAMPLE,"symbol":symbol}
        return dict(symbol=symbol,provider="FMP",retrieved_at=datetime.now(timezone.utc).isoformat(),
                    data=consensus_distribution([row],symbol),warnings=[],status="available")
    monkeypatch.setattr(ui,"load_analyst_consensus",load)
    app=AppTest.from_string('''
from langgraphagenticai.ui.analyst_consensus import render_analyst_consensus
render_analyst_consensus(["AAPL","MSFT"],"AAPL","synthetic")
''',default_timeout=30).run()
    assert not app.exception and not calls
    app.button(key="movers_consensus_load").click().run()
    assert not app.exception and len(calls)==1
    assert any(all(value in m.value for value in ["63.4%","28.6%","8.0%", "Consensus Rating"]) for m in app.markdown)
    app.run();assert len(calls)==1
    app.selectbox(key="movers_consensus_stock").set_value("MSFT").run()
    assert not any("<svg" in m.value for m in app.markdown) and len(calls)==1
    app.button(key="movers_consensus_load").click().run()
    assert len(calls)==2
    app.button(key="movers_consensus_load").click().run()
    assert not app.exception and any("<svg" in m.value for m in app.markdown)
    assert any("previously saved" in w.value for w in app.warning)
    app.selectbox(key="movers_consensus_stock").set_value("AAPL").run()
    assert len(calls)==3 and any("<svg" in m.value for m in app.markdown)


def test_gauge_matches_reference_layout_and_preserves_rating_counts():
    svg=consensus_gauge(consensus_distribution([SAMPLE],"AAPL"))
    assert 'viewBox="0 0 340 332"' in svg and 'role="img"' in svg
    assert "Consensus Rating" in svg and "Based on 112 Analyst Ratings" in svg
    assert "63.4%" in svg and "28.6%" in svg and "8.0%" in svg
    assert "<line" in svg and "linearGradient" in svg
    assert svg.rindex('>Sell</text>')<svg.rindex('>Hold</text>')<svg.rindex('>Buy</text>')
