from copy import deepcopy
import pytest
from langgraphagenticai.deep_research.quarterly_ttm import aggregate, INCOME_FIELDS, CASH_FIELDS, derived_ratios
from langgraphagenticai.deep_research.models import ResearchRequest, Evidence
from langgraphagenticai.deep_research import v2_data


def quarters():
    return [dict(symbol="AAPL", fiscalYear=2025, period=f"Q{i}", date=d, reportedCurrency="USD", revenue=v,
                 netIncome=v/10, operatingIncome=v/5, grossProfit=v/2, ebitda=v/4,
                 freeCashFlow=v/8, capitalExpenditure=-v/20, netCashProvidedByOperatingActivities=v/6)
            for i, d, v in zip((4,3,2,1), ("2025-12-31","2025-09-30","2025-06-30","2025-03-31"), (40,30,20,10))]


def test_independent_sum_zero_missing_and_no_eps():
    rows=quarters(); rows[0]["revenue"]=0
    result=aggregate(rows,"AAPL",INCOME_FIELDS)
    assert result["revenue"] == 60
    assert result["netIncome"] == 10
    assert result["researchAndDevelopmentExpenses"] is None
    assert "eps" not in result and "weightedAverageShsOut" not in result
    rows[0]["revenue"]=None
    assert aggregate(rows,"AAPL",INCOME_FIELDS)["revenue"] is None


@pytest.mark.parametrize("change", ["missing","duplicate","restated","currency","symbol","annual","date","fiscal"])
def test_invalid_windows(change):
    rows=quarters()
    if change=="missing": rows.pop()
    elif change=="duplicate": rows[1]=dict(rows[0])
    elif change=="restated": rows.append({**rows[0],"revenue":999})
    elif change=="currency": rows[1]["reportedCurrency"]="EUR"
    elif change=="symbol": rows[1]["symbol"]="MSFT"
    elif change=="annual": rows[1]["period"]="FY"
    elif change=="date": rows[1]["date"]="bad"
    elif change=="fiscal": rows[1]["fiscalYear"]=2023
    with pytest.raises(ValueError): aggregate(rows,"AAPL",INCOME_FIELDS)


@pytest.mark.parametrize("bad", [True,float("inf"),float("nan"),"bad"])
def test_nonfinite_missing(bad):
    rows=quarters();rows[0]["revenue"]=bad
    assert aggregate(rows,"AAPL",INCOME_FIELDS)["revenue"] is None


def test_valuation_currency_positive_denominator_and_alignment():
    income=aggregate(quarters(),"AAPL",INCOME_FIELDS);cash=aggregate(quarters(),"AAPL",CASH_FIELDS)
    balance={"date":income["date"],"reportedCurrency":"USD","totalDebt":30,"cashAndCashEquivalents":10,"totalStockholdersEquity":40}
    ratios,metrics=derived_ratios(income,cash,balance,{"symbol":"AAPL","marketCap":200},"USD")
    assert ratios["priceToEarningsRatioTTM"]==20
    assert ratios["priceToSalesRatioTTM"]==2
    assert ratios["priceToBookRatioTTM"]==5
    assert metrics["enterpriseValueOverEBITDATTM"]==8.8
    assert "priceToEarningsRatioTTM" not in derived_ratios(income,cash,balance,{"symbol":"AAPL","marketCap":200},"EUR")[0]
    income["netIncome"]=-1
    assert derived_ratios(income,cash,balance,{"symbol":"AAPL","marketCap":200},"USD")[0]["priceToEarningsRatioTTM"] is None
    cash["quarters"]=[]
    assert "priceToFreeCashFlowRatioTTM" not in derived_ratios(income,cash,balance,{"symbol":"AAPL","marketCap":200},"USD")[0]


