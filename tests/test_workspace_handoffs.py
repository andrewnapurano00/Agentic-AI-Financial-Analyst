"""P01/D01-D05: offline navigation, explicit paid actions and session isolation."""
from datetime import datetime, timezone
from dataclasses import asdict
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.state.research_context import ResearchContext, SavedEvidenceReference
from langgraphagenticai.ui.workspace_handoff import queue_handoff, apply_pending_handoff


@pytest.mark.parametrize("symbol", ["", "../AAPL", "AAPL,MSFT", "AAPL?apikey=secret", "^GSPC", None])
def test_invalid_identity_has_no_state_mutation(symbol):
    state = {"chat_history": ["saved"]}
    with pytest.raises(ValueError):
        queue_handoff(state, ResearchContext((symbol,), "Research", "analyze", "Introduction"))
    assert state == {"chat_history": ["saved"]}


def test_metadata_only_contract_and_one_shot_adapter():
    reference = SavedEvidenceReference("saved-report-1", "FMP", "2026-01-02T00:00:00Z")
    context = ResearchContext((" brk-b ", "aapl", "AAPL"), "Deep Research V2", "compare", "Research", reference)
    assert context.symbols == ("BRK-B", "AAPL")
    assert asdict(context)["saved_reference"]["as_of"] == "2026-01-02T00:00:00Z"
    state = {"dr_history": ["saved"], "chat_history": ["saved chat"]}
    queue_handoff(state, context)
    assert apply_pending_handoff(state) == context
    assert state["drv2_tickers"] == "BRK-B, AAPL"
    assert apply_pending_handoff(state) is None
    assert state["dr_history"] == ["saved"] and state["chat_history"] == ["saved chat"]
    assert "financial_context" not in state
    with pytest.raises(ValueError):
        ResearchContext(("AAPL",), "Research", "analyze", "Introduction", {"api_key": "secret"})
    with pytest.raises(ValueError):
        SavedEvidenceReference("https://example.com/?api_key=secret")
    with pytest.raises(ValueError):
        SavedEvidenceReference("saved-1", "sk-abcdefghijklmnop")


@pytest.mark.parametrize("destination,symbols,intent", [("Portfolio Lab", ("AAPL",), "analyze"), ("Introduction", ("AAPL", "MSFT"), "compare"), ("Research", ("AAPL",), "compare"), ("Deep Research", tuple("ABCDE"), "analyze")])
def test_destination_cardinality_and_intent(destination, symbols, intent):
    with pytest.raises(ValueError):
        ResearchContext(symbols, destination, intent, "Introduction")


HARNESS = "from langgraphagenticai.main import load_langgraph_agenticai_app; load_langgraph_agenticai_app()"


@pytest.fixture
def routing(monkeypatch):
    from langgraphagenticai import main
    from langgraphagenticai.ui.streamlitui import loadui
    from langgraphagenticai.ui import introduction_tab, top_movers_tab, stock_screener_tab
    calls = {"model": 0, "screen": 0}
    def forbidden(*a, **k):
        calls["model"] += 1
        raise AssertionError("Navigation must not invoke models")
    monkeypatch.setattr(loadui, "_resolve_secret", lambda value, key, env: "test" if key == "FMP_API_KEY" else "")
    monkeypatch.setattr(main, "_build_cached_graph", forbidden)
    monkeypatch.setattr(main, "_build_repair_llm", forbidden)
    monkeypatch.setattr(introduction_tab, "load_company_snapshot", lambda symbol, *a: {"symbol": symbol})
    monkeypatch.setattr(introduction_tab, "_render_company_snapshot", lambda *a: None)
    monkeypatch.setattr(introduction_tab, "generate_company_summary", forbidden)
    frame = pd.DataFrame([{"symbol": "AAPL", "companyName": "Apple", "sector": "Technology", "price": 180, "5D": 2., "1D": 1., "marketCap": 3e12, "liquidityRatio": 1.2}])
    monkeypatch.setattr(top_movers_tab, "load_top_movers", lambda *a: {"universe": frame, "gainers": frame, "losers": frame, "sectors": pd.DataFrame(), "news": {}, "providers": ["Synthetic"], "universe_size": 1, "fetched_at": datetime(2026, 10, 2, tzinfo=timezone.utc)})
    monkeypatch.setattr(top_movers_tab, "_sector_heatmap", lambda frame: "")
    def screen(**kwargs):
        calls["screen"] += 1
        return pd.DataFrame([{"ticker": "AAPL", "marketCap": 3e12}]), {"pages": 1}
    monkeypatch.setattr(stock_screener_tab, "fmp_company_screener_safe", screen)
    monkeypatch.setattr(stock_screener_tab, "fetch_all_metrics", lambda *a, **k: pd.DataFrame([{"Ticker": "AAPL", "Market Cap": 3e12}]))
    return calls


