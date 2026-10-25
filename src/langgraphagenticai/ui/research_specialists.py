"""Opt-in one-company specialist audit, separate from original reports/committees."""
import streamlit as st

from langgraphagenticai.deep_research.specialist_workflow import collect_saved, fingerprint, run_specialists
from langgraphagenticai.providers.research_specialists import call_specialist
from langgraphagenticai.utils.safety import sanitize_error


def render_specialists(result, *, engine, api_key, model):
    with st.expander("Independent specialist review · experimental"):
        st.caption("Two separate company-research model calls, exact observation checks and deterministic reconciliation. "
                   "At most one extra call resolves a named gap from saved metrics only. No fresh data or automatic committee. "
                   "Evidence and claim verification remain limited; this is an experimental pilot, not verified advice. "
                   "Each call allows at most 1,200 output tokens and a 25-second client timeout; "
                   "the run stops scheduling after 90 seconds. This separate action is outside the original report's budget. "
                   "Pricing is unknown, so there is no guaranteed dollar ceiling.")
        key = "specialists_" + engine + "_" + str(result.get("id", "saved"))
        refs, gaps = collect_saved(result)
        st.caption(f"Eligible saved metrics: {len(refs)}. Original retrieval/financial dates are retained.")
        if not refs:
            st.info("No eligible one-company audited evidence. " + " ".join(gaps[:2]))
        with st.expander("Evidence eligibility and missing metrics"):
            st.caption("Pilot retrieval-age limits: quotes one day, other inputs thirty days. "
                       "Observation-age limits: quotes seven days, current TTM/latest balances two hundred days, "
                       "historical matched balances eight hundred days. Unknown dates/currencies are ineligible.")
            for gap in gaps:
                st.write(gap)
        acknowledge = st.checkbox("I understand the pilot limitations and additional model calls", key=key + "_ack")
        if st.button("Run independent specialists on saved evidence", key=key + "_run",
                     disabled=not (refs and acknowledge and api_key and model)):
            try:
                with st.spinner("Running bounded specialist review"):
                    review = run_specialists(result, lambda task, evidence: call_specialist(
                        task, evidence, api_key=api_key, model=model))
                # Failed attempts never erase an earlier usable specialist review.
                previous = st.session_state.get(key)
                valid_count = lambda run: sum(a["status"] == "finished" for a in run["agents"])
                if previous and (review["decision"]["status"] == "unavailable" or valid_count(review) < valid_count(previous)):
                    st.session_state[key + "_failed_attempt"] = review
                else:
                    st.session_state[key] = review
                    st.session_state.pop(key + "_failed_attempt", None)
            except Exception as exc:
                st.error("Specialist review stopped. " + sanitize_error(exc) + " Original research is preserved.")
        review = st.session_state.get(key)
        if st.session_state.get(key + "_failed_attempt"):
            st.warning("The latest specialist attempt failed or returned fewer usable specialists. Prior specialist output is retained; no automatic retry.")
            with st.expander("Failed specialist attempt audit"):
                st.json(st.session_state[key + "_failed_attempt"])
        if not review:
            return
        if review["source_fingerprint"] != fingerprint(result):
            st.warning("Saved evidence changed after this specialist review. The prior output is retained; explicitly run again to review the current evidence.")
        decision = review["decision"]
        st.markdown("**Specialist work summary · " + decision["status"] + " · " + decision["agreement"] + "**")
        labels = {"fundamentals": "Fundamentals", "valuation_risk": "Valuation and risk"}
        for agent in review["agents"]:
            count = len(agent["result"]["observations"]) if agent.get("result") else 0
            st.write(f"{labels[agent['role']]}: {agent['status']} · {count} cited "
                     + ("observation" if count == 1 else "observations"))
            if agent.get("result"):
                st.write(agent["result"]["summary"])
                for risk in agent["result"]["risks"]:
                    st.write("Risk: " + risk)
            elif agent.get("error"):
                st.caption(agent["error"])
        for dissent in decision["disagreements"]:
            role, stance = dissent.split(": ", 1)
            st.warning("Named disagreement: " + labels[role] + ": " + stance)
        st.caption(f"{review['model_attempts']} model attempts · {len(review['tool_dispatches'])} local gap lookups · "
                   f"{review['elapsed_seconds']:.1f}s. No measured quality/cost advantage established.")
        with st.expander("Specialist source audit, checks and research gaps"):
            st.json(review)
