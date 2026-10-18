"""Offline quote contracts and cross-workspace ribbon reuse."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.providers import market_strip as provider
from langgraphagenticai.ui.market_strip import market_strip_html


def quotes():
    now = datetime.now(timezone.utc) - timedelta(minutes=1)
    return [dict(symbol=symbol, price=100 + i, changePercentage=change, timestamp=now.timestamp(), previousClose=100) for i, (symbol, change) in enumerate(zip(provider.INDEXES.values(), [1.25, -2.5, 0., .5, -1.]))]


@pytest.fixture(autouse=True)
def clear_cache():
    cached = provider.load_market_strip
    cached.clear()
    yield
    cached.clear()


def test_quote_units_aliases_zero_and_independent_calculation():
    rows = quotes()
    rows[0].pop("changePercentage")
    rows[0].update(changesPercentage=1.25)
    rows[1].pop("changePercentage")
    rows[1].update(price=110, previousClose=100)
    result = provider.normalize_quotes(rows)
    assert result["^GSPC"]["percent"] == 1.25
    assert result["^IXIC"]["percent"] == pytest.approx(10.)
    assert result["^DJI"]["percent"] == 0
    assert result["^VIX"]["unit"] == "index points"
    assert result["^GSPC"]["as_of"]


@pytest.mark.parametrize("edit", [
    lambda r: r.update(price=0), lambda r: r.update(price=-1), lambda r: r.update(price=float("nan")),
    lambda r: r.update(price=True), lambda r: r.update(symbol="SPY"),
    lambda r: r.update(timestamp=datetime.now(timezone.utc).timestamp()+3600),
])
def test_invalid_quotes_never_fill_index_cells(edit):
    row = quotes()[0]
    edit(row)
    assert provider.normalize_quotes([row]) == {}


def test_missing_change_is_not_flat_and_undated_is_disclosed():
    row = quotes()[0]
    for field in ("changePercentage", "previousClose", "timestamp"):
        row.pop(field)
    normalized = provider.normalize_quotes([row])
    assert normalized["^GSPC"]["percent"] is None
    html = market_strip_html(normalized, {"status":"partial"})
    assert "Change unavailable" in html and "Stale / undated" in html
    assert "+0.00%" not in html


def test_cache_one_batch_and_no_credentials_in_packet(monkeypatch):
    get = Mock(return_value=quotes())
    monkeypatch.setattr(provider, "get_fmp_json", get)
    first = provider.load_market_strip("synthetic-secret")
    assert first == provider.load_market_strip("synthetic-secret") and get.call_count == 1
    assert first["status"] == "available" and len(first["rows"]) == 5
    assert "synthetic-secret" not in str(first)
    assert get.call_args.kwargs["timeout"] == (3, 8)
    assert provider.load_market_strip("")["status"] == "unconfigured" and get.call_count == 1


def test_partial_batch_fallback_preserves_successful_whole_quotes(monkeypatch):
    data = quotes()
    fallback = [dict(data[0], price=999), *data[1:]]
    get = Mock(side_effect=[data[:1], fallback])
    monkeypatch.setattr(provider, "get_fmp_json", get)
    packet = provider.load_market_strip("synthetic")
    assert get.call_count == 2 and packet["status"] == "available"
    assert packet["rows"]["^GSPC"]["price"] == data[0]["price"]
    assert len(packet["rows"]) == 5


def test_failures_are_bounded_safe_and_keep_successful_cells(monkeypatch):
    get = Mock(side_effect=[quotes()[:1], RuntimeError("apikey=secret")])
    monkeypatch.setattr(provider, "get_fmp_json", get)
    packet = provider.load_market_strip("synthetic")
    assert packet["status"] == "partial" and get.call_count == 2
    assert "secret" not in str(packet) and len(packet["rows"]) == 1


def test_safe_signed_html_all_five_and_stale_metadata():
    rows = provider.normalize_quotes(quotes())
    html = market_strip_html(rows, {"status":"available"})
    assert all(name.replace("&", "&amp;") in html for name in provider.INDEXES)
    assert "+1.25%" in html and "-2.50%" in html and "+0.00%" in html
    assert "MARKET CONTEXT" not in html and "index levels" in html
    rows["^GSPC"].update(as_of=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat(), retained=True, change_basis='<script>bad</script>')
    html = market_strip_html(rows, {"status":"partial"})
    assert "Saved" in html and "stale" in html and "&lt;script&gt;" in html and "<script>" not in html


def test_ui_partial_recovery_keeps_original_dates_and_credential_scope(monkeypatch):
    rows = provider.normalize_quotes(quotes())
    for row in rows.values():row["retrieved_at"] = "original retrieval"
    packet = {"rows":rows, "status":"available"}
    monkeypatch.setattr(provider, "load_market_strip", lambda key: packet)
    app = AppTest.from_string("""
