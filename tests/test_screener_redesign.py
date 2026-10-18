"""Offline Screener page-composition checks with saved and missing-key states."""

from unittest.mock import Mock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.ui import stock_screener_tab as ui


SAVED = '''
from langgraphagenticai.ui.stock_screener_tab import render_stock_screener_tab
render_stock_screener_tab('synthetic')
'''
MISSING_KEY = '''
from langgraphagenticai.ui.stock_screener_tab import render_stock_screener_tab
render_stock_screener_tab('')
'''


def _saved_frame():
    return pd.DataFrame([{
        "Ticker": "AAPL", "Company Name": "Apple", "Sector": "Technology",
        "Industry": "Hardware", "Market Cap": 3_000_000_000_000,
        "Price": 200, "RSI": 50, "Company Description": "Synthetic fixture",
    }])


def test_saved_screener_retains_filters_table_csv_and_handoff_without_provider_call(monkeypatch):
    screen = Mock()
    enrich = Mock()
    monkeypatch.setattr(ui, "fmp_company_screener_safe", screen)
    monkeypatch.setattr(ui, "fetch_all_metrics", enrich)
    app = AppTest.from_string(SAVED, default_timeout=30)
    app.session_state["stock_screener_payload"] = {
        "generated_at": "2026-10-14T12:00:00Z", "results": _saved_frame(),
    }
    app.run()
    assert not app.exception
    assert not any(item.value == "Stock Screener" for item in app.subheader)
    assert any("Company universe" in item.value for item in app.markdown)
    assert [item.label for item in app.expander] == [
        "Server-side range filters", "Enrichment + final output controls", "Post-screen metric filters",
    ]
    assert any("this is not a new retrieval time" in item.value for item in app.caption)
    assert any(item.label == "Download Results CSV" for item in app.get("download_button"))
    assert app.selectbox(key="screener_focus").value == "AAPL"
    assert any(item.key == "screener_open_intro" for item in app.button)
    assert any(item.label == "Run Screener" for item in app.button)
    app.run()
    screen.assert_not_called()
    enrich.assert_not_called()


def test_missing_fmp_key_still_displays_saved_result_without_form():
    app = AppTest.from_string(MISSING_KEY, default_timeout=30)
    app.session_state["stock_screener_payload"] = {
        "generated_at": "2026-10-14T12:00:00Z", "results": _saved_frame(),
    }
    app.run()
    assert not app.exception
    assert any("FMP API key" in item.value for item in app.error)
    assert any(item.label == "Download Results CSV" for item in app.get("download_button"))
    assert not any(item.label == "Run Screener" for item in app.button)


@pytest.mark.parametrize("stage", ["screen", "industry", "enrichment", "advanced"])
def test_failed_new_screener_run_keeps_prior_identity_and_export(monkeypatch, stage):
    screen_rows = pd.DataFrame([{"ticker": "NEW", "industry": "Hardware", "marketCap": 1_000_000}])
    screen = Mock(return_value=(pd.DataFrame() if stage == "screen" else screen_rows,
                                {"pages": 1, "warnings": ["synthetic warning"]}))
    enrich = Mock(return_value=pd.DataFrame() if stage == "enrichment" else _saved_frame().assign(Ticker="NEW"))
    monkeypatch.setattr(ui, "fmp_company_screener_safe", screen)
    monkeypatch.setattr(ui, "fetch_all_metrics", enrich)
    if stage == "advanced":
        monkeypatch.setattr(ui, "apply_metric_filters", lambda *_args, **_kwargs: pd.DataFrame())
    app = AppTest.from_string(SAVED, default_timeout=30)
    app.session_state["stock_screener_payload"] = {
        "generated_at": "2026-10-14T12:00:00Z", "results": _saved_frame(),
    }
    app.run()
    if stage == "industry":
        next(item for item in app.text_input if item.label == "Industry contains").set_value("No-match")
    if stage == "advanced":
        next(item for item in app.checkbox if item.label == "Enable post-screen metric filters").set_value(True)
    next(item for item in app.button if item.label == "Run Screener").click().run()
    assert not app.exception
    assert app.session_state["stock_screener_payload"]["generated_at"] == "2026-10-14T12:00:00Z"
    assert app.selectbox(key="screener_focus").value == "AAPL"
    assert any("earlier saved screen" in item.value for item in app.warning)
    assert any(item.label == "Download Results CSV" for item in app.get("download_button"))
    assert any("API warnings encountered" in item.value for item in app.caption) == (stage in {"enrichment", "advanced"})
    app.run()
    assert any("earlier saved screen" in item.value for item in app.warning)
    screen.assert_called_once()
    assert enrich.call_count == (0 if stage in {"screen", "industry"} else 1)
