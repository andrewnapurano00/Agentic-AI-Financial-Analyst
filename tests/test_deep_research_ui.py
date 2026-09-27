import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from streamlit.testing.v1 import AppTest


HARNESS = '''
import streamlit as st
from langgraphagenticai.ui.deep_research_tab import render_deep_research_tab
# AppTest does not yet send the active index for stateful tab containers.
if st.session_state.get("qa_notebook"):
    st.session_state["dr_result_tabs_test-run"] = "Research notebook"
render_deep_research_tab(openai_api_key="test", model_name="test", fmp_api_key="test", serper_api_key="test")
'''


def sample_result():
    return {"id": "test-run", "created_at": "2026-01-02T00:00:00Z", "status": "complete",
            "request": {"symbols": ["AAPL", "MSFT"], "question": "Compare", "horizon": "1–3 years", "depth": "Standard", "period": "annual", "news_days": 30, "include_news": True},
            "report": "## Test thesis\nCash flow is $111.5 billion versus $118.3 billion [E001].", "markdown": "Test export",
            "warnings": [], "gaps": [], "plan": {"questions": ["Compare quality"]},
            "comparison": [{"Ticker": "AAPL", "Price": 10}, {"Ticker": "MSFT", "Price": 20}],
            "evidence": [
                {"id": "E001", "symbol": "AAPL", "category": "income", "title": "Income",
                 "provider": "FMP", "data": [{"revenue": 5}], "retrieved_at": "2026-01-02T00:00:00Z", "url": "", "status": "ok", "note": ""},
                {"id": "E002", "symbol": "AAPL", "category": "news", "title": "Apple news",
                 "provider": "Serper", "data": [{"title": "Earnings update", "published": "1 day ago"}],
                 "retrieved_at": "2026-01-02T00:00:00Z", "url": "https://example.com/news", "status": "ok", "note": ""},
            ]}


