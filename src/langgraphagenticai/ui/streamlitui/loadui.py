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
        st.sidebar.markdown('<div class="ax-sidebar-label">Workspace</div>', unsafe_allow_html=True)
        next_workspace = st.session_state.pop("next_workspace", None)
        if next_workspace:
            st.session_state["active_workspace"] = next_workspace
        active_page = st.sidebar.radio(
            "Workspace navigation",
            ["Introduction", "Top Movers", "Research", "Equity Report", "Stock Screener", "Portfolio Lab", "Deep Research"],
            label_visibility="collapsed",
            key="active_workspace",
        )

        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="ax-sidebar-label">Configuration</div>', unsafe_allow_html=True)
        selected_model = st.sidebar.selectbox("Select OpenAI Model", self.config.OPENAI_MODEL_OPTIONS, index=0)
        selected_usecase = st.sidebar.selectbox("Select Use Case", self.config.USECASE_OPTIONS, index=0)

        with st.sidebar.expander("Model & data settings", expanded=False):
            st.caption("Keys load from .env, environment variables, or Streamlit secrets.")
            openai_input = st.text_input("OpenAI API Key", type="password")
            fmp_input = st.text_input("FMP API Key", type="password")
            marketaux_input = st.text_input("Marketaux API Key", type="password")
            serper_input = st.text_input("Serper API Key", type="password")
        debug_mode = st.sidebar.checkbox("Show debug trace", value=False)

        openai_api_key = _resolve_secret(openai_input, "OPENAI_API_KEY", "OPENAI_API_KEY")
        fmp_api_key = _resolve_secret(fmp_input, "FMP_API_KEY", "FMP_API_KEY")
        serper_api_key = _resolve_secret(serper_input, "SERPER_API_KEY", "SERPER_API_KEY")
        marketaux_api_key = _resolve_secret(marketaux_input, "MARKETAUX_API_KEY", "MARKETAUX_API_KEY")

        st.sidebar.caption(f"OpenAI {'ready' if openai_api_key else 'not configured'} / FMP {'ready' if fmp_api_key else 'not configured'}")
        st.sidebar.caption(f"Serper {'ready' if serper_api_key else 'not configured'} / MarketAux {'ready' if marketaux_api_key else 'not configured'}")

        return {
            "active_page": active_page,
            "selected_model": selected_model,
            "selected_usecase": selected_usecase,
            "OPENAI_API_KEY": openai_api_key,
            "FMP_API_KEY": fmp_api_key,
            "SERPER_API_KEY": serper_api_key,
            "MARKETAUX_API_KEY": marketaux_api_key,
            "debug_mode": debug_mode,
        }
