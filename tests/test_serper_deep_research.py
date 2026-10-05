"""Offline Serper transport-to-saved-evidence and shared coverage contracts."""
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.deep_research.models import Evidence, ResearchRequest
from langgraphagenticai.deep_research import v2_workflow
from langgraphagenticai.deep_research.v2 import stage_configuration
from langgraphagenticai.tools.serper_tools import SerperClient
from langgraphagenticai.ui import deep_research_tab as v1

STAMP = "2026-10-04T12:34:56+00:00"
REPORT = "## Executive Investment Thesis\nAAPL in USD as of 2026-10-04 [E001].\n## Risks\nRisk.\n## Thesis invalidation\nCash flow weakens."


@pytest.fixture
def http(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"news": [
        {"title": "Earnings", "link": "https://example.com/earnings", "snippet": "Revenue rose",
         "date": "1 day ago", "source": "Example"},
        {"title": "Duplicate", "link": "https://example.com/earnings"},
        None, {"link": "javascript:alert(1)"}]}
    post = Mock(return_value=response)
    monkeypatch.setattr("langgraphagenticai.tools.serper_tools.requests.post", post)
    monkeypatch.setattr("langgraphagenticai.tools.serper_tools.utc_now", lambda: STAMP)
    return post, response


@pytest.mark.parametrize("news", [True, False])
@pytest.mark.parametrize("invalid", [42, {}, "bad", None])
def test_malformed_collection_is_structured_failure(http, news, invalid):
    post, response = http
    response.json.return_value = {"news" if news else "organic": invalid}
    result = SerperClient("synthetic").search("AAPL", news=news)
    assert not result["ok"] and result["results"] == []
    assert "invalid" in result["error"]


def manager_for(monkeypatch, mode, include_news=True):
    source = Mock()
    source.collect.side_effect = lambda request, progress: [record
        for symbol in request.symbols for record in (
            Evidence("", symbol, "profile", "Profile", "Synthetic",
                     [{"companyName": {"AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation"}[symbol]}]),
            Evidence("", symbol, "income", "Income", "Synthetic", [{"revenue": 5}]))]
    model = Mock()
    model.invoke.side_effect = lambda messages, **kwargs: SimpleNamespace(content="{}")
    request = ResearchRequest(["AAPL", "MSFT"], include_news=include_news, news_days=7)
    if mode == "v1":
        monkeypatch.setattr(v1, "OpenAILLM", lambda _: SimpleNamespace(get_llm_model=lambda: model))
        monkeypatch.setattr(v1, "FinancialDataSource", lambda _: source)
        monkeypatch.setattr(v1, "get_finance_tools", lambda *args: [])
        manager = v1._manager("synthetic", "test", "synthetic", "serper-synthetic", "")
        manager.stop_after_evidence = True
    else:
        monkeypatch.setattr(v2_workflow, "QuarterlyFinancialDataSource", lambda _: source)
        monkeypatch.setattr(v2_workflow, "get_v2_finance_tools", lambda *args: [])
        monkeypatch.setattr(v2_workflow, "build_stage_llm", lambda *args, **kwargs: model)
        manager = v2_workflow.build_manager(
            request=request, config=stage_configuration("Economy", light_provider="OpenAI"), openai_api_key="synthetic",
            groq_api_key="", fmp_api_key="synthetic", serper_api_key="serper-synthetic",
            marketaux_api_key="", ollama_base_url="http://localhost:11434/v1", budget=.35,
            stop_after_evidence=True)
    return manager, request, source


@pytest.mark.parametrize("mode", ["v1", "v2"])
def test_factory_news_transport_and_saved_sources(monkeypatch, http, mode):
    manager, request, source = manager_for(monkeypatch, mode)
    result = manager.run(request)
    post, _ = http
    assert post.call_count == 2
    assert {call.kwargs["json"]["q"] for call in post.call_args_list} == {"Apple Inc. AAPL", "Microsoft Corporation MSFT"}
    for call in post.call_args_list:
        assert call.args == ("https://google.serper.dev/news",)
        assert call.kwargs["headers"]["X-API-KEY"] == "serper-synthetic"
        assert call.kwargs["json"]["tbs"] == "qdr:d7"
        assert call.kwargs["json"]["num"] == 5
        assert call.kwargs["timeout"] == (5, 25)
    records = [item for item in result["evidence"] if item["category"] == "news"]
    assert {item["symbol"] for item in records} == {"AAPL", "MSFT"}
    for item in records:
        assert item["retrieved_at"] == STAMP and item["provider"] == "Serper"
        assert item["url"] == "https://example.com/earnings"
        assert item["data"] == [{"title": "Earnings", "url": item["url"], "snippet": "Revenue rose",
                                  "published": "1 day ago", "publisher": "Example"}]
    assert len([item for item in result["evidence"] if item["category"] == "income"]) == 2
    # Real resume executes orchestration using the saved evidence; only synthesis is mocked.
    monkeypatch.setattr(manager, "write_report", lambda *args, **kwargs: REPORT)
    resumed = manager.resume(result)
    assert resumed["report"] == REPORT
    assert post.call_count == 2 and source.collect.call_count == 1


