"""Tests for false-positive reduction, semantic/structural analysis, batch and reports."""
import io
import sys
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from config import Settings
from src import batch, report_generator as rg, structure_analyzer
from src.boilerplate import classify_line
from src.code_normalizer import normalize
from src.file_handler import (FileValidationError, load_from_path, load_zip,
                              source_from_text)
from src.semantic import canonicalize_line
from src.similarity_engine import SimilarityEngine

S = config.SAMPLES_DIR


def sample(name, rename=None):
    f = load_from_path(S / name)
    return replace(f, name=rename) if rename else f


JAVA_A = """import java.util.Scanner;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        int total = 0;
        for (int i = 0; i < n; i++) {
            total += i * 2;
        }
        System.out.println(total);
        sc.close();
    }
}
"""
JAVA_B = """import java.util.Scanner;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String word = sc.next();
        String rev = "";
        for (int k = word.length() - 1; k >= 0; k--) {
            rev = rev + word.charAt(k);
        }
        System.out.println(rev);
        sc.close();
    }
}
"""
STARTER = """import java.util.Scanner;
public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        int total = 0;
        sc.close();
    }
}
"""


class FalsePositiveTests(unittest.TestCase):
    def test_boilerplate_patterns(self):
        self.assertEqual(classify_line("if __name__ == __main__ :", "python"), "entry point")
        self.assertEqual(classify_line("int main ( ) {", "c"), "entry point")
        self.assertIsNone(classify_line("total = total + x", "python"))

    def test_boilerplate_reduces_score_between_unrelated_programs(self):
        a = source_from_text(JAVA_A, "java", "a.java")
        b = source_from_text(JAVA_B, "java", "b.java")
        on = SimilarityEngine(Settings(exclude_boilerplate=True)).compare_files(a, b)
        off = SimilarityEngine(Settings(exclude_boilerplate=False)).compare_files(a, b)
        self.assertLess(on.overall, off.overall - 10)
        self.assertIn("entry point", on.excluded_a)
        self.assertTrue(any("false-positive" in r for r in on.reasons))

    def test_template_code_is_excluded(self):
        a = source_from_text(JAVA_A, "java", "s1.java")
        b = source_from_text(JAVA_A.replace("i * 2", "i + 7"), "java", "s2.java")
        tmpl = source_from_text(STARTER, "java", "Template.java", origin="template")
        plain = SimilarityEngine().compare_files(a, b)
        with_t = SimilarityEngine().compare_files(a, b, [tmpl])
        self.assertLess(with_t.overall, plain.overall)
        self.assertEqual(with_t.excluded_a.get("instructor template code"), 3)

    def test_common_lines_across_many_submissions_are_excluded(self):
        shared = "def helper(x):\n    y = x * 2\n    z = y + 1\n    return z\n\n"
        files = []
        for i in range(7):
            body = f"def own{i}(v):\n    r = v + {i}\n    s = r * {i + 3}\n    return s - {i * 5}\n"
            files.append(source_from_text(shared + body, "python", f"s{i}.py"))
        engine = SimilarityEngine()
        corpus = engine.prepare(files)
        self.assertGreater(corpus.common_lines, 0)
        r = engine.compare(corpus, "s0.py", "s1.py")
        self.assertIn("common across submissions", r.excluded_a)
        off = SimilarityEngine(Settings(common_fraction=0.0))
        r2 = off.compare(off.prepare(files), "s0.py", "s1.py")
        self.assertNotIn("common across submissions", r2.excluded_a)
        self.assertGreater(r2.overall, r.overall)

    def test_real_copy_survives_common_filter_in_small_batch(self):
        files = [sample("grades_original.py"), sample("grades_renamed.py"), sample("prime_sieve.py")]
        engine = SimilarityEngine()
        corpus = engine.prepare(files)
        self.assertEqual(corpus.common_lines, 0)          # needs >= 6 files
        self.assertGreaterEqual(engine.compare(corpus, files[0].name, files[1].name).overall, 70)


