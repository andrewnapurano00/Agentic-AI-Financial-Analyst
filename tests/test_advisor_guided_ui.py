"""AX-01: guided mandate confirmation without hidden collection or destructive resets."""
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.portfolio_architect.mandate import default_mandate
from langgraphagenticai.portfolio_architect.research import demo_snapshot
from langgraphagenticai.portfolio_architect.universe import eligible_names
from langgraphagenticai.ui import portfolio_architect_tab as ui
from langgraphagenticai.ui.advisor_mandate_editor import preview_rows


PAGE = "from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect; render_portfolio_architect(fmp_api_key='fixture-key')"


def build_app(app):
    next(b for b in app.button if b.label == "Build portfolio").click().run()
    assert not app.exception
    return app


def test_preview_does_not_claim_unparsed_amount_or_word_horizon_was_extracted():
    mandate, _ = default_mandate("Invest $25000 for seven years in a growth portfolio")
    rows = preview_rows(mandate, mandate.model_dump())
    assert rows[0]["Basis"] == "Prompt keyword / numeric horizon"
    assert all("Needs confirmation" in row["Basis"] for row in rows[1:])
    assert float(rows[-1]["Current choice"]) == 100000
    edited = mandate.model_dump() | {"amount": 25000.}
    assert preview_rows(mandate, edited)[-1]["Basis"] == "User edit"
    assert "AI suggestion" in preview_rows(mandate, mandate.model_dump(), ai=True)[-1]["Basis"]
    # A rewritten AI objective cannot establish that its inferred style was user supplied.
    assert "AI suggestion" in preview_rows(mandate, mandate.model_dump(), ai=True, prompt="Build a balanced portfolio")[0]["Basis"]


def test_simple_path_has_three_stages_preserves_advanced_controls_and_no_implicit_calls(monkeypatch):
    m, _ = default_mandate("Build a moderate growth portfolio for 5 years")
    provider = Mock(return_value=demo_snapshot(eligible_names(m), m.benchmark))
    monkeypatch.setattr(ui, "collect", provider)
    app = AppTest.from_string(PAGE, default_timeout=30).run()
    app.session_state["unrelated_research"] = {"report": "keep"}
    assert any("1. Describe" in x.value for x in app.markdown)
    provider.assert_not_called()
    app.button(key="architect_interpret").click().run()
    assert any("2. Review your mandate" in x.value for x in app.markdown)
    advanced = next(e for e in app.expander if e.label == "Advanced settings")
    assert not advanced.proto.expanded
    for suffix in ("holdings", "assets", "method", "cash", "cap", "sector", "excluded", "forbidden", "themes", "benchmark"):
        assert any(x.key == "architect_edit_1_" + suffix for x in advanced)
    provider.assert_not_called()
    build_app(app)
    assert any("3. Review your portfolio" in x.value for x in app.markdown)
    assert any(e.label == "Applied constraints and limitations" for e in app.expander)
    assert any("no enforced future loss ceiling" in c.value for c in app.caption)
    before = app.session_state["architect_result"]
    app.selectbox(key="architect_edit_1_method").select("equal").run()
    assert any("Inputs differ" in x.value for x in app.info)
    app.button(key="architect_save").click().run()
    app.run()
    assert app.session_state["architect_result"] == before
    assert app.session_state["unrelated_research"] == {"report": "keep"}
    provider.assert_called_once()


@pytest.mark.parametrize("failure", ["provider", "infeasible"])
def test_new_failed_build_preserves_previous_report_and_exports(monkeypatch, failure):
    m, _ = default_mandate("Build an aggressive five-year growth portfolio focused on AI with diversified risk.")
    provider = Mock(return_value=demo_snapshot(eligible_names(m), m.benchmark))
    monkeypatch.setattr(ui, "collect", provider)
    app = AppTest.from_string(PAGE, default_timeout=30).run()
    app.button(key="architect_interpret").click().run()
    build_app(app)
    before = app.session_state["architect_result"]
    if failure == "provider":
        provider.side_effect = RuntimeError("private provider diagnostics")
    else:
        app.number_input(key="architect_edit_1_holdings").set_value(5)
        app.number_input(key="architect_edit_1_cap").set_value(5.)
    build_app(app)
    assert app.error and app.session_state["architect_result"] == before
    assert len(app.get("download_button")) == 4
    assert "private provider" not in str([e.value for e in app.error])
    assert provider.call_count == (2 if failure == "provider" else 1)


def test_empty_and_conflicting_objectives_require_review_without_collection(monkeypatch):
    provider = Mock(side_effect=AssertionError("No implicit collection"))
    monkeypatch.setattr(ui, "collect", provider)
    app = AppTest.from_string(PAGE, default_timeout=30).run()
    app.text_area(key="architect_prompt").set_value("").run()
    app.button(key="architect_interpret").click().run()
    assert app.error
    app.text_area(key="architect_prompt").set_value("A conservative and aggressive portfolio for seven years with $25000").run()
    app.button(key="architect_interpret").click().run()
    assert not app.exception
    assert any("Conflicting risk words" in x.value for x in app.warning)
    preview = next(x.value for x in app.dataframe if "Basis" in x.value.columns)
    assert all("Needs confirmation" in value for value in preview["Basis"])
    provider.assert_not_called()
