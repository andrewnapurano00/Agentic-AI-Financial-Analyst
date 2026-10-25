"""Unified navigation, provider and concise export contracts, entirely offline."""
from copy import deepcopy
from datetime import date
from unittest.mock import Mock
from streamlit.testing.v1 import AppTest
from langgraphagenticai.deep_research.quarterly_data import QuarterlyFinancialDataSource
from langgraphagenticai.deep_research.models import ResearchRequest
from langgraphagenticai.deep_research.report_basis import report_basis_notes


def test_format_switch_preserves_histories_without_running_models(monkeypatch):
    from langgraphagenticai.ui import deep_research_tab, deep_research_v2_tab
    standard, economy = Mock(), Mock()
    monkeypatch.setattr(deep_research_tab, "render_deep_research_tab", standard)
    monkeypatch.setattr(deep_research_v2_tab, "render_deep_research_v2_tab", economy)
    app = AppTest.from_string('''
import streamlit as st
from langgraphagenticai.ui.deep_research_workspace import render_deep_research_workspace
st.session_state["deep_research_intent_preview"] = False
st.session_state.setdefault("dr_history", [{"id":"standard"}])
st.session_state.setdefault("drv2_history", [{"id":"economy"}])
render_deep_research_workspace(openai_api_key="", model_name="test", fmp_api_key="")
''', default_timeout=30).run()
    assert not app.exception and standard.call_count == 1 and economy.call_count == 0
    app.radio(key="deep_research_format_control").set_value("Low cost format").run()
    assert not app.exception and economy.call_count == 1
    app.run()
    assert app.session_state["deep_research_format"] == "Low cost format"
    app.radio(key="deep_research_format_control").set_value("Standard format").run()
    assert app.session_state["dr_history"] == [{"id":"standard"}]
    assert app.session_state["drv2_history"] == [{"id":"economy"}]


def test_legacy_navigation_selects_low_cost(monkeypatch):
    from langgraphagenticai.ui.streamlitui import loadui
    monkeypatch.setattr(loadui, "_resolve_secret", lambda *_: "")
    app=AppTest.from_string('''
from langgraphagenticai.ui.streamlitui.loadui import LoadStreamlitUI
LoadStreamlitUI().load_streamlit_ui()
''', default_timeout=30)
    app.session_state["active_workspace"]="Deep Research V2"
    app.run()
    assert not app.exception
    assert app.session_state["active_workspace"]=="Deep Research"
    assert app.session_state["deep_research_format"]=="Low cost format"
    assert "Deep Research V2" not in app.radio(key="active_workspace").options


def test_v3_estimates_annual_identity_zero_and_source():
    source=QuarterlyFinancialDataSource("synthetic")
    def fetch(url, *, api_key, params):
        if "/analyst-estimates/" in url:
            assert url=="https://financialmodelingprep.com/api/v3/analyst-estimates/AAPL"
            assert params["period"]=="annual"
            return [{"symbol":"AAPL","date":"2090-09-30","estimatedRevenueAvg":100,"estimatedEpsAvg":0},
                    {"symbol":"MSFT","date":"2090-09-30","estimatedRevenueAvg":999},
                    {"symbol":"AAPL","date":"2000-09-30","estimatedRevenueAvg":1}]
        return []
    source.fetch_json=fetch
    evidence=source.collect(ResearchRequest(["AAPL"]),lambda _:None)
    estimates=next(e for e in evidence if e.category=="estimates")
    assert estimates.status=="ok" and len(estimates.data)==1
    assert estimates.data[0]["estimatedEpsAvg"]==0
    assert "/api/v3/analyst-estimates/AAPL" in estimates.url
    assert "synthetic" not in estimates.url


def test_coverage_discloses_relevant_gaps_without_mutating_audit():
    result={"comparison":[{"Ticker":"AAPL","ROIC":None,"ARPU":None,"Metric contracts":{
        "ROIC":{"status":"unsupported","applicability":"applicable"},
        "ARPU":{"status":"unsupported","applicability":"inapplicable"}}}],
        "sector_frameworks":[{"symbol":"AAPL","must_have":["ROIC","ARPU"]}]}
    saved=deepcopy(result)
    notes=" ".join(report_basis_notes(result))
    assert "ROIC" in notes and "ARPU" not in notes
    assert "audit JSON" in notes and result==saved
