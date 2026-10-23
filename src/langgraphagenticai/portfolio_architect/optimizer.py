"""Deterministic selection and nested cap allocation; no forecasts or order execution."""
from collections import defaultdict
from .risk import sizing_signals
from .construction import quantitative_weights

TOL = 1e-9


def capacity(securities, mandate):
    counts = defaultdict(int)
    for s in securities:
        counts[s.sector] += 1
    return sum(min(k*mandate.position_cap, mandate.sector_cap) for k in counts.values())


def select(securities, scores, mandate):
    if len(securities) < mandate.holdings:
        raise ValueError(f"Only {len(securities)} eligible securities; {mandate.holdings} requested. Revise exclusions or refresh evidence.")
    ranking = {s.ticker:s.score for s in scores}
    chosen = []
    remaining = {s.ticker:s for s in securities}
    for _ in range(mandate.holdings):
        def can_complete(candidate):
            proposed = chosen+[candidate]
            counts, available = defaultdict(int), defaultdict(int)
            for s in proposed:
                counts[s.sector] += 1
            for s in remaining.values():
                if s.ticker != candidate.ticker:
                    available[s.sector] += 1
            gains = []
            for sector, count in available.items():
                start = counts[sector]
                for j in range(count):
                    gains.append(min((start+j+1)*mandate.position_cap,mandate.sector_cap)
                                 -min((start+j)*mandate.position_cap,mandate.sector_cap))
            slots = mandate.holdings-len(proposed)
            return (len(gains) >= slots and capacity(proposed,mandate)+sum(sorted(gains,reverse=True)[:slots])
                    >= 1-mandate.cash-TOL)
        feasible = [s for s in remaining.values() if can_complete(s)]
        if not feasible:
            raise ValueError("Eligible sectors and position limits cannot fund the requested allocation. Increase cash/caps or revise the universe.")
        # Preserve mandate/AI ranking unless choosing a name would make completion impossible.
        next_security = max(feasible, key=lambda s:(ranking[s.ticker],s.ticker))
        chosen.append(next_security)
        remaining.pop(next_security.ticker)
    if capacity(chosen, mandate) < 1-mandate.cash-TOL:
        raise ValueError("Eligible sectors and position limits cannot fund the requested allocation. Increase cash/caps or revise the universe.")
    return chosen


def allocate(securities, mandate, conviction=None):
    signals, note = ({s.ticker:1. for s in securities}, "Equal-weight baseline subject to caps.")
    used = mandate.method
    if mandate.method in {"min_variance", "risk_parity", "ai_risk_budget"}:
        signals, note = quantitative_weights(securities, mandate, conviction)
        if signals is None:
            signals = {s.ticker:1. for s in securities}
            used = "equal (quantitative sizing unavailable)"
    elif mandate.method != "equal":
        signals, note = sizing_signals(securities)
        if signals is None:
            signals = {s.ticker:1. for s in securities}
            used = "equal (insufficient reliable covariance)"
        elif mandate.method == "conviction_risk":
            if conviction and set(conviction) >= {s.ticker for s in securities}:
                # Bounded subjective influence, not expected alpha or probability.
                signals = {s: v*{"low":.8,"medium":1.,"high":1.2}[conviction[s]] for s,v in signals.items()}
            else:
                used = "risk (validated conviction unavailable)"
    weights = {s.ticker:0. for s in securities}
    sectors = defaultdict(float)
    budget = 1-mandate.cash
    for _ in range(500):
        remaining = budget-sum(weights.values())
        if remaining < TOL:
            break
        active = [s for s in securities if weights[s.ticker] < mandate.position_cap-TOL and sectors[s.sector] < mandate.sector_cap-TOL]
        if not active:
            raise ValueError("Allocation capacity exhausted before requested cash target.")
        denom = sum(signals[s.ticker] for s in active)
        proposed = {s.ticker:min(remaining*signals[s.ticker]/denom, mandate.position_cap-weights[s.ticker]) for s in active}
        group = defaultdict(float)
        for s in active:
            group[s.sector] += proposed[s.ticker]
        for s in active:
            value = proposed[s.ticker]*min(1., (mandate.sector_cap-sectors[s.sector])/group[s.sector]) if group[s.sector] else 0.
            weights[s.ticker] += value
        sectors = defaultdict(float)
        for s in securities:
            sectors[s.sector] += weights[s.ticker]
    cash = 1-sum(weights.values())
    validate_weights(securities, weights, cash, mandate)
    binding = [s+" position cap" for s,w in weights.items() if abs(w-mandate.position_cap) < 1e-7]
    binding += [s+" sector/category cap" for s,w in sectors.items() if abs(w-mandate.sector_cap) < 1e-7]
    binding += ["Minimum cash target"] if abs(cash-mandate.cash) < 1e-7 else []
    return weights, cash, dict(sectors), used, binding, note


def validate_weights(securities, weights, cash, mandate):
    import math
    if len(securities) != mandate.holdings or set(weights) != {s.ticker for s in securities} or len(weights) != len(securities):
        raise ValueError("Holdings identity/count mismatch.")
    if not math.isfinite(cash) or cash < mandate.cash-TOL or abs(sum(weights.values())+cash-1) > TOL:
        raise ValueError("Cash/budget does not reconcile.")
    sectors = defaultdict(float)
    for s in securities:
        w = weights[s.ticker]
        if not math.isfinite(w) or w <= 0 or w > mandate.position_cap+TOL:
            raise ValueError("Invalid position weight.")
        sectors[s.sector] += w
    if any(w > mandate.sector_cap+TOL for w in sectors.values()):
        raise ValueError("Sector/category cap violated.")


def dollar_allocations(weights, cash, amount):
    # Integer cents with largest-remainder reconciliation. No fabricated share quantities.
    from decimal import Decimal, ROUND_HALF_UP
    cents = int((Decimal(str(amount))*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    values = {**weights, "CASH":cash}
    raw = {k: cents*v for k,v in values.items()}
    result = {k:int(v) for k,v in raw.items()}
    for k in sorted(raw, key=lambda k: (-(raw[k]-result[k]), k))[:cents-sum(result.values())]:
        result[k] += 1
    return {k:v/100 for k,v in result.items()}
