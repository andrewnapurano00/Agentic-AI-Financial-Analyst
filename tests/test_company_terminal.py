"""D01-D13: recorded FMP contracts + independent numeric/state edge cases."""
from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.analysis.company_terminal import (annual_cagr, build_metrics, compatible_peer_metrics, earnings_events,
                                                         finite, matching_rows, quarters)
from langgraphagenticai.providers import company_terminal as provider, symbol_history
from langgraphagenticai.ui import company_snapshot, introduction_tab
from langgraphagenticai.ui.opening_presentation import metric_value, opening_price_chart
from langgraphagenticai.ui.top_movers_tab import ranked_display

REFERENCE = Path(__file__).resolve().parents[1] / "fmp_data_reference" / "samples"


def saved(api, variant="default"):
    return json.loads((REFERENCE / api / "20261003T044241108241Z" / f"AAPL-{variant}.json").read_text(encoding="utf-8-sig"))


def quarter_rows():
    rows = []
    for year in (2025, 2024):
        for quarter in (4, 3, 2, 1):
            rows.append({"symbol": "AAPL", "date": f"{year}-{quarter*3:02d}-" + ("31" if quarter in (1,4) else "30"),
                         "fiscalYear": str(year), "period": f"Q{quarter}", "reportedCurrency": "USD",
                         "revenue": 100 if year == 2025 else 80, "grossProfit": 45, "operatingIncome": 25,
                         "netIncome": 10, "freeCashFlow": 20, "filingDate": f"{year+1}-01-31"})
    return rows


def snapshot():
    rows = quarter_rows()
    return {"symbol": "AAPL", "company": "Apple", "profile": {"currency": "USD", "beta": 0},
            "quote": {"price": 100, "market_cap": 0, "currency": None, "volume": 0}, "fetched_at": "2026-10-12T12:00:00Z",
            "fundamentals": {}, "news": [], "providers": ["Synthetic"], "performance": {},
            "terminal_evidence": {"income": rows, "cashflow": rows[:4], "ratios": saved("FMP-077")[0], "metrics": saved("FMP-075")[0]}}


@pytest.mark.parametrize("value", [True, False, float("inf"), float("-inf"), float("nan"), None, "bad"])
def test_nonfinancial_values_rejected(value):
    assert finite(value) is None
    assert company_snapshot._number({"value": value}, "value") is None


def test_zero_and_identity_preserved():
    assert finite(0) == 0
    assert matching_rows([{"symbol": "MSFT", "price": 9}, {"symbol": "aapl", "price": 0}], "AAPL") == [{"symbol": "aapl", "price": 0}]
    assert company_snapshot._first({"_error": "failed"}, "AAPL") == {}
    assert company_snapshot._first([{"symbol": "MSFT"}], "AAPL") == {}
    with pytest.raises(ValueError):
        company_snapshot.normalize_symbol("AA/PL")


def test_calculated_percentages_are_fractions_and_match_fiscal_windows():
    metrics = build_metrics(snapshot())
    assert metrics["revenue_growth"]["value"] == pytest.approx(.25)
    assert metrics["gross_margin"]["value"] == pytest.approx(.45)
    assert metrics["operating_margin"]["value"] == pytest.approx(.25)
    assert metrics["net_margin"]["value"] == pytest.approx(.10)
    assert metrics["fcf_margin"]["value"] == pytest.approx(.20)
    assert metric_value("gross_margin", metrics["gross_margin"]) == "45.0%"
    assert metrics["market_cap"]["value"] == 0 and metrics["beta"]["value"] == 0
    assert metrics["market_cap"]["currency"] is None  # profile USD cannot certify quote USD
    bad = snapshot()
    bad["terminal_evidence"]["cashflow"][0] = {**bad["terminal_evidence"]["cashflow"][0], "date": "2025-12-30"}
    assert build_metrics(bad)["fcf_margin"]["value"] is None
    bad["terminal_evidence"]["cashflow"] = quarter_rows()[:4]
    bad["terminal_evidence"]["cashflow"][0]["reportedCurrency"] = "EUR"
    assert build_metrics(bad)["fcf_margin"]["value"] is None


