from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


def render_score_bar_chart(df: pd.DataFrame) -> None:
    if df is None or df.empty or "ticker" not in df.columns or "composite_score" not in df.columns:
        return
    plot_df = df[["ticker", "composite_score"]].copy().head(15)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(plot_df["ticker"].astype(str), pd.to_numeric(plot_df["composite_score"], errors="coerce"))
    ax.set_title("Composite Scores")
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)


def render_price_chart(prices: pd.DataFrame, tickers: list[str]) -> None:
    if prices is None or prices.empty:
        return
    keep = [t for t in tickers if t in prices.columns][:6]
    if not keep:
        return
    fig, ax = plt.subplots(figsize=(10, 4))
    indexed = prices[keep].dropna(how="all").copy()
    indexed = indexed / indexed.iloc[0] - 1
    indexed.plot(ax=ax)
    ax.set_title("Normalized Price Performance")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
