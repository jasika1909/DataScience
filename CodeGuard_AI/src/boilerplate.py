"""False-positive reduction: recognise standard boilerplate lines.

Lines are matched on their *exact normalized* text (tokens joined by single
spaces, comments removed, string contents without quotes). Only constructs
that carry no authorship information are listed: entry points, standard I/O
set-up, empty constructors and plain accessors. Real logic is never listed.
"""
from __future__ import annotations

import re

_P = {
    "python": [
        ("entry point", r"if __name__ == __main__ :"),
        ("entry point", r"(def )?main \( \)( :)?"),
        ("entry point", r"main \( \)"),
        ("constructor / accessor", r"def __init__ \( self( , \w+)* \) :"),
        ("constructor / accessor", r"self \. \w+ = \w+"),
        ("constructor / accessor", r"return self \. \w+"),
    ],
    "java": [
        ("entry point", r"public static void main \( String \[ \] \w+ \) \{?"),
        ("entry point", r"public static void main \( String \. \. \. \w+ \) \{?"),
        ("standard I/O set-up", r"Scanner \w+ = new Scanner \( System \. in \) ;"),
        ("standard I/O set-up", r"\w+ \. close \( \) ;"),
        ("standard I/O set-up", r"BufferedReader \w+ = new BufferedReader \( new InputStreamReader \( System \. in \) \) ;"),
        ("constructor / accessor", r"this \. \w+ = \w+ ;"),
        ("constructor / accessor", r"return this \. \w+ ;"),
        ("constructor / accessor", r"public \w+ \( \) \{"),
        ("constructor / accessor", r"@ \w+"),
        ("constructor / accessor", r"public (String|int|double|boolean|long) (get|set|is)\w+ \( (\w+ \w+)? \) \{"),
    ],
    "c": [
        ("entry point", r"int main \( ((void|int \w+ , char \* \w+ \[ \]|int \w+ , char \*\* \w+) )?\) \{?"),
        ("entry point", r"return 0 ;"),
        ("standard I/O set-up", r"setbuf \( stdout , NULL \) ;"),
    ],
    "cpp": [
        ("entry point", r"int main \( ((void|int \w+ , char \* \w+ \[ \]|int \w+ , char \*\* \w+) )?\) \{?"),
        ("entry point", r"return 0 ;"),
        ("standard I/O set-up", r"using namespace std ;"),
        ("standard I/O set-up", r"(std :: )?ios( _base)? :: sync_with_stdio \( false \) ;"),
        ("standard I/O set-up", r"(std :: )?cin \. tie \( (NULL|nullptr|0) \) ;"),
        ("constructor / accessor", r"(public|private|protected) :"),
    ],
    "javascript": [
        ("entry point", r"module \. exports = .*"),
        ("entry point", r"export default \w+ ;?"),
        ("standard I/O set-up", r"use strict ;?"),
        ("standard I/O set-up", r"(const|let|var) \w+ = require \( \w+ \) ;?"),
    ],
}
_COMPILED = {lang: [(why, re.compile(rf"^{pat}$")) for why, pat in items]
             for lang, items in _P.items()}


def classify_line(exact: str, language: str):
    """Return the boilerplate category of a line, or None."""
    for reason, pattern in _COMPILED.get(language, ()):
        if pattern.match(exact):
            return reason
    return None
