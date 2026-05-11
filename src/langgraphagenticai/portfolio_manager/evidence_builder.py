from __future__ import annotations

from typing import Any
import math
import numpy as np
import pandas as pd

COMMON_ETF_TICKERS = {
    "SPY", "VOO", "IVV", "VTI", "VT", "QQQ", "QQQM", "DIA", "IWM", "IJR", "MDY",
    "SCHD", "VIG", "VYM", "DGRO", "NOBL", "SPYD", "JEPI", "JEPQ", "XLK", "XLF", "XLV",
    "XLY", "XLP", "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC", "SMH", "SOXX", "ARKK",
    "KRE", "KBE", "TLT", "IEF", "SHY", "BIL", "SGOV", "AGG", "BND", "LQD", "HYG",
    "GLD", "IAU", "SLV", "DBC", "VNQ", "IYR", "EFA", "VEA", "EEM", "VWO", "VXUS", "ACWI",
}

SECTOR_DEFAULT = "Unclassified"


def safe_float(x: Any, default: float | None = np.nan) -> float:
    try:
        if x is None or pd.isna(x):
            return default
        value = float(x)
        if isinstance(value, complex) or math.isnan(value) or math.isinf(value):
            return default
        return value
    except Exception:
        return default


def clean_text(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    text = str(x).strip()
    return text if text else default


def pct_points(x: Any) -> float:
    """Return a percent-style number from either decimal or percent inputs."""
    value = safe_float(x, np.nan)
    if pd.isna(value):
        return np.nan
    if abs(value) <= 2.0:
        return value * 100.0
    return value


def score_high(value: Any, low: float, high: float) -> float:
    value = safe_float(value, np.nan)
    if pd.isna(value):
        return 5.0
    if high == low:
        return 5.0
    return float(np.clip((value - low) / (high - low) * 10.0, 0.0, 10.0))


def score_low(value: Any, low: float, high: float) -> float:
    value = safe_float(value, np.nan)
    if pd.isna(value):
        return 5.0
    if high == low:
        return 5.0
    return float(np.clip((high - value) / (high - low) * 10.0, 0.0, 10.0))


def score_abs_low(value: Any, good: float, bad: float) -> float:
    return score_low(abs(safe_float(value, 0.0)), good, bad)


def is_fund_like(row: pd.Series | dict[str, Any]) -> bool:
    get = row.get if isinstance(row, dict) else row.get
    ticker = clean_text(get("ticker"), "").upper()
    quote_type = clean_text(get("quoteType"), "").lower()
    asset_type = clean_text(get("asset_type"), "").lower()
    name = f"{get('company_name', '')} {get('shortName', '')} {get('longName', '')}".lower()
    if ticker in COMMON_ETF_TICKERS:
        return True
    if any(token in quote_type for token in ["etf", "fund"]):
        return True
    if any(token in asset_type for token in ["etf", "fund"]):
        return True
    return any(token in name for token in [" etf", " fund", "trust", "index", "sector spdr"])


def _coalesce(row: pd.Series, names: list[str], default: Any = np.nan) -> Any:
    for name in names:
        if name in row.index:
            value = row.get(name)
            try:
                if pd.notna(value):
                    return value
            except Exception:
                if value not in [None, ""]:
                    return value
    return default


def _label(score: float, strong: str, weak: str, neutral: str = "mixed") -> str:
    if score >= 7.0:
        return strong
    if score <= 4.0:
        return weak
    return neutral


def _technical_signal(row: pd.Series) -> tuple[float, str, list[str], list[str]]:
    ret_1m = pct_points(_coalesce(row, ["ret_1m"]))
    ret_3m = pct_points(_coalesce(row, ["ret_3m", "relative_strength_3m"]))
    ret_6m = pct_points(_coalesce(row, ["ret_6m"]))
    ret_12m = pct_points(_coalesce(row, ["ret_12m", "ret_1y"]))
    px50 = pct_points(_coalesce(row, ["price_vs_50dma"]))
    px200 = pct_points(_coalesce(row, ["price_vs_200dma"]))
    rsi = safe_float(_coalesce(row, ["rsi_14"]), np.nan)
    rel = pct_points(_coalesce(row, ["relative_strength_3m", "rel_3m_vs_benchmark"]))

    scores = [
        score_high(ret_1m, -8, 10),
        score_high(ret_3m, -12, 20),
        score_high(ret_6m, -18, 35),
        score_high(ret_12m, -25, 50),
        score_high(px50, -8, 8),
        score_high(px200, -15, 20),
        score_high(rel, -10, 12),
    ]
    if pd.notna(rsi):
        if rsi < 30:
            scores.append(4.0)
        elif rsi <= 70:
            scores.append(7.0)
        elif rsi <= 82:
            scores.append(6.0)
        else:
            scores.append(4.5)
    score = float(np.nanmean(scores)) if scores else 5.0
    supports: list[str] = []
    conflicts: list[str] = []
    if pd.notna(px200):
        (supports if px200 > 0 else conflicts).append(f"price vs 200DMA {px200:.1f}%")
    if pd.notna(ret_3m):
        (supports if ret_3m > 0 else conflicts).append(f"3M return {ret_3m:.1f}%")
    if pd.notna(rel):
        (supports if rel > 0 else conflicts).append(f"relative strength {rel:.1f}%")
    if pd.notna(rsi) and rsi > 80:
        conflicts.append(f"RSI elevated at {rsi:.0f}")
    elif pd.notna(rsi):
        supports.append(f"RSI {rsi:.0f}")
    return score, _label(score, "positive", "weak", "mixed"), supports, conflicts


def _fundamental_score(row: pd.Series, fund_like: bool) -> tuple[float, str, list[str], list[str]]:
    if fund_like:
        return 5.8, "fund/ETF - fundamentals not scored", ["fund/ETF judged mainly on trend, risk, diversification, and portfolio role"], []
    rev = pct_points(_coalesce(row, ["revenue_cagr_3y", "revenue_growth"]))
    fcf = pct_points(_coalesce(row, ["fcf_cagr_3y", "fcf_growth"]))
    opm = pct_points(_coalesce(row, ["operating_margin", "ebitda_margin", "profit_margin"]))
    roe = pct_points(_coalesce(row, ["return_on_equity"]))
    debt = safe_float(_coalesce(row, ["debt_to_equity", "debtEquityRatio"]), np.nan)
    fcf_yield = pct_points(_coalesce(row, ["fcf_yield"]))
    scores = [
        score_high(rev, -5, 20), score_high(fcf, -10, 25), score_high(opm, 0, 35),
        score_high(roe, 0, 30), score_low(debt, 0, 2.5), score_high(fcf_yield, -2, 8),
    ]
    score = float(np.nanmean(scores))
    supports, conflicts = [], []
    if pd.notna(rev): (supports if rev > 8 else conflicts).append(f"3Y revenue growth {rev:.1f}%")
    if pd.notna(fcf): (supports if fcf > 8 else conflicts).append(f"3Y FCF growth {fcf:.1f}%")
    if pd.notna(opm): (supports if opm > 15 else conflicts).append(f"operating margin {opm:.1f}%")
    if pd.notna(roe): (supports if roe > 12 else conflicts).append(f"ROE {roe:.1f}%")
    if pd.notna(debt): (supports if debt < 1.2 else conflicts).append(f"debt/equity {debt:.2f}")
    return score, _label(score, "strong", "weak", "mixed"), supports, conflicts


def _valuation_score(row: pd.Series, fund_like: bool) -> tuple[float, str, list[str], list[str]]:
    if fund_like:
        return 5.5, "fund/ETF - valuation not primary", ["valuation multiples are not the main ETF/fund sizing input"], []
    fpe = safe_float(_coalesce(row, ["forward_pe"]), np.nan)
    tpe = safe_float(_coalesce(row, ["trailing_pe"]), np.nan)
    ps = safe_float(_coalesce(row, ["forward_ps", "price_to_sales"]), np.nan)
    pb = safe_float(_coalesce(row, ["price_to_book"]), np.nan)
    ev_ebitda = safe_float(_coalesce(row, ["enterprise_to_ebitda"]), np.nan)
    upside = pct_points(_coalesce(row, ["analyst_upside_pct", "Price Target Upside"]))
    scores = [score_low(fpe, 8, 45), score_low(tpe, 8, 55), score_low(ps, 1, 16), score_low(pb, 1, 12), score_low(ev_ebitda, 6, 35), score_high(upside, -15, 35)]
    score = float(np.nanmean(scores))
    supports, conflicts = [], []
    if pd.notna(upside): (supports if upside > 10 else conflicts).append(f"analyst upside {upside:.1f}%")
    if pd.notna(fpe): (supports if fpe < 25 else conflicts).append(f"forward P/E {fpe:.1f}")
    if pd.notna(ps): (supports if ps < 8 else conflicts).append(f"P/S {ps:.1f}")
    if pd.notna(pb): (supports if pb < 5 else conflicts).append(f"P/B {pb:.1f}")
    return score, _label(score, "attractive", "expensive", "fair/mixed"), supports, conflicts


def _forward_score(row: pd.Series, fund_like: bool) -> tuple[float, str, list[str], list[str]]:
    if fund_like:
        return 5.5, "fund/ETF - estimates not applicable", [], []
    rev = pct_points(_coalesce(row, ["forward_revenue_growth", "revenue_growth"]))
    eps = pct_points(_coalesce(row, ["forward_eps_growth", "earnings_growth"]))
    rating = safe_float(_coalesce(row, ["rating_score"]), np.nan)
    upside = pct_points(_coalesce(row, ["analyst_upside_pct"] ))
    scores = [score_high(rev, -5, 20), score_high(eps, -10, 30), score_high(rating, 1, 5), score_high(upside, -15, 35)]
    score = float(np.nanmean(scores))
    supports, conflicts = [], []
    if pd.notna(rev): (supports if rev > 6 else conflicts).append(f"forward revenue growth {rev:.1f}%")
    if pd.notna(eps): (supports if eps > 8 else conflicts).append(f"forward EPS growth {eps:.1f}%")
    if pd.notna(upside): (supports if upside > 10 else conflicts).append(f"target upside {upside:.1f}%")
    return score, _label(score, "strong", "weak", "mixed"), supports, conflicts


def _risk_score(row: pd.Series, current_weight: float, max_weight: float) -> tuple[float, str, list[str], list[str]]:
    vol = pct_points(_coalesce(row, ["ann_vol_3m", "realized_vol_20d"]))
    dd = pct_points(_coalesce(row, ["max_drawdown_1y", "drawdown_from_52w_high"]))
    beta = safe_float(_coalesce(row, ["beta"]), np.nan)
    scores = [score_low(vol, 12, 65), score_abs_low(dd, 5, 45), score_low(beta, 0.6, 2.2)]
    concentration_penalty = 0.0
    if current_weight > max_weight:
        concentration_penalty = min(2.5, (current_weight - max_weight) / max_weight * 4.0)
    score = max(0.0, float(np.nanmean(scores)) - concentration_penalty)
    supports, conflicts = [], []
    if current_weight > max_weight:
        conflicts.append(f"above max position weight ({current_weight:.1%} vs {max_weight:.1%})")
    if pd.notna(vol): (supports if vol < 30 else conflicts).append(f"annualized volatility {vol:.1f}%")
    if pd.notna(dd): (supports if abs(dd) < 20 else conflicts).append(f"drawdown/risk marker {dd:.1f}%")
    if pd.notna(beta): (supports if beta < 1.2 else conflicts).append(f"beta {beta:.2f}")
    return score, _label(score, "controlled", "elevated", "moderate"), supports, conflicts


def _action_from_scores(composite: float, risk_score: float, current_weight: float, max_weight: float) -> str:
    if current_weight > max_weight * 1.10 and risk_score < 5.5:
        return "Trim"
    if composite >= 7.6 and risk_score >= 4.5:
        return "Strong Buy"
    if composite >= 6.7:
        return "Add"
    if composite >= 5.2:
        return "Hold"
    if composite >= 4.2:
        return "Watchlist"
    if current_weight > 0:
        return "Trim"
    return "Avoid"


def build_evidence_table(dataset: pd.DataFrame, max_weight: float = 0.18, max_sector_weight: float = 0.35) -> pd.DataFrame:
    """Build clean, no-peer evidence packets used by the AI committee.

    This is intentionally deterministic, but it does not make the final portfolio decision.
    Scores summarize evidence only; the committee decides actions and target weights.
    """
    if dataset is None or dataset.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, row in dataset.iterrows():
        ticker = clean_text(row.get("ticker"), "").upper()
        if not ticker:
            continue
        fund_like = is_fund_like(row)
        current_weight = safe_float(row.get("current_weight"), 0.0) or 0.0
        sector = clean_text(_coalesce(row, ["sector"]), SECTOR_DEFAULT)
        industry = clean_text(_coalesce(row, ["industry"]), "")
        company_name = clean_text(_coalesce(row, ["company_name", "companyName", "shortName", "longName"]), ticker)

        fundamental_score, fundamental_view, f_support, f_conflict = _fundamental_score(row, fund_like)
        valuation_score, valuation_view, v_support, v_conflict = _valuation_score(row, fund_like)
        forward_score, forward_view, fw_support, fw_conflict = _forward_score(row, fund_like)
        technical_score, technical_view, t_support, t_conflict = _technical_signal(row)
        risk_score, risk_view, r_support, r_conflict = _risk_score(row, current_weight, max_weight)

        if fund_like:
            composite = 0.50 * technical_score + 0.25 * risk_score + 0.15 * score_high(current_weight, 0, max_weight) + 0.10 * 5.5
        else:
            composite = (
                0.22 * fundamental_score + 0.18 * valuation_score + 0.20 * forward_score +
                0.25 * technical_score + 0.15 * risk_score
            )
        composite = float(np.clip(composite, 0.0, 10.0))
        evidence_action = _action_from_scores(composite, risk_score, current_weight, max_weight)
        conviction = "High" if composite >= 7.2 and risk_score >= 5.0 else "Medium" if composite >= 5.2 else "Low"
        supports = (f_support + v_support + fw_support + t_support + r_support)[:6]
        conflicts = (f_conflict + v_conflict + fw_conflict + t_conflict + r_conflict)[:6]
        if not supports:
            supports = ["Evidence is limited; committee should size conservatively."]
        if not conflicts:
            conflicts = ["No major conflict detected from available fields."]

        reason = (
            f"{ticker}: {fundamental_view}; valuation {valuation_view}; forward outlook {forward_view}; "
            f"technical trend {technical_view}; risk {risk_view}."
        )
        rows.append({
            "ticker": ticker,
            "company_name": company_name,
            "asset_type": "ETF / Fund" if fund_like else "Equity",
            "sector": sector,
            "industry": industry,
            "shares": safe_float(row.get("shares"), 0.0) or 0.0,
            "last_price": safe_float(_coalesce(row, ["last_price", "price"]), np.nan),
            "market_value": safe_float(row.get("market_value"), 0.0) or 0.0,
            "current_weight": current_weight,
            "evidence_action": evidence_action,
            "evidence_conviction": conviction,
            "composite_score": round(composite, 2),
            "fundamental_score": round(fundamental_score, 2),
            "valuation_score": round(valuation_score, 2),
            "forward_score": round(forward_score, 2),
            "technical_score": round(technical_score, 2),
            "risk_score": round(risk_score, 2),
            "fundamental_view": fundamental_view,
            "valuation_view": valuation_view,
            "forward_view": forward_view,
            "technical_view": technical_view,
            "risk_view": risk_view,
            "analyst_upside_pct": pct_points(_coalesce(row, ["analyst_upside_pct", "Price Target Upside"])),
            "forward_revenue_growth": pct_points(_coalesce(row, ["forward_revenue_growth", "revenue_growth"])),
            "forward_eps_growth": pct_points(_coalesce(row, ["forward_eps_growth", "earnings_growth"])),
            "forward_pe": safe_float(_coalesce(row, ["forward_pe"]), np.nan),
            "forward_ps": safe_float(_coalesce(row, ["forward_ps"]), np.nan),
            "price_to_sales": safe_float(_coalesce(row, ["price_to_sales"]), np.nan),
            "price_to_book": safe_float(_coalesce(row, ["price_to_book"]), np.nan),
            "debt_to_equity": safe_float(_coalesce(row, ["debt_to_equity"]), np.nan),
            "rsi_14": safe_float(_coalesce(row, ["rsi_14"]), np.nan),
            "price_vs_50dma": pct_points(_coalesce(row, ["price_vs_50dma"])),
            "price_vs_200dma": pct_points(_coalesce(row, ["price_vs_200dma"])),
            "ret_1m": pct_points(_coalesce(row, ["ret_1m"])),
            "ret_3m": pct_points(_coalesce(row, ["ret_3m"])),
            "ret_6m": pct_points(_coalesce(row, ["ret_6m"])),
            "ret_12m": pct_points(_coalesce(row, ["ret_12m", "ret_1y"])),
            "relative_strength_3m": pct_points(_coalesce(row, ["relative_strength_3m", "rel_3m_vs_benchmark"])),
            "ann_vol_3m": pct_points(_coalesce(row, ["ann_vol_3m", "realized_vol_20d"])),
            "max_drawdown_1y": pct_points(_coalesce(row, ["max_drawdown_1y", "drawdown_from_52w_high"])),
            "data_quality_score": safe_float(row.get("data_quality_score"), np.nan),
            "key_supports": " | ".join(supports),
            "key_conflicts": " | ".join(conflicts),
            "evidence_reason": reason,
            "max_position_weight": max_weight,
            "max_sector_weight": max_sector_weight,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["composite_score", "technical_score"], ascending=[False, False]).reset_index(drop=True)


def compact_evidence_records(evidence_table: pd.DataFrame, max_rows: int = 30) -> list[dict[str, Any]]:
    cols = [
        "ticker", "company_name", "asset_type", "sector", "industry", "current_weight", "market_value",
        "evidence_action", "evidence_conviction", "composite_score", "fundamental_score", "valuation_score",
        "forward_score", "technical_score", "risk_score", "fundamental_view", "valuation_view", "forward_view",
        "technical_view", "risk_view", "analyst_upside_pct", "forward_revenue_growth", "forward_eps_growth",
        "forward_pe", "price_to_sales", "price_to_book", "debt_to_equity", "rsi_14", "price_vs_50dma",
        "price_vs_200dma", "ret_1m", "ret_3m", "ret_6m", "ret_12m", "relative_strength_3m",
        "ann_vol_3m", "max_drawdown_1y", "key_supports", "key_conflicts", "evidence_reason",
    ]
    if evidence_table is None or evidence_table.empty:
        return []
    use_cols = [c for c in cols if c in evidence_table.columns]
    records = evidence_table[use_cols].head(max_rows).to_dict(orient="records")
    cleaned = []
    for record in records:
        item = {}
        for k, v in record.items():
            if isinstance(v, (np.integer, np.floating)):
                v = v.item()
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                v = None
            item[k] = v
        cleaned.append(item)
    return cleaned
