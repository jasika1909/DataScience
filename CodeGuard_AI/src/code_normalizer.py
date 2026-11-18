"""Tokenizing and normalizing source code.

A single regex-driven scanner handles Python, Java, C, C++ and JavaScript.
It removes comments, understands string literals and produces, per source
line, an *exact* normalized form (identifiers kept) and an *abstract* form
(identifiers, numbers and strings replaced by placeholders).

This is a lexical approach: it does not parse the languages (except Python,
see ``ast_analyzer``). JavaScript regex literals and C++ digit separators are
not specially handled.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

KEYWORDS = {
    "python": {
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
        "while", "with", "yield",
    },
    "java": {
        "abstract", "assert", "boolean", "break", "byte", "case", "catch",
        "char", "class", "continue", "default", "do", "double", "else",
        "enum", "extends", "final", "finally", "float", "for", "if",
        "implements", "import", "instanceof", "int", "interface", "long",
        "new", "package", "private", "protected", "public", "return",
        "short", "static", "super", "switch", "this", "throw", "throws",
        "try", "void", "while", "true", "false", "null",
    },
    "c": {
        "auto", "break", "case", "char", "const", "continue", "default", "do",
        "double", "else", "enum", "extern", "float", "for", "goto", "if",
        "int", "long", "register", "return", "short", "signed", "sizeof",
        "static", "struct", "switch", "typedef", "union", "unsigned", "void",
        "volatile", "while",
    },
    "cpp": {
        "auto", "bool", "break", "case", "catch", "char", "class", "const",
        "continue", "default", "delete", "do", "double", "else", "enum",
        "explicit", "false", "float", "for", "friend", "if", "inline", "int",
        "long", "namespace", "new", "nullptr", "operator", "private",
        "protected", "public", "return", "short", "signed", "sizeof",
        "static", "struct", "switch", "template", "this", "throw", "true",
        "try", "typedef", "typename", "union", "unsigned", "using", "virtual",
        "void", "while",
    },
    "javascript": {
        "async", "await", "break", "case", "catch", "class", "const",
        "continue", "default", "delete", "do", "else", "export", "extends",
        "false", "finally", "for", "function", "if", "import", "in",
        "instanceof", "let", "new", "null", "of", "return", "super",
        "switch", "this", "throw", "true", "try", "typeof", "undefined",
        "var", "void", "while", "yield",
    },
}

_OPERATORS = [
    "<<=", ">>=", "...", "===", "!==", "**=", "//=", "&&=", "||=", "??=",
    "==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=",
    "%=", "&=", "|=", "^=", "<<", ">>", "->", "=>", "::", "**", "//", ":=",
    "??", "?.",
]

# Lines made only of these values carry no information of their own.
_TRIVIAL_VALUES = {
    "{", "}", "(", ")", "[", "]", ";", ",", ":", "else", "try", "finally",
    "do", "pass", "break", "continue", "default",
}
_BOILERPLATE_FIRST = {
    "python": {"import", "from"},
    "java": {"import", "package"},
    "javascript": {"import"},
    "cpp": {"using"},
    "c": set(),
}
_C_DIRECTIVES = {"include", "pragma", "ifndef", "ifdef", "endif"}


@dataclass(frozen=True)
class Token:
    kind: str       # kw | id | num | str | op
    value: str
    line: int


@dataclass(frozen=True)
class NormalizedLine:
    number: int
    exact: str                  # identifiers kept
    abstract: str               # identifiers / literals replaced
    values: tuple               # concrete token values
    kinds: tuple                # token kinds, parallel to ``values``
    significant: bool           # False for braces, imports, docstrings ...


@dataclass
class NormalizedCode:
    language: str
    tokens: list
    lines: list

    @property
    def significant_lines(self) -> list:
        return [ln for ln in self.lines if ln.significant]


@lru_cache(maxsize=None)
def _pattern(language: str) -> re.Pattern:
    parts = []
    if language == "python":
        parts.append(r"(?P<comment>\#[^\n]*)")
        parts.append(
            r"(?P<tstr>(?:[rRbBuUfF]{1,2})?(?P<q>\"\"\"|''')[\s\S]*?(?:(?P=q)|\Z))"
        )
        parts.append(
            r"(?P<str>(?:[rRbBuUfF]{1,2})?(?:\"(?:\\.|[^\"\\\n])*\"?"
            r"|'(?:\\.|[^'\\\n])*'?))"
        )
    else:
        parts.append(r"(?P<comment>/\*[\s\S]*?(?:\*/|\Z)|//[^\n]*)")
        if language == "java":
            parts.append(r"(?P<tstr>\"\"\"[\s\S]*?(?:\"\"\"|\Z))")
        if language == "javascript":
            parts.append(r"(?P<tstr>`(?:\\[\s\S]|[^`\\])*`?)")
        parts.append(
            r"(?P<str>\"(?:\\.|[^\"\\\n])*\"?|'(?:\\.|[^'\\\n])*'?)"
        )
    parts.append(
        r"(?P<num>0[xX][0-9a-fA-F_]+[uUlL]*|0[bB][01_]+"
        r"|\d[\d_]*(?:\.\d*)?(?:[eE][+-]?\d+)?[fFdDlLuU]*"
        r"|\.\d+(?:[eE][+-]?\d+)?[fFdD]?)"
    )
    parts.append(r"(?P<id>(?:[^\W\d]|\$)[\w$]*)")
    ops = "|".join(re.escape(o) for o in sorted(_OPERATORS, key=len, reverse=True))
    parts.append(f"(?P<op>{ops})")
    parts.append(r"(?P<ws>\s+)")
    parts.append(r"(?P<other>\S)")
    return re.compile("|".join(parts))


def _string_value(text: str) -> str:
    """Quote-style independent string content, whitespace collapsed."""
    t = re.sub(r"^[rRbBuUfF]{1,2}(?=[\"'])", "", text)
    for q in ('"""', "'''"):
        if t.startswith(q):
            t = t[3:]
            t = t[:-3] if t.endswith(q) else t
            break
    else:
        if t[:1] in "\"'`":
            t = t[1:]
            if t[-1:] in "\"'`":
                t = t[:-1]
    return re.sub(r"\s+", " ", t).strip()[:80]


