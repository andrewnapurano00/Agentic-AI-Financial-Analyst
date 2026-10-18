"""Saved stakeholder presentation contracts; no live providers/models."""
from copy import deepcopy
import io
from streamlit.testing.v1 import AppTest
from langgraphagenticai.deep_research.executive import decision_sections, executive_metric_groups, executive_prose


def test_decision_is_one_bounded_paragraph_with_three_parts_and_no_references():
    decision={"summary":"Resilient growth [E001]. " * 100, "preferred_ticker":"AAPL",
        "decisions":[{"ticker":"AAPL","recommendation":"BUY","confidence":72,
        "rationale":"Long analysis "*100,"catalysts":["Product launch [E002]"],
        "risks":["Demand slows [E003]"], "invalidation_signals":["Cash conversion deteriorates"]}],
        "dissent":"Valuation is demanding.", "evidence_limitations":["News coverage is partial."]}
    saved=deepcopy(decision)
    sections=decision_sections(decision)
    assert [label for label,_ in sections]==["Decision","Key drivers","Risks & watchpoints"]
    assert sum(len(value.split()) for _,value in sections)<=130
    assert all("\n" not in value and "E001" not in value for _,value in sections)
    assert "BUY" in sections[0][1] and "72%" in sections[0][1]
    assert "Demand slows" in sections[2][1] and "partial" in sections[2][1]
    assert decision==saved


def test_source_markers_and_links_hidden_without_removing_figures():
    value=executive_prose("Revenue grew 12% [E001, E002]. [Earnings](https://example.com/a) supports USD 2.5B. https://example.com/raw [Sources: E003]")
    assert "12%" in value and "USD 2.5B" in value and "Earnings" in value
    assert "E001" not in value and "https://" not in value and "Sources:" not in value


def test_technical_metrics_cannot_be_crowded_out_and_sector_exclusions_survive():
    rows=[{"Ticker":"AAPL","Sector":"Technology","Industry":"Software", "Sector framework":"Technology / Software / Semis",
        "Revenue CAGR 3Y":0,"Latest Gross Margin":.4,"Forward P/E":20,"P/B TTM":4,
        "% From SMA 50":0,"% From SMA 200":10,"RSI 14":55,"1Y price return (%)":12}]
    groups=executive_metric_groups(rows)
    assert "Revenue CAGR 3Y" in groups["Fundamentals"]
    assert "P/B TTM" not in groups["Valuation"]
    assert "Forward P/E" in groups["Valuation"]
    assert "% From SMA 50" in groups["Momentum & technicals"]
    assert "RSI 14" in groups["Momentum & technicals"]


def test_saved_and_quick_decisions_use_same_compact_renderer():
    app=AppTest.from_string('''
import streamlit as st
from langgraphagenticai.ui.research_decision import render_executive_decision
render_executive_decision({"verdict":"WATCH","confidence":55,"summary":"Wait for momentum [E001].", "risks":["Demand weakens"],"limitations":["Partial news"]})
''',default_timeout=30).run()
    assert not app.exception
    assert len(app.markdown)==1
    assert "E001" not in app.markdown[0].value
    assert len(app.expander)==1 and app.expander[0].label=="Full decision & limitations"
    assert "WATCH" in app.markdown[0].value and "Partial news" in app.markdown[0].value


def test_executive_thesis_hides_links_but_news_keeps_article_links():
    from langgraphagenticai.deep_research.presentation import clean_report_markdown
    report="## Executive Investment Thesis\nGrowth [E001] from [earnings](https://example.com/earnings).\n## News, Sentiment & Catalysts\n[Announcement](https://example.com/news)."
    displayed=clean_report_markdown(report)
    thesis,news=displayed.split("## News,")
    assert "https://" not in thesis and "earnings" in thesis
    assert "https://example.com/news" in news and "E001" not in displayed


def test_pdf_retains_dedicated_technical_section_and_original_audit():
    from langgraphagenticai.deep_research.presentation import build_research_pdf
    from pdfminer.high_level import extract_text
    result={"request":{"symbols":["AAPL"]},"status":"needs_review",
        "report":"## Executive Investment Thesis\nWatch growth [E001].\n## Risks\nDemand.\n## Thesis invalidation\nMargins weaken.",
        "comparison":[{"Ticker":"AAPL","Sector":"Technology", "Revenue CAGR 3Y":10,
            "Forward P/E":20,"RSI 14":55,"% From SMA 50":0,"Quote currency":"USD"}]}
    saved=deepcopy(result)
    text=extract_text(io.BytesIO(build_research_pdf(result)))
    assert "Momentum & technicals" in text and "RSI 14" in text
    assert "Fundamentals" in text and "Valuation" in text and "Draft" in text
    assert "E001" not in text and result==saved


