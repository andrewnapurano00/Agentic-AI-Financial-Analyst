import json
from datetime import datetime, timezone
import pytest
from langgraphagenticai.research.guided_workflow import config,prepare,run,validate_facts,fingerprint
from langgraphagenticai.research.guided_schemas import Plan,Answer
from langgraphagenticai.providers.guided_research import collect

CFG=config('aapl','What are the annual financials?','synthetic',unknown_ack=True)
PLAN={'steps':[{'tool':'quote_profile','purpose':'business'},{'tool':'annual_income','purpose':'annual facts'},{'tool':'news_snapshot','purpose':'news'}]}
E=dict(id='annual_income-1',symbol='AAPL',provider='FMP',route='/stable/income-statement',status='available',retrieved_at='2026-10-07',as_of='2025-09-27',basis='annual FY',currency='USD',unit='currency amount',fields={'netIncome':0},missing=[],limitations=[])
def stub(text,schema,limit):
    if schema==Plan:
        return json.dumps(PLAN)
    return json.dumps({'interpretation':'Limited evidence.','facts':[{'evidence_id':E['id'],'field':'netIncome','value':0,'currency':'USD','as_of':E['as_of'],'basis':'annual FY'}],'risks':[],'missing_inputs':[]})
def tools(name,symbol):
    if name=='news_snapshot':
        raise RuntimeError('private key')
    return {'symbol':symbol,'status':'available','evidence':[dict(E,id=name+'-1')] if name=='annual_income' else [],'warnings':[]}

def test_partial_budget_and_facts():
    plan=prepare(CFG,model_call=stub)
    result=run(plan,CFG,model_call=stub,tool_call=tools)
    assert result['usage']['model_attempts']==2
    assert result['usage']['tool_dispatches']==3
    assert result['usage']['graph_steps']==2
    assert result['answer']['facts'][0]['value']==0
    assert result['steps'][-1]['status']=='failed'
    assert 'private key' not in json.dumps(result)

@pytest.mark.parametrize('steps',[[{'tool':'evil','purpose':'x'}],PLAN['steps']+[PLAN['steps'][0]],[PLAN['steps'][0],PLAN['steps'][0]]])
def test_hostile_plan(steps):
    with pytest.raises(ValueError):
        prepare(CFG,model_call=lambda *a:json.dumps({'steps':steps}))

def test_unknown_extra_and_mismatch():
    with pytest.raises(ValueError):
        prepare(CFG,model_call=lambda *a:json.dumps({**PLAN,'symbol':'MSFT'}))
    p=prepare(CFG,model_call=stub)
    with pytest.raises(ValueError):
        run(p,{**CFG,'symbol':'MSFT'},model_call=stub,tool_call=tools)
    p['plan']['steps'][0]['purpose']='tampered'
    with pytest.raises(ValueError):
        run(p,CFG,model_call=stub,tool_call=tools)

def test_fact_basis_bool_and_citation():
    fields={'interpretation':'x','facts':[{'evidence_id':E['id'],'field':'netIncome','value':0,'currency':'USD','as_of':E['as_of'],'basis':'TTM'}],'risks':[],'missing_inputs':[]}
    good,bad=validate_facts(Answer.model_validate(fields),[E]);assert not good and bad
    fields['facts'][0]['basis']='annual FY';fields['facts'][0]['evidence_id']='unknown'
    assert not validate_facts(Answer.model_validate(fields),[E])[0]
    fields['facts'][0]['value']=True
    with pytest.raises(ValueError):Answer.model_validate(fields)

def test_price_reservations_before_call():
    cfg=config('AAPL','question','model',ceiling=.001,input_price=10.,output_price=10.)
    calls=[]
    with pytest.raises(ValueError):prepare(cfg,model_call=lambda *a:calls.append(a))
    assert calls==[]
    with pytest.raises(ValueError):config('AAPL','q','m')

