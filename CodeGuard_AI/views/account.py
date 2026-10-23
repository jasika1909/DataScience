"""My account: password, security log, data deletion, sign out."""
from __future__ import annotations

import streamlit as st

import config
from src import accounts as acc
from src import database as db
from src import report_generator as rg
from views.common import current_user, html, safe_db


def _sign_out() -> None:
    st.session_state.clear()
    st.session_state["login_notice"] = "You have been signed out."


def render() -> None:
    user = current_user()
    html('<div class="cg-page-title">My account</div>'
         f'<div class="cg-lead">Signed in as <b>{user.display_name}</b> ({user.username}), '
         f'role: {user.role}{" (administrator)" if user.is_admin else ""}.</div>')
    if config.AUTH_ENABLED:
        st.button("Sign out", key="sign_out", on_click=_sign_out)
    else:
        st.caption("Single-user mode (CODEGUARD_AUTH=off): no sign-in is required.")

    tab_pw, tab_log, tab_data = st.tabs(["Password", "Security log", "My data"])

    with tab_pw:
        if not config.AUTH_ENABLED:
            st.info("Passwords are not used in single-user mode.")
        else:
            with st.form("pw_form", clear_on_submit=True):
                old = st.text_input("Current password", type="password")
                new = st.text_input("New password", type="password")
                new2 = st.text_input("Repeat new password", type="password")
                go = st.form_submit_button("Change password", type="primary")
            if go:
                if new != new2:
                    st.error("The new passwords do not match.")
                else:
                    try:
                        acc.change_password(user, old, new)
                        st.success("Password changed.")
                    except acc.AccountError as exc:
                        st.error(str(exc))

    with tab_log:
        events = safe_db(acc.recent_events, user, 25, default=[]) or []
        if events:
            st.dataframe(events, hide_index=True)
        else:
            st.info("No events recorded yet.")
        st.caption("Failed sign-in attempts are listed here so you can spot guessing. "
                   "After repeated failures an account is locked for a few minutes.")

    with tab_data:
        st.markdown("**What is stored about you**")
        st.markdown(
            "- Comparison history: file names, content hashes, scores (no source code).\n"
            "- Saved report files in your own reports folder (PDF reports can contain code snippets).\n"
            + ("- Your submitted assignment files (visible to your teacher).\n"
               if not user.is_teacher else "- Your assignments, with their submissions.\n"))
        stats = safe_db(db.get_stats, owner_id=user.id, default=None)
        if stats:
            st.caption(f"{stats['comparisons']} comparison(s) stored for you.")
        st.markdown("**Delete data**")
        c1, c2 = st.columns(2)
        with c1:
            if st.checkbox("Confirm: delete my comparison history", key="confirm_hist"):
                if st.button("Delete comparison history", key="del_hist"):
                    safe_db(db.clear_history, owner_id=user.id)
                    st.session_state["analysis"] = None
                    st.success("Comparison history deleted.")
        with c2:
            if st.checkbox("Confirm: delete my saved report files", key="confirm_reports"):
                if st.button("Delete saved reports", key="del_reports"):
                    n = rg.delete_user_reports(user.id)
                    st.success(f"{n} report file(s) overwritten and deleted.")
        st.caption("Deleted database content is overwritten (SQLite secure_delete) and the "
                   "database file is compacted. Uploaded files are held in memory only and "
                   "disappear when you press Clear all or sign out.")
        if not user.is_teacher and config.AUTH_ENABLED:
            with st.expander("Delete my account and everything stored about me"):
                st.warning("This removes your account, submissions, history and saved reports. "
                           "It cannot be undone.")
                pw = st.text_input("Confirm with your password", type="password", key="del_acct_pw")
                if st.button("Delete my account", key="del_acct"):
                    try:
                        rg.delete_user_reports(user.id)
                        acc.delete_my_account(user, pw)
                        st.session_state.clear()
                        st.session_state["login_notice"] = "Your account and data were deleted."
                        st.rerun()
                    except acc.AccountError as exc:
                        st.error(str(exc))
