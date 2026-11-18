"""Semantic canonicalization (offline, rule-based).

Each code line is rewritten into a small language-neutral vocabulary so that
programs implementing the same steps compare as similar even when they use
different variable names, loop styles, assignment forms, or even a different
language:

* identifiers -> ID, numbers -> NUM, strings -> STR
* types, modifiers, ``this``/``self``, ``new`` are dropped
* ``i++``, ``i += 1`` and ``i = i + 1`` become the same tokens
* ``for``/``while``/``do`` -> LOOP; counting loops and ``range(n)`` -> LOOP RANGE ( n )
* for-each loops in Python, Java, C++ and JavaScript -> LOOP EACH ...
* print/println/printf/console.log -> OUT; len/size/length -> LEN;
  append/add/push/push_back -> APPEND, and so on
* method calls ``x.size()`` and function calls ``len(x)`` become ``LEN ( ID )``

It is a heuristic model, not a proof of equivalence.
"""
from __future__ import annotations

from src.code_normalizer import NormalizedLine

TYPE_WORDS = {
    "int", "long", "short", "byte", "char", "float", "double", "boolean",
    "bool", "void", "String", "string", "size_t", "auto", "Integer", "Double",
    "Long", "Boolean", "Character", "List", "ArrayList", "LinkedList", "Map",
    "HashMap", "Set", "HashSet", "Queue", "Deque", "vector", "Object",
    "var", "let", "const",
}
MODIFIERS = {
    "final", "static", "public", "private", "protected", "abstract", "virtual",
    "override", "inline", "extern", "unsigned", "signed", "register",
    "volatile", "async", "await", "throws", "extends", "implements", "global",
    "nonlocal", "import", "from", "as", "pass", "endl", "explicit", "friend",
    "typedef", "template", "typename", "namespace", "using",
}
DROP = TYPE_WORDS | MODIFIERS | {"new", "self", "this"}

KW_MAP = {
    "for": "LOOP", "while": "LOOP", "do": "LOOP", "foreach": "LOOP",
    "if": "IF", "elif": "ELIF", "else": "ELSE", "switch": "SWITCH",
    "case": "CASE", "return": "RET", "break": "BRK", "continue": "CNT",
    "try": "TRY", "except": "CATCH", "catch": "CATCH", "finally": "FIN",
    "raise": "THROW", "throw": "THROW", "def": "FUNC", "function": "FUNC",
    "lambda": "FUNC", "class": "CLASS", "struct": "CLASS",
    "interface": "CLASS", "enum": "CLASS", "and": "AND", "or": "OR",
    "not": "NOT", "in": "IN", "is": "EQ", "True": "TRUE", "true": "TRUE",
    "False": "FALSE", "false": "FALSE", "None": "NULL", "null": "NULL",
    "nullptr": "NULL", "undefined": "NULL", "assert": "ASSERT",
    "with": "WITH", "yield": "YIELD", "default": "DEFAULT", "of": "OF",
}
OP_MAP = {"&&": "AND", "||": "OR", "!": "NOT", "==": "EQ", "===": "EQ",
          "!=": "NE", "!==": "NE", "=>": "ARROW"}
SKIP_OPS = {"{", "}", ".", "->", "::", "@", "#"}
AUG = {"+=": "+", "-=": "-", "*=": "*", "/=": "/", "%=": "%", "//=": "//",
       "**=": "**", "&=": "&", "|=": "|", "^=": "^", "<<=": "<<", ">>=": ">>"}
API = {
    "print": "OUT", "println": "OUT", "printf": "OUT", "puts": "OUT",
    "cout": "OUT", "len": "LEN", "length": "LEN", "size": "LEN",
    "count": "LEN", "append": "APPEND", "add": "APPEND", "push": "APPEND",
    "push_back": "APPEND", "pop": "POP", "pop_back": "POP", "remove": "POP",
    "range": "RANGE", "input": "IN", "scanf": "IN", "cin": "IN",
    "nextInt": "IN", "nextLine": "IN", "next": "IN", "readLine": "IN",
    "sorted": "SORT", "sort": "SORT", "sum": "SUM", "max": "MAX", "min": "MIN",
    "abs": "ABS", "sqrt": "SQRT", "pow": "POW", "floor": "FLOOR",
    "ceil": "CEIL", "round": "ROUND", "reverse": "REVERSE", "join": "JOIN",
    "split": "SPLIT", "contains": "HAS", "get": "GET", "put": "PUT",
}
CONTROL_START = {
    "if", "else", "for", "while", "do", "switch", "case", "return", "try",
    "catch", "finally", "throw", "break", "continue", "goto", "new", "class",
    "struct", "enum", "interface", "namespace", "using", "typedef", "default",
    "synchronized",
}
HEADER_WORDS = {"IF", "ELIF", "LOOP", "SWITCH"}


