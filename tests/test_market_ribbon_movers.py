import pandas as pd
from langgraphagenticai.providers import ticker_ribbon as provider
from langgraphagenticai.ui.ticker_ribbon import ribbon_html
from langgraphagenticai.ui.movers_heatmap import concentration_rows, concentration_chart
from langgraphagenticai.analysis.discovery import rank_discovery


def test_ribbon_membership_partial_quotes_and_zero(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        if 'constituent' in url:
            return [{'symbol': 'aaa'}, {'symbol': 'bad/<script>'}, {'symbol': 'AAA'}, {'symbol': 'BBB'}]
        return [{'symbol': 'AAA', 'price': 10, 'changesPercentage': 0, 'timestamp': 1},
                {'symbol': 'BBB', 'price': float('nan')}, {'symbol': 'OTHER', 'price': 20}]
    monkeypatch.setattr(provider, 'get_fmp_json', get)
    provider.load_members.clear()
    packet = provider.load_ribbon.__wrapped__('synthetic')
    assert packet['requested'] == 2
    assert len(calls) == 2
    assert len(packet['rows']) == 1 and packet['rows'][0]['change'] == 0
    assert '+0.00%' in ribbon_html(packet['rows'])
    assert 'prefers-reduced-motion' in ribbon_html(packet['rows'])
    provider.load_members.clear()


def test_ribbon_escaping_and_failure(monkeypatch):
    html = ribbon_html([dict(symbol='<script>', price=10, change=-2, as_of='" onmouseover="x')])
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert '#e2747e' in html and '-2.00%' in html
    monkeypatch.setattr(provider, 'load_members', lambda _: (_ for _ in ()).throw(ValueError('secret')))
    packet = provider.load_ribbon.__wrapped__('synthetic')
    assert packet['warnings'] and 'secret' not in str(packet)
    assert not provider.load_ribbon.__wrapped__('')['rows']


def test_heatmap_tracks_ranking_period_direction_sector():
    universe = pd.DataFrame([dict(symbol='AAA', sector='Technology', **{'1D': 2, '5D': -3}),
                            dict(symbol='BBB', sector='Energy', **{'1D': -1, '5D': 5}),
                            dict(symbol='CCC', sector='Energy', **{'1D': 0, '5D': None})])
    frame, _ = rank_discovery(universe, '1D', limit=2)
    rows = concentration_rows(frame, '1D')
    assert sum(r['stocks'] for r in rows) == 2
    assert sum(r['share'] for r in rows) == 1
    assert rows[0]['sector'] == 'Technology'
    frame, _ = rank_discovery(universe, '5D', direction='Laggards', limit=1)
    rows = concentration_rows(frame, '5D')
    assert rows[0]['mean'] == -3 and rows[0]['share'] == 1
    assert concentration_chart(rows).to_dict()
    assert not concentration_rows(frame.iloc[:0], '5D')
