"""Reports page: history, per-comparison downloads and saved report files."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from src import database as db
from src import report_generator as rg
from src import ui_components as ui
from views.common import current_user, download_row, goto, html, owner_id, safe_db


def render() -> None:
    html('<div class="cg-page-title">Reports</div>'
         '<div class="cg-lead">Browse earlier comparisons, download reports for any of '
         'them, and manage saved files.</div>')
    uid = owner_id()
    rows = safe_db(db.get_all, owner_id=uid, default=[]) or []

    tab_hist, tab_files = st.tabs(["Comparison history", "Saved report files"])

    with tab_hist:
        if not rows:
            st.info("No comparisons stored yet. Run an analysis first.")
            st.button("Compare code", type="primary", key="hist_go", on_click=goto,
                      args=("compare",))
        else:
            f1, f2 = st.columns([2, 3])
            risks = f1.multiselect("Indicator", list(config.RISK_LEVELS),
                                   default=list(config.RISK_LEVELS), key="hist_risk")
            query = f2.text_input("Search file names", key="hist_query").strip().lower()
            shown = [r for r in rows if r["risk"] in risks and
                     (not query or query in r["file_a"].lower() or query in r["file_b"].lower())]
            if not shown:
                st.warning("No comparisons match these filters.")
            else:
                df = pd.DataFrame(shown)[["id", "created_at", "file_a", "file_b", "overall",
                                          "risk", "matched_lines", "matched_blocks", "method"]]
                df.columns = ["ID", "When", "File A", "File B", "Similarity %",
                              "Indicator", "Matching lines", "Blocks", "Method"]
                st.dataframe(df, hide_index=True)
                st.download_button("Download history CSV", rg.history_csv(shown),
                                   file_name="codeguard_history.csv", mime="text/csv",
                                   key="hist_csv")

                st.markdown("#### Report for one comparison")
                ids = [r["id"] for r in shown]
                labels = {r["id"]: f'#{r["id"]}  {r["file_a"]} vs {r["file_b"]}  ({r["overall"]:.1f}%)'
                          for r in shown}
                chosen = st.selectbox("Comparison", ids, format_func=labels.get, key="hist_pick")
                result = safe_db(db.get_result, chosen, owner_id=uid, default=None)
                if result is None:
                    st.error("That comparison could not be loaded.")
                else:
                    st.caption(f"{result.method}. {result.method_note}")
                    html('<div class="cg-card"><div class="cg-h">Why this score</div>'
                         + ui.bullets(result.reasons)
                         + '</div>')
                    st.caption("Source code is not stored in history, so PDF reports rebuilt "
                               "from history list line numbers but no code snippets.")
                    download_row([result], f"codeguard_comparison_{chosen}", f"hist_{chosen}")
                    st.button("Delete this comparison", key=f"del_{chosen}",
                              on_click=lambda i=chosen: safe_db(db.delete_comparison, i, owner_id=uid))

            with st.expander("Clear all history"):
                st.warning("This permanently deletes every stored comparison.")
                if st.checkbox("I understand", key="clear_confirm"):
                    st.button("Delete all history", key="clear_hist",
                              on_click=lambda: safe_db(db.clear_history, owner_id=uid))

    with tab_files:
        files = rg.list_reports(rg.user_reports_dir(uid))
        if not files:
            st.info("No report files saved yet. Copies are saved to the reports folder "
                    "after each analysis when that option is on.")
        for i, path in enumerate(files):
            c1, c2 = st.columns([4, 1])
            c1.write(f"{path.name}  ({path.stat().st_size / 1024:.1f} KB)")
            try:
                data = path.read_bytes()
            except OSError as exc:
                c2.error(str(exc))
                continue
            mime = "application/pdf" if path.suffix == ".pdf" else "text/csv"
            c2.download_button("Download", data, file_name=path.name, mime=mime,
                               key=f"file_{i}_{path.name}")
