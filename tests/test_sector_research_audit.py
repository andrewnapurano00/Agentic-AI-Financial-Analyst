"""D01-D10 offline arithmetic, applicability and fresh/saved workflow contracts."""
import ast
from copy import deepcopy
from dataclasses import asdict
from datetime import date
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.deep_research import quarterly_data, v2_workflow
from langgraphagenticai.deep_research.models import Evidence, ResearchRequest
from langgraphagenticai.deep_research.quarterly_ttm import aggregate, INCOME_FIELDS, CASH_FIELDS, METHODOLOGY
from langgraphagenticai.deep_research.research_metrics import (audited_comparison_rows, annual_cagr, future_estimates,
    valid_snapshots, project_sector_row, format_metric, BASE_KEYS)
from langgraphagenticai.deep_research.sector import SECTOR_METRIC_REGISTRY, sector_frameworks
from langgraphagenticai.deep_research.manager import _analysis_comparison
from langgraphagenticai.deep_research.research_workflow import AuditedResearchManager
from langgraphagenticai.deep_research.v2 import stage_configuration
from langgraphagenticai.ui import deep_research_tab as ui

RECORD = json.loads((Path(__file__).parent/'fixtures/sector_quarterly_recorded_20261003.json').read_text(encoding='utf-8'))
REPORT = "## Executive Investment Thesis\nSaved evidence in USD as of 2026-06-30 [E001].\n## Risks\nRisk.\n## Thesis invalidation\nCash flow weakens."


def recorded_fetch(url, *, params, **kwargs):
    symbol=params['symbol']; data=RECORD['companies'][symbol]
    route=url.rsplit('/',1)[-1]
    category={'income-statement':'income','balance-sheet-statement':'balance','cash-flow-statement':'cash_flow',
              'profile':'profile','quote':'quote','analyst-estimates':'estimates'}.get(route)
    if category in {'income','balance','cash_flow'}:
        category += '_quarterly' if params['period']=='quarter' else '_annual'
    return deepcopy(data.get(category,[]))


def recorded_evidence():
    source=quarterly_data.QuarterlyFinancialDataSource('synthetic')
    source.fetch_json=recorded_fetch
    evidence=source.collect(ResearchRequest(['AAPL','JPM','PLD']),lambda _:None)
    for i,item in enumerate(evidence): item.id=f'E{i+1:03d}'
    return evidence


def recorded_result():
    evidence=recorded_evidence(); rows=audited_comparison_rows(evidence,['AAPL','JPM','PLD'])
    return dict(id='audit-test',created_at='2026-10-04T12:00:00Z',status='complete',report=REPORT,
        draft=REPORT,markdown=REPORT,request=asdict(ResearchRequest(['AAPL','JPM','PLD'],include_news=False)),
        evidence=[e.to_dict() for e in evidence],comparison=rows,sector_frameworks=sector_frameworks(evidence,['AAPL','JPM','PLD'],rows),
        warnings=[],gaps=[],diagnostics=[],plan={},financial_methodology=METHODOLOGY,
        cost_mode='Economy',v2_config=stage_configuration('Economy',light_provider='OpenAI'),
        v2_runtime=dict(budget=.35,decision_mode='None',ollama_base_url='http://localhost:11434/v1'))


@pytest.mark.parametrize('symbol,totals',[('AAPL',(466823000000,128930000000,146724000000,383266000000)),
    ('JPM',(297633000000,65067000000,-162534000000,5015069000000)),
    ('PLD',(9189768000,4208216000,5240975000,101011872000))])
def test_recorded_hand_expectations(symbol,totals):
    evidence=recorded_evidence(); rows=audited_comparison_rows(evidence,[symbol]); row=rows[0]
    assets=next(e for e in evidence if e.symbol==symbol and e.category=='balance_latest').data[0]['totalAssets']
    assert (row['Revenue (TTM)'],row['Net income (TTM)'],row['Operating cash flow (TTM)'],assets)==totals
    assert set(BASE_KEYS)<=set(row['Metric contracts'])
    assert all(c['formula'] and c['unit'] and c['status'] for c in row['Metric contracts'].values())


