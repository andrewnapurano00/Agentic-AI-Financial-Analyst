"""Focused launcher for the standalone trading/architect experience."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/"src"))
import streamlit as st
from langgraphagenticai.ui.app_shell import inject_app_shell_css
from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect


def main():
    st.set_page_config(page_title="AI Portfolio Architect",layout="wide")
    inject_app_shell_css()
    with st.sidebar:
        st.caption("Keys are used only for explicit research actions.")
        fmp = st.text_input("FMP API key",value=os.getenv("FMP_API_KEY",""),type="password")
        key = st.text_input("OpenAI API key",value=os.getenv("OPENAI_API_KEY",""),type="password")
        model = st.text_input("OpenAI model",value=os.getenv("OPENAI_MODEL","gpt-5"))
    render_portfolio_architect(fmp,key,model)


if __name__ == "__main__":
    main()
