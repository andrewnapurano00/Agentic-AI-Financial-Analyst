from __future__ import annotations

import pandas as pd


def split_recommendation_buckets(recommendation_table: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if recommendation_table is None or recommendation_table.empty:
        empty = pd.DataFrame()
        return {'add': empty, 'hold': empty, 'trim': empty, 'sell': empty, 'watchlist': empty, 'avoid': empty}
    df = recommendation_table.copy()
    action = df['final_action'].astype(str).str.lower().str.strip()
    return {
        'add': df[action.isin(['strong buy', 'buy', 'add', 'start / rotate in'])].reset_index(drop=True),
        'hold': df[action.isin(['hold'])].reset_index(drop=True),
        'trim': df[action.isin(['trim'])].reset_index(drop=True),
        'sell': df[action.isin(['sell', 'exit'])].reset_index(drop=True),
        'watchlist': df[action.isin(['watchlist'])].reset_index(drop=True),
        'avoid': df[action.isin(['avoid'])].reset_index(drop=True),
    }