def test_recorded_reconciliation_exact_and_different():
    evidence=recorded_evidence()
    diagnostics={s:next(e for e in evidence if e.symbol==s and e.category=='annual_reconciliation').data for s in ('AAPL','JPM','PLD')}
    def metric(symbol,name): return next(r for r in diagnostics[symbol] if str(r['fiscal_year'])=='2025' and r['metric']==name)
    assert [metric('AAPL',field)['quarter_sum'] for field in ('revenue','netIncome','netCashProvidedByOperatingActivities','capitalExpenditure','freeCashFlow')]==[416161000000,112010000000,111482000000,-12715000000,98767000000]
    assert metric('JPM','revenue')['quarter_sum']==280333000000
    assert metric('JPM','revenue')['annual']==279745000000
    assert metric('PLD','netIncome')['quarter_sum']==3328231000
    assert metric('PLD','netIncome')['annual']==3410663000
    assert all(r['cause'].startswith('Unknown') for r in diagnostics['JPM'])


def test_bank_tech_reit_alias_projection_prompt_ui_and_pdf():
    result=recorded_result(); original=deepcopy(result)
    rows={r['Ticker']:project_sector_row(r) for r in result['comparison']}
    assert rows['AAPL']['P/B (TTM)'] is None and rows['AAPL']['P/B TTM'] is None
    for key in ('Latest Gross Margin','Gross margin (TTM)','Gross profit (TTM)','EBITDA (TTM)','FCF Margin','FCF margin (TTM)','Forward P/S'):
        assert rows['JPM'][key] is None,key
    assert rows['JPM']['Metric contracts']['Gross margin (TTM)']['applicability']=='downweighted'
    assert rows['JPM']['Metric contracts']['True Net Interest Margin']['status']=='unsupported'
    assert rows['PLD']['P/E (TTM)'] is None
    assert rows['PLD']['Metric contracts']['FFO']['status']=='unsupported'
    assert rows['AAPL']['Metric contracts']['FFO']['applicability']=='inapplicable'
    prompts={r['Ticker']:r for r in _analysis_comparison(result['comparison'],result['sector_frameworks'])}
    assert 'Gross margin (TTM)' not in prompts['JPM']
    assert 'P/B (TTM)' not in prompts['AAPL']
    matrix=ui._metric_matrix(__import__('pandas').DataFrame(result['comparison']),['P/B (TTM)','P/E (TTM)','Gross margin (TTM)'])
    assert matrix.loc['P/B (latest quarterly equity)','AAPL']=='\u2014'
    assert matrix.loc['Gross margin (TTM)','JPM']=='\u2014'
    from langgraphagenticai.deep_research.presentation import build_research_pdf
    from pdfminer.high_level import extract_text
    text=extract_text(io.BytesIO(build_research_pdf(result)))
    assert 'Metric audit' in text and 'unsupported' in text and 'FY+2' in text
    assert result==original


def synthetic_evidence():
    quarters=[dict(symbol='AAPL',fiscalYear=2025,period=f'Q{q}',date=d,reportedCurrency='USD',
        revenue=100,netIncome=10,grossProfit=50,operatingIncome=20,ebitda=25,
        researchAndDevelopmentExpenses=5,netCashProvidedByOperatingActivities=15,
        capitalExpenditure=-5,freeCashFlow=10,stockBasedCompensation=2)
        for q,d in zip((4,3,2,1),('2025-12-31','2025-09-30','2025-06-30','2025-03-31'))]
    income=aggregate(quarters,'AAPL',INCOME_FIELDS);cash=aggregate(quarters,'AAPL',CASH_FIELDS)
    end=dict(symbol='AAPL',date='2025-12-31',period='Q4',fiscalYear=2025,reportedCurrency='USD',
        totalDebt=30,cashAndCashEquivalents=10,totalAssets=200,totalStockholdersEquity=40,totalLiabilities=160,
        totalCurrentAssets=60,totalCurrentLiabilities=30)
    prior={**end,'date':'2024-12-31','fiscalYear':2024,'totalAssets':100,'totalStockholdersEquity':20}
    latest={**end,'date':'2026-03-31','fiscalYear':2026,'period':'Q1','totalDebt':60,'cashAndCashEquivalents':20,
            'totalStockholdersEquity':80,'totalAssets':300}
    contents={'profile':[dict(symbol='AAPL',currency='USD',sector='Technology')],
        'quote':[dict(symbol='AAPL',price=10,marketCap=200,currency='USD',timestamp=1767225600)],
        'income_ttm':[income],'cash_flow_ttm':[cash],'income':[quarters[0]],'cash_flow':[quarters[0]],
        'balance_quarterly':[latest,end,prior],'balance_latest':[latest],'balance_ttm':[end],
        'price_targets':[dict(symbol='AAPL',targetConsensus=15,currency='USD')]}
    return [Evidence(f'E{i+1:03d}','AAPL',category,category,'Synthetic',data,retrieved_at='2026-10-04T12:00:00Z',url='https://example.com/source') for i,(category,data) in enumerate(contents.items())]


