from __future__ import annotations

import pandas as pd

from langgraphagenticai.portfolio_manager.schemas import FundamentalResult
from langgraphagenticai.portfolio_manager.scoring import blend_with_peer_score, clip_score, pct_to_score


def _get(data: dict, *keys):
    for key in keys:
        value = data.get(key)
        if value is not None and not (isinstance(value, float) and pd.isna(value)):
            return value
    return None


def _sector_family(sector: str | None) -> str:
    s = str(sector or "").strip().lower()
    if "financial" in s:
        return "financials"
    if "real estate" in s:
        return "real_estate"
    if "energy" in s:
        return "energy"
    if "technology" in s or "communication" in s:
        return "growth"
    if "utility" in s or "consumer defensive" in s or "staples" in s:
        return "defensive"
    if "health" in s:
        return "healthcare"
    return "default"


def _sector_pillar_weights(sector: str | None) -> dict[str, float]:
    family = _sector_family(sector)
    if family == "financials":
        return {"growth": 0.16, "profitability": 0.22, "cash_flow_quality": 0.08, "returns_balance_sheet": 0.34, "forward_outlook": 0.20}
    if family == "real_estate":
        return {"growth": 0.18, "profitability": 0.18, "cash_flow_quality": 0.22, "returns_balance_sheet": 0.24, "forward_outlook": 0.18}
    if family == "energy":
        return {"growth": 0.17, "profitability": 0.23, "cash_flow_quality": 0.25, "returns_balance_sheet": 0.20, "forward_outlook": 0.15}
    if family == "growth":
        return {"growth": 0.30, "profitability": 0.24, "cash_flow_quality": 0.18, "returns_balance_sheet": 0.12, "forward_outlook": 0.16}
    if family == "defensive":
        return {"growth": 0.16, "profitability": 0.24, "cash_flow_quality": 0.20, "returns_balance_sheet": 0.24, "forward_outlook": 0.16}
    return {"growth": 0.24, "profitability": 0.24, "cash_flow_quality": 0.18, "returns_balance_sheet": 0.20, "forward_outlook": 0.14}


def _weighted_pillars(pillars: dict[str, float], weights: dict[str, float]) -> float:
    total = 0.0
    weight_sum = 0.0
    for key, weight in weights.items():
        total += clip_score(pillars.get(key, 5.0)) * weight
        weight_sum += weight
    return clip_score(total / weight_sum) if weight_sum else 5.0


