"""Manual, session-preserved paper trading and observation-based evaluation."""
import json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

from langgraphagenticai.providers.paper_market import load_paper_market
from langgraphagenticai.paper_trading.engine import create_experiment, mark, scorecard, validate_market
from langgraphagenticai.paper_trading.workflow import demo_market, run_round
from langgraphagenticai.paper_trading.personas import PERSONAS, DEFAULT_UNIVERSE
from langgraphagenticai.utils.export_csv import safe_csv_bytes
from langgraphagenticai.paper_trading.safety import safe_text


def export_experiment(experiment, credentials=()):
    text = json.dumps(experiment, allow_nan=False, indent=2)
    for credential in credentials:
        if credential:
            text = text.replace(credential, "[REDACTED]")
    text = safe_text(text)
    if len(text.encode()) > 4000000:
        raise ValueError("Experiment exceeds the download budget.")
    return text.encode()


def render_paper_trading_tab(fmp_api_key="", openai_api_key="", model_name="gpt-5"):
    experience = st.radio("Trading workflow", ["Manual paper rounds", "Historical replay"], horizontal=True, key="paper_workflow")
    if experience == "Historical replay":
        from langgraphagenticai.ui.paper_replay_tab import render_paper_replay
        render_paper_replay(fmp_api_key, openai_api_key, model_name)
        return
    st.subheader("Agent Trading Lab")
    st.caption("Paper trading only · four fictional course-inspired personas · USD accounts · manual rounds")
    st.info("Each trader has a separate simulated account. No brokerage connection, shorting or leverage. "
            "FMP mode uses dated reference quotes, which can be a prior close; these are not executable market fills.")
    store = st.session_state.setdefault("paper_experiments_v1", {})
    with st.expander("Create a trading experiment", expanded=not bool(store)):
        with st.form("paper_create_form"):
            name = st.text_input("Experiment name", value="Four trader comparison", max_chars=80)
            mode = st.selectbox("Experiment mode", ["Demo", "FMP + AI"])
            universe = st.text_input("Trading universe (up to 8 tickers)", value=DEFAULT_UNIVERSE)
            cols = st.columns(3)
            capital = cols[0].number_input("Starting cash per trader (USD)", min_value=100., max_value=10000000., value=100000., step=1000.)
            benchmark = cols[1].text_input("Paper benchmark", value="SPY")
            cap = cols[2].number_input("Paper position limit (%)", min_value=5., max_value=100., value=30., step=5.)
            cols = st.columns(2)
            reserve = cols[0].number_input("Minimum paper cash (%)", min_value=0., max_value=90., value=10., step=5.)
            cost = cols[1].number_input("Simulated transaction cost (bps)", min_value=0., max_value=100., value=10., step=1.)
            created = st.form_submit_button("Create experiment", type="primary")
        if created:
            try:
                if len(store) >= 6:
                    raise ValueError("Six experiments are already saved in this session. Download them before starting a new session.")
                experiment = create_experiment(safe_text(name), universe, benchmark, capital, cap/100, reserve/100, cost, mode)
                store[experiment["id"]] = experiment
                st.session_state["paper_experiment_choice"] = experiment["id"]
            except ValueError as exc:
                st.warning(str(exc))
    if not store:
        st.write("Start in Demo to test the four accounts without providers or AI charges.")
        return
    st.session_state.setdefault("paper_experiment_choice", st.session_state.get("paper_active_experiment", next(iter(store))))
    selected = st.selectbox("Saved trading experiment", list(store), key="paper_experiment_choice",
                            format_func=lambda key: store[key]["name"]+" · "+store[key]["mode"]+" · "+key)
    st.session_state["paper_active_experiment"] = selected
    experiment = store[selected]
    st.caption("Fixed experiment settings: "+", ".join(experiment["universe"])+
               f" | benchmark {experiment['benchmark']} | position cap {experiment['cap']:.0%} | cash reserve {experiment['reserve']:.0%} | cost {experiment['cost_bps']:g} bps")
    with st.expander("Trader styles"):
        for persona in PERSONAS.values():
            st.write(persona["name"]+" — "+persona["style"])
            st.text(persona["instructions"])
        st.caption("Names are fictional course-inspired roles, not claims about the actual investors. Cathie's initial mandate supports IBIT/BITO only.")
    columns = st.columns(2)
    refresh = columns[0].button("Refresh paper market", key="paper_refresh", disabled=experiment["mode"] != "Demo" and not fmp_api_key)
    action = "Run demo round" if experiment["mode"] == "Demo" else "Run AI trading round"
    snapshot = experiment.get("market")
    done = bool(snapshot and len([v for v in experiment["rounds"].get(snapshot["id"], {}).values() if v["status"] == "complete"]) == 4)
    run = columns[1].button(action, key="paper_run", type="primary",
                            disabled=(not snapshot or done or not openai_api_key or not model_name) if experiment["mode"] != "Demo" else False)
    if refresh or (run and experiment["mode"] == "Demo"):
        try:
            with st.spinner("Loading the shared paper market snapshot"):
                if experiment["mode"] == "Demo":
                    fresh = demo_market(experiment)
                else:
                    args = (tuple(experiment["universe"]), experiment["benchmark"], fmp_api_key)
                    load_paper_market.clear(*args)
                    fresh = load_paper_market(*args)
                experiment = mark(experiment, fresh)
            store[selected] = experiment
        except Exception:
            st.warning("Market refresh could not establish valid dated USD evidence. Previous accounts and prices remain saved.")
    snapshot = experiment.get("market")
    if run and snapshot:
        try:
            def save_progress(value):
                store[selected] = value
            with st.status("Processing the four paper accounts", expanded=True) as status:
                experiment = run_round(experiment, snapshot, openai_api_key, model_name,
                                       progress=lambda name: st.write("Considering "+name), checkpoint=save_progress)
                status.update(label="Paper round saved; inspect decisions and any failures below", state="complete", expanded=False)
            store[selected] = experiment
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
    if experiment["mode"] == "FMP + AI":
        st.caption("Refresh loads one shared quote batch and bounded profile/TTM context. Run makes up to four paid AI requests, no model retries. "
                   "Retrying the same snapshot skips successful traders and retries only failures; fully completed snapshots cannot trade twice. "
                   "Identical quote evidence after Refresh does not create another trading opportunity.")
        if not fmp_api_key or not openai_api_key:
            st.warning("Configure FMP for market snapshots and OpenAI for AI trading rounds.")
    else:
        st.caption("Synthetic demo prices and fixed demonstration strategies. No provider/model calls; these results are not evidence of AI skill.")
    if snapshot:
        st.caption("Market retrieved: "+snapshot["retrieved_at"]+" · "+snapshot.get("provider", "Unavailable"))
        for warning in snapshot.get("warnings", []):
            st.caption(warning)
        try:
            validate_market(experiment, snapshot)
        except ValueError as exc:
            st.warning(str(exc))
    monitor, holdings, journal, decisions, evidence = st.tabs(["Monitor", "Holdings", "Trade journal", "Decisions & evaluation", "Market evidence"])
    with monitor:
        st.dataframe(pd.DataFrame(scorecard(experiment)), hide_index=True, use_container_width=True)
        history = []
        for persona, account in experiment["accounts"].items():
            for point in account["history"]:
                history.append(dict(at=point["at"], trader=PERSONAS[persona]["name"], equity=point["equity"]))
        st.line_chart(pd.DataFrame(history).pivot_table(index="at", columns="trader", values="equity", aggfunc="last"))
        st.caption("Observed paper return includes simulated costs. Benchmark is buy-and-hold price return, excluding dividends/costs. "
                   "Excess is shown only with matching quote calendar dates and an available start benchmark; intraday timing may differ. "
                   "Drawdown uses observed valuations, not continuous market prices. No annualized Sharpe or backtested skill claim.")
    with holdings:
        rows = []
        for persona, account in experiment["accounts"].items():
            for symbol, shares in account["positions"].items():
                row = (snapshot or {}).get("rows", {}).get(symbol)
                rows.append(dict(Trader=PERSONAS[persona]["name"], Symbol=symbol, Shares=shares,
                                 Reference_price=row["price"] if row else None,
                                 Value=shares*row["price"] if row else None, Quote_as_of=row["as_of"] if row else "Unavailable"))
            rows.append(dict(Trader=PERSONAS[persona]["name"], Symbol="CASH", Shares=None, Reference_price=None, Value=account["cash"], Quote_as_of="Account cash"))
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("Limits apply when validating new allocations. Price drift after a round can change weights; HOLD does not force a rebalance.")
    with journal:
        trades = [dict(trader=PERSONAS[p]["name"], **trade) for p, a in experiment["accounts"].items() for trade in a["trades"]]
        st.dataframe(pd.DataFrame(trades), hide_index=True, use_container_width=True)
        st.download_button("Download paper trades CSV", safe_csv_bytes(pd.DataFrame(trades)), "paper-trades.csv", "text/csv", key="paper_trades_download")
    with decisions:
        records = [dict(snapshot=sid, trader=PERSONAS[p]["name"], **r) for sid, records in experiment["rounds"].items() for p, r in records.items()]
        st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if k != "proposal"} for r in records]), hide_index=True, use_container_width=True)
        for persona, account in experiment["accounts"].items():
            with st.expander(PERSONAS[persona]["name"]+" decisions"):
                for decision in account["decisions"][-10:]:
                    st.caption(decision["at"]+" · "+decision["action"])
                    st.text(decision["rationale"])
                    for risk in decision["risks"]:
                        st.text("Risk: "+risk)
        st.caption("Model calls include failed attempts; tokens are reported only when supplied. Dollar costs, forecast calibration and live execution quality are not measured. "
                   "Compare equal starting capital, identical evidence and constraints. HOLD is a valid outcome.")
    with evidence:
        if snapshot:
            st.dataframe(pd.DataFrame(snapshot["rows"].values()), hide_index=True, use_container_width=True)
        st.caption("FMP context includes quote/profile and provider TTM ratios where available; no news, fresh macro investigation, audited filings or covariance model. "
                   "Profile-only currency assumes compatible quote units; no FX conversion or corporate-action adjustment. All fills are fractional reference-price simulations.")
    try:
        payload = export_experiment(experiment, (fmp_api_key, openai_api_key))
        st.download_button("Download paper experiment JSON", payload, "paper-experiment.json", "application/json", key="paper_experiment_download")
    except ValueError:
        st.warning("The experiment exceeded the download size budget.")
    st.caption("Manual shell: no background trading when the app is closed. Saved within this browser session; download the audit before restarting. "
               "Create a separate experiment to change capital, universe or limits. Up to six experiments and 50 rounds each.")
