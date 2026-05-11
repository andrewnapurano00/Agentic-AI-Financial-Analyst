"""Legacy renderer retained for backward compatibility.

The main Streamlit flow now renders results directly in main.py.
This class is kept only so old imports do not break.
"""

from __future__ import annotations

import streamlit as st


class DisplayResultStreamlit:
    def __init__(self, usecase: str, graph, user_message: str):
        self.usecase = usecase
        self.graph = graph
        self.user_message = user_message

    def display_result_on_ui(self):
        st.info(
            "DisplayResultStreamlit is deprecated in this version. "
            "Use the main Streamlit flow in src/langgraphagenticai/main.py instead."
        )
