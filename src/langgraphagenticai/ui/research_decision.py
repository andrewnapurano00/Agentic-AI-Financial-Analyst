"""One executive paragraph, with complete saved committee detail on demand."""
import re
import streamlit as st
from langgraphagenticai.deep_research.executive import decision_sections


def render_executive_decision(decision):
    sections = decision_sections(decision)
    text = " ".join("**" + label + ":** " + value for label, value in sections)
    st.markdown(re.sub(r"(?<!\\)\$", r"\\$", text))
    with st.expander("Full decision & limitations"):
        st.json(decision, expanded=False)
    st.caption(decision.get("disclaimer", "AI-generated research opinion, not personalized investment advice."))
