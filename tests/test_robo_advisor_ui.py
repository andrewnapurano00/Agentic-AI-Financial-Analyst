"""Dedicated Axiom route, legacy-name migration and preserved offline sessions."""
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest


def test_axiom_routes_shared_settings_to_robo_advisor(monkeypatch):
    from langgraphagenticai import main
    from langgraphagenticai.ui import robo_advisor_tab
    renderer=Mock()
    monkeypatch.setattr(robo_advisor_tab,"render_robo_advisor",renderer)
    monkeypatch.setattr(main.LoadStreamlitUI,"load_streamlit_ui",lambda self:dict(active_page="AI Robo Advisor",FMP_API_KEY="fixture-fmp",OPENAI_API_KEY="fixture-ai",selected_model="fixture-model"))
    for name in ("render_market_strip","render_terminal_status","_render_status_panel"):
        monkeypatch.setattr(main,name,lambda *a,**kw:None)
    monkeypatch.setattr(main,"render_command_bar",lambda:"")
    a=AppTest.from_string("from langgraphagenticai.main import load_langgraph_agenticai_app; load_langgraph_agenticai_app()",default_timeout=30).run()
    assert not a.exception
    renderer.assert_called_once_with(fmp_api_key="fixture-fmp",openai_api_key="fixture-ai",model_name="fixture-model")
    assert any("AI Robo Advisor" in m.value for m in a.markdown)


@pytest.mark.parametrize("old_name",["AI Live Agent Traders","Live Traders","Agent Trading Lab","Live Agent Traders"])
def test_sidebar_migrates_trader_name_and_exposes_robo_advisor(old_name):
    a=AppTest.from_string("from langgraphagenticai.ui.streamlitui.loadui import LoadStreamlitUI; LoadStreamlitUI().load_streamlit_ui()",default_timeout=30)
    a.session_state["active_workspace"]=old_name
    a.run()
    assert not a.exception
    assert a.radio(key="active_workspace").value == "AI Robo Advisor"
    assert len(a.radio(key="active_workspace").options) == 10


def test_robo_advisor_has_only_live_architect_and_no_implicit_calls(monkeypatch):
    from langgraphagenticai.ui import portfolio_architect_tab
    forbidden=Mock(side_effect=AssertionError("No external calls"))
    monkeypatch.setattr(portfolio_architect_tab,"collect",forbidden)
    a=AppTest.from_string("from langgraphagenticai.ui.robo_advisor_tab import render_robo_advisor; render_robo_advisor()",default_timeout=30).run()
    assert not a.exception and not a.radio
    assert not any("SYNTHETIC DEMO" in str(x.value) for x in a.info)
    a.button(key="architect_interpret").click().run()
    next(b for b in a.button if b.label == "Build portfolio").click().run()
    assert a.error and "Configure FMP" in a.error[0].value
    a.run()
    forbidden.assert_not_called()
