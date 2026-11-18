"""About page: methods, limitations and responsible use."""
from __future__ import annotations

import streamlit as st

import config
from views.common import html


def render() -> None:
    html('<div class="cg-page-title">About CodeGuard AI</div>'
         f'<div class="cg-lead">Version {config.APP_VERSION}. A local tool that helps '
         'teachers, students and developers spot code that may have been copied.</div>')

    st.markdown("### Responsible use")
    st.markdown(
        "Similarity scores are **indicators for human review**. A high score can come "
        "from a shared assignment template, a standard algorithm or a very short "
        "program. A low score does not prove originality, because copied code can be "
        "restructured. Always read the highlighted sections before drawing a conclusion.")

    st.markdown("### Methods")
    for key in config.SIGNAL_KEYS:
        st.markdown(f"**{config.SIGNAL_LABELS[key]}.** {config.SIGNAL_DESCRIPTIONS[key]}")
    st.markdown(
        "The overall score is a weighted mean of the available signals. Weights are "
        "configurable and re-normalized when a signal does not apply (for example, AST "
        "analysis for non-Python files).")

    st.markdown("### False-positive reduction")
    st.markdown(
        "Before scoring, CodeGuard ignores comments, whitespace, imports, brace-only "
        "lines, standard boilerplate (entry points, standard input set-up, plain "
        "constructors and accessors), lines from an optional instructor template, and, "
        f"in batches of {config.COMMON_MIN_FILES} or more files, lines that appear in "
        f"{int(config.COMMON_FRACTION * 100)}% or more of them. Every report lists what was "
        "excluded. The common-code filter can hide a real copy if most of a class "
        "copied the same lines, so prefer an instructor template when you have one.")

    st.markdown("### Known limitations")
    st.markdown(
        "- Java, C, C++ and JavaScript use a lexical tokenizer and a lightweight "
        "statement-level parser, not a full compiler grammar. JavaScript regular-"
        "expression literals and C++ digit separators are not specially handled.\n"
        "- The semantic signal is rule-based and offline. It is not a neural network and "
        "cannot prove two programs are equivalent.\n"
        "- Cross-language comparisons are supported but flagged as less meaningful.\n"
        "- Code that is re-implemented with different logic, or split across many "
        "small edits, can evade detection.\n"
        "- Comments, whitespace, import lines and brace-only lines are ignored, so "
        "matches limited to those are not counted.\n"
        "- Matched blocks need a minimum number of consecutive significant lines "
        "(default 3, configurable).")

    st.markdown("### Accounts and security")
    st.markdown(
        "- Teachers and students sign in with PBKDF2-HMAC-SHA256 hashed passwords; "
        "repeated failures lock the account for a few minutes; sessions expire after "
        f"{config.SESSION_TIMEOUT_MIN} minutes of inactivity.\n"
        "- Access control is enforced in the server code: students see only their own "
        "submissions, teachers only their own assignments and students.\n"
        "- Submissions, comparison history and reports can be deleted; deleted database "
        "content is overwritten and the database is compacted.\n"
        "- The database file is not encrypted at rest. Use disk encryption (for example "
        "BitLocker) on shared computers, and HTTPS if you host the app for a class.")

    st.markdown("### Privacy and limits")
    st.markdown(
        f"- Files never leave this computer; no API keys, accounts or network calls "
        "are used, and Streamlit usage statistics are disabled in `.streamlit/config.toml`.\n"
        "- Uploaded code is decoded as text and never imported or run.\n"
        "- History stores file names, content hashes and scores, not source code.\n"
        f"- Limits: {config.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB and "
        f"{config.MAX_LINES_PER_FILE:,} lines per file, up to {config.MAX_FILES} files, "
        f"extensions {', '.join(config.SUPPORTED_EXTENSIONS)}.")
