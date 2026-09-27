from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from langgraphagenticai.portfolio_manager.constraint_validator import validate_agentic_weights
from langgraphagenticai.ui.company_snapshot import _validated_quarters
from langgraphagenticai.ui.equity_report_tab import parse_tickers as parse_equity_tickers
from langgraphagenticai.ui.portfolio_optimizer_tab import parse_custom_weights, parse_tickers
from langgraphagenticai.utils.safety import redact_sensitive_text, redact_value


def _recommendations() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "ticker": "AAA", "sector": "Technology", "target_weight_proposed": 1.0,
            "current_weight": 1.0, "market_value": 100.0, "shares": 10.0,
            "last_price": 10.0, "final_action": "Hold",
        },
        {
            "ticker": "BBB", "sector": "Technology", "target_weight_proposed": 0.0,
            "current_weight": 0.0, "market_value": 0.0, "shares": 0.0,
            "last_price": 10.0, "final_action": "Add",
        },
        {
            "ticker": "CCC", "sector": "Healthcare", "target_weight_proposed": 0.0,
            "current_weight": 0.0, "market_value": 0.0, "shares": 0.0,
            "last_price": 10.0, "final_action": "Add",
        },
    ])


def test_constraint_validator_never_reintroduces_caps():
    recommendations, _, sectors, diagnostics = validate_agentic_weights(
        _recommendations(), portfolio_value=100.0, max_position_weight=0.4,
        max_sector_weight=0.5, cash_buffer=0.0,
    )
    securities = recommendations[recommendations["ticker"] != "CASH"]
    assert securities["target_weight"].max() <= 0.4 + 1e-9
    assert sectors.loc[sectors["sector"] != "Cash", "target_weight"].max() <= 0.5 + 1e-9
    assert abs(recommendations["target_weight"].fillna(0).sum() - 1.0) <= 1e-9
    assert diagnostics["positions_over_cap_after_validation"] == 0
    assert diagnostics["sectors_over_cap_after_validation"] == 0


def test_secret_redaction_handles_urls_headers_and_nested_values():
    raw = "https://provider.test/x?apikey=secret-value&x=1 Authorization: Bearer sk-example-secret-12345"
    cleaned = redact_sensitive_text(raw)
    assert "secret-value" not in cleaned
    assert "sk-example" not in cleaned
    nested = redact_value({"api_key": "plain-secret", "error": raw})
    assert nested["api_key"] == "[REDACTED]"
    assert "secret-value" not in nested["error"]


def test_ttm_quarters_require_consecutive_unique_quarters_and_currency():
    rows = []
    start = date(2026, 9, 30)
    for index, period in enumerate(("Q3", "Q2", "Q1", "Q4")):
        rows.append({
            "date": (start - timedelta(days=91 * index)).isoformat(),
            "fiscalYear": 2026 if period != "Q4" else 2025,
            "period": period,
            "reportedCurrency": "USD",
            "revenue": 10,
        })
    assert len(_validated_quarters(rows, 4)) == 4
    mixed_currency = [dict(row) for row in rows]
    mixed_currency[1]["reportedCurrency"] = "EUR"
    assert _validated_quarters(mixed_currency, 4) == []
    broken = [dict(row) for row in rows]
    broken[1]["date"] = "2025-01-01"
    assert _validated_quarters(broken, 4) == []


def test_optimizer_rejects_invalid_symbols_and_negative_weights():
    assert parse_tickers("AAPL, MSFT; <script>") == ["AAPL", "MSFT"]
    weights, error = parse_custom_weights("120% -20%", 2)
    assert weights is None
    assert "non-negative" in error
    assert parse_equity_tickers("aapl; MSFT AAPL") == ["AAPL", "MSFT"]
    try:
        parse_equity_tickers("AAPL,<script>")
        assert False, "invalid ticker should fail"
    except ValueError:
        pass


def test_top_movers_reports_partial_batch_coverage(monkeypatch):
    from langgraphagenticai.ui import top_movers_data

    symbols = [f"S{index:03d}" for index in range(81)]
    universe = [
        {
            "symbol": symbol, "companyName": symbol, "sector": "Technology",
            "price": 10.0, "marketCap": 3_000_000_000, "volume": 1_000_000,
            "avgVolume": 1_000_000, "isEtf": False, "isFund": False,
        }
        for symbol in symbols
    ]

    def fake_get(url, _api_key, **_params):
        if "stock-screener" in url:
            return universe
        requested = url.rsplit("/", 1)[-1].split(",")
        if len(requested) == 1:
            raise RuntimeError("batch unavailable")
        return [{"symbol": symbol, "1D": 0.5, "5D": float(index)} for index, symbol in enumerate(requested)]

    monkeypatch.setattr(top_movers_data, "_get", fake_get)
    top_movers_data.load_top_movers.clear()
    result = top_movers_data.load_top_movers("test-key")
    assert result["partial"] is True
    assert result["universe_size"] == 80
    assert result["requested_universe_size"] == 81
    assert result["provider_warnings"]


def test_stock_screener_uses_shared_provider_and_preserves_metadata(monkeypatch):
    from langgraphagenticai.ui import stock_screener_tab

    calls = []

    def fake_get(url, *, api_key, params, timeout):
        calls.append((url, api_key, params, timeout))
        if params["page"] == 0:
            return [{"symbol": "AAPL", "marketCap": 3_000_000_000, "isEtf": False, "isFund": False}]
        return []

    monkeypatch.setattr(stock_screener_tab, "get_fmp_json", fake_get)
    monkeypatch.setattr(stock_screener_tab, "FMP_API_KEY", "test-key")
    stock_screener_tab.fmp_company_screener_safe.clear()
    frame, metadata = stock_screener_tab.fmp_company_screener_safe({"limit": 2}, max_pages=2)
    assert frame["ticker"].tolist() == ["AAPL"]
    assert metadata["pages"] == 1
    assert calls[0][1] == "test-key"
    assert "apikey" not in calls[0][2]
