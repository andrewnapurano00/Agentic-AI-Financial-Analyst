from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _session() -> requests.Session:
    s = requests.Session()
    s.mount(
        'https://',
        HTTPAdapter(
            max_retries=Retry(
                total=5,
                backoff_factor=0.7,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=['GET'],
                raise_on_status=False,
            )
        ),
    )
    return s


SESSION = _session()


def _get_json(url: str, params: dict[str, Any], timeout: int = 25) -> Any:
    r = SESSION.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _safe_float(x: Any, default: float | None = None) -> float | None:
    try:
        if x is None or x == '':
            return default
        return float(x)
    except Exception:
        return default


def _cagr(start_value: float | None, end_value: float | None, years: float) -> float | None:
    if start_value is None or end_value is None or years <= 0:
        return None
    try:
        if float(start_value) <= 0 or float(end_value) <= 0:
            return None
        return (float(end_value) / float(start_value)) ** (1 / years) - 1
    except Exception:
        return None


def _standardize(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if 'date' in out.columns:
        out['date'] = pd.to_datetime(out['date'], errors='coerce')
    if 'ticker' not in out.columns:
        if 'symbol' in out.columns:
            out = out.rename(columns={'symbol': 'ticker'})
        else:
            out['ticker'] = ticker
    return out.sort_values('date').reset_index(drop=True)


def _add_ttm(df: pd.DataFrame, cols: list[str], group_col: str = 'ticker') -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[f'{c}_ttm'] = (
                out.groupby(group_col)[c]
                .rolling(4, min_periods=4)
                .sum()
                .reset_index(level=0, drop=True)
            )
    return out


def _fetch_statement(symbol: str, statement_type: str, api_key: str, period: str = 'quarter', limit: int = 12) -> pd.DataFrame:
    base = {
        'income': 'https://financialmodelingprep.com/api/v3/income-statement',
        'balance': 'https://financialmodelingprep.com/api/v3/balance-sheet-statement',
        'cashflow': 'https://financialmodelingprep.com/api/v3/cash-flow-statement',
    }
    try:
        data = _get_json(f"{base[statement_type]}/{symbol}", {'period': period, 'limit': limit, 'apikey': api_key})
    except Exception:
        return pd.DataFrame()
    if not isinstance(data, list) or not data:
        return pd.DataFrame()
    return _standardize(pd.DataFrame(data), symbol.upper())


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fmp_fundamental_snapshot(symbol: str, api_key: str) -> dict[str, Any]:
    symbol = str(symbol or '').upper().strip()
    if not symbol or not api_key:
        return {'ticker': symbol}

    income = _fetch_statement(symbol, 'income', api_key, limit=12)
    balance = _fetch_statement(symbol, 'balance', api_key, limit=12)
    cashflow = _fetch_statement(symbol, 'cashflow', api_key, limit=12)

    def _num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        out = df.copy()
        for c in cols:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors='coerce')
        return out

    income = _num(income, ['revenue', 'grossProfit', 'operatingIncome', 'netIncome', 'ebitda', 'weightedAverageShsOutDil'])
    balance = _num(balance, ['totalCurrentAssets', 'totalCurrentLiabilities', 'totalLiabilities', 'totalStockholdersEquity', 'totalAssets', 'totalDebt'])
    cashflow = _num(cashflow, ['operatingCashFlow', 'freeCashFlow'])

    income = _add_ttm(income, ['revenue', 'grossProfit', 'operatingIncome', 'netIncome', 'ebitda'])
    cashflow = _add_ttm(cashflow, ['operatingCashFlow', 'freeCashFlow'])

    latest_i = income.iloc[-1] if not income.empty else pd.Series(dtype=object)
    latest_b = balance.iloc[-1] if not balance.empty else pd.Series(dtype=object)
    latest_c = cashflow.iloc[-1] if not cashflow.empty else pd.Series(dtype=object)

    def _first_last_valid(df: pd.DataFrame, col: str):
        if df.empty or col not in df.columns:
            return None, None
        temp = df.dropna(subset=[col]).sort_values('date')
        if temp.empty:
            return None, None
        return temp.iloc[0], temp.iloc[-1]

    rev_first, rev_last = _first_last_valid(income.dropna(subset=['revenue_ttm']) if 'revenue_ttm' in income.columns else income, 'revenue_ttm' if 'revenue_ttm' in income.columns else 'revenue')
    ni_first, ni_last = _first_last_valid(income.dropna(subset=['netIncome_ttm']) if 'netIncome_ttm' in income.columns else income, 'netIncome_ttm' if 'netIncome_ttm' in income.columns else 'netIncome')
    fcf_first, fcf_last = _first_last_valid(cashflow.dropna(subset=['freeCashFlow_ttm']) if 'freeCashFlow_ttm' in cashflow.columns else cashflow, 'freeCashFlow_ttm' if 'freeCashFlow_ttm' in cashflow.columns else 'freeCashFlow')

    years_span = 3.0
    revenue_cagr_3y = _cagr(_safe_float(rev_first.get('revenue_ttm') if rev_first is not None and 'revenue_ttm' in rev_first else rev_first.get('revenue') if rev_first is not None else None),
                           _safe_float(rev_last.get('revenue_ttm') if rev_last is not None and 'revenue_ttm' in rev_last else rev_last.get('revenue') if rev_last is not None else None), years_span)
    net_income_cagr_3y = _cagr(_safe_float(ni_first.get('netIncome_ttm') if ni_first is not None and 'netIncome_ttm' in ni_first else ni_first.get('netIncome') if ni_first is not None else None),
                              _safe_float(ni_last.get('netIncome_ttm') if ni_last is not None and 'netIncome_ttm' in ni_last else ni_last.get('netIncome') if ni_last is not None else None), years_span)
    fcf_cagr_3y = _cagr(_safe_float(fcf_first.get('freeCashFlow_ttm') if fcf_first is not None and 'freeCashFlow_ttm' in fcf_first else fcf_first.get('freeCashFlow') if fcf_first is not None else None),
                       _safe_float(fcf_last.get('freeCashFlow_ttm') if fcf_last is not None and 'freeCashFlow_ttm' in fcf_last else fcf_last.get('freeCashFlow') if fcf_last is not None else None), years_span)

    revenue_ttm = _safe_float(latest_i.get('revenue_ttm') if 'revenue_ttm' in latest_i else latest_i.get('revenue'))
    gross_profit_ttm = _safe_float(latest_i.get('grossProfit_ttm') if 'grossProfit_ttm' in latest_i else latest_i.get('grossProfit'))
    operating_income_ttm = _safe_float(latest_i.get('operatingIncome_ttm') if 'operatingIncome_ttm' in latest_i else latest_i.get('operatingIncome'))
    net_income_ttm = _safe_float(latest_i.get('netIncome_ttm') if 'netIncome_ttm' in latest_i else latest_i.get('netIncome'))
    ebitda_ttm = _safe_float(latest_i.get('ebitda_ttm') if 'ebitda_ttm' in latest_i else latest_i.get('ebitda'))
    fcf_ttm = _safe_float(latest_c.get('freeCashFlow_ttm') if 'freeCashFlow_ttm' in latest_c else latest_c.get('freeCashFlow'))
    ocf_ttm = _safe_float(latest_c.get('operatingCashFlow_ttm') if 'operatingCashFlow_ttm' in latest_c else latest_c.get('operatingCashFlow'))

    revenue_yoy = None
    eps_yoy = None
    if len(income) >= 5:
        recent = income.dropna(subset=['revenue', 'netIncome'])
        if len(recent) >= 5:
            revenue_yoy = _safe_float(recent.iloc[-1].get('revenue'))
            revenue_prev = _safe_float(recent.iloc[-5].get('revenue'))
            if revenue_yoy and revenue_prev:
                revenue_yoy = revenue_yoy / revenue_prev - 1
            shares_now = _safe_float(recent.iloc[-1].get('weightedAverageShsOutDil'))
            shares_prev = _safe_float(recent.iloc[-5].get('weightedAverageShsOutDil'))
            eps_now = (_safe_float(recent.iloc[-1].get('netIncome')) / shares_now) if shares_now else None
            eps_prev = (_safe_float(recent.iloc[-5].get('netIncome')) / shares_prev) if shares_prev else None
            if eps_now is not None and eps_prev not in (None, 0):
                eps_yoy = eps_now / eps_prev - 1

    profile = {}
    quote = {}
    ratios = {}
    key_metrics = {}
    estimates = pd.DataFrame()
    try:
        p = _get_json(f'https://financialmodelingprep.com/api/v3/profile/{symbol}', {'apikey': api_key})
        if isinstance(p, list) and p:
            profile = p[0]
    except Exception:
        pass
    try:
        q = _get_json(f'https://financialmodelingprep.com/api/v3/quote/{symbol}', {'apikey': api_key})
        if isinstance(q, list) and q:
            quote = q[0]
    except Exception:
        pass
    try:
        r = _get_json('https://financialmodelingprep.com/stable/ratios-ttm', {'symbol': symbol, 'apikey': api_key})
        if isinstance(r, list) and r:
            ratios = r[0]
        elif isinstance(r, dict):
            ratios = r
    except Exception:
        pass
    try:
        km = _get_json('https://financialmodelingprep.com/stable/key-metrics-ttm', {'symbol': symbol, 'apikey': api_key})
        if isinstance(km, list) and km:
            key_metrics = km[0]
        elif isinstance(km, dict):
            key_metrics = km
    except Exception:
        pass
    try:
        est = _get_json(f'https://financialmodelingprep.com/api/v3/analyst-estimates/{symbol}', {'limit': 8, 'period': 'annual', 'apikey': api_key})
        if isinstance(est, list) and est:
            estimates = pd.DataFrame(est)
    except Exception:
        pass

    forward_revenue_growth = None
    forward_eps_growth = None
    if not estimates.empty:
        estimates['date'] = pd.to_datetime(estimates.get('date'), errors='coerce')
        estimates = estimates.sort_values('date').reset_index(drop=True)
        if 'estimatedRevenueAvg' in estimates.columns and len(estimates) >= 2:
            a = _safe_float(estimates.iloc[0].get('estimatedRevenueAvg'))
            b = _safe_float(estimates.iloc[1].get('estimatedRevenueAvg'))
            if a and b:
                forward_revenue_growth = b / a - 1
        if 'estimatedEpsAvg' in estimates.columns and len(estimates) >= 2:
            a = _safe_float(estimates.iloc[0].get('estimatedEpsAvg'))
            b = _safe_float(estimates.iloc[1].get('estimatedEpsAvg'))
            if a not in (None, 0) and b is not None:
                forward_eps_growth = b / a - 1

    current_price = _safe_float(quote.get('price') or profile.get('price'))
    price_target = _safe_float(quote.get('priceTarget'))
    analyst_upside_pct = (price_target / current_price - 1) if current_price not in (None, 0) and price_target is not None else None

    current_ratio = _safe_float(ratios.get('currentRatioTTM') or ratios.get('currentRatio'))
    debt_to_equity = _safe_float(ratios.get('debtEquityRatioTTM') or ratios.get('debtToEquity') or ratios.get('debtEquityRatio'))
    roe = _safe_float(ratios.get('returnOnEquityTTM') or ratios.get('returnOnEquity'))
    roa = _safe_float(ratios.get('returnOnAssetsTTM') or ratios.get('returnOnAssets'))
    price_to_book = _safe_float(key_metrics.get('pbRatioTTM') or key_metrics.get('pbRatio'))
    forward_pe = _safe_float(quote.get('pe') or key_metrics.get('peRatioTTM'))
    price_to_sales = _safe_float(key_metrics.get('priceToSalesRatioTTM') or key_metrics.get('priceToSalesRatio'))
    ev_to_ebitda = _safe_float(key_metrics.get('enterpriseValueOverEBITDATTM') or key_metrics.get('enterpriseValueOverEBITDA'))

    total_liabilities = _safe_float(latest_b.get('totalLiabilities'))
    total_assets = _safe_float(latest_b.get('totalAssets'))
    liabilities_to_assets = (total_liabilities / total_assets) if total_assets not in (None, 0) and total_liabilities is not None else None

    return {
        'ticker': symbol,
        'company_name': profile.get('companyName') or quote.get('name') or symbol,
        'sector': profile.get('sector') or 'Unknown',
        'industry': profile.get('industry') or 'Unknown',
        'market_cap': _safe_float(profile.get('mktCap') or quote.get('marketCap')),
        'beta': _safe_float(profile.get('beta') or quote.get('beta')),
        'last_price': current_price,
        'revenue_cagr_3y': revenue_cagr_3y,
        'net_income_cagr_3y': net_income_cagr_3y,
        'fcf_cagr_3y': fcf_cagr_3y,
        'revenue_growth': revenue_yoy,
        'earnings_growth': eps_yoy,
        'revenue_ttm': revenue_ttm,
        'gross_margin': (gross_profit_ttm / revenue_ttm) if revenue_ttm not in (None, 0) and gross_profit_ttm is not None else None,
        'operating_margin': (operating_income_ttm / revenue_ttm) if revenue_ttm not in (None, 0) and operating_income_ttm is not None else None,
        'profit_margin': (net_income_ttm / revenue_ttm) if revenue_ttm not in (None, 0) and net_income_ttm is not None else None,
        'free_cashflow_margin': (fcf_ttm / revenue_ttm) if revenue_ttm not in (None, 0) and fcf_ttm is not None else None,
        'operating_cashflow_margin': (ocf_ttm / revenue_ttm) if revenue_ttm not in (None, 0) and ocf_ttm is not None else None,
        'return_on_equity': roe,
        'return_on_assets': roa,
        'current_ratio': current_ratio,
        'debt_to_equity': debt_to_equity,
        'liabilities_to_assets': liabilities_to_assets,
        'forward_revenue_growth': forward_revenue_growth,
        'forward_eps_growth': forward_eps_growth,
        'forward_pe': forward_pe,
        'price_to_sales': price_to_sales,
        'price_to_book': price_to_book,
        'enterprise_to_ebitda': ev_to_ebitda,
        'analyst_upside_pct': analyst_upside_pct,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fmp_fundamental_snapshots(tickers: list[str], api_key: str) -> pd.DataFrame:
    rows = [fetch_fmp_fundamental_snapshot(t, api_key) for t in sorted({str(x).upper().strip() for x in tickers if str(x).strip()})]
    df = pd.DataFrame(rows)
    return df if not df.empty else pd.DataFrame(columns=['ticker'])
