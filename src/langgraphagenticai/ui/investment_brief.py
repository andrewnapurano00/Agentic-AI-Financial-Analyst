"""D10: the same saved-only brief and sensitivity controls in both research versions."""
from datetime import datetime, timezone
import hashlib
import json
import pandas as pd
import streamlit as st
from langgraphagenticai.analysis.scenarios import saved_inputs, calculate
from langgraphagenticai.analysis.investment_brief import brief, export_packet, exports, safe_text

def render_investment_brief(result, workspace, credentials=(), reference_time=None):
    reference_time = reference_time or datetime.now(timezone.utc).isoformat()
    key = "brief_" + hashlib.sha256(json.dumps([workspace,result.get("id"),result.get("request",{}).get("symbols")]).encode()).hexdigest()[:18]
    st.caption("Saved AI interpretation · Provider facts · Calculated audited TTM · User assumptions")
    narrative = brief(result,credentials)
    st.caption(narrative["label"])
    for item in narrative["topics"]:
        with st.expander(item["topic"]):
            # Plain text preserves citation IDs and avoids model/provider-controlled executable links.
            st.text(item["saved_ai_excerpt"] or item["status"])
    if narrative["unresolved_evidence_ids"]:
        st.warning("Unresolved saved evidence references: " + ", ".join(narrative["unresolved_evidence_ids"]))
    symbols = list(dict.fromkeys(str(s).upper() for s in result.get("request",{}).get("symbols",[])))
    if not symbols:
        st.info("No saved company identity is available for scenarios.")
        return
    ticker = st.selectbox("Scenario company", symbols, key=key+"_ticker")
    inputs = saved_inputs(result,ticker,reference_time)
    st.caption("Hypothetical total equity value = saved TTM net income × (1 + user earnings change % / 100) × user P/E. Difference = (value / dated saved cap − 1) × 100.")
    scenarios = []
    if not inputs.eligible:
        st.warning("Scenarios unavailable: " + safe_text(" ".join(inputs.reasons),credentials))
    else:
        st.write(f"Calculated audited TTM net income: {inputs.net_income:,.0f} {inputs.currency} through {inputs.ttm_through}")
        st.write(f"Provider market capitalization: {inputs.market_cap:,.0f} {inputs.currency}; quote as-of {inputs.quote_as_of}")
        st.caption(f"Freshness reference: {inputs.reference_time}; maximum seven UTC calendar days. Sector: {inputs.framework}.")
        st.info("Demonstrative editable defaults below are user assumptions, not forecasts or recommendations. Bull/base/bear names do not enforce ordering.")
        for name, change_default, pe_default in (("Bear",-20.0,10.0),("Base",0.0,15.0),("Bull",20.0,20.0)):
            cols=st.columns(2)
            change=cols[0].number_input(name+" earnings change (%)", min_value=-100.0,max_value=200.0,value=change_default,key=key+"_"+ticker+name+"_change")
            pe=cols[1].number_input(name+" P/E (user assumption)",min_value=0.1,max_value=100.0,value=pe_default,key=key+"_"+ticker+name+"_pe")
            try:
                scenarios.append(dict(scenario=name,**calculate(inputs,change,pe)))
            except ValueError as error:
                st.warning(str(error))
        st.dataframe(pd.DataFrame(scenarios),hide_index=True,width="stretch")
        curve=[]
        for scenario in scenarios:
            for multiple in (5,10,15,20,25,30,40,50,75,100):
                try:
                    curve.append(dict(pe=multiple,scenario=scenario["scenario"],value=calculate(inputs,scenario["earnings_change_percent"],multiple)["hypothetical_total_equity_value"]))
                except ValueError:
                    pass
        if curve:
            st.line_chart(pd.DataFrame(curve).pivot(index="pe",columns="scenario",values="value"),x_label="User P/E sensitivity",y_label=f"Hypothetical total equity value ({inputs.currency})")
    for note in inputs.limitations:
        st.caption(note)
    with st.expander("Saved scenario provenance"):
        provenance_packet=export_packet(result,inputs,scenarios,credentials)
        st.json(dict(inputs=provenance_packet["inputs"],saved_evidence=provenance_packet["saved_evidence"]))
    packet=export_packet(result,inputs,scenarios,credentials)
    json_data,csv_data=exports(packet)
    cols=st.columns(2)
    cols[0].download_button("Download brief/scenarios JSON",json_data,"investment_brief.json","application/json",key=key+"_json",on_click="ignore")
    cols[1].download_button("Download brief/scenarios CSV",csv_data,"investment_brief.csv","text/csv",key=key+"_csv",on_click="ignore")
