"""Explicit Interpret → edit → Build. Saved results render without provider/model calls."""
import json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from langgraphagenticai.ui.app_shell import render_executive_cards, render_evidence_row
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
from langgraphagenticai.portfolio_architect.mandate import interpret
from langgraphagenticai.portfolio_architect.universe import eligible_names, SECTORS, THEMES, UNIVERSE
from langgraphagenticai.portfolio_architect.research import demo_snapshot, candidates
from langgraphagenticai.portfolio_architect.workflow import build
from langgraphagenticai.portfolio_architect.export import csv_bytes, json_bytes, html_bytes, allocation_rows
from langgraphagenticai.providers.portfolio_architect import collect


def _editor(mandate):
    # A new interpretation has a new widget namespace; ordinary reruns retain edits.
    version = st.session_state.get("architect_editor_version", 0)
    prefix = f"architect_edit_{version}_"
    with st.form(prefix+"form"):
        st.markdown("#### Review the mandate")
        st.caption("These controls define enforced constraints. Prompt themes are preferences; review any requirements that were not extracted.")
        cols = st.columns(3)
        horizon = cols[0].selectbox("Horizon (years)", [1,3,5,10], index=[1,3,5,10].index(mandate.horizon), key=prefix+"horizon")
        risk = cols[1].selectbox("Risk preference", ["conservative","moderate","aggressive"], index=["conservative","moderate","aggressive"].index(mandate.risk), key=prefix+"risk")
        amount = cols[2].number_input("Hypothetical amount (USD)",min_value=100.,max_value=100000000.,value=mandate.amount, key=prefix+"amount")
        cols = st.columns(3)
        n = cols[0].number_input("Holdings", min_value=5,max_value=15,value=mandate.holdings, key=prefix+"holdings")
        assets = cols[1].selectbox("Allowed assets",["both","stocks","etfs"], index=["both","stocks","etfs"].index(mandate.assets), key=prefix+"assets")
        method = cols[2].selectbox("Sizing method",["risk","equal","conviction_risk"], index=["risk","equal","conviction_risk"].index(mandate.method),
                                   format_func=lambda v:{"risk":"Volatility / correlation aware","equal":"Equal weight","conviction_risk":"Conviction + risk aware"}[v],key=prefix+"method")
        with st.expander("Allocation limits, exclusions and themes",expanded=False):
            cols = st.columns(3)
            cash = cols[0].number_input("Cash target (%)",min_value=0.,max_value=80.,value=mandate.cash*100,key=prefix+"cash")
            cap = cols[1].number_input("Max position (%)",min_value=1.,max_value=100.,value=mandate.position_cap*100,key=prefix+"cap")
            sector = cols[2].number_input("Max sector/category (%)",min_value=1.,max_value=100.,value=mandate.sector_cap*100,key=prefix+"sector")
            excluded = st.multiselect("Excluded stock sectors (all ETFs excluded when set: no look-through)",SECTORS,
                                       default=[s for s in mandate.excluded_sectors if s in SECTORS],key=prefix+"excluded")
            forbidden = st.text_input("Forbidden tickers (comma separated)",value=", ".join(mandate.forbidden),key=prefix+"forbidden")
            themes = st.multiselect("Preferred curated themes",THEMES,default=[t for t in mandate.themes if t in THEMES],key=prefix+"themes")
            benchmark = st.selectbox("Historical benchmark",sorted(UNIVERSE),index=sorted(UNIVERSE).index(mandate.benchmark) if mandate.benchmark in UNIVERSE else sorted(UNIVERSE).index("SPY"),key=prefix+"benchmark")
        submitted = st.form_submit_button("Build portfolio",type="primary")
    if not submitted:
        return None
    try:
        return InvestorMandate(objective=mandate.objective,horizon=horizon,risk=risk,amount=amount,holdings=int(n),assets=assets,
            cash=cash/100,position_cap=cap/100,sector_cap=sector/100,excluded_sectors=excluded,
            forbidden=[s.strip() for s in forbidden.split(",") if s.strip()],themes=themes,benchmark=benchmark,method=method)
    except ValueError:
        st.error("The mandate is invalid or infeasible. Check holdings × position/sector cap against the non-cash allocation, and ticker formats.")
        return None


