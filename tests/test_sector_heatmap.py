from datetime import datetime, timezone

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.analysis.sector_heatmap import SECTORS, canonical_sector, industry_groups, sector_returns
from langgraphagenticai.providers import sector_heatmap as provider
from langgraphagenticai.ui import sector_heatmap as ui


NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)


def packet(*args):
    return {"provider": "Synthetic FMP", "retrieved_at": "2026-01-10T00:00:00+00:00",
            "basis": "Adjusted close", "sectors": {name: {"day": 0, "week": 5, "ytd": 10,
            "as_of": "2026-01-09", "starts": {"day": "2026-01-08"}, "stale": False} for name in SECTORS}}


def records(values, dates=None):
    dates = dates if dates is not None else pd.date_range("2026-01-08", periods=len(values))
    return [{"date": str(pd.Timestamp(date).date()), "close": value, "adj_close": value} for date, value in zip(dates, values)]


def test_returns_use_previous_adjclose_not_raw_close_or_ohlc_change():
    now = pd.Timestamp("2026-01-09T18:00Z")
    rows = [{"date": "2026-01-08", "close": 200, "adj_close": 100},
            {"date": "2026-01-09", "close": 110, "adj_close": 109}]
    result = sector_returns(rows, now)
    assert result["day"] == pytest.approx(10)
    assert result["previous_adj_close"] == 100 and result["price"] == 110
    assert result["starts"]["day"] == "2026-01-08"
    assert result["change"] == 10


def test_quote_uses_previous_trading_date_even_with_today_history():
    rows = records([100, 105], ["2026-01-08", "2026-01-09"])
    result = sector_returns(rows, pd.Timestamp("2026-01-09T19:00Z"),
                            {"price": 110, "as_of": "2026-01-09T18:00Z"})
    assert result["day"] == pytest.approx(10)  # Not 110 / same-day 105.
    assert result["price_source"] == "FMP quote price"


def test_monday_uses_friday_adjusted_close():
    rows = records([200, 100], ["2026-01-08", "2026-01-09"])
    result = sector_returns(rows, pd.Timestamp("2026-01-12T18:00Z"),
                            {"price": 110, "as_of": "2026-01-12T17:59Z"})
    assert result["day"] == pytest.approx(10)
    assert result["starts"]["day"] == "2026-01-09"


@pytest.mark.parametrize("quote", [
    {"price": 999, "as_of": "2026-01-09T23:00Z"},
    {"price": 999, "as_of": None},
    {"price": 999, "as_of": "2026-01-08T17:00Z"},
])
def test_future_undated_and_older_quotes_do_not_replace_latest_history(quote):
    result = sector_returns(records([100, 110]), pd.Timestamp("2026-01-09T19:00Z"), quote)
    assert result["day"] == pytest.approx(10)
    assert result["price"] == 110
    assert "historical close" in result["price_source"]


@pytest.mark.parametrize("bad", [None, 0, float("inf"), -1])
def test_missing_previous_adjclose_never_uses_raw_or_older_close(bad):
    rows = records([50, 100, 110], ["2026-01-07", "2026-01-08", "2026-01-09"])
    rows[1]["adj_close"] = bad
    assert sector_returns(rows, pd.Timestamp("2026-01-09T19:00Z"))["day"] is None


def test_zero_duplicates_future_stale_and_new_york_date():
    assert sector_returns(records([100, 100]), NOW)["day"] == 0
    rows = records([100, 101, 102], ["2026-01-08", "2026-01-08", "2026-01-09"])
    assert sector_returns(rows, NOW)["day"] is None
    result = sector_returns(records([100, 110], ["2025-11-01", "2025-12-01"]), NOW)
    assert result["day"] is None and result["stale"] and result["ytd"] is None
    rows = records([100, 110, 999], ["2026-01-08", "2026-01-09", "2026-01-10"])
    result = sector_returns(rows, pd.Timestamp("2026-01-10T00:30Z"))
    assert result["price_date"] == "2026-01-09"  # Still Friday in New York.
    assert result["day"] == pytest.approx(10)


