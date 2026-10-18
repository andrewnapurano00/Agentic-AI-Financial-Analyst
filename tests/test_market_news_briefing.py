"""Article text, qualitative sentiment and top-of-page briefing contracts."""
import json
import sys
from types import SimpleNamespace
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.providers.article_text import normalize_article_body, MAX_ARTICLE_CHARS, safe_news_url
from langgraphagenticai.analysis.market_news_ai import news_evidence, summarize_news
from test_market_updates import sample_news, summary_response


def test_provider_html_is_text_redacted_and_bounded():
    assert not safe_news_url('https://example.com/news?api_token=private')
    assert not safe_news_url('https://user:password@example.com/news')
    assert safe_news_url('https://example.com/news?id=1')
    result = normalize_article_body('<h1>Rates &amp; growth</h1><script>bad()</script><style>hidden</style><p>https://example.com/?apikey=privatekey</p>')
    assert 'Rates & growth' in result['article_text']
    assert 'bad()' not in result['article_text'] and '<h1>' not in result['article_text']
    assert 'hidden' not in result['article_text'] and 'privatekey' not in result['article_text']
    assert 'completeness unverified' in result['content_basis']
    result = normalize_article_body('x'*(MAX_ARTICLE_CHARS+1))
    assert len(result['article_text']) == MAX_ARTICLE_CHARS and result['content_truncated']
    assert normalize_article_body(None)['content_basis'] == 'Headline/snippet only'


def test_article_body_identity_and_model_excerpt_coverage():
    news = sample_news()
    news['articles'][0].update(article_text='Full provider text '*500, content_source='FMP Articles API', content_retrieved_at='2026-10-17')
    packet = news_evidence(news)
    body = packet['articles'][0]
    assert len(body['article_text']) == 6000 and body['content_truncated']
    assert body['content_source'] == 'FMP Articles API'
    assert packet['articles'][1]['content_basis'] == 'Headline/snippet only'
    news['articles'][0]['article_text'] = 'Changed article content'
    assert news_evidence(news)['fingerprint'] != packet['fingerprint']


@pytest.mark.parametrize('bad_tone,bad_reference', [(True, False), (False, True)])
def test_sentiment_enum_and_sentiment_sources_are_validated(monkeypatch, bad_tone, bad_reference):
    from langgraphagenticai.analysis import market_news_ai as ai
    def create(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        result = summary_response(packet)
        if bad_tone:
            result['sentiment'] = 'guaranteed rally'
        if bad_reference:
            result['sentiment_evidence_ids'] = ['N999']
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=json.dumps(result), refusal=None))])
    monkeypatch.setattr(ai, 'build_openai_client', lambda *a, **k: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with pytest.raises(ValueError):
        summarize_news(sample_news(), 'synthetic', 'gpt-5')


def test_fmp_bodies_independent_of_general_news_and_dedup_metadata(monkeypatch):
    from langgraphagenticai.providers import market_brief_news as provider
    monkeypatch.setattr(provider.SerperClient, 'search', lambda *a, **k: {'ok': True, 'results': [{'title': 'Rates', 'url': 'https://example.com/rates'}]})
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        if 'general-latest' in url:
            raise ValueError('Synthetic unavailable feed')
        assert kwargs['params'] == {'page': 0, 'limit': 5}
        return [{'title': 'Rates', 'link': 'https://example.com/rates', 'content': '<p>Broader market rates article.</p>', 'date': '2026-10-17'}]
    monkeypatch.setattr(provider, 'get_fmp_json', get)
    result = provider.load_market_news.__wrapped__('synthetic', '', 'synthetic')
    assert len(calls) == 2 and len(result['articles']) == 1
    article = result['articles'][0]
    assert article['providers'] == ['FMP', 'Serper']
    assert article['article_text'] == 'Broader market rates article.'
    assert article['content_source'] == 'FMP Articles API' and article['content_retrieved_at']
    assert result['warnings']


def test_news_briefing_near_top_with_preview_disclosure_and_no_duplicate(market_dashboard_stub, monkeypatch):
    ui, packet, calls = market_dashboard_stub
    news = sample_news()
    news['articles'][0]['article_text'] = 'Provider rates article'
    monkeypatch.setattr(ui, 'load_market_news', lambda *a: news)
    app = AppTest.from_string('from langgraphagenticai.ui.market_dashboard import render_market_dashboard\nrender_market_dashboard()', default_timeout=30).run()
    assert not app.button(key='intro_refresh').disabled
    app.button(key='intro_refresh').click().run()
    headings = [s.value for s in app.subheader]
    assert headings.index('Market news & sentiment') < headings.index('Sector heatmap')
    assert len([b for b in app.button if b.key == 'market_news_summarize']) == 1
    assert any('1 with provider article text' in c.value for c in app.caption)
    assert app.button(key='market_news_summarize').disabled  # No implicit model dependency.


def test_legacy_saved_news_readable_without_generation(monkeypatch):
    from langgraphagenticai.ui import market_news_summary as ui
    news = sample_news()
    legacy = news_evidence(news)
    legacy['version'] = 'news-v1'
    result = {'fingerprint': legacy['fingerprint'], 'claims': [{'interpretation': 'Prior saved text', 'evidence_ids': ['N1']}], 'limitations': 'Old preview-only coverage'}
    monkeypatch.setitem(sys.modules, 'legacy_news_fixture', SimpleNamespace(news=news))
    monkeypatch.setattr(ui, 'summarize_news', lambda *a: pytest.fail('No implicit generation'))
    app = AppTest.from_string('from legacy_news_fixture import news\nfrom langgraphagenticai.ui.market_news_summary import render_news_summary\nrender_news_summary(news)', default_timeout=30)
    app.session_state['market_news_summary'] = {'result': result, 'evidence': legacy, 'model': 'gpt-5'}
    app.run()
    assert not app.exception and any('Previously saved' in i.value for i in app.info)
    assert app.session_state['market_news_summary']['result'] == result
