"""Tests for accounts, roles, access control, submissions and deletion."""
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src import accounts as acc
from src import database as db
from src.accounts import AccountError, PermissionDenied
from src.file_handler import source_from_text
from src.similarity_engine import SimilarityEngine

config.PBKDF2_ITERATIONS = 1000          # fast hashing for tests only
PW = "Passw0rd!"


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "t.db"
        db.init_db(self.db)
        self.t1 = acc.create_first_teacher("teacher1", "Ms One", PW, self.db)
        self.t2 = acc.create_user(self.t1, "teacher2", "Mr Two", PW, config.ROLE_TEACHER, self.db)
        self.s1 = acc.create_user(self.t1, "alice", "Alice", PW, db_path=self.db)
        self.s2 = acc.create_user(self.t1, "bob", "Bob", PW, db_path=self.db)
        self.s3 = acc.create_user(self.t2, "carol", "Carol", PW, db_path=self.db)

    def tearDown(self):
        self.tmp.cleanup()

    # ---- passwords and login ------------------------------------------- #
    def test_password_hashing(self):
        h = acc.hash_password(PW)
        self.assertTrue(h.startswith("pbkdf2_sha256$"))
        self.assertNotIn(PW, h)
        self.assertTrue(acc.verify_password(PW, h))
        self.assertFalse(acc.verify_password("wrong", h))
        self.assertNotEqual(h, acc.hash_password(PW))          # random salt
        self.assertFalse(acc.verify_password(PW, "garbage"))

    def test_password_and_username_policy(self):
        for bad in ("short1", "alllettersonly", "12345678"):
            with self.assertRaises(AccountError):
                acc.validate_password(bad)
        with self.assertRaises(AccountError):
            acc.validate_password("alice123", "ALICE123")
        for bad in ("a", "has space", "bad/name", "x" * 40):
            with self.assertRaises(AccountError):
                acc.validate_username(bad)

    def test_passwords_are_not_stored_in_plain_text(self):
        raw = sqlite3.connect(self.db).execute("SELECT password_hash FROM users").fetchall()
        self.assertTrue(all(PW not in r[0] for r in raw))

    def test_authenticate_success_and_generic_failure(self):
        self.assertEqual(acc.authenticate("alice", PW, self.db).role, "student")
        self.assertEqual(acc.authenticate("ALICE", PW, self.db).username, "alice")   # case-insensitive
        for u, p in (("alice", "nope1234"), ("ghost", PW)):
            with self.assertRaises(AccountError) as ctx:
                acc.authenticate(u, p, self.db)
            self.assertEqual(str(ctx.exception), "Invalid username or password.")

    def test_lockout_after_repeated_failures(self):
        for _ in range(config.MAX_FAILED_LOGINS):
            with self.assertRaises(AccountError):
                acc.authenticate("alice", "wrongpass1", self.db)
        with self.assertRaises(AccountError) as ctx:
            acc.authenticate("alice", PW, self.db)            # even the right password
        self.assertIn("Too many failed attempts", str(ctx.exception))
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE users SET locked_until = ? WHERE username = 'alice'", (time.time() - 1,))
        conn.commit(); conn.close()
        self.assertEqual(acc.authenticate("alice", PW, self.db).username, "alice")

    def test_inactive_user_cannot_log_in(self):
        acc.set_student_active(self.t1, self.s1.id, False, self.db)
        with self.assertRaises(AccountError):
            acc.authenticate("alice", PW, self.db)

    def test_first_teacher_only_once_and_duplicates_rejected(self):
        with self.assertRaises(PermissionDenied):
            acc.create_first_teacher("another1", "X", PW, self.db)
        with self.assertRaises(AccountError):
            acc.create_user(self.t1, "ALICE", "Dup", PW, db_path=self.db)

    def test_offline_reset_recovers_account_and_keeps_data(self):
        a = acc.create_assignment(self.t1, "HW", "", "python", db_path=self.db)
        for _ in range(config.MAX_FAILED_LOGINS):
            with self.assertRaises(AccountError):
                acc.authenticate("teacher1", "forgotten1x", self.db)       # locked out
        names = [u["username"] for u in acc.list_usernames(self.db)]
        self.assertIn("teacher1", names)
        with self.assertRaises(AccountError):
            acc.reset_password_offline("nobody", "Newpass123", self.db)
        with self.assertRaises(AccountError):
            acc.reset_password_offline("teacher1", "weak", self.db)       # policy still applies
        acc.reset_password_offline("teacher1", "Newpass123", self.db)
        self.assertEqual(acc.authenticate("teacher1", "Newpass123", self.db).id, self.t1.id)
        with self.assertRaises(AccountError):
            acc.authenticate("teacher1", PW, self.db)                      # old password gone
        self.assertEqual([x["id"] for x in acc.list_assignments(self.t1, self.db)], [a])

    def test_self_signup_teacher(self):
        t = acc.register("teacher", "newteacher", "New T", PW, db_path=self.db)
        self.assertEqual((t.role, t.is_admin, t.created_by), ("teacher", False, None))
        self.assertEqual(acc.authenticate("newteacher", PW, self.db).id, t.id)
        a = acc.create_assignment(self.t1, "HW", "", "python", db_path=self.db)
        self.assertEqual(acc.list_assignments(t, self.db), [])              # separate from teacher1
        with self.assertRaises(PermissionDenied):
            acc.list_submissions(t, a, self.db)
        with self.assertRaises(PermissionDenied):
            acc.create_user(t, "someone1", "X", PW, config.ROLE_TEACHER, self.db)   # not an admin

    def test_self_signup_student_chooses_teacher(self):
        names = {x["username"] for x in acc.list_teachers(self.db)}
        self.assertEqual(names, {"teacher1", "teacher2"})
        a1 = acc.create_assignment(self.t1, "HW1", "", "python", db_path=self.db)
        a2 = acc.create_assignment(self.t2, "HW2", "", "python", db_path=self.db)
        s = acc.register("student", "dave", "Dave", PW, self.t2.id, self.db)
        self.assertEqual((s.role, s.created_by), ("student", self.t2.id))
        self.assertEqual([x["id"] for x in acc.list_assignments(s, self.db)], [a2])
        with self.assertRaises(PermissionDenied):
            acc.submit_file(s, a1, source_from_text("x = 1\nprint(x)\n", "python", "m.py"), self.db)
        self.assertIn("dave", [x["username"] for x in acc.list_students(self.t2, self.db)])
        other = acc.register("teacher", "teacher3", "Third", PW, db_path=self.db)    # ordinary teacher
        self.assertNotIn("dave", [x["username"] for x in acc.list_students(other, self.db)])
        with self.assertRaises(PermissionDenied):
            acc.reset_student_password(other, s.id, "Hijack1234", self.db)

    def test_signup_validation(self):
        for teacher in (None, 99999, self.s1.id):                         # missing, unknown, a student
            with self.assertRaises(AccountError):
                acc.register("student", "erin1", "E", PW, teacher, self.db)
        with self.assertRaises(AccountError):
            acc.register("admin", "erin1", "E", PW, db_path=self.db)       # unknown role
        with self.assertRaises(AccountError):
            acc.register("teacher", "alice", "E", PW, db_path=self.db)     # taken username
        with self.assertRaises(AccountError):
            acc.register("teacher", "erin1", "E", "weak", db_path=self.db)

    def test_signup_can_be_turned_off(self):
        config.ALLOW_SELF_SIGNUP = False
        try:
            with self.assertRaises(PermissionDenied):
                acc.register("teacher", "blocked1", "B", PW, db_path=self.db)
        finally:
            config.ALLOW_SELF_SIGNUP = True

    def test_deactivated_teacher_is_not_offered(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE users SET active = 0 WHERE username = 'teacher2'")
        conn.commit(); conn.close()
        self.assertEqual({x["username"] for x in acc.list_teachers(self.db)}, {"teacher1"})
        with self.assertRaises(AccountError):
            acc.register("student", "frank1", "F", PW, self.t2.id, self.db)

    def test_change_password(self):
        acc.change_password(self.s1, PW, "N3wpassword", self.db)
        self.assertEqual(acc.authenticate("alice", "N3wpassword", self.db).id, self.s1.id)
        with self.assertRaises(AccountError):
            acc.change_password(self.s1, "wrong-old1", "An0therpass", self.db)

    # ---- role checks ---------------------------------------------------- #
    def test_students_cannot_create_accounts_or_assignments(self):
        with self.assertRaises(PermissionDenied):
            acc.create_user(self.s1, "mallory1", "M", PW, db_path=self.db)
        with self.assertRaises(PermissionDenied):
            acc.create_assignment(self.s1, "Hack", "", "python", db_path=self.db)
        with self.assertRaises(PermissionDenied):
            acc.list_students(self.s1, self.db)

    def test_only_admin_creates_teachers(self):
        with self.assertRaises(PermissionDenied):
            acc.create_user(self.t2, "teacher3", "T3", PW, config.ROLE_TEACHER, self.db)

    def test_teacher_manages_only_own_students(self):
        self.assertEqual({s["username"] for s in acc.list_students(self.t2, self.db)}, {"carol"})
        with self.assertRaises(PermissionDenied):
            acc.reset_student_password(self.t2, self.s1.id, "Hijack123", self.db)
        with self.assertRaises(PermissionDenied):
            acc.delete_student(self.t2, self.s1.id, self.db)
        acc.reset_student_password(self.t1, self.s1.id, "Reset1234", self.db)
        self.assertEqual(acc.authenticate("alice", "Reset1234", self.db).id, self.s1.id)

    # ---- assignments and submissions ------------------------------------ #
    def make_assignment(self, teacher=None, language="python", **kw):
        return acc.create_assignment(teacher or self.t1, "HW1", "Sort a list", language,
                                     db_path=self.db, **kw)

    def src(self, text="x = 1\nprint(x)\n", name="main.py"):
        return source_from_text(text, "python", name)

    def test_student_sees_only_own_teachers_assignments(self):
        a1 = self.make_assignment(self.t1)
        a2 = self.make_assignment(self.t2)
        self.assertEqual([a["id"] for a in acc.list_assignments(self.s1, self.db)], [a1])
        self.assertEqual([a["id"] for a in acc.list_assignments(self.s3, self.db)], [a2])
        self.assertEqual([a["id"] for a in acc.list_assignments(self.t1, self.db)], [a1])
        with self.assertRaises(PermissionDenied):
            acc.submit_file(self.s1, a2, self.src(), self.db)

    def test_submit_replace_and_language_check(self):
        a = self.make_assignment()
        self.assertFalse(acc.submit_file(self.s1, a, self.src(), self.db)["late"])
        acc.submit_file(self.s1, a, self.src("y = 2\nprint(y)\n"), self.db)       # replaces
        subs = acc.list_submissions(self.t1, a, self.db)
        self.assertEqual(len(subs), 1)
        with self.assertRaises(AccountError):
            acc.submit_file(self.s1, a, source_from_text("int x;\n", "c", "a.c"), self.db)

    def test_closed_and_late_submissions(self):
        a = self.make_assignment(due_date="2000-01-01")
        self.assertTrue(acc.submit_file(self.s1, a, self.src(), self.db)["late"])
        acc.set_assignment_closed(self.t1, a, True, self.db)
        with self.assertRaises(AccountError):
            acc.submit_file(self.s2, a, self.src(), self.db)
        with self.assertRaises(AccountError):
            self.make_assignment(due_date="31/12/2026")

    def test_students_see_only_their_own_submission(self):
        a = self.make_assignment()
        acc.submit_file(self.s1, a, self.src("a = 1\nprint(a)\n"), self.db)
        acc.submit_file(self.s2, a, self.src("b = 2\nprint(b)\n"), self.db)
        mine = acc.list_submissions(self.s1, a, self.db)
        self.assertEqual([m["username"] for m in mine], ["alice"])
        self.assertEqual(len(acc.list_submissions(self.t1, a, self.db)), 2)
        with self.assertRaises(PermissionDenied):
            acc.list_submissions(self.t2, a, self.db)             # other teacher
        with self.assertRaises(PermissionDenied):
            acc.assignment_sources(self.s1, a, self.db)            # students never get code
        with self.assertRaises(PermissionDenied):
            acc.assignment_sources(self.t2, a, self.db)
        files, templates = acc.assignment_sources(self.t1, a, self.db)
        self.assertEqual(sorted(f.name for f in files), ["alice__main.py", "bob__main.py"])

    def test_viewing_submitted_code_is_access_controlled(self):
        a = self.make_assignment()
        text = "def hello():\n    return 'riya code'\n\nprint(hello())\n"
        acc.submit_file(self.s1, a, self.src(text, "main.py"), self.db)
        acc.submit_file(self.s2, a, self.src("y = 2\nprint(y)\n"), self.db)
        sub = next(x["id"] for x in acc.list_submissions(self.t1, a, self.db) if x["username"] == "alice")
        src = acc.get_submission_source(self.t1, sub, self.db)            # the teacher
        self.assertEqual(src.content, text)
        self.assertEqual(src.name, "alice__main.py")
        self.assertEqual(acc.get_submission_source(self.s1, sub, self.db).content, text)   # the owner
        with self.assertRaises(PermissionDenied):
            acc.get_submission_source(self.s2, sub, self.db)               # another student
        with self.assertRaises(PermissionDenied):
            acc.get_submission_source(self.t2, sub, self.db)               # another teacher
        with self.assertRaises(AccountError):
            acc.get_submission_source(self.t1, 99999, self.db)
        self.assertIn("submission_viewed", [e["action"] for e in acc.recent_events(self.t1, 10, self.db)])

    def test_batch_comparison_of_submissions(self):
        a = self.make_assignment(template=self.src("def main():\n    pass\n", "template.py"))
        code = "def total(items):\n    s = 0\n    for i in items:\n        s += i\n    return s\n\nprint(total([1, 2, 3]))\n"
        acc.submit_file(self.s1, a, self.src(code), self.db)
        acc.submit_file(self.s2, a, self.src(code.replace("items", "xs").replace("s", "acc")), self.db)
        files, templates = acc.assignment_sources(self.t1, a, self.db)
        self.assertEqual(len(templates), 1)
        engine = SimilarityEngine()
        corpus = engine.prepare(files, templates)
        res = engine.compare(corpus, files[0].name, files[1].name)
        self.assertGreaterEqual(res.overall, 60)

    def test_deleting_submissions(self):
        a = self.make_assignment()
        acc.submit_file(self.s1, a, self.src(), self.db)
        sub = acc.list_submissions(self.t1, a, self.db)[0]["id"]
        with self.assertRaises(PermissionDenied):
            acc.delete_submission(self.s2, sub, self.db)
        with self.assertRaises(PermissionDenied):
            acc.delete_submission(self.t2, sub, self.db)
        acc.delete_submission(self.s1, sub, self.db)               # owner may delete
        self.assertEqual(acc.list_submissions(self.t1, a, self.db), [])

    def test_deleted_code_is_gone_from_the_file(self):
        a = self.make_assignment()
        marker = "UNIQUE_MARKER_STRING_12345"
        acc.submit_file(self.s1, a, self.src(f"x = '{marker}'\nprint(x)\n"), self.db)
        self.assertIn(marker.encode(), self.db.read_bytes())
        acc.delete_submission(self.t1, acc.list_submissions(self.t1, a, self.db)[0]["id"], self.db)
        self.assertNotIn(marker.encode(), self.db.read_bytes())

    def test_delete_assignment_cascades(self):
        a = self.make_assignment()
        acc.submit_file(self.s1, a, self.src(), self.db)
        with self.assertRaises(PermissionDenied):
            acc.delete_assignment(self.t2, a, self.db)
        acc.delete_assignment(self.t1, a, self.db)
        self.assertEqual(acc.list_assignments(self.t1, self.db), [])
        self.assertIsNone(acc.my_submission(self.s1, a, self.db))

    def test_student_can_erase_own_account_and_data(self):
        a = self.make_assignment()
        acc.submit_file(self.s1, a, self.src(), self.db)
        res = SimilarityEngine().compare_files(self.src("x = 1\nprint(x)\n", "a.py"),
                                               self.src("y = 2\nprint(y)\n", "b.py"))
        db.save_comparison(res, self.src(), self.src(), self.db, owner_id=self.s1.id)
        with self.assertRaises(AccountError):
            acc.delete_my_account(self.s1, "wrong-pass1", self.db)
        acc.delete_my_account(self.s1, PW, self.db)
        self.assertEqual(db.get_all(self.db, owner_id=self.s1.id), [])
        self.assertEqual(acc.list_submissions(self.t1, a, self.db), [])
        with self.assertRaises(AccountError):
            acc.authenticate("alice", PW, self.db)
        with self.assertRaises(PermissionDenied):
            acc.delete_my_account(self.t1, PW, self.db)

    def test_overview_only_for_teachers(self):
        a = self.make_assignment()
        self.assertEqual(acc.assignment_overview(self.t1, self.db)[0]["id"], a)
        with self.assertRaises(PermissionDenied):
            acc.assignment_overview(self.s1, self.db)

    def test_audit_log_is_per_user(self):
        with self.assertRaises(AccountError):
            acc.authenticate("alice", "badpass123", self.db)
        acc.authenticate("alice", PW, self.db)
        actions = [e["action"] for e in acc.recent_events(self.s1, 10, self.db)]
        self.assertIn("login_failed", actions)
        self.assertIn("login", actions)
        self.assertNotIn("login", [e["action"] for e in acc.recent_events(self.s2, 10, self.db)])


class ScopedHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "t.db"
        db.init_db(self.db)
        e = SimilarityEngine()
        self.a = source_from_text("x = 1\nprint(x)\ny = 2\n", "python", "a.py")
        self.b = source_from_text("p = 1\nprint(p)\nq = 2\n", "python", "b.py")
        self.res = e.compare_files(self.a, self.b)

    def tearDown(self):
        self.tmp.cleanup()

    def test_history_is_isolated_per_owner(self):
        i1 = db.save_comparison(self.res, self.a, self.b, self.db, owner_id=1)
        i2 = db.save_comparison(self.res, self.a, self.b, self.db, owner_id=2)
        self.assertEqual([r["id"] for r in db.get_all(self.db, owner_id=1)], [i1])
        self.assertEqual(db.get_stats(self.db, owner_id=2)["comparisons"], 1)
        self.assertIsNone(db.get_result(i1, self.db, owner_id=2))      # not theirs
        self.assertIsNotNone(db.get_result(i1, self.db, owner_id=1))
        db.delete_comparison(i1, self.db, owner_id=2)                    # no effect
        self.assertEqual(len(db.get_all(self.db)), 2)
        db.clear_history(self.db, owner_id=1)
        self.assertEqual([r["id"] for r in db.get_all(self.db)], [i2])

    def test_old_database_is_migrated(self):
        old = Path(self.tmp.name) / "old.db"
        conn = sqlite3.connect(old)
        conn.executescript("""CREATE TABLE comparisons (id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT, file_a TEXT, file_b TEXT, sha_a TEXT, sha_b TEXT, language_a TEXT,
            language_b TEXT, overall REAL, risk TEXT, matched_lines INTEGER, matched_blocks INTEGER,
            method TEXT, details_json TEXT);
            INSERT INTO comparisons (created_at,file_a,file_b,sha_a,sha_b,language_a,language_b,overall,
            risk,matched_lines,matched_blocks,method,details_json) VALUES
            ('2026-01-01','a','b','s','t','python','python',50,'Moderate',1,1,'m','{}');""")
        conn.commit(); conn.close()
        db.init_db(old)
        rows = db.get_all(old)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["owner_id"])
        self.assertEqual(db.get_stats(old)["comparisons"], 1)


if __name__ == "__main__":
    unittest.main()