def test_cross_sector_priorities_include_bank_returns_and_valuation():
    tech={"Ticker":"AAPL","Sector framework":"Technology / Software / Semis"}
    from langgraphagenticai.deep_research.sector import SECTOR_METRIC_REGISTRY
    tech.update({k:1 for k in SECTOR_METRIC_REGISTRY[tech["Sector framework"]]["must_have"]})
    bank={"Ticker":"JPM","Sector framework":"Banks / Financials","ROE":.15,"ROA":.02,"P/B TTM":1.2}
    groups=executive_metric_groups([tech,bank])
    assert "ROE" in groups["Fundamentals"] and "ROA" in groups["Fundamentals"]
    assert "P/B TTM" in groups["Valuation"]


def test_statement_references_hidden_in_summary_preserving_financial_conclusions():
    from langgraphagenticai.deep_research.summary_text import clean_summary_references
    value="According to the quarterly income statement, revenue grew 12% (FY2026). Cash generation improved (cash_flow_ttm.freeCashFlow; E004). The balance sheet shows debt declined to USD 2B."
    clean=clean_summary_references(value)
    assert "12%" in clean and "FY2026" in clean and "USD 2B" in clean
    assert clean.startswith("Revenue grew") and "Debt declined" in clean
    assert "statement" not in clean.lower() and "balance sheet" not in clean.lower()
    assert "cash_flow_ttm" not in clean and "E004" not in clean


def test_statement_detail_is_hidden_in_body_and_preserved_in_audit():
    from langgraphagenticai.deep_research.presentation import clean_report_markdown
    report="## Executive Investment Thesis\nThe income statement shows revenue grew 12% [income_statement; E001].\n## Financial detail\nThe income statement shows revenue grew 12% [E001]."
    clean=clean_report_markdown(report)
    summary,body=clean.split("## Financial detail")
    assert "statement" not in summary.lower() and "12%" in summary
    assert "income statement" not in body and "12%" in body
    assert "income_statement" in report


def test_saved_report_reader_and_pdf_hide_bare_statement_labels_and_grouped_ids():
    import io
    from pdfminer.high_level import extract_text
    from langgraphagenticai.deep_research.presentation import clean_report_markdown, build_research_pdf
    report = ("## Executive Investment Thesis\nRevenue grew 12% in FY2026 [E001][E029][comparison]. "
              "The quarterly income statement supports the outlook.\n"
              "## Financial strength\nThe balance sheet remains resilient with USD 2B of cash. "
              "Cash flow statements indicate strong conversion [E004].")
    result = dict(status="complete", report=report, request={"symbols": ["AAPL"]}, comparison=[], evidence=[])
    outputs = [clean_report_markdown(report), extract_text(io.BytesIO(build_research_pdf(result)))]
    for output in outputs:
        assert "statement" not in output.lower() and "balance sheet" not in output.lower()
        assert "E001" not in output and "comparison]" not in output
        assert "12%" in output and "FY2026" in output and "USD 2B" in output
    assert result["report"] == report


def test_preview_only_shows_business_thesis_not_statement_details():
    from langgraphagenticai.deep_research.executive import executive_preview
    report="## Executive Investment Thesis\nAccording to the quarterly income statement, revenue rose 12% (FY2026).\n## Financial detail\nAnnual statements were collected and validated."
    clean=executive_preview(report)
    assert "12%" in clean and "FY2026" in clean
    assert "statement" not in clean.lower() and "collected" not in clean.lower()
    assert "Methodology" not in executive_preview("## Executive Investment Thesis\nRevenue rose.\nMethodology: four statements summed.")


def test_statement_gap_keeps_uncertainty_without_source_diagnostics():
    decision={"summary":"Growth remains attractive.","verdict":"WATCH","limitations":["Income statement dataset unavailable from FMP"]}
    rendered=" ".join(value for _,value in decision_sections(decision))
    assert "statement" not in rendered.lower() and "FMP" not in rendered and "dataset" not in rendered
    assert "uncertain" in rendered
    assert "Income statement" in decision["limitations"][0]
