import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.providers import market_history
from langgraphagenticai.providers import symbol_history
from langgraphagenticai.ui import market_overview_data
from langgraphagenticai.providers import discovery as top_movers_data
from langgraphagenticai.ui.top_movers_tab import _rows


@pytest.fixture(autouse=True)
def clear_chart_cache():
    market_history.load_market_chart.clear()
    symbol_history.clear_history_cache()
    yield
    market_history.load_market_chart.clear()
    symbol_history.clear_history_cache()


def test_chart_ranges_sort_and_filter(monkeypatch):
    rows = [{"date": date, "close": price} for date, price in
            [("2026-09-30 15:00", 101), ("2026-09-29 15:00", 90), ("2026-09-30 09:30", 100)]]
    monkeypatch.setattr(symbol_history, "get_fmp_json", lambda *a, **k: rows)
    result = market_history.load_market_chart.__wrapped__("test", "1D")
    assert [value for _, value in result["points"]] == [100, 101]
    result = market_history.load_market_chart.__wrapped__("test", "5D")
    assert [value for _, value in result["points"]] == [90, 100, 101]


def test_chart_fallback_keeps_one_source(monkeypatch):
    monkeypatch.setattr(symbol_history, "get_fmp_json", lambda *a, **k: [])
    monkeypatch.setattr(symbol_history.yf, "download", lambda *a, **k: pd.DataFrame(
        {"Close": [1, 2]}, index=pd.date_range("2026-09-29", periods=2)))
    result = market_history.load_market_chart.__wrapped__("", "1M")
    assert result["provider"] == "Yahoo Finance"
    assert result["warnings"]
    assert len(result["points"]) == 2


def test_missing_market_quotes_are_labelled(monkeypatch):
    monkeypatch.setattr(market_overview_data, "get_fmp_json", lambda url, **k:
                        [{"symbol": "^GSPC", "price": 100, "changesPercentage": 0}] if "/quote/" in url else [])
    def download(*a, **k):
        return pd.DataFrame({("Close", "^VIX"): [20, 21]}, index=pd.date_range("2026-09-29", periods=2))
    monkeypatch.setattr(market_overview_data.yf, "download", download)
    result = market_overview_data._load_fmp_market_overview("test")
    assert result["indexes"]["VIX"]["price"] == 21
    assert "fallback" in result["indexes"]["VIX"]["provider"]
    assert result["indexes"]["S&P 500"]["percent"] == 0
    assert result["warnings"]


def test_fmp_commodity_and_crypto_aliases(monkeypatch):
    calls = []
    def quotes(url, **kwargs):
        calls.append(url)
        return [{"symbol": symbol, "price": price, "changesPercentage": 0,
                 "timestamp": 1790866800} for symbol, price in
                [("GCUSD", 3000), ("CLUSD", 70), ("BTCUSD", 100000)]]
    monkeypatch.setattr(market_overview_data, "get_fmp_json", quotes)
    monkeypatch.setattr(market_overview_data.yf, "download", lambda **kwargs: pd.DataFrame())
    result = market_overview_data._load_fmp_market_overview("test")
    assert "GC=F" not in calls[0] and "BTC-USD" not in calls[0]
    assert "GCUSD" in calls[0] and "CLUSD" in calls[0] and "BTCUSD" in calls[0]
    assert result["cross_assets"]["Gold"]["price"] == 3000
    assert result["cross_assets"]["Bitcoin"]["price"] == 100000


def test_movers_missing_average_volume_preserves_rankings(monkeypatch):
    def get(url, key, **params):
        if "stock-screener" in url:
            return [{"symbol": "aapl", "price": 100, "marketCap": 3e12, "volume": 10, "sector": None}]
        if "stock-price-change" in url:
            return [{"symbol": "AAPL", "5D": 2, "1D": 0}]
        return [{"symbol": "AAPL", "price": 101}]
    monkeypatch.setattr(top_movers_data, "_get", get)
    result = top_movers_data.collect_discovery.__wrapped__("test")
    frame = result["gainers"]
    assert frame.iloc[0]["price"] == 100
    assert pd.isna(frame.iloc[0]["liquidityRatio"])
    assert frame.iloc[0]["sector"] == "Unknown"
    html = _rows(frame)
    assert "Unavailable" in html and "nan" not in html.lower()
    assert "+0.00%" in html


def test_market_range_interaction_does_not_call_ai(market_dashboard_stub):
    ui, packet, calls = market_dashboard_stub
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab()").run(timeout=30)
    app.button(key="intro_refresh").click().run()
    assert not app.exception
    app.get("button_group")[0].set_value("3M").run(); assert calls[-1] == ("^GSPC", "3M") and not app.exception



