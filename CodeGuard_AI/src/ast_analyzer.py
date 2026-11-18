"""Structural comparison of Python code using the standard ``ast`` module.

The code is only *parsed* (never compiled or executed). Names, literal values
and docstrings are ignored, so renamed variables or reformatted code produce
the same structure.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass, field

import config
from src.models import FunctionMatch


@dataclass
class FuncInfo:
    name: str
    start: int
    end: int
    seq: tuple
    digest: int
    grams: Counter = field(default_factory=Counter)


@dataclass
class AstInfo:
    ok: bool
    reason: str = ""
    ngrams: Counter = field(default_factory=Counter)
    node_count: int = 0
    functions: list = field(default_factory=list)


@dataclass
class AstResult:
    available: bool
    score: float | None = None
    reason: str = ""
    function_matches: list = field(default_factory=list)


_EQUIVALENT = {
    "AugAssign": "Assign", "AnnAssign": "Assign",
    "For": "Loop", "AsyncFor": "Loop", "While": "Loop",
    "ListComp": "Comp", "SetComp": "Comp", "GeneratorExp": "Comp",
    "DictComp": "Comp",
}


def _label(node: ast.AST) -> str:
    """Node type with equivalent constructs unified (e.g. for/while -> Loop)."""
    if isinstance(node, ast.Constant):
        return "Constant:" + type(node.value).__name__
    name = type(node).__name__
    return _EQUIVALENT.get(name, name)


def _strip_docstrings(tree: ast.AST) -> None:
    holders = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for node in ast.walk(tree):
        if isinstance(node, holders) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]


def _sequence(root: ast.AST) -> tuple:
    """Pre-order node-type sequence (iterative, so deep trees are safe)."""
    seq = []
    stack = [root]
    while stack:
        node = stack.pop()
        seq.append(_label(node))
        children = [c for c in ast.iter_child_nodes(node)
                    if not isinstance(c, ast.expr_context)]
        stack.extend(reversed(children))
    return tuple(seq)


def _ngrams(seq: tuple, n: int = 3) -> Counter:
    if len(seq) < n:
        return Counter([seq]) if seq else Counter()
    return Counter(seq[i:i + n] for i in range(len(seq) - n + 1))


def _dice(a: Counter, b: Counter) -> float:
    total = sum(a.values()) + sum(b.values())
    if not total:
        return 0.0
    return 2.0 * sum((a & b).values()) / total


def build_info(code: str) -> AstInfo:
    """Parse ``code`` and extract structure; never raises."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return AstInfo(False, f"Python syntax error on line {exc.lineno}")
    except (ValueError, RecursionError, MemoryError):
        return AstInfo(False, "The file could not be parsed as Python")
    try:
        _strip_docstrings(tree)
        seq = _sequence(tree)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fseq = _sequence(node)
                functions.append(FuncInfo(
                    name=node.name,
                    start=node.lineno,
                    end=getattr(node, "end_lineno", node.lineno),
                    seq=fseq,
                    digest=hash(fseq),
                    grams=_ngrams(fseq),
                ))
    except RecursionError:
        return AstInfo(False, "The syntax tree is too deeply nested")
    functions.sort(key=lambda f: len(f.seq), reverse=True)
    return AstInfo(True, "", _ngrams(seq), len(seq),
                   functions[: config.AST_MAX_FUNCTIONS])


def _similarity(a: FuncInfo, b: FuncInfo) -> float:
    """Structure similarity of two functions (0-1), linear time.

    Identical node sequences score 1.0; otherwise the Dice overlap of the
    node-type trigrams is used. Pairs whose sizes differ too much cannot reach
    the match threshold and are skipped without any comparison.
    """
    if a.digest == b.digest and a.seq == b.seq:
        return 1.0
    la, lb = len(a.seq), len(b.seq)
    if 2.0 * min(la, lb) / (la + lb) < config.AST_FUNCTION_THRESHOLD:
        return 0.0
    return _dice(a.grams, b.grams)


def compare_info(a: AstInfo, b: AstInfo) -> AstResult:
    if not a.ok or not b.ok:
        reasons = [r for r in (a.reason, b.reason) if r]
        return AstResult(False, None, "; ".join(reasons) or "AST unavailable")
    score = round(100.0 * _dice(a.ngrams, b.ngrams), 1)
    candidates = []
    for fa in a.functions:
        if len(fa.seq) < config.AST_MIN_FUNCTION_NODES:
            continue
        for fb in b.functions:
            if len(fb.seq) < config.AST_MIN_FUNCTION_NODES:
                continue
            sim = _similarity(fa, fb)
            if sim >= config.AST_FUNCTION_THRESHOLD:
                candidates.append((sim, fa, fb))
    candidates.sort(key=lambda c: c[0], reverse=True)
    used_a, used_b, matches = set(), set(), []
    for sim, fa, fb in candidates:
        ka, kb = (fa.name, fa.start), (fb.name, fb.start)
        if ka in used_a or kb in used_b:
            continue
        used_a.add(ka)
        used_b.add(kb)
        matches.append(FunctionMatch(fa.name, fa.start, fa.end, fb.name,
                                     fb.start, fb.end, round(100 * sim, 1)))
    matches.sort(key=lambda m: m.a_start)
    return AstResult(True, score, "", matches)
