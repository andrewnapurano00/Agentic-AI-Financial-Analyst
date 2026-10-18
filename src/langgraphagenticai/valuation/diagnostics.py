"""Calculated assumption checks and reverse targets; never a price forecast."""
from datetime import date
from langgraphagenticai.valuation.model import number
from langgraphagenticai.valuation.projection import projection_basis, consensus_growth_path


def driver_diagnostics(facts, cases, years):
    anchor = projection_basis(facts, years)
    base = next(case for case in cases if case["name"] == "Base")
    rows = [
        {"Driver": "Base annual earnings growth", "Value": f"{base['growth_pct']:.2f}%", "Basis": "After the displayed earnings anchor"},
        {"Driver": "Base exit multiple", "Value": f"{base['terminal_multiple']:.2f}x", "Basis": facts["method"]},
        {"Driver": "Reference price / anchor earnings", "Value": f"{facts['price']/anchor['value']:.2f}x", "Basis": anchor["kind"] + " / " + str(anchor["date"])},
    ]
    history = sorted(facts.get("history", []), key=lambda row: row["date"], reverse=True)
    if len(history) >= 2:
        latest, prior = history[:2]
        gap = (date.fromisoformat(latest["date"]) - date.fromisoformat(prior["date"])).days
        if 330 <= gap <= 400 and prior["value"] > 0:
            rows.append({"Driver": "Historical annual per-share growth", "Value": f"{100*(latest['value']/prior['value']-1):.2f}%",
                         "Basis": f"Reported fiscal dates {prior['date']} to {latest['date']}; not a forecast"})
    path = [row for row in consensus_growth_path(facts)
            if row["analysts"] >= 3 and (not anchor["target_date"] or row["date"] <= anchor["target_date"])]
    comparison = max(path, key=lambda row: row["date"]) if path else None
    if comparison:
        rows.append({"Driver": "Consensus earnings growth", "Value": f"{comparison['implied_annual_growth_pct']:.2f}%",
                     "Basis": f"Annualized forecast path {anchor['date']} to {comparison['date']}; not the full target horizon"})
    # An informative review flag, never an automatic rescaling or growth floor.
    near_flat = (comparison is not None and comparison["implied_annual_growth_pct"] >= 5
                 and all(abs(case["growth_pct"]) <= 1 for case in cases))
    return dict(rows=rows, near_flat=near_flat, forecast_comparison=comparison)


def target_requirements(facts, cases, years, *, price_factor=2.):
    """Reverse the exact target formula, keeping a user's thesis hypothetical."""
    factor = number(price_factor)
    price = number(facts.get("price"))
    if factor is None or factor <= 0 or price is None or price <= 0 or not facts.get("eligible"):
        raise ValueError("Positive finite price and target factor required.")
    anchor = projection_basis(facts, years)
    rows = []
    for case in cases:
        multiple = number(case.get("terminal_multiple"))
        if multiple is None or multiple <= 0:
            raise ValueError("Positive finite exit multiples required.")
        target = factor * price
        earnings = target / multiple
        growth = ((earnings / anchor["value"]) ** (1 / anchor["years"]) - 1) * 100
        rows.append({"Case multiple": case["name"], "Exit multiple": multiple,
                     "Hypothetical target": target, "Required exit EPS / BVPS": earnings,
                     "Required annual growth (%)": growth})
    return rows