@pytest.mark.parametrize("mode", ["v1", "v2"])
def test_disabled_news_never_requests_serper(monkeypatch, http, mode):
    manager, request, _ = manager_for(monkeypatch, mode, include_news=False)
    result = manager.run(request)
    http[0].assert_not_called()
    assert not any(item["provider"] == "Serper" for item in result["evidence"])


@pytest.mark.parametrize("mode", ["v1", "v2"])
def test_malformed_news_preserves_financial_evidence(monkeypatch, http, mode):
    http[1].json.return_value = {"news": 42}
    manager, request, _ = manager_for(monkeypatch, mode)
    result = manager.run(request)
    assert result["status"] == "evidence_ready"
    assert len([e for e in result["evidence"] if e["category"] == "income"]) == 2
    assert all(e["status"] == "missing" for e in result["evidence"] if e["category"] == "news")
    assert len(result["gaps"]) == 2


@pytest.mark.parametrize("kind", ["full", "partial", "empty", "disabled", "legacy", "malformed_rows"])
def test_shared_saved_news_coverage(kind):
    request = asdict(ResearchRequest(["AAPL", "MSFT"], include_news=kind != "disabled"))
    records = [] if kind == "empty" else [Evidence("E1", "AAPL", "news", "News", "Serper",
        [{"title": "Earnings", "url": "https://example.com/news"}], retrieved_at=STAMP).to_dict()]
    if kind == "full":
        records.append({**records[0], "symbol": "MSFT", "id": "E2"})
    if kind == "malformed_rows":
        records[0]["data"] = [None, {}, {"title": "No source"}]
    if kind == "legacy":
        records[0]["retrieved_at"] = None
    app = AppTest.from_string("""
import streamlit as st
from langgraphagenticai.ui.research_news import render_serper_news_coverage
render_serper_news_coverage(st.session_state['saved'])
""", default_timeout=30)
    app.session_state["saved"] = {"request": request, "evidence": records}
    app.run()
    assert not app.exception
    captions = " ".join(item.value for item in app.caption)
    if kind == "disabled":
        assert not captions and not app.warning
    else:
        assert "30-day requested lookback" in captions
        assert "Saved reuse does not refresh news" in captions
        assert ("2026-10-04 12:34:56 UTC" if kind not in {"empty", "legacy", "malformed_rows"} else "unavailable") in captions
        assert bool(app.warning) == (kind != "full")


def test_web_search_transport_and_missing_key(http):
    post, response = http
    SerperClient("").search("AAPL")
    post.assert_not_called()
    response.json.return_value = {"organic": [{"title": "Source", "link": "https://example.com/web"}]}
    result = SerperClient("synthetic").search("AAPL", news=False, days=7)
    assert result["ok"] and result["retrieved_at"] == STAMP
    assert post.call_args.args == ("https://google.serper.dev/search",)
    assert "tbs" not in post.call_args.kwargs["json"]


@pytest.mark.parametrize("mode", ["v1", "v2"])
def test_partial_provider_failure_preserves_other_news(monkeypatch, http, mode):
    post, successful = http
    failed = Mock(status_code=429)
    post.side_effect = lambda url, **kwargs: failed if kwargs["json"]["q"].endswith("MSFT") else successful
    manager, request, _ = manager_for(monkeypatch, mode)
    result = manager.run(request)
    news = {item["symbol"]: item for item in result["evidence"] if item["category"] == "news"}
    assert news["AAPL"]["status"] == "ok" and news["AAPL"]["data"]
    assert news["MSFT"]["status"] == "missing" and "429" in news["MSFT"]["note"]
    assert len([item for item in result["evidence"] if item["category"] == "income"]) == 2


@pytest.mark.parametrize("news", [True, False])
@pytest.mark.parametrize("kind", ["missing", "empty", "unsafe"])
def test_response_diagnostics_distinguish_missing_empty_and_discarded(http, news, kind):
    _, response = http
    collection = "news" if news else "organic"
    response.json.return_value = ({"unexpected": []} if kind == "missing" else
        {collection: []} if kind == "empty" else
        {collection: [None, {"link": "javascript:alert(1)"}, {"title": "No URL"}]})
    result = SerperClient("synthetic").search("AAPL", news=news)
    assert not result["ok"] and result["results"] == []
    assert result["error"] == ({
        "missing": f"Serper response is missing the expected {collection} result collection.",
        "empty": "No matching search results returned.",
        "unsafe": "Serper returned results, but none had usable safe source links."}[kind])
    assert "javascript" not in result["error"]


@pytest.mark.parametrize("mode", ["v1", "v2"])
def test_news_query_without_profile_uses_symbol_only(monkeypatch, http, mode):
    manager, request, source = manager_for(monkeypatch, mode)
    source.collect.side_effect = lambda request, progress: [
        Evidence("", symbol, "income", "Income", "Synthetic", [{"revenue": 5}])
        for symbol in request.symbols]
    manager.run(request)
    assert {call.kwargs["json"]["q"] for call in http[0].call_args_list} == {"AAPL", "MSFT"}
