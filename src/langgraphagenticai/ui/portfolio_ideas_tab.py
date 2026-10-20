"""Prompt + universe + Generate: four simple research baskets, no trading setup."""
import pandas as pd
import streamlit as st
from datetime import datetime,timezone
from langgraphagenticai.portfolio_ideas.contracts import PERSONAS,DEFAULT_UNIVERSE,DEFAULT_PROMPT,universe,clean,export,fingerprint
from langgraphagenticai.portfolio_ideas.workflow import recommend
from langgraphagenticai.portfolio_ideas.ranking import build_ranked
from langgraphagenticai.portfolio_ideas.reuse import company_inputs
from langgraphagenticai.providers.portfolio_ideas import load_ideas_evidence
from langgraphagenticai.utils.export_csv import safe_csv_bytes


def render_portfolio_ideas(fmp_api_key="",openai_api_key="",model_name="gpt-5"):
    st.subheader("AI Portfolio Ideas")
    st.caption("One prompt · Four investor perspectives · Three or four companies per basket")
    st.write("Compare companies using the data already available in the app. Four simple screens produce equal-weight shortlists; optional AI refines them around your research prompt.")
    prompt=st.text_area("What should the portfolios focus on?",st.session_state.get("ideas_saved_prompt",DEFAULT_PROMPT),height=110,max_chars=1500,key="ideas_prompt")
    names_text=st.text_input("Companies to compare (4–12 tickers)",st.session_state.get("ideas_saved_universe",DEFAULT_UNIVERSE),key="ideas_universe")
    st.session_state["ideas_saved_prompt"]=prompt
    st.session_state["ideas_saved_universe"]=names_text
    with st.expander("Perspectives & data options"):
        report_names=st.session_state.get("equity_report_tickers",[])
        if isinstance(report_names,list) and 4<=len(report_names)<=12:
            def use_report_companies():
                try:
                    text=", ".join(universe(",".join(report_names)))
                    st.session_state["ideas_universe"]=text
                    st.session_state["ideas_saved_universe"]=text
                except ValueError:
                    pass
            st.button("Use Equity Report companies",on_click=use_report_companies,key="ideas_use_report")
        for persona,(style,_) in PERSONAS.items():st.write(persona+" — "+style)
        add_ai=st.checkbox("Add AI perspective (one short request)",value=st.session_state.get("ideas_saved_add_ai",True),key="ideas_add_ai")
        st.session_state["ideas_saved_add_ai"]=add_ai
        st.caption("Data-ranked baskets work without AI. One optional request can refine the picks and explain tradeoffs. These are fictional styles, not independent agents or actual investors. "
                   "Recent compatible quote/profile/ratio inputs from Equity Report and AI Valuation are reused; missing or expired inputs are loaded once.")
        refresh=st.checkbox("Force fresh company data when generating",key="ideas_force_refresh")
        st.caption("Fundamentals: provider TTM ratios. Technicals: quote moving averages. News: up to two recent headlines per company from one shared, incomplete news batch. Missing coverage stays visible.")
    generate=st.button("Build portfolios",type="primary",key="ideas_generate",disabled=not fmp_api_key)
    if not fmp_api_key:st.info("Configure FMP to load missing company data. OpenAI is optional.")
    selected_model=model_name if add_ai and openai_api_key else ""
    if generate:
        phase="inputs"
        try:
            names=universe(names_text)
            request=clean(prompt,(fmp_api_key,openai_api_key),1500)
            if len(request.strip())<10:raise ValueError("Describe your research goal in at least 10 characters.")
            shared={} if refresh else company_inputs(st.session_state,names,fmp_api_key)
            args=(tuple(names),fmp_api_key,shared)
            with st.spinner("Comparing company evidence and preparing four portfolios"):
                phase="evidence"
                saved=st.session_state.get("portfolio_ideas_evidence_v1")
                from langgraphagenticai.providers.company_evidence import credential_scope
                reusable=bool(not refresh and saved and saved.get("credential_scope")==credential_scope(fmp_api_key) and set(saved.get("rows",{}))==set(names))
                if reusable:
                    stamp=datetime.fromisoformat(saved["retrieved_at"])
                    reusable=stamp.tzinfo is not None and 0<=(datetime.now(timezone.utc)-stamp).total_seconds()<=300
                if refresh:load_ideas_evidence.clear(*args)
                evidence=saved if reusable else load_ideas_evidence(*args)
                st.session_state["portfolio_ideas_evidence_v1"]=evidence
                if len(evidence["rows"])<4:
                    st.warning(f"Only {len(evidence['rows'])} of {len(names)} companies have usable dated USD quotes. At least four are needed. No AI request was made. See Company comparison & sources for the provider/coverage reasons.")
                elif (old:=st.session_state.get("portfolio_ideas_result_v1")) and old.get("schema_version")==2 and old["fingerprint"]==fingerprint(request,names,evidence,selected_model):
                    st.info("Showing the saved result for this prompt and evidence; no new AI request.")
                else:
                    phase="model"
                    base=build_ranked(request,names,evidence,selected_model)
                    st.session_state["portfolio_ideas_result_v1"]=base
                    try:
                        st.session_state["portfolio_ideas_result_v1"]=recommend(request,names,evidence,openai_api_key if add_ai else "",selected_model)
                    except Exception:
                        base["ai_status"]="failed"
        except ValueError:
            # Local validation only; never display arbitrary model/provider error text.
            if phase=="inputs":st.warning("Enter 4–12 valid company tickers and a research prompt of at least 10 characters. Prior ideas are preserved.")
            elif phase=="model":st.warning("The local screen could not use this evidence. Company inputs and prior saved ideas remain available.")
            else:st.warning("Company evidence could not be validated. Check the source coverage details; prior ideas remain saved.")
        except Exception:
            st.warning("Company data or AI generation failed. Prior ideas and successfully collected evidence remain saved; retry when access is restored.")
    result=st.session_state.get("portfolio_ideas_result_v1")
    if result:
        try:matches=clean(prompt,(fmp_api_key,openai_api_key),1500)==result["prompt"] and universe(names_text)==result["universe"] and selected_model==result["model"]
        except ValueError:matches=False
        if not matches:st.info("Saved portfolios use the earlier prompt, universe or model shown below. Generate explicitly to replace them.")
        st.caption("Saved: "+result["generated_at"]+" | Evidence retrieved: "+result["evidence"]["retrieved_at"]+" | Provider: FMP | Model: "+(result["model"] or "Local screen"))
        if (datetime.now(timezone.utc)-datetime.fromisoformat(result["evidence"]["retrieved_at"])).total_seconds()>900:
            st.info("Saved evidence is over 15 minutes old. Generate explicitly to collect current evidence; the saved ideas remain readable.")
        st.text("Research request: "+result["prompt"])
        if result.get("ai_status") not in {None,"complete","not_requested"}:
            st.info("AI refinement did not finish for every perspective. The data-ranked baskets below remain usable; their free-text request is not treated as an enforced constraint.")
        for warning in result["warnings"]:st.warning(warning)
        tabs=st.tabs([name+" · "+style for name,(style,_) in PERSONAS.items()])
        all_rows=[]
        for (persona,(style,_)),tab in zip(PERSONAS.items(),tabs):
            with tab:
                view=result["perspectives"].get(persona)
                if not view:
                    st.info("This perspective did not pass validation. The other saved portfolios remain available.");continue
                st.text(view["summary"])
                if view.get("selection_basis"):st.caption(view["selection_basis"])
                if not view["picks"]:st.info("No basket recommended from the available evidence.")
                for pick in view["picks"]:
                    row=result["evidence"]["rows"][pick["symbol"]]
                    st.markdown("**"+pick["symbol"]+" · "+f"{pick['weight_pct']:.1f}%"+"**")
                    st.caption(row["company"]+" | "+row["sector"]+" | Quote as of "+row["as_of"])
                    st.text(pick["thesis"])
                    st.text("Main risk: "+pick["risk"])
                    st.text("Watch for: "+pick["monitor"])
                    if row["gaps"]:st.caption("Missing coverage: "+", ".join(row["gaps"]))
                    all_rows.append(dict(Persona=persona,Ticker=pick["symbol"],Weight_pct=pick["weight_pct"],Thesis=pick["thesis"],Risk=pick["risk"],Monitor=pick["monitor"]))
        if all_rows:
            with st.expander("Compare all four baskets"):
                st.dataframe(pd.DataFrame(all_rows).round(2),hide_index=True,width="stretch")
            st.download_button("Download portfolio ideas CSV",safe_csv_bytes(pd.DataFrame(all_rows)),"portfolio-ideas.csv","text/csv")
        try:
            st.download_button("Download portfolio ideas JSON",export(result,(fmp_api_key,openai_api_key)),"portfolio-ideas.json","application/json")
        except ValueError:
            st.warning("The saved result exceeds the JSON export size budget. The portfolios remain available above.")
        with st.expander("Usage & assumptions"):
            st.write("Model attempts: "+str(result.get("model_calls",0))+". AI status: "+str(result.get("ai_status","legacy"))+". Prompt tokens: "+str(result["prompt_tokens"])+"; completion tokens: "+str(result["completion_tokens"])+". Dollar cost is not calculated.")
            st.caption("The selected Settings model is preserved. One request is not a dollar ceiling. Same-input Generate reuses a saved result while cached evidence is unchanged. "
                       "Equal-weight baskets sum to 100% each; they are separate alternatives, not a combined allocation. No trades, backtest, optimizer, debate, review pass or return forecast. "
                       "Ticker/count checks are mechanical; every numerical or qualitative claim in AI prose is not independently verified.")
            st.caption("Local screens: Warren emphasizes sector-relative profitability/value; George value and pullback positioning; Ray quality and sector breadth; Cathie trend, profitability and a sector proxy. "
                       "Missing features are omitted, ties alphabetical; singleton sectors receive neutral relative ranks. Financials use P/B when supplied and exclude debt/equity from resilience. "
                       "A sector proxy is not evidence of innovation or future growth. News is supplied to AI, not converted into a local sentiment score. Prompt constraints are applied only by successful AI refinement and are not formally certified.")
            if result.get("ranking"):st.json(result["ranking"],expanded=False)
    evidence=st.session_state.get("portfolio_ideas_evidence_v1") or (result or {}).get("evidence")
    if evidence:
        with st.expander("Company comparison & sources"):
            st.caption("Latest collected evidence: "+evidence["retrieved_at"]+" | "+evidence["news_basis"])
            for warning in evidence["warnings"]:st.caption(warning)
            rows=[]
            for symbol,row in evidence["rows"].items():
                rows.append(dict(Ticker=symbol,Sector=row["sector"],Price_USD=row["price"],Quote_as_of=row["as_of"],
                                 **row["fundamentals"],**row["technicals"],Headlines=len(row["news"]),Missing=", ".join(row["gaps"])))
            st.dataframe(pd.DataFrame(rows).round(3),hide_index=True,width="stretch")
            for symbol,row in evidence["rows"].items():
                st.write(symbol+" — "+row["currency_basis"])
                st.json(dict(sources=row["sources"],evidence_refs=row["evidence_refs"]),expanded=False)
                for article in row["news"]:
                    st.link_button(article["title"],article["url"])
                    st.caption(article["published"]+" | "+article["time_basis"])
            st.caption("Margins and yields are fractions (0.20 = 20%); valuation ratios are multiples. Technical distances are percentages. "
                       "Provider TTM period ends and quote adjustment policies can be unavailable. News omissions are not a neutral signal; no article scraping or extra model summaries.")
    st.caption("Research ideas, not personalized investment advice. Results stay in this session; download before restarting.")
