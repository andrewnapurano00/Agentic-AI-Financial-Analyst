"""Single-owner session sign-in for a private Hugging Face research Space.

No durable users, jobs or shared report store. Never log passwords or state.
"""
import hashlib
import hmac
import os
import threading
import time
from collections import deque

_LOCK = threading.Lock()
_ATTEMPTS = deque(maxlen=5)
_SESSION_SECONDS = 8 * 60 * 60


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def authenticate(candidate, expected, now=None):
    """Process-wide five-attempt/minute budget; compare fixed-length digests."""
    now = time.monotonic() if now is None else now
    with _LOCK:
        while _ATTEMPTS and now - _ATTEMPTS[0] >= 60:
            _ATTEMPTS.popleft()
        if len(_ATTEMPTS) >= 5:
            return False
        _ATTEMPTS.append(now)
    return hmac.compare_digest(_digest(candidate), _digest(expected))


def _clear_session(st):
    for key in list(st.session_state):
        del st.session_state[key]


def require_owner():
    import streamlit as st
    expected = os.environ.get("AXIOM_OWNER_PASSWORD", "")
    if not 24 <= len(expected) <= 1024:
        st.error("Configure AXIOM_OWNER_PASSWORD in Space secrets, then restart.")
        st.stop()
    fingerprint = _digest(expected)
    saved = st.session_state.get("_axiom_owner_auth")
    if saved and isinstance(saved, tuple) and len(saved) == 2:
        if hmac.compare_digest(str(saved[0]), fingerprint) and 0 <= time.monotonic() - saved[1] < _SESSION_SECONDS:
            if st.sidebar.button("Sign out", key="_axiom_owner_logout"):
                _clear_session(st)
                st.rerun()
            return
        _clear_session(st)

    def submit():
        candidate = st.session_state.pop("_axiom_owner_password", "")
        if len(candidate) <= 1024 and authenticate(candidate, expected):
            _clear_session(st)
            st.session_state["_axiom_owner_auth"] = (fingerprint, time.monotonic())
        else:
            st.session_state["_axiom_owner_failed"] = True

    st.title("Axiom Research")
    st.caption("Private single-owner research workspace. Sign in to continue.")
    if st.session_state.pop("_axiom_owner_failed", False):
        st.error("Sign-in failed or attempt limit reached. Wait one minute before retrying.")
    with st.form("_axiom_owner_login"):
        st.text_input("Owner password", type="password", key="_axiom_owner_password", max_chars=1024)
        st.form_submit_button("Sign in", on_click=submit)
    st.stop()
