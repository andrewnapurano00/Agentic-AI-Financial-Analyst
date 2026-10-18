"""Bounded P02 shell and navigation contracts; synthetic and offline."""

from streamlit.testing.v1 import AppTest

from langgraphagenticai.ui.app_shell import PAGE_LABELS


ROUTES = (
    "Introduction", "Top Movers", "Stock Screener", "Research",
    "Equity Report", "AI Valuation", "Deep Research", "Portfolio Lab",
)


def test_market_brief_is_display_label_only():
    assert PAGE_LABELS["Introduction"][0] == "Market Brief"
    assert set(ROUTES) <= set(PAGE_LABELS)


def test_sidebar_single_radio_preserves_route_values_and_settings(monkeypatch):
    from langgraphagenticai.ui.streamlitui import loadui

    monkeypatch.setattr(loadui, "_resolve_secret", lambda *_: "")
    app = AppTest.from_string("""
from langgraphagenticai.ui.streamlitui.loadui import LoadStreamlitUI
controls = LoadStreamlitUI().load_streamlit_ui()
""").run()
    assert not app.exception
    radio = app.radio(key="active_workspace")
    assert tuple(radio.options) == ("Market Brief",) + ROUTES[1:]
    assert app.session_state["active_workspace"] == "Introduction"
    radio.set_value("Deep Research").run()
    assert app.session_state["active_workspace"] == "Deep Research"
    assert not app.exception
    assert any(item.label == "Select OpenAI Model" for item in app.selectbox)
    assert any(item.label == "Select Use Case" for item in app.selectbox)
    assert any(item.label == "Show debug trace" for item in app.checkbox)
    model = next(item for item in app.selectbox if item.label == "Select OpenAI Model")
    chosen = model.options[-1]
    model.set_value(chosen).run()
    app.radio(key="active_workspace").set_value("Research").run()
    assert next(item for item in app.selectbox if item.label == "Select OpenAI Model").value == chosen
