from unittest.mock import Mock
from streamlit.testing.v1 import AppTest
from langgraphagenticai.ui import ai_portfolio_manager_tab as ui


def test_manager_settings_belong_to_manager_tab_and_rerun_without_calls(monkeypatch):
    run = Mock(return_value={})
    monkeypatch.setattr(ui, "run_hybrid_portfolio_workflow", run)
    app = AppTest.from_string(
        "import streamlit as st\n"
        "from langgraphagenticai.ui.ai_portfolio_manager_tab import render_ai_portfolio_manager_tab\n"
        "optimizer, manager = st.tabs(['Optimizer', 'AI Portfolio Manager'])\n"
        "with optimizer: st.write('Optimizer fixture')\n"
        "with manager: render_ai_portfolio_manager_tab(openai_api_key='synthetic', model_name='synthetic')",
        default_timeout=30)
    app.run()
    assert not app.exception
    assert not app.sidebar.slider and not app.sidebar.button and not app.sidebar.text_input
    manager = next(tab for tab in app.tabs if tab.label == "AI Portfolio Manager")
    labels = [slider.label for slider in manager.slider]
    assert labels == ["Maximum position weight", "Maximum sector weight", "Target cash buffer", "Ignore trades smaller than"]
    assert len(app.tabs[0].slider) == 0
    assert manager.slider[0].value == .18 and manager.slider[1].value == .35
    assert manager.slider[3].proto.format == "%.4f"
    assert manager.slider[3].proto.step == .0005
    manager.slider[0].set_value(.22).run()
    assert not app.exception
    run.assert_not_called()
    assert app.slider[0].value == .22
    next(button for button in app.button if button.label == "Run hybrid AI committee").click().run()
    assert not app.exception
    assert run.call_count == 1
    assert run.call_args.kwargs["max_weight"] == .22
    assert run.call_args.kwargs["max_sector_weight"] == .35
    assert run.call_args.kwargs["min_trade_weight_change"] == .0025
    app.run()
    assert run.call_count == 1 and app.slider[0].value == .22
