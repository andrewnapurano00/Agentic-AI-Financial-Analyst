from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


SECTOR_ETFS = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]


def _safe_float(x: Any, default: float | None = None) -> float | None:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def _compute_rsi(series: pd.Series, period: int = 14) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < period + 1:
        return None
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    try:
        return float(rsi.dropna().iloc[-1])
    except Exception:
        return None


def _compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[float | None, float | None, float | None]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < slow + signal:
        return None, None, None
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    try:
        return float(macd.iloc[-1]), float(sig.iloc[-1]), float(hist.iloc[-1])
    except Exception:
        return None, None, None


def compute_position_snapshot(holdings_df: pd.DataFrame, last_prices: pd.Series, company_info: dict[str, dict[str, Any]]) -> pd.DataFrame:
    if holdings_df is None or holdings_df.empty:
        return pd.DataFrame(columns=["ticker", "shares", "last_price", "market_value", "current_weight", "sector", "industry", "company_name"])
    prices = pd.to_numeric(last_prices, errors="coerce") if last_prices is not None else pd.Series(dtype=float)
    rows: list[dict[str, Any]] = []
    for _, row in holdings_df.iterrows():
        ticker = str(row.get("ticker") or "").upper().strip()
        shares = _safe_float(row.get("shares"), 0.0) or 0.0
        last_price = _safe_float(prices.get(ticker), 0.0) or 0.0
        info = company_info.get(ticker, {}) if isinstance(company_info, dict) else {}
        rows.append(
            {
                "ticker": ticker,
                "shares": shares,
                "last_price": last_price,
                "market_value": shares * last_price,
                "sector": str(info.get("sector") or info.get("sectorDisp") or "Unknown"),
                "industry": str(info.get("industry") or "Unknown"),
                "company_name": str(info.get("longName") or info.get("shortName") or ticker),
            }
        )
    out = pd.DataFrame(rows)
    total = float(out["market_value"].sum()) if not out.empty else 0.0
    out["current_weight"] = out["market_value"] / total if total > 0 else 0.0
    return out.sort_values("market_value", ascending=False).reset_index(drop=True)


