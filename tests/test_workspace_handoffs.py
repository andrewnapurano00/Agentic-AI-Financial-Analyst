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
def routing(monkeypatch, market_dashboard_stub):
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
    from langgraphagenticai.providers import discovery, symbol_history
    monkeypatch.setattr(discovery, "load_selected_quote", lambda *args: {"error": "Synthetic quote unavailable"})
    monkeypatch.setattr(discovery, "load_selected_news", lambda *args: {"results": [], "error": "Synthetic news unavailable"})
    monkeypatch.setattr(symbol_history, "load_symbol_history", lambda *args: {"points": []})
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


@pytest.mark.parametrize("selection", ["keyboard", "native-row"])
def test_selected_mover_snapshot_market_back_roundtrip(routing, monkeypatch, selection):
    from langgraphagenticai.ui import top_movers_tab, introduction_tab
    frame = pd.DataFrame([
        {"symbol": "NVDA", "companyName": "NVIDIA", "sector": "Technology", "5D": 6.8, "1M": 10},
        {"symbol": "AMD", "companyName": "AMD", "sector": "Technology", "5D": 5.4, "1M": 8},
    ])
    monkeypatch.setattr(top_movers_tab, "load_top_movers", lambda *args: {"universe": frame})
    monkeypatch.setattr(introduction_tab, "load_market_overview", lambda *args: {"indexes": {"S&P 500": {"price": 100}}, "sectors": {}, "movers": [], "cross_assets": {}})
    monkeypatch.setattr(introduction_tab, "_render_market_chart", lambda *args: None)
    app = app_at("Top Movers")
    app.selectbox(key="movers_sector_filter").set_value("Technology").run()
    app.selectbox(key="movers_period").set_value("1M").run()
    if selection == "native-row":
        # Streamlit1.61 AppTest exposes grid protobufs but no public row selector.
        # Send the same JSON selection state as the native dataframe client.
        states = app._tree.get_widget_states()
        selected = states.widgets.add()
        selected.id = app.dataframe[0].proto.id
        selected.string_value = '{"selection":{"rows":[1],"columns":[],"cells":[]}}'
        app._run(states)
    else:
        app.selectbox(key="movers_focus").set_value("AMD").run()
    assert app.session_state["discovery_state"].selected_ticker == "AMD"
    app.button(key="movers_open_snapshot").click().run()
    assert not app.exception
    assert app.session_state["intro_company_symbol"] == "AMD"
    app.button(key="intro_refresh").click().run()
    assert app.text_input[1].value == "AMD"
    assert not app.exception
    assert app.session_state["discovery_state"].selected_ticker == "AMD"
    app.radio(key="active_workspace").set_value("Top Movers").run()
    assert not app.exception
    assert app.selectbox(key="movers_focus").value == "AMD"
    assert app.selectbox(key="movers_sector_filter").value == "Technology"
    assert app.selectbox(key="movers_period").value == "1M"
    assert routing["model"] == 0


@pytest.mark.parametrize("origin,key", [("Top Movers", "movers_handoff")])
@pytest.mark.parametrize("destination,input_key", [("Research", "research_request_draft"), ("Equity Report", "equity_report_ticker_input"), ("Deep Research", "dr_tickers")])
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
    app.button(key="intro_refresh").click().run()
    assert app.text_input[1].value == "AAPL"
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


def test_research_saved_findings_precede_editable_draft_without_model_call(routing):
    app = app_at("Research")

    def rendered_nodes(node):
        yield node
        for child in getattr(node, "children", {}).values():
            yield from rendered_nodes(child)

    nodes = list(rendered_nodes(app._tree))
    findings_at = next(i for i, node in enumerate(nodes) if "Saved AI findings" in str(getattr(node, "value", "")))
    draft_at = next(i for i, node in enumerate(nodes) if getattr(node, "label", "") == "Research request draft")
    assert findings_at < draft_at
    assert app.session_state["chat_history"][-1]["content"] == "Saved conversation"
    assert routing["model"] == 0


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
    assert not any(b.label.startswith(("Finalize","Retry")) for b in app.button)
    assert next(b for b in app.button if b.label == "Start deep research").disabled
    app.sidebar.radio[0].set_value("Research").run()
    app.sidebar.radio[0].set_value("Deep Research").run()
    assert not app.exception
    assert app.session_state["dr_history"][0]["delivery_audit"]["report"] == sample_result()["report"]
    assert app.session_state["dr_history"][0]["status"]=="complete"
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
    next(b for b in app.button if b.label == "Run V2 pilot").click().run()
    assert not app.exception
    assert seen == [["AAPL", "MSFT"]]
    assert any("Offline alternate-provider preflight reached" in e.value for e in app.error)
    assert routing["model"] == 0


def test_empty_ranking_recovery_remount_default_matches_selected_evidence(routing, monkeypatch):
    from langgraphagenticai.ui import top_movers_tab
    complete = pd.DataFrame([
        {"symbol": "NVDA", "companyName": "NVIDIA", "sector": "Technology", "5D": 6.8, "1M": 10},
        {"symbol": "AMD", "companyName": "AMD", "sector": "Technology", "5D": 5.4, "1M": 8},
    ])
    evidence = {"frame": complete}
    monkeypatch.setattr(top_movers_tab, "load_top_movers", lambda *args: {"universe": evidence["frame"]})
    app = app_at("Top Movers")
    app.selectbox(key="movers_period").set_value("1M").run()
    app.selectbox(key="movers_focus").set_value("AMD").run()
    evidence["frame"] = complete.assign(**{"1M": float("nan")})
    app.run()
    assert not app.exception and not any(box.key == "movers_focus" for box in app.selectbox)
    app.radio(key="active_workspace").set_value("Research").run()
    app.radio(key="active_workspace").set_value("Top Movers").run()
    assert app.session_state["discovery_state"].selected_ticker == "AMD"
    evidence["frame"] = complete
    app.run()
    selector = app.selectbox(key="movers_focus")
    assert not app.exception and selector.value == "AMD"
    # AppTest's backend value alone missed the browser remount bug: the browser
    # initializes the reappearing control using this serialized default index.
    assert selector.options[selector.proto.default] == "AMD"
    period_selector = app.selectbox(key="movers_period")
    assert period_selector.options[period_selector.proto.default] == "1M"
    assert app.session_state["discovery_state"].selected_ticker == "AMD"
    assert any('<h2>AMD <span>AMD</span>' in item.value for item in app.markdown)
    assert routing["model"] == 0