def test_provider_independent_failure_and_identity(monkeypatch):
    calls=[]
    def provider(url,**kwargs):
        calls.append(url)
        if url.endswith('profile'):return [{'symbol':'MSFT'}]
        return [{'symbol':'AAPL','timestamp':int(datetime(2026,10,6,tzinfo=timezone.utc).timestamp()),'price':0,'marketCap':True}]
    monkeypatch.setattr('langgraphagenticai.providers.guided_research.get_fmp_json',provider)
    result=collect('quote_profile','aapl',now=datetime(2026,10,7,tzinfo=timezone.utc))
    assert len(calls)==2 and result['status']=='partial'
    assert result['evidence'][0]['fields']=={'price':0,'marketCap':None}
    with pytest.raises(ValueError):collect('quote_profile','bad ticker')
    assert len(calls)==2

def test_secrets_not_saved():
    p=prepare(CFG,model_call=lambda *a:json.dumps({'steps':[{'tool':'quote_profile','purpose':'arbitrary-private-token'}]}),secrets=('arbitrary-private-token',))
    assert 'arbitrary-private-token' not in json.dumps(p)


def test_session_app_reruns_and_reuse(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import langgraphagenticai.ui.guided_research_tab as ui
    counts={'model':0,'tool':0}
    def model(*a):counts['model']+=1;return stub(*a)
    def tool(*a):counts['tool']+=1;return tools(*a)
    monkeypatch.setattr(ui,'prepare',lambda cfg,**kw:prepare(cfg,model_call=model))
    monkeypatch.setattr(ui,'run',lambda p,cfg,**kw:run(p,cfg,model_call=model,tool_call=tool))
    script="from langgraphagenticai.ui.guided_research_tab import render_guided_research_tab\nrender_guided_research_tab(openai_api_key='dummy',model_name='synthetic')"
    at=AppTest.from_string(script).run()
    assert not at.exception and counts=={'model':0,'tool':0}
    at.checkbox(key='guided_unknown_ack').check().run()
    at.button(key='guided_prepare').click().run()
    assert counts=={'model':1,'tool':0} and not at.exception
    at.button(key='guided_run').click().run()
    assert counts=={'model':2,'tool':3} and not at.exception
    at.run();at.button(key='guided_run').click().run()
    assert counts=={'model':2,'tool':3}
    second=AppTest.from_string(script).run()
    assert 'guided_result' not in second.session_state
    at.text_input(key='guided_symbol').set_value('MSFT').run()
    assert at.button(key='guided_run').disabled and counts=={'model':2,'tool':3}

def test_new_generation_consumed_and_failed_reservation():
    a=prepare(CFG,model_call=stub);b=prepare(CFG,model_call=stub)
    assert a['run_id']!=b['run_id']
    run(a,CFG,model_call=stub,tool_call=tools)
    with pytest.raises(ValueError):run(a,CFG,model_call=stub,tool_call=tools)
    assert a['usage']['model_attempts']==2 and a['consumed']
    calls=[]
    def failed(*args):calls.append(args);raise RuntimeError('fail')
    with pytest.raises(ValueError) as error:prepare(CFG,model_call=failed)
    assert error.value.usage['model_attempts']==1 and len(calls)==1

def test_pre_prompt_secret_removal_and_oversized():
    secret='arbitrary-private-token'
    cfg={**CFG,'question':'question '+secret}
    calls=[]
    def model(text,schema,limit):calls.append(text);return stub(text,schema,limit)
    p=prepare(cfg,model_call=model,secrets=(secret,))
    assert secret not in calls[0] and secret not in json.dumps(p)
    with pytest.raises(ValueError):prepare(CFG,model_call=lambda *a:'x'*12001)

def test_annual_contract_missing_nonfinite_and_future(monkeypatch):
    row={'symbol':'AAPL','period':'FY','date':'2025-09-27','reportedCurrency':'USD','revenue':0,'operatingIncome':float('inf'),'netIncome':None}
    monkeypatch.setattr('langgraphagenticai.providers.guided_research.get_fmp_json',lambda *a,**kw:[row])
    result=collect('annual_income','AAPL',now=datetime(2026,10,7,tzinfo=timezone.utc))
    assert result['evidence'][0]['fields']['revenue']==0
    assert result['evidence'][0]['missing']==['operatingIncome','netIncome']
    row['date']='2027-01-01';assert collect('annual_income','AAPL')['status']=='failed'
    row['date']='2025-09-27';row['period']='Q4';assert collect('annual_income','AAPL')['status']=='failed'


def test_news_filtered_partial_dedup_and_empty(monkeypatch):
    from langgraphagenticai.providers import guided_research as provider
    row={'entities':[{'symbol':'AAPL'}],'published_at':'2026-10-06T12:00:00Z','url':'https://example.com/article','title':'Example','source':'Synthetic','description':'excerpt'}
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'data':[{'published_at':'bad'},row,row]}
    monkeypatch.setattr(provider.requests,'get',lambda *a,**kw:Response())
    result=collect('news_snapshot','AAPL',news_key='fake',now=datetime(2026,10,7,tzinfo=timezone.utc))
    assert result['status']=='partial' and len(result['evidence'])==1
    assert '2 news records omitted' in result['warnings'][0]
    monkeypatch.setattr(Response,'json',lambda self:{'data':[]})
    assert collect('news_snapshot','AAPL',news_key='fake')['status']=='empty'


