"""Results workspace: ranking, heatmap, Source A | Similarity analysis | Source B."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

import config
from src import batch, charts, database as db
from src import ui_components as ui
from src.code_viewer import code_panel_html
from src.models import ComparisonResult
from views.common import download_row, html, owner_id, safe_db


def pair_key(a: str, b: str) -> tuple:
    return tuple(sorted((a, b)))


def get_pair_result(analysis: dict, a: str, b: str):
    """Return the full result oriented as (a, b); computes and stores it if needed."""
    key = pair_key(a, b)
    existing = analysis["results"].get(key)
    if existing is None or existing.quick_only:
        res = analysis["engine"].compare(analysis["corpus"], key[0], key[1], screen=False)
        analysis["results"][key] = res
        files = analysis["files"]
        safe_db(db.save_comparison, res, files[key[0]], files[key[1]], quiet=True,
                owner_id=owner_id(), assignment_id=analysis.get("assignment_id"))
    res = analysis["results"][key]
    return res if res.file_a == a else res.swapped()


def _jump_to_pair() -> None:
    analysis = st.session_state.get("analysis")
    label = st.session_state.get("jump_pair")
    if analysis and label in analysis["jump_map"]:
        st.session_state["view_a"], st.session_state["view_b"] = analysis["jump_map"][label]


def _overview(analysis: dict) -> None:
    results = sorted(analysis["results"].values(), key=lambda r: r.overall, reverse=True)
    if len(results) < 2:
        return
    settings = analysis["engine"].settings
    info = batch.summarize(results)
    with st.expander(f"Batch overview: {len(results)} compared pairs", expanded=True):
        html('<div class="cg-card"><div class="cg-h">Analysis summary</div>'
             f'<div class="cg-muted" style="line-height:1.6">{escape(info["text"])}</div></div>')
        run = analysis.get("run", {})
        if run.get("screened"):
            st.caption(f"{run['screened']} pair(s) were quick-screened as clearly different "
                       "(open one in the workspace to run the full analysis). "
                       f"Total time {run.get('elapsed', 0)}s.")

        st.markdown("**Highest-similarity pairs**")
        top = batch.top_pairs(results, 5)
        cards = []
        for r in top:
            cards.append(
                f'<div class="cg-match"><span class="cg-swatch" style="background:'
                f'{ui.risk_color(r.risk)}"></span><div class="cg-match-body">'
                f'<b>{escape(r.file_a)}</b> and <b>{escape(r.file_b)}</b>'
                f'<small>{escape(r.risk)} indicator, {r.matched_lines} matching lines in '
                f'{r.matched_blocks} block(s)</small></div>'
                f'<span class="cg-pct">{r.overall:.1f}%</span></div>')
        html("".join(cards))

        clusters = batch.find_clusters(results, settings.moderate_max)
        if clusters:
            st.markdown(f"**Possible groups** (pairs at or above {settings.moderate_max:g}%; large or sparse groups are split at higher similarity)")
            for i, g in enumerate(clusters[:8], start=1):
                tag = "loosely linked" if g["loose"] else f'linked at {g["threshold"]:g}%+'
                html(f'<div class="cg-match"><div class="cg-match-body"><b>Group {i}</b> '
                     f'<span class="cg-tag">{len(g["files"])} files</span>'
                     f'<span class="cg-tag">{tag}</span>'
                     f'<small>{escape(", ".join(g["files"]))}</small></div>'
                     f'<span class="cg-pct">{g["max"]:.0f}%</span></div>')
        else:
            st.caption(f"No pair reaches {settings.moderate_max:g}%, so no groups were formed.")

        names = sorted({n for r in results for n in (r.file_a, r.file_b)})
        if len(names) >= 3:
            st.plotly_chart(charts.pair_heatmap(names, results), key=f"heatmap_{analysis['id']}")
        df = pd.DataFrame([{
            "File A": r.file_a, "File B": r.file_b, "Similarity %": r.overall,
            "Indicator": r.risk + (" (quick screen)" if r.quick_only else ""),
            "Matching lines": r.matched_lines, "Blocks": r.matched_blocks,
        } for r in results])
        st.dataframe(df, hide_index=True, column_config={
            "Similarity %": st.column_config.ProgressColumn(
                "Similarity %", min_value=0, max_value=100, format="%.1f")})
        labels = {f"{r.file_a} vs {r.file_b}: {r.overall:.1f}%": (r.file_a, r.file_b)
                  for r in results}
        analysis["jump_map"] = labels
        st.selectbox("Open a pair in the workspace below", list(labels),
                     key="jump_pair", on_change=_jump_to_pair)


def _explanation() -> None:
    st.markdown("**How the score is built.** The overall score is a weighted mean of the "
                "signals below. Weights and thresholds are configurable under *Analysis "
                "settings* and are indicators for human review, not proof.")
    for key in config.SIGNAL_KEYS:
        st.markdown(f"- **{config.SIGNAL_LABELS[key]}**: {config.SIGNAL_DESCRIPTIONS[key]}")
    st.markdown(
        "**False-positive reduction.** Comments, whitespace, imports, brace-only lines, "
        "standard boilerplate (entry points, input set-up, plain constructors), instructor "
        "template code and lines common to most submissions are ignored before scoring.")
    st.markdown(
        "**Limitations.** Lexical and rule-based methods cannot see intent. Shared "
        "assignment templates, standard algorithms and very short files can raise scores, "
        "while code re-implemented with different logic can score low. Java, C, C++ and "
        "JavaScript structure comes from a lightweight parser, not a full compiler grammar.")


def _unique_code(result: ComparisonResult, file_a, file_b) -> None:
    c1, c2 = st.columns(2)
    for col, label, ranges, count, src in (
            (c1, "A", result.unique_ranges_a, result.unique_lines_a, file_a),
            (c2, "B", result.unique_ranges_b, result.unique_lines_b, file_b)):
        with col:
            st.markdown(f"**Unique in {label}: {count} comparable line(s)**")
            st.caption("Line ranges: " + ui.ranges_text(ranges))
            if ranges:
                lines = src.content.split("\n")
                start, end = ranges[0]
                shown = "\n".join(lines[start - 1:min(end, start + 14)])
                st.caption(f"First unique range (lines {start}-{end}):")
                st.code(shown, language=src.language if src.language != "cpp" else "cpp")


def render_results(analysis: dict) -> None:
    html('<div class="cg-rule"></div><div class="cg-page-title">Results</div>')
    for pair, message in analysis["errors"].items():
        st.warning(f"Could not compare {pair[0]} and {pair[1]}: {message}")
    for name, message in analysis["corpus"].failed.items():
        st.warning(f"Could not analyse {name}: {message}")
    if not analysis["results"] and not analysis["corpus"].docs:
        st.error("No comparison could be completed. Check the warnings above.")
        return
    corpus = analysis["corpus"]
    if corpus.templates_used or corpus.common_lines:
        bits = []
        if corpus.templates_used:
            bits.append(f"{corpus.templates_used} template file(s)")
        if corpus.common_lines:
            bits.append(f"{corpus.common_lines} line pattern(s) common to most submissions")
        st.info("Ignored as non-evidence: " + " and ".join(bits) + ".")

    _overview(analysis)

    names = [n for n in analysis["order"] if n in corpus.docs]
    if len(names) < 2:
        st.info("At least two analysable files are needed.")
        return
    st.session_state.setdefault("view_a", names[0])
    st.session_state.setdefault("view_b", names[1])
    for k in ("view_a", "view_b"):
        if st.session_state[k] not in names:       # file removed / renamed
            st.session_state[k] = names[0] if k == "view_a" else names[1]

    sel_a, sel_mid, sel_b = st.columns([5, 4, 5], gap="medium")
    sel_a.selectbox("Source code A", names, key="view_a")
    sel_b.selectbox("Source code B", names, key="view_b")
    a_name, b_name = st.session_state["view_a"], st.session_state["view_b"]
    if a_name == b_name:
        st.warning("Choose two different files to compare.")
        return

    try:
        with st.spinner("Comparing selected files..."):
            result: ComparisonResult = get_pair_result(analysis, a_name, b_name)
    except Exception as exc:
        st.error(f"This pair could not be compared: {exc}")
        return
    file_a, file_b = analysis["files"][a_name], analysis["files"][b_name]

    col_a, col_mid, col_b = st.columns([5, 4, 5], gap="medium")

    # Center first, so the focus choice is known before the code panels render.
    focus = None
    with col_mid:
        html('<div class="cg-card blue"><div class="cg-h" style="color:#fde68a">Similarity Analysis</div>'
             + ui.score_ring(result)
             + ui.stat_tiles([
                 (result.matched_lines, "matching lines"),
                 (result.matched_blocks, "matched code blocks"),
                 (f"{result.coverage_a:.0f}%", "of A matched"),
                 (f"{result.coverage_b:.0f}%", "of B matched"),
                 (result.unique_lines_a, "unique lines in A"),
                 (result.unique_lines_b, "unique lines in B"),
             ]) + '</div>')
        html('<div class="cg-card" style="margin-top:.8rem"><div class="cg-h">Signals</div>'
             + ui.signal_bars(result) + '</div>')
        html('<div class="cg-card" style="margin-top:.8rem"><div class="cg-h">Matched sections</div>'
             + ui.match_list(result) + '</div>')
        if result.blocks:
            options = ["All sections"] + [
                f"Section {b.id} ({b.kind}): A {b.a_start}-{b.a_end}" for b in result.blocks]
            choice = st.selectbox("Highlight", options, key=f"focus_{pair_key(a_name, b_name)}")
            if choice != "All sections":
                focus = int(choice.split(" (")[0].split()[1])
        html(f'<div class="cg-muted" style="margin-top:.5rem">{escape(result.method)}. '
             f'{escape(result.method_note)}</div>')

    with col_a:
        html(code_panel_html(file_a, "a", result.blocks, focus, title=f"Source A: {file_a.name}"))
    with col_b:
        html(code_panel_html(file_b, "b", result.blocks, focus, title=f"Source B: {file_b.name}"))

    html(ui.legend(result))
    for warning in result.warnings:
        st.warning(warning)

    tab_names = ["Why this score", "Signal breakdown", "Unique code"]
    if result.function_matches:
        tab_names.append("Function structure")
    tab_names.append("How it works")
    tabs = dict(zip(tab_names, st.tabs(tab_names)))

    with tabs["Why this score"]:
        html('<div class="cg-card"><div class="cg-h">Reasons behind the similarity score</div>'
             + ui.bullets(result.reasons) + '</div>')
        table = ui.excluded_table(result)
        if table:
            html('<div class="cg-card" style="margin-top:.8rem">' + table + '</div>')
    with tabs["Signal breakdown"]:
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(charts.signal_chart(result), key=f"sig_{a_name}_{b_name}")
        c2.plotly_chart(charts.risk_gauge(result), key=f"gauge_{a_name}_{b_name}")
        st.caption(
            f"Risk indicator thresholds (configurable): Low below "
            f"{result.thresholds.get('low_max', 30):g}%, Moderate below "
            f"{result.thresholds.get('moderate_max', 60):g}%, otherwise High. "
            "Treat these as prompts for a human review.")
    with tabs["Unique code"]:
        _unique_code(result, file_a, file_b)
    if result.function_matches:
        with tabs["Function structure"]:
            st.caption("Functions whose syntax trees match after names, literal values and "
                       "docstrings are ignored.")
            html(ui.function_match_list(result))
    with tabs["How it works"]:
        _explanation()

    st.markdown("#### Download reports")
    st.caption("Selected pair (PDF includes matched code snippets)")
    download_row([result], f"codeguard_{a_name}_vs_{b_name}".replace(" ", "_"), "dl_pair",
                 sources=analysis["files"])
    all_results = list(analysis["results"].values())
    if len(all_results) > 1:
        st.caption(f"All {len(all_results)} compared pairs")
        download_row(all_results, f"codeguard_all_pairs_{analysis['id']}", "dl_all",
                     sources=analysis["files"])