def test_latest_balance_independent_and_average_returns():
    evidence=synthetic_evidence(); row=audited_comparison_rows(evidence,['AAPL'])[0]
    assert row['Balance sheet date']=='2026-03-31'
    assert row['P/B (TTM)']==2.5 and row['Debt / Assets']==.2 and row['Current Ratio']==2
    assert row['ROE']==pytest.approx(40/30) and row['ROA']==pytest.approx(40/150)
    assert row['Net Debt / EBITDA']==.2
    assert row['EV/EBITDA (TTM)']==2.4
    assert row['OCF margin (TTM)']==.15 and row['Capex to Revenue']==5
    evidence=[e for e in evidence if e.category not in {'income_ttm','income'}]
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    assert row['Balance sheet date']=='2026-03-31' and row['P/B (TTM)']==2.5
    assert row['ROE'] is None and row['P/E (TTM)'] is None


@pytest.mark.parametrize('field,bad',[('totalDebt',None),('cashAndCashEquivalents',None),('totalStockholdersEquity',0),('totalAssets',-1)])
def test_balance_missing_zero_negative_policy(field,bad):
    evidence=synthetic_evidence()
    for e in evidence:
        if e.category in {'balance_quarterly','balance_latest','balance_ttm'}:
            for r in e.data:r[field]=bad
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    if field in {'totalDebt','cashAndCashEquivalents'}:
        assert row['Net Debt / EBITDA'] is None and row['EV/EBITDA (TTM)'] is None
    if field=='totalStockholdersEquity': assert row['P/B (TTM)'] is None and row['ROE'] is None
    if field=='totalAssets': assert row['Debt / Assets'] is None and row['ROA'] is None


@pytest.mark.parametrize('value',[-4,0])
def test_signed_yields_retained_and_loss_multiples_unavailable(value):
    evidence=synthetic_evidence()
    for e in evidence:
        if e.category=='income_ttm':e.data[0]['netIncome']=value
        if e.category=='cash_flow_ttm':e.data[0]['freeCashFlow']=value
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    assert row['Earnings Yield']==value/200 and row['FCF Yield']==value/200
    assert row['P/E (TTM)'] is None and row['P/FCF TTM'] is None


@pytest.mark.parametrize('bad',['currency','date','quarters'])
def test_cross_statement_ratios_require_full_matching_window(bad):
    evidence=synthetic_evidence(); cash=next(e for e in evidence if e.category=='cash_flow_ttm').data[0]
    if bad=='currency':cash['reportedCurrency']='EUR'
    elif bad=='date':cash['quarters'][1]['date']='2025-09-29'
    else:cash['quarters']=cash['quarters'][:3]
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    assert row['Free cash flow (TTM)']==40
    assert row['Cash Conversion'] is None and row['FCF margin (TTM)'] is None


@pytest.mark.parametrize('flag',['YTD','as-reported','cumulative'])
def test_nonstandalone_durations_rejected(flag):
    rows=RECORD['companies']['AAPL']['income_quarterly']
    rows=deepcopy(rows);rows[0]['duration']=flag
    with pytest.raises(ValueError,match='duration'):aggregate(rows,'AAPL',INCOME_FIELDS)


