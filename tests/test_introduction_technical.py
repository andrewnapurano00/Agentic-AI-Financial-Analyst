"""Offline Introduction history/indicator/evidence/agent/interaction contracts."""
import json
import math
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.providers import symbol_history as history
from langgraphagenticai.technical_analysis.indicators import (
    IndicatorSettings, calculate_indicators, finite_domain, axis_style,
)
from langgraphagenticai.technical_analysis.evidence import technical_packet, technical_summary
from langgraphagenticai.technical_analysis import agent
from langgraphagenticai.ui import technical_chart


@pytest.fixture(autouse=True)
def no_cached_history():
    history.clear_history_cache()
    yield
    history.clear_history_cache()


def prices(values, start="2026-01-01"):
    return list(zip(pd.date_range(start, periods=len(values)), values))


def chart_data(period="1Y"):
    points = prices(list(range(100, 140)))
    return {"symbol": "AAPL", "period": period, "points": points, "calculation_points": points,
            "provider": "Synthetic", "source": "offline fixture", "price_basis": "Raw close",
            "as_of": str(points[-1][0]), "retrieved_at": "2026-02-10T00:00:00Z",
            "unit": "USD", "currency": "USD", "interval": "1d", "timezone": "Unknown", "warnings": []}


@pytest.mark.parametrize("period", list(history.RANGES))
def test_all_ranges_shared_history_exact_request_and_metadata(monkeypatch, period):
    calls = []
    points = prices(range(100, 180))
    def get(url, *, api_key, params, timeout):
        calls.append((url, params, timeout))
        return [{"date": stamp.isoformat(), "close": value, "symbol": "AAPL"} for stamp, value in points]
    monkeypatch.setattr(history, "get_fmp_json", get)
    monkeypatch.setattr(history.yf, "download", lambda *a, **k: pytest.fail("No fallback when FMP has valid partial prices"))
    result = history.load_symbol_history("aapl", "synthetic", period, "USD")
    assert len(calls) == 1 and calls[0][1]["symbol"] == "AAPL"
    assert calls[0][0].endswith("historical-chart/5min" if period in {"1D", "5D"} else "historical-price-eod/full")
    assert calls[0][2] == (5, 20)
    assert result["provider"] == "Financial Modeling Prep"
    assert result["price_basis"] == "Close; adjustment unverified"
    assert result["currency"] == "USD" and "naive" in result["timezone"]
    assert result["retrieved_at"] and result["as_of"] and result["source"]
    assert len(result["points"]) == (1 if period == "1D" else 5 if period == "5D" else len(result["points"]))
    if period in {"3M", "1Y", "3Y", "5Y", "10Y"}:
        assert result["partial"]


def test_five_observed_sessions_instead_of_five_calendar_days():
    timestamps = pd.to_datetime(["2026-09-18 15:00", "2026-09-21 10:00", "2026-09-21 15:00", "2026-09-22 15:00",
                                 "2026-09-23 15:00", "2026-09-24 15:00", "2026-09-25 15:00"])
    observed = list(zip(timestamps, range(100, 107)))
    shown, calculation, partial = history.select_history(observed, "5D")
    assert len({stamp.date() for stamp, _ in shown}) == 5
    assert shown[0][0] == timestamps[1] and len(shown) == 6
    assert not partial and len(calculation) == 7
    latest, _, _ = history.select_history(observed, "1D")
    assert latest == [observed[-1]]


def test_history_rejects_nonfinite_zero_wrong_symbol_and_conflicts():
    rows = [{"date": "2026-01-02", "close": 2}, {"date": "2026-01-01", "close": 1},
            {"date": "2026-01-02", "close": 2}, {"date": "2026-01-03", "close": 3},
            {"date": "2026-01-03", "close": 4}, {"date": "2026-01-04", "close": 0},
            {"date": "2026-01-05", "close": float("inf")}, {"date": "bad", "close": 1},
            {"date": "2026-01-06", "close": 6, "symbol": "MSFT"}, {"date": "2026-01-07", "close": True}]
    points, rejected = history.normalize_history(rows, "AAPL")
    assert [value for _, value in points] == [1, 2] and rejected == 6
    assert history.normalize_history([{"date": "2026-01-01", "close": 1}, {"date": "2026-01-02T00:00Z", "close": 2}], "AAPL")[0] == []


