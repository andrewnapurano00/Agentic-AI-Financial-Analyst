from pathlib import Path
from unittest.mock import Mock
from streamlit.testing.v1 import AppTest
from langgraphagenticai.providers.data_validation_catalog import endpoints, endpoint
from langgraphagenticai.providers.data_validation_usage import REPORTS, usages, endpoint_ids


def test_every_report_and_variant_has_source_backed_metric_family_coverage():
    rows=usages()
    assert set(REPORTS)=={r["report"] for r in rows}
    known={e["id"] for e in endpoints()}
    for row in rows:
        assert row["endpoints"] and set(row["endpoints"])<=known
        assert all(row[k] for k in ("family","places","fields","calculation","basis","kind","sources"))
        assert all((Path("src/langgraphagenticai")/path).is_file() for path in row["sources"])
    assert endpoint_ids()==known
    rows[0]["endpoints"].clear()
    assert usages()[0]["endpoints"]


def test_report_filter_does_not_confuse_fund_company_or_fiscal_bases():
    funds=usages("AI Robo Advisor", "ETF allocation thesis")
    assert len(funds)==1 and "NAV" in funds[0]["calculation"]
    assert "fmp.stable.ratios-ttm" not in funds[0]["endpoints"]
    assert endpoint_ids("Portfolio Lab - Optimizer")=={"yahoo.history"}
    audit=usages("Deep Research - Standard format", "Audited financial metrics")[0]
    assert "four validated consecutive quarters" in audit["calculation"]
    assert "Annual CAGR and forecasts stay separate" in audit["calculation"]
    assert "not universally audited" in usages("Equity Report", "Company financials / growth")[0]["calculation"]


def test_report_and_metric_filters_reconcile_controls_without_fetching(monkeypatch):
    from langgraphagenticai.ui import data_validation_tab as ui
    request=Mock()
    monkeypatch.setattr(ui,"fetch_endpoint",request)
    app=AppTest.from_string('from langgraphagenticai.ui.data_validation_tab import render_data_validation\nrender_data_validation("fixture")',default_timeout=30).run()
    assert not app.exception
    app.session_state["validation_saved_response"]={"scope":"older-settings", "response":{"data":[{"zero":0}]}}
    retained=app.session_state["validation_saved_response"]
    app.selectbox(key="validation_report").set_value("Portfolio Lab - Optimizer").run()
    assert not app.exception
    assert app.selectbox(key="validation_provider").options==[endpoint("yahoo.history")["provider"]]
    assert app.selectbox(key="validation_endpoint").value=="yahoo.history"
    app.selectbox(key="validation_report").set_value("Equity Report").run()
    app.selectbox(key="validation_metric_family").set_value("Summary / CrewAI decision").run()
    assert not app.exception
    assert "fmp.v3.ratios-ttm" in endpoint_ids("Equity Report", "Summary / CrewAI decision")
    assert any("saved scorecard" in m.value for m in app.markdown)
    app.selectbox(key="validation_report").set_value("All reports").run()
    assert not app.exception
    assert app.session_state["validation_saved_response"]==retained
    request.assert_not_called()


def test_calculation_index_resolves_actual_active_source_definitions():
    from langgraphagenticai.providers.data_validation_usage import calculation_index
    rows=calculation_index("Equity Report", "Summary / CrewAI decision")
    pdf=[r for r in rows if r["Source file"]=="ui/equity_report_tab.py" and r["Definition"]=="generate_story_pdf_report"]
    assert len(pdf)==1
    source=Path("src/langgraphagenticai/ui/equity_report_tab.py").read_text(encoding="utf-8-sig").splitlines()
    assert source[pdf[0]["Line"]-1].startswith("def generate_story_pdf_report(")
    assert any(r["Definition"]=="build_equity_pdf" for r in rows)
