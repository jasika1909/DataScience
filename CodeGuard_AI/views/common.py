"""Helpers shared by all views."""
from __future__ import annotations

import streamlit as st

import config
from config import Settings
from src import database as db
from src.report_generator import pdf_available, pdf_report


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def goto(page: str) -> None:
    st.session_state["page"] = page


def current_user():
    return st.session_state.get("user")


def owner_id():
    user = current_user()
    return user.id if user else None


def get_settings() -> Settings:
    if "settings" not in st.session_state:
        st.session_state["settings"] = Settings()
    return st.session_state["settings"]


def safe_db(func, *args, default=None, quiet: bool = False, **kwargs):
    """Run a database call; show a warning instead of crashing the page."""
    try:
        return func(*args, **kwargs)
    except db.DatabaseError as exc:
        if not quiet:
            st.warning(f"History database unavailable: {exc}")
        return default


def cached_pdf(results: list, sources: dict | None = None) -> bytes:
    """Generate a PDF once per distinct set of results."""
    cache = st.session_state.setdefault("_pdf_cache", {})
    key = (tuple((r.file_a, r.file_b, r.overall, r.matched_blocks, r.risk) for r in results),
           bool(sources))
    if key not in cache:
        if len(cache) > 8:
            cache.clear()
        cache[key] = pdf_report(list(results), sources=sources)
    return cache[key]


def download_row(results: list, stem: str, key: str, sources: dict | None = None) -> None:
    """CSV (summary + blocks) and PDF download buttons for ``results``."""
    from src.report_generator import blocks_csv, summary_csv

    c1, c2, c3 = st.columns(3)
    c1.download_button("Download summary CSV", summary_csv(results),
                       file_name=f"{stem}_summary.csv", mime="text/csv",
                       key=f"{key}_csv")
    c2.download_button("Download matched blocks CSV", blocks_csv(results),
                       file_name=f"{stem}_blocks.csv", mime="text/csv",
                       key=f"{key}_blocks")
    if pdf_available():
        try:
            c3.download_button("Download PDF report", cached_pdf(results, sources),
                               file_name=f"{stem}.pdf", mime="application/pdf",
                               key=f"{key}_pdf")
        except Exception as exc:  # keep page usable if PDF generation fails
            c3.warning(f"PDF could not be generated: {exc}")
    else:
        c3.info("Install reportlab to enable PDF reports.")
