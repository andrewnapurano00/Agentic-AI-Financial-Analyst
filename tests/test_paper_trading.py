"""Independent paper-account arithmetic, evidence guards and failure recovery."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest

from langgraphagenticai.paper_trading.engine import (
    create_experiment, snapshot_id, validate_market, rebalance, mark, scorecard, equity,
)
from langgraphagenticai.paper_trading.workflow import demo_market, demo_proposal, run_round
from langgraphagenticai.paper_trading.agent import validate_proposal, propose
from langgraphagenticai.paper_trading.personas import DEFAULT_UNIVERSE


def experiment(mode="Demo", **kwargs):
    return create_experiment("test", DEFAULT_UNIVERSE, mode=mode, **kwargs)


def market(exp):
    result = demo_market(exp)
    result["mode"] = exp["mode"]
    result["id"] = snapshot_id(result)
    return result


def edited(snapshot, edit):
    result = deepcopy(snapshot)
    edit(result)
    result["id"] = snapshot_id(result)
    return result


def test_post_cost_targets_cash_and_sale_are_independently_reconciled():
    exp = create_experiment("cost", "AAPL, MSFT", capital=1000, cap=.5, reserve=.1, cost_bps=100)
    snapshot = market(exp)
    account = rebalance(exp, "Warren", snapshot, [dict(symbol=s, weight=.45) for s in exp["universe"]])
    expected_nav = 1000/1.009
    assert equity(account, snapshot) == pytest.approx(expected_nav)
    assert account["cash"] == pytest.approx(.1*expected_nav)
    assert account["fees"] == pytest.approx(1000-expected_nav)
    assert account["positions"]["AAPL"] == pytest.approx(.45*expected_nav/100)
    assert exp["accounts"]["Warren"]["positions"] == {}
    exp["accounts"]["Warren"] = account
    sold = rebalance(exp, "Warren", snapshot, [])
    assert sold["positions"] == {}
    assert sold["cash"] == pytest.approx(.1*expected_nav+.9*expected_nav*.99)
    assert all(t["side"] == "SELL" for t in sold["trades"][-2:])


@pytest.mark.parametrize("allocations", [
    [{"symbol":"AAPL","weight":.31}], [{"symbol":"AAPL","weight":-.1}],
    [{"symbol":"AAPL","weight":float("nan")}], [{"symbol":"UNLISTED","weight":.1}],
    [{"symbol":"AAPL","weight":.2},{"symbol":"AAPL","weight":.1}],
    [{"symbol":s,"weight":.3} for s in ["AAPL","MSFT","NVDA","SPY"]],
])
def test_bad_allocations_cannot_change_an_account(allocations):
    exp = experiment(); original = deepcopy(exp)
    with pytest.raises(ValueError):
        rebalance(exp, "Warren", market(exp), allocations)
    assert exp == original


def test_cathie_mandate_is_enforced_and_infeasible_capacity_stays_cash():
    exp = experiment()
    with pytest.raises(ValueError):
        rebalance(exp, "Cathie", market(exp), [dict(symbol="AAPL", weight=.2)])
    result = run_round(exp, market(exp))
    assert set(result["accounts"]["Cathie"]["positions"]) == {"IBIT","BITO"}
    cash_weight = result["accounts"]["Cathie"]["cash"]/equity(result["accounts"]["Cathie"], result["market"])
    assert cash_weight == pytest.approx(.4)


@pytest.mark.parametrize("edit", [
    lambda s:s["rows"]["AAPL"].update(price=0),
    lambda s:s["rows"]["AAPL"].update(price=float("inf")),
    lambda s:s["rows"]["AAPL"].update(currency="EUR"),
    lambda s:s["rows"]["AAPL"].update(symbol="MSFT"),
    lambda s:s["rows"]["AAPL"].update(as_of=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()),
    lambda s:s["rows"]["AAPL"].update(as_of=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()),
    lambda s:s.update(retrieved_at=(datetime.now(timezone.utc)-timedelta(minutes=16)).isoformat()),
    lambda s:s.update(mode="FMP + AI"),
])
def test_market_guards_block_paper_execution(edit):
    exp = experiment(); snapshot = market(exp)
    edit(snapshot)
    # Nonfinite JSON itself must also fail, never authorize a fill.
    with pytest.raises(ValueError):
        snapshot["id"] = snapshot_id(snapshot)
        validate_market(exp, snapshot)


def test_same_snapshot_round_is_idempotent_and_retrieval_does_not_reauthorize():
    exp = experiment("FMP + AI")
    snapshot = market(exp); calls = Mock(side_effect=demo_proposal)
    once = run_round(exp, snapshot, "synthetic", "model", decider=calls)
    again = run_round(once, snapshot, "synthetic", "model", decider=calls)
    assert calls.call_count == 4
    assert [a["trades"] for a in once["accounts"].values()] == [a["trades"] for a in again["accounts"].values()]
    changed = deepcopy(snapshot); changed["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    assert snapshot_id(changed) == snapshot["id"]


def test_failed_trader_preserves_positions_and_retry_skips_successes():
    exp = experiment("FMP + AI"); snapshot = market(exp); attempts = []
    failed = {"on":True}
    def decide(exp, persona, *args):
        attempts.append(persona)
        if persona == "George" and failed["on"]:
            raise RuntimeError("apikey=must-never-be-retained")
        return demo_proposal(exp, persona, *args)
    result = run_round(exp, snapshot, decider=decide)
    assert result["accounts"]["George"]["cash"] == exp["capital"]
    assert not result["accounts"]["George"]["positions"]
    assert result["accounts"]["Warren"]["trades"]
    assert "must-never" not in json.dumps(result)
    failed["on"] = False
    result = run_round(result, snapshot, decider=decide)
    assert attempts == ["Warren","George","Ray","Cathie","George"]
    assert all(r["status"] == "complete" for r in result["rounds"][snapshot["id"]].values())


def test_checkpoints_preserve_completed_accounts_when_a_round_is_interrupted():
    exp = experiment("FMP + AI"); snapshot = market(exp); saved = []
    def progress(name):
        if name.startswith("Ray"):
            raise KeyboardInterrupt("Simulated session stop")
    with pytest.raises(KeyboardInterrupt):
        run_round(exp, snapshot, decider=demo_proposal, progress=progress, checkpoint=lambda state:saved.append(deepcopy(state)))
    state = saved[-1]
    assert state["accounts"]["Warren"]["trades"] and state["accounts"]["George"]["trades"]
    calls = Mock(side_effect=demo_proposal)
    result = run_round(state, snapshot, decider=calls)
    assert calls.call_count == 2
    assert len(result["rounds"][snapshot["id"]]) == 4


def test_missing_held_quotes_preserve_valuation_and_block_only_affected_accounts():
    exp = run_round(experiment("FMP + AI"), market(experiment("FMP + AI")), decider=demo_proposal)
    before = deepcopy(exp["accounts"]["Warren"])
    snapshot = edited(exp["market"], lambda s:s["rows"].pop("AAPL"))
    calls = Mock(side_effect=demo_proposal)
    result = run_round(exp, snapshot, decider=calls)
    assert result["accounts"]["Warren"]["cash"] == before["cash"]
    assert result["accounts"]["Warren"]["positions"] == before["positions"]
    assert result["accounts"]["Warren"]["history"][-1] == before["history"][-1]
    assert "Missing held" in result["accounts"]["Warren"]["status"]
    assert calls.call_count == 3


def test_drawdown_includes_start_capital_and_benchmark_dates_are_not_invented():
    exp = experiment(cost_bps=0)
    exp = run_round(exp, market(exp))
    fallen = edited(exp["market"], lambda s:[r.update(price=r["price"]*.8) for r in s["rows"].values()])
    exp = mark(exp, fallen)
    row = scorecard(exp)[0]
    assert row["Return_pct"] == pytest.approx(-18)
    assert row["Observed_drawdown_pct"] == pytest.approx(-18)
    assert row["Benchmark_pct"] == pytest.approx(-20)
    mismatched = edited(fallen, lambda s:s["rows"]["SPY"].update(as_of=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()))
    assert scorecard(mark(exp, mismatched))[0]["Excess_pp"] is None


@pytest.mark.parametrize("edit", [
    lambda p:p.update(persona="George"), lambda p:p.update(snapshot="other"),
    lambda p:p.update(experiment="other"),
    lambda p:p.update(evidence_symbols=["UNLISTED"]),
    lambda p:p["allocations"][0].update(weight=True),
    lambda p:p.update(action="HOLD"),
])
def test_structured_proposal_identity_citations_and_units(edit):
    exp = experiment(); snapshot = market(exp)
    value = demo_proposal(exp,"Warren",snapshot)["proposal"]
    edit(value)
    with pytest.raises(ValueError):
        validate_proposal(value,exp,"Warren",snapshot)


def test_model_boundary_is_bounded_structured_and_redacts_exact_key(monkeypatch):
    from langgraphagenticai.paper_trading import agent
    exp=experiment("FMP + AI"); snapshot=market(exp); key="nonprefixed-private-credential"
    value=demo_proposal(exp,"Warren",snapshot)["proposal"];value["rationale"]="Evidence "+key
    response=SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(value),refusal=None))],
                             usage=SimpleNamespace(prompt_tokens=100,completion_tokens=50))
    request=Mock(return_value=response)
    factory=Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=request))))
    monkeypatch.setattr(agent,"build_openai_client",factory)
    result=propose(exp,"Warren",snapshot,key,"synthetic-model")
    assert key not in json.dumps(result) and result["prompt_tokens"] == 100
    assert factory.call_args.kwargs == {"timeout":90,"max_retries":0}
    assert request.call_count == 1 and request.call_args.kwargs["max_completion_tokens"] == 2200