import streamlit as st
from langgraphagenticai.ui.app_shell import render_market_strip
key=st.text_input("Synthetic credential", value="first")
render_market_strip(key)
""", default_timeout=30).run()
    assert not app.exception
    packet = {"rows":{}, "status":"unavailable"}
    app.run()
    assert not app.exception and "original retrieval" in " ".join(item.value for item in app.markdown)
    assert "Saved" in " ".join(item.value for item in app.markdown)
    app.text_input[0].set_value("second").run()
    assert "original retrieval" not in " ".join(item.value for item in app.markdown)
    assert "Unavailable" in " ".join(item.value for item in app.markdown)


def test_every_ribbon_workspace_reuses_cached_quotes(monkeypatch):
    import streamlit as st
    from langgraphagenticai import main
    from langgraphagenticai.ui import ai_valuation_tab, deep_research_workspace, guided_research_tab
    get = Mock(return_value=quotes())
    monkeypatch.setattr(provider, "get_fmp_json", get)
    monkeypatch.setattr(main.LoadStreamlitUI, "load_streamlit_ui", lambda self: dict(active_page=st.session_state["test_ribbon_page"], FMP_API_KEY="synthetic", OPENAI_API_KEY="", selected_model="gpt-5"))
    for name in ("render_equity_report_tab", "render_stock_screener_tab", "render_portfolio_optimizer_tab", "render_ai_portfolio_manager_tab", "render_terminal_status", "_render_status_panel"):
        monkeypatch.setattr(main, name, lambda *a, **kw: None)
    monkeypatch.setattr(main, "render_command_bar", lambda: "")
    monkeypatch.setattr(ai_valuation_tab, "render_ai_valuation_tab", lambda **kw: None)
    monkeypatch.setattr(deep_research_workspace, "render_deep_research_workspace", lambda **kw: None)
    monkeypatch.setattr(guided_research_tab, "render_guided_research_tab", lambda **kw: None)
    app = AppTest.from_string("""
import streamlit as st
from langgraphagenticai.main import load_langgraph_agenticai_app
st.selectbox("Workspace", ["Equity Report", "AI Valuation", "Stock Screener", "Portfolio Lab", "Deep Research", "Deep Research V2", "Research"], key="test_ribbon_page")
load_langgraph_agenticai_app()
""", default_timeout=30)
    app.session_state["research_mode"] = "Guided research"
    app.run()
    for page in app.selectbox(key="test_ribbon_page").options:
        app.selectbox(key="test_ribbon_page").set_value(page).run()
        assert not app.exception and "+1.25%" in " ".join(item.value for item in app.markdown) and "-2.50%" in " ".join(item.value for item in app.markdown)
    assert get.call_count == 1


def test_quote_arriving_during_request_is_not_mistaken_for_future_data(monkeypatch):
    start = datetime.now(timezone.utc)
    completed = start + timedelta(seconds=3)
    data = quotes()
    for row in data:row["timestamp"] = (start + timedelta(seconds=2)).timestamp()
    class Clock:
        calls = 0
        @staticmethod
        def now(tz):
            Clock.calls += 1
            return start if Clock.calls == 1 else completed
        fromtimestamp = datetime.fromtimestamp
    monkeypatch.setattr(provider, "datetime", Clock)
    get = Mock(return_value=data)
    monkeypatch.setattr(provider, "get_fmp_json", get)
    packet = provider.load_market_strip("synthetic")
    assert packet["status"] == "available" and get.call_count == 1
    assert packet["retrieved_at"] == completed.isoformat()
    assert all(row["retrieved_at"] == completed.isoformat() for row in packet["rows"].values())
