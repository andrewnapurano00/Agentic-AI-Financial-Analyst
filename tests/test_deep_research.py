import asyncio
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langgraphagenticai.deep_research.context import collect_app_context
from langgraphagenticai.deep_research.crew_committee import clean_committee_text
from langgraphagenticai.deep_research.data import FinancialDataSource, comparison_rows, extract_rows, technical_snapshot, financial_trends
from langgraphagenticai.deep_research.manager import ResearchManager, evidence_context
from langgraphagenticai.deep_research.models import Evidence, ResearchRequest, dumps, parse_symbols
from langgraphagenticai.deep_research.presentation import _font_safe, build_research_pdf, clean_report_markdown
from langgraphagenticai.deep_research.sector import map_sector_to_framework, sector_frameworks
from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient, fmp_request_budget
from langgraphagenticai.tools.earnings_transcript_tools import build_earnings_transcript_tools
from langgraphagenticai.tools.serper_tools import SerperClient


class ResearchDataTests(unittest.TestCase):
    def test_committee_text_removes_internal_references(self):
        text = clean_committee_text(
            "MSFT has stronger margins [E028 E022 E023]. The research packet supports upside [E025]."
        )
        self.assertEqual(text, "MSFT has stronger margins. The analysis supports upside.")

    def test_sector_mapping_matches_equity_research_taxonomy(self):
        self.assertEqual(map_sector_to_framework("Technology", "Software - Infrastructure"),
                         "Technology / Software / Semis")
        self.assertEqual(map_sector_to_framework("Financial Services", "Banks - Regional"), "Banks / Financials")
        self.assertEqual(map_sector_to_framework("Financial Services", "Mortgage REIT"), "Real Estate / REITs")

    def test_sector_framework_tracks_available_and_missing_priority_metrics(self):
        evidence = [
            Evidence("E001", "NVDA", "profile", "Profile", "FMP",
                     [{"sector": "Technology", "industry": "Semiconductors"}]),
            Evidence("E002", "NVDA", "income", "Income", "FMP",
                     [{"date": "2025-01-31", "fiscalYear": 2025, "period": "FY", "revenue": 100,
                       "grossProfit": 70, "operatingIncome": 50, "researchAndDevelopmentExpenses": 10},
                      {"date": "2023-01-31", "fiscalYear": 2023, "period": "FY", "revenue": 50}]),
            Evidence("E003", "NVDA", "ratios_ttm", "Ratios", "FMP",
                     [{"priceToSalesRatioTTM": 20, "freeCashFlowYieldTTM": .02}]),
        ]
        rows = comparison_rows(evidence, ["NVDA"])
        framework = sector_frameworks(evidence, ["NVDA"], rows)[0]
        self.assertEqual(rows[0]["Sector framework"], "Technology / Software / Semis")
        self.assertAlmostEqual(rows[0]["R&D as % Revenue"], 10)
        self.assertIn("Latest Gross Margin", framework["available_priority_metrics"])
        self.assertIn("Forward EPS Next FY", framework["unavailable_priority_metrics"])
        self.assertIn("ARR", framework["missing_but_useful"])

    def test_symbols_validate_and_deduplicate(self):
        self.assertEqual(parse_symbols("aapl; MSFT aapl BRK-B"), ["AAPL", "MSFT", "BRK-B"])
        for text in ("", "A,B,C,D,E", "AAPL/<script>"):
            with self.assertRaises(ValueError):
                parse_symbols(text)

    def test_error_envelopes_are_not_financial_rows(self):
        self.assertEqual(extract_rows({"ok": False, "data": [], "error": "denied"}), [])
        self.assertEqual(extract_rows({"ok": True, "data": {"historical": [{"close": 5}]}}), [{"close": 5}])
        self.assertEqual(extract_rows({"data": {"Error Message": "Upgrade"}}), [])

    def test_technicals_sort_deduplicate_and_require_history(self):
        rows = [{"date": str(d.date()), "close": float(i + 1)} for i, d in enumerate(pd.date_range("2025-01-01", periods=260))]
        result = technical_snapshot(list(reversed(rows)) + [rows[-1]])
        self.assertEqual(result["observations"], 260)
        self.assertEqual(result["rsi_14"], 100)
        self.assertAlmostEqual(result["sma_50"], 235.5)
        self.assertEqual(result["max_drawdown_pct"], 0)
        self.assertIsNone(technical_snapshot(rows[:10])["sma_50"])
        self.assertNotIn("rsi_14", technical_snapshot(rows[:10]))

    def test_flat_and_falling_rsi(self):
        dates = pd.date_range("2025-01-01", periods=30)
        flat = technical_snapshot([{"date": str(d.date()), "close": 10} for d in dates])
        falling = technical_snapshot([{"date": str(d.date()), "close": 50-i} for i, d in enumerate(dates)])
        self.assertEqual(flat["rsi_14"], 50)
        self.assertEqual(falling["rsi_14"], 0)

    def test_comparison_preserves_zero_and_missing(self):
        rows = comparison_rows([Evidence("E001", "AAPL", "ratios_ttm", "Ratios", "FMP",
                                           [{"priceToEarningsRatioTTM": 0, "netProfitMarginTTM": 0}])], ["AAPL"])
        self.assertEqual(rows[0]["P/E (TTM)"], 0)
        self.assertIsNone(rows[0]["Revenue (latest period)"])

    def test_comparison_includes_forward_estimates_and_valuation(self):
        evidence = [
            Evidence("E001", "AAPL", "quote", "Quote", "FMP", [{"price": 200, "marketCap": 3_000}]),
            Evidence("E002", "AAPL", "ratios_ttm", "Ratios", "FMP", [{"priceToEarningsRatioTTM": 25}]),
            Evidence("E003", "AAPL", "metrics_ttm", "Metrics", "FMP", [{"evToEBITDATTM": 18}]),
            Evidence("E004", "AAPL", "estimates", "Estimates", "FMP", [
                {"date": "2099-09-30", "estimatedRevenueAvg": 100, "estimatedEpsAvg": 10,
                 "estimatedEbitdaAvg": 25},
                {"date": "2100-09-30", "estimatedRevenueAvg": 110, "estimatedEpsAvg": 11},
            ]),
            Evidence("E005", "AAPL", "price_targets", "Targets", "FMP", [{"targetConsensus": 240}]),
        ]
        row = comparison_rows(evidence, ["AAPL"])[0]
        self.assertEqual(row["Forward revenue"], 100)
        self.assertEqual(row["Forward EPS"], 10)
        self.assertEqual(row["Forward P/E"], 20)
        self.assertEqual(row["EV/EBITDA (TTM)"], 18)
        self.assertAlmostEqual(row["Forward revenue growth (%)"], 10)
        self.assertAlmostEqual(row["Target upside (%)"], 20)

    def test_comparison_keeps_ttm_and_reported_statement_bases_separate(self):
        evidence = [
            Evidence("E001", "AAPL", "income", "Annual income", "FMP", [{
                "date": "2025-09-30", "period": "FY", "reportedCurrency": "USD",
                "revenue": 100, "grossProfit": 40, "operatingIncome": 20, "netIncome": 15, "ebitda": 25,
            }]),
            Evidence("E002", "AAPL", "cash_flow", "Annual cash flow", "FMP", [{
                "date": "2025-09-30", "period": "FY", "reportedCurrency": "USD",
                "netCashProvidedByOperatingActivities": 22, "capitalExpenditure": -7, "freeCashFlow": 15,
            }]),
            Evidence("E003", "AAPL", "income_ttm", "TTM income", "FMP", [{
                "date": "2026-06-30", "period": "TTM", "reportedCurrency": "USD",
                "revenue": 120, "grossProfit": 54, "operatingIncome": 30, "netIncome": 21, "ebitda": 36,
            }]),
            Evidence("E004", "AAPL", "cash_flow_ttm", "TTM cash flow", "FMP", [{
                "date": "2026-06-30", "period": "TTM", "reportedCurrency": "USD",
                "netCashProvidedByOperatingActivities": 32, "capitalExpenditure": -8, "freeCashFlow": 24,
            }]),
        ]
        row = comparison_rows(evidence, ["AAPL"])[0]
        self.assertEqual(row["Revenue (latest period)"], 100)
        self.assertEqual(row["Revenue (TTM)"], 120)
        self.assertEqual(row["TTM through"], "2026-06-30")
        self.assertAlmostEqual(row["Operating margin (latest period)"], .20)
        self.assertAlmostEqual(row["Operating margin (TTM)"], .25)
        self.assertEqual(row["Free cash flow (latest period)"], 15)
        self.assertEqual(row["Free cash flow (TTM)"], 24)

    def test_clean_executive_report_and_pdf_export(self):
        report = (
            "## Executive Investment Thesis\n"
            "Revenue is growing [E002][E003].\n\n"
            "| Sources: [E002][E003][E006] | |\n"
            "| --- | -: |\n"
        )
        clean = clean_report_markdown(report)
        self.assertNotIn("[E002]", clean)
        self.assertNotIn("Sources:", clean)
        self.assertNotIn("| --- |", clean)
        pdf = build_research_pdf({
            "request": {"symbols": ["AAPL"], "horizon": "1–3 years"},
            "report": report,
            "comparison": [{"Ticker": "AAPL", "Forward EPS": 10, "Forward P/E": 20}],
        })
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1500)

    def test_clean_report_promotes_plain_sections_and_removes_internal_audit_markers(self):
        report = (
            "Executive Investment Thesis\n"
            "Prefer MSFT [E001, E004, comparison].\n\n"
            "Business quality and competitive positioning\n"
            "Apple remains durable [comparison]."
        )
        clean = clean_report_markdown(report)
        self.assertIn("## Executive Investment Thesis", clean)
        self.assertIn("## Business quality and competitive positioning", clean)
        self.assertNotIn("[E001", clean)
        self.assertNotIn("[comparison]", clean)

    def test_oversized_executive_thesis_splits_across_pdf_pages(self):
        paragraphs = "\n\n".join(
            f"Investment point {index}: recurring revenue, cash generation, valuation discipline, catalysts, and downside controls remain central to the thesis."
            for index in range(1, 55)
        )
        pdf = build_research_pdf({
            "request": {"symbols": ["AAPL", "MSFT"], "horizon": "1–3 years"},
            "status": "complete",
            "report": "## Executive Investment Thesis\n" + paragraphs,
            "comparison": [],
        })
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 3000)

    def test_sector_aware_pdf_export(self):
        pdf = build_research_pdf({
            "request": {"symbols": ["JPM"], "horizon": "1–3 years"},
            "report": "## Executive Investment Thesis\nBook value is central.",
            "comparison": [{"Ticker": "JPM", "P/B TTM": 1.8, "ROE": .16}],
            "sector_frameworks": [{
                "symbol": "JPM", "framework": "Banks / Financials",
                "description": "Book-value compounding and returns on equity.",
                "must_have": ["P/B TTM", "ROE"], "preferred": [],
            }],
        })
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 2000)

    def test_pdf_text_normalization_removes_unsupported_glyphs(self):
        raw = "Bull case " + chr(0x1F680) + " EPS " + chr(0x2265) + " 10 " + chr(0x2192) + " upside"
        safe = _font_safe(raw)
        self.assertNotIn(chr(0x1F680), safe)
        self.assertIn(">=", safe)
        self.assertIn("->", safe)

    def test_financial_trends_detect_decline_and_avoid_quarter_mismatch(self):
        source = Evidence("E001", "AAPL", "cash_flow", "Cash flow", "FMP", [
            {"fiscalYear": 2025, "date": "2025-09-30", "period": "FY", "reportedCurrency": "USD", "netCashProvidedByOperatingActivities": 111},
            {"fiscalYear": 2024, "date": "2024-09-30", "period": "FY", "reportedCurrency": "USD", "netCashProvidedByOperatingActivities": 118}])
        trend = financial_trends([source], ["AAPL"])[0].data[0]
        self.assertEqual(trend["direction"], "decrease")
        self.assertAlmostEqual(trend["yoy_pct"], -5.93220339)
        source.data[1]["period"] = "Q1"
        self.assertEqual(financial_trends([source], ["AAPL"]), [])

    def test_comparison_keeps_each_company_and_currency_separate(self):
        evidence = [
            Evidence("E001", "AAPL", "profile", "Profile", "FMP", [{"companyName": "Apple", "currency": "USD"}]),
            Evidence("E002", "AAPL", "income", "Income", "FMP", [{"revenue": 100, "reportedCurrency": "USD", "period": "FY"}]),
            Evidence("E003", "SAP", "profile", "Profile", "FMP", [{"companyName": "SAP", "currency": "USD"}]),
            Evidence("E004", "SAP", "income", "Income", "FMP", [{"revenue": 40, "reportedCurrency": "EUR", "period": "Q1"}]),
        ]
        first, second = comparison_rows(evidence, ["AAPL", "SAP"])
        self.assertEqual(first["Revenue (latest period)"], 100)
        self.assertEqual(second["Revenue (latest period)"], 40)
        self.assertEqual(second["Statement currency"], "EUR")
        self.assertEqual(second["Statement period"], "Q1")

    def test_context_is_scoped_and_does_not_leak_credentials(self):
        state = {"OPENAI_API_KEY": "do-not-send", "chat_history": ["private"],
                 "equity_report_payload": {"combined_scorecard": pd.DataFrame([
                     {"Ticker": "AAPL", "value": 1}, {"Ticker": "MSFT", "value": 2}]),
                     "pdf_bytes": b"private", "generated_at": "2026-01-01"}}
        evidence = collect_app_context(state, ["AAPL"])
        self.assertEqual(evidence[0].data["combined_scorecard"], [{"Ticker": "AAPL", "value": 1}])
        self.assertEqual(evidence[0].retrieved_at, "2026-01-01")
        self.assertNotIn("private", evidence_context(evidence))
        self.assertNotIn("do-not-send", evidence_context(evidence))

    def test_export_is_valid_json_and_redacts_embedded_keys(self):
        result = dumps({"api_key": "secret", "value": float("nan"), "url": "https://provider.test?a=1&apikey=secret"})
        self.assertNotIn("secret", result)
        self.assertIsNone(json.loads(result)["value"])

    def test_source_failure_does_not_discard_other_companies(self):
        source = FinancialDataSource("")
        source.client = Mock()
        def payload(symbol, **kwargs):
            if symbol == "BAD":
                raise RuntimeError("failure")
            return {"data": [{"symbol": symbol, "price": 5}]}
        for name in ("profile", "quote", "income_statement", "balance_sheet", "cashflow_statement",
                     "income_statement_ttm", "balance_sheet_ttm", "cashflow_statement_ttm",
                     "metrics_ratios_ttm", "key_metrics_ttm", "analyst_estimates",
                     "price_target_consensus", "historical_price_full"):
            getattr(source.client, name).side_effect = payload
        results = source.collect(ResearchRequest(["AAPL", "BAD"]), lambda _: None)
        self.assertTrue(any(e.symbol == "AAPL" and e.status == "ok" for e in results))
        self.assertTrue(all(e.status == "error" for e in results if e.symbol == "BAD"))

    def test_mcp_timeout_is_actually_enforced(self):
        client = FMPMCPClient("test", retries=0)
        client.timeout_seconds = 0.01
        class SlowClient:
            def __init__(self, *args):
                pass
            async def __aenter__(self):
                await asyncio.sleep(1)
            async def __aexit__(self, *args):
                pass
        with patch("langgraphagenticai.tools.fmp_mcp_client.MCPClient", SlowClient):
            result = client.quote("AAPL")
        self.assertFalse(result["ok"])

    def test_expired_fmp_budget_skips_network(self):
        client = FMPMCPClient("test", retries=0)
        with patch("langgraphagenticai.tools.fmp_mcp_client.MCPClient") as transport:
            with fmp_request_budget(0):
                result = client.quote("AAPL")
        transport.assert_not_called()
        self.assertFalse(result["ok"])

    @patch("langgraphagenticai.tools.earnings_transcript_tools.FMPMCPClient")
    def test_latest_transcript_never_uses_another_company(self, factory):
        client = factory.return_value
        client.latest_transcripts.return_value = {"data": [{"symbol": "MSFT", "content": "Wrong company"}]}
        client.transcript_dates_by_symbol.return_value = {"data": []}
        tools = {t.name: t for t in build_earnings_transcript_tools("test")}
        result = json.loads(tools["get_latest_earnings_transcript"].invoke({"symbol": "AAPL"}))
        self.assertFalse(result["ok"])
        self.assertNotIn("Wrong company", dumps(result))

    @patch("langgraphagenticai.tools.earnings_transcript_tools.FMPMCPClient")
    def test_latest_transcript_fetches_company_specific_period(self, factory):
        client = factory.return_value
        client.latest_transcripts.return_value = {"data": []}
        client.transcript_dates_by_symbol.return_value = {"data": [{"year": 2025, "quarter": 1}, {"year": 2026, "quarter": 2}]}
        client.search_transcripts.return_value = {"data": [{"symbol": "AAPL", "content": "Company guidance", "date": "2026-07-01"}]}
        tools = {t.name: t for t in build_earnings_transcript_tools("test")}
        result = json.loads(tools["get_latest_earnings_transcript"].invoke({"symbol": "AAPL"}))
        self.assertTrue(result["ok"])
        client.search_transcripts.assert_called_once_with(symbol="AAPL", year=2026, quarter=2)


