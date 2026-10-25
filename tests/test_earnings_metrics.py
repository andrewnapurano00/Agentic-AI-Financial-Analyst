"""Independent earnings oracles: status, fiscal/currency/source contracts and consumers."""
from copy import deepcopy
from datetime import datetime, timezone
import csv
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis.earnings_metrics import observe_net_income, research_net_income
from langgraphagenticai.analysis.metric_contracts import DEFINITIONS
from langgraphagenticai.deep_research.quarterly_ttm import aggregate, METHODOLOGY

REFERENCE = "2026-10-23T12:00:00+00:00"
RETRIEVED = "2026-10-22T12:00:00+00:00"
ROUTE = "https://financialmodelingprep.com/stable/income-statement"


def quarters():
    return [{"symbol": "AAPL", "date": day, "fiscalYear": year, "period": period,
             "reportedCurrency": "USD", "netIncome": value}
            for day, year, period, value in [("2026-09-30", 2026, "Q3", 30.),
                ("2026-06-30", 2026, "Q2", 20.), ("2026-03-31", 2026, "Q1", 0.),
                ("2025-12-31", 2025, "Q4", -10.)]]


def observe(rows=None, **kwargs):
    return observe_net_income(quarters() if rows is None else rows, "aapl", basis=kwargs.pop("basis", "TTM"),
        source_id="E001", provider="FMP", route=kwargs.pop("route", ROUTE),
        retrieved_at=kwargs.pop("retrieved_at", RETRIEVED), reference_time=kwargs.pop("reference_time", REFERENCE), **kwargs)


def saved_company():
    raw = quarters(); derived = aggregate(raw, "AAPL", ("netIncome",))
    derived["source_records"] = {"category": "income_quarterly", "url": ROUTE, "retrieved_at": RETRIEVED}
    provider = "Calculated from FMP quarterly statements"
    evidence = [{"id": "E001", "symbol": "AAPL", "category": "income_quarterly", "provider": "FMP",
                 "url": ROUTE, "retrieved_at": RETRIEVED, "status": "ok", "data": raw},
                {"id": "E002", "symbol": "AAPL", "category": "income_ttm", "provider": provider,
                 "url": "", "retrieved_at": RETRIEVED, "status": "ok", "data": [derived]}]
    contract = {"value": 40., "unit": "currency", "currency": "USD", "status": "ok",
                "applicability": "applicable", "methodology": METHODOLOGY, "formula": "Four-quarter sum",
                "basis": derived["quarters"], "inputs": [{"source_id": "E002", "category": "income_ttm",
                    "field": "netIncome", "value": 40., "currency": "USD", "currency_basis": "Source-reported currency",
                    "date": derived["date"], "provider": provider, "retrieved_at": RETRIEVED}]}
    return {"id": "earnings-fixture", "financial_methodology": METHODOLOGY,
            "request": {"symbols": ["AAPL"]}, "evidence": evidence,
            "comparison": [{"Ticker": "AAPL", "Net income (TTM)": 40., "TTM through": derived["date"],
                            "TTM currency": "USD", "Metric contracts": {"Net income (TTM)": contract}}]}


def test_independent_oracle_distinct_bases_zero_losses_and_identity():
    before = quarters()
    obs = observe(before)
    assert obs.value == 40 and obs.eligible and obs.origin == "derived" and obs.verification == "reconciled"
    assert len(obs.inputs) == 4 and obs.currency == "USD" and before == quarters()
    assert observe(before, basis="quarterly").value == 30
    annual = [{**before[0], "period": "FY", "netIncome": 77.}]
    assert observe(annual, basis="annual").value == 77
    zero = quarters()
    for row in zero: row["netIncome"] = 0
    assert observe(zero).valid_zero and observe(zero).eligible
    for row in zero: row["netIncome"] = -1
    assert observe(zero).value == -4 and observe(zero).eligible
    stale = observe(before, reference_time="2026-12-01T12:00:00Z")
    assert stale.status == "stale" and stale.value == 40 and stale.identity == obs.identity
    assert "quote" not in obs.to_dict()["scaling"].lower()
    with pytest.raises(TypeError): DEFINITIONS["x"] = DEFINITIONS["net_income.ttm"]


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), "bad"])
def test_missing_component_never_becomes_zero(value):
    rows = quarters(); rows[1]["netIncome"] = value
    obs = observe(rows)
    assert obs.status == "missing" and obs.value is None and not obs.valid_zero
    assert obs.verification == "unverifiable"