class SemanticTests(unittest.TestCase):
    def canon(self, code, lang):
        n = normalize(code, lang)
        return [" ".join(canonicalize_line(l, lang)) for l in n.lines]

    def test_assignment_forms_unify(self):
        self.assertEqual(self.canon("i += 1\n", "python"), self.canon("i = i + 1\n", "python"))
        self.assertEqual(self.canon("i++;\n", "java"), self.canon("i = i + 1;\n", "java"))

    def test_loop_styles_unify_across_languages(self):
        py = self.canon("for i in range(n):\n    pass\n", "python")[0]
        java = self.canon("for (int i = 0; i < n; i++) {\n}\n", "java")[0]
        self.assertEqual(py, java)
        self.assertEqual(py, "LOOP RANGE ( ID )")

    def test_same_logic_different_style_scores_high_unrelated_low(self):
        e = SimilarityEngine()
        same = e.compare_files(sample("search_a.py"), sample("search_b.py"))
        other = e.compare_files(sample("search_a.py"), sample("prime_sieve.py"))
        self.assertGreaterEqual(same.signals["semantic"], 75)
        self.assertLess(other.signals["semantic"], 30)
        self.assertGreaterEqual(same.overall, 55)
        self.assertLess(other.overall, 25)

    def test_translated_code_is_detected_across_languages(self):
        e = SimilarityEngine()
        t = e.compare_files(sample("search_a.py"), sample("Search.java"))
        u = e.compare_files(sample("search_a.py"), sample("BankAccount.java"))
        self.assertGreaterEqual(t.overall, 60)
        self.assertEqual(t.risk, config.RISK_HIGH)
        self.assertTrue(any(b.kind == "semantic" for b in t.blocks))
        self.assertIsNone(t.signals["exact_lines"])
        self.assertLess(u.overall, 30)

    def test_identical_files_have_no_semantic_blocks(self):
        r = SimilarityEngine().compare_files(sample("search_a.py"), sample("search_a.py", "c.py"))
        self.assertEqual(r.semantic_lines, 0)


class StructureTests(unittest.TestCase):
    def info(self, name, lang):
        return structure_analyzer.build_info(normalize((S / name).read_text(), lang).tokens, lang)

    def test_java_functions_found_and_renames_ignored(self):
        i = self.info("QueueSimA.java", "java")
        self.assertTrue(i.ok)
        self.assertEqual({f.name for f in i.functions if len(f.seq) > 12},
                         {"serveNext", "averageWait", "main"})
        r = SimilarityEngine().compare_files(sample("QueueSimA.java"), sample("QueueSimB.java"))
        self.assertEqual(r.signals["ast"], 100.0)
        self.assertEqual(len(r.function_matches), 3)

    def test_c_and_cpp_and_js(self):
        for a, b in [("matrix_a.c", "matrix_b.c"), ("stack_a.cpp", "stack_b.cpp"),
                     ("cart_original.js", "cart_modified.js")]:
            r = SimilarityEngine().compare_files(sample(a), sample(b))
            self.assertGreaterEqual(r.signals["ast"], 70, (a, b))
            self.assertTrue(r.function_matches, (a, b))
        unrelated = SimilarityEngine().compare_files(sample("matrix_a.c"), sample("stack_a.cpp"))
        self.assertLess(unrelated.signals["ast"], 30)

    def test_unbalanced_braces_do_not_crash_or_hang(self):
        for code in ("int main( { {{ if (", "}}}} for(;;", "class { { ", "if (x) else else"):
            norm = normalize(code, "java")
            structure_analyzer.build_info(norm.tokens, "java")

    def test_deep_nesting_is_reported_not_raised(self):
        code = "{" * 400 + "x = 1;" + "}" * 400
        info = structure_analyzer.build_info(normalize(code, "java").tokens, "java")
        self.assertFalse(info.ok)


class ReasonsAndUniqueCodeTests(unittest.TestCase):
    def test_reasons_and_unique_ranges_present(self):
        a = sample("grades_original.py")
        mixed = a.content.split("def report")[0] + "def other(n):\n    r = []\n    for i in range(n):\n        r.append(i * i)\n    return r\n"
        b = source_from_text(mixed, "python", "mixed.py")
        r = SimilarityEngine().compare_files(a, b)
        self.assertTrue(r.reasons)
        self.assertTrue(any("matched block" in x for x in r.reasons))
        self.assertGreater(r.unique_lines_b, 0)
        self.assertTrue(r.unique_ranges_b)
        for start, end in r.unique_ranges_b:
            self.assertLessEqual(end, b.line_count)

    def test_swap_keeps_new_fields(self):
        r = SimilarityEngine().compare_files(sample("QueueSimA.java"), sample("QueueSimB.java"))
        sw = r.swapped()
        self.assertEqual(sw.unique_lines_a, r.unique_lines_b)
        self.assertEqual(sw.excluded_a, r.excluded_b)


