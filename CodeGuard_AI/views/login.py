"""Sign-in and first-run setup."""
from __future__ import annotations

import time

import streamlit as st

import config
from src import accounts
from views.common import html


def _start_session(user) -> None:
    st.session_state.clear()
    st.session_state["user"] = user
    st.session_state["last_seen"] = time.time()
    st.session_state["page"] = "home"


def render() -> None:
    html('<div class="cg-page-title">Welcome</div>'
         '<div class="cg-lead">Sign in to compare code, manage assignments and view your '
         'history. Accounts live only in this installation; nothing is sent anywhere.</div>')
    notice = st.session_state.pop("login_notice", "")
    if notice:
        st.info(notice)
    try:
        first_run = accounts.user_count() == 0
    except Exception as exc:
        st.error(f"The account database is unavailable: {exc}")
        return

    left, _ = st.columns([2, 3])
    with left:
        if first_run:
            html('<div class="cg-card"><div class="cg-h">First-time setup</div>'
                 '<div class="cg-muted">Create the administrator (teacher) account. '
                 'Teachers and students can then sign up themselves from the sign-in page.</div></div>')
            with st.form("setup_form"):
                username = st.text_input("Username")
                name = st.text_input("Display name")
                pw = st.text_input("Password", type="password",
                                   help=f"At least {config.MIN_PASSWORD_LENGTH} characters with a "
                                        "letter and a digit.")
                pw2 = st.text_input("Repeat password", type="password")
                go = st.form_submit_button("Create administrator account", type="primary")
            if go:
                if pw != pw2:
                    st.error("The passwords do not match.")
                else:
                    try:
                        user = accounts.create_first_teacher(username, name or username, pw)
                        _start_session(user)
                        st.rerun()
                    except (accounts.AccountError, PermissionError) as exc:
                        st.error(str(exc))
        else:
            if config.ALLOW_SELF_SIGNUP:
                tab_in, tab_up = st.tabs(["Sign in", "Sign up"])
            else:
                (tab_in,), tab_up = st.tabs(["Sign in"]), None
            with tab_in:
                with st.form("login_form"):
                    username = st.text_input("Username")
                    pw = st.text_input("Password", type="password")
                    go = st.form_submit_button("Sign in", type="primary")
                if go:
                    try:
                        user = accounts.authenticate(username, pw)
                        _start_session(user)
                        st.rerun()
                    except accounts.AccountError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Sign-in failed: {exc}")
                st.caption("Forgot your password? A teacher can reset a student's password. "
                           "Teachers can run reset_password.py on the computer that hosts "
                           "CodeGuard.")
            if tab_up is not None:
                with tab_up:
                    _signup_form()


def _signup_form() -> None:
    role_label = st.radio("I am a", ["Student", "Teacher"], horizontal=True, key="signup_role")
    role = config.ROLE_TEACHER if role_label == "Teacher" else config.ROLE_STUDENT
    teachers = accounts.list_teachers() if role == config.ROLE_STUDENT else []
    if role == config.ROLE_STUDENT and not teachers:
        st.info("No teacher has signed up yet. A teacher must create an account first.")
        return
    with st.form("signup_form"):
        teacher_id = None
        if role == config.ROLE_STUDENT:
            labels = {t["id"]: f'{t["display_name"]} ({t["username"]})' for t in teachers}
            teacher_id = st.selectbox("My teacher", list(labels), format_func=labels.get)
        u = st.text_input("Choose a username")
        n = st.text_input("Your name")
        p1 = st.text_input("Choose a password", type="password",
                           help=f"At least {config.MIN_PASSWORD_LENGTH} characters with a "
                                "letter and a digit.")
        p2 = st.text_input("Repeat password", type="password")
        go = st.form_submit_button("Create account", type="primary")
    if go:
        if p1 != p2:
            st.error("The passwords do not match.")
            return
        try:
            user = accounts.register(role, u, n or u, p1, teacher_id)
            _start_session(user)
            st.rerun()
        except (accounts.AccountError, PermissionError) as exc:
            st.error(str(exc))