def test_safe_source_links():
    from langgraphagenticai.providers.guided_research import safe_link
    for bad in ('https://[invalid','https://user:pass@example.com','javascript:alert(1)','https://example.com/?apikey=secret','https://exa mple.com'):
        assert safe_link(bad)==''


def test_ui_new_plan_runs_and_saved_evidence_tamper(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import langgraphagenticai.ui.guided_research_tab as ui
    counts={'model':0,'tool':0}
    def model(*a):counts['model']+=1;return stub(*a)
    def tool(*a):counts['tool']+=1;return tools(*a)
    monkeypatch.setattr(ui,'prepare',lambda cfg,**kw:prepare(cfg,model_call=model))
    monkeypatch.setattr(ui,'run',lambda p,cfg,**kw:run(p,cfg,model_call=model,tool_call=tool))
    at=AppTest.from_string("from langgraphagenticai.ui.guided_research_tab import render_guided_research_tab\nrender_guided_research_tab(openai_api_key='dummy',model_name='synthetic')").run()
    at.checkbox(key='guided_unknown_ack').check().run()
    for _ in range(2):
        at.button(key='guided_prepare').click().run();at.button(key='guided_run').click().run()
    assert counts=={'model':4,'tool':6}
    at.session_state['guided_result']['evidence'][0]['fields']['netIncome']=5
    at.run()
    assert any('fingerprint mismatch' in e.value for e in at.error)
    assert counts=={'model':4,'tool':6}

def test_actual_main_mode_drafts_navigation_and_chat_preserved(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import langgraphagenticai.main as main
    import langgraphagenticai.ui.guided_research_tab as ui
    counts={'model':0,'tool':0}
    monkeypatch.setattr(main.LoadStreamlitUI,'load_streamlit_ui',lambda self:{'active_page':'Research','OPENAI_API_KEY':'dummy','selected_model':'synthetic'})
    monkeypatch.setattr(main,'render_command_bar',lambda:'Fresh command' if __import__('streamlit').session_state.get('inject_command') else '')
    for name in ('render_market_strip','render_page_header','render_terminal_status','_render_status_panel'):
        monkeypatch.setattr(main,name,lambda *a,**kw:None)
    def model(*a):counts['model']+=1;return stub(*a)
    def tool(*a):counts['tool']+=1;return tools(*a)
    monkeypatch.setattr(ui,'prepare',lambda cfg,**kw:prepare(cfg,model_call=model))
    monkeypatch.setattr(ui,'run',lambda p,cfg,**kw:run(p,cfg,model_call=model,tool_call=tool))
    at=AppTest.from_string('from langgraphagenticai.main import load_langgraph_agenticai_app\nload_langgraph_agenticai_app()').run()
    at.session_state['chat_history']=[{'role':'user','content':'saved chat'}]
    at.session_state['pending_research_query']='Incoming AAPL question'
    at.radio(key='research_mode').set_value('Guided research').run()
    assert at.text_area(key='guided_question').value=='Incoming AAPL question'
    at.text_input(key='guided_symbol').set_value('MSFT').run()
    at.checkbox(key='guided_unknown_ack').check().run()
    at.button(key='guided_prepare').click().run()
    at.radio(key='research_mode').set_value('Chat').run()
    assert at.session_state['chat_history']==[{'role':'user','content':'saved chat'}]
    at.radio(key='research_mode').set_value('Guided research').run()
    assert at.text_input(key='guided_symbol').value=='MSFT'
    assert at.checkbox(key='guided_unknown_ack').value
    assert not at.button(key='guided_run').disabled
    at.session_state['inject_command']=True
    at.run()
    assert at.text_area(key='guided_question').value=='Fresh command'
    assert counts=={'model':1,'tool':0} and not at.exception

def test_saved_fmp_samples(monkeypatch):
    from pathlib import Path
    stamp='20261003T044241108241Z'
    base=Path('fmp_data_reference/samples')
    routes={'/stable/profile':base/'FMP-018'/stamp/'AAPL-default.json','/stable/quote':base/'FMP-045'/stamp/'AAPL-default.json','/stable/income-statement':base/'FMP-061'/stamp/'AAPL-annual.json'}
    seen=[]
    def fake(url,**kw):
        route=url.replace('https://financialmodelingprep.com','');seen.append((route,kw['params']))
        return json.loads(routes[route].read_text(encoding='utf-8'))
    monkeypatch.setattr('langgraphagenticai.providers.guided_research.get_fmp_json',fake)
    quote=collect('quote_profile','AAPL',now=datetime(2026,10,7,tzinfo=timezone.utc))
    annual=collect('annual_income','AAPL',now=datetime(2026,10,7,tzinfo=timezone.utc))
    assert quote['status']=='available' and annual['status']=='available'
    assert annual['evidence'][0]['as_of']=='2025-09-27' and annual['evidence'][0]['basis']=='annual FY'
    assert seen[-1][1]=={'symbol':'AAPL','period':'annual','limit':1}
    assert quote['evidence'][1]['unit']['price']=='currency/share'
    quote_record=quote['evidence'][1]
    raw_quote=json.loads(routes['/stable/quote'].read_text(encoding='utf-8'))[0]
    assert quote_record['as_of']==datetime.fromtimestamp(raw_quote['timestamp'],timezone.utc).isoformat()
    assert 'Quote timestamp is interpreted as Unix seconds; dictionary units are unknown and this interpretation is inferred.' in quote_record['limitations']
    raw_annual=json.loads(routes['/stable/income-statement'].read_text(encoding='utf-8'))[0]
    assert annual['evidence'][0]['fields']=={key:raw_annual[key] for key in ('revenue','operatingIncome','netIncome')}
    assert 'Original provider monetary values are preserved without rescaling; exact monetary scaling has not been independently verified.' in annual['evidence'][0]['limitations']


def test_all_missing_is_not_available(monkeypatch):
    row={'symbol':'AAPL','period':'FY','date':'2025-09-27','reportedCurrency':'USD'}
    monkeypatch.setattr('langgraphagenticai.providers.guided_research.get_fmp_json',lambda *a,**kw:[row])
    assert collect('annual_income','AAPL')['status']=='missing'

def test_boundary_credentials_removed_before_provider_truncation(monkeypatch):
    from langgraphagenticai.providers import guided_research as provider
    secret='private-arbitrary-credential-token'
    hostile='x'*790+secret
    cleaned=provider.clean(hostile,(secret,))
    assert 'private-ar' not in cleaned
    def fmp(url,**kwargs):
        if url.endswith('profile'):
            return [{'symbol':'AAPL','companyName':'Synthetic','sector':'Technology','industry':'Software','description':hostile,'currency':'USD'}]
        return [{'symbol':'AAPL','timestamp':1791288000,'price':0,'marketCap':1}]
    class NewsResponse:
        def raise_for_status(self):pass
        def json(self):
            return {'data':[{'entities':[{'symbol':'AAPL'}],'published_at':'2026-10-06T12:00:00Z','url':'https://example.com/article','title':'News','source':'Synthetic','description':hostile}]}
    monkeypatch.setattr(provider,'get_fmp_json',fmp)
    monkeypatch.setattr(provider.requests,'get',lambda *a,**kw:NewsResponse())
    captured=[]
    def model(text,schema,limit):
        captured.append(text)
        return stub(text,schema,limit)
    plan=prepare(CFG,model_call=model,secrets=(secret,))
    def dispatcher(tool,symbol):
        return collect(tool,symbol,fmp_key=secret,news_key=secret,now=datetime(2026,10,7,tzinfo=timezone.utc))
    result=run(plan,CFG,model_call=model,tool_call=dispatcher,fmp_key=secret,news_key=secret)
    export=json.dumps(result)
    assert any(e['route']=='/stable/profile' for e in result['evidence'])
    assert any(e['route']=='/v1/news/all' for e in result['evidence'])
    for text in [*captured,json.dumps(plan),export]:
        assert secret not in text and 'private-ar' not in text

def test_pricing_status_unknown_export_null_and_configured_numeric():
    p=prepare(CFG,model_call=stub)
    result=run(p,CFG,model_call=stub,tool_call=tools)
    encoded=json.loads(json.dumps(result))
    assert encoded['usage']['reserved_cost'] is None
    assert encoded['usage']['pricing_status']=='unknown'
    known=config('AAPL','question','synthetic',ceiling=1.,input_price=1.,output_price=2.)
    p=prepare(known,model_call=stub)
    assert p['usage']['pricing_status']=='configured'
    assert p['usage']['reserved_cost']==pytest.approx(.0196)
    result=run(p,known,model_call=stub,tool_call=tools)
    assert result['usage']['reserved_cost']==pytest.approx(.0392)


def test_sdk_json_contract_usage_and_finish_validation(monkeypatch):
    from types import SimpleNamespace
    import langgraphagenticai.research.guided_workflow as workflow
    created=[]; construction=[]
    finish=['stop']; refusal=[None]
    class Completions:
        def create(self,**kwargs):
            created.append(kwargs)
            assert kwargs['response_format']=={'type':'json_object'}
            assert 'JSON' in kwargs['messages'][0]['content']
            assert kwargs['max_completion_tokens']==1800
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish[0],message=SimpleNamespace(content=json.dumps(PLAN),refusal=refusal[0]))],usage=SimpleNamespace(total_tokens=110,prompt_tokens=100,completion_tokens=10))
    def client(key,**kwargs):
        construction.append(kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    monkeypatch.setattr(workflow,'build_openai_client',client)
    p=prepare(CFG,key='dummy')
    assert construction==[{'timeout':60,'max_retries':0}]
    assert p['usage']['model_attempts']==1 and p['usage']['actual_tokens']==110
    assert p['usage']['measured_stages']==[{'stage':'planner','input_tokens':100,'completion_tokens':10}]
    finish[0]='length'
    with pytest.raises(ValueError) as error:prepare(CFG,key='dummy')
    assert error.value.usage['model_attempts']==1
    assert len(created)==2
    finish[0]='stop';refusal[0]='refused'
    with pytest.raises(ValueError) as error:prepare(CFG,key='dummy')
    assert error.value.usage['model_attempts']==1 and len(created)==3
