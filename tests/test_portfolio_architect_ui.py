"""Streamlit interaction/state regressions, fully offline."""
from unittest.mock import Mock
from streamlit.testing.v1 import AppTest
from langgraphagenticai.ui import portfolio_architect_tab as ui
from langgraphagenticai.portfolio_architect import committee

PAGE="""
from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect
render_portfolio_architect()
"""


def prepared():
    a=AppTest.from_string(PAGE,default_timeout=30).run()
    a.button(key="architect_interpret").click().run()
    assert not a.exception
    return a


def build_app(a):
    next(b for b in a.button if b.label == "Build portfolio").click().run()
    assert not a.exception
    return a


def test_demo_interpret_build_save_rerun_no_calls(monkeypatch):
    provider=Mock(side_effect=AssertionError("No live calls"))
    ai=Mock(side_effect=AssertionError("No model calls"))
    monkeypatch.setattr(ui,"collect",provider)
    monkeypatch.setattr(committee,"build_openai_client",ai)
    a=prepared()
    a.checkbox(key="architect_use_ai").check().run()
    build_app(a)
    result=a.session_state["architect_result"]
    assert result["snapshot"]["mode"] == "SYNTHETIC DEMO" and len(result["holdings"]) == 10
    assert len(a.get("download_button")) == 3
    a.button(key="architect_save").click().run()
    assert result["id"] in a.session_state["architect_saved"]
    a.run()
    assert result == a.session_state["architect_result"]
    provider.assert_not_called();ai.assert_not_called()


def test_live_missing_credentials_preserves_previous_result(monkeypatch):
    provider=Mock(side_effect=AssertionError("No call"));monkeypatch.setattr(ui,"collect",provider)
    a=build_app(prepared())
    before=a.session_state["architect_result"]
    a.radio(key="architect_mode").set_value("FMP live").run()
    build_app(a)
    assert a.error and "Configure FMP" in a.error[0].value
    assert before == a.session_state["architect_result"]
    provider.assert_not_called()


def test_revised_prompt_requires_interpret_and_editor_validates():
    a=prepared()
    a.text_area(key="architect_prompt").set_value("A revised defensive portfolio question").run()
    assert any("differs" in v.value for v in a.caption)
    a.number_input(key="architect_edit_1_holdings").set_value(5)
    a.number_input(key="architect_edit_1_cap").set_value(5.)
    build_app(a)
    assert a.error and "infeasible" in a.error[0].value


def test_entrypoint_navigation_preserves_demo_session(monkeypatch):
    from pathlib import Path
    a=AppTest.from_file(Path(__file__).resolve().parents[1]/"portfolio_architect_app.py",default_timeout=30).run()
    assert not a.exception
    a.button(key="architect_interpret").click().run()
    build_app(a)
    before=a.session_state["architect_result"]
    a.radio(key="architect_workspace").set_value("Agent Trading Lab").run()
    assert not a.exception and any(s.value == "Agent Trading Lab" for s in a.subheader)
    a.radio(key="architect_workspace").set_value("AI Portfolio Architect").run()
    assert not a.exception and before == a.session_state["architect_result"]


def test_failed_provider_collection_shows_causes_and_keeps_saved_result(monkeypatch):
    from langgraphagenticai.portfolio_architect.schemas import EvidenceSnapshot
    failed=EvidenceSnapshot(id='fixture-failed',mode='FMP live',retrieved_at='2026-10-19T12:00:00+00:00',
        securities=[],benchmark=None,warnings=['FMP batch-quote: HTTP 402: endpoint access unavailable for the configured FMP plan.'],
        excluded={'MSFT':'Unique quote unavailable; check provider access or collection warnings.'},universe_version='fixture')
    loader=Mock(return_value=failed);monkeypatch.setattr(ui,'collect',loader)
    a=AppTest.from_string("from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect; render_portfolio_architect(fmp_api_key='fixture-key')",default_timeout=30).run()
    a.button(key='architect_interpret').click().run();build_app(a)
    saved=a.session_state['architect_result']
    a.radio(key='architect_mode').set_value('FMP live').run();build_app(a)
    assert a.error and 'provider validation' in a.error[0].value
    assert a.session_state['architect_result']==saved
    assert any(e.label=='Latest collection diagnostics' for e in a.expander)
    assert any('HTTP 402' in m.value for m in a.markdown)
    assert any('Unique quote unavailable' in str(d.value) for d in a.dataframe)
    a.run();loader.assert_called_once()
