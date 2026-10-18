"""One visible workspace; independent engines and saved histories."""
import streamlit as st


def render_deep_research_workspace(*, openai_api_key, model_name, fmp_api_key,
                                   serper_api_key="", marketaux_api_key="", groq_api_key=""):
    from .deep_research_tab import render_deep_research_tab
    from .deep_research_v2_tab import render_deep_research_v2_tab
    # A separate preference survives Streamlit cleanup of an unmounted widget.
    preference = st.session_state.get("deep_research_format", "Standard format")
    st.session_state["deep_research_format_control"] = preference
    def remember_format():
        st.session_state["deep_research_format"] = st.session_state["deep_research_format_control"]
    selected = st.radio("Research format", ("Standard format", "Low cost format"),
                        horizontal=True,
                        key="deep_research_format_control", on_change=remember_format)
    st.session_state["deep_research_format"] = selected
    common = dict(openai_api_key=openai_api_key, fmp_api_key=fmp_api_key,
                  serper_api_key=serper_api_key, marketaux_api_key=marketaux_api_key)
    if selected == "Low cost format":
        render_deep_research_v2_tab(**common, groq_api_key=groq_api_key)
    else:
        render_deep_research_tab(**common, model_name=model_name)
