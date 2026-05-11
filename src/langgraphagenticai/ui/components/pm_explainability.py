from __future__ import annotations

import math

import pandas as pd
import streamlit as st


DISPLAY_NAME_MAP = {
    "revenue_growth": "Revenue Growth",
    "earnings_growth": "Earnings Growth",
    "operating_margin": "Operating Margin",
    "analyst_upside_pct": "Analyst Upside",
    "forward_revenue_growth": "Forward Revenue Growth",
    "forward_eps_growth": "Forward EPS Growth",
    "free_cashflow_margin": "FCF Margin",
    "operating_cashflow_margin": "OCF Margin",
    "return_on_equity": "ROE",
    "return_on_assets": "ROA",
    "ret_1m": "1M Return",
    "ret_3m": "3M Return",
    "ret_1y": "1Y Return",
    "ret_12m": "1Y Return",
    "price_vs_50dma": "% From SMA 50",
    "price_vs_200dma": "% From SMA 200",
    "drawdown_from_52w_high": "% Below 52W High",
    "distance_from_52w_low": "% Above 52W Low",
    "volume_vs_20d_avg": "Volume vs 20D Avg",
    "ann_vol_3m": "Annualized Vol 3M",
    "max_drawdown_1y": "Max Drawdown 1Y",
    "trailing_pe": "P/E TTM",
    "forward_pe": "Forward P/E",
    "price_to_sales": "P/S TTM",
    "price_to_book": "P/B TTM",
    "price_to_fcf": "P/FCF TTM",
    "enterprise_to_ebitda": "Enterprise Value / EBITDA",
    "price_target_consensus": "Price Target Consensus",
    "rating_score": "Rating Score",
    "current_ratio": "Current Ratio",
    "debt_to_equity": "Debt to Equity",
    "liabilities_to_assets": "Liabilities to Assets",
    "gross_margin": "Gross Margin",
    "profit_margin": "Net Margin",
    "ebitda_margin": "EBITDA Margin",
    "ocf_margin": "OCF Margin",
    "fcf_margin": "FCF Margin",
    "cash_conversion": "Cash Conversion",
    "earnings_yield": "Earnings Yield",
    "fcf_yield": "FCF Yield",
    "rsi_14": "RSI 14",
    "macd_line": "MACD Line",
    "macd_signal": "MACD Signal",
    "macd_hist": "MACD Hist",
    "atr_14": "ATR 14",
    "news_quality_score": "News Quality Score",
    "peer_news_score": "Peer News Score",
    "peer_news_rank": "Peer News Rank",
    "peer_reliability": "Peer Reliability",
    "peer_confidence": "Peer Confidence",
    "peer_fallback_used": "Peer Fallback Used",
    "news_overlay_used": "News Overlay Used",
    "news_data_status": "News Data Status",
    "usable_news_count": "Usable News Count",
}

PCT_METRICS = {
    "Revenue CAGR 3Y", "FCF CAGR 3Y", "Latest Operating Margin", "Latest Net Margin",
    "OCF Margin", "FCF Margin", "Cash Conversion", "ROE", "ROA", "Debt to Equity",
    "Liabilities to Assets", "Forward Revenue Growth FY+1", "Price Target Upside", "YTD Return",
    "1M Return", "3M Return", "1Y Return", "3Y Return (Price)", "5Y Return (Price)",
    "% Below 52W High", "% Above 52W Low", "% From SMA 50", "% From SMA 200",
    "Volume vs 20D Avg", "Annualized Vol 3M", "Max Drawdown 1Y", "Revenue Growth",
    "Earnings Growth", "Operating Margin", "Analyst Upside", "Forward Revenue Growth",
    "Forward EPS Growth", "Gross Margin", "Net Margin", "EBITDA Margin", "Earnings Yield",
    "FCF Yield",
}

MULTIPLE_METRICS = {
    "P/E TTM", "Forward P/E", "P/S TTM", "P/B TTM", "P/FCF TTM", "Enterprise Value / EBITDA"
}