def _skip_generics(items: list, i: int) -> int:
    """If items[i] is '<', return the index after the matching '>'."""
    if i < len(items) and items[i][1] == "<":
        depth = 0
        j = i
        while j < len(items):
            if items[j][1] == "<":
                depth += 1
            elif items[j][1] == ">":
                depth -= 1
                if depth == 0:
                    return j + 1
            elif items[j][1] in (";", "{", "(", ")"):
                return i
            j += 1
    return i


def _convert(items: list) -> list:
    """Core token-by-token rewrite (no loop-header logic)."""
    out: list = []
    n = len(items)
    i = 0
    prev_dot = False
    init_depth = 0
    while i < n:
        kind, value = items[i]
        if value == "{" and i > 0 and items[i - 1][1] == "=":
            out.append("[")
            init_depth += 1
            i += 1
            continue
        if value == "}" and init_depth:
            out.append("]")
            init_depth -= 1
            i += 1
            continue
        if value == "System" and i + 4 < n and items[i + 1][1] == "." \
                and items[i + 2][1] == "out" and items[i + 3][1] == ".":
            out.append("OUT")
            i += 5
            prev_dot = False
            continue
        if value == "console" and i + 2 < n and items[i + 1][1] == ".":
            out.append("OUT")
            i += 3
            prev_dot = False
            continue
        if value == "std" and i + 1 < n and items[i + 1][1] == "::":
            i += 2
            continue
        if value == "else" and i + 1 < n and items[i + 1][1] == "if":
            out.append("ELIF")
            i += 2
            continue
        if kind == "num":
            out.append("NUM")
        elif kind == "str":
            out.append("STR")
        elif kind == "op":
            if value in (".", "->"):
                prev_dot = True
                i += 1
                continue
            if value in OP_MAP:
                out.append(OP_MAP[value])
            elif value in SKIP_OPS:
                pass
            else:
                out.append(value)
        elif value in API and kind == "id" and (
                prev_dot or value in ("cout", "cin")
                or (i + 1 < n and items[i + 1][1] == "(")):
            canon = API[value]
            nxt_paren = i + 1 < n and items[i + 1][1] == "("
            if prev_dot and out and out[-1] == "ID":
                out.pop()
                if nxt_paren:
                    out += [canon, "(", "ID"]
                    if not (i + 2 < n and items[i + 2][1] == ")"):
                        out.append(",")
                    i += 2
                    prev_dot = False
                    continue
                out += [canon, "(", "ID", ")"]
            else:
                out.append(canon)
        elif value in DROP:
            j = _skip_generics(items, i + 1)
            i = j
            prev_dot = False
            continue
        elif kind == "kw" or value in KW_MAP:
            if value in KW_MAP:
                out.append(KW_MAP[value])
            else:
                out.append(value.upper())
        else:  # identifier
            nxt = items[i + 1] if i + 1 < n else None
            if value[:1].isupper() and nxt and nxt[0] == "id" and nxt[1] not in API:
                i += 1                      # type name before a variable
                continue
            out.append("ID")
        prev_dot = False
        i += 1
    return out


def _expand_assignments(tokens: list) -> list:
    out: list = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("++", "--"):
            base = "+" if t == "++" else "-"
            if out and out[-1] == "ID":
                out += ["=", "ID", base, "NUM"]
                i += 1
                continue
            if i + 1 < len(tokens) and tokens[i + 1] == "ID":
                out += ["ID", "=", "ID", base, "NUM"]
                i += 2
                continue
        if t in AUG:
            base = AUG[t]
            if out and out[-1] == "ID":
                out += ["=", "ID", base]
            else:
                out += ["=", base]
            i += 1
            continue
        out.append(t)
        i += 1
    return out


def _split_depth0(items: list, sep: str) -> list:
    parts, cur, depth = [], [], 0
    for it in items:
        v = it[1]
        if v in ("(", "[", "{"):
            depth += 1
        elif v in (")", "]", "}"):
            depth -= 1
        if v == sep and depth == 0:
            parts.append(cur)
            cur = []
        else:
            cur.append(it)
    parts.append(cur)
    return parts


