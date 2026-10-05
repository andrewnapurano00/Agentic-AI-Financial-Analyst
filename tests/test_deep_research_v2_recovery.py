"""Offline AAFA-2 contracts: real V2 controls and isolated stage recovery."""
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.deep_research import v2_workflow as workflow
from langgraphagenticai.deep_research.manager import ResearchManager
from langgraphagenticai.deep_research.models import Evidence, ResearchRequest
from langgraphagenticai.deep_research.v2 import V2ConfigurationError, report_instruction, stage_configuration, validate_report
from langgraphagenticai.tools.serper_tools import SerperClient
from langgraphagenticai.ui import deep_research_v2_tab as ui

REPORT = "## Executive Investment Thesis\nAAPL is assessed in USD as of 2026-06-30 [E001].\n## Risks\nRisk.\n## Thesis invalidation\nCash flow weakens."
HARNESS = '''
from langgraphagenticai.ui.deep_research_v2_tab import render_deep_research_v2_tab
render_deep_research_v2_tab(openai_api_key="synthetic", fmp_api_key="synthetic")
'''


def saved(status="complete"):
    return {"financial_methodology": "quarterly-ttm-v1", "id": "v2-test", "created_at": "2026-10-02T12:00:00Z", "status": status,
            "request": asdict(ResearchRequest(["AAPL"], include_news=False)),
            "report": REPORT if status in {"complete", "review_pending", "needs_review"} else "",
            "draft": REPORT if status in {"complete", "review_pending", "needs_review"} else "",
            "markdown": REPORT, "evidence": [Evidence("E001", "AAPL", "income", "Income", "Synthetic", [{"revenue": 5}]).to_dict()],
            "comparison": [], "warnings": [], "gaps": [], "diagnostics": [], "plan": {},
            "cost_mode": "Economy", "v2_config": stage_configuration("Economy", light_provider="OpenAI"),
            "v2_runtime": {"budget": .35, "ollama_base_url": "http://localhost:11434/v1", "decision_mode": "None"}}


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(ui, "build_research_pdf", lambda _: b"synthetic PDF")
    return AppTest.from_string(HARNESS, default_timeout=30)


def widget(app, group, label):
    return next(w for w in getattr(app, group) if w.label == label)


@pytest.mark.parametrize("status,label", [("incomplete", "Retry report writing"), ("review_pending", "Retry review"), ("evidence_ready", "Generate report from saved evidence")])
def test_recovery_uses_saved_runtime_and_preserves_history(app, monkeypatch, status, label):
    first = saved(status); first["warnings"] = ["Saved failure reason"]
    second = saved(); second["id"] = "other"
    app.session_state["drv2_history"] = [first, second]
    app.session_state["drv2_active_run"] = first["id"]
    manager = Mock(); manager.resume.return_value = {**first, "status": "complete", "report": REPORT, "draft": REPORT}
    factory = Mock(return_value=manager); monkeypatch.setattr(ui, "_manager_v2", factory)
    app.run()
    assert not app.exception
    assert any("Saved failure reason" in w.value for w in app.warning)
    if status != "evidence_ready": assert not any("research ready" in w.value for w in app.success)
    widget(app, "button", label).click().run()
    assert not app.exception
    assert factory.call_args.kwargs["saved"]["id"] == first["id"]
    assert factory.call_args.kwargs["budget"] == .35
    manager.resume.assert_called_once(); manager.run.assert_not_called()
    assert len(app.session_state["drv2_history"]) == 2
    assert app.session_state["drv2_history"][0]["v2_runtime"] == first["v2_runtime"]
    app.run()
    assert manager.resume.call_count == 1


def test_missing_evidence_has_actionable_message_without_useless_retry(app):
    result = saved("incomplete"); result["evidence"] = []; result["gaps"] = ["AAPL / income: unavailable"]
    app.session_state["drv2_history"] = [result]
    app.run()
    assert not app.exception
    assert any("No usable company evidence" in i.value for i in app.info)
    assert not any("Retry" in b.label for b in app.button)


