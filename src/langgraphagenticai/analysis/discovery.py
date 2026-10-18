"""Deterministic finite, period-aware discovery ranking and sector aggregates."""
import pandas as pd
from math import ceil
from langgraphagenticai.providers.discovery_numbers import finite_number

PERIODS = ("1D", "5D", "1M", "ytd")
RANKING_SIZES = ("Top 50 stocks", "Top 10%")


def expanded_ranking(universe, period="5D", sector="All sectors", direction="Leaders", size="Top 50 stocks"):
    """Apply filters before choosing a fixed or rounded-up percentile count."""
    if size not in RANKING_SIZES:
        raise ValueError("Unsupported ranking size.")
    pool, stats = rank_discovery(universe, period, sector, direction, limit=len(universe))
    limit = 50 if size == "Top 50 stocks" else ceil(len(pool) / 10)
    return pool.head(limit).reset_index(drop=True), stats


def sector_participation(universe, ranking, period, sector="All sectors"):
    """Count unique usable screened stocks per sector; never imply full-market coverage."""
    pool, _ = rank_discovery(universe, period, sector, limit=len(universe))
    pool = pool.drop_duplicates("symbol").copy()
    pool["sector"] = pool["sector"].fillna("Unknown").astype(str)
    selected = set(ranking["symbol"]) if not ranking.empty else set()
    pool["in_ranking"] = pool["symbol"].isin(selected).astype(int)
    result = pool.groupby("sector").agg(available=("symbol", "count"), movers=("in_ranking", "sum")).reset_index()
    result["other"] = result["available"] - result["movers"]
    result["share"] = result["movers"] / result["available"]
    return result.sort_values(["share", "sector"], ascending=[False, True]).reset_index(drop=True)


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
