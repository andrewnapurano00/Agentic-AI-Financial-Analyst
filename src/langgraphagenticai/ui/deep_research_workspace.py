"""One visible workspace; independent engines and saved histories."""
import streamlit as st
from .research_intent import PRESETS, intent_defaults


def render_deep_research_workspace(*, openai_api_key, model_name, fmp_api_key,
                                   serper_api_key="", marketaux_api_key="", groq_api_key=""):
    from .deep_research_tab import render_deep_research_tab
    from .deep_research_v2_tab import render_deep_research_v2_tab
    st.session_state.setdefault("deep_research_unified_preference", st.session_state.get("deep_research_intent_preview", True))
    st.session_state["deep_research_intent_preview"] = st.session_state["deep_research_unified_preference"]
    def remember_controls():
        st.session_state["deep_research_unified_preference"] = st.session_state["deep_research_intent_preview"]
    preview = st.checkbox("Use unified research controls", key="deep_research_intent_preview",
                          on_change=remember_controls,
                          help="Turn off to restore classic format controls. Both engines and saved histories remain available.")
    intent = None
    if preview:
        # Durable preferences survive widget cleanup during navigation/rollback.
        preset = st.session_state.get("deep_research_intent", "Quick Brief" if
            st.session_state.get("deep_research_format") == "Low cost format" else "Deep Dive")
        st.session_state["deep_research_intent_control"] = preset
        def remember_intent():
            st.session_state["deep_research_intent"] = st.session_state["deep_research_intent_control"]
            st.session_state.pop("deep_research_engine_override", None)
        preset = st.radio("Research goal", PRESETS, horizontal=True,
                          key="deep_research_intent_control", on_change=remember_intent)
        st.session_state["deep_research_intent"] = preset
        saved_runs = {}
        for engine, history in (("Standard format", "dr_history"), ("Low cost format", "drv2_history")):
            for run in st.session_state.get(history, []):
                if run.get("id") and run.get("request"):
                    saved_runs[engine + ":" + run["id"]] = (engine, run)
        if saved_runs:
            options = [""] + list(saved_runs)
            if st.session_state.get("deep_research_saved_control", "") not in options:
                st.session_state["deep_research_saved_control"] = ""
            def open_saved():
                choice = st.session_state["deep_research_saved_control"]
                if choice:
                    engine, run = saved_runs[choice]
                    st.session_state["deep_research_engine_override"] = engine
                    st.session_state["dr_active_run" if engine == "Standard format" else "drv2_active_run"] = run["id"]
            def saved_label(choice):
                if not choice:
                    return "Choose a saved report"
                engine, run = saved_runs[choice]
                return (", ".join(run["request"].get("symbols", [])) + " · "
                        + str(run.get("created_at") or "Date unavailable") + " · "
                        + str(run.get("status", "unknown")) + " · " + engine)
            st.selectbox("Saved research across all goals", options, format_func=saved_label,
                         key="deep_research_saved_control", on_change=open_saved)
        default = intent_defaults(preset)
        with st.expander("Advanced settings · engine and routing"):
            st.session_state["deep_research_engine_control"] = st.session_state.get(
                "deep_research_engine_override", default["engine"])
            def remember_engine():
                st.session_state["deep_research_engine_override"] = st.session_state["deep_research_engine_control"]
            selected = st.radio("Research engine", ("Standard format", "Low cost format"),
                                key="deep_research_engine_control", on_change=remember_engine)
            st.caption("Standard retains the sidebar model and its existing stage limits; no hard dollar cap. "
                       "Low cost retains Economy/Balanced routing and an editable estimated-model budget, initially $0.35. "
                       "Unknown pricing cannot guarantee a dollar ceiling. Expert controls remain in the run form.")
        intent = intent_defaults(preset, selected)
        st.caption(f"{preset} · {selected} · {intent['depth']} investigation. "
                   "Selecting a goal does not start research. Saved histories remain separate by engine.")
        if selected == "Low cost format":
            st.warning("Low cost research remains an experimental pilot; Quick Brief does not promise measured speed or savings.")
        if intent["committee"]:
            st.info("This goal preselects an optional investment committee with additional model calls after a completed report. "
                    "Review or disable that option before submitting the run form.")
        st.session_state["deep_research_format"] = selected
        common = dict(openai_api_key=openai_api_key, fmp_api_key=fmp_api_key,
                      serper_api_key=serper_api_key, marketaux_api_key=marketaux_api_key,
                      intent=intent)
        if selected == "Low cost format":
            render_deep_research_v2_tab(**common, groq_api_key=groq_api_key)
        else:
            render_deep_research_tab(**common, model_name=model_name)
        return
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