def test_partial_prior_preserves_latest_ttm_and_nonpositive_revenue_withheld():
    data = snapshot()
    data["terminal_evidence"]["income"].pop(5)
    metrics = build_metrics(data)
    assert metrics["gross_margin"]["value"] == .45
    assert metrics["revenue_growth"]["value"] is None
    for row in data["terminal_evidence"]["income"]:
        row["revenue"] = -100
    assert build_metrics(data)["gross_margin"]["value"] is None
    conflicting_prior = snapshot()
    conflicting_prior["terminal_evidence"]["income"].append({**quarter_rows()[7], "revenue": 99})
    metrics = build_metrics(conflicting_prior)
    assert metrics["gross_margin"]["value"] == .45 and metrics["revenue_growth"]["value"] is None


def test_documented_fmp_percentage_fields_are_fractions_not_magnitude_guesses():
    data = snapshot()
    for raw in (.01, 1, 100):
        data["terminal_evidence"]["metrics"]["returnOnEquityTTM"] = raw
        metrics = build_metrics(data)
        assert metrics["roe"]["value"] == raw and metrics["roe"]["raw"] == raw
        assert metrics["roic"]["value"] == pytest.approx(.5186736691216669)
        assert metrics["dividend_yield"]["value"] == pytest.approx(.0031766)
        assert metric_value("roe", metrics["roe"]) == f"{raw*100:,.1f}%"
    assert metrics["roe"]["fields"] == ["returnOnEquityTTM"]
    assert metrics["pe_forward"]["value"] is None
    assert metrics["enterprise_value"]["value"] == 4945786823640
    assert metrics["ev_ebitda"]["value"] == pytest.approx(29.354289517467326)


def test_annual_cagr_requires_n_plus_one_positive_consecutive_same_currency_years():
    rows = [{"symbol": "AAPL", "date": f"{year}-12-31", "fiscalYear": year, "period": "FY", "reportedCurrency": "USD", "revenue": 100 * 2 ** (year - 2020)} for year in range(2020, 2026)]
    assert annual_cagr(rows, 3)[0] == pytest.approx(1)
    assert annual_cagr(rows, 5)[0] == pytest.approx(1)
    assert annual_cagr(rows[1:], 5)[0] is None
    for change in ({"revenue": 0}, {"revenue": -1}, {"revenue": True}, {"reportedCurrency": "EUR"}):
        bad = deepcopy(rows)
        bad[-1].update(change)
        assert annual_cagr(bad, 3)[0] is None
    assert annual_cagr(rows[:2] + rows[3:], 5)[0] is None
    assert annual_cagr(saved("FMP-061", "annual"), 3)[0] is not None
    assert annual_cagr(saved("FMP-061", "annual"), 5)[0] is None


def test_quarter_conflicts_future_currency_and_missing_reject():
    rows = quarter_rows()
    assert len(quarters(rows, 4)) == 4
    assert quarters(rows + [{**rows[0], "revenue": 5}], 4) == []
    bad = deepcopy(rows[:4])
    bad[0]["reportedCurrency"] = ""
    assert quarters(bad, 4) == []
    bad[0].update(date="2099-12-31", fiscalYear="2099")
    assert len(quarters(bad, 4)) < 4


def test_recorded_earnings_labels_actual_estimate_and_signed_surprise():
    events = earnings_events(saved("FMP-123"), date(2026, 10, 12))
    assert len(events["reported"]) == 4
    assert events["next_event"]["date"] == "2026-10-29"
    assert events["reported"][0]["surprise"] == pytest.approx((2.02 - 1.89) / 1.89)
    assert "Announcement dates" in events["basis"]
    edges = earnings_events([{"date": "2025-01-01", "epsActual": 0, "epsEstimated": None},
                              {"date": "2025-02-01", "epsActual": -1, "epsEstimated": -2},
                              {"date": "2025-03-01", "epsActual": 2, "epsEstimated": 0}], date(2026, 10, 12))["reported"]
    assert edges[0]["surprise"] is None
    assert edges[1]["surprise"] == .5 and edges[1]["comparison"] == "Beat"
    assert edges[2]["actual"] == 0 and edges[2]["estimate"] is None and edges[2]["surprise"] is None


