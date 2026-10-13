"""D01-D10: deterministic opening-company contracts, without provider or UI calls.

Calculated and documented FMP percentage ratios are fractions. Units come from
the provider field contract, never from a number's magnitude.
"""
from datetime import date
import math


KEY_STATISTICS = (
    ("Market Cap", "market_cap"), ("Enterprise Value", "enterprise_value"),
    ("P/E (TTM)", "pe_ttm"), ("P/E (FWD)", "pe_forward"),
    ("PEG", "peg"), ("P/S", "price_to_sales"),
    ("P/B", "price_to_book"), ("EV/EBITDA", "ev_ebitda"),
    ("Beta", "beta"), ("Dividend Yield", "dividend_yield"),
    ("Volume", "volume"), ("Avg Volume", "avg_volume"),
)
GROWTH_STATISTICS = (
    ("Revenue Growth YoY", "revenue_growth"), ("Revenue 3Y CAGR", "revenue_cagr_3y"),
    ("Revenue 5Y CAGR", "revenue_cagr_5y"), ("Gross Margin", "gross_margin"),
    ("Operating Margin", "operating_margin"), ("Net Margin", "net_margin"),
    ("FCF Margin", "fcf_margin"), ("ROIC", "roic"),
    ("ROE", "roe"), ("ROA", "roa"),
    ("Debt/Equity", "debt_to_equity"), ("Current Ratio", "current_ratio"),
)
PERCENT_METRICS = {key for _, key in GROWTH_STATISTICS} - {"debt_to_equity", "current_ratio"}
PERCENT_METRICS.add("dividend_yield")


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def matching_rows(payload, symbol):
    """Ticker-specific endpoints must identify their security, never first-row wins."""
    rows = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict) and str(row.get("symbol", "")).strip().upper() == symbol]


def day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def field_number(row, *fields):
    for field in fields:
        value = finite(row.get(field))
        if value is not None:
            return value, field
    return None, fields[0]


def fiscal_year(row):
    return row.get("fiscalYear") or row.get("calendarYear")


def quarters(rows, limit=8):
    normalized = {}
    conflicts = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        period, stamp = str(row.get("period", "")).upper(), day(row.get("date"))
        try:
            year = int(fiscal_year(row))
        except (TypeError, ValueError):
            continue
        if period not in {"Q1", "Q2", "Q3", "Q4"} or stamp is None or stamp > date.today():
            continue
        key = year * 4 + int(period[1])
        if key in normalized and normalized[key] != row:
            conflicts.add(key)
        normalized[key] = row
    selected = sorted(normalized.items(), reverse=True)[:limit]
    if conflicts.intersection(rank for rank, _ in selected):
        return []  # Conflicting restatements in this window require a policy.
    currencies = {str(row.get("reportedCurrency", "")).upper() for _, row in selected}
    if len(currencies) != 1 or not next(iter(currencies), ""):
        return []
    for (rank, current), (prior_rank, prior) in zip(selected, selected[1:]):
        if rank - prior_rank != 1 or not 60 <= (day(current["date"]) - day(prior["date"])).days <= 130:
            return []
    return [row for _, row in selected]


def total(rows, field):
    values = [finite(row.get(field)) for row in rows]
    return sum(values) if len(values) == 4 and all(value is not None for value in values) else None


def ratio(numerator, denominator):
    numerator, denominator = finite(numerator), finite(denominator)
    return finite(numerator / denominator) if numerator is not None and denominator not in (None, 0) else None


def fiscal_window(rows):
    return tuple((str(fiscal_year(row)), row.get("period"), row.get("date"), row.get("reportedCurrency")) for row in rows)