def build_asset_feature_table(
    prices: pd.DataFrame,
    company_info: dict[str, dict[str, Any]],
    benchmark_col: str,
    news_summary: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if prices is None or prices.empty:
        return pd.DataFrame()

    work = prices.copy().sort_index().ffill().dropna(how="all")
    benchmark = benchmark_col if benchmark_col in work.columns else work.columns[0]
    bench_series = pd.to_numeric(work[benchmark], errors="coerce")
    bench_ret_3m = bench_series.pct_change(63).iloc[-1] if len(bench_series) >= 64 else np.nan

    news_map: dict[str, dict[str, Any]] = {}
    if news_summary is not None and not news_summary.empty and "ticker" in news_summary.columns:
        tmp_news = news_summary.copy()
        tmp_news["ticker"] = tmp_news["ticker"].astype(str).str.upper().str.strip()
        news_map = tmp_news.set_index("ticker").to_dict(orient="index")

    rows: list[dict[str, Any]] = []
    for ticker in work.columns:
        s = pd.to_numeric(work[ticker], errors="coerce").dropna()
        if s.empty:
            continue

        last_price = float(s.iloc[-1])
        sma_50 = s.tail(50).mean() if len(s) >= 50 else np.nan
        sma_200 = s.tail(200).mean() if len(s) >= 200 else np.nan
        ret_1m = s.pct_change(21).iloc[-1] if len(s) >= 22 else np.nan
        ret_3m = s.pct_change(63).iloc[-1] if len(s) >= 64 else np.nan
        ret_6m = s.pct_change(126).iloc[-1] if len(s) >= 127 else np.nan
        ret_12m = s.pct_change(252).iloc[-1] if len(s) >= 253 else np.nan
        rolling = s.pct_change().dropna()
        realized_vol_20d = rolling.tail(20).std() * np.sqrt(252) if len(rolling) >= 20 else np.nan

        high_52w = s.tail(252).max() if len(s) >= 20 else s.max()
        low_52w = s.tail(252).min() if len(s) >= 20 else s.min()
        drawdown = last_price / high_52w - 1 if high_52w and not pd.isna(high_52w) else np.nan
        dist_low = last_price / low_52w - 1 if low_52w and not pd.isna(low_52w) else np.nan

        rsi_14 = _compute_rsi(s, 14)
        macd, macd_signal, macd_hist = _compute_macd(s)

        info = company_info.get(str(ticker).upper(), {}) if isinstance(company_info, dict) else {}
        news = news_map.get(str(ticker).upper(), {}) if news_map else {}

        rows.append(
            {
                "ticker": str(ticker).upper(),
                "last_price": last_price,
                "company_name": str(info.get("longName") or info.get("shortName") or ticker),
                "sector": str(info.get("sector") or info.get("sectorDisp") or "Unknown"),
                "industry": str(info.get("industry") or "Unknown"),
                "ret_1m": ret_1m,
                "ret_3m": ret_3m,
                "ret_6m": ret_6m,
                "ret_12m": ret_12m,
                "benchmark_ret_3m": bench_ret_3m,
                "relative_strength_3m": ret_3m - bench_ret_3m if pd.notna(ret_3m) and pd.notna(bench_ret_3m) else np.nan,
                "sma_50": sma_50,
                "sma_200": sma_200,
                "price_vs_50dma": last_price / sma_50 - 1 if pd.notna(sma_50) and sma_50 else np.nan,
                "price_vs_200dma": last_price / sma_200 - 1 if pd.notna(sma_200) and sma_200 else np.nan,
                "rsi_14": rsi_14,
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "realized_vol_20d": realized_vol_20d,
                "drawdown_from_52w_high": drawdown,
                "distance_from_52w_low": dist_low,
                "article_count": _safe_float(news.get("article_count")),
                "articles_with_full_text": _safe_float(news.get("articles_with_full_text")),
                "full_text_ratio": _safe_float(news.get("full_text_ratio")),
                "usable_news_count": _safe_float(news.get("usable_news_count")),
                "news_quality_score": _safe_float(news.get("news_quality_score"), 0.0),
                "news_overlay_used": bool(news.get("news_overlay_used", False)),
                "news_data_status": str(news.get("news_data_status") or ""),
                "top_themes": str(news.get("top_themes") or ""),
                "news_signal_score": _safe_float(news.get("news_signal_score")),
                "avg_news_sentiment": _safe_float(news.get("avg_news_sentiment")),
                "news_sentiment_label": str(news.get("news_sentiment_label") or ""),
                "news_summary": str(news.get("news_summary") or ""),
                "positioning_news_view": str(news.get("positioning_news_view") or ""),
                "positioning_news_rationale": str(news.get("positioning_news_rationale") or ""),
                "catalyst_positive_count": _safe_float(news.get("catalyst_positive_count"), 0.0),
                "catalyst_negative_count": _safe_float(news.get("catalyst_negative_count"), 0.0),
                "low_signal_noisy_count": _safe_float(news.get("low_signal_noisy_count"), 0.0),
            }
        )

    return pd.DataFrame(rows)


def build_cross_asset_dashboard(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    if dataset is None or dataset.empty:
        return []
    work = dataset.copy()
    work["ret_3m"] = pd.to_numeric(work.get("ret_3m"), errors="coerce")
    work["ret_1m"] = pd.to_numeric(work.get("ret_1m"), errors="coerce")
    cols = [c for c in ["ticker", "sector", "ret_1m", "ret_3m", "ret_6m", "realized_vol_20d"] if c in work.columns]
    leaders = work.sort_values(["ret_3m", "ret_1m"], ascending=[False, False])[cols].head(12)
    return leaders.fillna("").to_dict(orient="records")


def rank_sector_momentum(dataset: pd.DataFrame) -> list[dict[str, Any]]:
    if dataset is None or dataset.empty or "sector" not in dataset.columns:
        return []
    work = dataset.copy()
    for col in ["ret_1m", "ret_3m", "ret_6m", "current_weight"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    grp = (
        work.groupby("sector", dropna=False)
        .agg(
            avg_ret_1m=("ret_1m", "mean"),
            avg_ret_3m=("ret_3m", "mean"),
            avg_ret_6m=("ret_6m", "mean"),
            holdings=("ticker", "count"),
            portfolio_weight=("current_weight", "sum") if "current_weight" in work.columns else ("ticker", "count"),
        )
        .reset_index()
    )
    grp["momentum_score"] = grp[["avg_ret_1m", "avg_ret_3m", "avg_ret_6m"]].mean(axis=1, skipna=True)
    return grp.sort_values("momentum_score", ascending=False).fillna("").to_dict(orient="records")


def compute_market_regime(prices: pd.DataFrame) -> dict[str, Any]:
    if prices is None or prices.empty:
        return {"regime": "Unknown", "confidence": 0.0, "signals": []}
    benchmark = "SPY" if "SPY" in prices.columns else prices.columns[0]
    s = pd.to_numeric(prices[benchmark], errors="coerce").dropna()
    if s.empty:
        return {"regime": "Unknown", "confidence": 0.0, "signals": []}
    sma_50 = s.tail(50).mean() if len(s) >= 50 else np.nan
    sma_200 = s.tail(200).mean() if len(s) >= 200 else np.nan
    ret_3m = s.pct_change(63).iloc[-1] if len(s) >= 64 else np.nan
    vol = s.pct_change().tail(20).std() * np.sqrt(252) if len(s) >= 25 else np.nan
    above_50 = pd.notna(sma_50) and s.iloc[-1] > sma_50
    above_200 = pd.notna(sma_200) and s.iloc[-1] > sma_200
    positive_momentum = pd.notna(ret_3m) and ret_3m > 0
    elevated_vol = pd.notna(vol) and vol > 0.28
    if above_50 and above_200 and positive_momentum and not elevated_vol:
        regime = "Risk-On"
        confidence = 0.8
    elif (not above_200) and elevated_vol:
        regime = "Risk-Off"
        confidence = 0.75
    else:
        regime = "Mixed"
        confidence = 0.6
    return {
        "benchmark": benchmark,
        "regime": regime,
        "confidence": confidence,
        "signals": [
            f"Price vs 50DMA: {((s.iloc[-1] / sma_50 - 1) if pd.notna(sma_50) and sma_50 else np.nan):.2%}" if pd.notna(sma_50) else "Price vs 50DMA: NA",
            f"Price vs 200DMA: {((s.iloc[-1] / sma_200 - 1) if pd.notna(sma_200) and sma_200 else np.nan):.2%}" if pd.notna(sma_200) else "Price vs 200DMA: NA",
            f"3M return: {ret_3m:.2%}" if pd.notna(ret_3m) else "3M return: NA",
            f"20D realized vol: {vol:.2%}" if pd.notna(vol) else "20D realized vol: NA",
        ],
    }


def build_portfolio_news_summary(news_summary: pd.DataFrame, recommendations: pd.DataFrame) -> list[dict[str, Any]]:
    if news_summary is None or news_summary.empty:
        return []
    work = news_summary.copy()
    if recommendations is not None and not recommendations.empty:
        join_cols = [c for c in ["ticker", "action", "current_weight", "composite_score"] if c in recommendations.columns]
        if join_cols:
            work = work.merge(recommendations[join_cols], on="ticker", how="left")
    out_cols = [
        c
        for c in [
            "ticker",
            "article_count",
            "articles_with_full_text",
            "full_text_ratio",
            "news_sentiment_label",
            "positioning_news_view",
            "positioning_news_rationale",
            "top_themes",
            "news_summary",
            "action",
            "current_weight",
            "composite_score",
        ]
        if c in work.columns
    ]
    return work[out_cols].fillna("").to_dict(orient="records")