def test_peer_period_differences_are_disclosed_without_erasing_valid_ratios():
    selected = build_metrics(snapshot())
    peer = deepcopy(selected)
    assert compatible_peer_metrics(selected, peer)["gross_margin"]["value"] == .45
    peer["gross_margin"]["as_of"] = "2025-09-30"
    peer["operating_margin"]["currency"] = "EUR"
    result = compatible_peer_metrics(selected, peer)
    assert result["gross_margin"]["value"] == .45 and result["operating_margin"]["value"] == .25
    assert "dates/currencies/bases differ" in result["gross_margin"]["note"]
    assert result["pe_ttm"]["value"] == selected["pe_ttm"]["value"] and result["roic"]["value"] == selected["roic"]["value"]
    assert "Not a same-date" in result["roic"]["note"]


def test_provider_saved_routes_bounded_peer_identity_and_partial_failure(monkeypatch):
    calls = []
    def request(route, symbol, api_key, **params):
        calls.append((route, symbol, params))
        if route == "stock-peers":
            return saved("FMP-035") + [{"symbol": "GOOGL"}, {"symbol": "AAPL"}, {"symbol": "bad/ticker"}]
        if route == "earnings":
            return saved("FMP-123") + [{"symbol": "MSFT", "date": "2026-01-01", "epsActual": 999}]
        if route == "income-statement" and params.get("period") == "annual":
            return saved("FMP-061", "annual")
        if symbol == "META":
            raise RuntimeError("Synthetic peer failure")
        if route == "income-statement":
            return [{**row, "symbol": symbol} for row in quarter_rows()]
        return [{"symbol": "OTHER", "priceToEarningsRatioTTM": 999}]
    monkeypatch.setattr(provider, "_request", request)
    result = provider.load_terminal_evidence.__wrapped__("aapl", "test")
    assert len(calls) == 18 and len(result["peers"]) == 4
    assert {row["symbol"] for row in result["peers"]} == {"GOOGL", "META", "MSFT", "NVDA"}
    assert next(row for row in result["peers"] if row["symbol"] == "META")["terminal_evidence"]["income"] == []
    assert all(row["symbol"] == "AAPL" for row in result["earnings"])
    assert ("earnings", "AAPL", {}) in calls
    assert ("income-statement", "AAPL", {"period": "annual", "limit": 6}) in calls
    assert result["annual"] and result["earnings"] and result["warnings"]
    assert all(not row["terminal_evidence"]["ratios"] for row in result["peers"])


def test_extension_no_key_never_dispatches_and_mismatched_snapshot_rejected(monkeypatch):
    monkeypatch.setattr(provider, "_request", lambda *a, **k: pytest.fail("No key must never collect"))
    result = provider.load_terminal_evidence.__wrapped__("AAPL", "")
    assert result["retrieved_at"] is None and result["warnings"]
    with pytest.raises(ValueError):
        provider.load_company_terminal("MSFT", "", snapshot())


