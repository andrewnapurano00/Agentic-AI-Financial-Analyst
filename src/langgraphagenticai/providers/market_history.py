"""Compatibility wrapper for the shared Introduction history provider."""
import streamlit as st
from .symbol_history import RANGES, load_symbol_history, clear_history_cache

@st.cache_data(ttl=300, show_spinner=False)
def load_market_chart(api_key: str = "", period: str = "1D") -> dict:
    return load_symbol_history("^GSPC", api_key, period)
