"""Conservative, reproducible TTM calculations from standardized quarterly flows."""
from datetime import date
import math

METHODOLOGY = "sector-quarterly-audit-v2"
INCOME_FIELDS = ("revenue", "grossProfit", "operatingIncome", "ebitda", "netIncome", "researchAndDevelopmentExpenses")
CASH_FIELDS = ("netCashProvidedByOperatingActivities", "operatingCashFlow", "capitalExpenditure", "freeCashFlow", "stockBasedCompensation")


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def divide(top, bottom):
    top, bottom = number(top), number(bottom)
    return top / bottom if top is not None and bottom is not None and bottom > 0 else None


def window(rows, symbol, offset=0, count=4):
    """Reject ambiguous restatements rather than picking a provider row silently."""
    normalized = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Quarterly records must be objects.")
        valid_duration, duration_reason = flow_duration(row)
        if not valid_duration:
            raise ValueError(duration_reason)
        period = str(row.get("period", "")).upper()
        if period not in {"Q1", "Q2", "Q3", "Q4"}:
            raise ValueError("Quarterly data contains a non-quarterly period.")
        try:
            year = int(row.get("fiscalYear"))
            day = date.fromisoformat(str(row.get("date")))
        except (TypeError, ValueError):
            raise ValueError("Missing or invalid fiscal identity/date.") from None
        if not 1900 <= year <= 2200 or abs(day.year - year) > 1 or day > date.today():
            raise ValueError("Implausible fiscal identity/date.")
        key = year * 4 + int(period[1]) - 1
        if key in normalized and normalized[key] != row:
            raise ValueError("Ambiguous duplicate/restated fiscal quarter.")
        normalized[key] = row
    selected = sorted(normalized.items(), reverse=True)[offset:offset + count]
    if len(selected) != count or any(a[0] - b[0] != 1 for a, b in zip(selected, selected[1:])):
        raise ValueError(f"{count} consecutive unique fiscal quarters are required.")
    selected = [row for _, row in selected]
    currency = selected[0].get("reportedCurrency")
    if not currency or any(row.get("symbol") != symbol or row.get("reportedCurrency") != currency for row in selected):
        raise ValueError("Quarterly security/currency identity is missing or inconsistent.")
    days = [date.fromisoformat(row["date"]) for row in selected]
    if any(not 60 <= (a - b).days <= 120 for a, b in zip(days, days[1:])):
        raise ValueError("Fiscal quarter dates are not chronologically plausible.")
    return selected


def aggregate(rows, symbol, fields, offset=0):
    quarters = window(rows, symbol, offset)
    result = {"symbol": symbol, "date": quarters[0]["date"], "period": "TTM",
              "reportedCurrency": quarters[0]["reportedCurrency"], "methodology": METHODOLOGY,
              "quarters": [{k: q.get(k) for k in ("date", "fiscalYear", "calendarYear", "period")} for q in quarters],
              "units": "Reported currency units (not scaled); standardized quarterly flow amounts",
              "formula": "Sum four standardized quarterly flows; missing/nonfinite components remain missing.",
              "duration_assumption": "Standardized routes assumed standalone quarters when duration absent; explicit YTD/as-reported/unknown duration rejected."}
    for field in fields:
        values = [number(q.get(field)) for q in quarters]
        result[field] = sum(values) if all(v is not None for v in values) else None
    if "freeCashFlow" in fields:
        result["fcf_formula_diagnostics"] = [{"date": q["date"], "reported_fcf": number(q.get("freeCashFlow")),
            "ocf_plus_signed_capex": number(q.get("netCashProvidedByOperatingActivities"))+number(q.get("capitalExpenditure"))
                if number(q.get("netCashProvidedByOperatingActivities")) is not None and number(q.get("capitalExpenditure")) is not None else None,
            "policy": "Diagnostic only; reported FCF remains the summed field; missing FCF is never fabricated."} for q in quarters]
    return result


def same_window(a, b):
    return bool(a and b and a.get("reportedCurrency") == b.get("reportedCurrency") and a.get("quarters") == b.get("quarters"))