def test_snapshot_identity_errors_currency_and_nonfinite_fields(monkeypatch):
    def get(url, api_key, **params):
        if "/profile/" in url:
            return [{"symbol": "MSFT", "companyName": "Wrong"}, {"symbol": "AAPL", "companyName": "Apple", "currency": "USD", "averageVolume": 4}]
        if "/quote/" in url:
            return [{"symbol": "MSFT", "price": 999}, {"symbol": "AAPL", "price": float("inf"), "changesPercentage": 0}]
        if "income-statement" in url or "cash-flow-statement" in url:
            return quarter_rows()
        if "ratios" in url:
            return saved("FMP-077")
        if "key-metrics" in url:
            return saved("FMP-075")
        return {"symbol": "WRONG", "historical": [{"date": "2025-01-01", "close": 999}]}
    monkeypatch.setattr(company_snapshot, "_get", get)
    monkeypatch.setattr(company_snapshot, "fetch_recent_news", lambda *a, **k: pd.DataFrame())
    result = company_snapshot.load_company_snapshot.__wrapped__("AAPL", "test")
    assert result["company"] == "Apple" and result["quote"]["price"] is None
    assert result["profile"]["currency"] == "USD" and result["quote"]["currency"] is None
    assert result["quote"]["change_pct"] == 0 and result["quote"]["avg_volume"] == 4
    assert result["quote"]["avg_volume_source"] == "profile.averageVolume"
    metrics = build_metrics(result)
    assert metrics["avg_volume"]["as_of"] is None and metrics["avg_volume"]["fields"] == ["profile.averageVolume"]
    for invalid_timestamp in (True, float("inf"), float("nan"), 1e100, -1, 9999999999):
        assert company_snapshot._quote_timestamp(invalid_timestamp) is None
    assert result["performance"]["series"] == [] and result["fundamentals"]["roic"] == pytest.approx(.5186736691216669)
    monkeypatch.setattr(company_snapshot, "_get", lambda *a, **k: {"_error": "synthetic"})
    with pytest.raises(ValueError):
        company_snapshot.load_company_snapshot.__wrapped__("AAPL", "test")


def test_new_ranges_ytd_calendar_anchor_and_bounded_all(monkeypatch):
    monkeypatch.setattr(symbol_history, "_utc_now", lambda: datetime(2026, 10, 12, tzinfo=timezone.utc))
    history = [(pd.Timestamp(day), value) for day, value in (("2025-12-31", 100), ("2026-01-02", 101), ("2026-04-01", 102), ("2026-09-30", 103))]
    visible, _, _ = symbol_history.select_history(history, "YTD")
    assert [price for _, price in visible] == [101, 102, 103]
    assert [price for _, price in symbol_history.select_history(history, "6M")[0]] == [102, 103]
    monkeypatch.setattr(symbol_history, "_daily_history", lambda *a: {"history": history, "warnings": [], "provider": "Synthetic"})
    result = symbol_history.load_symbol_history("AAPL", "", "All")
    assert len(result["points"]) == 4 and "bounded to ten years" in result["warnings"][0]
    old = [(pd.Timestamp("2025-12-31"), 1)]
    assert symbol_history.select_history(old, "YTD")[0] == []


def test_red_price_area_preserves_finite_domain_source_timestamp_and_interaction():
    from langgraphagenticai.ui.technical_chart import price_chart_spec
    frame = pd.DataFrame({"Date": pd.date_range("2026-01-01", periods=2, tz="America/New_York"), "Close": [100., 101.]})
    original = price_chart_spec(frame, "1M", "Unknown currency").to_dict()
    spec = opening_price_chart(frame, "1M", "Unknown currency", height=385).to_dict()
    assert spec["layer"][0]["mark"]["type"] == "area" and spec["layer"][1]["mark"]["type"] == "line"
    for layer in spec["layer"]:
        assert layer["encoding"]["y"]["scale"]["domain"] == original["encoding"]["y"]["scale"]["domain"]
        assert layer["encoding"]["tooltip"] == original["encoding"]["tooltip"]
    assert spec["datasets"] == original["datasets"] and spec["params"]


def test_ranked_table_no_duplicate_daily_and_missing_never_zero():
    rows = pd.DataFrame([{"symbol": "AAPL", "1D": 0, "5D": -1, "price": True, "volume": float("inf")}, {"symbol": "MSFT", "1D": 2, "5D": 3}])
    daily = ranked_display(rows, "1D")
    assert list(daily.columns).count("1D change (%)") == 1
    assert daily["1D change (%)"].tolist() == [0, 2]
    assert pd.isna(daily.iloc[0]["Last Price"]) and pd.isna(daily.iloc[0]["Volume"])
    assert "5D change (%)" in ranked_display(rows, "5D")
    assert daily["Rank"].tolist() == [1, 2]


