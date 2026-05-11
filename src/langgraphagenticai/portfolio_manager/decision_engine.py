from __future__ import annotations

from typing import Any
import json
import re

import numpy as np
import pandas as pd

try:
    from openai import OpenAI
except Exception:  # OpenAI is optional for tests/offline mode
    OpenAI = None

from langgraphagenticai.portfolio_manager.analytics import compute_market_regime, compute_position_snapshot
from langgraphagenticai.portfolio_manager.data_sources import (
    build_multi_agent_dataset,
    fetch_company_info,
    fetch_price_history,
)
from langgraphagenticai.portfolio_manager.fmp_screener import fmp_company_screener
from langgraphagenticai.portfolio_manager.portfolio_actions import split_recommendation_buckets
from langgraphagenticai.portfolio_manager.portfolio_reporting import (
    build_sector_allocation_table,
    build_stress_scenario_table,
    build_target_weight_explanations,
)
from langgraphagenticai.portfolio_manager.rebalance_engine import compute_recommended_rebalance
from langgraphagenticai.portfolio_manager.schemas import (
    AgentResult,
    CatalystResult,
    DebateResult,
    EarningsResult,
    FinalRecommendation,
    FundamentalResult,
    PortfolioFitResult,
    RiskResult,
    ScreeningResult,
    TechnicalResult,
    TickerAnalysisBundle,
    ValuationResult,
)

DEFAULT_SCREEN_COLUMNS = ["ticker", "companyName", "sector", "industry", "marketCap", "price", "beta", "volume"]

PILLAR_WEIGHTS = {
    # Portfolio Manager intentionally excludes the token-heavy news overlay.
    # The agentic framework relies on durable, refreshable evidence: sector-aware
    # fundamentals, valuation, forward estimates, technical/momentum, risk, fit,
    # and capital-allocation policy.
    "fundamental": 0.24,
    "valuation": 0.18,
    "forward": 0.21,
    "technical": 0.23,
    "portfolio_fit": 0.08,
    "capital_policy": 0.06,
}

# ETFs/funds should not be penalized for missing company fundamentals or analyst estimates.
# They are mostly portfolio-construction instruments, so the recommendation should lean on
# technical/momentum, risk, liquidity/fit, and allocation policy.
ETF_PILLAR_WEIGHTS = {
    "technical": 0.52,
    "risk_fit": 0.23,
    "portfolio_fit": 0.15,
    "capital_policy": 0.10,
}

COMMON_ETF_TICKERS = {
    "SPY", "VOO", "IVV", "VTI", "VT", "QQQ", "QQQM", "DIA", "IWM", "IJR", "MDY",
    "SCHD", "VIG", "VYM", "DGRO", "NOBL", "SPYD", "JEPI", "JEPQ",
    "XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC",
    "SMH", "SOXX", "ARKK", "ARKG", "ARKW", "IBB", "XBI", "KRE", "KBE",
    "TLT", "IEF", "SHY", "BIL", "SGOV", "AGG", "BND", "LQD", "HYG", "JNK",
    "GLD", "IAU", "SLV", "USO", "UNG", "DBC", "VNQ", "IYR",
    "EFA", "VEA", "EEM", "VWO", "VXUS", "ACWI",
}


def _normalize_tickers(text: str) -> list[str]:
    parts = str(text or "").replace("\n", ",").replace(";", ",").replace("|", ",").split(",")
    return sorted({p.strip().upper() for p in parts if p.strip()})


def _normalize_holdings_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("Please provide at least one holding.")
    work = df.copy()
    work.columns = [str(c).strip().lower() for c in work.columns]
    if "ticker" not in work.columns or "shares" not in work.columns:
        raise ValueError("Holdings input must contain 'ticker' and 'shares' columns.")
    work["ticker"] = work["ticker"].astype(str).str.upper().str.strip()
    work["shares"] = pd.to_numeric(work["shares"], errors="coerce")
    work = work[(work["ticker"] != "") & work["shares"].notna() & (work["shares"] > 0)].copy()
    if work.empty:
        raise ValueError("No valid holdings were found.")
    return work.groupby("ticker", as_index=False).agg({"shares": "sum"})


