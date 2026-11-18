"""Approximate syntax trees for Java, C, C++ and JavaScript.

This is a lightweight, statement-level parser that works on the token stream.
It recognises blocks, functions, classes, if/else, loops, try/catch, switch,
return/break/continue/throw, declarations, assignments and calls, and emits a
tree of node types with names and literal values removed. It is NOT a full
compiler grammar: unusual constructs (templates, macros, lambdas with complex
bodies) are handled approximately. The result feeds the same comparison used
for Python's real ``ast`` module.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from src.ast_analyzer import AstInfo, FuncInfo, _ngrams
from src.code_normalizer import Token

MAX_DEPTH = 150
TYPE_DECL = {"class", "struct", "interface", "enum", "namespace", "union"}
LOOP_WORDS = {"for", "while"}
OPS_OF_INTEREST = {
    "+": "Add", "-": "Sub", "*": "Mul", "/": "Div", "%": "Mod", "<": "Lt",
    ">": "Gt", "<=": "Le", ">=": "Ge", "==": "Eq", "===": "Eq", "!=": "Ne",
    "!==": "Ne", "&&": "And", "||": "Or", "!": "Not", "?": "Cond",
    "&": "BitAnd", "|": "BitOr", "^": "BitXor", "<<": "Shl", ">>": "Shr",
}
AUG_OPS = {"+=": "Add", "-=": "Sub", "*=": "Mul", "/=": "Div", "%=": "Mod",
           "++": "Add", "--": "Sub"}


class _TooDeep(Exception):
    pass


@dataclass
class Node:
    label: str
    children: list = field(default_factory=list)
    name: str = ""
    start: int = 0
    end: int = 0


class _Parser:
    def __init__(self, tokens: list, language: str):
        self.t = tokens
        self.pos = 0
        self.depth = 0
        self.language = language

    # ---- helpers ------------------------------------------------------- #
    def peek(self, k: int = 0):
        i = self.pos + k
        return self.t[i] if i < len(self.t) else None

    def line_before(self) -> int:
        return self.t[self.pos - 1].line if self.pos > 0 else 0

    def skip_balanced(self, open_v: str, close_v: str) -> list:
        """Consume a balanced group starting at the opening token."""
        collected = []
        depth = 0
        while self.pos < len(self.t):
            tok = self.t[self.pos]
            if tok.value == open_v:
                depth += 1
            elif tok.value == close_v:
                depth -= 1
                if depth == 0:
                    self.pos += 1
                    return collected
            collected.append(tok)
            self.pos += 1
        return collected

    @staticmethod
    def summarize(tokens: list) -> list:
        """Operator / call / index children for a token run."""
        kids = []
        for i, tok in enumerate(tokens):
            v = tok.value
            if tok.kind == "op":
                if v in OPS_OF_INTEREST:
                    kids.append(Node("Op:" + OPS_OF_INTEREST[v]))
                elif v in AUG_OPS:
                    kids.append(Node("Op:" + AUG_OPS[v]))
                elif v == "[" and i > 0 and (tokens[i - 1].kind == "id"
                                             or tokens[i - 1].value in ("]", ")")):
                    kids.append(Node("Index"))
                elif v == "(" and i > 0 and tokens[i - 1].kind == "id":
                    kids.append(Node("Call"))
            elif v == "new" and tok.kind == "kw":
                kids.append(Node("New"))
        return kids

    # ---- grammar ------------------------------------------------------- #
    def parse_unit(self) -> Node:
        root = Node("Unit")
        while self.pos < len(self.t):
            before = self.pos
            node = self.statement()
            if node is not None:
                root.children.append(node)
            if self.pos == before:        # stray token: always make progress
                self.pos += 1
        return root

    def block(self) -> Node:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise _TooDeep()
        start = self.peek().line
        self.pos += 1                     # '{'
        node = Node("Block", start=start)
        while self.pos < len(self.t) and self.t[self.pos].value != "}":
            before = self.pos
            child = self.statement()
            if child is not None:
                node.children.append(child)
            if self.pos == before:
                self.pos += 1
        if self.pos < len(self.t):
            self.pos += 1                 # '}'
        node.end = self.line_before()
        self.depth -= 1
        return node

    def body(self):
        """Body of a control statement (a block or one statement)."""
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise _TooDeep()
        tok = self.peek()
        node = None if tok is None or tok.value == "}" else self.statement()
        self.depth -= 1
        return node

    def statement(self):
        tok = self.peek()
        if tok is None:
            return None
        v = tok.value
        if v == "{":
            return self.block()
        if v == ";":
            self.pos += 1
            return None
        if v == "}":
            return None
        if tok.kind == "kw":
            if v == "if":
                return self.if_statement()
            if v in LOOP_WORDS or v in ("switch", "catch", "synchronized"):
                return self.header_statement(v)
            if v == "do":
                start = tok.line
                self.pos += 1
                node = Node("Loop", start=start)
                inner = self.body()
                if inner is not None:
                    node.children.append(inner)
                if self.peek() and self.peek().value == "while":
                    self.pos += 1
                    if self.peek() and self.peek().value == "(":
                        node.children += self.summarize(self.skip_balanced("(", ")"))
                    if self.peek() and self.peek().value == ";":
                        self.pos += 1
                node.end = self.line_before()
                return node
            if v == "try":
                node = Node("Try", start=tok.line)
                self.pos += 1
                if self.peek() and self.peek().value == "(":
                    self.skip_balanced("(", ")")       # try-with-resources
                inner = self.body()
                if inner is not None:
                    node.children.append(inner)
                node.end = self.line_before()
                return node
            if v == "finally":
                node = Node("Finally", start=tok.line)
                self.pos += 1
                inner = self.body()
                if inner is not None:
                    node.children.append(inner)
                node.end = self.line_before()
                return node
            if v in ("return", "break", "continue", "throw", "goto"):
                return self.simple(v.capitalize())
            if v in ("case", "default"):
                return self.case_label()
        return self.declaration_or_expression()

    def if_statement(self):
        tok = self.peek()
        node = Node("If", start=tok.line)
        self.pos += 1
        if self.peek() and self.peek().value == "(":
            node.children += self.summarize(self.skip_balanced("(", ")"))
        inner = self.body()
        if inner is not None:
            node.children.append(inner)
        if self.peek() and self.peek().value == "else":
            self.pos += 1
            else_node = Node("Else", start=self.line_before())
            branch = self.body()
            if branch is not None:
                else_node.children.append(branch)
            else_node.end = self.line_before()
            node.children.append(else_node)
        node.end = self.line_before()
        return node

    def header_statement(self, word: str):
        tok = self.peek()
        label = {"for": "Loop", "while": "Loop", "switch": "Switch",
                 "catch": "Catch", "synchronized": "Sync"}[word]
        node = Node(label, start=tok.line)
        self.pos += 1
        if self.peek() and self.peek().value == "(":
            node.children += self.summarize(self.skip_balanced("(", ")"))
        inner = self.body()
        if inner is not None:
            node.children.append(inner)
        node.end = self.line_before()
        return node

    def simple(self, label: str):
        tok = self.peek()
        node = Node(label, start=tok.line)
        self.pos += 1
        run = self.until_statement_end()
        node.children += self.summarize(run)
        node.end = self.line_before()
        return node

    def case_label(self):
        tok = self.peek()
        node = Node("Case", start=tok.line)
        self.pos += 1
        while self.pos < len(self.t) and self.t[self.pos].value not in (":", "{", "}", ";"):
            self.pos += 1
        if self.peek() and self.peek().value == ":":
            self.pos += 1
        node.end = self.line_before()
        return node

    def until_statement_end(self) -> list:
        """Consume up to and including ';' at depth 0 (stops before '}')."""
        run = []
        depth = 0
        while self.pos < len(self.t):
            tok = self.t[self.pos]
            v = tok.value
            if v in ("(", "[", "{"):
                depth += 1
            elif v in (")", "]"):
                depth -= 1
            elif v == "}":
                if depth == 0:
                    break
                depth -= 1
            elif v == ";" and depth <= 0:
                self.pos += 1
                break
            run.append(tok)
            self.pos += 1
        return run

    def declaration_or_expression(self):
        start_tok = self.peek()
        run: list = []
        depth = 0
        saw_assign = False
        while self.pos < len(self.t):
            tok = self.t[self.pos]
            v = tok.value
            if depth == 0 and v == "{":
                kind = self.classify_brace(run, saw_assign)
                if kind == "type":
                    return self.type_declaration(run, start_tok)
                if kind == "func":
                    return self.function(run, start_tok)
                self.skip_balanced("{", "}")          # initializer / literal
                run.append(Token("op", "[", tok.line))
                run.append(Token("op", "]", tok.line))
                continue
            if v in ("(", "["):
                depth += 1
            elif v in (")", "]"):
                depth -= 1
            elif v == "}" and depth <= 0:
                break
            elif v == ";" and depth <= 0:
                self.pos += 1
                break
            elif v == "=" and depth == 0:
                saw_assign = True
            run.append(tok)
            self.pos += 1
        if not run:
            return None
        return self.expression_node(run, start_tok)

    def classify_brace(self, run: list, saw_assign: bool) -> str:
        values = [t.value for t in run]
        if any(v in TYPE_DECL for v in values):
            return "type"
        if "=>" in values or "function" in values:
            return "func"
        if saw_assign:
            return "init"
        if "(" in values:
            first = values.index("(")
            if first > 0 and run[first - 1].kind in ("id",) and \
                    run[first - 1].value not in ("new",):
                return "func"
        return "init"

    def function(self, run: list, start_tok: Token) -> Node:
        name = "<anonymous>"
        values = [t.value for t in run]
        if "(" in values:
            k = values.index("(")
            if k > 0 and run[k - 1].kind == "id":
                name = run[k - 1].value
        node = Node("Func", name=name, start=start_tok.line)
        node.children.append(Node("Params", [Node("Param") for _ in
                                             self.count_params(run)]))
        node.children.append(self.block())
        node.end = self.line_before()
        return node

    @staticmethod
    def count_params(run: list) -> list:
        values = [t.value for t in run]
        if "(" not in values:
            return []
        i = values.index("(") + 1
        depth, params, seen = 1, [], False
        while i < len(values) and depth:
            v = values[i]
            if v == "(":
                depth += 1
            elif v == ")":
                depth -= 1
            elif v == "," and depth == 1:
                params.append(1)
                seen = False
                i += 1
                continue
            if depth:
                seen = True
            i += 1
        if seen:
            params.append(1)
        return params

    def type_declaration(self, run: list, start_tok: Token) -> Node:
        node = Node("Class", start=start_tok.line)
        names = [t.value for t in run if t.kind == "id"]
        node.name = names[0] if names else ""
        node.children.append(self.block())
        node.end = self.line_before()
        return node

    def expression_node(self, run: list, start_tok: Token) -> Node:
        values = [t.value for t in run]
        is_assign = any(v == "=" for v in values) or any(v in AUG_OPS for v in values)
        label = "Assign" if is_assign else ("Call" if "(" in values else "Expr")
        node = Node("Stmt:" + label, start=start_tok.line, end=self.line_before())
        node.children = self.summarize(run)
        return node


def _preorder(root: Node) -> tuple:
    seq = []
    stack = [root]
    while stack:
        node = stack.pop()
        seq.append(node.label)
        stack.extend(reversed(node.children))
    return tuple(seq)


def _functions(root: Node) -> list:
    out = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.label == "Func":
            seq = _preorder(node)
            out.append(FuncInfo(name=node.name, start=node.start,
                                end=node.end or node.start, seq=seq,
                                digest=hash(seq), grams=_ngrams(seq)))
        stack.extend(node.children)
    return out


def build_info(tokens: list, language: str) -> AstInfo:
    """Build structure info for Java, C, C++ or JavaScript tokens."""
    if not tokens:
        return AstInfo(False, "No code tokens")
    try:
        root = _Parser(tokens, language).parse_unit()
    except _TooDeep:
        return AstInfo(False, "The code is too deeply nested")
    except Exception as exc:      # defensive: never break the batch
        return AstInfo(False, f"Structure parser failed ({type(exc).__name__})")
    seq = _preorder(root)
    if len(seq) < 3:
        return AstInfo(False, "Too little structure to compare")
    funcs = sorted(_functions(root), key=lambda f: len(f.seq), reverse=True)
    import config
    return AstInfo(True, "", _ngrams(seq), len(seq), funcs[: config.AST_MAX_FUNCTIONS])


FAMILY = {"python": "python", "java": "java", "c": "c", "cpp": "c",
          "javascript": "javascript"}
