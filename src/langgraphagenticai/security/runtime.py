"""Fail closed for unsupported hosted identity/job configurations."""
import os


def runtime_block_reason(environ=None):
    mode = (os.environ if environ is None else environ).get("AXIOM_RUNTIME_MODE") or "local"
    if mode == "local":
        return None
    if mode == "hosted":
        return ("Hosted access is disabled. A deployment-specific authenticated identity adapter, "
                "per-user data/job isolation and release gates must be verified before activation. "
                "Research controls and saved results are not accessible.")
    return "Unsupported AXIOM_RUNTIME_MODE. Application access is disabled."


def enforce_runtime_access():
    reason = runtime_block_reason()
    if reason:
        import streamlit as st
        st.error(reason)
        st.stop()
