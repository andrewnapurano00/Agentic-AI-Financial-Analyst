"""Seven user-facing repairs, with provider/model boundaries kept offline."""
import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


def response(value):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=value,refusal=None))])


def test_ribbon_moves_right_without_scrollbar_and_escapes():
    from langgraphagenticai.ui.ticker_ribbon import ribbon_html
    html=ribbon_html([dict(symbol='<script>',price=10,change=-1)])
    assert 'overflow:hidden' in html and 'overflow:auto' not in html
    assert 'from{transform:translateX(-50%)}to{transform:translateX(0)}' in html
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'prefers-reduced-motion' in html


def test_news_previews_keep_distinct_detail_and_strip_html():
    from langgraphagenticai.providers.news_content import preview
    text=preview(dict(description='Description',snippet='Longer preview',entities=[dict(highlights=[dict(highlight='<b>Entity detail</b>')])]))
    assert all(t in text for t in ('Description','Longer preview','Entity detail'))
    assert '<b>' not in text


def test_executive_prose_hides_portfolio_metric_references_preserving_values():
    from langgraphagenticai.analysis.executive_text import executive_text
    text=executive_text('Provider TTM margin is 0%; downside -12%. [XOM:pe_ttm] [N1] source #3')
    assert '0%' in text and '-12%' in text
    assert not any(token in text for token in ('Provider','pe_ttm','N1','source #'))


def test_ticker_news_recovers_web_search_when_news_index_empty(monkeypatch):
    from langgraphagenticai.providers import ticker_news as provider
    calls=[]
    def search(self,query,**kwargs):
        calls.append((query,kwargs))
        if kwargs.get('news',True):return {'ok':False,'results':[]}
        return {'ok':True,'results':[dict(title='Zscaler expands product',url='https://example.com/zs',snippet='Product detail',published='2 hours ago')]}
    monkeypatch.setattr(provider.SerperClient,'search',search)
    data=provider._collect.__wrapped__('ZS','Zscaler','','','synthetic')
    assert len(data['articles'])==1 and len(calls)==2
    assert calls[1][1]['news'] is False and calls[1][1]['days']==7
    assert calls[1][1]['filter_dates'] is True
    assert 'Zscaler' in calls[0][0] and data['symbol']=='ZS'


def test_market_news_readable_without_citation_controls(monkeypatch):
    from langgraphagenticai.ui import market_news_summary as ui
    from test_market_updates import sample_news, summary_response
    news=sample_news();packet=ui.news_evidence(news);result=summary_response(packet)
    result['overview']='Rates are the key portfolio risk. [N1]'
    saved=dict(result=result,evidence=packet,model='gpt-5')
    monkeypatch.setattr(ui,'summarize_news',Mock(return_value=saved))
    app=AppTest.from_string('from langgraphagenticai.ui.market_news_summary import render_news_summary\nfrom test_market_updates import sample_news\nrender_news_summary(sample_news(),"synthetic")',default_timeout=30).run()
    app.button(key='market_news_summarize').click().run()
    assert not app.exception and not app.get('link_button')
    assert not any('sources' in e.label.lower() for e in app.expander)
    assert all('[N1]' not in t.value for t in app.text)
    app.run();assert ui.summarize_news.call_count==1


