"""Offline paginated social evidence, daily math and selected-ticker UI reuse."""
from datetime import datetime, timedelta, timezone
import json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis.social_sentiment import normalize_snapshots, daily_statistics
from langgraphagenticai.providers import social_sentiment as provider

NOW = datetime(2026, 10, 17, 20, tzinfo=timezone.utc)


def snapshot(date='2026-10-17 12:00:00', symbol='AAA', **fields):
    return dict(date=date, symbol=symbol, stocktwitsSentiment=0, twitterSentiment=.6,
                stocktwitsPosts=0, twitterPosts=20, **fields)


def test_normalization_preserves_zero_rejects_bad_identity_values_and_future():
    rows = [snapshot(), snapshot('2026-10-17 13:00:00'),
            {'symbol': 'AAA', 'date': '2026-10-17 14:00:00', 'twitterSentiment': True, 'stocktwitsLikes': -1},
            snapshot(symbol='BBB'), snapshot('bad'), snapshot('2026-10-18'),
            snapshot('2026-10-17T21:00:00Z')]
    normalized, diagnostics = normalize_snapshots(rows, 'AAA', NOW)
    assert len(normalized) == 2 and normalized[0]['stocktwitsSentiment'] == 0
    assert normalized[0]['stocktwitsPosts'] == 0 and normalized[0]['twitterLikes'] is None
    assert diagnostics['rejected_rows'] == 5 and diagnostics['invalid_values'] == 2
    assert normalized[0]['timezone'].startswith('Unknown')


def test_equivalent_duplicate_timestamps_and_conflicts_do_not_bias_means():
    row = snapshot()
    conflict = {**snapshot('2026-10-17 13:00:00'), 'twitterSentiment': .8}
    records, diagnostics = normalize_snapshots([row, {**row, 'date': '2026-10-17T12:00:00'},
                                              snapshot('2026-10-17 13:00:00'), conflict], 'AAA', NOW)
    assert len(records) == 1
    assert diagnostics['duplicate_rows'] == 2 and diagnostics['conflicting_timestamps'] == 1


def test_offset_normalization_and_unknown_zone_same_day_policy():
    records, _ = normalize_snapshots([snapshot('2026-10-17T00:30:00+02:00'), snapshot('2026-10-17 23:00:00')], 'AAA', NOW)
    assert records[0]['day'] == '2026-10-16' and records[0]['timezone'].startswith('UTC')
    assert records[1]['day'] == '2026-10-17'  # Naive intraday timing cannot be compared with UTC.


def test_daily_average_median_and_missing_dates_independent_platform_counts():
    rows = [{**snapshot('2026-10-16 12:00:00'), 'stocktwitsSentiment': .25, 'stocktwitsPosts': 1},
            {**snapshot('2026-10-16 13:00:00'), 'stocktwitsSentiment': 1, 'stocktwitsPosts': 100},
            {**snapshot('2026-10-16 14:00:00'), 'stocktwitsSentiment': 1, 'stocktwitsPosts': 1, 'twitterSentiment': None}]
    records, _ = normalize_snapshots(rows, 'AAA', NOW)
    daily = pd.DataFrame(daily_statistics(records, NOW))
    score = daily[(daily.Date == '2026-10-16') & (daily.Platform == 'Stocktwits') & (daily.Metric == 'Sentiment score')].iloc[0]
    assert score.Average == pytest.approx(.75) and score.Median == 1 and score.Observations == 3
    tw = daily[(daily.Date == '2026-10-16') & (daily.Platform == 'Twitter') & (daily.Metric == 'Sentiment score')].iloc[0]
    assert tw.Observations == 2 and tw.Snapshots == 3 and tw.Average == .6
    missing = daily[daily.Date == '2026-10-13']
    assert missing.Average.isna().all() and missing.Observations.eq(0).all()
    assert daily.Date.nunique() == 5


def test_latest_reported_window_does_not_mislabel_stale_as_last_five_days():
    records, _ = normalize_snapshots([snapshot('2026-10-01 12:00:00')], 'AAA', NOW)
    assert not any(r['Average'] is not None for r in daily_statistics(records, NOW))
    history = daily_statistics(records, NOW, 'Latest 5 reported trading dates')
    assert {r['Date'] for r in history} == {'2026-10-01'}


def test_pagination_overlapping_pages_and_empty_terminal_page(monkeypatch):
    pages, calls = [[snapshot()], [snapshot(), snapshot('2026-10-16')], []], []
    def get(url, **kwargs):
        calls.append(kwargs['params'])
        assert kwargs['timeout'] == (5, 20) and 'apikey' not in url
        return pages[kwargs['params']['page']]
    monkeypatch.setattr(provider, 'get_fmp_json', get)
    result = provider._collect.__wrapped__('AAA', 'synthetic-secret', 5)
    assert [c['page'] for c in calls] == [0, 1, 2]
    assert len(result['records']) == 2 and result['diagnostics']['duplicate_rows'] == 1
    assert result['pagination_end'] == 'empty_page' and 'synthetic-secret' not in json.dumps(result)


