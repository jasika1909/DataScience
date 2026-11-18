"""Tests for CSV/PDF reports and SQLite history."""
import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src import database as db
from src import report_generator as rg
from src.file_handler import load_from_path, source_from_text
from src.similarity_engine import SimilarityEngine

S = config.SAMPLES_DIR


class ReportAndDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = [load_from_path(S / n) for n in
                     ("grades_original.py", "grades_renamed.py", "prime_sieve.py")]
        engine = SimilarityEngine()
        corpus = engine.prepare(cls.files)
        cls.results, _ = engine.compare_pairs(
            corpus, engine.all_pairs([f.name for f in cls.files]))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.db"
        db.init_db(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_summary_csv_matches_results(self):
        rows = list(csv.DictReader(io.StringIO(rg.summary_csv(self.results).decode("utf-8-sig"))))
        self.assertEqual(len(rows), len(self.results))
        for row, r in zip(rows, self.results):
            self.assertEqual(float(row["overall_similarity_pct"]), r.overall)
            self.assertEqual(row["risk_indicator"], r.risk)

    def test_blocks_csv(self):
        rows = list(csv.DictReader(io.StringIO(rg.blocks_csv(self.results).decode("utf-8-sig"))))
        self.assertEqual(len(rows), sum(len(r.blocks) for r in self.results))

    def test_csv_formula_injection_neutralised(self):
        self.assertEqual(rg._safe("=1+1"), "'=1+1")
        self.assertEqual(rg._safe("ok.py"), "ok.py")

    @unittest.skipUnless(rg.pdf_available(), "reportlab not installed")
    def test_pdf_report(self):
        pdf = rg.pdf_report(self.results)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 2000)
        self.assertTrue(rg.pdf_report([]).startswith(b"%PDF"))

    def test_save_and_list_reports(self):
        p = rg.save_report(b"a,b\n", "my report!", "csv", Path(self.tmp.name))
        self.assertTrue(p.exists())
        self.assertEqual(rg.list_reports(Path(self.tmp.name)), [p])

    def test_database_roundtrip(self):
        a, b = self.files[0], self.files[1]
        res = self.results[0]
        cid = db.save_comparison(res, a, b, self.db_path)
        self.assertGreater(cid, 0)
        stats = db.get_stats(self.db_path)
        self.assertEqual(stats["comparisons"], 1)
        self.assertEqual(stats["files"], 2)
        self.assertEqual(stats["average"], round(res.overall, 1))
        self.assertEqual(db.get_result(cid, self.db_path), res)
        self.assertEqual(len(db.get_recent(5, self.db_path)), 1)
        # same files again: comparisons grow, unique files do not
        db.save_comparison(res, a, b, self.db_path)
        stats = db.get_stats(self.db_path)
        self.assertEqual((stats["comparisons"], stats["files"]), (2, 2))
        db.delete_comparison(cid, self.db_path)
        self.assertEqual(db.get_stats(self.db_path)["comparisons"], 1)
        db.clear_history(self.db_path)
        self.assertEqual(db.get_stats(self.db_path),
                         {"files": 0, "comparisons": 0, "average": 0.0, "high": 0})

    def test_empty_database_stats_and_missing_result(self):
        self.assertEqual(db.get_all(self.db_path), [])
        self.assertIsNone(db.get_result(999, self.db_path))

    def test_history_csv(self):
        db.save_comparison(self.results[0], self.files[0], self.files[1], self.db_path)
        data = rg.history_csv(db.get_all(self.db_path)).decode("utf-8-sig")
        self.assertIn("overall", data.splitlines()[0])
        self.assertEqual(len(data.strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
