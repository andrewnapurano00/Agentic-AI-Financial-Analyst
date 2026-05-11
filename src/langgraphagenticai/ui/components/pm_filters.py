from __future__ import annotations

import streamlit as st


def render_pm_sidebar_defaults(default_watchlist: str, default_period: str = "2y") -> dict:
    st.header("Portfolio Settings")
    benchmark = st.text_input("Benchmark", value="SPY").upper().strip()
    watchlist = st.text_area("Extra tickers to compare", value=default_watchlist, height=90)
    period = st.selectbox("Price history window", ["1y", "2y", "5y"], index=["1y", "2y", "5y"].index(default_period))
    enable_news = st.checkbox("Enable MarketAux news overlay", value=True)
    news_lookback_days = st.slider("News lookback days", 3, 21, 7, 1)
    enable_ai = st.checkbox("Enable AI commentary", value=True)
    max_weight = st.slider("Maximum position weight", 0.08, 0.30, 0.18, 0.01)
    run_button = st.button("Run multi-agent engine", type="primary")
    return {
        "benchmark": benchmark,
        "watchlist": watchlist,
        "period": period,
        "enable_news": enable_news,
        "news_lookback_days": news_lookback_days,
        "enable_ai": enable_ai,
        "max_weight": max_weight,
        "run_button": run_button,
    }
