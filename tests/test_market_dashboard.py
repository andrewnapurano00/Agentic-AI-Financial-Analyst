"""Offline daily dashboard calculations, provider isolation and explicit AI actions."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis.market_dashboard import dashboard_metrics
from langgraphagenticai.providers.market_brief_news import merge_news


def history():
    dates = pd.bdate_range(end="2026-10-16", periods=260)
    return [{"date": d.date().isoformat(), "close": 100+i, "adj_close": 90+i} for i, d in enumerate(dates)]


def test_daily_returns_and_indicator_math():
    rows = history()
    result = dashboard_metrics(rows, "2026-10-16T22:00:00Z")
    assert result["day"] == pytest.approx((359/348-1)*100)
    assert result["week"] == pytest.approx((359/344-1)*100)
    assert result["30D"] == pytest.approx((359/319-1)*100)
    assert result["60D"] == pytest.approx((359/289-1)*100)
    assert result["RSI (14)"] == 100
    assert result["vs SMA 7 %"] == pytest.approx((359/346-1)*100)
    assert result["vs SMA 200 %"] == pytest.approx((359/249.5-1)*100)


def test_missing_adjclose_does_not_bridge_indicators_or_substitute_baseline():
    rows = history()
    rows[-2]["adj_close"] = None
    result = dashboard_metrics(rows, "2026-10-16T22:00Z")
    assert result["day"] is None
    assert result["vs SMA 7 %"] is None and result["RSI (14)"] is None
    assert result["week"] is not None
    assert dashboard_metrics([], "2026-10-16T22:00Z")["price"] is None


def test_news_dedup_preserves_providers_and_removes_sentiment():
    common = {"title": "Markets rise", "url": "https://example.com/a?utm_source=x", "sentiment": None, "providers": ["Serper"]}
    result = merge_news([common, {**common, "url": "https://example.com/a", "providers": ["Marketaux"], "sentiment": 0}])
    assert len(result) == 1 and result[0]["providers"] == ["Marketaux", "Serper"]
    assert "sentiment" not in result[0]
    distinct = merge_news([{**common, "url": "https://example.com/article?id=1"},
                           {**common, "title": "Other article", "url": "https://example.com/article?id=2"}])
    assert len(distinct) == 2


def test_crypto_midnight_quote_uses_explicit_utc_daily_policy():
    rows = [{"date": "2026-10-15", "close": 99, "adj_close": 99},
            {"date": "2026-10-16", "close": 100, "adj_close": 100}]
    result = dashboard_metrics(rows, "2026-10-17T00:30Z", {"price": 110, "as_of": "2026-10-17T00:15Z"}, quote_timezone="UTC")
    assert result["price_date"] == "2026-10-17" and result["day"] == pytest.approx(10)
    assert result["previous_adj_close"] == 100


def test_dashboard_controls_and_explicit_ai(monkeypatch):
    from langgraphagenticai.ui import market_dashboard as ui
    from langgraphagenticai.analysis.sector_heatmap import SECTORS
    record = dashboard_metrics(history(), "2026-10-16T22:00Z")
    packet = {"rows": [{"Instrument": "Technology", "Ticker": "XLK", "Group": "Sector", "Level": 359,
        "1D %": record["day"], "5D %": record["week"], "30D %": record["30D"], "60D %": record["60D"],
        "YTD %": record["ytd"], "RSI (14)": 100, "vs SMA 7 %": 1, "evidence": record}],
        "sectors": {name: record for name in SECTORS}, "warnings": [], "retrieved_at": "2026-10-16"}
    monkeypatch.setattr(ui, "load_dashboard", lambda *a: packet)
    monkeypatch.setattr(ui, "load_market_news", lambda *a: {"articles": [], "warnings": []})
    calls, charts = [], []
    monkeypatch.setattr(ui, "interpret_market", lambda *a: calls.append(a) or "Synthetic market summary")
    def chart(symbol, key, period):
        charts.append((symbol, period))
        points = list(zip(pd.bdate_range("2026-01-01", periods=220), range(100,320)))
        return {"symbol": symbol, "points": points, "calculation_points": points, "period": period, "interval": "1d"}
    monkeypatch.setattr(ui, "load_symbol_history", chart)
    app = AppTest.from_string('from langgraphagenticai.ui.market_dashboard import render_market_dashboard\nrender_market_dashboard("fake", "fake")', default_timeout=30).run(timeout=30)
    assert not app.exception and not calls
    app.button(key="intro_refresh").click().run()
    assert not app.radio
    assert not any("ANALYZE COMPANY" in b.label for b in app.button)
    app.button(key="market_summary_generate").click().run()
    assert not app.exception and len(calls) == 1
    app.run()
    assert len(calls) == 1
    app.text_input[1].set_value("MSFT")
    next(b for b in app.button if b.label == "Update chart").click().run()
    assert not app.exception and charts[-1] == ("MSFT", "1Y") and len(calls) == 1


def test_provider_partial_failure_preserves_other_instruments(monkeypatch):
    from langgraphagenticai.providers import market_dashboard as provider
    monkeypatch.setattr(provider, "get_fmp_json", lambda *a, **k: [])
    def load(symbol, key):
        if symbol == "XLK":
            raise ValueError("Synthetic unavailable history")
        return {"records": history(), "warnings": []}
    monkeypatch.setattr(provider, "load_fmp_daily_prices", load)
    packet = provider.load_dashboard.__wrapped__("fake")
    assert packet["sectors"]["Technology"]["day"] is None
    assert packet["sectors"]["Energy"]["day"] is not None
    assert len(packet["rows"]) == 23 and packet["warnings"]


def test_marketaux_news_ignores_sentiment_and_serper_fails_independently(monkeypatch):
    from langgraphagenticai.providers import market_brief_news as provider
    from types import SimpleNamespace
    monkeypatch.setattr(provider.SerperClient, "search", lambda *a, **k: {"ok": False, "results": []})
    response = SimpleNamespace(status_code=200, raise_for_status=lambda: None, json=lambda: {"data": [{"title": "Rates",
        "url": "https://example.com/rates", "entities": [{"sentiment_score": 0}, {"sentiment_score": .4}, {"sentiment_score": "bad"}]},
        {"title": "No entity score", "url": "https://example.com/other", "entities": None}]})
    monkeypatch.setattr(provider.requests, "get", lambda *a, **k: response)
    result = provider.load_market_news.__wrapped__("fake", "fake")
    assert len(result["articles"]) == 2
    assert all("sentiment" not in article for article in result["articles"])
    assert result["warnings"] and "fake" not in str(result)


def test_summary_receives_entire_dashboard_with_bounded_explicit_request(monkeypatch):
    from langgraphagenticai.analysis import market_brief_ai as ai
    from types import SimpleNamespace
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Summary"))])
    def client(*a, **k):
        assert k["max_retries"] == 0 and k["timeout"] == 75
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(ai, "build_openai_client", client)
    packet = {"rows": [{"Ticker": "XLK", "vs SMA 200 %": 7, "60D %": 10}], "warnings": ["partial"]}
    assert ai.interpret_market(packet, {"articles": [{"title": "Market news"}]}, "fake", "gpt-5") == "Summary"
    prompt = str(calls[0]["messages"])
    assert "vs SMA 200 %" in prompt and "Market news" not in prompt and "partial" in prompt
    assert "160 words" in prompt and "What is working" in prompt and "What is not working" in prompt
    assert "fake" not in prompt and calls[0]["max_completion_tokens"] == 6000
    ai.interpret_market(packet, {"articles": [{"title": "Market news", "url": "https://example.com/news", "article_text": "Provider article content", "sentiment": .9}]}, "fake", "gpt-5", "What news is relevant?")
    import json
    followup_evidence = json.loads(calls[1]["messages"][1]["content"].split("\n", 1)[1])
    assert followup_evidence["news"]["articles"][0]["title"] == "Market news"
    assert followup_evidence["news"]["articles"][0]["article_text"] == "Provider article content"
    assert "sentiment" not in followup_evidence["news"]["articles"][0]
    assert calls[1]["max_completion_tokens"] == 6000


def test_news_presentation_is_scannable_and_escaped(monkeypatch):
    import sys
    from types import SimpleNamespace
    news = {"articles": [{"title": "<script>bad()</script> Markets rally", "url": "https://example.com/story", "snippet": "<img src=x onerror=bad()> " + "Long preview " * 40,
        "publisher": "Reuters", "providers": ["Serper", "Marketaux"], "published": "2026-10-16", "sentiment": .9} for _ in range(7)]}
    monkeypatch.setitem(sys.modules, "market_news_fixture", SimpleNamespace(news=news))
    app = AppTest.from_string("from market_news_fixture import news\nfrom langgraphagenticai.ui.market_dashboard import render_market_news\nrender_market_news(news)").run(timeout=30)
    assert not app.exception
    text = " ".join(x.value for x in app.markdown) + " ".join(x.value for x in app.caption)
    assert "sentiment" not in text.lower()
    assert "&lt;script&gt;" in text and "<script>" not in text
    assert "LEAD STORY" in text and any(e.label == "More headlines (2)" for e in app.expander)


@pytest.mark.parametrize("finish,content,expected", [("length", None, "reasoning/output"), ("length", "Partial", "truncated"), ("stop", "  ", "no readable")])
def test_empty_reasoning_and_truncation_are_actionable(monkeypatch, finish, content, expected):
    from langgraphagenticai.analysis import market_brief_ai as ai
    from types import SimpleNamespace
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(content=content))])
    monkeypatch.setattr(ai, "build_openai_client", lambda *a, **k: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with pytest.raises(ValueError, match=expected):
        ai.interpret_market({"rows": []}, {}, "fake", "gpt-5")
    assert len(calls) == 1 and calls[0]["max_completion_tokens"] == 6000


def test_marketaux_request_uses_supported_date_and_small_plan_limit(monkeypatch):
    from langgraphagenticai.providers import market_brief_news as provider
    from types import SimpleNamespace
    import re
    def get(url, **kwargs):
        assert kwargs["params"]["limit"] == 3
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", kwargs["params"]["published_after"])
        return SimpleNamespace(status_code=200, raise_for_status=lambda: None, json=lambda: {"data": []})
    monkeypatch.setattr(provider.requests, "get", get)
    result = provider.load_market_news.__wrapped__("", "fake")
    assert not any("failed" in w for w in result["warnings"])