def tokenize(code: str, language: str) -> list:
    """Return code tokens (comments and whitespace removed)."""
    if language not in KEYWORDS:
        raise ValueError(f"Unsupported language: {language}")
    keywords = KEYWORDS[language]
    tokens = []
    line = 1
    for m in _pattern(language).finditer(code):
        kind = m.lastgroup
        text = m.group()
        if kind in ("comment", "ws"):
            pass
        elif kind in ("str", "tstr"):
            tokens.append(Token("str", _string_value(text), line))
        elif kind == "num":
            tokens.append(Token("num", text.replace("_", ""), line))
        elif kind == "id":
            tokens.append(Token("kw" if text in keywords else "id", text, line))
        else:
            tokens.append(Token("op", text, line))
        line += text.count("\n")
    return tokens


def _abstract(token: Token) -> str:
    if token.kind == "id":
        return "ID"
    if token.kind == "num":
        return "NUM"
    if token.kind == "str":
        return "STR"
    return token.value


def _is_significant(tokens: list, language: str) -> bool:
    values = [t.value for t in tokens]
    if all(t.kind in ("op", "kw") and t.value in _TRIVIAL_VALUES for t in tokens):
        return False
    if len(tokens) == 1 and tokens[0].kind == "str":      # docstring
        return False
    first = tokens[0]
    if first.kind == "kw" and first.value in _BOILERPLATE_FIRST.get(language, ()):
        return False
    if language in ("c", "cpp") and first.value == "#" and len(values) > 1:
        if values[1] in _C_DIRECTIVES:
            return False
    return True


def normalize(code: str, language: str) -> NormalizedCode:
    tokens = tokenize(code, language)
    by_line: dict = {}
    for tok in tokens:
        by_line.setdefault(tok.line, []).append(tok)
    lines = []
    for number in sorted(by_line):
        toks = by_line[number]
        values = tuple(t.value for t in toks)
        lines.append(
            NormalizedLine(
                number=number,
                exact=" ".join(values),
                abstract=" ".join(_abstract(t) for t in toks),
                values=values,
                kinds=tuple(t.kind for t in toks),
                significant=_is_significant(toks, language),
            )
        )
    return NormalizedCode(language=language, tokens=tokens, lines=lines)
