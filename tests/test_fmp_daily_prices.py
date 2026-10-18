"""Adjusted-baseline regressions use independently different raw/adjusted prices."""
import pandas as pd
import pytest

from langgraphagenticai.providers import fmp_daily_prices as daily, symbol_history
from langgraphagenticai.analysis.sector_heatmap import sector_returns


NOW = pd.Timestamp("2026-10-16T18:00Z")


@pytest.fixture(autouse=True)
def clear_daily():
    symbol_history.clear_history_cache()
    yield
    symbol_history.clear_history_cache()


def test_endpoint_envelope_dates_fields_and_cache(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return {"symbol": "XLK", "historical": [
            {"date": "2026-10-16", "close": 110, "adjClose": 109, "changePercent": -99},
            {"date": "2026-10-15", "close": 200, "adjClose": 100}]}
    monkeypatch.setattr(daily, "get_fmp_json", get)
    first = daily.load_fmp_daily_prices("xlk", "synthetic")
    second = daily.load_fmp_daily_prices("xlk", "synthetic")
    assert first == second and len(calls) == 1
    assert calls[0][0] == daily.BASE + "XLK" and "apikey" not in calls[0][0]
    assert calls[0][1]["timeout"] == (5, 20) and "from" in calls[0][1]["params"]
    assert first["records"][0] == {"date": "2026-10-15", "close": 200, "adj_close": 100}
    assert sector_returns(first["records"], NOW)["day"] == pytest.approx(10)
    assert "synthetic" not in str(first)


@pytest.mark.parametrize("bad", [None, 0, "bad", float("inf"), True])
def test_missing_adjclose_keeps_date_and_never_substitutes_close(bad):
    payload = {"symbol": "XLK", "historical": [
        {"date": "2026-10-14", "close": 50, "adjClose": 50},
        {"date": "2026-10-15", "close": 100, "adjClose": bad},
        {"date": "2026-10-16", "close": 110, "adjClose": 110}]}
    records, _ = daily.normalize_daily_prices(payload, "XLK", NOW)
    assert records[1]["adj_close"] is None
    assert sector_returns(records, NOW)["day"] is None


def test_daily_identity_duplicate_and_future_rules():
    rows = [{"date": "2026-10-15", "close": 100, "adjClose": 90},
            {"date": "2026-10-15", "close": 100, "adjClose": 90},
            {"date": "2026-10-16", "close": 110, "adjClose": 109},
            {"date": "2099-01-01", "close": 999, "adjClose": 999},
            {"date": "2026-10-14", "symbol": "XLF", "close": 10, "adjClose": 10}]
    records, warnings = daily.normalize_daily_prices({"symbol": "XLK", "historical": rows}, "XLK", NOW)
    assert len(records) == 2 and records[0]["adj_close"] is None and warnings
    assert sector_returns(records, NOW)["day"] is None
    assert daily.normalize_daily_prices({"symbol": "XLF", "historical": rows}, "XLK", NOW)[0] == []


def test_daily_chart_uses_adjclose_and_keeps_today(monkeypatch):
    monkeypatch.setattr(daily, "get_fmp_json", lambda *a, **k: {"symbol": "XLK", "historical": [
        {"date": "2026-10-15", "close": 200, "adjClose": 100},
        {"date": "2026-10-16", "close": 220, "adjClose": 110}]})
    monkeypatch.setattr(symbol_history, "_utc_now", lambda: NOW)
    monkeypatch.setattr(symbol_history.yf, "download", lambda *a, **k: pytest.fail("FMP configured; no Yahoo"))
    chart = symbol_history.load_symbol_history("XLK", "synthetic", "1M")
    assert [point[1] for point in chart["points"]] == [100, 110]
    assert chart["price_basis"] == "FMP adjClose"
    assert chart["source"] == daily.BASE + "XLK"


def test_daily_provider_failure_is_secret_safe_without_fallback(monkeypatch):
    def fail(*a, **k):
        raise RuntimeError("synthetic-private-key")
    monkeypatch.setattr(daily, "get_fmp_json", fail)
    monkeypatch.setattr(symbol_history.yf, "download", lambda *a, **k: pytest.fail("No substitute"))
    chart = symbol_history.load_symbol_history("XLK", "synthetic-private-key", "1M")
    assert not chart["points"] and chart["warnings"]
    assert "synthetic-private-key" not in str(chart)


def test_overview_sectors_use_shared_adjusted_baseline_not_quote_percent(monkeypatch):
    from langgraphagenticai.ui import market_overview_data as overview
    monkeypatch.setattr(overview, "get_fmp_json", lambda *a, **k: [
        {"symbol": "XLK", "price": 110, "changesPercentage": -50}])
    monkeypatch.setattr(overview.yf, "download", lambda **kwargs: pd.DataFrame())
    monkeypatch.setattr(overview, "load_sector_performance", lambda key: {
        "basis": "Latest price / prior adjClose - 1", "sectors": {"Technology": {
            "price": 110, "day": 10, "change": 10, "previous_adj_close": 100,
            "starts": {"day": "2026-10-15"}, "as_of": "2026-10-16T17:59Z"}}})
    row = overview._load_fmp_market_overview("synthetic")["sectors"]["Technology"]
    assert row["percent"] == 10 and row["previous_adj_close"] == 100
    assert row["previous_date"] == "2026-10-15"