def run_fundamental_agent(ticker: str, data: dict) -> FundamentalResult:
    sector = _get(data, 'sector')
    revenue_cagr = _get(data, 'revenue_cagr_3y', 'Revenue CAGR 3Y')
    eps_growth = _get(data, 'earnings_growth', 'Forward EPS Growth FY+1', 'Forward Revenue Growth FY+1')
    fcf_cagr = _get(data, 'fcf_cagr_3y', 'FCF CAGR 3Y')
    op_margin = _get(data, 'operating_margin', 'Latest Operating Margin')
    net_margin = _get(data, 'profit_margin', 'Latest Net Margin')
    ocf_margin = _get(data, 'OCF Margin', 'ocf_margin')
    fcf_margin = _get(data, 'FCF Margin', 'fcf_margin')
    cash_conversion = _get(data, 'Cash Conversion', 'cash_conversion')
    roe = _get(data, 'return_on_equity', 'ROE')
    roa = _get(data, 'return_on_assets', 'ROA')
    debt_to_equity = _get(data, 'debt_to_equity', 'Debt to Equity')
    current_ratio = _get(data, 'current_ratio', 'Current Ratio')
    liabilities_to_assets = _get(data, 'liabilities_to_assets', 'Liabilities to Assets')
    fwd_rev = _get(data, 'forward_revenue_growth', 'Forward Revenue Growth FY+1')
    rating_score = _get(data, 'rating_score', 'Rating Score')
    peer_score = _get(data, 'peer_fundamental_score')
    peer_reliability = _get(data, 'peer_reliability')
    peer_percentile = _get(data, 'peer_percentile_overall')

    family = _sector_family(sector)
    growth_score = (pct_to_score(revenue_cagr, -0.10, 0.25) + pct_to_score(eps_growth, -0.15, 0.30) + pct_to_score(fcf_cagr, -0.15, 0.25)) / 3
    profitability_score = (pct_to_score(op_margin, 0.00, 0.35) + pct_to_score(net_margin, 0.00, 0.25) + pct_to_score(fcf_margin, 0.00, 0.25)) / 3
    cash_flow_score = (pct_to_score(ocf_margin, 0.00, 0.30) + pct_to_score(cash_conversion, 0.5, 2.0)) / 2

    balance_sheet_parts = [
        pct_to_score(roe, 0.00, 0.30),
        pct_to_score(roa, 0.00, 0.12),
        pct_to_score(current_ratio, 0.7, 2.5),
        pct_to_score(debt_to_equity, 0.0, 2.5, invert=True),
        pct_to_score(liabilities_to_assets, 0.25, 0.80, invert=True),
    ]
    if family == "financials":
        balance_sheet_parts = [pct_to_score(roe, 0.05, 0.22), pct_to_score(roa, 0.002, 0.025), pct_to_score(debt_to_equity, 0.0, 4.0, invert=True), pct_to_score(rating_score, 1.0, 5.0)]
    elif family == "real_estate":
        balance_sheet_parts = [pct_to_score(debt_to_equity, 0.0, 2.0, invert=True), pct_to_score(liabilities_to_assets, 0.25, 0.75, invert=True), pct_to_score(fcf_margin, 0.00, 0.22), pct_to_score(rating_score, 1.0, 5.0)]

    pillar_scores = {
        'growth': growth_score,
        'profitability': profitability_score,
        'cash_flow_quality': cash_flow_score,
        'returns_balance_sheet': sum(balance_sheet_parts) / len(balance_sheet_parts),
        'forward_outlook': (pct_to_score(fwd_rev, -0.05, 0.20) + pct_to_score(rating_score, 1.0, 5.0)) / 2,
    }

    absolute_score = _weighted_pillars(pillar_scores, _sector_pillar_weights(sector))
    score, peer_note = blend_with_peer_score(absolute_score=absolute_score, peer_score=peer_score, peer_reliability=peer_reliability, max_peer_weight=0.18)

    strengths, risks, data_gaps = [], [], []
    if revenue_cagr is not None and revenue_cagr > 0.08:
        strengths.append('Three-year revenue CAGR is attractive.')
    elif revenue_cagr is not None and revenue_cagr < 0:
        risks.append('Revenue CAGR is negative over the lookback period.')
    else:
        data_gaps.append('Historical revenue growth is incomplete.')
    if op_margin is not None and op_margin > 0.18:
        strengths.append('Operating margins indicate good business quality.')
    elif op_margin is not None and op_margin < 0.08:
        risks.append('Operating margins are thin versus a high-quality profile.')
    if fcf_margin is not None and fcf_margin > 0.10:
        strengths.append('Free-cash-flow margin supports quality of earnings.')
    elif fcf_margin is not None and fcf_margin < 0:
        risks.append('Free-cash-flow margin is negative.')
    if fwd_rev is not None and fwd_rev > 0.08:
        strengths.append('Forward revenue expectations remain supportive.')
    elif fwd_rev is not None and fwd_rev < 0:
        risks.append('Forward revenue expectations are weak.')
    if debt_to_equity is not None and debt_to_equity > (4.0 if family == 'financials' else 2.0):
        risks.append('Leverage is elevated and deserves monitoring.')
    if current_ratio is not None and current_ratio < 1.0 and family not in {'financials', 'real_estate'}:
        risks.append('Liquidity coverage is weaker than ideal.')

    if peer_score is not None and peer_reliability is not None and float(peer_reliability or 0) >= 0.45:
        if float(peer_score) >= 7.2:
            strengths.append('Fundamental metrics rank well versus the selected peer group.')
        elif float(peer_score) <= 3.8:
            risks.append('Fundamental metrics rank weakly versus the selected peer group.')
        if peer_note:
            (strengths if float(peer_score or 0) >= absolute_score else risks).append(peer_note)

    if peer_percentile is not None and not pd.isna(peer_percentile):
        try:
            p = float(peer_percentile)
            if p >= 0.75:
                strengths.append('Overall peer percentile is top-quartile.')
            elif p <= 0.25:
                risks.append('Overall peer percentile is bottom-quartile.')
        except Exception:
            pass

    if not strengths:
        strengths.append('Fundamental profile is broadly stable without a major outlier.')

    verdict = 'strong' if score >= 7.0 else 'mixed' if score >= 5.0 else 'weak'
    return FundamentalResult(
        thesis=("bullish" if score >= 6.7 else "bearish" if score <= 4.4 else "neutral"),
        conviction=("high" if score >= 7.5 or score <= 3.8 else "medium"),
        evidence_for=strengths[:4],
        evidence_against=risks[:4],
        action_preference=("Buy" if score >= 6.8 else "Hold" if score >= 4.8 else "Avoid"),
        challenge_points=["Validate whether future growth is already priced into expectations."],
        data_gaps=data_gaps[:3],
        ticker=ticker,
        score=score,
        verdict=verdict,
        summary=strengths[:4],
        risks=risks[:4],
        metrics={
            'Sector Family': family,
            'Revenue CAGR 3Y': revenue_cagr,
            'FCF CAGR 3Y': fcf_cagr,
            'Latest Operating Margin': op_margin,
            'Latest Net Margin': net_margin,
            'OCF Margin': ocf_margin,
            'FCF Margin': fcf_margin,
            'Cash Conversion': cash_conversion,
            'ROE': roe,
            'ROA': roa,
            'Debt to Equity': debt_to_equity,
            'Current Ratio': current_ratio,
            'Liabilities to Assets': liabilities_to_assets,
            'Forward Revenue Growth FY+1': fwd_rev,
            'Rating Score': rating_score,
            'Peer Fundamental Score': peer_score,
            'Peer Reliability': peer_reliability,
            'Peer Percentile Overall': peer_percentile,
        },
        pillar_scores={k: round(v, 2) for k, v in pillar_scores.items()},
    )
