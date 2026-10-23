"""Plain data containers shared by the engine, database, reports and UI."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SourceFile:
    """A validated source file. Content is only ever treated as text."""

    name: str
    language: str
    content: str
    size_bytes: int
    sha256: str
    line_count: int
    origin: str = "upload"          # upload | paste | sample


@dataclass
class MatchBlock:
    """A run of consecutive significant lines that appear in both files."""

    id: int
    a_start: int
    a_end: int
    b_start: int
    b_end: int
    lines: int                      # significant lines inside the block
    similarity: float               # 0-100, token identity inside the block
    kind: str                       # "identical" | "renamed" | "semantic"

    def swapped(self) -> "MatchBlock":
        return MatchBlock(self.id, self.b_start, self.b_end, self.a_start,
                          self.a_end, self.lines, self.similarity, self.kind)


@dataclass
class FunctionMatch:
    """Two Python functions whose syntax trees are (nearly) identical."""

    name_a: str
    a_start: int
    a_end: int
    name_b: str
    b_start: int
    b_end: int
    similarity: float               # 0-100

    def swapped(self) -> "FunctionMatch":
        return FunctionMatch(self.name_b, self.b_start, self.b_end,
                             self.name_a, self.a_start, self.a_end,
                             self.similarity)


@dataclass
class ComparisonResult:
    file_a: str
    file_b: str
    language_a: str
    language_b: str
    sha_a: str
    sha_b: str
    method: str
    method_note: str
    signals: dict                    # signal key -> percent or None
    weights_used: dict               # signal key -> normalized weight
    overall: float
    risk: str
    significant_lines_a: int
    significant_lines_b: int
    matched_lines: int
    blocks: list = field(default_factory=list)
    function_matches: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    thresholds: dict = field(default_factory=dict)
    elapsed_ms: float = 0.0
    excluded_a: dict = field(default_factory=dict)   # reason -> line count
    excluded_b: dict = field(default_factory=dict)
    unique_lines_a: int = 0
    unique_lines_b: int = 0
    unique_ranges_a: list = field(default_factory=list)   # [[start, end], ...]
    unique_ranges_b: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    quick_only: bool = False

    # ---- derived values ------------------------------------------------- #
    @property
    def matched_blocks(self) -> int:
        return len(self.blocks)

    @property
    def coverage_a(self) -> float:
        n = self.significant_lines_a
        return round(100.0 * self.matched_lines / n, 1) if n else 0.0

    @property
    def coverage_b(self) -> float:
        n = self.significant_lines_b
        return round(100.0 * self.matched_lines / n, 1) if n else 0.0

    @property
    def semantic_lines(self) -> int:
        return sum(b.lines for b in self.blocks if b.kind == "semantic")

    @property
    def pair_label(self) -> str:
        return f"{self.file_a}  vs  {self.file_b}"

    # ---- transformations ------------------------------------------------ #
    def swapped(self) -> "ComparisonResult":
        """Same comparison seen from the other side (A and B exchanged)."""
        return ComparisonResult(
            file_a=self.file_b, file_b=self.file_a,
            language_a=self.language_b, language_b=self.language_a,
            sha_a=self.sha_b, sha_b=self.sha_a,
            method=self.method, method_note=self.method_note,
            signals=dict(self.signals), weights_used=dict(self.weights_used),
            overall=self.overall, risk=self.risk,
            significant_lines_a=self.significant_lines_b,
            significant_lines_b=self.significant_lines_a,
            matched_lines=self.matched_lines,
            blocks=[b.swapped() for b in self.blocks],
            function_matches=[f.swapped() for f in self.function_matches],
            warnings=list(self.warnings), thresholds=dict(self.thresholds),
            elapsed_ms=self.elapsed_ms,
            excluded_a=dict(self.excluded_b), excluded_b=dict(self.excluded_a),
            unique_lines_a=self.unique_lines_b, unique_lines_b=self.unique_lines_a,
            unique_ranges_a=[list(r) for r in self.unique_ranges_b],
            unique_ranges_b=[list(r) for r in self.unique_ranges_a],
            reasons=list(self.reasons), quick_only=self.quick_only,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ComparisonResult":
        data = dict(data)
        data["blocks"] = [MatchBlock(**b) for b in data.get("blocks", [])]
        data["function_matches"] = [
            FunctionMatch(**f) for f in data.get("function_matches", [])
        ]
        return cls(**data)


def optional_float(value: Optional[float]) -> Optional[float]:
    return None if value is None else float(value)
