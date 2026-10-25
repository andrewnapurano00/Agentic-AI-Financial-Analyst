"""Data Validation workspace: explicit provider action, local saved inspection."""
from hashlib import sha256
import json
import pandas as pd
import streamlit as st
from langgraphagenticai.providers.data_validation_catalog import endpoints,endpoint
from langgraphagenticai.providers.data_validation_usage import REPORTS, usages, endpoint_ids, calculation_index
from langgraphagenticai.providers.data_validation import defaults_for,fetch_endpoint,prepare,response_rows


def _scope(credentials):
    return sha256(json.dumps(credentials,sort_keys=True).encode()).hexdigest()


def render_data_validation(fmp_api_key="",marketaux_api_key="",serper_api_key=""):
    credentials={"FMP_API_KEY":fmp_api_key,"MARKETAUX_API_KEY":marketaux_api_key,"SERPER_API_KEY":serper_api_key}
    scope=_scope(credentials)
    st.caption("Choose one data operation and fetch it explicitly. Inspect provider fields, dates, currency and ticker identity; no AI analysis runs here.")
    catalog=endpoints()
    report=st.selectbox("Report / workspace", ["All reports", *REPORTS], key="validation_report")
    families=["All metric families", *dict.fromkeys(row["family"] for row in usages(report))]
    if st.session_state.get("validation_metric_family") not in families:
        st.session_state["validation_metric_family"]=families[0]
    family=st.selectbox("Metric / calculation family", families, key="validation_metric_family")
    mapped=usages(report, family)
    st.caption("Report lens maps metric families to display locations, provider fields, basis and local calculation code. It is maintained source documentation, not a live per-cell audit or a guarantee of financial correctness.")
    with st.expander("Report data & calculation map", expanded=report!="All reports"):
        st.dataframe(pd.DataFrame([{"Report":r["report"], "Metric family":r["family"],
            "Used in":r["places"], "Type":r["kind"], "Provider fields / inputs":r["fields"],
            "Calculation / validation rule":r["calculation"], "Period / limitations":r["basis"],
            "Endpoints":"; ".join(r["endpoints"]), "Code locations":"; ".join(r["sources"])} for r in mapped]),
            hide_index=True, width="stretch")
        st.download_button("Download report data map JSON", json.dumps(mapped,ensure_ascii=False,indent=2).encode(),
                           file_name="report_data_calculation_map.json",mime="application/json",key="validation_map_download",on_click="ignore")
    with st.expander("Calculation code index", expanded=False):
        st.caption("Actual function definitions in the mapped consumer modules, including helpers. This index does not claim every function runs for the selected endpoint. Later same-name definitions take precedence over retained legacy definitions.")
        code_filter=st.text_input("Find calculation or function",key="validation_calculation_search")
        definitions=calculation_index(report, family)
        if code_filter:
            definitions=[r for r in definitions if code_filter.casefold() in " ".join(str(v) for v in r.values()).casefold()]
        st.dataframe(pd.DataFrame(definitions),hide_index=True,width="stretch")
    allowed_ids=endpoint_ids(report, family)
    filtered=[e for e in catalog if e["id"] in allowed_ids]
    providers=list(dict.fromkeys(e["provider"] for e in filtered))
    if st.session_state.get("validation_provider") not in providers:
        st.session_state["validation_provider"]=providers[0]
    provider=st.selectbox("Data provider",providers,key="validation_provider")
    choices=[e for e in filtered if e["provider"]==provider]
    ids=[e["id"] for e in choices]
    if st.session_state.get("validation_endpoint") not in ids:
        st.session_state["validation_endpoint"]=ids[0]
    selected=st.selectbox("Endpoint",ids,format_func=lambda identifier:endpoint(identifier)["label"],key="validation_endpoint")
    item=endpoint(selected)
    with st.expander("Where this endpoint is used", expanded=report!="All reports"):
        references=usages(report, family, selected)
        if report=="All reports":
            app_references=[r for r in references if r["report"]!="Data Validation"]
            references=app_references or references
        for row in references:
            st.markdown("**"+row["report"]+" / "+row["family"]+"**")
            st.write("Used in: "+row["places"])
            st.write("Inputs: "+row["fields"])
            st.write("Calculation: "+row["calculation"])
            st.caption(row["kind"]+" | "+row["basis"])
            st.code("\n".join(row["sources"]),language=None)
        if not references:
            st.info("This retained endpoint has no report-specific usage mapping yet. Catalog registration does not establish active invocation.")
    st.code(item["route"],language=None)
    st.caption("Scope: "+item["scope"]+". "+("Uses retained read-only research wrappers; availability depends on your FMP plan." if provider=="FMP MCP" else "Legacy routes are compatibility paths; your provider plan may restrict access." if "/api/v" in item["route"] else "Uses the existing provider configuration."))
    if item["scope"]=="global":
        st.info("This endpoint returns market-wide data. The ticker is not sent as a filter.")
    if st.session_state.get("validation_params_endpoint")!=selected:
        st.session_state["validation_parameters"]=json.dumps(defaults_for(item),indent=2)
        st.session_state["validation_params_endpoint"]=selected
    key_name={"FMP REST":"FMP_API_KEY","FMP MCP":"FMP_API_KEY","Marketaux":"MARKETAUX_API_KEY","Serper":"SERPER_API_KEY"}.get(provider)
    ready=not key_name or bool(credentials.get(key_name,""))
    if not ready:st.info("Configure "+key_name+" in Settings to fetch this endpoint.")
    with st.form("data_validation_request"):
        ticker=st.text_input("Ticker",value="AAPL",key="validation_ticker",disabled=item["scope"]=="global",max_chars=20)
        query=st.text_input("Search query (optional)",key="validation_query",max_chars=500) if item["scope"]=="search" else ""
        with st.expander("Request parameters",expanded=bool(defaults_for(item))):
            st.caption("Allowed parameters: "+(", ".join(item["allowed"]) or "None")+". Ticker and credentials are supplied separately. Change period to quarter for quarterly statements.")
            params_text=st.text_area("Parameters (JSON)",key="validation_parameters",height=150)
        fetch=st.form_submit_button("Fetch data",type="primary",disabled=not ready)
    if fetch:
        try:
            if len(params_text)>5000:raise ValueError("Request parameters are too long.")
            params=json.loads(params_text)
            prepare(selected,ticker,params,query)
            with st.spinner("Fetching the selected provider response..."):
                response=fetch_endpoint(selected,ticker,params,query,credentials)
            st.session_state["validation_last_attempt"]={"scope":scope,"response":response}
            if response["status"]!="error":
                st.session_state["validation_saved_response"]={"scope":scope,"response":response}
        except (ValueError,TypeError):
            st.warning("Request not sent. Check the ticker and the listed JSON parameters, types, dates and bounds.")
    attempt=st.session_state.get("validation_last_attempt")
    if attempt and attempt["scope"]==scope and attempt["response"]["status"]=="error":
        failure=attempt["response"]
        st.error(failure.get("message","The selected endpoint could not return data."))
        st.caption("Failed request: "+failure["label"]+"; retrieved "+failure["retrieved_at"]+". Any previous successful response remains below.")
        with st.expander("Failed request details"):
            st.json(failure)
    saved=st.session_state.get("validation_saved_response")
    if not saved:
        st.info("Fetch an endpoint to save a response here. Changing filters, navigating and downloading do not fetch again.")
    elif saved["scope"]!=scope:
        st.info("Saved data belongs to different provider settings. Fetch again using the current credentials to inspect or download a response.")
    else:
        response=saved["response"]
        st.subheader("Saved provider response")
        current_signature=None
        try:
            current_signature=prepare(selected,ticker,json.loads(params_text),query)
        except (ValueError,TypeError):pass
        if not current_signature or response["endpoint_id"]!=selected or response["ticker"]!=(current_signature[1] or None) or response["parameters"]!=current_signature[3]:
            st.warning("Inputs differ from this saved response. Fetch data to update it; the displayed response retains its original request.")
        st.caption(response["provider"]+" | "+response["label"]+" | ticker "+str(response["ticker"] or "market-wide")+" | retrieved "+response["retrieved_at"]+" | "+str(response.get("record_count",0))+" preview records | "+str(response["elapsed_seconds"])+" seconds")
        st.caption(response["basis"])
        if response["status"]=="empty":st.info("The provider returned no data rows for this request. This does not prove endpoint access for other tickers or dates.")
        if response.get("identity_warning"):st.warning(response["identity_warning"])
        if response.get("truncated"):st.warning("Response preview was limited for size. Narrow the parameters to inspect more detail; the download contains this same sanitized preview.")
        table,raw,request=st.tabs(["Data table","JSON response","Request details"])
        with table:
            rows=response_rows(response["data"])
            if rows:
                frame=pd.json_normalize(rows[:500])
                # Nested objects are displayed as JSON text, not executable HTML.
                for column in frame.columns:
                    frame[column]=frame[column].map(lambda v:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v)
                field=st.text_input("Filter field names",key="validation_field_filter")
                if field:frame=frame[[c for c in frame if field.lower() in c.lower()]]
                st.dataframe(frame,hide_index=True,width="stretch")
                st.caption("Table shows at most 500 preview rows. Use JSON response for the retained structure; zero and missing values remain distinct.")
            else:st.info("No tabular rows. Inspect the JSON response for the provider's original structure.")
        with raw:st.json(response["data"])
        with request:st.json({k:v for k,v in response.items() if k!="data"})
        st.download_button("Download response JSON",json.dumps(response,ensure_ascii=False,allow_nan=False).encode(),file_name="data_validation_response.json",mime="application/json",key="validation_download",on_click="ignore")
    with st.expander("Endpoint catalog & usage"):
        st.caption(str(len(catalog))+" registered data operations. REST routes and retained research-tool wrappers are listed separately; presence is not a claim of current plan entitlement. Yahoo and Serper show adapter output. No model endpoints or arbitrary URLs are supported.")
        st.dataframe(pd.DataFrame([{k:e[k] for k in ("provider","label","route","scope","source")} for e in catalog]),hide_index=True,width="stretch")
