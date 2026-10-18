"""Offline Portfolio Lab page-composition and preserved-action checks."""

from unittest.mock import Mock

import pandas as pd
from streamlit.testing.v1 import AppTest

from langgraphagenticai.ui import ai_portfolio_manager_tab as manager_ui
from langgraphagenticai.ui import portfolio_optimizer_tab as optimizer_ui


MANAGER = '''
from langgraphagenticai.ui.ai_portfolio_manager_tab import render_ai_portfolio_manager_tab
render_ai_portfolio_manager_tab(openai_api_key="synthetic", model_name="synthetic")
'''
OPTIMIZER = '''
from langgraphagenticai.ui.portfolio_optimizer_tab import render_portfolio_optimizer_tab
render_portfolio_optimizer_tab()
'''


def _bundle():
    return {
        "portfolio_summary": {"portfolio_value": 1000, "analysis_count": 1},
        "run_diagnostics": {"agentic_ai_status": "complete", "target_weight_sum": 0.9},
        "portfolio_committee_summary": "Saved committee summary.",
        "recommendation_table": pd.DataFrame([{
            "ticker": "AAPL", "final_action": "HOLD", "current_weight": 0.3,
            "target_weight": 0.25, "delta_weight": -0.05, "trade_value": -50,
            "committee_reason": "Saved reasoning.",
        }]),
        "sector_allocation_table": pd.DataFrame([{
            "sector": "Technology", "current_weight": 0.3, "target_weight": 0.25,
            "delta_weight": -0.05,
        }]),
        "rebalance_table": pd.DataFrame(),
        "evidence_table": pd.DataFrame(),
        "monitoring_table": pd.DataFrame(),
    }


def test_saved_manager_recommendations_show_sector_and_committee_rail_without_run(monkeypatch):
    run = Mock()
    monkeypatch.setattr(manager_ui, "run_hybrid_portfolio_workflow", run)
    app = AppTest.from_string(MANAGER, default_timeout=30)
    app.session_state["pm_hybrid_bundle_v1"] = _bundle()
    app.run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Recommendations", "Rebalance Trades", "Agent Debate", "Evidence Scores",
        "Sector Exposure", "Monitoring", "Diagnostics", "AI Chat",
    ]
    assert any("Sector allocation" in item.value for item in app.markdown)
    assert any("AI Committee Summary" in item.value for item in app.markdown)
    assert any("Saved committee summary" in item.value for item in app.markdown)
    assert any("Committee Decision Summaries" in item.value for item in app.markdown)
    assert any("portfolio-recommendations-marker" in item.value for item in app.markdown)
    assert any("max-width:1100px" in item.value and "flex-wrap:wrap" in item.value for item in app.markdown)
    assert any(item.label == "Download recommendation table CSV" for item in app.get("download_button"))
    app.run()
    run.assert_not_called()


