"""Historical evidence isolation, next-session accounting and safe resumption."""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import Mock
import pytest
from langgraphagenticai.paper_trading.replay import create_replay, prepare_replay, market_at, advance_replay, demo_history
from langgraphagenticai.paper_trading.engine import scorecard, validate_market


def fixture(ai=False, interval=1):
    exp=create_replay("test","SPY, IBIT","SPY","2025-01-02","2025-01-08",interval,1000,1,0,0,ai)
    hist=dict(series={"SPY":{"2025-01-01":90,"2025-01-02":100,"2025-01-03":200,"2025-01-06":220,"2025-01-07":180,"2025-01-08":240},
                      "IBIT":{"2025-01-01":40,"2025-01-02":50,"2025-01-03":60,"2025-01-06":70,"2025-01-07":80,"2025-01-08":90}},
              currency="USD",retrieved_at=datetime.now(timezone.utc).isoformat(),provider="Synthetic demo",basis="synthetic",currency_basis="synthetic")
    return prepare_replay(exp,hist)


def proposal(exp,persona,snapshot,*args):
    return dict(proposal=dict(persona=persona,experiment=exp["id"],snapshot=snapshot["id"],action="REBALANCE" if persona=="Warren" else "HOLD",
                             allocations=[dict(symbol="SPY",weight=1.)] if persona=="Warren" else [],
                             rationale="Only past prices considered",risks=["Price-only evidence"],evidence_symbols=["SPY"]),model="fake")


def test_future_rows_and_current_facts_never_enter_agent_view():
    exp=fixture(True)
    exp["history_data"]["secret_future_news"]="tomorrow acquisition"
    seen=[]
    def inspect(view,persona,snapshot,*args):
        assert "history_data" not in view and "schedule" not in view and "sessions" not in view
        assert view["end"]=="2025-01-02"
        assert "tomorrow acquisition" not in str(view)+str(snapshot)
        assert all(row["as_of"][:10]<=snapshot["simulation_date"] for row in snapshot["rows"].values())
        assert all(point["date"]<=snapshot["simulation_date"] for row in snapshot["rows"].values() for point in row["history"])
        seen.append(snapshot)
        return proposal(view,persona,snapshot)
    advance_replay(exp,decider=inspect)
    altered=deepcopy(exp)
    altered["history_data"]["series"]["SPY"]["2025-01-08"]=99999
    assert market_at(exp,"2025-01-02",decision=True)==market_at(altered,"2025-01-02",decision=True)
    assert len(seen)==4


def test_next_close_execution_and_independent_return_benchmark_math():
    exp=advance_replay(fixture(),decider=proposal)
    trade=exp["accounts"]["Warren"]["trades"][0]
    assert trade["decision_date"]=="2025-01-02" and trade["at"]=="2025-01-03" and trade["price"]==200
    assert trade["shares"]==5 and exp["accounts"]["Warren"]["cash"]==0
    assert scorecard(exp)[0]["Return_pct"]==0
    assert scorecard(exp)[0]["Benchmark_pct"]==100
    while exp["cursor"]<len(exp["schedule"]):
        exp=advance_replay(exp,decider=proposal)
    row=scorecard(exp)[0]
    assert row["Equity"]==1200
    assert row["Return_pct"]==pytest.approx(20) and row["Benchmark_pct"]==pytest.approx(140)
    assert row["Excess_pp"]==pytest.approx(-120)
    assert row["Observed_drawdown_pct"]==pytest.approx((900/1100-1)*100)
    assert len(exp["accounts"]["Warren"]["trades"])==1 # Already matching weights produce no orders.
    assert len(exp["accounts"]["George"]["decisions"])==4 and not exp["accounts"]["George"]["trades"]


def test_final_period_marks_every_day_and_completed_replay_is_noop():
    exp=advance_replay(fixture(interval=21),decider=proposal)
    assert exp["cursor"]==1 and exp["accounts"]["Warren"]["history"][-1]["at"]=="2025-01-08"
    assert {p["at"] for p in exp["accounts"]["Warren"]["history"]} >= set(exp["sessions"])
    forbidden=Mock(side_effect=AssertionError())
    assert advance_replay(exp,decider=forbidden)==exp
    forbidden.assert_not_called()


def test_failed_agent_has_no_order_and_no_automatic_paid_retry():
    exp=fixture(True)
    def fail(view,persona,snapshot,*args):
        if persona=="Warren":raise RuntimeError("apikey=private")
        return proposal(view,persona,snapshot)
    out=advance_replay(exp,decider=fail)
    record=next(iter(out["rounds"].values()))["Warren"]
    assert record["status"]=="failed" and record["model_calls"]==1 and "private" not in str(out)
    assert out["accounts"]["Warren"]["cash"]==1000 and not out["accounts"]["Warren"]["trades"]


def test_checkpoint_resume_after_trade_does_not_double_execute_or_recall():
    saved=[]
    def checkpoint(exp):
        saved.append(exp)
        if exp["accounts"]["Warren"]["trades"]:raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        advance_replay(fixture(True),decider=proposal,checkpoint=checkpoint)
    forbidden=Mock(side_effect=AssertionError("already proposed"))
    out=advance_replay(saved[-1],decider=forbidden)
    assert len(out["accounts"]["Warren"]["trades"])==1 and out["cursor"]==1
    forbidden.assert_not_called()


