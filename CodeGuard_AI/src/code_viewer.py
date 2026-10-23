"""Syntax-highlighted, line-numbered code panels with match highlighting.

Output is a single-line HTML string (no blank lines), which keeps Streamlit's
Markdown renderer from breaking the markup.
"""
from __future__ import annotations

from html import escape
from typing import Optional

import config
from src.models import MatchBlock, SourceFile

try:
    from pygments.lexers import get_lexer_by_name
    from pygments.token import Token
    _HAS_PYGMENTS = True
except ImportError:  # pragma: no cover
    _HAS_PYGMENTS = False

_LEXER_NAMES = {"python": "python", "java": "java", "c": "c",
                "cpp": "cpp", "javascript": "javascript"}


def _css_class(ttype) -> str:
    if ttype in Token.Comment:
        return "t-c"
    if ttype in Token.Literal.String:
        return "t-s"
    if ttype in Token.Literal.Number:
        return "t-n"
    if ttype in Token.Keyword:
        return "t-k"
    if ttype in Token.Name.Function or ttype in Token.Name.Class:
        return "t-f"
    if ttype in Token.Name.Decorator or ttype in Token.Name.Builtin:
        return "t-b"
    if ttype in Token.Operator:
        return "t-o"
    return ""


def _span(text: str, cls: str) -> str:
    safe = escape(text)
    return f'<span class="{cls}">{safe}</span>' if cls else safe


def highlight_lines(code: str, language: str) -> list:
    """Return one HTML fragment per source line."""
    code = code.expandtabs(4)
    n_lines = len(code.split("\n"))
    if code.endswith("\n"):
        n_lines -= 1
    n_lines = max(n_lines, 1)
    lines: list = []
    try:
        if not _HAS_PYGMENTS:
            raise RuntimeError("pygments missing")
        lexer = get_lexer_by_name(_LEXER_NAMES[language])
        current: list = []
        for ttype, value in lexer.get_tokens(code):
            cls = _css_class(ttype)
            parts = value.split("\n")
            for idx, part in enumerate(parts):
                if idx > 0:
                    lines.append("".join(current))
                    current = []
                if part:
                    current.append(_span(part, cls))
        lines.append("".join(current))
    except Exception:
        lines = [escape(l) for l in code.split("\n")]
    lines = lines[:n_lines] + [""] * max(0, n_lines - len(lines))
    return lines


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def block_color(block_id: int) -> str:
    return config.BLOCK_COLORS[(block_id - 1) % len(config.BLOCK_COLORS)]


def line_block_map(blocks: list, side: str) -> dict:
    """Map line number -> block for side 'a' or 'b'."""
    mapping = {}
    for blk in blocks:
        start, end = ((blk.a_start, blk.a_end) if side == "a"
                      else (blk.b_start, blk.b_end))
        for ln in range(start, end + 1):
            mapping[ln] = blk
    return mapping


def code_panel_html(source: SourceFile, side: str, blocks: list,
                    focus_block: Optional[int] = None, title: str = "") -> str:
    """Build the full panel (header + scrollable code)."""
    mapping = line_block_map(blocks, side)
    rows = []
    for number, frag in enumerate(highlight_lines(source.content, source.language), 1):
        blk: Optional[MatchBlock] = mapping.get(number)
        if blk is not None and (focus_block is None or blk.id == focus_block):
            color = block_color(blk.id)
            other = (f"B lines {blk.b_start}-{blk.b_end}" if side == "a"
                     else f"A lines {blk.a_start}-{blk.a_end}")
            tip = escape(f"Section {blk.id} ({blk.kind}) matches {other}")
            style = (f' style="background:{_rgba(color, 0.2)};'
                     f'box-shadow:inset 4px 0 0 {color}" title="{tip}"')
        else:
            style = ""
        rows.append(f'<div class="cg-row"{style}><span class="cg-ln">{number}</span>'
                    f'<span class="cg-src">{frag or "&nbsp;"}</span></div>')
    label = escape(config.LANGUAGE_LABELS.get(source.language, source.language))
    head = (f'<div class="cg-panel-head"><b>{escape(title or source.name)}</b>'
            f'<span>{label}, {source.line_count} lines</span></div>')
    return (f'<div class="cg-panel">{head}<div class="cg-code" tabindex="0" '
            f'aria-label="Source code of {escape(source.name)}">{"".join(rows)}</div></div>')
