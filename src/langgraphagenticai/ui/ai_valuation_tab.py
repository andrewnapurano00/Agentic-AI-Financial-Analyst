"""AI-first valuation: one explicit action produces three calculated price targets."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import streamlit as st

from langgraphagenticai.providers.valuation import load_valuation_evidence
from langgraphagenticai.providers.company_evidence import saved_company_evidence
from langgraphagenticai.state.research_context import normalize_company_symbol, ResearchContext
from langgraphagenticai.ui.app_shell import render_company_header, render_evidence_row, render_executive_cards
from langgraphagenticai.ui.workspace_handoff import queue_handoff
from langgraphagenticai.ui.valuation_charts import scenario_chart, sensitivity_chart
from langgraphagenticai.valuation.model import prepare, calculate_ai_cases
from langgraphagenticai.valuation.projection import projection_basis
from langgraphagenticai.valuation.diagnostics import driver_diagnostics, target_requirements
from langgraphagenticai.valuation.ai import evidence_packet, generate_assumptions
from langgraphagenticai.valuation.errors import failure_state
from langgraphagenticai.valuation.coverage import coverage_rows
from langgraphagenticai.deep_research.executive import executive_prose
from langgraphagenticai.utils.safety import redact_sensitive_text


def _prose(value):
    text = executive_prose(redact_sensitive_text(value, max_length=1600))
    text = re.sub(r"\[[^]\n]*(?:income|balance|quote|profile|estimates|metric|technicals|ratios|metrics|targets|cashflow):[^]\n]*\]", "", text, flags=re.I)
    text = re.sub(r"(?:income|balance|quote|profile|estimates|metric|technicals|ratios|metrics|targets|cashflow):[A-Za-z0-9_]+", "", text, flags=re.I)
    text = re.sub(r"\((?:income|balance|cashflow|quote|profile|estimate)\s+(?:series|data|records?)[^)]*\)", "", text, flags=re.I)
    text = re.sub(r"[([][\s,;|.]*[)\]]", "", text)
    return re.sub(r"\s+([,.;:])", r"\1", re.sub(r"[ \t]{2,}", " ", text)).strip()


def _save(store, key, value):
    store.pop(key, None)
    store[key] = value
    while len(store) > 8:
        del store[next(iter(store))]


def _scenario_output(facts, packet, cases, years, *, hurdle=.10, ai_generation=None):
    result = calculate_ai_cases(facts, years, cases, hurdle=hurdle)
    base = next(c for c in cases if c["name"] == "Base")
    return dict(result=result, years=years, growth=base["growth_pct"]/100, multiple=base["terminal_multiple"], hurdle=hurdle,
        cases=cases, fingerprint=packet["fingerprint"], facts=facts, generated_at=datetime.now(timezone.utc).isoformat(), ai_generation=ai_generation)


def render_ai_valuation_tab(fmp_api_key="", openai_api_key="", model_name="gpt-5"):
    st.caption("AI PRICE TARGETS  /  BEAR · BASE · BULL  /  FUNDAMENTALS + FORECASTS + MOMENTUM")
    if "valuation_ticker" not in st.session_state:
        st.session_state["valuation_ticker"] = st.session_state.get("valuation_last_ticker", "AAPL")
    if "valuation_horizon" not in st.session_state:
        st.session_state["valuation_horizon"] = st.session_state.get("valuation_last_horizon", 5)
    a,b = st.columns([3,1])
    text = a.text_input("Company ticker", value=None, key="valuation_ticker", max_chars=16)
    years = b.selectbox("Target horizon (years)", [3,4,5], index=None, key="valuation_horizon")
    st.session_state["valuation_last_ticker"] = text
    st.session_state["valuation_last_horizon"] = years
    try:
        symbol = normalize_company_symbol(text)
    except ValueError:
        st.info("Enter a valid company ticker, such as AAPL or BRK-B.")
        return
    from .verified_research import render_verified_sensitivity
    render_verified_sensitivity(symbol, fmp_api_key)
    scope = sha256(fmp_api_key.encode()).hexdigest()[:16]
    key = f"{scope}:{symbol}"
    ai_key = key+":"+sha256(openai_api_key.encode()).hexdigest()[:16]
    evidence = st.session_state.setdefault("valuation_evidence", {})
    summaries = st.session_state.setdefault("valuation_summaries", {})
    failures = st.session_state.setdefault("valuation_failures", {})
    scenarios = st.session_state.setdefault("valuation_scenarios", {})
    controls = st.session_state.setdefault("valuation_controls", {})
    if key not in controls:
        _save(controls,key,{})
    control = controls[key]
    a,b = st.columns([2,1])
    run = a.button("Generate AI Valuation", type="primary", key="valuation_generate", disabled=not bool(fmp_api_key and openai_api_key and model_name and years))
    refresh = b.button("Refresh company metrics", key="valuation_load", disabled=not bool(fmp_api_key))
    st.caption("Generate loads available company metrics when needed, then creates three AI valuation cases and their price targets. Changing controls reuses saved analysis.")
    if not fmp_api_key or not openai_api_key:
        st.info("Configure FMP and OpenAI in Settings to generate AI price targets. Refresh company metrics works with FMP alone.")
    raw = evidence.get(key)
    # Upgrade the earlier five-feed shell on explicit generation, never on navigation.
    needs_evidence = not raw or raw.get("evidence_version") != 3
    if raw:
        try:
            retrieved=datetime.fromisoformat(str(raw.get("retrieved_at","")).replace("Z","+00:00"))
            needs_evidence = needs_evidence or retrieved.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-retrieved).total_seconds() <= 300
        except (ValueError,TypeError):
            needs_evidence=True
    if refresh or (run and needs_evidence):
        try:
            with st.spinner(f"Loading {symbol} company metrics"):
                shared = None if refresh else saved_company_evidence(st.session_state, symbol, fmp_api_key)
                new = load_valuation_evidence(symbol, fmp_api_key, refresh=True, **({"shared":shared} if shared else {}))
            if raw:
                for kind,status in new.get("sources",{}).items():
                    if status.get("status")=="failed" and raw.get(kind):
                        new[kind]=raw[kind]
                        new["sources"][kind]=raw.get("sources",{}).get(kind,{})
                        new["warnings"].append(f"Retained previous {kind} with its original retrieval time.")
            if any(new.get(k) for k in ("quote","profile","income","balance")):
                _save(evidence,key,new)
                raw=new
            else:
                st.warning("No usable company metrics returned. Previous evidence remains saved.")
                run=False
        except Exception:
            st.error("Company metrics could not be loaded. Previous analysis remains saved; refresh to retry.")
            run=False
    if not raw:
        if saved_company_evidence(st.session_state, symbol, fmp_api_key):
            st.caption("Dated Equity Report inputs are available for this company. Generate reuses compatible inputs and loads any missing annual evidence.")
        st.info("Select a company and Generate AI Valuation to see Bear/Base/Bull targets and potential upside or downside.")
        render_executive_cards([("Bear", "Downside case", "Weaker growth, profitability or valuation."),("Base", "AI central case", "Expected execution under the stated assumptions."),("Bull", "Upside case", "Stronger execution and valuation support.")])
        return
    facts=prepare(raw,use_disclosed_assumptions=True,dated_projection=True)
    reused = [kind.replace("quarter_", "quarterly ") for kind, source in raw.get("sources",{}).items() if source.get("reused")]
    if reused:
        st.caption("Reused dated Equity Report evidence: " + ", ".join(reused) + ". Missing annual inputs are collected separately; original retrieval times are preserved.")
    display_method=facts.get("method_label", facts["method"])
    render_company_header(symbol,f"{facts['company']} · {facts['sector']}",f"{display_method} · annual FY")
    render_evidence_row([("Provider","FMP"),("Annual basis",facts["as_of"] or "Unavailable"),("Quote as of",facts["quote_as_of"] or "Unavailable"),("Metrics retrieved",raw.get("retrieved_at","Unavailable")),("Currency",facts["currency"])])
    cols=st.columns(3)
    cols[0].metric("Current reference price",f"{facts['price']:,.2f} {facts['quote_currency']}" if facts["price"] else "Unavailable")
    cols[1].metric(facts["basis_label"],f"{facts['basis']:,.2f} {facts['currency']}" if facts["basis"] is not None else "Unavailable")
    cols[2].metric(f"Observed annual {facts['method']}", f"{facts['current_multiple']:.1f}x" if facts["current_multiple"] else "Unavailable")
    if facts.get("method_note"):
        st.info(display_method + ": " + facts["method_note"])
    packet=None
    try:
        packet=evidence_packet(facts,raw)
    except (ValueError,TypeError):
        st.warning("Company metrics could not be prepared safely. Refresh metrics to recover.")
    if packet:
        coverage=coverage_rows(packet)
        counts={group:sum(r["Category"]==group for r in coverage) for group in ("Fundamentals","Valuation","Technicals","Analyst expectations")}
        st.caption("Available research inputs: "+" · ".join(f"{group}: {count}" for group,count in counts.items()))
        with st.expander("What the AI is using",expanded=False):
            st.dataframe(coverage,hide_index=True,use_container_width=True,column_config={"Source ID":None,"Used by AI":None})
            st.caption("These are inputs actually included in this company's request. Annual facts, reused quarterly calculations, provider TTM metrics and forecasts remain separate. Peer comparisons and macro forecasts are not currently included.")
    if facts["eligible"] and years:
        anchor=projection_basis(facts,years)
        if anchor["kind"]=="annual consensus forecast":
            st.caption(f"Target earnings anchor: {anchor['value']:.2f} {facts['currency']} consensus EPS for {anchor['date']} · {anchor['analysts']:g} analysts · reference price / anchor EPS {facts['price']/anchor['value']:.1f}×. Case growth starts after this forecast date.")
        else:
            st.caption("Target anchor: " + facts["basis_label"] + ". Growth includes elapsed time since its fiscal date; no forward EPS is substituted.")
    if facts["reasons"]:
        st.warning("Targets unavailable: "+" ".join(facts["reasons"]))
        if facts["method"] == "P/B" and facts["basis"] is None:
            st.caption("Common BVPS needs common equity and fiscal year-end outstanding common shares. Diluted average shares, stock capital amounts and provider TTM book value are not interchangeable with that denominator. Refresh company metrics to retry the annual as-reported source.")
    if run and packet and facts["eligible"]:
        try:
            with st.spinner("AI is building Bear, Base and Bull valuation cases"):
                saved=generate_assumptions(facts,raw,openai_api_key,model_name)
                output=_scenario_output(facts,packet,saved["ai"]["scenarios"],years,ai_generation=saved["generated_at"])
            _save(summaries,ai_key,saved)
            _save(scenarios,key,output)
            control["cases"]=[dict(c) for c in saved["ai"]["scenarios"]]
            control["hurdle"]=10.
            for case in control["cases"]:
                for field in ("growth_pct","terminal_multiple"):
                    st.session_state[f"valuation_case_{key}_{case['name']}_{field}"]=float(case[field])
            failures.pop(ai_key,None)
        except Exception as exc:
            _save(failures,ai_key,{**failure_state(exc),"model":redact_sensitive_text(model_name,max_length=80)})
    if ai_key in failures:
        failure=failures[ai_key]
        st.error(failure["message"]+(" Previous analysis remains saved." if ai_key in summaries else " No new AI valuation was saved."))
        with st.expander("AI valuation request status"):
            st.json({k:v for k,v in failure.items() if k!="message"})
    saved=summaries.get(ai_key)
    current=bool(saved and packet and saved["packet"]["fingerprint"]==packet["fingerprint"] and saved["model"]==model_name)
    if saved and not current:
        st.warning("Saved AI analysis uses earlier metrics or model settings. Generate again to refresh its valuation cases.")
    output=scenarios.get(key)
    if output and not output.get("cases"):
        st.info("Earlier manual scenarios remain saved. Generate AI Valuation to replace them with three AI-selected cases.")
        output=None
    # A horizon change recalculates the same saved annual assumptions locally, without a new AI request.
    if output and current and facts["eligible"] and years and output.get("years")!=years and output.get("cases") and output["fingerprint"]==packet["fingerprint"]:
        output=_scenario_output(facts,packet,output["cases"],years,hurdle=output["hurdle"],ai_generation=output["ai_generation"])
        _save(scenarios,key,output)
    if output and facts["eligible"]:
        if not packet or output["fingerprint"]!=packet["fingerprint"]:
            st.warning("Saved targets use earlier company metrics or valuation methodology. Generate again to rebuild them using the current earnings bridge.")
        st.markdown(f"### {output['years']}-year {'AI ' if output['ai_generation'] else ''}price targets")
        cols=st.columns(3)
        for col,(name,row) in zip(cols,output["result"].items()):
            col.metric(f"{name} price target",f"{row['target']:,.2f} {output['facts']['currency']}",f"{row['price_return']:+.1%} {'upside' if row['price_return']>=0 else 'downside'}")
            col.caption(f"{row['cagr']:+.1%} annualized price return · {row['growth']:.1%} growth · {row['exit_multiple']:.1f}×")
            projection=row.get("projection",{})
            col.caption(f"Exit EPS / BVPS: {row['end_basis']:.2f} × {row['exit_multiple']:.1f} = {row['target']:.2f}")
            if projection.get("target_date"):
                col.caption(f"{projection['kind']}: {projection['value']:.2f} ({projection['date']}); {projection['years']:.2f} growth years to {projection['target_date']}")
            col.write(_prose(row.get("rationale","")) if output["ai_generation"] else "User-edited assumptions; original AI rationale is retained in the saved investment view.")
        if output["facts"].get("projection_method")=="dated-consensus-v1":
            st.caption("Targets are dated from the reference quote. Where eligible, all cases share the nearest forward annual consensus EPS (at least three analysts); case growth applies only after that forecast date. Near-term consensus uncertainty is not separately modeled. Otherwise growth starts at the reported fiscal date.")
        diagnostic=driver_diagnostics(output["facts"],output["cases"],output["years"])
        if diagnostic["near_flat"]:
            st.warning("All three cases assume at most 1% annual earnings growth despite a supplied consensus path of at least 5%. Review the growth assumptions below; values have not been automatically increased.")
        with st.expander("Growth and valuation drivers",expanded=diagnostic["near_flat"]):
            st.dataframe(diagnostic["rows"],hide_index=True,use_container_width=True)
            st.caption("Growth units: 20 means 20%; 0.20 means 0.20%. The forecast growth path covers its stated fiscal dates, not necessarily the full target horizon.")
            if saved and saved["packet"]["fingerprint"]==output["fingerprint"] and (not output["ai_generation"] or saved["generated_at"]==output["ai_generation"]):
                st.write("Growth rationale: "+_prose(saved["ai"]["growth_reason"]))
                st.write("Exit-multiple rationale: "+_prose(saved["ai"]["multiple_reason"]))
                if not output["ai_generation"]:
                    st.caption("Rationales describe the original AI cases; the displayed assumptions have been edited.")
        with st.expander("What would it take for the stock to double?"):
            st.caption("A hypothetical 2x price scenario, not a prediction or an additional AI recommendation. Required earnings growth uses each displayed exit multiple and the same dated earnings anchor.")
            st.dataframe(target_requirements(output["facts"],output["cases"],output["years"]),hide_index=True,use_container_width=True,column_config={
                "Exit multiple":st.column_config.NumberColumn("Exit multiple",format="%.1fx"),
                "Hypothetical target":st.column_config.NumberColumn(f"2x reference price ({output['facts']['quote_currency']})",format="%.2f"),
                "Required exit EPS / BVPS":st.column_config.NumberColumn(f"Required exit EPS / BVPS ({output['facts']['currency']})",format="%.2f"),
                "Required annual growth (%)":st.column_config.NumberColumn("Required annual growth (%)",format="%.2f%%"),
            })
        a,b=st.columns(2)
        with a:
            st.markdown("**Price targets versus current price**")
            st.altair_chart(scenario_chart(output["facts"],output["result"],output["years"]),use_container_width=True)
        with b:
            st.markdown("**Growth and valuation sensitivity**")
            st.altair_chart(sensitivity_chart(output["facts"],output["years"],output["growth"],output["multiple"]),use_container_width=True)
        st.caption(f"{'AI-selected' if output['ai_generation'] else 'User-edited'} scenario assumptions; target prices and signed upside/downside calculated locally from the saved reference quote. Generated {output['ai_generation'] or output['generated_at']}. Future nominal exit prices exclude dividends, dilution, capital actions, FX and leverage changes; no scenario probabilities.")
        if not output["ai_generation"]:
            st.info("The saved AI investment view describes the original cases. Edited targets have not been re-reviewed by AI.")
    elif not saved and facts["eligible"]:
        st.info("Company metrics are ready. Generate AI Valuation to calculate three price targets automatically.")
    if saved:
        view=saved["ai"]
        st.markdown("### AI investment view")
        render_executive_cards([("AI research opinion",view["recommendation"],"Conditional research view."),("Evidence confidence",view["confidence"],"Qualitative, not a probability."),("Valuation method",saved["packet"].get("valuation_framework",{}).get("label") or saved["packet"].get("method",display_method),_prose(view["sector_logic"]))])
        st.write(_prose(view["thesis"]))
        a,b=st.columns(2)
        with a:
            st.markdown("**What supports the targets**")
            for item in view["catalysts"]: st.write("• "+_prose(item))
        with b:
            st.markdown("**What could change the outcome**")
            for item in view["risks"]: st.write("• "+_prose(item))
        st.caption("Reassess if: "+_prose(view["invalidation"]))
        st.caption(_prose(view["limitations"]))
        if not view.get("scenarios"):
            st.info("This saved view predates automatic price targets. Generate AI Valuation to build three cases from the richer metrics.")
    if output and output.get("cases") and facts["eligible"] and packet and output["fingerprint"]==packet["fingerprint"]:
        with st.expander("Adjust scenario assumptions",expanded=False):
            edited=[]
            for column,name in zip(st.columns(3),("Bear","Base","Bull")):
                case=next(c for c in control.get("cases",output["cases"]) if c["name"]==name)
                with column:
                    st.markdown(f"**{name} case**")
                    growth=st.number_input(f"{name} annual growth (%)",min_value=-45.,max_value=60.,value=float(case["growth_pct"]),step=.5,key=f"valuation_case_{key}_{name}_growth_pct",help="Annual growth after the displayed earnings anchor. Near-term consensus growth is already included in that anchor.")
                    multiple=st.number_input(f"{name} exit multiple (×)",min_value=.1,max_value=300.,value=float(case["terminal_multiple"]),step=.5,key=f"valuation_case_{key}_{name}_terminal_multiple")
                    edited.append({**case,"growth_pct":growth,"annual_growth_decimal":growth/100,"terminal_multiple":multiple})
            if st.button("Recalculate scenarios",key="valuation_calculate"):
                try:
                    _save(scenarios,key,_scenario_output(facts,packet,edited,years,ai_generation=None))
                    control["cases"]=edited
                    st.rerun()
                except (ValueError,TypeError):
                    st.error("Enter valid assumptions with Bear target ≤ Base target ≤ Bull target. Existing targets remain saved.")
    with st.expander("Metrics, sources & valuation assumptions"):
        st.write("The AI selects three annual growth/exit-multiple cases. New targets use a dated annual consensus EPS anchor when supported, otherwise reported EPS/common BVPS. Growth runs from that anchor to the quote-relative exit date. Legacy saved targets retain their original formula: target = annual EPS or common BVPS × (1+growth)^years × exit multiple. Upside/downside = target / saved reference price − 1. Annualized price return = (target / price)^(1/years) − 1.")
        st.write("Conditional scenarios assume compatible quote/profile/statement currency units and corporate-action basis when the provider does not independently verify them. Known currency conflicts, stale quotes and invalid earnings/book-value inputs still block targets. Missing specialist inputs use the disclosed provisional framework where usable earnings evidence exists.")
        for warning in facts["warnings"]: st.write("• "+_prose(warning))
        if packet:
            st.dataframe([{"Metric":r["id"].removeprefix("metric:"),**r["fields"]} for r in packet["evidence"] if r["kind"]=="calculated_metric"],hide_index=True,use_container_width=True)
        if facts["estimates"]: st.dataframe(facts["estimates"],hide_index=True,use_container_width=True)
        st.json({"sources":raw.get("sources"),"blockers":facts["reasons"],"valuation_framework":facts.get("method_label"),"annual_formula":facts.get("formula"),"annual_book_value_inputs":facts.get("book_value_contract"),"basis_source_ids":facts.get("basis_source_ids"),"compatibility_basis":facts.get("compatibility_basis")})
        if saved: st.json(saved["packet"])
    if st.button("Continue in Deep Research",key="valuation_research"):
        queue_handoff(st.session_state,ResearchContext((symbol,),"Deep Research","deep_research","AI Valuation"))
        st.rerun()
    st.caption("Conditional AI valuation scenarios, not personalized investment advice. Missing peers or macro context limits confidence; it does not automatically prevent price targets.")
