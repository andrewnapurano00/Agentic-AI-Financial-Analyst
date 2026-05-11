from __future__ import annotations

import pandas as pd

from langgraphagenticai.portfolio_manager.schemas import ValuationResult
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
    return "default"


def run_valuation_agent(ticker: str, data: dict) -> ValuationResult:
    sector = _get(data, 'sector')
    fwd_pe = _get(data, 'forward_pe', 'Forward P/E')
    trailing_pe = _get(data, 'trailing_pe', 'P/E TTM')
    ps = _get(data, 'price_to_sales', 'P/S TTM')
    pb = _get(data, 'price_to_book', 'P/B TTM')
    pfcf = _get(data, 'price_to_fcf', 'P/FCF TTM')
    upside = _get(data, 'analyst_upside_pct', 'Price Target Upside')
    fwd_ps = _get(data, 'forward_ps', 'Forward P/S')
    earnings_yield = _get(data, 'Earnings Yield', 'earnings_yield')
    fcf_yield = _get(data, 'FCF Yield', 'fcf_yield')
    peer_score = _get(data, 'peer_valuation_score')
    peer_reliability = _get(data, 'peer_reliability')
    peer_rank = _get(data, 'peer_rank_overall')
    peer_group = _get(data, 'peer_group_name')

    family = _sector_family(sector)
    if family == 'financials':
        parts = {
            'price_to_book': pct_to_score(pb, 0.7, 3.0, invert=True),
            'forward_pe': pct_to_score(fwd_pe, 7, 22, invert=True),
            'trailing_pe': pct_to_score(trailing_pe, 7, 24, invert=True),
            'analyst_upside': pct_to_score(upside, -0.08, 0.22),
            'earnings_yield': pct_to_score(earnings_yield, 0.035, 0.13),
        }
    elif family == 'real_estate':
        parts = {
            'price_to_book': pct_to_score(pb, 0.8, 3.5, invert=True),
            'price_to_sales': pct_to_score(ps, 2.0, 12.0, invert=True),
            'price_to_fcf': pct_to_score(pfcf, 10.0, 35.0, invert=True),
            'fcf_yield': pct_to_score(fcf_yield, 0.025, 0.10),
            'analyst_upside': pct_to_score(upside, -0.08, 0.22),
        }
    elif family == 'energy':
        parts = {
            'forward_pe': pct_to_score(fwd_pe, 6, 24, invert=True),
            'price_to_sales': pct_to_score(ps, 0.5, 5.0, invert=True),
            'price_to_fcf': pct_to_score(pfcf, 6.0, 28.0, invert=True),
            'fcf_yield': pct_to_score(fcf_yield, 0.035, 0.14),
            'analyst_upside': pct_to_score(upside, -0.10, 0.25),
        }
    elif family == 'growth':
        parts = {
            'forward_pe': pct_to_score(fwd_pe, 15, 45, invert=True),
            'forward_ps': pct_to_score(fwd_ps, 2.0, 15.0, invert=True),
            'price_to_sales': pct_to_score(ps, 2.0, 15.0, invert=True),
            'price_to_fcf': pct_to_score(pfcf, 15.0, 55.0, invert=True),
            'fcf_yield': pct_to_score(fcf_yield, 0.015, 0.08),
            'analyst_upside': pct_to_score(upside, -0.10, 0.28),
        }
    else:
        parts = {
            'forward_pe': pct_to_score(fwd_pe, 8, 35, invert=True),
            'forward_ps': pct_to_score(fwd_ps, 1.0, 12.0, invert=True),
            'trailing_pe': pct_to_score(trailing_pe, 8, 35, invert=True),
            'price_to_sales': pct_to_score(ps, 1.0, 12.0, invert=True),
            'price_to_book': pct_to_score(pb, 1.0, 10.0, invert=True),
            'price_to_fcf': pct_to_score(pfcf, 8.0, 40.0, invert=True),
            'analyst_upside': pct_to_score(upside, -0.10, 0.25),
            'earnings_yield': pct_to_score(earnings_yield, 0.02, 0.10),
            'fcf_yield': pct_to_score(fcf_yield, 0.02, 0.10),
        }

    absolute_score = clip_score(sum(parts.values()) / len(parts))
    score, peer_note = blend_with_peer_score(absolute_score=absolute_score, peer_score=peer_score, peer_reliability=peer_reliability, max_peer_weight=0.22)

    summary, risks, data_gaps = [], [], []
    if upside is not None and upside > 0.10:
        summary.append('Analyst target upside still suggests room for appreciation.')
    elif upside is not None and upside < 0:
        risks.append('Analyst targets imply limited or negative upside from current levels.')
    else:
        data_gaps.append('Analyst upside is incomplete or neutral.')

    expensive_pe = 35 if family == 'growth' else 30
    reasonable_pe = 25 if family == 'growth' else 18
    if fwd_pe is not None and fwd_pe > expensive_pe:
        risks.append('Forward earnings multiple screens as expensive for the sector profile.')
    elif fwd_pe is not None and fwd_pe < reasonable_pe:
        summary.append('Forward valuation is not demanding versus the sector profile.')
    if fwd_ps is not None and fwd_ps > (10 if family == 'growth' else 8):
        risks.append('Forward sales multiple is elevated.')
    if pfcf is not None and pfcf < (25 if family == 'growth' else 20):
        summary.append('Free cash flow valuation remains reasonable.')
    if fcf_yield is not None and fcf_yield > 0.05:
        summary.append('Free-cash-flow yield provides valuation support.')

    if peer_score is not None and peer_reliability is not None and float(peer_reliability or 0) >= 0.45:
        if float(peer_score) >= 7.2:
            summary.append('Valuation ranks attractively versus the selected peer group.')
        elif float(peer_score) <= 3.8:
            risks.append('Valuation ranks expensive versus the selected peer group.')
        if peer_note:
            (summary if float(peer_score or 0) >= absolute_score else risks).append(peer_note)

    if not summary:
        summary.append('Valuation appears balanced without an obvious deep-value signal.')

    valuation_status = 'cheap' if score >= 7.0 else 'fair' if score >= 5.0 else 'expensive'
    return ValuationResult(
        thesis=("bullish" if score >= 6.7 else "bearish" if score <= 4.4 else "neutral"),
        conviction=("high" if upside is not None and abs(float(upside)) >= 0.15 else "medium"),
        evidence_for=summary[:4],
        evidence_against=risks[:4],
        action_preference=("Buy" if score >= 6.8 else "Hold" if score >= 4.8 else "Trim"),
        challenge_points=["Check whether peer multiples justify the apparent discount or premium."],
        data_gaps=data_gaps[:3],
        ticker=ticker,
        score=score,
        verdict=valuation_status,
        valuation_status=valuation_status,
        summary=summary[:4],
        risks=risks[:4],
        metrics={
            'Sector Family': family,
            'P/E TTM': trailing_pe,
            'P/B TTM': pb,
            'P/S TTM': ps,
            'P/FCF TTM': pfcf,
            'Forward P/E': fwd_pe,
            'Forward P/S': fwd_ps,
            'Earnings Yield': earnings_yield,
            'FCF Yield': fcf_yield,
            'Price Target Upside': upside,
            'Peer Valuation Score': peer_score,
            'Peer Reliability': peer_reliability,
            'Peer Rank Overall': peer_rank,
            'Peer Group': peer_group,
        },
    )