def test_market_chart_preserves_legacy_company_result_without_rendering_analysis(market_dashboard_stub):
    ui, packet, calls = market_dashboard_stub
    app = AppTest.from_string("from langgraphagenticai.ui.introduction_tab import render_introduction_tab\nrender_introduction_tab()", default_timeout=30)
    app.session_state["intro_summary:AAPL:gpt-5"] = "Saved interpretation"
    app.session_state["market_chart_symbol"] = "AAPL"
    app.run(timeout=30)
    app.button(key="intro_refresh").click().run()
    for period in ("1M", "3M", "1Y"):
        app.get("button_group")[0].set_value(period).run()
        assert not app.exception and calls[-1] == ("AAPL", period)
    assert app.session_state["intro_summary:AAPL:gpt-5"] == "Saved interpretation"
    assert not any("company" in b.label.lower() for b in app.button)


def test_explicit_summary_receives_dated_currency_basis_caveats_and_no_raw_packets(monkeypatch):
    from types import SimpleNamespace
    from langgraphagenticai.analysis.company_terminal import summary_financial_context
    data = snapshot()
    data["fundamental_basis"] = {"period": "TTM", "through": "2025-12-31", "currency": "USD", "status": "partial"}
    data["performance"] = {"as_of": "2026-10-09", "return_1m": .1, "series": [{"date": "2026-10-09", "close": 100}]}
    data["fundamentals"] = {"revenue_ttm": 400, "pe_ttm": 38}
    data["source_errors"] = {"cashflow": "Synthetic partial coverage", "ratios": "https://example.test/?apikey=synthetic-secret"}
    data["terminal_evidence"]["income"] *= 10  # metadata remains bounded despite larger saved packets
    captured = []
    configs = []
    class FakeLLM:
        def __init__(self, config):
            configs.append(config)
        def get_llm_model(self):
            return self
        def invoke(self, messages):
            captured.append(messages)
            return SimpleNamespace(content="Captured dated summary")
    monkeypatch.setattr(company_snapshot, "OpenAILLM", FakeLLM)
    result = company_snapshot.generate_company_summary.__wrapped__(company_snapshot.snapshot_json(data), "test", "test-model")
    assert result == "Captured dated summary" and len(captured) == 1
    system, user = captured[0]
    evidence = json.loads(user.content.split("EVIDENCE:\n", 1)[1])
    assert evidence["fundamental_basis"] == data["fundamental_basis"]
    fields = evidence["fundamental_provenance"]
    assert fields["revenue_ttm"]["period_end"] == "2025-12-31" and fields["revenue_ttm"]["currency"] == "USD"
    assert fields["operating_margin"]["unit"] == "fraction"
    assert fields["pe_ttm"]["period_end"] is None and "undated" in fields["pe_ttm"]["basis"]
    assert "conventions unverified" in fields["pe_ttm"]["assumption"]
    assert evidence["performance_basis"]["as_of"] == "2026-10-09" and "adjustment basis unverified" in evidence["performance_basis"]["price_basis"]
    assert evidence["fetched_at"] == data["fetched_at"] and "retrieval time" in evidence["date_semantics"]
    assert len(evidence["statement_period_metadata"]["income"]) == 8
    assert evidence["statement_period_metadata"]["income"][0]["filingDate"] == "2026-01-31"
    assert evidence["source_errors"]["cashflow"] == "Synthetic partial coverage" and "synthetic-secret" not in user.content
    assert "terminal_evidence" not in evidence and "series" not in evidence["performance"]
    assert "retrieval time" in system.content and "profile metadata" in system.content
    assert configs[0]["timeout"] == 75 and configs[0]["max_retries"] == 1
    # Missing legacy basis stays unknown; context preparation never replaces saved values.
    original_values = dict(data["fundamentals"])
    data.pop("fundamental_basis")
    legacy = summary_financial_context(data)
    assert legacy["fundamental_provenance"]["revenue_ttm"]["basis"] == "Saved financial basis unverified"
    assert data["fundamentals"] == original_values
    assert company_snapshot.generate_company_summary.__wrapped__("{}", "", "test-model").startswith("OpenAI is not configured")
    assert len(captured) == 1
