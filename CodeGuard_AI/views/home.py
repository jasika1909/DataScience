"""Landing page."""
from __future__ import annotations

import streamlit as st

import config
from views.common import goto, html


def _try_samples() -> None:
    from views.compare_code import _init_state, _load_sample_set
    _init_state()
    _load_sample_set(next(iter(config.SAMPLE_SETS)))
    goto("compare")


def render() -> None:
    html('<div class="cg-hero"><h1>Find copied code, with evidence you can review</h1>'
         '<p>CodeGuard AI compares source files line by line and structure by structure. '
         'It highlights matching blocks even when variables were renamed or the code was '
         'reformatted, and explains where every score comes from. Results are indicators '
         'for a person to review, not automatic proof of plagiarism.</p></div>')
    st.write("")
    c1, c2, _ = st.columns([1, 1, 3])
    c1.button("Compare code", type="primary", key="home_start", on_click=goto, args=("compare",))
    c2.button("Try sample files", key="home_samples", on_click=_try_samples)

    st.write("")
    cols = st.columns(3)
    cards = [
        ("Fewer false positives", "Imports, boilerplate, instructor templates and code that "
                                  "most students share are ignored before scoring, and the "
                                  "report lists exactly what was excluded."),
        ("Finds the same logic", "Renamed variables, different loop styles, reordered "
                                 "functions and even code ported between languages are "
                                 "detected by structural and semantic analysis."),
        ("Batch and classroom ready", "Compare a ZIP of submissions, see a similarity "
                                      "heatmap and ranked pairs, and manage assignments with "
                                      "teacher and student accounts."),
    ]
    for col, (title, text) in zip(cols, cards):
        with col:
            html(f'<div class="cg-card" style="height:100%"><div class="cg-h">{title}</div>'
                 f'<div class="cg-muted" style="line-height:1.55">{text}</div></div>')

    st.write("")
    html('<div class="cg-card"><div class="cg-h">How a comparison works</div>'
         '<div class="cg-muted" style="line-height:1.7">'
         '1. Add two or more files (or a ZIP of submissions) by upload, paste or sample.<br>'
         '2. Comments, whitespace, imports and brace-only lines are stripped; identifiers '
         'and literals are abstracted.<br>'
         '3. Each signal is scored 0 to 100 and blended into an overall percentage.<br>'
         '4. Matching blocks are colour-highlighted in both files, and every result can '
         'be exported as CSV or PDF.</div></div>')
