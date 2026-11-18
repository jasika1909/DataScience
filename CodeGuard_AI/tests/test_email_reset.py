"""Tests for email registration and the forgot-password flow."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src import accounts as acc
from src import database as db
from src.accounts import AccountError, PermissionDenied

config.PBKDF2_ITERATIONS = 1000
PW = "Passw0rd!"
NEW = "Brandnew9x"


class EmailResetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "t.db"
        db.init_db(self.db)
        self.t1 = acc.create_first_teacher("teacher1", "Ms One", PW, self.db, email="Teacher.One@Example.com")
        self.s1 = acc.register("student", "alice", "Alice", PW, self.t1.id, self.db, email="alice@example.com")
        config.ALLOW_EMAIL_RESET = True

    def tearDown(self):
        config.ALLOW_EMAIL_RESET = True
        self.tmp.cleanup()

    def test_email_validation_and_normalisation(self):
        self.assertEqual(acc.validate_email("  Name@Example.COM "), "name@example.com")
        for bad in ("", "plain", "a@b", "a b@c.com", "@x.com", "x@.com", "a@b.c", "x" * 250 + "@a.com"):
            with self.assertRaises(AccountError):
                acc.validate_email(bad)
        self.assertEqual(self.t1.email, "teacher.one@example.com")

    def test_duplicate_email_is_rejected_case_insensitively(self):
        with self.assertRaises(AccountError) as ctx:
            acc.register("teacher", "other1", "O", PW, db_path=self.db, email="ALICE@example.com")
        self.assertIn("already registered", str(ctx.exception))
        with self.assertRaises(AccountError):
            acc.create_user(self.t1, "bob1", "Bob", PW, db_path=self.db, email="alice@example.com")

    def test_accounts_without_email_still_work(self):
        b = acc.create_user(self.t1, "bobby", "Bob", PW, db_path=self.db)
        self.assertIsNone(b.email)
        c = acc.create_user(self.t1, "carol1", "Carol", PW, db_path=self.db)
        self.assertIsNone(c.email)                                   # many NULL emails are allowed
        self.assertFalse(acc.email_is_registered("bob@example.com", self.db))

    def test_registered_and_unknown_email(self):
        self.assertTrue(acc.email_is_registered("alice@example.com", self.db))
        self.assertTrue(acc.email_is_registered("  ALICE@Example.com ", self.db))
        self.assertFalse(acc.email_is_registered("nobody@example.com", self.db))
        with self.assertRaises(AccountError):
            acc.email_is_registered("not-an-email", self.db)

    def test_deactivated_account_cannot_reset(self):
        acc.set_student_active(self.t1, self.s1.id, False, self.db)
        with self.assertRaises(AccountError) as ctx:
            acc.email_is_registered("alice@example.com", self.db)
        self.assertIn("deactivated", str(ctx.exception))
        with self.assertRaises(AccountError):
            acc.reset_password_by_email("alice@example.com", NEW, NEW, self.db)

    def test_mismatched_passwords_change_nothing(self):
        with self.assertRaises(AccountError) as ctx:
            acc.reset_password_by_email("alice@example.com", NEW, NEW + "x", self.db)
        self.assertIn("do not match", str(ctx.exception))
        self.assertEqual(acc.authenticate("alice", PW, self.db).id, self.s1.id)

    def test_matching_passwords_update_the_password(self):
        acc.reset_password_by_email("alice@example.com", NEW, NEW, self.db)
        self.assertEqual(acc.authenticate("alice", NEW, self.db).id, self.s1.id)
        with self.assertRaises(AccountError):
            acc.authenticate("alice", PW, self.db)
        raw = sqlite3.connect(self.db).execute("SELECT password_hash FROM users").fetchall()
        self.assertTrue(all(NEW not in r[0] for r in raw))
        self.assertIn("password_reset_email", [e["action"] for e in acc.recent_events(self.s1, 10, self.db)])

    def test_weak_new_password_is_rejected(self):
        for weak in ("short1", "alllettersonly", "12345678"):
            with self.assertRaises(AccountError):
                acc.reset_password_by_email("alice@example.com", weak, weak, self.db)
        self.assertEqual(acc.authenticate("alice", PW, self.db).id, self.s1.id)

    def test_reset_clears_a_lock_out(self):
        for _ in range(config.MAX_FAILED_LOGINS):
            with self.assertRaises(AccountError):
                acc.authenticate("alice", "wrongpass1", self.db)
        with self.assertRaises(AccountError):
            acc.authenticate("alice", PW, self.db)
        acc.reset_password_by_email("alice@example.com", NEW, NEW, self.db)
        self.assertEqual(acc.authenticate("alice", NEW, self.db).id, self.s1.id)

    def test_unregistered_email_gets_an_error(self):
        with self.assertRaises(AccountError) as ctx:
            acc.reset_password_by_email("nobody@example.com", NEW, NEW, self.db)
        self.assertIn("not registered", str(ctx.exception))

    def test_many_unknown_lookups_pause_the_check(self):
        for i in range(config.RESET_LOOKUP_MAX_FAILS):
            self.assertFalse(acc.email_is_registered(f"guess{i}@example.com", self.db))
        with self.assertRaises(AccountError) as ctx:
            acc.email_is_registered("alice@example.com", self.db)
        self.assertIn("Too many attempts", str(ctx.exception))
        with self.assertRaises(AccountError):
            acc.reset_password_by_email("alice@example.com", NEW, NEW, self.db)

    def test_feature_can_be_turned_off(self):
        config.ALLOW_EMAIL_RESET = False
        with self.assertRaises(PermissionDenied):
            acc.email_is_registered("alice@example.com", self.db)
        with self.assertRaises(PermissionDenied):
            acc.reset_password_by_email("alice@example.com", NEW, NEW, self.db)

    def test_set_email_needs_the_password_and_a_free_address(self):
        with self.assertRaises(AccountError):
            acc.set_email(self.s1, "wrong-pass1", "new@example.com", self.db)
        with self.assertRaises(AccountError):
            acc.set_email(self.s1, PW, "teacher.one@example.com", self.db)
        with self.assertRaises(AccountError):
            acc.set_email(self.s1, PW, "bad", self.db)
        acc.set_email(self.s1, PW, "Alice.New@Example.com", self.db)
        self.assertFalse(acc.email_is_registered("alice@example.com", self.db))
        self.assertTrue(acc.email_is_registered("alice.new@example.com", self.db))
        acc.set_email(self.s1, PW, "alice.new@example.com", self.db)
        self.assertEqual(acc.get_user(self.s1.id, self.db).email, "alice.new@example.com")

    def test_account_without_email_can_add_one_then_reset(self):
        bob = acc.create_user(self.t1, "bobby", "Bob", PW, db_path=self.db)
        acc.set_email(bob, PW, "bob@example.com", self.db)
        acc.reset_password_by_email("bob@example.com", NEW, NEW, self.db)
        self.assertEqual(acc.authenticate("bobby", NEW, self.db).id, bob.id)

    def test_old_database_gets_the_email_column(self):
        old = Path(self.tmp.name) / "old.db"
        conn = sqlite3.connect(old)
        conn.executescript("""CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE, display_name TEXT NOT NULL,
            role TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0, password_hash TEXT NOT NULL,
            created_by INTEGER, created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
            failed_attempts INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0);
            INSERT INTO users (username, display_name, role, is_admin, password_hash, created_at)
            VALUES ('legacy', 'Legacy', 'teacher', 1, 'x', '2026-01-01');""")
        conn.commit(); conn.close()
        db.init_db(old)
        conn = sqlite3.connect(old)
        self.assertIn("email", {r[1] for r in conn.execute("PRAGMA table_info(users)")})
        self.assertIsNone(conn.execute("SELECT email FROM users").fetchone()[0])
        conn.close()
        self.assertEqual(acc.get_user(1, old).username, "legacy")
        self.assertIsNone(acc.get_user(1, old).email)


if __name__ == "__main__":
    unittest.main()