def run_fmp_screen(filters: dict[str, Any], fmp_api_key: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not fmp_api_key:
        raise ValueError("FMP API key is required for Screen companies mode.")
    screen_df, meta = fmp_company_screener(filters=filters, api_key=fmp_api_key, max_pages=filters.get("max_pages", 5))
    if screen_df.empty:
        return screen_df, meta
    keep = [c for c in DEFAULT_SCREEN_COLUMNS if c in screen_df.columns]
    out = screen_df[keep].copy() if keep else screen_df.copy()
    return out, meta


def _safe_float(x: Any, default: float | None = np.nan) -> float:
    try:
        if x is None or pd.isna(x):
            return default
        val = float(x)
        if isinstance(val, complex):
            return default
        if np.isinf(val):
            return default
        return val
    except Exception:
        return default


def _clean_text(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    text = str(x).strip()
    return text if text else default

def _is_fund_like(row: pd.Series | dict[str, Any]) -> bool:
    """Detect ETFs/funds using the fields available from yfinance/FMP plus common tickers.

    This intentionally errs on the side of treating obvious ETFs/funds as fund-like so
    missing revenue, EPS, margins, or analyst-estimate fields do not create false negatives.
    """
    get = row.get if hasattr(row, "get") else lambda k, default=None: default
    ticker = _clean_text(get("ticker"), "").upper()
    if ticker in COMMON_ETF_TICKERS:
        return True

    quote_type = _clean_text(get("quoteType") or get("quote_type"), "").lower()
    sector = _clean_text(get("sector"), "").lower()
    industry = _clean_text(get("industry"), "").lower()
    name = _clean_text(get("company_name") or get("companyName") or get("shortName"), "").lower()

    haystack = " ".join([quote_type, sector, industry, name])
    fund_markers = [
        "etf", "fund", "mutualfund", "exchange traded", "index", "trust",
        "ishares", "vanguard", "spdr", "invesco", "schwab", "proshares",
        "direxion", "global x", "van eck", "vaneck", "wisdomtree", "ark ",
    ]
    return any(marker in haystack for marker in fund_markers)


def _asset_type(row: pd.Series | dict[str, Any]) -> str:
    return "ETF / Fund" if _is_fund_like(row) else "Equity"


def _weights_for_row(row: pd.Series) -> dict[str, float]:
    return ETF_PILLAR_WEIGHTS if _is_fund_like(row) else PILLAR_WEIGHTS


def _score_high(value: Any, good: float, great: float, neutral: float = 5.5) -> float:
    v = _safe_float(value)
    if pd.isna(v):
        return neutral
    if great == good:
        return neutral
    score = 5.0 + 5.0 * ((v - good) / (great - good))
    return float(np.clip(score, 0.0, 10.0))


def _score_low(value: Any, good: float, great: float, neutral: float = 5.5) -> float:
    v = _safe_float(value)
    if pd.isna(v):
        return neutral
    if good == great:
        return neutral
    score = 5.0 + 5.0 * ((good - v) / (good - great))
    return float(np.clip(score, 0.0, 10.0))


def _score_range(value: Any, low: float, high: float, neutral: float = 5.5) -> float:
    v = _safe_float(value)
    if pd.isna(v):
        return neutral
    if low <= v <= high:
        return 8.0
    if v < low:
        return float(np.clip(8.0 - abs(v - low) / max(abs(low), 1e-6) * 5.0, 0.0, 8.0))
    return float(np.clip(8.0 - abs(v - high) / max(abs(high), 1e-6) * 5.0, 0.0, 8.0))


def _avg(scores: list[float]) -> float:
    clean = [float(s) for s in scores if s is not None and not pd.isna(s)]
    return float(np.mean(clean)) if clean else 5.5


def _fmt_pct(value: Any) -> str:
    v = _safe_float(value)
    if pd.isna(v):
        return "NA"
    return f"{v * 100:.1f}%"


def _fmt_num(value: Any, suffix: str = "") -> str:
    v = _safe_float(value)
    if pd.isna(v):
        return "NA"
    return f"{v:.1f}{suffix}"


def _first_available(row: pd.Series, candidates: list[str]) -> Any:
    for col in candidates:
        if col in row.index:
            val = row.get(col)
            try:
                if pd.notna(val):
                    return val
            except Exception:
                if val is not None:
                    return val
    return np.nan


def _sector_profile(sector: str) -> dict[str, Any]:
    s = (sector or "").lower()
    if "financial" in s:
        return {"valuation_cols": ["price_to_book", "forward_pe"], "debt_sensitive": False, "pb_focus": True}
    if "real estate" in s:
        return {"valuation_cols": ["price_to_book", "price_to_sales", "forward_pe"], "debt_sensitive": True, "pb_focus": True}
    if "technology" in s or "communication" in s or "consumer cyclical" in s:
        return {"valuation_cols": ["forward_pe", "price_to_sales", "price_to_fcf"], "debt_sensitive": True, "growth_focus": True}
    if "energy" in s or "materials" in s or "industrial" in s:
        return {"valuation_cols": ["forward_pe", "price_to_book", "enterprise_to_ebitda"], "debt_sensitive": True}
    return {"valuation_cols": ["forward_pe", "price_to_sales", "price_to_book"], "debt_sensitive": True}


def _fundamental_agent(row: pd.Series) -> FundamentalResult:
    ticker = _clean_text(row.get("ticker"), "NA")
    if _is_fund_like(row):
        return FundamentalResult(
            ticker=ticker,
            score=6.0,
            verdict="not scored for ETF/fund",
            summary=[
                "ETF/fund detected: company fundamentals are not used as a negative signal.",
                "Portfolio recommendation will lean on momentum, risk, diversification, and fit.",
            ],
            risks=["No fundamental penalty applied because this is an ETF/fund-style instrument."],
            metrics={"asset_type": "ETF / Fund", "fundamental_scoring_used": False},
            thesis="fundamentals not applicable",
            conviction="medium",
            pillar_scores={"quality_growth": 6.0},
        )

    sector = _clean_text(row.get("sector"), "Unknown")
    profile = _sector_profile(sector)

    revenue_growth = _first_available(row, ["revenue_cagr_3y", "revenue_growth"])
    earnings_growth = _first_available(row, ["net_income_cagr_3y", "earnings_growth"])
    fcf_growth = row.get("fcf_cagr_3y")
    operating_margin = _first_available(row, ["operating_margin", "profit_margin"])
    fcf_margin = _first_available(row, ["fcf_margin", "free_cashflow_margin"])
    roe = row.get("return_on_equity")
    debt_to_equity = row.get("debt_to_equity")
    liabilities_to_assets = row.get("liabilities_to_assets")

    scores = [
        _score_high(revenue_growth, good=0.03, great=0.18),
        _score_high(earnings_growth, good=0.02, great=0.18),
        _score_high(fcf_growth, good=0.02, great=0.15),
        _score_high(operating_margin, good=0.08, great=0.28),
        _score_high(fcf_margin, good=0.04, great=0.18),
        _score_high(roe, good=0.08, great=0.25),
    ]
    if profile.get("debt_sensitive", True):
        scores.append(_score_low(debt_to_equity, good=1.5, great=0.25))
        scores.append(_score_low(liabilities_to_assets, good=0.70, great=0.35))

    score = _avg(scores)
    verdict = "strong" if score >= 7.5 else "constructive" if score >= 6.3 else "mixed" if score >= 4.8 else "weak"
    summary = [
        f"Revenue growth/CAGR: {_fmt_pct(revenue_growth)}",
        f"Earnings growth/CAGR: {_fmt_pct(earnings_growth)}",
        f"Operating margin: {_fmt_pct(operating_margin)}",
        f"ROE: {_fmt_pct(roe)}",
    ]
    risks = []
    if _safe_float(debt_to_equity) > 2.0:
        risks.append(f"Debt/equity is elevated at {_fmt_num(debt_to_equity)}x.")
    if _safe_float(operating_margin) < 0.05:
        risks.append("Margins are thin versus broad quality thresholds.")
    if _safe_float(revenue_growth) < 0:
        risks.append("Revenue growth is negative.")

    return FundamentalResult(
        ticker=ticker,
        score=round(score, 2),
        verdict=verdict,
        summary=summary,
        risks=risks or ["No major fundamental risk flag from available fields."],
        metrics={
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "fcf_cagr_3y": fcf_growth,
            "operating_margin": operating_margin,
            "roe": roe,
            "debt_to_equity": debt_to_equity,
            "liabilities_to_assets": liabilities_to_assets,
        },
        thesis=verdict,
        conviction="high" if score >= 7.5 else "medium" if score >= 5.0 else "low",
        pillar_scores={"quality_growth": round(score, 2)},
    )


def _valuation_agent(row: pd.Series) -> ValuationResult:
    ticker = _clean_text(row.get("ticker"), "NA")
    if _is_fund_like(row):
        return ValuationResult(
            ticker=ticker,
            score=6.0,
            verdict="not scored for ETF/fund",
            summary=[
                "ETF/fund detected: equity valuation multiples are not used as a negative signal.",
                "Use price trend, relative momentum, volatility, drawdown, and portfolio role instead.",
            ],
            risks=["No valuation-multiple penalty applied because this is an ETF/fund-style instrument."],
            metrics={"asset_type": "ETF / Fund", "valuation_scoring_used": False},
            thesis="valuation multiples not applicable",
            conviction="medium",
            valuation_status="not applicable",
        )

    sector = _clean_text(row.get("sector"), "Unknown")
    profile = _sector_profile(sector)
    fpe = row.get("forward_pe")
    ps = _first_available(row, ["forward_ps", "price_to_sales"])
    pb = row.get("price_to_book")
    pfcf = row.get("price_to_fcf")
    ev_ebitda = row.get("enterprise_to_ebitda")
    earnings_yield = row.get("earnings_yield")
    fcf_yield = row.get("fcf_yield")

    scores: list[float] = []
    if "forward_pe" in profile["valuation_cols"]:
        scores.append(_score_low(fpe, good=28.0, great=10.0))
    if "price_to_sales" in profile["valuation_cols"]:
        scores.append(_score_low(ps, good=8.0, great=1.5))
    if "price_to_book" in profile["valuation_cols"]:
        scores.append(_score_low(pb, good=4.0, great=0.9))
    if "price_to_fcf" in profile["valuation_cols"]:
        scores.append(_score_low(pfcf, good=35.0, great=10.0))
    if "enterprise_to_ebitda" in profile["valuation_cols"]:
        scores.append(_score_low(ev_ebitda, good=16.0, great=6.0))
    scores.extend([
        _score_high(earnings_yield, good=0.03, great=0.08),
        _score_high(fcf_yield, good=0.02, great=0.07),
    ])

    score = _avg(scores)
    verdict = "attractive" if score >= 7.3 else "reasonable" if score >= 6.0 else "expensive/mixed" if score >= 4.5 else "expensive"
    summary = [
        f"Forward P/E: {_fmt_num(fpe, 'x')}",
        f"Price/Sales: {_fmt_num(ps, 'x')}",
        f"Price/Book: {_fmt_num(pb, 'x')}",
        f"FCF yield: {_fmt_pct(fcf_yield)}",
    ]
    risks = []
    if _safe_float(fpe) > 40:
        risks.append("Forward P/E is elevated, so the stock needs strong execution to justify the multiple.")
    if _safe_float(ps) > 12:
        risks.append("Price/sales is elevated versus broad market thresholds.")

    return ValuationResult(
        ticker=ticker,
        score=round(score, 2),
        verdict=verdict,
        summary=summary,
        risks=risks or ["No major valuation risk flag from available fields."],
        metrics={"forward_pe": fpe, "price_to_sales": ps, "price_to_book": pb, "price_to_fcf": pfcf, "fcf_yield": fcf_yield},
        thesis=verdict,
        conviction="high" if score >= 7.3 else "medium" if score >= 5.0 else "low",
        valuation_status=verdict,
    )


def _forward_agent(row: pd.Series) -> EarningsResult:
    ticker = _clean_text(row.get("ticker"), "NA")
    if _is_fund_like(row):
        return EarningsResult(
            ticker=ticker,
            score=6.0,
            verdict="not scored for ETF/fund",
            summary=[
                "ETF/fund detected: forward revenue/EPS estimates are not used as a negative signal.",
                "The recommendation will be driven mainly by momentum, risk, and portfolio construction.",
            ],
            risks=["No forward-estimate penalty applied because this is an ETF/fund-style instrument."],
            metrics={"asset_type": "ETF / Fund", "forward_scoring_used": False},
            thesis="forward estimates not applicable",
            conviction="medium",
            management_tone="not used",
            guidance_quality="not applicable",
        )

    revenue = row.get("forward_revenue_growth")
    eps = row.get("forward_eps_growth")
    upside = row.get("analyst_upside_pct")
    rating = row.get("rating_score")
    score = _avg([
        _score_high(revenue, good=0.03, great=0.18),
        _score_high(eps, good=0.03, great=0.20),
        _score_high(upside, good=0.05, great=0.30),
        _score_high(rating, good=3.0, great=4.5),
    ])
    verdict = "strong outlook" if score >= 7.5 else "constructive outlook" if score >= 6.2 else "mixed outlook" if score >= 4.8 else "weak outlook"
    risks = []
    if _safe_float(upside) < 0:
        risks.append("Analyst target upside is negative based on available data.")
    if _safe_float(eps) < 0:
        risks.append("Forward EPS growth is negative based on available data.")
    return EarningsResult(
        ticker=ticker,
        score=round(score, 2),
        verdict=verdict,
        summary=[
            f"Forward revenue growth: {_fmt_pct(revenue)}",
            f"Forward EPS growth: {_fmt_pct(eps)}",
            f"Analyst upside: {_fmt_pct(upside)}",
        ],
        risks=risks or ["Forward outlook has no major negative flag from available fields."],
        metrics={"forward_revenue_growth": revenue, "forward_eps_growth": eps, "analyst_upside_pct": upside, "rating_score": rating},
        thesis=verdict,
        conviction="high" if score >= 7.5 else "medium" if score >= 5.0 else "low",
        management_tone="not used",
        guidance_quality=verdict,
    )


def _technical_agent(row: pd.Series) -> TechnicalResult:
    ticker = _clean_text(row.get("ticker"), "NA")
    rsi = row.get("rsi_14")
    price_50 = row.get("price_vs_50dma")
    price_200 = row.get("price_vs_200dma")
    ret_1m = row.get("ret_1m")
    ret_3m = row.get("ret_3m")
    ret_6m = row.get("ret_6m")
    ret_12m = _first_available(row, ["ret_12m", "ret_1y"])
    rel_3m = _first_available(row, ["relative_strength_3m", "rel_3m_vs_benchmark"])
    vol = _first_available(row, ["ann_vol_3m", "realized_vol_20d"])
    drawdown = _first_available(row, ["drawdown_from_52w_high", "max_drawdown_1y"])
    macd_hist = row.get("macd_hist")

    rsi_score = _score_range(rsi, low=42.0, high=68.0)
    # Overbought is not automatically bearish, but it lowers timing quality.
    if _safe_float(rsi) > 75:
        rsi_score = min(rsi_score, 5.5)
    if _safe_float(rsi) < 30:
        rsi_score = min(rsi_score + 1.0, 7.0)

    score = _avg([
        rsi_score,
        _score_high(price_50, good=0.0, great=0.12),
        _score_high(price_200, good=0.0, great=0.25),
        _score_high(ret_1m, good=0.0, great=0.08),
        _score_high(ret_3m, good=0.02, great=0.18),
        _score_high(ret_6m, good=0.04, great=0.28),
        _score_high(ret_12m, good=0.06, great=0.35),
        _score_high(rel_3m, good=0.0, great=0.12),
        _score_low(vol, good=0.45, great=0.18),
        _score_high(drawdown, good=-0.25, great=-0.02),
        _score_high(macd_hist, good=0.0, great=max(abs(_safe_float(row.get("last_price"), 1.0)) * 0.002, 0.01)),
    ])
    verdict = "strong momentum" if score >= 7.5 else "positive momentum" if score >= 6.2 else "mixed momentum" if score >= 4.8 else "weak momentum"

    risks = []
    if _safe_float(rsi) > 75:
        risks.append(f"RSI is extended at {_fmt_num(rsi)}; timing risk is elevated.")
    if _safe_float(price_200) < 0:
        risks.append("Price is below the 200-day moving average.")
    if _safe_float(rel_3m) < -0.05:
        risks.append("3-month relative strength versus benchmark is negative.")

    return TechnicalResult(
        ticker=ticker,
        score=round(score, 2),
        verdict=verdict,
        summary=[
            f"RSI 14: {_fmt_num(rsi)}",
            f"Price vs 50DMA: {_fmt_pct(price_50)}",
            f"Price vs 200DMA: {_fmt_pct(price_200)}",
            f"3M relative strength: {_fmt_pct(rel_3m)}",
        ],
        risks=risks or ["No major technical risk flag from available fields."],
        metrics={
            "rsi_14": rsi,
            "price_vs_50dma": price_50,
            "price_vs_200dma": price_200,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "ret_6m": ret_6m,
            "ret_12m": ret_12m,
            "relative_strength_3m": rel_3m,
            "realized_vol_20d": vol,
            "drawdown_from_52w_high": drawdown,
        },
        thesis=verdict,
        conviction="high" if score >= 7.5 else "medium" if score >= 5.0 else "low",
        trend="positive" if _safe_float(price_50) > 0 and _safe_float(price_200) > 0 else "mixed",
        momentum="positive" if _safe_float(ret_3m) > 0 and _safe_float(rel_3m) > 0 else "mixed",
        timing="extended" if _safe_float(rsi) > 75 else "neutral",
    )


def _allocation_policy_agent(row: pd.Series, portfolio_context: dict[str, Any]) -> CatalystResult:
    """Capital-allocation policy agent used in place of the old news/catalyst agent.

    This agent does not fetch articles or call an LLM. It gives the committee a
    simple view of whether a name is eligible for incremental capital based on
    position size, sector concentration, and data quality.
    """
    ticker = _clean_text(row.get("ticker"), "NA")
    sector = _clean_text(row.get("sector"), "Unknown")
    current_weight = _safe_float(row.get("current_weight"), 0.0) or 0.0
    max_weight = _safe_float(portfolio_context.get("max_weight"), 0.18) or 0.18
    max_sector_weight = _safe_float(portfolio_context.get("max_sector_weight"), 0.35) or 0.35
    sector_weight = _safe_float((portfolio_context.get("sector_weights") or {}).get(sector), 0.0) or 0.0
    data_quality = _safe_float(row.get("data_quality_score"), 0.6) or 0.6

    size_score = _score_low(current_weight, good=max_weight, great=max_weight * 0.30)
    sector_score = _score_low(sector_weight, good=max_sector_weight, great=max_sector_weight * 0.45)
    quality_score = _score_high(data_quality, good=0.50, great=0.85)
    score = _avg([size_score, sector_score, quality_score])

    risks = []
    if current_weight >= max_weight * 0.95:
        risks.append("Position is near the maximum position weight, so adds should be limited.")
    if sector_weight >= max_sector_weight * 0.95:
        risks.append("Sector allocation is near the max sector setting, so new capital should be selective.")
    if data_quality < 0.55:
        risks.append("Data quality is below ideal, so conviction should be reduced.")

    verdict = "capital eligible" if score >= 6.7 else "capital constrained" if score < 5.0 else "selective sizing"
    return CatalystResult(
        ticker=ticker,
        score=round(score, 2),
        verdict=verdict,
        summary=[
            f"Current weight: {_fmt_pct(current_weight)}",
            f"Sector weight: {_fmt_pct(sector_weight)}",
            f"Data quality: {_fmt_pct(data_quality)}",
        ],
        risks=risks or ["No major capital-allocation constraint from available fields."],
        metrics={
            "current_weight": current_weight,
            "sector_weight": sector_weight,
            "max_weight": max_weight,
            "max_sector_weight": max_sector_weight,
            "data_quality_score": data_quality,
        },
        thesis=verdict,
        conviction="high" if score >= 7.5 else "medium" if score >= 5.0 else "low",
        sentiment="not_used",
        catalyst_view="news disabled; allocation policy active",
    )

def _risk_and_fit_agents(row: pd.Series, portfolio_context: dict[str, Any]) -> tuple[RiskResult, PortfolioFitResult]:
    ticker = _clean_text(row.get("ticker"), "NA")
    sector = _clean_text(row.get("sector"), "Unknown")
    current_weight = _safe_float(row.get("current_weight"), 0.0) or 0.0
    max_weight = _safe_float(portfolio_context.get("max_weight"), 0.18) or 0.18
    max_sector_weight = _safe_float(portfolio_context.get("max_sector_weight"), 0.35) or 0.35
    sector_weight = _safe_float((portfolio_context.get("sector_weights") or {}).get(sector), 0.0) or 0.0
    vol = _first_available(row, ["ann_vol_3m", "realized_vol_20d"])
    drawdown = _first_available(row, ["max_drawdown_1y", "drawdown_from_52w_high"])
    beta = row.get("beta")
    data_quality = _safe_float(row.get("data_quality_score"), 0.6) or 0.6

    risk_score = _avg([
        _score_low(vol, good=0.45, great=0.18),
        _score_high(drawdown, good=-0.30, great=-0.03),
        _score_low(beta, good=1.6, great=0.7),
        _score_high(data_quality, good=0.50, great=0.85),
    ])
    concentration_score = _score_low(current_weight, good=max_weight, great=max_weight * 0.35)
    sector_score = _score_low(sector_weight, good=max_sector_weight, great=max_sector_weight * 0.45)
    fit_score = _avg([concentration_score, sector_score, risk_score])

    risk_flags = []
    if current_weight > max_weight:
        risk_flags.append(f"Position is above the max weight setting ({_fmt_pct(current_weight)} vs {_fmt_pct(max_weight)}).")
    if sector_weight > max_sector_weight:
        risk_flags.append(f"Sector exposure is above the max sector setting ({_fmt_pct(sector_weight)} vs {_fmt_pct(max_sector_weight)}).")
    if _safe_float(vol) > 0.50:
        risk_flags.append("Realized volatility is elevated.")

    risk = RiskResult(
        ticker=ticker,
        score=round(risk_score, 2),
        verdict="low/moderate risk" if risk_score >= 6.5 else "moderate risk" if risk_score >= 5.0 else "elevated risk",
        summary=[f"Volatility: {_fmt_pct(vol)}", f"Drawdown: {_fmt_pct(drawdown)}", f"Beta: {_fmt_num(beta)}"],
        risks=risk_flags or ["No major portfolio risk flag from available fields."],
        metrics={"volatility": vol, "drawdown": drawdown, "beta": beta, "data_quality_score": data_quality},
        risk_level="elevated" if risk_score < 5.0 else "moderate",
    )
    fit = PortfolioFitResult(
        ticker=ticker,
        score=round(fit_score, 2),
        verdict="good fit" if fit_score >= 6.5 else "position constrained" if fit_score >= 5.0 else "risk constrained",
        summary=[f"Current weight: {_fmt_pct(current_weight)}", f"Sector weight: {_fmt_pct(sector_weight)}"],
        risks=risk_flags or ["No major fit constraint from available fields."],
        metrics={"current_weight": current_weight, "sector_weight": sector_weight, "max_weight": max_weight, "max_sector_weight": max_sector_weight},
        action_bias="add" if fit_score >= 6.5 else "hold" if fit_score >= 5.0 else "trim",
        sizing_guidance="normal" if fit_score >= 6.5 else "small / defensive",
    )
    return risk, fit


def _confidence(score: float, data_quality: float) -> str:
    if data_quality >= 0.78 and score >= 7.2:
        return "high"
    if data_quality < 0.45:
        return "low"
    return "medium"


def _action_from_score(score: float, current_weight: float, data_quality: float, technical_score: float, max_weight: float) -> str:
    owned = current_weight > 0.0001
    if owned:
        if score >= 8.0:
            action = "Add"
        elif score >= 6.3:
            action = "Hold"
        elif score >= 4.8:
            action = "Hold"
        elif score >= 3.5:
            action = "Trim"
        else:
            action = "Sell"
    else:
        if score >= 8.0:
            action = "Start / Rotate In"
        elif score >= 6.5:
            action = "Watchlist"
        else:
            action = "Avoid"

    # Guardrails: no aggressive add on weak data, bad technicals, or an already oversized position.
    if data_quality < 0.45 and action in {"Add", "Start / Rotate In"}:
        action = "Hold" if owned else "Watchlist"
    if technical_score < 4.2 and action in {"Add", "Start / Rotate In"}:
        action = "Hold" if owned else "Watchlist"
    if owned and current_weight >= max_weight * 0.95 and action == "Add":
        action = "Hold"
    if owned and current_weight > max_weight * 1.15 and score < 7.2:
        action = "Trim"
    return action


def _build_final(row: pd.Series, agents: dict[str, AgentResult], portfolio_context: dict[str, Any]) -> FinalRecommendation:
    ticker = _clean_text(row.get("ticker"), "NA")
    sector = _clean_text(row.get("sector"), "Unknown")
    industry = _clean_text(row.get("industry"), "Unknown")
    current_weight = _safe_float(row.get("current_weight"), 0.0) or 0.0
    data_quality = _safe_float(row.get("data_quality_score"), 0.6) or 0.6
    max_weight = _safe_float(portfolio_context.get("max_weight"), 0.18) or 0.18

    sub_scores = {
        "fundamental": agents["fundamental"].score,
        "valuation": agents["valuation"].score,
        "forward": agents["forward"].score,
        "technical": agents["technical"].score,
        "capital_policy": agents["capital_policy"].score,
        "portfolio_fit": agents["portfolio_fit"].score,
        "risk_fit": agents["risk"].score,
    }
    is_fund_like = _is_fund_like(row)
    active_weights = _weights_for_row(row)
    composite = sum(active_weights[k] * sub_scores[k] for k in active_weights)
    action = _action_from_score(composite, current_weight, data_quality, sub_scores["technical"], max_weight)

    positives = []
    conflicts = []
    score_items = [
        ("fundamental", "fundamentals"),
        ("valuation", "valuation"),
        ("forward", "forward outlook"),
        ("technical", "technical/momentum"),
        ("portfolio_fit", "portfolio fit"),
        ("capital_policy", "capital allocation policy"),
    ]
    if is_fund_like:
        score_items = [
            ("technical", "technical/momentum"),
            ("risk_fit", "risk profile"),
            ("portfolio_fit", "portfolio fit"),
            ("capital_policy", "capital allocation policy"),
        ]
    for key, label in score_items:
        if sub_scores[key] >= 7.0:
            positives.append(f"{label} score is supportive ({sub_scores[key]:.1f}/10).")
        elif sub_scores[key] <= 4.5:
            conflicts.append(f"{label} score is weak or constrained ({sub_scores[key]:.1f}/10).")

    triggered = []
    if current_weight >= max_weight * 0.95:
        triggered.append("position size near/above cap")
    if data_quality < 0.55:
        triggered.append("medium/low data quality")
    if sub_scores["technical"] < 4.5:
        triggered.append("weak technical momentum")
    if _safe_float(row.get("rsi_14"), np.nan) > 75:
        triggered.append("extended RSI")

    consensus = "aligned" if len(positives) >= 4 and len(conflicts) <= 1 else "constructive" if len(positives) >= 3 else "mixed" if len(conflicts) <= 2 else "conflicted"
    if is_fund_like:
        decision_reason = (
            "ETF momentum and portfolio fit" if sub_scores["technical"] >= 6.5 and sub_scores["portfolio_fit"] >= 5.0
            else "ETF risk / portfolio constraints" if sub_scores["portfolio_fit"] < 5 or sub_scores["risk_fit"] < 5
            else "ETF technical scorecard"
        )
    else:
        decision_reason = (
            "technical momentum and forward outlook" if sub_scores["technical"] >= 7 and sub_scores["forward"] >= 6.5
            else "quality and valuation" if sub_scores["fundamental"] >= 7 and sub_scores["valuation"] >= 6
            else "risk / portfolio constraints" if sub_scores["portfolio_fit"] < 5 or sub_scores["risk_fit"] < 5
            else "balanced scorecard"
        )
    conf = _confidence(composite, data_quality)
    sizing = "large" if composite >= 8.2 and current_weight < max_weight * 0.75 else "normal" if composite >= 6.3 else "small / defensive"

    why = positives[:4] or [f"Composite score is {composite:.1f}/10 with a {decision_reason} driver."]
    risks = conflicts[:4] or triggered[:3] or ["No major scorecard conflict from available fields."]
    next_steps = [
        "Use the rebalance table for sizing rather than buying/selling solely from the action label.",
        "Re-check the signal after the next earnings update or major technical trend change.",
    ]
    summary = f"{ticker}: {action}. Composite {composite:.1f}/10; main driver is {decision_reason}."

    return FinalRecommendation(
        ticker=ticker,
        sector=sector,
        industry=industry,
        current_weight=current_weight,
        composite_score=round(composite, 2),
        absolute_score=round(composite, 2),
        # Legacy schema fields kept as NaN for backward compatibility; they are not used by this engine.
        peer_score=np.nan,
        peer_rank=np.nan,
        peer_percentile=np.nan,
        confidence=round(float(data_quality), 2),
        final_action=action,
        action_bias=action,
        suggested_sizing=sizing,
        consensus_state=consensus,
        decision_confidence=conf,
        data_quality_score=round(float(data_quality), 2),
        data_quality_label=_clean_text(row.get("data_quality_label"), "medium"),
        decision_reason=decision_reason,
        pm_decision_summary=summary,
        key_supports=positives[:4],
        key_conflicts=conflicts[:4],
        missing_evidence=[] if is_fund_like else (["Some FMP/fundamental fields were unavailable." ] if data_quality < 0.55 else []),
        monitor_triggers=["RSI above 75", "price breaks below 200DMA", "analyst upside turns negative"],
        triggered_guardrails=triggered,
        why=why,
        risks=risks,
        next_steps=next_steps,
        explanation=(
            f"Decision: {action}\n"
            f"Composite score: {composite:.1f}/10\n"
            f"Pillar scores: fundamentals {sub_scores['fundamental']:.1f}, valuation {sub_scores['valuation']:.1f}, "
            f"forward outlook {sub_scores['forward']:.1f}, technical/momentum {sub_scores['technical']:.1f}, "
            f"capital policy {sub_scores['capital_policy']:.1f}, portfolio fit {sub_scores['portfolio_fit']:.1f}, risk {sub_scores['risk_fit']:.1f}.\n"
            f"Asset type: {_asset_type(row)}. Active weights: {active_weights}.\n"
            f"Main driver: {decision_reason}."
        ),
        sub_scores=sub_scores,
        raw_metrics=row.to_dict(),
    )


def _build_portfolio_context(position_snapshot: pd.DataFrame, max_weight: float, max_sector_weight: float, cash_buffer: float) -> dict[str, Any]:
    if position_snapshot is None or position_snapshot.empty:
        return {
            "sector_weights": {},
            "cash_weight": 1.0,
            "max_weight": max_weight,
            "max_sector_weight": max_sector_weight,
            "cash_buffer": cash_buffer,
            "portfolio_mode": False,
        }
    work = position_snapshot.copy()
    work["current_weight"] = pd.to_numeric(work.get("current_weight"), errors="coerce").fillna(0.0)
    return {
        "sector_weights": work.groupby("sector", dropna=False)["current_weight"].sum().to_dict(),
        "cash_weight": max(0.0, 1.0 - float(work["current_weight"].sum())),
        "max_weight": max_weight,
        "max_sector_weight": max_sector_weight,
        "cash_buffer": cash_buffer,
        "portfolio_mode": True,
    }


def _run_light_agent_committee(dataset: pd.DataFrame, portfolio_context: dict[str, Any]) -> dict[str, TickerAnalysisBundle]:
    bundles: dict[str, TickerAnalysisBundle] = {}
    for _, row in dataset.iterrows():
        ticker = _clean_text(row.get("ticker"), "NA")
        sector = _clean_text(row.get("sector"), "Unknown")
        industry = _clean_text(row.get("industry"), "Unknown")

        fundamentals = _fundamental_agent(row)
        valuation = _valuation_agent(row)
        forward = _forward_agent(row)
        technicals = _technical_agent(row)
        capital_policy = _allocation_policy_agent(row, portfolio_context)
        risk, fit = _risk_and_fit_agents(row, portfolio_context)
        agents = {
            "fundamental": fundamentals,
            "valuation": valuation,
            "forward": forward,
            "technical": technicals,
            "capital_policy": capital_policy,
            "risk": risk,
            "portfolio_fit": fit,
        }
        final = _build_final(row, agents, portfolio_context)

        screening = ScreeningResult(
            ticker=ticker,
            score=final.composite_score,
            verdict="pass" if final.composite_score >= 5.0 else "soft fail",
            summary=["Lightweight committee screen completed without per-ticker LLM calls."],
            risks=final.risks,
            passes_screen=final.composite_score >= 5.0,
        )
        debate = DebateResult(
            ticker=ticker,
            consensus_state=final.consensus_state,
            support_count=len(final.key_supports),
            oppose_count=len(final.key_conflicts),
            neutral_count=max(0, 6 - len(final.key_supports) - len(final.key_conflicts)),
            action_tilt=final.final_action,
            support_reasons=final.key_supports,
            conflict_reasons=final.key_conflicts,
            open_questions=final.missing_evidence,
            sizing_hint=final.suggested_sizing,
            confidence=final.confidence,
        )

        bundles[ticker] = TickerAnalysisBundle(
            ticker=ticker,
            sector=sector,
            industry=industry,
            current_weight=_safe_float(row.get("current_weight"), 0.0) or 0.0,
            shares=_safe_float(row.get("shares"), 0.0) or 0.0,
            last_price=_safe_float(row.get("last_price"), 0.0) or 0.0,
            market_value=_safe_float(row.get("market_value"), 0.0) or 0.0,
            data=row.to_dict(),
            screening=screening,
            fundamentals=fundamentals,
            valuation=valuation,
            technicals=technicals,
            catalysts=capital_policy,
            earnings=forward,
            risk=risk,
            portfolio_fit=fit,
            debate=debate,
            final=final,
        )
    return bundles


def _recommendation_table_from_bundles(bundles: dict[str, TickerAnalysisBundle]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ticker, bundle in bundles.items():
        final = bundle.final
        if final is None:
            continue
        # Use the final recommendation raw_metrics as the primary data source because
        # the LLM committee writes agentic allocation fields there after reviewing
        # the quantitative evidence pack.  bundle.data is the original pre-LLM row,
        # so reading only bundle.data causes agentic_target_weight to show as None
        # and the rebalance engine falls back to deterministic max-weight sizing.
        data = dict(bundle.data or {})
        data.update(dict(final.raw_metrics or {}))
        rows.append({
            "ticker": ticker,
            "company_name": data.get("company_name") or data.get("companyName") or ticker,
            "sector": bundle.sector,
            "industry": bundle.industry,
            "asset_type": data.get("asset_type") or _asset_type(data),
            "shares": bundle.shares,
            "last_price": bundle.last_price,
            "market_value": bundle.market_value,
            "current_weight": bundle.current_weight,
            "fundamental_score": final.sub_scores.get("fundamental"),
            "valuation_score": final.sub_scores.get("valuation"),
            "forward_score": final.sub_scores.get("forward"),
            "technical_score": final.sub_scores.get("technical"),
            "capital_policy_score": final.sub_scores.get("capital_policy"),
            "risk_fit_score": final.sub_scores.get("risk_fit"),
            "portfolio_fit_score": final.sub_scores.get("portfolio_fit"),
            "composite_score": final.composite_score,
            "absolute_score": final.absolute_score,
            # Legacy comparative fields are intentionally omitted from the Portfolio Manager output.
            # The Portfolio Manager uses sector-aware absolute scoring, ETF-aware scoring,
            # technical/momentum scoring, and portfolio concentration rules instead.
            "confidence": final.confidence,
            "consensus_state": final.consensus_state,
            "suggested_sizing": final.suggested_sizing,
            "decision_confidence": final.decision_confidence,
            "data_quality_score": final.data_quality_score,
            "data_quality_label": final.data_quality_label,
            "decision_reason": final.decision_reason,
            "pm_decision_summary": final.pm_decision_summary,
            "triggered_guardrails": " | ".join(final.triggered_guardrails[:4]),
            "missing_evidence": " | ".join(final.missing_evidence[:4]),
            "final_action": final.final_action,
            "base_recommendation": final.action_bias,
            "action_bias": final.action_bias,
            "key_supports": " | ".join(final.key_supports[:3]),
            "key_conflicts": " | ".join(final.key_conflicts[:3]),
            "why": " | ".join(final.why[:3]),
            "risks": " | ".join(final.risks[:3]),
            "next_steps": " | ".join(final.next_steps[:2]),
            "agentic_target_weight": data.get("agentic_target_weight") if data.get("agentic_target_weight") is not None else data.get("ai_target_weight"),
            "agentic_target_weight_rationale": data.get("agentic_target_weight_rationale") if data.get("agentic_target_weight_rationale") is not None else data.get("target_weight_rationale"),
            "allocation_role": data.get("allocation_role"),
            "rsi_14": data.get("rsi_14"),
            "price_vs_50dma": data.get("price_vs_50dma"),
            "price_vs_200dma": data.get("price_vs_200dma"),
            "ret_1m": data.get("ret_1m"),
            "ret_3m": data.get("ret_3m"),
            "ret_6m": data.get("ret_6m"),
            "ret_12m": data.get("ret_12m") or data.get("ret_1y"),
            "relative_strength_3m": data.get("relative_strength_3m") or data.get("rel_3m_vs_benchmark"),
            "analyst_upside_pct": data.get("analyst_upside_pct"),
            "forward_revenue_growth": data.get("forward_revenue_growth"),
            "forward_eps_growth": data.get("forward_eps_growth"),
            "forward_pe": data.get("forward_pe"),
            "price_to_sales": data.get("price_to_sales"),
            "price_to_book": data.get("price_to_book"),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    order = {"Add": 0, "Strong Buy": 0, "Buy": 1, "Start / Rotate In": 1, "Hold": 2, "Watchlist": 3, "Trim": 4, "Sell": 5, "Exit": 5, "Avoid": 6}
    df["action_rank"] = df["final_action"].map(order).fillna(9)
    return df.sort_values(["action_rank", "composite_score"], ascending=[True, False]).drop(columns=["action_rank"]).reset_index(drop=True)


def _decision_audit_table(recommendation_table: pd.DataFrame) -> pd.DataFrame:
    if recommendation_table is None or recommendation_table.empty:
        return pd.DataFrame()
    cols = [
        "ticker", "asset_type", "sector", "industry", "final_action", "decision_reason", "decision_confidence",
        "composite_score", "fundamental_score", "valuation_score", "forward_score", "technical_score",
        "capital_policy_score", "portfolio_fit_score", "risk_fit_score", "current_weight", "data_quality_score",
        "triggered_guardrails", "key_supports", "key_conflicts", "pm_decision_summary",
    ]
    return recommendation_table[[c for c in cols if c in recommendation_table.columns]].copy().reset_index(drop=True)


def _technical_signal_table(recommendation_table: pd.DataFrame) -> pd.DataFrame:
    if recommendation_table is None or recommendation_table.empty:
        return pd.DataFrame()
    cols = [
        "ticker", "technical_score", "rsi_14", "price_vs_50dma", "price_vs_200dma",
        "ret_1m", "ret_3m", "ret_6m", "ret_12m", "relative_strength_3m",
    ]
    out = recommendation_table[[c for c in cols if c in recommendation_table.columns]].copy()
    def signal(row: pd.Series) -> str:
        score = _safe_float(row.get("technical_score"), 5.5) or 5.5
        rsi = _safe_float(row.get("rsi_14"), np.nan)
        if rsi > 75:
            return "Positive trend, but extended"
        if score >= 7.2:
            return "Strong momentum"
        if score >= 6.0:
            return "Positive trend"
        if score >= 4.5:
            return "Mixed / neutral"
        return "Weak momentum"
    if not out.empty:
        out["technical_signal"] = out.apply(signal, axis=1)
    return out



ACTION_LADDER = ["Sell", "Trim", "Hold / Watch", "Hold", "Add", "Strong Add"]
_ACTION_ALIASES = {
    "strong buy": "Strong Add",
    "buy": "Add",
    "start": "Add",
    "start / rotate in": "Add",
    "rotate in": "Add",
    "watchlist": "Hold / Watch",
    "avoid": "Hold / Watch",
    "exit": "Sell",
}


def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy objects to compact JSON-safe values for the LLM evidence pack."""
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None
        return round(value, 6)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    try:
        if hasattr(value, "item"):
            return _json_safe(value.item())
    except Exception:
        pass
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in list(value)]
    return str(value)


def _sector_framework_for_row(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    """Small PM-side mirror of the sector-aware equity research framework.

    The Equity Research tab has the full reporting framework; this compact registry keeps
    Portfolio Manager token usage low while still telling the LLM which metrics matter most
    for the company sector. Only metrics already present in the PM dataset are referenced.
    """
    get = row.get if hasattr(row, "get") else lambda k, default=None: default
    sector = _clean_text(get("sector"), "Unknown").lower()
    industry = _clean_text(get("industry"), "").lower()
    txt = f"{sector} {industry}"

    common = [
        "analyst_upside_pct", "forward_revenue_growth", "forward_eps_growth",
        "forward_pe", "trailing_pe", "price_to_sales", "price_to_book",
        "ret_3m", "ret_6m", "ret_12m", "relative_strength_3m",
        "price_vs_50dma", "price_vs_200dma", "rsi_14",
        "ann_vol_3m", "max_drawdown_1y", "debt_to_equity",
    ]
    frameworks = {
        "financials": {
            "framework": "Financials / banks",
            "primary_metrics": ["price_to_book", "return_on_equity", "return_on_assets", "forward_pe", "forward_eps_growth", "analyst_upside_pct", "debt_to_equity"],
            "valuation_note": "For banks and financials, put more weight on P/B, ROE/ROA, forward EPS, analyst upside, and balance-sheet risk than P/S or FCF margin.",
        },
        "technology": {
            "framework": "Technology / growth compounders",
            "primary_metrics": ["revenue_cagr_3y", "forward_revenue_growth", "forward_eps_growth", "fcf_cagr_3y", "operating_margin", "gross_margin", "forward_pe", "forward_ps", "price_to_sales", "debt_to_equity"],
            "valuation_note": "For technology, pay for growth only when supported by margins, FCF compounding, forward estimates, and durable momentum.",
        },
        "healthcare": {
            "framework": "Health Care",
            "primary_metrics": ["revenue_cagr_3y", "forward_revenue_growth", "forward_eps_growth", "operating_margin", "profit_margin", "return_on_equity", "forward_pe", "analyst_upside_pct", "debt_to_equity"],
            "valuation_note": "For health care, balance growth and profitability with valuation, analyst upside, and risk/drawdown control.",
        },
        "energy": {
            "framework": "Energy",
            "primary_metrics": ["fcf_yield", "fcf_margin", "operating_margin", "profit_margin", "return_on_equity", "forward_pe", "price_to_book", "debt_to_equity", "analyst_upside_pct"],
            "valuation_note": "For energy, favor cash generation, capital discipline, balance-sheet strength, and valuation; growth metrics are more cyclical.",
        },
        "consumer": {
            "framework": "Consumer / product companies",
            "primary_metrics": ["revenue_cagr_3y", "forward_revenue_growth", "forward_eps_growth", "gross_margin", "operating_margin", "fcf_cagr_3y", "forward_pe", "price_to_sales", "debt_to_equity", "analyst_upside_pct"],
            "valuation_note": "For consumer/product companies, balance brand-quality growth, margins, FCF growth, leverage, and valuation versus momentum.",
        },
        "industrial": {
            "framework": "Industrials / cyclicals",
            "primary_metrics": ["revenue_cagr_3y", "forward_revenue_growth", "forward_eps_growth", "operating_margin", "return_on_equity", "debt_to_equity", "forward_pe", "price_to_book", "analyst_upside_pct"],
            "valuation_note": "For industrials, emphasize cycle-adjusted growth, operating margin, ROE, leverage, valuation, and technical confirmation.",
        },
        "utilities": {
            "framework": "Utilities / defensive yield",
            "primary_metrics": ["forward_eps_growth", "return_on_equity", "debt_to_equity", "price_to_book", "forward_pe", "analyst_upside_pct", "beta"],
            "valuation_note": "For utilities, favor stability, leverage discipline, valuation, yield-like defensiveness, and lower beta over high-growth metrics.",
        },
        "real_estate": {
            "framework": "Real Estate / REIT proxy",
            "primary_metrics": ["price_to_book", "debt_to_equity", "forward_eps_growth", "return_on_equity", "forward_pe", "analyst_upside_pct", "beta"],
            "valuation_note": "For real estate, this app uses available proxy metrics; flag missing REIT-specific FFO/AFFO as a limitation.",
        },
    }
    if "financial" in txt or "bank" in txt or "insurance" in txt or "capital market" in txt:
        key = "financials"
    elif "technology" in txt or "software" in txt or "semiconductor" in txt:
        key = "technology"
    elif "health" in txt or "pharma" in txt or "biotech" in txt:
        key = "healthcare"
    elif "energy" in txt or "oil" in txt or "gas" in txt:
        key = "energy"
    elif "consumer" in txt or "retail" in txt or "restaurant" in txt or "auto" in txt:
        key = "consumer"
    elif "industrial" in txt or "aerospace" in txt or "defense" in txt or "machinery" in txt:
        key = "industrial"
    elif "utilit" in txt:
        key = "utilities"
    elif "real estate" in txt or "reit" in txt:
        key = "real_estate"
    else:
        key = "technology" if "communication" in txt else "consumer"
    cfg = dict(frameworks[key])
    cfg["technical_momentum_metrics"] = ["ret_1m", "ret_3m", "ret_6m", "ret_12m", "relative_strength_3m", "price_vs_50dma", "price_vs_200dma", "rsi_14", "macd_hist", "volume_vs_20d_avg"]
    cfg["common_risk_metrics"] = ["beta", "ann_vol_3m", "max_drawdown_1y", "drawdown_from_52w_high", "debt_to_equity", "liabilities_to_assets"]
    cfg["all_metrics_requested"] = list(dict.fromkeys(cfg["primary_metrics"] + common + cfg["technical_momentum_metrics"] + cfg["common_risk_metrics"]))
    return cfg


def _sector_metric_snapshot(row: pd.Series, max_metrics: int = 24) -> dict[str, Any]:
    cfg = _sector_framework_for_row(row)
    out = {
        "framework": cfg.get("framework"),
        "valuation_note": cfg.get("valuation_note"),
        "metrics": {},
        "missing_primary_metrics": [],
    }
    requested = cfg.get("all_metrics_requested", [])[:max_metrics]
    for metric in requested:
        if metric in row.index:
            val = _json_safe(row.get(metric))
            if val is None:
                if metric in cfg.get("primary_metrics", []):
                    out["missing_primary_metrics"].append(metric)
            else:
                out["metrics"][metric] = val
        elif metric in cfg.get("primary_metrics", []):
            out["missing_primary_metrics"].append(metric)
    return out


def _normalize_committee_targets(
    committee_result: dict[str, Any],
    recommendation_table: pd.DataFrame,
    portfolio_context: dict[str, Any],
) -> dict[str, Any]:
    """Repair LLM allocation math without changing the investment thesis.

    The LLM owns the ranking and intended sizing. This helper only enforces
    arithmetic: decimal weights, hard position caps, optional sector caps, and a
    CASH row when the selected universe cannot mathematically reach 100%.
    """
    if not isinstance(committee_result, dict):
        return committee_result
    recs = committee_result.get("recommendations", [])
    if not isinstance(recs, list) or recommendation_table is None or recommendation_table.empty:
        return committee_result

    max_position = float(_safe_float(portfolio_context.get("max_weight"), 0.18) or 0.18)
    max_sector = float(_safe_float(portfolio_context.get("max_sector_weight"), 1.0) or 1.0)
    target_total = float(np.clip(1.0 - (_safe_float(portfolio_context.get("cash_buffer"), 0.0) or 0.0), 0.0, 1.0))

    sector_map = {str(r.get("ticker", "")).upper(): _clean_text(r.get("sector"), "Unknown") for r in recommendation_table.to_dict(orient="records")}
    score_map = {str(r.get("ticker", "")).upper(): _safe_float(r.get("composite_score"), 5.0) for r in recommendation_table.to_dict(orient="records")}

    clean_items = []
    for item in recs:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker", "")).upper().strip()
        if not ticker:
            continue
        raw_target = _safe_float(item.get("recommended_target_weight") or item.get("target_weight") or item.get("ai_target_weight"), np.nan)
        if pd.isna(raw_target):
            raw_target = 0.0
        # Accept accidental percent inputs like 12 for 12%.
        if raw_target > 1.0:
            raw_target = raw_target / 100.0
        action = _normalize_llm_action(item.get("final_action"), fallback="Hold")
        if action in {"Sell", "Exit", "Avoid"}:
            raw_target = min(raw_target, 0.01)
        target = float(np.clip(raw_target, 0.0, max_position))
        item["recommended_target_weight"] = target
        item["target_weight_repaired_by_engine"] = bool(abs(target - raw_target) > 1e-9)
        item["target_weight_repair_note"] = "Clipped to hard max-position cap." if item["target_weight_repaired_by_engine"] else ""
        clean_items.append(item)

    # Enforce sector caps by scaling within breached sectors.
    for _ in range(8):
        sector_totals: dict[str, float] = {}
        for item in clean_items:
            ticker = str(item.get("ticker", "")).upper()
            sector = sector_map.get(ticker, "Unknown")
            sector_totals[sector] = sector_totals.get(sector, 0.0) + float(item.get("recommended_target_weight") or 0.0)
        breaches = {s: w for s, w in sector_totals.items() if w > max_sector + 1e-12}
        if not breaches:
            break
        for sector, total in breaches.items():
            if total <= 0:
                continue
            scale = max_sector / total
            for item in clean_items:
                ticker = str(item.get("ticker", "")).upper()
                if sector_map.get(ticker, "Unknown") == sector:
                    item["recommended_target_weight"] = float(item.get("recommended_target_weight") or 0.0) * scale
                    item["target_weight_repaired_by_engine"] = True
                    note = str(item.get("target_weight_repair_note") or "")
                    item["target_weight_repair_note"] = (note + " Sector cap applied.").strip()

    # If the LLM undershot the investable budget and there is mathematical room,
    # add the residual to the names it already liked most. This is conviction-weighted,
    # not equal-weighted, and still respects caps.
    for _ in range(20):
        total = sum(float(item.get("recommended_target_weight") or 0.0) for item in clean_items)
        shortage = target_total - total
        if shortage <= 1e-6:
            break
        eligible = []
        for item in clean_items:
            action = _normalize_llm_action(item.get("final_action"), fallback="Hold")
            if action in {"Sell", "Exit", "Avoid", "Trim"}:
                continue
            ticker = str(item.get("ticker", "")).upper()
            current = float(item.get("recommended_target_weight") or 0.0)
            room = max(0.0, max_position - current)
            if room <= 1e-6:
                continue
            sector = sector_map.get(ticker, "Unknown")
            sector_total = sum(float(x.get("recommended_target_weight") or 0.0) for x in clean_items if sector_map.get(str(x.get("ticker", "")).upper(), "Unknown") == sector)
            room = min(room, max(0.0, max_sector - sector_total))
            if room <= 1e-6:
                continue
            ai_score = _safe_float(item.get("composite_score"), score_map.get(ticker, 5.0))
            conf = str(item.get("confidence") or "medium").lower()
            conf_mult = {"low": 0.75, "medium": 1.0, "high": 1.25, "very high": 1.35}.get(conf, 1.0)
            priority = max(0.05, ai_score / 10.0) * conf_mult
            eligible.append((item, room, priority))
        if not eligible:
            break
        weight_sum = sum(room * priority for _, room, priority in eligible)
        if weight_sum <= 0:
            break
        added = 0.0
        for item, room, priority in eligible:
            add = min(room, shortage * ((room * priority) / weight_sum))
            if add > 0:
                item["recommended_target_weight"] = float(item.get("recommended_target_weight") or 0.0) + add
                item["target_weight_repaired_by_engine"] = True
                item["target_weight_repair_note"] = (str(item.get("target_weight_repair_note") or "") + " Budget residual allocated by conviction.").strip()
                added += add
        if added <= 1e-8:
            break

    final_total = sum(float(item.get("recommended_target_weight") or 0.0) for item in clean_items)
    cash_target = max(0.0, target_total - final_total) + max(0.0, 1.0 - target_total)
    committee_result["recommendations"] = clean_items
    committee_result["allocation_total_weight"] = round(final_total, 6)
    committee_result["cash_target_weight"] = round(cash_target, 6)
    committee_result["allocation_math_note"] = (
        f"Security targets sum to {final_total:.1%}; cash/unallocated is {cash_target:.1%}. "
        "If cash is above the requested buffer, the selected universe and hard caps did not leave enough room to invest 100%."
    )
    if cash_target > 1e-4:
        summary = str(committee_result.get("portfolio_committee_summary") or "")
        committee_result["portfolio_committee_summary"] = (summary + " " + committee_result["allocation_math_note"]).strip()
    return committee_result


def _extract_json_obj(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    text = str(raw).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _normalize_llm_action(action: Any, fallback: str = "Hold") -> str:
    raw = str(action or "").strip()
    if not raw:
        return fallback
    lowered = raw.lower()
    if lowered in _ACTION_ALIASES:
        return _ACTION_ALIASES[lowered]
    for allowed in ACTION_LADDER:
        if lowered == allowed.lower():
            return allowed
    return fallback


def _llm_client(openai_api_key: str):
    if not openai_api_key or OpenAI is None:
        return None
    return OpenAI(api_key=openai_api_key)


def _call_openai_json(payload: dict[str, Any], openai_api_key: str, model_name: str) -> tuple[dict[str, Any], str, str | None]:
    """One LLM call that returns parsed JSON, raw text, and an optional error."""
    client = _llm_client(openai_api_key)
    if client is None:
        return {}, "", "OpenAI key/package unavailable; using quantitative fallback."

    system_prompt = (
        "You are an institutional multi-agent AI portfolio committee and allocator. "
        "You are not a deterministic score calculator and you must not equal-weight by default. Specialist quantitative scores are evidence inputs only. "
        "Use judgment to form agent views, resolve conflicts, make final portfolio actions, and assign target weights. "
        "Use only supplied facts. Do not invent missing financial metrics. "
        "Do not use news; news is intentionally excluded. "
        "Return valid JSON only."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, default=str)},
    ]
    raw = ""
    try:
        # Responses API first for newer OpenAI packages.
        try:
            response = client.responses.create(model=model_name, input=messages, temperature=0.25)
        except TypeError:
            response = client.responses.create(model=model_name, input=messages)
        except Exception as exc:
            # Some models do not accept temperature; retry without it.
            if "temperature" in str(exc).lower() or "unsupported" in str(exc).lower():
                response = client.responses.create(model=model_name, input=messages)
            else:
                raise
        raw = getattr(response, "output_text", None) or ""
        return _extract_json_obj(raw), raw, None
    except Exception as first_exc:
        try:
            kwargs = {"model": model_name, "messages": messages}
            try:
                response = client.chat.completions.create(**kwargs, temperature=0.25)
            except TypeError:
                response = client.chat.completions.create(**kwargs)
            except Exception as exc:
                if "temperature" in str(exc).lower() or "unsupported" in str(exc).lower():
                    response = client.chat.completions.create(**kwargs)
                else:
                    raise
            raw = response.choices[0].message.content or ""
            return _extract_json_obj(raw), raw, None
        except Exception as second_exc:
            return {}, raw, f"OpenAI committee failed: {second_exc or first_exc}"


def _agentic_evidence_pack(
    recommendation_table: pd.DataFrame,
    portfolio_context: dict[str, Any],
    regime_info: dict[str, Any],
    max_names: int = 35,
) -> dict[str, Any]:
    recs = recommendation_table.copy() if recommendation_table is not None else pd.DataFrame()
    if not recs.empty:
        # Keep all owned names plus strongest watchlist names. Sorting by composite is only
        # a token-budget choice; the LLM is explicitly told not to treat it as a ranking rule.
        recs = recs.sort_values(["current_weight", "composite_score"], ascending=[False, False]).head(max_names)

    evidence = []
    base_cols = [
        "ticker", "company_name", "asset_type", "sector", "industry", "current_weight",
        "market_value", "shares", "last_price", "final_action", "trade_direction",
        "composite_score", "fundamental_score", "valuation_score", "forward_score",
        "technical_score", "capital_policy_score", "risk_fit_score", "portfolio_fit_score",
        "analyst_upside_pct", "data_quality_score", "data_quality_label",
        "triggered_guardrails", "key_supports", "key_conflicts", "risks", "next_steps",
        "missing_evidence", "decision_reason", "pm_decision_summary",
        "agentic_target_weight", "agentic_target_weight_rationale",
    ]
    metric_cols = [
        # Sector-aware equity research metrics already available in the PM dataset.
        "revenue_cagr_3y", "net_income_cagr_3y", "fcf_cagr_3y", "revenue_growth",
        "earnings_growth", "forward_revenue_growth", "forward_eps_growth",
        "gross_margin", "operating_margin", "profit_margin", "ebitda_margin",
        "ocf_margin", "fcf_margin", "cash_conversion", "return_on_equity",
        "return_on_assets", "current_ratio", "debt_to_equity", "liabilities_to_assets",
        "forward_pe", "forward_ps", "trailing_pe", "price_to_book", "price_to_sales",
        "price_to_fcf", "enterprise_to_revenue", "earnings_yield", "fcf_yield",
        "target_mean_price", "price_target_consensus", "rating_score", "market_cap", "beta",
        # Technicals and momentum.
        "ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_1y",
        "relative_strength_3m", "rel_3m_vs_benchmark", "price_vs_50dma", "price_vs_200dma",
        "rsi_14", "macd", "macd_signal", "macd_hist", "atr_14", "ann_vol_3m",
        "realized_vol_20d", "drawdown_from_52w_high", "distance_from_52w_low",
        "max_drawdown_1y", "volume_vs_20d_avg",
    ]
    use_cols = [c for c in list(dict.fromkeys(base_cols + metric_cols)) if c in recs.columns]
    for _, row in recs.iterrows():
        item = {k: _json_safe(row.get(k)) for k in use_cols}
        item["sector_aware_equity_research_framework"] = _sector_metric_snapshot(row)
        evidence.append(item)

    target_total = float(np.clip(1.0 - (_safe_float(portfolio_context.get("cash_buffer"), 0.0) or 0.0), 0.0, 1.0))
    max_position = float(_safe_float(portfolio_context.get("max_weight"), 0.18) or 0.18)
    max_sector = float(_safe_float(portfolio_context.get("max_sector_weight"), 0.35) or 0.35)
    capacity = len(evidence) * max_position

    return {
        "task": "Redo the AI Portfolio Manager as a true multi-agent balancing recommendation, with no news inputs.",
        "portfolio_context": _json_safe(portfolio_context),
        "macro_regime": _json_safe(regime_info),
        "allocation_budget": {
            "target_total_security_weight": round(target_total, 6),
            "required_cash_buffer": round(1.0 - target_total, 6),
            "max_single_position_weight": round(max_position, 6),
            "max_sector_weight": round(max_sector, 6),
            "selected_security_capacity_at_single_name_cap": round(capacity, 6),
            "math_warning": (
                "If selected_security_capacity_at_single_name_cap is below target_total_security_weight, "
                "the securities cannot sum to 100% under the max-position cap. Put the difference in CASH and explain it."
            ),
        },
        "action_ladder": ACTION_LADDER,
        "important_instruction": (
            "Technicals, momentum, and the sector-aware equity research metrics are the core evidence. "
            "The base scores/actions are only evidence. The agents must debate the tradeoff between quality, valuation, forward estimates, technical trend, risk, current concentration, and sector exposure."
        ),
        "specialist_agents": [
            "Sector-Aware Fundamental Quality Agent",
            "Sector-Aware Valuation Discipline Agent",
            "Forward Estimates / Earnings Revision Agent",
            "Technical Momentum Agent",
            "Risk / Drawdown Agent",
            "Portfolio Fit / Concentration Agent",
            "Capital Allocation / Rebalance Agent",
            "Lead PM Decision Agent",
        ],
        "rules": [
            "Use supplied data only; do not invent metrics.",
            "Do not use news or article sentiment.",
            "For each ticker, evaluate the sector-aware metric snapshot first, then the technical/momentum setup, then risk and portfolio fit.",
            "ETFs/funds should be judged on role, momentum, risk, liquidity, and diversification, not missing company fundamentals.",
            "Owned positions may be Add, Hold, Trim, or Sell. Unowned names may be Strong Add, Add, Hold / Watch, or Sell only if clearly unsuitable.",
            "Treat max_position_weight and max_sector_weight as hard caps only, never as target weights.",
            "Do not equal-weight names unless the evidence truly supports equal conviction.",
            "Return target weights as decimals, not percent strings. Example: 0.115 means 11.5%.",
            "Security target weights should sum to target_total_security_weight when mathematically possible after caps. If not possible, include a cash_target_weight for the residual.",
            "Recommended target weights must reflect relative conviction learned from the data, not user defaults.",
            "Explicitly identify what to look out for: technical breakdowns, valuation risk, estimate risk, leverage risk, sector concentration, or data gaps.",
            "Final actions must be one of the action ladder values."
        ],
        "recommendation_evidence": evidence,
        "required_json_schema": {
            "portfolio_committee_summary": "Plain English summary of the committee debate and allocation decision.",
            "cash_target_weight": "decimal cash/unallocated weight if constraints prevent full security allocation",
            "recommendations": [
                {
                    "ticker": "symbol",
                    "final_action": "Sell | Trim | Hold / Watch | Hold | Add | Strong Add",
                    "confidence": "low | medium | high",
                    "composite_score": "0-10 AI judgment score, can differ from base score",
                    "recommended_target_weight": "decimal target portfolio weight from 0.0 to max_position_weight",
                    "target_weight_rationale": "why this target weight is appropriate versus current weight and other names",
                    "allocation_role": "core holding | satellite growth | defensive diversifier | tactical trade | funding source | avoid",
                    "decision_reason": "short reason",
                    "key_supports": ["support 1", "support 2"],
                    "key_conflicts": ["conflict 1"],
                    "risks": ["risk 1"],
                    "next_steps": ["specific thing to monitor"],
                    "agent_views": {
                        "fundamental": {"score": "0-10", "verdict": "bullish/neutral/bearish", "summary": "short sector-aware metric view"},
                        "valuation": {"score": "0-10", "verdict": "bullish/neutral/bearish", "summary": "short valuation view"},
                        "forward": {"score": "0-10", "verdict": "bullish/neutral/bearish", "summary": "short estimate/growth view"},
                        "technical": {"score": "0-10", "verdict": "bullish/neutral/bearish", "summary": "short momentum/technical view"},
                        "risk": {"score": "0-10", "verdict": "bullish/neutral/bearish", "summary": "short risk view"},
                        "portfolio_fit": {"score": "0-10", "verdict": "bullish/neutral/bearish", "summary": "short concentration/diversification view"},
                        "capital_policy": {"score": "0-10", "verdict": "bullish/neutral/bearish", "summary": "short rebalance/funding view"}
                    }
                }
            ]
        },
    }


def _apply_llm_agent_view(agent: AgentResult | None, view: dict[str, Any] | None) -> None:
    if agent is None or not isinstance(view, dict):
        return
    try:
        score = _safe_float(view.get("score"), np.nan)
        if not pd.isna(score):
            agent.score = float(np.clip(score, 0.0, 10.0))
    except Exception:
        pass
    if view.get("verdict"):
        agent.verdict = str(view.get("verdict"))[:80]
    if view.get("summary"):
        agent.summary = [str(view.get("summary"))[:300]]
    agent.metrics = dict(agent.metrics or {})
    agent.metrics["llm_agent_override"] = True


def _apply_agentic_committee_to_bundles(
    bundles: dict[str, TickerAnalysisBundle],
    committee_result: dict[str, Any],
) -> dict[str, int]:
    recommendations = committee_result.get("recommendations", []) if isinstance(committee_result, dict) else []
    if not isinstance(recommendations, list):
        recommendations = []
    by_ticker: dict[str, dict[str, Any]] = {}
    for item in recommendations:
        if isinstance(item, dict):
            ticker = str(item.get("ticker", "")).upper().strip()
            if ticker:
                by_ticker[ticker] = item

    changed = 0
    reviewed = 0
    for ticker, bundle in bundles.items():
        item = by_ticker.get(str(ticker).upper())
        if not item or bundle.final is None:
            continue
        reviewed += 1
        final = bundle.final
        base_action = final.final_action
        action = _normalize_llm_action(item.get("final_action"), fallback=base_action)
        score = _safe_float(item.get("composite_score"), np.nan)
        if not pd.isna(score):
            final.composite_score = round(float(np.clip(score, 0.0, 10.0)), 2)
            final.absolute_score = final.composite_score
        final.final_action = action
        final.action_bias = action

        # Agentic allocation: the LLM committee owns the target-weight recommendation.
        # The rebalance engine will treat this as the source-of-truth target and only
        # apply hard risk constraints such as max single-name and max sector weight.
        target_weight = _safe_float(
            item.get("recommended_target_weight")
            or item.get("target_weight")
            or item.get("ai_target_weight"),
            np.nan,
        )
        if not pd.isna(target_weight):
            max_w = _safe_float((final.raw_metrics or {}).get("max_position_weight"), np.nan)
            if pd.isna(max_w):
                max_w = _safe_float((final.raw_metrics or {}).get("max_weight"), 0.18) or 0.18
            target_weight = float(np.clip(target_weight, 0.0, max_w))
            final.raw_metrics = dict(final.raw_metrics or {})
            final.raw_metrics["agentic_target_weight"] = target_weight
            final.raw_metrics["ai_target_weight"] = target_weight
            final.raw_metrics["agentic_target_weight_rationale"] = str(
                item.get("target_weight_rationale") or item.get("allocation_rationale") or "LLM committee target weight."
            )[:300]
            final.raw_metrics["allocation_role"] = str(item.get("allocation_role") or "")[:80]
        final.decision_confidence = str(item.get("confidence") or final.decision_confidence).lower()
        final.consensus_state = "AI committee reviewed"
        final.decision_reason = str(item.get("decision_reason") or final.decision_reason)[:250]
        final.pm_decision_summary = f"{ticker}: {action}. {final.decision_reason}"
        for attr in ["key_supports", "key_conflicts", "risks", "next_steps"]:
            val = item.get(attr)
            if isinstance(val, list) and val:
                setattr(final, attr, [str(x)[:250] for x in val[:4]])
            elif isinstance(val, str) and val.strip():
                setattr(final, attr, [val.strip()[:250]])
        final.why = final.key_supports or final.why
        final.explanation = (
            f"AI Lead PM decision: {action}\n"
            f"AI decision reason: {final.decision_reason}\n"
            f"Base quantitative action before AI review: {base_action}\n"
            f"The final action was produced by the LLM agent committee using the scorecard as evidence, not as a hard rule."
        )
        final.raw_metrics = dict(final.raw_metrics or {})
        final.raw_metrics["base_quant_action_before_ai"] = base_action
        final.raw_metrics["llm_final_action"] = action
        final.raw_metrics["llm_decision_reason"] = final.decision_reason
        if action != base_action:
            changed += 1

        views = item.get("agent_views", {}) if isinstance(item.get("agent_views"), dict) else {}
        _apply_llm_agent_view(bundle.fundamentals, views.get("fundamental"))
        _apply_llm_agent_view(bundle.valuation, views.get("valuation"))
        _apply_llm_agent_view(bundle.earnings, views.get("forward"))
        _apply_llm_agent_view(bundle.technicals, views.get("technical"))
        _apply_llm_agent_view(bundle.risk, views.get("risk"))
        _apply_llm_agent_view(bundle.portfolio_fit, views.get("portfolio_fit"))
        _apply_llm_agent_view(bundle.catalysts, views.get("capital_policy"))
        if bundle.debate is not None:
            bundle.debate.action_tilt = action
            bundle.debate.consensus_state = "AI committee reviewed"
            bundle.debate.support_reasons = final.key_supports
            bundle.debate.conflict_reasons = final.key_conflicts
            bundle.debate.open_questions = final.missing_evidence
    return {"reviewed": reviewed, "changed": changed}


def _run_agentic_llm_committee(
    bundles: dict[str, TickerAnalysisBundle],
    recommendation_table: pd.DataFrame,
    portfolio_context: dict[str, Any],
    regime_info: dict[str, Any],
    openai_api_key: str,
    model_name: str,
) -> dict[str, Any]:
    evidence_pack = _agentic_evidence_pack(recommendation_table, portfolio_context, regime_info)
    parsed, raw, error = _call_openai_json(evidence_pack, openai_api_key, model_name)
    if error or not parsed:
        return {
            "status": "fallback_quantitative",
            "error": error or "AI committee did not return parseable JSON; used quantitative fallback.",
            "raw_response": raw,
            "openai_calls": 0 if error and "unavailable" in error.lower() else 1,
            "reviewed": 0,
            "changed": 0,
        }
    parsed = _normalize_committee_targets(parsed, recommendation_table, portfolio_context)
    stats = _apply_agentic_committee_to_bundles(bundles, parsed)
    return {
        "status": "ai_committee_applied",
        "error": "",
        "raw_response": raw,
        "openai_calls": 1,
        "portfolio_committee_summary": parsed.get("portfolio_committee_summary", ""),
        "cash_target_weight": parsed.get("cash_target_weight", 0.0),
        "allocation_total_weight": parsed.get("allocation_total_weight", None),
        "allocation_math_note": parsed.get("allocation_math_note", ""),
        **stats,
    }

def _build_deterministic_committee_summary(portfolio_summary: dict[str, Any], recommendation_table: pd.DataFrame, regime_info: dict[str, Any]) -> str:
    if recommendation_table is None or recommendation_table.empty:
        return "No recommendation table was created."
    adds = recommendation_table[recommendation_table["final_action"].isin(["Add", "Start / Rotate In", "Buy", "Strong Buy"])]
    trims = recommendation_table[recommendation_table["final_action"].isin(["Trim", "Sell", "Exit"])]
    top = recommendation_table.sort_values("composite_score", ascending=False).head(3)
    tech = recommendation_table.sort_values("technical_score", ascending=False).head(3) if "technical_score" in recommendation_table.columns else pd.DataFrame()
    lines = [
        "Portfolio Committee Summary",
        f"Macro regime: {regime_info.get('regime', 'Unknown')}.",
        f"Portfolio value: ${float(portfolio_summary.get('portfolio_value') or 0):,.0f}.",
        f"Actions: {len(adds)} add/start candidates, {len(trims)} trim/sell candidates, {int((recommendation_table['final_action'] == 'Hold').sum())} holds.",
        "Top composite ideas: " + ", ".join([f"{r.ticker} ({r.composite_score:.1f})" for r in top.itertuples(index=False)]),
    ]
    if not tech.empty:
        lines.append("Best technical/momentum setups: " + ", ".join([f"{r.ticker} ({r.technical_score:.1f})" for r in tech.itertuples(index=False)]))
    if not trims.empty:
        lines.append("Primary funding / risk-control candidates: " + ", ".join(trims["ticker"].astype(str).head(5).tolist()))
    lines.append("This summary is the quantitative fallback. When an OpenAI key is loaded, the final actions are reviewed and overwritten by the LLM agent committee during the engine run.")
    return "\n".join(lines)


def run_portfolio_decision_workflow(
    mode: str,
    benchmark: str,
    period: str,
    enable_news: bool,
    news_lookback_days: int,
    openai_api_key: str,
    model_name: str,
    marketaux_api_key: str = "",
    fmp_api_key: str = "",
    max_weight: float = 0.18,
    max_sector_weight: float = 0.35,
    cash_buffer: float = 0.00,
    starter_min_weight: float = 0.025,
    min_trade_weight_change: float = 0.0025,
    holdings_df: pd.DataFrame | None = None,
    tickers_text: str = "",
    screen_filters: dict[str, Any] | None = None,
    selected_screen_tickers: list[str] | None = None,
) -> dict[str, Any]:
    benchmark = (benchmark or "SPY").upper().strip()
    selected_screen_tickers = [str(x).upper().strip() for x in (selected_screen_tickers or []) if str(x).strip()]

    holdings = pd.DataFrame(columns=["ticker", "shares"])
    input_tickers: list[str] = []
    screen_df = pd.DataFrame()
    screen_meta: dict[str, Any] = {}

    if mode == "holdings":
        holdings = _normalize_holdings_df(holdings_df)
        input_tickers = holdings["ticker"].tolist() + _normalize_tickers(tickers_text)
    elif mode == "manual":
        input_tickers = _normalize_tickers(tickers_text)
        if not input_tickers:
            raise ValueError("Enter at least one ticker.")
    elif mode == "screen":
        screen_df, screen_meta = run_fmp_screen(screen_filters or {}, fmp_api_key)
        if screen_df.empty:
            raise ValueError("The FMP screener returned no names. Adjust the filters and try again.")
        input_tickers = selected_screen_tickers or screen_df["ticker"].astype(str).head(int((screen_filters or {}).get("analyze_top_n", 15))).tolist()
    else:
        raise ValueError("Unsupported mode.")

    tickers = sorted({t for t in input_tickers if t})
    if benchmark not in tickers:
        tickers = tickers + [benchmark]

    prices = fetch_price_history(tickers, period=period)
    if prices.empty:
        raise ValueError("No price history was returned for the selected tickers.")
    if benchmark not in prices.columns:
        benchmark = prices.columns[0]

    analysis_tickers = [t for t in tickers if t in prices.columns and t != benchmark]
    if not analysis_tickers:
        raise ValueError("None of the selected tickers returned usable price history.")

    company_info = fetch_company_info(analysis_tickers + [benchmark])

    if not holdings.empty:
        available_holdings = [t for t in holdings["ticker"].tolist() if t in prices.columns]
        position_prices = prices[available_holdings].iloc[-1] if available_holdings else pd.Series(dtype=float)
        position_snapshot = compute_position_snapshot(holdings[holdings["ticker"].isin(available_holdings)], position_prices, company_info)
    else:
        position_snapshot = pd.DataFrame(columns=["ticker", "shares", "market_value", "current_weight", "sector", "industry", "company_name"])

    # News is intentionally disabled in the AI Portfolio Manager to avoid token-heavy
    # article ingestion. News can remain in the Equity Research workflow where it belongs.
    news_articles = pd.DataFrame()
    news_summary = pd.DataFrame()

    dataset = build_multi_agent_dataset(
        tickers=analysis_tickers,
        prices=prices[analysis_tickers + [benchmark]] if benchmark in prices.columns else prices[analysis_tickers],
        company_info=company_info,
        benchmark_col=benchmark,
        news_summary=news_summary,
        position_snapshot=position_snapshot,
        fmp_api_key=fmp_api_key,
        comparison_mode=len(analysis_tickers) > 1,
    )
    dataset = dataset[dataset["ticker"].isin(analysis_tickers)].copy() if not dataset.empty else dataset
    if dataset.empty:
        raise ValueError("The portfolio dataset is empty after processing.")

    for col, default in [("shares", 0.0), ("market_value", 0.0), ("current_weight", 0.0)]:
        if col not in dataset.columns:
            dataset[col] = default
        dataset[col] = pd.to_numeric(dataset[col], errors="coerce").fillna(default)

    dataset["portfolio_mode"] = not position_snapshot.empty
    dataset["comparison_mode"] = len(analysis_tickers) > 1
    dataset["is_fund_like"] = dataset.apply(_is_fund_like, axis=1)
    dataset["asset_type"] = np.where(dataset["is_fund_like"], "ETF / Fund", "Equity")

    # For ETFs/funds, missing revenue/EPS/margins/analyst-estimate fields should not lower
    # confidence. Rebase data quality on fields that actually matter for fund decisions.
    fund_quality_cols = [
        c for c in [
            "last_price", "ret_1m", "ret_3m", "ret_6m", "ret_12m", "price_vs_50dma",
            "price_vs_200dma", "rsi_14", "relative_strength_3m", "ann_vol_3m",
            "max_drawdown_1y", "drawdown_from_52w_high", "market_value", "current_weight",
        ] if c in dataset.columns
    ]
    if fund_quality_cols:
        fund_mask = dataset["is_fund_like"].astype(bool)
        fund_quality = dataset.loc[fund_mask, fund_quality_cols].notna().mean(axis=1).astype(float)
        dataset.loc[fund_mask, "data_quality_score"] = fund_quality.clip(lower=0.45, upper=1.0)
        dataset.loc[fund_mask, "data_quality_label"] = np.select(
            [dataset.loc[fund_mask, "data_quality_score"] >= 0.78, dataset.loc[fund_mask, "data_quality_score"] >= 0.55],
            ["high", "medium"],
            default="low",
        )

    dataset["max_position_weight"] = max_weight
    dataset["max_sector_weight"] = max_sector_weight

    portfolio_context = _build_portfolio_context(position_snapshot, max_weight, max_sector_weight, cash_buffer)
    bundles = _run_light_agent_committee(dataset=dataset, portfolio_context=portfolio_context)
    recommendation_table = _recommendation_table_from_bundles(bundles)
    decision_audit_table = _decision_audit_table(recommendation_table)
    technical_signal_table = _technical_signal_table(recommendation_table)
    action_buckets = split_recommendation_buckets(recommendation_table)

    portfolio_value = float(position_snapshot["market_value"].sum()) if not position_snapshot.empty else 0.0
    rebalance_table = compute_recommended_rebalance(
        recommendation_table=recommendation_table,
        portfolio_value=portfolio_value if portfolio_value > 0 else None,
        cash_buffer=cash_buffer,
        max_position_weight=max_weight,
        max_sector_weight=max_sector_weight,
        starter_min_weight=starter_min_weight,
        min_trade_weight_change=min_trade_weight_change,
    )
    regime_info = compute_market_regime(prices[[benchmark]]) if benchmark in prices.columns else compute_market_regime(prices)

    ai_committee_result = _run_agentic_llm_committee(
        bundles=bundles,
        recommendation_table=recommendation_table,
        portfolio_context=portfolio_context,
        regime_info=regime_info,
        openai_api_key=openai_api_key,
        model_name=model_name,
    )
    if ai_committee_result.get("status") == "ai_committee_applied":
        recommendation_table = _recommendation_table_from_bundles(bundles)
        decision_audit_table = _decision_audit_table(recommendation_table)
        technical_signal_table = _technical_signal_table(recommendation_table)
        action_buckets = split_recommendation_buckets(recommendation_table)
        rebalance_table = compute_recommended_rebalance(
            recommendation_table=recommendation_table,
            portfolio_value=portfolio_value if portfolio_value > 0 else None,
            cash_buffer=cash_buffer,
            max_position_weight=max_weight,
            max_sector_weight=max_sector_weight,
            starter_min_weight=starter_min_weight,
            min_trade_weight_change=min_trade_weight_change,
        )

    portfolio_summary = {
        "mode": mode,
        "portfolio_value": portfolio_value,
        "benchmark": benchmark,
        "regime": regime_info.get("regime"),
        "cash_buffer": cash_buffer,
        "max_position_weight": max_weight,
        "max_sector_weight": max_sector_weight,
        "holding_count": int(len(position_snapshot)),
        "analysis_count": int(len(recommendation_table)),
        "best_idea": None if recommendation_table.empty else recommendation_table.sort_values("composite_score", ascending=False).iloc[0]["ticker"],
        "token_mode": "LLM agent committee applied" if ai_committee_result.get("status") == "ai_committee_applied" else "quantitative fallback; OpenAI committee unavailable",
    }

    sector_allocation_table = build_sector_allocation_table(position_snapshot, rebalance_table, portfolio_value=portfolio_value)
    target_weight_explanations = build_target_weight_explanations(rebalance_table)
    stress_scenario_table = build_stress_scenario_table(recommendation_table, rebalance_table, sector_allocation_table)
    committee_summary = ai_committee_result.get("portfolio_committee_summary") or _build_deterministic_committee_summary(portfolio_summary, recommendation_table, regime_info)

    return {
        "mode": mode,
        "holdings": holdings,
        "screen_df": screen_df,
        "screen_meta": screen_meta,
        "benchmark": benchmark,
        "prices": prices,
        "company_info": company_info,
        "position_snapshot": position_snapshot,
        "dataset": dataset,
        "bundles": bundles,
        "recommendation_table": recommendation_table,
        "decision_audit_table": decision_audit_table,
        "technical_signal_table": technical_signal_table,
        "rebalance_table": rebalance_table,
        "sector_allocation_table": sector_allocation_table,
        "target_weight_explanations": target_weight_explanations,
        "stress_scenario_table": stress_scenario_table,
        "portfolio_committee_summary": committee_summary,
        "run_diagnostics": {
            "input_tickers": input_tickers,
            "analysis_tickers": analysis_tickers,
            "price_columns_returned": list(prices.columns),
            "missing_price_tickers": sorted(set(input_tickers) - set(analysis_tickers)),
            "news_enabled": False,
            "news_rows": 0,
            "news_removed_from_pm": True,
            "fmp_key_loaded": bool(fmp_api_key),
            "marketaux_key_loaded": bool(marketaux_api_key),
            "openai_key_loaded": bool(openai_api_key),
            "cash_buffer": cash_buffer,
            "max_position_weight": max_weight,
            "max_sector_weight": max_sector_weight,
            "starter_min_weight": starter_min_weight,
            "min_trade_weight_change": min_trade_weight_change,
            "engine_version": "agentic_sector_aware_technical_momentum_rebalance_v6",
            "cash_target_weight": ai_committee_result.get("cash_target_weight", 0.0),
            "allocation_total_weight": ai_committee_result.get("allocation_total_weight"),
            "allocation_math_note": ai_committee_result.get("allocation_math_note", ""),
            "agentic_ai_status": ai_committee_result.get("status"),
            "agentic_ai_error": ai_committee_result.get("error"),
            "agentic_ai_reviewed": ai_committee_result.get("reviewed", 0),
            "agentic_ai_changed_actions": ai_committee_result.get("changed", 0),
            "openai_calls_during_run": ai_committee_result.get("openai_calls", 0),
            "allocation_mode": "agentic_target_weights" if ("agentic_target_weight" in recommendation_table.columns and recommendation_table["agentic_target_weight"].notna().any()) else "fallback_rebalance_engine",
        },
        "regime_info": regime_info,
        "news_articles": pd.DataFrame(),
        "news_summary": pd.DataFrame(),
        "portfolio_summary": portfolio_summary,
        "agentic_ai_committee_result": ai_committee_result,
        "pm_note": committee_summary,
        "bucket_add": action_buckets["add"],
        "bucket_hold": action_buckets["hold"],
        "bucket_trim": action_buckets["trim"],
        "bucket_sell": action_buckets["sell"],
        "bucket_watchlist": action_buckets["watchlist"],
        "bucket_avoid": action_buckets.get("avoid", pd.DataFrame()),
    }