def test_collection_no_ttm_and_reuses_quarters(monkeypatch):
    calls=[]
    def fetch(url, **kwargs):
        calls.append((url,kwargs["params"]))
        assert "ttm" not in url.lower()
        if "statement" in url: return quarters()
        if url.endswith("profile"): return [{"symbol":"AAPL","currency":"USD"}]
        if url.endswith("quote"): return [{"symbol":"AAPL","marketCap":200}]
        return []
    monkeypatch.setattr(v2_data,"get_fmp_json",fetch)
    evidence=v2_data.QuarterlyFinancialDataSource("synthetic").collect(ResearchRequest(["AAPL"],period="quarter"),lambda _:None)
    assert len([c for c in calls if "statement" in c[0]])==3
    assert next(e for e in evidence if e.category=="income_ttm").data[0]["revenue"]==100
    assert next(e for e in evidence if e.category=="income").data==quarters()


def test_missing_balances_not_zero():
    income=aggregate(quarters(),"AAPL",INCOME_FIELDS)
    evidence=[Evidence("E001","AAPL","income_ttm","Income","Calculated",[income])]
    row=v2_data.quarterly_comparison_rows(evidence,["AAPL"])[0]
    assert row["Net Debt / EBITDA"] is None and row["Debt / Capital"] is None


def test_saved_aapl_independent_totals():
    import json
    from pathlib import Path
    sample=json.loads((Path(__file__).parent/"fixtures/aapl_quarterly_ttm_20261003.json").read_text())
    income=aggregate(sample["income"],"AAPL",INCOME_FIELDS)
    assert [income[k] for k in ("revenue","grossProfit","operatingIncome","ebitda","netIncome")] == [466823000000,227123000000,154859000000,168486000000,128930000000]
    cash=aggregate(sample["cash"],"AAPL",CASH_FIELDS)
    assert [cash[k] for k in ("netCashProvidedByOperatingActivities","capitalExpenditure","freeCashFlow")] == [146724000000,-10041000000,136683000000]


def test_v2_tools_preserve_safe_targeted_and_exclude_ttm(monkeypatch):
    from types import SimpleNamespace
    from langgraphagenticai.deep_research import v2_workflow as workflow
    names=["get_valuation_bundle","get_financial_metrics_bundle","get_financial_fundamentals_bundle","get_full_stock_analysis_bundle","compare_stocks_research_bundle","get_company_peers","get_dcf_valuation","get_latest_earnings_transcript"]
    monkeypatch.setattr(workflow,"get_finance_tools",lambda *a:[SimpleNamespace(name=n) for n in names])
    assert [t.name for t in workflow.get_v2_finance_tools("synthetic")] == names[-3:]


def test_all_exposed_v2_tools_invoke_without_ttm(monkeypatch):
    from langgraphagenticai.deep_research.v2_workflow import get_v2_finance_tools
    from langgraphagenticai.tools.fmp_mcp_client import FMPMCPClient
    calls=[]
    def stub(name):
        def call(*args, **kwargs):
            calls.append(name)
            assert "ttm" not in name.lower(), name
            return {"data": []}
        return call
    for name in dir(FMPMCPClient):
        if not name.startswith("_") and callable(getattr(FMPMCPClient,name)):
            monkeypatch.setattr(FMPMCPClient,name,stub(name))
    for tool in get_v2_finance_tools("synthetic"):
        args={"symbol":"AAPL"}
        if tool.name=="get_earnings_transcript": args.update(year=2025,quarter=4)
        tool.invoke(args)
    assert calls and all("ttm" not in name.lower() for name in calls)


def test_eight_quarter_growth_and_partial_failure(monkeypatch):
    rows=quarters()
    prior=[{**r,"fiscalYear":2024,"date":r["date"].replace("2025","2024"),"revenue":r["revenue"]*.8} for r in rows]
    def fetch(url, **kwargs):
        if "cash-flow-statement" in url: raise RuntimeError("synthetic failure")
        if "statement" in url: return rows+prior
        return []
    monkeypatch.setattr(v2_data,"get_fmp_json",fetch)
    evidence=v2_data.QuarterlyFinancialDataSource("synthetic").collect(ResearchRequest(["AAPL"],period="quarter"),lambda _:None)
    income=next(e for e in evidence if e.category=="income_ttm")
    assert income.status=="ok" and income.data[0]["growth_pct"]["revenue"]==25
    assert next(e for e in evidence if e.category=="cash_flow_ttm").status=="missing"
    assert v2_data.quarterly_comparison_rows(evidence,["AAPL"])[0]["Cash conversion (TTM)"] is None