def test_future_naive_dates_rejected_without_inventing_intraday_timezone(monkeypatch):
    monkeypatch.setattr(history, "_utc_now", lambda: pd.Timestamp("2026-10-04T12:00:00Z"))
    points, rejected = history.normalize_history([
        {"date": "2026-10-02", "close": 100},
        {"date": "2026-10-04 23:59:00", "close": 101},
        {"date": "2026-10-05", "close": 102},
        {"date": "2099-12-31", "close": 200},
    ], "AAPL")
    assert [value for _, value in points] == [100, 101] and rejected == 2
    assert points[-1][0].tz is None  # Current naive calendar day accepted; no timezone conversion.


def test_aware_future_instants_rejected_current_boundary_and_offsets_retained(monkeypatch):
    monkeypatch.setattr(history, "_utc_now", lambda: pd.Timestamp("2026-10-04T12:00:00Z"))
    points, rejected = history.normalize_history([
        {"date": "2026-10-04T07:59:59-04:00", "close": 100},
        {"date": "2026-10-04T08:00:00-04:00", "close": 101},
        {"date": "2026-10-04T08:00:01-04:00", "close": 102},
    ], "AAPL")
    assert [value for _, value in points] == [100, 101] and rejected == 1
    assert points[-1][0].isoformat() == "2026-10-04T08:00:00-04:00"


def test_future_day_exclusion_protects_asof_warmup_range_and_ai(monkeypatch):
    monkeypatch.setattr(history, "_utc_now", lambda: pd.Timestamp("2026-10-04T12:00:00Z"))
    monkeypatch.setattr(history, "get_fmp_json", lambda *a, **k: [
        {"date": "2026-10-01", "close": 99}, {"date": "2026-10-02", "close": 100},
        {"date": "2099-12-31", "close": 200}])
    monkeypatch.setattr(history.yf, "download", lambda *a, **k: pytest.fail("Valid FMP data must remain intact"))
    chart = history.load_symbol_history("AAPL", "synthetic", "1Y", "USD")
    assert chart["as_of"] == "2026-10-02T00:00:00" and chart["partial"]
    assert [value for _, value in chart["calculation_points"]] == [99, 100]
    assert any("Excluded 1" in warning and "future-dated" in warning for warning in chart["warnings"])
    settings = IndicatorSettings(sma=2)
    frame = calculate_indicators(chart["calculation_points"], settings)
    packet = technical_packet(chart, frame, settings, "gpt-5")
    assert packet["as_of"] == chart["as_of"]
    assert packet["evidence"][0]["value"] == 100 and packet["evidence"][2]["value"] == 99.5
    assert "2099" not in json.dumps(packet)


def test_future_exclusion_count_survives_whole_series_fallback(monkeypatch):
    monkeypatch.setattr(history, "_utc_now", lambda: pd.Timestamp("2026-10-04T12:00:00Z"))
    monkeypatch.setattr(history, "get_fmp_json", lambda *a, **k: [{"date": "2099-12-31", "close": 200}])
    monkeypatch.setattr(history.yf, "download", lambda *a, **k: pd.DataFrame(
        {"Close": [100, 200]}, index=pd.to_datetime(["2026-10-02", "2099-12-31"])))
    chart = history.load_symbol_history("AAPL", "synthetic", "1D")
    assert chart["provider"] == "Yahoo Finance" and [value for _, value in chart["points"]] == [100]
    assert any("Excluded 2" in warning for warning in chart["warnings"])


@pytest.mark.parametrize("payload", [None, {}, {"error": "bad"}, 1, ["bad"]])
def test_malformed_provider_whole_yahoo_fallback(monkeypatch, payload):
    monkeypatch.setattr(history, "get_fmp_json", lambda *a, **k: payload)
    fallback = Mock(return_value=pd.DataFrame({"Close": [100, 101]}, index=pd.date_range("2026-01-01", periods=2, tz="America/New_York")))
    monkeypatch.setattr(history.yf, "download", fallback)
    result = history.load_symbol_history("AAPL", "synthetic", "10Y")
    assert result["provider"] == "Yahoo Finance" and result["price_basis"] == "Yahoo auto-adjusted close"
    assert result["timezone"] == "America/New_York" and result["partial"]
    assert fallback.call_count == 1 and fallback.call_args.kwargs["auto_adjust"] is True


def test_errors_empty_recovery_and_secret_safe(monkeypatch):
    def fail(*a, **k):
        raise RuntimeError("apikey=synthetic-secret")
    monkeypatch.setattr(history, "get_fmp_json", fail)
    monkeypatch.setattr(history.yf, "download", fail)
    result = history.load_symbol_history("AAPL", "synthetic", "1D")
    assert result["points"] == [] and len(result["warnings"]) == 2
    assert "synthetic-secret" not in str(result)
    history.clear_history_cache()
    monkeypatch.setattr(history, "get_fmp_json", lambda *a, **k: [{"date": "2026-01-02", "close": 1}])
    assert history.load_symbol_history("AAPL", "synthetic", "1D")["points"]


