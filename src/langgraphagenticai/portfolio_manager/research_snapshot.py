
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st

PRICE_FROM_DATE = "2019-01-01"
PRICE_TO_DATE = None


def _get_json(url: str, params: dict, timeout: int = 30):
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _safe_number(x):
    try:
        if x is None or x == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def _safe_series_get(row: pd.Series, keys: List[str], default=np.nan):
    for k in keys:
        if k in row.index and pd.notna(row[k]):
            return row[k]
    return default


def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def cagr(start_value: float, end_value: float, years: float) -> float:
    if pd.isna(start_value) or pd.isna(end_value) or start_value <= 0 or years <= 0:
        return np.nan
    return (end_value / start_value) ** (1 / years) - 1


def first_last_valid(g: pd.DataFrame, col: str):
    if col not in g.columns:
        return None, None
    temp = g.dropna(subset=[col]).sort_values("date")
    if temp.empty:
        return None, None
    return temp.iloc[0], temp.iloc[-1]


def latest_and_window(df: pd.DataFrame, years: int = 3) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return df.copy()
    max_date = df["date"].max()
    cutoff = max_date - pd.DateOffset(years=years)
    return df[df["date"] >= cutoff].copy()


def standardize_date_sort(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
    if "ticker" not in out.columns and "symbol" in out.columns:
        out = out.rename(columns={"symbol": "ticker"})
    if "ticker" in out.columns and "date" in out.columns:
        out = out.sort_values(["ticker", "date"]).reset_index(drop=True)
    return out


def to_numeric_if_exists(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def add_ttm(df: pd.DataFrame, cols: List[str], group_col: str = "ticker") -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[f"{c}_ttm"] = (
                out.groupby(group_col)[c]
                .rolling(4, min_periods=4)
                .sum()
                .reset_index(level=0, drop=True)
            )
    return out


def fetch_statement(symbol: str, statement_type: str, api_key: str, period: str = "quarter", limit: int = 40) -> pd.DataFrame:
    base_v3 = {
        "income": "https://financialmodelingprep.com/api/v3/income-statement",
        "balance": "https://financialmodelingprep.com/api/v3/balance-sheet-statement",
        "cashflow": "https://financialmodelingprep.com/api/v3/cash-flow-statement",
    }
    url = f"{base_v3[statement_type]}/{symbol}"
    params = {"period": period, "limit": limit, "apikey": api_key}
    data = _get_json(url, params)
    if not isinstance(data, list) or len(data) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["ticker"] = symbol.upper()
    df["statement_type"] = statement_type
    return df


def fetch_all_statements(symbols: List[str], api_key: str, limit: int = 40) -> Dict[str, pd.DataFrame]:
    out = {"income": [], "balance": [], "cashflow": []}
    for sym in symbols:
        for stype in ["income", "balance", "cashflow"]:
            try:
                df = fetch_statement(sym, stype, api_key=api_key, period="quarter", limit=limit)
                if not df.empty:
                    out[stype].append(df)
            except Exception:
                continue
    for k in out:
        out[k] = pd.concat(out[k], ignore_index=True) if out[k] else pd.DataFrame()
    return out


def prepare_financials(symbols: List[str], api_key: str, limit: int = 40) -> Dict[str, pd.DataFrame]:
    data = fetch_all_statements(symbols, api_key=api_key, limit=limit)
    income = standardize_date_sort(data["income"])
    balance = standardize_date_sort(data["balance"])
    cashflow = standardize_date_sort(data["cashflow"])
    income_cols = ["revenue", "grossProfit", "operatingIncome", "netIncome", "ebitda", "weightedAverageShsOutDil"]
    balance_cols = ["cashAndCashEquivalents", "cashAndShortTermInvestments", "totalCurrentAssets", "totalAssets", "totalCurrentLiabilities", "totalLiabilities", "netDebt", "totalDebt", "longTermDebt", "shortTermDebt", "totalStockholdersEquity"]
    cashflow_cols = ["operatingCashFlow", "freeCashFlow", "capitalExpenditure", "netCashProvidedByOperatingActivities"]
    income = to_numeric_if_exists(income, income_cols)
    balance = to_numeric_if_exists(balance, balance_cols)
    cashflow = to_numeric_if_exists(cashflow, cashflow_cols)
    income = add_ttm(income, ["revenue", "grossProfit", "operatingIncome", "netIncome", "ebitda"])
    cashflow = add_ttm(cashflow, ["operatingCashFlow", "freeCashFlow", "capitalExpenditure"])
    if "revenue_ttm" in income.columns:
        if "grossProfit_ttm" in income.columns:
            income["gross_margin_ttm"] = income["grossProfit_ttm"] / income["revenue_ttm"]
        if "operatingIncome_ttm" in income.columns:
            income["operating_margin_ttm"] = income["operatingIncome_ttm"] / income["revenue_ttm"]
        if "netIncome_ttm" in income.columns:
            income["net_margin_ttm"] = income["netIncome_ttm"] / income["revenue_ttm"]
        if "ebitda_ttm" in income.columns:
            income["ebitda_margin_ttm"] = income["ebitda_ttm"] / income["revenue_ttm"]
    return {"income": income, "balance": balance, "cashflow": cashflow}


def fetch_one_row_endpoint(url: str, symbol: str, api_key: str, extra_params: dict = None) -> pd.DataFrame:
    params = {"symbol": symbol, "apikey": api_key}
    if extra_params:
        params.update(extra_params)
    try:
        data = _get_json(url, params)
    except Exception:
        return pd.DataFrame()
    if isinstance(data, dict):
        df = pd.DataFrame([data])
    elif isinstance(data, list) and len(data) > 0:
        df = pd.DataFrame(data)
    else:
        return pd.DataFrame()
    if "symbol" in df.columns and "ticker" not in df.columns:
        df = df.rename(columns={"symbol": "ticker"})
    elif "ticker" not in df.columns:
        df["ticker"] = symbol.upper()
    return df


def fetch_analyst_estimates(symbol: str, api_key: str, limit: int = 12, period: str = "annual") -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{symbol}"
    params = {"period": period, "limit": limit, "apikey": api_key}
    try:
        data = _get_json(url, params)
    except Exception:
        return pd.DataFrame()
    if not isinstance(data, list) or len(data) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "symbol" in df.columns and "ticker" not in df.columns:
        df = df.rename(columns={"symbol": "ticker"})
    elif "ticker" not in df.columns:
        df["ticker"] = symbol.upper()
    return df


def fetch_quote(symbol: str, api_key: str) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
    params = {"apikey": api_key}
    try:
        data = _get_json(url, params)
    except Exception:
        return pd.DataFrame()
    if not isinstance(data, list) or len(data) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "symbol" in df.columns and "ticker" not in df.columns:
        df = df.rename(columns={"symbol": "ticker"})
    return df


def fetch_market_intelligence(symbols: List[str], api_key: str) -> Dict[str, pd.DataFrame]:
    base_other = {
        "ratios_ttm": "https://financialmodelingprep.com/stable/ratios-ttm",
        "key_metrics_ttm": "https://financialmodelingprep.com/stable/key-metrics-ttm",
        "price_target_consensus": "https://financialmodelingprep.com/api/v4/price-target-consensus",
        "ratings_snapshot": "https://financialmodelingprep.com/stable/ratings-snapshot",
    }
    ratios, key_metrics, ests, pt_consensus, ratings, quotes = [], [], [], [], [], []
    for sym in symbols:
        r = fetch_one_row_endpoint(base_other["ratios_ttm"], sym, api_key=api_key)
        if not r.empty:
            ratios.append(r)
        km = fetch_one_row_endpoint(base_other["key_metrics_ttm"], sym, api_key=api_key)
        if not km.empty:
            key_metrics.append(km)
        ae = fetch_analyst_estimates(sym, api_key=api_key, limit=12, period="annual")
        if not ae.empty:
            ests.append(ae)
        ptc = fetch_one_row_endpoint(base_other["price_target_consensus"], sym, api_key=api_key)
        if not ptc.empty:
            pt_consensus.append(ptc)
        rs = fetch_one_row_endpoint(base_other["ratings_snapshot"], sym, api_key=api_key)
        if not rs.empty:
            ratings.append(rs)
        q = fetch_quote(sym, api_key=api_key)
        if not q.empty:
            quotes.append(q)
    return {
        "ratios_ttm": pd.concat(ratios, ignore_index=True) if ratios else pd.DataFrame(),
        "key_metrics_ttm": pd.concat(key_metrics, ignore_index=True) if key_metrics else pd.DataFrame(),
        "analyst_estimates": pd.concat(ests, ignore_index=True) if ests else pd.DataFrame(),
        "price_target_consensus": pd.concat(pt_consensus, ignore_index=True) if pt_consensus else pd.DataFrame(),
        "ratings_snapshot": pd.concat(ratings, ignore_index=True) if ratings else pd.DataFrame(),
        "quote": pd.concat(quotes, ignore_index=True) if quotes else pd.DataFrame(),
    }


def summarize_analyst_estimates(est_df: pd.DataFrame) -> pd.DataFrame:
    if est_df.empty:
        return pd.DataFrame()
    tmp = est_df.copy()
    if "symbol" in tmp.columns and "ticker" not in tmp.columns:
        tmp = tmp.rename(columns={"symbol": "ticker"})
    if "date" in tmp.columns:
        tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
    else:
        tmp["date"] = pd.NaT
    revenue_col = pick_col(tmp, ["estimatedRevenueAvg", "revenueAvg", "estimatedRevenue"])
    ebitda_col = pick_col(tmp, ["estimatedEbitdaAvg", "ebitdaAvg", "estimatedEbitda"])
    net_income_col = pick_col(tmp, ["estimatedNetIncomeAvg", "netIncomeAvg"])
    eps_col = pick_col(tmp, ["estimatedEpsAvg", "epsAvg", "estimatedEps"])
    today = pd.Timestamp.today().normalize()
    out_rows = []
    for ticker, g in tmp.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True).copy()
        future_g = g[g["date"] >= today].copy()
        if future_g.empty:
            future_g = g.copy()
        next1 = future_g.iloc[0] if len(future_g) >= 1 else pd.Series(dtype=object)
        next2 = future_g.iloc[1] if len(future_g) >= 2 else pd.Series(dtype=object)
        rev1 = _safe_number(next1.get(revenue_col, np.nan)) if revenue_col else np.nan
        rev2 = _safe_number(next2.get(revenue_col, np.nan)) if revenue_col else np.nan
        ebitda1 = _safe_number(next1.get(ebitda_col, np.nan)) if ebitda_col else np.nan
        net_income1 = _safe_number(next1.get(net_income_col, np.nan)) if net_income_col else np.nan
        eps1 = _safe_number(next1.get(eps_col, np.nan)) if eps_col else np.nan
        rev_growth_fwd = np.nan
        if pd.notna(rev1) and pd.notna(rev2) and rev1 != 0:
            rev_growth_fwd = (rev2 / rev1) - 1
        out_rows.append({
            "ticker": ticker,
            "Estimate Period 1": next1.get("date", pd.NaT),
            "Estimate Period 2": next2.get("date", pd.NaT),
            "Forward Revenue Next FY": rev1,
            "Forward Revenue FY+1": rev2,
            "Forward Revenue Growth FY+1": rev_growth_fwd,
            "Forward EBITDA Next FY": ebitda1,
            "Forward Net Income Next FY": net_income1,
            "Forward EPS Next FY": eps1,
        })
    return pd.DataFrame(out_rows)


def build_analyst_scorecard(financials: Dict[str, pd.DataFrame], market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    income = latest_and_window(financials["income"], years=3)
    balance = latest_and_window(financials["balance"], years=3)
    cashflow = latest_and_window(financials["cashflow"], years=3)
    ratios = market_data["ratios_ttm"].copy()
    key_metrics = market_data["key_metrics_ttm"].copy()
    est_summary = summarize_analyst_estimates(market_data["analyst_estimates"])
    pt_consensus = market_data["price_target_consensus"].copy()
    ratings = market_data["ratings_snapshot"].copy()
    quotes = market_data["quote"].copy()
    for df in [ratios, key_metrics, est_summary, pt_consensus, ratings, quotes]:
        if not df.empty and "symbol" in df.columns and "ticker" not in df.columns:
            df.rename(columns={"symbol": "ticker"}, inplace=True)
    tickers = sorted(set(income.get("ticker", pd.Series(dtype=str)).dropna().unique()).union(balance.get("ticker", pd.Series(dtype=str)).dropna().unique()).union(cashflow.get("ticker", pd.Series(dtype=str)).dropna().unique()))
    rows = []
    for ticker in tickers:
        gi = income[income["ticker"] == ticker].sort_values("date").copy()
        gb = balance[balance["ticker"] == ticker].sort_values("date").copy()
        gc = cashflow[cashflow["ticker"] == ticker].sort_values("date").copy()
        li = gi.iloc[-1] if not gi.empty else pd.Series(dtype=float)
        lb = gb.iloc[-1] if not gb.empty else pd.Series(dtype=float)
        lc = gc.iloc[-1] if not gc.empty else pd.Series(dtype=float)
        rrow = ratios[ratios["ticker"] == ticker].iloc[0] if (not ratios.empty and ticker in ratios["ticker"].values) else pd.Series(dtype=object)
        kmrow = key_metrics[key_metrics["ticker"] == ticker].iloc[0] if (not key_metrics.empty and ticker in key_metrics["ticker"].values) else pd.Series(dtype=object)
        erow = est_summary[est_summary["ticker"] == ticker].iloc[0] if (not est_summary.empty and ticker in est_summary["ticker"].values) else pd.Series(dtype=object)
        pcrow = pt_consensus[pt_consensus["ticker"] == ticker].iloc[0] if (not pt_consensus.empty and ticker in pt_consensus["ticker"].values) else pd.Series(dtype=object)
        rsrow = ratings[ratings["ticker"] == ticker].iloc[0] if (not ratings.empty and ticker in ratings["ticker"].values) else pd.Series(dtype=object)
        qrow = quotes[quotes["ticker"] == ticker].iloc[0] if (not quotes.empty and ticker in quotes["ticker"].values) else pd.Series(dtype=object)
        first_rev, last_rev = first_last_valid(gi, "revenue_ttm")
        rev_cagr = np.nan
        if first_rev is not None and last_rev is not None:
            years = (last_rev["date"] - first_rev["date"]).days / 365.25
            rev_cagr = cagr(first_rev["revenue_ttm"], last_rev["revenue_ttm"], years)
        first_ni, last_ni = first_last_valid(gi, "netIncome_ttm")
        ni_cagr = np.nan
        if first_ni is not None and last_ni is not None:
            years = (last_ni["date"] - first_ni["date"]).days / 365.25
            ni_cagr = cagr(first_ni["netIncome_ttm"], last_ni["netIncome_ttm"], years)
        first_fcf, last_fcf = first_last_valid(gc, "freeCashFlow_ttm")
        fcf_cagr = np.nan
        if first_fcf is not None and last_fcf is not None:
            years = (last_fcf["date"] - first_fcf["date"]).days / 365.25
            fcf_cagr = cagr(first_fcf["freeCashFlow_ttm"], last_fcf["freeCashFlow_ttm"], years)
        cash_col = pick_col(gb, ["cashAndShortTermInvestments", "cashAndCashEquivalents"])
        debt_col = pick_col(gb, ["totalDebt", "netDebt", "longTermDebt"])
        equity_col = pick_col(gb, ["totalStockholdersEquity"])
        ca_col = pick_col(gb, ["totalCurrentAssets"])
        cl_col = pick_col(gb, ["totalCurrentLiabilities"])
        assets_col = pick_col(gb, ["totalAssets"])
        liabilities_col = pick_col(gb, ["totalLiabilities"])
        latest_cash = lb.get(cash_col, np.nan) if cash_col else np.nan
        latest_debt = lb.get(debt_col, np.nan) if debt_col else np.nan
        latest_equity = lb.get(equity_col, np.nan) if equity_col else np.nan
        latest_current_assets = lb.get(ca_col, np.nan) if ca_col else np.nan
        latest_current_liabilities = lb.get(cl_col, np.nan) if cl_col else np.nan
        latest_assets = lb.get(assets_col, np.nan) if assets_col else np.nan
        latest_liabilities = lb.get(liabilities_col, np.nan) if liabilities_col else np.nan
        current_ratio = latest_current_assets / latest_current_liabilities if pd.notna(latest_current_assets) and pd.notna(latest_current_liabilities) and latest_current_liabilities != 0 else np.nan
        debt_to_equity = latest_debt / latest_equity if pd.notna(latest_debt) and pd.notna(latest_equity) and latest_equity != 0 else np.nan
        liabilities_to_assets = latest_liabilities / latest_assets if pd.notna(latest_liabilities) and pd.notna(latest_assets) and latest_assets != 0 else np.nan
        latest_revenue_ttm = li.get("revenue_ttm", np.nan)
        latest_net_income_ttm = li.get("netIncome_ttm", np.nan)
        latest_ocf_ttm = lc.get("operatingCashFlow_ttm", np.nan)
        latest_fcf_ttm = lc.get("freeCashFlow_ttm", np.nan)
        latest_capex_ttm = lc.get("capitalExpenditure_ttm", np.nan)
        ocf_margin = latest_ocf_ttm / latest_revenue_ttm if pd.notna(latest_ocf_ttm) and pd.notna(latest_revenue_ttm) and latest_revenue_ttm != 0 else np.nan
        fcf_margin = latest_fcf_ttm / latest_revenue_ttm if pd.notna(latest_fcf_ttm) and pd.notna(latest_revenue_ttm) and latest_revenue_ttm != 0 else np.nan
        cash_conversion = latest_ocf_ttm / latest_net_income_ttm if pd.notna(latest_ocf_ttm) and pd.notna(latest_net_income_ttm) and latest_net_income_ttm != 0 else np.nan
        capex_as_pct_rev = abs(latest_capex_ttm) / latest_revenue_ttm if pd.notna(latest_capex_ttm) and pd.notna(latest_revenue_ttm) and latest_revenue_ttm != 0 else np.nan
        roe = latest_net_income_ttm / latest_equity if pd.notna(latest_net_income_ttm) and pd.notna(latest_equity) and latest_equity != 0 else np.nan
        roa = latest_net_income_ttm / latest_assets if pd.notna(latest_net_income_ttm) and pd.notna(latest_assets) and latest_assets != 0 else np.nan
        quote_price = _safe_number(_safe_series_get(qrow, ["price"]))
        quote_pe = _safe_number(_safe_series_get(qrow, ["pe"]))
        quote_market_cap = _safe_number(_safe_series_get(qrow, ["marketCap"]))
        shares_outstanding = _safe_number(_safe_series_get(qrow, ["sharesOutstanding"]))
        pe_ttm = _safe_number(_safe_series_get(rrow, ["peRatioTTM", "priceEarningsRatioTTM", "peRatio"]))
        if pd.isna(pe_ttm):
            pe_ttm = quote_pe
        pb_ttm = _safe_number(_safe_series_get(rrow, ["priceToBookRatioTTM", "pbRatioTTM", "priceToBookRatio"]))
        ps_ttm = _safe_number(_safe_series_get(rrow, ["priceToSalesRatioTTM", "psRatioTTM", "priceToSalesRatio"]))
        pfcf_ttm = _safe_number(_safe_series_get(rrow, ["priceToFreeCashFlowsRatioTTM", "pfcfRatioTTM", "priceToFreeCashFlowsRatio"]))
        market_cap = _safe_number(_safe_series_get(kmrow, ["marketCapTTM", "marketCap"]))
        if pd.isna(market_cap):
            market_cap = quote_market_cap
        enterprise_value = _safe_number(_safe_series_get(kmrow, ["enterpriseValueTTM", "enterpriseValue"]))
        enterprise_to_ebitda = _safe_number(_safe_series_get(kmrow, ["enterpriseValueOverEBITDATTM", "enterpriseValueOverEBITDA"]))
        book_value_per_share = _safe_number(_safe_series_get(kmrow, ["bookValuePerShareTTM", "bookValuePerShare"]))
        fcf_per_share = _safe_number(_safe_series_get(kmrow, ["freeCashFlowPerShareTTM", "freeCashFlowPerShare"]))
        earnings_yield = _safe_number(_safe_series_get(kmrow, ["earningsYieldTTM", "earningsYield"]))
        fcf_yield = _safe_number(_safe_series_get(kmrow, ["freeCashFlowYieldTTM", "freeCashFlowYield"]))
        if pd.isna(book_value_per_share) and pd.notna(latest_equity) and pd.notna(shares_outstanding) and shares_outstanding != 0:
            book_value_per_share = latest_equity / shares_outstanding
        if pd.isna(fcf_per_share) and pd.notna(latest_fcf_ttm) and pd.notna(shares_outstanding) and shares_outstanding != 0:
            fcf_per_share = latest_fcf_ttm / shares_outstanding
        if pd.isna(ps_ttm) and pd.notna(market_cap) and pd.notna(latest_revenue_ttm) and latest_revenue_ttm != 0:
            ps_ttm = market_cap / latest_revenue_ttm
        if pd.isna(pfcf_ttm) and pd.notna(market_cap) and pd.notna(latest_fcf_ttm) and latest_fcf_ttm != 0:
            pfcf_ttm = market_cap / latest_fcf_ttm
        if pd.isna(earnings_yield) and pd.notna(pe_ttm) and pe_ttm != 0:
            earnings_yield = 1 / pe_ttm
        if pd.isna(fcf_yield) and pd.notna(pfcf_ttm) and pfcf_ttm != 0:
            fcf_yield = 1 / pfcf_ttm
        forward_rev = _safe_number(erow.get("Forward Revenue Next FY", np.nan))
        forward_rev_2 = _safe_number(erow.get("Forward Revenue FY+1", np.nan))
        forward_rev_growth = _safe_number(erow.get("Forward Revenue Growth FY+1", np.nan))
        forward_eps = _safe_number(erow.get("Forward EPS Next FY", np.nan))
        forward_ebitda = _safe_number(erow.get("Forward EBITDA Next FY", np.nan))
        forward_net_income = _safe_number(erow.get("Forward Net Income Next FY", np.nan))
        forward_pe = np.nan
        if pd.notna(quote_price) and pd.notna(forward_eps) and forward_eps != 0:
            forward_pe = quote_price / forward_eps
        forward_ps = np.nan
        if pd.notna(market_cap) and pd.notna(forward_rev) and forward_rev != 0:
            forward_ps = market_cap / forward_rev
        pt_consensus_val = _safe_number(_safe_series_get(pcrow, ["targetConsensus", "priceTargetConsensus", "targetMean", "priceTargetAverage", "consensusPriceTarget"]))
        analyst_rating = _safe_series_get(rsrow, ["ratingRecommendation", "rating", "overallRecommendation", "ratingDetailsDCFRecommendation", "ratingDetailsROERecommendation"], default=np.nan)
        overall_score = _safe_number(_safe_series_get(rsrow, ["ratingScore", "overallScore"]))
        price_target_upside = np.nan
        if pd.notna(pt_consensus_val) and pd.notna(quote_price) and quote_price != 0:
            price_target_upside = (pt_consensus_val - quote_price) / quote_price
        rows.append({
            "Ticker": ticker,
            "Latest Revenue TTM": latest_revenue_ttm,
            "Revenue CAGR 3Y": rev_cagr,
            "Net Income CAGR 3Y": ni_cagr,
            "FCF CAGR 3Y": fcf_cagr,
            "Latest Gross Margin": li.get("gross_margin_ttm", np.nan),
            "Latest Operating Margin": li.get("operating_margin_ttm", np.nan),
            "Latest EBITDA Margin": li.get("ebitda_margin_ttm", np.nan),
            "Latest Net Margin": li.get("net_margin_ttm", np.nan),
            "Latest OCF TTM": latest_ocf_ttm,
            "Latest FCF TTM": latest_fcf_ttm,
            "OCF Margin": ocf_margin,
            "FCF Margin": fcf_margin,
            "Cash Conversion": cash_conversion,
            "Capex as % Revenue": capex_as_pct_rev,
            "Cash / ST Investments": latest_cash,
            "Total Debt": latest_debt,
            "Equity": latest_equity,
            "Current Ratio": current_ratio,
            "Debt to Equity": debt_to_equity,
            "Liabilities to Assets": liabilities_to_assets,
            "ROE": roe,
            "ROA": roa,
            "Market Cap": market_cap,
            "Enterprise Value": enterprise_value,
            "Enterprise Value / EBITDA": enterprise_to_ebitda,
            "P/E TTM": pe_ttm,
            "P/B TTM": pb_ttm,
            "P/S TTM": ps_ttm,
            "P/FCF TTM": pfcf_ttm,
            "Earnings Yield": earnings_yield,
            "FCF Yield": fcf_yield,
            "Book Value / Share": book_value_per_share,
            "FCF / Share": fcf_per_share,
            "Forward Revenue Next FY": forward_rev,
            "Forward Revenue FY+1": forward_rev_2,
            "Forward Revenue Growth FY+1": forward_rev_growth,
            "Forward EPS Next FY": forward_eps,
            "Forward EBITDA Next FY": forward_ebitda,
            "Forward Net Income Next FY": forward_net_income,
            "Forward P/E": forward_pe,
            "Forward P/S": forward_ps,
            "Price Target Consensus": pt_consensus_val,
            "Price Target Upside": price_target_upside,
            "Analyst Rating": analyst_rating,
            "Rating Score": overall_score,
            "Close": quote_price,
        })
    return pd.DataFrame(rows)


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["SMA 50"] = out["close"].rolling(50, min_periods=50).mean()
    out["SMA 200"] = out["close"].rolling(200, min_periods=200).mean()
    out["RSI 14"] = compute_rsi(out["close"], window=14)
    macd_line, signal_line, macd_hist = compute_macd(out["close"])
    out["MACD Line"] = macd_line
    out["MACD Signal"] = signal_line
    out["MACD Hist"] = macd_hist
    out["ATR 14"] = compute_atr(out, window=14)
    out["20D Avg Volume"] = out["volume"].rolling(20, min_periods=20).mean()
    out["ret_3m"] = out["close"].pct_change(63)
    out["ret_1m"] = out["close"].pct_change(21)
    return out


def fetch_price_history(symbol: str, api_key: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> pd.DataFrame:
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
    params = {"apikey": api_key}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or "historical" not in data or not data["historical"]:
        return pd.DataFrame()
    df = pd.DataFrame(data["historical"])
    df["ticker"] = symbol
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["open", "high", "low", "close", "adjClose", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def fetch_all_price_history(symbols: List[str], api_key: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    out = {}
    for sym in symbols:
        try:
            out[sym] = fetch_price_history(sym, api_key=api_key, from_date=from_date, to_date=to_date)
        except Exception:
            out[sym] = pd.DataFrame()
    return out


def get_price_on_or_before(df: pd.DataFrame, target_date: pd.Timestamp) -> float:
    temp = df[df["date"] <= target_date]
    if temp.empty:
        return np.nan
    return temp.iloc[-1]["close"]


def calc_return(current_price: float, past_price: float) -> float:
    if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
        return np.nan
    return (current_price / past_price) - 1


def summarize_technicals(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    df = add_technical_indicators(df)
    latest = df.iloc[-1]
    latest_date = latest["date"]
    current_price = latest["close"]
    ytd_anchor = pd.Timestamp(year=latest_date.year - 1, month=12, day=31)
    ytd_price = get_price_on_or_before(df, ytd_anchor)
    one_year_price = get_price_on_or_before(df, latest_date - pd.DateOffset(years=1))
    three_year_price = get_price_on_or_before(df, latest_date - pd.DateOffset(years=3))
    five_year_price = get_price_on_or_before(df, latest_date - pd.DateOffset(years=5))
    trailing_52w = df[df["date"] >= (latest_date - pd.DateOffset(weeks=52))].copy()
    high_52w = trailing_52w["high"].max() if not trailing_52w.empty else np.nan
    low_52w = trailing_52w["low"].min() if not trailing_52w.empty else np.nan
    pct_below_52w_high = (current_price / high_52w) - 1 if pd.notna(current_price) and pd.notna(high_52w) and high_52w != 0 else np.nan
    pct_above_52w_low = (current_price / low_52w) - 1 if pd.notna(current_price) and pd.notna(low_52w) and low_52w != 0 else np.nan
    sma50 = latest.get("SMA 50", np.nan)
    sma200 = latest.get("SMA 200", np.nan)
    pct_from_sma50 = (current_price / sma50) - 1 if pd.notna(current_price) and pd.notna(sma50) and sma50 != 0 else np.nan
    pct_from_sma200 = (current_price / sma200) - 1 if pd.notna(current_price) and pd.notna(sma200) and sma200 != 0 else np.nan
    vol20 = latest.get("20D Avg Volume", np.nan)
    volume_vs_20d = (latest["volume"] / vol20) - 1 if pd.notna(latest["volume"]) and pd.notna(vol20) and vol20 != 0 else np.nan
    drawdown = None
    if pd.notna(current_price) and pd.notna(high_52w) and high_52w != 0:
        drawdown = pct_below_52w_high
    ann_vol = df["close"].pct_change().tail(63).std() * (252 ** 0.5)
    return {
        "Ticker": latest["ticker"],
        "As Of Date": latest_date.date(),
        "Close": current_price,
        "YTD Return": calc_return(current_price, ytd_price),
        "1Y Return": calc_return(current_price, one_year_price),
        "3Y Return (Price)": calc_return(current_price, three_year_price),
        "5Y Return (Price)": calc_return(current_price, five_year_price),
        "52W High": high_52w,
        "52W Low": low_52w,
        "% Below 52W High": pct_below_52w_high,
        "% Above 52W Low": pct_above_52w_low,
        "RSI 14": latest.get("RSI 14", np.nan),
        "MACD Line": latest.get("MACD Line", np.nan),
        "MACD Signal": latest.get("MACD Signal", np.nan),
        "MACD Hist": latest.get("MACD Hist", np.nan),
        "SMA 50": sma50,
        "SMA 200": sma200,
        "% From SMA 50": pct_from_sma50,
        "% From SMA 200": pct_from_sma200,
        "ATR 14": latest.get("ATR 14", np.nan),
        "Volume": latest.get("volume", np.nan),
        "20D Avg Volume": vol20,
        "Volume vs 20D Avg": volume_vs_20d,
        "1M Return": latest.get("ret_1m", np.nan),
        "3M Return": latest.get("ret_3m", np.nan),
        "Annualized Vol 3M": ann_vol,
        "Max Drawdown 1Y": drawdown,
    }


def build_technical_scorecard(symbols: List[str], api_key: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> pd.DataFrame:
    history = fetch_all_price_history(symbols, api_key=api_key, from_date=from_date, to_date=to_date)
    rows = []
    for sym, df in history.items():
        if not df.empty:
            rows.append(summarize_technicals(df))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    if "Ticker" in out.columns:
        out["Ticker"] = out["Ticker"].astype(str).str.upper().str.strip()
    return out.sort_values("Ticker").reset_index(drop=True)


def build_combined_scorecard(fundamental_scorecard: pd.DataFrame, technical_scorecard: pd.DataFrame) -> pd.DataFrame:
    f = fundamental_scorecard.copy()
    t = technical_scorecard.copy()
    if "Ticker" in f.columns:
        f["Ticker"] = f["Ticker"].astype(str).str.upper().str.strip()
    if not t.empty and "Ticker" in t.columns:
        t["Ticker"] = t["Ticker"].astype(str).str.upper().str.strip()
    if t.empty:
        return f
    return f.merge(t, on="Ticker", how="left")


ALIAS_MAP = {
    "Ticker": "ticker",
    "Close": "last_price",
    "Market Cap": "market_cap",
    "Revenue CAGR 3Y": "revenue_cagr_3y",
    "Net Income CAGR 3Y": "net_income_cagr_3y",
    "FCF CAGR 3Y": "fcf_cagr_3y",
    "Latest Gross Margin": "gross_margin",
    "Latest Operating Margin": "operating_margin",
    "Latest EBITDA Margin": "ebitda_margin",
    "Latest Net Margin": "profit_margin",
    "Current Ratio": "current_ratio",
    "Debt to Equity": "debt_to_equity",
    "Liabilities to Assets": "liabilities_to_assets",
    "ROE": "return_on_equity",
    "ROA": "return_on_assets",
    "P/E TTM": "trailing_pe",
    "P/B TTM": "price_to_book",
    "P/S TTM": "price_to_sales",
    "P/FCF TTM": "price_to_fcf",
    "Enterprise Value / EBITDA": "enterprise_to_ebitda",
    "Forward Revenue Growth FY+1": "forward_revenue_growth",
    "Forward EPS Next FY": "forward_eps_next_fy",
    "Forward P/E": "forward_pe",
    "Forward P/S": "forward_ps",
    "Price Target Consensus": "price_target_consensus",
    "Price Target Upside": "analyst_upside_pct",
    "Analyst Rating": "analyst_rating",
    "Rating Score": "rating_score",
    "YTD Return": "ret_ytd",
    "1M Return": "ret_1m",
    "3M Return": "ret_3m",
    "1Y Return": "ret_1y",
    "3Y Return (Price)": "ret_3y_price",
    "5Y Return (Price)": "ret_5y_price",
    "% Below 52W High": "drawdown_from_52w_high",
    "% Above 52W Low": "distance_from_52w_low",
    "RSI 14": "rsi_14",
    "MACD Line": "macd_line",
    "MACD Signal": "macd_signal",
    "MACD Hist": "macd_hist",
    "% From SMA 50": "price_vs_50dma",
    "% From SMA 200": "price_vs_200dma",
    "ATR 14": "atr_14",
    "Volume": "volume",
    "20D Avg Volume": "avg_volume_20d",
    "Volume vs 20D Avg": "volume_vs_20d_avg",
    "Annualized Vol 3M": "ann_vol_3m",
    "Max Drawdown 1Y": "max_drawdown_1y",
}


def add_alias_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for old, new in ALIAS_MAP.items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]
    if "Ticker" in out.columns and "ticker" not in out.columns:
        out["ticker"] = out["Ticker"]
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def build_research_snapshot(symbols: List[str], api_key: str, price_from: Optional[str] = None, price_to: Optional[str] = None) -> pd.DataFrame:
    symbols = sorted({str(s).upper().strip() for s in symbols if str(s).strip()})
    if not symbols or not api_key:
        return pd.DataFrame({"ticker": symbols})
    financials = prepare_financials(symbols, api_key=api_key, limit=40)
    market_data = fetch_market_intelligence(symbols, api_key=api_key)
    fundamentals = build_analyst_scorecard(financials, market_data)
    technicals = build_technical_scorecard(symbols, api_key=api_key, from_date=price_from or PRICE_FROM_DATE, to_date=price_to)
    combined = build_combined_scorecard(fundamentals, technicals)
    return add_alias_columns(combined)
