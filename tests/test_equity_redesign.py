"""Offline active Equity Report presentation checks with a saved synthetic scorecard."""

from unittest.mock import Mock

import pandas as pd
from streamlit.testing.v1 import AppTest

from langgraphagenticai.ui import equity_report_tab as ui


HARNESS = '''
from langgraphagenticai.ui.equity_report_tab import render_equity_report_tab
render_equity_report_tab(fmp_api_key="synthetic", openai_api_key="", model_name="synthetic")
'''


def test_equity_research_card_uses_shared_navy_gold_tokens(monkeypatch):
    markdown = Mock()
    monkeypatch.setattr(ui.st, "markdown", markdown)
    ui.inject_equity_research_report_css()
    css = markdown.call_args.args[0]
    assert "background: var(--ax-panel, #121D2B)" in css
    assert "color: var(--ax-text, #E6EBF2)" in css
    assert "color: var(--ax-amber, #C8AA73)" in css
    assert "background: #FFFFFF" not in css


def test_saved_active_report_keeps_five_tabs_and_stacked_thesis_context_without_collection(monkeypatch):
    collect = Mock()
    monkeypatch.setattr(ui, "prepare_financials", collect)
    monkeypatch.setattr(ui, "add_equity_research_decision_layer", lambda frame, peer_group: frame)
    monkeypatch.setattr(ui, "add_story_template_fields", lambda frame: frame)
    monkeypatch.setattr(ui, "_build_research_ranking_table", lambda frame: pd.DataFrame())
    monkeypatch.setattr(ui, "build_story_report_tables", lambda frame, peer_group: {})
    monkeypatch.setattr(ui, "build_executive_summary_paragraph", lambda frame: "Saved deterministic thesis.")
    monkeypatch.setattr(ui, "generate_story_pdf_report", lambda *args, **kwargs: b"synthetic pdf")
    monkeypatch.setattr(ui, "make_display_df", lambda frame: frame)
    monkeypatch.setattr(ui, "render_sector_metric_coverage_audit", lambda *args: None)
    monkeypatch.setattr(ui, "build_price_return_long_df", lambda *args: pd.DataFrame())
    monkeypatch.setattr(ui, "build_selected_period_return_table", lambda frame: pd.DataFrame())
    monkeypatch.setattr(ui, "get_sector_config", lambda peer_group: {"description": "Synthetic framework."})
    app = AppTest.from_string(HARNESS, default_timeout=30)
    app.session_state["equity_report_payload"] = {
        "generated_at": "2026-10-14T12:00:00+00:00", "tickers": ["AAPL"],
        "combined_scorecard": pd.DataFrame([{"Ticker": "AAPL", "Final Rank": 1}]),
        "peer_group": "General / Cross-Sector", "gpt_note": None,
        "price_history": {}, "excel_bytes": b"synthetic xlsx",
    }
    app.run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "THESIS", "PERFORMANCE", "FINANCIALS / VALUATION", "SOURCES / AUDIT", "EXPORTS",
    ]
    assert any("Saved comparison" in item.value for item in app.markdown)
    assert any("Generation time is separate from source dates" in item.value for item in app.caption)
    assert any("equity-thesis-marker" in item.value for item in app.markdown)
    assert any("max-width:1100px" in item.value for item in app.markdown)
    assert any("Saved deterministic thesis" in item.value for item in app.markdown)
    assert {button.label for button in app.get("download_button")} >= {
        "Download PDF Report", "Download Excel Research Pack", "Download Display CSV", "Download Raw CSV",
    }
    app.run()
    collect.assert_not_called()
