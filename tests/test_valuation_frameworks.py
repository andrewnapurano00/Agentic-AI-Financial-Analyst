"""All-sector conditional valuation and earnings-proxy contracts."""
from datetime import date, datetime, timezone, timedelta
from copy import deepcopy
import pytest
from streamlit.testing.v1 import AppTest
from test_ai_valuation import evidence, answer, UI
from langgraphagenticai.valuation import model, ai


def prepare(raw):
    return model.prepare(raw, use_disclosed_assumptions=True, dated_projection=True)


@pytest.mark.parametrize("sector", ["Technology", "Communication Services", "Consumer Cyclical", "Consumer Defensive", "Healthcare", "Financial Services", "Industrials", "Energy", "Basic Materials", "Utilities", "Real Estate", ""])
def test_profitable_company_has_framework_in_every_sector(sector):
    raw = evidence("TEST", sector)
    f = prepare(raw)
    assert f["eligible"] and f["method_label"]
    packet = ai.evidence_packet(f, raw)
    view = ai.validate(answer(packet), packet)
    for years in (3, 4, 5):
        result = model.calculate_ai_cases(f, years, view["scenarios"])
        assert 0 < result["Bear"]["target"] <= result["Base"]["target"] <= result["Bull"]["target"]
    assert packet["valuation_framework"]["label"] == f["method_label"]


@pytest.mark.parametrize("sector,term", [("Real Estate", "FFO/AFFO"), ("Basic Materials", "mid-cycle"), ("", "classification"), ("Utilities", "Rate-base")])
def test_provisional_framework_exposes_specific_limitations(sector, term):
    f = prepare(evidence("TEST", sector))
    assert term in f["method_note"]
    assert any(term in warning for warning in f["warnings"])


@pytest.mark.parametrize("edit", [
    lambda r: r["balance"].clear(),
    lambda r: r["balance"].append(dict(r["balance"][0])),
    lambda r: r["balance"][0].update(commonStockSharesOutstanding=None),
    lambda r: r["balance"][0].update(totalStockholdersEquity=-1),
    lambda r: r["sources"]["balance"].update(retrieved_at="2020-01-01T00:00:00Z"),
    lambda r: r["balance"][0].update(reportedCurrency="EUR"),
])
def test_financials_unusable_book_uses_own_valid_earnings(edit):
    raw = evidence("BANK", "Financial Services")
    edit(raw)
    original = deepcopy(raw)
    f = prepare(raw)
    assert f["eligible"] and f["method"] == "P/E" and f["financial_fallback"]
    assert f["basis"] == 5 and f["basis_source_ids"] == ["income:0"]
    assert f["book_value_contract"] == {} and raw == original


def test_earnings_proxy_arithmetic_and_consensus_basis_separation():
    raw = evidence("TEST", "Real Estate")
    for row in raw["income"]:
        row.pop("epsDiluted")
        row.update(netIncome=500, weightedAverageShsOutDil=100)
    f = prepare(raw)
    assert f["eligible"] and f["earnings_proxy"] and f["basis"] == 5
    assert f["estimates"] and not f["forecast_anchor_eligible"]
    assert "net income / annual diluted" in f["formula"]
    packet = ai.evidence_packet(f, raw)
    assert packet["valuation_framework"]["earnings_proxy"]
    ai.validate(answer(packet), packet)
    result = model.calculate(f, 3, .1, 20)["Base"]
    projection = result["projection"]
    elapsed = (date.fromisoformat(projection["target_date"]) - date.fromisoformat(f["as_of"])).days / 365.25
    assert result["target"] == pytest.approx(5 * 1.1 ** elapsed * 20)
    assert projection["kind"] == "historical annual earnings proxy"


@pytest.mark.parametrize("edit", [
    lambda r: r["income"][0].update(netIncome=0, epsDiluted=None),
    lambda r: r["income"][0].update(netIncome=-1),
    lambda r: r["income"][0].update(epsDiluted=-1),
    lambda r: r["income"][0].update(epsDiluted=0),
    lambda r: r["income"][0].update(epsDiluted="invalid"),
    lambda r: r["income"][0].update(epsDiluted=None, weightedAverageShsOutDil=0),
    lambda r: r["income"].clear(),
    lambda r: r["quote"][0].update(currency="EUR"),
    lambda r: r["quote"][0].update(timestamp=1),
    lambda r: r["sources"]["income"].update(retrieved_at="2020-01-01T00:00:00Z"),
])
def test_sector_fallback_never_bypasses_required_evidence(edit):
    raw = evidence("TEST", "Real Estate")
    edit(raw)
    f = prepare(raw)
    assert not f["eligible"]
    with pytest.raises(ValueError):
        model.calculate(f, 3, .1, 20)


@pytest.mark.parametrize("sector", ["Real Estate", "Basic Materials", ""])
def test_provisional_ui_generate_once_horizon_and_rerun_reuse(monkeypatch, sector):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    raw = evidence("TEST", sector)
    calls = {"provider":0, "ai":0}
    def load(*args, **kwargs):
        calls["provider"] += 1
        return raw
    def generate(f, data, *args):
        calls["ai"] += 1
        packet = ai.evidence_packet(f, data)
        return dict(ai=ai.validate(answer(packet), packet), packet=packet, model="gpt-5", generated_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(ui, "load_valuation_evidence", load)
    monkeypatch.setattr(ui, "generate_assumptions", generate)
    app = AppTest.from_string(UI, default_timeout=30)
    app.session_state["valuation_ticker"] = "TEST"
    app.run()
    assert calls == {"provider":0, "ai":0}
    app.button(key="valuation_generate").click().run()
    assert not app.exception and not app.error
    assert any("Provisional earnings P/E" in info.value for info in app.info)
    assert len([m for m in app.metric if "price target" in m.label]) == 3
    app.selectbox(key="valuation_horizon").set_value(3).run()
    app.run()
    assert not app.exception and calls == {"provider":1, "ai":1}
    assert next(iter(app.session_state["valuation_scenarios"].values()))["years"] == 3


def test_ambiguous_required_earnings_do_not_enable_provisional_targets():
    raw = evidence("TEST", "Real Estate")
    raw["income"].append(dict(raw["income"][0]))
    result = prepare(raw)
    assert not result["eligible"] and any("Duplicate income" in reason for reason in result["reasons"])


def test_proxy_history_never_mixes_reported_and_calculated_earnings():
    raw = evidence("TEST", "Technology")
    raw["income"][0].pop("epsDiluted")
    f = prepare(raw)
    assert f["earnings_proxy"] and len(f["history"]) == 1
    packet = ai.evidence_packet(f, raw)
    assert not any(row["id"] == "metric:annual_per_share_growth" for row in packet["evidence"])