def test_daily_range_and_setting_changes_reuse_provider_cache(monkeypatch):
    get = Mock(return_value=[{"date": stamp.isoformat(), "close": value} for stamp, value in prices(range(100, 200))])
    monkeypatch.setattr(history, "get_fmp_json", get)
    a = history.load_symbol_history("AAPL", "synthetic", "1M")
    b = history.load_symbol_history("AAPL", "synthetic", "10Y")
    calculate_indicators(a["calculation_points"], IndicatorSettings(sma=30))
    calculate_indicators(b["calculation_points"], IndicatorSettings(sma=50))
    assert get.call_count == 1


def test_indicator_arithmetic_and_flat_oscillators():
    settings = IndicatorSettings(selected=("SMA", "EMA", "RSI", "MACD", "Bollinger"), sma=3, ema=3, rsi=2,
                                 macd_fast=2, macd_slow=3, macd_signal=2, bollinger=3, bollinger_std=2)
    frame = calculate_indicators(prices([1, 2, 3, 4, 3]), settings)
    assert frame.SMA.iloc[2] == 2 and math.isnan(frame.SMA.iloc[1])
    assert frame.EMA.iloc[2] == 2.25 and frame.EMA.iloc[3] == 3.125
    assert frame.RSI.iloc[2] == 100 and frame.RSI.iloc[-1] == 50
    assert frame["Bollinger mid"].iloc[2] == 2
    assert frame["Bollinger upper"].iloc[2] == pytest.approx(2 + 2 * math.sqrt(2 / 3))
    # EMA2: 1, 5/3, 23/9; EMA3: 1, 1.5, 2.25; MACD at third bar=11/36.
    assert frame.MACD.iloc[2] == pytest.approx(11 / 36)
    assert math.isnan(frame["MACD signal"].iloc[2])
    assert frame["MACD signal"].iloc[3] == pytest.approx((11 / 36) / 3 + (frame.MACD.iloc[3]) * 2 / 3)
    flat = calculate_indicators(prices([10] * 40), settings)
    assert flat.RSI.iloc[-1] == 50 and flat.MACD.iloc[-1] == 0
    assert flat["Bollinger upper"].iloc[-1] == 10


@pytest.mark.parametrize("kwargs", [{"sma": 0}, {"rsi": 501}, {"ema": True}, {"macd_fast": 30},
                                     {"macd_slow": 499}, {"bollinger_std": float("nan")}, {"selected": ("fake",)}])
def test_invalid_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        IndicatorSettings(**kwargs)


def test_warmup_before_trim_and_axis_price_overlay_bounds():
    observed = prices(range(100, 900))
    visible, calc, _ = history.select_history(observed, "1M")
    assert len(calc) - len(visible) == 500
    frame = calculate_indicators(calc, IndicatorSettings(sma=100))
    shown = frame[frame.Date >= visible[0][0]]
    assert pd.notna(shown.SMA.iloc[0])
    domain = finite_domain([10, 10, None, float("nan"), float("inf")])
    assert 0 < domain[0] < 10 < domain[1]
    assert axis_style("1D")["format"] == "%H:%M"
    assert axis_style("5D")["format"] == "%b %d"
    assert axis_style("10Y")["format"] == "%Y"
    spec = technical_chart.price_chart_spec(shown, "1M", "USD").to_dict()
    scale = spec["encoding"]["y"]["scale"]
    assert scale["zero"] is False and scale["domain"][0] < shown.SMA.min()


def test_timezone_wall_clock_projection_preserves_source_offset():
    frame = pd.DataFrame({"Date": [pd.Timestamp("2026-09-30 09:30", tz="America/New_York")], "Close": [100.]})
    projected = technical_chart._plot_frame(frame)
    assert projected.Date.iloc[0] == pd.Timestamp("2026-09-30 09:30Z")
    assert projected["Observed timestamp"].iloc[0] == "2026-09-30T09:30:00-04:00"
    spec = technical_chart.price_chart_spec(frame, "1D", "USD").to_dict()
    assert spec["encoding"]["x"]["scale"]["type"] == "utc"


