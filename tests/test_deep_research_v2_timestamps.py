"""D01-D03: offline saved-operation timestamps, distinct from evidence freshness."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.deep_research.quarterly_ttm import METHODOLOGY
from langgraphagenticai.deep_research.models import Evidence, ResearchRequest
from langgraphagenticai.deep_research.v2 import stage_configuration
from langgraphagenticai.deep_research.v2_timestamps import (
    format_saved_time, saved_result_caption, stamp_saved_result,
)
from langgraphagenticai.ui import deep_research_v2_tab as ui

NOW = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
HARNESS = '''
from langgraphagenticai.ui.deep_research_v2_tab import render_deep_research_v2_tab
render_deep_research_v2_tab(openai_api_key="synthetic", fmp_api_key="synthetic")
'''


def saved(status="complete"):
    return {"id": "timestamp-test", "created_at": None, "status": status,
            "financial_methodology": METHODOLOGY,
            "request": asdict(ResearchRequest(["AAPL"], include_news=False)),
            "report": "", "draft": "", "evidence": [Evidence(
                "E001", "AAPL", "income", "Income", "Synthetic", [{"revenue": 5}]).to_dict()],
            "comparison": [], "warnings": [], "gaps": [], "diagnostics": [], "plan": {},
            "cost_mode": "Economy", "v2_config": stage_configuration("Economy", light_provider="OpenAI"),
            "v2_runtime": {"budget": .35, "decision_mode": "None"}}


@pytest.mark.parametrize("value", [None, "", 42, {}, "bad", "2026-10-04T12:00:00"])
def test_legacy_and_invalid_timestamp_unavailable(value):
    assert format_saved_time(value) == "unavailable"
    assert "unavailable" in saved_result_caption({"result_generated_at": value}, now=NOW)


@pytest.mark.parametrize("value", ["2026-10-04T12:00:00Z", "2026-10-04T08:00:00-04:00"])
def test_offsets_and_z_normalize_to_utc(value):
    assert format_saved_time(value) == "2026-10-04 12:00:00 UTC"


@pytest.mark.parametrize("seconds, expected", [(20, "less than 1 minute"), (60, "1 minute ago"),
    (120, "2 minutes ago"), (3600, "1 hour ago"), (7200, "2 hours ago"),
    (86400, "1 day ago"), (172800, "2 days ago"), (-60, "clock mismatch")])
def test_age_units(seconds, expected):
    caption = saved_result_caption({"result_generated_at": (NOW-timedelta(seconds=seconds)).isoformat()}, now=NOW)
    assert expected in caption
    assert "Evidence dates may differ" in caption


def test_completion_stamp_merges_checkpoint_without_rewriting_stage_times():
    checkpoint = {**saved("incomplete"), "updated_at": "stage", "saved_only": True}
    result = {"id": checkpoint["id"], "status": "evidence_ready"}
    history = stamp_saved_result(result, [checkpoint, {"id": "other"}], now=NOW)
    assert result["result_generated_at"] == NOW.isoformat()
    assert result["created_at"] is None and result["updated_at"] == "stage"
    assert history[0] == result and history[1]["id"] == "other"
    assert checkpoint.get("result_generated_at") is None


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(ui, "build_research_pdf", lambda _: b"synthetic PDF")
    return AppTest.from_string(HARNESS, default_timeout=30)


def button(app, label):
    return next(w for w in app.button if w.label == label)


@pytest.mark.parametrize("timestamp", [None, "2026-10-02T12:00:00Z"])
def test_history_rerun_is_read_only_and_legacy_safe(app, monkeypatch, timestamp):
    result = saved()
    if timestamp: result["result_generated_at"] = timestamp
    app.session_state["drv2_history"] = [result]
    factory = Mock(); monkeypatch.setattr(ui, "_manager_v2", factory)
    app.run(); app.run()
    assert not app.exception
    factory.assert_not_called()
    assert app.session_state["drv2_history"][0] == result
    captions = [w.value for w in app.caption]
    assert any("Saved result generated:" in c for c in captions)
    assert any(("2026-10-02 12:00:00 UTC" if timestamp else "unavailable") in c for c in captions)


def test_generation_stamps_before_decision_and_cache_reuses(app, monkeypatch):
    manager = Mock()
    def factory(**kwargs):
        def run(request, context):
            result = saved(); result["request"] = asdict(request)
            kwargs["checkpoint"](result)
            return result
        manager.run.side_effect = run
        return manager
    factory_mock = Mock(side_effect=factory)
    monkeypatch.setattr(ui, "_manager_v2", factory_mock)
    app.run(); button(app, "Run V2 pilot").click().run()
    assert not app.exception
    timestamp = app.session_state["drv2_history"][0]["result_generated_at"]
    assert format_saved_time(timestamp) != "unavailable"
    app.run(); button(app, "Run V2 pilot").click().run()
    assert not app.exception
    assert app.session_state["drv2_history"][0]["result_generated_at"] == timestamp
    manager.run.assert_called_once()
    factory_mock.assert_called_once()


def test_saved_evidence_recovery_advances_only_on_action(app, monkeypatch):
    original = {**saved("evidence_ready"), "result_generated_at": "2026-10-01T12:00:00Z"}
    app.session_state["drv2_history"] = [original]
    manager = Mock(); manager.resume.return_value = {**original, "status": "complete"}
    factory = Mock(return_value=manager); monkeypatch.setattr(ui, "_manager_v2", factory)
    app.run()
    factory.assert_not_called()
    recover = next(w for w in app.button if w.label.startswith("Generate report"))
    recover.click().run()
    assert not app.exception
    timestamp = app.session_state["drv2_history"][0]["result_generated_at"]
    assert timestamp != original["result_generated_at"]
    app.run()
    assert app.session_state["drv2_history"][0]["result_generated_at"] == timestamp
    manager.resume.assert_called_once(); manager.run.assert_not_called()


def test_optional_decision_failure_preserves_returned_timestamp(app, monkeypatch):
    manager = Mock()
    def factory(**kwargs):
        def run(request, context):
            result = saved(); result.update(request=asdict(request), report="Synthetic saved report")
            kwargs["checkpoint"](result)
            return result
        manager.run.side_effect = run
        return manager
    monkeypatch.setattr(ui, "_manager_v2", factory)
    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic decision failure")
    if hasattr(ui, "run_decision"):
        monkeypatch.setattr(ui, "run_decision", fail)
    else:
        monkeypatch.setattr(ui, "build_stage_llm", fail)
    app.run()
    next(w for w in app.selectbox if w.label == "Decision stage").set_value("Quick decision")
    button(app, "Run V2 pilot").click().run()
    assert not app.exception
    result = app.session_state["drv2_history"][0]
    assert result["report"] == "Synthetic saved report"
    timestamp = result["result_generated_at"]
    assert format_saved_time(timestamp) != "unavailable"
    app.run()
    assert app.session_state["drv2_history"][0]["result_generated_at"] == timestamp
    manager.run.assert_called_once()


def test_history_selection_preserves_each_run_time(app, monkeypatch):
    current = {**saved(), "result_generated_at": "2026-10-02T12:00:00Z"}
    legacy = {**saved(), "id": "legacy-run"}
    app.session_state["drv2_history"] = [current, legacy]
    factory = Mock(); monkeypatch.setattr(ui, "_manager_v2", factory)
    app.run()
    next(w for w in app.selectbox if w.label == "V2 run history").set_value("legacy-run").run()
    assert not app.exception
    assert any("Saved result generated: unavailable" in w.value for w in app.caption)
    next(w for w in app.selectbox if w.label == "V2 run history").set_value(current["id"]).run()
    assert not app.exception
    assert any("Saved result generated: 2026-10-02 12:00:00 UTC" in w.value for w in app.caption)
    assert app.session_state["drv2_history"] == [current, legacy]
    factory.assert_not_called()
