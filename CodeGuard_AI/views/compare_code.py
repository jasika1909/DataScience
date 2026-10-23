"""Compare Code page: upload (files or ZIP), paste, samples, settings, analysis."""
from __future__ import annotations

import hashlib
import time

import streamlit as st

import config
from config import Settings
from src import database as db
from src import report_generator as rg
from src import ui_components as ui
from src.file_handler import (FileValidationError, dedupe_names, load_from_path,
                              load_source_file, load_zip, source_from_text)
from src.similarity_engine import SimilarityEngine
from views.common import get_settings, html, owner_id, safe_db
from views.results import pair_key, render_results


# --------------------------------------------------------------------------- #
# State helpers
# --------------------------------------------------------------------------- #
def _init_state() -> None:
    st.session_state.setdefault("uploader_n", 0)
    st.session_state.setdefault("extras", [])
    st.session_state.setdefault("analysis", None)
    st.session_state.setdefault("_parse_cache", {})
    st.session_state.setdefault("_analysis_counter", 0)
    st.session_state.setdefault("paste_n", 1)
    st.session_state.setdefault("_engine_cache", {})


def _add_extra(source) -> bool:
    extras = st.session_state["extras"]
    if any(e.sha256 == source.sha256 and e.name == source.name for e in extras):
        return False
    extras.append(source)
    return True


def _clear_all() -> None:
    st.session_state["uploader_n"] += 1
    st.session_state["extras"] = []
    st.session_state["analysis"] = None


def _remove_extra(index: int) -> None:
    extras = st.session_state["extras"]
    if 0 <= index < len(extras):
        extras.pop(index)


def _load_sample_set(label: str) -> None:
    errors = []
    for name in config.SAMPLE_SETS[label]:
        try:
            _add_extra(load_from_path(config.SAMPLES_DIR / name))
        except FileValidationError as exc:
            errors.append(str(exc))
    st.session_state["sample_errors"] = errors


def _load_all_samples() -> None:
    errors = []
    for label in config.SAMPLE_SETS:
        for name in config.SAMPLE_SETS[label]:
            try:
                _add_extra(load_from_path(config.SAMPLES_DIR / name))
            except FileValidationError as exc:
                errors.append(str(exc))
    st.session_state["sample_errors"] = errors


def _add_snippet() -> None:
    language = st.session_state.get("paste_language", "python")
    text = st.session_state.get("paste_text", "")
    name = st.session_state.get("paste_name", "").strip() or None
    default = f"snippet_{st.session_state['paste_n']}{config.DEFAULT_EXTENSION[language]}"
    try:
        src = source_from_text(text, language, name or default)
    except FileValidationError as exc:
        st.session_state["paste_error"] = str(exc)
        return
    st.session_state["paste_error"] = ""
    if _add_extra(src):
        st.session_state["paste_n"] += 1
    st.session_state["paste_text"] = ""
    st.session_state["paste_name"] = ""


def parse_uploads(uploaded: list, origin: str = "upload"):
    """Validate uploads (cached by name + content hash). Handles ZIP archives.

    Returns (sources, errors, notes).
    """
    cache = st.session_state.setdefault("_parse_cache", {})
    sources, errors, notes = [], [], []
    for up in uploaded:
        data = up.getvalue()
        key = (up.name, hashlib.sha1(data).hexdigest(), origin)
        if key not in cache:
            try:
                if up.name.lower().endswith(".zip"):
                    got, errs, skipped = load_zip(up.name, data)
                    cache[key] = ("zip", got, errs, skipped)
                else:
                    src = load_source_file(up.name, data, origin)
                    cache[key] = ("file", [src], [], 0)
            except FileValidationError as exc:
                cache[key] = ("error", [], [str(exc)], 0)
        kind, got, errs, skipped = cache[key]
        sources += got
        errors += errs
        if kind == "zip":
            notes.append(f"{up.name}: {len(got)} file(s) read, {skipped} skipped "
                         "(unsupported or hidden).")
    return sources, errors, notes


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
def _reset_settings() -> None:
    for key in config.SIGNAL_KEYS:
        st.session_state[f"w_{key}"] = config.DEFAULT_WEIGHTS[key]
    st.session_state["low_max"] = 30
    st.session_state["moderate_max"] = 60
    st.session_state["min_block"] = config.DEFAULT_MIN_BLOCK_LINES
    st.session_state["excl_boiler"] = True
    st.session_state["common_pct"] = int(config.COMMON_FRACTION * 100)
    st.session_state["screen_pct"] = int(config.SCREEN_THRESHOLD)


