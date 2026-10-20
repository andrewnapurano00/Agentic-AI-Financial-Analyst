"""Explicit manual rounds, partial failure isolation, and an offline demo."""
from copy import deepcopy
from datetime import datetime, timezone
from .engine import mark, rebalance, validate_market, snapshot_id, equity
from .agent import validate_proposal, propose
from .personas import PERSONAS


def demo_market(experiment):
    step = experiment["demo_step"]
    now = datetime.now(timezone.utc).isoformat()
    all_symbols = list(dict.fromkeys(experiment["universe"] + [experiment["benchmark"]]))
    rows = {}
    for index, symbol in enumerate(all_symbols):
        rows[symbol] = dict(symbol=symbol, price=(100+index*20)*(1 + (.025 if index % 2 == 0 else -.015)*min(step, 20)),
                            as_of=now, currency="USD", currency_basis="synthetic USD",
                            company=symbol+" synthetic instrument", sector="Synthetic", provider="Synthetic demo",
                            pe_ttm=15+index*3, margin_ttm=.20, change_pct=2.5 if index % 2 == 0 else -1.5,
                            sma50=None, sma200=None, description="Synthetic fixture, not actual financial evidence.")
    packet = dict(rows=rows, mode="Demo", retrieved_at=now, warnings=["Synthetic demonstration, not actual trading performance."], provider="Synthetic demo")
    packet["id"] = snapshot_id(packet)
    return packet


def demo_proposal(experiment, persona, snapshot, *_args):
    preferred = {"Warren": ["AAPL", "MSFT", "NVDA"], "George": ["SPY", "GLD"],
                 "Ray": ["SPY", "TLT", "GLD"], "Cathie": ["IBIT", "BITO"]}[persona]
    selected = [s for s in preferred if s in experiment["universe"] and s in snapshot["rows"]]
    weight = min(experiment["cap"], (1-experiment["reserve"])/max(1, len(selected)))
    return dict(proposal=dict(persona=persona, experiment=experiment["id"], snapshot=snapshot["id"],
                              action="REBALANCE" if selected else "HOLD",
                              allocations=[dict(symbol=s, weight=weight) for s in selected],
                              rationale="Deterministic demo allocation to exercise accounting and monitoring, not an AI investment opinion.",
                              risks=["Synthetic prices and fixed demo strategies do not establish live returns."],
                              evidence_symbols=selected or list(snapshot["rows"])[:1]),
                model="deterministic demo", prompt_tokens=None, completion_tokens=None)


def run_round(experiment, snapshot, api_key="", model="", *, decider=None, progress=None, checkpoint=None):
    validate_market(experiment, snapshot)
    if len(experiment["rounds"]) >= 50 and snapshot["id"] not in experiment["rounds"]:
        raise ValueError("This shell supports 50 rounds per experiment. Export and start a new experiment.")
    if len([r for r in experiment["rounds"].get(snapshot["id"], {}).values() if r["status"] == "complete"]) == 4:
        return deepcopy(experiment)
    out = mark(experiment, snapshot)
    if decider is None:
        decider = demo_proposal if out["mode"] == "Demo" else propose
    records = out["rounds"].setdefault(snapshot["id"], {})
    for persona in PERSONAS:
        if records.get(persona, {}).get("status") == "complete":
            continue
        if progress:
            progress(PERSONAS[persona]["name"])
        previous_calls = records.get(persona, {}).get("model_calls", 0)
        record = dict(status="failed", model_calls=previous_calls)
        try:
            # Do not pay for a proposal when held assets cannot be valued.
            equity(out["accounts"][persona], snapshot)
            record["model_calls"] += 0 if out["mode"] == "Demo" else 1
            records[persona] = dict(record, status="running")
            if checkpoint:
                checkpoint(deepcopy(out))
            response = decider(deepcopy(out), persona, snapshot, api_key, model)
            proposal = validate_proposal(response["proposal"], out, persona, snapshot)
            candidate = deepcopy(out["accounts"][persona])
            if proposal["action"] == "REBALANCE":
                candidate = rebalance(out, persona, snapshot, proposal["allocations"])
            candidate["decisions"].append(dict(at=datetime.now(timezone.utc).isoformat(), **proposal))
            out["accounts"][persona] = candidate
            record.update(status="complete", proposal=proposal, model=response.get("model", model),
                          prompt_tokens=response.get("prompt_tokens"), completion_tokens=response.get("completion_tokens"))
        except Exception:
            # Never put raw SDK/model/provider errors or credentials in the ledger.
            record["message"] = "Proposal or execution could not be validated. Account unchanged; successful traders are preserved."
        records[persona] = record
        if checkpoint:
            checkpoint(mark(out, snapshot))
    out = mark(out, snapshot)
    if out["mode"] == "Demo" and out["rounds"] != experiment["rounds"]:
        out["demo_step"] += 1
    return out