def test_exact_three_year_cagr_and_guards():
    rows=[dict(symbol='AAPL',period='FY',fiscalYear=y,date=f'{y}-12-31',reportedCurrency='USD',revenue=v) for y,v in ((2025,200),(2023,100),(2022,100))]
    assert annual_cagr(rows,'AAPL','revenue')[0]==pytest.approx((2**(1/3)-1)*100)
    assert annual_cagr(rows[:2],'AAPL','revenue')[0] is None
    for field,value in [('symbol','MSFT'),('reportedCurrency','EUR'),('date','2024-12-31')]:
        changed=deepcopy(rows);changed[-1][field]=value
        assert annual_cagr(changed,'AAPL','revenue')[0] is None
    assert annual_cagr(rows+[rows[-1]],'AAPL','revenue')[0] is None


def test_future_annual_selector_does_not_use_historical_or_quarterly():
    rows=[dict(symbol='AAPL',date=d,revenueAvg=100,epsAvg=2,period=p) for d,p in [('2024-12-31','FY'),('2027-12-31','FY'),('2026-12-31','FY'),('2026-12-30','Q4')]]
    assert [r['date'] for r in future_estimates(rows,'AAPL',date(2026,10,4))]==['2026-12-31','2027-12-31']
    assert not future_estimates(rows[:1],'AAPL',date(2026,10,4))
    evidence=synthetic_evidence();evidence.append(Evidence('E020','AAPL','estimates','Estimates','Synthetic',rows))
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    assert row['Forward P/E']==5
    assert row['Forward revenue growth (%)']==0
    assert row['Metric contracts']['Forward revenue next period']['basis']=='2027-12-31'
    rows[2]['epsAvg']=-2
    assert audited_comparison_rows(evidence,['AAPL'])[0]['Forward P/E'] is None


def test_all_visible_keys_and_registry_have_audit_contracts():
    row=audited_comparison_rows(synthetic_evidence(),['AAPL'])[0]
    registry={m for r in SECTOR_METRIC_REGISTRY.values() for group in r.values() for m in group}
    assert registry<=set(row['Metric contracts'])
    source=(Path(__file__).parents[1]/'src/langgraphagenticai/ui/deep_research_tab.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_show_metric_matrix']
    visible={k.value for c in calls if len(c.args)>1 and isinstance(c.args[1],ast.List) for k in c.args[1].elts if isinstance(k,ast.Constant)}
    assert visible<=set(row['Metric contracts'])
    for key,c in row['Metric contracts'].items():
        assert c['formula'] and c['unit'] and c['methodology']==METHODOLOGY,key
        if c['unit'] not in {'metadata','text','date','unknown'} and c['status']=='ok':assert c['inputs'],key


@pytest.mark.parametrize('mode',['v1','v2'])
def test_fresh_factories_share_source_and_preserve_news_gate(monkeypatch,mode):
    fetch=Mock(side_effect=recorded_fetch)
    monkeypatch.setattr(quarterly_data.QuarterlyFinancialDataSource,'fetch_json',staticmethod(fetch))
    monkeypatch.setattr('langgraphagenticai.deep_research.v2_data.get_fmp_json',fetch)
    model=Mock();model.invoke.return_value=SimpleNamespace(content='{}')
    request=ResearchRequest(['AAPL'],period='quarter',include_news=False)
    if mode=='v1':
        monkeypatch.setattr(ui,'OpenAILLM',lambda _:SimpleNamespace(get_llm_model=lambda:model))
        monkeypatch.setattr(ui,'get_finance_tools',lambda *args:[])
        manager=ui._manager('synthetic','test','synthetic','','');manager.stop_after_evidence=True
    else:
        monkeypatch.setattr(v2_workflow,'build_stage_llm',lambda *args,**kwargs:model)
        monkeypatch.setattr(v2_workflow,'get_v2_finance_tools',lambda *args:[])
        manager=v2_workflow.build_manager(request=request,config=stage_configuration('Economy',light_provider='OpenAI'),
            openai_api_key='synthetic',groq_api_key='',fmp_api_key='synthetic',serper_api_key='',marketaux_api_key='',
            ollama_base_url='http://localhost:11434/v1',budget=.35,stop_after_evidence=True)
    result=manager.run(request)
    assert result['financial_methodology']==METHODOLOGY
    assert result['comparison'][0]['Revenue (TTM)']==466823000000
    routes=[c.args[0] for c in fetch.call_args_list]
    assert len(routes)==11 and not any('ttm' in url.lower() for url in routes)
    estimates=next(c for c in fetch.call_args_list if c.args[0].endswith('analyst-estimates'))
    assert estimates.kwargs['params']['period']=='annual'
    assert any(e['category']=='income_annual' for e in result['evidence'])


