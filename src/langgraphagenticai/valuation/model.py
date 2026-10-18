"""Annual-basis contracts and reproducible nominal exit-price arithmetic."""
from datetime import datetime, timezone
import math
import re

from langgraphagenticai.deep_research.sector import map_sector_to_framework, GENERAL_FRAMEWORK
from langgraphagenticai.state.research_context import normalize_company_symbol


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def currency(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Z]{3}", value) else None


def prepare(raw, *, now=None, acknowledge_units=False, use_disclosed_assumptions=False, dated_projection=False):
    """Unknown units require an explicit assumption; known conflicts never do."""
    now = now or datetime.now(timezone.utc)
    symbol = normalize_company_symbol(raw.get("symbol"))
    reasons, warnings = [], list(raw.get("warnings", []))
    sources = raw.get("sources", {})
    rows = {}
    for kind in ("quote", "profile", "income", "balance", "estimates"):
        candidates = raw.get(kind, [])
        rows[kind] = [r for r in candidates if isinstance(r, dict) and r.get("symbol") == symbol]
        if len(rows[kind]) != len(candidates):
            reasons.append(f"{kind.title()} identity mismatch; reload evidence.")
    profile = (rows["profile"] or [{}])[0]
    quote = (rows["quote"] or [{}])[0]
    framework = map_sector_to_framework(profile.get("sector"), profile.get("industry"))
    method = "P/B" if framework == "Banks / Financials" else "P/E"
    family = "financial" if method == "P/B" else "operating"
    if framework == GENERAL_FRAMEWORK and not use_disclosed_assumptions:
        reasons.append("Sector classification is unavailable; a supported sector method is required.")
    if framework == "Real Estate / REITs" and not use_disclosed_assumptions:
        reasons.append("Verified FFO/AFFO per share is unavailable. REIT targets require a specialist method.")
    if framework in ("Materials", "Energy") and not use_disclosed_assumptions:
        reasons.append("Validated mid-cycle earnings are unavailable. Commodity-cycle targets require normalized earnings.")
    conditional_energy = framework == "Energy" and use_disclosed_assumptions
    annuals = {}
    annual_issues = {"income": [], "balance": []}
    for kind in ("income", "balance"):
        valid = []
        seen = set()
        for row in rows[kind]:
            try:
                dated = datetime.strptime(row.get("date", ""), "%Y-%m-%d").date()
                if row.get("period") != "FY" or dated > now.date():
                    raise ValueError("Invalid annual date/basis")
                if dated in seen:
                    annual_issues[kind].append(f"Duplicate {kind} fiscal date; reload unambiguous statements.")
                    continue
                seen.add(dated)
                # Future filing/acceptance dates cannot establish presently available evidence.
                for field in ("filingDate", "acceptedDate"):
                    if row.get(field) and str(row[field])[:10] > now.date().isoformat():
                        raise ValueError("Future publication")
                valid.append(row)
            except (ValueError, TypeError):
                warnings.append(f"An invalid/future/non-FY {kind} record was excluded.")
        annuals[kind] = sorted(valid, key=lambda row: row["date"], reverse=True)
    from .framework import usable_book, earnings_basis, method_disclosure
    financial_fallback = False
    if method == "P/B" and use_disclosed_assumptions:
        from .book_value import common_book_value
        balance = (annuals["balance"] or [{}])[0]
        contract = common_book_value(balance, raw.get("balance_reported", []), today=now.date())
        known_currencies = {c for c in (currency(balance.get("reportedCurrency")), currency(quote.get("currency")), currency(profile.get("currency"))) if c}
        if annual_issues["balance"] or not usable_book(balance, contract, sources, known_currencies, now):
            method, family, financial_fallback = "P/E", "operating", True
    for kind, issues in annual_issues.items():
        if not use_disclosed_assumptions or kind == ("balance" if method == "P/B" else "income"):
            reasons.extend(issues)
        else:
            warnings.extend(issues)
    earnings_proxy = False
    relevant = annuals["balance"] if method == "P/B" else annuals["income"]
    latest = (relevant or [{}])[0]
    basis, shares, formula = None, None, ""
    basis_source_ids, book_contract = [], {}
    if method == "P/B":
        from .book_value import common_book_value
        book_contract = common_book_value(latest, raw.get("balance_reported", []), today=now.date())
        basis, shares = book_contract["value"], book_contract["shares"]
        basis_source_ids = [f"balance:{rows['balance'].index(latest)}"] if latest else []
        if book_contract["reported_index"] is not None:
            basis_source_ids.append(f"balance_reported:{book_contract['reported_index']}")
            warnings.append(book_contract["note"] + "; year-end shares, not diluted weighted-average shares.")
        formula = "Common equity / fiscal year-end common shares; common equity = stockholders' equity minus explicit preferred stock when direct common equity is absent."
    else:
        basis, earnings_proxy = earnings_basis(latest, allow_proxy=use_disclosed_assumptions)
        basis_source_ids = [f"income:{rows['income'].index(latest)}"] if latest else []
        shares = number(latest.get("weightedAverageShsOutDil"))
        if shares is None or shares <= 0:
            reasons.append("Positive annual diluted weighted-average shares are required to establish the EPS basis.")
        profit = number(latest.get("netIncome"))
        if profit is not None and profit <= 0:
            reasons.append("Non-positive annual net income requires a specialist method; P/E targets are disabled.")
        formula = "Annual net income / annual diluted weighted-average shares; earnings proxy, not reported diluted EPS." if earnings_proxy else "Provider-reported annual diluted EPS; no TTM substitution or annualization."
    if basis is None or basis <= 0:
        reasons.append(f"Positive verified annual {'common book value per share' if method == 'P/B' else 'diluted EPS'} is required.")
    as_of = latest.get("date")
    if not as_of or (now.date() - datetime.strptime(as_of, "%Y-%m-%d").date()).days > 550:
        reasons.append("Annual basis is missing or older than the 550-day policy.")
    price = number(quote.get("price"))
    if price is None or price <= 0:
        reasons.append("A positive current quote is required.")
    quote_as_of = None
    try:
        stamp = number(quote.get("timestamp"))
        if stamp is None:
            raise ValueError("No quote date")
        instant = datetime.fromtimestamp(stamp, timezone.utc)
        if instant > now or (now - instant).total_seconds() > 7 * 86400:
            raise ValueError("Stale/future quote")
        quote_as_of = instant.isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        reasons.append("Quote date is missing, future, or older than seven UTC calendar days.")
    try:
        retrieved = datetime.fromisoformat(str(raw.get("retrieved_at", "")).replace("Z", "+00:00"))
        if retrieved.tzinfo is None or retrieved > now or (now - retrieved).total_seconds() > 86400:
            raise ValueError("Stale retrieval")
    except (ValueError, TypeError):
        reasons.append("Evidence retrieval is undated or older than 24 hours; explicitly refresh it.")
    required_sources = ["quote", "profile", "balance" if method == "P/B" else "income"]
    if book_contract.get("reported_index") is not None:
        required_sources.append("balance_reported")
    for kind in required_sources:
        try:
            timestamp = datetime.fromisoformat(str(sources.get(kind, {}).get("retrieved_at", "")).replace("Z", "+00:00"))
            if timestamp.tzinfo is None or timestamp > now or (now - timestamp).total_seconds() > 86400:
                raise ValueError("Invalid source retrieval")
        except (TypeError, ValueError):
            reasons.append(f"{kind.title()} source retrieval is unverified or older than 24 hours; explicitly refresh it.")
    reported = currency(latest.get("reportedCurrency"))
    quote_currency, profile_currency = currency(quote.get("currency")), currency(profile.get("currency"))
    if not reported:
        reasons.append("Statement currency is unverified.")
    known = {c for c in (reported, quote_currency, profile_currency) if c}
    if len(known) > 1:
        reasons.append("Known quote/profile/statement currency mismatch; resolve FX and quote units before pricing.")
    if not quote_currency and not profile_currency:
        reasons.append("Quote currency is unavailable from both quote and profile.")
    if not acknowledge_units and not use_disclosed_assumptions:
        reasons.append("Confirm quote/statement units and corporate-action compatibility before calculating targets.")
    warnings.append("Annual per-share values are not verified as split-adjusted to the latest quote. Quote adjustment basis and original statement monetary/share scaling are unverified; no FX conversion or rescaling is applied.")
    if not quote_currency and profile_currency:
        warnings.append("Trading currency is profile-reported. Conditional targets assume it matches the quoted price units; direct quote currency is unavailable.")
    method_label, method_note = method_disclosure(framework, method, financial_fallback=financial_fallback, earnings_proxy=earnings_proxy)
    if method_note:
        warnings.append(method_note)
    history = []
    for row in relevant:
        if currency(row.get("reportedCurrency")) != reported:
            continue
        value = earnings_basis(row, allow_proxy=earnings_proxy)[0] if method == "P/E" else None
        if method == "P/E" and earnings_basis(row, allow_proxy=earnings_proxy)[1] != earnings_proxy:
            continue  # Do not calculate growth across reported EPS and a net-income proxy.
        if method == "P/B":
            value = common_book_value(row, raw.get("balance_reported", []), today=now.date())["value"]
        if value is not None:
            record = {"date": row["date"], "value": value}
            if method == "P/B":
                contract = common_book_value(row, raw.get("balance_reported", []), today=now.date())
                record["source_ids"] = [f"balance:{rows['balance'].index(row)}"]
                if contract["reported_index"] is not None:
                    record["source_ids"].append(f"balance_reported:{contract['reported_index']}")
            history.append(record)
    estimates = []
    forecast_anchor_eligible = False
    try:
        forecast_retrieved = datetime.fromisoformat(str(sources.get("estimates", {}).get("retrieved_at", "")).replace("Z", "+00:00"))
        forecast_anchor_eligible = forecast_retrieved.tzinfo is not None and 0 <= (now - forecast_retrieved).total_seconds() <= 86400
    except (TypeError, ValueError):
        pass  # Undated forecasts remain context, never a numeric projection anchor.
    for row in rows["estimates"]:
        try:
            dated = datetime.strptime(row.get("date", ""), "%Y-%m-%d").date()
            count = next((number(row.get(k)) for k in ("numAnalystsEps", "numberAnalystEstimatedEps", "numberAnalystsEstimatedEps") if number(row.get(k)) is not None), None)
            if dated <= now.date() or count is None or count < 1 or not count.is_integer():
                continue
            eps = next((number(row.get(k)) for k in ("epsAvg", "estimatedEpsAvg", "estimatedEps") if number(row.get(k)) is not None), None)
            estimate_currency = currency(row.get("reportedCurrency")) or currency(row.get("currency"))
            # Annual route supplies the period basis. Fiscal year-end must match the actual annual issuer calendar.
            comparable = bool(as_of and abs((dated-dated.replace(month=int(as_of[5:7]), day=min(int(as_of[8:10]),28))).days) <= 45)
            if row.get("period") not in (None, "FY", "annual", "ANNUAL") or not comparable or eps is None or eps <= 0:
                continue
            if estimate_currency and reported and estimate_currency != reported:
                warnings.append("A forward estimate currency conflicted with the annual basis and was excluded.")
                continue
            estimates.append({"date": row["date"], "eps": eps, "analysts": count, "currency": estimate_currency or reported, "currency_basis": "provider-reported" if estimate_currency else "assumed same issuer/reporting currency; estimate currency not supplied", "basis": "forward annual consensus; forecast, not reported earnings", "annual_actual_date": as_of})
        except (TypeError, ValueError):
            continue
    if earnings_proxy:
        forecast_anchor_eligible = False
    if dated_projection and estimates and not forecast_anchor_eligible and not earnings_proxy:
        warnings.append("Forecast retrieval is undated, future or older than 24 hours; forecasts are excluded from the numeric earnings anchor.")
    return dict(method_label=method_label, method_note=method_note, financial_fallback=financial_fallback, earnings_proxy=earnings_proxy, basis_label="Annual earnings / diluted share (proxy)" if earnings_proxy else "Annual BVPS" if method == "P/B" else "Annual diluted EPS", conditional_energy=conditional_energy, basis_source_ids=basis_source_ids, book_value_contract=book_contract, forecast_anchor_eligible=forecast_anchor_eligible, projection_method="dated-consensus-v1" if dated_projection else "legacy-annual", symbol=symbol, company=profile.get("companyName") or symbol, sector=profile.get("sector") or "Unknown", industry=profile.get("industry") or "Unknown", framework=framework, family=family, method=method, eligible=not reasons, reasons=list(dict.fromkeys(reasons)), warnings=list(dict.fromkeys(warnings)), price=price, basis=basis, shares=shares, currency=reported or "Unknown", quote_currency=quote_currency or profile_currency or "Unknown", as_of=as_of, quote_as_of=quote_as_of, retrieved_at=raw.get("retrieved_at"), formula=formula, current_multiple=price / basis if price and basis and basis > 0 else None, history=history, estimates=sorted(estimates,key=lambda r:r["date"]), sources=sources, units_acknowledged=acknowledge_units or use_disclosed_assumptions, compatibility_basis="disclosed scenario assumptions" if use_disclosed_assumptions else "user reviewed")