PRICE_METRICS = {
    "Close", "Price Target Consensus", "ATR 14", "MACD Line", "MACD Signal"
}

RAW_DECIMAL_METRICS = {
    "Current Ratio", "Rating Score", "RSI 14", "News Quality Score", "Peer News Score", "Peer News Rank"
}

INTEGER_METRICS = {"Volume", "20D Avg Volume", "average_volume", "shares_outstanding"}


def _display_name(key: str) -> str:
    if key in DISPLAY_NAME_MAP:
        return DISPLAY_NAME_MAP[key]
    text = str(key).replace("_", " ").strip()
    if text.isupper():
        return text
    return text.title()


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _format_metric_value(key: str, value):
    label = _display_name(key)
    if label == 'News Overlay Used':
        return 'Yes' if bool(value) else 'No'
    if label == 'News Data Status':
        return str(value).replace('_', ' ').title() if not _is_missing(value) else 'No usable news'
    if _is_missing(value):
        if label in {'Avg News Sentiment', 'News Signal Score', 'Full Text Ratio', 'Peer News Score', 'Peer News Rank'}:
            return 'No usable news'
        return 'N/A'
    label = _display_name(key)
    try:
        v = float(value)
    except Exception:
        return str(value)

    if label in INTEGER_METRICS:
        return f"{v:,.0f}"
    if label in PCT_METRICS:
        return f"{v:.1%}"
    if label in MULTIPLE_METRICS:
        return f"{v:,.1f}x"
    if label in PRICE_METRICS:
        return f"{v:,.2f}"
    if label in RAW_DECIMAL_METRICS:
        return f"{v:,.2f}"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def _technical_signal_and_meaning(key: str, value):
    if _is_missing(value):
        return '', ''
    label = _display_name(key)
    try:
        v = float(value)
    except Exception:
        return '', ''

    if label == 'RSI 14':
        if v >= 70:
            return 'Overbought', 'Momentum is strong, but short-term pullback risk is elevated.'
        if v <= 30:
            return 'Oversold', 'Selling pressure has been heavy and the name may be stretched to the downside.'
        if v >= 55:
            return 'Bullish momentum', 'Buying pressure is constructive without being extremely stretched.'
        if v <= 45:
            return 'Weak momentum', 'Momentum is soft and buyers are not in control right now.'
        return 'Neutral', 'Momentum is balanced and does not add a strong timing signal.'

    if label == 'MACD Hist':
        if v > 0:
            return 'Bullish crossover', 'Short-term momentum is running above the signal line.'
        if v < 0:
            return 'Bearish crossover', 'Short-term momentum is running below the signal line.'
        return 'Flat momentum', 'Momentum is close to neutral versus the signal line.'

    if label == '% From SMA 50':
        if v > 0.05:
            return 'Above short-term trend', 'Price is extended above the 50-day average and trend is supportive.'
        if v > 0:
            return 'Constructive trend', 'Price is holding above the 50-day average.'
        if v > -0.05:
            return 'Near trend break', 'Price is slightly below the 50-day average and short-term trend is softening.'
        return 'Below short-term trend', 'Price is meaningfully below the 50-day average and short-term momentum is weak.'

    if label == '% From SMA 200':
        if v > 0.10:
            return 'Strong long-term trend', 'Price is comfortably above the 200-day average, supporting a stronger long-term tape.'
        if v > 0:
            return 'Above long-term trend', 'Price is above the 200-day average, which supports the longer trend.'
        if v > -0.10:
            return 'Below long-term trend', 'Price is modestly below the 200-day average and long-term trend strength is fading.'
        return 'Weak long-term trend', 'Price is materially below the 200-day average, indicating a weaker longer-term setup.'

    if label in {'1M Return', '3M Return', '1Y Return'}:
        horizon = label.split()[0]
        if v > 0.15:
            return 'Strong momentum', f'{horizon} price performance is strong and supports positive momentum.'
        if v > 0:
            return 'Positive momentum', f'{horizon} return is positive and supportive of trend-following interpretations.'
        if v > -0.10:
            return 'Soft momentum', f'{horizon} return is slightly negative and momentum support is limited.'
        return 'Negative momentum', f'{horizon} return is clearly negative and acts as a momentum headwind.'

    if label == '% Below 52W High':
        if v >= -0.05:
            return 'Near highs', 'The stock is trading close to its 52-week high, which often signals strong trend persistence.'
        if v >= -0.15:
            return 'Reasonable trend position', 'The stock is below the high but still within a healthy range of recent leadership.'
        return 'Well off highs', 'The stock is far below its 52-week high, which points to weaker trend confirmation.'

    if label == '% Above 52W Low':
        if v >= 0.50:
            return 'Far from lows', 'The stock is well above its 52-week low, reducing distress-style technical risk.'
        if v >= 0.20:
            return 'Comfortably above lows', 'The stock has a decent cushion above the low.'
        return 'Near lows', 'The stock is trading relatively close to its 52-week low and downside sensitivity remains relevant.'

    if label == 'Volume vs 20D Avg':
        if v >= 0.25:
            return 'High participation', 'Trading volume is running above normal levels, which strengthens price-action confirmation.'
        if v > 0:
            return 'Volume confirmation', 'Volume is modestly above average and supports the recent move.'
        if v > -0.20:
            return 'Light confirmation', 'Volume is a bit below average, so the move has weaker participation behind it.'
        return 'Weak participation', 'Volume is well below average, which weakens confidence in the recent move.'

    if label == 'Annualized Vol 3M':
        if v <= 0.20:
            return 'Low volatility', 'Recent price swings have been relatively contained.'
        if v <= 0.35:
            return 'Moderate volatility', 'Risk is normal for an active equity setup.'
        return 'High volatility', 'Recent price swings are elevated, so sizing and timing matter more.'

    if label == 'Max Drawdown 1Y':
        if v >= -0.15:
            return 'Controlled drawdown', 'The worst trailing drawdown has been relatively manageable.'
        if v >= -0.30:
            return 'Moderate drawdown', 'The stock has seen a meaningful pullback and path risk is notable.'
        return 'Deep drawdown', 'The stock has experienced a severe drawdown and risk tolerance should be higher.'

    if label == 'ATR 14':
        if v <= 2:
            return 'Tighter trading range', 'Average daily movement is relatively contained.'
        return 'Wider trading range', 'Average daily movement is elevated and the name may require wider risk limits.'

    return '', ''


def render_metrics_table(title: str, metrics: dict):
    st.markdown(f'#### {title}')
    if not metrics:
        st.info('No metrics available.')
        return

    is_technical = 'technical' in title.lower()
    rows = []
    for k, v in metrics.items():
        row = {
            'Metric': _display_name(k),
            'Value': _format_metric_value(k, v),
        }
        if is_technical:
            signal, meaning = _technical_signal_and_meaning(k, v)
            row['Signal'] = signal
            row['What it means'] = meaning
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_bundle_explainability(bundle):
    render_metrics_table('Fundamental metrics used', getattr(bundle.fundamentals, 'metrics', {}))
    render_metrics_table('Valuation metrics used', getattr(bundle.valuation, 'metrics', {}))
    render_metrics_table('Technical metrics used', getattr(bundle.technicals, 'metrics', {}))
    render_metrics_table('Catalyst metrics used', getattr(bundle.catalysts, 'metrics', {}))
    render_metrics_table('Earnings metrics used', getattr(bundle.earnings, 'metrics', {}))
    render_metrics_table('Risk and portfolio-fit metrics used', {
        **getattr(bundle.risk, 'metrics', {}),
        **getattr(bundle.portfolio_fit, 'metrics', {}),
    })


