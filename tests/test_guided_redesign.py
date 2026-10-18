"""Saved-first Guided Research presentation, with explicit-only call checks."""

from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from langgraphagenticai.research.guided_workflow import config, fingerprint
from langgraphagenticai.ui import guided_research_tab as ui


HARNESS = '''
from langgraphagenticai.ui.guided_research_tab import render_guided_research_tab
render_guided_research_tab(openai_api_key="synthetic", model_name="synthetic")
'''


def test_saved_guided_result_keeps_setup_and_evidence_without_prepare_or_run(monkeypatch):
    prepare = Mock()
    run = Mock()
    monkeypatch.setattr(ui, "prepare", prepare)
    monkeypatch.setattr(ui, "run", run)
    question = "What do the business, latest annual financials and recent news establish?"
    cfg = config("AAPL", question, "synthetic", 1.0, None, None, True)
    saved = {
        "run_id": "saved-run", "config_fingerprint": fingerprint(cfg),
        "plan_fingerprint": "plan-fingerprint", "plan": {"steps": [{"tool": "quote_profile", "purpose": "Check identity"}]},
        "usage": {"model_attempts": 1, "reserved_cost": None},
    }
    result = {
        "run_id": "saved-run", "config_fingerprint": fingerprint(cfg),
        "plan_fingerprint": "plan-fingerprint", "evidence": [],
        "evidence_fingerprint": fingerprint([]), "answer": {
            "interpretation": "Saved synthetic interpretation.", "facts": [],
            "missing_inputs": ["Recent news"], "risks": ["Evidence gap"],
        }, "warnings": ["Synthetic partial evidence"], "steps": [], "usage": saved["usage"],
    }
    app = AppTest.from_string(HARNESS, default_timeout=30)
    app.session_state["guided_plan"] = saved
    app.session_state["guided_result"] = result
    app.session_state["guided_widget_values"] = {"guided_unknown_ack": True}
    app.run()
    assert not app.exception
    assert any(item.label == "Configure guided research" for item in app.expander)
    assert any(item.label == "Spend limits and pricing" for item in app.expander)
    assert any("Saved AI interpretation" in item.value for item in app.markdown)
    assert any("Saved synthetic interpretation" in item.value for item in app.markdown)
    assert any("Synthetic partial evidence" in item.value for item in app.warning)
    assert any(item.label == "Download saved evidence and answer" for item in app.get("download_button"))
    app.run()
    assert app.checkbox(key="guided_unknown_ack").value
    prepare.assert_not_called()
    run.assert_not_called()