def test_company_range_reuses_summary(market_dashboard_stub):
    ui, packet, calls = market_dashboard_stub
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab()").run(timeout=30)
    app.button(key="intro_refresh").click().run()
    assert not app.exception
    assert not any("ANALYZE COMPANY" in b.label for b in app.button); assert app.text_input[1].value == "^GSPC"



def test_top_movers_direction_and_sector_interaction(monkeypatch):
    from datetime import datetime, timezone
    from langgraphagenticai.ui import top_movers_tab
    frame = pd.DataFrame([
        {"symbol": "AAA", "companyName": "Alpha", "sector": "Technology", "price": 10, "5D": 3, "1D": 0, "marketCap": 3e9},
        {"symbol": "BBB", "companyName": "Beta", "sector": "Energy", "price": 20, "5D": -2, "1D": -1, "marketCap": 4e9}])
    sectors = pd.DataFrame([{"sector": "Technology", "weekly_return": 3, "advancers": 1, "decliners": 0}])
    data = {"universe": frame, "gainers": frame.iloc[:1], "losers": frame.iloc[1:].reset_index(drop=True),
            "sectors": sectors, "news": {}, "universe_size": 2,
            "fetched_at": datetime.now(timezone.utc), "providers": ["Synthetic"]}
    monkeypatch.setattr(top_movers_tab, "load_top_movers", lambda *args: data)
    from langgraphagenticai.providers import discovery
    monkeypatch.setattr(discovery, "load_selected_news", lambda *args: {"results": [], "error": "Not configured"})
    monkeypatch.setattr(discovery, "load_selected_quote", lambda *args: {"error": "Not configured"})
    monkeypatch.setattr(symbol_history, "load_symbol_history", lambda *args: {"points": []})
    app = AppTest.from_string("from langgraphagenticai.ui.top_movers_tab import render_top_movers_tab\nrender_top_movers_tab(fmp_api_key='test', serper_api_key='')")
    app.run(timeout=30)
    assert not app.exception
    app.get("button_group")[0].set_value("Laggards").run()
    assert not app.exception
    assert app.selectbox(key="movers_focus").value == "AAA"  # Valid selection is retained.
    assert app.dataframe[0].value.iloc[0]["Ticker"] == "BBB"
    app.selectbox(key="movers_sector_filter").set_value("Technology").run()
    assert not app.exception
    assert app.selectbox(key="movers_focus").value == "AAA"


def test_market_brief_primary_row_keeps_chart_observations_sector_and_no_ai(market_dashboard_stub):
    ui, packet, calls = market_dashboard_stub
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab()").run(timeout=30)
    app.button(key="intro_refresh").click().run()
    assert not app.exception
    assert {"Sector heatmap", "Macro context & sector ETFs", "Daily price chart"}.issubset({s.value for s in app.subheader})



def test_populated_market_brief_keeps_sector_and_candidate_actions(market_dashboard_stub):
    ui, packet, calls = market_dashboard_stub
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab()").run(timeout=30)
    app.button(key="intro_refresh").click().run()
    assert not app.exception
    assert not app.radio; assert not any("Research candidates" in s.value or "Explore sectors" in s.value for s in app.subheader)



def test_movers_selected_quote_keeps_unknown_currency_and_zero_change(monkeypatch):
    from langgraphagenticai.ui import top_movers_tab
    from langgraphagenticai.providers import discovery, symbol_history

    frame = pd.DataFrame([{"symbol": "AAA", "companyName": "Alpha", "sector": "Technology", "price": 210, "1D": 0, "5D": 0}])
    monkeypatch.setattr(top_movers_tab, "load_top_movers", lambda *_: {"universe": frame, "requested_universe_size": 1})
    monkeypatch.setattr(discovery, "load_selected_quote", lambda *_: {"price": 210, "change": 0, "change_pct": 0})
    monkeypatch.setattr(discovery, "load_selected_news", lambda *_: {"results": []})
    monkeypatch.setattr(symbol_history, "load_symbol_history", lambda *_: {"points": []})
    app = AppTest.from_string("from langgraphagenticai.ui.top_movers_tab import render_top_movers_tab\nrender_top_movers_tab(fmp_api_key='fixture',serper_api_key='')").run(timeout=30)
    assert not app.exception
    quote = next(item.value for item in app.markdown if 'class="terminal-quote"' in item.value)
    assert "210.00" in quote and "Unknown quote currency" in quote
    assert "+0.00 (+0.00%)" in quote
