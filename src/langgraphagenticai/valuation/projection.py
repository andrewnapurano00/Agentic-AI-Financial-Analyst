"""Explicit dated earnings bridge; consensus forecasts are not reported facts."""
from datetime import date, datetime
from langgraphagenticai.valuation.model import number


def projection_basis(facts, years):
    """Legacy results retain their arithmetic; new results use quote-relative exits."""
    if facts.get("projection_method") != "dated-consensus-v1":
        return dict(value=facts["basis"], years=float(years), date=facts.get("as_of"),
                    target_date=None, kind="historical annual earnings proxy" if facts.get("earnings_proxy") else "historical annual", analysts=None)
    quoted = datetime.fromisoformat(facts["quote_as_of"]).date()
    try:
        target = quoted.replace(year=quoted.year + years)
    except ValueError:  # February 29 in a non-leap target year.
        target = quoted.replace(year=quoted.year + years, day=28)
    annual = date.fromisoformat(facts["as_of"])
    anchor = dict(value=facts["basis"], date=annual.isoformat(), kind="historical annual earnings proxy" if facts.get("earnings_proxy") else "historical annual", analysts=None)
    # A short forecast bridge avoids anchoring long-term value to a sparse distant year.
    # Use only normalized same-currency annual consensus with at least three analysts.
    if facts.get("method") == "P/E" and facts.get("forecast_anchor_eligible") is True:
        candidates = []
        for row in facts.get("estimates", []):
            dated = date.fromisoformat(row["date"])
            eps, count = number(row.get("eps")), number(row.get("analysts"))
            if (0 < (dated - quoted).days <= 550 and dated < target and eps is not None
                    and eps > 0 and count is not None and count >= 3 and count.is_integer()
                    and row.get("currency") == facts.get("currency")):
                candidates.append(row)
        if candidates:
            # Nearest forward FY avoids skipping the most visible earnings year.
            selected = min(candidates, key=lambda row: row["date"])
            same_date = [r for r in candidates if r["date"] == selected["date"]]
            if len(same_date) == 1:
                anchor = dict(value=selected["eps"], date=selected["date"],
                              kind="annual consensus forecast", analysts=selected["analysts"])
    elapsed = (target - date.fromisoformat(anchor["date"])).days / 365.25
    if elapsed <= 0:
        raise ValueError("Projection anchor must precede the target date.")
    return dict(**anchor, years=elapsed, target_date=target.isoformat())


def projection_context(facts):
    return {str(years): projection_basis(facts, years) for years in (3, 4, 5)}


def consensus_growth_path(facts):
    """Comparable forecast-to-forecast CAGR guides; no invented extrapolation."""
    if not facts.get("eligible") or facts.get("projection_method") != "dated-consensus-v1":
        return []
    anchor = projection_basis(facts, 5)
    if anchor["kind"] != "annual consensus forecast":
        return []
    result = []
    dates = [row["date"] for row in facts.get("estimates", [])]
    for row in facts.get("estimates", []):
        elapsed = (date.fromisoformat(row["date"]) - date.fromisoformat(anchor["date"])).days / 365.25
        if elapsed > 0 and row["currency"] == facts["currency"] and dates.count(row["date"]) == 1:
            result.append(dict(date=row["date"], eps=row["eps"], analysts=row["analysts"],
                               implied_annual_growth_pct=100 * ((row["eps"] / anchor["value"]) ** (1 / elapsed) - 1)))
    return result
