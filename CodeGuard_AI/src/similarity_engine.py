"""The comparison engine.

Signals (all computed from the submitted code, nothing is hard-coded):

1. exact_lines     identical normalized lines (Dice overlap)
2. token_ngrams    identifier-abstracted 4-token sequences (Dice overlap)
3. tfidf_cosine    TF-IDF vectors + cosine similarity
4. sequence        difflib.SequenceMatcher over abstracted lines
5. block_coverage  Greedy String Tiling (finds moved blocks too)
6. ast             syntax-tree trigrams (Python ast; lightweight parser for
                   Java/C/C++/JavaScript), same-language pairs only
7. semantic        canonical-form comparison (offline, rule-based)

False-positive reduction: comments, whitespace, imports, brace-only lines,
standard boilerplate, instructor template lines and lines that appear in most
submissions are excluded before any signal is computed. The overall score is
a weighted mean of the available signals (weights are re-normalized when a
signal does not apply).
"""
from __future__ import annotations

import hashlib
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from itertools import combinations
from typing import Callable, Optional

import config
from config import Settings
from src import ast_analyzer, boilerplate, structure_analyzer
from src.code_normalizer import NormalizedCode, normalize
from src.models import ComparisonResult, MatchBlock, SourceFile
from src.semantic import canonicalize_line

API_TOKENS = {"OUT", "LEN", "APPEND", "POP", "RANGE", "IN", "SORT", "SUM", "MAX",
              "MIN", "ABS", "SQRT", "POW", "FLOOR", "CEIL", "ROUND", "REVERSE",
              "JOIN", "SPLIT", "HAS", "GET", "PUT"}
IMPORT_KEY = "imports, braces and docstrings"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def classify_risk(score: float, low_max: float, moderate_max: float) -> str:
    if score < low_max:
        return config.RISK_LOW
    if score < moderate_max:
        return config.RISK_MODERATE
    return config.RISK_HIGH


def _dice(a: Counter, b: Counter) -> float:
    total = sum(a.values()) + sum(b.values())
    if not total:
        return 0.0
    return 2.0 * sum((a & b).values()) / total


def _ngrams(seq: list, n: int) -> Counter:
    if not seq:
        return Counter()
    if len(seq) < n:
        return Counter([tuple(seq)])
    return Counter(tuple(seq[i:i + n]) for i in range(len(seq) - n + 1))


def build_idf(counters: list) -> dict:
    n = len(counters)
    df: Counter = Counter()
    for c in counters:
        df.update(c.keys())
    return {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}


def _tfidf_vector(counter: Counter, idf: dict) -> dict:
    vec = {t: (1.0 + math.log(c)) * idf.get(t, 1.0) for t, c in counter.items()}
    norm = math.sqrt(sum(v * v for v in vec.values()))
    return {t: v / norm for t, v in vec.items()} if norm else {}


def cosine_similarity(a: Counter, b: Counter, idf: dict) -> float:
    va, vb = _tfidf_vector(a, idf), _tfidf_vector(b, idf)
    if not va or not vb:
        return 0.0
    if len(va) > len(vb):
        va, vb = vb, va
    return min(1.0, sum(v * vb.get(t, 0.0) for t, v in va.items()))


