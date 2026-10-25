"""Request-bound citations prevent transcription errors without bypassing checks."""
from copy import deepcopy
import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import jsonschema
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.analysis import market_news_ai as ai
from langgraphagenticai.ui import market_news_summary as ui
from test_market_updates import sample_news, summary_response


def stub(monkeypatch, mutate=None):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        packet = json.loads(kwargs["messages"][-1]["content"])
        result = summary_response(packet)
        ids = [a["id"] for a in packet["articles"]]
        result["sentiment_evidence_ids"] = ids[:2]
        result["claims"][0]["evidence_ids"] = ids[:3]
        if mutate:
            mutate(result)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(result), refusal=None))])
    builder = Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(ai, "build_openai_client", builder)
    return calls, builder


def test_generated_schema_accepts_only_this_snapshot_and_article_ids(monkeypatch):
    calls, builder = stub(monkeypatch)
    saved = ai.summarize_news(sample_news(), "synthetic", "gpt-5")
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    jsonschema.validate(saved["result"], schema)
    for mutation in (lambda r: r.update(fingerprint="wrong"),
                     lambda r: r.update(sentiment_evidence_ids=["N999"]),
                     lambda r: r["claims"][0].update(evidence_ids=["N999"])):
        altered = deepcopy(saved["result"])
        mutation(altered)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(altered, schema)
    assert len(calls) == 1
    assert builder.call_args.kwargs == {"timeout": 75, "max_retries": 0}
    assert calls[0]["max_completion_tokens"] == 6000


@pytest.mark.parametrize("field,expected", [("fingerprint", "snapshot"), ("sentiment", "source outside"), ("claim", "source outside")])
def test_independent_validation_still_rejects_noncompliant_model_once(monkeypatch, field, expected):
    def corrupt(result):
        if field == "fingerprint": result["fingerprint"] = "wrong"
        elif field == "sentiment": result["sentiment_evidence_ids"] = ["N999"]
        else: result["claims"][0]["evidence_ids"] = ["N999"]
    calls, _ = stub(monkeypatch, corrupt)
    with pytest.raises(ValueError, match=expected):
        ai.summarize_news(sample_news(), "synthetic", "gpt-5")
    assert len(calls) == 1


def test_request_constraints_do_not_leak_to_another_packet(monkeypatch):
    calls, _ = stub(monkeypatch)
    first = ai.summarize_news(sample_news(), "synthetic", "gpt-5")
    reduced = sample_news(); reduced["articles"] = reduced["articles"][:1]
    second = ai.summarize_news(reduced, "synthetic", "gpt-5")
    schema = calls[1]["response_format"]["json_schema"]["schema"]
    jsonschema.validate(second["result"], schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(first["result"], schema)
    assert "enum" not in ai.NewsSummary.model_json_schema()["properties"]["fingerprint"]
    assert len(calls) == 2


@pytest.mark.parametrize("has_saved", [False, True])
def test_failure_notice_preserves_real_saved_state_without_claiming_missing_summary(monkeypatch, has_saved):
    news = sample_news()
    evidence = ai.news_evidence(news)
    saved = {"result": summary_response(evidence), "evidence": evidence, "model": "gpt-5"}
    monkeypatch.setitem(sys.modules, "news_source_fixture", SimpleNamespace(news=news))
    generate = Mock(side_effect=ValueError("News briefing did not match the saved news snapshot. Generate again using the saved articles."))
    monkeypatch.setattr(ui, "summarize_news", generate)
    app = AppTest.from_string('''
from news_source_fixture import news
from langgraphagenticai.ui.market_news_summary import render_news_summary
render_news_summary(news, "synthetic")
''', default_timeout=30)
    if has_saved:
        app.session_state["market_news_summary"] = deepcopy(saved)
    app.run()
    generate.assert_not_called()
    app.button(key="market_news_summarize").click().run()
    assert not app.exception and generate.call_count == 1
    warning = " ".join(w.value for w in app.warning)
    assert ("Your saved briefing is unchanged" in warning) == has_saved
    if has_saved:
        assert app.session_state["market_news_summary"] == saved
    else:
        assert "market_news_summary" not in app.session_state
    app.run()
    assert generate.call_count == 1
