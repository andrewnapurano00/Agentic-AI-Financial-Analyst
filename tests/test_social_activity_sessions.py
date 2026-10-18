"""Active-platform social statistics on exchange sessions, including FICO-shaped data."""
from datetime import datetime, timezone, date
import pytest
from langgraphagenticai.analysis.social_sentiment import normalize_snapshots, daily_statistics
from langgraphagenticai.analysis.trading_calendar import session_dates, last_trading_dates

NOW = datetime(2026, 10, 17, 20, tzinfo=timezone.utc)


def fico_rows():
    return [dict(symbol='FICO', date=f'2026-10-16 {hour:02}:00:00',
                 stocktwitsPosts=1 if hour == 19 else 0, twitterPosts=3 if hour == 19 else 0,
                 stocktwitsSentiment=.5 if hour == 19 else 0, twitterSentiment=.53955 if hour == 19 else 0,
                 stocktwitsLikes=1 if hour == 19 else 0) for hour in range(20)]


def test_no_post_zero_rows_do_not_dilute_fico_scores():
    records, _ = normalize_snapshots(fico_rows(), 'FICO', NOW)
    daily = daily_statistics(records, NOW)
    def score(platform):
        return next(r for r in daily if r['Date'] == '2026-10-16' and r['Platform'] == platform and r['Metric'] == 'Sentiment score')
    assert score('Stocktwits')['Average'] == .5
    assert score('Twitter')['Average'] == .53955
    assert score('Stocktwits')['Median'] == .5
    assert score('Stocktwits')['Observations'] == 1
    assert score('Stocktwits')['Excluded snapshots'] == 19
    assert {r['Date'] for r in daily} == {'2026-10-12','2026-10-13','2026-10-14','2026-10-15','2026-10-16'}


def test_independent_post_filters_and_optional_real_zero():
    rows = [dict(symbol='FICO',date='2026-10-16 12:00:00', stocktwitsPosts=0,stocktwitsSentiment=.7,
                 twitterPosts=2,twitterSentiment=0,twitterLikes=0)]
    records, _ = normalize_snapshots(rows, 'FICO', NOW)
    recent = [r for r in daily_statistics(records, NOW) if r['Date']=='2026-10-16']
    assert all(r['Average'] is None for r in recent if r['Metric']=='Sentiment score')
    likes = next(r for r in recent if r['Platform']=='Twitter' and r['Metric']=='Likes')
    assert likes['Average'] == 0
    included = daily_statistics(records, NOW, hide_zero_sentiment=False)
    twitter = next(r for r in included if r['Date']=='2026-10-16' and r['Platform']=='Twitter' and r['Metric']=='Sentiment score')
    assert twitter['Average'] == 0 and twitter['Observations'] == 1
    assert records[0]['twitterSentiment'] == 0  # No destructive correction of provider facts.


def test_exchange_sessions_exclude_weekends_holidays_and_special_closures():
    assert last_trading_dates(date(2026,10,17)) == ['2026-10-12','2026-10-13','2026-10-14','2026-10-15','2026-10-16']
    assert '2026-07-03' not in session_dates(date(2026,7,1),date(2026,7,6))
    assert '2026-04-03' not in session_dates(date(2026,4,1),date(2026,4,6))  # Good Friday
    assert '2025-01-09' not in session_dates(date(2025,1,8),date(2025,1,10))  # Exceptional closure
    assert '2026-10-12' in session_dates(date(2026,10,12),date(2026,10,12))  # Not a stock-market holiday


def test_historical_window_also_excludes_weekend_records_and_us_holidays():
    rows = [dict(symbol='FICO',date=day+' 12:00:00',twitterPosts=2,twitterSentiment=.7)
            for day in ['2026-07-02','2026-07-03','2026-07-04','2026-07-05','2026-07-06']]
    records, _ = normalize_snapshots(rows,'FICO',NOW)
    daily = daily_statistics(records,NOW,'Latest 5 reported trading dates')
    assert {r['Date'] for r in daily} == {'2026-07-02','2026-07-06'}


def test_aware_records_group_in_new_york_trading_date():
    records, _ = normalize_snapshots([dict(symbol='FICO',date='2026-10-17T01:00:00Z',twitterPosts=2,twitterSentiment=.7)],'FICO',NOW)
    daily = daily_statistics(records,NOW)
    row = next(r for r in daily if r['Date']=='2026-10-16' and r['Platform']=='Twitter' and r['Metric']=='Sentiment score')
    assert row['Average'] == .7


def test_minimum_posts_validation_and_threshold():
    records, _ = normalize_snapshots(fico_rows(),'FICO',NOW)
    assert all(r['Average'] is None for r in daily_statistics(records,NOW,min_posts=4))
    with pytest.raises(ValueError):
        daily_statistics(records,NOW,min_posts=0)


def test_ui_migrates_saved_window_and_activity_controls_recompute_without_loading(monkeypatch):
    from hashlib import sha256
    from streamlit.testing.v1 import AppTest
    from langgraphagenticai.ui import social_sentiment as ui
    class Clock:
        @staticmethod
        def now(tz=None):
            return NOW
    monkeypatch.setattr(ui,'datetime',Clock)
    rows = [dict(symbol='FICO',date='2026-10-16 12:00:00',stocktwitsPosts=1,stocktwitsSentiment=.5),
            dict(symbol='FICO',date='2026-10-16 13:00:00',stocktwitsPosts=1,stocktwitsSentiment=0)]
    records, diagnostics = normalize_snapshots(rows,'FICO',NOW)
    monkeypatch.setattr(ui,'load_social_sentiment',lambda *a,**k: pytest.fail('Saved activity controls must not collect'))
    app = AppTest.from_string('from langgraphagenticai.ui.social_sentiment import render_social_sentiment\nrender_social_sentiment("FICO","synthetic")',default_timeout=30)
    app.session_state['movers_social_results'] = {(sha256(b'synthetic').hexdigest(),'FICO'): dict(symbol='FICO',records=records,diagnostics=diagnostics,page_budget=5,warnings=[])}
    app.session_state['movers_social_preferences'] = {'window':'Last 5 calendar days'}
    app.session_state['movers_social_window'] = 'Last 5 calendar days'
    app.run()
    assert not app.exception and app.selectbox(key='movers_social_window').value == 'Last 5 trading days'
    assert app.metric[0].value == '0.5000'
    app.checkbox(key='movers_social_hide_zero').uncheck().run()
    assert not app.exception and app.metric[0].value == '0.2500'
    app.number_input(key='movers_social_min_posts').set_value(2).run()
    assert not app.exception and app.metric[0].value == 'Unavailable'
