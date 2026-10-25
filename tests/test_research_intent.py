"""Offline intent adapters: actual forms, saved histories and zero implicit calls."""
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.ui.research_intent import PRESETS, intent_defaults, saved_sections
from test_deep_research_ui import sample_result
from test_deep_research_v2_recovery import saved, widget

HARNESS = '''
from langgraphagenticai.ui.deep_research_workspace import render_deep_research_workspace
render_deep_research_workspace(openai_api_key="synthetic", model_name="synthetic", fmp_api_key="synthetic")
'''


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("engine", ["Standard format", "Low cost format"])
def test_real_preset_forms_submit_only_explicitly(monkeypatch, preset, engine):
    from langgraphagenticai.ui import deep_research_tab as v1, deep_research_v2_tab as v2
    calls = []
    def factory(*args, **kwargs):
        def run(request, context):
            calls.append(request)
            result = sample_result() if engine == "Standard format" else saved()
            result["request"] = asdict(request)
            return result
        return Mock(run=run)
    monkeypatch.setattr(v1, "_manager", factory)
    monkeypatch.setattr(v2, "_manager_v2", factory)
    monkeypatch.setattr(v1, "run_investment_committee", Mock(return_value={"summary": "Saved committee"}))
    monkeypatch.setattr(v2, "run_decision", Mock(side_effect=lambda result, **kwargs: result))
    monkeypatch.setattr(v1, "build_research_pdf", lambda *_: b"PDF")
    monkeypatch.setattr(v2, "build_research_pdf", lambda *_: b"PDF")
    app = AppTest.from_string(HARNESS, default_timeout=40)
    app.session_state["deep_research_intent_preview"] = True
    app.session_state["deep_research_intent"] = preset
    app.session_state["deep_research_engine_override"] = engine
    app.run()
    assert not app.exception and not calls
    defaults = intent_defaults(preset, engine)
    assert widget(app, "selectbox", "Research depth").value == defaults["depth"]
    if engine == "Standard format":
        assert widget(app, "checkbox", "Enable CrewAI investment committee").value == defaults["committee"]
        label = "Start deep research"
    else:
        assert widget(app, "selectbox", "Cost mode").value == defaults["mode"]
        assert widget(app, "selectbox", "Decision stage").value == ("Full committee" if defaults["committee"] else "None")
        label = "Run V2 pilot"
    app.run()
    assert not calls
    widget(app, "button", label).click().run()
    assert not app.exception and not app.error and len(calls) == 1
    assert calls[0].depth == defaults["depth"]
    app.run()
    assert not app.exception and len(calls) == 1
    assert any("Research overview" in m.value for m in app.markdown)


def test_switch_and_rollback_preserve_both_saved_histories(monkeypatch):
    from langgraphagenticai.ui import deep_research_tab as v1, deep_research_v2_tab as v2
    services = Mock(side_effect=AssertionError("Display must not call services"))
    for module, name in [(v1, "_manager"), (v2, "_manager_v2"), (v1, "run_investment_committee"), (v2, "run_decision")]:
        monkeypatch.setattr(module, name, services)
    monkeypatch.setattr(v2, "build_research_pdf", lambda *_: b"PDF")
    a, b = sample_result(), saved("incomplete")
    app = AppTest.from_string(HARNESS, default_timeout=40)
    app.session_state["dr_history"] = [deepcopy(a)]
    app.session_state["drv2_history"] = [deepcopy(b)]
    app.run()
    app.checkbox(key="deep_research_intent_preview").check().run()
    app.radio(key="deep_research_intent_control").set_value("Quick Brief").run()
    assert not app.exception
    assert any("Partial or unfinished" in w.value for w in app.warning)
    app.radio(key="deep_research_intent_control").set_value("Investment Committee").run()
    app.checkbox(key="deep_research_intent_preview").uncheck().run()
    assert not app.exception
    assert app.session_state["dr_history"][0]["report"] == a["report"]
    assert app.session_state["drv2_history"][0]["evidence"] == b["evidence"]
    assert app.radio(key="deep_research_format_control").value == "Standard format"
    services.assert_not_called()


def test_section_adapter_keeps_missing_explicit_and_does_not_mutate():
    result = {"report": "## Thesis\nHold.\n## Valuation\nP/E assumption.\n## Risks\nLoss possible."}
    original = deepcopy(result)
    sections = saved_sections(result)
    assert "P/E assumption" in sections["Valuation implications"]
    assert not sections["Competing perspectives"] and not sections["Research gaps"]
    assert result == original
    assert not any(saved_sections({}).values())
    with pytest.raises(ValueError):
        intent_defaults("unknown")


@pytest.mark.parametrize("engine", ["Standard format", "Low cost format"])
def test_failed_new_run_preserves_saved_result_and_does_not_retry(monkeypatch, engine):
    from langgraphagenticai.ui import deep_research_tab as v1, deep_research_v2_tab as v2
    manager = Mock()
    manager.run.side_effect = TimeoutError("Synthetic model timeout")
    factory = Mock(return_value=manager)
    monkeypatch.setattr(v1, "_manager", factory)
    monkeypatch.setattr(v2, "_manager_v2", factory)
    monkeypatch.setattr(v2, "build_research_pdf", lambda *_: b"PDF")
    result = sample_result() if engine == "Standard format" else saved()
    history = "dr_history" if engine == "Standard format" else "drv2_history"
    app = AppTest.from_string(HARNESS, default_timeout=40)
    app.session_state[history] = [deepcopy(result)]
    app.session_state["deep_research_intent_preview"] = True
    app.session_state["deep_research_engine_override"] = engine
    app.run()
    label = "Start deep research" if engine == "Standard format" else "Run V2 pilot"
    widget(app, "button", label).click().run()
    assert not app.exception and app.error
    assert app.session_state[history][0]["report"] == result["report"]
    app.run()
    manager.run.assert_called_once()