def app_at(workspace):
    app = AppTest.from_string(HARNESS, default_timeout=30)
    app.session_state["active_workspace"] = workspace
    app.session_state["intro_company_symbol"] = "AAPL"
    app.session_state["chat_history"] = [{"role": "assistant", "content": "Saved conversation"}]
    app.session_state["thread_id"] = "saved-thread"
    app.run()
    assert not app.exception
    return app


@pytest.mark.parametrize("origin,key", [("Introduction", "intro_handoff"), ("Top Movers", "movers_handoff")])
@pytest.mark.parametrize("destination,input_key", [("Research", "research_request_draft"), ("Equity Report", "equity_report_ticker_input"), ("Deep Research", "dr_tickers"), ("Deep Research V2", "drv2_tickers")])
def test_discovery_actual_routes_prefill_without_execution(routing, origin, key, destination, input_key):
    app = app_at(origin)
    app.button(key=f"{key}_{destination}").click().run()
    assert not app.exception
    assert app.session_state["active_workspace"] == destination
    assert not any("default value" in warning.value and "Session State" in warning.value for warning in app.warning)
    assert "AAPL" in app.session_state[input_key]
    assert app.session_state["thread_id"] == "saved-thread"
    assert app.session_state["chat_history"][0]["content"] == "Saved conversation"
    if destination.startswith("Deep Research"):
        assert next(c for c in app.checkbox if c.label == ("Use saved app data" if destination == "Deep Research V2" else "Include saved data from other tabs")).disabled
    app.sidebar.radio[0].set_value(origin).run()
    assert not app.exception
    assert app.session_state["chat_history"][0]["content"] == "Saved conversation"
    assert routing["model"] == 0


def test_screener_saved_return_without_recollection(routing):
    app = app_at("Stock Screener")
    next(b for b in app.button if b.label == "Run Screener").click().run()
    assert not app.exception and routing["screen"] == 1
    app.button(key="screener_open_intro").click().run()
    assert app.text_input(key="intro_company_search").value == "AAPL"
    assert not any("default value" in warning.value and "Session State" in warning.value for warning in app.warning)
    app.sidebar.radio[0].set_value("Stock Screener").run()
    assert not app.exception
    assert app.dataframe and routing["screen"] == 1 and routing["model"] == 0


def test_research_drafts_command_and_explicit_submit(monkeypatch, routing):
    from langgraphagenticai import main
    from langgraphagenticai.ui.streamlitui import loadui
    from langchain_core.messages import AIMessage
    monkeypatch.setattr(loadui, "_resolve_secret", lambda *a: "test")
    class Graph:
        def invoke(self, *a, **k):
            routing["model"] += 1
            return {"messages": [AIMessage(content="Explicit answer")]}
    monkeypatch.setattr(main, "_build_cached_graph", lambda **k: Graph())
    monkeypatch.setattr(main, "_build_repair_llm", lambda **k: None)
    app = app_at("Research")
    app.session_state["pending_research_query"] = "Analyze AAPL"
    app.run()
    assert app.text_area(key="research_request_draft").value == "Analyze AAPL"
    app.text_area(key="research_request_draft").set_value("Analyze MSFT").run()
    app.run()
    assert routing["model"] == 0
    app.button(key="research_submit").click().run()
    assert not app.exception and routing["model"] == 1
    app.run()
    assert routing["model"] == 1
    other = app_at("Research")
    assert other.session_state["thread_id"] == "saved-thread"
    assert len(other.session_state["chat_history"]) == 1


