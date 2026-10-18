"""Explicit collection gates, news synthesis and expanded sector ranking contracts."""
import json
import sys
from types import SimpleNamespace
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis.discovery import expanded_ranking, sector_participation
from langgraphagenticai.analysis import market_news_ai as news_ai
from langgraphagenticai.ui.movers_heatmap import participation_chart


def universe(size=101):
    return pd.DataFrame([dict(symbol=f'S{i:03}', sector='Technology' if i < 60 else 'Energy',
                              **{'1D': float(i), '5D': float(-i)}) for i in range(size)])


def test_ranking_size_uses_filtered_finite_denominator():
    data = universe()
    data.loc[0, '1D'] = float('inf')
    top, stats = expanded_ranking(data, '1D')
    assert len(top) == 50 and stats['usable'] == 100 and top.iloc[0].symbol == 'S100'
    tenth, _ = expanded_ranking(data, '1D', size='Top 10%')
    assert len(tenth) == 10
    filtered, stats = expanded_ranking(data, '1D', 'Technology', 'Laggards', 'Top 10%')
    assert len(filtered) == 6 and stats['usable'] == 59 and filtered.iloc[0].symbol == 'S001'
    assert len(expanded_ranking(data.iloc[:1], '5D', size='Top 10%')[0]) == 1
    assert expanded_ranking(data, '1M', size='Top 10%')[0].empty


def test_participation_denominators_zero_sectors_and_missing():
    data = universe()
    data.loc[0, '1D'] = None
    ranking, _ = expanded_ranking(data, '1D', size='Top 10%')
    participation = sector_participation(data, ranking, '1D').set_index('sector')
    assert participation.loc['Energy', 'movers'] == 10
    assert participation.loc['Energy', 'available'] == 41
    assert participation.loc['Technology', 'movers'] == 0
    assert participation.loc['Technology', 'available'] == 59
    assert participation.loc['Energy', 'share'] == pytest.approx(10/41)
    assert (participation.movers + participation.other == participation.available).all()
    assert participation_chart(participation.reset_index()).to_dict()
    assert sector_participation(data, ranking, '1M').empty


def sample_news():
    return {'articles': [dict(title=f'News {i}', url=f'https://example.com/{i}', snippet='Reported rates news',
                             providers=[provider], published='2026-10-17')
                         for i, provider in enumerate(['Serper', 'Marketaux', 'FMP'])],
            'retrieved_at': '2026-10-17T15:00:00Z', 'warnings': ['Partial publication coverage']}


def summary_response(packet):
    return {'fingerprint': packet['fingerprint'], 'overview': 'Rates news dominates this coverage.',
            'sentiment': 'mixed', 'sentiment_reason': 'Available coverage has both supportive and cautionary themes.',
            'sentiment_evidence_ids': ['N1', 'N2'],
            'claims': [dict(interpretation='Reported rates themes differ across coverage.', market_implication='The conditional effect spans financing costs across sectors.', evidence_ids=['N1', 'N2', 'N3'])],
            'limitations': 'Headlines and snippets only; some publication dates unavailable.'}


@pytest.mark.parametrize('failure', [None, 'unknown_id', 'identity', 'truncated', 'refusal'])
def test_news_model_bounded_all_sources_and_validation(monkeypatch, failure):
    requests = []
    def client(key, **kwargs):
        assert kwargs == {'timeout': 75, 'max_retries': 0}
        def create(**options):
            requests.append(options)
            packet = json.loads(options['messages'][1]['content'])
            assert {a['providers'][0] for a in packet['articles']} == {'Serper', 'Marketaux', 'FMP'}
            result = summary_response(packet)
            if failure == 'unknown_id':
                result['claims'][0]['evidence_ids'] = ['N999']
            if failure == 'identity':
                result['fingerprint'] = 'wrong'
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason='length' if failure == 'truncated' else 'stop',
                message=SimpleNamespace(content=json.dumps(result), refusal='refused' if failure == 'refusal' else None))])
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(news_ai, 'build_openai_client', client)
    if failure:
        with pytest.raises(ValueError):
            news_ai.summarize_news(sample_news(), 'synthetic', 'gpt-5')
    else:
        assert news_ai.summarize_news(sample_news(), 'synthetic', 'gpt-5')['result']['claims']
    assert len(requests) == 1 and requests[0]['max_completion_tokens'] == 6000
    assert requests[0]['response_format']['json_schema']['strict']