def test_annual_history_preserved_and_cagr_currency_guard(monkeypatch):
    annual=[dict(symbol="AAPL",fiscalYear=y,date=f"{y}-12-31",period="FY",reportedCurrency="USD",revenue=v)
            for y,v in ((2025,100),(2024,90),(2023,80),(2022,50))]
    def fetch(url,**kwargs):
        if "statement" in url: return annual if kwargs["params"].get("period")=="annual" else quarters()
        return []
    monkeypatch.setattr(v2_data,"get_fmp_json",fetch)
    evidence=v2_data.QuarterlyFinancialDataSource("synthetic").collect(ResearchRequest(["AAPL"]),lambda _:None)
    source=next(e for e in evidence if e.category=="income")
    assert source.data==annual
    row=v2_data.quarterly_comparison_rows(evidence,["AAPL"])[0]
    assert row["Revenue CAGR 3Y"]==pytest.approx((2**(1/3)-1)*100)
    source.data=deepcopy(source.data);source.data[-1]["reportedCurrency"]="EUR"
    assert v2_data.quarterly_comparison_rows(evidence,["AAPL"])[0]["Revenue CAGR 3Y"] is None


def test_cache_methodology_differs_from_legacy_key():
    from dataclasses import asdict
    import hashlib
    from langgraphagenticai.deep_research.models import dumps
    from langgraphagenticai.deep_research.v2 import research_cache_key
    request=ResearchRequest(["AAPL"]);config={"mode":"Economy"}
    legacy=hashlib.sha256(dumps({"request":asdict(request),"config":config,"provider_dates":[]}).encode()).hexdigest()[:20]
    assert research_cache_key(request,config)!=legacy


@pytest.mark.parametrize("invalid", ["currency", "gap"])
def test_growth_rejects_cross_window_currency_and_gap_preserves_current(monkeypatch, invalid):
    rows=quarters()
    prior=[{**r,"fiscalYear":2024,"date":r["date"].replace("2025","2024"),"revenue":r["revenue"]*.8} for r in rows]
    if invalid=="currency":
        prior=[{**r,"reportedCurrency":"EUR"} for r in prior]
    else:
        prior=[{**r,"fiscalYear":2023,"date":r["date"].replace("2024","2023")} for r in prior]
    monkeypatch.setattr(v2_data,"get_fmp_json",lambda url,**kwargs: rows+prior if "statement" in url else [])
    evidence=v2_data.QuarterlyFinancialDataSource("synthetic").collect(ResearchRequest(["AAPL"],period="quarter"),lambda _:None)
    income=next(e for e in evidence if e.category=="income_ttm")
    assert income.status=="ok" and income.data[0]["revenue"]==100
    assert "growth_pct" not in income.data[0] and "prior_ttm" not in income.data[0]


def test_average_balance_roe_roa_and_missing_mismatch():
    income=aggregate(quarters(),"AAPL",INCOME_FIELDS)
    balance=dict(symbol="AAPL", date="2025-12-31", fiscalYear=2025, period="Q4", reportedCurrency="USD", totalAssets=200, totalStockholdersEquity=40)
    prior={**balance,"date":"2024-12-31","fiscalYear":2024,"totalAssets":100,"totalStockholdersEquity":20}
    ratios,_=derived_ratios(income,{},balance,{},"USD",prior)
    assert ratios["returnOnEquityTTM"]==pytest.approx(10/30)
    assert ratios["returnOnAssetsTTM"]==pytest.approx(10/150)
    assert ratios["return_balance_window"]["beginning"]["date"]=="2024-12-31"
    assert "average" in ratios["metric_formulas"]["returnOnEquityTTM"]
    for field,value in (("reportedCurrency","EUR"),("period","Q3"),("fiscalYear",2023),("date","2023-12-31"),("symbol","MSFT")):
        assert "returnOnEquityTTM" not in derived_ratios(income,{},balance,{},"USD",{**prior,field:value})[0]
    assert derived_ratios(income,{},balance,{},"USD",{**prior,"totalStockholdersEquity":None})[0]["returnOnEquityTTM"] is None