def _plain_cosine(a: Counter, b: Counter) -> Optional[float]:
    if not a or not b:
        return None
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def greedy_string_tiling(a: list, b: list, min_len: int,
                         max_steps: int = config.MAX_GST_STEPS):
    """Greedy String Tiling. Returns (tiles, truncated).

    Each tile is (i, j, k): a[i:i+k] == b[j:j+k]. Tiles never overlap, and
    blocks that were moved to a different position are still found.
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0 or min_len < 1:
        return [], False
    positions = defaultdict(list)
    for j, x in enumerate(b):
        positions[x].append(j)
    mark_a = [False] * n
    mark_b = [False] * m
    tiles = []
    steps = 0
    while True:
        maxmatch = min_len
        found = []
        for i in range(n):
            if n - i < maxmatch:
                break
            if mark_a[i]:
                continue
            for j in positions.get(a[i], ()):
                if m - j < maxmatch:
                    break
                if mark_b[j]:
                    continue
                k = 0
                while (i + k < n and j + k < m and a[i + k] == b[j + k]
                       and not mark_a[i + k] and not mark_b[j + k]):
                    k += 1
                steps += k + 1
                if steps > max_steps:
                    return sorted(tiles), True
                if k >= maxmatch:
                    if k > maxmatch:
                        found = []
                        maxmatch = k
                    found.append((i, j, k))
        if not found:
            break
        for i, j, k in found:
            if any(mark_a[i:i + k]) or any(mark_b[j:j + k]):
                continue
            for t in range(k):
                mark_a[i + t] = True
                mark_b[j + t] = True
            tiles.append((i, j, k))
    return sorted(tiles), False


def _ranges(unmatched: list, lines: list) -> list:
    """Merge consecutive unmatched kept-line indices into [start, end] ranges."""
    ranges, run = [], []
    for idx in unmatched:
        if run and idx != run[-1] + 1:
            ranges.append([lines[run[0]].number, lines[run[-1]].number])
            run = []
        run.append(idx)
    if run:
        ranges.append([lines[run[0]].number, lines[run[-1]].number])
    return ranges


# --------------------------------------------------------------------------- #
# Prepared documents
# --------------------------------------------------------------------------- #
@dataclass
class PreparedDoc:
    file: SourceFile
    norm: NormalizedCode
    kept: list                               # comparable lines (NormalizedLine)
    exclusions: dict                         # reason -> number of lines
    abstract_tokens: list
    features: Counter
    canon: list                              # canonical tuple per kept line
    canon_stream: list
    ast_info: Optional[ast_analyzer.AstInfo] = None


@dataclass
class Corpus:
    docs: dict = field(default_factory=dict)       # name -> PreparedDoc
    idf: dict = field(default_factory=dict)
    failed: dict = field(default_factory=dict)     # name -> error message
    ctx: str = ""                                  # fingerprint of exclusion context
    templates_used: int = 0
    common_lines: int = 0


def _features(tokens: list) -> tuple:
    feats: Counter = Counter()
    abstract = []
    for t in tokens:
        if t.kind in ("id", "num", "str"):
            feats["v:" + t.value] += 1
            abstract.append(t.kind.upper())
        else:
            abstract.append(t.value)
    for i in range(len(abstract) - 2):
        feats["g:" + " ".join(abstract[i:i + 3])] += 1
    return abstract, feats


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
class SimilarityEngine:
    def __init__(self, settings: Optional[Settings] = None,
                 cache: Optional[dict] = None):
        self.settings = (settings or Settings()).validate()
        self.cache = cache if cache is not None else {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.last_run: dict = {"skipped": 0, "elapsed": 0.0, "screened": 0}

    def _cache_put(self, key, value) -> None:
        if len(self.cache) >= config.CACHE_MAX_ENTRIES:
            for old in list(self.cache)[: config.CACHE_MAX_ENTRIES // 5]:
                self.cache.pop(old, None)
        self.cache[key] = value

    # ---- preparation -------------------------------------------------- #
    def _base(self, f: SourceFile):
        key = ("doc", f.sha256, f.language)
        base = self.cache.get(key)
        if base is None:
            norm = normalize(f.content, f.language)
            if f.language == "python":
                ast_info = ast_analyzer.build_info(f.content)
            else:
                ast_info = structure_analyzer.build_info(norm.tokens, f.language)
            canon = {ln.number: canonicalize_line(ln, f.language)
                     for ln in norm.significant_lines}
            base = (norm, ast_info, canon)
            self._cache_put(key, base)
        return base

    def prepare(self, files: list, templates: Optional[list] = None) -> Corpus:
        s = self.settings
        corpus = Corpus()
        bases = {}
        for f in files:
            try:
                bases[f.name] = (f,) + self._base(f)
            except Exception as exc:       # keep the rest of the batch usable
                corpus.failed[f.name] = f"{type(exc).__name__}: {exc}"

        template_lines: dict = defaultdict(set)
        for t in templates or []:
            try:
                n = normalize(t.content, t.language)
                template_lines[t.language].update(l.exact for l in n.significant_lines)
                corpus.templates_used += 1
            except Exception:
                continue

        # Step 1: boilerplate and template classification per line.
        pre: dict = {}
        for name, (f, norm, _ast, _canon) in bases.items():
            reasons = {}
            for ln in norm.significant_lines:
                why = None
                if s.exclude_boilerplate:
                    why = boilerplate.classify_line(ln.exact, f.language)
                if why is None and ln.exact in template_lines.get(f.language, ()):
                    why = "instructor template code"
                if why:
                    reasons[ln.number] = why
            pre[name] = reasons

        # Step 2: lines shared by most submissions (corpus frequency).
        common: dict = defaultdict(set)
        if s.common_fraction > 0:
            by_lang: dict = defaultdict(list)
            for name, (f, *_rest) in bases.items():
                by_lang[f.language].append(name)
            for lang, names in by_lang.items():
                if len(names) < config.COMMON_MIN_FILES:
                    continue
                df: Counter = Counter()
                for name in names:
                    norm = bases[name][1]
                    df.update({l.exact for l in norm.significant_lines
                               if l.number not in pre[name]})
                limit = s.common_fraction * len(names)
                common[lang] = {line for line, c in df.items() if c >= limit}
        corpus.common_lines = sum(len(v) for v in common.values())

        # Step 3: build the comparable view of each file.
        for name, (f, norm, ast_info, canon_all) in bases.items():
            exclusions: Counter = Counter()
            kept = []
            for ln in norm.lines:
                if not ln.significant:
                    exclusions[IMPORT_KEY] += 1
                    continue
                why = pre[name].get(ln.number)
                if why is None and ln.exact in common.get(f.language, ()):
                    why = "common across submissions"
                if why:
                    exclusions[why] += 1
                else:
                    kept.append(ln)
            numbers = {ln.number for ln in kept}
            tokens = [t for t in norm.tokens if t.line in numbers]
            abstract, feats = _features(tokens)
            canon = [canon_all.get(ln.number, ()) for ln in kept]
            stream: list = []
            for tup in canon:
                stream.extend(tup)
                stream.append("\n")
            corpus.docs[name] = PreparedDoc(
                file=f, norm=norm, kept=kept, exclusions=dict(exclusions),
                abstract_tokens=abstract, features=feats, canon=canon,
                canon_stream=stream, ast_info=ast_info)

        corpus.idf = build_idf([d.features for d in corpus.docs.values()])
        fingerprint = repr((sorted(sorted(v) for v in common.values()),
                            sorted(sorted(v) for v in template_lines.values())))
        corpus.ctx = hashlib.md5(fingerprint.encode()).hexdigest()[:12]
        return corpus

    # ---- single pair -------------------------------------------------- #
    def compare(self, corpus: Corpus, name_a: str, name_b: str,
                screen: bool = False) -> ComparisonResult:
        for name in (name_a, name_b):
            if name not in corpus.docs:
                reason = corpus.failed.get(name, "file not prepared")
                raise ValueError(f"Cannot compare '{name}': {reason}")
        a, b = corpus.docs[name_a], corpus.docs[name_b]
        key = ("pair", tuple(sorted(((name_a, a.file.sha256), (name_b, b.file.sha256)))),
               self.settings.key(), corpus.ctx, screen, corpus.templates_used)
        cached = self.cache.get(key)
        if cached is not None:
            self.cache_hits += 1
            return cached if cached.file_a == name_a else cached.swapped()
        self.cache_misses += 1
        result = self._compare(corpus, a, b, screen)
        self._cache_put(key, result)
        return result

    def _combine(self, signals: dict) -> tuple:
        usable = {k: w for k, w in self.settings.weights.items()
                  if signals.get(k) is not None and w > 0}
        if not usable:
            usable = {k: 1.0 for k, v in signals.items() if v is not None}
        total_w = sum(usable.values())
        weights_used = {k: w / total_w for k, w in usable.items()}
        overall = sum(weights_used[k] * signals[k] for k in weights_used)
        return weights_used, round(min(100.0, max(0.0, overall)), 1)

    @staticmethod
    def _pct(signals: dict) -> dict:
        return {k: (None if v is None else round(100.0 * min(1.0, max(0.0, v)), 1))
                for k, v in signals.items()}

    def _compare(self, corpus: Corpus, a: PreparedDoc, b: PreparedDoc,
                 screen: bool) -> ComparisonResult:
        started = time.perf_counter()
        s = self.settings
        warnings: list = []
        fam = structure_analyzer.FAMILY
        signals: dict = {k: None for k in config.SIGNAL_KEYS}

        # 1-3: cheap signals
        ca = Counter(l.exact for l in a.kept)
        cb = Counter(l.exact for l in b.kept)
        signals["exact_lines"] = _dice(ca, cb)
        signals["token_ngrams"] = _dice(
            _ngrams(a.abstract_tokens, config.TOKEN_NGRAM_SIZE),
            _ngrams(b.abstract_tokens, config.TOKEN_NGRAM_SIZE))
        signals["tfidf_cosine"] = cosine_similarity(a.features, b.features, corpus.idf)

        base_kwargs = dict(
            file_a=a.file.name, file_b=b.file.name,
            language_a=a.file.language, language_b=b.file.language,
            sha_a=a.file.sha256, sha_b=b.file.sha256,
            significant_lines_a=len(a.kept), significant_lines_b=len(b.kept),
            excluded_a=dict(a.exclusions), excluded_b=dict(b.exclusions),
            thresholds={"low_max": s.low_max, "moderate_max": s.moderate_max,
                        "min_block_lines": s.min_block_lines},
        )

        if screen and fam[a.file.language] == fam[b.file.language] and 100.0 * max(
                signals["exact_lines"], signals["token_ngrams"]) < s.screen_threshold:
            pct = self._pct(signals)
            weights_used, overall = self._combine(pct)
            return ComparisonResult(
                method="Quick screening (cheap signals only)",
                method_note=("Block, structure and semantic analysis were skipped "
                             "because the quick screen found little overlap. Open "
                             "this pair to run the full analysis."),
                signals=pct, weights_used=weights_used, overall=overall,
                risk=classify_risk(overall, s.low_max, s.moderate_max),
                matched_lines=0, quick_only=True,
                reasons=[f"Quick screen: exact-line overlap "
                         f"{pct['exact_lines']:.0f}% and token n-gram overlap "
                         f"{pct['token_ngrams']:.0f}% are both below the "
                         f"{s.screen_threshold:g}% screening threshold."],
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                **base_kwargs)

        # 4: sequence matching over abstracted lines
        vocab: dict = {}
        seq_a = [vocab.setdefault(l.abstract, len(vocab)) for l in a.kept]
        seq_b = [vocab.setdefault(l.abstract, len(vocab)) for l in b.kept]
        if seq_a and seq_b:
            junk = len(seq_a) * len(seq_b) > 4_000_000
            signals["sequence"] = SequenceMatcher(None, seq_a, seq_b, autojunk=junk).ratio()
        else:
            signals["sequence"] = 0.0

        # 5: blocks (Greedy String Tiling)
        blocks: list = []
        covered_a = [False] * len(a.kept)
        covered_b = [False] * len(b.kept)
        primary_lines = 0
        min_len = max(1, min(s.min_block_lines, len(seq_a) or 1, len(seq_b) or 1))
        if seq_a and seq_b:
            tiles, truncated = greedy_string_tiling(seq_a, seq_b, min_len)
            if truncated:
                warnings.append("Block detection stopped early because the files are "
                                "very repetitive; block results may be incomplete.")
            for i, j, k in tiles:
                la, lb = a.kept[i:i + k], b.kept[j:j + k]
                total = equal = 0
                for x, y in zip(la, lb):
                    for tx, ty in zip(x.values, y.values):
                        total += 1
                        equal += tx == ty
                sim = 100.0 * equal / total if total else 100.0
                blocks.append(MatchBlock(
                    id=len(blocks) + 1, a_start=la[0].number, a_end=la[-1].number,
                    b_start=lb[0].number, b_end=lb[-1].number, lines=k,
                    similarity=round(sim, 1),
                    kind="identical" if equal == total else "renamed"))
                for t in range(k):
                    covered_a[i + t] = covered_b[j + t] = True
                primary_lines += k
            signals["block_coverage"] = 2.0 * primary_lines / (len(seq_a) + len(seq_b))
        else:
            signals["block_coverage"] = 0.0

        # 6: syntax-tree structure (same language family only)
        fmatches: list = []
        ast_note = ""
        same_family = fam[a.file.language] == fam[b.file.language]
        if same_family and a.ast_info and b.ast_info:
            ar = ast_analyzer.compare_info(a.ast_info, b.ast_info)
            if ar.available:
                signals["ast"] = ar.score / 100.0
                fmatches = ar.function_matches
            else:
                ast_note = ar.reason

        # 7: semantic profile and semantic blocks
        s1 = _dice(_ngrams(a.canon_stream, config.SEMANTIC_NGRAM_SIZE),
                   _ngrams(b.canon_stream, config.SEMANTIC_NGRAM_SIZE))
        s2 = _dice(Counter(c for c in a.canon if c), Counter(c for c in b.canon if c))
        s3 = _plain_cosine(Counter(t for t in a.canon_stream if t in API_TOKENS),
                           Counter(t for t in b.canon_stream if t in API_TOKENS))
        parts = [(0.5, s1), (0.35, s2)] + ([(0.15, s3)] if s3 is not None else [])
        signals["semantic"] = sum(w * v for w, v in parts) / sum(w for w, _ in parts)

        if seq_a and seq_b:
            canon_vocab: dict = {}
            barrier = [0]

            def masked(canon: list, covered: list) -> list:
                out = []
                for c, done in zip(canon, covered):
                    if done or not c:
                        barrier[0] -= 1
                        out.append(barrier[0])
                    else:
                        out.append(canon_vocab.setdefault(c, len(canon_vocab)))
                return out

            ma, mb = masked(a.canon, covered_a), masked(b.canon, covered_b)
            sem_tiles, _truncated = greedy_string_tiling(ma, mb, min_len)
            for i, j, k in sem_tiles:
                la, lb = a.kept[i:i + k], b.kept[j:j + k]
                tok_a = [v for l in la for v in l.values]
                tok_b = [v for l in lb for v in l.values]
                sim = 100.0 * _dice(_ngrams(tok_a, 2), _ngrams(tok_b, 2))
                blocks.append(MatchBlock(
                    id=len(blocks) + 1, a_start=la[0].number, a_end=la[-1].number,
                    b_start=lb[0].number, b_end=lb[-1].number, lines=k,
                    similarity=round(sim, 1), kind="semantic"))
                for t in range(k):
                    covered_a[i + t] = covered_b[j + t] = True

        matched = sum(blk.lines for blk in blocks)
        cross = fam[a.file.language] != fam[b.file.language]
        if cross:
            # Literal/lexical signals cannot apply across languages; judge on
            # the semantic profile and on how much logic was matched.
            for k in ("exact_lines", "token_ngrams", "tfidf_cosine", "sequence", "ast"):
                signals[k] = None
            signals["block_coverage"] = (2.0 * matched / (len(seq_a) + len(seq_b))
                                         if seq_a and seq_b else 0.0)
        unique_a = [i for i, c in enumerate(covered_a) if not c]
        unique_b = [i for i, c in enumerate(covered_b) if not c]

        pct = self._pct(signals)
        weights_used, overall = self._combine(pct)
        risk = classify_risk(overall, s.low_max, s.moderate_max)

        # ---- method description ---------------------------------------- #
        label_a = config.LANGUAGE_LABELS[a.file.language]
        label_b = config.LANGUAGE_LABELS[b.file.language]
        if pct["ast"] is not None and a.file.language == "python":
            method = "Python AST + normalized token analysis"
            note = ("Python syntax trees were compared in addition to the "
                    "lexical, sequence and semantic signals.")
        elif pct["ast"] is not None:
            method = "Structural tree analysis + normalized token analysis"
            note = (f"{label_a} structure was compared using an approximate syntax "
                    "tree from a lightweight parser (not a full compiler grammar), "
                    "in addition to the lexical, sequence and semantic signals.")
        elif same_family:
            method = "Generic token-based analysis"
            note = f"Structural analysis was unavailable ({ast_note or 'not applicable'})."
        else:
            method = "Generic token-based analysis"
            note = (f"Cross-language comparison ({label_a} vs {label_b}); lexical and "
                    "structural signals do not apply, so only the semantic profile "
                    "and matched-logic coverage were used.")
            warnings.append("The files use different languages, so similarity "
                            "scores are less meaningful.")
        if min(len(seq_a), len(seq_b)) < 5:
            warnings.append("Very little comparable code: scores for tiny files "
                            "are easily inflated.")
        if not seq_a or not seq_b:
            warnings.append("After excluding boilerplate and common code, one file "
                            "has no comparable lines left.")

        result = ComparisonResult(
            method=method, method_note=note, signals=pct,
            weights_used=weights_used, overall=overall, risk=risk,
            matched_lines=matched, blocks=blocks, function_matches=fmatches,
            warnings=warnings,
            unique_lines_a=len(unique_a), unique_lines_b=len(unique_b),
            unique_ranges_a=_ranges(unique_a, a.kept)[:60],
            unique_ranges_b=_ranges(unique_b, b.kept)[:60],
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **base_kwargs)
        result.reasons = explain(result, corpus.templates_used)
        return result

    # ---- many pairs --------------------------------------------------- #
    def compare_pairs(self, corpus: Corpus, pairs: list,
                      progress: Optional[Callable[[int, int, str], None]] = None):
        """Compare many pairs. One failing pair never stops the others.

        Large batches are quick-screened, results are cached, and the run
        stops after ``settings.time_budget_s`` seconds (see ``last_run``).
        """
        results, errors = [], {}
        total = len(pairs)
        screen = (self.settings.screen_threshold > 0
                  and total >= config.SCREEN_MIN_PAIRS)
        started = time.perf_counter()
        skipped = 0
        for n, (na, nb) in enumerate(pairs, start=1):
            if time.perf_counter() - started > self.settings.time_budget_s:
                skipped = total - n + 1
                break
            if progress:
                progress(n - 1, total, f"{na} vs {nb}")
            try:
                results.append(self.compare(corpus, na, nb, screen=screen))
            except Exception as exc:
                errors[(na, nb)] = f"{type(exc).__name__}: {exc}"
        if progress:
            progress(total, total, "done")
        self.last_run = {"skipped": skipped,
                         "elapsed": round(time.perf_counter() - started, 2),
                         "screened": sum(1 for r in results if r.quick_only)}
        return results, errors

    def compare_files(self, a: SourceFile, b: SourceFile,
                      templates: Optional[list] = None) -> ComparisonResult:
        corpus = self.prepare([a, b], templates)
        return self.compare(corpus, a.name, b.name)

    @staticmethod
    def all_pairs(names: list) -> list:
        return list(combinations(names, 2))


# --------------------------------------------------------------------------- #
# Explanations
# --------------------------------------------------------------------------- #
def explain(r: ComparisonResult, templates_used: int = 0) -> list:
    """Plain-language reasons behind a score (derived from the result only)."""
    out = []
    contrib = sorted(((r.weights_used[k] * (r.signals[k] or 0), k)
                      for k in r.weights_used), reverse=True)
    top = [f"{config.SIGNAL_LABELS[k]} {r.signals[k]:.0f}%" for _, k in contrib[:3]
           if r.signals[k] is not None]
    out.append(f"Overall {r.overall:.1f}% ({r.risk} indicator) is a weighted blend of "
               f"{len(r.weights_used)} signals. Largest contributions: {', '.join(top)}.")
    if r.blocks:
        biggest = max(r.blocks, key=lambda b: b.lines)
        out.append(
            f"{r.matched_blocks} matched block(s) cover {r.matched_lines} of "
            f"{r.significant_lines_a} comparable lines in A ({r.coverage_a:.0f}%) and "
            f"{r.matched_lines} of {r.significant_lines_b} in B ({r.coverage_b:.0f}%). "
            f"Largest: A lines {biggest.a_start}-{biggest.a_end} matches B lines "
            f"{biggest.b_start}-{biggest.b_end} ({biggest.lines} lines).")
        kinds = Counter(b.kind for b in r.blocks)
        bits = []
        if kinds["identical"]:
            bits.append(f"{kinds['identical']} identical")
        if kinds["renamed"]:
            bits.append(f"{kinds['renamed']} with the same structure but different "
                        "names or literals")
        if kinds["semantic"]:
            bits.append(f"{kinds['semantic']} with equivalent logic written in a "
                        "different form")
        out.append("Block types: " + ", ".join(bits) + ".")
    else:
        out.append(f"No run of {r.thresholds.get('min_block_lines', 3)} or more "
                   "matching consecutive lines was found.")
    ex, ng = r.signals.get("exact_lines"), r.signals.get("token_ngrams")
    if ex is not None and ng is not None and ex < 35 and ng >= 75:
        out.append(f"Exact-line match is only {ex:.0f}% while identifier-abstracted "
                   f"token sequences match {ng:.0f}%: the code has the same shape with "
                   "different names or literals, a typical sign of renaming.")
    elif ex is not None and ex >= 85:
        out.append(f"{ex:.0f}% of comparable lines are identical after removing "
                   "comments and whitespace.")
    if r.signals.get("ast") is not None:
        names = ", ".join(f"{f.name_a} ~ {f.name_b}" for f in r.function_matches[:4])
        out.append(f"Syntax-tree structure overlaps {r.signals['ast']:.0f}%; "
                   f"{len(r.function_matches)} function(s) have matching structure"
                   + (f" ({names})." if names else "."))
    sem = r.signals.get("semantic")
    if sem is not None and sem >= 60 and (ex or 0) < 60:
        out.append(f"Canonical logic form matches {sem:.0f}%: the programs perform the "
                   "same steps even where loop style, assignment form or names differ.")
    ignored = []
    for label, side in (("A", r.excluded_a), ("B", r.excluded_b)):
        extra = {k: v for k, v in side.items() if k != IMPORT_KEY}
        if extra:
            ignored.append(f"{label}: " + ", ".join(f"{v} {k}" for k, v in extra.items()))
    if ignored:
        out.append("Excluded as non-evidence (false-positive reduction): "
                   + "; ".join(ignored) + ".")
    if r.unique_lines_a or r.unique_lines_b:
        out.append(f"Unique code: {r.unique_lines_a} comparable line(s) in A and "
                   f"{r.unique_lines_b} in B have no match.")
    if r.overall < r.thresholds.get("low_max", 30):
        out.append("The score is low: shared vocabulary comes from ordinary language "
                   "constructs rather than copied blocks.")
    return out
