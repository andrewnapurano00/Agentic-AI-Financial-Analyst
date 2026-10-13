"""Existing Equity Report feeds must reach the company terminal without guesses."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from langgraphagenticai.analysis.company_terminal import build_metrics, analyst_summary, forward_estimate, quarters
from langgraphagenticai.providers import company_terminal, discovery
from langgraphagenticai.ui import opening_presentation


def saved(api, variant="default"):
    path = Path(__file__).resolve().parents[1] / "fmp_data_reference/samples" / api / "20261003T044241108241Z" / f"AAPL-{variant}.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def snapshot():
    return {"symbol": "AAPL", "profile": {"currency": "USD"}, "quote": {"price": 100, "currency": "USD"},
            "fetched_at": "2026-10-13T12:00:00Z", "terminal_evidence": {
                "income": saved("FMP-061", "quarter"), "cashflow": saved("FMP-065", "quarter"),
                "metrics": saved("FMP-075")[0], "ratios": saved("FMP-077")[0]}}


def test_recorded_existing_feeds_reach_selected_and_peer_panels(monkeypatch):
    calls = []
    routes = {"analyst-estimates": "FMP-031", "price-target-consensus": "FMP-094", "grades-consensus": "FMP-098",
              "stock-peers": "FMP-035", "earnings": "FMP-123", "ratios-ttm": "FMP-077", "key-metrics-ttm": "FMP-075"}
    def request(route, symbol, key, **params):
        calls.append((route, symbol, params))
        payload = saved("FMP-061", params["period"]) if route == "income-statement" else saved(routes[route])
        return payload if route == "stock-peers" else [{**row, "symbol": symbol} for row in payload]
    monkeypatch.setattr(company_terminal, "_request", request)
    monkeypatch.setattr(company_terminal, "load_terminal_evidence", company_terminal.load_terminal_evidence.__wrapped__)
    result = company_terminal.load_company_terminal("AAPL", "synthetic", snapshot())
    metrics = result["metrics"]
    assert metrics["roe"]["value"] == pytest.approx(1.3718365457766524)  # 137.2%, not 1.37%
    assert metrics["roic"]["value"] == pytest.approx(.5186736691216669)
    assert metrics["roa"]["value"] == pytest.approx(.3363982195133406)
    assert metrics["dividend_yield"]["value"] == pytest.approx(.0031766)
    expected = forward_estimate(saved("FMP-031"))
    assert metrics["pe_forward"]["value"] == pytest.approx(100 / expected["eps"])
    assert metrics["pe_forward"]["as_of"] == expected["date"]
    assert result["analyst"]["consensus"] == "Buy" and result["analyst"]["target"] == 341.68
    assert result["analyst"]["upside"] == pytest.approx(2.4168)
    assert result["analyst"]["count"] == expected["analysts"]
    assert all(peer["metrics"]["pe_ttm"]["value"] is not None and peer["metrics"]["roic"]["value"] is not None for peer in result["peers"])
    assert len(calls) == 18
    assert ("analyst-estimates", "AAPL", {"period": "annual", "limit": 12, "page": 0}) in calls


def test_forward_selects_next_future_annual_period_never_stale_or_invalid_eps():
    rows = [{"date": "2025-12-31", "epsAvg": 1}, {"date": "2028-12-31", "epsAvg": 8},
            {"date": "2027-12-31", "estimatedEpsAvg": 4, "numAnalystsEps": 12}]
    assert forward_estimate(rows, date(2026, 10, 13))["eps"] == 4
    assert forward_estimate(rows[:1], date(2026, 10, 13)) == {}
    for eps in (0, -1, True, float("inf"), None):
        estimates = [{"date": "2090-12-31", "epsAvg": eps}]
        assert build_metrics(snapshot(), estimates=estimates)["pe_forward"]["value"] is None
    estimates = [{"date": "2090-12-31", "epsAvg": 4, "currency": "EUR"}]
    assert build_metrics(snapshot(), estimates=estimates)["pe_forward"]["value"] is None
    estimates[0].pop("currency")
    item = build_metrics(snapshot(), estimates=estimates)["pe_forward"]
    assert item["value"] == 25 and "Assumes EPS" in item["note"]


def test_estimate_count_not_rating_count_and_explicit_target_currency_mismatch():
    evidence = {"estimates": [{"date": "2090-12-31", "epsAvg": 4, "numAnalystsEps": 0}],
                "grades": {"consensus": "Buy", "buy": 99}, "targets": {"targetConsensus": 120, "currency": "EUR"}}
    result = analyst_summary(snapshot(), evidence)
    assert result["count"] == 0 and result["target"] == 120 and result["upside"] is None
    evidence["targets"].pop("currency")
    assert analyst_summary(snapshot(), evidence)["upside"] == pytest.approx(.2)


def test_aliases_preserve_zero_legacy_year_and_reject_nonfinite():
    data = snapshot()
    data["terminal_evidence"]["ratios"] = {"peRatioTTM": 0, "pbRatioTTM": "2", "dividendYieldTTM": 0}
    data["terminal_evidence"]["metrics"] = {"roicTTM": 1.2, "returnOnEquityTTM": float("nan")}
    metrics = build_metrics(data)
    assert metrics["pe_ttm"]["value"] == 0 and metrics["price_to_book"]["value"] == 2
    assert metrics["dividend_yield"]["value"] == 0 and metrics["roic"]["value"] == 1.2 and metrics["roe"]["value"] is None
    rows = deepcopy(data["terminal_evidence"]["income"])
    for row in rows:
        row["calendarYear"] = row.pop("fiscalYear")
    assert len(quarters(rows, 8)) == 8


def test_provider_margin_fallback_is_available_and_explicitly_distinct():
    data = snapshot()
    data["terminal_evidence"]["income"] = []
    metrics = build_metrics(data)
    assert metrics["gross_margin"]["value"] == pytest.approx(.4865291555900202)
    assert "Provider TTM fallback" in metrics["gross_margin"]["basis"]
    assert metrics["gross_margin"]["as_of"] is None and metrics["revenue_growth"]["value"] is None
    assert metrics["gross_margin"]["inputs"] == []  # Never label this as the audited four quarters.
    assert metrics["market_cap"]["currency"] == "USD"
    assert metrics["enterprise_value"]["currency"] is None and metrics["enterprise_value"]["listing_currency"] == "USD"


def test_header_displays_real_analyst_values_and_escapes_provider_strings(monkeypatch):
    rendered = []
    monkeypatch.setattr(opening_presentation.st, "markdown", lambda text, **kw: rendered.append(text))
    opening_presentation.quote_header("AAPL", "Apple", "Technology", {"price": 100}, analyst={
        "consensus": "<script>bad</script>", "count": 12, "target": 120, "upside": .2, "estimate_date": "2027-09-30"})
    text = rendered[0]
    assert "EPS analysts: 12" in text and "Price target: 120.00" in text and "+20.00%" in text
    assert "<script>" not in text and "&lt;script&gt;" in text


def test_movers_accepts_stable_quote_percent_alias_without_extra_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(discovery, "_get", lambda *a, **kw: calls.append(a) or [{"symbol": "AAPL", "price": 100, "changePercentage": 0}])
    result = discovery.load_selected_quote.__wrapped__("AAPL", "synthetic")
    assert result["change_pct"] == 0 and len(calls) == 1
