"""Dated Equity Report reuse and financial common-share contracts, offline only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.providers import company_evidence as bridge, valuation as provider
from langgraphagenticai.valuation import model, ai
from langgraphagenticai.valuation.book_value import common_book_value
from langgraphagenticai.valuation.citations import source_roles
from test_ai_valuation import evidence, rich_evidence, answer


def bank():
    raw = evidence("MS", "Financial Services")
    raw["balance"][0].pop("commonStockSharesOutstanding")
    row = raw["balance"][0]
    row["fiscalYear"] = int(row["date"][:4])
    raw["balance_reported"] = [{"symbol":"MS", "period":"FY", "date":row["date"], "reportedCurrency":"USD", "fiscalYear":row["fiscalYear"],
                                 "commonstocksharesoutstanding":100., "stockholdersequity":2200.}]
    return raw


def capture(raw, kind, *, period=None, api_key="synthetic", state=None):
    state = {} if state is None else state
    route, options, _ = provider.JOBS[kind]
    params = {"symbol":raw["symbol"], **options}
    if period:
        params["period"] = period
    with bridge.capture_company_evidence(api_key) as recorded:
        bridge.capture_fmp_response(provider.BASE+route.format(symbol=raw["symbol"]), params, raw[kind], api_key)
    bridge.save_company_evidence(state, recorded)
    return state


def test_common_bvps_uses_same_fiscal_reported_shares_and_resolves_both_sources():
    raw = bank(); snapshot = deepcopy(raw)
    facts = model.prepare(raw, use_disclosed_assumptions=True)
    assert facts["eligible"] and facts["basis"] == 20 and facts["shares"] == 100
    assert facts["current_multiple"] == 5
    assert facts["basis_source_ids"] == ["balance:0", "balance_reported:0"]
    packet = ai.evidence_packet(facts, raw)
    row = next(r for r in packet["evidence"] if r["id"]=="metric:annual_common_bvps")
    assert row["fields"]["value"] == 20
    assert source_roles(packet)["metric:annual_common_bvps"] == {"growth", "valuation"}
    assert raw == snapshot


@pytest.mark.parametrize("edit", [
    lambda row: row.update(symbol="JPM"), lambda row: row.update(period="Q4"),
    lambda row: row.update(reportedCurrency="EUR"), lambda row: row.update(date="2099-12-31"),
    lambda row: row.update(fiscalYear=2099),
    lambda row: row.update(commonstocksharesoutstanding=0),
    lambda row: row.update(commonstocksharesoutstanding=None, commonstocksharesissued=120),
    lambda row: row.update(commonstocksharesissued=120, treasurystockcommonshares=30),
    lambda row: row.update(acceptedDate="2099-01-01"),
])
def test_unsafe_share_inputs_cannot_enable_book_targets_but_allow_earnings_fallback(edit):
    raw = bank(); edit(raw["balance_reported"][0])
    result = model.prepare(raw, use_disclosed_assumptions=True)
    assert result["eligible"] and result["method"] == "P/E" and result["financial_fallback"]


def test_issued_minus_treasury_requires_both_counts_and_explicit_zero_is_valid():
    raw = bank(); row = raw["balance_reported"][0]
    row.update(commonstocksharesoutstanding=None, commonstocksharesissued=120, treasurystockcommonshares=20)
    assert common_book_value(raw["balance"][0], [row])["value"] == 20
    row["treasurystockcommonshares"] = 0
    assert common_book_value(raw["balance"][0], [row])["value"] == pytest.approx(2000/120)
    row.pop("treasurystockcommonshares")
    assert common_book_value(raw["balance"][0], [row])["value"] is None


def test_one_day_offset_needs_matching_fiscal_year_and_independent_equity():
    raw = bank(); row = raw["balance_reported"][0]
    row["date"] = str(datetime.fromisoformat(row["date"]).date()-timedelta(days=1))
    assert model.prepare(raw, use_disclosed_assumptions=True)["eligible"]
    row["stockholdersequity"] = 2201
    result = model.prepare(raw, use_disclosed_assumptions=True)
    assert result["eligible"] and result["method"] == "P/E" and result["financial_fallback"]


def test_duplicate_or_stale_as_reported_inputs_do_not_enable_targets():
    raw = bank(); raw["balance_reported"] *= 2
    result = model.prepare(raw,use_disclosed_assumptions=True)
    assert result["eligible"] and result["method"] == "P/E" and result["financial_fallback"]
    raw = bank(); raw["sources"]["balance_reported"]["retrieved_at"] = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    result = model.prepare(raw,use_disclosed_assumptions=True)
    assert result["eligible"] and result["method"] == "P/E" and result["financial_fallback"]


def test_recorded_jpm_common_book_value_uses_issued_less_treasury_not_diluted_shares():
    root=Path(__file__).resolve().parents[1]/"fmp_data_reference/samples"
    balance=json.loads(next((root/"FMP-064").rglob("JPM-annual.json")).read_text())[0]
    reported=json.loads(next((root/"FMP-068").rglob("JPM-annual.json")).read_text())[0]
    rows=provider.normalize_rows("balance_reported",[reported],"JPM","",1)
    contract=common_book_value(balance,rows)
    expected_shares=4104933895-1408700000
    assert contract["shares"]==expected_shares
    assert contract["value"]==pytest.approx((362438000000-20045000000)/expected_shares)
    assert "one-day" in contract["note"]


def test_equity_get_json_captures_allowlisted_raw_records_with_actual_timestamp(monkeypatch):
    from langgraphagenticai.ui import equity_report_tab as equity
    raw=rich_evidence(); rows=deepcopy(raw["profile"]); rows[0]["api_key"]="do-not-save"
    monkeypatch.setattr(equity,"get_fmp_json",lambda *a,**k: rows)
    with bridge.capture_company_evidence("synthetic") as recorded:
        equity._get_json(provider.BASE+"/stable/profile",{"symbol":"AAPL","apikey":"synthetic"})
    state={}; bridge.save_company_evidence(state,recorded)
    shared=bridge.saved_company_evidence(state,"AAPL","synthetic")
    assert shared["profile"][0]["companyName"]==rows[0]["companyName"]
    assert shared["sources"]["profile"]["workspace"]=="Equity Report"
    assert "do-not-save" not in json.dumps(shared)
    assert bridge.saved_company_evidence(state,"AAPL","other-key") is None
    assert bridge.saved_company_evidence({},"AAPL","synthetic") is None


def test_quarterly_evidence_cannot_masquerade_as_annual_and_capture_scope_restores():
    raw=rich_evidence(); raw["income"][0]["period"]="Q4"
    state=capture(raw,"income",period="quarter")
    saved=bridge.saved_company_evidence(state,"AAPL","synthetic")
    assert "quarter_income" in saved and "income" not in saved
    with bridge.capture_company_evidence("synthetic") as recorded:
        bridge.capture_fmp_response("https://example.com/stable/profile",{"symbol":"AAPL"},raw["profile"],"synthetic")
    assert not recorded["companies"]
    assert bridge._capture.get() is None


def test_generate_reuses_fresh_feeds_without_relabeling_retrieval_time(monkeypatch):
    provider._collect.clear(); raw=rich_evidence(); state={}
    for kind in ("quote","profile","income","balance","estimates","ratios","metrics","history","cashflow","targets"):
        state=capture(raw,kind,state=state)
    shared=bridge.saved_company_evidence(state,"AAPL","synthetic")
    quote_time=shared["sources"]["quote"]["retrieved_at"]
    request=Mock(side_effect=AssertionError("Must reuse fresh captured evidence"))
    monkeypatch.setattr(provider,"get_fmp_json",request)
    result=provider.load_valuation_evidence("AAPL","synthetic",shared=shared,refresh=True)
    assert result["sources"]["quote"]["retrieved_at"]==quote_time
    assert result["sources"]["quote"]["reused"]
    request.assert_not_called()


def test_stale_quote_and_other_credential_scope_are_fetched_not_reused(monkeypatch):
    provider._collect.clear(); raw=rich_evidence(); state=capture(raw,"quote")
    shared=bridge.saved_company_evidence(state,"AAPL","synthetic")
    shared["sources"]["quote"]["retrieved_at"]=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
    calls=[]
    def fetch(url,**kwargs):
        calls.append(url)
        kind=next(k for k,(route,*_) in provider.JOBS.items() if route.format(symbol="AAPL")==url.removeprefix(provider.BASE))
        return raw.get(kind,[])
    monkeypatch.setattr(provider,"get_fmp_json",fetch)
    result=provider.load_valuation_evidence("AAPL","synthetic",shared=shared,refresh=True)
    assert len(calls)==10 and not result["sources"]["quote"].get("reused")
    calls.clear()
    result=provider.load_valuation_evidence("AAPL","other-key",shared=shared,refresh=True)
    assert len(calls)==10 and not any(s.get("reused") for s in result["sources"].values())


def test_bank_provider_collects_missing_share_feed_and_normalizes_nested_tags(monkeypatch):
    provider._collect.clear(); raw=bank(); calls=[]
    def fetch(url,**kwargs):
        kind=next(k for k,(route,*_) in provider.JOBS.items() if route.format(symbol="MS")==url.removeprefix(provider.BASE))
        calls.append(kind)
        if kind=="balance_reported":
            row=raw[kind][0]
            return [{**{k:v for k,v in row.items() if k not in {"commonstocksharesoutstanding","stockholdersequity"}},"data":{"commonstocksharesoutstanding":100,"stockholdersequity":2200}}]
        return raw.get(kind,[])
    monkeypatch.setattr(provider,"get_fmp_json",fetch)
    result=provider.load_valuation_evidence("MS","synthetic",refresh=True)
    assert len(calls)==11 and calls.count("balance_reported")==1
    assert model.prepare(result,use_disclosed_assumptions=True)["basis"]==20


def test_reused_quarters_produce_audited_ttm_metrics_with_resolvable_provenance():
    raw=rich_evidence(); year=datetime.now(timezone.utc).year-1
    rows=[]
    for y, revenue in ((year,120.),(year-1,100.)):
        for quarter, end in ((4,"12-31"),(3,"09-30"),(2,"06-30"),(1,"03-31")):
            rows.append(dict(symbol="AAPL",date=f"{y}-{end}",period=f"Q{quarter}",fiscalYear=y,reportedCurrency="USD",revenue=revenue,grossProfit=revenue*.5,operatingIncome=revenue*.3,netIncome=revenue*.2))
    raw["quarter_income"]=rows
    raw["quarter_cashflow"]=[{**{k:r[k] for k in ("symbol","date","period","fiscalYear","reportedCurrency")},"freeCashFlow":24.} for r in rows[:4]]
    for kind in ("quarter_income","quarter_cashflow"):
        raw["sources"][kind]={"provider":"FMP","workspace":"Equity Report","reused":True,"status":"available","retrieved_at":raw["retrieved_at"]}
    packet=ai.evidence_packet(model.prepare(raw,use_disclosed_assumptions=True),raw)
    metrics={r["id"]:r["fields"] for r in packet["evidence"] if r["kind"]=="calculated_metric"}
    assert metrics["metric:revenue_growth"]["value"]==pytest.approx(.2)
    assert metrics["metric:fcf_margin"]["value"]==pytest.approx(.2)
    assert set(metrics["metric:fcf_margin"]["source_ids"])=={f"quarter_{kind}:{i}" for kind in ("income","cashflow") for i in range(4)}
    assert "growth" in source_roles(packet)["metric:revenue_growth"]
    assert "growth" in source_roles(packet)["metric:fcf_margin"]


def test_saved_equity_evidence_is_bounded_and_independent_between_sessions():
    state={}
    for symbol in ("AAPL","MSFT","MS","JPM","GOOG","NVDA","META","AMD","AVGO","XOM","CVX","CAT","JNJ","UNH","V","MA","HD"):
        state=capture(rich_evidence(symbol),"profile",state=state)
    assert len(state["company_evidence"])==16
    assert bridge.saved_company_evidence(state,"AAPL","synthetic") is None
    assert bridge.saved_company_evidence({},"MS","synthetic") is None


def test_valuation_ui_only_uses_bridge_on_explicit_generate_and_refresh_bypasses_it(monkeypatch):
    from langgraphagenticai.ui import ai_valuation_tab as ui
    raw=rich_evidence(); state=capture(raw,"profile")
    load=Mock(return_value=raw)
    monkeypatch.setattr(ui,"load_valuation_evidence",load)
    def generate(f,r,*_):
        packet=ai.evidence_packet(f,r)
        return {"ai":answer(packet),"packet":packet,"model":"gpt-5","generated_at":datetime.now(timezone.utc).isoformat()}
    generate=Mock(side_effect=generate); monkeypatch.setattr(ui,"generate_assumptions",generate)
    app=AppTest.from_string("from langgraphagenticai.ui.ai_valuation_tab import render_ai_valuation_tab; render_ai_valuation_tab('synthetic','synthetic','gpt-5')",default_timeout=30)
    app.session_state["company_evidence"]=state["company_evidence"]
    app.run(); load.assert_not_called(); generate.assert_not_called()
    app.button(key="valuation_generate").click().run()
    assert not app.exception and load.call_args.kwargs["shared"]["symbol"]=="AAPL"
    assert generate.call_count==1
    app.run(); assert load.call_count==1 and generate.call_count==1
    app.button(key="valuation_load").click().run()
    assert not app.exception and "shared" not in load.call_args.kwargs
    assert generate.call_count==1
