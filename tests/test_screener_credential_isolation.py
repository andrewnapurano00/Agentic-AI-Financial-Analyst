"""Offline contracts for per-credential Screener requests and caches."""

import pandas as pd
from streamlit.testing.v1 import AppTest

from langgraphagenticai.ui import stock_screener_tab as ui


def test_universe_and_enrichment_caches_are_scoped_to_request_credentials(monkeypatch):
    calls = []

    def fake_get(url, *, api_key, params, timeout):
        calls.append((url, api_key, dict(params), timeout))
        value = 1 if api_key == "tenant-a" else 2
        if url.endswith("/stable/company-screener"):
            return [{"symbol": "AAPL", "marketCap": value * 100, "isEtf": False, "isFund": False}]
        if "/api/v3/quote/" in url:
            return [{"price": float(value), "volume": value * 10}]
        return []

    monkeypatch.setattr(ui, "get_fmp_json", fake_get)
    monkeypatch.setattr(ui.time, "sleep", lambda _seconds: None)
    ui.fmp_company_screener_safe.clear()
    ui.fetch_all_metrics.clear()

    a_universe, a_meta = ui.fmp_company_screener_safe({"limit": 2}, max_pages=1, api_key="tenant-a")
    b_universe, b_meta = ui.fmp_company_screener_safe({"limit": 2}, max_pages=1, api_key="tenant-b")
    again_a, again_meta = ui.fmp_company_screener_safe({"limit": 2}, max_pages=1, api_key="tenant-a")
    assert [frame["marketCap"].iloc[0] for frame in (a_universe, b_universe, again_a)] == [100, 200, 100]
    assert [a_meta["pages"], b_meta["pages"], again_meta["pages"]] == [1, 1, 1]
    universe_calls = [call for call in calls if call[0].endswith("/stable/company-screener")]
    assert [call[1] for call in universe_calls] == ["tenant-a", "tenant-b"]

    same_screen = pd.DataFrame([{"ticker": "AAPL", "marketCap": 100}])
    a_metrics = ui.fetch_all_metrics(["AAPL"], same_screen, api_key="tenant-a")
    b_metrics = ui.fetch_all_metrics(["AAPL"], same_screen, api_key="tenant-b")
    before_hit = len(calls)
    again_metrics = ui.fetch_all_metrics(["AAPL"], same_screen, api_key="tenant-a")
    assert len(calls) == before_hit
    assert [frame["Price"].iloc[0] for frame in (a_metrics, b_metrics, again_metrics)] == [1.0, 2.0, 1.0]
    assert {call[1] for call in calls} == {"tenant-a", "tenant-b"}
    assert all("apikey" not in params for _, _, params, _ in calls)
    assert all("tenant-" not in frame.to_json() for frame in (a_universe, b_universe, a_metrics, b_metrics))
    assert ui._credential_scope("tenant-a") != ui._credential_scope("tenant-b")
    assert "tenant-a" not in ui._credential_scope("tenant-a")


def test_missing_key_stops_before_screener_or_enrichment_cache():
    ui.fmp_company_screener_safe.clear()
    ui.fetch_all_metrics.clear()
    for action in (
        lambda: ui.fmp_company_screener_safe({"limit": 2}, api_key=" "),
        lambda: ui.fetch_all_metrics(["AAPL"], pd.DataFrame(), api_key=""),
    ):
        try:
            action()
        except ValueError as exc:
            assert str(exc) == "FMP API key is required."
        else:
            raise AssertionError("Missing credentials must not access a cached result")


def test_provider_error_does_not_return_or_cache_the_active_key(monkeypatch):
    def rejected(_url, *, api_key, **_kwargs):
        raise RuntimeError(f"credential {api_key} rejected")

    monkeypatch.setattr(ui, "get_fmp_json", rejected)
    ui.fmp_company_screener_safe.clear()
    frame, meta = ui.fmp_company_screener_safe({"limit": 2}, max_pages=1, api_key="tenant-a")
    assert frame.empty
    assert "tenant-a" not in str(meta)
    assert "[REDACTED]" in str(meta)
    cached_frame, cached_meta = ui.fmp_company_screener_safe({"limit": 2}, max_pages=1, api_key="tenant-a")
    assert cached_frame.empty and cached_meta == meta


def test_two_screener_sessions_keep_their_own_saved_results(monkeypatch):
    requests = []

    def screen(filters, *, api_key, **_kwargs):
        requests.append(("screen", api_key))
        symbol = "AAA" if api_key == "tenant-a" else "BBB"
        return pd.DataFrame([{"ticker": symbol, "marketCap": 100}]), {"pages": 1, "warnings": [], "errors": []}

    def enrich(symbols, *, api_key, **_kwargs):
        requests.append(("enrich", api_key))
        return pd.DataFrame([{"Ticker": symbols[0], "Market Cap": 100, "Price": 1.0}])

    monkeypatch.setattr(ui, "fmp_company_screener_safe", screen)
    monkeypatch.setattr(ui, "fetch_all_metrics", enrich)
    harness = (
        "import streamlit as st\n"
        "from langgraphagenticai.ui.stock_screener_tab import render_stock_screener_tab\n"
        "render_stock_screener_tab(st.session_state['credential'])\n"
    )
    apps = [AppTest.from_string(harness, default_timeout=30) for _ in range(2)]
    for app, credential in zip(apps, ("tenant-a", "tenant-b")):
        app.session_state["credential"] = credential
        app.run()
        next(button for button in app.button if button.label == "Run Screener").click().run()
        assert not app.exception
    assert [app.session_state["stock_screener_payload"]["results"]["Ticker"].iloc[0] for app in apps] == ["AAA", "BBB"]
    for app in apps:
        app.run()
        assert not app.exception
    assert requests == [
        ("screen", "tenant-a"), ("enrich", "tenant-a"),
        ("screen", "tenant-b"), ("enrich", "tenant-b"),
    ]
