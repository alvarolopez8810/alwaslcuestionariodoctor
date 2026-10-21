"""
Shared-password gate, same model as the Doctor Input app.

AUDIT_APP_PASSWORD must be set. The only exception is local review: with
AUDIT_ALLOW_NO_AUTH=1 and no RENDER env var, the gate is skipped and a
banner says so. On Render the app refuses to start without a password, so
the questionnaire can never be served publicly without access control.
"""

import hmac
import os

import streamlit as st


def _password() -> str | None:
    return os.environ.get("AUDIT_APP_PASSWORD") or None


def auth_mode() -> str:
    """'password', 'local-open' or 'blocked'."""
    if _password():
        return "password"
    if os.environ.get("AUDIT_ALLOW_NO_AUTH") == "1" and not os.environ.get("RENDER"):
        return "local-open"
    return "blocked"


def require_login() -> None:
    mode = auth_mode()
    if mode == "local-open":
        st.warning("Local review mode: authentication is OFF (AUDIT_ALLOW_NO_AUTH=1). "
                   "Never use this mode on a hosted instance.")
        return
    if mode == "blocked":
        st.error("AUDIT_APP_PASSWORD is not set. The questionnaire is locked until an "
                 "access password is configured.")
        st.stop()
    if st.session_state.get("authenticated"):
        return

    st.markdown("### Al Wasl FC · Medical & Performance Process Audit")
    with st.form("login"):
        pw = st.text_input("Access password", type="password")
        if st.form_submit_button("Sign in"):
            if hmac.compare_digest(pw.encode(), _password().encode()):
                st.session_state["authenticated"] = True
                st.rerun()
            st.error("Incorrect password.")
    st.stop()


def logout_button() -> None:
    if auth_mode() == "password" and st.sidebar.button("Sign out"):
        st.session_state.clear()
        st.rerun()
