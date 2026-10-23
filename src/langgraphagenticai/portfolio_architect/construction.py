"""Bounded NumPy portfolio construction; no expected-return estimates or providers."""
import numpy as np
from .risk import aligned_returns, shrunk_covariance


CONVICTION = {"low": .8, "medium": 1., "high": 1.2}


def project_weights(values, sectors, budget, position_cap, sector_cap):
    """Euclidean projection onto a long-only capped simplex with disjoint sectors."""
    values = np.asarray(values, dtype=float)
    groups = [np.array([i for i, s in enumerate(sectors) if s == name]) for name in sorted(set(sectors))]
    floor = 1e-7  # Keep each requested holding positive; not an executable lot size.
    if (len(values)*floor > budget or any(len(g)*floor > sector_cap for g in groups)
            or sum(min(len(g)*position_cap, sector_cap) for g in groups) < budget-1e-10):
        raise ValueError("Insufficient allocation capacity for the requested cash and caps.")

    thresholds = np.full(len(values), -np.inf)
    for indices in groups:
        if np.clip(values[indices], floor, position_cap).sum() > sector_cap or sector_cap < len(indices)*position_cap:
            low, high = float(values[indices].min()-position_cap), float(values[indices].max())
            for _ in range(50):
                mid = (low+high)/2
                if np.clip(values[indices]-mid, floor, position_cap).sum() > sector_cap:
                    low = mid
                else:
                    high = mid
            thresholds[indices] = high

    def at(multiplier):
        return np.clip(values-np.maximum(multiplier, thresholds), floor, position_cap)

    low = float(values.min()-position_cap-1)
    high = float(values.max()+1)
    for _ in range(70):
        mid = (low+high)/2
        if at(mid).sum() > budget:
            low = mid
        else:
            high = mid
    return at(high)


def risk_budget_weights(covariance, budgets):
    """Cyclic coordinate descent on .5*x'C*x - sum(b_i*log(x_i))."""
    cov = np.asarray(covariance, dtype=float)
    cov = cov/np.max(np.diag(cov))
    budgets = np.asarray(budgets, dtype=float)
    budgets = budgets/budgets.sum()
    x = np.sqrt(budgets/np.diag(cov))
    for _ in range(2000):
        for i in range(len(x)):
            cross = cov[i]@x-cov[i, i]*x[i]
            root = np.sqrt(cross*cross+4*cov[i, i]*budgets[i])
            x[i] = 2*budgets[i]/(root+cross) if cross >= 0 else (root-cross)/(2*cov[i, i])
        shares = x*(cov@x)/(x@cov@x)
        if np.max(np.abs(shares-budgets)) < 1e-8:
            return x/x.sum()
    raise ValueError("Risk-budget solver did not converge.")


def minimum_variance_weights(covariance, sectors, mandate):
    """Projected gradient descent with a fixed Lipschitz step and explicit caps."""
    cov = np.asarray(covariance, dtype=float)
    cov = cov/np.max(np.diag(cov))
    lipschitz = float(np.linalg.eigvalsh(cov).max())
    project = lambda x: project_weights(x, sectors, 1-mandate.cash, mandate.position_cap, mandate.sector_cap)
    x = project(np.full(len(sectors), (1-mandate.cash)/len(sectors)))
    for _ in range(2000):
        updated = project(x-cov@x/lipschitz)
        if np.max(np.abs(updated-x)) < 1e-9:
            return updated
        x = updated
    raise ValueError("Minimum-variance solver did not converge.")


def quantitative_weights(securities, mandate, conviction=None):
    returns, coverage = aligned_returns(securities)
    if returns is None:
        return None, coverage
    cov = shrunk_covariance(returns)
    if not np.isfinite(cov).all() or np.min(np.diag(cov)) < 1e-16:
        return None, "Zero or unstable historical variance."
    names = list(returns.columns)
    by_name = {s.ticker:s for s in securities}
    sectors = [by_name[n].sector for n in names]
    try:
        if mandate.method == "min_variance":
            weights = minimum_variance_weights(cov, sectors, mandate)
            note = "Constrained minimum historical variance; 20% diagonal-shrunk sample covariance, no expected-return input."
        else:
            valid = bool(conviction) and all(conviction.get(n) in CONVICTION for n in names)
            budgets = [CONVICTION[conviction[n]] if mandate.method == "ai_risk_budget" and valid else 1. for n in names]
            raw = risk_budget_weights(cov, budgets)*(1-mandate.cash)
            weights = project_weights(raw, sectors, 1-mandate.cash, mandate.position_cap, mandate.sector_cap)
            note = "Covariance risk budgets, followed by closest-weight projection to position/sector caps. Caps can change achieved risk shares."
            if mandate.method == "ai_risk_budget":
                note += " AI conviction sets relative risk budgets at 0.8/1.0/1.2; not expected returns." if valid else " Validated AI conviction unavailable; equal risk budgets used."
        return dict(zip(names, weights.tolist())), note+" "+coverage
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return None, "Quantitative solver failed or did not converge; equal-weight allocation subject to caps retained."


def allocation_analytics(securities, weights, mandate, conviction=None):
    """Risk shares use the exact sizing covariance; negatives indicate hedging."""
    returns, note = aligned_returns(securities)
    if returns is None:
        return {"status":"unavailable", "reason":note}
    cov = shrunk_covariance(returns)
    names = list(returns.columns)
    w = np.array([weights[n] for n in names])
    variance = float(w@cov@w)
    if not np.isfinite(variance) or variance <= 1e-16:
        return {"status":"unavailable", "reason":"Zero or unstable portfolio variance."}
    vol = np.sqrt(np.diag(cov))
    valid = bool(conviction) and all(conviction.get(n) in CONVICTION for n in names)
    budgets = np.array([CONVICTION[conviction[n]] if mandate.method == "ai_risk_budget" and valid else 1. for n in names])
    budgets /= budgets.sum()
    target = dict(zip(names, budgets.tolist())) if mandate.method in {"risk_parity", "ai_risk_budget"} else {}
    return {"status":"available", "basis":"Sizing covariance: sample daily price returns, 20% diagonal shrinkage; 252 sessions/year; cash return/risk-free assumption 0%. Not a forecast.",
            "start":min(set.intersection(*(set(s.history) for s in securities))), "end":str(returns.index[-1]),
            "observations":len(returns), "coverage":note,
            "risk_contributions":dict(zip(names, (w*(cov@w)/variance).tolist())),
            "target_risk_budgets":target,
            "sizing_annualized_volatility":float(np.sqrt(variance*252)),
            "diversification_ratio":float(w@vol/np.sqrt(variance)),
            "effective_holdings":float(1/np.sum((w/w.sum())**2)),
            "limitations":"Risk shares can be negative for hedges; caps can prevent target budgets. Effective holdings is concentration-based. ETF look-through, future returns and suitability are unmeasured."}