def _report(result, credentials):
    snapshot = result.snapshot
    st.divider()
    st.markdown("### Portfolio recommendation")
    if snapshot.mode == "SYNTHETIC DEMO":
        st.warning("SYNTHETIC DEMO · Every price, fundamental and return observation is invented. This is a software demonstration.")
    else:
        try:
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(snapshot.retrieved_at)).total_seconds()
            if age > 900:
                st.warning("Saved result · quote retrieval older than fifteen minutes. Reopening does not refresh evidence; use explicit Build with fresh evidence.")
        except ValueError:
            st.warning("Evidence age unavailable.")
    render_executive_cards([("Holdings",str(len(result.holdings)),result.mandate.assets),
                            ("Cash",f"{result.cash:.1%}",f"${result.cash_dollars:,.2f}"),
                            ("Hypothetical account",f"${result.mandate.amount:,.0f}",result.method_used)])
    st.caption(f"{result.mandate.horizon}-year horizon · {result.mandate.risk} risk preference")
    render_evidence_row([("Mode",snapshot.mode),("Retrieved UTC",snapshot.retrieved_at),("Snapshot",snapshot.id),
                         ("Benchmark",result.mandate.benchmark),("Version",result.version)])
    st.caption("Research and hypothetical allocation only. No orders, forecast returns or personal suitability assessment.")
    st.write(result.mandate.objective)
    allocation, holdings, risk, committee, evidence = st.tabs(["Allocation","Holding research","Risk & tradeoffs","Investment committee","Evidence & exports"])
    with allocation:
        frame = pd.DataFrame(allocation_rows(result))
        st.dataframe(frame.drop(columns=["Sizing","Evidence IDs"]),hide_index=True,width="stretch",
                     column_config={"Weight %":st.column_config.NumberColumn(format="%.1f"),
                                    "Hypothetical USD":st.column_config.NumberColumn(format="$%.2f")})
        cols = st.columns(2)
        with cols[0]:
            st.caption("Weights (% of total hypothetical account)")
            st.bar_chart(frame.set_index("Ticker")[["Weight %"]],horizontal=True)
        with cols[1]:
            st.caption("Stock sectors / fund categories (%); no ETF look-through")
            st.bar_chart(pd.DataFrame({"Weight %":{k:v*100 for k,v in result.sectors.items()}}),horizontal=True)
        st.write("Binding constraints: "+"; ".join(result.binding_constraints))
        st.caption("Dollar amounts reconcile to cents using largest-remainder rounding. Weights are calculated before display rounding; no share execution is implied.")
    with holdings:
        facts = {s.ticker:s for s in snapshot.securities}
        for h in result.holdings:
            with st.expander(f"{h.ticker} · {h.name} · {h.weight:.1%} · ${h.dollars:,.2f}"):
                st.write("Why included: "+" ".join(h.pros))
                cols = st.columns(2)
                with cols[0]:
                    st.markdown("**Supporting observations**")
                    for p in h.pros: st.write("• "+p)
                with cols[1]:
                    st.markdown("**Counterarguments / gaps**")
                    for p in h.cons: st.write("• "+p)
                st.write("Sizing rationale: "+h.sizing)
                st.caption("Conviction: "+h.conviction+" · Subjective classification, not a return probability.")
                st.dataframe(pd.DataFrame([f.model_dump() for f in facts[h.ticker].facts]),hide_index=True,width="stretch")
                st.caption("Quote as of "+facts[h.ticker].quote_as_of+" · "+facts[h.ticker].currency_basis)
                st.write("Catalysts: not researched; obtain dated issuer/news evidence before asserting a catalyst.")
                st.write("What would change my mind? "+" ".join(h.thesis_breakers))
                for flag in facts[h.ticker].flags: st.caption(flag)
    with risk:
        r = result.risk
        if r.status == "available":
            cols = st.columns(3)
            cols[0].metric("Historical annualized volatility",f"{r.annualized_volatility:.1%}")
            cols[1].metric("Historical mix max drawdown",f"{r.max_drawdown:.1%}")
            cols[2].metric("Historical mix price return",f"{r.portfolio_return:.1%}")
            st.caption(f"{r.start} through {r.end} · {r.observations} aligned return observations · benchmark price return: "+
                       (f"{r.benchmark_return:.1%}" if r.benchmark_return is not None else "unavailable"))
        else:
            st.warning("Portfolio risk estimates unavailable; insufficient reliable aligned history. No low-risk inference is supported.")
        st.write(r.convention)
        for pair in r.high_correlations: st.write("High historical correlation: "+pair)
        for p in result.committee.vulnerabilities: st.write("• "+p)
        st.write("Qualitative scenarios: rising rates can pressure long-duration growth and bonds; an earnings contraction can weaken equities; a sector shock can overwhelm category diversification. No numerical scenario loss is estimated.")
        with st.expander("Data and methodology disclosures"):
            for note in list(dict.fromkeys(result.warnings+r.warnings)): st.write("• "+note)
    with committee:
        st.info(result.committee.source)
        for role, description in result.committee.roles.items():
            st.markdown("**"+role+"**")
            st.write(description)
        st.markdown("#### Initial proposal → final construction")
        for change in result.committee.changes: st.write("• "+change)
        st.markdown("#### Unresolved disagreements")
        for p in result.committee.disagreements: st.write("• "+p)
        st.markdown("#### Rejected / excluded alternatives")
        st.dataframe(pd.DataFrame([{"Ticker":k,"Reason":v} for k,v in result.committee.rejected.items()]),hide_index=True,width="stretch")
        st.markdown("#### What would change my mind?")
        st.write("Refresh deteriorating profitability evidence, reassess valuation with dated earnings, investigate volatility/concentration changes and replace missing or conflicting data. User assumptions can change; this saved report does not monitor them automatically.")
    with evidence:
        st.caption("Saved evidence only; these downloads do not refresh providers or call AI. JSON/HTML omit raw user prompts and retain provenance/history.")
        cols = st.columns(3)
        cols[0].download_button("Allocation CSV",csv_bytes(result,credentials),"portfolio_architect.csv","text/csv",key="architect_csv")
        cols[1].download_button("Evidence JSON",json_bytes(result,credentials),"portfolio_architect.json","application/json",key="architect_json")
        cols[2].download_button("Research HTML",html_bytes(result,credentials),"portfolio_architect.html","text/html",key="architect_html")
        st.json({"snapshot_id":snapshot.id,"mode":snapshot.mode,"universe_version":snapshot.universe_version,
                 "excluded":snapshot.excluded,"model":result.model,"usage":result.usage,"warnings":result.warnings})
    if st.button("Save session snapshot",key="architect_save"):
        saved = st.session_state.setdefault("architect_saved",{})
        if result.id in saved or len(saved) < 6:
            saved[result.id] = result.model_dump(mode="json")
            st.success("Snapshot saved in this session. Download before closing the app.")
        else:
            st.warning("Six snapshots already saved; download your results before ending this session.")


