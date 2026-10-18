"""Energy scenarios are explicitly conditional, never fabricated mid-cycle earnings."""
from datetime import date
import pytest
from test_ai_valuation import evidence, answer
from langgraphagenticai.valuation import model, ai


def energy():
    return evidence("CVX", "Energy")


def prepare(raw):
    return model.prepare(raw, use_disclosed_assumptions=True, dated_projection=True)


def test_energy_conditional_contract_and_exact_dated_arithmetic():
    raw = energy()
    raw["estimates"] = []
    raw["income"][0]["epsDiluted"] = 6.63
    f = prepare(raw)
    assert f["eligible"] and f["conditional_energy"] and f["method"] == "P/E"
    assert any("not validated normalized or mid-cycle" in w for w in f["warnings"])
    result = model.calculate(f, 5, .02, 15)["Base"]
    elapsed = (date.fromisoformat(result["projection"]["target_date"]) - date.fromisoformat(f["as_of"])).days / 365.25
    assert result["target"] == pytest.approx(6.63 * 1.02 ** elapsed * 15)
    assert result["projection"]["kind"] == "historical annual"


def test_energy_packet_discloses_basis_and_validates_all_horizons():
    raw = energy()
    f = prepare(raw)
    packet = ai.evidence_packet(f, raw)
    assert "not validated" in packet["energy_valuation_basis"]
    assert packet["projection_bases"]["5"]["kind"] == "annual consensus forecast"
    view = ai.validate(answer(packet), packet)
    for years in (3, 4, 5):
        cases = model.calculate_ai_cases(f, years, view["scenarios"])
        assert cases["Bear"]["target"] <= cases["Base"]["target"] <= cases["Bull"]["target"]


@pytest.mark.parametrize("edit", [
    lambda r: r["income"][0].update(epsDiluted=0),
    lambda r: r["income"][0].update(netIncome=-1),
    lambda r: r["quote"][0].update(currency="EUR"),
    lambda r: r["quote"][0].update(timestamp=1),
    lambda r: r["sources"]["income"].update(retrieved_at="2020-01-01T00:00:00Z"),
])
def test_conditional_energy_does_not_bypass_financial_gates(edit):
    raw = energy()
    edit(raw)
    f = prepare(raw)
    assert not f["eligible"]
    with pytest.raises(ValueError):
        model.calculate(f, 5, .02, 15)


def test_strict_energy_and_other_specialist_contracts_remain_blocked():
    assert not model.prepare(energy(), acknowledge_units=True)["eligible"]
    for sector, industry in [("Basic Materials", "Chemicals"), ("Real Estate", "REIT - Retail")]:
        raw = evidence("TEST", sector)
        raw["profile"][0]["industry"] = industry
        assert not model.prepare(raw, acknowledge_units=True)["eligible"]
