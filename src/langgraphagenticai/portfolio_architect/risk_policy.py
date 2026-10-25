"""Saved, deterministic allocation policy and hypothetical shocks; no forecasts."""
from datetime import date
import math
from .optimizer import validate_weights
from .risk import diagnostics
from .schemas import utc_stamp


def check_volatility(securities, weights, mandate, snapshot):
    """Reject rather than silently change cash, caps, selection or user policy."""
    limit = mandate.historical_volatility_cap
    if limit is None:
        return
    risk = diagnostics(securities, weights)
    try:
        reference = utc_stamp(snapshot.retrieved_at)
        current = risk.end is not None and 0 <= (reference.date()-date.fromisoformat(risk.end)).days <= 10
        for security in securities:
            retrieved = utc_stamp(security.history_retrieved_at)
            current = current and 0 <= (reference-retrieved).total_seconds() <= 30*86400
            current = current and max(security.history) <= reference.date().isoformat()
    except (ValueError, TypeError):
        current = False
    if risk.status != "available" or not current or risk.annualized_volatility is None:
        raise ValueError("Historical-volatility policy cannot be checked: refresh aligned history (at least 60 returns, 90% coverage, end within 10 days and retrieval within 30 days of snapshot). Review the policy explicitly; no limit was relaxed.")
    if risk.annualized_volatility > limit+1e-9:
        raise ValueError(f"Historical-volatility ceiling exceeded: {risk.annualized_volatility:.2%} versus {limit:.2%}. Explicitly increase minimum cash, revise holdings/sizing, or edit the ceiling and Build again. No policy was relaxed; previous results remain available.")


def stress_loss(securities, weights, cash, shocks):
    """One-period fractional price shocks on top-level holdings, zero cash shock."""
    if set(weights) != {s.ticker for s in securities} or abs(sum(weights.values())+cash-1) > 1e-9:
        raise ValueError("Stress allocation does not reconcile.")
    if not math.isfinite(cash) or cash < 0 or any(not math.isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError("Stress requires finite long-only weights.")
    if set(shocks) != set(weights) or any(not math.isfinite(v) or v < -1 for v in shocks.values()):
        raise ValueError("Every holding needs an explicit finite fractional shock >= -100%.")
    return sum(weights[t]*shocks[t] for t in weights)


def policy_summary(securities, weights, cash, mandate, snapshot):
    validate_weights(securities, weights, cash, mandate)
    check_volatility(securities, weights, mandate, snapshot)
    for security in securities:
        if (security.ticker in mandate.forbidden
                or (mandate.assets == "stocks" and security.asset != "stock")
                or (mandate.assets == "etfs" and security.asset != "etf")
                or security.sector in mandate.excluded_sectors
                or (mandate.excluded_sectors and security.asset == "etf")):
            raise ValueError("Final holding violates asset, ticker or sector exclusions. Review mandate; no exclusion was relaxed.")
    sectors = {}
    for s in securities:
        sectors[s.sector] = sectors.get(s.sector, 0)+weights[s.ticker]
    checks = [
        {"constraint":"long_only_position_cap", "limit":mandate.position_cap, "actual":max(weights.values()), "passed":True},
        {"constraint":"top_level_sector_category_cap", "limit":mandate.sector_cap, "actual":max(sectors.values()), "passed":True},
        {"constraint":"minimum_cash", "limit":mandate.cash, "actual":cash, "passed":True},
        {"constraint":"holdings_count", "limit":mandate.holdings, "actual":len(weights), "passed":True},
        {"constraint":"total_weight", "limit":1., "actual":sum(weights.values())+cash, "passed":True},
        {"constraint":"asset_ticker_sector_exclusions", "limit":{"assets":mandate.assets, "forbidden":mandate.forbidden, "excluded_sectors":mandate.excluded_sectors}, "actual":[s.ticker for s in securities], "passed":True},
    ]
    if mandate.historical_volatility_cap is not None:
        checks.append({"constraint":"historical_volatility_ceiling", "limit":mandate.historical_volatility_cap,
                       "actual":diagnostics(securities, weights).annualized_volatility, "passed":True})
    warnings = []
    if max(weights.values()) >= .2-1e-9:
        warnings.append("High top-level concentration: a position is at least 20% of capital.")
    if max(sectors.values()) >= .4-1e-9:
        warnings.append("High top-level concentration: a sector/category is at least 40% of capital.")
    scenarios = []
    for name, stock, etf in [("All risky holdings -20%", -.2, -.2), ("Stocks -30%; every ETF -15%", -.3, -.15), ("All risky holdings +10%", .1, .1)]:
        shocks = {s.ticker:stock if s.asset == "stock" else etf for s in securities}
        loss = stress_loss(securities, weights, cash, shocks)
        scenarios.append({"scenario":name, "holding_price_shocks":shocks, "cash_shock":0., "account_return":loss,
                          "account_change_usd":loss*mandate.amount})
    return {"schema":"axiom-risk-policy-v1", "snapshot_id":snapshot.id, "retrieved_at":snapshot.retrieved_at,
            "tolerance":1e-9, "checks":checks, "warnings":warnings,
            "descriptive_only":["risk preference", "horizon", "AI conviction", "historical drawdown", "correlation", "risk-budget shares"],
            "volatility_basis":"Sample daily price returns ddof=1, 252 sessions/year, common dates, no covariance shrinkage; static daily-rebalanced weights; cash/risk-free 0%. Historical estimate, no future loss guarantee. Ceiling checks evidence age relative to saved snapshot, not current freshness.",
            "etf_look_through":{"status":"unknown" if any(s.asset == "etf" for s in securities) else "not_applicable", "exposure":None, "reason":"No eligible dated constituent holdings collected; category caps cannot enforce underlying exposures."},
            "benchmark_relative_weights":{"status":"unavailable", "weights":None, "reason":"Benchmark constituent weights unavailable; a price series does not establish holdings."},
            "turnover_and_transaction_costs":{"status":"unavailable", "value":None, "reason":"No current account holdings, execution prices or cost assumptions supplied."},
            "stress_scenarios":scenarios,
            "stress_basis":"Hypothetical one-period top-level price shocks, weighted sum; cash unchanged. ETF shocks apply to the whole fund regardless of constituents. No probabilities, forecast, taxes, fees, trading or correlation model.",
            "purpose":"Educational model portfolio; no personalized suitability assessment or execution."}
