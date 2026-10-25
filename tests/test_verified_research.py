"""AX-07 session/credential/lineage/freshness contracts; no paid/live calls."""
from copy import deepcopy
import json
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from test_investment_brief import eligible_result, REFERENCE
from langgraphagenticai.state.verified_research import bind_collected_run,create_snapshot,accept_snapshot,VerifiedResearchSnapshot
from langgraphagenticai.ui.workspace_handoff import queue_handoff,apply_pending_handoff
from langgraphagenticai.state.research_context import ResearchContext

ENGINE="Standard V1"


def fixture(engine=ENGINE):
    saved=eligible_result()
    history="dr_history" if engine==ENGINE else "drv2_history"
    state={history:[saved]}
    bind_collected_run(state,saved,engine,"fixture-key")
    return state,saved


@pytest.mark.parametrize("engine",[ENGINE,"Low cost V2 pilot"])
def test_reuse_revalidates_without_refetch_or_source_mutation(engine,monkeypatch):
    monkeypatch.setattr("requests.sessions.Session.request",Mock(side_effect=AssertionError("No IO")))
    state,saved=fixture(engine); original=deepcopy(saved)
    snap=create_snapshot(state,saved,"aapl",engine,"fixture-key",reference_time=REFERENCE)
    inputs=accept_snapshot(state,snap,"AAPL","fixture-key",reference_time=REFERENCE)
    assert inputs.eligible and inputs.net_income==128930000000
    assert saved==original
    assert "fixture-key" not in snap.model_dump_json()
    assert "report" not in json.loads(snap.evidence_json)
    assert "scope" not in json.loads(snap.evidence_json)
    assert snap.observations_json
    assert accept_snapshot(state,snap,"AAPL","fixture-key",reference_time=REFERENCE)==inputs
    restored=VerifiedResearchSnapshot.model_validate_json(snap.model_dump_json())
    assert accept_snapshot(state,restored,"AAPL","fixture-key",reference_time=REFERENCE)==inputs


@pytest.mark.parametrize("change",["ticker","credential","session","source","refresh","history","tamper","purpose","version"])
def test_incompatible_packets_fail_closed_and_ticker_navigation_still_works(change):
    state,saved=fixture()
    snap=create_snapshot(state,saved,"AAPL",ENGINE,"fixture-key",reference_time=REFERENCE)
    symbol,key="AAPL","fixture-key"
    if change=="ticker": symbol="MSFT"
    if change=="credential": key="rotated-key"
    if change=="session": state,_=fixture()
    if change=="source": saved["comparison"][0]["Net income (TTM)"]=1
    if change=="refresh":
        saved["evidence"][0]["retrieved_at"]="2026-10-08T00:00:00Z"
        bind_collected_run(state,saved,ENGINE,"fixture-key")
    if change=="history": state["dr_history"]=[]
    if change=="tamper": snap=snap.model_copy(update={"evidence_json":snap.evidence_json.replace("128930000000","999")})
    if change=="purpose": snap=snap.model_copy(update={"purpose":"annual_price_target"})
    if change=="version": snap=snap.model_copy(update={"version":"legacy"})
    with pytest.raises(ValueError): accept_snapshot(state,snap,symbol,key,reference_time=REFERENCE)
    queue_handoff(state,ResearchContext((symbol,),"AI Valuation","analyze","Deep Research"))
    context=apply_pending_handoff(state)
    assert context.symbols==(symbol,) and state["valuation_ticker"]==symbol
    assert "verified_sensitivity_snapshot" not in state


@pytest.mark.parametrize("reference",["2026-10-09T16:00:00+00:00","2027-10-08T16:00:00+00:00","2026-10-07T15:00:00+00:00"])
def test_revalidation_rejects_stale_or_future_reference(reference):
    state,saved=fixture()
    snap=create_snapshot(state,saved,"AAPL",ENGINE,"fixture-key",reference_time=REFERENCE)
    with pytest.raises(ValueError):accept_snapshot(state,snap,"AAPL","fixture-key",reference_time=reference)


@pytest.mark.parametrize("change",["legacy","currency","basis","metadata","unsupported_sector"])
def test_source_ineligibility_is_not_repaired_by_binding(change):
    state,saved=fixture()
    if change=="legacy": state.pop("_verified_research_bindings")
    if change=="currency": saved["comparison"][0]["Metric contracts"]["Market cap"]["currency"]="EUR"
    if change=="basis": saved["comparison"][0]["TTM fiscal quarters"]=[]
    if change=="metadata": saved["evidence"][0]["provider"]=""
    if change=="unsupported_sector": saved["comparison"][0]["Sector"]="Real Estate"
    if change!="legacy":bind_collected_run(state,saved,ENGINE,"fixture-key")
    with pytest.raises(ValueError):create_snapshot(state,saved,"AAPL",ENGINE,"fixture-key",reference_time=REFERENCE)


def test_explicit_button_and_recipient_edits_make_no_calls(monkeypatch):
    state,saved=fixture()
    snap=create_snapshot(state,saved,"AAPL",ENGINE,"fixture-key",reference_time=REFERENCE)
    from langgraphagenticai.ui import verified_research as ui
    imported=accept_snapshot(state,snap,"AAPL","fixture-key",reference_time=REFERENCE)
    accept=Mock(return_value=imported)
    monkeypatch.setattr(ui,"accept_snapshot",accept)
    monkeypatch.setattr("requests.sessions.Session.request",Mock(side_effect=AssertionError("No provider")))
    app=AppTest.from_string("import streamlit as st\nfrom langgraphagenticai.ui.verified_research import render_verified_sensitivity\nrender_verified_sensitivity('AAPL','fixture-key')",default_timeout=30)
    app.session_state["verified_sensitivity_snapshot"]=snap
    app.run(); assert not app.exception
    app.number_input[0].set_value(20.).run()
    assert not app.exception and accept.call_count==2
    assert any("No per-share target" in c.value for c in app.caption)
    accept.side_effect=ValueError("Stale")
    app.run()
    assert any("reuse rejected" in w.value for w in app.warning)
    assert app.session_state["verified_sensitivity_snapshot"]==snap


def test_source_action_is_explicit_and_legacy_stays_unbound(monkeypatch):
    state,saved=fixture()
    from langgraphagenticai.ui import verified_research as ui
    snap=create_snapshot(state,saved,"AAPL",ENGINE,"fixture-key",reference_time=REFERENCE)
    create=Mock(return_value=snap)
    monkeypatch.setattr(ui,"create_snapshot",create)
    app=AppTest.from_string("from langgraphagenticai.ui.verified_research import render_verified_handoff\nrender_verified_handoff({'id':'run','request':{'symbols':['AAPL']}},'Standard V1','fixture-key')",default_timeout=30).run()
    assert not app.exception
    assert "verified_sensitivity_snapshot" not in app.session_state
    next(b for b in app.button if b.label=="Use saved verified research").click().run()
    assert not app.exception
    assert app.session_state["verified_sensitivity_snapshot"]==snap
    assert app.session_state["next_workspace"]=="AI Valuation"
    assert app.session_state["pending_company_context"].saved_reference is None
    assert "_verified_research_secret" not in app.session_state
    next(b for b in app.button if b.label=="Open AI Valuation with ticker only").click().run()
    assert app.session_state["verified_sensitivity_active"] is False
    assert app.session_state["verified_sensitivity_snapshot"]==snap