def annual_cagr(rows, years):
    """Requires all n+1 consecutive same-currency FY records, not calendar approximations."""
    annual = {}
    for row in rows:
        stamp, value = day(row.get("date")), finite(row.get("revenue"))
        try:
            year = int(fiscal_year(row))
        except (TypeError, ValueError):
            continue
        if row.get("period") != "FY" or stamp is None or stamp > date.today():
            continue
        if year in annual and annual[year] != row:
            return None, []
        annual[year] = row
    if not annual:
        return None, []
    latest = max(annual)
    selected = [annual.get(latest - index) for index in range(years + 1)]
    if any(row is None for row in selected):
        return None, []
    if any(finite(row.get("revenue")) is None or finite(row.get("revenue")) <= 0 for row in selected):
        return None, []
    currencies = {str(row.get("reportedCurrency") or "").upper() for row in selected}
    if len(currencies) != 1 or not next(iter(currencies)):
        return None, []
    if any(not 330 <= (day(left["date"]) - day(right["date"])).days <= 400 for left, right in zip(selected, selected[1:])):
        return None, []
    return finite((float(selected[0]["revenue"]) / float(selected[-1]["revenue"])) ** (1 / years) - 1), selected


def metric(value=None, *, basis="Unavailable", unit="ratio", as_of=None, currency=None, fields=(), reason="", raw=None, inputs=()):
    value = finite(value)
    return {"value": value, "basis": basis, "unit": unit, "as_of": as_of, "currency": currency,
            "provider": "Financial Modeling Prep", "fields": list(fields), "status": "available" if value is not None else "unavailable",
            "reason": reason if value is None else "", "raw": raw, "inputs": list(inputs)}


