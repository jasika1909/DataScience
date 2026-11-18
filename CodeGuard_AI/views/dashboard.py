"""Dashboard: role-based totals, charts and recent history."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import accounts as acc
from src import charts, database as db
from src import ui_components as ui
from views.common import current_user, goto, html, safe_db


def _teacher_overview(user) -> None:
    rows = safe_db(acc.assignment_overview, user, default=[]) or []
    st.markdown("#### Assignments")
    if not rows:
        st.info("No assignments yet. Create one on the Assignments page.")
        return
    df = pd.DataFrame(rows)[["title", "submissions", "comparisons", "top", "high"]]
    df.columns = ["Assignment", "Submissions", "Comparisons", "Highest similarity %", "High-similarity pairs"]
    st.dataframe(df, hide_index=True)


def _student_overview(user) -> None:
    rows = safe_db(acc.list_assignments, user, default=[]) or []
    st.markdown("#### My assignments")
    if not rows:
        st.info("Your teacher has not published any assignments yet.")
        return
    df = pd.DataFrame([{"Assignment": r["title"], "Due": r["due_date"] or "-",
                        "Status": "Submitted" if r["mine"] else ("Closed" if r["closed"] else "Not submitted")}
                       for r in rows])
    st.dataframe(df, hide_index=True)


def render() -> None:
    user = current_user()
    title = "Teacher dashboard" if user.is_teacher else "My dashboard"
    html(f'<div class="cg-page-title">{title}</div>'
         '<div class="cg-lead">Overview of the comparisons stored for your account.</div>')
    if user.is_teacher:
        _teacher_overview(user)
    else:
        _student_overview(user)

    stats = safe_db(db.get_stats, owner_id=user.id, default=None)
    rows = safe_db(db.get_all, owner_id=user.id, default=[]) or []
    if not stats or stats["comparisons"] == 0:
        html(ui.empty_state("No comparisons yet",
                            "Run an analysis on the Compare Code page and its results "
                            "will appear here."))
        st.button("Compare code", type="primary", key="dash_go", on_click=goto, args=("compare",))
        return

    cols = st.columns(4)
    tiles = [
        (stats["files"], "Files analyzed", ""),
        (stats["comparisons"], "Comparisons performed", "gold"),
        (f'{stats["average"]:.1f}%', "Average similarity", "green"),
        (stats["high"], "High-similarity comparisons", "red"),
    ]
    for col, (value, label, tone) in zip(cols, tiles):
        with col:
            html(ui.metric_card(value, label, tone))
    st.write("")

    settings = st.session_state.get("settings")
    low = getattr(settings, "low_max", 30)
    mod = getattr(settings, "moderate_max", 60)
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(charts.distribution_chart(rows, low, mod), key="dash_dist")
    c2.plotly_chart(charts.risk_donut(rows), key="dash_donut")
    if len(rows) > 1:
        st.plotly_chart(charts.timeline_chart(rows), key="dash_timeline")
    st.caption("Risk labels use the thresholds that were active when each comparison "
               "ran; they are indicators for review, not verdicts.")

    st.markdown("#### Recent comparisons")
    recent = pd.DataFrame(rows[:10])[["created_at", "file_a", "file_b", "overall",
                                      "risk", "matched_lines", "matched_blocks"]]
    recent.columns = ["When", "File A", "File B", "Similarity %", "Indicator",
                      "Matching lines", "Blocks"]
    st.dataframe(recent, hide_index=True)
    st.button("Open full history and reports", key="dash_reports", on_click=goto,
              args=("reports",))