def test_single_bar_has_visible_marker_and_no_invented_change():
    chart = chart_data()
    chart["points"] = chart["calculation_points"] = chart["points"][:1]
    settings = IndicatorSettings()
    frame = calculate_indicators(chart["points"], settings)
    packet = technical_packet(chart, frame, settings, "gpt-5")
    assert packet["evidence"][1]["value"] is None
    assert "unavailable" in technical_summary(packet)[0]
    assert technical_chart.price_chart_spec(frame, "1D", "USD").to_dict()["mark"]["point"] is True


def packet_for_test(settings=None):
    chart = chart_data()
    settings = settings or IndicatorSettings()
    return technical_packet(chart, calculate_indicators(chart["points"], settings), settings, "gpt-5")


def response_for(packet, **changes):
    result = {"symbol": packet["symbol"], "range": packet["range"], "as_of": packet["as_of"], "fingerprint": packet["fingerprint"],
              "outlook": "mixed", "summary": "Close is above SMA; research only.",
              "claims": [{"interpretation": "Close above SMA.", "evidence_ids": ["T001", "T003"]}],
              "risks": ["Limited coverage"], "invalidation_conditions": ["Close below SMA"], "limitations": ["Timezone unknown"]}
    result.update(changes)
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(result), refusal=None))])


def test_fingerprint_identity_covers_prices_settings_range_interval_source_model():
    chart = chart_data()
    settings = IndicatorSettings()
    frame = calculate_indicators(chart["points"], settings)
    original = technical_packet(chart, frame, settings, "gpt-5")["fingerprint"]
    for field, value in (("period", "3Y"), ("interval", "5m"), ("provider", "Another"), ("price_basis", "Adjusted"), ("as_of", "Another")):
        assert technical_packet({**chart, field: value}, frame, settings, "gpt-5")["fingerprint"] != original
    assert technical_packet(chart, frame, IndicatorSettings(sma=30), "gpt-5")["fingerprint"] != original
    assert technical_packet(chart, frame, settings, "gpt-4.1")["fingerprint"] != original
    changed = {**chart, "calculation_points": [*chart["points"][:-1], (chart["points"][-1][0], 999)]}
    assert technical_packet(changed, frame, settings, "gpt-5")["fingerprint"] != original


def test_bounded_structured_agent(monkeypatch):
    packet = packet_for_test()
    client = Mock()
    client.chat.completions.create.return_value = response_for(packet)
    build = Mock(return_value=client)
    monkeypatch.setattr(agent, "build_openai_client", build)
    result = agent.analyze_technical(packet, "synthetic", "gpt-5")
    assert result["fingerprint"] == packet["fingerprint"]
    build.assert_called_once_with("synthetic", timeout=45, max_retries=0)
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["max_completion_tokens"] == 2200 and kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["reasoning_effort"] == "low" and len(kwargs["messages"][1]["content"]) < 16000


@pytest.mark.parametrize("changes", [{"symbol": "MSFT"}, {"fingerprint": "stale"}, {"as_of": "stale"},
    {"outlook": "buy"}, {"claims": [{"interpretation": "Bad", "evidence_ids": ["T999"]}]}, {"unexpected": "field"}])
def test_agent_rejects_identity_schema_and_unknown_citations(monkeypatch, changes):
    packet = packet_for_test()
    client = Mock()
    client.chat.completions.create.return_value = response_for(packet, **changes)
    monkeypatch.setattr(agent, "build_openai_client", lambda *a, **k: client)
    with pytest.raises(ValueError):
        agent.analyze_technical(packet, "synthetic", "gpt-5")


def test_unavailable_indicators_and_citations(monkeypatch):
    packet = packet_for_test(IndicatorSettings(sma=100))
    assert any("Insufficient" in line for line in technical_summary(packet))
    client = Mock()
    client.chat.completions.create.return_value = response_for(packet)
    monkeypatch.setattr(agent, "build_openai_client", lambda *a, **k: client)
    with pytest.raises(ValueError, match="unavailable"):
        agent.analyze_technical(packet, "synthetic", "gpt-5")


def test_agent_rejects_truncated_generation_and_missing_key_without_call(monkeypatch):
    packet = packet_for_test()
    client = Mock()
    response = response_for(packet)
    response.choices[0].finish_reason = "length"
    client.chat.completions.create.return_value = response
    build = Mock(return_value=client)
    monkeypatch.setattr(agent, "build_openai_client", build)
    with pytest.raises(ValueError, match="incomplete"):
        agent.analyze_technical(packet, "synthetic", "gpt-5")
    build.reset_mock()
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        agent.analyze_technical(packet, "", "gpt-5")
    build.assert_not_called()