def derived_ratios(income, cash, balance, quote, quote_currency, prior_balance=None):
    ratios, metrics = {}, {}
    revenue = income.get("revenue")
    for field, name in (("grossProfit", "grossProfitMarginTTM"), ("operatingIncome", "operatingProfitMarginTTM"),
                        ("netIncome", "netProfitMarginTTM"), ("ebitda", "ebitdaMarginTTM")):
        ratios[name] = divide(income.get(field), revenue)
    aligned = same_window(income, cash)
    balance_aligned = bool(balance and income and balance.get("date") == income.get("date") and balance.get("reportedCurrency") == income.get("reportedCurrency"))
    if balance_aligned:
        debt, equity = number(balance.get("totalDebt")), number(balance.get("totalStockholdersEquity"))
        ratios.update(debtToEquityRatioTTM=divide(debt, equity), debtToAssetsRatioTTM=divide(debt, balance.get("totalAssets")),
                      currentRatioTTM=divide(balance.get("totalCurrentAssets"), balance.get("totalCurrentLiabilities")))
        ratios["debtToCapitalRatioTTM"] = divide(debt, debt + equity) if debt is not None and equity is not None else None
        if prior_balance:
            try:
                days = (date.fromisoformat(balance["date"]) - date.fromisoformat(prior_balance["date"])).days
                current_year = int(balance.get("fiscalYear") or balance.get("calendarYear"))
                prior_year = int(prior_balance.get("fiscalYear") or prior_balance.get("calendarYear"))
                prior_aligned = (330 <= days <= 400 and current_year - prior_year == 1 and
                    balance.get("period") == prior_balance.get("period") and balance.get("symbol") == prior_balance.get("symbol") == income.get("symbol") and
                    balance.get("reportedCurrency") == prior_balance.get("reportedCurrency"))
            except (ValueError, TypeError, KeyError):
                prior_aligned = False
            if prior_aligned:
                for field, name in (("totalStockholdersEquity", "returnOnEquityTTM"), ("totalAssets", "returnOnAssetsTTM")):
                    beginning, ending = number(prior_balance.get(field)), number(balance.get(field))
                    ratios[name] = divide(income.get("netIncome"), (beginning + ending)/2) if beginning is not None and ending is not None and beginning > 0 and ending > 0 else None
                ratios["return_balance_window"] = {"beginning": prior_balance, "ending_date": balance.get("date"), "basis": "Average prior-year/end snapshot; not quarterly average."}
    cap = number(quote.get("marketCap"))
    quote_aligned = bool(income.get("symbol") and quote.get("symbol") == income.get("symbol"))
    if quote_aligned and cap is not None and cap > 0 and quote_currency and quote_currency == income.get("reportedCurrency"):
        for field, name in (("netIncome", "priceToEarningsRatioTTM"), ("revenue", "priceToSalesRatioTTM")):
            ratios[name] = divide(cap, income.get(field))
        ratios["earningsYieldTTM"] = divide(income.get("netIncome"), cap)
        if aligned:
            ratios["priceToFreeCashFlowRatioTTM"] = divide(cap, cash.get("freeCashFlow"))
            ratios["freeCashFlowYieldTTM"] = divide(cash.get("freeCashFlow"), cap)
        if balance_aligned:
            ratios["priceToBookRatioTTM"] = divide(cap, balance.get("totalStockholdersEquity"))
            debt, cash_eq = number(balance.get("totalDebt")), number(balance.get("cashAndCashEquivalents"))
            if debt is not None and cash_eq is not None:
                ev = cap + debt - cash_eq
                if ev > 0:
                    metrics.update(enterpriseValueOverEBITDATTM=divide(ev, income.get("ebitda")), evToSalesTTM=divide(ev, revenue),
                                   evToFreeCashFlowTTM=divide(ev, cash.get("freeCashFlow")) if aligned else None)
    ratios["metric_formulas"] = {
        "grossProfitMarginTTM": "TTM gross profit / TTM revenue", "operatingProfitMarginTTM": "TTM operating income / TTM revenue",
        "netProfitMarginTTM": "TTM net income / TTM revenue", "ebitdaMarginTTM": "TTM EBITDA / TTM revenue",
        "priceToEarningsRatioTTM": "Quote market cap / positive TTM net income", "priceToSalesRatioTTM": "Quote market cap / positive TTM revenue",
        "priceToBookRatioTTM": "Quote market cap / positive matched end equity", "priceToFreeCashFlowRatioTTM": "Quote market cap / positive aligned TTM FCF",
        "earningsYieldTTM": "TTM net income / positive quote market cap", "freeCashFlowYieldTTM": "Aligned TTM FCF / positive quote market cap",
        "debtToEquityRatioTTM": "Matched end total debt / positive equity", "debtToAssetsRatioTTM": "Matched end total debt / positive assets",
        "debtToCapitalRatioTTM": "Matched end total debt / positive (debt + equity)", "currentRatioTTM": "Matched end current assets / positive current liabilities",
        "returnOnEquityTTM": "TTM net income / average positive equity at matched TTM end and same quarter prior fiscal year",
        "returnOnAssetsTTM": "TTM net income / average positive assets at matched TTM end and same quarter prior fiscal year",
    }
    metrics["metric_formulas"] = {"enterpriseValueOverEBITDATTM": "Simplified EV / positive TTM EBITDA",
                                  "evToSalesTTM": "Simplified EV / positive TTM revenue", "evToFreeCashFlowTTM": "Simplified EV / positive aligned TTM FCF"}
    return ratios, metrics


def flow_duration(row):
    """Reject explicit cumulative/unknown flows rather than infer duration equivalence."""
    period=str(row.get("period") or "").upper()
    quarter=period in {"Q1","Q2","Q3","Q4"}
    annual=period in {"FY","ANNUAL"}
    if not quarter and not annual:
        return False,"Missing or invalid reported flow period."
    allowed={"quarter","quarterly","standalone","3m","3 months","90 days"} if quarter else {"annual","year","fy","12m","12 months","standalone"}
    for field in ("duration","periodType","reportingBasis"):
        value=str(row.get(field) or "").strip().lower()
        if value and value not in allowed:
            return False,"YTD/as-reported/unknown duration requires verified conversion; reported-period arithmetic excluded."
    if row.get("startDate"):
        try:
            span=(date.fromisoformat(str(row["date"]))-date.fromisoformat(str(row["startDate"]))).days
        except (ValueError,TypeError,KeyError):
            return False,"Invalid flow duration dates."
        lower,upper=(60,120) if quarter else (330,400)
        if not lower<=span<=upper:
            return False,"Flow duration does not match the declared standalone period."
    return True,"Duration absent: standardized standalone period assumed" if not any(row.get(f) for f in ("duration","periodType","reportingBasis","startDate")) else "Explicit standalone duration validated"
