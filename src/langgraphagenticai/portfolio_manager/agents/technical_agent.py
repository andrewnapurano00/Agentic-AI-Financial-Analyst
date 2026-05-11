from __future__ import annotations

from langgraphagenticai.portfolio_manager.schemas import TechnicalResult
from langgraphagenticai.portfolio_manager.scoring import clip_score, pct_to_score, weighted_average


def run_technical_agent(ticker: str, data: dict) -> TechnicalResult:
    ret_3m = data.get('ret_3m')
    rel_3m = data.get('rel_3m_vs_benchmark')
    px_50 = data.get('price_vs_50dma')
    px_200 = data.get('price_vs_200dma')
    rsi = data.get('rsi_14')
    macd_hist = data.get('macd_hist')
    vol = data.get('ann_vol_3m')
    dd = data.get('max_drawdown_1y')
    vol_ratio = data.get('volume_vs_20d_avg')

    trend_score = weighted_average([
        (pct_to_score(px_50, -0.15, 0.18), 0.45),
        (pct_to_score(px_200, -0.20, 0.28), 0.55),
    ])
    momentum_score = weighted_average([
        (pct_to_score(ret_3m, -0.20, 0.35), 0.38),
        (pct_to_score(rel_3m, -0.15, 0.20), 0.32),
        (pct_to_score(macd_hist, -0.5, 0.5), 0.15),
        (pct_to_score(rsi, 38, 68), 0.15),
    ])
    risk_score = weighted_average([
        (pct_to_score(vol, 0.12, 0.58, invert=True), 0.55),
        (pct_to_score(abs(dd) if dd is not None else None, 0.05, 0.48, invert=True), 0.45),
    ])
    confirmation_score = weighted_average([
        (pct_to_score(vol_ratio, 0.7, 1.6), 0.35),
        (pct_to_score(rsi, 42, 66), 0.30),
        (pct_to_score(px_50, -0.10, 0.15), 0.35),
    ])
    score = weighted_average([
        (trend_score, 0.34),
        (momentum_score, 0.30),
        (risk_score, 0.20),
        (confirmation_score, 0.16),
    ])

    if trend_score >= 6.6 and momentum_score >= 6.0:
        trend = 'bullish'
    elif trend_score <= 4.0:
        trend = 'bearish'
    else:
        trend = 'neutral'

    if momentum_score >= 6.1:
        momentum = 'positive'
    elif momentum_score <= 4.0:
        momentum = 'negative'
    else:
        momentum = 'neutral'

    if score >= 7.0:
        timing = 'constructive'
        signal_meaning = 'Trend and momentum are supportive enough for new buying.'
    elif score >= 5.2:
        timing = 'mixed'
        signal_meaning = 'Technicals are not broken, but the timing edge is only moderate.'
    else:
        timing = 'weak'
        signal_meaning = 'Price action does not currently support aggressive adds.'

    summary, risks = [], []
    if trend == 'bullish':
        summary.append('Price is holding above key moving averages, supporting the broader trend.')
    elif trend == 'neutral':
        summary.append('Trend is mixed, with the stock lacking a decisive long-term breakout setup.')
    else:
        risks.append('Price is below at least one key moving average, which weakens the trend backdrop.')

    if momentum == 'positive':
        summary.append('Relative momentum versus the benchmark remains supportive.')
    elif momentum == 'negative':
        risks.append('Recent momentum is lagging the benchmark and reduces near-term timing conviction.')

    if rsi is not None and rsi > 72:
        risks.append('RSI is elevated, which increases short-term overbought risk.')
    elif rsi is not None and rsi < 35:
        risks.append('RSI is washed out, reflecting a weak recent tape.')

    if dd is not None and dd < -0.25:
        risks.append('The stock has experienced a deep drawdown, implying higher path risk.')

    if not summary:
        summary.append('Technical picture is mixed and does not offer a high-conviction timing edge.')

    return TechnicalResult(
        thesis=("bullish" if score >= 6.7 else "bearish" if score <= 4.4 else "neutral"),
        conviction=("high" if trend == "bullish" and momentum == "positive" else "medium"),
        evidence_for=summary[:3],
        evidence_against=risks[:3],
        action_preference=("Buy" if score >= 6.8 else "Hold" if score >= 4.8 else "Watchlist"),
        challenge_points=["Confirm whether the recent tape is being supported by volume and not just short-covering."],
        data_gaps=[] if rsi is not None else ["Some technical features are missing, which lowers timing confidence."],
        ticker=ticker,
        score=clip_score(score),
        verdict=timing,
        trend=trend,
        momentum=momentum,
        timing=timing,
        summary=summary[:3],
        risks=risks[:3],
        metrics={
            'technical_signal_meaning': signal_meaning,
            'trend_score': trend_score,
            'momentum_score': momentum_score,
            'risk_score': risk_score,
            'confirmation_score': confirmation_score,
            '1M Return': data.get('ret_1m'),
            '3M Return': ret_3m,
            '1Y Return': data.get('ret_1y'),
            '% Below 52W High': data.get('drawdown_from_52w_high'),
            '% Above 52W Low': data.get('distance_from_52w_low'),
            'RSI 14': rsi,
            'MACD Line': data.get('macd_line'),
            'MACD Signal': data.get('macd_signal'),
            'MACD Hist': macd_hist,
            '% From SMA 50': px_50,
            '% From SMA 200': px_200,
            'ATR 14': data.get('atr_14'),
            'Volume vs 20D Avg': vol_ratio,
            'Annualized Vol 3M': vol,
            'Max Drawdown 1Y': dd,
        },
    )
