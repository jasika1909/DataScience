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
                email = st.text_input("Email ID", help="Used to reset your password if you forget it.")
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
                        user = accounts.create_first_teacher(username, name or username, pw, email=accounts.validate_email(email))
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
                if st.session_state.get("forgot_mode"):
                    _forgot_flow()
                else:
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
                    st.button("Forgot Password?", key="forgot_link", on_click=_enter_forgot)
            if tab_up is not None:
                with tab_up:
                    _signup_form()


def _enter_forgot() -> None:
    st.session_state["forgot_mode"] = True
    st.session_state.pop("reset_email", None)


def _leave_forgot() -> None:
    st.session_state["forgot_mode"] = False
    st.session_state.pop("reset_email", None)


def _different_email() -> None:
    st.session_state.pop("reset_email", None)


def _forgot_flow() -> None:
    """Forgot password: email check, then new password twice, then update."""
    st.markdown("#### Forgot Password")
    if not config.ALLOW_EMAIL_RESET:
        st.info("Password reset by email is turned off. Please ask your teacher or the "
                "administrator to reset your password.")
        st.button("Back to sign in", key="forgot_back_off", on_click=_leave_forgot)
        return
    email = st.session_state.get("reset_email")
    if not email:
        st.caption("Enter the email ID that you registered with.")
        with st.form("forgot_email_form"):
            typed = st.text_input("Registered email ID")
            go = st.form_submit_button("Continue", type="primary")
        if go:
            try:
                if accounts.email_is_registered(typed):
                    st.session_state["reset_email"] = accounts.validate_email(typed)
                    st.rerun()
                else:
                    st.error("This email ID is not registered. Please check the email ID "
                             "or sign up for a new account.")
            except (accounts.AccountError, PermissionError) as exc:
                st.error(str(exc))
    else:
        st.success(f"Registered email ID found: {email}. Create a new password below.")
        with st.form("forgot_password_form"):
            p1 = st.text_input("Create New Password", type="password",
                               help=f"At least {config.MIN_PASSWORD_LENGTH} characters with a "
                                    "letter and a digit.")
            p2 = st.text_input("Re-enter New Password", type="password")
            go = st.form_submit_button("Update password", type="primary")
        if go:
            try:
                accounts.reset_password_by_email(email, p1, p2)
                st.session_state["forgot_mode"] = False
                st.session_state.pop("reset_email", None)
                st.session_state["login_notice"] = ("Your password has been updated. "
                                                    "Please sign in with your new password.")
                st.rerun()
            except (accounts.AccountError, PermissionError) as exc:
                st.error(str(exc))
        st.button("Use a different email ID", key="forgot_other", on_click=_different_email)
    st.button("Back to sign in", key="forgot_back", on_click=_leave_forgot)


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
        em = st.text_input("Email ID", help="Needed to reset your password if you forget it.")
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
            user = accounts.register(role, u, n or u, p1, teacher_id,
                                     email=accounts.validate_email(em))
            _start_session(user)
            st.rerun()
        except (accounts.AccountError, PermissionError) as exc:
            st.error(str(exc))
