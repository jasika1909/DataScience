"""CodeGuard AI - entry point.

Run from the project root:   python -m streamlit run app.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import pandas  # noqa: F401
    import plotly  # noqa: F401
    import streamlit as st
except ImportError as exc:  # friendly message instead of a raw traceback
    sys.stderr.write(
        f"\nMissing dependency: {exc.name}\n"
        "Activate your virtual environment and run:\n"
        "    python -m pip install -r requirements.txt\n"
        "Then start the app with:\n"
        "    python -m streamlit run app.py\n\n")
    raise SystemExit(1)

import config

st.set_page_config(page_title=f"{config.APP_NAME}: code similarity analysis",
                   page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

from src import accounts, database as db
from src import ui_components as ui
from views import (about, account, assignments, comparison_history, compare_code,
                   dashboard, home, login)
from views.common import goto, html

PAGES = {
    "home": ("Home", home.render),
    "compare": ("Compare Code", compare_code.render),
    "assignments": ("Assignments", assignments.render),
    "dashboard": ("Dashboard", dashboard.render),
    "reports": ("Reports", comparison_history.render),
    "about": ("About", about.render),
    "account": ("Account", account.render),
}


def render_header(user) -> None:
    brand, nav = st.columns([4, 7], vertical_alignment="center")
    with brand:
        html(ui.brand_html(user))
    with nav:
        cols = st.columns(len(PAGES))
        for col, (key, (label, _)) in zip(cols, PAGES.items()):
            with col:
                st.button(label, key=f"nav_{key}", on_click=goto, args=(key,),
                          type="primary" if st.session_state["page"] == key else "secondary")
    html('<div class="cg-rule"></div>')


def current_session_user():
    """The signed-in user, or None (after showing the sign-in page)."""
    if not config.AUTH_ENABLED:
        if "user" not in st.session_state:
            st.session_state["user"] = accounts.get_or_create_local_user()
        return st.session_state["user"]
    user = st.session_state.get("user")
    if user is not None:
        idle = time.time() - st.session_state.get("last_seen", 0)
        if idle > config.SESSION_TIMEOUT_MIN * 60:
            st.session_state.clear()
            st.session_state["login_notice"] = (
                f"You were signed out after {config.SESSION_TIMEOUT_MIN} minutes of inactivity.")
            return None
        st.session_state["last_seen"] = time.time()
        # Re-check the account on every run (deactivated or deleted users are cut off).
        if accounts.get_user(user.id) is None:
            st.session_state.clear()
            st.session_state["login_notice"] = "This account is no longer active."
            return None
    return user


def main() -> None:
    html(ui.stylesheet())
    try:
        db.init_db()
    except db.DatabaseError as exc:
        st.error(f"{exc} The app cannot start without its database.")
        return
    st.session_state.setdefault("page", "home")
    user = current_session_user()
    if user is None:
        html(ui.brand_html())
        html('<div class="cg-rule"></div>')
        login.render()
        return
    if st.session_state["page"] not in PAGES:
        st.session_state["page"] = "home"
    render_header(user)
    try:
        PAGES[st.session_state["page"]][1]()
    except Exception as exc:  # a page failure must not take down the layout
        st.error(f"This page hit an unexpected error: {type(exc).__name__}: {exc}")
        st.button("Back to Home", key="err_home", on_click=goto, args=("home",))


main()
