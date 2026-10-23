"""Central configuration for CodeGuard AI.

Everything that can reasonably be tuned (limits, scoring weights, risk
thresholds, colours) lives here so that no other module contains magic numbers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
ASSETS_DIR = BASE_DIR / "assets"
SAMPLES_DIR = BASE_DIR / "samples"
DB_PATH = DATA_DIR / "codeguard.db"

# --------------------------------------------------------------------------- #
# Branding
# --------------------------------------------------------------------------- #
APP_NAME = "CodeGuard AI"
APP_TAGLINE = "Intelligent Code Similarity & Plagiarism Analysis"
APP_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# Upload limits
# --------------------------------------------------------------------------- #
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024      # 1 MB per file
MAX_LINES_PER_FILE = 5000                  # keeps pairwise comparison fast
MAX_FILES = 60                             # 60 files -> 1,770 pairs maximum
MAX_PASTE_CHARS = 300_000
MAX_NAME_LENGTH = 80
MAX_ZIP_ENTRIES = 300                      # files read from one ZIP archive
MAX_ZIP_TOTAL_BYTES = 30 * 1024 * 1024     # total uncompressed size per ZIP
MAX_ZIP_RATIO = 200                        # reject suspicious compression ratios

# --------------------------------------------------------------------------- #
# Languages
# --------------------------------------------------------------------------- #
LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".js": "javascript",
    ".mjs": "javascript",
}
LANGUAGE_LABELS = {
    "python": "Python",
    "java": "Java",
    "c": "C",
    "cpp": "C++",
    "javascript": "JavaScript",
}
DEFAULT_EXTENSION = {
    "python": ".py",
    "java": ".java",
    "c": ".c",
    "cpp": ".cpp",
    "javascript": ".js",
}
SUPPORTED_EXTENSIONS = tuple(sorted(LANGUAGE_BY_EXTENSION))

# Sample files grouped for the "Sample files" tab.
SAMPLE_SETS = {
    "Python (copy, renamed, reformatted, unrelated)": [
        "grades_original.py",
        "grades_renamed.py",
        "grades_reformatted.py",
        "prime_sieve.py",
    ],
    "Java (copy with renamed identifiers, unrelated)": [
        "QueueSimA.java",
        "QueueSimB.java",
        "BankAccount.java",
    ],
    "JavaScript (original, modified)": ["cart_original.js", "cart_modified.js"],
    "C and C++ (original, modified)": [
        "matrix_a.c",
        "matrix_b.c",
        "stack_a.cpp",
        "stack_b.cpp",
    ],
    "Same logic, different style (Python, Python, Java)": [
        "search_a.py",
        "search_b.py",
        "Search.java",
    ],
}

# --------------------------------------------------------------------------- #
# Similarity signals and scoring
# --------------------------------------------------------------------------- #
SIGNAL_KEYS = (
    "exact_lines",
    "token_ngrams",
    "tfidf_cosine",
    "sequence",
    "block_coverage",
    "ast",
    "semantic",
)
SIGNAL_LABELS = {
    "exact_lines": "Exact line matching",
    "token_ngrams": "Normalized token n-grams",
    "tfidf_cosine": "TF-IDF cosine similarity",
    "sequence": "Sequence matching",
    "block_coverage": "Matched block coverage",
    "ast": "Syntax-tree structure (AST)",
    "semantic": "Semantic logic profile",
}
SIGNAL_DESCRIPTIONS = {
    "exact_lines": (
        "Dice overlap of code lines that are identical after comments and "
        "whitespace are removed. Sensitive to copy-paste; blind to renaming."
    ),
    "token_ngrams": (
        "Dice overlap of 4-token sequences in which identifiers, numbers and "
        "strings are replaced by placeholders. Resistant to renaming and "
        "reformatting; also matches generic language idioms."
    ),
    "tfidf_cosine": (
        "Cosine similarity of TF-IDF vectors built from identifiers, literals "
        "and structural token trigrams. Rare shared terms weigh more than "
        "common ones when several files are analysed together."
    ),
    "sequence": (
        "difflib SequenceMatcher ratio over the ordered, identifier-"
        "normalized code lines. Rewards code that keeps its order."
    ),
    "block_coverage": (
        "Share of significant lines covered by matched blocks found with "
        "Greedy String Tiling, which also finds blocks that were moved."
    ),
    "ast": (
        "Dice overlap of node-type trigrams of the syntax tree (names, literal "
        "values and docstrings ignored). Python uses the real ast module; Java, "
        "C, C++ and JavaScript use a lightweight statement-level parser that "
        "builds an approximate tree. Same-language pairs only."
    ),
    "semantic": (
        "Local semantic fingerprint: code is rewritten into a canonical form "
        "(compound assignments expanded, loop styles unified, types and "
        "modifiers dropped, I/O and collection calls mapped to common names) "
        "and compared statement by statement. Finds the same logic written "
        "with different variable names, loop styles or even languages. This is "
        "a rule-based model that runs fully offline, not a neural network."
    ),
}
DEFAULT_WEIGHTS = {
    "exact_lines": 0.10,
    "token_ngrams": 0.12,
    "tfidf_cosine": 0.10,
    "sequence": 0.12,
    "block_coverage": 0.20,
    "ast": 0.18,
    "semantic": 0.18,
}

TOKEN_NGRAM_SIZE = 4
DEFAULT_MIN_BLOCK_LINES = 3
MAX_GST_STEPS = 30_000_000        # work budget for block detection
SEMANTIC_NGRAM_SIZE = 5
# False-positive reduction
COMMON_MIN_FILES = 6              # corpus-frequency filter needs this many files
COMMON_FRACTION = 0.70            # line in >= 70% of files => common/template code
# Performance
SCREEN_THRESHOLD = 20.0           # quick-screen pairs below this cheap score
SCREEN_MIN_PAIRS = 15             # only screen when a batch is this large
TIME_BUDGET_S = 120.0             # stop a batch analysis after this long
CACHE_MAX_ENTRIES = 5000
AST_FUNCTION_THRESHOLD = 0.80
AST_MIN_FUNCTION_NODES = 12
AST_MAX_FUNCTIONS = 150

RISK_LOW = "Low"
RISK_MODERATE = "Moderate"
RISK_HIGH = "High"
RISK_LEVELS = (RISK_LOW, RISK_MODERATE, RISK_HIGH)
RISK_COLORS = {
    RISK_LOW: "#34d399",
    RISK_MODERATE: "#fbbf24",
    RISK_HIGH: "#f87171",
}

# Highlight colours for matched blocks (cycled).
BLOCK_COLORS = (
    "#fbbf24",  # amber
    "#22d3ee",  # cyan
    "#f472b6",  # pink
    "#4ade80",  # green
    "#fb923c",  # orange
    "#a78bfa",  # violet
    "#a3e635",  # lime
    "#60a5fa",  # sky
)


# --------------------------------------------------------------------------- #
# Accounts and security
# --------------------------------------------------------------------------- #
# Set the environment variable CODEGUARD_AUTH=off for single-user local use
# without a login screen.
AUTH_ENABLED = os.environ.get("CODEGUARD_AUTH", "on").strip().lower() != "off"
# Anyone who can open the app may create a teacher or student account. Set
# CODEGUARD_SIGNUP=off to turn self-registration off (accounts are then created
# by teachers and the administrator only).
ALLOW_SELF_SIGNUP = os.environ.get("CODEGUARD_SIGNUP", "on").strip().lower() != "off"
SESSION_TIMEOUT_MIN = 30
PBKDF2_ITERATIONS = 310_000
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300
MIN_PASSWORD_LENGTH = 8
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"


@dataclass
class Settings:
    """User-tunable analysis settings.

    The thresholds are *indicators for human review*, not proof of anything.
    """

    weights: dict = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    low_max: float = 30.0          # below this  -> Low
    moderate_max: float = 60.0     # below this  -> Moderate, otherwise High
    min_block_lines: int = DEFAULT_MIN_BLOCK_LINES
    exclude_boilerplate: bool = True
    common_fraction: float = COMMON_FRACTION     # 0 disables the filter
    screen_threshold: float = SCREEN_THRESHOLD   # 0 disables quick screening
    time_budget_s: float = TIME_BUDGET_S

    def key(self) -> tuple:
        """Hashable fingerprint used for result caching."""
        return (tuple(sorted(self.weights.items())), self.low_max,
                self.moderate_max, self.min_block_lines,
                self.exclude_boilerplate, self.common_fraction,
                self.screen_threshold)

    def validate(self) -> "Settings":
        if not 0 <= self.low_max < self.moderate_max <= 100:
            raise ValueError("Thresholds must satisfy 0 <= low < moderate <= 100.")
        if self.min_block_lines < 1:
            raise ValueError("Minimum block size must be at least 1 line.")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("Weights cannot be negative.")
        if not 0 <= self.common_fraction <= 1:
            raise ValueError("The common-code fraction must be between 0 and 1.")
        return self