class SerperTests(unittest.TestCase):
    @patch("langgraphagenticai.tools.serper_tools.requests.post")
    def test_news_request_and_source_normalization(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"news": [
            {"title": "News", "link": "https://example.org/story", "date": "2 hours ago", "snippet": "A result"},
            {"title": "Duplicate", "link": "https://example.org/story"},
            {"title": "Bad", "link": "javascript:alert(1)"}]}
        result = SerperClient("test-key").search("Apple AAPL", days=7)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(post.call_args.kwargs["json"]["tbs"], "qdr:d7")
        self.assertIn("timeout", post.call_args.kwargs)
        self.assertEqual(result["results"][0]["published"], "2 hours ago")

    @patch("langgraphagenticai.tools.serper_tools.requests.post")
    def test_missing_key_and_http_failures(self, post):
        self.assertFalse(SerperClient("").search("AAPL")["ok"])
        post.assert_not_called()
        post.return_value.status_code = 429
        result = SerperClient("test").search("AAPL")
        self.assertFalse(result["ok"])
        self.assertIn("429", result["error"])


class ManagerTests(unittest.TestCase):
    def manager(self, replies):
        llm = Mock()
        llm.invoke.side_effect = [SimpleNamespace(content=r) if isinstance(r, str) else r for r in replies]
        source = Mock()
        source.collect.return_value = [Evidence("", "AAPL", "income", "Income", "FMP", [{"revenue": 5}])]
        return ResearchManager(llm, source, SerperClient(""))

    def test_complete_run_and_followup_use_same_evidence(self):
        manager = self.manager(['{"questions": [], "tool_requests": [], "searches": []}',
                                "## Thesis\nReported revenue is 5 [E001].", '{"corrections": [], "unresolved": []}', "Revenue is 5 [E001]."])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "complete")
        self.assertIn("Evidence register", result["markdown"])
        self.assertEqual(result["evidence"][0]["id"], "E001")
        answer = manager.follow_up(result, "What is revenue?")
        self.assertIn("[E001]", answer)
        manager.financial_source.collect.assert_called_once()

    def test_planning_failure_and_writer_failure_keep_evidence(self):
        manager = self.manager([RuntimeError("planning unavailable"), RuntimeError("write unavailable")])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(len(result["warnings"]), 2)

    def test_no_evidence_does_not_generate_thesis(self):
        manager = self.manager(['{}'])
        manager.financial_source.collect.return_value = []
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("inconclusive", result["report"])
        self.assertEqual(manager.llm.invoke.call_count, 1)

    def test_unknown_citations_flagged(self):
        manager = self.manager(['{}', "A claim [E001, E999].", '{"corrections": [], "unresolved": []}'])
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        self.assertTrue(any("E999" in w for w in result["warnings"]))

    def test_tool_scope_and_budget(self):
        plan = {"tool_requests": [{"name": "example", "arguments": {"symbol": "MSFT"}}] * 12}
        manager = self.manager([json.dumps(plan), "Memo [E001]", '{"corrections": [], "unresolved": []}'])
        tool = Mock()
        tool.name, tool.description, tool.args = "example", "An example", {"symbol": {"type": "string"}}
        manager.tools = {"example": tool}
        result = manager.run(ResearchRequest(["AAPL"], include_news=False))
        tool.invoke.assert_not_called()
        self.assertEqual(len(result["evidence"]), 5)

    def test_serper_news_keeps_five_results_for_sentiment_coverage(self):
        manager = self.manager([])
        manager.serper = Mock()
        manager.serper.search.return_value = {
            "ok": True,
            "results": [{"title": f"Item {index}", "url": f"https://example.com/{index}",
                         "snippet": "Earnings and guidance update", "published": "1 day ago"}
                        for index in range(1, 6)],
        }
        items = manager._search("AAPL", "Apple earnings guidance", ResearchRequest(["AAPL"]), news=True)
        self.assertEqual(len(items[0].data), 5)
        self.assertIn("five grouped search results", items[0].note)
        manager.serper.search.assert_called_once_with(
            "Apple earnings guidance", news=True, days=30, limit=5,
        )


if __name__ == "__main__":
    unittest.main()