def render_portfolio_architect(fmp_api_key="", openai_api_key="", model_name="gpt-5"):
    st.subheader("AI Portfolio Architect")
    st.caption("Mandate → evidence → deterministic construction → committee review · research only")
    mode = st.radio("Research mode",["SYNTHETIC DEMO","FMP live"],horizontal=True,key="architect_mode")
    use_ai = st.checkbox("Use bounded AI interpretation and specialist review",value=False,key="architect_use_ai",
                         help="At most one interpretation call and one specialist call; no model retries. Demo always stays offline.")
    if mode == "SYNTHETIC DEMO":
        st.info("Offline demo uses invented evidence and local interpretation. AI is disabled in this mode.")
    prompt = st.text_area("Investment objective",value="Build an aggressive five-year growth portfolio focused on AI with diversified risk.",height=110,max_chars=1800,key="architect_prompt")
    force = st.checkbox("Refresh provider evidence on next Build",value=False,key="architect_force")
    if st.button("Interpret mandate",key="architect_interpret",type="primary"):
        try:
            live_ai = mode == "FMP live" and use_ai
            if live_ai and not openai_api_key:
                raise ValueError("OpenAI missing")
            safe_prompt = prompt
            for configured_key in (fmp_api_key,openai_api_key):
                if configured_key:
                    safe_prompt = safe_prompt.replace(configured_key,"[REDACTED]")
            with st.spinner("Preparing an editable mandate"):
                mandate, notes, usage = interpret(safe_prompt,openai_api_key,model_name,live_ai)
            # Sanitize exact configured values before retaining any user/model text.
            for key in (fmp_api_key,openai_api_key):
                if key:
                    mandate = mandate.model_copy(update={"objective":mandate.objective.replace(key,"[REDACTED]")})
            st.session_state["architect_mandate"] = mandate.model_dump()
            st.session_state["architect_notes"] = notes
            st.session_state["architect_interpret_usage"] = usage
            st.session_state["architect_editor_version"] = st.session_state.get("architect_editor_version",0)+1
        except Exception:
            st.error("Interpretation failed or returned invalid constraints. Previous mandate and results remain. Disable AI for a transparent local draft or revise the prompt.")
    if st.session_state.get("architect_mandate"):
        mandate = InvestorMandate.model_validate(st.session_state["architect_mandate"])
        for note in st.session_state.get("architect_notes",[]): st.caption(note)
        if prompt.strip() != mandate.objective.strip():
            st.caption("The prompt differs from the interpreted mandate. Click Interpret mandate to apply the revised objective.")
        requested = _editor(mandate)
        if requested:
            try:
                if mode == "FMP live" and not fmp_api_key:
                    raise ValueError("Configure FMP in Settings for live evidence, or choose SYNTHETIC DEMO.")
                if mode == "FMP live" and use_ai and not openai_api_key:
                    raise ValueError("Configure OpenAI or disable AI; local live construction is available without it.")
                names = eligible_names(requested)
                with st.spinner("Collecting a bounded evidence snapshot and constructing the portfolio"):
                    snapshot = demo_snapshot(names,requested.benchmark) if mode == "SYNTHETIC DEMO" else collect(names,requested.benchmark,fmp_api_key,force)
                    st.session_state["architect_last_evidence"] = snapshot.model_dump(mode="json")
                    eligible, _, excluded = candidates(snapshot,requested)
                    st.session_state["architect_collection_status"] = dict(requested=len(names), provider_eligible=len(snapshot.securities),
                        mandate_eligible=len(eligible), excluded=excluded)
                    if not snapshot.securities:
                        raise ValueError("No securities passed provider validation. Review collection diagnostics below; changing allocation constraints will not repair missing quotes.")
                    local = build(snapshot,requested)
                    st.session_state["architect_result"] = local.model_dump(mode="json")  # checkpoint before paid review
                    if mode == "FMP live" and use_ai:
                        local = build(snapshot,requested,openai_api_key,model_name,True)
                    usage = st.session_state.get("architect_interpret_usage")
                    if usage: local.usage.insert(0,{**usage,"stage":"interpretation"})
                    st.session_state["architect_result"] = local.model_dump(mode="json")
                    st.session_state["architect_mandate"] = requested.model_dump()
            except ValueError as exc:
                # Only locally generated validation messages reach this path.
                st.error(str(exc))
            except Exception:
                st.error("Portfolio construction could not complete. Previous results and collected evidence remain; no automatic retry occurred.")
    latest = st.session_state.get("architect_last_evidence")
    if latest:
        status = st.session_state.get("architect_collection_status",{})
        with st.expander("Latest collection diagnostics",expanded=not latest.get("securities")):
            st.caption("Saved collection; viewing these details does not call providers or models. "+str(latest.get("retrieved_at","")))
            st.write(f"Provider-eligible: {status.get('provider_eligible',len(latest.get('securities',[])))}; "
                     f"mandate-eligible: {status.get('mandate_eligible','unavailable')}; requested universe: {status.get('requested','unavailable')}.")
            for warning in latest.get("warnings",[]):
                st.write("• "+warning)
            excluded = status.get("excluded",latest.get("excluded",{}))
            if excluded:
                st.dataframe(pd.DataFrame([{"Ticker":symbol,"Exclusion reason":reason} for symbol,reason in excluded.items()]),hide_index=True,width="stretch")
            st.caption("For provider failures, check endpoint access, credentials or network configuration, then enable Refresh provider evidence on next Build and click Build portfolio. For mandate exclusions, revise the relevant controls.")
    if st.session_state.get("architect_result"):
        from langgraphagenticai.portfolio_architect.schemas import PortfolioRecommendation
        _report(PortfolioRecommendation.model_validate(st.session_state["architect_result"]),(fmp_api_key,openai_api_key))
    elif st.session_state.get("architect_last_evidence"):
        st.warning("Collection did not produce a portfolio. Review provider warnings and exclusion reasons in Latest collection diagnostics before retrying.")
    else:
        st.caption("Start with Interpret mandate, review the controls, then Build portfolio. No collection or AI runs automatically.")
    if st.session_state.get("architect_saved"):
        from langgraphagenticai.portfolio_architect.schemas import PortfolioRecommendation
        saved = st.session_state["architect_saved"]
        selected = st.selectbox("Saved session snapshots",list(saved),key="architect_saved_choice")
        if st.button("Open saved snapshot",key="architect_open"):
            st.session_state["architect_result"] = saved[selected]
            st.rerun()