def test_week_and_ytd_keep_separate_adjusted_baselines():
    rows = records([100, 101, 102, 103, 104, 105, 110],
                   ["2025-12-31", "2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"])
    result = sector_returns(rows, NOW)
    assert result["day"] == pytest.approx(100 * (110 / 105 - 1))
    assert result["week"] == pytest.approx(100 * (110 / 101 - 1))
    assert result["ytd"] == pytest.approx(10)
    assert result["starts"] == {"day": "2026-01-08", "week": "2026-01-02", "ytd": "2025-12-31"}


def test_provider_fmp_quote_and_histories_partial_failure(monkeypatch):
    from types import SimpleNamespace
    calls = []
    monkeypatch.setattr(provider, "datetime", SimpleNamespace(now=lambda tz: pd.Timestamp("2026-01-09T19:00Z")))
    def get(url, **kwargs):
        calls.append(url)
        return [{"symbol": "XLK", "price": 110, "changesPercentage": -99,
                 "timestamp": int(pd.Timestamp("2026-01-09T18:00Z").timestamp())}]
    def load(symbol, key):
        if symbol != "XLK":
            raise RuntimeError("sensitive-provider-detail")
        return {"records": records([100, 105]), "warnings": []}
    monkeypatch.setattr(provider, "get_fmp_json", get)
    monkeypatch.setattr(provider, "load_fmp_daily_prices", load)
    result = provider.load_sector_performance.__wrapped__("synthetic")
    assert len(calls) == 1 and "/quote/" in calls[0]
    assert result["sectors"]["Technology"]["day"] == pytest.approx(10)
    assert result["sectors"]["Energy"]["day"] is None
    assert "sensitive-provider-detail" not in str(result)
    assert "Yahoo" not in str(result)


def test_missing_fmp_key_never_calls_other_provider(monkeypatch):
    monkeypatch.setattr(provider, "get_fmp_json", lambda *a, **k: pytest.fail("No key must not request prices"))
    result = provider.load_sector_performance.__wrapped__()
    assert len(result["sectors"]) == 11 and result["warnings"]
    assert all(row["day"] is None for row in result["sectors"].values())


def test_memberships_alias_dedup_and_missing_industry():
    frame = pd.DataFrame([{"symbol": "BBB", "sector": "Financials", "industry": "Banks", "marketCap": 2},
                          {"symbol": "AAA", "sector": "Financial Services", "industry": "Banks", "marketCap": 4},
                          {"symbol": "AAA", "sector": "Financial Services", "industry": "Banks", "marketCap": 4},
                          {"symbol": "CCC", "sector": "Technology", "industry": "Software", "marketCap": 9}])
    groups = industry_groups(frame, "Financial Services")
    assert [row["symbol"] for row in groups["Banks"]] == ["AAA", "BBB"]
    assert industry_groups(frame.drop(columns="industry"), "Financial Services") == {}
    assert canonical_sector("Basic Materials") == "Materials"
    assert canonical_sector("Unrecognized") == "Unrecognized"


def test_tile_table_zero_clipping_and_missing_contract():
    data = packet()
    data["sectors"]["Energy"]["day"] = -20
    data["sectors"]["Utilities"]["day"] = None
    rows = {row["sector"]: row for row in ui.mosaic_rows(data, "Technology")}
    assert len(rows) == 11 and rows["Technology"]["display"] == "+0.00%"
    assert rows["Energy"]["color"] == -3 and rows["Energy"]["day"] == -20
    assert rows["Utilities"]["display"] == "Unavailable"
    assert rows["Technology"]["selected"]
    ui.mosaic_chart(data, "Technology").to_dict(validate=True)