def build_metrics(snapshot, annual=(), estimates=()):
    quote, profile = snapshot.get("quote", {}), snapshot.get("profile", {})
    evidence = snapshot.get("terminal_evidence", {})
    ratios, keys = evidence.get("ratios", {}), evidence.get("metrics", {})
    income = quarters(evidence.get("income", []), 8)
    cash = quarters(evidence.get("cashflow", []), 4)
    current_rows = quarters(evidence.get("income", []), 4)
    current, prior = current_rows if len(current_rows) == 4 else [], income[4:8] if len(income) == 8 else []
    through = current[0]["date"] if current else None
    currency = current[0].get("reportedCurrency") if current else None
    result = {key: metric(reason="Input or validated definition unavailable") for _, key in KEY_STATISTICS + GROWTH_STATISTICS}
    for key in ("market_cap", "volume", "avg_volume"):
        source = quote.get("avg_volume_source", "quote.avgVolume") if key == "avg_volume" else {"market_cap": "quote.marketCap", "volume": "quote.volume"}[key]
        result[key] = metric(quote.get(key), basis="Quote" if key != "avg_volume" else "Provider average; window unknown",
                             unit="currency" if key == "market_cap" else "provider volume units", currency=quote.get("currency"),
                             as_of=None if source.startswith("profile.") else quote.get("timestamp"), fields=(source,))
        if source.startswith("profile."):
            result[key]["basis"] = "Profile average; observation date / window unknown"
    result["market_cap"]["listing_currency"] = profile.get("currency")
    result["beta"] = metric(profile.get("beta"), basis="Profile; estimation window unknown", fields=("beta",))
    direct = {"pe_ttm": ("priceToEarningsRatioTTM", "peRatioTTM", "priceEarningsRatioTTM"),
              "peg": ("priceToEarningsGrowthRatioTTM", "pegRatioTTM"),
              "price_to_sales": ("priceToSalesRatioTTM", "priceSalesRatioTTM"),
              "price_to_book": ("priceToBookRatioTTM", "pbRatioTTM"),
              "debt_to_equity": ("debtToEquityRatioTTM", "debtEquityRatioTTM"), "current_ratio": ("currentRatioTTM",)}
    for key, fields in direct.items():
        value, field = field_number(ratios, *fields)
        result[key] = metric(value, basis="Provider TTM; latest retrieved, valuation date not supplied", fields=(field,), as_of=ratios.get("date"))
    for key, fields in (("enterprise_value", ("enterpriseValueTTM", "enterpriseValue")),
                        ("ev_ebitda", ("evToEBITDATTM", "enterpriseValueOverEBITDATTM", "enterpriseValueMultipleTTM"))):
        value, field = field_number(keys, *fields)
        if value is None:
            value, field = field_number(ratios, *fields)
        result[key] = metric(value, basis="Provider TTM; latest retrieved, valuation date not supplied", unit="currency" if key == "enterprise_value" else "ratio", fields=(field,), as_of=keys.get("date"))
    result["enterprise_value"]["listing_currency"] = profile.get("currency")
    # FMP financial formulas define these ratios as fractions; display *100 only.
    for key, fields, source in (("roic", ("returnOnInvestedCapitalTTM", "roicTTM"), keys),
                               ("roe", ("returnOnEquityTTM", "roeTTM"), keys),
                               ("roa", ("returnOnAssetsTTM",), keys),
                               ("dividend_yield", ("dividendYieldTTM",), ratios)):
        value, field = field_number(source, *fields)
        result[key] = metric(value, unit="fraction", basis="Provider TTM; FMP fraction convention; period end not supplied",
                             fields=(field,), as_of=source.get("date"), raw=value)
    forward = forward_estimate(estimates)
    price = finite(quote.get("price"))
    eps = forward.get("eps")
    listing_currency = quote.get("currency") or profile.get("currency")
    estimate_currency = forward.get("currency")
    compatible = not (listing_currency and estimate_currency and listing_currency != estimate_currency)
    result["pe_forward"] = metric(ratio(price, eps) if price is not None and price > 0 and eps is not None and eps > 0 and compatible else None,
                                    basis="Calculated quote / next annual consensus EPS; forecast, not TTM",
                                    as_of=forward.get("date"), fields=("quote.price", forward.get("field", "epsAvg")), inputs=forward.get("inputs", []),
                                    reason="Positive price/future annual EPS missing or explicit currencies differ")
    result["pe_forward"]["note"] = "Assumes EPS and quote use the same listing currency unless explicit metadata contradicts it; EPS GAAP/adjustment basis not supplied. Quote observation and estimate FY end are separate."
    revenue = total(current, "revenue")
    revenue = revenue if revenue is not None and revenue > 0 else None
    for key, field in (("gross_margin", "grossProfit"), ("operating_margin", "operatingIncome"), ("net_margin", "netIncome")):
        result[key] = metric(ratio(total(current, field), revenue), basis="Calculated standalone-quarter TTM", unit="fraction", as_of=through,
                             currency=currency, fields=(field, "revenue"), inputs=current)
    if not current:
        for key, field in (("gross_margin", "grossProfitMarginTTM"), ("operating_margin", "operatingProfitMarginTTM"), ("net_margin", "netProfitMarginTTM")):
            result[key] = metric(ratios.get(field), basis="Provider TTM fallback; quarterly calculation unavailable", unit="fraction", fields=(field,), as_of=ratios.get("date"))
            result[key]["note"] = "Provider-supplied ratio, not audited/calculated quarterly TTM. Provider period end not supplied."
    previous_revenue = total(prior, "revenue")
    growth = ratio(revenue, previous_revenue) if previous_revenue is not None and previous_revenue > 0 else None
    result["revenue_growth"] = metric(growth - 1 if growth is not None else None, basis="Calculated TTM vs prior TTM", unit="fraction", as_of=through,
                                      currency=currency, fields=("revenue",), inputs=current + prior)
    aligned = len(cash) == len(current) == 4 and fiscal_window(cash) == fiscal_window(current)
    result["fcf_margin"] = metric(ratio(total(cash, "freeCashFlow"), revenue) if aligned else None, basis="Calculated matching-quarter TTM", unit="fraction", as_of=through,
                                 currency=currency, fields=("freeCashFlow", "revenue"), inputs=current + cash,
                                 reason="Income/cash-flow fiscal dates/currencies do not match, or inputs missing")
    for years in (3, 5):
        value, inputs = annual_cagr(annual, years)
        result[f"revenue_cagr_{years}y"] = metric(value, basis=f"Calculated annual FY {years}Y CAGR", unit="fraction",
                                                as_of=inputs[0]["date"] if inputs else None,
                                                currency=inputs[0].get("reportedCurrency") if inputs else None,
                                                fields=("revenue", "fiscalYear", "date", "reportedCurrency"), inputs=inputs,
                                                reason=f"Requires {years + 1} consecutive positive same-currency FY revenues")
    return result