def test_historical_question_fetches_requested_symbol_and_dated_indicators(monkeypatch):
    from langgraphagenticai.technical_analysis import questions as q
    points=[(d,100+i) for i,d in enumerate(pd.bdate_range('2020-01-01',periods=100))]
    load=Mock(return_value=dict(symbol='ZS',calculation_points=points,price_basis='adjusted',retrieved_at='2026-10-24'))
    create=Mock(return_value=response('Momentum improved, with reversal risk.'))
    monkeypatch.setattr(q,'load_symbol_history',load)
    monkeypatch.setattr(q,'build_openai_client',lambda *a,**k:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    result=q.answer_question('ZS',date(2020,3,1),date(2020,4,1),'How did MACD evolve?','fmp','synthetic','gpt-5')
    load.assert_called_once_with('ZS','fmp','All')
    packet=json.loads(create.call_args.kwargs['messages'][1]['content'])
    assert packet['daily_observations'][0]['Date'].startswith('2020-03-02')
    assert 'MACD' in packet['daily_observations'][0] and packet['daily_observations'][0]['RSI']==100
    assert result['symbol']=='ZS' and create.call_count==1
    with pytest.raises(ValueError):q.answer_question('ZS',date(2021,1,1),date(2020,1,1),'x','fmp','synthetic','gpt-5')
    assert load.call_count==1


def test_historical_question_form_reruns_never_call_model(monkeypatch):
    from langgraphagenticai.ui import technical_questions as ui
    ask=Mock(return_value=dict(symbol='ZS',question='Explain RSI',answer='Momentum strengthened. [T1]',start='2020-01-01',end='2020-06-01'))
    monkeypatch.setattr(ui,'answer_question',ask)
    app=AppTest.from_string('from langgraphagenticai.ui.technical_questions import render_technical_questions\nrender_technical_questions("ZS","synthetic","synthetic","gpt-5")',default_timeout=30).run()
    assert ask.call_count==0
    app.text_area[0].set_value('Explain RSI')
    app.button[0].click().run()
    assert not app.exception and ask.call_count==1
    app.run();assert ask.call_count==1
    assert all('[T1]' not in m.value for m in app.markdown)


def test_social_active_ui_has_no_chart_and_preserves_result_on_failure(monkeypatch):
    from langgraphagenticai.ui import social_brief as ui
    load=Mock(return_value={'symbol':'ZS','records':[{}],'retrieved_at':'2026-10-24'})
    summary=Mock(return_value=dict(tone='Neutral',summary='Participation is mixed.',uncertainty='Direction is uncertain.'))
    monkeypatch.setattr(ui,'load_social_sentiment',load);monkeypatch.setattr(ui,'summarize_social',summary)
    app=AppTest.from_string('from langgraphagenticai.ui.social_brief import render_social_brief\nrender_social_brief("ZS","synthetic","synthetic","gpt-5")',default_timeout=30).run()
    assert not load.called
    app.button[0].click().run()
    assert not app.exception and not app.get('arrow_vega_lite_chart') and summary.call_count==1
    app.run();assert summary.call_count==1
    summary.side_effect=ValueError('Unavailable')
    app.button[0].click().run()
    assert any('Participation is mixed' in t.value for t in app.markdown)


def test_committee_timeout_does_not_expose_task_packet_and_has_bounded_llm(monkeypatch):
    import sys
    from langgraphagenticai.equity_committee import run_equity_committee
    class Component:
        def __init__(self,**kwargs):self.__dict__.update(kwargs)
    class Crew(Component):
        def kickoff(self):raise TimeoutError("Task 'PRIVATE EQUITY PACKET' execution timed out after 90 seconds")
    llm=Mock(side_effect=lambda **kw:Component(**kw))
    monkeypatch.setitem(sys.modules,'crewai',SimpleNamespace(Agent=Component,Task=Component,Crew=Crew,LLM=llm,Process=SimpleNamespace(sequential='sequential')))
    with pytest.raises(RuntimeError,match='exceeded its time budget') as error:
        run_equity_committee({'tickers':['ZS']},openai_api_key='synthetic',model_name='gpt-5')
    assert 'PRIVATE' not in str(error.value) and error.value.__suppress_context__
    assert llm.call_args.kwargs['max_retries']==0 and llm.call_args.kwargs['max_completion_tokens']==4000
    assert llm.call_args.kwargs['api']=='responses' and llm.call_args.kwargs['store'] is False


def test_installed_crewai_gpt5_adapter_preserves_reasoning_and_token_budget():
    from crewai import LLM
    llm=LLM(model='openai/gpt-5',api_key='synthetic-offline',timeout=60,max_retries=0,
            max_completion_tokens=4000,api='responses',store=False,reasoning_effort='low')
    params=llm._prepare_responses_params([{'role':'user','content':'Offline contract'}])
    assert params['max_output_tokens']==4000 and params['reasoning']=={'effort':'low'}
    assert params['store'] is False and 'max_tokens' not in params


def test_portfolio_memo_ignores_multi_megabyte_research_universe():
    from langgraphagenticai.analysis.investment_memo import portfolio_memo
    from langgraphagenticai.analysis.memo_pdf import pdf_bytes
    source={'holdings':[dict(ticker='ZS',name='Zscaler',weight=.9,pros=['Growth opportunity'],cons=['Valuation risk'])],
            'cash':.1,'snapshot':{'mode':'LIVE','retrieved_at':'2026-10-24','securities':[{'history':'x'*3_000_000}]},'risk':{}}
    memo=portfolio_memo(source)
    assert sum(len(t) for _,t in memo.appendices)<2000
    assert 'ZS' in memo.thesis and '90.00%' in dict(memo.sections)['Allocation - ticker | name | weight | reason']
    assert pdf_bytes(memo).startswith(b'%PDF')
    assert len(source['snapshot']['securities'][0]['history'])==3_000_000