@pytest.mark.parametrize("change", [
    lambda r: r.pop(),
    lambda r: r.append({**r[0], "netIncome": 999}),
    lambda r: r[1].update(period="Q3"),
    lambda r: r[0].update(period="FY"),
    lambda r: r[0].update(reportedCurrency="EUR"),
    lambda r: r[0].update(symbol="MSFT"),
    lambda r: r[0].update(date="2026-10-24"),
    lambda r: r[0].update(reportingBasis="YTD"),
    lambda r: r[0].update(startDate="2026-01-01"),
    lambda r: r[0].update(filingDate="2026-11-01"),
    lambda r: r[0].update(acceptedDate="2026-08-01 12:00:00"),
])
def test_invalid_quarters_revisions_duration_and_availability_fail_closed(change):
    rows = quarters(); change(rows)
    obs = observe(rows)
    assert not obs.eligible and obs.verification == "unverifiable"


def test_53_week_calendar_duplicates_and_missing_metadata():
    rows = [{"symbol": "AAPL", "date": day, "fiscalYear": year, "period": period,
             "reportedCurrency": "USD", "netIncome": value} for day, year, period, value in
            [("2023-09-30", 2023, "Q4", 1), ("2023-07-01", 2023, "Q3", 2),
             ("2023-04-01", 2023, "Q2", 3), ("2022-12-31", 2023, "Q1", 4)]]
    obs = observe(rows + [deepcopy(rows[0])], reference_time="2023-11-01T12:00:00Z", retrieved_at="2023-10-31T12:00:00Z")
    assert obs.eligible and obs.value == 10
    missing = quarters(); missing[0].pop("reportedCurrency")
    assert observe(missing).status == "unverifiable"
    scaled = quarters(); scaled[0]["scale"] = 1000000
    assert observe(scaled).status == "unverifiable"
    units = quarters(); units[0]["units"] = "USD millions"
    assert observe(units).status == "unverifiable"
    identity = quarters(); identity[0]["cik"] = "00001"; identity[1]["cik"] = "00002"
    assert observe(identity).status == "inconsistent"
    assert observe(retrieved_at="2026-10-22T12:00:00").status == "unverifiable"
    assert observe(retrieved_at="2026-10-24T12:00:00Z").status == "inconsistent"
    hostile = observe(route=ROUTE + "?apikey=hidden&custom=also-hidden")
    assert hostile.inputs[0].route == ROUTE and "hidden" not in json.dumps(hostile.to_dict())


def test_saved_adapter_reconciles_raw_and_never_replaces_declared_value():
    saved = saved_company(); before = deepcopy(saved)
    obs = research_net_income(saved, "aapl", reference_time=REFERENCE)
    assert obs.eligible and obs.value == 40 and saved == before
    row = saved["comparison"][0]
    row["Net income (TTM)"] = 99; row["Metric contracts"]["Net income (TTM)"]["value"] = 99
    row["Metric contracts"]["Net income (TTM)"]["inputs"][0]["value"] = 99
    saved["evidence"][1]["data"][0]["netIncome"] = 99
    obs = research_net_income(saved, "AAPL", reference_time=REFERENCE)
    assert obs.status == "inconsistent" and obs.value == 99 and not obs.eligible
    assert saved["comparison"][0]["Net income (TTM)"] == 99
    saved = before; saved["evidence"] = saved["evidence"][1:]
    obs = research_net_income(saved, "AAPL", reference_time=REFERENCE)
    assert obs.status == "unverifiable" and obs.value == 40


@pytest.mark.parametrize("ticker", ["AAPL", "JPM", "PLD"])
@pytest.mark.parametrize("basis", ["TTM", "annual", "quarterly"])
def test_dated_fmp_samples_sectors_and_periods(ticker, basis):
    root = Path(__file__).parents[1] / "fmp_data_reference"
    with (root / "coverage_matrix.csv").open(encoding="utf-8", newline="") as stream:
        case = next(r for r in csv.DictReader(stream) if r["api_id"] == "FMP-061" and r["ticker_or_input"] == ticker
                    and r["variant"] == ("annual" if basis == "annual" else "quarter"))
    rows = json.loads((root / case["sample_file"]).read_text(encoding="utf-8"))
    obs = observe_net_income(rows, ticker, basis=basis, source_id="FMP-061-" + ticker,
        provider="FMP", route=case["endpoint"], retrieved_at=case["retrieved_at_utc"],
        reference_time=case["retrieved_at_utc"])
    expected = sum(float(r["netIncome"]) for r in rows[:4]) if basis == "TTM" else float(rows[0]["netIncome"])
    assert obs.eligible, obs.reasons
    assert obs.value == expected and obs.currency == rows[0]["reportedCurrency"]
    assert obs.basis == basis