def test_legacy_resume_preserves_values_without_external_calls(monkeypatch):
    saved=recorded_result();saved['financial_methodology']='quarterly-ttm-v1'
    for e in saved['evidence']:
        if isinstance(e['data'],list):
            for r in e['data']:
                if isinstance(r,dict):r.pop('methodology',None)
    saved['comparison']=[dict(Ticker='AAPL',**{'P/E (TTM)':999,'Revenue (TTM)':123})]
    source=Mock();model=Mock()
    manager=AuditedResearchManager(model,source,Mock())
    monkeypatch.setattr(manager,'write_report',lambda *args,**kwargs:REPORT)
    result=manager.resume(saved)
    assert result['comparison']==saved['comparison']
    source.collect.assert_not_called();model.invoke.assert_not_called()
    assert 'legacy_financial_basis' in result


@pytest.mark.parametrize('unit,value,expected',[('fraction',2.5,'250.0%'),('percentage_points',2.5,'2.5%'),('fraction',0,'0.0%')])
def test_units_are_explicit_independent_of_magnitude(unit,value,expected):
    assert format_metric('Arbitrary',value,{'Metric contracts':{'Arbitrary':{'unit':unit}}})==expected


def test_technical_ytd_and_same_history_basis():
    from langgraphagenticai.deep_research.data import technical_snapshot
    rows=[dict(date='2025-12-31',close=100),dict(date='2026-01-02',close=110),dict(date='2026-01-05',close=120)]
    result=technical_snapshot(rows)
    assert result['return_ytd_pct']==pytest.approx(20)
    assert result['ytd_reference_date']=='2025-12-31'
    assert technical_snapshot(rows[1:])['return_ytd_pct'] is None
    assert technical_snapshot([{**r,'adjClose':r['close']*2} for r in rows])['price_basis']=='adjClose'
    assert technical_snapshot([dict(date='2030-01-01',close=100)])=={}


def test_actual_comparison_ui_audit_and_legacy_label():
    app=AppTest.from_string("""
import streamlit as st
from langgraphagenticai.ui.deep_research_tab import _render_comparison
_render_comparison(st.session_state['result'])
""",default_timeout=60)
    app.session_state['result']=recorded_result();app.run()
    assert not app.exception
    assert any('Metric audit' in item.label for item in app.expander)
    legacy=recorded_result();legacy['financial_methodology']='old';app.session_state['result']=legacy;app.run()
    assert not app.exception and any('legacy financial methodology' in item.value for item in app.warning)


def test_model_evidence_excludes_downweighted_bank_flows_and_labels_units():
    from langgraphagenticai.deep_research.prompt_context import evidence_context
    records=evidence_context(recorded_evidence(),200000)
    income=next(r for r in records if r['symbol']=='JPM' and r['category']=='income_ttm')
    assert 'ebitda' not in income['data'][0] and 'grossProfit' not in income['data'][0]
    assert income['financial_basis']=='TTM_standalone_quarter_sum'
    cash=next(r for r in records if r['symbol']=='JPM' and r['category']=='cash_flow_ttm')
    assert 'freeCashFlow' not in cash['data'][0] and 'reported currency units' in records[0]['context_policy']
    assert not any(r['category'] in {'ratios_ttm','metrics_ttm'} for r in records)


def test_compact_evidence_budget_keeps_substantive_core_data():
    from langgraphagenticai.deep_research.prompt_context import evidence_context
    from langgraphagenticai.deep_research.models import dumps
    records=evidence_context(recorded_evidence(),22000)
    assert len(dumps(records))<=22000
    assert any(r['symbol']=='AAPL' and r['category']=='income_ttm' and r['data'] for r in records)
    assert all(not isinstance(r['data'],dict) or bool(r['data'].get('excerpt')) for r in records if r['data'])