def test_submission_and_saved_reuse_do_not_repeat_calls(app, monkeypatch):
    manager = Mock(); calls = []
    def factory(**kwargs):
        calls.append(kwargs)
        def run(request, context):
            result = saved(); result["request"] = asdict(request)
            kwargs["checkpoint"](result)
            return result
        manager.run.side_effect = run
        return manager
    monkeypatch.setattr(ui, "_manager_v2", factory)
    app.run(); widget(app, "button", "Run V2 pilot").click().run()
    assert not app.exception
    assert app.session_state["drv2_active_run"] == "v2-test"
    assert any("V2 research ready" in i.value for i in app.success)
    assert len(app.get("download_button")) == 3
    app.run(); widget(app, "button", "Run V2 pilot").click().run()
    assert len(calls) == 1
    assert any("Reused" in i.value for i in app.info)
    widget(app, "number_input", "Maximum estimated model cost (USD)").set_value(.40)
    widget(app, "button", "Run V2 pilot").click().run()
    assert len(calls) == 2  # Changed runtime must not reuse an incompatible result.


def test_invalid_ticker_stops_before_factory(app, monkeypatch):
    factory = Mock(); monkeypatch.setattr(ui, "_manager_v2", factory)
    app.run(); widget(app, "text_input", "Companies").set_value("BAD/TICKER")
    widget(app, "button", "Run V2 pilot").click().run()
    factory.assert_not_called()
    assert any("Use ticker symbols" in e.value for e in app.error)


def test_missing_selected_provider_has_safe_specific_error(app):
    app.run(); widget(app, "selectbox", "Light-stage provider").set_value("Groq")
    widget(app, "button", "Run V2 pilot").click().run()
    assert not app.exception
    assert any("Plan / Groq: GROQ_API_KEY is required" in e.value for e in app.error)
    assert app.session_state["drv2_history"] == []


@pytest.mark.parametrize("status", ["incomplete", "review_pending", "needs_review", "evidence_ready"])
def test_ineligible_report_cannot_trigger_decision(monkeypatch, status):
    result = saved(status); result["v2_runtime"]["decision_mode"] = "Quick decision"
    call = Mock(); monkeypatch.setattr(workflow, "build_stage_llm", call)
    updated = workflow.run_decision(result, openai_api_key="synthetic")
    call.assert_not_called()
    assert updated["status"] == status
    assert updated["decision_status"] == "waiting_for_report"


@pytest.mark.parametrize("mode", ["Quick decision", "Full committee"])
def test_decision_failure_retains_report_and_cost_reservation(monkeypatch, mode):
    result = saved(); result["v2_runtime"]["decision_mode"] = mode
    monkeypatch.setattr(workflow, "preflight", lambda *a, **k: None)
    monkeypatch.setattr(workflow, "build_stage_llm", lambda *a, **k: Mock())
    monkeypatch.setattr(workflow, "run_quick_decision", Mock(side_effect=TimeoutError()))
    monkeypatch.setattr(workflow, "run_investment_committee", Mock(side_effect=TimeoutError()))
    updated = workflow.run_decision(result, openai_api_key="synthetic")
    assert updated["report"] == REPORT and updated["status"] == "complete"
    assert updated["decision_status"] == "failed"
    assert "timed out" in updated["decision_error"]
    assert updated["estimated_model_cost_usd"] > 0
    assert result.get("decision_status") is None


def test_budget_blocked_decision_makes_no_call(monkeypatch):
    result = saved(); result["v2_runtime"].update(decision_mode="Quick decision", budget=.00001)
    call = Mock(); monkeypatch.setattr(workflow, "build_stage_llm", call)
    updated = workflow.run_decision(result, openai_api_key="synthetic")
    call.assert_not_called()
    assert updated["diagnostics"][-1]["status"] == "blocked"
    assert "budget" in updated["decision_error"]


def test_ui_decision_failure_keeps_report_and_retry(app, monkeypatch):
    result = saved(); result["v2_runtime"]["decision_mode"] = "Quick decision"
    result.update(decision_status="failed", decision_error="The model request timed out.")
    app.session_state["drv2_history"] = [result]
    retry = Mock(return_value={**result, "decision_status": "complete", "decision_error": ""})
    monkeypatch.setattr(ui, "run_decision", retry)
    app.run()
    assert any("report is preserved" in i.value for i in app.warning)
    assert any("Executive Investment Thesis" in i.value for i in app.markdown)
    widget(app, "button", "Retry decision").click().run()
    assert not app.exception
    retry.assert_called_once()
    assert app.session_state["drv2_history"][0]["report"] == REPORT


