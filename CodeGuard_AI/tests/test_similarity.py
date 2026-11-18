"""Tests for the normalizer, AST analyzer and similarity engine."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from config import Settings
from src import ast_analyzer
from src.code_normalizer import normalize, tokenize
from src.file_handler import load_from_path, source_from_text
from src.similarity_engine import (SimilarityEngine, classify_risk,
                                   greedy_string_tiling)

S = config.SAMPLES_DIR


def sample(name, rename=None):
    f = load_from_path(S / name)
    if rename:
        from dataclasses import replace
        f = replace(f, name=rename)
    return f


class NormalizerTests(unittest.TestCase):
    def test_comments_removed_per_language(self):
        py = [t.value for t in tokenize("x = 1  # note\n", "python")]
        self.assertEqual(py, ["x", "=", "1"])
        js = [t.value for t in tokenize("a = 1; // c\n/* b\nc */ b = 2;", "javascript")]
        self.assertEqual(js, ["a", "=", "1", ";", "b", "=", "2", ";"])

    def test_comment_markers_inside_strings_survive(self):
        toks = tokenize('s = "http://x.com # not a comment"\n', "python")
        self.assertEqual([t.kind for t in toks], ["id", "op", "str"])

    def test_python_floor_division_is_operator(self):
        vals = [t.value for t in tokenize("a = b // c\n", "python")]
        self.assertIn("//", vals)

    def test_line_numbers_after_multiline_tokens(self):
        toks = tokenize('"""doc\nstring"""\nx = 1\n', "python")
        self.assertEqual(toks[-1].line, 3)

    def test_trivial_lines_not_significant(self):
        code = "import os\nif x:\n    pass\nelse:\n    y = 1\n"
        sig = [l.exact for l in normalize(code, "python").significant_lines]
        self.assertEqual(sig, ["if x :", "y = 1"])

    def test_unterminated_input_does_not_crash(self):
        for lang in config.LANGUAGE_LABELS:
            normalize('x = "unterminated\n/* open', lang)
            normalize("'''never closed", lang)


class TilingTests(unittest.TestCase):
    def test_finds_moved_blocks(self):
        a = [1, 2, 3, 4, 9, 5, 6, 7, 8]
        b = [5, 6, 7, 8, 0, 1, 2, 3, 4]
        tiles, truncated = greedy_string_tiling(a, b, 3)
        self.assertFalse(truncated)
        self.assertEqual(sorted((i, j, k) for i, j, k in tiles), [(0, 5, 4), (5, 0, 4)])

    def test_min_length_and_empty(self):
        self.assertEqual(greedy_string_tiling([1, 2], [1, 2], 3)[0], [])
        self.assertEqual(greedy_string_tiling([], [1], 1)[0], [])

    def test_budget_guard(self):
        _, truncated = greedy_string_tiling([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], 3, max_steps=3)
        self.assertTrue(truncated)


class AstTests(unittest.TestCase):
    def test_rename_invariant(self):
        a = ast_analyzer.build_info("def f(a):\n    b = a + 1\n    return b * 2\n")
        b = ast_analyzer.build_info("def g(zz):\n    q = zz + 7\n    return q * 9\n")
        self.assertEqual(ast_analyzer.compare_info(a, b).score, 100.0)

    def test_syntax_error_is_reported_not_raised(self):
        info = ast_analyzer.build_info("def broken(:\n")
        self.assertFalse(info.ok)
        res = ast_analyzer.compare_info(info, ast_analyzer.build_info("x = 1\n"))
        self.assertFalse(res.available)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = SimilarityEngine()

    def test_identical_files(self):
        r = self.engine.compare_files(sample("grades_original.py"),
                                      sample("grades_original.py", "copy.py"))
        self.assertEqual(r.overall, 100.0)
        self.assertEqual(r.risk, config.RISK_HIGH)
        self.assertEqual(r.matched_lines, r.significant_lines_a)
        self.assertEqual(r.blocks[0].kind, "identical")
        self.assertEqual(r.blocks[0].similarity, 100.0)
        self.assertGreaterEqual(len(r.function_matches), 4)

    def test_renamed_variables(self):
        r = self.engine.compare_files(sample("grades_original.py"), sample("grades_renamed.py"))
        self.assertGreaterEqual(r.overall, 70)
        self.assertEqual(r.signals["ast"], 100.0)
        self.assertLess(r.signals["exact_lines"], 30)       # names differ
        self.assertGreater(r.signals["token_ngrams"], 95)   # structure same
        self.assertTrue(all(b.kind in ("renamed", "semantic") for b in r.blocks))
        self.assertTrue(any(b.kind == "renamed" for b in r.blocks))
        self.assertEqual(r.risk, config.RISK_HIGH)

    def test_reformatted_code(self):
        r = self.engine.compare_files(sample("grades_original.py"), sample("grades_reformatted.py"))
        self.assertGreaterEqual(r.overall, 95)

    def test_completely_different_code(self):
        r = self.engine.compare_files(sample("grades_original.py"), sample("prime_sieve.py"))
        self.assertLess(r.overall, 30)
        self.assertEqual(r.risk, config.RISK_LOW)
        self.assertEqual(r.blocks, [])

    def test_cross_language_is_flagged_and_low(self):
        r = self.engine.compare_files(sample("grades_original.py"), sample("QueueSimA.java"))
        self.assertLess(r.overall, 30)
        self.assertIsNone(r.signals["ast"])
        self.assertIn("Cross-language", r.method_note)
        self.assertTrue(r.warnings)

    def test_generic_vs_ast_method_label(self):
        java = self.engine.compare_files(sample("QueueSimA.java"), sample("QueueSimB.java"))
        self.assertEqual(java.method, "Structural tree analysis + normalized token analysis")
        self.assertIn("lightweight parser", java.method_note)
        self.assertIsNotNone(java.signals["ast"])
        cross = self.engine.compare_files(sample("grades_original.py"), sample("QueueSimA.java"))
        self.assertEqual(cross.method, "Generic token-based analysis")
        py = self.engine.compare_files(sample("grades_original.py"), sample("grades_renamed.py"))
        self.assertIn("AST", py.method)

    def test_python_syntax_error_falls_back(self):
        a = source_from_text("def f(:\n    return 1\nx = f()\ny = 2\nz = 3\n", "python", "a.py")
        b = source_from_text("def f(:\n    return 1\nx = f()\ny = 2\nz = 3\n", "python", "b.py")
        r = self.engine.compare_files(a, b)
        self.assertIsNone(r.signals["ast"])
        self.assertEqual(r.overall, 100.0)       # weights re-normalized
        self.assertIn("syntax error", r.method_note)

    def test_other_languages_detect_copies(self):
        for x, y in [("QueueSimA.java", "QueueSimB.java"), ("cart_original.js", "cart_modified.js"),
                     ("matrix_a.c", "matrix_b.c"), ("stack_a.cpp", "stack_b.cpp")]:
            r = self.engine.compare_files(sample(x), sample(y))
            self.assertGreaterEqual(r.overall, 55, (x, y))
            self.assertGreaterEqual(r.matched_blocks, 1)

    def test_partial_copy_is_partial(self):
        a = sample("grades_original.py")
        mixed = a.content.split("def report")[0] + (
            "def other(n):\n    r = []\n    for i in range(n):\n        r.append(i * i)\n"
            "    return r\n\nprint(other(4))\nprint(other(8))\n")
        b = source_from_text(mixed, "python", "mixed.py")
        r = self.engine.compare_files(a, b)
        self.assertGreater(r.overall, 30)
        self.assertLess(r.overall, 100)
        self.assertLess(r.matched_lines, r.significant_lines_a)

    def test_blocks_come_from_real_lines(self):
        a, b = sample("QueueSimA.java"), sample("QueueSimB.java")
        r = self.engine.compare_files(a, b)
        for blk in r.blocks:
            self.assertGreaterEqual(blk.a_start, 1)
            self.assertLessEqual(blk.a_end, a.line_count)
            self.assertLessEqual(blk.b_end, b.line_count)
            self.assertGreaterEqual(blk.lines, config.DEFAULT_MIN_BLOCK_LINES)
        # blocks on one side never overlap
        spans = sorted((x.a_start, x.a_end) for x in r.blocks)
        for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
            self.assertLess(e1, s2)
        # B's reordered methods are still matched (moved-block detection)
        self.assertGreaterEqual(r.coverage_a, 90)

    def test_symmetry_and_swap(self):
        a, b = sample("QueueSimA.java"), sample("QueueSimB.java")
        ab = self.engine.compare_files(a, b)
        ba = self.engine.compare_files(b, a)
        self.assertAlmostEqual(ab.overall, ba.overall, delta=1.0)
        sw = ab.swapped()
        self.assertEqual(sw.file_a, ab.file_b)
        self.assertEqual(sw.blocks[0].a_start, ab.blocks[0].b_start)

    def test_settings_change_results(self):
        a, b = sample("grades_original.py"), sample("grades_renamed.py")
        base = self.engine.compare_files(a, b)
        only_exact = SimilarityEngine(Settings(weights={"exact_lines": 1.0})).compare_files(a, b)
        self.assertLess(only_exact.overall, base.overall)
        self.assertEqual(only_exact.overall, only_exact.signals["exact_lines"])
        strict = SimilarityEngine(Settings(low_max=90, moderate_max=95)).compare_files(a, b)
        self.assertEqual(strict.risk, config.RISK_LOW)
        with self.assertRaises(ValueError):
            Settings(low_max=70, moderate_max=40).validate()

    def test_tfidf_uses_corpus(self):
        files = [sample("grades_original.py"), sample("grades_renamed.py"), sample("prime_sieve.py")]
        corpus = self.engine.prepare(files)
        self.assertTrue(corpus.idf)
        results, errors = self.engine.compare_pairs(
            corpus, self.engine.all_pairs([f.name for f in files]))
        self.assertEqual((len(results), errors), (3, {}))

    def test_one_bad_pair_does_not_stop_batch(self):
        corpus = self.engine.prepare([sample("grades_original.py"), sample("prime_sieve.py")])
        results, errors = self.engine.compare_pairs(
            corpus, [("grades_original.py", "prime_sieve.py"), ("grades_original.py", "missing.py")])
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)

    def test_tiny_files_warn(self):
        a = source_from_text("x = 1\n", "python", "a.py")
        b = source_from_text("x = 1\n", "python", "b.py")
        r = self.engine.compare_files(a, b)
        self.assertTrue(any("tiny" in w for w in r.warnings))

    def test_risk_thresholds(self):
        self.assertEqual(classify_risk(10, 30, 60), "Low")
        self.assertEqual(classify_risk(30, 30, 60), "Moderate")
        self.assertEqual(classify_risk(60, 30, 60), "High")

    def test_result_roundtrip(self):
        from src.models import ComparisonResult
        r = self.engine.compare_files(sample("QueueSimA.java"), sample("QueueSimB.java"))
        again = ComparisonResult.from_dict(r.to_dict())
        self.assertEqual(again, r)


if __name__ == "__main__":
    unittest.main()