def test_news_evidence_filters_unsafe_links_redacts_and_requires_inputs(monkeypatch):
    news = sample_news()
    news['articles'][0]['url'] = 'javascript:alert(1)'
    news['articles'][1]['snippet'] = 'apikey=ignored https://example.com/?apikey=privatevalue'
    packet = news_ai.news_evidence(news)
    assert len(packet['articles']) == 2 and 'privatevalue' not in str(packet)
    monkeypatch.setattr(news_ai, 'build_openai_client', lambda *a, **k: pytest.fail('No missing-input model calls'))
    with pytest.raises(ValueError):
        news_ai.summarize_news(news, '', 'gpt-5')
    with pytest.raises(ValueError):
        news_ai.summarize_news({'articles': []}, 'synthetic', 'gpt-5')


def test_market_requires_refresh_and_reuses_saved_chart_and_evidence(market_dashboard_stub, monkeypatch):
    ui, packet, charts = market_dashboard_stub
    calls = dict(dashboard=0, news=0, ribbon=0)
    cache_clears = []
    monkeypatch.setattr(ui, 'clear_history_cache', lambda: cache_clears.append('history'))
    def load(name, value):
        def action(*args):
            calls[name] += 1
            return value
        return action
    monkeypatch.setattr(ui, 'load_dashboard', load('dashboard', packet))
    monkeypatch.setattr(ui, 'load_market_news', load('news', sample_news()))
    monkeypatch.setattr(ui, 'load_ribbon', load('ribbon', {'rows': [], 'warnings': []}))
    script = 'import streamlit as st\nfrom langgraphagenticai.ui.market_dashboard import render_market_dashboard\npage=st.radio("Workspace", ["Market Brief", "Other"])\nif page == "Market Brief": render_market_dashboard("synthetic", "synthetic")'
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception and sum(calls.values()) == 0 and charts == []
    assert not cache_clears
    app.radio[0].set_value('Other').run()
    app.radio[0].set_value('Market Brief').run()
    assert sum(calls.values()) == 0
    app.button(key='intro_refresh').click().run()
    assert not app.exception and list(calls.values()) == [1, 1, 1] and len(charts) == 1
    assert cache_clears == ['history']
    app.checkbox(key='market_daily_technical_indicator_EMA').check().run()
    app.number_input(key='market_daily_technical_ema').set_value(30).run()
    app.run()
    assert list(calls.values()) == [1, 1, 1] and len(charts) == 1
    assert cache_clears == ['history']
    app.get('button_group')[0].set_value('3M').run()
    assert len(charts) == 2 and charts[-1] == ('^GSPC', '3M')
    app.radio[0].set_value('Other').run()
    app.radio[0].set_value('Market Brief').run()
    assert not app.exception and len(charts) == 2 and list(calls.values()) == [1, 1, 1]
    assert app.checkbox(key='market_daily_technical_indicator_EMA').value
    app.button(key='intro_refresh').click().run()
    assert list(calls.values()) == [2, 2, 2] and len(charts) == 3
    saved_chart = app.session_state['market_daily_saved_chart']
    monkeypatch.setattr(ui, 'load_symbol_history', lambda *a: (_ for _ in ()).throw(ValueError('Synthetic history failure')))
    app.button(key='market_daily_refresh').click().run()
    assert app.warning and app.session_state['market_daily_saved_chart'] == saved_chart
    app.run()
    assert list(calls.values()) == [2, 2, 2] and len(charts) == 3
    monkeypatch.setattr(ui, 'load_dashboard', lambda *a: (_ for _ in ()).throw(ValueError('Synthetic dashboard failure')))
    app.button(key='intro_refresh').click().run()
    assert not app.exception and app.session_state['market_evidence_snapshot']['packet'] == packet
    assert list(calls.values()) == [2, 3, 3]