def test_missing_fcf_not_fabricated_and_nonsummable_fields_absent():
    rows=deepcopy(RECORD['companies']['AAPL']['cash_flow_quarterly'])
    rows[0]['freeCashFlow']=None
    result=aggregate(rows,'AAPL',CASH_FIELDS)
    assert result['freeCashFlow'] is None
    assert result['fcf_formula_diagnostics'][0]['ocf_plus_signed_capex'] is not None
    assert 'weightedAverageShsOut' not in result and 'eps' not in result


@pytest.mark.parametrize('duration',['6M','12 months','unknown'])
def test_unknown_or_long_durations_fail(duration):
    rows=deepcopy(RECORD['companies']['AAPL']['income_quarterly']);rows[0]['duration']=duration
    with pytest.raises(ValueError): aggregate(rows,'AAPL',INCOME_FIELDS)


def test_fiscal_year_required_instead_of_inferring_calendar_year():
    rows=deepcopy(RECORD['companies']['AAPL']['income_quarterly'])
    rows[0]['calendarYear']=2026;rows[0].pop('fiscalYear')
    with pytest.raises(ValueError):aggregate(rows,'AAPL',INCOME_FIELDS)


def test_both_workflows_share_ttm_free_investigation_tools():
    from langgraphagenticai.deep_research.research_workflow import audited_finance_tools
    tools=[SimpleNamespace(name=name) for name in ['get_valuation_bundle','get_financial_metrics_bundle','get_latest_earnings_transcript','get_dcf_valuation']]
    assert [tool.name for tool in audited_finance_tools(tools)]==['get_latest_earnings_transcript','get_dcf_valuation']


@pytest.mark.parametrize('period',['annual','quarter'])
def test_cagr_audit_inputs_are_actual_annual_endpoints(period):
    source=quarterly_data.QuarterlyFinancialDataSource('synthetic');source.fetch_json=recorded_fetch
    evidence=source.collect(ResearchRequest(['AAPL'],period=period),lambda _:None)
    for i,item in enumerate(evidence):item.id=f'E{i+1:03d}'
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    contract=row['Metric contracts']['Revenue CAGR 3Y']
    annual=next(e for e in evidence if e.category=='income_annual')
    assert len(contract['inputs'])==2
    ending,beginning=contract['inputs']
    assert (ending['value'],beginning['value'])==(416161000000,394328000000)
    assert [r['date'] for r in contract['inputs']]==['2025-09-27','2022-09-24']
    assert {r['source_id'] for r in contract['inputs']}=={annual.id}
    assert {r['category'] for r in contract['inputs']}=={'income_annual'}
    assert all(r['currency']=='USD' for r in contract['inputs'])
    assert row['Revenue CAGR 3Y']==pytest.approx((416161/394328)**(1/3)*100-100)


@pytest.mark.parametrize('duration',['YTD','as-reported','unknown'])
def test_latest_unverified_duration_excluded_from_ui_prompt_and_audit(duration):
    evidence=synthetic_evidence()
    latest=next(e for e in evidence if e.category=='income').data[0]
    latest['duration']=duration
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    assert row['Revenue (latest period)'] is None and row['Gross margin (latest period)'] is None
    contract=row['Metric contracts']['Revenue (latest period)']
    assert contract['status']=='missing' and 'duration' in contract['reason']
    assert contract['duration']['income']['duration']==duration
    assert ui._display_metric('Revenue (latest period)',row['Revenue (latest period)'],row)=='\u2014'
    context=__import__('langgraphagenticai.deep_research.prompt_context',fromlist=['evidence_context']).evidence_context(evidence,18000)
    selected=next(r for r in context if r['category']=='income')
    assert selected['financial_basis']=='excluded_unverified_duration'
    assert 'revenue' not in selected['data']