def forward_estimate(rows, today=None):
    """Annual estimate route only; never substitute a past period for forward EPS."""
    today = today or date.today()
    future = sorted((row for row in rows if isinstance(row, dict) and day(row.get("date")) and day(row["date"]) >= today), key=lambda row: row["date"])
    if not future:
        return {}
    row = future[0]
    eps, field = field_number(row, "epsAvg", "estimatedEpsAvg", "estimatedEps")
    count, _ = field_number(row, "numAnalystsEps", "numberAnalystEstimatedEps")
    return {"date": row["date"], "eps": eps, "field": field, "analysts": count if count is not None and count >= 0 and count.is_integer() else None,
            "currency": row.get("reportedCurrency") or row.get("currency"), "inputs": [row]}


def analyst_summary(snapshot, evidence):
    rating = evidence.get("grades", {})
    target = evidence.get("targets", {})
    estimates = forward_estimate(evidence.get("estimates", []))
    price = finite(snapshot.get("quote", {}).get("price"))
    value, _ = field_number(target, "targetConsensus", "priceTargetConsensus", "targetMean")
    currency = snapshot.get("quote", {}).get("currency") or snapshot.get("profile", {}).get("currency")
    target_currency = target.get("currency") or target.get("reportedCurrency")
    mismatch = bool(currency and target_currency and currency != target_currency)
    upside = ratio(value, price) if value is not None and value > 0 and price is not None and price > 0 and not mismatch else None
    return {"consensus": str(rating.get("consensus") or "Unavailable")[:80], "count": estimates.get("analysts"),
            "estimate_date": estimates.get("date"), "target": value, "upside": upside - 1 if upside is not None else None,
            "currency": target_currency, "listing_currency": currency, "retrieved_at": evidence.get("retrieved_at"),
            "note": "FMP current consensus; target/rating observation dates not supplied. Count is EPS contributors for the shown annual estimate, not all unique rating analysts. Target upside assumes target and quote share listing currency; EPS/target currency and adjustment conventions are not certified."}


def earnings_events(rows, today=None):
    today = today or date.today()
    events = []
    seen = set()
    for row in rows:
        stamp = day(row.get("date"))
        if stamp is None or stamp in seen:
            continue
        seen.add(stamp)
        actual, estimate = finite(row.get("epsActual")), finite(row.get("epsEstimated"))
        comparison = "Unavailable comparison" if actual is None or estimate is None else "Beat" if actual > estimate else "Miss" if actual < estimate else "Equal"
        surprise = ratio(actual - estimate, abs(estimate)) if actual is not None and estimate not in (None, 0) else None
        events.append({"date": stamp.isoformat(), "actual": actual, "estimate": estimate,
                       "surprise": surprise, "comparison": comparison, "last_updated": row.get("lastUpdated")})
    events.sort(key=lambda row: row["date"], reverse=True)
    reported = [row for row in events if row["actual"] is not None and day(row["date"]) <= today][:4]
    upcoming = sorted((row for row in events if day(row["date"]) > today and row["actual"] is None), key=lambda row: row["date"])
    return {"reported": reported, "next_event": upcoming[0] if upcoming else None,
            "basis": "Provider EPS; GAAP/adjustment/currency unverified. Announcement dates; fiscal-quarter labels unavailable."}