def test_checkpoint_before_paid_call_is_not_retried_after_interrupt():
    saved=[]
    def checkpoint(exp):
        saved.append(exp)
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):advance_replay(fixture(True),checkpoint=checkpoint)
    decider=Mock(side_effect=proposal)
    out=advance_replay(saved[-1],decider=decider)
    assert decider.call_count==3 and next(iter(out["rounds"].values()))["Warren"]["status"]=="interrupted"
    assert not out["accounts"]["Warren"]["trades"]


@pytest.mark.parametrize("start,end,interval",[("2025-01-01","2025-01-01",1),("2024-01-01","2025-01-20",1),("2025-01-01","2099-01-01",1),("2025-01-01","2025-01-20",2)])
def test_invalid_periods(start,end,interval):
    with pytest.raises(ValueError):create_replay("bad","SPY,IBIT","SPY",start,end,interval)


def test_missing_sessions_and_wrong_currency_block_loading():
    exp=fixture()
    clean=create_replay("fresh","SPY, IBIT","SPY",exp["start"],exp["end"])
    hist=deepcopy(exp["history_data"])
    del hist["series"]["IBIT"]["2025-01-06"]
    with pytest.raises(ValueError,match="missing sessions"):prepare_replay(clean,hist)
    hist["currency"]="EUR"
    with pytest.raises(ValueError,match="USD"):prepare_replay(clean,hist)
    with pytest.raises(ValueError,match="frozen"):prepare_replay(exp,hist)


def test_outside_period_snapshot_and_too_many_decisions_blocked():
    exp=fixture()
    snapshot=market_at(exp,"2025-01-02")
    snapshot["simulation_date"]="2026-01-01"
    with pytest.raises(ValueError):validate_market(exp,snapshot)
    large=create_replay("large","SPY, IBIT","SPY","2025-01-01","2025-06-01",1)
    with pytest.raises(ValueError,match="24"):prepare_replay(large,demo_history(large["universe"],large["benchmark"],large["start"],large["end"]))


def test_demo_no_paid_model_and_post_fee_caps():
    exp=fixture()
    exp["cap"],exp["reserve"],exp["cost_bps"] = .3,.1,10
    out=advance_replay(exp)
    assert all(r["model_calls"]==0 for r in next(iter(out["rounds"].values())).values())
    for account in out["accounts"].values():
        nav=account["history"][-1]["equity"]
        assert account["cash"] >= .1*nav-1e-6
    assert out["accounts"]["Cathie"]["positions"]=={"IBIT":pytest.approx(1000/(1+.0003)*.3/60)}


def test_daily_history_is_not_truncated_for_long_replay():
    exp=create_replay("long","SPY,IBIT","SPY","2025-01-01","2025-12-31",21)
    exp=prepare_replay(exp,demo_history(exp["universe"],exp["benchmark"],exp["start"],exp["end"]))
    while exp["cursor"]<len(exp["schedule"]):exp=advance_replay(exp)
    assert len(exp["accounts"]["Warren"]["history"])>200
    assert exp["accounts"]["Warren"]["history"][-1]["at"]==exp["coverage"]["last"]


def test_malicious_future_dated_or_wrong_identity_quote_rejected():
    from langgraphagenticai.paper_trading.engine import snapshot_id
    exp=fixture()
    packet=market_at(exp,"2025-01-02",decision=True)
    packet["rows"]["SPY"]["as_of"]="2025-01-03T23:59:59+00:00"
    packet["id"]=snapshot_id(packet)
    with pytest.raises(ValueError):validate_market(exp,packet)


def test_loaded_period_has_no_future_bars_and_insufficient_coverage_is_explicit():
    exp=fixture()
    history=deepcopy(exp["history_data"])
    history["series"]["SPY"]["2099-01-01"]=99999
    clean=create_replay("filtered","SPY,IBIT","SPY",exp["start"],exp["end"])
    out=prepare_replay(clean,history)
    assert "2099-01-01" not in out["history_data"]["series"]["SPY"]
    history["series"]["IBIT"]={}
    with pytest.raises(ValueError,match="two common"):prepare_replay(clean,history)


def test_actual_model_packet_excludes_later_data_and_declares_cutoff(monkeypatch):
    import json
    from types import SimpleNamespace
    from langgraphagenticai.paper_trading import agent
    exp=fixture(True)
    exp["history_data"]["future_outcome"]="FUTURE_SENTINEL"
    snapshot=market_at(exp,"2025-01-02",decision=True)
    value=proposal(exp,"Warren",snapshot)["proposal"]
    request=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=json.dumps(value),refusal=None))],usage=None))
    monkeypatch.setattr(agent,"build_openai_client",Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=request)))))
    agent.propose(exp,"Warren",snapshot,"fake","fake")
    packet=json.loads(request.call_args.kwargs["messages"][1]["content"])
    assert packet["decision_date"]=="2025-01-02" and "next session close" in packet["historical_rules"]
    assert "FUTURE_SENTINEL" not in str(packet) and "2025-01-08" not in str(packet)
