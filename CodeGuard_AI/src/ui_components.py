"""Reusable HTML fragments for the CodeGuard UI.

Every function returns a single-line HTML string and escapes user-supplied
text. Render them with ``st.markdown(html, unsafe_allow_html=True)``.
"""
from __future__ import annotations

import base64
from html import escape

import config
from src.code_viewer import block_color
from src.models import ComparisonResult


def read_asset(name: str) -> str:
    try:
        return (config.ASSETS_DIR / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def stylesheet() -> str:
    css = read_asset("styles.css")
    return f"<style>{css}</style>"


def brand_html(user=None) -> str:
    svg = read_asset("logo.svg")
    chip = ""
    if user is not None:
        chip = (f'<div class="cg-sub">Signed in as <b>{escape(user.display_name)}</b> '
                f'<span class="cg-tag">{escape(user.role)}</span></div>')
    return (f'<div class="cg-brand">{svg.replace(chr(10), " ")}<div>'
            f'<div class="cg-title">{escape(config.APP_NAME.upper())}</div>'
            f'<div class="cg-sub">{escape(config.APP_TAGLINE)}</div>{chip}</div></div>')


def logo_data_uri() -> str:
    svg = read_asset("logo.svg").encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")


def risk_color(risk: str) -> str:
    return config.RISK_COLORS.get(risk, "#94a3b8")


def risk_badge(risk: str, text: str = "") -> str:
    label = text or f"{risk} similarity indicator"
    return f'<span class="cg-badge" style="--c:{risk_color(risk)}">{escape(label)}</span>'


def score_ring(result: ComparisonResult) -> str:
    pct = max(0.0, min(100.0, result.overall))
    return (
        '<div class="cg-ring-wrap">'
        f'<div class="cg-ring" style="--pct:{pct};--ring:{risk_color(result.risk)}" '
        f'role="img" aria-label="Overall similarity {pct:.1f} percent">'
        f'<div class="cg-ring-inner"><span class="cg-ring-val">{pct:.1f}%</span>'
        '<span class="cg-ring-lbl">overall similarity</span></div></div>'
        f'{risk_badge(result.risk)}</div>'
    )


def stat_tiles(items: list) -> str:
    """items: [(value, label), ...]"""
    tiles = "".join(f'<div class="cg-stat"><b>{escape(str(v))}</b><span>{escape(l)}</span></div>'
                    for v, l in items)
    return f'<div class="cg-stats">{tiles}</div>'


def metric_card(value, label: str, tone: str = "") -> str:
    return (f'<div class="cg-metric {tone}"><b>{escape(str(value))}</b>'
            f'<span>{escape(label)}</span></div>')


def signal_bars(result: ComparisonResult) -> str:
    rows = []
    for key in config.SIGNAL_KEYS:
        value = result.signals.get(key)
        label = escape(config.SIGNAL_LABELS[key])
        if value is None:
            rows.append(f'<div class="cg-sig"><div class="cg-sig-top"><span>{label}</span>'
                        '<span>not applicable</span></div></div>')
            continue
        rows.append(
            f'<div class="cg-sig"><div class="cg-sig-top"><span>{label}</span>'
            f'<span>{value:.1f}%</span></div>'
            f'<div class="cg-bar"><i style="width:{max(0.0, min(100.0, value))}%"></i></div></div>')
    return "".join(rows)


def match_list(result: ComparisonResult) -> str:
    if not result.blocks:
        return ('<div class="cg-empty">No matching blocks of '
                f'{result.thresholds.get("min_block_lines", config.DEFAULT_MIN_BLOCK_LINES)}'
                ' or more lines were found.</div>')
    items = []
    for b in result.blocks:
        items.append(
            f'<div class="cg-match"><span class="cg-swatch" style="background:{block_color(b.id)}"></span>'
            f'<div class="cg-match-body"><b>Section {b.id}</b>'
            f'<span class="cg-tag">{escape(b.kind)}</span>'
            f'<small>A lines {b.a_start}-{b.a_end}, B lines {b.b_start}-{b.b_end} '
            f'({b.lines} significant lines)</small></div>'
            + ('<span class="cg-pct" style="font-size:.78rem" title="Matched by canonical '
               'logic form, not by identical tokens">equivalent</span>' if b.kind == "semantic"
               else f'<span class="cg-pct">{b.similarity:.0f}%</span>') + '</div>')
    return f'<div class="cg-list-scroll">{"".join(items)}</div>'


def function_match_list(result: ComparisonResult) -> str:
    if not result.function_matches:
        return ""
    items = []
    for f in result.function_matches:
        items.append(
            '<div class="cg-match"><div class="cg-match-body">'
            f'<b>{escape(f.name_a)}</b> matches <b>{escape(f.name_b)}</b>'
            f'<small>A lines {f.a_start}-{f.a_end}, B lines {f.b_start}-{f.b_end}</small></div>'
            f'<span class="cg-pct">{f.similarity:.0f}%</span></div>')
    return f'<div class="cg-list-scroll">{"".join(items)}</div>'


def legend(result: ComparisonResult) -> str:
    if not result.blocks:
        return ""
    chips = "".join(f'<span><i style="background:{block_color(b.id)}"></i>Section {b.id}</span>'
                    for b in result.blocks[:24])
    return f'<div class="cg-legend">{chips}</div>'


def files_table(files: list, removable_note: str = "") -> str:
    rows = "".join(
        f'<tr><td>{escape(f.name)}</td><td>{escape(config.LANGUAGE_LABELS[f.language])}</td>'
        f'<td>{f.line_count}</td><td>{f.size_bytes / 1024:.1f} KB</td>'
        f'<td>{escape(f.origin)}</td></tr>' for f in files)
    return ('<table class="cg-files"><thead><tr><th>File</th><th>Language</th><th>Lines</th>'
            f'<th>Size</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table>')


def empty_state(title: str, text: str) -> str:
    return (f'<div class="cg-card"><div class="cg-h">{escape(title)}</div>'
            f'<div class="cg-muted">{escape(text)}</div></div>')


def bullets(items: list) -> str:
    """A safe HTML bullet list."""
    if not items:
        return ""
    lis = "".join(f"<li>{escape(str(i))}</li>" for i in items)
    return f'<ul class="cg-bullets">{lis}</ul>'


def ranges_text(ranges: list, limit: int = 20) -> str:
    if not ranges:
        return "none"
    parts = [f"{a}-{b}" if a != b else str(a) for a, b in ranges[:limit]]
    more = f" (+{len(ranges) - limit} more)" if len(ranges) > limit else ""
    return ", ".join(parts) + more


def excluded_table(result: ComparisonResult) -> str:
    reasons = sorted(set(result.excluded_a) | set(result.excluded_b))
    if not reasons:
        return ""
    rows = "".join(
        f'<tr><td>{escape(r)}</td><td>{result.excluded_a.get(r, 0)}</td>'
        f'<td>{result.excluded_b.get(r, 0)}</td></tr>' for r in reasons)
    return ('<table class="cg-files"><thead><tr><th>Ignored as non-evidence</th>'
            f'<th>Lines in A</th><th>Lines in B</th></tr></thead><tbody>{rows}</tbody></table>')
