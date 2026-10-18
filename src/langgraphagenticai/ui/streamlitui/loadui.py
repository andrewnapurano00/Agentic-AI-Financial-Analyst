from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from langgraphagenticai.ui.app_shell import inject_app_shell_css
from langgraphagenticai.ui.uiconfigfile import Config


def _load_project_env() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            return env_path
    return None


_load_project_env()


def _resolve_secret(sidebar_value: str, streamlit_key: str, env_key: str) -> str:
    if sidebar_value and sidebar_value.strip():
        return sidebar_value.strip().strip('"').strip("'")
    try:
        if streamlit_key in st.secrets:
            return str(st.secrets[streamlit_key]).strip().strip('"').strip("'")
    except Exception:
        pass
    return os.getenv(env_key, "").strip().strip('"').strip("'")


class LoadStreamlitUI:
    def __init__(self):
        self.config = Config()

    def load_streamlit_ui(self):
        st.set_page_config(page_title="Axiom Research", page_icon="AR", layout="wide", initial_sidebar_state="auto")
        inject_app_shell_css()
        st.sidebar.markdown('<div class="ax-brand"><strong>Axiom</strong> <span>Research</span></div>', unsafe_allow_html=True)
        st.sidebar.markdown('<div class="ax-tagline">DISCOVER. ANALYZE. INVEST.</div>', unsafe_allow_html=True)
        from langgraphagenticai.ui.workspace_handoff import apply_pending_handoff
        from langgraphagenticai.state.discovery import apply_discovery
        apply_discovery(st.session_state)
        apply_pending_handoff(st.session_state)
        next_workspace = st.session_state.pop("next_workspace", None)
        if next_workspace:
            st.session_state["active_workspace"] = next_workspace
        if st.session_state.get("active_workspace") == "Deep Research V2":
            st.session_state["active_workspace"] = "Deep Research"
            st.session_state["deep_research_format"] = "Low cost format"
        st.sidebar.markdown('<div class="ax-sidebar-label">Workspaces</div>', unsafe_allow_html=True)
        active_page = st.sidebar.radio(
            "Workspace navigation",
            ["Introduction", "Top Movers", "Stock Screener", "Research", "Equity Report", "AI Valuation", "Deep Research", "Portfolio Lab"],
            label_visibility="collapsed",
            key="active_workspace",
            format_func=lambda label: "Market Brief" if label == "Introduction" else label,
        )

        st.sidebar.markdown("---")
        with st.sidebar.expander("Settings", expanded=False):
            st.caption("Model, use case, provider keys and debug controls")
            selected_model = st.selectbox("Select OpenAI Model", self.config.OPENAI_MODEL_OPTIONS, index=0)
            selected_usecase = st.selectbox("Select Use Case", self.config.USECASE_OPTIONS, index=0)
            st.caption("Keys load from .env, environment variables, or Streamlit secrets.")
            openai_input = st.text_input("OpenAI API Key", type="password")
            fmp_input = st.text_input("FMP API Key", type="password")
            marketaux_input = st.text_input("Marketaux API Key", type="password")
            serper_input = st.text_input("Serper API Key", type="password")
            groq_input = st.text_input("Groq API Key (V2 pilot)", type="password")
            debug_mode = st.checkbox("Show debug trace", value=False)

        openai_api_key = _resolve_secret(openai_input, "OPENAI_API_KEY", "OPENAI_API_KEY")
        fmp_api_key = _resolve_secret(fmp_input, "FMP_API_KEY", "FMP_API_KEY")
        serper_api_key = _resolve_secret(serper_input, "SERPER_API_KEY", "SERPER_API_KEY")
        marketaux_api_key = _resolve_secret(marketaux_input, "MARKETAUX_API_KEY", "MARKETAUX_API_KEY")
        groq_api_key = _resolve_secret(groq_input, "GROQ_API_KEY", "GROQ_API_KEY")

        st.sidebar.caption(f"OpenAI {'configured' if openai_api_key else 'not configured'} / FMP {'configured' if fmp_api_key else 'not configured'}")
        st.sidebar.caption(f"Serper {'configured' if serper_api_key else 'not configured'} / MarketAux {'configured' if marketaux_api_key else 'not configured'}")

        return {
            "active_page": active_page,
            "selected_model": selected_model,
            "selected_usecase": selected_usecase,
            "OPENAI_API_KEY": openai_api_key,
            "FMP_API_KEY": fmp_api_key,
            "SERPER_API_KEY": serper_api_key,
            "MARKETAUX_API_KEY": marketaux_api_key,
            "GROQ_API_KEY": groq_api_key,
            "debug_mode": debug_mode,
        }
