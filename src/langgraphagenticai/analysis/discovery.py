"""Deterministic finite, period-aware discovery ranking and sector aggregates."""
import pandas as pd
from langgraphagenticai.providers.discovery_numbers import finite_number

PERIODS = ("1D", "5D", "1M", "ytd")


def rank_discovery(universe, period="5D", sector="All sectors", direction="Leaders", limit=12):
    if period not in PERIODS:
        raise ValueError("Unsupported performance period.")
    pool = universe.copy()
    if period not in pool:
        pool[period] = float("nan")
    pool[period] = pd.to_numeric(pool[period].map(finite_number), errors="coerce")
    pool = pool.dropna(subset=[period])
    if sector != "All sectors":
        pool = pool[pool["sector"].astype(str) == sector]
    pool = pool.sort_values([period, "symbol"], ascending=[direction != "Leaders", True])
    return pool.head(limit).reset_index(drop=True), {
        "usable": len(pool), "advancing": float((pool[period] > 0).mean() * 100) if len(pool) else None,
        "median": float(pool[period].median()) if len(pool) else None,
    }


def sector_summary(universe, period="5D"):
    pool, _ = rank_discovery(universe, period, limit=len(universe))
    return pool.groupby("sector", dropna=False).agg(
        mean_return=(period, "mean"), median_return=(period, "median"), stocks=("symbol", "count")
    ).reset_index().sort_values("mean_return", ascending=False)
