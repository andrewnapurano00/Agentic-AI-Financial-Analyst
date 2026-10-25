"""AX-05: explicit historical gate, saved policy, units and unknown exposure."""
import json
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate, PortfolioRecommendation
from langgraphagenticai.portfolio_architect.research import demo_snapshot
from langgraphagenticai.portfolio_architect.universe import eligible_names
from langgraphagenticai.portfolio_architect.workflow import build
from langgraphagenticai.portfolio_architect.risk_policy import check_volatility, stress_loss, policy_summary
from langgraphagenticai.portfolio_architect.export import json_bytes


def fixture():
    m = InvestorMandate(objective="Build a diversified research portfolio", method="equal")
    s = demo_snapshot(eligible_names(m), m.benchmark)
    return m, s


def test_policy_export_legacy_and_unknowns():
    m, s = fixture()
    r = build(s, m)
    p = r.risk_policy
    assert all(c["passed"] for c in p["checks"])
    assert sum(h.weight for h in r.holdings)+r.cash == pytest.approx(1, abs=1e-9)
    assert all(h.weight <= m.position_cap+1e-9 for h in r.holdings)
    assert all(v <= m.sector_cap+1e-9 for v in r.sectors.values())
    assert p["benchmark_relative_weights"]["weights"] is None
    assert p["turnover_and_transaction_costs"]["value"] is None
    assert p["etf_look_through"]["exposure"] is None
    assert json.loads(json_bytes(r))["risk_policy"] == p
    old = r.model_dump()
    old.pop("risk_policy")
    old["mandate"].pop("historical_volatility_cap")
    assert PortfolioRecommendation.model_validate(old).risk_policy == {}
    scenario = p["stress_scenarios"][0]
    assert scenario["account_return"] == pytest.approx(-.2*(1-r.cash))
    assert scenario["account_change_usd"] == pytest.approx(scenario["account_return"]*m.amount)


@pytest.mark.parametrize("cap", [0, -1, 1.01, float("nan"), float("inf")])
def test_invalid_ceiling(cap):
    with pytest.raises(ValueError):
        InvestorMandate(objective="A diversified portfolio", historical_volatility_cap=cap)


def test_ceiling_rejects_before_paid_review_and_never_relaxes(monkeypatch):
    m, s = fixture()
    m = m.model_copy(update={"historical_volatility_cap":.01})
    review = Mock(side_effect=AssertionError("No paid review on failed local policy"))
    monkeypatch.setattr("langgraphagenticai.portfolio_architect.workflow.review", review)
    with pytest.raises(ValueError, match="ceiling exceeded"):
        build(s, m, use_ai=True)
    review.assert_not_called()
    assert m.cash == .1 and m.historical_volatility_cap == .01


def test_permissive_ceiling_saved_and_sparse_stale_future_blocked():
    m, s = fixture()
    m = m.model_copy(update={"historical_volatility_cap":1.})
    r = build(s, m)
    assert r.risk_policy["checks"][-1]["actual"] == r.risk.annualized_volatility
    securities = [next(v for v in s.securities if v.ticker == h.ticker) for h in r.holdings]
    weights = {h.ticker:h.weight for h in r.holdings}
    for change in ({"history":{}}, {"history_retrieved_at":"2020-01-01T00:00:00+00:00"},
                   {"history_retrieved_at":"2099-01-01T00:00:00+00:00"},
                   {"history_retrieved_at":"2026-10-19"}):
        altered = [securities[0].model_copy(update=change)]+securities[1:]
        with pytest.raises(ValueError, match="cannot be checked"):
            check_volatility(altered, weights, m, s)
    old = s.model_copy(update={"retrieved_at":"2027-01-01T00:00:00+00:00"})
    with pytest.raises(ValueError, match="cannot be checked"):
        check_volatility(securities, weights, m, old)


def test_correlated_stress_cash_and_bad_units():
    m, s = fixture()
    securities = s.securities[:2]
    weights = {v.ticker:.2 for v in securities}
    assert stress_loss(securities, weights, .6, {v.ticker:-1. for v in securities}) == pytest.approx(-.4)
    assert stress_loss(securities, weights, .6, {v.ticker:.1 for v in securities}) == pytest.approx(.04)
    for shocks in ({}, {v.ticker:-20. for v in securities}, {v.ticker:float("nan") for v in securities}):
        with pytest.raises(ValueError):
            stress_loss(securities, weights, .6, shocks)


def test_ui_failed_policy_keeps_saved_portfolio(monkeypatch):
    from langgraphagenticai.ui import portfolio_architect_tab as ui
    m, s = fixture()
    # Perfectly correlated synthetic histories make the 1% ceiling infeasible.
    for security in s.securities:
        security.history = dict(s.securities[0].history)
    provider = Mock(return_value=s)
    monkeypatch.setattr(ui, "collect", provider)
    app = AppTest.from_string("from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect; render_portfolio_architect(fmp_api_key='fixture')", default_timeout=30).run()
    app.button(key="architect_interpret").click().run()
    next(b for b in app.button if b.label == "Build portfolio").click().run()
    assert not app.exception
    saved = app.session_state["architect_result"]
    app.checkbox(key="architect_edit_1_vol_enabled").check()
    app.number_input(key="architect_edit_1_vol_cap").set_value(1.)
    next(b for b in app.button if b.label == "Build portfolio").click().run()
    assert not app.exception
    assert app.session_state["architect_result"] == saved
    assert any("ceiling exceeded" in e.value for e in app.error)
    assert provider.call_count == 2


def test_concentration_and_etf_exposure_are_disclosed():
    m, s = fixture()
    m = m.model_copy(update={"holdings":5, "cash":0., "sector_cap":1., "position_cap":.3, "assets":"etfs"})
    r = build(s, m)
    assert r.risk_policy["warnings"]
    assert r.risk_policy["etf_look_through"]["status"] == "unknown"
    securities = [next(v for v in s.securities if v.ticker == h.ticker) for h in r.holdings]
    weights = {h.ticker:h.weight for h in r.holdings}
    forbidden = m.model_copy(update={"forbidden":[r.holdings[0].ticker]})
    with pytest.raises(ValueError, match="exclusions"):
        policy_summary(securities, weights, r.cash, forbidden, s)
