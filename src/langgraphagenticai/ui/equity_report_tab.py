import io
import json
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
from openai import OpenAI
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak


PRICE_FROM_DATE = "2019-01-01"
PRICE_TO_DATE = None


def _get_json(url: str, params: dict, timeout: int = 30):
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _safe_number(x):
    """Convert API/display values to a safe real float. Complex or invalid values become NaN."""
    try:
        if x is None or x == "":
            return np.nan
        if isinstance(x, complex):
            if abs(x.imag) < 1e-12:
                x = x.real
            else:
                return np.nan
        val = float(x)
        if not np.isfinite(val):
            return np.nan
        return val
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
    """Safe CAGR. Returns NaN when values are non-positive to avoid complex numbers."""
    start_value = _safe_number(start_value)
    end_value = _safe_number(end_value)
    years = _safe_number(years)

    if (
        pd.isna(start_value)
        or pd.isna(end_value)
        or pd.isna(years)
        or start_value <= 0
        or end_value <= 0
        or years <= 0
    ):
        return np.nan

    result = (end_value / start_value) ** (1 / years) - 1
    return _safe_number(result)


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


def weighted_average_available(row: pd.Series, weighted_cols: Dict[str, float]) -> float:
    vals, wts = [], []
    for col, wt in weighted_cols.items():
        val = row.get(col, np.nan)
        if pd.notna(val):
            vals.append(val * wt)
            wts.append(wt)
    if not wts:
        return np.nan
    return sum(vals) / sum(wts)


def safe_rank_series(series: pd.Series, ascending: bool = True) -> pd.Series:
    """
    Safely create percentile ranks without calling pandas.Series.rank().

    This avoids the pandas compiled rank path that can throw:
    TypeError: No matching signature found.

    Returns 0-to-1 percentile scores.
    ascending=True  -> larger values get higher scores.
    ascending=False -> smaller values get higher scores.
    Missing/non-numeric/inf values remain NaN.
    """
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    arr = np.asarray(s, dtype="float64")

    out = np.full(len(arr), np.nan, dtype="float64")
    valid_mask = np.isfinite(arr)
    valid_idx = np.where(valid_mask)[0]

    if len(valid_idx) == 0:
        return pd.Series(out, index=series.index, dtype="float64")

    values = arr[valid_idx]
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]

    ranks = np.empty(len(values), dtype="float64")
    n = len(values)
    start_pos = 0
    while start_pos < n:
        end_pos = start_pos + 1
        while end_pos < n and sorted_values[end_pos] == sorted_values[start_pos]:
            end_pos += 1
        avg_rank = (start_pos + 1 + end_pos) / 2.0
        ranks[order[start_pos:end_pos]] = avg_rank
        start_pos = end_pos

    pct = ranks / n

    if not ascending:
        pct = 1.0 - pct + (1.0 / n)

    out[valid_idx] = pct
    return pd.Series(out, index=series.index, dtype="float64")




def _first_existing_value(row: pd.Series, keys: List[str], default=np.nan):
    """Return the first available numeric value from a row using flexible FMP field names."""
    for k in keys:
        if k in row.index and pd.notna(row.get(k)):
            return _safe_number(row.get(k))
    return default


def _latest_field_value(df: pd.DataFrame, keys: List[str], default=np.nan):
    """Return the most recent value for the first field that exists in a dataframe."""
    if df.empty:
        return default
    for k in keys:
        if k in df.columns:
            temp = df.dropna(subset=[k]).sort_values("date") if "date" in df.columns else df.dropna(subset=[k])
            if not temp.empty:
                return _safe_number(temp.iloc[-1].get(k))
    return default


def _cagr_from_field(df: pd.DataFrame, keys: List[str], years_hint: float = 3.0) -> float:
    """Calculate CAGR using the first/last available values for flexible FMP fields."""
    if df.empty:
        return np.nan
    for k in keys:
        if k not in df.columns:
            continue
        temp = df.dropna(subset=[k]).sort_values("date") if "date" in df.columns else df.dropna(subset=[k])
        if len(temp) < 2:
            continue
        first = temp.iloc[0]
        last = temp.iloc[-1]
        if "date" in temp.columns and pd.notna(first.get("date")) and pd.notna(last.get("date")):
            years = max((last["date"] - first["date"]).days / 365.25, 0.25)
        else:
            years = years_hint
        return cagr(_safe_number(first.get(k)), _safe_number(last.get(k)), years)
    return np.nan


def _safe_divide(numerator, denominator) -> float:
    numerator = _safe_number(numerator)
    denominator = _safe_number(denominator)
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return np.nan
    return numerator / denominator

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


def fetch_as_reported_statement(symbol: str, statement_type: str, api_key: str, period: str = "quarter", limit: int = 40) -> pd.DataFrame:
    """
    Fetch FMP as-reported statements. This is especially useful for banks because
    standardized statements often hide useful fields like deposits, loan balances,
    provision expense, interest income/expense, noninterest expense, and fee revenue.
    """
    base_v3 = {
        "income_ar": "https://financialmodelingprep.com/api/v3/income-statement-as-reported",
        "balance_ar": "https://financialmodelingprep.com/api/v3/balance-sheet-statement-as-reported",
    }
    url = f"{base_v3[statement_type]}/{symbol}"
    params = {"period": period, "limit": limit, "apikey": api_key}

    try:
        data = _get_json(url, params)
    except Exception:
        return pd.DataFrame()

    if not isinstance(data, list) or len(data) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["ticker"] = symbol.upper()
    df["statement_type"] = statement_type
    df["as_reported_period_request"] = period
    return df


def fetch_all_statements(symbols: List[str], api_key: str, limit: int = 40) -> Dict[str, pd.DataFrame]:
    out = {"income": [], "balance": [], "cashflow": [], "income_ar": [], "balance_ar": []}

    for sym in symbols:
        # Standardized statements
        for stype in ["income", "balance", "cashflow"]:
            try:
                df = fetch_statement(sym, stype, api_key=api_key, period="quarter", limit=limit)
                if not df.empty:
                    out[stype].append(df)
            except Exception as e:
                st.warning(f"{sym} {stype} fetch failed: {e}")

        # As-reported statements. We try quarterly first so TTM metrics work.
        # If quarterly is unavailable, we fall back to annual and still use latest FY values.
        for ar_type in ["income_ar", "balance_ar"]:
            try:
                df_ar = fetch_as_reported_statement(sym, ar_type, api_key=api_key, period="quarter", limit=limit)
                if df_ar.empty:
                    df_ar = fetch_as_reported_statement(sym, ar_type, api_key=api_key, period="annual", limit=min(limit, 10))
                if not df_ar.empty:
                    out[ar_type].append(df_ar)
            except Exception as e:
                st.warning(f"{sym} {ar_type} fetch failed: {e}")

    for k in out:
        out[k] = pd.concat(out[k], ignore_index=True) if out[k] else pd.DataFrame()

    return out