def test_ytd_vs_standalone_trend_never_becomes_yoy():
    from langgraphagenticai.deep_research.data import financial_trends
    rows=[dict(symbol='AAPL',date='2025-12-31',fiscalYear=2025,period='Q4',reportedCurrency='USD',revenue=100,duration='YTD'),
          dict(symbol='AAPL',date='2024-12-31',fiscalYear=2024,period='Q4',reportedCurrency='USD',revenue=50,duration='quarter')]
    item=Evidence('E1','AAPL','income','Income','Synthetic',rows)
    assert financial_trends([item],['AAPL'])==[]
    rows[0]['duration']='quarter'
    assert financial_trends([item],['AAPL'])[0].data[0]['yoy_pct']==100
    rows[1]['date']='2024-03-31'
    assert financial_trends([item],['AAPL'])==[]


def four_company_result():
    result=recorded_result()
    copied=[]
    for item in result['evidence']:
        if item['symbol']=='AAPL':
            clone=deepcopy(item);clone['symbol']='MSFT';clone['id']='M'+clone['id'];clone['provider']='Synthetic renamed AAPL fixture'
            if isinstance(clone['data'],list):
                for row in clone['data']:
                    if isinstance(row,dict) and row.get('symbol')=='AAPL':row['symbol']='MSFT'
            copied.append(clone)
    result['evidence']+=copied
    result['request']['symbols'].append('MSFT')
    evidence=[Evidence(**item) for item in result['evidence']]
    result['comparison']=audited_comparison_rows(evidence,result['request']['symbols'])
    result['sector_frameworks']=sector_frameworks(evidence,result['request']['symbols'],result['comparison'])
    return result


@pytest.mark.parametrize('budget',[18000,22000])
def test_four_company_evidence_budget_preserves_substantive_core_values(budget):
    from langgraphagenticai.deep_research.prompt_context import evidence_context
    from langgraphagenticai.deep_research.models import dumps
    result=four_company_result()
    context=evidence_context([Evidence(**e) for e in result['evidence']],budget)
    assert len(dumps(context))<=budget
    for symbol in result['request']['symbols']:
        record=next(r for r in context if r['symbol']==symbol and r['category']=='income_ttm')
        assert record['data'][0]['revenue']>0 and record['data'][0]['netIncome']>0
    assert not any(isinstance(r['data'],dict) and r['data'].get('excerpt')=='' for r in context)


@pytest.mark.parametrize('company_count',[3,4])
def test_decision_and_committee_packets_are_projected_and_wholly_bounded(company_count):
    from langgraphagenticai.deep_research.v2 import compact_decision_brief
    from langgraphagenticai.deep_research.crew_committee import _research_packet
    from langgraphagenticai.deep_research.models import dumps
    result=recorded_result() if company_count==3 else four_company_result()
    for packet in [compact_decision_brief(result,10000),json.loads(_research_packet(result,max_chars=10000))]:
        assert len(dumps(packet))<=10000
        rows={row['Ticker']:row for row in packet['comparison']}
        assert set(rows)==set(result['request']['symbols'])
        assert 'Metric contracts' not in dumps(packet)
        assert 'Gross margin (TTM)' not in rows['JPM'] and 'Latest Gross Margin' not in rows['JPM']
        assert 'P/E (TTM)' not in rows['PLD'] and 'P/E TTM' not in rows['PLD']
        for symbol in result['request']['symbols']:
            assert any(record['symbol']==symbol and record['data'] for record in packet['evidence'])


def test_actual_alias_and_complete_growth_return_inputs():
    evidence=synthetic_evidence()
    target=next(e for e in evidence if e.category=='price_targets').data[0]
    target['targetMedian']=target.pop('targetConsensus')
    estimates=[dict(symbol='AAPL',date='2026-12-31',period='FY',estimatedRevenueAvg=100,estimatedEpsAvg=2,reportedCurrency='USD'),
               dict(symbol='AAPL',date='2027-12-31',period='FY',estimatedRevenueAvg=200,estimatedEpsAvg=3,reportedCurrency='USD')]
    evidence.append(Evidence('EST','AAPL','estimates','Estimates','Synthetic',estimates))
    row=audited_comparison_rows(evidence,['AAPL'])[0];contracts=row['Metric contracts']
    assert row['Forward P/E']==5 and row['Forward revenue growth (%)']==100 and row['Target upside (%)']==50
    for key,field,value in [('Forward revenue','estimatedRevenueAvg',100),('Forward EPS','estimatedEpsAvg',2),('Analyst target','targetMedian',15)]:
        record=contracts[key]['inputs'][0]
        assert record['field']==field and record['value']==value
    assert contracts['Forward P/E']['inputs'][1]['field']=='estimatedEpsAvg'
    assert contracts['Target upside (%)']['inputs'][0]['field']=='targetMedian'
    growth=contracts['Forward revenue growth (%)']['inputs']
    assert [(r['field'],r['value'],r['date'],r['source_id']) for r in growth]==[
        ('estimatedRevenueAvg',100,'2026-12-31','EST'),('estimatedRevenueAvg',200,'2027-12-31','EST')]
    roe=contracts['ROE']['inputs']
    assert [(r['value'],r['date']) for r in roe[1:]]==[(20,'2024-12-31'),(40,'2025-12-31')]
    balance=next(e for e in evidence if e.category=='balance_quarterly')
    assert all(r['source_id']==balance.id for r in roe[1:])
    ev=contracts['EV/EBITDA (TTM)']['inputs']
    assert [(r['field'],r['value']) for r in ev]==[('marketCap',200),('totalDebt',60),('cashAndCashEquivalents',20),('ebitda',100)]