def test_news_summary_explicit_rerun_failure_and_changed_evidence(monkeypatch):
    from langgraphagenticai.ui import market_news_summary as ui
    news = sample_news()
    calls = []
    def generate(news, key, model):
        calls.append(model)
        evidence = news_ai.news_evidence(news)
        return dict(result=summary_response(evidence), evidence=evidence, model=model)
    monkeypatch.setattr(ui, 'summarize_news', generate)
    monkeypatch.setitem(sys.modules, 'market_update_fixture', SimpleNamespace(news=news))
    app = AppTest.from_string('from market_update_fixture import news\nfrom langgraphagenticai.ui.market_news_summary import render_news_summary\nrender_news_summary(news,"synthetic")', default_timeout=30).run()
    assert not calls
    app.button(key='market_news_summarize').click().run()
    app.run()
    assert not app.exception and calls == ['gpt-5']
    saved = app.session_state['market_news_summary']
    news['articles'][0]['title'] = 'Changed report'
    app.run()
    assert app.warning and calls == ['gpt-5']
    monkeypatch.setattr(ui, 'summarize_news', lambda *a: (_ for _ in ()).throw(ValueError('Synthetic failure')))
    app.button(key='market_news_summarize').click().run()
    assert not app.exception and app.session_state['market_news_summary'] == saved


def test_fmp_news_merge_and_failure_isolation(monkeypatch):
    from langgraphagenticai.providers import market_brief_news as provider
    monkeypatch.setattr(provider.SerperClient, 'search', lambda *a, **k: {'ok': True, 'results': [{'title': 'Same story', 'url': 'https://example.com/a'}]})
    def get(*a, **k):
        assert k['params'] == {'page': 0, 'limit': 10 if 'general-latest' in a[0] else 5}
        return [{'title': 'Same story', 'url': 'https://example.com/a', 'text': 'FMP snippet'}]
    monkeypatch.setattr(provider, 'get_fmp_json', get)
    news = provider.load_market_news.__wrapped__('synthetic', '', 'synthetic')
    assert news['articles'][0]['providers'] == ['FMP', 'Serper']
    monkeypatch.setattr(provider, 'get_fmp_json', lambda *a, **k: (_ for _ in ()).throw(ValueError('private')))
    news = provider.load_market_news.__wrapped__('synthetic', '', 'synthetic')
    assert len(news['articles']) == 1 and any('FMP' in w for w in news['warnings'])
    assert 'private' not in str(news)


def test_movers_ranking_size_interaction_and_navigation(monkeypatch):
    from langgraphagenticai.ui import top_movers_tab as ui
    from langgraphagenticai.providers import discovery, symbol_history
    monkeypatch.setattr(ui, 'load_top_movers', lambda *a: {'universe': universe(120)})
    monkeypatch.setattr(discovery, 'load_selected_news', lambda *a: {'results': []})
    monkeypatch.setattr(discovery, 'load_selected_quote', lambda *a: {'error': 'Synthetic unavailable'})
    monkeypatch.setattr(symbol_history, 'load_symbol_history', lambda *a: {'points': []})
    script = 'import streamlit as st\nfrom langgraphagenticai.ui.top_movers_tab import render_top_movers_tab\npage=st.radio("Workspace", ["Top Movers", "Other"])\nif page == "Top Movers": render_top_movers_tab(fmp_api_key="synthetic",serper_api_key="")'
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception and len(app.dataframe[0].value) == 50
    app.selectbox(key='movers_ranking_size').set_value('Top 10%').run()
    assert len(app.dataframe[0].value) == 12
    app.selectbox(key='movers_sector_filter').set_value('Technology').run()
    assert len(app.dataframe[0].value) == 6
    app.radio[0].set_value('Other').run()
    app.radio[0].set_value('Top Movers').run()
    assert not app.exception and app.selectbox(key='movers_ranking_size').value == 'Top 10%'
    assert len(app.dataframe[0].value) == 6
