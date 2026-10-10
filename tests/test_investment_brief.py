"""P04 D01-D10: saved-only synthetic/recorded, arithmetic and hostile export checks."""
from copy import deepcopy
from datetime import datetime, timezone
import csv
import io
import json
import math
import pytest
from streamlit.testing.v1 import AppTest
from test_sector_research_audit import recorded_result
from langgraphagenticai.deep_research.models import Evidence
from langgraphagenticai.deep_research.research_metrics import audited_comparison_rows
from langgraphagenticai.analysis.scenarios import saved_inputs, calculate, SavedInputs
from langgraphagenticai.analysis.investment_brief import brief, export_packet, exports, safe_text

REFERENCE = '2026-10-08T16:00:00+00:00'

def eligible_result():
    """Explicit synthetic source-currency quote; recorded quote alone is ineligible."""
    result=recorded_result()
    for e in result['evidence']:
        if e['category']=='quote':
            row=e['data'][0] if isinstance(e['data'],list) else e['data']
            row['currency']='USD'
            row['timestamp']=datetime.fromisoformat('2026-10-07T16:00:00+00:00').timestamp()
    result['comparison']=audited_comparison_rows([Evidence(**e) for e in result['evidence']],result['request']['symbols'])
    return result

def test_saved_arithmetic_monotonicity_and_immutability():
    result=eligible_result(); before=deepcopy(result)
    inputs=saved_inputs(result,'aapl',REFERENCE)
    assert inputs.eligible,inputs.reasons
    assert inputs.net_income==128930000000
    assert calculate(inputs,20,20)['hypothetical_total_equity_value']==128930000000*1.2*20
    assert calculate(inputs,-100,100)['hypothetical_total_equity_value']==0
    assert calculate(inputs,0,20)['difference_vs_saved_cap_percent']==pytest.approx((128930000000*20/inputs.market_cap-1)*100)
    assert calculate(inputs,20,20)['hypothetical_total_equity_value'] > calculate(inputs,0,20)['hypothetical_total_equity_value'] > calculate(inputs,0,10)['hypothetical_total_equity_value']
    assert result==before
    assert saved_inputs(result,'JPM',REFERENCE).eligible
    assert not saved_inputs(result,'PLD',REFERENCE).eligible
    assert not saved_inputs(recorded_result(),'AAPL',REFERENCE).eligible

def test_bounded_source_appendix_discloses_omissions_and_removes_malformed_urls():
    result=eligible_result()
    result['evidence']=[dict(id=f'E{i:03d}',symbol='AAPL',provider='x'*4000,category='news',note='n'*4000,
        retrieved_at='2026-10-07T00:00:00Z',url='https://bad.example:999999/a',data={}) for i in range(150)]
    packet=export_packet(result,SavedInputs('AAPL',False,('Legacy',)),[])
    json_data,csv_data=exports(packet)
    assert len(json_data.encode())<=300000 and len(csv_data.encode())<=300000
    assert packet['saved_evidence']['omitted_records']>50
    assert all(not e['url'] for e in packet['saved_evidence']['records'])

@pytest.mark.parametrize('change,pe',[(True,20),(0,True),(math.nan,20),(0,math.inf),(-101,20),(201,20),(0,0),(0,101)])
def test_invalid_assumptions(change,pe):
    with pytest.raises(ValueError): calculate(saved_inputs(eligible_result(),'AAPL',REFERENCE),change,pe)

@pytest.mark.parametrize('mutation',[
    lambda r:r['comparison'][0].pop('Metric contracts'),
    lambda r:r['comparison'][0].update({'Net income (TTM)':0}),
    lambda r:r['comparison'][0].update({'Sector':'Unknown','Industry':'Unknown'}),
    lambda r:r['comparison'][0]['Metric contracts']['Net income (TTM)'].update(status='missing'),
    lambda r:r['comparison'][0]['Metric contracts']['Net income (TTM)'].update(unit='million USD'),
    lambda r:r['comparison'][0]['Metric contracts']['Net income (TTM)'].update(formula=''),
    lambda r:r['comparison'][0]['Metric contracts']['Net income (TTM)']['inputs'][0].update(source_id='unresolved'),
    lambda r:r['comparison'][0]['Metric contracts']['Market cap']['inputs'][0].update(currency_basis='Matching profile inference; not independently verified'),
    lambda r:r['comparison'][0]['Metric contracts']['Market cap']['inputs'][0].update(date='2026-10-07'),
    lambda r:r['comparison'][0].update({'Quote as of':'2026-10-07T16:00:00'}),
    lambda r:r['evidence'].append(deepcopy(r['evidence'][0])),
    lambda r:r.update(comparison=[None]),
    lambda r:r['request'].update(symbols=['JPM']),
])
def test_reject_inconsistent_audit_packets(mutation):
    result=eligible_result(); mutation(result)
    assert not saved_inputs(result,'AAPL',REFERENCE).eligible

