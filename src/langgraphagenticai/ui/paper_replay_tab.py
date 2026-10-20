"""Executive dated-simulation controls; explicit evidence loading and model actions."""
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from langgraphagenticai.paper_trading.replay import create_replay, prepare_replay, demo_history, advance_replay
from langgraphagenticai.paper_trading.engine import scorecard
from langgraphagenticai.paper_trading.personas import DEFAULT_UNIVERSE, PERSONAS
from langgraphagenticai.paper_trading.safety import safe_text
from langgraphagenticai.providers.paper_history import load_paper_history
from langgraphagenticai.utils.export_csv import safe_csv_bytes


def render_paper_replay(fmp_api_key="", openai_api_key="", model_name="gpt-5"):
    st.subheader("Historical Agent Replay")
    st.caption("Warren Patience · George Bold · Ray Systematic · Cathie Crypto | Independent USD paper accounts")
    st.info("Choose a completed period. Decisions see only earlier/equal-date prices; orders execute at the next session close. "
            "Current news, profiles and ratios are excluded from AI evidence. No market-hours browser session is needed.")
    st.warning("Experimental historical simulation: model training may contain later events; revised/split-adjusted historical prices "
               "and a user-selected surviving universe can introduce bias. This is not a certified point-in-time backtest. "
               "Value/macro personas may HOLD because this first replay supplies prices only.")
    store = st.session_state.setdefault("paper_replays_v1",{})
    with st.expander("Create historical experiment",expanded=not bool(store)):
        with st.form("replay_create"):
            name = st.text_input("Replay name", "Dated trader comparison",max_chars=80)
            mode = st.selectbox("Replay evidence",["Synthetic demo", "FMP history + AI"])
            cols = st.columns(2)
            start = cols[0].date_input("Simulation start",date.today()-timedelta(days=180),max_value=date.today()-timedelta(days=2))
            end = cols[1].date_input("Simulation end",date.today()-timedelta(days=1),max_value=date.today()-timedelta(days=1))
            cadence = st.selectbox("Decision frequency",["Every 21 sessions", "Every 5 sessions", "Every session"])
            universe = st.text_input("Replay universe (up to 8 tickers)",DEFAULT_UNIVERSE)
            benchmark = st.text_input("Replay benchmark", "SPY")
            cols = st.columns(4)
            capital = cols[0].number_input("Replay starting cash (USD)",100.,10000000.,100000.,1000.)
            cap = cols[1].number_input("Replay position limit (%)",5.,100.,30.,5.)
            reserve = cols[2].number_input("Replay minimum cash (%)",0.,90.,10.,5.)
            fees = cols[3].number_input("Replay cost (bps)",0.,100.,10.,1.)
            create = st.form_submit_button("Create historical experiment")
        if create:
            try:
                if len(store)>=6:
                    raise ValueError("Six replay experiments are saved; download before starting a new session.")
                exp = create_replay(safe_text(name),universe,benchmark,start,end,{"Every session":1,"Every 5 sessions":5,"Every 21 sessions":21}[cadence],capital,cap/100,reserve/100,fees,mode=="FMP history + AI")
                store[exp["id"]] = exp
                st.session_state["replay_active"] = exp["id"]
                st.session_state["replay_choice"] = exp["id"]
            except ValueError as exc:
                st.warning(str(exc))
    if not store:
        return
    saved = st.session_state.get("replay_active",next(iter(store)))
    selected = st.selectbox("Saved historical experiment",list(store),index=list(store).index(saved) if saved in store else 0,
                            format_func=lambda key:store[key]["name"]+" · "+store[key]["mode"]+" · "+key,key="replay_choice")
    st.session_state["replay_active"] = selected
    exp = store[selected]
    st.caption(f"Fixed period: {exp['start']} to {exp['end']} | {exp['interval']}-session decisions | Benchmark {exp['benchmark']} | {exp['mode']}")
    if not exp["loaded"]:
        if st.button("Load replay history",key="replay_load",disabled=exp["mode"]=="Historical AI" and not fmp_api_key):
            try:
                with st.spinner("Loading and freezing historical evidence"):
                    history = (demo_history(exp["universe"],exp["benchmark"],exp["start"],exp["end"]) if exp["mode"]=="Historical Demo"
                               else load_paper_history(tuple(exp["universe"]),exp["benchmark"],exp["start"],exp["end"],fmp_api_key))
                    exp = prepare_replay(exp,history)
                    store[selected] = exp
            except Exception:
                if exp["mode"]=="Historical AI":
                    load_paper_history.clear(tuple(exp["universe"]),exp["benchmark"],exp["start"],exp["end"],fmp_api_key)
                st.warning("History could not establish a complete common USD period. Check coverage, shorten the dates or remove unavailable symbols; no account was replaced.")
        st.caption("Up to one year and 24 decision dates. History is frozen after loading. Cathie uses IBIT/BITO only; dates before fund inception may need a different universe.")
    if not exp["loaded"]:
        return
    total = len(exp["schedule"])
    finished = exp["cursor"]>=total
    st.progress(exp["cursor"]/total,text=f"{exp['cursor']} / {total} decision dates processed")
    coverage = exp["coverage"]
    st.caption(f"Actual common coverage: {coverage['first']} to {coverage['last']} ({coverage['sessions']} sessions). Source: {exp['history_data']['provider']} | Retrieved: {exp['history_data']['retrieved_at']}")
    st.caption(exp["history_data"]["basis"]+" "+exp["history_data"]["currency_basis"])
    if not finished:
        st.write("Next decision date: "+exp["schedule"][exp["cursor"]])
    if st.button("Run next historical decision",key="replay_next",disabled=finished or (exp["mode"]=="Historical AI" and (not openai_api_key or not model_name))):
        with st.spinner("Processing dated decisions, next-session orders and daily valuations"):
            exp = advance_replay(exp,openai_api_key,model_name,checkpoint=lambda value:store.__setitem__(selected,value))
            store[selected] = exp
        st.rerun()
    st.caption("Each click advances one decision date for all four traders and marks every intervening common session. "
               "AI mode attempts at most four paid calls per date; no automatic retries. Failed/interrupted decisions keep holdings. "
               "Reruns/navigation/downloads do not advance time or call AI.")
    if finished:
        st.success("Replay complete through "+coverage["last"])
    monitor, journal, log = st.tabs(["Replay performance", "Replay trades", "Decision log"])
    with monitor:
        st.dataframe(pd.DataFrame(scorecard(exp)).round(3),hide_index=True,width="stretch")
        points=[]
        for persona,account in exp["accounts"].items():
            for point in account["history"]:
                points.append(dict(date=point["at"][:10],series=PERSONAS[persona]["name"],return_pct=100*(point["equity"]/exp["capital"]-1)))
                if persona=="Warren" and point["benchmark"] is not None:
                    points.append(dict(date=point["at"][:10],series=exp["benchmark"]+" benchmark",return_pct=100*point["benchmark"]))
        st.line_chart(pd.DataFrame(points).pivot_table(index="date",columns="series",values="return_pct",aggfunc="last"))
        st.caption("Return % since first common session; benchmark bought at its first close. Traders start with cash, first fills at the next close. "
                   "Paper portfolio returns include fees; benchmark excludes fees. Both exclude cash dividends. Fractional simulated shares; no slippage, taxes or liquidity model. "
                   "Drawdown is daily-close observed. Caps apply to rebalances; price drift can change weights. Full daily history is in the JSON export.")
    with journal:
        trades=[dict(trader=PERSONAS[p]["name"],**t) for p,a in exp["accounts"].items() for t in a["trades"]]
        st.dataframe(pd.DataFrame(trades).round(5),hide_index=True,width="stretch")
        st.download_button("Download replay trades CSV",safe_csv_bytes(pd.DataFrame(trades)),"replay-trades.csv","text/csv")
    with log:
        rows=[]
        for records in exp["rounds"].values():
            for persona,record in records.items():
                proposal=record.get("proposal",{})
                rows.append(dict(Trader=PERSONAS[persona]["name"],Decision_date=record["decision_date"],Execution_date=record["execution_date"],
                                 Status=record["status"],Action=record.get("action",proposal.get("action","NO ORDER")),
                                 Reason=record.get("message") if record["status"]!="complete" else proposal.get("rationale"),
                                 Risks="; ".join(proposal.get("risks",[])),Targets=str(proposal.get("allocations",[])),
                                 Model_attempts=record["model_calls"],Prompt_tokens=record.get("prompt_tokens"),Completion_tokens=record.get("completion_tokens")))
        st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
        if exp["rounds"]:
            for persona,record in list(exp["rounds"].values())[-1].items():
                with st.expander(PERSONAS[persona]["name"]+" · "+record["decision_date"]+" · "+record["status"]):
                    proposal=record.get("proposal",{})
                    st.text(record.get("message",proposal.get("rationale","No validated decision")))
                    st.text("Action: "+record.get("action",proposal.get("action","NO ORDER")))
                    for risk in proposal.get("risks",[]):
                        st.text("Risk: "+risk)
        st.download_button("Download decision log CSV",safe_csv_bytes(pd.DataFrame(rows)),"replay-decisions.csv","text/csv")
        st.caption("HOLD means the trader chose no order. Failed/interrupted means no validated decision, not an investment opinion. "
                   "A REBALANCE at already-matching targets can have no trade. Rationales use price evidence, without validating every prose claim.")
    from langgraphagenticai.ui.paper_trading_tab import export_experiment
    try:
        st.download_button("Download historical experiment JSON",export_experiment(exp,(fmp_api_key,openai_api_key)),"historical-experiment.json","application/json")
    except ValueError:
        st.warning("Experiment exceeds the export size budget.")
    st.caption("Session-backed prototype: download before restarting. No background runs or account import. Create a new experiment to change settings or reload history.")