class BatchAndPerformanceTests(unittest.TestCase):
    def setUp(self):
        names = ["grades_original.py", "grades_renamed.py", "grades_reformatted.py",
                 "prime_sieve.py", "search_a.py", "search_b.py"]
        self.files = [sample(n) for n in names]
        self.engine = SimilarityEngine()
        self.corpus = self.engine.prepare(self.files)
        self.results, _ = self.engine.compare_pairs(
            self.corpus, self.engine.all_pairs([f.name for f in self.files]))

    def test_top_pairs_and_clusters(self):
        top = batch.top_pairs(self.results, 3)
        self.assertGreaterEqual(top[0].overall, top[1].overall)
        clusters = batch.find_clusters(self.results, 60)
        sets = [set(c["files"]) for c in clusters]
        self.assertIn({"grades_original.py", "grades_renamed.py", "grades_reformatted.py"}, sets)
        self.assertIn({"search_a.py", "search_b.py"}, sets)
        self.assertFalse(any("prime_sieve.py" in s for s in sets))

    def test_clusters_do_not_chain_into_one_giant_group(self):
        from src.models import ComparisonResult
        def edge(a, b, score):
            return ComparisonResult(file_a=a, file_b=b, language_a="python", language_b="python",
                                    sha_a="", sha_b="", method="", method_note="", signals={},
                                    weights_used={}, overall=score, risk="High",
                                    significant_lines_a=1, significant_lines_b=1, matched_lines=0)
        names = [f"f{i}" for i in range(14)]
        chain = [edge(names[i], names[i + 1], 70) for i in range(13)]       # weak chain
        strong = [edge("f0", "f1", 97), edge("f1", "f2", 97), edge("f0", "f2", 97)]
        groups = batch.find_clusters(chain + strong[:1] + strong[1:], 60)
        self.assertTrue(groups)
        self.assertTrue(all(len(g["files"]) <= 10 or g["loose"] for g in groups))
        core = [g for g in groups if set(g["files"]) == {"f0", "f1", "f2"}]
        self.assertTrue(core and not core[0]["loose"] and core[0]["threshold"] > 60)
        loose = batch.find_clusters(chain, 60)
        self.assertEqual(len(loose), 1)
        self.assertTrue(loose[0]["loose"])

    def test_matrix_and_ordering(self):
        names = [f.name for f in self.files]
        z = batch.similarity_matrix(names, self.results)
        self.assertEqual(z[0][0], 100.0)
        self.assertEqual(z[0][1], z[1][0])
        order = batch.cluster_order(names, self.results)
        self.assertEqual(sorted(order), sorted(names))
        pos = {n: i for i, n in enumerate(order)}
        grades = [pos[n] for n in names[:3]]
        self.assertLessEqual(max(grades) - min(grades), 2)       # kept adjacent

    def test_summary_text(self):
        info = batch.summarize(self.results)
        self.assertEqual(info["pairs"], 15)
        self.assertIn("highest pair", info["text"])
        self.assertEqual(batch.summarize([])["pairs"], 0)

    def test_cache_is_used_on_repeat(self):
        e = SimilarityEngine()
        c = e.prepare(self.files)
        pairs = e.all_pairs([f.name for f in self.files])
        first, _ = e.compare_pairs(c, pairs)
        misses = e.cache_misses
        again, _ = e.compare_pairs(c, pairs)
        self.assertEqual(e.cache_misses, misses)
        self.assertEqual(e.cache_hits, len(pairs))
        self.assertEqual([r.overall for r in first], [r.overall for r in again])
        # a second analysis re-uses normalized documents
        c2 = e.prepare(self.files)
        self.assertEqual(len(c2.docs), len(self.files))

    def test_quick_screen_skips_unrelated_pairs_but_flags_copies(self):
        files = [source_from_text(f"def f{i}(a):\n    return a * {i} + {i * 3}\n\ndef g{i}(b, c):\n"
                                  f"    if b > c:\n        return b - {i}\n    return c\n", "python", f"u{i}.py")
                 for i in range(3)]
        files += [sample("grades_original.py"), sample("grades_renamed.py"), sample("prime_sieve.py"),
                  sample("search_a.py"), sample("search_b.py"), sample("grades_reformatted.py")]
        e = SimilarityEngine()
        c = e.prepare(files)
        pairs = e.all_pairs([f.name for f in files])
        self.assertGreaterEqual(len(pairs), config.SCREEN_MIN_PAIRS)
        results, _ = e.compare_pairs(c, pairs)
        self.assertGreater(e.last_run["screened"], 0)
        by = {(r.file_a, r.file_b): r for r in results}
        copy = by[("grades_original.py", "grades_renamed.py")]
        self.assertFalse(copy.quick_only)
        self.assertGreaterEqual(copy.overall, 70)
        self.assertTrue(any(r.quick_only for r in results))
        off = SimilarityEngine(Settings(screen_threshold=0))
        none, _ = off.compare_pairs(off.prepare(files), pairs)
        self.assertFalse(any(r.quick_only for r in none))

    def test_time_budget_stops_and_reports(self):
        e = SimilarityEngine(Settings(time_budget_s=0.0))
        c = e.prepare(self.files)
        results, _ = e.compare_pairs(c, e.all_pairs([f.name for f in self.files]))
        self.assertLess(len(results), 15)
        self.assertGreater(e.last_run["skipped"], 0)


