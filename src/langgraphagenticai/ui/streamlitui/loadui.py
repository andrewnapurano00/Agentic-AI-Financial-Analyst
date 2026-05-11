from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.langgraphagenticai.ui.uiconfigfile import Config


def _load_project_env() -> None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            break


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
        st.set_page_config(page_title=self.config.PAGE_TITLE, layout="wide")
        st.title(self.config.PAGE_TITLE)
        st.caption(
            "Agentic research prototype powered by LangGraph, OpenAI, and Financial Modeling Prep MCP."
        )

        st.sidebar.header("Configuration")

        selected_model = st.sidebar.selectbox(
            "Select OpenAI Model",
            self.config.OPENAI_MODEL_OPTIONS,
            index=0,
        )

        selected_usecase = st.sidebar.selectbox(
            "Select Use Case",
            self.config.USECASE_OPTIONS,
            index=0,
        )

        openai_input = st.sidebar.text_input("OpenAI API Key", type="password")
        fmp_input = st.sidebar.text_input("FMP API Key", type="password")
        marketaux_input = st.sidebar.text_input(
            "Marketaux API Key (optional for enhanced news)",
            type="password",
        )
        debug_mode = st.sidebar.checkbox("Show debug trace", value=False)

        openai_api_key = _resolve_secret(openai_input, "OPENAI_API_KEY", "OPENAI_API_KEY")
        fmp_api_key = _resolve_secret(fmp_input, "FMP_API_KEY", "FMP_API_KEY")
        marketaux_api_key = _resolve_secret(
            marketaux_input,
            "MARKETAUX_API_KEY",
            "MARKETAUX_API_KEY",
        )

        st.sidebar.markdown("---")
        st.sidebar.caption(f"OpenAI key detected: {'Yes' if bool(openai_api_key) else 'No'}")
        st.sidebar.caption(f"FMP key detected: {'Yes' if bool(fmp_api_key) else 'No'}")
        st.sidebar.caption(f"MarketAux key detected: {'Yes' if bool(marketaux_api_key) else 'No'}")
        st.sidebar.markdown(
            "Use debug mode to inspect the graph conversation, tool messages, and final synthesis path."
        )

        return {
            "selected_model": selected_model,
            "selected_usecase": selected_usecase,
            "OPENAI_API_KEY": openai_api_key,
            "FMP_API_KEY": fmp_api_key,
            "MARKETAUX_API_KEY": marketaux_api_key,
            "debug_mode": debug_mode,
        }