def _matching_paren(items: list, start: int) -> int:
    depth = 0
    for j in range(start, len(items)):
        if items[j][1] == "(":
            depth += 1
        elif items[j][1] == ")":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _canon_for(items: list, language: str):
    """Canonical form of a for-loop line, or None to use the generic path."""
    if language == "python":
        if len(items) >= 4 and items[0][1] == "for":
            try:
                k = next(i for i, it in enumerate(items) if it[1] == "in")
            except StopIteration:
                return None
            coll = [it for it in items[k + 1:] if it[1] != ":"]
            canon = _expand_assignments(_convert(coll))
            return ["LOOP"] + (canon if canon[:1] == ["RANGE"] else ["EACH"] + canon)
        return None
    if items[0][1] != "for" or len(items) < 3 or items[1][1] != "(":
        return None
    end = _matching_paren(items, 1)
    if end < 0:
        return None
    header = items[2:end]
    parts = _split_depth0(header, ";")
    if len(parts) == 3:
        init, cond, step = parts
        eq = next((i for i, it in enumerate(init) if it[1] == "="), None)
        if eq is None or eq == 0:
            return None
        var = init[eq - 1][1]
        start = init[eq + 1:]
        if (len(cond) < 3 or cond[0][1] != var or cond[1][1] not in ("<", "<=")):
            return None
        sv = [t[1] for t in step]
        if sv not in ([var, "++"], ["++", var], [var, "+=", "1"]):
            return None
        bound = _expand_assignments(_convert(cond[2:]))
        if cond[1][1] == "<=":
            bound += ["+", "NUM"]
        begin = _expand_assignments(_convert(start))
        args = ([] if begin == ["NUM"] and start[0][1] == "0" else begin + [","]) + bound
        return ["LOOP", "RANGE", "("] + args + [")"]
    colon = next((i for i, it in enumerate(header) if it[1] in (":", "of")), None)
    if colon is not None:
        return ["LOOP", "EACH"] + _expand_assignments(_convert(header[colon + 1:]))
    return None


def _is_function_def(items: list, language: str) -> bool:
    first = items[0][1]
    if language == "python":
        return first == "def" or (first == "async" and len(items) > 1 and items[1][1] == "def")
    if first == "function" or any(it[1] == "=>" for it in items):
        return True
    if first in CONTROL_START or items[-1][1] != "{":
        return False
    for i, it in enumerate(items):
        if it[1] in (";", "="):
            return False
        if it[0] == "id" and i + 1 < len(items) and items[i + 1][1] == "(":
            return i == 0 or items[i - 1][1] not in (".", "new", "return", "->")
    return False


_BEFORE_CAST = {"=", "+", "-", "*", "/", "%", "(", ",", "<", ">", "EQ", "NE",
                "AND", "OR", "NOT", "RET"}


def _cleanup(tokens: list) -> list:
    """Drop empty casts '( )', empty array types '[ ]' and unify OUT args."""
    out: list = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if t == "(" and nxt == ")" and (not out or out[-1] in _BEFORE_CAST):
            i += 2
            continue
        if t == "[" and nxt == "]" and out and out[-1] not in ("ID", "]", ")"):
            i += 2
            continue
        if t == "[" and nxt == "]" and (not out or out[-1] == "ID") and \
                i + 2 < len(tokens) and tokens[i + 2] == "ID":
            i += 2                         # 'int[] data' -> 'data'
            continue
        out.append(t)
        i += 1
    if out[:1] == ["OUT"]:
        out = [("," if t == "+" else t) for t in out]
    return out


def _strip_header_parens(tokens: list) -> list:
    if len(tokens) >= 3 and tokens[0] in HEADER_WORDS and tokens[1] == "(" \
            and tokens[-1] == ")":
        depth = 0
        for j in range(1, len(tokens)):
            if tokens[j] == "(":
                depth += 1
            elif tokens[j] == ")":
                depth -= 1
                if depth == 0 and j == len(tokens) - 1:
                    return [tokens[0]] + tokens[2:-1]
                if depth == 0:
                    break
    return tokens


def canonicalize_line(line: NormalizedLine, language: str) -> tuple:
    items = list(zip(line.kinds, line.values))
    if not items or items[0][1] == "@":
        return ()
    head = [v for _, v in items[:4]]
    if (any(v in ("class", "struct", "interface", "enum", "namespace") for v in head)
            and items[-1][1] in ("{", ":")):
        return ("CLASS",)
    if _is_function_def(items, language):
        return ("FUNC",)
    canon = _canon_for(items, language)
    if canon is None:
        canon = _expand_assignments(_convert(items))
    canon = _cleanup([t for t in canon if t != ";"])
    while canon and canon[-1] == ":":
        canon.pop()
    canon = _strip_header_parens(canon)
    return tuple(canon)