def test_quote_age_future_fraction_currency_and_quarters():
    for timestamp in ('2026-10-08T16:00:00.5+00:00','2026-09-30T16:00:00+00:00'):
        result=eligible_result()
        quote=next(e for e in result['evidence'] if e['symbol']=='AAPL' and e['category']=='quote')['data'][0]
        quote['timestamp']=datetime.fromisoformat(timestamp).timestamp()
        result['comparison']=audited_comparison_rows([Evidence(**e) for e in result['evidence']],result['request']['symbols'])
        assert not saved_inputs(result,'AAPL',REFERENCE).eligible
    result=eligible_result()
    income=next(e for e in result['evidence'] if e['symbol']=='AAPL' and e['category']=='income_ttm')['data']
    income=income[0] if isinstance(income,list) else income
    income['quarters'][1]=deepcopy(income['quarters'][0])
    assert not saved_inputs(result,'AAPL',REFERENCE).eligible

def test_overflow():
    inputs=SavedInputs('AAPL',True,(),1e308,1)
    with pytest.raises(ValueError):calculate(inputs,200,100)
    with pytest.raises(ValueError):calculate(SavedInputs('AAPL',True,(),1e306,1),0,10)

def test_raw_heading_brief_and_hostile_exports():
    result=eligible_result(); credential='arbitrary-value-sensitive-1234'
    result['report']='## Business drivers\nSaved driver [E001]. '+credential+'\n## Risks\n=HYPERLINK("javascript:alert(1)") https://user:pass@evil.example/x https://ok.example/x?odd='+credential+'\n## Catalysts\nNo date stated. [E999]'
    before=deepcopy(result)
    b=brief(result,(credential,))
    assert '[E001]' in b['topics'][0]['saved_ai_excerpt']
    assert b['unresolved_evidence_ids']==['E999']
    assert b['topics'][2]['status']=='Not present in saved narrative'
    packet=export_packet(result,saved_inputs(result,'AAPL',REFERENCE),[],(credential,))
    encoded,tabular=exports(packet)
    assert json.loads(encoded)['schema']=='axiom-saved-brief-v1'
    assert json.loads(encoded)['inputs']['reference_time']==REFERENCE
    assert json.loads(encoded)['inputs']['quote_as_of']=='2026-10-07T16:00:00+00:00'
    assert safe_text('2026-10-08T16:00:00-04:00')=='2026-10-08T16:00:00-04:00'
    assert safe_text('Context: saved')=='Context: saved'
    assert all(bad not in encoded+tabular for bad in (credential,'javascript:','user:pass','?odd='))
    rows=list(csv.reader(io.StringIO(tabular)))
    assert rows[0]==['path','value']
    assert exports({'=hostile':'=SUM(1,2)','numeric':-2})[1].find("'=SUM")>=0
    assert '-2' in exports({'numeric':-2})[1]
    assert credential[:5] not in safe_text('x'*1998+credential,(credential,),2000)
    assert result==before

@pytest.mark.parametrize('workspace',['v1','v2'])
def test_shared_actual_controls_saved_immutability(workspace):
    result=eligible_result()
    app=AppTest.from_string('''
import streamlit as st
from langgraphagenticai.ui.investment_brief import render_investment_brief
render_investment_brief(st.session_state.saved,st.session_state.workspace,reference_time='2026-10-08T16:00:00+00:00')
''',default_timeout=60)
    app.session_state['saved']=deepcopy(result); app.session_state['workspace']=workspace
    app.run()
    assert not app.exception
    assert len(app.number_input)==6
    app.number_input[0].set_value(-100).run()
    assert not app.exception
    assert app.dataframe[0].value.iloc[0]['hypothetical_total_equity_value']==0
    assert app.session_state['saved']==result
    assert len(app.get('download_button'))==2

@pytest.mark.parametrize('workspace',['v1','v2'])
def test_real_workspace_saved_tab_zero_services(monkeypatch,workspace):
    from langgraphagenticai.ui import deep_research_tab as v1, deep_research_v2_tab as v2
    from langgraphagenticai.ui import investment_brief as shared
    from unittest.mock import Mock
    calls=Mock(side_effect=AssertionError('Saved controls must not call services'))
    monkeypatch.setattr(v1,'_manager',calls)
    monkeypatch.setattr(v1,'run_investment_committee',calls)
    monkeypatch.setattr(v2,'_manager_v2',calls)
    monkeypatch.setattr(v2,'run_decision',calls)
    original=shared.saved_inputs
    monkeypatch.setattr(shared,'saved_inputs',lambda result,ticker,reference:original(result,ticker,REFERENCE))
    result=eligible_result()
    if workspace=='v1':
        source='''
import streamlit as st
from langgraphagenticai.ui.deep_research_tab import render_deep_research_tab
st.session_state['dr_result_tabs_audit-test']='Investment brief & scenarios'
render_deep_research_tab(openai_api_key='',model_name='test',fmp_api_key='')
'''
        history='dr_history'
    else:
        source='''
from langgraphagenticai.ui.deep_research_v2_tab import render_deep_research_v2_tab
render_deep_research_v2_tab(openai_api_key='',fmp_api_key='')
'''
        history='drv2_history'
    app=AppTest.from_string(source,default_timeout=60)
    app.session_state[history]=[deepcopy(result)]
    app.run()
    assert not app.exception
    controls=[control for control in app.number_input if control.label=='Bear earnings change (%)']
    assert len(controls)==1
    controls[0].set_value(-100).run()
    assert not app.exception
    assert app.session_state[history]==[result]
    assert calls.call_count==0
