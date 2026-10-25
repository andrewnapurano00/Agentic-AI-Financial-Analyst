"""Top Movers: identity/source schema binding and truthful saved-result recovery."""
from copy import deepcopy
from unittest.mock import Mock

import jsonschema
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.analysis import ticker_news_ai as ai
from langgraphagenticai.ui import ticker_news_summary as ui
from test_ticker_news_summary import news, result, mock_client


def test_ticker_schema_rejects_wrong_company_snapshot_and_both_citation_fields(monkeypatch):
    calls, builder = mock_client(monkeypatch)
    saved = ai.summarize_ticker_news(news("ZS"), "synthetic", "gpt-5")
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    jsonschema.validate(saved["result"], schema)
    for mutate in (lambda r: r.update(ticker="MSFT"), lambda r: r.update(fingerprint="wrong"),
                   lambda r: r.update(sentiment_evidence_ids=["N999"]),
                   lambda r: r["stories"][0].update(evidence_ids=["N999"])):
        altered = deepcopy(saved["result"]); mutate(altered)
        with pytest.raises(jsonschema.ValidationError): jsonschema.validate(altered, schema)
    assert len(calls) == 1
    builder.assert_called_once_with("synthetic", timeout=75, max_retries=0)
    assert calls[0]["max_completion_tokens"] == 6000


@pytest.mark.parametrize("edit,message", [
    (lambda r: {**r, "ticker": "MSFT"}, "selected stock"),
    (lambda r: {**r, "fingerprint": "wrong"}, "saved news snapshot"),
    (lambda r: {**r, "sentiment_evidence_ids": ["N999"]}, "source outside"),
    (lambda r: {**r, "stories": [{**r["stories"][0], "evidence_ids": ["N999"]}]}, "source outside"),
])
def test_noncompliant_output_is_still_rejected_in_one_attempt(monkeypatch, edit, message):
    calls, _ = mock_client(monkeypatch, edit=edit)
    with pytest.raises(ValueError, match=message): ai.summarize_ticker_news(news("ZS"), "synthetic", "gpt-5")
    assert len(calls) == 1


def test_selection_and_schema_are_isolated_without_mutating_base_contract(monkeypatch):
    calls, _ = mock_client(monkeypatch)
    first = ai.summarize_ticker_news(news("ZS"), "synthetic", "gpt-5")
    second = ai.summarize_ticker_news(news("MSFT"), "synthetic", "gpt-5")
    schema = calls[1]["response_format"]["json_schema"]["schema"]
    jsonschema.validate(second["result"], schema)
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate(first["result"], schema)
    assert "enum" not in ai.TickerNewsSummary.model_json_schema()["properties"]["ticker"]
    assert len(calls) == 2


@pytest.mark.parametrize("has_saved", [False, True])
def test_rejected_company_generation_preserves_only_existing_summary_and_never_reloads_news(monkeypatch, has_saved):
    source = news("ZS")
    packet = ai.ticker_evidence(source)
    saved = dict(result=result(packet), evidence=packet, model="gpt-5", generated_at="2026-10-24T12:00:00Z")
    provider = Mock(return_value=source)
    generate = Mock(return_value=saved)
    monkeypatch.setattr(ui, "load_ticker_news", provider)
    monkeypatch.setattr(ui, "summarize_ticker_news", generate)
    app = AppTest.from_string('''
from langgraphagenticai.ui.ticker_news_summary import render_ticker_news_summary
render_ticker_news_summary("ZS", "Zscaler", fmp_api_key="synthetic", openai_api_key="synthetic")
''', default_timeout=30).run()
    provider.assert_not_called(); generate.assert_not_called()
    app.button(key="movers_news_load").click().run()
    if has_saved:
        app.button(key="movers_news_generate").click().run()
    before = deepcopy(app.session_state["movers_news_summaries"] if "movers_news_summaries" in app.session_state else {})
    generate.side_effect = ValueError("Company briefing did not match the selected stock. Generate again using its saved news.")
    app.button(key="movers_news_generate").click().run()
    assert not app.exception and provider.call_count == 1 and generate.call_count == (2 if has_saved else 1)
    assert (app.session_state["movers_news_summaries"] if "movers_news_summaries" in app.session_state else {}) == before
    notices = " ".join(w.value for w in app.warning)
    assert "selected stock" in notices
    assert ("previous summary preserved" in notices) == has_saved
    app.run()
    assert provider.call_count == 1 and generate.call_count == (2 if has_saved else 1)