class ZipTests(unittest.TestCase):
    def make_zip(self, entries):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name, data in entries.items():
                z.writestr(name, data)
        return buf.getvalue()

    def test_zip_of_student_folders(self):
        data = self.make_zip({"alice/main.py": "x = 1\nprint(x)\n", "bob/main.py": "y = 2\nprint(y)\n",
                              "readme.txt": "hello", "__MACOSX/x.py": "x=1", "carol/empty.py": ""})
        sources, errors, skipped = load_zip("subs.zip", data)
        self.assertEqual(sorted(s.name for s in sources), ["alice__main.py", "bob__main.py"])
        self.assertEqual(skipped, 2)
        self.assertEqual(len(errors), 1)

    def test_corrupt_and_oversized_zip(self):
        with self.assertRaises(FileValidationError):
            load_zip("bad.zip", b"this is not a zip")
        entries = {f"s{i}/a.py": "x = 1\n" for i in range(config.MAX_ZIP_ENTRIES + 1)}
        with self.assertRaises(FileValidationError):
            load_zip("many.zip", self.make_zip(entries))

    def test_path_traversal_names_are_flattened(self):
        data = self.make_zip({"../../evil/main.py": "x = 1\nprint(x)\n"})
        sources, _, skipped = load_zip("t.zip", data)
        self.assertEqual(sources, [])            # '..' entries are never read
        self.assertEqual(skipped, 1)
        data = self.make_zip({"a/b/../c/main.py": "x = 1\nprint(x)\n"})
        sources, _, _ = load_zip("t.zip", data)
        self.assertTrue(all("/" not in s.name for s in sources))


class ReportTests(unittest.TestCase):
    @unittest.skipUnless(rg.pdf_available(), "reportlab not installed")
    def test_pdf_has_snippets_and_charts_content(self):
        files = [sample("grades_original.py"), sample("grades_renamed.py"), sample("prime_sieve.py")]
        e = SimilarityEngine()
        c = e.prepare(files)
        results, _ = e.compare_pairs(c, e.all_pairs([f.name for f in files]))
        with_src = rg.pdf_report(results, sources={f.name: f for f in files})
        without = rg.pdf_report(results)
        self.assertTrue(with_src.startswith(b"%PDF"))
        self.assertGreater(len(with_src), len(without))          # snippets add content

    def test_csv_includes_reasons_and_unique_columns(self):
        r = SimilarityEngine().compare_files(sample("QueueSimA.java"), sample("QueueSimB.java"))
        header = rg.summary_csv([r]).decode("utf-8-sig").splitlines()[0]
        for col in ("unique_lines_a", "excluded_lines_a", "reasons", "semantic_pct"):
            self.assertIn(col, header)


if __name__ == "__main__":
    unittest.main()