def calculate_ai_cases(facts, years, cases, *, hurdle=.10):
    """AI selects three scenario drivers; deterministic arithmetic sets target/upside."""
    if {c["name"] for c in cases} != {"Bear", "Base", "Bull"} or len(cases) != 3:
        raise ValueError("Exactly three named valuation cases are required.")
    output = {}
    for name in ("Bear", "Base", "Bull"):
        case = next(c for c in cases if c["name"] == name)
        growth, multiple = number(case.get("growth_pct")), number(case.get("terminal_multiple"))
        if growth is None or multiple is None:
            raise ValueError("Finite scenario growth and multiple required.")
        row = calculate(facts, years, growth / 100, multiple, hurdle=hurdle)["Base"]
        output[name] = {**row, "rationale": case["rationale"], "evidence_ids": case["evidence_ids"]}
    if not output["Bear"]["target"] <= output["Base"]["target"] <= output["Bull"]["target"]:
        raise ValueError("AI case prices must be ordered Bear ≤ Base ≤ Bull.")
    return output


def calculate(facts, years, growth, terminal_multiple, *, hurdle=0.10):
    """Prices are future nominal exits; price returns exclude dividends and dilution."""
    if not facts.get("eligible"):
        raise ValueError("Valuation evidence is ineligible.")
    vals = [number(v) for v in (growth, terminal_multiple, hurdle, facts.get("basis"), facts.get("price"))]
    if any(v is None for v in vals):
        raise ValueError("Finite valuation inputs are required.")
    growth, terminal_multiple, hurdle, basis, price = vals
    if isinstance(years, bool) or years not in (3, 4, 5) or not -.45 <= growth <= .60 or not .1 <= terminal_multiple <= 300 or not 0 <= hurdle <= .50 or basis <= 0 or price <= 0:
        raise ValueError("Valuation inputs are outside supported bounds.")
    from langgraphagenticai.valuation.projection import projection_basis
    anchor = projection_basis(facts, years)
    result = {}
    for name, delta, factor in (("Bear", -.04, .75), ("Base", 0, 1), ("Bull", .04, 1.25)):
        g, multiple = growth + delta, terminal_multiple * factor
        end = anchor["value"] * (1 + g) ** anchor["years"]
        target = end * multiple
        result[name] = dict(growth=g, exit_multiple=multiple, end_basis=end, projection=anchor, target=target, price_return=target / price - 1, cagr=(target / price) ** (1 / years) - 1, review_price=target / (1 + hurdle) ** years)
    return result