def compatible_peer_metrics(selected, peer):
    """Latest peer ratios with explicit period labels, never a same-date audit claim."""
    result = {}
    for key in ("revenue_growth", "gross_margin", "operating_margin", "pe_ttm", "roic"):
        reference, item = selected[key], dict(peer[key])
        if key in {"pe_ttm", "roic"}:
            item["note"] = "Latest provider TTM snapshots; period/valuation dates not supplied. Not a same-date audited comparison."
        elif item.get("as_of") != reference.get("as_of") or item.get("currency") != reference.get("currency") or item.get("basis") != reference.get("basis"):
            item["note"] = "Latest available TTM ratios; fiscal dates/currencies/bases differ. Period end and basis are disclosed per peer; dimensionless ratios do not aggregate currency amounts."
        result[key] = item
    return result


def summary_financial_context(snapshot):
    """Bounded metadata for explicit AI; never recalculate saved financial values.

    A missing legacy basis remains unknown. Statement periods, filings, quote
    observations and retrieval time are separate concepts, not interchangeable.
    """
    original = snapshot.get("fundamental_basis", {})
    basis = {key: original.get(key) for key in ("period", "through", "currency", "status")}
    known_ttm = basis["period"] == "TTM" and day(basis["through"]) is not None
    provenance = {}
    calculated = {"revenue_ttm": "sum four standalone-quarter revenues", "revenue_growth": "current four-quarter revenue / prior four-quarter revenue - 1",
                  "operating_margin": "four-quarter operating income / matching positive revenue", "net_margin": "four-quarter net income / matching positive revenue",
                  "free_cash_flow_ttm": "sum four cash-flow quarters with exact income fiscal dates/currency"}
    for field, formula in calculated.items():
        provenance[field] = {"source": "Financial Modeling Prep statements; local calculation",
                             "basis": "Calculated quarterly TTM" if known_ttm else "Saved financial basis unverified",
                             "period_end": basis["through"] if known_ttm else None, "currency": basis["currency"],
                             "unit": "fraction" if field in {"revenue_growth", "operating_margin", "net_margin"} else "currency amount",
                             "formula": formula if known_ttm else "Unavailable",
                             "assumption": "Standalone fiscal quarters assumed; provider semantics not independently certified"}
    for field in ("pe_ttm", "price_to_sales", "price_to_book", "debt_to_equity"):
        provenance[field] = {"source": "Financial Modeling Prep ratios-ttm", "basis": "Provider TTM; undated",
                             "period_end": None, "currency": None, "unit": "multiple / ratio",
                             "assumption": "Provider formula/valuation date conventions unverified; not a same-date calculated financial fact"}
    for field in ("roe", "roic", "fcf_yield"):
        provenance[field] = {"source": "Financial Modeling Prep key-metrics-ttm", "basis": "Provider TTM; undated",
                             "period_end": None, "unit": "fraction", "assumption": "FMP documented ratio convention; not locally audited quarterly balance-return metrics. Missing values are not zero"}
    periods = {}
    for dataset in ("income", "cashflow"):
        periods[dataset] = [{key: str(row.get(key))[:64] if row.get(key) is not None else None
                             for key in ("symbol", "fiscalYear", "period", "date", "reportedCurrency", "filingDate", "fillingDate", "acceptedDate")}
                            for row in snapshot.get("terminal_evidence", {}).get(dataset, [])[:8] if isinstance(row, dict)]
    return {"fundamental_basis": basis, "fundamental_provenance": provenance, "statement_period_metadata": periods,
            "performance_basis": {"as_of": snapshot.get("performance", {}).get("as_of"),
                                  "price_basis": "Snapshot historical close; adjustment basis unverified", "return_type": "Price return, not certified total return",
                                  "return_windows": "1M/3M/1Y use 21/63/252 observed daily bars; volatility sqrt(252)",
                                  "currency": "Unverified unless supplied by the quote; profile currency is separate metadata"},
            "date_semantics": "fetched_at is retrieval time, not statement period end, filing/availability date, quote timestamp or proof of freshness"}
