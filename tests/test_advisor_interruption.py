from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.ui import portfolio_architect_tab as ui
from langgraphagenticai.portfolio_architect.mandate import default_mandate
from langgraphagenticai.portfolio_architect.research import demo_snapshot
from langgraphagenticai.portfolio_architect.universe import eligible_names
from langgraphagenticai.portfolio_architect.workflow import build
from langgraphagenticai.portfolio_architect import committee

PAGE = "from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect; render_portfolio_architect(fmp_api_key='fixture',openai_api_key='fixture-ai')"


def saved():
    mandate, _ = default_mandate("Build an aggressive five-year growth portfolio focused on AI with diversified risk.")
    snapshot = demo_snapshot(eligible_names(mandate), mandate.benchmark)
    return build(snapshot, mandate)


@pytest.mark.parametrize("matching", [True, False])
def test_interrupted_ai_checkpoint_requires_explicit_retry_and_exact_result(monkeypatch, matching):
    local = saved()
    collect = Mock(side_effect=AssertionError("No recollection"))
    reviewed = Mock(return_value=local)
    monkeypatch.setattr(ui, "collect", collect)
    monkeypatch.setattr(ui, "build", reviewed)
    app = AppTest.from_string(PAGE, default_timeout=30)
    app.session_state["architect_result"] = local.model_dump(mode="json")
    app.session_state["architect_build_stage"] = {"stage":"ai_review", "result_id":local.id if matching else "older-result"}
    app.run()
    assert not app.exception and any("interrupted during AI review" in w.value for w in app.warning)
    collect.assert_not_called()
    reviewed.assert_not_called()
    retries = [b for b in app.button if b.key == "architect_retry_ai"]
    assert bool(retries) is matching
    if matching:
        retries[0].click().run()
        assert not app.exception
        assert reviewed.call_count == 1 and reviewed.call_args.args[-1] is True
        assert app.session_state["architect_build_stage"]["stage"] == "completed"
        app.run()
        assert reviewed.call_count == 1
    collect.assert_not_called()


def test_timeout_preserves_local_portfolio_and_sanitizes_diagnostic(monkeypatch):
    local = saved()
    monkeypatch.setattr("langgraphagenticai.portfolio_architect.workflow.review", Mock(side_effect=TimeoutError("secret-provider-packet")))
    result = build(local.snapshot, local.mandate, "fixture-ai", "synthetic", True)
    assert result.ai_review_status["state"] == "failed"
    assert "time budget" in result.ai_review_status["reason"]
    assert "secret-provider-packet" not in str(result.model_dump())
    assert [h.ticker for h in result.holdings] == [h.ticker for h in local.holdings]


def test_collection_failure_keeps_submitted_mandate_and_prior_result(monkeypatch):
    local = saved()
    collect = Mock(side_effect=RuntimeError("private transport details"))
    monkeypatch.setattr(ui, "collect", collect)
    app = AppTest.from_string(PAGE, default_timeout=30)
    app.session_state["architect_mandate"] = local.mandate.model_dump()
    app.session_state["architect_result"] = local.model_dump(mode="json")
    app.run()
    app.number_input(key="architect_edit_0_amount").set_value(25000.)
    next(b for b in app.button if b.label == "Build portfolio").click().run()
    assert not app.exception
    assert app.session_state["architect_mandate"]["amount"] == 25000.
    assert app.session_state["architect_result"] == local.model_dump(mode="json")
    assert app.session_state["architect_build_stage"]["stage"] == "failed"
    app.run()
    collect.assert_called_once()