@pytest.mark.parametrize('ending', ['failure', 'repeated', 'limit', 'malformed'])
def test_partial_pagination_retains_success_and_respects_bounds(monkeypatch, ending):
    calls = []
    def get(url, **kwargs):
        page = kwargs['params']['page']
        calls.append(page)
        if page and ending == 'failure':
            raise ValueError('https://example.com/?apikey=do-not-emit')
        if page and ending == 'malformed':
            return {'error': 'do-not-emit'}
        return [snapshot() if ending == 'repeated' else snapshot(f'2026-10-{17-page:02} 12:00:00')]
    monkeypatch.setattr(provider, 'get_fmp_json', get)
    result = provider._collect.__wrapped__('AAA', 'synthetic', 3)
    assert result['records'] and result['status'] == 'partial' and len(calls) <= 3
    assert result['warnings'] and 'do-not-emit' not in json.dumps(result)


def test_record_budget_and_validation_before_transport(monkeypatch):
    monkeypatch.setattr(provider, 'MAX_RECORDS', 2)
    monkeypatch.setattr(provider, 'get_fmp_json', lambda *a, **k: [snapshot(), snapshot('2026-10-16'), snapshot('2026-10-15')])
    result = provider._collect.__wrapped__('AAA', 'synthetic', 5)
    assert len(result['records']) == 2 and result['pagination_end'] == 'record_limit'
    monkeypatch.setattr(provider, '_collect', lambda *a, **k: pytest.fail('No invalid-input transport'))
    for symbol, key, pages in [('AAA?apikey=bad', 'fake', 5), ('AAA', '', 5), ('AAA', 'fake', 11), ('AAA', 'fake', True)]:
        with pytest.raises(ValueError):
            provider.load_social_sentiment(symbol, key, pages)


def test_credential_symbol_cache_and_explicit_refresh(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(kwargs['params'])
        return [snapshot(symbol=kwargs['params']['symbol'])] if kwargs['params']['page'] == 0 else []
    monkeypatch.setattr(provider, 'get_fmp_json', get)
    provider._collect.clear()
    try:
        provider.load_social_sentiment(' aaa ', 'tenant-one', 3)
        provider.load_social_sentiment('AAA', 'tenant-one', 3)
        assert len(calls) == 2
        provider.load_social_sentiment('AAA', 'tenant-one', 3, refresh=True)
        assert len(calls) == 4
        provider.load_social_sentiment('AAA', 'tenant-two', 3)
        provider.load_social_sentiment('BBB', 'tenant-one', 3)
        assert len(calls) == 8
    finally:
        provider._collect.clear()


def test_ui_explicit_load_controls_ticker_switch_and_failure_recovery(monkeypatch):
    from langgraphagenticai.ui import social_sentiment as ui
    calls, fail = [], {'empty': False}
    def load(symbol, key, pages, **kwargs):
        calls.append((symbol, pages))
        now = datetime.now(timezone.utc)
        rows = [snapshot((now.date()-timedelta(days=i)).isoformat()+' 00:00:00', symbol) for i in range(5)]
        records, diagnostics = normalize_snapshots(rows, symbol, now)
        return dict(symbol=symbol, records=[] if fail['empty'] else records, diagnostics=diagnostics,
                    warnings=[], page_budget=pages, retrieved_at=now.isoformat())
    monkeypatch.setattr(ui, 'load_social_sentiment', load)
    script = 'import streamlit as st\nfrom langgraphagenticai.ui.social_sentiment import render_social_sentiment\nsymbol=st.selectbox("Ticker", ["AAA","BBB"])\nrender_social_sentiment(symbol,st.session_state.get("qa_key","synthetic"))'
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception and not calls
    app.button(key='movers_social_load').click().run()
    assert not app.exception and calls == [('AAA', 5)]
    app.selectbox(key='movers_social_metric').set_value('Posts').run()
    app.radio(key='movers_social_statistic').set_value('Median').run()
    app.selectbox(key='movers_social_window').set_value('Latest 5 reported trading dates').run()
    assert not app.exception and len(calls) == 1
    app.selectbox[0].set_value('BBB').run()
    assert not app.dataframe and len(calls) == 1
    app.button(key='movers_social_load').click().run()
    assert calls[-1] == ('BBB', 5)
    app.selectbox[0].set_value('AAA').run()
    assert app.dataframe and len(calls) == 2
    assert app.selectbox(key='movers_social_metric').value == 'Posts'
    assert app.radio(key='movers_social_statistic').value == 'Median'
    fail['empty'] = True
    app.button(key='movers_social_load').click().run()
    assert not app.exception and app.dataframe and any('previously saved' in w.value for w in app.warning)
    app.session_state['qa_key'] = 'other-tenant'
    app.run()
    assert not app.dataframe and len(calls) == 3
