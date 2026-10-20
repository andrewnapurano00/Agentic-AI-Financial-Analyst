"""Deterministic, atomic, long-only paper accounting and evaluation."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import uuid

from langgraphagenticai.state.research_context import normalize_company_symbol
from .personas import PERSONAS, CRYPTO_ETFS


def finite(value):
    if isinstance(value, bool):
        raise ValueError("A finite number is required.")
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("A finite number is required.") from exc
    if not math.isfinite(value):
        raise ValueError("A finite number is required.")
    return value


def symbols(text):
    result = list(dict.fromkeys(normalize_company_symbol(s) for s in text.replace("\n", ",").split(",") if s.strip()))
    if not 1 <= len(result) <= 8:
        raise ValueError("Choose one to eight ticker symbols.")
    return result


def create_experiment(name, universe, benchmark="SPY", capital=100000., cap=.30, reserve=.10, cost_bps=10., mode="Demo"):
    universe = symbols(universe)
    benchmark = normalize_company_symbol(benchmark)
    capital, cap, reserve, cost_bps = map(finite, (capital, cap, reserve, cost_bps))
    if not 100 <= capital <= 10000000 or not .05 <= cap <= 1 or not 0 <= reserve <= .9 or not 0 <= cost_bps <= 100:
        raise ValueError("Experiment settings are outside supported bounds.")
    if mode not in {"Demo", "FMP + AI"}:
        raise ValueError("Unsupported experiment mode.")
    now = datetime.now(timezone.utc).isoformat()
    return dict(id=uuid.uuid4().hex[:12], schema_version=1, execution="paper_reference_quotes", name=str(name).strip()[:80] or "Trading experiment",
                created_at=now, universe=universe, benchmark=benchmark, capital=capital, cap=cap,
                reserve=reserve, cost_bps=cost_bps, mode=mode, market=None, baseline=None,
                accounts={p: dict(cash=capital, positions={}, fees=0., trades=[], decisions=[], peak=capital, max_drawdown=0.,
                                 history=[dict(snapshot="initial", at=now, equity=capital, benchmark=None)], status="Ready")
                          for p in PERSONAS}, rounds={}, demo_step=0)


def snapshot_id(snapshot):
    # Retrieval time alone must not authorize repeating a paid/executed round.
    rows = {s: {k: v for k, v in row.items() if k != "retrieved_at"} for s, row in snapshot["rows"].items()}
    return sha256(json.dumps(dict(mode=snapshot["mode"], rows=rows), sort_keys=True, allow_nan=False).encode()).hexdigest()


def validate_market(experiment, snapshot, now=None):
    now = now or datetime.now(timezone.utc)
    if snapshot.get("mode") != experiment["mode"]:
        raise ValueError("Demo and FMP evidence cannot be mixed.")
    historical = experiment["mode"] in {"Historical Demo", "Historical AI"}
    retrieved = datetime.fromisoformat(snapshot["retrieved_at"])
    if retrieved.tzinfo is None or (retrieved > now) or (not historical and (now-retrieved).total_seconds() > 900):
        raise ValueError("Refresh the market snapshot: retrieval must be within 15 minutes.")
    if historical:
        day = snapshot.get("simulation_date", "")
        if not experiment["start"] <= day <= experiment["end"] or day > now.date().isoformat():
            raise ValueError("Historical snapshot is outside the simulation period.")
    if not snapshot.get("rows") or set(snapshot["rows"]) - set(experiment["universe"] + [experiment["benchmark"]]):
        raise ValueError("No usable allowed market evidence.")
    for symbol, row in snapshot["rows"].items():
        stamp = datetime.fromisoformat(row["as_of"])
        if (row["symbol"] != symbol or row["currency"] != "USD" or finite(row["price"]) <= 0
                or stamp.tzinfo is None or (historical and stamp.date().isoformat() != day)
                or (not historical and not 0 <= (now-stamp).total_seconds() <= 7*86400)):
            raise ValueError("Quotes need positive USD prices and dates within seven UTC calendar days.")
    if snapshot.get("id") != snapshot_id(snapshot):
        raise ValueError("Market snapshot identity mismatch.")


def equity(account, snapshot):
    missing = set(account["positions"]) - set(snapshot["rows"])
    if missing:
        raise ValueError("Held-position quotes are missing; previous valuation is retained.")
    return finite(account["cash"] + sum(q * snapshot["rows"][s]["price"] for s, q in account["positions"].items()))


def validate_targets(experiment, persona, allocations):
    weights = {}
    for row in allocations:
        symbol = row["symbol"]
        weight = finite(row["weight"])
        if symbol in weights or symbol not in experiment["universe"] or not 0 <= weight <= experiment["cap"] + 1e-10:
            raise ValueError("Unknown/duplicate symbol or position cap violation.")
        if persona == "Cathie" and symbol not in CRYPTO_ETFS:
            raise ValueError("Cathie's shell mandate is IBIT/BITO crypto ETFs only.")
        weights[symbol] = weight
    if sum(weights.values()) > 1-experiment["reserve"] + 1e-10:
        raise ValueError("Target allocations violate the cash reserve.")
    return weights


def rebalance(experiment, persona, snapshot, allocations):
    """Solve post-cost equity first, then sell before buying. No silent clipping."""
    validate_market(experiment, snapshot)
    account = deepcopy(experiment["accounts"][persona])
    weights = validate_targets(experiment, persona, allocations)
    if set(weights) - set(snapshot["rows"]):
        raise ValueError("A target quote is unavailable.")
    before = equity(account, snapshot)
    current = {s: q*snapshot["rows"][s]["price"] for s, q in account["positions"].items()}
    names = sorted(set(current) | set(weights))
    rate = experiment["cost_bps"]/10000
    def turnover(nav):
        return sum(abs(weights.get(s, 0.)*nav-current.get(s, 0.)) for s in names)
    low, high = 0., before
    for _ in range(70):
        middle = (low+high)/2
        if middle + rate*turnover(middle) > before:
            high = middle
        else:
            low = middle
    nav = (low+high)/2
    changes = {s: weights.get(s, 0.)*nav-current.get(s, 0.) for s in names}
    for symbol in sorted(names, key=lambda s: (changes[s] > 0, s)):
        value = changes[symbol]
        if abs(value) < max(1e-8, before*1e-12):
            continue
        price = snapshot["rows"][symbol]["price"]
        quantity = abs(value)/price
        fee = abs(value)*rate
        account["cash"] -= value+fee
        account["fees"] += fee
        account["positions"][symbol] = account["positions"].get(symbol, 0.) + value/price
        if abs(account["positions"][symbol]) < 1e-10:
            account["positions"].pop(symbol)
        account["trades"].append(dict(execution="paper", snapshot=snapshot["id"], at=snapshot.get("simulation_date") or datetime.now(timezone.utc).isoformat(),
                                      market_retrieved_at=snapshot["retrieved_at"], symbol=symbol,
                                      side="BUY" if value > 0 else "SELL", shares=quantity, price=price,
                                      notional=abs(value), fee=fee, quote_as_of=snapshot["rows"][symbol]["as_of"]))
        if account["cash"] < -max(1e-7, before*1e-10):
            raise ValueError("Insufficient simulated cash.")
    after = equity(account, snapshot)
    if not math.isclose(after, nav, rel_tol=1e-9, abs_tol=1e-6) or account["cash"] < experiment["reserve"]*after - 1e-6:
        raise ValueError("Post-cost cash reconciliation failed.")
    if any(q < -1e-10 or q*snapshot["rows"][s]["price"] > experiment["cap"]*after+1e-6 for s, q in account["positions"].items()):
        raise ValueError("Post-trade concentration or long-only check failed.")
    account["cash"] = max(0., account["cash"])
    return account


def mark(experiment, snapshot):
    validate_market(experiment, snapshot)
    out = deepcopy(experiment)
    out["market"] = snapshot
    benchmark = snapshot["rows"].get(out["benchmark"])
    if out["baseline"] is None and benchmark and all(len(a["history"]) == 1 for a in out["accounts"].values()):
        out["baseline"] = dict(price=benchmark["price"], as_of=benchmark["as_of"])
    for account in out["accounts"].values():
        try:
            nav = equity(account, snapshot)
        except ValueError:
            account["status"] = "Missing held quotes; showing saved valuation"
            continue
        quote_dates = {snapshot["rows"][s]["as_of"][:10] for s in account["positions"]}
        comparable = bool(benchmark and out["baseline"] and (not quote_dates or quote_dates == {benchmark["as_of"][:10]}))
        point = dict(snapshot=snapshot["id"], at=snapshot.get("simulation_date") or datetime.now(timezone.utc).isoformat(), equity=nav,
                     benchmark=benchmark["price"]/out["baseline"]["price"]-1 if comparable else None)
        account["peak"] = max(account["peak"], nav)
        account["max_drawdown"] = min(account["max_drawdown"], nav/account["peak"]-1)
        if account["history"][-1]["snapshot"] == snapshot["id"]:
            account["history"][-1] = point
        else:
            account["history"].append(point)
        # Keep initial capital in drawdown calculations even with a bounded monitor history.
        account["history"] = account["history"][:1] + account["history"][-199:] if len(account["history"]) > 200 and not out["mode"].startswith("Historical") else account["history"]
        account["status"] = "Marked to reference quotes"
    return out


def scorecard(experiment):
    rows = []
    for persona, account in experiment["accounts"].items():
        last = account["history"][-1]
        latest = next((r[persona] for r in reversed(list(experiment["rounds"].values())) if persona in r), {})
        result = last["equity"]/experiment["capital"]-1
        rows.append(dict(Trader=PERSONAS[persona]["name"], Equity=last["equity"], Cash=account["cash"],
                         Return_pct=100*result, Benchmark_pct=None if last["benchmark"] is None else 100*last["benchmark"],
                         Excess_pp=None if last["benchmark"] is None else 100*(result-last["benchmark"]),
                         Observed_drawdown_pct=100*account["max_drawdown"], Fees=account["fees"], Trades=len(account["trades"]),
                         Last_decision=latest.get("status", "Not run"),
                         Status=account["status"], Last_mark=last["at"]))
    return rows