def test_currency_inference_is_recorded_in_actual_audit_input():
    evidence=synthetic_evidence()
    quote=next(e for e in evidence if e.category=='quote').data[0];quote.pop('currency')
    evidence.append(Evidence('EST','AAPL','estimates','Estimates','Synthetic',[
        dict(symbol='AAPL',date='2026-12-31',period='FY',estimatedRevenueAvg=100,estimatedEpsAvg=2)]))
    row=audited_comparison_rows(evidence,['AAPL'])[0]
    profile=next(e for e in evidence if e.category=='profile')
    for record in row['Metric contracts']['Forward P/E']['inputs']:
        assert record['currency']=='USD' and record['currency_source_id']==profile.id
        assert 'inference' in record['currency_basis']


@pytest.mark.parametrize("budget",[18000,48000])
def test_category_specific_research_payloads_survive_context_compaction(budget):
    from langgraphagenticai.deep_research.prompt_context import evidence_context
    from langgraphagenticai.deep_research.models import dumps
    payloads=[
        ("investigation",{"data":{"content":"Management guided revenue growth 20%", "date":"2026-01-01"}}),
        ("investigation",{"content":"Transcript: management discussed demand"}),
        ("financial_trends",[{"metric":"revenue","latest":100,"prior":50,"yoy_pct":100,"latest_date":"2025-12-31","prior_date":"2024-12-31","currency":"USD"}]),
        ("technicals",{"rsi":60,"ytd":20,"as_of":"2026-01-02","price_basis":"raw close"}),
        ("investigation",{"data":{"dcf":150,"currency":"USD","assumptions":{"growth":0.1}}}),
        ("investigation",{"data":{"peers":[{"symbol":"MSFT","revenue":200}]}}),
        ("news",[{"title":"Demand grows","snippet":"New product launch","published":"2026-01-01","publisher":"Synthetic"}]),
    ]
    evidence=[Evidence(symbol+"R"+str(i),symbol,category,"Research","Synthetic",data)
              for symbol in ["AAPL","MSFT","JPM","PLD"] for i,(category,data) in enumerate(payloads)]
    context=evidence_context(evidence,budget)
    assert len(dumps(context))<=budget
    by_id={r['id']:r['data'] for r in context}
    for symbol in ['AAPL','MSFT','JPM','PLD']:
        for i,(_,data) in enumerate(payloads):
            assert by_id[symbol+'R'+str(i)]==data


def test_ytd_exclusion_retains_duration_reason_in_actual_context():
    from langgraphagenticai.deep_research.prompt_context import evidence_context
    for category in ['income','cash_flow']:
        item=Evidence('YTD','AAPL',category,'Statement','Synthetic',[
            dict(symbol='AAPL',date='2025-12-31',period='Q4',fiscalYear=2025,
                 reportedCurrency='USD',revenue=100,duration='YTD',startDate='2025-01-01')])
        record=evidence_context([item])[0]
        assert record['financial_basis']=='excluded_unverified_duration'
        assert record['data']['duration']=='YTD' and record['data']['excluded']
        assert 'revenue' not in record['data']
