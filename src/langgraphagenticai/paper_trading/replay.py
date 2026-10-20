"""Dated replay: cutoff-only decisions, next-session close execution, daily marks."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from .engine import create_experiment, snapshot_id, mark, rebalance, finite
from .agent import propose, validate_proposal
from .personas import PERSONAS


def demo_history(universe, benchmark, start, end):
    first, last = date.fromisoformat(start)-timedelta(days=120), date.fromisoformat(end)
    days = [(first+timedelta(days=i)).isoformat() for i in range((last-first).days+1) if (first+timedelta(days=i)).weekday()<5]
    names = list(dict.fromkeys(universe+[benchmark]))
    return dict(series={s:{d:100+20*j+i*(.2 if j%2 == 0 else -.08) for i,d in enumerate(days)} for j,s in enumerate(names)},
                retrieved_at=datetime.now(timezone.utc).isoformat(), provider="Synthetic demo", currency="USD",
                basis="Synthetic close; no dividends", currency_basis="Synthetic USD", warnings=[])


def create_replay(name, universe, benchmark, start, end, interval=21, capital=100000., cap=.30, reserve=.10, cost_bps=10., ai=False):
    first, last = date.fromisoformat(str(start)), date.fromisoformat(str(end))
    if not 1 <= (last-first).days <= 366 or last >= date.today() or interval not in {1,5,21}:
        raise ValueError("Choose a completed historical period of up to one year.")
    out = create_experiment(name, universe, benchmark, capital, cap, reserve, cost_bps)
    out.update(mode="Historical AI" if ai else "Historical Demo", start=first.isoformat(), end=last.isoformat(),
               interval=interval, cursor=0, loaded=False, schedule=[], sessions=[])
    for account in out["accounts"].values():
        account["history"][0]["at"] = first.isoformat()
    return out


def prepare_replay(experiment, history):
    if experiment["loaded"]:
        raise ValueError("History is frozen after loading; create another experiment to replace it.")
    names = list(dict.fromkeys(experiment["universe"]+[experiment["benchmark"]]))
    clean = {}
    for symbol in names:
        clean[symbol] = {}
        for day, value in history["series"].get(symbol, {}).items():
            stamp = date.fromisoformat(day)
            price = finite(value)
            if price <= 0:
                raise ValueError("Historical prices must be positive.")
            if date.fromisoformat(experiment["start"])-timedelta(days=120) <= stamp <= date.fromisoformat(experiment["end"]):
                clean[symbol][day] = price
    if history.get("currency") != "USD":
        raise ValueError("Replay requires compatible USD history.")
    common = set(clean[names[0]])
    for symbol in names[1:]:
        common &= set(clean[symbol])
    sessions = sorted(d for d in common if experiment["start"] <= d <= experiment["end"])
    if len(sessions) < 2:
        raise ValueError("At least two common sessions are required for every symbol and benchmark. Narrow the period/universe.")
    # Never silently bridge missing bars inside an instrument's observed period.
    union = {d for rows in clean.values() for d in rows if sessions[0] <= d <= sessions[-1]}
    if union != set(sessions):
        raise ValueError("Historical series have missing sessions. Choose a complete common period/universe.")
    schedule = sessions[:-1:experiment["interval"]]
    if len(schedule)>24:
        raise ValueError("Limit replay to 24 decision dates; shorten the period or use weekly/monthly decisions.")
    out = deepcopy(experiment)
    out.update(loaded=True, sessions=sessions, schedule=schedule,
               history_data=dict(history, series=clean), coverage=dict(first=sessions[0], last=sessions[-1], sessions=len(sessions)))
    out["history_fingerprint"] = hashlib.sha256(json.dumps(clean,sort_keys=True).encode()).hexdigest()
    out = mark(out, market_at(out, sessions[0]))
    return out


def market_at(experiment, day, *, decision=False):
    history = experiment["history_data"]
    rows = {}
    for symbol in dict.fromkeys(experiment["universe"]+[experiment["benchmark"]]):
        prices = history["series"][symbol]
        if day not in prices:
            raise ValueError("Exact historical session missing; no stale-price substitution.")
        row = dict(symbol=symbol, price=prices[day], as_of=day+"T23:59:59+00:00", currency="USD",
                   provider=history["provider"], price_basis=history["basis"])
        if decision:
            past = sorted((d,p) for d,p in prices.items() if d<=day)[-60:]
            row["history"] = [dict(date=d, close=p) for d,p in past[-12:]]
            row["sma20"] = sum(p for _,p in past[-20:])/20 if len(past)>=20 else None
            row["return20"] = past[-1][1]/past[-21][1]-1 if len(past)>=21 else None
        rows[symbol] = row
    result = dict(mode=experiment["mode"], simulation_date=day, retrieved_at=history["retrieved_at"],
                  provider=history["provider"], rows=rows, warnings=[])
    result["id"] = snapshot_id(result)
    return result


def _agent_view(experiment, day):
    # No schedule, future prices, endpoint dates, benchmark future outcomes or entire saved experiment.
    return {k:deepcopy(experiment[k]) for k in ("id","mode","start","universe","benchmark","capital","cap","reserve","cost_bps","accounts")} | {"end":day}


def advance_replay(experiment, api_key="", model="", *, decider=None, checkpoint=None):
    if not experiment["loaded"] or experiment["cursor"] >= len(experiment["schedule"]):
        return deepcopy(experiment)
    out = deepcopy(experiment)
    day = out["schedule"][out["cursor"]]
    execution = out["sessions"][out["sessions"].index(day)+1]
    evidence = market_at(out, day, decision=True)
    key = evidence["id"]
    records = out["rounds"].setdefault(key,{})
    if decider is None:
        if out["mode"] == "Historical Demo":
            from .workflow import demo_proposal
            decider = demo_proposal
        else:
            decider = propose
    for persona in PERSONAS:
        if persona in records: # Started/failed calls are not automatically paid for again after interruption.
            continue
        records[persona] = dict(status="interrupted", model_calls=int(out["mode"] == "Historical AI"),
                                decision_date=day, execution_date=execution, message="Interrupted attempt; no trade.")
        if checkpoint:
            checkpoint(deepcopy(out))
        try:
            response = decider(_agent_view(out,day),persona,evidence,api_key,model)
            proposal = validate_proposal(response["proposal"],out,persona,evidence)
            records[persona].update(status="proposed", proposal=proposal, model=response.get("model",model),
                                    prompt_tokens=response.get("prompt_tokens"),completion_tokens=response.get("completion_tokens"))
        except Exception:
            records[persona].update(status="failed",message="Decision failed validation; no order. Existing holdings retained.")
        if checkpoint:
            checkpoint(deepcopy(out))
    fills = market_at(out, execution)
    for persona, record in records.items():
        if record["status"] == "proposed":
            proposal = record["proposal"]
            try:
                before_trades = len(out["accounts"][persona]["trades"])
                account = rebalance(out,persona,fills,proposal["allocations"]) if proposal["action"] == "REBALANCE" else deepcopy(out["accounts"][persona])
                for trade in account["trades"][before_trades:]:
                    trade["decision_date"] = day
                account["decisions"].append(dict(at=day, execution_date=execution, **proposal))
                out["accounts"][persona] = account
                record.update(status="complete", action=proposal["action"])
            except ValueError:
                record.update(status="failed",message="Next-session allocation could not be executed within limits; no order.")
            if checkpoint:
                checkpoint(deepcopy(out))
    next_index = out["cursor"]+1
    stop = out["schedule"][next_index] if next_index < len(out["schedule"]) else out["sessions"][-1]
    for session in out["sessions"]:
        if day < session <= stop:
            out = mark(out, market_at(out,session))
    out["cursor"] = next_index
    if checkpoint:
        checkpoint(deepcopy(out))
    return out
