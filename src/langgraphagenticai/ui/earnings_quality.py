"""Shared earnings presentation; original report values remain intact."""
from datetime import datetime, timezone
import streamlit as st
from langgraphagenticai.analysis.earnings_metrics import research_net_income


def render_earnings_quality(saved, *, reference_time=None):
    reference_time = reference_time or datetime.now(timezone.utc).isoformat()
    observations = [research_net_income(saved, ticker, basis=basis, reference_time=reference_time).to_dict()
                    for ticker in saved.get("request", {}).get("symbols", [])[:4]
                    for basis in ("quarterly", "annual", "TTM")]
    if observations:
        st.caption("Saved earnings quality: " + "; ".join(o["ticker"] + " TTM " + o["status"]
                   for o in observations if o["basis"] == "TTM") + ". Original report amounts are retained.")
    with st.expander("Earnings data quality · quarterly, annual and TTM"):
        st.caption("Read-only validation of saved statements and total company earnings. "
                   "No refresh, saved-report replacement or EPS/FFO/AFFO/future-target certification.")
        st.caption("Retrieval-age limit: thirty days. Fiscal age limits: quarterly/TTM two hundred days, annual five hundred fifty days. "
                   "Amounts are unscaled; filing/acceptance dates remain separate from fiscal end. "
                   "Absent duration metadata retains the disclosed standalone-flow assumption.")
        if not observations:
            st.info("No saved company identity is available.")
            return
        st.dataframe([{"Company": o["ticker"], "Basis": o["basis"], "Value": o["value"],
                       "Currency": o["currency"] or "Unknown", "Fiscal as of": o["as_of"] or "Unknown",
                       "State": o["status"], "Origin": o["origin"], "Valid zero": o["valid_zero"],
                       "Source retrieval": ", ".join(sorted({i["retrieved_at"] for i in o["inputs"]})) or "Unknown"}
                      for o in observations], hide_index=True, width="stretch")
        for o in observations:
            if o["reasons"]:
                st.caption(o["ticker"] + " " + o["basis"] + ": " + "; ".join(o["reasons"]))
        with st.expander("Earnings formulas, source inputs and filing availability"):
            st.json(observations)
