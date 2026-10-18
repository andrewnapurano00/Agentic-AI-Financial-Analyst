"""Question-driven outlines and saved-decision PDF contracts; no live services."""
from copy import deepcopy
import io
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pdfminer.high_level import extract_text
from streamlit.testing.v1 import AppTest

from langgraphagenticai.deep_research.committee_export import committee_markdown
from langgraphagenticai.deep_research.models import ResearchRequest, Evidence
from langgraphagenticai.deep_research.manager import ResearchManager
from langgraphagenticai.deep_research.presentation import build_research_pdf, clean_report_markdown
from langgraphagenticai.deep_research.report_structure import report_structure, structure_instruction
from langgraphagenticai.deep_research.v2 import report_instruction, stage_configuration
from langgraphagenticai.tools.serper_tools import SerperClient


def saved_report():
    return {"id": "format-test", "status": "complete", "created_at": "2026-10-18T12:00:00Z",
            "request": {"symbols": ["AAPL", "MSFT"], "question": "Compare fair value and the downside.", "horizon": "1-3 years", "include_news": False},
            "report": "**Executive Investment Thesis**\nGrowth differs [E001].\n\n**Valuation anchors & assumptions**\nRevenue is USD 5B in FY2026.\n\n## Investment conclusion\nDemand is the deciding factor.",
            "evidence": [], "comparison": [{"Ticker": "AAPL", "Sector": "Technology", "Forward P/E": 20}],
            "warnings": [], "gaps": [], "plan": {}}


def committee():
    return {"summary": "Prefer MSFT with valuation discipline [E001].", "preferred_ticker": "MSFT",
            "created_at": "2026-10-18T12:10:00Z",
            "decisions": [
                {"ticker": "AAPL", "recommendation": "HOLD", "confidence": 0, "rationale": "Cash conversion is strong.",
                 "risks": ["Demand weakens"], "invalidation_signals": ["Margins deteriorate"]},
                {"ticker": "MSFT", "recommendation": "BUY", "confidence": 72, "rationale": "Growth supports the multiple.",
                 "catalysts": ["Cloud momentum"]}],
            "dissent": "Capital intensity may offset growth.", "evidence_limitations": ["Future demand is uncertain."]}


@pytest.mark.parametrize("question,focus", [
    ("What is AAPL worth?", "valuation"), ("Analyze earnings and guidance", "earnings"),
    ("What news catalysts matter next?", "catalysts"), ("Stress the downside and liquidity", "risk"),
    ("Assess AI strategy and competitive moat", "strategy"),
    ("Compare the risk-adjusted long-term opportunities", "comparison"),
    ("Compare fundamentals, valuation, news and downside risks", "comparison"),
])
def test_question_drives_outline_for_both_writers(question, focus):
    request = ResearchRequest(["AAPL", "MSFT"], question)
    outline = report_structure(request)
    assert outline["focus"] == focus
    assert outline["sections"][0] == "Executive Investment Thesis"
    assert outline["sections"][-1] == "Investment conclusion & monitoring"
    prompt = report_instruction(request, stage_configuration("Economy", light_provider="OpenAI"))
    assert outline["sections"][1] in prompt and "## section headings" in prompt


def test_standard_writer_uses_outline_without_another_model_call():
    llm = Mock(); llm.invoke.side_effect = [SimpleNamespace(content="{}"), SimpleNamespace(content=saved_report()["report"])]
    source = Mock(); source.collect.return_value = [Evidence("", "AAPL", "income", "Synthetic", "Test", [{"revenue": 5}])]
    manager = ResearchManager(llm, source, SerperClient(""), auto_finish=True, single_pass=True)
    result = manager.run(ResearchRequest(["AAPL"], "What is fair value?", include_news=False))
    assert result["report_structure"]["focus"] == "valuation"
    assert llm.invoke.call_count == 2
    assert "Valuation anchors & assumptions" in llm.invoke.call_args.args[0][0].content
    assert not any(d["stage"] == "review" for d in manager.diagnostics)


def test_heading_cleanup_preserves_claim_order_and_custom_topics():
    raw = "**Executive Investment Thesis**\nRevenue grew 12% [E001].\n\n2. **AI monetization**\nUSD 2B in FY2026.\n\n- **Risk:** Competition."
    clean = clean_report_markdown(raw)
    assert "## Executive Investment Thesis" in clean and "## AI monetization" in clean
    assert "- **Risk:** Competition." in clean
    assert clean.index("12%") < clean.index("USD 2B")
    assert "E001" not in clean and "FY2026" in clean


def test_pdf_includes_complete_saved_committee_after_argument_before_metrics():
    result = saved_report(); result["crewai_decision"] = committee()
    snapshot = deepcopy(result)
    text = extract_text(io.BytesIO(build_research_pdf(result)))
    for expected in ("CrewAI Committee Decision", "HOLD", "BUY", "0%", "72%", "MSFT",
                     "Cash conversion is strong", "Cloud momentum", "Demand weakens", "Margins deteriorate",
                     "Capital intensity", "Future demand", "2026-10-18T12:10:00Z", "RESEARCH QUESTION"):
        assert expected in text
    assert text.index("Demand is the deciding factor") < text.index("CrewAI Committee Decision") < text.index("Supporting financial detail")
    assert "E001" not in text and "USD 5B" in text and "FY2026" in text
    assert result == snapshot


