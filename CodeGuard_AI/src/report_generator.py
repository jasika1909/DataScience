"""CSV and PDF reports. PDF output needs ``reportlab`` (listed in
requirements.txt); CSV works with the standard library only."""
from __future__ import annotations

import csv
import io
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from xml.sax.saxutils import escape

import config
from src.models import ComparisonResult

DISCLAIMER = (
    "Similarity scores are indicators for human review. They are not proof of "
    "plagiarism: shared assignment templates, common algorithms, boilerplate "
    "and short programs can all produce high scores, and copied code that was "
    "heavily restructured can score low."
)

try:  # optional at import time so CSV keeps working without reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, Preformatted,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)
    _HAS_REPORTLAB = True
except ImportError:  # pragma: no cover
    _HAS_REPORTLAB = False


def pdf_available() -> bool:
    return _HAS_REPORTLAB


def _safe(value) -> str:
    """Neutralise spreadsheet formula injection."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _pct(value) -> str:
    return "" if value is None else f"{value:.1f}"


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def summary_csv(results: Iterable[ComparisonResult]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["file_a", "file_b", "language_a", "language_b",
                "overall_similarity_pct", "risk_indicator",
                *[f"{k}_pct" for k in config.SIGNAL_KEYS],
                "matched_lines", "matched_blocks", "coverage_a_pct",
                "coverage_b_pct", "unique_lines_a", "unique_lines_b",
                "excluded_lines_a", "excluded_lines_b", "method", "reasons"])
    for r in results:
        w.writerow([_safe(r.file_a), _safe(r.file_b), r.language_a,
                    r.language_b, _pct(r.overall), r.risk,
                    *[_pct(r.signals.get(k)) for k in config.SIGNAL_KEYS],
                    r.matched_lines, r.matched_blocks, r.coverage_a,
                    r.coverage_b, r.unique_lines_a, r.unique_lines_b,
                    sum(v for k, v in r.excluded_a.items() if not k.startswith("imports")),
                    sum(v for k, v in r.excluded_b.items() if not k.startswith("imports")),
                    r.method, " | ".join(r.reasons)])
    return buf.getvalue().encode("utf-8-sig")


def blocks_csv(results: Iterable[ComparisonResult]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["file_a", "file_b", "block_id", "a_start_line", "a_end_line",
                "b_start_line", "b_end_line", "significant_lines",
                "token_identity_pct", "kind"])
    for r in results:
        for b in r.blocks:
            w.writerow([_safe(r.file_a), _safe(r.file_b), b.id, b.a_start,
                        b.a_end, b.b_start, b.b_end, b.lines,
                        _pct(b.similarity), b.kind])
    return buf.getvalue().encode("utf-8-sig")


def history_csv(rows: list) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["id", "created_at", "file_a", "file_b", "language_a", "language_b",
            "overall", "risk", "matched_lines", "matched_blocks", "method"]
    w.writerow(cols)
    for row in rows:
        w.writerow([_safe(row.get(c)) for c in cols])
    return buf.getvalue().encode("utf-8-sig")


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def _risk_color(risk: str):
    return colors.HexColor(config.RISK_COLORS.get(risk, "#94a3b8"))


def _p(text, style) -> "Paragraph":
    return Paragraph(escape(str(text)), style)


def _mix(hex_color: str, amount: float):
    """Blend a colour with white (amount 0 = white, 1 = full colour)."""
    c = colors.HexColor(hex_color)
    return colors.Color(1 - amount * (1 - c.red), 1 - amount * (1 - c.green),
                        1 - amount * (1 - c.blue))


def _heat(value: float):
    return _mix("#ef4444", min(1.0, max(0.0, value / 100.0)) * 0.85)


def _short(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "~"


def _risk_pie_and_histogram(results: list) -> "Drawing":
    d = Drawing(480, 150)
    counts = [sum(1 for r in results if r.risk == lvl) for lvl in config.RISK_LEVELS]
    if sum(counts):
        pie = Pie()
        pie.x, pie.y, pie.width, pie.height = 30, 25, 100, 100
        pie.data = [c for c in counts if c] or [1]
        pie.labels = [f"{lvl} ({c})" for lvl, c in zip(config.RISK_LEVELS, counts) if c]
        pie.sideLabels = True
        pie.simpleLabels = False
        pie.slices.strokeWidth = 0.5
        shown = [lvl for lvl, c in zip(config.RISK_LEVELS, counts) if c]
        for i, lvl in enumerate(shown):
            pie.slices[i].fillColor = _risk_color(lvl)
        d.add(pie)
    bins = [0] * 10
    for r in results:
        bins[min(9, int(r.overall // 10))] += 1
    bar = VerticalBarChart()
    bar.x, bar.y, bar.width, bar.height = 240, 30, 220, 95
    bar.data = [bins]
    bar.categoryAxis.categoryNames = [f"{10 * i}" for i in range(10)]
    bar.categoryAxis.labels.fontSize = 6
    bar.valueAxis.valueMin = 0
    bar.valueAxis.valueMax = max(max(bins), 1) + 1
    bar.valueAxis.valueStep = max(1, (max(bins) + 1) // 4)
    bar.valueAxis.labels.fontSize = 6
    bar.bars[0].fillColor = colors.HexColor("#3b82f6")
    d.add(bar)
    d.add(String(240, 135, "Similarity distribution (10% bins)", fontSize=7))
    d.add(String(30, 135, "Risk indicators", fontSize=7))
    return d


def _top_pairs_chart(results: list, n: int = 10) -> "Drawing":
    top = sorted(results, key=lambda r: r.overall, reverse=True)[:n]
    height = 28 + 16 * len(top)
    d = Drawing(480, height)
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 190, 15, 260, height - 28
    chart.data = [[r.overall for r in reversed(top)]]
    chart.categoryAxis.categoryNames = [
        _short(f"{r.file_a} / {r.file_b}", 38) for r in reversed(top)]
    chart.categoryAxis.labels.fontSize = 6
    chart.valueAxis.valueMin, chart.valueAxis.valueMax, chart.valueAxis.valueStep = 0, 100, 25
    chart.valueAxis.labels.fontSize = 6
    chart.bars[0].fillColor = colors.HexColor("#6366f1")
    for i, r in enumerate(reversed(top)):
        chart.bars[(0, i)].fillColor = _risk_color(r.risk)
    d.add(chart)
    d.add(String(190, height - 10, "Highest-similarity pairs (%)", fontSize=7))
    return d


def _signal_chart(r: ComparisonResult) -> "Drawing":
    keys = [k for k in config.SIGNAL_KEYS if r.signals.get(k) is not None]
    height = 22 + 14 * len(keys)
    d = Drawing(420, height)
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 140, 8, 250, height - 16
    chart.data = [[r.signals[k] for k in reversed(keys)]]
    chart.categoryAxis.categoryNames = [config.SIGNAL_LABELS[k] for k in reversed(keys)]
    chart.categoryAxis.labels.fontSize = 6.5
    chart.valueAxis.valueMin, chart.valueAxis.valueMax, chart.valueAxis.valueStep = 0, 100, 25
    chart.valueAxis.labels.fontSize = 6
    chart.bars[0].fillColor = colors.HexColor("#6366f1")
    d.add(chart)
    return d


def _matrix_table(results: list, small, max_files: int = 24):
    from src.batch import cluster_order, similarity_matrix
    names = sorted({n for r in results for n in (r.file_a, r.file_b)})
    if len(names) < 3 or len(names) > max_files:
        return None
    order = cluster_order(names, results)
    z = similarity_matrix(order, results)
    rows = [[""] + [str(i + 1) for i in range(len(order))]]
    for i, n in enumerate(order):
        rows.append([str(i + 1)] + [("-" if z[i][j] is None or i == j else f"{z[i][j]:.0f}")
                                     for j in range(len(order))])
    cell = max(6.0, min(11.0, 170.0 / (len(order) + 1)))
    table = Table(rows, colWidths=[cell * mm] * (len(order) + 1))
    style = [("FONTSIZE", (0, 0), (-1, -1), 5.5), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.white),
             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
             ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#dbeafe"))]
    for i in range(len(order)):
        for j in range(len(order)):
            if i != j and z[i][j] is not None:
                style.append(("BACKGROUND", (j + 1, i + 1), (j + 1, i + 1), _heat(z[i][j])))
    table.setStyle(TableStyle(style))
    legend = Table([[_p(f"{i + 1}", small), _p(n, small)] for i, n in enumerate(order)],
                   colWidths=[7 * mm, 70 * mm])
    legend.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 6),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return table, legend


def _snippet_table(src_a, src_b, block, code_style, small, max_lines: int):
    la = src_a.content.split("\n")
    lb = src_b.content.split("\n")
    ra = list(range(block.a_start, block.a_end + 1))
    rb = list(range(block.b_start, block.b_end + 1))
    n = max(len(ra), len(rb))
    shown = min(n, max_lines)
    rows = []
    for k in range(shown):
        a_no = ra[k] if k < len(ra) else ""
        b_no = rb[k] if k < len(rb) else ""
        a_txt = la[a_no - 1].expandtabs(4) if a_no and a_no <= len(la) else ""
        b_txt = lb[b_no - 1].expandtabs(4) if b_no and b_no <= len(lb) else ""
        rows.append([_p(a_no, small), Preformatted(a_txt[:60], code_style),
                     _p(b_no, small), Preformatted(b_txt[:60], code_style)])
    if n > shown:
        rows.append([_p("", small), _p(f"... {n - shown} more line(s)", small),
                     _p("", small), _p(f"... {n - shown} more line(s)", small)])
    color = config.BLOCK_COLORS[(block.id - 1) % len(config.BLOCK_COLORS)]
    t = Table(rows, colWidths=[8 * mm, 78 * mm, 8 * mm, 78 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _mix(color, 0.22)),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(color)),
        ("LINEBEFORE", (2, 0), (2, -1), 2.5, colors.HexColor(color)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return t


def _range_text(ranges: list, limit: int = 12) -> str:
    if not ranges:
        return "none"
    parts = [f"{a}-{b}" if a != b else str(a) for a, b in ranges[:limit]]
    more = f" (+{len(ranges) - limit} more)" if len(ranges) > limit else ""
    return ", ".join(parts) + more


def pdf_report(results: list, title: str = "Code Similarity Report",
               sources: Optional[dict] = None, max_detail_pairs: int = 25,
               snippet_blocks: int = 4, snippet_lines: int = 12) -> bytes:
    """Build the PDF.

    ``sources`` maps file name -> SourceFile and enables matched-code snippets;
    without it (for example reports rebuilt from stored history, which keeps no
    source code) the report lists line numbers only.
    """
    if not _HAS_REPORTLAB:
        raise RuntimeError("PDF reports need the 'reportlab' package "
                           "(pip install reportlab).")
    from src.batch import summarize
    sources = sources or {}
    results = sorted(results, key=lambda r: r.overall, reverse=True)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=colors.HexColor("#0b1736"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor("#1e3a8a"))
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], textColor=colors.HexColor("#4c1d95"))
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10)
    bullet = ParagraphStyle("bullet", parent=small, leftIndent=10, bulletIndent=0)
    code = ParagraphStyle("code", parent=small, fontName="Courier", fontSize=6.5, leading=8)
    note = ParagraphStyle("note", parent=body, textColor=colors.HexColor("#92400e"),
                          backColor=colors.HexColor("#fef3c7"), borderPadding=6)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title, author=config.APP_NAME,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    info = summarize(results)
    story = [
        _p(f"{config.APP_NAME}: {title}", h1),
        _p(f"Generated {datetime.now():%Y-%m-%d %H:%M}. {len(results)} pair(s) compared.", small),
        Spacer(1, 6), _p(DISCLAIMER, note), Spacer(1, 10),
        _p("Analysis summary", h2), _p(info["text"], body), Spacer(1, 6),
    ]
    if results:
        story += [_risk_pie_and_histogram(results)]
        if len(results) > 1:
            story += [_top_pairs_chart(results)]
        matrix = _matrix_table(results, small)
        if matrix:
            story += [_p("Similarity heatmap (darker red = higher similarity)", h3),
                      matrix[0], Spacer(1, 4), matrix[1], Spacer(1, 8)]

    head = [_p(h, small) for h in ("File A", "File B", "Overall", "Risk indicator",
                                   "Matched lines", "Blocks")]
    rows = [head]
    for r in results:
        rows.append([_p(r.file_a, small), _p(r.file_b, small),
                     _p(f"{r.overall:.1f}%", small), _p(r.risk, small),
                     _p(r.matched_lines, small), _p(r.matched_blocks, small)])
    story.append(_p("Ranking", h2))
    table = Table(rows, colWidths=[48 * mm, 48 * mm, 20 * mm, 24 * mm, 20 * mm, 14 * mm],
                  repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
             ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#94a3b8")),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, r in enumerate(results, start=1):
        style.append(("BACKGROUND", (3, i), (3, i), _risk_color(r.risk)))
    table.setStyle(TableStyle(style))
    story += [table, PageBreak()]

    for r in results[:max_detail_pairs]:
        block = [_p(f"{r.file_a}  vs  {r.file_b}", h2)]
        score = Table([[_p(f"{r.overall:.1f}%", ParagraphStyle(
            "score", parent=h1, fontSize=20, leading=22, textColor=colors.white)),
            _p(f"{r.risk} similarity indicator. {r.matched_lines} matching line(s) in "
               f"{r.matched_blocks} block(s). Coverage: A {r.coverage_a}%, B {r.coverage_b}%.", small)]],
            colWidths=[32 * mm, 138 * mm])
        score.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), _risk_color(r.risk)),
                                   ("ALIGN", (0, 0), (0, 0), "CENTER"),
                                   ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8"))]))
        block += [score, Spacer(1, 4),
                  _p(f"Method: {r.method}. {r.method_note}", small), Spacer(1, 4)]
        story += block
        if r.reasons:
            story.append(_p("Why this score", h3))
            for reason in r.reasons:
                story.append(Paragraph(escape(reason), bullet, bulletText="-"))
            story.append(Spacer(1, 4))
        story.append(_signal_chart(r))
        sig_rows = [[_p("Signal", small), _p("Score", small), _p("Weight", small)]]
        for k in config.SIGNAL_KEYS:
            v = r.signals.get(k)
            wgt = r.weights_used.get(k)
            sig_rows.append([_p(config.SIGNAL_LABELS[k], small),
                             _p("n/a" if v is None else f"{v:.1f}%", small),
                             _p("-" if wgt is None else f"{100 * wgt:.0f}%", small)])
        st = Table(sig_rows, colWidths=[70 * mm, 25 * mm, 25 * mm])
        st.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
                                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#94a3b8"))]))
        story += [Spacer(1, 4), st, Spacer(1, 6)]

        if r.blocks:
            brow = [[_p(h, small) for h in ("#", "Lines in A", "Lines in B", "Comparable lines",
                                            "Token identity", "Kind")]]
            for b in r.blocks[:60]:
                brow.append([_p(b.id, small), _p(f"{b.a_start}-{b.a_end}", small),
                             _p(f"{b.b_start}-{b.b_end}", small), _p(b.lines, small),
                             _p(f"{b.similarity:.1f}%", small), _p(b.kind, small)])
            bt = Table(brow, colWidths=[10 * mm, 28 * mm, 28 * mm, 30 * mm, 28 * mm, 26 * mm],
                       repeatRows=1)
            bt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#94a3b8"))]))
            story += [_p("Matched blocks", h3), bt,
                      _p("Token identity compares literal tokens. Blocks of kind 'semantic' "
                         "match by canonical logic form (equivalent steps written differently, "
                         "possibly in another language), so a low token identity is expected "
                         "for them.", small), Spacer(1, 6)]
            src_a, src_b = sources.get(r.file_a), sources.get(r.file_b)
            if src_a and src_b:
                story.append(_p("Matched code snippets (A on the left, B on the right)", h3))
                for b in sorted(r.blocks, key=lambda x: x.lines, reverse=True)[:snippet_blocks]:
                    story.append(KeepTogether([
                        _p(f"Section {b.id}: {b.kind}, {b.lines} lines, token identity "
                           f"{b.similarity:.0f}%", small),
                        _snippet_table(src_a, src_b, b, code, small, snippet_lines),
                        Spacer(1, 5)]))
            else:
                story.append(_p("Code snippets are not included because source code is "
                                "not stored in the history database.", small))
        if r.function_matches:
            frow = [[_p(h, small) for h in ("Function in A", "Lines", "Function in B",
                                            "Lines", "Structure match")]]
            for f in r.function_matches[:40]:
                frow.append([_p(f.name_a, small), _p(f"{f.a_start}-{f.a_end}", small),
                             _p(f.name_b, small), _p(f"{f.b_start}-{f.b_end}", small),
                             _p(f"{f.similarity:.1f}%", small)])
            ft = Table(frow, colWidths=[40 * mm, 24 * mm, 40 * mm, 24 * mm, 30 * mm])
            ft.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcfce7")),
                                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#94a3b8"))]))
            story += [_p("Functions with matching syntax-tree structure", h3), ft, Spacer(1, 6)]

        story += [_p("Unique code (no match in the other file)", h3),
                  _p(f"A: {r.unique_lines_a} comparable line(s) in ranges "
                     f"{_range_text(r.unique_ranges_a)}.", small),
                  _p(f"B: {r.unique_lines_b} comparable line(s) in ranges "
                     f"{_range_text(r.unique_ranges_b)}.", small)]
        excl = []
        for label, side in (("A", r.excluded_a), ("B", r.excluded_b)):
            if side:
                excl.append(f"{label}: " + ", ".join(f"{v} {k}" for k, v in side.items()))
        if excl:
            story.append(_p("Ignored as non-evidence: " + "; ".join(excl) + ".", small))
        for warning in r.warnings:
            story.append(_p("Note: " + warning, small))
        story.append(PageBreak())
    if len(results) > max_detail_pairs:
        story.append(_p(f"Details are shown for the top {max_detail_pairs} pairs; "
                        "see the CSV export for all pairs.", small))

    story += [_p("Methodology and limitations", h2)]
    for k in config.SIGNAL_KEYS:
        story.append(_p(f"{config.SIGNAL_LABELS[k]}: {config.SIGNAL_DESCRIPTIONS[k]}", small))
    story += [
        Spacer(1, 4),
        _p("The overall score is a weighted mean of the available signals; weights are "
           "configurable and re-normalized when a signal does not apply. Risk levels use "
           "configurable thresholds and are not universally valid cut-offs. Comments, "
           "whitespace, import lines, brace-only lines, standard boilerplate, instructor "
           "template code and lines common to most submissions are excluded. Java, C, C++ "
           "and JavaScript structure comes from a lightweight parser, and the semantic "
           "signal is a rule-based model, not a neural network. No automated method can "
           "detect every form of plagiarism.", small),
    ]
    doc.build(story)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Saving to the reports/ folder
# --------------------------------------------------------------------------- #
def save_report(data: bytes, stem: str, extension: str,
                directory: Optional[Path] = None) -> Path:
    directory = Path(directory or config.REPORTS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w\-]+", "_", stem).strip("_")[:50] or "report"
    path = directory / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.{extension.lstrip('.')}"
    path.write_bytes(data)
    return path


def list_reports(directory: Optional[Path] = None, limit: int = 30) -> list:
    directory = Path(directory or config.REPORTS_DIR)
    if not directory.exists():
        return []
    files = [p for p in directory.iterdir() if p.suffix in (".csv", ".pdf")]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def user_reports_dir(user_id: Optional[int]) -> Path:
    """Each account saves its reports in its own folder."""
    return config.REPORTS_DIR / (f"user_{int(user_id)}" if user_id is not None else "shared")


def secure_delete_file(path: Path) -> None:
    """Overwrite a file with zeros before removing it (best effort)."""
    path = Path(path)
    try:
        size = path.stat().st_size
        with open(path, "r+b") as handle:
            handle.write(b"\x00" * size)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        pass
    try:
        path.unlink()
    except OSError:
        pass


def delete_user_reports(user_id: Optional[int]) -> int:
    """Delete every saved report of a user. Returns the number of files removed."""
    directory = user_reports_dir(user_id)
    count = 0
    if directory.exists():
        for p in list(directory.iterdir()):
            if p.is_file():
                secure_delete_file(p)
                count += 1
        try:
            directory.rmdir()
        except OSError:
            pass
    return count