def prepare_financials(symbols: List[str], api_key: str, limit: int = 40) -> Dict[str, pd.DataFrame]:
    data = fetch_all_statements(symbols, api_key=api_key, limit=limit)

    income = standardize_date_sort(data["income"])
    balance = standardize_date_sort(data["balance"])
    cashflow = standardize_date_sort(data["cashflow"])
    income_ar = standardize_date_sort(data.get("income_ar", pd.DataFrame()))
    balance_ar = standardize_date_sort(data.get("balance_ar", pd.DataFrame()))

    income_cols = [
        "revenue", "grossProfit", "operatingIncome", "netIncome",
        "ebitda", "interestExpense", "incomeBeforeTax", "weightedAverageShsOutDil",
        "researchAndDevelopmentExpenses",
        # Bank / financial institution fields. FMP field availability varies by ticker,
        # so these are optional and are converted only when present.
        "interestIncome", "interestRevenue", "netInterestIncome",
        "nonInterestIncome", "noninterestIncome",
        "provisionForLoanLosses", "provisionForCreditLosses", "provisionForCreditLoss",
        "nonInterestExpense", "noninterestExpense", "operatingExpenses",
        "sellingGeneralAndAdministrativeExpenses",
    ]
    balance_cols = [
        "cashAndCashEquivalents", "shortTermInvestments", "cashAndShortTermInvestments",
        "totalCurrentAssets", "totalAssets", "totalCurrentLiabilities", "totalLiabilities",
        "netDebt", "totalDebt", "longTermDebt", "shortTermDebt", "totalStockholdersEquity",
        # Bank / financial institution balance-sheet fields.
        "totalDeposits", "deposits", "customerDeposits", "bankDeposits",
        "totalLoans", "netLoans", "loans", "loansAndLeases", "grossLoans",
        "tangibleCommonEquity", "tangibleBookValue", "goodwill", "intangibleAssets",
        "goodwillAndIntangibleAssets", "deferredRevenue", "deferredRevenueNonCurrent",
        "riskWeightedAssets", "commonEquityTier1Capital",
    ]
    cashflow_cols = [
        "operatingCashFlow", "freeCashFlow", "capitalExpenditure",
        "netCashProvidedByOperatingActivities"
    ]

    bank_income_ar_cols = [
        "investmentbankingrevenue",
        "principaltransactionsrevenue",
        "lendinganddepositrelatedfees",
        "assetmanagementfees",
        "feesandcommissions",
        "feesandcommissioncreditanddebitcards",
        "mortgagefeesandrelatedincome",
        "noninterestincomeother",
        "interestincomeoperating",
        "interestexpenseoperating",
        "revenuesnetofinterestexpense",
        "provisionforloanleaselossesandotherlosses",
        "noninterestexpense",
        "netincome",
    ]

    bank_balance_ar_cols = [
        "deposits",
        "financingreceivableexcludingaccruedinterestbeforeallowanceforcreditlossesnetofdeferredincome",
        "financingreceivableexcludinguaccruedinterestafterallowanceforcreditlosses",
        "financingreceivableexcludinguaccruedinterestbeforeallowanceforcreditlossesnetofdeferredincome",
        "loansreceivablefairvaluedisclosure",
        "financingreceivablesbeforeallowanceforcreditlosses",
        "financingreceivablesafterallowanceforcreditlosses",
        "financingreceivable",
        "financingreceivables",
        "loans",
        "loansandleases",
        "loansandleasefinancingreceivables",
        "loansreceivable",
        "loansreceivablenet",
        "loansheldforinvestment",
        "loansheldforinvestmentnet",
        "totalloans",
        "totalloansandleases",
        "commercialloans",
        "consumerloans",
        "loanstocustomers",
        "customerloans",
        "assets",
        "liabilities",
        "stockholdersequity",
        "longtermdebtandcapitalleaseobligationsincludingcurrentmaturities",
        "shorttermborrowings",
        "cashduefrombanks",
        "interestbearingdepositsinbanks",
        "goodwillservicingassetsatfairvalueandotherintangibleassets",
    ]

    income = to_numeric_if_exists(income, income_cols)
    balance = to_numeric_if_exists(balance, balance_cols)
    cashflow = to_numeric_if_exists(cashflow, cashflow_cols)
    income_ar = to_numeric_if_exists(income_ar, bank_income_ar_cols)
    balance_ar = to_numeric_if_exists(balance_ar, bank_balance_ar_cols)

    income = add_ttm(income, [
        "revenue", "grossProfit", "operatingIncome", "netIncome", "ebitda",
        "researchAndDevelopmentExpenses",
        "interestIncome", "interestRevenue", "interestExpense", "netInterestIncome",
        "nonInterestIncome", "noninterestIncome",
        "provisionForLoanLosses", "provisionForCreditLosses", "provisionForCreditLoss",
        "nonInterestExpense", "noninterestExpense", "operatingExpenses",
        "sellingGeneralAndAdministrativeExpenses",
    ])
    cashflow = add_ttm(cashflow, ["operatingCashFlow", "freeCashFlow", "capitalExpenditure"])

    # As-reported bank fields. If the endpoint returns quarterly periods, these become TTM.
    # If the endpoint only returns annual FY rows, downstream logic falls back to latest FY.
    if not income_ar.empty and "period" in income_ar.columns:
        is_quarterly_ar = income_ar["period"].astype(str).str.upper().str.startswith("Q").any()
    else:
        is_quarterly_ar = False

    if is_quarterly_ar:
        income_ar = add_ttm(income_ar, bank_income_ar_cols)
    else:
        for c in bank_income_ar_cols:
            if c in income_ar.columns:
                income_ar[f"{c}_ttm"] = income_ar[c]

    # Balance sheet fields are point-in-time, so we keep raw fields and do not TTM-sum them.

    if "revenue_ttm" in income.columns:
        if "grossProfit_ttm" in income.columns:
            income["gross_margin_ttm"] = income["grossProfit_ttm"] / income["revenue_ttm"]
        if "operatingIncome_ttm" in income.columns:
            income["operating_margin_ttm"] = income["operatingIncome_ttm"] / income["revenue_ttm"]
        if "netIncome_ttm" in income.columns:
            income["net_margin_ttm"] = income["netIncome_ttm"] / income["revenue_ttm"]
        if "ebitda_ttm" in income.columns:
            income["ebitda_margin_ttm"] = income["ebitda_ttm"] / income["revenue_ttm"]

    return {
        "income": income,
        "balance": balance,
        "cashflow": cashflow,
        "income_ar": income_ar,
        "balance_ar": balance_ar,
    }


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

    ratios, key_metrics, ests, pt_consensus, ratings, quotes, profiles = [], [], [], [], [], [], []

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

        prof = fetch_one_row_endpoint(f"https://financialmodelingprep.com/api/v3/profile/{sym}", sym, api_key=api_key)
        if not prof.empty:
            profiles.append(prof)

    return {
        "ratios_ttm": pd.concat(ratios, ignore_index=True) if ratios else pd.DataFrame(),
        "key_metrics_ttm": pd.concat(key_metrics, ignore_index=True) if key_metrics else pd.DataFrame(),
        "analyst_estimates": pd.concat(ests, ignore_index=True) if ests else pd.DataFrame(),
        "price_target_consensus": pd.concat(pt_consensus, ignore_index=True) if pt_consensus else pd.DataFrame(),
        "ratings_snapshot": pd.concat(ratings, ignore_index=True) if ratings else pd.DataFrame(),
        "quote": pd.concat(quotes, ignore_index=True) if quotes else pd.DataFrame(),
        "profile": pd.concat(profiles, ignore_index=True) if profiles else pd.DataFrame(),
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
    income_ar = latest_and_window(financials.get("income_ar", pd.DataFrame()), years=3)
    balance_ar = latest_and_window(financials.get("balance_ar", pd.DataFrame()), years=3)

    ratios = market_data["ratios_ttm"].copy()
    key_metrics = market_data["key_metrics_ttm"].copy()
    est_summary = summarize_analyst_estimates(market_data["analyst_estimates"])
    pt_consensus = market_data["price_target_consensus"].copy()
    ratings = market_data["ratings_snapshot"].copy()
    quotes = market_data["quote"].copy()
    profiles = market_data.get("profile", pd.DataFrame()).copy()

    for df in [ratios, key_metrics, est_summary, pt_consensus, ratings, quotes, profiles]:
        if not df.empty and "symbol" in df.columns and "ticker" not in df.columns:
            df.rename(columns={"symbol": "ticker"}, inplace=True)

    tickers = sorted(
        set(income["ticker"].dropna().unique())
        .union(balance["ticker"].dropna().unique())
        .union(cashflow["ticker"].dropna().unique())
        .union(income_ar["ticker"].dropna().unique() if not income_ar.empty and "ticker" in income_ar.columns else [])
        .union(balance_ar["ticker"].dropna().unique() if not balance_ar.empty and "ticker" in balance_ar.columns else [])
    )

    rows = []

    for ticker in tickers:
        gi = income[income["ticker"] == ticker].sort_values("date").copy()
        gb = balance[balance["ticker"] == ticker].sort_values("date").copy()
        gc = cashflow[cashflow["ticker"] == ticker].sort_values("date").copy()
        gai = income_ar[income_ar["ticker"] == ticker].sort_values("date").copy() if not income_ar.empty and "ticker" in income_ar.columns else pd.DataFrame()
        gab = balance_ar[balance_ar["ticker"] == ticker].sort_values("date").copy() if not balance_ar.empty and "ticker" in balance_ar.columns else pd.DataFrame()

        li = gi.iloc[-1] if not gi.empty else pd.Series(dtype=float)
        lb = gb.iloc[-1] if not gb.empty else pd.Series(dtype=float)
        lc = gc.iloc[-1] if not gc.empty else pd.Series(dtype=float)
        lai = gai.iloc[-1] if not gai.empty else pd.Series(dtype=float)
        lab = gab.iloc[-1] if not gab.empty else pd.Series(dtype=float)

        rrow = ratios[ratios["ticker"] == ticker].iloc[0] if (not ratios.empty and ticker in ratios["ticker"].values) else pd.Series(dtype=object)
        kmrow = key_metrics[key_metrics["ticker"] == ticker].iloc[0] if (not key_metrics.empty and ticker in key_metrics["ticker"].values) else pd.Series(dtype=object)
        erow = est_summary[est_summary["ticker"] == ticker].iloc[0] if (not est_summary.empty and ticker in est_summary["ticker"].values) else pd.Series(dtype=object)
        pcrow = pt_consensus[pt_consensus["ticker"] == ticker].iloc[0] if (not pt_consensus.empty and ticker in pt_consensus["ticker"].values) else pd.Series(dtype=object)
        rsrow = ratings[ratings["ticker"] == ticker].iloc[0] if (not ratings.empty and ticker in ratings["ticker"].values) else pd.Series(dtype=object)
        qrow = quotes[quotes["ticker"] == ticker].iloc[0] if (not quotes.empty and ticker in quotes["ticker"].values) else pd.Series(dtype=object)
        prow = profiles[profiles["ticker"] == ticker].iloc[0] if (not profiles.empty and ticker in profiles["ticker"].values) else pd.Series(dtype=object)

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

        pt_consensus_val = _safe_number(_safe_series_get(
            pcrow,
            ["targetConsensus", "priceTargetConsensus", "targetMean", "priceTargetAverage", "consensusPriceTarget"]
        ))

        analyst_rating = _safe_series_get(
            rsrow,
            ["ratingRecommendation", "rating", "overallRecommendation", "ratingDetailsDCFRecommendation", "ratingDetailsROERecommendation"],
            default=np.nan
        )
        overall_score = _safe_number(_safe_series_get(rsrow, ["ratingScore", "overallScore"]))

        # -------------------------------
        # Bank / Financials-specific metrics
        # -------------------------------
        interest_income_ttm = _first_existing_value(
            li,
            ["interestIncome_ttm", "interestRevenue_ttm"],
        )
        if pd.isna(interest_income_ttm):
            interest_income_ttm = _first_existing_value(lai, ["interestincomeoperating_ttm", "interestincomeoperating"])

        interest_expense_ttm = _first_existing_value(li, ["interestExpense_ttm"])
        if pd.isna(interest_expense_ttm):
            interest_expense_ttm = _first_existing_value(lai, ["interestexpenseoperating_ttm", "interestexpenseoperating"])

        net_interest_income_ttm = _first_existing_value(li, ["netInterestIncome_ttm"])
        if pd.isna(net_interest_income_ttm) and pd.notna(interest_income_ttm) and pd.notna(interest_expense_ttm):
            net_interest_income_ttm = interest_income_ttm - abs(interest_expense_ttm)

        revenue_net_interest_expense_ttm = _first_existing_value(
            lai,
            ["revenuesnetofinterestexpense_ttm", "revenuesnetofinterestexpense"],
        )

        noninterest_income_ttm = _first_existing_value(li, ["nonInterestIncome_ttm", "noninterestIncome_ttm"])
        if pd.isna(noninterest_income_ttm):
            noninterest_income_ttm = _first_existing_value(lai, ["noninterestincomeother_ttm", "noninterestincomeother"])

        provision_expense_ttm = _first_existing_value(
            li,
            ["provisionForLoanLosses_ttm", "provisionForCreditLosses_ttm", "provisionForCreditLoss_ttm"],
        )
        if pd.isna(provision_expense_ttm):
            provision_expense_ttm = _first_existing_value(
                lai,
                ["provisionforloanleaselossesandotherlosses_ttm", "provisionforloanleaselossesandotherlosses"],
            )

        noninterest_expense_ttm = _first_existing_value(
            li,
            ["nonInterestExpense_ttm", "noninterestExpense_ttm", "operatingExpenses_ttm", "sellingGeneralAndAdministrativeExpenses_ttm"],
        )
        if pd.isna(noninterest_expense_ttm):
            noninterest_expense_ttm = _first_existing_value(lai, ["noninterestexpense_ttm", "noninterestexpense"])

        investment_banking_revenue_ttm = _first_existing_value(lai, ["investmentbankingrevenue_ttm", "investmentbankingrevenue"])
        trading_revenue_ttm = _first_existing_value(lai, ["principaltransactionsrevenue_ttm", "principaltransactionsrevenue"])
        asset_management_fees_ttm = _first_existing_value(lai, ["assetmanagementfees_ttm", "assetmanagementfees"])
        fees_and_commissions_ttm = _first_existing_value(lai, ["feesandcommissions_ttm", "feesandcommissions"])
        lending_deposit_fees_ttm = _first_existing_value(lai, ["lendinganddepositrelatedfees_ttm", "lendinganddepositrelatedfees"])
        card_fees_ttm = _first_existing_value(lai, ["feesandcommissioncreditanddebitcards_ttm", "feesandcommissioncreditanddebitcards"])
        mortgage_fees_ttm = _first_existing_value(lai, ["mortgagefeesandrelatedincome_ttm", "mortgagefeesandrelatedincome"])

        bank_fee_revenue_components = [
            investment_banking_revenue_ttm,
            asset_management_fees_ttm,
            fees_and_commissions_ttm,
            lending_deposit_fees_ttm,
            card_fees_ttm,
            mortgage_fees_ttm,
        ]
        bank_fee_revenue_ttm = np.nansum([x for x in bank_fee_revenue_components if pd.notna(x)])
        if bank_fee_revenue_ttm == 0 and all(pd.isna(x) for x in bank_fee_revenue_components):
            bank_fee_revenue_ttm = np.nan

        # Use a safer bank revenue denominator. Some capital-markets banks can report
        # a narrow revenuesnetofinterestexpense value that makes fee mix / efficiency
        # ratios look impossible. The revenue base uses the largest sensible available
        # revenue measure from standardized revenue, net revenue, and identified fee revenue.
        bank_revenue_base_candidates = [
            revenue_net_interest_expense_ttm,
            latest_revenue_ttm,
            bank_fee_revenue_ttm,
        ]
        valid_bank_revenue_base_candidates = [
            _safe_number(x)
            for x in bank_revenue_base_candidates
            if pd.notna(_safe_number(x)) and _safe_number(x) > 0
        ]
        bank_revenue_base_ttm = max(valid_bank_revenue_base_candidates) if valid_bank_revenue_base_candidates else np.nan
        bank_fee_revenue_mix = _safe_divide(bank_fee_revenue_ttm, bank_revenue_base_ttm)

        deposits = _first_existing_value(lb, ["totalDeposits", "deposits", "customerDeposits", "bankDeposits"])
        if pd.isna(deposits):
            deposits = _first_existing_value(lab, ["deposits"])

        loans = _first_existing_value(
            lb,
            [
                "totalLoans", "netLoans", "loans", "loansAndLeases", "grossLoans",
                "loansHeldForInvestment", "loansReceivable", "netLoansAndLeases",
                "totalLoansAndLeases",
            ],
        )
        if pd.isna(loans):
            loans = _first_existing_value(
                lab,
                [
                    "financingreceivableexcludingaccruedinterestbeforeallowanceforcreditlossesnetofdeferredincome",
                    "financingreceivableexcludinguaccruedinterestafterallowanceforcreditlosses",
                    "financingreceivableexcludingaccruedinterestafterallowanceforcreditlosses",
                    "financingreceivableexcludinguaccruedinterestbeforeallowanceforcreditlossesnetofdeferredincome",
                    "financingreceivablesbeforeallowanceforcreditlosses",
                    "financingreceivablesafterallowanceforcreditlosses",
                    "financingreceivable",
                    "financingreceivables",
                    "loans",
                    "loansandleases",
                    "loansandleasefinancingreceivables",
                    "loansandleasesbeforeallowanceforloanlosses",
                    "loansandleasesnetofallowance",
                    "loansreceivable",
                    "loansreceivablenet",
                    "loansreceivablefairvaluedisclosure",
                    "loansheldforinvestment",
                    "loansheldforinvestmentnet",
                    "loansheldforsale",
                    "netloans",
                    "totalloans",
                    "totalloansandleases",
                    "commercialloans",
                    "consumerloans",
                    "loanstocustomers",
                    "customerloans",
                ],
            )
        loan_data_status = "Available" if pd.notna(loans) else "Not Found in Current Field Map"

        if pd.isna(latest_assets):
            latest_assets = _first_existing_value(lab, ["assets"])
        if pd.isna(latest_liabilities):
            latest_liabilities = _first_existing_value(lab, ["liabilities"])
        if pd.isna(latest_equity):
            latest_equity = _first_existing_value(lab, ["stockholdersequity"])
        if pd.isna(latest_debt):
            latest_debt = _first_existing_value(
                lab,
                ["longtermdebtandcapitalleaseobligationsincludingcurrentmaturities", "shorttermborrowings"],
            )

        risk_weighted_assets = _first_existing_value(lb, ["riskWeightedAssets"])
        cet1_capital = _first_existing_value(lb, ["commonEquityTier1Capital"])
        # Recompute balance-sheet ratios after as-reported fallback values are applied.
        debt_to_equity = _safe_divide(latest_debt, latest_equity)
        liabilities_to_assets = _safe_divide(latest_liabilities, latest_assets)
        roe = _safe_divide(latest_net_income_ttm, latest_equity)
        roa = _safe_divide(latest_net_income_ttm, latest_assets)

        tangible_common_equity = _first_existing_value(lb, ["tangibleCommonEquity"])
        if pd.isna(tangible_common_equity):
            tangible_book_value = _first_existing_value(lb, ["tangibleBookValue"])
            if pd.notna(tangible_book_value):
                tangible_common_equity = tangible_book_value
        if pd.isna(tangible_common_equity):
            goodwill = _first_existing_value(lb, ["goodwill"], default=0.0)
            intangibles = _first_existing_value(lb, ["intangibleAssets"], default=0.0)
            if pd.notna(latest_equity):
                tangible_common_equity = latest_equity - (goodwill if pd.notna(goodwill) else 0.0) - (intangibles if pd.notna(intangibles) else 0.0)

        net_interest_margin_proxy = _safe_divide(net_interest_income_ttm, latest_assets)
        efficiency_ratio = _safe_divide(noninterest_expense_ttm, bank_revenue_base_ttm)
        loan_to_deposit_ratio = _safe_divide(loans, deposits)
        provision_to_loans = _safe_divide(provision_expense_ttm, loans)
        tangible_equity_ratio = _safe_divide(tangible_common_equity, latest_assets)
        rotce_proxy = _safe_divide(latest_net_income_ttm, tangible_common_equity)
        cet1_ratio = _safe_divide(cet1_capital, risk_weighted_assets)

        deposit_growth_3y = _cagr_from_field(gb, ["totalDeposits", "deposits", "customerDeposits", "bankDeposits"])
        if pd.isna(deposit_growth_3y):
            deposit_growth_3y = _cagr_from_field(gab, ["deposits"])

        loan_growth_3y = _cagr_from_field(gb, ["totalLoans", "netLoans", "loans", "loansAndLeases", "grossLoans"])
        if pd.isna(loan_growth_3y):
            loan_growth_3y = _cagr_from_field(
                gab,
                [
                    "financingreceivableexcludingaccruedinterestbeforeallowanceforcreditlossesnetofdeferredincome",
                    "financingreceivableexcludinguaccruedinterestafterallowanceforcreditlosses",
                    "financingreceivableexcludingaccruedinterestafterallowanceforcreditlosses",
                    "financingreceivableexcludinguaccruedinterestbeforeallowanceforcreditlossesnetofdeferredincome",
                    "financingreceivablesbeforeallowanceforcreditlosses",
                    "financingreceivablesafterallowanceforcreditlosses",
                    "financingreceivable",
                    "financingreceivables",
                    "loans",
                    "loansandleases",
                    "loansandleasefinancingreceivables",
                    "loansreceivable",
                    "loansreceivablenet",
                    "loansreceivablefairvaluedisclosure",
                    "loansheldforinvestment",
                    "loansheldforinvestmentnet",
                    "netloans",
                    "totalloans",
                    "totalloansandleases",
                ],
            )

        nii_growth_3y = _cagr_from_field(gi, ["netInterestIncome_ttm"])
        if pd.isna(nii_growth_3y):
            first_ii_ar, last_ii_ar = first_last_valid(gai, "interestincomeoperating_ttm")
            first_ie_ar, last_ie_ar = first_last_valid(gai, "interestexpenseoperating_ttm")
            if first_ii_ar is not None and last_ii_ar is not None and first_ie_ar is not None and last_ie_ar is not None:
                first_nii = _safe_number(first_ii_ar.get("interestincomeoperating_ttm")) - abs(_safe_number(first_ie_ar.get("interestexpenseoperating_ttm")))
                last_nii = _safe_number(last_ii_ar.get("interestincomeoperating_ttm")) - abs(_safe_number(last_ie_ar.get("interestexpenseoperating_ttm")))
                years = max((last_ii_ar["date"] - first_ii_ar["date"]).days / 365.25, 0.25)
                nii_growth_3y = cagr(first_nii, last_nii, years)

        if pd.isna(nii_growth_3y):
            first_ii, last_ii = first_last_valid(gi, "interestIncome_ttm")
            first_ie, last_ie = first_last_valid(gi, "interestExpense_ttm")
            if first_ii is not None and last_ii is not None and first_ie is not None and last_ie is not None:
                first_nii = _safe_number(first_ii.get("interestIncome_ttm")) - abs(_safe_number(first_ie.get("interestExpense_ttm")))
                last_nii = _safe_number(last_ii.get("interestIncome_ttm")) - abs(_safe_number(last_ie.get("interestExpense_ttm")))
                years = max((last_ii["date"] - first_ii["date"]).days / 365.25, 0.25)
                nii_growth_3y = cagr(first_nii, last_nii, years)
        book_value_growth_3y = _cagr_from_field(gb, ["totalStockholdersEquity", "tangibleCommonEquity", "tangibleBookValue"])


        # -------------------------------
        # Practical sector metrics supported by current FMP sources
        # -------------------------------
        rd_expense_ttm = li.get("researchAndDevelopmentExpenses_ttm", np.nan)
        rd_to_revenue = _safe_number(_safe_series_get(
            kmrow,
            [
                "researchAndDevelopementToRevenueTTM", "researchAndDdevelopementToRevenueTTM",
                "researchAndDevelopmentToRevenueTTM", "researchAndDevelopementToRevenue",
                "researchAndDdevelopementToRevenue", "researchAndDevelopmentToRevenue",
            ],
        ))
        if pd.isna(rd_to_revenue):
            rd_to_revenue = _safe_divide(rd_expense_ttm, latest_revenue_ttm)

        stock_comp_to_revenue = _safe_number(_safe_series_get(
            kmrow,
            ["stockBasedCompensationToRevenueTTM", "stockBasedCompensationToRevenue"],
        ))
        capex_to_revenue = _safe_number(_safe_series_get(
            kmrow,
            ["capexToRevenueTTM", "capexToRevenue"],
        ))
        if pd.isna(capex_to_revenue):
            capex_to_revenue = capex_as_pct_rev

        deferred_revenue = _first_existing_value(lb, ["deferredRevenue"], default=0.0)
        deferred_revenue_noncurrent = _first_existing_value(lb, ["deferredRevenueNonCurrent"], default=0.0)
        if pd.isna(deferred_revenue) and pd.isna(deferred_revenue_noncurrent):
            deferred_revenue_total = np.nan
        else:
            deferred_revenue_total = (0.0 if pd.isna(deferred_revenue) else deferred_revenue) + (0.0 if pd.isna(deferred_revenue_noncurrent) else deferred_revenue_noncurrent)
        deferred_revenue_growth_3y = _cagr_from_field(gb, ["deferredRevenue"])

        debt_to_assets = _safe_number(_safe_series_get(rrow, ["debtToAssetsRatioTTM", "debtToAssetsRatio", "debtToAssets"]))
        if pd.isna(debt_to_assets):
            debt_to_assets = _safe_divide(latest_debt, latest_assets)
        debt_to_capital = _safe_number(_safe_series_get(rrow, ["debtToCapitalRatioTTM", "debtToCapitalRatio", "totalDebtToCapitalization"]))
        return_on_tangible_assets = _safe_number(_safe_series_get(kmrow, ["returnOnTangibleAssetsTTM", "returnOnTangibleAssets"]))
        tangible_asset_value = _safe_number(_safe_series_get(kmrow, ["tangibleAssetValueTTM", "tangibleAssetValue"]))
        tangible_book_value_per_share = _safe_number(_safe_series_get(rrow, ["tangibleBookValuePerShareTTM", "tangibleBookValuePerShare"]))
        if pd.isna(tangible_book_value_per_share):
            tangible_book_value_per_share = _safe_number(_safe_series_get(kmrow, ["tangibleBookValuePerShareTTM", "tangibleBookValuePerShare"]))

        net_interest_spread_proxy = np.nan
        if pd.notna(interest_income_ttm) and pd.notna(interest_expense_ttm):
            net_interest_spread_proxy = interest_income_ttm - abs(interest_expense_ttm)

        dividend_yield = _safe_number(_safe_series_get(rrow, ["dividendYieldTTM", "dividendYield"]))
        if pd.isna(dividend_yield):
            dividend_yield = _safe_number(_safe_series_get(prow, ["dividendYield", "lastDiv"]))
        dividend_payout_ratio = _safe_number(_safe_series_get(rrow, ["dividendPayoutRatioTTM", "payoutRatioTTM", "payoutRatio"]))
        debt_service_coverage = _safe_number(_safe_series_get(rrow, ["debtServiceCoverageRatioTTM", "debtServiceCoverageRatio"]))
        net_debt_to_ebitda = _safe_number(_safe_series_get(kmrow, ["netDebtToEBITDATTM", "netDebtToEBITDA"]))
        ev_to_ebitda = _safe_number(_safe_series_get(kmrow, ["enterpriseValueOverEBITDATTM", "evToEBITDATTM", "evToEBITDA"]))
        if pd.isna(ev_to_ebitda) and pd.notna(enterprise_value) and pd.notna(li.get("ebitda_ttm", np.nan)) and li.get("ebitda_ttm", np.nan) != 0:
            ev_to_ebitda = enterprise_value / li.get("ebitda_ttm", np.nan)

        ev_to_sales = _safe_number(_safe_series_get(kmrow, ["evToSalesTTM", "enterpriseValueOverRevenueTTM", "enterpriseValueOverSalesTTM", "evToSales"]))
        if pd.isna(ev_to_sales) and pd.notna(enterprise_value) and pd.notna(latest_revenue_ttm) and latest_revenue_ttm != 0:
            ev_to_sales = enterprise_value / latest_revenue_ttm

        ev_to_fcf = _safe_number(_safe_series_get(kmrow, ["evToFreeCashFlowTTM", "enterpriseValueOverFreeCashFlowTTM", "evToFCFTTM", "evToFCF"]))
        if pd.isna(ev_to_fcf) and pd.notna(enterprise_value) and pd.notna(latest_fcf_ttm) and latest_fcf_ttm != 0:
            ev_to_fcf = enterprise_value / latest_fcf_ttm

        roic = _safe_number(_safe_series_get(kmrow, ["returnOnInvestedCapitalTTM", "roicTTM", "returnOnCapitalEmployedTTM", "returnOnInvestedCapital"]))
        income_quality = _safe_number(_safe_series_get(kmrow, ["incomeQualityTTM", "incomeQuality"]))
        inventory_days = _safe_number(_safe_series_get(kmrow, ["daysOfInventoryOutstandingTTM", "daysOfInventoryOutstanding", "inventoryDaysTTM"]))
        cash_conversion_cycle_days = _safe_number(_safe_series_get(kmrow, ["cashConversionCycleTTM", "cashConversionCycle"]))
        days_sales_outstanding = _safe_number(_safe_series_get(kmrow, ["daysOfSalesOutstandingTTM", "daysOfSalesOutstanding"]))
        days_payables_outstanding = _safe_number(_safe_series_get(kmrow, ["daysOfPayablesOutstandingTTM", "daysOfPayablesOutstanding"]))

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
            "Analyst Rating": analyst_rating,
            "Rating Score": overall_score,
            "Net Interest Income TTM": net_interest_income_ttm,
            "Net Interest Margin Proxy": net_interest_margin_proxy,
            "Net Interest Income Growth 3Y": nii_growth_3y,
            "Interest Income TTM": interest_income_ttm,
            "Interest Expense TTM": interest_expense_ttm,
            "Noninterest Income TTM": noninterest_income_ttm,
            "Revenue Net of Interest Expense TTM": revenue_net_interest_expense_ttm,
            "Bank Revenue Base TTM": bank_revenue_base_ttm,
            "Bank Fee Revenue TTM": bank_fee_revenue_ttm,
            "Bank Fee Revenue Mix": bank_fee_revenue_mix,
            "Investment Banking Revenue TTM": investment_banking_revenue_ttm,
            "Trading Revenue TTM": trading_revenue_ttm,
            "Asset Management Fees TTM": asset_management_fees_ttm,
            "Fees and Commissions TTM": fees_and_commissions_ttm,
            "Lending and Deposit Fees TTM": lending_deposit_fees_ttm,
            "Card Fees TTM": card_fees_ttm,
            "Mortgage Fees TTM": mortgage_fees_ttm,
            "Efficiency Ratio": efficiency_ratio,
            "Provision Expense TTM": provision_expense_ttm,
            "Provision / Loans": provision_to_loans,
            "Deposits": deposits,
            "Deposit Growth 3Y": deposit_growth_3y,
            "Loans": loans,
            "Loan Data Status": loan_data_status,
            "Loan Growth 3Y": loan_growth_3y,
            "Loan-to-Deposit Ratio": loan_to_deposit_ratio,
            "Tangible Common Equity": tangible_common_equity,
            "Tangible Equity / Assets": tangible_equity_ratio,
            "ROTCE Proxy": rotce_proxy,
            "CET1 Ratio": cet1_ratio,
            "Book Value Growth 3Y": book_value_growth_3y,
            "R&D as % Revenue": rd_to_revenue,
            "R&D Expense TTM": rd_expense_ttm,
            "Deferred Revenue": deferred_revenue_total,
            "Deferred Revenue Growth 3Y": deferred_revenue_growth_3y,
            "Stock-Based Comp % Revenue": stock_comp_to_revenue,
            "Capex to Revenue": capex_to_revenue,
            "Debt / Assets": debt_to_assets,
            "Debt / Capital": debt_to_capital,
            "Return on Tangible Assets": return_on_tangible_assets,
            "Tangible Asset Value": tangible_asset_value,
            "Tangible Book Value / Share": tangible_book_value_per_share,
            "Net Interest Spread Proxy": net_interest_spread_proxy,
            "Dividend Yield": dividend_yield,
            "Dividend Payout Ratio": dividend_payout_ratio,
            "Debt Service Coverage": debt_service_coverage,
            "Net Debt / EBITDA": net_debt_to_ebitda,
            "EV / EBITDA": ev_to_ebitda,
            "EV / Sales": ev_to_sales,
            "EV / FCF": ev_to_fcf,
            "ROIC": roic,
            "Income Quality": income_quality,
            "Inventory Days": inventory_days,
            "Cash Conversion Cycle Days": cash_conversion_cycle_days,
            "Days Sales Outstanding": days_sales_outstanding,
            "Days Payables Outstanding": days_payables_outstanding,
        })

    scorecard = pd.DataFrame(rows)

    positive_rank_cols = [
        "Revenue CAGR 3Y", "Net Income CAGR 3Y", "FCF CAGR 3Y",
        "Latest Operating Margin", "Latest Net Margin",
        "FCF Margin", "Cash Conversion", "Current Ratio", "ROE", "ROA",
        "Earnings Yield", "FCF Yield", "Forward Revenue Growth FY+1", "Rating Score",
        "Net Interest Income Growth 3Y", "Deposit Growth 3Y", "Loan Growth 3Y",
        "Tangible Equity / Assets", "ROTCE Proxy", "Book Value Growth 3Y", "Bank Fee Revenue Mix",
        "ROIC", "Income Quality"
    ]
    negative_rank_cols = [
        "Debt to Equity", "Liabilities to Assets",
        "P/E TTM", "P/B TTM", "P/S TTM", "P/FCF TTM",
        "Forward P/E", "Forward P/S", "EV / Sales", "EV / FCF", "Efficiency Ratio",
        "Provision / Loans", "Loan-to-Deposit Ratio", "Inventory Days", "Cash Conversion Cycle Days"
    ]

    internal_rank_cols = []

    for c in positive_rank_cols:
        rank_col = f"__rank_{c}"

        if c in scorecard.columns:
            scorecard[c] = pd.to_numeric(scorecard[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
            scorecard[rank_col] = safe_rank_series(scorecard[c], ascending=True)
        else:
            scorecard[rank_col] = np.nan

        internal_rank_cols.append(rank_col)

    for c in negative_rank_cols:
        rank_col = f"__rank_{c}"

        if c in scorecard.columns:
            scorecard[c] = pd.to_numeric(scorecard[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
            scorecard[rank_col] = safe_rank_series(scorecard[c], ascending=False)
        else:
            scorecard[rank_col] = np.nan

        internal_rank_cols.append(rank_col)

    weighted_rank_map = {
        "__rank_Revenue CAGR 3Y": 0.12,
        "__rank_Net Income CAGR 3Y": 0.12,
        "__rank_FCF CAGR 3Y": 0.11,
        "__rank_Latest Operating Margin": 0.08,
        "__rank_Latest Net Margin": 0.05,
        "__rank_FCF Margin": 0.06,
        "__rank_Cash Conversion": 0.03,
        "__rank_ROA": 0.03,
        "__rank_Current Ratio": 0.04,
        "__rank_Debt to Equity": 0.05,
        "__rank_Liabilities to Assets": 0.03,
        "__rank_ROE": 0.03,
        "__rank_P/E TTM": 0.03,
        "__rank_P/B TTM": 0.02,
        "__rank_P/S TTM": 0.03,
        "__rank_P/FCF TTM": 0.03,
        "__rank_Forward P/E": 0.02,
        "__rank_Forward P/S": 0.02,
        "__rank_Earnings Yield": 0.02,
        "__rank_FCF Yield": 0.02,
        "__rank_Forward Revenue Growth FY+1": 0.03,
        "__rank_Rating Score": 0.03,
        "__rank_ROIC": 0.02,
        "__rank_Income Quality": 0.02,
        "__rank_EV / Sales": 0.02,
        "__rank_EV / FCF": 0.02,
    }

    scorecard["Composite Score"] = scorecard.apply(lambda row: weighted_average_available(row, weighted_rank_map), axis=1)
    scorecard = scorecard.drop(columns=internal_rank_cols, errors="ignore")

    return scorecard.sort_values("Composite Score", ascending=False).reset_index(drop=True)


# =========================================================
# TECHNICAL SCORECARD
# =========================================================
def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi



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
    atr = true_range.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    return atr



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

    numeric_cols = ["open", "high", "low", "close", "adjClose", "volume"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.sort_values("date").reset_index(drop=True)
    return df



def fetch_all_price_history(symbols: List[str], api_key: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    out = {}
    for sym in symbols:
        try:
            df = fetch_price_history(sym, api_key=api_key, from_date=from_date, to_date=to_date)
            out[sym] = df
        except Exception as e:
            st.error(f"{sym} technical fetch failed: {e}")
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
        "SMA 50": sma50,
        "SMA 200": sma200,
        "% From SMA 50": pct_from_sma50,
        "% From SMA 200": pct_from_sma200,
        "ATR 14": latest.get("ATR 14", np.nan),
        "Volume": latest.get("volume", np.nan),
        "20D Avg Volume": vol20,
        "Volume vs 20D Avg": volume_vs_20d,
    }



def build_technical_scorecard(symbols: List[str], api_key: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> pd.DataFrame:
    history = fetch_all_price_history(symbols, api_key=api_key, from_date=from_date, to_date=to_date)
    rows = []

    for sym, df in history.items():
        if not df.empty:
            rows.append(summarize_technicals(df))
        else:
            st.warning(f"{sym}: no price history returned, so technicals were skipped.")

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
        return add_equity_research_decision_layer(f)

    combined = f.merge(t, on="Ticker", how="left")

    if {"Price Target Consensus", "Close"}.issubset(combined.columns):
        combined["Price Target Upside"] = np.where(
            combined["Close"].notna() & (combined["Close"] != 0) & combined["Price Target Consensus"].notna(),
            (combined["Price Target Consensus"] - combined["Close"]) / combined["Close"],
            np.nan,
        )
    else:
        combined["Price Target Upside"] = np.nan

    # Version 2 decision layer: add score buckets and analyst labels after
    # fundamentals, market intelligence, and technical data have been merged.
    return add_equity_research_decision_layer(combined)



# =========================================================
# EQUITY RESEARCH DECISION LAYER - VERSION 5
# TRUE SECTOR-AWARE METRIC REGISTRY + COVERAGE FILTERING
# =========================================================
# Paste this block over your current sector-aware decision-layer section.
#
# Recommended replacement range:
#   Replace from:
#       # =========================================================
#       # EQUITY RESEARCH DECISION LAYER ...
#   Through the end of:
#       build_sector_methodology_table()
#
# This block keeps the same public function names used elsewhere:
#   - SECTOR_PEER_GROUPS
#   - get_sector_config()
#   - get_report_sections()
#   - build_sector_methodology_table()
#   - add_equity_research_decision_layer()
#   - _build_research_ranking_table()
#
# New helpers added:
#   - build_sector_metric_coverage_table()
#   - build_sector_missing_metric_table()
#   - build_sector_analysis_input_table()
#   - build_sector_analysis_prompt()
#   - render_sector_metric_coverage_audit()
#
# Usage in Streamlit:
#   After combined_scorecard is built and peer_group is selected:
#
#       coverage_df = build_sector_metric_coverage_table(combined_scorecard, peer_group)
#       st.dataframe(make_display_df(coverage_df), use_container_width=True, hide_index=True)
#
# Or simply:
#
#       render_sector_metric_coverage_audit(combined_scorecard, peer_group)
#
# =========================================================


# ---------------------------------------------------------
# Peer groups
# ---------------------------------------------------------
SECTOR_PEER_GROUPS = [
    "General / Cross-Sector",
    "Technology / Software / Semis",
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Consumer",
    "Healthcare",
    "Banks / Financials",
    "Industrials",
    "Energy",
    "Materials",
    "Utilities",
    "Real Estate / REITs",
]


# ---------------------------------------------------------
# Core technical score weights
# ---------------------------------------------------------
TECHNICAL_BUCKET_WEIGHTS = {
    "YTD Return": (0.10, True),
    "1Y Return": (0.20, True),
    "3Y Return (Price)": (0.12, True),
    "% From SMA 50": (0.18, True),
    "% From SMA 200": (0.22, True),
    "% Below 52W High": (0.10, True),
    "Volume vs 20D Avg": (0.08, True),
}


# ---------------------------------------------------------
# Default cross-sector scoring framework
# ---------------------------------------------------------
DEFAULT_BUCKET_DEFINITIONS = {
    "Quality Score": {
        "Latest Operating Margin": (0.20, True),
        "Latest Net Margin": (0.16, True),
        "ROE": (0.16, True),
        "ROA": (0.14, True),
        "FCF Margin": (0.18, True),
        "Cash Conversion": (0.16, True),
    },
    "Growth Score": {
        "Revenue CAGR 3Y": (0.30, True),
        "Net Income CAGR 3Y": (0.22, True),
        "FCF CAGR 3Y": (0.22, True),
        "Forward Revenue Growth FY+1": (0.26, True),
    },
    "Profitability Score": {
        "Latest Gross Margin": (0.20, True),
        "Latest Operating Margin": (0.30, True),
        "Latest EBITDA Margin": (0.20, True),
        "Latest Net Margin": (0.30, True),
    },
    "Cash Flow Score": {
        "OCF Margin": (0.24, True),
        "FCF Margin": (0.28, True),
        "Cash Conversion": (0.20, True),
        "FCF Yield": (0.18, True),
        "FCF CAGR 3Y": (0.10, True),
    },
    "Balance Sheet Score": {
        "Current Ratio": (0.25, True),
        "Debt to Equity": (0.30, False),
        "Liabilities to Assets": (0.25, False),
        "Cash / ST Investments": (0.20, True),
    },
    "Valuation Score": {
        "P/E TTM": (0.14, False),
        "P/B TTM": (0.08, False),
        "P/S TTM": (0.10, False),
        "P/FCF TTM": (0.16, False),
        "Forward P/E": (0.16, False),
        "Forward P/S": (0.10, False),
        "Earnings Yield": (0.10, True),
        "FCF Yield": (0.16, True),
    },
    "Forward Expectations Score": {
        "Forward Revenue Growth FY+1": (0.38, True),
        "Forward EPS Next FY": (0.20, True),
        "Forward EBITDA Next FY": (0.14, True),
        "Forward Net Income Next FY": (0.14, True),
        "Price Target Upside": (0.14, True),
    },
    "Technical Score": TECHNICAL_BUCKET_WEIGHTS,
    "Analyst Sentiment Score": {
        "Price Target Upside": (0.60, True),
        "Rating Score": (0.40, True),
    },
}


DEFAULT_FINAL_WEIGHTS = {
    "Quality Score": 0.16,
    "Growth Score": 0.16,
    "Profitability Score": 0.12,
    "Cash Flow Score": 0.14,
    "Balance Sheet Score": 0.10,
    "Valuation Score": 0.14,
    "Forward Expectations Score": 0.08,
    "Technical Score": 0.06,
    "Analyst Sentiment Score": 0.04,
}


DEFAULT_REPORT_SECTIONS = {
    "Executive Snapshot": [
        "Final Rank", "Research View", "Final Research Score", "Best Attribute", "Biggest Weakness",
        "Valuation Label", "Technical Signal", "Price Target Upside", "Market Cap",
        "Price Target Consensus", "Analyst Rating",
    ],
    "Growth": [
        "Revenue CAGR 3Y", "Net Income CAGR 3Y", "FCF CAGR 3Y", "Forward Revenue Growth FY+1",
    ],
    "Margins": [
        "Latest Gross Margin", "Latest Operating Margin", "Latest EBITDA Margin", "Latest Net Margin",
    ],
    "Returns on Capital": [
        "ROE", "ROA", "Earnings Yield", "FCF Yield",
    ],
    "Cash Flow Quality": [
        "Latest OCF TTM", "Latest FCF TTM", "OCF Margin", "FCF Margin", "Cash Conversion",
    ],
    "Balance Sheet": [
        "Cash / ST Investments", "Total Debt", "Current Ratio", "Debt to Equity", "Liabilities to Assets",
    ],
    "Valuation Multiples": [
        "P/E TTM", "P/B TTM", "P/S TTM", "P/FCF TTM", "Forward P/E", "Forward P/S",
    ],
    "Forward Expectations": [
        "Forward Revenue Next FY", "Forward EPS Next FY", "Forward EBITDA Next FY", "Forward Net Income Next FY",
    ],
    "Price Performance": [
        "YTD Return", "1Y Return", "3Y Return (Price)", "5Y Return (Price)",
    ],
    "Trend Positioning": [
        "% Below 52W High", "% Above 52W Low", "% From SMA 50", "% From SMA 200",
    ],
    "Momentum / Trading": [
        "RSI 14", "MACD Line", "MACD Signal", "ATR 14", "Volume vs 20D Avg",
    ],
}


# ---------------------------------------------------------
# Sector metric registry
# This is the new source of truth.
# ---------------------------------------------------------
SECTOR_METRIC_REGISTRY = {
    "General / Cross-Sector": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest Operating Margin", "ROE", "ROA",
            "FCF CAGR 3Y", "Debt to Equity",
            "Forward P/E", "Forward P/S", "Price Target Upside",
            "YTD Return", "1Y Return", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "Net Income CAGR 3Y", "Latest Gross Margin", "Latest EBITDA Margin",
            "FCF Yield", "Cash Conversion", "P/E TTM", "P/S TTM", "P/FCF TTM",
            "EV / EBITDA", "Rating Score", "% From SMA 50",
        ],
        "avoid_or_downweight": [],
        "missing_but_useful": [],
    },

    "Technology / Software / Semis": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest Gross Margin", "Latest Operating Margin",
            "FCF CAGR 3Y", "R&D as % Revenue", "Capex to Revenue",
            "Forward P/S", "Forward P/E", "P/S TTM", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "ROIC", "Income Quality", "Stock-Based Comp % Revenue", "FCF Yield",
            "P/FCF TTM", "EV / Sales", "EV / FCF", "Rating Score", "1Y Return",
        ],
        "avoid_or_downweight": [
            "P/B TTM", "Dividend Yield", "Loan-to-Deposit Ratio", "Provision / Loans", "CET1 Ratio",
        ],
        "missing_but_useful": [
            "ARR", "Net Revenue Retention", "Cloud Backlog", "Customer Churn", "Segment Revenue Growth",
        ],
    },

    "Communication Services": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest EBITDA Margin", "Latest Operating Margin",
            "FCF CAGR 3Y", "Capex to Revenue",
            "Forward P/E", "Forward P/S", "P/S TTM", "EV / EBITDA", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "FCF Yield", "Cash Conversion", "Net Debt / EBITDA", "ROA", "ROE", "EV / Sales", "EV / FCF", "1Y Return",
        ],
        "avoid_or_downweight": ["P/B TTM", "Current Ratio"],
        "missing_but_useful": ["ARPU", "Subscriber Growth", "Churn", "Ad Revenue Growth", "Content Spend"],
    },

    "Consumer Discretionary": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest Gross Margin", "Latest Operating Margin", "FCF CAGR 3Y",
            "Forward P/E", "Forward P/S", "P/E TTM", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "P/S TTM", "FCF Yield", "Cash Conversion", "ROA", "ROE", "Inventory Days", "Cash Conversion Cycle Days",
            "Debt to Equity", "1Y Return",
        ],
        "avoid_or_downweight": ["P/B TTM", "R&D as % Revenue"],
        "missing_but_useful": ["Same Store Sales Growth", "Traffic Growth", "Average Ticket", "Store Count"],
    },

    "Consumer Staples": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest Gross Margin", "Latest Operating Margin", "FCF CAGR 3Y",
            "Forward P/E", "P/E TTM", "Dividend Yield", "Dividend Payout Ratio", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "FCF Yield", "Cash Conversion", "ROA", "ROE", "Debt to Equity", "Inventory Days", "Cash Conversion Cycle Days", "1Y Return",
        ],
        "avoid_or_downweight": ["P/B TTM", "R&D as % Revenue", "Forward P/S"],
        "missing_but_useful": ["Organic Sales Growth", "Volume Growth", "Pricing Growth", "Retail Scanner Data"],
    },

    "Consumer": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest Gross Margin", "Latest Operating Margin", "FCF CAGR 3Y",
            "Forward P/E", "Forward P/S", "P/E TTM", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "P/S TTM", "FCF Yield", "Cash Conversion", "Dividend Yield", "Dividend Payout Ratio",
            "Inventory Days", "Cash Conversion Cycle Days", "ROA", "ROE", "1Y Return",
        ],
        "avoid_or_downweight": ["R&D as % Revenue", "P/B TTM"],
        "missing_but_useful": ["Same Store Sales Growth", "Traffic Growth", "Average Ticket", "Store Count"],
    },

    "Healthcare": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest Gross Margin", "Latest Operating Margin", "Latest Net Margin",
            "FCF CAGR 3Y", "R&D as % Revenue", "Forward P/E", "Forward P/S", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "P/S TTM", "FCF Yield", "Cash Conversion", "Debt to Equity", "ROA", "ROE", "ROIC", "1Y Return",
        ],
        "avoid_or_downweight": ["P/B TTM", "Dividend Yield"],
        "missing_but_useful": ["Pipeline Stage Data", "Patent Cliff Exposure", "Drug-Level Revenue", "Medical Loss Ratio"],
    },

    "Banks / Financials": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward EPS Next FY",
            "P/B TTM", "ROE", "ROA", "Book Value / Share", "Book Value Growth 3Y",
            "P/E TTM", "Forward P/E", "Earnings Yield", "Dividend Yield", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "Latest Net Margin", "Debt / Assets", "Debt / Capital", "Liabilities to Assets",
            "Net Interest Margin Proxy", "Efficiency Ratio", "Bank Fee Revenue Mix", "Rating Score", "1Y Return",
        ],
        "avoid_or_downweight": [
            "Latest Gross Margin", "Latest EBITDA Margin", "FCF Margin", "FCF CAGR 3Y", "P/FCF TTM", "Current Ratio",
            "R&D as % Revenue", "Stock-Based Comp % Revenue", "CET1 Ratio", "Provision / Loans", "Forward P/S",
        ],
        "missing_but_useful": ["CET1 Ratio", "Risk-Weighted Assets", "Net Charge-Offs", "True Net Interest Margin"],
    },

    "Industrials": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest EBITDA Margin", "Latest Operating Margin", "FCF CAGR 3Y", "Capex to Revenue",
            "Net Debt / EBITDA", "EV / EBITDA", "Forward P/E", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "ROIC", "ROA", "ROE", "Debt / Capital", "FCF Yield", "EV / FCF", "Cash Conversion", "1Y Return",
        ],
        "avoid_or_downweight": ["P/S TTM", "R&D as % Revenue", "P/B TTM"],
        "missing_but_useful": ["Backlog", "Book-to-Bill", "Order Growth", "Organic Growth", "Segment Margin"],
    },

    "Energy": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest EBITDA Margin", "Latest Operating Margin", "FCF Yield", "EV / EBITDA",
            "Net Debt / EBITDA", "Forward P/E", "Dividend Yield", "Dividend Payout Ratio", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "FCF CAGR 3Y", "Capex to Revenue", "Debt / Capital", "Debt / Assets", "EV / FCF", "1Y Return",
        ],
        "avoid_or_downweight": ["R&D as % Revenue", "P/B TTM", "Current Ratio", "Forward P/S"],
        "missing_but_useful": ["Production Growth", "Reserve Replacement Ratio", "Proved Reserves", "Realized Oil/Gas Pricing"],
    },

    "Materials": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Latest Gross Margin", "Latest EBITDA Margin", "Latest Operating Margin", "FCF CAGR 3Y",
            "EV / EBITDA", "Forward P/E", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "FCF Yield", "Capex to Revenue", "Net Debt / EBITDA", "Debt / Capital", "ROIC", "ROA", "ROE", "EV / FCF", "1Y Return",
        ],
        "avoid_or_downweight": ["R&D as % Revenue", "P/B TTM", "Forward P/S"],
        "missing_but_useful": ["Volume Growth", "Commodity Exposure", "Input Cost Inflation", "Capacity Utilization"],
    },

    "Utilities": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward EPS Next FY",
            "Dividend Yield", "Dividend Payout Ratio", "Debt / Capital", "Debt / Assets", "Debt Service Coverage",
            "Forward P/E", "P/B TTM", "Latest Net Margin", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "Earnings Yield", "ROE", "ROA", "Net Debt / EBITDA", "1Y Return",
        ],
        "avoid_or_downweight": ["R&D as % Revenue", "P/S TTM", "Forward P/S", "High Growth Metrics"],
        "missing_but_useful": ["Rate Base Growth", "Allowed ROE", "Regulated Earnings Mix", "Capex Plan"],
    },

    "Real Estate / REITs": {
        "must_have": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY",
            "Dividend Yield", "Dividend Payout Ratio", "Debt / Assets", "Debt / Capital", "Net Debt / EBITDA",
            "P/B TTM", "Forward P/E", "Price Target Upside",
            "% From SMA 50", "% From SMA 200", "RSI 14",
        ],
        "preferred": [
            "Book Value / Share", "Tangible Book Value / Share", "Latest Net Margin", "Debt Service Coverage", "1Y Return",
        ],
        "avoid_or_downweight": ["P/E TTM", "P/FCF TTM", "Latest Gross Margin", "R&D as % Revenue", "Current Ratio", "Forward P/S"],
        "missing_but_useful": ["FFO", "AFFO", "AFFO Payout Ratio", "Occupancy Rate", "Same Store NOI Growth"],
    },
}