def test_absent_failed_and_quick_decisions_are_distinguished():
    result = saved_report()
    assert committee_markdown(result) == ""
    result["decision_status"] = "failed"
    assert "No completed decision" in committee_markdown(result)
    result["quick_decision"] = {"verdict": "WATCH", "confidence": 55, "summary": "Wait for demand"}
    text = committee_markdown(result)
    assert "Quick investment decision" in text and "55%" in text and "WATCH" in text
    assert "CrewAI Committee Decision" not in text and "later decision attempt" in text


def test_partial_legacy_committee_cannot_break_the_research_pdf():
    result = saved_report()
    result["crewai_decision"] = {"summary": "A partial saved opinion", "decisions": None, "preferred_ticker": {"invalid": True}}
    text = extract_text(io.BytesIO(build_research_pdf(result)))
    assert "A partial saved opinion" in text and "ratings were not available" in text
    assert "USD 5B" in text


def test_committee_export_filters_credentials_markup_and_foreign_tickers():
    result = saved_report(); decision = committee()
    decision["summary"] = "Growth <b> & margins [E001]. https://example.test/?api_key=synthetic-secret"
    decision["decisions"].append({"ticker": "ZZZ", "recommendation": "BUY", "confidence": 99})
    decision["decisions"][0]["rationale"] = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456"
    result["crewai_decision"] = decision
    pdf = build_research_pdf(result)
    text = extract_text(io.BytesIO(pdf))
    assert "synthetic-secret" not in text and "abcdefghijklmnopqrstuvwxyz123456" not in text
    assert "E001" not in text and "ZZZ" not in text and "Growth" in text


@pytest.mark.parametrize("paragraphs", [8, 16, 28])
def test_long_report_has_no_empty_overflow_page(paragraphs):
    import pdfplumber
    result = saved_report(); result["crewai_decision"] = committee()
    paragraph = "Demand and cash conversion determine resilience. " * 12
    result["report"] += "\n\n" + "\n\n".join([paragraph] * paragraphs)
    with pdfplumber.open(io.BytesIO(build_research_pdf(result))) as pdf:
        for page in pdf.pages:
            assert page.crop((0, 55, 612, 740)).extract_text().strip()


def test_standard_pdf_download_reuses_saved_committee_on_rerun(monkeypatch):
    from langgraphagenticai.ui import deep_research_tab as ui
    captured = []
    actual = ui.build_research_pdf
    def export(value):
        data = actual(value); captured.append(data); return data
    monkeypatch.setattr(ui, "build_research_pdf", export)
    models = Mock(); committee_model = Mock()
    monkeypatch.setattr(ui, "_manager", models)
    monkeypatch.setattr(ui, "run_investment_committee", committee_model)
    app = AppTest.from_string('''
from langgraphagenticai.ui.deep_research_tab import render_deep_research_tab
render_deep_research_tab(openai_api_key="", model_name="test", fmp_api_key="")
''', default_timeout=30)
    result = saved_report(); result["crewai_decision"] = committee()
    app.session_state["dr_history"] = [result]
    app.run(); app.run()
    assert not app.exception
    assert any("PDF includes" in c.value for c in app.caption)
    assert all("CrewAI Committee Decision" in extract_text(io.BytesIO(data)) for data in captured)
    assert captured
    models.assert_not_called(); committee_model.assert_not_called()


def test_low_cost_pdf_download_reuses_saved_committee_on_rerun(monkeypatch):
    from langgraphagenticai.ui import deep_research_v2_tab as ui
    captured = []
    actual = ui.build_research_pdf
    def export(value):
        data = actual(value); captured.append(data); return data
    monkeypatch.setattr(ui, "build_research_pdf", export)
    models = Mock(); decision_model = Mock()
    monkeypatch.setattr(ui, "_manager_v2", models)
    monkeypatch.setattr(ui, "run_decision", decision_model)
    app = AppTest.from_string('''
from langgraphagenticai.ui.deep_research_v2_tab import render_deep_research_v2_tab
render_deep_research_v2_tab(openai_api_key="", fmp_api_key="")
''', default_timeout=30)
    result = saved_report(); result["crewai_decision"] = committee()
    result.update(cost_mode="Economy", v2_config=stage_configuration("Economy", light_provider="OpenAI"),
                  v2_runtime={"decision_mode": "None"})
    app.session_state["drv2_history"] = [result]
    app.run(); app.run()
    assert not app.exception and captured
    assert all("CrewAI Committee Decision" in extract_text(io.BytesIO(data)) for data in captured)
    models.assert_not_called(); decision_model.assert_not_called()