def _settings_panel() -> Settings:
    with st.expander("Analysis settings (weights, thresholds, false-positive reduction)"):
        st.caption("Risk thresholds are configurable indicators for human review, not "
                   "universally valid cut-offs.")
        cols = st.columns(3)
        weights = {}
        for i, key in enumerate(config.SIGNAL_KEYS):
            weights[key] = cols[i % 3].slider(
                config.SIGNAL_LABELS[key], 0.0, 1.0, config.DEFAULT_WEIGHTS[key], 0.05,
                key=f"w_{key}", help=config.SIGNAL_DESCRIPTIONS[key])
        c1, c2, c3 = st.columns(3)
        low = c1.slider("Low indicator below (%)", 5, 90, 30, key="low_max")
        mod = c2.slider("Moderate indicator below (%)", 10, 95, 60, key="moderate_max")
        block = c3.slider("Minimum matched block (lines)", 1, 10,
                          config.DEFAULT_MIN_BLOCK_LINES, key="min_block")
        st.markdown("**False-positive reduction and performance**")
        d1, d2, d3 = st.columns(3)
        boiler = d1.checkbox("Ignore standard boilerplate", value=True, key="excl_boiler",
                             help="Entry points (main), standard input set-up, plain "
                                  "constructors and accessors are not counted as evidence.")
        common = d2.slider("Common-code filter (% of files)", 0, 100,
                           int(config.COMMON_FRACTION * 100), key="common_pct",
                           help=f"With at least {config.COMMON_MIN_FILES} files, lines present "
                                "in this share of the files are treated as template or common "
                                "code. 0 turns the filter off.")
        screen = d3.slider("Quick-screen threshold (%)", 0, 60, int(config.SCREEN_THRESHOLD),
                           key="screen_pct",
                           help=f"Batches of {config.SCREEN_MIN_PAIRS}+ pairs skip the full "
                                "analysis for pairs whose cheap signals fall below this value. "
                                "0 analyses every pair in full.")
        st.button("Reset to defaults", on_click=_reset_settings, key="reset_settings")
    settings = Settings(weights=weights, low_max=float(low), moderate_max=float(mod),
                        min_block_lines=int(block), exclude_boilerplate=bool(boiler),
                        common_fraction=common / 100.0, screen_threshold=float(screen))
    try:
        settings.validate()
        if sum(weights.values()) <= 0:
            raise ValueError("At least one weight must be above zero.")
    except ValueError as exc:
        st.error(f"Invalid settings, using defaults: {exc}")
        settings = Settings()
    st.session_state["settings"] = settings
    return settings