@pytest.mark.parametrize("surface", ["market", "company"])
def test_all_eight_introduction_ranges_preserve_narrative_and_do_not_call_models(monkeypatch, surface):
    from datetime import datetime, timezone
    from langgraphagenticai.ui import introduction_tab
    requested = []
    def load(*args):
        period = args[1] if surface == "market" else args[2]
        requested.append(period)
        return chart_data(period)
    monkeypatch.setattr(introduction_tab, "load_market_chart", load)
    monkeypatch.setattr(introduction_tab, "load_symbol_history", load)
    monkeypatch.setattr(introduction_tab, "load_market_overview", lambda *args: {
        "indexes": {"S&P 500": {"price": 100, "percent": 0}}, "sectors": {}, "cross_assets": {}, "movers": [],
        "as_of": datetime.now(timezone.utc), "fetched_at": datetime.now(timezone.utc), "warnings": []})
    snapshot = {"symbol": "AAPL", "company": "Apple", "quote": {"price": 100}, "fundamentals": {},
                "profile": {"currency": "USD"}, "news": [], "providers": ["Synthetic"], "fetched_at": "2026-02-10", "performance": {}}
    monkeypatch.setattr(introduction_tab, "load_company_snapshot", lambda *args: snapshot)
    def paid(*a, **k):
        pytest.fail("Ordinary range/settings controls must not call models")
    monkeypatch.setattr(introduction_tab, "generate_company_summary", paid)
    monkeypatch.setattr(technical_chart, "analyze_technical", paid)
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab(openai_api_key='synthetic')")
    if surface == "company":
        app.session_state["intro_company_symbol"] = "AAPL"
        app.session_state["intro_summary:AAPL:gpt-5"] = "Existing saved company narrative"
    app.run(timeout=30)
    assert not app.exception
    for period in history.RANGES:
        app.get("button_group")[-1].set_value(period).run(timeout=30)
        assert not app.exception and requested[-1] == period
    if surface == "company":
        assert any("Existing saved company narrative" in item.value for item in app.markdown)


def test_explicit_ai_action_and_saved_result_invalidation(monkeypatch):
    calls = []
    def analyze(packet, key, model):
        calls.append(packet)
        return json.loads(response_for(packet).choices[0].message.content)
    monkeypatch.setattr(technical_chart, "analyze_technical", analyze)
    script = "from langgraphagenticai.ui.technical_chart import render_technical_chart\nfrom tests_placeholder import chart_data\nrender_technical_chart(chart_data(), key='chart', openai_api_key='synthetic')"
    # Supply the fixture through a temporary in-memory module, never a live provider.
    import sys
    monkeypatch.setitem(sys.modules, "tests_placeholder", SimpleNamespace(chart_data=chart_data))
    app = AppTest.from_string(script).run(timeout=30)
    assert not app.exception and calls == []
    app.number_input(key="chart_sma").set_value(30).run()
    assert not app.exception and calls == []
    app.button(key="chart_analyze").click().run()
    assert not app.exception and len(calls) == 1
    app.number_input(key="chart_sma").set_value(31).run()
    assert len(calls) == 1 and any("earlier chart" in item.value for item in app.warning)
    monkeypatch.setattr(technical_chart, "analyze_technical", lambda *a: (_ for _ in ()).throw(ValueError("offline failure")))
    app.button(key="chart_analyze").click().run()
    assert not app.exception and app.session_state["technical_ai:chart"]["fingerprint"] == calls[0]["fingerprint"]


def test_invalid_macd_configuration_disables_ai_and_preserves_prices(monkeypatch):
    import sys
    rendered = []
    render_charts = technical_chart.render_indicator_charts
    def render(frame, period, unit):
        rendered.append(frame.copy())
        return render_charts(frame, period, unit)
    monkeypatch.setattr(technical_chart, "render_indicator_charts", render)
    monkeypatch.setitem(sys.modules, "tests_placeholder", SimpleNamespace(chart_data=chart_data))
    monkeypatch.setattr(technical_chart, "analyze_technical", lambda *a: pytest.fail("Invalid settings must not call AI"))
    app = AppTest.from_string("from langgraphagenticai.ui.technical_chart import render_technical_chart\nfrom tests_placeholder import chart_data\nrender_technical_chart(chart_data(), key='invalid', openai_api_key='synthetic')").run(timeout=30)
    app.multiselect(key="invalid_indicators").set_value(["MACD"]).run()
    app.number_input(key="invalid_macd_fast").set_value(40).run()
    assert not app.exception and app.error
    assert app.button(key="invalid_analyze").disabled
    assert rendered[-1].Close.tolist() == list(range(100, 140))
    assert "MACD" not in rendered[-1]
