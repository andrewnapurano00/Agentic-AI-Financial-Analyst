"""Explicit two-stage Guided research UI with session-only saved results."""
import json
import streamlit as st
from langgraphagenticai.research.guided_workflow import config, prepare, run, fingerprint
from langgraphagenticai.state.research_context import ResearchContext
from langgraphagenticai.ui.workspace_handoff import queue_handoff
from langgraphagenticai.ui.app_shell import render_company_header, render_evidence_row

def render_guided_research_tab(*, openai_api_key='',model_name='',fmp_api_key='',marketaux_api_key=''):
    for name,value in st.session_state.get('guided_widget_values',{}).items():
        if name not in st.session_state:
            st.session_state[name]=value
    context=st.session_state.get('research_context')
    initial=context.symbols[0] if isinstance(context,ResearchContext) else 'AAPL'
    if isinstance(context,ResearchContext) and len(context.symbols)>1:
        st.info('Guided research covers one company. Select a ticker explicitly below, or open Deep Research.')
    draft=st.session_state.get('research_request_draft','')
    handoff=fingerprint({'symbols':list(context.symbols) if isinstance(context,ResearchContext) else [],'draft':draft})
    if st.session_state.get('guided_handoff_fingerprint')!=handoff:
        st.session_state['guided_handoff_fingerprint']=handoff
        if isinstance(context,ResearchContext):
            st.session_state['guided_symbol']=initial
        if draft:
            st.session_state['guided_question']=draft
    symbol=st.text_input('One company ticker',value=initial,key='guided_symbol')
    question=st.text_area('Focused research question',value=st.session_state.get('research_request_draft','What do the business, latest annual financials and recent news establish?'),key='guided_question')
    render_company_header(symbol,'Guided research','Provider facts and AI interpretation')
    st.caption('Prepare plan: one model attempt, zero provider calls. Run plan: at most three tools and one further model attempt. Maximum 12 graph steps; no model retries. Session storage only.')
    st.caption('Quote/profile uses two independent HTTP requests; annual and news use one each. Shared FMP transient retries may add attempts. Network timeouts bound inactivity, not total elapsed time; news is one page of up to five records.')
    with st.expander('Spend limits and pricing'):
        ceiling=st.number_input('Estimated spend ceiling (USD)',min_value=0.,value=1.,step=.1,key='guided_ceiling')
        known=st.checkbox('I have configured current model prices',key='guided_known')
        input_price=st.number_input('Input USD per million tokens',min_value=0.,value=0.,key='guided_input_price') if known else None
        output_price=st.number_input('Output USD per million tokens',min_value=0.,value=0.,key='guided_output_price') if known else None
        ack=st.checkbox('Allow unknown cost: the dollar ceiling cannot be guaranteed',key='guided_unknown_ack') if not known else False
        st.caption('Each attempt reserves 16,000 input tokens and 1,800 completion tokens, including reasoning. Configured prices are user supplied; actual usage is separate from reservations.')
    owned=('guided_symbol','guided_question','guided_ceiling','guided_known','guided_input_price','guided_output_price','guided_unknown_ack')
    st.session_state['guided_widget_values']={name:st.session_state[name] for name in owned if name in st.session_state}
    cfg=None
    try:
        cfg=config(symbol,question,model_name,ceiling,input_price,output_price,ack)
    except ValueError as exc:
        st.info(str(exc))
    if st.button('Prepare new plan',key='guided_prepare',type='primary',disabled=cfg is None or not openai_api_key):
        try:
            candidate=prepare(cfg,key=openai_api_key,secrets=(fmp_api_key,marketaux_api_key))
            st.session_state['guided_plan']=candidate
        except Exception as exc:
            st.session_state['guided_failed_planning_usage']=getattr(exc,'usage',{'model_attempts':0})
            st.error('Planning failed validation or exceeded the budget. Prior plan and result remain available. No automatic retry.')
    if st.session_state.get('guided_failed_planning_usage'):
        st.caption(f"Last failed explicit planning attempt usage: {st.session_state['guided_failed_planning_usage']}")
    saved=st.session_state.get('guided_plan')
    result=st.session_state.get('guided_result')
    matching=bool(saved and cfg and saved['config_fingerprint']==fingerprint(cfg))
    if saved:
        if not matching:
            st.warning('Saved plan mismatches current inputs. Prepare a new plan to run; prior work is retained.')
        st.markdown('**Proposed plan**')
        for i,step in enumerate(saved['plan']['steps'],1):
            st.write(f"{i}. {step['tool']}: {step['purpose']}")
        st.caption(f"Model attempts used: {saved['usage']['model_attempts']}/2. Estimated reserved USD: {saved['usage']['reserved_cost']:.4f}" if saved['usage']['reserved_cost'] is not None else 'Pricing unknown: estimated dollar cap unavailable.')
        if st.button('Run plan',key='guided_run',disabled=not matching or not openai_api_key):
            same=bool(result and result['run_id']==saved['run_id'] and result['config_fingerprint']==saved['config_fingerprint'] and result['plan_fingerprint']==saved['plan_fingerprint'])
            if same:
                st.info('Reusing saved result. Prepare new plan for a separately counted new run.')
            else:
                try:
                    with st.status('Running approved plan',expanded=True) as status:
                        def progress(tool,state):
                            st.write(f'{tool}: {state}')
                        st.session_state['guided_result']=run(saved,cfg,key=openai_api_key,fmp_key=fmp_api_key,news_key=marketaux_api_key,progress=progress)
                        status.update(label='Plan finished; inspect partial-data notices',state='complete')
                except Exception:
                    st.error('Execution failed. Prior work retained; no automatic retry.')
    result=st.session_state.get('guided_result')
    if result:
        if result['evidence_fingerprint']!=fingerprint(result['evidence']):
            st.error('Saved evidence fingerprint mismatch. Result withheld; prepare a new plan.')
            return
        if not cfg or result['config_fingerprint']!=fingerprint(cfg) or not saved or result['plan_fingerprint']!=saved['plan_fingerprint'] or result['run_id']!=saved['run_id']:
            st.warning('Saved result mismatches current question, company, model, limits or plan.')
        st.markdown('**Saved AI interpretation**')
        st.write(result['answer']['interpretation'])
        st.caption('Missing or withheld structured facts indicate incomplete validation. Saved evidence is not refreshed automatically; inspect original dates. Structured facts are checked against exact provider fields. AI interpretation is not semantically certified. Annual evidence is not TTM; this slice does not provide investment recommendations.')
        for warning in result['warnings']:
            st.warning(warning)
        st.write('Missing inputs:',result['answer']['missing_inputs'])
        st.write('Risks:',result['answer']['risks'])
        st.dataframe(result['steps'],use_container_width=True)
        if result['answer']['facts']:
            st.dataframe(result['answer']['facts'],use_container_width=True)
        with st.expander('Provider evidence, dates and usage'):
            for e in result['evidence']:
                render_evidence_row([('Evidence',e['id']),('Provider',e['provider']),('As of',e['as_of'] or 'Unavailable'),('Retrieved',e['retrieved_at']),('Basis',e['basis']),('Currency',e['currency'] or 'Unknown'),('Status',e['status']),('Units',str(e['unit']))])
                st.write(e['fields']);st.write(e['limitations']);st.write('Missing fields:',e['missing'])
            st.write(result['usage'])
        st.download_button('Download saved evidence and answer',json.dumps(result,ensure_ascii=False,indent=2),file_name='guided-research.json',mime='application/json',key='guided_download')
    if cfg and st.button('Open Deep Research',key='guided_deep'):
        queue_handoff(st.session_state,ResearchContext((cfg['symbol'],),'Deep Research','deep_research','Research'))
        st.rerun()