# --------------------------------------------------------------------------- #
# Analysis (also used by the assignments page)
# --------------------------------------------------------------------------- #
def run_analysis(files: list, mode: str, a: str, b: str, settings: Settings,
                 save_copy: bool, templates: list | None = None,
                 assignment_id: int | None = None) -> None:
    """Analyse ``files`` and store the analysis in the session."""
    _init_state()
    engine = SimilarityEngine(settings, cache=st.session_state["_engine_cache"])
    bar = st.progress(0.0, text="Preparing files...")
    with st.spinner("Analyzing code similarity..."):
        corpus = engine.prepare(files, templates)
        names = [f.name for f in files]
        pairs = engine.all_pairs(names) if mode == "all" else [pair_key(a, b)]
        pairs = [p for p in pairs if p[0] in corpus.docs and p[1] in corpus.docs]

        def progress(done: int, total: int, label: str) -> None:
            bar.progress(done / max(total, 1), text=f"Comparing {label} ({done}/{total})")

        results, errors = engine.compare_pairs(corpus, pairs, progress)
    bar.empty()

    by_name = {f.name: f for f in files}
    uid = owner_id()
    db_failed = False
    for res in results:
        if safe_db(db.save_comparison, res, by_name[res.file_a], by_name[res.file_b],
                   default=None, quiet=True, owner_id=uid, assignment_id=assignment_id) is None:
            db_failed = True
    if db_failed:
        st.warning("Results could not be saved to the history database; "
                   "they are still shown below.")
    if engine.last_run["skipped"]:
        st.warning(f"The time budget ({settings.time_budget_s:g}s) was reached: "
                   f"{engine.last_run['skipped']} pair(s) were not analysed. Compare "
                   "fewer files or raise the quick-screen threshold.")

    if save_copy and results:
        try:
            folder = rg.user_reports_dir(uid)
            rg.save_report(rg.summary_csv(results), "summary", "csv", folder)
            if rg.pdf_available():
                rg.save_report(rg.pdf_report(results, sources=by_name), "report", "pdf", folder)
        except Exception as exc:
            st.warning(f"Could not save report copies to the reports folder: {exc}")

    st.session_state["_analysis_counter"] += 1
    st.session_state["analysis"] = {
        "id": st.session_state["_analysis_counter"],
        "files": by_name, "order": names, "engine": engine, "corpus": corpus,
        "results": {pair_key(r.file_a, r.file_b): r for r in results},
        "errors": errors, "jump_map": {}, "created": time.time(),
        "assignment_id": assignment_id, "templates": templates or [],
        "run": dict(engine.last_run),
    }
    st.session_state["view_a"], st.session_state["view_b"] = (
        (a, b) if mode == "pair" else (names[0], names[1]))
    for key in [k for k in st.session_state if str(k).startswith("focus_")]:
        del st.session_state[key]


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def render() -> None:
    _init_state()
    html('<div class="cg-page-title">Compare Code</div>'
         '<div class="cg-lead">Add two or more source files (or a ZIP of student '
         'submissions), choose what to compare, and run the analysis. Everything is '
         'processed on this computer; uploaded code is only read as text and never '
         'executed.</div>')

    tab_up, tab_paste, tab_sample = st.tabs(["Upload files or ZIP", "Paste code", "Sample files"])

    with tab_up:
        types = [e.lstrip(".") for e in config.SUPPORTED_EXTENSIONS] + ["zip"]
        uploaded = st.file_uploader(
            "Drop source files or a ZIP archive here, or browse",
            type=types, accept_multiple_files=True,
            key=f"uploader_{st.session_state['uploader_n']}",
            help=(f"Supported: {', '.join(config.SUPPORTED_EXTENSIONS)} and .zip. Up to "
                  f"{config.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB and "
                  f"{config.MAX_LINES_PER_FILE:,} lines per file, {config.MAX_FILES} files in "
                  "total. In a ZIP, folder names become part of the file name "
                  "(student1/main.py -> student1__main.py). Remove a file with the x next to "
                  "it, or upload again to replace it."))
        tmpl_files = st.file_uploader(
            "Optional: instructor template / starter code (ignored as non-evidence)",
            type=[e.lstrip(".") for e in config.SUPPORTED_EXTENSIONS],
            accept_multiple_files=True, key=f"templates_{st.session_state['uploader_n']}",
            help="Lines that appear in the template are not counted as similarity.")

    with tab_paste:
        c1, c2 = st.columns([1, 2])
        c1.selectbox("Language", list(config.LANGUAGE_LABELS),
                     format_func=lambda k: config.LANGUAGE_LABELS[k], key="paste_language")
        c2.text_input("Snippet name (optional)", key="paste_name", placeholder="student_a.py")
        st.text_area("Paste source code", height=220, key="paste_text",
                     placeholder="Paste code here, then choose Add snippet.")
        st.button("Add snippet", on_click=_add_snippet, key="add_snippet")
        if st.session_state.get("paste_error"):
            st.error(st.session_state["paste_error"])

    with tab_sample:
        st.caption("Ready-made examples: exact copies, renamed identifiers, reformatting, "
                   "unrelated code and the same logic written in a different style or language.")
        for i, label in enumerate(config.SAMPLE_SETS):
            st.button(f"Load: {label}", key=f"sample_{i}", on_click=_load_sample_set, args=(label,))
        st.button("Load all sample files", key="sample_all", on_click=_load_all_samples)
        for message in st.session_state.get("sample_errors", []):
            st.error(message)

    # ---- workspace ------------------------------------------------------ #
    uploaded_sources, upload_errors, notes = parse_uploads(uploaded or [])
    template_sources, template_errors, _ = parse_uploads(tmpl_files or [], origin="template")
    for message in upload_errors + template_errors:
        st.error(message)
    for note in notes:
        st.caption(note)
    files = dedupe_names(uploaded_sources + st.session_state["extras"])
    if len(files) > config.MAX_FILES:
        st.warning(f"Only the first {config.MAX_FILES} files are used.")
        files = files[: config.MAX_FILES]

    if files:
        head, clear = st.columns([5, 1])
        head.markdown(f"**Workspace: {len(files)} file(s)**"
                      + (f" and {len(template_sources)} template file(s)" if template_sources else ""))
        clear.button("Clear all", key="clear_all", on_click=_clear_all)
        html(f'<div class="cg-card">{ui.files_table(files)}</div>')
        extras = st.session_state["extras"]
        if extras:
            with st.expander("Remove pasted or sample files"):
                for i, e in enumerate(extras):
                    r1, r2 = st.columns([5, 1])
                    r1.write(f"{e.name} ({e.origin})")
                    r2.button("Remove", key=f"rm_{i}_{e.sha256[:8]}",
                              on_click=_remove_extra, args=(i,))

    settings = _settings_panel()

    if len(files) < 2:
        st.info("Add at least two files to start. You can upload them, paste snippets, "
                "or load the sample files.")
        if st.session_state["analysis"]:
            render_results(st.session_state["analysis"])
        return

    names = [f.name for f in files]
    st.markdown("#### Choose what to compare")
    mode_label = st.radio("Scope", ["Selected pair", "All pairs"], horizontal=True, key="scope",
                          help="All pairs compares every file with every other file and "
                               "ranks the most similar pairs.")
    c1, c2 = st.columns(2)
    if st.session_state.get("pick_a") not in names:
        st.session_state["pick_a"] = names[0]
    if st.session_state.get("pick_b") not in names:
        st.session_state["pick_b"] = names[1]
    a = c1.selectbox("Source code A", names, key="pick_a")
    b = c2.selectbox("Source code B", names, key="pick_b")
    save_copy = st.checkbox("Save report copies in the reports/ folder", value=True, key="save_copy")

    mode = "all" if mode_label == "All pairs" else "pair"
    invalid = mode == "pair" and a == b
    if invalid:
        st.warning("Pick two different files for A and B.")
    if mode == "all":
        n = len(files)
        st.caption(f"{n * (n - 1) // 2} pair(s) will be compared.")

    if st.button("Analyze Similarity", type="primary", key="analyze", disabled=invalid):
        if mode == "all":
            a, b = names[0], names[1]
        try:
            run_analysis(files, mode, a, b, settings, save_copy, templates=template_sources)
        except Exception as exc:       # never lose the layout because of one failure
            st.error(f"The analysis failed: {type(exc).__name__}: {exc}")

    if st.session_state["analysis"]:
        render_results(st.session_state["analysis"])