class ResearchUITests(unittest.TestCase):
    def test_saved_research_offers_crewai_committee(self):
        app = AppTest.from_string(HARNESS, default_timeout=20)
        app.session_state["dr_history"] = [sample_result()]
        app.session_state["dr_result_tabs_test-run"] = "CrewAI decision"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("CrewAI decision", [t.label for t in app.tabs])
        self.assertTrue(any(b.label == "Run CrewAI investment committee" for b in app.button))

    def test_saved_crewai_decision_renders_ticker_calls(self):
        result = sample_result()
        result["crewai_decision"] = {
            "summary": "MSFT has the stronger risk-adjusted case.", "preferred_ticker": "MSFT",
            "decisions": [{"ticker": "AAPL", "recommendation": "HOLD", "confidence": 62,
                           "rationale": "Valuation limits upside.", "catalysts": ["Services growth"],
                           "risks": ["Multiple compression"], "invalidation_signals": ["Growth reaccelerates"]},
                          {"ticker": "MSFT", "recommendation": "BUY", "confidence": 78,
                           "rationale": "Durable growth.", "catalysts": ["Cloud demand"],
                           "risks": ["AI capex"], "invalidation_signals": ["Margin erosion"]}],
            "dissent": "Valuation remains elevated.", "evidence_limitations": [],
            "disclaimer": "AI-generated research opinion, not personalized investment advice.",
        }
        app = AppTest.from_string(HARNESS, default_timeout=20)
        app.session_state["dr_history"] = [result]
        app.session_state["dr_result_tabs_test-run"] = "CrewAI decision"
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("MSFT · BUY" in item.value for item in app.markdown))

    def test_professional_comparison_workspace_renders_ttm_and_statement_sections(self):
        result = sample_result()
        result["comparison"] = [{
            "Ticker": "AAPL", "Company": "Apple", "Sector": "Technology", "Industry": "Hardware",
            "Sector framework": "Technology / Software / Semis", "Quote currency": "USD",
            "Statement currency": "USD", "Price": 200, "Forward P/E": 25, "Target upside (%)": 10,
            "TTM through": "2026-06-30", "Revenue (TTM)": 120_000_000_000,
            "Operating margin (TTM)": .30, "Statement date": "2025-09-30", "Statement period": "FY",
            "Revenue (latest period)": 100_000_000_000, "Operating margin (latest period)": .25,
        }]
        result["sector_frameworks"] = [{
            "symbol": "AAPL", "sector": "Technology", "industry": "Hardware",
            "framework": "Technology / Software / Semis", "description": "Growth and cash generation.",
            "must_have": ["Latest Operating Margin", "Forward P/E"], "preferred": [],
            "unavailable_priority_metrics": [], "missing_but_useful": ["Segment Revenue Growth"],
        }]
        app = AppTest.from_string(HARNESS, default_timeout=20)
        app.session_state["dr_history"] = [result]
        app.session_state["dr_active_run"] = "test-run"
        app.session_state["dr_result_tabs_test-run"] = "Company comparison"
        app.run()
        self.assertEqual(len(app.exception), 0)
        labels = [tab.label for tab in app.tabs]
        self.assertIn("TTM performance", labels)
        self.assertIn("Reported period", labels)
        self.assertIn("Forward & valuation", labels)
        self.assertTrue(any("Company snapshot" in item.value for item in app.markdown))

    def test_completed_review_issues_can_be_finalized_with_caveats(self):
        result = sample_result()
        result.update(status="needs_review", review_status="needs_review", draft=result["report"])
        result["warnings"] = ["Review flagged issues: missing primary source."]
        app = AppTest.from_string(HARNESS, default_timeout=20)
        app.session_state["dr_history"] = [result]
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Review completed and flagged evidence issues" in item.value for item in app.info))
        self.assertFalse(any(b.label.startswith("Retry") for b in app.button))
        next(b for b in app.button if b.label == "Finalize report").click().run()
        finalized = app.session_state["dr_history"][0]
        self.assertEqual(finalized["status"], "complete")
        self.assertEqual(finalized["review_status"], "finalized_with_caveats")
        self.assertTrue(finalized["finalized_with_caveats"])
        self.assertTrue(finalized["finalized_at"])
        self.assertEqual(finalized["warnings"], ["Review flagged issues: missing primary source."])
        self.assertTrue(any("Complete · Caveats disclosed" in item.value for item in app.metric))

    @patch("langgraphagenticai.ui.deep_research_tab._manager")
    def test_run_followup_and_history_survive_reruns(self, factory):
        factory.return_value.run.return_value = sample_result()
        factory.return_value.follow_up.return_value = "Saved evidence answer [E001]."
        app = AppTest.from_string(HARNESS, default_timeout=20).run()
        self.assertEqual(len(app.exception), 0)
        next(b for b in app.button if b.label == "Start deep research").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Investment thesis", [t.label for t in app.tabs])
        self.assertTrue(any(r"\$111.5" in item.value and r"\$118.3" in item.value for item in app.markdown))
        self.assertEqual(len(app.session_state["dr_history"]), 1)
        app.session_state["qa_notebook"] = True
        app.run()
        next(t for t in app.text_input if t.label == "Follow-up question").set_value("What is missing?")
        next(b for b in app.button if b.label == "Ask about this research").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.session_state["dr_history"][0]["follow_ups"]), 1)
        app.run()
        factory.return_value.run.assert_called_once()

    @patch("langgraphagenticai.ui.deep_research_tab._manager")
    def test_invalid_tickers_never_call_providers(self, factory):
        app = AppTest.from_string(HARNESS, default_timeout=20).run()
        app.text_input(key="dr_tickers").set_value("A,B,C,D,E")
        next(b for b in app.button if b.label == "Start deep research").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("one and four" in e.value for e in app.error))
        factory.assert_not_called()

    @patch("langgraphagenticai.ui.deep_research_tab._manager")
    def test_retry_does_not_recollect_evidence(self, factory):
        result = sample_result()
        result["status"] = "incomplete"
        factory.return_value.resume.return_value = {**result, "status": "complete", "report": "Recovered thesis [E001]."}
        app = AppTest.from_string(HARNESS, default_timeout=20)
        app.session_state["dr_history"] = [result]
        app.run()
        next(b for b in app.button if b.label == "Retry report writing").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["dr_history"][0]["status"], "complete")
        factory.return_value.run.assert_not_called()

    @patch("langgraphagenticai.ui.deep_research_tab._manager")
    def test_retry_failure_is_actionable_and_preserves_saved_evidence(self, factory):
        result = sample_result()
        result.update(status="incomplete", report="## Research collected", draft="")
        factory.return_value.resume.side_effect = TimeoutError()
        app = AppTest.from_string(HARNESS, default_timeout=20)
        app.session_state["dr_history"] = [result]
        app.run()
        next(b for b in app.button if b.label == "Retry report writing").click().run()
        self.assertEqual(app.session_state["dr_history"][0]["evidence"], result["evidence"])
        self.assertTrue(any("timed out" in item.value and "saved evidence is unchanged" in item.value
                            for item in app.error))
        factory.return_value.run.assert_not_called()

    @patch("langgraphagenticai.ui.deep_research_tab._manager")
    def test_pending_review_displays_draft_and_retries_review(self, factory):
        result = sample_result()
        result.update(status="review_pending", draft=result["report"], review_status="pending",
                      warnings=["Draft saved; review is pending."], report_warnings=["Draft saved; review is pending."])
        factory.return_value.resume.return_value = {**result, "status": "complete", "warnings": []}
        app = AppTest.from_string(HARNESS, default_timeout=20)
        app.session_state["dr_history"] = [result]
        app.run()
        self.assertTrue(any(r"\$111.5" in item.value for item in app.markdown))
        next(b for b in app.button if b.label == "Retry review").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["dr_history"][0]["status"], "complete")
        self.assertEqual(len(app.warning), 0)
        factory.return_value.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