def test_chat_configuration_changes_preserve_until_new_thread(routing):
    app = app_at("Research")
    old = app.sidebar.selectbox[0].value
    alternative = next(x for x in app.sidebar.selectbox[0].options if x != old)
    app.sidebar.radio[0].set_value("Stock Screener").run()
    app.sidebar.selectbox[0].set_value(alternative).run()
    assert app.session_state["thread_id"] == "saved-thread"
    app.sidebar.radio[0].set_value("Research").run()
    assert app.warning and app.session_state["chat_history"]
    app.button(key="research_new_thread").click().run()
    assert not app.exception and not app.session_state["chat_history"]
    assert not any("The model or use case changed" in warning.value for warning in app.warning)
    assert app.session_state["thread_id"] != "saved-thread"
    assert routing["model"] == 0


def test_missing_openai_optimizer_route_and_v2_alternative_preflight(routing):
    app = app_at("Portfolio Lab")
    assert any(b.label == "Run Portfolio Analysis" for b in app.button)
    assert next(b for b in app.button if b.label == "Run hybrid AI committee").disabled
    from langgraphagenticai.deep_research.v2_workflow import preflight
    preflight({"routes": {"report": {"provider": "ollama", "model": "offline"}}}, ["report"], openai_api_key="")
    assert routing["model"] == 0


def test_command_navigation_prepares_draft_without_submit(monkeypatch, routing):
    from langgraphagenticai import main
    pending = ["Analyze BRK-B"]
    monkeypatch.setattr(main, "render_command_bar", lambda: pending.pop() if pending else "")
    app = app_at("Stock Screener")
    assert app.session_state["active_workspace"] == "Research"
    assert app.text_area(key="research_request_draft").value == "Analyze BRK-B"
    assert routing["model"] == 0


def test_saved_v1_report_roundtrip_does_not_collect(monkeypatch, routing):
    from test_deep_research_ui import sample_result
    from langgraphagenticai.ui import deep_research_tab
    def forbidden(*a, **k):
        raise AssertionError("Opening saved reports must not collect or generate")
    monkeypatch.setattr(deep_research_tab, "_manager", forbidden)
    app = app_at("Research")
    saved = sample_result()
    saved["status"] = "needs_review"
    app.session_state["dr_history"] = [saved]
    app.sidebar.radio[0].set_value("Deep Research").run()
    assert not app.exception
    assert app.download_button
    assert not next(b for b in app.button if b.label == "Finalize report").disabled
    assert next(b for b in app.button if b.label == "Start deep research").disabled
    app.sidebar.radio[0].set_value("Research").run()
    app.sidebar.radio[0].set_value("Deep Research").run()
    assert not app.exception
    assert app.session_state["dr_history"][0]["report"] == sample_result()["report"]
    assert routing["model"] == 0


def test_v2_alternate_provider_explicit_stage_preflight(monkeypatch, routing):
    from langgraphagenticai.ui import deep_research_v2_tab
    from langgraphagenticai.deep_research.v2_workflow import preflight
    from langgraphagenticai.deep_research.v2 import V2ConfigurationError
    seen = []
    def stub_factory(**kwargs):
        assert kwargs["openai_api_key"] == ""
        routes = kwargs["config"]["routes"]
        stages = [stage for stage, route in routes.items() if route["provider"].lower() == "ollama"]
        assert stages
        preflight(kwargs["config"], stages, ollama_base_url=kwargs["ollama_base_url"])
        seen.append(kwargs["request"].symbols)
        raise V2ConfigurationError("Offline alternate-provider preflight reached")
    monkeypatch.setattr(deep_research_v2_tab, "_manager_v2", stub_factory)
    app = app_at("Deep Research V2")
    next(s for s in app.selectbox if s.label == "Light-stage provider").set_value("Ollama")
    next(c for c in app.checkbox if c.label == "Stop after evidence").set_value(True)
    next(b for b in app.button if b.label == "Run V2 pilot").click().run()
    assert not app.exception
    assert seen == [["AAPL", "MSFT"]]
    assert any("Offline alternate-provider preflight reached" in e.value for e in app.error)
    assert routing["model"] == 0