def test_same_observation_used_for_specialists_and_safe_brief_export():
    from langgraphagenticai.deep_research.specialist_workflow import collect_saved
    from langgraphagenticai.analysis.investment_brief import export_packet
    from langgraphagenticai.analysis.scenarios import SavedInputs
    saved = saved_company()
    observation = research_net_income(saved, "AAPL", reference_time=REFERENCE)
    refs, _ = collect_saved(saved, now=datetime.fromisoformat(REFERENCE))
    ref = next(r for r in refs if r.metric == "Net income (TTM)")
    assert ref.value == observation.value and ref.currency == observation.currency
    packet = export_packet(saved, SavedInputs("AAPL", False, (), reference_time=REFERENCE), [])
    assert packet["earnings_observation"]["identity"] == observation.identity
    assert packet["earnings_observation"]["value"] == 40


def test_real_quality_ui_read_only_states_and_no_network():
    saved = saved_company(); before = deepcopy(saved)
    app = AppTest.from_string('''
import streamlit as st
from langgraphagenticai.ui.earnings_quality import render_earnings_quality
render_earnings_quality(st.session_state.saved,reference_time="2026-10-23T12:00:00+00:00")
''', default_timeout=30)
    app.session_state["saved"] = saved; app.run()
    assert not app.exception
    frame = app.dataframe[0].value
    assert set(frame["Basis"]) == {"quarterly", "annual", "TTM"}
    assert frame.loc[frame["Basis"] == "TTM", "State"].iloc[0] == "available"
    assert frame.loc[frame["Basis"] == "annual", "State"].iloc[0] == "unverifiable"
    app.run()
    assert app.session_state["saved"] == before


def test_no_quote_needed_for_reported_earnings_but_target_prerequisites_fail_closed():
    from langgraphagenticai.analysis.scenarios import saved_inputs
    saved = saved_company()
    assert research_net_income(saved, "AAPL", reference_time=REFERENCE).eligible
    assert not saved_inputs(saved, "AAPL", REFERENCE).eligible


def test_shared_gate_rejects_tampered_raw_earnings_in_otherwise_eligible_scenario():
    from test_investment_brief import eligible_result, REFERENCE as brief_time
    from langgraphagenticai.analysis.scenarios import saved_inputs
    result = eligible_result()
    assert saved_inputs(result, "AAPL", brief_time).eligible
    raw = next(e for e in result["evidence"] if e["symbol"] == "AAPL" and e["category"] == "income_quarterly")
    raw["data"][0]["netIncome"] += 1000
    assert not research_net_income(result, "AAPL", reference_time=brief_time).eligible
    inputs = saved_inputs(result, "AAPL", brief_time)
    assert not inputs.eligible and "Shared earnings validation" in inputs.reasons[0]


def test_availability_audit_redacts_malformed_sensitive_metadata():
    rows = quarters(); rows[0]["acceptedDate"] = "sk-verylongsyntheticcredential"
    obs = observe(rows)
    assert not obs.eligible
    assert "verylongsyntheticcredential" not in json.dumps(obs.to_dict())
    assert observe(reference_time="unknown").status == "unverifiable"


def test_annual_revisions_irregular_year_and_filing_clock():
    row = {**quarters()[0], "period": "FY", "startDate": "2025-10-01", "filingDate": "2026-10-15",
           "acceptedDate": "2026-10-15 10:30:00"}
    annual = observe([row], basis="annual")
    assert annual.eligible and annual.inputs[0].accepted_at == "2026-10-15 10:30:00"
    assert "timezone" in annual.inputs[0].availability_basis
    assert not observe([row, {**row, "netIncome": 99}], basis="annual").eligible
    assert not observe([{**row, "startDate": "2026-07-01"}], basis="annual").eligible
