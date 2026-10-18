"""Offline target-window, quote-basis and saved UI contracts."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis.price_targets import normalize_targets,compare_targets
from langgraphagenticai.ui.price_targets import target_chart,merge_target_evidence

NOW=datetime(2026,10,17,20,tzinfo=timezone.utc)
ROW=dict(symbol="FICO",lastMonth=13,lastMonthAvgPriceTarget=1096.15,lastQuarter=18,lastQuarterAvgPriceTarget=1207.72)


def summary(row=None):return dict(symbol="FICO",targets=normalize_targets([row or ROW],"FICO"),retrieved_at=NOW.isoformat(),warnings=[])
def quote(price=1000,**kwargs):return dict(symbol="FICO",price=price,currency="USD",as_of=NOW.isoformat(),retrieved_at=NOW.isoformat(),error=None,**kwargs)


def test_sample_upside_and_real_zero_target():
    data=compare_targets(summary(),quote(),NOW)
    assert [r["upside_pct"] for r in data["rows"]]==pytest.approx([9.615,20.772])
    assert [r["count"] for r in data["rows"]]==[13,18]
    zero=summary({**ROW,"lastMonthAvgPriceTarget":0})
    assert compare_targets(zero,quote(),NOW)["rows"][0]["upside_pct"]==-100
    below=compare_targets(summary(),quote(1500),NOW)
    assert all(r["direction"]=="Downside" for r in below["rows"])


@pytest.mark.parametrize("bad",[None,False,-1,float("nan"),float("inf"),"bad"])
def test_invalid_target_only_affects_its_window(bad):
    rows=normalize_targets([{**ROW,"lastMonthAvgPriceTarget":bad}],"FICO")
    assert rows[0]["target"] is None and rows[1]["target"]==1207.72


def test_empty_window_currency_mismatch_missing_quote_future_and_identity():
    empty=summary({**ROW,"lastMonth":0,"lastMonthAvgPriceTarget":0})
    assert empty["targets"][0]["target"] is None
    different=summary({**ROW,"currency":"EUR"})
    compared=compare_targets(different,quote(),NOW)
    assert all(r["upside_pct"] is None for r in compared["rows"])
    assert any("currencies differ" in w for w in compared["warnings"])
    assert compare_targets(summary(),quote(0),NOW)["price"] is None
    future=quote();future["as_of"]=(NOW+timedelta(days=1)).isoformat()
    assert compare_targets(summary(),future,NOW)["price"] is None
    other=quote();other["symbol"]="AAPL"
    with pytest.raises(ValueError):compare_targets(summary(),other,NOW)
    with pytest.raises(ValueError):normalize_targets([{**ROW,"symbol":"AAPL"}],"FICO")
    with pytest.raises(ValueError):normalize_targets([ROW,{**ROW,"lastMonthAvgPriceTarget":2}],"FICO")


def test_currency_assumption_and_stale_quote_are_explicit():
    data=compare_targets(summary(),quote(),NOW)
    assert any("assumes matching currencies" in w for w in data["warnings"])
    old=quote();old["as_of"]=(NOW-timedelta(days=5)).isoformat()
    assert any("over four" in w for w in compare_targets(summary(),old,NOW)["warnings"])


def test_partial_refresh_retains_saved_window_quote_and_original_timestamps():
    old=dict(symbol="FICO",summary=summary(),quote=quote())
    old["summary"]["targets"][1]["retrieved_at"]="old-quarter-time"
    new=dict(symbol="FICO",summary=summary({**ROW,"lastMonthAvgPriceTarget":1100,"lastQuarterAvgPriceTarget":None}),quote={**quote(),"error":"Unavailable"})
    saved=deepcopy(old)
    merged=merge_target_evidence(old,new)
    assert merged["summary"]["targets"][0]["target"]==1100
    assert merged["summary"]["targets"][1]["target"]==1207.72
    assert merged["summary"]["targets"][1]["retrieved_at"]=="old-quarter-time"
    assert merged["quote"]["price"]==1000 and len(merged["refresh_warnings"])==2
    assert old==saved


def test_provider_route_cache_refresh_and_safe_failure(monkeypatch):
    from langgraphagenticai.providers import price_targets as p
    p._summary.clear()
    fetch=Mock(return_value=[ROW]);monkeypatch.setattr(p,"get_fmp_json",fetch)
    quotes=Mock(return_value=quote());monkeypatch.setattr(p,"load_selected_quote",quotes)
    packet=p.load_price_targets(" fico ","synthetic")
    assert packet["summary"]["targets"][0]["target"]==1096.15
    assert fetch.call_args.args==(p.ENDPOINT,)
    assert fetch.call_args.kwargs["params"]=={"symbol":"FICO"}
    assert "synthetic" not in str(packet)
    p.load_price_targets("FICO","synthetic")
    assert fetch.call_count==1
    p.load_price_targets("FICO","synthetic",refresh=True)
    assert fetch.call_count==2 and quotes.clear.call_count==1
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    fetch.side_effect=ProviderRequestError("FMP","do not render provider error",status_code=403)
    packet=p.load_price_targets("FICO","synthetic",refresh=True)
    assert packet["summary"]["targets"]==[] and packet["quote"]["price"]==1000
    assert "403" in str(packet) and "do not render" not in str(packet)
    p._summary.clear()


def test_no_network_for_invalid_symbol_or_missing_key(monkeypatch):
    from langgraphagenticai.providers import price_targets as p
    fetch=Mock();monkeypatch.setattr(p,"get_fmp_json",fetch)
    for symbol,key in (("../FICO","synthetic"),("FICO","")):
        with pytest.raises(ValueError):p.load_price_targets(symbol,key)
    fetch.assert_not_called()


def test_target_chart_positive_negative_and_flat():
    data=compare_targets(summary(),quote(),NOW)
    spec=target_chart(data).to_dict()
    assert len(spec["layer"])==5
    assert spec["layer"][3]["mark"]["shape"]=="diamond"
    assert "strokeDash" in spec["layer"][0]["mark"]


def test_explicit_load_rerun_switch_and_failure_retention(monkeypatch):
    from langgraphagenticai.ui import price_targets as ui
    calls=[]
    def load(symbol,key,**kwargs):
        calls.append(symbol)
        if len(calls)==2:return dict(symbol=symbol,summary={**summary(),"targets":[]},quote={**quote(),"error":"Unavailable"})
        return dict(symbol=symbol,summary=summary(),quote=quote())
    monkeypatch.setattr(ui,"load_price_targets",load)
    app=AppTest.from_string('''
import streamlit as st
from langgraphagenticai.ui.price_targets import render_price_targets
render_price_targets(st.session_state.get("test_symbol","FICO"),"synthetic")
''',default_timeout=30).run()
    assert not app.exception and calls==[]
    app.button(key="movers_targets_load").click().run()
    assert not app.exception and len(app.metric)==3 and calls==["FICO"]
    app.run();assert calls==["FICO"]
    app.button(key="movers_targets_load").click().run()
    assert not app.exception and len(app.metric)==3
    assert any("saved targets" in w.value for w in app.warning)
    app.session_state["test_symbol"]="AAPL";app.run()
    assert not app.metric and len(calls)==2
    app.session_state["test_symbol"]="FICO";app.run()
    assert len(app.metric)==3 and len(calls)==2


def test_explicit_zero_coverage_replaces_old_window_instead_of_stale_fallback():
    old=dict(symbol="FICO",summary=summary(),quote=quote())
    fresh=dict(symbol="FICO",summary=summary({**ROW,"lastMonth":0,"lastMonthAvgPriceTarget":0}),quote=quote())
    result=merge_target_evidence(old,fresh)
    assert result["summary"]["targets"][0]["target"] is None
    assert result["summary"]["targets"][0]["count"]==0
    assert not result["refresh_warnings"]
