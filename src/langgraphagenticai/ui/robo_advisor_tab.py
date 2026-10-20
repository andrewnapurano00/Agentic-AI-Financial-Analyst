"""Axiom's research-only advisor and existing simulated trader workflows."""
import streamlit as st


def render_robo_advisor(fmp_api_key="", openai_api_key="", model_name="gpt-5"):
    workflow = st.radio("Advisor workflow", ["Portfolio architect", "Agent traders"],
                        horizontal=True, key="robo_advisor_workflow")
    if workflow == "Portfolio architect":
        from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect
        render_portfolio_architect(fmp_api_key=fmp_api_key, openai_api_key=openai_api_key, model_name=model_name)
    else:
        from langgraphagenticai.ui.paper_trading_tab import render_paper_trading_tab
        render_paper_trading_tab(fmp_api_key=fmp_api_key, openai_api_key=openai_api_key, model_name=model_name)