@pytest.mark.parametrize("identity", [None,"MSFT"])
def test_mismatched_quote_profile_identity_excluded_without_losing_flows(monkeypatch,identity):
    def fetch(url,**kwargs):
        if "statement" in url: return quarters()
        if url.endswith("quote"): return [{"symbol":identity,"marketCap":200,"price":10,"currency":"USD"}]
        if url.endswith("profile"): return [{"symbol":identity,"currency":"USD","companyName":"Wrong company"}]
        return []
    monkeypatch.setattr(v2_data,"get_fmp_json",fetch)
    evidence=v2_data.QuarterlyFinancialDataSource("synthetic").collect(ResearchRequest(["AAPL"],period="quarter"),lambda _:None)
    assert next(e for e in evidence if e.category=="income_ttm").data[0]["revenue"]==100
    row=v2_data.quarterly_comparison_rows(evidence,["AAPL"])[0]
    assert row["Market cap"] is None and row["Price"] is None and row["Company"] is None and row["P/E TTM"] is None
    income=aggregate(quarters(),"AAPL",INCOME_FIELDS)
    assert "priceToEarningsRatioTTM" not in derived_ratios(income,{}, {}, {"symbol":identity,"marketCap":200},"USD")[0]


@pytest.mark.parametrize("revenue", [0,-100])
def test_comparison_denominator_policy_matches_pure_calculations(revenue):
    income=aggregate(quarters(),"AAPL",INCOME_FIELDS)
    income.update(revenue=revenue,grossProfit=50,researchAndDevelopmentExpenses=2)
    evidence=[Evidence("E001","AAPL","income_ttm","Income","Calculated",[income]),
              Evidence("E002","AAPL","income","Income","FMP",[{**quarters()[0],"revenue":revenue,"researchAndDevelopmentExpenses":2}])]
    row=v2_data.quarterly_comparison_rows(evidence,["AAPL"])[0]
    for key in ("Gross margin (TTM)","Operating margin (TTM)","EBITDA margin (TTM)","Net margin (TTM)","Net margin (TTM, fraction)","R&D as % revenue (TTM)","R&D as % Revenue", "Latest Gross Margin", "Latest Operating Margin", "Latest EBITDA Margin", "Latest Net Margin"):
        assert row[key] is None,key


def test_derived_renderer_uses_each_statement_currency():
    from langgraphagenticai.ui.deep_research_tab import _display_metric
    row={"TTM methodology":"quarterly-ttm-v1","Statement currency":"GBP","TTM currency":"USD", "Cash flow TTM currency":"EUR", "Cash flow statement currency":"JPY"}
    assert _display_metric("Revenue (TTM)",100,row)=="USD 100.00"
    assert _display_metric("Free cash flow (TTM)",100,row)=="EUR 100.00"
    assert _display_metric("Capital expenditure (latest period)",100,row)=="JPY 100.00"


def test_mixed_currency_comparison_preserves_independent_flows_and_labels():
    income=aggregate(quarters(),"AAPL",INCOME_FIELDS)
    cash_rows=[{**r,"reportedCurrency":"EUR"} for r in quarters()]
    cash=aggregate(cash_rows,"AAPL",CASH_FIELDS)
    evidence=[Evidence("E001","AAPL","income_ttm","Income","Calculated",[income]),
              Evidence("E002","AAPL","cash_flow_ttm","Cash","Calculated",[cash]),
              Evidence("E003","AAPL","income","Annual income","FMP",[{"date":"2024-12-31","period":"FY","reportedCurrency":"GBP"}])]
    row=v2_data.quarterly_comparison_rows(evidence,["AAPL"])[0]
    assert row["Revenue (TTM)"]==100 and row["Free cash flow (TTM)"]==12.5
    assert row["TTM currency"]=="USD" and row["Cash flow TTM currency"]=="EUR" and row["Statement currency"]=="GBP"
    assert row["Cash flow TTM through"]=="2025-12-31"
    assert row["FCF margin (TTM)"] is None