def factory_args():
    return dict(request=ResearchRequest(["AAPL"], include_news=False),
                config=stage_configuration("Economy", light_provider="OpenAI"),
                openai_api_key="synthetic", groq_api_key="", fmp_api_key="", serper_api_key="",
                marketaux_api_key="", ollama_base_url="http://localhost:11434/v1", budget=.35, stop_after_evidence=False)


def test_lazy_factory_and_review_resume_only_construct_required_model(monkeypatch):
    args = factory_args(); args["saved"] = saved("review_pending")
    args["saved"]["request"] = asdict(args["request"])
    fake = Mock(); fake.invoke.return_value = SimpleNamespace(content='{"corrections": [], "unresolved": []}')
    build = Mock(return_value=fake); monkeypatch.setattr(workflow, "build_stage_llm", build)
    tools = Mock(); monkeypatch.setattr(workflow, "get_finance_tools", tools)
    manager = workflow.build_manager(**args)
    build.assert_not_called(); tools.assert_not_called()
    result = manager.resume(args["saved"])
    assert result["status"] == "complete"
    assert build.call_count == 1 and build.call_args.args[1] == "gpt-5-nano"
    assert fake.invoke.call_count == 1


@pytest.mark.parametrize("kind", ["empty", "length", "timeout", "malformed_review", "budget"])
def test_real_manager_generation_failures_remain_recoverable(kind):
    llm = Mock(); llm.model_name = "gpt-5-mini"
    source = Mock(); source.collect.return_value = [Evidence("", "AAPL", "income", "Income", "Synthetic", [{"revenue": 5}])]
    llm.invoke.side_effect = [SimpleNamespace(content='{}'), SimpleNamespace(content='not valid JSON')]
    content = "" if kind == "empty" else REPORT
    if kind == "timeout":
        llm.stream.side_effect = TimeoutError()
    else:
        llm.stream.return_value = iter([SimpleNamespace(content=content, response_metadata={"finish_reason": "length" if kind == "length" else "stop"})])
    config = factory_args()["config"]
    manager = ResearchManager(llm, source, SerperClient(""), on_text=lambda _: None,
        stage_limits={**config["limits"], "draft": (150, 1800)}, stage_options={"draft": {"reasoning_effort": "minimal"}},
        report_instruction=lambda req: report_instruction(req, config), deterministic_validator=validate_report,
        interpretive_review=kind == "malformed_review", max_estimated_cost_usd=.00001 if kind == "budget" else .35)
    result = manager.run(ResearchRequest(["AAPL"], include_news=False))
    assert result["status"] == ("review_pending" if kind == "malformed_review" else "incomplete")
    assert result["evidence"] and result["warnings"]
    if kind == "length": assert result["partial_draft"] == REPORT
    if kind == "budget":
        llm.stream.assert_not_called()
        assert any(d["status"] == "blocked" and d["stage"] == "draft" for d in result["diagnostics"])
    if kind not in {"timeout", "budget"}:
        assert llm.stream.call_args.kwargs["reasoning_effort"] == "minimal"
        assert "at most 540 words" in llm.stream.call_args.args[0][0].content


def test_non_openai_stage_strips_unsupported_reasoning_parameters(monkeypatch):
    config = stage_configuration("Economy", light_provider="Ollama", light_model="llama3.1:8b")
    fake = Mock(); build = Mock(return_value=fake); monkeypatch.setattr(workflow, "build_stage_llm", build)
    lazy = workflow.LazyStage("plan", config, dict(openai_api_key="", groq_api_key="", ollama_base_url="http://localhost:11434/v1"))
    lazy.invoke([], max_completion_tokens=650, reasoning_effort="minimal", response_format={"type": "json_object"})
    assert fake.invoke.call_args.kwargs == {"max_tokens": 650}


def test_evidence_only_preflight_does_not_require_unused_openai():
    args = factory_args(); args.update(openai_api_key="", stop_after_evidence=True)
    args["config"] = stage_configuration("Economy", light_provider="Ollama", light_model="llama3.1:8b")
    manager = workflow.build_manager(**args)
    assert manager.stop_after_evidence
    with pytest.raises(V2ConfigurationError, match="Draft / OpenAI"):
        workflow.build_manager(**{**args, "stop_after_evidence": False})