# ---------------------------------------------------------
# Sector-specific scoring configs
# High-level sector frameworks that prioritize reliable, broadly available data.
# ---------------------------------------------------------
def _merge_config(base: dict, updates: dict) -> dict:
    merged = dict(base)
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            inner = dict(merged[k])
            inner.update(v)
            merged[k] = inner
        else:
            merged[k] = v
    return merged


SECTOR_CONFIGS = {
    "General / Cross-Sector": {
        "description": "Balanced cross-sector framework emphasizing revenue growth, forward estimates, forward valuation where applicable, cash-flow compounding, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Growth Score": {
                "Revenue CAGR 3Y": (0.28, True),
                "Forward Revenue Growth FY+1": (0.28, True),
                "FCF CAGR 3Y": (0.18, True),
                "Net Income CAGR 3Y": (0.16, True),
                "Forward EPS Next FY": (0.10, True),
            },
            "Valuation Score": {
                "Forward P/E": (0.18, False),
                "Forward P/S": (0.12, False),
                "P/E TTM": (0.12, False),
                "P/S TTM": (0.10, False),
                "P/FCF TTM": (0.14, False),
                "FCF Yield": (0.14, True),
                "Price Target Upside": (0.20, True),
            },
        }),
        "final_weights": DEFAULT_FINAL_WEIGHTS,
        "report_sections": DEFAULT_REPORT_SECTIONS,
    },

    "Technology / Software / Semis": {
        "description": "Tech framework focused on revenue growth, forward estimates, gross/operating margin, 3Y FCF CAGR instead of FCF margin, R&D/capex intensity, forward P/S, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Gross Margin": (0.22, True),
                "Latest Operating Margin": (0.20, True),
                "ROIC": (0.14, True),
                "Income Quality": (0.12, True),
                "R&D as % Revenue": (0.12, True),
                "Capex to Revenue": (0.10, False),
                "Stock-Based Comp % Revenue": (0.10, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.30, True),
                "Forward Revenue Growth FY+1": (0.30, True),
                "FCF CAGR 3Y": (0.24, True),
                "Forward EPS Next FY": (0.10, True),
                "Net Income CAGR 3Y": (0.06, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.36, True),
                "FCF Yield": (0.20, True),
                "Cash Conversion": (0.18, True),
                "Capex to Revenue": (0.16, False),
                "Income Quality": (0.10, True),
            },
            "Valuation Score": {
                "Forward P/S": (0.22, False),
                "P/S TTM": (0.14, False),
                "Forward P/E": (0.16, False),
                "P/FCF TTM": (0.14, False),
                "EV / Sales": (0.12, False),
                "EV / FCF": (0.10, False),
                "Price Target Upside": (0.12, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.20,
            "Growth Score": 0.24,
            "Profitability Score": 0.08,
            "Cash Flow Score": 0.16,
            "Balance Sheet Score": 0.05,
            "Valuation Score": 0.15,
            "Forward Expectations Score": 0.05,
            "Technical Score": 0.05,
            "Analyst Sentiment Score": 0.02,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / Quality": ["Latest Gross Margin", "Latest Operating Margin", "ROIC", "Income Quality"],
            "Tech Investment Intensity": ["R&D as % Revenue", "Capex to Revenue", "Stock-Based Comp % Revenue"],
            "Valuation": ["Forward P/S", "P/S TTM", "Forward P/E", "P/FCF TTM", "EV / Sales", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Communication Services": {
        "description": "Communication services framework using revenue growth, forward estimates, EBITDA/operating margin, 3Y FCF CAGR, capex intensity, forward valuation, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest EBITDA Margin": (0.22, True),
                "Latest Operating Margin": (0.22, True),
                "Cash Conversion": (0.16, True),
                "ROIC": (0.14, True),
                "Net Debt / EBITDA": (0.14, False),
                "Capex to Revenue": (0.12, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.30, True),
                "Forward Revenue Growth FY+1": (0.30, True),
                "FCF CAGR 3Y": (0.18, True),
                "Net Income CAGR 3Y": (0.12, True),
                "Forward EBITDA Next FY": (0.10, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.28, True),
                "FCF Yield": (0.24, True),
                "Cash Conversion": (0.22, True),
                "Capex to Revenue": (0.16, False),
                "Net Debt / EBITDA": (0.10, False),
            },
            "Valuation Score": {
                "Forward P/S": (0.16, False),
                "P/S TTM": (0.12, False),
                "Forward P/E": (0.18, False),
                "EV / EBITDA": (0.16, False),
                "P/FCF TTM": (0.14, False),
                "FCF Yield": (0.10, True),
                "Price Target Upside": (0.14, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.18,
            "Growth Score": 0.20,
            "Profitability Score": 0.08,
            "Cash Flow Score": 0.17,
            "Balance Sheet Score": 0.08,
            "Valuation Score": 0.17,
            "Forward Expectations Score": 0.05,
            "Technical Score": 0.05,
            "Analyst Sentiment Score": 0.02,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "Forward EBITDA Next FY", "FCF CAGR 3Y"],
            "Margins / Cash Flow": ["Latest EBITDA Margin", "Latest Operating Margin", "FCF Yield", "Cash Conversion", "Capex to Revenue"],
            "Leverage / Returns": ["Net Debt / EBITDA", "ROIC", "ROA", "ROE"],
            "Valuation": ["Forward P/S", "P/S TTM", "Forward P/E", "EV / EBITDA", "P/FCF TTM", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Consumer Discretionary": {
        "description": "Product/consumer growth framework using revenue growth, forward estimates, gross/operating margin, 3Y FCF CAGR instead of FCF margin, inventory/cash-cycle checks, forward valuation, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Gross Margin": (0.22, True),
                "Latest Operating Margin": (0.22, True),
                "ROA": (0.14, True),
                "ROE": (0.12, True),
                "Cash Conversion": (0.12, True),
                "Inventory Days": (0.10, False),
                "Cash Conversion Cycle Days": (0.08, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.30, True),
                "Forward Revenue Growth FY+1": (0.30, True),
                "FCF CAGR 3Y": (0.20, True),
                "Net Income CAGR 3Y": (0.12, True),
                "Forward EPS Next FY": (0.08, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.34, True),
                "FCF Yield": (0.22, True),
                "Cash Conversion": (0.20, True),
                "Inventory Days": (0.12, False),
                "Cash Conversion Cycle Days": (0.12, False),
            },
            "Valuation Score": {
                "Forward P/E": (0.22, False),
                "P/E TTM": (0.14, False),
                "Forward P/S": (0.14, False),
                "P/S TTM": (0.10, False),
                "P/FCF TTM": (0.14, False),
                "FCF Yield": (0.10, True),
                "Price Target Upside": (0.16, True),
            },
        }),
        "final_weights": DEFAULT_FINAL_WEIGHTS,
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / Product Economics": ["Latest Gross Margin", "Latest Operating Margin", "ROA", "ROE"],
            "Cash Flow / Working Capital": ["FCF Yield", "Cash Conversion", "Inventory Days", "Cash Conversion Cycle Days"],
            "Valuation": ["Forward P/E", "P/E TTM", "Forward P/S", "P/S TTM", "P/FCF TTM", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Consumer Staples": {
        "description": "Defensive consumer framework using revenue growth, forward estimates, gross/operating margin, 3Y FCF CAGR, dividend quality, forward P/E, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Gross Margin": (0.22, True),
                "Latest Operating Margin": (0.22, True),
                "ROA": (0.14, True),
                "ROE": (0.14, True),
                "Cash Conversion": (0.14, True),
                "Debt to Equity": (0.14, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.28, True),
                "Forward Revenue Growth FY+1": (0.28, True),
                "FCF CAGR 3Y": (0.20, True),
                "Net Income CAGR 3Y": (0.14, True),
                "Forward EPS Next FY": (0.10, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.30, True),
                "FCF Yield": (0.22, True),
                "Cash Conversion": (0.20, True),
                "Dividend Yield": (0.14, True),
                "Dividend Payout Ratio": (0.14, False),
            },
            "Valuation Score": {
                "Forward P/E": (0.24, False),
                "P/E TTM": (0.18, False),
                "FCF Yield": (0.14, True),
                "Dividend Yield": (0.12, True),
                "Dividend Payout Ratio": (0.12, False),
                "Price Target Upside": (0.20, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.18,
            "Growth Score": 0.16,
            "Profitability Score": 0.10,
            "Cash Flow Score": 0.16,
            "Balance Sheet Score": 0.10,
            "Valuation Score": 0.16,
            "Forward Expectations Score": 0.06,
            "Technical Score": 0.05,
            "Analyst Sentiment Score": 0.03,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / Quality": ["Latest Gross Margin", "Latest Operating Margin", "ROA", "ROE", "Cash Conversion"],
            "Dividend / Balance Sheet": ["Dividend Yield", "Dividend Payout Ratio", "Debt to Equity", "Debt / Assets"],
            "Valuation": ["Forward P/E", "P/E TTM", "FCF Yield", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Consumer": {
        "description": "Combined consumer framework for mixed peer sets. Uses revenue growth, forward estimates, gross/operating margin, 3Y FCF CAGR, forward valuation, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Gross Margin": (0.22, True),
                "Latest Operating Margin": (0.22, True),
                "ROA": (0.14, True),
                "ROE": (0.12, True),
                "Cash Conversion": (0.14, True),
                "Inventory Days": (0.08, False),
                "Cash Conversion Cycle Days": (0.08, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.30, True),
                "Forward Revenue Growth FY+1": (0.30, True),
                "FCF CAGR 3Y": (0.20, True),
                "Net Income CAGR 3Y": (0.12, True),
                "Forward EPS Next FY": (0.08, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.32, True),
                "FCF Yield": (0.20, True),
                "Cash Conversion": (0.20, True),
                "Dividend Yield": (0.12, True),
                "Inventory Days": (0.08, False),
                "Cash Conversion Cycle Days": (0.08, False),
            },
            "Valuation Score": {
                "Forward P/E": (0.22, False),
                "P/E TTM": (0.14, False),
                "Forward P/S": (0.12, False),
                "P/S TTM": (0.10, False),
                "P/FCF TTM": (0.14, False),
                "FCF Yield": (0.10, True),
                "Price Target Upside": (0.18, True),
            },
        }),
        "final_weights": DEFAULT_FINAL_WEIGHTS,
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / Quality": ["Latest Gross Margin", "Latest Operating Margin", "ROA", "ROE", "Cash Conversion"],
            "Cash Flow / Working Capital": ["FCF Yield", "Dividend Yield", "Inventory Days", "Cash Conversion Cycle Days"],
            "Valuation": ["Forward P/E", "P/E TTM", "Forward P/S", "P/S TTM", "P/FCF TTM", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Healthcare": {
        "description": "Healthcare framework using revenue growth, forward estimates, margins, R&D intensity, 3Y FCF CAGR, forward P/E/P/S where applicable, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Gross Margin": (0.20, True),
                "Latest Operating Margin": (0.20, True),
                "Latest Net Margin": (0.16, True),
                "R&D as % Revenue": (0.14, True),
                "ROIC": (0.12, True),
                "ROA": (0.10, True),
                "Debt to Equity": (0.08, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.30, True),
                "Forward Revenue Growth FY+1": (0.30, True),
                "FCF CAGR 3Y": (0.18, True),
                "Net Income CAGR 3Y": (0.12, True),
                "Forward EPS Next FY": (0.10, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.30, True),
                "FCF Yield": (0.24, True),
                "Cash Conversion": (0.22, True),
                "Income Quality": (0.14, True),
                "Debt to Equity": (0.10, False),
            },
            "Valuation Score": {
                "Forward P/E": (0.24, False),
                "Forward P/S": (0.14, False),
                "P/E TTM": (0.12, False),
                "P/S TTM": (0.10, False),
                "FCF Yield": (0.12, True),
                "P/FCF TTM": (0.12, False),
                "Price Target Upside": (0.16, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.18,
            "Growth Score": 0.20,
            "Profitability Score": 0.10,
            "Cash Flow Score": 0.14,
            "Balance Sheet Score": 0.08,
            "Valuation Score": 0.16,
            "Forward Expectations Score": 0.07,
            "Technical Score": 0.05,
            "Analyst Sentiment Score": 0.02,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / R&D Quality": ["Latest Gross Margin", "Latest Operating Margin", "Latest Net Margin", "R&D as % Revenue", "ROIC"],
            "Cash Flow / Balance Sheet": ["FCF Yield", "Cash Conversion", "Debt to Equity", "ROA", "ROE"],
            "Valuation": ["Forward P/E", "Forward P/S", "P/E TTM", "P/S TTM", "P/FCF TTM", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Banks / Financials": {
        "description": "Financials framework focused on revenue/forward EPS, P/B, ROE, ROA, book value, forward P/E, dividend yield, analyst upside, and technical trend. Forward P/S and FCF metrics are intentionally downweighted for banks.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "ROE": (0.26, True),
                "ROA": (0.22, True),
                "Latest Net Margin": (0.16, True),
                "Book Value Growth 3Y": (0.14, True),
                "Debt / Assets": (0.12, False),
                "Liabilities to Assets": (0.10, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.28, True),
                "Forward Revenue Growth FY+1": (0.24, True),
                "Net Income CAGR 3Y": (0.20, True),
                "Book Value Growth 3Y": (0.16, True),
                "Forward EPS Next FY": (0.12, True),
            },
            "Balance Sheet Score": {
                "P/B TTM": (0.20, False),
                "Book Value / Share": (0.18, True),
                "Debt / Assets": (0.18, False),
                "Debt / Capital": (0.16, False),
                "Liabilities to Assets": (0.14, False),
                "Dividend Payout Ratio": (0.14, False),
            },
            "Valuation Score": {
                "P/B TTM": (0.24, False),
                "Forward P/E": (0.22, False),
                "P/E TTM": (0.14, False),
                "Earnings Yield": (0.14, True),
                "Dividend Yield": (0.10, True),
                "Price Target Upside": (0.16, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.22,
            "Growth Score": 0.16,
            "Profitability Score": 0.08,
            "Cash Flow Score": 0.04,
            "Balance Sheet Score": 0.18,
            "Valuation Score": 0.18,
            "Forward Expectations Score": 0.06,
            "Technical Score": 0.05,
            "Analyst Sentiment Score": 0.03,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "Net Income CAGR 3Y"],
            "Bank Quality": ["ROE", "ROA", "Latest Net Margin", "Book Value Growth 3Y", "Book Value / Share"],
            "Balance Sheet / Income": ["Debt / Assets", "Debt / Capital", "Dividend Yield", "Dividend Payout Ratio", "Earnings Yield"],
            "Valuation": ["P/B TTM", "P/E TTM", "Forward P/E", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Industrials": {
        "description": "Industrials framework using revenue growth, forward estimates, operating/EBITDA margin, 3Y FCF CAGR, capex efficiency, leverage, EV/EBITDA, forward P/E, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest EBITDA Margin": (0.20, True),
                "Latest Operating Margin": (0.20, True),
                "ROIC": (0.18, True),
                "Cash Conversion": (0.14, True),
                "Net Debt / EBITDA": (0.14, False),
                "Capex to Revenue": (0.14, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.30, True),
                "Forward Revenue Growth FY+1": (0.30, True),
                "FCF CAGR 3Y": (0.20, True),
                "Net Income CAGR 3Y": (0.12, True),
                "Forward EPS Next FY": (0.08, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.32, True),
                "FCF Yield": (0.20, True),
                "Cash Conversion": (0.20, True),
                "Capex to Revenue": (0.16, False),
                "Net Debt / EBITDA": (0.12, False),
            },
            "Valuation Score": {
                "EV / EBITDA": (0.22, False),
                "Forward P/E": (0.20, False),
                "P/E TTM": (0.12, False),
                "P/FCF TTM": (0.14, False),
                "FCF Yield": (0.12, True),
                "Price Target Upside": (0.20, True),
            },
        }),
        "final_weights": DEFAULT_FINAL_WEIGHTS,
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / Returns": ["Latest EBITDA Margin", "Latest Operating Margin", "ROIC", "ROA", "ROE"],
            "Cash Flow / Leverage": ["FCF Yield", "Cash Conversion", "Capex to Revenue", "Net Debt / EBITDA", "Debt / Capital"],
            "Valuation": ["EV / EBITDA", "Forward P/E", "P/E TTM", "P/FCF TTM", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Energy": {
        "description": "Energy framework using revenue/forward estimates, EBITDA/operating margin, FCF yield, leverage, EV/EBITDA, dividends, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest EBITDA Margin": (0.24, True),
                "Latest Operating Margin": (0.18, True),
                "FCF Yield": (0.18, True),
                "Net Debt / EBITDA": (0.18, False),
                "ROIC": (0.12, True),
                "Dividend Payout Ratio": (0.10, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.28, True),
                "Forward Revenue Growth FY+1": (0.24, True),
                "FCF CAGR 3Y": (0.18, True),
                "Net Income CAGR 3Y": (0.16, True),
                "Forward EPS Next FY": (0.14, True),
            },
            "Cash Flow Score": {
                "FCF Yield": (0.30, True),
                "FCF CAGR 3Y": (0.18, True),
                "Cash Conversion": (0.16, True),
                "Dividend Yield": (0.16, True),
                "Dividend Payout Ratio": (0.10, False),
                "Capex to Revenue": (0.10, False),
            },
            "Valuation Score": {
                "EV / EBITDA": (0.24, False),
                "Forward P/E": (0.20, False),
                "P/E TTM": (0.12, False),
                "EV / FCF": (0.12, False),
                "FCF Yield": (0.14, True),
                "Price Target Upside": (0.18, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.16,
            "Growth Score": 0.16,
            "Profitability Score": 0.10,
            "Cash Flow Score": 0.20,
            "Balance Sheet Score": 0.10,
            "Valuation Score": 0.16,
            "Forward Expectations Score": 0.04,
            "Technical Score": 0.06,
            "Analyst Sentiment Score": 0.02,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / Cash Returns": ["Latest EBITDA Margin", "Latest Operating Margin", "FCF Yield", "Dividend Yield", "Dividend Payout Ratio"],
            "Leverage": ["Net Debt / EBITDA", "Debt / Capital", "Debt / Assets", "Capex to Revenue"],
            "Valuation": ["EV / EBITDA", "Forward P/E", "P/E TTM", "EV / FCF", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Materials": {
        "description": "Materials framework using revenue growth, forward estimates, gross/EBITDA/operating margin, 3Y FCF CAGR, capex/leverage, EV/EBITDA, forward P/E, analyst upside, and technical trend.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Gross Margin": (0.18, True),
                "Latest EBITDA Margin": (0.20, True),
                "Latest Operating Margin": (0.18, True),
                "ROIC": (0.16, True),
                "Net Debt / EBITDA": (0.14, False),
                "Capex to Revenue": (0.14, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.30, True),
                "Forward Revenue Growth FY+1": (0.28, True),
                "FCF CAGR 3Y": (0.20, True),
                "Net Income CAGR 3Y": (0.12, True),
                "Forward EPS Next FY": (0.10, True),
            },
            "Cash Flow Score": {
                "FCF CAGR 3Y": (0.32, True),
                "FCF Yield": (0.22, True),
                "Cash Conversion": (0.18, True),
                "Capex to Revenue": (0.16, False),
                "Net Debt / EBITDA": (0.12, False),
            },
            "Valuation Score": {
                "EV / EBITDA": (0.24, False),
                "Forward P/E": (0.20, False),
                "P/E TTM": (0.12, False),
                "P/FCF TTM": (0.12, False),
                "FCF Yield": (0.12, True),
                "Price Target Upside": (0.20, True),
            },
        }),
        "final_weights": DEFAULT_FINAL_WEIGHTS,
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "FCF CAGR 3Y"],
            "Margins / Returns": ["Latest Gross Margin", "Latest EBITDA Margin", "Latest Operating Margin", "ROIC", "ROA"],
            "Cash Flow / Leverage": ["FCF Yield", "Cash Conversion", "Capex to Revenue", "Net Debt / EBITDA", "Debt / Capital"],
            "Valuation": ["EV / EBITDA", "Forward P/E", "P/E TTM", "P/FCF TTM", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Utilities": {
        "description": "Utilities framework using revenue/forward EPS growth, dividend quality, leverage, P/B, forward P/E, analyst upside, and technical trend. High-growth and forward P/S metrics are downweighted.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Net Margin": (0.18, True),
                "ROE": (0.18, True),
                "ROA": (0.12, True),
                "Debt / Capital": (0.18, False),
                "Debt / Assets": (0.16, False),
                "Debt Service Coverage": (0.10, True),
                "Dividend Payout Ratio": (0.08, False),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.28, True),
                "Forward Revenue Growth FY+1": (0.22, True),
                "Net Income CAGR 3Y": (0.18, True),
                "Forward EPS Next FY": (0.20, True),
                "FCF CAGR 3Y": (0.12, True),
            },
            "Cash Flow Score": {
                "Dividend Yield": (0.26, True),
                "Dividend Payout Ratio": (0.24, False),
                "FCF Yield": (0.18, True),
                "Debt Service Coverage": (0.18, True),
                "Net Debt / EBITDA": (0.14, False),
            },
            "Valuation Score": {
                "Forward P/E": (0.24, False),
                "P/E TTM": (0.16, False),
                "P/B TTM": (0.16, False),
                "Earnings Yield": (0.14, True),
                "Dividend Yield": (0.12, True),
                "Price Target Upside": (0.18, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.16,
            "Growth Score": 0.14,
            "Profitability Score": 0.08,
            "Cash Flow Score": 0.18,
            "Balance Sheet Score": 0.16,
            "Valuation Score": 0.14,
            "Forward Expectations Score": 0.06,
            "Technical Score": 0.05,
            "Analyst Sentiment Score": 0.03,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "Net Income CAGR 3Y"],
            "Income / Stability": ["Dividend Yield", "Dividend Payout Ratio", "Debt Service Coverage", "ROE", "ROA"],
            "Balance Sheet": ["Debt / Capital", "Debt / Assets", "Net Debt / EBITDA", "P/B TTM"],
            "Valuation": ["Forward P/E", "P/E TTM", "Earnings Yield", "Dividend Yield", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },

    "Real Estate / REITs": {
        "description": "REIT framework using revenue/forward estimates, dividend yield/payout, leverage, P/B, forward P/E as an imperfect but available proxy, analyst upside, and technical trend. FFO/AFFO remain future enhancements.",
        "bucket_definitions": _merge_config(DEFAULT_BUCKET_DEFINITIONS, {
            "Quality Score": {
                "Latest Net Margin": (0.16, True),
                "ROE": (0.14, True),
                "ROA": (0.12, True),
                "Debt / Assets": (0.18, False),
                "Debt / Capital": (0.18, False),
                "Net Debt / EBITDA": (0.14, False),
                "Debt Service Coverage": (0.08, True),
            },
            "Growth Score": {
                "Revenue CAGR 3Y": (0.32, True),
                "Forward Revenue Growth FY+1": (0.28, True),
                "Forward EPS Next FY": (0.16, True),
                "Book Value Growth 3Y": (0.14, True),
                "Net Income CAGR 3Y": (0.10, True),
            },
            "Cash Flow Score": {
                "Dividend Yield": (0.28, True),
                "Dividend Payout Ratio": (0.26, False),
                "Debt Service Coverage": (0.18, True),
                "Net Debt / EBITDA": (0.16, False),
                "FCF Yield": (0.12, True),
            },
            "Valuation Score": {
                "P/B TTM": (0.22, False),
                "Forward P/E": (0.20, False),
                "Dividend Yield": (0.16, True),
                "Debt / Assets": (0.12, False),
                "Price Target Upside": (0.20, True),
                "Earnings Yield": (0.10, True),
            },
        }),
        "final_weights": {
            "Quality Score": 0.16,
            "Growth Score": 0.16,
            "Profitability Score": 0.06,
            "Cash Flow Score": 0.18,
            "Balance Sheet Score": 0.18,
            "Valuation Score": 0.14,
            "Forward Expectations Score": 0.05,
            "Technical Score": 0.05,
            "Analyst Sentiment Score": 0.02,
        },
        "report_sections": {
            "Executive Snapshot": DEFAULT_REPORT_SECTIONS["Executive Snapshot"],
            "Growth / Forward Estimates": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY", "Forward EPS Next FY", "Book Value Growth 3Y"],
            "Income / Balance Sheet": ["Dividend Yield", "Dividend Payout Ratio", "Debt / Assets", "Debt / Capital", "Net Debt / EBITDA"],
            "Quality": ["Latest Net Margin", "ROE", "ROA", "Debt Service Coverage", "Book Value / Share"],
            "Valuation": ["P/B TTM", "Forward P/E", "Dividend Yield", "Price Target Upside"],
            "Technical Setup": ["YTD Return", "1Y Return", "% From SMA 50", "% From SMA 200", "RSI 14", "MACD Hist"],
        },
    },
}


