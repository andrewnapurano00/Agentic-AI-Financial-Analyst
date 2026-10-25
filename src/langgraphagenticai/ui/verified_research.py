"""Explicit snapshot transfer and local recipient calculations; no provider/model calls."""
import streamlit as st
from langgraphagenticai.state.verified_research import create_snapshot, accept_snapshot
from langgraphagenticai.analysis.scenarios import calculate
from langgraphagenticai.state.research_context import ResearchContext
from .workspace_handoff import queue_handoff


def render_verified_handoff(saved, engine, api_key, *, reference_time=None):
    symbols = saved.get("request",{}).get("symbols",[])
    if not symbols:
        return
    origin = "Deep Research V2" if engine == "Low cost V2 pilot" else "Deep Research"
    with st.expander("Reuse verified financial research"):
        st.caption("Session-only pilot: dated total-company earnings sensitivities in AI Valuation. No annual per-share targets, AI narrative, provider refresh or model call is transferred. Legacy/unbound runs need fresh collection.")
        ticker = st.selectbox("Company for verified reuse",symbols,key="verified_company_"+engine+str(saved.get("id")))
        snapshot = None
        try:
            snapshot = create_snapshot(st.session_state,saved,ticker,engine,api_key,reference_time=reference_time)
        except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
            st.info("Financial reuse unavailable: missing original credential lineage, incompatible/changed data or stale evidence. Explicitly run fresh research; ticker navigation remains available.")
        if snapshot:
            st.caption("Eligible at "+snapshot.created_at+". Recipient rechecks scope, lineage and original evidence dates on every view/edit.")
        if st.button("Use saved verified research",key="verified_send_"+engine+str(saved.get("id")),disabled=snapshot is None):
            # A separate snapshot never enters ResearchContext or the annual valuation store.
            st.session_state["verified_sensitivity_snapshot"] = snapshot
            st.session_state["verified_sensitivity_active"] = True
            queue_handoff(st.session_state,ResearchContext((ticker,),"AI Valuation","analyze",origin))
            st.rerun()
        if st.button("Open AI Valuation with ticker only",key="verified_ticker_"+engine+str(saved.get("id"))):
            st.session_state["verified_sensitivity_active"] = False
            queue_handoff(st.session_state,ResearchContext((ticker,),"AI Valuation","analyze",origin))
            st.rerun()


def render_verified_sensitivity(ticker, api_key, *, reference_time=None):
    snapshot = st.session_state.get("verified_sensitivity_snapshot")
    if snapshot is None or st.session_state.get("verified_sensitivity_active") is False:
        return
    st.markdown("### Saved verified research · earnings sensitivity")
    try:
        inputs = accept_snapshot(st.session_state,snapshot,ticker,api_key,reference_time=reference_time)
    except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
        st.warning("Saved financial reuse rejected: company/session/credential, lineage or evidence freshness no longer qualifies. Original research remains saved. Use ticker-only navigation or explicitly refresh research and prepare a new snapshot.")
        return
    st.caption(f"Saved {inputs.ticker} TTM earnings through {inputs.ttm_through}: {inputs.net_income:,.0f} {inputs.currency}; market cap {inputs.market_cap:,.0f} {inputs.currency} as of {inputs.quote_as_of}. Run {snapshot.run_id} · {snapshot.engine}.")
    st.caption("Original retrieval times and formulas remain in the saved research. This local total-equity sensitivity is separate from the annual per-share AI targets below. Assumptions are editable, not forecasts or advice.")
    prefix = "verified_sensitivity_"+snapshot.fingerprint[:16]
    change = st.number_input("Saved earnings change (%)",min_value=-100.,max_value=200.,value=0.,key=prefix+"_change")
    pe = st.number_input("Saved earnings P/E assumption",min_value=.1,max_value=100.,value=15.,key=prefix+"_pe")
    result = calculate(inputs,change,pe)
    st.metric("Hypothetical total equity value",f"{result['hypothetical_total_equity_value']:,.0f} {inputs.currency}")
    st.caption(f"Difference versus dated saved capitalization: {result['difference_vs_saved_cap_percent']:+.2f}%. No per-share target, prospective return or model conclusion is implied.")
    with st.expander("Verified snapshot provenance"):
        st.json({"schema":snapshot.version,"purpose":snapshot.purpose,"run":snapshot.run_id,"created_at":snapshot.created_at,
                 "fingerprint":snapshot.fingerprint,"validation":snapshot.validation,"observations":__import__('json').loads(snapshot.observations_json)})
