import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from langgraphagenticai.deep_research.manager import ResearchManager
from langgraphagenticai.deep_research.models import Evidence, ResearchRequest, dumps
from langgraphagenticai.deep_research.prompt_context import evidence_context
from langgraphagenticai.tools.serper_tools import SerperClient


ACCEPT = '{"corrections": [], "unresolved": []}'


class RecoveryTests(unittest.TestCase):
    def manager(self, replies, **kwargs):
        llm, source = Mock(), Mock()
        llm.invoke.side_effect = [SimpleNamespace(content=r) if isinstance(r, str) else r for r in replies]
        source.collect.return_value = [Evidence("", "AAPL", "income", "Income", "FMP", [{"revenue": 5}])]
        return ResearchManager(llm, source, SerperClient(""), **kwargs)

    def test_review_timeout_keeps_draft_and_retry_only_reviews(self):
        checkpoints = []
        manager = self.manager(['{}', 'Revenue is 5 [E001].', TimeoutError()], checkpoint=checkpoints.append)
        saved = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(saved["status"], "review_pending")
        self.assertEqual(saved["report"], 'Revenue is 5 [E001].')
        self.assertTrue(any(c.get("draft") for c in checkpoints))
        self.assertIn("review pending", saved["markdown"])
        retry = self.manager([ACCEPT])
        complete = retry.resume(saved)
        self.assertEqual(complete["status"], "complete")
        self.assertEqual(complete["warnings"], [])
        self.assertEqual(retry.llm.invoke.call_count, 1)
        self.assertEqual(retry.llm.invoke.call_args.kwargs["max_completion_tokens"], 3000)
        self.assertEqual(len(complete["diagnostics"]), len(saved["diagnostics"]) + 1)
        retry.financial_source.collect.assert_not_called()

    def test_structured_passes_use_minimal_reasoning_only_for_supported_models(self):
        manager = self.manager(['{}', ACCEPT])
        manager.llm.model_name = "gpt-5"
        manager._invoke("Plan", {}, stage="plan")
        self.assertEqual(manager.llm.invoke.call_args.kwargs["reasoning_effort"], "minimal")
        manager._invoke("Review", {}, stage="review")
        self.assertEqual(manager.llm.invoke.call_args.kwargs["reasoning_effort"], "minimal")
        self.assertEqual(manager.llm.invoke.call_args.kwargs["response_format"], {"type": "json_object"})
        other = self.manager(['{}'])
        other.llm.model_name = "gpt-4.1-mini"
        other._invoke("Plan", {}, stage="plan")
        self.assertNotIn("reasoning_effort", other.llm.invoke.call_args.kwargs)

    def test_structured_passes_use_separate_utility_model(self):
        utility = Mock()
        utility.model_name = "gpt-5-mini"
        utility.invoke.return_value = SimpleNamespace(content='{}', response_metadata={})
        manager = self.manager([], utility_llm=utility)
        manager.llm.model_name = "gpt-5"
        manager._invoke("Plan", {}, stage="plan")
        utility.invoke.assert_called_once()
        manager.llm.invoke.assert_not_called()
        self.assertEqual(manager.diagnostics[0]["model"], "gpt-5-mini")

    def test_review_context_keeps_cited_trends_and_gaps(self):
        evidence = [
            Evidence("E001", "AAPL", "income", "Income", "FMP", [{"revenue": 5}]),
            Evidence("E002", "AAPL", "balance", "Balance", "FMP", [{"totalDebt": 2}]),
            Evidence("E003", "AAPL", "financial_trends", "Trends", "Calculated", [{"yoy_pct": 4}]),
            Evidence("E004", "AAPL", "news", "News", "Serper", {}, status="missing"),
        ]
        selected = ResearchManager._review_evidence(evidence, "Revenue was 5 [E001].")
        self.assertEqual({item.id for item in selected}, {"E001", "E003", "E004"})

    def test_usage_telemetry_estimates_known_model_cost(self):
        response = SimpleNamespace(
            content='{}', response_metadata={},
            usage_metadata={"input_tokens": 1000, "output_tokens": 200,
                            "input_token_details": {"cache_read": 100}},
        )
        manager = self.manager([response])
        manager.llm.model_name = "gpt-5"
        manager._invoke("Plan", {}, stage="plan")
        diagnostic = manager.diagnostics[0]
        self.assertFalse(diagnostic["token_counts_estimated"])
        self.assertEqual(diagnostic["cached_input_tokens"], 100)
        self.assertAlmostEqual(diagnostic["estimated_cost_usd"], 0.003138, places=6)

    def test_review_applies_exact_correction(self):
        fix = json.dumps({"corrections": [{"original": "up from 118", "replacement": "down from 118"}], "unresolved": []})
        manager = self.manager(['{}', 'Cash flow 111, up from 118 [E001].', fix])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "complete")
        self.assertIn("down from 118", result["report"])

    def test_clarification_response_is_automatically_replaced_with_complete_memo(self):
        clarification = (
            "Before I proceed, a few quick clarifications: do you want a single recommendation? "
            "I can begin once you confirm."
        )
        manager = self.manager([
            '{}', clarification, '## Executive Investment Thesis\nPrefer AAPL [E001].', ACCEPT,
        ])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["report"].startswith("## Executive Investment Thesis"))
        self.assertNotIn("Before I proceed", result["report"])
        self.assertEqual(manager.llm.invoke.call_count, 4)
        retry_instruction = manager.llm.invoke.call_args_list[2].args[0][0].content
        self.assertIn("previous response only asked for clarification", retry_instruction)

    def test_saved_clarification_draft_is_discarded_on_resume(self):
        manager = self.manager(['## Executive Investment Thesis\nCompleted memo [E001].', ACCEPT])
        saved = {
            "id": "saved-run", "created_at": "2026-09-20T00:00:00Z",
            "request": {"symbols": ["AAPL"], "question": "Which is stronger?", "horizon": "1–3 years",
                        "depth": "Standard", "period": "annual", "news_days": 30,
                        "include_news": False},
            "status": "review_pending", "report": "Before I proceed, do you want a firm recommendation?",
            "draft": "Before I proceed, do you want a firm recommendation?", "partial_draft": "",
            "review_status": "pending", "evidence": [Evidence(
                "E001", "AAPL", "income", "Income", "FMP", [{"revenue": 5}]
            ).to_dict()],
            "comparison": [], "sector_frameworks": [], "plan": {}, "warnings": [], "gaps": [],
        }
        result = manager.resume(saved)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["report"].startswith("## Executive Investment Thesis"))
        self.assertEqual(manager.llm.invoke.call_count, 2)

    def test_completed_review_with_open_evidence_issues_is_not_a_generation_failure(self):
        review = json.dumps({"corrections": [], "unresolved": ["Unverified revenue claim needs a primary source."]})
        manager = self.manager(['{}', 'Memo [E001].', review])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "needs_review")
        self.assertIn("Review completed with open evidence issues", result["markdown"])
        self.assertNotIn("has not completed review", result["markdown"])

    def test_invalid_review_patch_cannot_destroy_draft(self):
        manager = self.manager(['{}', 'Original memo [E001].', '{"corrections": [{"original": "nonexistent", "replacement": "wrong"}], "unresolved": []}'])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "review_pending")
        self.assertEqual(result["report"], 'Original memo [E001].')

    def test_stream_disconnect_preserves_partial_output(self):
        updates = []
        manager = self.manager(['{}'], on_text=updates.append)
        def chunks():
            yield SimpleNamespace(content='Partial memo [E001]', response_metadata={})
            raise TimeoutError()
        manager.llm.stream.side_effect = lambda *a, **kw: chunks()
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["partial_draft"], 'Partial memo [E001]')
        self.assertEqual(result["draft"], '')
        self.assertIn('Partial memo', result["report"])
        self.assertTrue(updates)

    def test_output_token_limit_is_not_marked_complete(self):
        response = SimpleNamespace(content='Unfinished memo', response_metadata={"finish_reason": "length"})
        manager = self.manager(['{}', response])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["partial_draft"], 'Unfinished memo')

    def test_stream_completion_and_bounded_requests(self):
        manager = self.manager(['{}', ACCEPT], on_text=lambda text: None)
        manager.llm.stream.return_value = iter([
            SimpleNamespace(content='Memo ', response_metadata={}),
            SimpleNamespace(content='[E001].', response_metadata={"finish_reason": "stop"}),
        ])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["report"], 'Memo [E001].')
        self.assertEqual(manager.llm.stream.call_args.kwargs["max_completion_tokens"], 4500)
        self.assertTrue(all(d["seconds"] >= 0 for d in result["diagnostics"]))

    def test_prompt_budget_keeps_balanced_company_facts_without_mutation(self):
        sources = [Evidence(f"E{i:03d}", symbol, "investigation", "Large source", "FMP",
                            {"content": "X" * 40000, "data": [{"value": 1}] * 30})
                   for i, symbol in enumerate(["AAPL", "MSFT", "NVDA", "AMZN"] * 12, 1)]
        before = dumps([source.to_dict() for source in sources])
        packet = evidence_context(sources, 28000)
        self.assertGreater(len(packet), 0)
        self.assertLess(len(packet), len(sources))
        self.assertEqual(packet[0]["omitted_sources"], len(sources) - len(packet))
        self.assertTrue({r["id"] for r in packet}.issubset({source.id for source in sources}))
        counts = [sum(r["symbol"] == symbol for r in packet)
                  for symbol in ["AAPL", "MSFT", "NVDA", "AMZN"]]
        self.assertLessEqual(max(counts) - min(counts), 1)
        for record in packet:
            self.assertTrue(record["data"]["content"].startswith("X" * 100))
            self.assertIn("excerpt truncated", record["data"]["content"])
            self.assertEqual(record["data"]["data"][0]["value"], 1)
        self.assertEqual(dumps([source.to_dict() for source in sources]), before)
        self.assertLessEqual(len(dumps(packet)), 28000)
        self.assertEqual({r["symbol"] for r in packet}, {"AAPL", "MSFT", "NVDA", "AMZN"})
        self.assertEqual(len(sources[0].data["content"]), 40000)


if __name__ == "__main__":
    unittest.main()