def test_optimizer_setup_and_invalid_ticker_keep_provider_idle(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(optimizer_ui, "fetch_prices_yahoo", fetch)
    app = AppTest.from_string(OPTIMIZER, default_timeout=30).run()
    assert not app.exception
    assert any("Configure portfolio analysis" in item.value for item in app.markdown)
    assert any(item.label == "Run Portfolio Analysis" for item in app.button)
    app.text_area[0].set_value("BAD/TICKER")
    next(item for item in app.button if item.label == "Run Portfolio Analysis").click().run()
    assert not app.exception
    assert any("valid ticker" in item.value for item in app.error)
    fetch.assert_not_called()


def test_optimizer_completed_snapshot_rerenders_without_fetch_or_simulation_and_survives_failed_run(monkeypatch):
    prices = pd.DataFrame(
        {"AAA": [100.0, 101.0, 102.0], "BBB": [90.0, 91.0, 92.0]},
        index=pd.date_range("2024-01-02", periods=3),
    )
    fetch = Mock(return_value=prices)
    simulate = Mock(return_value=pd.DataFrame([
        {"ret": .08, "stdev": .12, "sharpe": .67, "AAA": .6, "BBB": .4},
        {"ret": .06, "stdev": .10, "sharpe": .60, "AAA": .4, "BBB": .6},
    ]))
    monkeypatch.setattr(optimizer_ui, "fetch_prices_yahoo", fetch)
    monkeypatch.setattr(optimizer_ui, "simulate_random_portfolios", simulate)
    monkeypatch.setattr(optimizer_ui, "make_asset_summary_table", lambda *_: pd.DataFrame({"Ticker": ["AAA", "BBB"]}))
    monkeypatch.setattr(optimizer_ui, "build_crisis_role_table", lambda *_: pd.DataFrame({"Ticker": ["AAA", "BBB"]}))
    monkeypatch.setattr(optimizer_ui, "pretty_crisis_table", lambda frame: frame)
    monkeypatch.setattr(optimizer_ui, "plot_efficient_frontier", lambda *args: object())
    monkeypatch.setattr(optimizer_ui, "plot_risk_buckets", lambda *args: None)
    monkeypatch.setattr(optimizer_ui, "plot_crisis_roles", lambda *args: None)
    monkeypatch.setattr(optimizer_ui.st, "pyplot", Mock())
    monkeypatch.setattr(optimizer_ui.plt, "close", Mock())
    app = AppTest.from_string(OPTIMIZER, default_timeout=30).run()
    app.text_area[0].set_value("AAA, BBB")
    next(item for item in app.button if item.label == "Run Portfolio Analysis").click().run()
    assert not app.exception
    assert [item.value for item in app.subheader if item.value[:2] in {"1.", "2.", "3.", "4.", "5."}] == [
        "1. Price Data", "2. Efficient Frontier", "3. Risk / Return Table",
        "4. Crisis Fingerprint Roles", "5. Key Portfolio Weights",
    ]
    saved = app.session_state["portfolio_optimizer_view_v1"]
    assert list(saved["frontier"].columns) == ["ret", "stdev", "sharpe"]
    assert len(saved["price_tail"]) <= 5
    assert set(app.session_state["portfolio_optimizer_payload"]) == {"generated_at", "risk_table", "regime", "weights"}
    first_time = saved["generated_at"]
    app.run()
    assert not app.exception
    fetch.assert_called_once()
    simulate.assert_called_once()
    app.text_area[0].set_value("BAD/TICKER")
    next(item for item in app.button if item.label == "Run Portfolio Analysis").click().run()
    assert not app.exception
    assert app.session_state["portfolio_optimizer_view_v1"]["generated_at"] == first_time
    assert any("earlier saved analysis" in item.value for item in app.warning)
    assert any("valid ticker" in item.value for item in app.error)
    app.run()
    assert any("earlier saved analysis" in item.value for item in app.warning)
    fetch.assert_called_once()
    simulate.assert_called_once()


def test_invalid_custom_weights_still_complete_core_optimizer_analysis(monkeypatch):
    prices = pd.DataFrame(
        {"AAA": [100.0, 101.0, 102.0], "BBB": [90.0, 91.0, 92.0]},
        index=pd.date_range("2024-01-02", periods=3),
    )
    fetch = Mock(return_value=prices)
    simulate = Mock(return_value=pd.DataFrame([
        {"ret": .08, "stdev": .12, "sharpe": .67, "AAA": .6, "BBB": .4},
        {"ret": .06, "stdev": .10, "sharpe": .60, "AAA": .4, "BBB": .6},
    ]))
    monkeypatch.setattr(optimizer_ui, "fetch_prices_yahoo", fetch)
    monkeypatch.setattr(optimizer_ui, "simulate_random_portfolios", simulate)
    monkeypatch.setattr(optimizer_ui, "make_asset_summary_table", lambda *_: pd.DataFrame({"Ticker": ["AAA", "BBB"]}))
    monkeypatch.setattr(optimizer_ui, "build_crisis_role_table", lambda *_: pd.DataFrame({"Ticker": ["AAA", "BBB"]}))
    monkeypatch.setattr(optimizer_ui, "pretty_crisis_table", lambda frame: frame)
    monkeypatch.setattr(optimizer_ui, "plot_efficient_frontier", lambda *args: object())
    monkeypatch.setattr(optimizer_ui, "plot_risk_buckets", lambda *args: None)
    monkeypatch.setattr(optimizer_ui, "plot_crisis_roles", lambda *args: None)
    monkeypatch.setattr(optimizer_ui.st, "pyplot", Mock())
    monkeypatch.setattr(optimizer_ui.plt, "close", Mock())
    app = AppTest.from_string(OPTIMIZER, default_timeout=30).run()
    app.text_area[0].set_value("AAA, BBB")
    next(item for item in app.selectbox if item.label == "Test portfolio").set_value("Custom weights")
    next(item for item in app.text_input if item.label == "Custom weights").set_value("bad weights")
    next(item for item in app.button if item.label == "Run Portfolio Analysis").click().run()
    assert not app.exception
    assert app.error
    assert len(app.error) == 1
    assert "User Test Portfolio was omitted" in app.error[0].value
    assert app.session_state["portfolio_optimizer_last_attempt"]["status"] == "complete"
    assert app.session_state["portfolio_optimizer_view_v1"]["test_row"] is None
    assert app.session_state["portfolio_optimizer_view_v1"]["test_metrics"] is None
    assert "weights" in app.session_state["portfolio_optimizer_payload"]
    assert not any("User Test Portfolio" in item.value for item in app.markdown)
    app.run()
    assert not app.exception
    assert len(app.error) == 1
    assert "User Test Portfolio was omitted" in app.error[0].value
    fetch.assert_called_once()
    simulate.assert_called_once()