# ---------------------------------------------------------
# Config accessors
# ---------------------------------------------------------
def get_sector_config(peer_group: Optional[str] = None) -> dict:
    if not peer_group:
        peer_group = "General / Cross-Sector"
    return SECTOR_CONFIGS.get(peer_group, SECTOR_CONFIGS["General / Cross-Sector"])


def get_sector_metric_registry(peer_group: Optional[str] = None) -> dict:
    if not peer_group:
        peer_group = "General / Cross-Sector"
    return SECTOR_METRIC_REGISTRY.get(peer_group, SECTOR_METRIC_REGISTRY["General / Cross-Sector"])


def get_report_sections(peer_group: Optional[str] = None) -> Dict[str, List[str]]:
    return get_sector_config(peer_group).get("report_sections", DEFAULT_REPORT_SECTIONS)


def get_sector_analysis_metrics(peer_group: Optional[str] = None) -> List[str]:
    registry = get_sector_metric_registry(peer_group)
    ordered = []

    for group in ["must_have", "preferred"]:
        for metric in registry.get(group, []):
            if metric not in ordered:
                ordered.append(metric)

    # Always include these if available.
    for metric in [
        "Final Rank", "Research View", "Final Research Score",
        "Best Attribute", "Biggest Weakness", "Valuation Label", "Technical Signal",
    ]:
        if metric not in ordered:
            ordered.insert(0, metric)

    return ordered


# ---------------------------------------------------------
# Coverage-aware scoring helpers
# ---------------------------------------------------------
def _metric_coverage(scorecard: pd.DataFrame, metric: str) -> Tuple[int, float]:
    if scorecard.empty or metric not in scorecard.columns:
        return 0, 0.0

    valid = pd.to_numeric(scorecard[metric], errors="coerce") if scorecard[metric].dtype != "object" else scorecard[metric]
    non_null = valid.notna().sum()
    coverage = non_null / max(len(scorecard), 1)
    return int(non_null), float(coverage)


def build_sector_metric_coverage_table(
    scorecard: pd.DataFrame,
    peer_group: str,
    min_coverage: float = 0.60,
) -> pd.DataFrame:
    registry = get_sector_metric_registry(peer_group)
    rows = []

    for importance in ["must_have", "preferred", "avoid_or_downweight", "missing_but_useful"]:
        for metric in registry.get(importance, []):
            available_count, coverage = _metric_coverage(scorecard, metric)

            if importance == "missing_but_useful":
                status = "Future API Enhancement"
                usable = False
            elif metric not in scorecard.columns:
                status = "Missing Column"
                usable = False
            elif coverage >= min_coverage:
                status = "Usable"
                usable = True
            elif coverage > 0:
                status = "Partial Coverage"
                usable = False
            else:
                status = "No Coverage"
                usable = False

            rows.append({
                "Peer Group": peer_group,
                "Metric": metric,
                "Importance": importance,
                "Available Count": available_count,
                "Ticker Count": len(scorecard),
                "Coverage %": coverage,
                "Usable In Score": usable,
                "Status": status,
            })

    return pd.DataFrame(rows)


