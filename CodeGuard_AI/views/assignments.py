"""Assignments: teachers manage them and run batch analyses; students submit."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import config
from src import accounts as acc
from src.code_viewer import code_panel_html
from src.file_handler import FileValidationError, load_source_file
from src.database import DatabaseError
from views.common import current_user, get_settings, html


def _guard(action):
    """Run an account action and show friendly errors."""
    try:
        return True, action()
    except (acc.AccountError, FileValidationError) as exc:
        st.error(str(exc))
    except PermissionError as exc:
        st.error(f"Not allowed: {exc}")
    except DatabaseError as exc:
        st.error(str(exc))
    return False, None


# --------------------------------------------------------------------------- #
# Teacher
# --------------------------------------------------------------------------- #
def _create_assignment_form(user) -> None:
    with st.expander("Create a new assignment"):
        with st.form("new_assignment", clear_on_submit=True):
            title = st.text_input("Title")
            description = st.text_area("Description (optional)", height=90)
            c1, c2 = st.columns(2)
            language = c1.selectbox("Language", ["any"] + list(config.LANGUAGE_LABELS),
                                    format_func=lambda k: "Any supported language"
                                    if k == "any" else config.LANGUAGE_LABELS[k])
            use_due = c2.checkbox("Set a due date")
            due = c2.date_input("Due date", value=date.today())
            tmpl = st.file_uploader("Optional: starter / template code (ignored as non-evidence)",
                                    type=[e.lstrip(".") for e in config.SUPPORTED_EXTENSIONS])
            go = st.form_submit_button("Create assignment", type="primary")
        if go:
            def action():
                template = load_source_file(tmpl.name, tmpl.getvalue(), "template") if tmpl else None
                return acc.create_assignment(user, title, description, language,
                                             due.isoformat() if use_due else None, template)
            ok, _ = _guard(action)
            if ok:
                st.success("Assignment created.")
                st.rerun()


def _teacher_assignments(user) -> None:
    from views.compare_code import run_analysis
    from views.results import render_results

    _create_assignment_form(user)
    ok, assignments = _guard(lambda: acc.list_assignments(user))
    if not ok or not assignments:
        if ok:
            st.info("No assignments yet. Create one above, then share it with your students.")
        return

    labels = {a["id"]: f'{a["title"]}  ({a["submissions"]} submission(s))' for a in assignments}
    chosen = st.selectbox("Assignment", list(labels), format_func=labels.get, key="asg_pick")
    a = next(x for x in assignments if x["id"] == chosen)
    html('<div class="cg-card">'
         f'<div class="cg-h">{ui_escape(a["title"])}</div>'
         f'<div class="cg-muted">{ui_escape(a["description"] or "No description.")}<br>'
         f'Language: {"any" if a["language"] == "any" else config.LANGUAGE_LABELS[a["language"]]}'
         f' | Due: {a["due_date"] or "not set"} | '
         f'{"Closed" if a["closed"] else "Open"}'
         f'{" | Template attached" if a["template_name"] else ""}</div></div>')

    ok, subs = _guard(lambda: acc.list_submissions(user, chosen))
    if ok and subs:
        df = pd.DataFrame(subs)[["username", "display_name", "filename", "line_count",
                                 "submitted_at", "late"]]
        df.columns = ["Username", "Name", "File", "Lines", "Submitted", "Late"]
        st.dataframe(df, hide_index=True)
        st.markdown("#### View submitted code")
        pick = st.selectbox(
            "Choose a submission", [x["id"] for x in subs], key=f"view_sub_{chosen}",
            format_func=lambda i: next(f'{x["display_name"]} ({x["username"]}): {x["filename"]}'
                                       for x in subs if x["id"] == i))
        ok2, src = _guard(lambda: acc.get_submission_source(user, pick))
        if ok2:
            html(code_panel_html(src, "a", [], None, title=src.name))
            st.download_button("Download this file", src.content.encode("utf-8"),
                               file_name=src.name, mime="text/plain", key=f"dl_sub_{pick}")
    elif ok:
        st.info("No submissions yet.")

    c1, c2, c3 = st.columns(3)
    c1.button("Reopen submissions" if a["closed"] else "Close submissions", key=f"close_{chosen}",
              on_click=lambda: _guard(lambda: acc.set_assignment_closed(user, chosen, not a["closed"])))
    if subs:
        victim = c2.selectbox("Delete a submission", [s["id"] for s in subs],
                              format_func=lambda i: next(s["username"] for s in subs if s["id"] == i),
                              key=f"del_pick_{chosen}")
        c2.button("Delete selected submission", key=f"del_sub_{chosen}",
                  on_click=lambda: _guard(lambda: acc.delete_submission(user, victim)))
    with c3.expander("Delete this assignment"):
        st.warning("Deletes the assignment, every submission and its stored comparisons.")
        if st.checkbox("I understand", key=f"confirm_del_{chosen}"):
            st.button("Delete assignment", key=f"del_asg_{chosen}",
                      on_click=lambda: _guard(lambda: acc.delete_assignment(user, chosen)))

    if subs and len(subs) >= 2:
        if st.button("Analyze all submissions", type="primary", key="analyze_assignment"):
            ok, data = _guard(lambda: acc.assignment_sources(user, chosen))
            if ok:
                files, templates = data
                names = [f.name for f in files]
                try:
                    run_analysis(files, "all", names[0], names[1], get_settings(), True,
                                 templates=templates, assignment_id=chosen)
                except Exception as exc:
                    st.error(f"The analysis failed: {type(exc).__name__}: {exc}")
        analysis = st.session_state.get("analysis")
        if analysis and analysis.get("assignment_id") == chosen:
            render_results(analysis)
    elif subs:
        st.caption("At least two submissions are needed to compare them with each other. "
                   "You can already read the submitted code above.")


def _teacher_students(user) -> None:
    st.markdown("#### Student accounts")
    with st.form("new_student", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        username = c1.text_input("Username")
        name = c2.text_input("Display name")
        pw = c3.text_input("Temporary password", type="password")
        go = st.form_submit_button("Create student account", type="primary")
    if go:
        ok, _ = _guard(lambda: acc.create_user(user, username, name or username, pw))
        if ok:
            st.success(f"Account '{username}' created. Share the temporary password privately.")
            st.rerun()
    ok, students = _guard(lambda: acc.list_students(user))
    if not ok or not students:
        if ok:
            st.info("No student accounts yet.")
        return
    df = pd.DataFrame(students)[["username", "display_name", "active", "created_at"]]
    df.columns = ["Username", "Name", "Active", "Created"]
    st.dataframe(df, hide_index=True)

    pick = st.selectbox("Manage a student", [s["id"] for s in students], key="stud_pick",
                        format_func=lambda i: next(s["username"] for s in students if s["id"] == i))
    c1, c2 = st.columns(2)
    with c1:
        newpw = st.text_input("New temporary password", type="password", key="stud_newpw")
        if st.button("Reset password", key="stud_reset"):
            ok, _ = _guard(lambda: acc.reset_student_password(user, pick, newpw))
            if ok:
                st.success("Password reset.")
        active = next(s["active"] for s in students if s["id"] == pick)
        st.button("Deactivate account" if active else "Reactivate account", key="stud_toggle",
                  on_click=lambda: _guard(lambda: acc.set_student_active(user, pick, not active)))
    with c2:
        st.warning("Deleting a student removes their submissions and comparison history.")
        if st.checkbox("I understand", key="stud_confirm"):
            st.button("Delete student", key="stud_delete",
                      on_click=lambda: _guard(lambda: acc.delete_student(user, pick)))
    if user.is_admin:
        with st.expander("Administrator: create a teacher account directly"):
            with st.form("new_teacher", clear_on_submit=True):
                u2 = st.text_input("Username", key="t_user")
                n2 = st.text_input("Display name", key="t_name")
                p2 = st.text_input("Temporary password", type="password", key="t_pw")
                go2 = st.form_submit_button("Create teacher account")
            if go2:
                ok, _ = _guard(lambda: acc.create_user(user, u2, n2 or u2, p2, config.ROLE_TEACHER))
                if ok:
                    st.success("Teacher account created.")


def _teacher_view(user) -> None:
    tab_a, tab_s = st.tabs(["Assignments", "Students"])
    with tab_a:
        _teacher_assignments(user)
    with tab_s:
        _teacher_students(user)


# --------------------------------------------------------------------------- #
# Student
# --------------------------------------------------------------------------- #
def _student_view(user) -> None:
    ok, assignments = _guard(lambda: acc.list_assignments(user))
    if not ok:
        return
    if not assignments:
        st.info("Your teacher has not published any assignments yet.")
        return
    st.caption("Your teacher can see the code you submit. Other students cannot. You can "
               "delete your submission at any time.")
    for a in assignments:
        mine = acc.my_submission(user, a["id"])
        status = ("Closed" if a["closed"] else "Open")
        html('<div class="cg-card" style="margin:.6rem 0">'
             f'<div class="cg-h">{ui_escape(a["title"])}</div>'
             f'<div class="cg-muted">{ui_escape(a["description"] or "")}<br>'
             f'Language: {"any" if a["language"] == "any" else config.LANGUAGE_LABELS[a["language"]]}'
             f' | Due: {a["due_date"] or "not set"} | {status}</div></div>')
        if mine:
            late = " (late)" if mine["late"] else ""
            st.success(f"Submitted {mine['filename']} ({mine['line_count']} lines) at "
                       f"{mine['submitted_at']}{late}.")
            with st.expander("View my submitted code"):
                okv, mysrc = _guard(lambda sid=mine["id"]: acc.get_submission_source(user, sid))
                if okv:
                    html(code_panel_html(mysrc, "a", [], None, title=mysrc.name))
            st.button("Delete my submission", key=f"del_mine_{a['id']}",
                      on_click=lambda sid=mine["id"]: _guard(lambda: acc.delete_submission(user, sid)))
        if a["closed"]:
            st.caption("This assignment is closed for new submissions.")
            continue
        up = st.file_uploader("Choose your file" if not mine else "Replace your submission",
                              type=[e.lstrip(".") for e in config.SUPPORTED_EXTENSIONS],
                              key=f"submit_file_{a['id']}")
        if up is not None and st.button("Submit", key=f"submit_{a['id']}", type="primary"):
            def action():
                src = load_source_file(up.name, up.getvalue(), "submission")
                return acc.submit_file(user, a["id"], src)
            ok, res = _guard(action)
            if ok:
                st.success("Submitted." + (" It is marked as late." if res["late"] else ""))
                st.rerun()


def ui_escape(text: str) -> str:
    from html import escape
    return escape(text or "")


def render() -> None:
    user = current_user()
    html('<div class="cg-page-title">Assignments</div>'
         '<div class="cg-lead">'
         + ("Create assignments, manage student accounts and compare all submissions at once."
            if user.is_teacher else "View assignments from your teacher and submit your work.")
         + '</div>')
    (_teacher_view if user.is_teacher else _student_view)(user)
