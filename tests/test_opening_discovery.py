"""D01-D08 opening discovery regressions; all evidence is synthetic/offline."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.providers import discovery
from langgraphagenticai.ui import market_overview_data
from langgraphagenticai.analysis.discovery import rank_discovery, sector_summary
from langgraphagenticai.analysis.saved_interpretation import save_interpretation, interpretation_matches
from langgraphagenticai.state.discovery import DiscoveryState, queue_discovery, apply_discovery, queue_discovery_research
from langgraphagenticai.ui.workspace_handoff import apply_pending_handoff, queue_handoff
from langgraphagenticai.state.research_context import ResearchContext


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), float("-inf"), True, False, "bad"])
def test_nonfinite_missing_not_zero(value):
    assert discovery.finite_number(value) is None


def test_zero_and_one_bar_overview():
    assert discovery.finite_number(0) == 0
    result = market_overview_data._snapshots(pd.DataFrame({"AAPL": [100]}))
    assert result["AAPL"]["price"] == 100
    assert result["AAPL"]["percent"] is None
    result = market_overview_data._snapshots(pd.DataFrame({"AAPL": [100, 100], "BAD": [float("inf"), float("nan")]}))
    assert result["AAPL"]["percent"] == 0
    assert "BAD" not in result


def test_yahoo_quote_date_matches_last_finite_observation(monkeypatch):
    prices = pd.DataFrame({("Close", "^GSPC"): [100, float("inf")]}, index=pd.date_range("2026-10-08", periods=2))
    monkeypatch.setattr(market_overview_data.yf, "download", lambda **kwargs: prices)
    result = market_overview_data.load_market_overview.__wrapped__("")
    quote = result["indexes"]["S&P 500"]
    assert quote["price"] == 100 and quote["percent"] is None
    assert quote["as_of"].startswith("2026-10-08")


def test_malformed_overview_row_does_not_erase_valid_quote(monkeypatch):
    monkeypatch.setattr(market_overview_data, "get_fmp_json", lambda *args, **kwargs: [None, {"symbol": "^GSPC", "price": 100, "changesPercentage": 0}])
    monkeypatch.setattr(market_overview_data.yf, "download", lambda **kwargs: pd.DataFrame())
    result = market_overview_data._load_fmp_market_overview("test")
    assert result["indexes"]["S&P 500"]["price"] == 100
    assert result["indexes"]["S&P 500"]["percent"] == 0


def test_collection_period_coverage_without_quote_requirement(monkeypatch):
    calls = []
    def get(url, key, **params):
        calls.append(url)
        if "stock-screener" in url:
            return [{"symbol": " aapl ", "sector": "Technology"}, {"symbol": "AAPL"},
                    {"symbol": None}, {"symbol": "BAD/KEY"}, {"symbol": "MSFT", "sector": "Technology"}]
        return [{"symbol": "AAPL", "1D": 0, "5D": None, "1M": 5},
                {"symbol": "MSFT", "1D": True, "5D": float("inf"), "1M": -1}]
    monkeypatch.setattr(discovery, "_get", get)
    data = discovery.collect_discovery.__wrapped__("test")
    assert data["requested_universe_size"] == 2
    assert data["period_coverage"] == {"1D": 1, "5D": 0, "1M": 2, "ytd": 0}
    assert data["coverage_pct"] == 0 and data["partial"]
    assert all("quote" not in url for url in calls)
    frame, stats = rank_discovery(data["universe"], "1M")
    assert frame["symbol"].tolist() == ["AAPL", "MSFT"]
    assert stats == {"usable": 2, "advancing": 50.0, "median": 2.0}


def test_rank_filter_before_limit_and_period_alignment():
    universe = pd.DataFrame([{"symbol": "AAPL", "sector": "Technology", "5D": 0, "1D": 8},
                             {"symbol": "MSFT", "sector": "Technology", "5D": -2, "1D": None},
                             {"symbol": "XOM", "sector": "Energy", "5D": 10, "1D": -1}])
    frame, stats = rank_discovery(universe, "5D", "Technology", "Laggards", 1)
    assert frame.iloc[0]["symbol"] == "MSFT"
    assert stats["usable"] == 2 and stats["median"] == -1 and stats["advancing"] == 0
    sectors = sector_summary(universe, "1D")
    assert sectors["stocks"].sum() == 2
    empty, stats = rank_discovery(universe, "1M")
    assert empty.empty and stats["median"] is None
    with pytest.raises(ValueError):
        rank_discovery(universe, "3M")


def test_discovery_handoff_draft_and_restoration_are_metadata_only():
    state = {}
    queue_discovery(state, "Financials")
    incoming = apply_discovery(state)
    assert incoming.sector == "Financial Services"
    assert state["movers_sector_filter"] == "Financial Services"
    discovery_state = DiscoveryState("Financial Services", "1M", "Laggards", "jpm")
    queue_discovery_research(state, discovery_state)
    apply_pending_handoff(state)
    assert "JPM" in state["research_request_draft"] and "1M" in state["research_request_draft"]
    assert "financials" in state["research_request_draft"]
    assert state["discovery_state"] == discovery_state
    assert state["research_context"].saved_reference is None
    other = {}
    assert apply_discovery(other) is None and not other


def test_stale_discovery_request_cannot_override_other_ticker():
    state = {}
    queue_discovery_research(state, DiscoveryState(selected_ticker="AAPL"))
    queue_handoff(state, ResearchContext(("MSFT",), "Research", "analyze", "Introduction"))
    apply_pending_handoff(state)
    assert state["research_request_draft"].startswith("Analyze MSFT")
    assert "pending_discovery_request" not in state


def test_saved_interpretation_exact_evidence_and_model_identity():
    snapshot = {"symbol": "AAPL", "quote": {"price": 100}, "fetched_at": "2026-10-09"}
    saved = save_interpretation(snapshot, "test-model", "Prior valid interpretation")
    assert interpretation_matches(saved, snapshot, "test-model")
    assert not interpretation_matches(saved, snapshot, "new-model")
    assert not interpretation_matches(saved, {**snapshot, "quote": {"price": 101}}, "test-model")
    assert not interpretation_matches(saved, {**snapshot, "symbol": "MSFT"}, "test-model")
    assert saved["text"] == "Prior valid interpretation"


def test_selected_news_retains_relative_publication_and_retrieval(monkeypatch):
    class Client:
        def __init__(self, key): pass
        def search(self, query, **kwargs):
            return {"ok": True, "retrieved_at": "2026-10-09T20:00:00Z", "results": [{"title": "Update", "published": "2 days ago", "url": "https://example.com/news"}]}
    monkeypatch.setattr(discovery, "SerperClient", Client)
    result = discovery.load_selected_news.__wrapped__(" aapl ", "test")
    assert result["symbol"] == "AAPL"
    assert result["retrieved_at"] == "2026-10-09T20:00:00Z"
    assert result["results"][0]["published"] == "2 days ago"
    with pytest.raises(ValueError):
        discovery.load_selected_news.__wrapped__("bad/ticker", "test")


def test_selected_quote_identity_missing_currency_and_zero(monkeypatch):
    monkeypatch.setattr(discovery, "_get", lambda *args: [{"symbol": "AAPL", "price": 0, "timestamp": 1791576000}])
    result = discovery.load_selected_quote.__wrapped__("aapl", "test")
    assert result["price"] == 0 and result["currency"] == "Unknown currency"
    assert result["as_of"] and result["retrieved_at"]
    monkeypatch.setattr(discovery, "_get", lambda *args: [{"symbol": "MSFT", "price": 10}])
    assert discovery.load_selected_quote.__wrapped__("AAPL", "test")["error"]


def test_market_generation_failure_preserves_previous(market_dashboard_stub, monkeypatch):
    ui, packet, _ = market_dashboard_stub
    from langgraphagenticai.analysis.market_brief_ai import evidence_identity
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab(openai_api_key='fake')")
    app.session_state["market_ai_summary"] = {"text": "Prior interpretation", "identity": "older", "model": "gpt-5"}
    app.run(timeout=30)
    app.button(key="intro_refresh").click().run()
    app.button(key="market_summary_generate").click().run()
    assert not app.exception
    assert app.session_state["market_ai_summary"]["text"] == "Prior interpretation"
    assert any("preserved" in item.value for item in app.warning)



def test_return_from_research_restores_filters_selection_and_failed_news(monkeypatch):
    from langgraphagenticai.ui import top_movers_tab
    from langgraphagenticai.providers import symbol_history
    frame = pd.DataFrame([{"symbol": "AAPL", "companyName": "Apple", "sector": "Technology", "1M": 2},
                          {"symbol": "MSFT", "companyName": "Microsoft", "sector": "Technology", "1M": 0}])
    monkeypatch.setattr(top_movers_tab, "load_top_movers", lambda *args: {"universe": frame})
    requests = []
    def news(symbol, key):
        requests.append(symbol)
        return {"symbol": symbol, "results": [], "error": "Synthetic news unavailable"}
    monkeypatch.setattr(discovery, "load_selected_news", news)
    monkeypatch.setattr(discovery, "load_selected_quote", lambda *args: {"error": "Quote unavailable"})
    monkeypatch.setattr(symbol_history, "load_symbol_history", lambda *args: {"points": []})
    app = AppTest.from_string("from langgraphagenticai.ui.top_movers_tab import render_top_movers_tab\nrender_top_movers_tab(fmp_api_key='test',serper_api_key='test')")
    app.session_state["discovery_state"] = DiscoveryState("Technology", "1M", "Laggards", "MSFT")
    app.run(timeout=30)
    assert not app.exception
    assert app.selectbox(key="movers_period").value == "1M"
    assert app.selectbox(key="movers_sector_filter").value == "Technology"
    assert app.selectbox(key="movers_focus").value == "MSFT"
    assert requests == ["MSFT"]
    assert app.dataframe[0].value.iloc[0]["Ticker"] == "MSFT"
    assert any("news unavailable" in item.value.lower() for item in app.info)
    app.selectbox(key="movers_period").set_value("5D").run()
    assert not app.exception and len(requests) == 1  # Empty period collects no unrelated enrichment.
    assert app.session_state["discovery_state"].period == "5D"
    assert app.session_state["discovery_state"].sector == "Technology"
    assert app.session_state["discovery_state"].selected_ticker == "MSFT"


def test_terminal_chart_style_preserves_price_and_layered_oscillator_evidence(monkeypatch):
    import altair as alt
    from langgraphagenticai.ui.opening_presentation import terminal_chart
    from langgraphagenticai.ui import technical_chart
    frame = pd.DataFrame({"Date": pd.date_range("2026-10-01", periods=2, tz="UTC"),
                          "Close": [100., 101.], "RSI": [40., 60.],
                          "MACD": [1., 2.], "MACD signal": [.5, 1.],
                          "MACD histogram": [.5, 1.]})
    original = technical_chart.price_chart_spec(frame, "5D", "Unknown currency").to_dict()
    styled = terminal_chart(technical_chart.price_chart_spec(frame, "5D", "Unknown currency")).to_dict()
    assert styled["encoding"] == original["encoding"]
    assert styled["datasets"] == original["datasets"]
    assert styled["config"]["background"] == "#121D2B"
    assert styled["config"]["axis"]["gridColor"] == "#283649"
    rendered = []
    monkeypatch.setattr(technical_chart.st, "altair_chart", lambda chart, **kwargs: rendered.append((chart.to_dict(), kwargs)))
    technical_chart.render_indicator_charts(frame, "5D", "Unknown currency", chart_style=terminal_chart)
    assert len(rendered) == 3
    assert all(spec["config"]["background"] == "#121D2B" and options["theme"] is None for spec, options in rendered)
    assert len(rendered[1][0]["layer"]) == 2 and len(rendered[2][0]["layer"]) == 2
    rendered.clear()
    technical_chart.render_indicator_charts(frame, "5D", "Unknown currency")
    assert all("theme" not in options for _, options in rendered)  # Other callers retain existing theme.