@pytest.mark.parametrize("engine", ["Standard format", "Low cost format"])
@pytest.mark.parametrize("failure", [False, True])
def test_explicit_saved_continuation_preserves_evidence_and_never_collects(monkeypatch, engine, failure):
    from langgraphagenticai.ui import deep_research_tab as v1, deep_research_v2_tab as v2
    result = sample_result() if engine == "Standard format" else saved("incomplete")
    result["status"] = "incomplete"
    result["report"] = "## Retained report\nSubstantial original research."
    result["draft"] = result["report"]
    result["report_mode"] = "single_pass"
    original = deepcopy(result)
    def resume(value):
        assert value == original
        value["status"] = "incomplete" if failure else "complete"
        value["report"] = "## Continued report\nRecovered thesis."
        return value
    manager = Mock(); manager.resume.side_effect = resume
    factory = Mock(return_value=manager)
    monkeypatch.setattr(v1, "_manager", factory)
    monkeypatch.setattr(v2, "_manager_v2", factory)
    monkeypatch.setattr(v2, "build_research_pdf", lambda *_: b"PDF")
    decisions = Mock(side_effect=AssertionError("Recovery must not run a committee"))
    monkeypatch.setattr(v1, "run_investment_committee", decisions)
    monkeypatch.setattr(v2, "run_decision", decisions)
    app = AppTest.from_string(HARNESS, default_timeout=40)
    history = "dr_history" if engine == "Standard format" else "drv2_history"
    app.session_state[history] = [deepcopy(result)]
    app.session_state["deep_research_engine_override"] = engine
    app.run()
    button = widget(app, "button", "Continue report using saved evidence")
    assert button.disabled
    factory.assert_not_called()
    widget(app, "checkbox", "Use the saved evidence without refreshing, including any legacy or stale inputs").check().run()
    factory.assert_not_called()
    widget(app, "button", "Continue report using saved evidence").click().run()
    assert not app.exception
    final = app.session_state[history][0]
    assert final["evidence"] == original["evidence"]
    assert final["report"] == (original["report"] if failure else "## Continued report\nRecovered thesis.")
    assert bool(app.error) == failure
    if not failure:
        assert final["continuation_original"]["report"] == original["report"]
    app.run()
    manager.resume.assert_called_once()
    manager.run.assert_not_called()
    assert factory.call_args.kwargs["saved"]
    decisions.assert_not_called()


def test_unified_default_and_combined_saved_selector(monkeypatch):
    from langgraphagenticai.ui import deep_research_tab as v1, deep_research_v2_tab as v2
    standard, pilot = Mock(), Mock()
    monkeypatch.setattr(v1, "render_deep_research_tab", standard)
    monkeypatch.setattr(v2, "render_deep_research_v2_tab", pilot)
    app = AppTest.from_string(HARNESS, default_timeout=40)
    app.session_state["dr_history"] = [sample_result()]
    app.session_state["drv2_history"] = [saved()]
    app.run()
    assert app.checkbox(key="deep_research_intent_preview").value
    assert standard.call_args.kwargs["intent"]["preset"] == "Deep Dive"
    app.selectbox(key="deep_research_saved_control").set_value("Low cost format:v2-test").run()
    assert not app.exception
    assert app.session_state["drv2_active_run"] == "v2-test"
    assert pilot.call_count == 1
    app.checkbox(key="deep_research_intent_preview").uncheck().run()
    assert app.radio(key="deep_research_format_control").value == "Low cost format"


def test_failed_recovery_keeps_budget_reservations_and_original_report():
    from langgraphagenticai.ui.research_intent import recover_saved
    original = saved("incomplete")
    manager = Mock()
    manager.diagnostics = [{"stage": "draft", "estimated_cost_usd": .12}]
    manager.resume.side_effect = TimeoutError("Synthetic timeout")
    result = recover_saved(original, manager)
    assert result["report"] == original["report"] and result["evidence"] == original["evidence"]
    assert result["diagnostics"] == manager.diagnostics
    assert result["estimated_model_cost_usd"] == .12 and result["continuation_error"]
    assert "continuation_error" not in original


def test_standard_saved_manager_does_not_construct_collection_tools(monkeypatch):
    from langgraphagenticai.ui import deep_research_tab as ui
    tools = Mock(side_effect=AssertionError("Recovery must not construct collection tools"))
    monkeypatch.setattr(ui, "get_finance_tools", tools)
    monkeypatch.setattr(ui.OpenAILLM, "get_llm_model", lambda *_: Mock())
    manager = ui._manager("synthetic", "synthetic", "", "", "", saved=True)
    assert not manager.tools
    tools.assert_not_called()