def test_review_patch_is_mechanically_revalidated():
    llm = Mock(); llm.model_name = "gpt-5-nano"
    llm.invoke.return_value = SimpleNamespace(content='{"corrections": [{"original": "## Risks", "replacement": "## Concerns"}], "unresolved": []}')
    source = Mock()
    manager = ResearchManager(llm, source, SerperClient(""), deterministic_validator=validate_report)
    result = manager.resume(saved("review_pending"))
    assert result["status"] == "needs_review"
    assert any("Risks" in w for w in result["warnings"])
    source.collect.assert_not_called()


def test_evidence_only_and_later_synthesis_are_separate_calls(monkeypatch):
    args = factory_args(); args["stop_after_evidence"] = True
    source = Mock(); source.collect.return_value = [Evidence("", "AAPL", "income", "Income", "Synthetic", [{"revenue": 5}])]
    monkeypatch.setattr(workflow, "QuarterlyFinancialDataSource", Mock(return_value=source))
    monkeypatch.setattr(workflow, "get_finance_tools", lambda *a: [])
    planner = Mock(); planner.invoke.return_value = SimpleNamespace(content='{}')
    writer = Mock(); writer.invoke.return_value = SimpleNamespace(content=REPORT)
    build = Mock(side_effect=[planner, writer]); monkeypatch.setattr(workflow, "build_stage_llm", build)
    evidence_run = workflow.build_manager(**args).run(args["request"])
    assert evidence_run["status"] == "evidence_ready" and not evidence_run["report"]
    assert build.call_count == 1
    complete = workflow.build_manager(**{**args, "stop_after_evidence": False, "saved": evidence_run}).resume(evidence_run)
    assert complete["status"] == "complete"
    assert source.collect.call_count == 1 and build.call_count == 2


def test_submission_decision_failure_selects_new_report_before_error(app, monkeypatch):
    other = saved(); other["id"] = "old"
    app.session_state["drv2_history"] = [other]
    app.session_state["drv2_active_run"] = "old"
    manager = Mock(); manager.run.return_value = saved()
    monkeypatch.setattr(ui, "_manager_v2", Mock(return_value=manager))
    def decision(result, **kwargs):
        assert app.session_state["drv2_history"][0]["id"] == "v2-test"
        return {**result, "decision_status": "failed", "decision_error": "Timeout"}
    monkeypatch.setattr(ui, "run_decision", decision)
    app.run(); widget(app, "selectbox", "Decision stage").set_value("Quick decision")
    widget(app, "button", "Run V2 pilot").click().run()
    assert not app.exception
    assert app.session_state["drv2_active_run"] == "v2-test"
    assert len(app.session_state["drv2_history"]) == 2
    assert not app.error
    assert any(b.label == "Retry decision" for b in app.button)


def test_hot_reload_tracks_v2_workflow_without_running_app(monkeypatch):
    import app as entry
    calls = []
    module = SimpleNamespace(render_deep_research_tab=lambda: None, render_deep_research_v2_tab=lambda: None)
    monkeypatch.setattr(entry.app_main, "_deep_research_source_stamp", (), raising=False)
    monkeypatch.setattr(entry.app_main, "render_deep_research_tab", entry.app_main.render_deep_research_tab)
    monkeypatch.setattr(entry.app_main, "render_deep_research_v2_tab", entry.app_main.render_deep_research_v2_tab)
    monkeypatch.setattr(entry.importlib, "import_module", lambda name: calls.append(name) or module)
    monkeypatch.setattr(entry.importlib, "reload", lambda value: value)
    entry._load_current_deep_research()
    assert "langgraphagenticai.deep_research.v2_workflow" in calls
    assert calls.index("langgraphagenticai.deep_research.v2") < calls.index("langgraphagenticai.deep_research.v2_workflow")


def test_committee_receives_saved_ollama_endpoint(monkeypatch):
    result = saved(); result["v2_config"] = stage_configuration("Economy", light_provider="Ollama", light_model="llama3.1:8b")
    result["v2_runtime"].update(decision_mode="Full committee", ollama_base_url="http://localhost:22434/v1")
    committee = Mock(return_value={"model": "gpt-5-mini", "specialist_model": "llama3.1:8b"})
    monkeypatch.setattr(workflow, "run_investment_committee", committee)
    updated = workflow.run_decision(result, openai_api_key="synthetic")
    assert updated["decision_status"] == "complete"
    assert committee.call_args.kwargs["ollama_base_url"] == "http://localhost:22434/v1"