@pytest.mark.parametrize("metric", ["ROE", "ROA", "Gross margin (TTM)", "Net margin (latest period)", "OCF Margin", "Earnings Yield", "FCF Yield", "FCF yield (TTM, fraction)"])
@pytest.mark.parametrize("value,expected", [(2.5,"250.0%"),(.25,"25.0%")])
def test_derived_fraction_rendering_has_no_magnitude_guess(metric,value,expected):
    from langgraphagenticai.ui.deep_research_tab import _display_metric
    assert _display_metric(metric,value,{"TTM methodology":"quarterly-ttm-v1"})==expected
    assert _display_metric("ROE",2.5,{})=="2.5%"


@pytest.mark.parametrize("metric", ["revenue TTM growth (%)", "R&D as % revenue (TTM)", "Stock-Based Comp % Revenue", "Capex to revenue (TTM)", "Capex to Revenue"])
def test_derived_percentage_points_rendering_unchanged(metric):
    from langgraphagenticai.ui.deep_research_tab import _display_metric
    assert _display_metric(metric,2.5,{"TTM methodology":"quarterly-ttm-v1"})=="2.5%"


def test_pdf_tables_preserve_cash_currency_dates_and_fraction_units():
    from reportlab.lib.styles import getSampleStyleSheet
    from langgraphagenticai.deep_research.presentation import _financial_basis_table, _comparison_table
    row={"Ticker":"AAPL", "TTM methodology":"quarterly-ttm-v1", "TTM through":"2025-12-31","TTM currency":"USD",
         "Statement date":"2024-12-31","Statement currency":"GBP","Cash flow TTM currency":"EUR","Cash flow TTM through":"2025-09-30",
         "Cash flow statement currency":"JPY","Cash flow statement date":"2024-09-30", "Revenue (TTM)":100,"Free cash flow (TTM)":12.5,
         "Free cash flow (latest period)":5,"Operating margin (TTM)":2.5,"ROE":2.5,"ROA":.25,"R&D as % Revenue":2.5}
    style=getSampleStyleSheet()["BodyText"]
    basis=_financial_basis_table([row],style)
    cells=[[cell.getPlainText() for cell in line] for line in basis._cellvalues]
    assert cells[1][3]=="USD 100.0" and cells[1][4]=="250.0%"
    assert cells[1][-1]=="EUR 12.5 (through 2025-09-30)"
    assert cells[2][-1]=="JPY 5.0 (through 2024-09-30)"
    table=_comparison_table([row],style,[{"must_have":["ROE","ROA","R&D as % Revenue"],"preferred":[]}])
    values={line[0].getPlainText():line[1].getPlainText() for line in table._cellvalues[1:]}
    assert values=={"ROE":"250.0%","ROA":"25.0%","R&D as % Revenue":"2.5%"}
    from io import BytesIO
    from pdfminer.high_level import extract_text
    from langgraphagenticai.deep_research.presentation import build_research_pdf
    packet={"request":{"symbols":["AAPL"]},"comparison":[row],"sector_frameworks":[{"symbol":"AAPL","framework":"Synthetic","must_have":["ROE","ROA","R&D as % Revenue"],"preferred":[]}],"report":"## Executive Investment Thesis\nSynthetic financial review.","status":"complete"}
    text=" ".join(extract_text(BytesIO(build_research_pdf(packet))).split())
    assert "EUR 12.5" in text and "2025-09-30" in text
    assert "JPY 5.0" in text and "2024-09-30" in text and "250.0%" in text