def test_ui_selection_sort_load_and_rerun_reuse(monkeypatch):
    monkeypatch.setattr(ui, "load_sector_performance", packet)
    calls = []
    def collect(key):
        calls.append(key)
        return {"fetched_at": "2026-01-10", "universe": pd.DataFrame([
            {"symbol": "AAA", "sector": "Technology", "industry": "Software", "marketCap": 10, "price": 100, "1D": 0},
            {"symbol": "BBB", "sector": "Energy", "industry": "Oil", "marketCap": 20, "price": 50, "1D": 1}])}
    monkeypatch.setattr(ui, "collect_discovery", collect)
    app = AppTest.from_string('from langgraphagenticai.ui.sector_heatmap import render_sector_heatmap\nrender_sector_heatmap("synthetic")').run(timeout=30)
    assert not app.exception
    app.button(key="heatmap_load").click().run()
    assert not app.exception and len(calls) == 1
    app.selectbox(key="heatmap_sector").select("Energy").run()
    assert not app.exception and len(calls) == 1
    assert app.session_state["heatmap_chart_epoch"] == 1
    assert any("Industries · Energy" in item.value for item in app.subheader)
    assert "BBB" in app.selectbox(key="heatmap_company").options
    app.selectbox(key="heatmap_sort").select("Week").run()
    app.run()
    assert not app.exception and len(calls) == 1
    app.button(key="heatmap_open").click().run()
    assert app.session_state["pending_company_context"].symbols == ("BBB",)


def test_heatmap_route_independent_of_market_indexes(market_dashboard_stub):
    ui, packet, calls = market_dashboard_stub
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab()").run(timeout=30)
    app.button(key="intro_refresh").click().run()
    assert not app.exception
    assert any(s.value == "Sector heatmap" for s in app.subheader); assert not app.radio



def test_ui_missing_key_and_history_failure_are_readable(monkeypatch):
    monkeypatch.setattr(ui, "load_sector_performance", lambda *args: {"sectors": {}, "warnings": ["History unavailable"]})
    app = AppTest.from_string('from langgraphagenticai.ui.sector_heatmap import render_sector_heatmap\nrender_sector_heatmap()').run(timeout=30)
    assert not app.exception
    assert app.button(key="heatmap_load").disabled
    assert any("History unavailable" in row.value for row in app.warning)
    assert any("configuration is required" in row.value for row in app.info)


def test_ui_credential_change_discards_old_screen(monkeypatch):
    monkeypatch.setattr(ui, "load_sector_performance", packet)
    monkeypatch.setattr(ui, "collect_discovery", lambda key: {"universe": pd.DataFrame(), "fetched_at": "2026-01-10"})
    app = AppTest.from_string('import streamlit as st\nfrom langgraphagenticai.ui.sector_heatmap import render_sector_heatmap\nrender_sector_heatmap(st.session_state.get("qa_key", "tenant-one"))').run(timeout=30)
    app.button(key="heatmap_load").click().run()
    assert "heatmap_screen" in app.session_state
    app.session_state["qa_key"] = "tenant-two"
    app.run()
    assert not app.exception and "heatmap_screen" not in app.session_state


def test_failed_reload_preserves_screen_and_redacts_known_key(monkeypatch):
    monkeypatch.setattr(ui, "load_sector_performance", packet)
    calls = []
    def collect(key):
        calls.append(key)
        if len(calls) > 1:
            raise RuntimeError("Credential tenant-sensitive rejected")
        return {"universe": pd.DataFrame(), "fetched_at": "2026-01-10"}
    monkeypatch.setattr(ui, "collect_discovery", collect)
    app = AppTest.from_string('from langgraphagenticai.ui.sector_heatmap import render_sector_heatmap\nrender_sector_heatmap("tenant-sensitive")').run(timeout=30)
    app.button(key="heatmap_load").click().run()
    app.button(key="heatmap_load").click().run()
    assert not app.exception and "heatmap_screen" in app.session_state
    assert all("tenant-sensitive" not in row.value for row in app.warning)
    assert any("refresh failed" in row.value for row in app.caption)