def build_sector_missing_metric_table(
    scorecard: pd.DataFrame,
    peer_group: str,
    min_coverage: float = 0.60,
) -> pd.DataFrame:
    coverage = build_sector_metric_coverage_table(scorecard, peer_group, min_coverage=min_coverage)
    if coverage.empty:
        return coverage

    missing = coverage[
        (coverage["Importance"].isin(["must_have", "preferred", "missing_but_useful"]))
        & (~coverage["Usable In Score"])
    ].copy()

    return missing.sort_values(
        ["Importance", "Coverage %", "Metric"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def _filter_bucket_metrics_by_coverage(
    scorecard: pd.DataFrame,
    bucket_weights: Dict[str, Tuple[float, bool]],
    min_coverage: float = 0.60,
) -> Dict[str, Tuple[float, bool]]:
    usable = {}

    for metric, config in bucket_weights.items():
        if metric not in scorecard.columns:
            continue

        _, coverage = _metric_coverage(scorecard, metric)
        if coverage >= min_coverage:
            usable[metric] = config

    return usable


def _weighted_bucket_score(
    df: pd.DataFrame,
    metric_weights: Dict[str, Tuple[float, bool]],
) -> pd.Series:
    """
    Convert raw metrics into percentile ranks and calculate a weighted bucket score.

    metric_weights format:
        {
            "Metric Name": (weight, higher_is_better_bool)
        }
    """
    if df.empty:
        return pd.Series(dtype="float64")

    rank_cols = {}
    for metric, (_, higher_is_better) in metric_weights.items():
        if metric not in df.columns:
            continue

        numeric_metric = pd.to_numeric(df[metric], errors="coerce").replace([np.inf, -np.inf], np.nan)

        # This assumes safe_rank_series exists earlier in your script.
        # It does in your current file.
        rank_cols[metric] = safe_rank_series(numeric_metric, ascending=higher_is_better)

    if not rank_cols:
        return pd.Series(np.nan, index=df.index, dtype="float64")

    rank_df = pd.DataFrame(rank_cols, index=df.index)

    scores = []
    for idx, row in rank_df.iterrows():
        numerator = 0.0
        denominator = 0.0

        for metric, (weight, _) in metric_weights.items():
            if metric not in row.index:
                continue
            val = row.get(metric, np.nan)
            if pd.notna(val):
                numerator += val * weight
                denominator += weight

        scores.append(numerator / denominator if denominator > 0 else np.nan)

    return pd.Series(scores, index=df.index, dtype="float64")


def _normalize_final_weights(
    final_weights: Dict[str, float],
    available_bucket_cols: List[str],
) -> Dict[str, float]:
    usable = {k: v for k, v in final_weights.items() if k in available_bucket_cols}
    total = sum(usable.values())
    if total <= 0:
        return usable
    return {k: v / total for k, v in usable.items()}


# ---------------------------------------------------------
# Label helpers
# ---------------------------------------------------------
def _best_and_weakest_attribute(row: pd.Series) -> Tuple[str, str]:
    bucket_cols = [
        "Quality Score", "Growth Score", "Profitability Score", "Cash Flow Score",
        "Balance Sheet Score", "Valuation Score", "Forward Expectations Score",
        "Technical Score", "Analyst Sentiment Score",
    ]

    vals = {
        c: row.get(c, np.nan)
        for c in bucket_cols
        if c in row.index and pd.notna(row.get(c, np.nan))
    }

    if not vals:
        return "Not enough data", "Not enough data"

    best = max(vals, key=vals.get)
    weakest = min(vals, key=vals.get)

    return best.replace(" Score", ""), weakest.replace(" Score", "")


def _valuation_label(row: pd.Series) -> str:
    valuation = row.get("Valuation Score", np.nan)
    quality = row.get("Quality Score", np.nan)
    growth = row.get("Growth Score", np.nan)
    upside = row.get("Price Target Upside", np.nan)

    valuation = valuation if pd.notna(valuation) else 0.0
    quality = quality if pd.notna(quality) else 0.0
    growth = growth if pd.notna(growth) else 0.0
    upside = upside if pd.notna(upside) else np.nan

    if valuation >= 0.75 and quality >= 0.55:
        return "Attractive Value / Quality"
    if valuation >= 0.70 and growth >= 0.60:
        return "Growth at Reasonable Value"
    if valuation <= 0.30 and quality >= 0.65:
        return "Expensive Quality"
    if valuation <= 0.35 and growth >= 0.65:
        return "Expensive Growth"
    if pd.notna(upside) and upside >= 0.20:
        return "Analyst Upside Support"
    if pd.notna(upside) and upside <= -0.10:
        return "Target Implies Downside"
    if valuation >= 0.60:
        return "Reasonable Valuation"
    if valuation <= 0.40:
        return "Valuation Risk"
    return "Mixed Valuation"


def _technical_signal_label(row: pd.Series) -> str:
    tech = row.get("Technical Score", np.nan)
    rsi = row.get("RSI 14", np.nan)
    sma50 = row.get("% From SMA 50", np.nan)
    sma200 = row.get("% From SMA 200", np.nan)

    tech = tech if pd.notna(tech) else 0.0

    if pd.notna(rsi) and rsi >= 75:
        return "Overbought / Extended"
    if pd.notna(rsi) and rsi <= 30:
        return "Oversold / Potential Reversal"
    if tech >= 0.75 and pd.notna(sma50) and sma50 > 0 and pd.notna(sma200) and sma200 > 0:
        return "Strong Uptrend"
    if tech >= 0.65:
        return "Positive Momentum"
    if tech <= 0.35 and pd.notna(sma200) and sma200 < 0:
        return "Weak / Below Long-Term Trend"
    if tech <= 0.40:
        return "Soft Momentum"
    return "Neutral Technical Setup"


def _research_view_label(row: pd.Series) -> str:
    peer_group = str(row.get("Peer Group", ""))
    fs = row.get("Final Research Score", np.nan)
    q = row.get("Quality Score", np.nan)
    g = row.get("Growth Score", np.nan)
    cf = row.get("Cash Flow Score", np.nan)
    b = row.get("Balance Sheet Score", np.nan)
    v = row.get("Valuation Score", np.nan)
    t = row.get("Technical Score", np.nan)

    fs = fs if pd.notna(fs) else 0.0
    q = q if pd.notna(q) else 0.0
    g = g if pd.notna(g) else 0.0
    cf = cf if pd.notna(cf) else 0.0
    b = b if pd.notna(b) else 0.0
    v = v if pd.notna(v) else 0.0
    t = t if pd.notna(t) else 0.0

    if "Banks" in peer_group and fs >= 0.70 and q >= 0.60 and b >= 0.55:
        return "High-Quality Bank Compounder"
    if "Banks" in peer_group and v >= 0.68 and b >= 0.55:
        return "Bank Value / Capital Return Candidate"
    if "Banks" in peer_group and b <= 0.35:
        return "Bank Balance Sheet / Credit Watch"

    if "Energy" in peer_group and fs >= 0.68 and cf >= 0.65:
        return "Energy Cash-Flow Yield Leader"
    if "Real Estate" in peer_group and fs >= 0.66 and b >= 0.60:
        return "Balance-Sheet Supported REIT Setup"
    if "Utilities" in peer_group and fs >= 0.64 and cf >= 0.60 and b >= 0.50:
        return "Utility Income / Stability Candidate"
    if "Technology" in peer_group and fs >= 0.70 and g >= 0.65 and q >= 0.60:
        return "Tech Growth Compounder"
    if "Healthcare" in peer_group and fs >= 0.68 and q >= 0.60:
        return "Healthcare Quality Growth Candidate"

    if fs >= 0.78 and q >= 0.65 and cf >= 0.60:
        return "High-Quality Compounder"
    if fs >= 0.72 and g >= 0.70:
        return "Growth Leader"
    if fs >= 0.68 and v >= 0.70:
        return "Balanced Buy Candidate"
    if q >= 0.70 and v <= 0.35:
        return "Overvalued Quality"
    if v >= 0.75 and q < 0.45:
        return "Deep Value / Recovery"
    if t >= 0.75 and fs >= 0.55:
        return "Momentum Leader"
    if b <= 0.30 and fs < 0.55:
        return "Balance Sheet Risk"
    if fs <= 0.35:
        return "Weak Fundamentals"

    return "Watchlist / Mixed Setup"


# ---------------------------------------------------------
# Main decision layer
# ---------------------------------------------------------
def add_equity_research_decision_layer(
    scorecard: pd.DataFrame,
    peer_group: str = "General / Cross-Sector",
    min_metric_coverage: float = 0.60,
) -> pd.DataFrame:
    """
    Add analyst-style score buckets and labels using sector-specific metric weights.

    Version 5 behavior:
    - Uses the selected sector's bucket definitions.
    - Filters bucket metrics by data coverage before scoring.
    - Scores only metrics that exist and have enough coverage across the selected tickers.
    - Preserves the same output columns used by the rest of your app.
    """
    if scorecard.empty:
        return scorecard.copy()

    out = scorecard.copy()
    config = get_sector_config(peer_group)
    bucket_definitions = config.get("bucket_definitions", DEFAULT_BUCKET_DEFINITIONS)
    final_weights = config.get("final_weights", DEFAULT_FINAL_WEIGHTS)

    out["Peer Group"] = peer_group
    out["Scoring Framework"] = config.get("description", "Sector-aware scoring framework.")

    coverage_table = build_sector_metric_coverage_table(
        out,
        peer_group=peer_group,
        min_coverage=min_metric_coverage,
    )

    usable_metric_count = int(coverage_table["Usable In Score"].sum()) if not coverage_table.empty else 0
    out["Sector Usable Metric Count"] = usable_metric_count

    active_bucket_names = []

    for bucket_name, metric_weights in bucket_definitions.items():
        filtered_weights = _filter_bucket_metrics_by_coverage(
            out,
            metric_weights,
            min_coverage=min_metric_coverage,
        )

        if filtered_weights:
            out[bucket_name] = _weighted_bucket_score(out, filtered_weights)
            active_bucket_names.append(bucket_name)
        else:
            out[bucket_name] = np.nan

    if "Technical Score" not in out.columns or out["Technical Score"].isna().all():
        filtered_technical = _filter_bucket_metrics_by_coverage(
            out,
            TECHNICAL_BUCKET_WEIGHTS,
            min_coverage=0.40,
        )
        out["Technical Score"] = _weighted_bucket_score(out, filtered_technical) if filtered_technical else np.nan
        if filtered_technical and "Technical Score" not in active_bucket_names:
            active_bucket_names.append("Technical Score")

    normalized_final_weights = _normalize_final_weights(final_weights, active_bucket_names)

    out["Final Research Score"] = out.apply(
        lambda row: weighted_average_available(row, normalized_final_weights),
        axis=1,
    )

    out["Composite Score"] = out["Final Research Score"]

    best_weakest = out.apply(_best_and_weakest_attribute, axis=1)
    out["Best Attribute"] = best_weakest.apply(lambda x: x[0])
    out["Biggest Weakness"] = best_weakest.apply(lambda x: x[1])

    out["Valuation Label"] = out.apply(_valuation_label, axis=1)
    out["Technical Signal"] = out.apply(_technical_signal_label, axis=1)
    out["Research View"] = out.apply(_research_view_label, axis=1)

    out = out.sort_values(
        "Final Research Score",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)

    out["Final Rank"] = np.arange(1, len(out) + 1)

    return out


def _build_research_ranking_table(scorecard: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Final Rank", "Ticker", "Peer Group", "Research View", "Final Research Score",
        "Best Attribute", "Biggest Weakness", "Valuation Label", "Technical Signal",
        "Sector Usable Metric Count",
        "Quality Score", "Growth Score", "Profitability Score", "Cash Flow Score",
        "Balance Sheet Score", "Valuation Score", "Forward Expectations Score",
        "Technical Score", "Analyst Sentiment Score",
        "Price Target Upside", "Composite Score",
    ]

    existing = [c for c in cols if c in scorecard.columns]
    if not existing:
        return pd.DataFrame()

    return scorecard[existing].copy()


# ---------------------------------------------------------
# Methodology / audit tables
# ---------------------------------------------------------
def build_sector_methodology_table(peer_group: str) -> pd.DataFrame:
    config = get_sector_config(peer_group)
    registry = get_sector_metric_registry(peer_group)

    rows = [
        {"Item": "Selected Peer Group", "Details": peer_group},
        {"Item": "Framework", "Details": config.get("description", "")},
        {
            "Item": "Version 5 Sector-Aware Metric Registry",
            "Details": "Scores are now based on sector-specific must-have and preferred metrics, not one generic metric set.",
        },
        {
            "Item": "Coverage Filter",
            "Details": "Metrics are only used in bucket scoring when enough tickers have usable values. Default threshold is 60%.",
        },
        {
            "Item": "Analysis Rule",
            "Details": "GPT analysis should be based only on selected sector metrics and should treat unavailable sector KPIs as data limitations.",
        },
    ]

    final_weights = config.get("final_weights", DEFAULT_FINAL_WEIGHTS)
    for bucket, weight in final_weights.items():
        rows.append({"Item": bucket, "Details": f"{weight:.0%} final score weight"})

    for group_name in ["must_have", "preferred", "avoid_or_downweight", "missing_but_useful"]:
        metrics = registry.get(group_name, [])
        rows.append({
            "Item": group_name.replace("_", " ").title(),
            "Details": ", ".join(metrics) if metrics else "None",
        })

    return pd.DataFrame(rows)


def build_sector_analysis_input_table(
    scorecard: pd.DataFrame,
    peer_group: str,
    max_tickers: Optional[int] = None,
) -> pd.DataFrame:
    if scorecard.empty:
        return pd.DataFrame()

    metrics = get_sector_analysis_metrics(peer_group)
    existing = ["Ticker"] + [c for c in metrics if c in scorecard.columns and c != "Ticker"]

    # Deduplicate while preserving order.
    seen = set()
    existing = [c for c in existing if not (c in seen or seen.add(c))]

    out = scorecard[existing].copy()

    if "Final Rank" in out.columns:
        out = out.sort_values("Final Rank", ascending=True)

    if max_tickers is not None and max_tickers > 0:
        out = out.head(max_tickers)

    return out.reset_index(drop=True)


def build_sector_analysis_prompt(
    scorecard: pd.DataFrame,
    peer_group: str,
    max_tickers: int = 8,
) -> str:
    analysis_df = build_sector_analysis_input_table(
        scorecard,
        peer_group=peer_group,
        max_tickers=max_tickers,
    )

    missing_df = build_sector_missing_metric_table(scorecard, peer_group)

    payload = {
        "peer_group": peer_group,
        "framework_description": get_sector_config(peer_group).get("description", ""),
        "analysis_metrics_used": list(analysis_df.columns) if not analysis_df.empty else [],
        "scorecard": analysis_df.to_dict(orient="records") if not analysis_df.empty else [],
        "missing_or_partial_metrics": missing_df.to_dict(orient="records") if not missing_df.empty else [],
    }

    return f"""
You are writing a sector-aware equity research summary.

Peer group: {peer_group}

Rules:
1. Base the analysis only on the metrics provided in the JSON payload.
2. Do not discuss metrics that are not shown.
3. If an important sector metric is missing or only partially available, mention it as a data limitation.
4. Explain why the top-ranked stock scored best.
5. Explain which metrics drove the ranking.
6. Explain the biggest weakness or risk for the top names.
7. Explain whether valuation is justified by sector-relevant growth, profitability, balance-sheet quality, cash flow, analyst upside, and technical setup.
8. Do not invent data.

JSON payload:
{json.dumps(payload, default=str, indent=2)}
""".strip()


def render_sector_metric_coverage_audit(
    scorecard: pd.DataFrame,
    peer_group: str,
    min_coverage: float = 0.60,
):
    st.markdown("### Sector Metric Coverage Audit")
    st.caption(
        "This shows which sector-specific metrics are available enough to be used in scoring. "
        "Metrics below the coverage threshold are flagged for API/source review."
    )

    coverage_df = build_sector_metric_coverage_table(
        scorecard,
        peer_group=peer_group,
        min_coverage=min_coverage,
    )

    if coverage_df.empty:
        st.info("No sector metric coverage table was available.")
        return

    display_df = coverage_df.copy()
    if "Coverage %" in display_df.columns:
        display_df["Coverage %"] = display_df["Coverage %"].map(lambda x: f"{x:.0%}" if pd.notna(x) else "NA")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    missing_df = build_sector_missing_metric_table(
        scorecard,
        peer_group=peer_group,
        min_coverage=min_coverage,
    )

    if not missing_df.empty:
        st.markdown("### Metrics to Check / Improve Next")
        missing_display = missing_df.copy()
        if "Coverage %" in missing_display.columns:
            missing_display["Coverage %"] = missing_display["Coverage %"].map(lambda x: f"{x:.0%}" if pd.notna(x) else "NA")
        st.dataframe(missing_display, use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# Optional: API coverage test helper
# ---------------------------------------------------------
SECTOR_TEST_TICKERS = {
    "Technology / Software / Semis": "MSFT",
    "Banks / Financials": "JPM",
    "Energy": "XOM",
    "Real Estate / REITs": "PLD",
    "Healthcare": "UNH",
    "Consumer": "COST",
    "Industrials": "CAT",
    "Utilities": "NEE",
    "Communication Services": "GOOGL",
}


def build_api_metric_gap_summary(
    combined_scorecard: pd.DataFrame,
    min_coverage: float = 0.60,
) -> pd.DataFrame:
    """
    Run this after you build a combined scorecard across whatever tickers you tested.

    It summarizes missing or low-coverage metrics by sector, so you can decide
    what to check in FMP or another API next.
    """
    rows = []

    for sector in SECTOR_PEER_GROUPS:
        coverage = build_sector_metric_coverage_table(
            combined_scorecard,
            peer_group=sector,
            min_coverage=min_coverage,
        )

        if coverage.empty:
            continue

        gaps = coverage[
            (coverage["Importance"].isin(["must_have", "preferred", "missing_but_useful"]))
            & (~coverage["Usable In Score"])
        ].copy()

        for _, r in gaps.iterrows():
            rows.append({
                "Sector": sector,
                "Metric": r["Metric"],
                "Importance": r["Importance"],
                "Coverage %": r["Coverage %"],
                "Status": r["Status"],
            })

    return pd.DataFrame(rows).sort_values(
        ["Sector", "Importance", "Coverage %", "Metric"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)



# =========================================================
# DISPLAY / REPORT HELPERS
# =========================================================
MONEY_B_COLS = {
    "Latest Revenue TTM", "Latest OCF TTM", "Latest FCF TTM", "Cash / ST Investments",
    "Total Debt", "Equity", "Market Cap", "Enterprise Value", "Forward Revenue Next FY",
    "Forward Revenue FY+1", "Forward EBITDA Next FY", "Forward Net Income Next FY",
    "Net Interest Income TTM", "Interest Income TTM", "Interest Expense TTM",
    "Noninterest Income TTM", "Revenue Net of Interest Expense TTM", "Bank Revenue Base TTM", "Bank Fee Revenue TTM",
    "Investment Banking Revenue TTM", "Trading Revenue TTM", "Asset Management Fees TTM",
    "Fees and Commissions TTM", "Lending and Deposit Fees TTM", "Card Fees TTM", "Mortgage Fees TTM",
    "Provision Expense TTM", "Deposits", "Loans", "Tangible Common Equity", "R&D Expense TTM",
    "Deferred Revenue", "Tangible Asset Value"
}
PCT_COLS = {
    "Revenue CAGR 3Y", "Net Income CAGR 3Y", "FCF CAGR 3Y", "Latest Gross Margin",
    "Latest Operating Margin", "Latest EBITDA Margin", "Latest Net Margin", "OCF Margin",
    "FCF Margin", "Cash Conversion", "Capex as % Revenue", "Debt to Equity",
    "Liabilities to Assets", "ROE", "ROA", "Earnings Yield", "FCF Yield",
    "Forward Revenue Growth FY+1", "Composite Score", "Price Target Upside", "YTD Return", "1Y Return",
    "3Y Return (Price)", "5Y Return (Price)", "% Below 52W High", "% Above 52W Low",
    "% From SMA 50", "% From SMA 200", "Volume vs 20D Avg",
    "Quality Score", "Growth Score", "Profitability Score", "Cash Flow Score",
    "Balance Sheet Score", "Valuation Score", "Forward Expectations Score",
    "Technical Score", "Analyst Sentiment Score", "Final Research Score",
    "Net Interest Margin Proxy", "Net Interest Income Growth 3Y", "Efficiency Ratio",
    "Provision / Loans", "Deposit Growth 3Y", "Loan Growth 3Y",
    "Loan-to-Deposit Ratio", "Tangible Equity / Assets", "ROTCE Proxy",
    "Bank Fee Revenue Mix", "Book Value Growth 3Y", "R&D as % Revenue", "Deferred Revenue Growth 3Y",
    "Stock-Based Comp % Revenue", "Capex to Revenue", "Debt / Assets", "Debt / Capital",
    "Return on Tangible Assets", "Net Interest Spread Proxy", "Dividend Yield",
    "Dividend Payout Ratio", "ROIC", "Selected Period Return", "Price Return"
}
MULTIPLE_COLS = {"P/E TTM", "P/B TTM", "P/S TTM", "P/FCF TTM", "Forward P/E", "Forward P/S", "EV / EBITDA", "EV / Sales", "EV / FCF", "Net Debt / EBITDA", "Debt Service Coverage", "Income Quality"}
PRICE_COLS = {"Close", "52W High", "52W Low", "SMA 50", "SMA 200", "ATR 14", "Price Target Consensus", "Book Value / Share", "FCF / Share", "Forward EPS Next FY", "Tangible Book Value / Share"}
RAW_DECIMAL_COLS = {"RSI 14", "MACD Line", "MACD Signal", "Volume", "20D Avg Volume", "Current Ratio", "Rating Score", "Final Rank", "Inventory Days", "Cash Conversion Cycle Days", "Days Sales Outstanding", "Days Payables Outstanding"}

TEXT_COLS = {
    "Ticker", "Peer Group", "Company Name", "Sector", "Industry",
    "Research View", "Best Attribute", "Biggest Weakness",
    "Valuation Label", "Technical Signal", "Analyst Rating", "GPT Recommendation",
    "Scoring Framework", "Loan Data Status",
    "Metric", "Valuation Explanation", "Technical Explanation",
}

REPORT_SECTIONS = {
    "Executive Snapshot": [
        "Final Rank", "Research View", "Final Research Score", "Best Attribute", "Biggest Weakness",
        "Valuation Label", "Technical Signal", "Price Target Upside", "Market Cap",
        "Price Target Consensus", "Analyst Rating"
    ],
    "Growth": [
        "Revenue CAGR 3Y", "Net Income CAGR 3Y", "FCF CAGR 3Y", "Forward Revenue Growth FY+1"
    ],
    "Margins": [
        "Latest Gross Margin", "Latest Operating Margin", "Latest EBITDA Margin", "Latest Net Margin"
    ],
    "Returns on Capital": [
        "ROE", "ROA", "Earnings Yield", "FCF Yield"
    ],
    "Cash Flow Quality": [
        "Latest OCF TTM", "Latest FCF TTM", "OCF Margin", "FCF Margin", "Cash Conversion"
    ],
    "Balance Sheet": [
        "Cash / ST Investments", "Total Debt", "Current Ratio", "Debt to Equity", "Liabilities to Assets"
    ],
    "Valuation Multiples": [
        "P/E TTM", "P/B TTM", "P/S TTM", "P/FCF TTM", "Forward P/E", "Forward P/S"
    ],
    "Forward Expectations": [
        "Forward Revenue Next FY", "Forward EPS Next FY", "Forward EBITDA Next FY", "Forward Net Income Next FY"
    ],
    "Price Performance": [
        "YTD Return", "1Y Return", "3Y Return (Price)", "5Y Return (Price)"
    ],
    "Trend Positioning": [
        "% Below 52W High", "% Above 52W Low", "% From SMA 50", "% From SMA 200"
    ],
    "Momentum / Trading": [
        "RSI 14", "MACD Line", "MACD Signal", "ATR 14", "Volume vs 20D Avg"
    ],
}


def format_metric_value(metric: str, value) -> str:
    """Format display values safely while preserving text-label columns."""
    if metric in TEXT_COLS:
        try:
            if value is None or pd.isna(value):
                return "N/A"
        except Exception:
            pass
        text_value = str(value).strip()
        return text_value if text_value else "N/A"

    num_value = _safe_number(value)

    if pd.isna(num_value):
        return "N/A"
    if metric in MONEY_B_COLS:
        return f"{num_value / 1e9:,.1f}B"
    if metric in PCT_COLS:
        return f"{num_value:.1%}"
    if metric in MULTIPLE_COLS:
        return f"{num_value:,.1f}x"
    if metric in PRICE_COLS:
        return f"{num_value:,.2f}"
    if metric in RAW_DECIMAL_COLS:
        if metric in {"Volume", "20D Avg Volume"}:
            return f"{num_value:,.0f}"
        return f"{num_value:,.2f}"
    return f"{num_value:,.2f}"



def make_display_df(scorecard: pd.DataFrame) -> pd.DataFrame:
    out = scorecard.copy()
    for c in out.columns:
        if c in TEXT_COLS:
            out[c] = out[c].apply(lambda x, metric=c: format_metric_value(metric, x))
            continue
        out[c] = out[c].apply(lambda x, metric=c: format_metric_value(metric, x))
    return out


def build_section_table(scorecard: pd.DataFrame, metrics: List[str]) -> pd.DataFrame:
    existing = [m for m in metrics if m in scorecard.columns]
    if not existing or scorecard.empty:
        return pd.DataFrame()

    temp = scorecard[["Ticker"] + existing].copy()
    temp = temp.set_index("Ticker").T.reset_index().rename(columns={"index": "Metric"})
    # Hide rows where every ticker is missing. This keeps sector reports clean when
    # a supported-but-optional field is unavailable for a specific peer set.
    value_cols = [c for c in temp.columns if c != "Metric"]
    if value_cols:
        temp = temp[~temp[value_cols].isna().all(axis=1)].reset_index(drop=True)
    if temp.empty:
        return pd.DataFrame()

    for c in temp.columns[1:]:
        temp[c] = temp.apply(lambda row, ticker=c: format_metric_value(row["Metric"], row[ticker]), axis=1)

    return temp


def winner_for_metric(scorecard: pd.DataFrame, metric: str, higher_is_better: bool = True) -> Optional[str]:
    if metric not in scorecard.columns:
        return None
    s = scorecard[["Ticker", metric]].dropna()
    if s.empty:
        return None
    idx = s[metric].idxmax() if higher_is_better else s[metric].idxmin()
    return s.loc[idx, "Ticker"]


def top_bottom_ticker(scorecard: pd.DataFrame, metric: str, higher_is_better: bool = True) -> Tuple[Optional[str], Optional[str]]:
    if metric not in scorecard.columns:
        return None, None
    s = scorecard[["Ticker", metric]].dropna().sort_values(metric, ascending=not higher_is_better)
    if s.empty:
        return None, None
    return s.iloc[0]["Ticker"], s.iloc[-1]["Ticker"]


def formatted_value_for_ticker(scorecard: pd.DataFrame, ticker: Optional[str], metric: str) -> Optional[str]:
    if not ticker or metric not in scorecard.columns or "Ticker" not in scorecard.columns:
        return None
    temp = scorecard.loc[scorecard["Ticker"] == ticker, metric]
    if temp.empty or pd.isna(temp.iloc[0]):
        return None
    return format_metric_value(metric, temp.iloc[0])


def comparison_bullet(
    scorecard: pd.DataFrame,
    metric: str,
    higher_is_better: bool,
    lead_label: str,
    tail_label: str,
    interpretation: str,
) -> Optional[str]:
    leader, laggard = top_bottom_ticker(scorecard, metric, higher_is_better=higher_is_better)
    if not leader or not laggard:
        return None
    leader_val = formatted_value_for_ticker(scorecard, leader, metric)
    laggard_val = formatted_value_for_ticker(scorecard, laggard, metric)
    if not leader_val or not laggard_val:
        return None
    return (
        f"{lead_label}: {leader} at {leader_val} versus {tail_label} {laggard} at {laggard_val}; "
        f"{interpretation}"
    )


def build_section_drivers(section_name: str, scorecard: pd.DataFrame) -> List[str]:
    bullets: List[str] = []

    if section_name == "Executive Snapshot":
        upside = comparison_bullet(
            scorecard, "Price Target Upside", True,
            "Greatest implied upside to consensus target", "lowest implied upside name",
            "this frames where the Street still sees the largest gap between current trading levels and fair value."
        )
        rating = comparison_bullet(
            scorecard, "Price Target Consensus", True,
            "Highest consensus price target", "lowest target in the group",
            "this is less important than percentage upside, but it still shows where absolute price expectations sit across the peer set."
        )
        analyst = comparison_bullet(
            scorecard, "Rating Score", True,
            "Strongest rating score", "weakest rating score",
            "analyst conviction is materially stronger at the top end of the peer set."
        )
        for item in [upside, rating, analyst]:
            if item:
                bullets.append(item)

    elif section_name == "Growth":
        for item in [
            comparison_bullet(
                scorecard, "Revenue CAGR 3Y", True,
                "Top-line leader", "slowest top-line grower",
                "the spread highlights which company has delivered the strongest multi-year demand expansion."
            ),
            comparison_bullet(
                scorecard, "Net Income CAGR 3Y", True,
                "Earnings growth leader", "weakest earnings growth profile",
                "this helps separate scalable operating leverage from names growing revenue without comparable bottom-line conversion."
            ),
            comparison_bullet(
                scorecard, "FCF CAGR 3Y", True,
                "Free cash flow growth leader", "slowest free cash flow grower",
                "cash-based growth tends to carry more weight in a research setting because it is harder to manufacture than accounting earnings."
            ),
            comparison_bullet(
                scorecard, "Forward Revenue Growth FY+1", True,
                "Best forward growth setup", "softest forward growth outlook",
                "this shows whether Street expectations confirm or fade the historical growth story."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Margins":
        for item in [
            comparison_bullet(
                scorecard, "Latest Gross Margin", True,
                "Best gross margin profile", "lowest gross margin profile",
                "this is often a signal of pricing power, product mix, or structural competitive advantage."
            ),
            comparison_bullet(
                scorecard, "Latest Operating Margin", True,
                "Best operating margin profile", "weakest operating margin profile",
                "the operating spread usually tells you which management team is converting scale into real operating discipline."
            ),
            comparison_bullet(
                scorecard, "Latest Net Margin", True,
                "Best net margin profile", "lowest net margin profile",
                "a wider net margin cushion provides more protection if revenue growth moderates."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Returns on Capital":
        for item in [
            comparison_bullet(
                scorecard, "ROE", True,
                "Highest ROE", "lowest ROE",
                "the leader is generating materially more equity productivity, which is a core quality signal in fundamental work."
            ),
            comparison_bullet(
                scorecard, "ROA", True,
                "Highest ROA", "lowest ROA",
                "this helps normalize for capital intensity and shows who is using the asset base most efficiently."
            ),
            comparison_bullet(
                scorecard, "FCF Yield", True,
                "Best free cash flow yield", "lowest free cash flow yield",
                "the higher-yielding name is offering more cash generation relative to market value."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Cash Flow Quality":
        for item in [
            comparison_bullet(
                scorecard, "OCF Margin", True,
                "Best operating cash flow margin", "lowest operating cash flow margin",
                "this gives a cleaner view of whether revenue is converting into operating cash generation."
            ),
            comparison_bullet(
                scorecard, "FCF Margin", True,
                "Best free cash flow margin", "lowest free cash flow margin",
                "stronger free cash flow conversion typically supports valuation durability and capital return flexibility."
            ),
            comparison_bullet(
                scorecard, "Cash Conversion", True,
                "Best cash conversion profile", "weakest cash conversion profile",
                "this helps identify which names are backing accounting earnings with real cash generation."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Balance Sheet":
        for item in [
            comparison_bullet(
                scorecard, "Current Ratio", True,
                "Strongest near-term liquidity", "tightest near-term liquidity",
                "liquidity cushion matters more in volatile operating or capital market environments."
            ),
            comparison_bullet(
                scorecard, "Debt to Equity", False,
                "Most conservative leverage profile", "most levered name",
                "lower leverage provides more balance-sheet flexibility and usually lowers downside fragility."
            ),
            comparison_bullet(
                scorecard, "Liabilities to Assets", False,
                "Best liability mix", "most liability-heavy balance sheet",
                "this is another simple way to frame capital structure risk across peers."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Valuation Multiples":
        for item in [
            comparison_bullet(
                scorecard, "P/E TTM", False,
                "Cheapest trailing earnings multiple", "richest trailing earnings multiple",
                "this provides a quick read on how much optimism is already reflected in price."
            ),
            comparison_bullet(
                scorecard, "P/S TTM", False,
                "Cheapest trailing sales multiple", "richest trailing sales multiple",
                "sales-based valuation is useful when comparing businesses with different margin structures."
            ),
            comparison_bullet(
                scorecard, "Forward P/E", False,
                "Cheapest forward earnings multiple", "richest forward earnings multiple",
                "forward valuation is often more relevant when consensus revisions are still active."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Forward Expectations":
        for item in [
            comparison_bullet(
                scorecard, "Forward Revenue Next FY", True,
                "Largest forward revenue base", "smallest forward revenue base",
                "the scale of expected revenue gives a sense of absolute operating footprint."
            ),
            comparison_bullet(
                scorecard, "Forward EPS Next FY", True,
                "Highest forward EPS", "lowest forward EPS",
                "this is a simple shorthand for near-term earnings power expected by the Street."
            ),
            comparison_bullet(
                scorecard, "Forward EBITDA Next FY", True,
                "Highest forward EBITDA", "lowest forward EBITDA",
                "this can help compare operating earnings power before capital structure effects."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Price Performance":
        for item in [
            comparison_bullet(
                scorecard, "1Y Return", True,
                "Best one-year performer", "weakest one-year performer",
                "the spread shows where market leadership has already been concentrated."
            ),
            comparison_bullet(
                scorecard, "3Y Return (Price)", True,
                "Best three-year price performer", "weakest three-year price performer",
                "this frames medium-term compounding rather than just near-term moves."
            ),
            comparison_bullet(
                scorecard, "5Y Return (Price)", True,
                "Best five-year price performer", "weakest five-year price performer",
                "this helps identify the most durable long-duration compounders in the group."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Trend Positioning":
        for item in [
            comparison_bullet(
                scorecard, "% Below 52W High", True,
                "Closest to 52-week high", "furthest below 52-week high",
                "trading closer to the high often signals stronger relative trend persistence."
            ),
            comparison_bullet(
                scorecard, "% From SMA 50", True,
                "Strongest short-term trend position", "weakest short-term trend position",
                "distance versus the 50-day moving average can help frame near-term momentum."
            ),
            comparison_bullet(
                scorecard, "% From SMA 200", True,
                "Strongest long-term trend position", "weakest long-term trend position",
                "distance versus the 200-day average helps distinguish secular leadership from weaker setups."
            ),
        ]:
            if item:
                bullets.append(item)

    elif section_name == "Momentum / Trading":
        for item in [
            comparison_bullet(
                scorecard, "RSI 14", True,
                "Highest RSI reading", "lowest RSI reading",
                "this provides a quick lens on which names are carrying the strongest recent buying pressure."
            ),
            comparison_bullet(
                scorecard, "ATR 14", False,
                "Lowest ATR profile", "highest ATR profile",
                "lower realized trading range may indicate a steadier short-term tape."
            ),
            comparison_bullet(
                scorecard, "Volume vs 20D Avg", True,
                "Greatest volume acceleration", "weakest volume confirmation",
                "volume confirmation matters when judging whether recent price action has real participation behind it."
            ),
        ]:
            if item:
                bullets.append(item)

    return bullets


def build_executive_summary_paragraph(scorecard: pd.DataFrame) -> str:
    if scorecard.empty:
        return "No reportable findings were available because the scorecard is empty."

    tmp = scorecard.copy()

    sort_metric = None
    if "Final Research Score" in tmp.columns and tmp["Final Research Score"].notna().any():
        sort_metric = "Final Research Score"
    elif "Composite Score" in tmp.columns and tmp["Composite Score"].notna().any():
        sort_metric = "Composite Score"
    elif "Price Target Upside" in tmp.columns and tmp["Price Target Upside"].notna().any():
        sort_metric = "Price Target Upside"

    if sort_metric:
        tmp = tmp.sort_values(sort_metric, ascending=False).reset_index(drop=True)

    lead = tmp.iloc[0]["Ticker"] if not tmp.empty else None
    lag = tmp.iloc[-1]["Ticker"] if len(tmp) > 1 else None

    growth_leader = winner_for_metric(tmp, "Revenue CAGR 3Y", True)
    margin_leader = winner_for_metric(tmp, "Latest Operating Margin", True)
    valuation_leader = winner_for_metric(tmp, "FCF Yield", True)
    technical_leader = winner_for_metric(tmp, "1Y Return", True)

    lead_sentence = ""
    if lead:
        if sort_metric == "Price Target Upside":
            lead_val = formatted_value_for_ticker(tmp, lead, "Price Target Upside")
            lead_sentence = f"{lead} screens as the highest implied upside idea at {lead_val} based on consensus analyst targets."
        elif sort_metric in {"Composite Score", "Final Research Score"}:
            lead_val = formatted_value_for_ticker(tmp, lead, sort_metric)
            view = tmp.iloc[0].get("Research View", "top-ranked setup")
            lead_sentence = f"{lead} ranks as the top current idea with a research score of {lead_val} and is classified as {view}."

    lag_sentence = ""
    if lag and lag != lead and sort_metric:
        lag_val = formatted_value_for_ticker(tmp, lag, sort_metric)
        label = "the lowest implied upside" if sort_metric == "Price Target Upside" else "the weakest composite score"
        lag_sentence = f"At the other end of the group, {lag} carries {label} at {lag_val}."

    descriptors = []
    if growth_leader:
        growth_val = formatted_value_for_ticker(tmp, growth_leader, "Revenue CAGR 3Y")
        descriptors.append(f"{growth_leader} stands out on growth with a 3-year revenue CAGR of {growth_val}")
    if margin_leader:
        margin_val = formatted_value_for_ticker(tmp, margin_leader, "Latest Operating Margin")
        descriptors.append(f"{margin_leader} leads on operating efficiency with an operating margin of {margin_val}")
    if valuation_leader:
        valuation_val = formatted_value_for_ticker(tmp, valuation_leader, "FCF Yield")
        descriptors.append(f"{valuation_leader} offers the strongest free cash flow yield at {valuation_val}")
    if technical_leader:
        technical_val = formatted_value_for_ticker(tmp, technical_leader, "1Y Return")
        descriptors.append(f"{technical_leader} has shown the best trailing 1-year market performance at {technical_val}")

    body = " ".join(descriptors)
    return " ".join([s for s in [lead_sentence, body, lag_sentence] if s]).strip()


def build_report_tables(scorecard: pd.DataFrame, peer_group: str = "General / Cross-Sector") -> Dict[str, pd.DataFrame]:
    tables = {}
    for section_name, metrics in get_report_sections(peer_group).items():
        tables[section_name] = build_section_table(scorecard, metrics)
    return tables


def summarize_scorecard_with_gpt(records: List[dict], openai_api_key: str, model: str = "gpt-5") -> Optional[str]:
    if not openai_api_key or not records:
        return None

    client = OpenAI(api_key=openai_api_key)

    prompt = f"""
You are writing a concise buy-side or sell-side style supporting note for an equity comparison report.

Return:
- 1 short paragraph on the most attractive names and why
- 1 short paragraph on the weaker or riskier names and why
- 1 short paragraph on what an analyst should watch next

Use a professional CFA-style tone.
Do not repeat every metric.
Focus on growth, margins, cash flow quality, balance sheet, valuation, and price action.

Structured peer data:
{json.dumps(records, default=str)}
"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a disciplined equity research analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"GPT supporting note generation failed: {e}"


def dataframe_to_pdf_table(df: pd.DataFrame) -> Table:
    data = [df.columns.tolist()] + df.astype(str).values.tolist()
    col_count = len(df.columns)

    first_col_width = 2.25 * inch
    remaining_width = max(1.2 * inch, (10.0 * inch - first_col_width) / max(col_count - 1, 1))
    col_widths = [first_col_width] + [remaining_width] * (col_count - 1)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table



# =========================================================
# VERSION 2 REPORTING / INTERPRETATION HELPERS
# =========================================================
def build_valuation_explanation(row: pd.Series) -> str:
    label = str(row.get("Valuation Label", "Fair / Mixed"))
    fpe = row.get("Forward P/E", np.nan)
    fps = row.get("Forward P/S", np.nan)
    fcf_yield = row.get("FCF Yield", np.nan)
    upside = row.get("Price Target Upside", np.nan)
    quality = row.get("Quality Score", np.nan)
    growth = row.get("Growth Score", np.nan)

    facts = []
    if pd.notna(fpe):
        facts.append(f"forward P/E of {fpe:.1f}x")
    if pd.notna(fps):
        facts.append(f"forward P/S of {fps:.1f}x")
    if pd.notna(fcf_yield):
        facts.append(f"FCF yield of {fcf_yield:.1%}")
    if pd.notna(upside):
        facts.append(f"consensus upside of {upside:.1%}")

    fact_text = ", ".join(facts) if facts else "limited valuation data"

    if label == "Attractive / Discounted":
        view = "Valuation screens favorably versus the comparison set."
    elif label == "Reasonable for Quality":
        view = "The multiple is not necessarily cheap, but it appears supportable given the quality or growth profile."
    elif label == "Expensive but Justifiable":
        view = "The stock screens expensive, but stronger quality or growth helps explain the premium."
    elif label == "Expensive / Risky":
        view = "The valuation screen is stretched without enough offsetting support from the current score buckets."
    elif label == "Downside to Target":
        view = "Consensus targets imply downside, so valuation discipline is important."
    elif label == "Valuation Data Limited":
        view = "There is not enough valuation data to make a strong relative call."
    else:
        view = "Valuation is mixed and should be interpreted alongside growth, margin, and technical confirmation."

    if pd.notna(quality) and pd.notna(growth):
        view += f" Quality score is {quality:.1%} and growth score is {growth:.1%}."
    return f"{view} Key inputs: {fact_text}."


def build_technical_explanation(row: pd.Series) -> str:
    signal = str(row.get("Technical Signal", "Neutral / Mixed"))
    rsi = row.get("RSI 14", np.nan)
    sma50 = row.get("% From SMA 50", np.nan)
    sma200 = row.get("% From SMA 200", np.nan)
    one_year = row.get("1Y Return", np.nan)
    vol = row.get("Volume vs 20D Avg", np.nan)

    facts = []
    if pd.notna(sma50):
        facts.append(f"{sma50:.1%} from the 50-day SMA")
    if pd.notna(sma200):
        facts.append(f"{sma200:.1%} from the 200-day SMA")
    if pd.notna(rsi):
        facts.append(f"RSI of {rsi:.1f}")
    if pd.notna(one_year):
        facts.append(f"1Y return of {one_year:.1%}")
    if pd.notna(vol):
        facts.append(f"volume {vol:.1%} versus the 20-day average")

    if "Bullish" in signal:
        view = "Price action confirms a constructive trend."
    elif "Pullback" in signal:
        view = "The long-term trend remains constructive, but the near-term setup has cooled."
    elif "Improving" in signal:
        view = "The setup is improving, but long-term trend confirmation is still incomplete."
    elif "Oversold" in signal:
        view = "Momentum is weak but may be approaching a rebound zone."
    elif "Bearish" in signal or "Weak" in signal:
        view = "Technical confirmation is poor and the stock should require stronger fundamental support."
    else:
        view = "Technical evidence is mixed and should not be the primary driver of the research view."

    fact_text = ", ".join(facts) if facts else "limited technical data"
    return f"{view} Key inputs: {fact_text}."


def build_interpretation_tables(scorecard: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if scorecard.empty or "Ticker" not in scorecard.columns:
        return pd.DataFrame(), pd.DataFrame()

    # Defensive fallback for older cached session_state payloads or partial rebuilds.
    if "Valuation Label" not in scorecard.columns or "Technical Signal" not in scorecard.columns:
        scorecard = add_equity_research_decision_layer(scorecard)

    valuation_rows = []
    technical_rows = []
    for _, row in scorecard.iterrows():
        ticker = row.get("Ticker", "")
        valuation_rows.append({
            "Ticker": ticker,
            "Valuation Label": row.get("Valuation Label", "N/A"),
            "Forward P/E": row.get("Forward P/E", np.nan),
            "Forward P/S": row.get("Forward P/S", np.nan),
            "FCF Yield": row.get("FCF Yield", np.nan),
            "Price Target Upside": row.get("Price Target Upside", np.nan),
            "Valuation Explanation": build_valuation_explanation(row),
        })
        technical_rows.append({
            "Ticker": ticker,
            "Technical Signal": row.get("Technical Signal", "N/A"),
            "RSI 14": row.get("RSI 14", np.nan),
            "% From SMA 50": row.get("% From SMA 50", np.nan),
            "% From SMA 200": row.get("% From SMA 200", np.nan),
            "1Y Return": row.get("1Y Return", np.nan),
            "Technical Explanation": build_technical_explanation(row),
        })
    return pd.DataFrame(valuation_rows), pd.DataFrame(technical_rows)


def build_score_breakdown_table(scorecard: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Final Rank", "Ticker", "Research View", "Final Research Score",
        "Quality Score", "Growth Score", "Profitability Score", "Cash Flow Score",
        "Balance Sheet Score", "Valuation Score", "Forward Expectations Score",
        "Technical Score", "Analyst Sentiment Score", "Best Attribute", "Biggest Weakness",
    ]
    existing = [c for c in cols if c in scorecard.columns]
    return scorecard[existing].copy() if existing else pd.DataFrame()


def _write_excel_sheet(writer, sheet_name: str, df: pd.DataFrame):
    if df is None or df.empty:
        pd.DataFrame({"Message": ["No data available for this section."]}).to_excel(writer, sheet_name=sheet_name[:31], index=False)
    else:
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)


def generate_excel_report(
    scorecard: pd.DataFrame,
    ranking_table: pd.DataFrame,
    report_tables: Dict[str, pd.DataFrame],
    valuation_explanations: pd.DataFrame,
    technical_explanations: pd.DataFrame,
    technical_scorecard: pd.DataFrame,
    executive_summary: Optional[str] = None,
    gpt_note: Optional[str] = None,
    peer_group: str = "General / Cross-Sector",
) -> bytes:
    buffer = io.BytesIO()
    writer = None
    for engine in ("xlsxwriter", "openpyxl"):
        try:
            writer = pd.ExcelWriter(buffer, engine=engine)
            break
        except Exception:
            writer = None
    if writer is None:
        raise RuntimeError("Excel export requires either xlsxwriter or openpyxl. Install one with pip install xlsxwriter openpyxl.")

    with writer:
        summary_rows = [
            {"Section": "Selected Peer Group", "Content": peer_group},
            {"Section": "Sector Framework", "Content": get_sector_config(peer_group).get("description", "")},
            {"Section": "Executive Summary", "Content": executive_summary or ""},
            {"Section": "GPT Supporting Note", "Content": gpt_note or ""},
        ]
        _write_excel_sheet(writer, "Executive Summary", pd.DataFrame(summary_rows))
        _write_excel_sheet(writer, "Scoring Methodology", build_sector_methodology_table(peer_group))
        _write_excel_sheet(writer, "Research Ranking", ranking_table)
        _write_excel_sheet(writer, "Score Breakdown", build_score_breakdown_table(scorecard))
        _write_excel_sheet(writer, "Valuation Explanations", valuation_explanations)
        _write_excel_sheet(writer, "Technical Explanations", technical_explanations)
        _write_excel_sheet(writer, "Full Scorecard", scorecard)
        _write_excel_sheet(writer, "Technical Raw", technical_scorecard)
        for section_name, table_df in report_tables.items():
            clean_name = section_name.replace("/", "-")[:31]
            _write_excel_sheet(writer, clean_name, table_df)
    return buffer.getvalue()


def dataframe_to_pdf_table_compact(df: pd.DataFrame, first_col_width: float = 1.7 * inch) -> Table:
    data = [df.columns.tolist()] + df.astype(str).values.tolist()
    col_count = len(df.columns)
    remaining_width = max(0.75 * inch, (10.0 * inch - first_col_width) / max(col_count - 1, 1))
    col_widths = [first_col_width] + [remaining_width] * (col_count - 1)
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.30, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table



def generate_pdf_report(
    scorecard: pd.DataFrame,
    report_tables: Dict[str, pd.DataFrame],
    tickers: List[str],
    executive_summary: Optional[str] = None,
    gpt_note: Optional[str] = None,
    peer_group: str = "General / Cross-Sector",
) -> bytes:
    """Generate a cleaner Version 2 PDF with front-page ranking, score breakdown, interpretation pages, and appendix tables."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("<b>CFA-Style Equity Comparison Report - Sector-Aware Version</b>", styles["Title"])
    subtitle = Paragraph(f"Tickers: {', '.join(tickers)} | Peer Group: {peer_group}", styles["Heading3"])
    methodology = Paragraph(f"<b>Sector Framework:</b> {get_sector_config(peer_group).get('description', '')}", styles["BodyText"])
    story.extend([title, subtitle, methodology, Spacer(1, 0.12 * inch)])

    if executive_summary:
        story.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.06 * inch))
        story.append(Paragraph(str(executive_summary), styles["BodyText"]))
        story.append(Spacer(1, 0.16 * inch))

    ranking_table = _build_research_ranking_table(scorecard)
    if not ranking_table.empty:
        ranking_cols = [
            "Final Rank", "Ticker", "Research View", "Final Research Score",
            "Best Attribute", "Biggest Weakness", "Valuation Label", "Technical Signal",
            "Price Target Upside",
        ]
        ranking_display = make_display_df(ranking_table[[c for c in ranking_cols if c in ranking_table.columns]])
        story.append(Paragraph("<b>Final Research Ranking</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.08 * inch))
        story.append(dataframe_to_pdf_table_compact(ranking_display, first_col_width=0.75 * inch))
        story.append(Spacer(1, 0.18 * inch))

    score_breakdown = build_score_breakdown_table(scorecard)
    if not score_breakdown.empty:
        story.append(PageBreak())
        story.append(Paragraph("<b>Score Breakdown</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.08 * inch))
        story.append(dataframe_to_pdf_table_compact(make_display_df(score_breakdown), first_col_width=0.75 * inch))

    valuation_explanations, technical_explanations = build_interpretation_tables(scorecard)
    if not valuation_explanations.empty:
        story.append(PageBreak())
        story.append(Paragraph("<b>Valuation Interpretation</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.08 * inch))
        val_pdf = valuation_explanations[[c for c in ["Ticker", "Valuation Label", "Forward P/E", "Forward P/S", "FCF Yield", "Price Target Upside", "Valuation Explanation"] if c in valuation_explanations.columns]].copy()
        for c in val_pdf.columns:
            if c != "Valuation Explanation":
                val_pdf[c] = val_pdf[c].apply(lambda x, metric=c: format_metric_value(metric, x))
        story.append(dataframe_to_pdf_table_compact(val_pdf, first_col_width=0.7 * inch))

    if not technical_explanations.empty:
        story.append(PageBreak())
        story.append(Paragraph("<b>Technical Signal Interpretation</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.08 * inch))
        tech_pdf = technical_explanations[[c for c in ["Ticker", "Technical Signal", "RSI 14", "% From SMA 50", "% From SMA 200", "1Y Return", "Technical Explanation"] if c in technical_explanations.columns]].copy()
        for c in tech_pdf.columns:
            if c != "Technical Explanation":
                tech_pdf[c] = tech_pdf[c].apply(lambda x, metric=c: format_metric_value(metric, x))
        story.append(dataframe_to_pdf_table_compact(tech_pdf, first_col_width=0.7 * inch))

    if gpt_note:
        story.append(PageBreak())
        story.append(Paragraph("<b>GPT Supporting Note</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.08 * inch))
        for para in str(gpt_note).split("\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), styles["BodyText"]))
                story.append(Spacer(1, 0.05 * inch))

    story.append(PageBreak())
    story.append(Paragraph("<b>Appendix: Section Tables</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.10 * inch))
    for section_name, table_df in report_tables.items():
        if table_df.empty:
            continue
        story.append(Paragraph(f"<b>{section_name}</b>", styles["Heading3"]))
        story.append(Spacer(1, 0.05 * inch))
        story.append(dataframe_to_pdf_table(table_df))
        story.append(Spacer(1, 0.08 * inch))

        drivers = build_section_drivers(section_name, scorecard)
        if drivers:
            driver_text = "<br/>".join([f"- {d}" for d in drivers])
            story.append(Paragraph(f"<b>Research Takeaways:</b><br/>{driver_text}", styles["BodyText"]))
            story.append(Spacer(1, 0.16 * inch))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def parse_tickers(tickers_text: str) -> List[str]:
    return [t.strip().upper() for t in tickers_text.split(",") if t.strip()]


def render_equity_report_tab(
    fmp_api_key: str,
    openai_api_key: str = "",
    model_name: str = "gpt-5",
) -> None:
    st.subheader("CFA-Style Equity Comparison Report")
    st.caption("Build a structured multi-ticker comparison report with Version 6 sector-aware metrics, as-reported bank data, coverage-aware scoring, deeper research takeaways, and PDF/Excel export.")

    default_tickers = st.session_state.get("equity_report_ticker_text", "AAPL, MSFT, NVDA, GOOGL")
    default_peer_group = st.session_state.get("equity_report_peer_group", "General / Cross-Sector")
    if default_peer_group not in SECTOR_PEER_GROUPS:
        default_peer_group = "General / Cross-Sector"
    with st.form("equity_report_form"):
        c1, c2 = st.columns([2, 1])
        with c1:
            tickers_text = st.text_input(
                "Tickers (comma-separated)",
                value=default_tickers,
                help="Example: AAPL, MSFT, NVDA, GOOGL",
            )
        with c2:
            include_gpt = st.checkbox(
                "Generate GPT supporting note",
                value=False,
                help="Adds a short optional note below the structured tables.",
            )

        c3, c4 = st.columns(2)
        with c3:
            sector_peer_group = st.selectbox(
                "Peer group / sector scoring framework",
                options=SECTOR_PEER_GROUPS,
                index=SECTOR_PEER_GROUPS.index(default_peer_group),
                help="This controls which metrics are emphasized and which section tables are shown. Technical indicators remain the same across sectors.",
            )
        with c4:
            price_from_date = st.text_input("Price history from date", value=PRICE_FROM_DATE)

        c5, _ = st.columns(2)
        with c5:
            price_to_date = st.text_input("Price history to date (optional)", value="")

        run_button = st.form_submit_button("Build Report", type="primary")

    if run_button:
        if not fmp_api_key:
            st.error("Please enter your FMP API key in the sidebar first.")
            return

        tickers = parse_tickers(tickers_text)
        if not tickers:
            st.error("Please enter at least one ticker.")
            return

        st.session_state["equity_report_ticker_text"] = tickers_text
        st.session_state["equity_report_tickers"] = tickers
        st.session_state["equity_report_peer_group"] = sector_peer_group
        price_to = price_to_date.strip() or None

        with st.spinner("Building comparison report..."):
            financials = prepare_financials(tickers, api_key=fmp_api_key, limit=40)
            market_data = fetch_market_intelligence(tickers, api_key=fmp_api_key)
            fundamental_scorecard = build_analyst_scorecard(financials, market_data)
            technical_scorecard = build_technical_scorecard(
                tickers,
                api_key=fmp_api_key,
                from_date=price_from_date.strip() or None,
                to_date=price_to,
            )
            combined_scorecard = build_combined_scorecard(fundamental_scorecard, technical_scorecard)
            combined_scorecard = add_equity_research_decision_layer(combined_scorecard, peer_group=sector_peer_group)
            ranking_table = _build_research_ranking_table(combined_scorecard)
            display_df = make_display_df(combined_scorecard)
            report_tables = build_report_tables(combined_scorecard, peer_group=sector_peer_group)
            valuation_explanations, technical_explanations = build_interpretation_tables(combined_scorecard)
            executive_summary = build_executive_summary_paragraph(combined_scorecard)

        gpt_note = None
        if include_gpt:
            if not openai_api_key:
                st.warning("OpenAI API key not provided, so the GPT supporting note was skipped.")
            else:
                with st.spinner("Generating GPT supporting note..."):
                    df_for_gpt = combined_scorecard.copy()
                    if "Price Target Upside" in df_for_gpt.columns:
                        df_for_gpt = df_for_gpt.sort_values("Price Target Upside", ascending=False).reset_index(drop=True)
                    elif "Composite Score" in df_for_gpt.columns:
                        df_for_gpt = df_for_gpt.sort_values("Composite Score", ascending=False).reset_index(drop=True)
                    df_for_gpt = df_for_gpt.where(pd.notna(df_for_gpt), None)
                    records = df_for_gpt.to_dict(orient="records")
                    gpt_note = summarize_scorecard_with_gpt(records, openai_api_key=openai_api_key, model=model_name)

        pdf_bytes = generate_pdf_report(
            combined_scorecard,
            report_tables,
            tickers,
            executive_summary=executive_summary,
            gpt_note=gpt_note,
            peer_group=sector_peer_group,
        )
        excel_bytes = generate_excel_report(
            combined_scorecard,
            ranking_table,
            report_tables,
            valuation_explanations,
            technical_explanations,
            technical_scorecard,
            executive_summary=executive_summary,
            gpt_note=gpt_note,
            peer_group=sector_peer_group,
        )

        st.session_state["equity_report_payload"] = {
            "tickers": tickers,
            "combined_scorecard": combined_scorecard,
            "display_df": display_df,
            "ranking_table": ranking_table,
            "technical_scorecard": technical_scorecard,
            "peer_group": sector_peer_group,
            "valuation_explanations": valuation_explanations,
            "technical_explanations": technical_explanations,
            "report_tables": report_tables,
            "executive_summary": executive_summary,
            "gpt_note": gpt_note,
            "pdf_bytes": pdf_bytes,
            "excel_bytes": excel_bytes,
        }

    payload = st.session_state.get("equity_report_payload")
    if not payload:
        st.info("Enter one or more tickers above, then click Build Report.")
        return

    tickers = payload["tickers"]
    peer_group = payload.get("peer_group", st.session_state.get("equity_report_peer_group", "General / Cross-Sector"))

    # Always rebuild the decision-layer labels and formatted report tables from the raw
    # scorecard. This prevents older Streamlit session_state payloads from continuing
    # to show stale "N/A" text labels after code updates.
    combined_scorecard = payload["combined_scorecard"].copy()
    combined_scorecard = add_equity_research_decision_layer(combined_scorecard, peer_group=peer_group)

    display_df = make_display_df(combined_scorecard)
    ranking_table = _build_research_ranking_table(combined_scorecard)
    technical_scorecard = payload["technical_scorecard"]
    valuation_explanations, technical_explanations = build_interpretation_tables(combined_scorecard)
    report_tables = build_report_tables(combined_scorecard, peer_group=peer_group)
    executive_summary = build_executive_summary_paragraph(combined_scorecard)
    gpt_note = payload.get("gpt_note")

    pdf_bytes = generate_pdf_report(
        combined_scorecard,
        report_tables,
        tickers,
        executive_summary=executive_summary,
        gpt_note=gpt_note,
        peer_group=peer_group,
    )
    excel_bytes = generate_excel_report(
        combined_scorecard,
        ranking_table,
        report_tables,
        valuation_explanations,
        technical_explanations,
        technical_scorecard,
        executive_summary=executive_summary,
        gpt_note=gpt_note,
        peer_group=peer_group,
    )

    st.session_state["equity_report_payload"].update({
        "combined_scorecard": combined_scorecard,
        "display_df": display_df,
        "ranking_table": ranking_table,
        "valuation_explanations": valuation_explanations,
        "technical_explanations": technical_explanations,
        "report_tables": report_tables,
        "executive_summary": executive_summary,
        "pdf_bytes": pdf_bytes,
        "excel_bytes": excel_bytes,
    })

    summary_tab, ranking_tab, explain_tab, metrics_tab, downloads_tab = st.tabs([
        "Summary Report", "Sector-Aware Ranking", "Interpretations", "Full Metrics Table", "Downloads"
    ])

    with summary_tab:
        st.markdown("### Executive Summary")
        st.write(executive_summary)

        st.markdown("### Selected Peer Group / Scoring Framework")
        st.info(f"**{peer_group}** — {get_sector_config(peer_group).get('description', '')}")
        with st.expander("View score weights used for this peer group"):
            st.dataframe(build_sector_methodology_table(peer_group), use_container_width=True, hide_index=True)
        with st.expander("View sector metric coverage audit"):
            render_sector_metric_coverage_audit(combined_scorecard, peer_group)

        if not ranking_table.empty:
            st.markdown("### Sector-Aware Research Ranking")
            ranking_display = make_display_df(ranking_table)
            st.dataframe(ranking_display, use_container_width=True, hide_index=True)

        for section_name, table_df in report_tables.items():
            if table_df.empty:
                continue
            st.markdown(f"### {section_name}")
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            drivers = build_section_drivers(section_name, combined_scorecard)
            if drivers:
                st.markdown("**Research Takeaways**")
                for d in drivers:
                    st.write(f"- {d}")

        if gpt_note:
            with st.expander("Open GPT supporting note"):
                st.markdown(gpt_note)

    with ranking_tab:
        st.subheader("Sector-Aware Analyst Decision Layer")
        st.caption("This table converts raw metrics into sector-aware score buckets, final rank, best attribute, biggest weakness, valuation label, technical signal, and research view.")
        if ranking_table.empty:
            st.info("No ranking table was available for this run.")
        else:
            st.dataframe(make_display_df(ranking_table), use_container_width=True, height=520, hide_index=True)

            st.markdown("### Bucket Score Details")
            bucket_cols = [
                "Ticker", "Quality Score", "Growth Score", "Profitability Score", "Cash Flow Score",
                "Balance Sheet Score", "Valuation Score", "Forward Expectations Score",
                "Technical Score", "Analyst Sentiment Score", "Final Research Score"
            ]
            existing_bucket_cols = [c for c in bucket_cols if c in combined_scorecard.columns]
            if existing_bucket_cols:
                st.dataframe(make_display_df(combined_scorecard[existing_bucket_cols]), use_container_width=True, hide_index=True)

    with explain_tab:
        st.subheader("Sector-Aware Interpretations")
        st.caption("These tables explain the valuation and technical labels using the underlying metrics so the report is easier to audit. Technical indicators use the same formulas across peer groups.")

        st.markdown("### Valuation Interpretation")
        if valuation_explanations.empty:
            st.info("No valuation interpretation table was available for this run.")
        else:
            val_display = valuation_explanations.copy()
            for c in val_display.columns:
                val_display[c] = val_display[c].apply(lambda x, metric=c: format_metric_value(metric, x))
            st.dataframe(val_display, use_container_width=True, hide_index=True, height=360)

        st.markdown("### Technical Signal Interpretation")
        if technical_explanations.empty:
            st.info("No technical interpretation table was available for this run.")
        else:
            tech_display = technical_explanations.copy()
            for c in tech_display.columns:
                tech_display[c] = tech_display[c].apply(lambda x, metric=c: format_metric_value(metric, x))
            st.dataframe(tech_display, use_container_width=True, hide_index=True, height=360)


    with metrics_tab:
        st.subheader("Raw Combined Metrics")
        st.dataframe(combined_scorecard, use_container_width=True, height=720)

    with downloads_tab:
        raw_csv = combined_scorecard.to_csv(index=False).encode("utf-8")
        display_csv = display_df.to_csv(index=False).encode("utf-8")
        ranking_csv = ranking_table.to_csv(index=False).encode("utf-8") if not ranking_table.empty else b""
        technical_csv = technical_scorecard.to_csv(index=False).encode("utf-8") if not technical_scorecard.empty else b""

        st.download_button(
            "Download Raw Combined CSV",
            data=raw_csv,
            file_name="fundamental_technical_scorecard_raw.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download Display CSV",
            data=display_csv,
            file_name="fundamental_technical_scorecard_display.csv",
            mime="text/csv",
        )
        if not ranking_table.empty:
            st.download_button(
                "Download Version 2 Ranking CSV",
                data=ranking_csv,
                file_name="equity_research_version_2_ranking.csv",
                mime="text/csv",
            )
        if not technical_scorecard.empty:
            st.download_button(
                "Download Technical CSV",
                data=technical_csv,
                file_name="technical_scorecard.csv",
                mime="text/csv",
            )
        st.download_button(
            "Download Excel Research Pack",
            data=excel_bytes,
            file_name=f"equity_research_pack_{'_'.join(tickers[:5])}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name=f"equity_comparison_report_{'_'.join(tickers[:5])}.pdf",
            mime="application/pdf",
        )


# =========================================================
# SIMPLIFIED STORY-FIRST EQUITY RESEARCH TAB OVERRIDES
# Adds the updated template, historical valuation averages,
# chart-period selector, OpenAI final recommendation, and PDF export.
# These definitions intentionally come after the original implementation
# so they override the older render/PDF/GPT functions when this file is used.
# =========================================================

PRICE_RETURN_PERIODS = ["1D", "5D", "1M", "6M", "YTD", "1Y", "3Y", "5Y", "10Y", "MAX"]

STORY_TEMPLATE_SECTIONS = {
    "Profile": [
        "Company Name", "Sector", "Industry", "Close", "Market Cap",
        "Price Target Consensus", "Price Target Upside",
    ],
    "Ratings": [
        "Analyst Rating", "GPT Recommendation", "Final Research Score", "Research View",
        "Rating Score", "Valuation Label", "Technical Signal",
    ],
    "Factor Grades": [
        "Valuation Grade", "Growth Grade", "Profitability Grade", "Momentum Grade",
        "Quality Grade", "Balance Sheet Grade", "Final Research Score",
    ],
    "Momentum": [
        "RSI 14", "MACD Signal", "MACD Hist", "% From SMA 50", "% From SMA 200",
        "SMA 50 vs SMA 200", "% Below 52W High", "% Above 52W Low", "Volume vs 20D Avg",
    ],
    "Total Return": [
        "1M Return", "3M Return", "6M Return", "9M Return", "YTD Return",
        "1Y Return", "3Y Return", "5Y Return", "10Y Return",
    ],
    "Valuation": [
        "P/E TTM", "3Y Avg P/E", "5Y Avg P/E", "Forward P/E",
        "P/S TTM", "3Y Avg P/S", "5Y Avg P/S", "Forward P/S",
        "P/B TTM", "3Y Avg P/B", "5Y Avg P/B", "EV / Sales", "EV / EBITDA",
        "P/FCF TTM", "FCF Yield", "Price Target Upside",
    ],
    "Growth": [
        "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY",
        "Forward EPS Next FY", "Net Income CAGR 3Y", "FCF CAGR 3Y",
    ],
    "Profitability": [
        "Latest Gross Margin", "Latest Operating Margin", "Latest EBITDA Margin",
        "Latest Net Margin", "ROE", "ROA", "ROIC", "FCF Margin", "Cash Conversion",
    ],
    "Balance Sheet / Leverage": [
        "Cash / ST Investments", "Total Debt", "Net Debt / EBITDA", "Debt to Equity",
        "Debt / Assets", "Debt / Capital", "Current Ratio", "Debt Service Coverage",
        "Book Value / Share", "Tangible Book Value / Share",
    ],
}

SECTOR_SECTION_OVERRIDES = {
    "Banks / Financials": {
        "Valuation": [
            "P/B TTM", "3Y Avg P/B", "5Y Avg P/B", "P/E TTM", "3Y Avg P/E", "5Y Avg P/E",
            "Forward P/E", "Price Target Upside", "Book Value / Share", "Tangible Book Value / Share",
        ],
        "Profitability": [
            "ROE", "ROA", "ROTCE Proxy", "Return on Tangible Assets", "Efficiency Ratio",
            "Net Interest Margin Proxy", "Bank Fee Revenue Mix", "Income Quality",
        ],
        "Balance Sheet / Leverage": [
            "Total Debt", "Debt to Equity", "Debt / Assets", "Debt / Capital",
            "Deposits", "Deposit Growth 3Y", "Loans", "Loan Growth 3Y",
            "Loan-to-Deposit Ratio", "Tangible Equity / Assets",
        ],
    },
    "Real Estate / REITs": {
        "Valuation": [
            "P/B TTM", "3Y Avg P/B", "5Y Avg P/B", "Forward P/E", "P/E TTM",
            "Dividend Yield", "Dividend Payout Ratio", "P/FCF TTM", "FCF Yield", "Price Target Upside",
        ],
        "Growth": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Book Value Growth 3Y",
            "Net Income CAGR 3Y", "FCF CAGR 3Y",
        ],
        "Balance Sheet / Leverage": [
            "Total Debt", "Debt / Assets", "Debt / Capital", "Net Debt / EBITDA",
            "Debt Service Coverage", "Book Value / Share", "Tangible Book Value / Share",
        ],
    },
    "Technology / Software / Semis": {
        "Profitability": [
            "Latest Gross Margin", "Latest Operating Margin", "Latest EBITDA Margin",
            "Latest Net Margin", "ROE", "ROA", "ROIC", "R&D as % Revenue",
            "Capex to Revenue", "Stock-Based Comp % Revenue",
        ],
        "Growth": [
            "Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward Revenue Next FY",
            "Forward EPS Next FY", "Net Income CAGR 3Y", "FCF CAGR 3Y",
            "Deferred Revenue Growth 3Y",
        ],
    },
    "Energy": {
        "Valuation": [
            "EV / EBITDA", "P/E TTM", "3Y Avg P/E", "5Y Avg P/E", "Forward P/E",
            "P/B TTM", "3Y Avg P/B", "5Y Avg P/B", "P/FCF TTM", "FCF Yield",
            "Dividend Yield", "Price Target Upside",
        ],
        "Profitability": [
            "Latest EBITDA Margin", "Latest Operating Margin", "ROIC", "ROA", "ROE",
            "FCF Yield", "Capex to Revenue",
        ],
        "Balance Sheet / Leverage": [
            "Total Debt", "Net Debt / EBITDA", "Debt / Capital", "Debt / Assets",
            "Debt Service Coverage", "Dividend Payout Ratio",
        ],
    },
}


def _normalize_ticker_col(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "symbol" in out.columns and "Ticker" not in out.columns:
        out = out.rename(columns={"symbol": "Ticker"})
    if "ticker" in out.columns and "Ticker" not in out.columns:
        out = out.rename(columns={"ticker": "Ticker"})
    if "Ticker" in out.columns:
        out["Ticker"] = out["Ticker"].astype(str).str.upper().str.strip()
    return out


def fetch_historical_valuation_averages(symbols: List[str], api_key: str, limit: int = 6) -> pd.DataFrame:
    """Fetch annual historical ratio records and calculate 3Y/5Y average P/E, P/S, and P/B."""
    rows = []
    for sym in symbols:
        try:
            url = f"https://financialmodelingprep.com/api/v3/ratios/{sym}"
            data = _get_json(url, {"period": "annual", "limit": limit, "apikey": api_key})
            if not isinstance(data, list) or not data:
                rows.append({"Ticker": sym.upper()})
                continue
            df = pd.DataFrame(data)
            for c in ["priceEarningsRatio", "priceToSalesRatio", "priceToBookRatio"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
            rows.append({
                "Ticker": sym.upper(),
                "3Y Avg P/E": df.get("priceEarningsRatio", pd.Series(dtype=float)).head(3).mean(),
                "5Y Avg P/E": df.get("priceEarningsRatio", pd.Series(dtype=float)).head(5).mean(),
                "3Y Avg P/S": df.get("priceToSalesRatio", pd.Series(dtype=float)).head(3).mean(),
                "5Y Avg P/S": df.get("priceToSalesRatio", pd.Series(dtype=float)).head(5).mean(),
                "3Y Avg P/B": df.get("priceToBookRatio", pd.Series(dtype=float)).head(3).mean(),
                "5Y Avg P/B": df.get("priceToBookRatio", pd.Series(dtype=float)).head(5).mean(),
            })
        except Exception:
            rows.append({"Ticker": sym.upper()})
    return pd.DataFrame(rows)





def _map_profile_sector_to_peer_group(sector_value: object, industry_value: object = "") -> str:
    """Map FMP profile sector/industry text to the report framework names."""
    sector = str(sector_value or "").strip().lower()
    industry = str(industry_value or "").strip().lower()
    txt = f"{sector} {industry}"

    if not txt.strip():
        return "General / Cross-Sector"
    if any(x in txt for x in ["bank", "financial", "capital markets", "asset management", "insurance"]):
        return "Banks / Financials"
    if any(x in txt for x in ["real estate", "reit", "mortgage"]):
        return "Real Estate / REITs"
    if any(x in txt for x in ["technology", "software", "semiconductor", "information technology", "hardware"]):
        return "Technology / Software / Semis"
    if "communication" in txt or "telecom" in txt or "media" in txt or "entertainment" in txt:
        return "Communication Services"
    if "consumer cyclical" in txt or "consumer discretionary" in txt:
        return "Consumer Discretionary"
    if "consumer defensive" in txt or "consumer staples" in txt:
        return "Consumer Staples"
    if "health" in txt or "biotech" in txt or "pharma" in txt or "medical" in txt:
        return "Healthcare"
    if "industrial" in txt:
        return "Industrials"
    if "energy" in txt or "oil" in txt or "gas" in txt:
        return "Energy"
    if "material" in txt or "chemical" in txt or "metals" in txt or "mining" in txt:
        return "Materials"
    if "utilities" in txt or "utility" in txt:
        return "Utilities"
    if "consumer" in txt:
        return "Consumer"
    return "General / Cross-Sector"


def infer_peer_group_from_scorecard(scorecard: pd.DataFrame, fallback: str = "General / Cross-Sector") -> str:
    """
    Infer the report framework from the companies being analyzed so stale sector selections
    from a previous run do not carry into a new ticker set.

    If the selected tickers span multiple different frameworks, use General / Cross-Sector.
    """
    if scorecard is None or scorecard.empty:
        return fallback if fallback in SECTOR_PEER_GROUPS else "General / Cross-Sector"

    sector_col = pick_col(scorecard, ["Sector", "sector"])
    industry_col = pick_col(scorecard, ["Industry", "industry"])
    inferred = []
    for _, row in scorecard.iterrows():
        mapped = _map_profile_sector_to_peer_group(
            row.get(sector_col, "") if sector_col else "",
            row.get(industry_col, "") if industry_col else "",
        )
        if mapped != "General / Cross-Sector":
            inferred.append(mapped)

    unique = sorted(set(inferred))
    if len(unique) == 1:
        return unique[0]
    return "General / Cross-Sector"

def _deterministic_gpt_recommendation_label(row: pd.Series) -> str:
    """
    Per-ticker recommendation label used in the Ratings table.

    The longer OpenAI narrative is still generated below the report when an OpenAI
    API key is provided. This field prevents the Ratings section from showing N/A
    and gives users a clean decision-oriented label for each ticker.
    """
    fs = _safe_number(row.get("Final Research Score", np.nan))
    valuation = _safe_number(row.get("Valuation Score", np.nan))
    growth = _safe_number(row.get("Growth Score", np.nan))
    quality = _safe_number(row.get("Quality Score", np.nan))
    balance = _safe_number(row.get("Balance Sheet Score", np.nan))
    technical = _safe_number(row.get("Technical Score", np.nan))
    analyst_upside = _safe_number(row.get("Analyst Upside", np.nan))

    fs = 0.0 if pd.isna(fs) else fs
    valuation = 0.0 if pd.isna(valuation) else valuation
    growth = 0.0 if pd.isna(growth) else growth
    quality = 0.0 if pd.isna(quality) else quality
    balance = 0.0 if pd.isna(balance) else balance
    technical = 0.0 if pd.isna(technical) else technical

    upside_support = pd.notna(analyst_upside) and analyst_upside >= 0.10
    downside_risk = pd.notna(analyst_upside) and analyst_upside <= -0.05
    weak_balance_sheet = balance > 0 and balance <= 0.30
    weak_quality = quality > 0 and quality <= 0.35

    if fs >= 0.72 and (upside_support or valuation >= 0.60 or growth >= 0.65) and not weak_balance_sheet:
        return "Buy"
    if fs >= 0.64 and quality >= 0.55 and not downside_risk and not weak_balance_sheet:
        return "Buy / Accumulate"
    if fs >= 0.50 and not downside_risk:
        return "Hold / Watchlist"
    if downside_risk and (valuation <= 0.35 or technical <= 0.35):
        return "Trim / Sell"
    if fs < 0.40 or weak_balance_sheet or weak_quality:
        return "Avoid / Sell"
    return "Hold"

def add_story_template_fields(scorecard: pd.DataFrame) -> pd.DataFrame:
    out = scorecard.copy()
    if out.empty:
        return out

    if "Close" in out.columns:
        out["Current Price"] = out["Close"]

    if {"SMA 50", "SMA 200"}.issubset(out.columns):
        out["SMA 50 vs SMA 200"] = np.where(
            out["SMA 200"].notna() & (out["SMA 200"] != 0),
            (out["SMA 50"] / out["SMA 200"]) - 1,
            np.nan,
        )

    # Existing technical scorecard has YTD/1Y/3Y/5Y. Add placeholders for the simpler report template.
    for col in ["1M Return", "3M Return", "6M Return", "9M Return", "10Y Return"]:
        if col not in out.columns:
            out[col] = np.nan
    if "3Y Return" not in out.columns and "3Y Return (Price)" in out.columns:
        out["3Y Return"] = out["3Y Return (Price)"]
    if "5Y Return" not in out.columns and "5Y Return (Price)" in out.columns:
        out["5Y Return"] = out["5Y Return (Price)"]

    # Convert score buckets to 1-10 grades to match the template.
    grade_sources = {
        "Valuation Grade": "Valuation Score",
        "Growth Grade": "Growth Score",
        "Profitability Grade": "Profitability Score",
        "Momentum Grade": "Technical Score",
        "Quality Grade": "Quality Score",
        "Balance Sheet Grade": "Balance Sheet Score",
    }
    for grade_col, score_col in grade_sources.items():
        if score_col in out.columns:
            out[grade_col] = pd.to_numeric(out[score_col], errors="coerce") * 10
        elif grade_col not in out.columns:
            out[grade_col] = np.nan

    # Populate the Ratings-table GPT Recommendation row with a per-ticker
    # decision label. Previously this column could exist as all NaN, which
    # displayed as N/A even when the OpenAI narrative was generated below.
    generated_gpt_rec = out.apply(_deterministic_gpt_recommendation_label, axis=1)
    if "GPT Recommendation" not in out.columns:
        out["GPT Recommendation"] = generated_gpt_rec
    else:
        out["GPT Recommendation"] = out["GPT Recommendation"].where(
            out["GPT Recommendation"].notna()
            & (out["GPT Recommendation"].astype(str).str.strip() != "")
            & (out["GPT Recommendation"].astype(str).str.upper() != "N/A"),
            generated_gpt_rec,
        )

    return out


def get_story_template_sections(peer_group: str) -> Dict[str, List[str]]:
    sections = {k: list(v) for k, v in STORY_TEMPLATE_SECTIONS.items()}
    for section_name, metrics in SECTOR_SECTION_OVERRIDES.get(peer_group, {}).items():
        sections[section_name] = metrics
    return sections


def build_story_report_tables(scorecard: pd.DataFrame, peer_group: str) -> Dict[str, pd.DataFrame]:
    scorecard = add_story_template_fields(scorecard)
    tables = {}
    for section_name, metrics in get_story_template_sections(peer_group).items():
        existing_metrics = [m for m in metrics if m in scorecard.columns]
        if not existing_metrics:
            tables[section_name] = pd.DataFrame()
        else:
            tables[section_name] = build_section_table(scorecard, existing_metrics)
    return tables


def build_price_return_long_df(price_history: Dict[str, pd.DataFrame], period: str) -> pd.DataFrame:
    rows = []
    for ticker, df in price_history.items():
        if df is None or df.empty or "date" not in df.columns or "close" not in df.columns:
            continue
        tmp = df.copy().sort_values("date")
        tmp = tmp.dropna(subset=["date", "close"])
        if tmp.empty:
            continue
        end_date = tmp["date"].max()
        if period == "1D":
            tmp = tmp.tail(2)
        elif period == "5D":
            tmp = tmp.tail(6)
        elif period == "1M":
            tmp = tmp[tmp["date"] >= end_date - pd.DateOffset(months=1)]
        elif period == "6M":
            tmp = tmp[tmp["date"] >= end_date - pd.DateOffset(months=6)]
        elif period == "YTD":
            tmp = tmp[tmp["date"] >= pd.Timestamp(year=end_date.year, month=1, day=1)]
        elif period == "1Y":
            tmp = tmp[tmp["date"] >= end_date - pd.DateOffset(years=1)]
        elif period == "3Y":
            tmp = tmp[tmp["date"] >= end_date - pd.DateOffset(years=3)]
        elif period == "5Y":
            tmp = tmp[tmp["date"] >= end_date - pd.DateOffset(years=5)]
        elif period == "10Y":
            tmp = tmp[tmp["date"] >= end_date - pd.DateOffset(years=10)]
        # MAX keeps all rows.
        if len(tmp) < 2:
            continue
        base = tmp.iloc[0]["close"]
        if pd.isna(base) or base == 0:
            continue
        tmp["Ticker"] = ticker.upper()
        tmp["Price Return"] = (tmp["close"] / base) - 1
        rows.append(tmp[["date", "Ticker", "Price Return"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "Ticker", "Price Return"])


def build_selected_period_return_table(chart_df: pd.DataFrame) -> pd.DataFrame:
    if chart_df.empty:
        return pd.DataFrame()
    rows = []
    for ticker, g in chart_df.groupby("Ticker"):
        g = g.sort_values("date")
        rows.append({"Ticker": ticker, "Selected Period Return": g.iloc[-1]["Price Return"]})
    return pd.DataFrame(rows).sort_values("Selected Period Return", ascending=False).reset_index(drop=True)


def build_final_recommendation_prompt(scorecard: pd.DataFrame, peer_group: str) -> str:
    analysis_cols = [
        "Ticker", "Final Rank", "Research View", "Final Research Score", "Valuation Grade", "Growth Grade",
        "Profitability Grade", "Momentum Grade", "Price Target Upside", "Forward P/E", "Forward P/S",
        "P/E TTM", "P/S TTM", "P/B TTM", "FCF Yield", "Revenue CAGR 3Y",
        "Forward Revenue Growth FY+1", "Latest Operating Margin", "ROE", "ROA", "ROIC",
        "Debt to Equity", "Net Debt / EBITDA", "YTD Return", "1Y Return", "RSI 14", "Technical Signal",
        "Best Attribute", "Biggest Weakness", "Valuation Label",
    ]
    existing = [c for c in analysis_cols if c in scorecard.columns]
    df = scorecard[existing].copy() if existing else scorecard.copy()
    if "Final Rank" in df.columns:
        df = df.sort_values("Final Rank", ascending=True)
    payload = df.where(pd.notna(df), None).to_dict(orient="records")
    return f"""
You are an equity research analyst writing the final recommendation for a simplified sector-aware comparison report.

Peer group: {peer_group}

Use only the metrics provided below. Do not invent missing data.

Return exactly this structure:
1. Final Recommendation: one of Buy / Hold / Sell for each ticker in a compact table-like bullet list.
2. Best Idea: identify the best risk/reward name and why.
3. Key Drivers: explain valuation, growth, profitability, balance sheet, and momentum in plain English.
4. Main Risks: call out the biggest weakness for the top name and any names to avoid.
5. Analyst Conclusion: one concise paragraph that tells the investment story.

Data:
{json.dumps(payload, default=str, indent=2)}
""".strip()


def summarize_scorecard_with_gpt(records: List[dict], openai_api_key: str, model: str = "gpt-5") -> Optional[str]:
    """Override: stronger final recommendation note aligned to the new template."""
    if not openai_api_key or not records:
        return None
    client = OpenAI(api_key=openai_api_key)
    prompt = f"""
You are a disciplined equity research analyst.

Create a simplified investment recommendation using only this structured scorecard data.
Do not invent data. Be direct and decision-oriented.

Required output:
- Final recommendation by ticker: Buy / Hold / Sell
- Best idea and why
- Key supporting evidence from valuation, growth, profitability, leverage, analyst upside, and momentum
- Biggest risks or watch-items
- One final analyst conclusion paragraph

Structured peer data:
{json.dumps(records, default=str, indent=2)}
"""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a concise CFA-style equity research analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"GPT final recommendation generation failed: {e}"


def _shorten_pdf_cell(value: object, max_chars: int = 44) -> str:
    """Keep one-page PDF cells compact and avoid tall wrapped boxes."""
    if value is None:
        return ""
    s = str(value).replace("\n", " ").replace("\r", " ")
    s = " ".join(s.split())
    if s.lower() in {"nan", "none", "nat"}:
        return "N/A"
    if len(s) > max_chars:
        return s[: max_chars - 1].rstrip() + "..."
    return s


def _one_page_pdf_rows(report_tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create a compact one-page research matrix from the story report sections."""
    keep_metrics = {
        "Profile": ["Close", "Market Cap", "Price Target Consensus", "Price Target Upside"],
        "Ratings": ["Analyst Rating", "GPT Recommendation", "Final Research Score", "Research View"],
        "Factor Grades": ["Valuation Grade", "Growth Grade", "Profitability Grade", "Momentum Grade"],
        "Valuation": ["P/E TTM", "Forward P/E", "P/S TTM", "Forward P/S", "FCF Yield"],
        "Growth": ["Revenue CAGR 3Y", "Forward Revenue Growth FY+1", "Forward EPS Next FY", "FCF CAGR 3Y"],
        "Profitability": ["Latest Operating Margin", "Latest Net Margin", "ROE", "FCF Margin"],
        "Balance Sheet / Leverage": ["Debt to Equity", "Net Debt / EBITDA", "Current Ratio", "Debt / Assets"],
        "Momentum": ["RSI 14", "% From SMA 50", "% From SMA 200", "Technical Signal"],
    }
    rows = []
    ticker_cols = []
    for section, metrics in keep_metrics.items():
        table = report_tables.get(section, pd.DataFrame())
        if table is None or table.empty or "Metric" not in table.columns:
            continue
        if not ticker_cols:
            ticker_cols = [c for c in table.columns if c != "Metric"]
        for metric in metrics:
            hit = table[table["Metric"].astype(str).eq(metric)]
            if hit.empty:
                continue
            row = hit.iloc[0].to_dict()
            out = {"Section": section, "Metric": metric}
            for c in ticker_cols:
                out[c] = row.get(c, "N/A")
            rows.append(out)
    if not rows:
        return pd.DataFrame()
    compact = pd.DataFrame(rows)
    # Keep section label only on the first row of each section to reduce visual clutter.
    last_section = None
    for i in compact.index:
        current = compact.at[i, "Section"]
        if current == last_section:
            compact.at[i, "Section"] = ""
        else:
            last_section = current
    return compact


def dataframe_to_one_page_pdf_table(df: pd.DataFrame) -> Table:
    clean = df.copy()
    for c in clean.columns:
        limit = 24 if c in {"Section", "Metric"} else 34
        clean[c] = clean[c].map(lambda x: _shorten_pdf_cell(x, limit))

    data = [clean.columns.tolist()] + clean.astype(str).values.tolist()
    ticker_count = max(len(clean.columns) - 2, 1)
    page_width = 10.3 * inch
    section_w = 1.15 * inch
    metric_w = 1.55 * inch
    ticker_w = max(0.90 * inch, (page_width - section_w - metric_w) / ticker_count)
    col_widths = [section_w, metric_w] + [ticker_w] * ticker_count

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 5.6),
        ("LEADING", (0, 0), (-1, -1), 6.2),
        ("GRID", (0, 0), (-1, -1), 0.20, colors.HexColor("#C9CDD3")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
    ]))
    return table


def generate_story_pdf_report(
    scorecard: pd.DataFrame,
    report_tables: Dict[str, pd.DataFrame],
    tickers: List[str],
    executive_summary: str,
    gpt_note: Optional[str],
    peer_group: str,
) -> bytes:
    """
    Generate a consolidated one-page PDF summary.

    The full detail remains available in the app and Excel export; the PDF is designed
    for a tight investment-committee style handout without tall wrapped boxes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.25 * inch,
        leftMargin=0.25 * inch,
        topMargin=0.22 * inch,
        bottomMargin=0.22 * inch,
    )
    styles = getSampleStyleSheet()
    styles["Title"].fontSize = 12
    styles["Title"].leading = 13
    styles["Heading2"].fontSize = 8
    styles["Heading2"].leading = 9
    styles["BodyText"].fontSize = 6.3
    styles["BodyText"].leading = 7.2

    story = []
    title = f"Equity Research One-Page: {', '.join(tickers)}"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(f"Framework: {peer_group}", styles["BodyText"]))

    summary = _shorten_pdf_cell(executive_summary or "No executive summary available.", 360)
    story.append(Paragraph(f"<b>Executive summary:</b> {summary}", styles["BodyText"]))

    if gpt_note:
        note = _shorten_pdf_cell(str(gpt_note), 300)
        story.append(Paragraph(f"<b>OpenAI recommendation note:</b> {note}", styles["BodyText"]))

    compact_df = _one_page_pdf_rows(report_tables)
    if not compact_df.empty:
        story.append(Spacer(1, 0.05 * inch))
        story.append(dataframe_to_one_page_pdf_table(compact_df))
    else:
        story.append(Paragraph("No compact report table was available.", styles["BodyText"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def render_equity_report_tab(
    fmp_api_key: str,
    openai_api_key: str = "",
    model_name: str = "gpt-5",
) -> None:
    st.subheader("Equity Research Report")
    st.caption(
        "Simplified story-first report: profile, price returns, ratings, factor grades, momentum, total return, valuation, growth, profitability, leverage, OpenAI recommendation, and PDF export."
    )
    inject_equity_research_report_css()

    default_tickers = st.session_state.get("equity_report_ticker_text", "AAPL, MSFT, NVDA, GOOGL")
    # Do not default to the prior run's sector. That caused new ticker sets to inherit
    # an old sector framework. The run below can auto-detect the correct framework
    # from company profile sector/industry after the data is fetched.
    default_peer_group = "General / Cross-Sector"

    with st.form("equity_report_form"):
        c1, c2 = st.columns([2, 1])
        with c1:
            tickers_text = st.text_input("Tickers", value=default_tickers, help="Comma-separated, e.g. AAPL, MSFT, NVDA")
        with c2:
            include_gpt = st.checkbox("Use OpenAI final recommendation", value=True)
            auto_detect_sector = st.checkbox("Auto-detect sector framework", value=True)

        c3, c4, c5 = st.columns([1.2, 0.9, 0.9])
        with c3:
            sector_peer_group = st.selectbox(
                "Manual sector / peer framework",
                options=SECTOR_PEER_GROUPS,
                index=SECTOR_PEER_GROUPS.index(default_peer_group),
                help="Used only when auto-detect is off or the ticker list spans multiple sectors.",
            )
        with c4:
            price_from_date = st.text_input("Price history from", value=PRICE_FROM_DATE)
        with c5:
            price_to_date = st.text_input("Price history to", value="")

        run_button = st.form_submit_button("Build Equity Research Report", type="primary")

    if run_button:
        if not fmp_api_key:
            st.error("Please enter your FMP API key in the sidebar first.")
            return
        tickers = parse_tickers(tickers_text)
        if not tickers:
            st.error("Please enter at least one ticker.")
            return

        st.session_state["equity_report_ticker_text"] = tickers_text
        st.session_state["equity_report_tickers"] = tickers
        st.session_state["equity_report_peer_group"] = sector_peer_group
        price_to = price_to_date.strip() or None

        with st.spinner("Fetching fundamentals, market data, technicals, historical valuation averages, and price history..."):
            financials = prepare_financials(tickers, api_key=fmp_api_key, limit=40)
            market_data = fetch_market_intelligence(tickers, api_key=fmp_api_key)
            fundamental_scorecard = build_analyst_scorecard(financials, market_data)
            technical_scorecard = build_technical_scorecard(
                tickers,
                api_key=fmp_api_key,
                from_date=price_from_date.strip() or None,
                to_date=price_to,
            )
            combined_scorecard = build_combined_scorecard(fundamental_scorecard, technical_scorecard)

            hist_val = fetch_historical_valuation_averages(tickers, api_key=fmp_api_key, limit=6)
            if not hist_val.empty:
                combined_scorecard = _normalize_ticker_col(combined_scorecard).merge(hist_val, on="Ticker", how="left")

            price_history = fetch_all_price_history(
                tickers,
                api_key=fmp_api_key,
                from_date=price_from_date.strip() or None,
                to_date=price_to,
            )
            inferred_peer_group = infer_peer_group_from_scorecard(combined_scorecard, fallback=sector_peer_group)
            selected_peer_group = inferred_peer_group if auto_detect_sector else sector_peer_group
            combined_scorecard = add_equity_research_decision_layer(combined_scorecard, peer_group=selected_peer_group)
            combined_scorecard = add_story_template_fields(combined_scorecard)
            ranking_table = _build_research_ranking_table(combined_scorecard)
            display_df = make_display_df(combined_scorecard)
            report_tables = build_story_report_tables(combined_scorecard, peer_group=selected_peer_group)
            valuation_explanations, technical_explanations = build_interpretation_tables(combined_scorecard)
            executive_summary = build_executive_summary_paragraph(combined_scorecard)

        gpt_note = None
        if include_gpt:
            if not openai_api_key:
                st.warning("OpenAI API key was not provided, so the final GPT recommendation was skipped.")
            else:
                with st.spinner("Generating OpenAI final recommendation..."):
                    df_for_gpt = combined_scorecard.copy()
                    if "Final Rank" in df_for_gpt.columns:
                        df_for_gpt = df_for_gpt.sort_values("Final Rank", ascending=True).reset_index(drop=True)
                    df_for_gpt = df_for_gpt.where(pd.notna(df_for_gpt), None)
                    gpt_note = summarize_scorecard_with_gpt(
                        df_for_gpt.to_dict(orient="records"),
                        openai_api_key=openai_api_key,
                        model=model_name,
                    )

        pdf_bytes = generate_story_pdf_report(
            combined_scorecard,
            report_tables,
            tickers,
            executive_summary=executive_summary,
            gpt_note=gpt_note,
            peer_group=selected_peer_group,
        )
        excel_bytes = generate_excel_report(
            combined_scorecard,
            ranking_table,
            report_tables,
            valuation_explanations,
            technical_explanations,
            technical_scorecard,
            executive_summary=executive_summary,
            gpt_note=gpt_note,
            peer_group=selected_peer_group,
        )

        st.session_state["equity_report_payload"] = {
            "tickers": tickers,
            "combined_scorecard": combined_scorecard,
            "display_df": display_df,
            "ranking_table": ranking_table,
            "technical_scorecard": technical_scorecard,
            "peer_group": selected_peer_group,
            "valuation_explanations": valuation_explanations,
            "technical_explanations": technical_explanations,
            "report_tables": report_tables,
            "executive_summary": executive_summary,
            "gpt_note": gpt_note,
            "pdf_bytes": pdf_bytes,
            "excel_bytes": excel_bytes,
            "price_history": price_history,
        }

    payload = st.session_state.get("equity_report_payload")
    if not payload:
        st.info("Enter one or more tickers above, then click Build Equity Research Report.")
        return

    tickers = payload["tickers"]
    peer_group = payload.get("peer_group", st.session_state.get("equity_report_peer_group", "General / Cross-Sector"))
    combined_scorecard = add_story_template_fields(add_equity_research_decision_layer(payload["combined_scorecard"].copy(), peer_group=peer_group))
    ranking_table = _build_research_ranking_table(combined_scorecard)
    report_tables = build_story_report_tables(combined_scorecard, peer_group=peer_group)
    executive_summary = build_executive_summary_paragraph(combined_scorecard)
    gpt_note = payload.get("gpt_note")
    price_history = payload.get("price_history", {})

    pdf_bytes = generate_story_pdf_report(
        combined_scorecard,
        report_tables,
        tickers,
        executive_summary=executive_summary,
        gpt_note=gpt_note,
        peer_group=peer_group,
    )

    st.session_state["equity_report_payload"].update({
        "combined_scorecard": combined_scorecard,
        "ranking_table": ranking_table,
        "report_tables": report_tables,
        "executive_summary": executive_summary,
        "pdf_bytes": pdf_bytes,
    })

    story_tab, chart_tab, sections_tab, audit_tab, downloads_tab = st.tabs([
        "Research Story", "Price Return Chart", "Metric Sections", "Audit / Raw Data", "Downloads"
    ])

    with story_tab:
        st.markdown("### Executive Summary")
        render_executive_summary_card(executive_summary)

        if gpt_note:
            st.markdown("### OpenAI Final Recommendation")
            render_research_note_html(gpt_note)

        if not ranking_table.empty:
            st.markdown("### Recommendation Snapshot")
            snap_cols = [
                "Final Rank", "Ticker", "Research View", "Final Research Score", "Best Attribute",
                "Biggest Weakness", "Valuation Label", "Technical Signal", "Price Target Upside",
            ]
            snap_cols = [c for c in snap_cols if c in combined_scorecard.columns]
            st.dataframe(make_display_df(combined_scorecard[snap_cols]), use_container_width=True, hide_index=True)

        st.markdown("### Framework")
        st.info(f"**{peer_group}** — {get_sector_config(peer_group).get('description', '')}")

    with chart_tab:
        st.markdown("### Price Return Chart")
        selected_period = st.radio(
            "Select return period",
            PRICE_RETURN_PERIODS,
            horizontal=True,
            index=PRICE_RETURN_PERIODS.index("1Y") if "1Y" in PRICE_RETURN_PERIODS else 0,
        )
        chart_df = build_price_return_long_df(price_history, selected_period)
        period_return_table = build_selected_period_return_table(chart_df)
        if period_return_table.empty:
            st.info("No price history was available for the selected chart period.")
        else:
            st.dataframe(make_display_df(period_return_table), use_container_width=True, hide_index=True)
            pivot = chart_df.pivot(index="date", columns="Ticker", values="Price Return")
            st.line_chart(pivot, use_container_width=True)

    with sections_tab:
        st.markdown("### Simplified Report Sections")
        for section_name in [
            "Profile", "Ratings", "Factor Grades", "Momentum", "Total Return",
            "Valuation", "Growth", "Profitability", "Balance Sheet / Leverage",
        ]:
            table_df = report_tables.get(section_name, pd.DataFrame())
            if table_df.empty:
                continue
            st.markdown(f"#### {section_name}")
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            if section_name in {"Valuation", "Growth", "Profitability", "Balance Sheet / Leverage", "Momentum"}:
                drivers = build_section_drivers(section_name.replace(" / Leverage", ""), combined_scorecard)
                if drivers:
                    st.markdown("**Research Takeaways**")
                    for d in drivers:
                        st.write(f"- {d}")

    with audit_tab:
        st.markdown("### Sector Metric Coverage")
        render_sector_metric_coverage_audit(combined_scorecard, peer_group)
        st.markdown("### Raw Combined Scorecard")
        st.dataframe(combined_scorecard, use_container_width=True, height=650)

    with downloads_tab:
        display_df = make_display_df(combined_scorecard)
        raw_csv = combined_scorecard.to_csv(index=False).encode("utf-8")
        display_csv = display_df.to_csv(index=False).encode("utf-8")
        ranking_csv = ranking_table.to_csv(index=False).encode("utf-8") if not ranking_table.empty else b""
        excel_bytes = payload.get("excel_bytes")
        if excel_bytes is None:
            excel_bytes = generate_excel_report(
                combined_scorecard,
                ranking_table,
                report_tables,
                payload.get("valuation_explanations", pd.DataFrame()),
                payload.get("technical_explanations", pd.DataFrame()),
                payload.get("technical_scorecard", pd.DataFrame()),
                executive_summary=executive_summary,
                gpt_note=gpt_note,
                peer_group=peer_group,
            )

        st.download_button("Download PDF Report", data=pdf_bytes, file_name=f"equity_research_report_{'_'.join(tickers[:5])}.pdf", mime="application/pdf")
        st.download_button("Download Excel Research Pack", data=excel_bytes, file_name=f"equity_research_pack_{'_'.join(tickers[:5])}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download Display CSV", data=display_csv, file_name="equity_research_display.csv", mime="text/csv")
        st.download_button("Download Raw CSV", data=raw_csv, file_name="equity_research_raw.csv", mime="text/csv")
        if ranking_csv:
            st.download_button("Download Ranking CSV", data=ranking_csv, file_name="equity_research_ranking.csv", mime="text/csv")



# =============================================================================
# V5 presentation polish: consistent report styling + CIO-level narrative
# =============================================================================
def _clean_report_text(value: object) -> str:
    """Normalize report text so Streamlit markdown does not switch fonts/formats."""
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Streamlit/Markdown can treat dollar signs as LaTeX math delimiters. Use USD.
    s = s.replace("$", "USD ")
    # Remove common markdown emphasis characters that create mixed font weights mid-sentence.
    s = s.replace("**", "").replace("__", "")
    # Normalize odd spacing while preserving paragraph breaks.
    paragraphs = []
    for p in s.split("\n\n"):
        lines = [" ".join(line.split()) for line in p.split("\n") if line.strip()]
        if lines:
            paragraphs.append("\n".join(lines))
    return "\n\n".join(paragraphs).strip()


def inject_equity_research_report_css() -> None:
    """Small scoped CSS layer to keep the research note visually consistent."""
    st.markdown(
        """
        <style>
        .er-card {
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            padding: 18px 20px;
            background: #FFFFFF;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            margin: 6px 0 18px 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            color: #111827;
            line-height: 1.55;
        }
        .er-card p { margin: 0 0 12px 0; font-size: 0.96rem; }
        .er-card ul { margin-top: 6px; margin-bottom: 14px; padding-left: 1.25rem; }
        .er-card li { margin-bottom: 7px; font-size: 0.95rem; }
        .er-section-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: #0F172A;
            margin: 16px 0 7px 0;
            padding-top: 8px;
            border-top: 1px solid #EEF2F7;
        }
        .er-section-title:first-child { border-top: none; margin-top: 0; padding-top: 0; }
        .er-subsection-title {
            font-size: 0.96rem;
            font-weight: 700;
            color: #1F2937;
            margin: 14px 0 8px 0;
            padding: 7px 10px;
            background: #F8FAFC;
            border-left: 4px solid #CBD5E1;
            border-radius: 8px;
        }
        .er-ticker-line {
            margin: 0 0 9px 0;
            padding: 9px 11px;
            background: #FFFFFF;
            border: 1px solid #EEF2F7;
            border-radius: 10px;
            font-size: 0.94rem;
        }
        .er-ticker-line strong {
            color: #0F172A;
            font-weight: 700;
        }
        .er-card-divider {
            height: 1px;
            background: #EEF2F7;
            margin: 12px 0;
        }
        .er-kicker {
            display: inline-block;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #64748B;
            font-weight: 700;
            margin-bottom: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _html_escape(s: object) -> str:
    import html
    return html.escape(str(s or ""), quote=True)


def _format_note_lines_as_html(note: str) -> str:
    """Convert GPT text into a cleaner executive note with separated sections/subsections."""
    clean = _clean_report_text(note)
    if not clean:
        return "<p>No recommendation note was generated.</p>"

    section_aliases = {
        "final recommendation by ticker": "Final Recommendation by Ticker",
        "final recommendation": "Final Recommendation by Ticker",
        "best idea and why": "Best Idea and Why",
        "best idea": "Best Idea and Why",
        "key supporting evidence": "Key Supporting Evidence",
        "key drivers": "Key Supporting Evidence",
        "biggest risks or watch-items": "Biggest Risks / Watch Items",
        "biggest risks / watch items": "Biggest Risks / Watch Items",
        "biggest risks": "Biggest Risks / Watch Items",
        "main risks": "Biggest Risks / Watch Items",
        "analyst conclusion": "Analyst Conclusion",
        "investment conclusion": "Analyst Conclusion",
    }

    subsection_aliases = {
        "valuation": "Valuation",
        "growth": "Growth",
        "profitability and cash flow": "Profitability and Cash Flow",
        "profitability & cash flow": "Profitability and Cash Flow",
        "cash flow and profitability": "Profitability and Cash Flow",
        "balance sheet": "Balance Sheet",
        "balance sheet / leverage": "Balance Sheet",
        "leverage": "Balance Sheet",
        "momentum and analyst support": "Momentum and Analyst Support",
        "momentum & analyst support": "Momentum and Analyst Support",
        "momentum": "Momentum and Analyst Support",
    }

    ticker_set = set()
    try:
        # A conservative ticker pattern: 1-5 capital letters followed by a colon.
        import re
        ticker_set = set(re.findall(r"(?m)^[-•* ]*([A-Z]{1,5}):", clean))
    except Exception:
        ticker_set = set()

    html_parts = []
    open_ul = False

    def close_ul_if_needed():
        nonlocal open_ul
        if open_ul:
            html_parts.append("</ul>")
            open_ul = False

    for raw in clean.split("\n"):
        line = raw.strip()
        if not line:
            close_ul_if_needed()
            continue

        normalized = line.lower().strip(" #:.-")
        title = section_aliases.get(normalized)
        if title:
            close_ul_if_needed()
            html_parts.append(f'<div class="er-section-title">{_html_escape(title)}</div>')
            continue

        subtitle = subsection_aliases.get(normalized)
        if subtitle:
            close_ul_if_needed()
            html_parts.append(f'<div class="er-subsection-title">{_html_escape(subtitle)}</div>')
            continue

        # Convert colon-only heading lines that are not ticker lines.
        if line.endswith(":") and len(line) < 80 and not any(ch.isdigit() for ch in line):
            maybe_heading = line[:-1].strip()
            maybe_norm = maybe_heading.lower().strip(" #:.-")
            if maybe_norm in section_aliases:
                close_ul_if_needed()
                html_parts.append(f'<div class="er-section-title">{_html_escape(section_aliases[maybe_norm])}</div>')
                continue
            if maybe_norm in subsection_aliases:
                close_ul_if_needed()
                html_parts.append(f'<div class="er-subsection-title">{_html_escape(subsection_aliases[maybe_norm])}</div>')
                continue
            close_ul_if_needed()
            html_parts.append(f'<div class="er-subsection-title">{_html_escape(maybe_heading)}</div>')
            continue

        is_bullet = line.startswith(("- ", "• ", "* "))
        content = line[2:].strip() if is_bullet else line

        # Ticker-specific evidence/risk lines display better as compact cards instead of one long wall of text.
        ticker_prefix = content.split(":", 1)[0].strip()
        if ticker_prefix in ticker_set and ":" in content:
            close_ul_if_needed()
            ticker, rest = content.split(":", 1)
            html_parts.append(
                f'<div class="er-ticker-line"><strong>{_html_escape(ticker.strip())}:</strong> '
                f'{_html_escape(rest.strip())}</div>'
            )
            continue

        if is_bullet:
            if not open_ul:
                html_parts.append("<ul>")
                open_ul = True
            html_parts.append(f"<li>{_html_escape(content)}</li>")
        else:
            close_ul_if_needed()
            html_parts.append(f"<p>{_html_escape(content)}</p>")

    close_ul_if_needed()
    return "".join(html_parts)


def render_executive_summary_card(summary: str) -> None:
    clean = _clean_report_text(summary)
    st.markdown(
        f'<div class="er-card"><span class="er-kicker">Investment committee readout</span><p>{_html_escape(clean)}</p></div>',
        unsafe_allow_html=True,
    )


def render_research_note_html(note: str) -> None:
    body = _format_note_lines_as_html(note)
    st.markdown(f'<div class="er-card">{body}</div>', unsafe_allow_html=True)


def build_executive_summary_paragraph(scorecard: pd.DataFrame) -> str:
    """Override: more polished executive-investment-officer style summary."""
    if scorecard is None or scorecard.empty:
        return "No reportable findings were available because the scorecard is empty."

    tmp = scorecard.copy()
    if "Ticker" not in tmp.columns and "ticker" in tmp.columns:
        tmp = tmp.rename(columns={"ticker": "Ticker"})

    sort_metric = None
    if "Final Research Score" in tmp.columns and tmp["Final Research Score"].notna().any():
        sort_metric = "Final Research Score"
    elif "Composite Score" in tmp.columns and tmp["Composite Score"].notna().any():
        sort_metric = "Composite Score"
    elif "Price Target Upside" in tmp.columns and tmp["Price Target Upside"].notna().any():
        sort_metric = "Price Target Upside"

    if sort_metric:
        tmp = tmp.sort_values(sort_metric, ascending=False).reset_index(drop=True)

    lead = tmp.iloc[0].get("Ticker") if not tmp.empty else None
    lag = tmp.iloc[-1].get("Ticker") if len(tmp) > 1 else None
    lead_score = formatted_value_for_ticker(tmp, lead, sort_metric) if lead and sort_metric else "N/A"
    lead_view = tmp.iloc[0].get("Research View", "top-ranked setup") if not tmp.empty else "top-ranked setup"

    growth_leader = winner_for_metric(tmp, "Revenue CAGR 3Y", True)
    margin_leader = winner_for_metric(tmp, "Latest Operating Margin", True)
    fcf_leader = winner_for_metric(tmp, "FCF Yield", True)
    upside_leader = winner_for_metric(tmp, "Price Target Upside", True)
    technical_leader = winner_for_metric(tmp, "1Y Return", True)

    evidence = []
    if growth_leader:
        evidence.append(f"growth leadership from {growth_leader} ({formatted_value_for_ticker(tmp, growth_leader, 'Revenue CAGR 3Y')} 3-year revenue CAGR)")
    if margin_leader:
        evidence.append(f"operating efficiency from {margin_leader} ({formatted_value_for_ticker(tmp, margin_leader, 'Latest Operating Margin')} operating margin)")
    if fcf_leader:
        evidence.append(f"cash-flow support from {fcf_leader} ({formatted_value_for_ticker(tmp, fcf_leader, 'FCF Yield')} FCF yield)")
    if upside_leader:
        evidence.append(f"analyst target support from {upside_leader} ({formatted_value_for_ticker(tmp, upside_leader, 'Price Target Upside')} implied upside)")
    if technical_leader:
        evidence.append(f"market leadership from {technical_leader} ({formatted_value_for_ticker(tmp, technical_leader, '1Y Return')} trailing 1-year return)")

    lead_sentence = (
        f"{lead} is the highest-ranked idea in the current peer review, with a research score of {lead_score} "
        f"and a classification of {lead_view}."
        if lead else "The peer review produced a ranked view of the selected companies."
    )

    evidence_sentence = ""
    if evidence:
        if len(evidence) == 1:
            evidence_sentence = f"The key support point is {evidence[0]}."
        else:
            evidence_sentence = "The ranking is supported by " + "; ".join(evidence[:-1]) + f"; and {evidence[-1]}."

    risk_sentence = ""
    if lag and lag != lead and sort_metric:
        lag_score = formatted_value_for_ticker(tmp, lag, sort_metric)
        lag_weakness = tmp.iloc[-1].get("Biggest Weakness", "weaker relative setup")
        risk_sentence = (
            f"The lower-ranked name is {lag}, with a score of {lag_score}; the main watch item is {lag_weakness}. "
            "For an executive investment review, the practical takeaway is to separate durable compounders from names that require a better entry point, stronger estimate revisions, or cleaner technical confirmation."
        )

    conclusion = (
        "Overall, the report favors names where growth, margins, balance-sheet quality, valuation support, and momentum align, "
        "while treating high multiple expansion or overextended price action as risk controls rather than standalone sell signals."
    )
    return _clean_report_text(" ".join([lead_sentence, evidence_sentence, risk_sentence, conclusion]))


def summarize_scorecard_with_gpt(records: List[dict], openai_api_key: str, model: str = "gpt-5") -> Optional[str]:
    """Override: CIO-ready investment note with consistent markdown-safe formatting."""
    if not openai_api_key or not records:
        return None
    client = OpenAI(api_key=openai_api_key)
    prompt = f"""
You are a senior equity research analyst preparing an investment committee note for an executive investment officer.

Use only the structured scorecard data provided. Do not invent missing data. Write in a professional buy-side tone.

Formatting rules:
- Use the exact section headings below.
- Add a blank line between every major section.
- Under Key Supporting Evidence, use the subsection headings Valuation, Growth, Profitability and Cash Flow, Balance Sheet, and Momentum and Analyst Support on their own lines.
- Put each ticker-specific evidence point on its own line using this format: TICKER: explanation.
- Use concise bullets only under Final Recommendation by Ticker and Biggest Risks / Watch Items.
- Do not use dollar signs; write USD instead, for example USD 62.6B.
- Do not use markdown tables.
- Do not use bold, italics, code formatting, emojis, or LaTeX.
- Avoid raw formula language unless essential.
- Explain what the metrics mean for the investment decision, not just what the numbers are.

Required structure:
Final Recommendation by Ticker
- TICKER: Buy, Hold, or Sell — one-sentence rationale.

Best Idea and Why
- Identify the best risk/reward idea and explain why it should matter to an executive investment officer.

Key Supporting Evidence
- Valuation: explain whether the multiple is justified by quality/growth.
- Growth: explain durability and forward estimate support.
- Profitability and cash flow: explain operating quality and reinvestment capacity.
- Balance sheet: explain financial flexibility and risk.
- Momentum and analyst support: explain entry-point quality and confirmation/risk.

Biggest Risks / Watch Items
- Summarize the main risk for each major name, including valuation, overbought technicals, slowing growth, leverage, or weak target upside where applicable.

Analyst Conclusion
- One polished paragraph with portfolio action: what to buy or accumulate, what to hold, and what needs a better entry point or better evidence.

Structured peer data:
{json.dumps(records, default=str, indent=2)}
"""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a disciplined, executive-ready CFA-style equity research analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        return _clean_report_text(resp.choices[0].message.content.strip())
    except Exception as e:
        return f"GPT final recommendation generation failed: {e}"


def generate_story_pdf_report(
    scorecard: pd.DataFrame,
    report_tables: Dict[str, pd.DataFrame],
    tickers: List[str],
    executive_summary: str,
    gpt_note: Optional[str],
    peer_group: str,
) -> bytes:
    """Override: tight one-page PDF with cleaner text and no tall narrative boxes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.25 * inch,
        leftMargin=0.25 * inch,
        topMargin=0.22 * inch,
        bottomMargin=0.22 * inch,
    )
    styles = getSampleStyleSheet()
    styles["Title"].fontSize = 12
    styles["Title"].leading = 13
    styles["Heading2"].fontSize = 8
    styles["Heading2"].leading = 9
    styles["BodyText"].fontSize = 6.2
    styles["BodyText"].leading = 7.1
    styles["BodyText"].fontName = "Helvetica"

    story = []
    title = f"Equity Research Summary: {', '.join(tickers)}"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(f"Framework: {_html_escape(peer_group)}", styles["BodyText"]))

    summary = _shorten_pdf_cell(_clean_report_text(executive_summary or "No executive summary available."), 430)
    story.append(Paragraph(f"<b>Executive summary:</b> {_html_escape(summary)}", styles["BodyText"]))

    if gpt_note:
        # Keep PDF one-page. Full note remains in the app and Excel export.
        note = _shorten_pdf_cell(_clean_report_text(str(gpt_note)), 360)
        story.append(Paragraph(f"<b>OpenAI recommendation note:</b> {_html_escape(note)}", styles["BodyText"]))

    compact_df = _one_page_pdf_rows(report_tables)
    if not compact_df.empty:
        story.append(Spacer(1, 0.05 * inch))
        story.append(dataframe_to_one_page_pdf_table(compact_df))
    else:
        story.append(Paragraph("No compact report table was available.", styles["BodyText"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
