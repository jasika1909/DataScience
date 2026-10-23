"""Local SQLite storage: comparison history, accounts, assignments, submissions.

Comparison history never stores source code, only names, hashes and results.
Submissions (student work handed in for an assignment) do store the code so a
teacher can compare them; they can be deleted by the student or the teacher.
Connections enable ``secure_delete`` so deleted content is overwritten.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from src.models import ComparisonResult, SourceFile

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
    is_admin INTEGER NOT NULL DEFAULT 0,
    password_hash TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL,
    due_date TEXT,
    closed INTEGER NOT NULL DEFAULT 0,
    template_name TEXT,
    template_content TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    language TEXT NOT NULL,
    content TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    line_count INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,
    late INTEGER NOT NULL DEFAULT 0,
    UNIQUE (assignment_id, student_id)
);
CREATE TABLE IF NOT EXISTS comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    owner_id INTEGER,
    assignment_id INTEGER,
    file_a TEXT NOT NULL,
    file_b TEXT NOT NULL,
    sha_a TEXT NOT NULL,
    sha_b TEXT NOT NULL,
    language_a TEXT NOT NULL,
    language_b TEXT NOT NULL,
    overall REAL NOT NULL,
    risk TEXT NOT NULL,
    matched_lines INTEGER NOT NULL,
    matched_blocks INTEGER NOT NULL,
    method TEXT NOT NULL,
    details_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    user_id INTEGER,
    action TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);
"""
_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_comparisons_created ON comparisons(created_at);
CREATE INDEX IF NOT EXISTS idx_comparisons_owner ON comparisons(owner_id);
CREATE INDEX IF NOT EXISTS idx_comparisons_assignment ON comparisons(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
"""


class DatabaseError(RuntimeError):
    pass


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA secure_delete = ON")
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _migrate(conn: sqlite3.Connection) -> None:
    """Upgrade a database created by an earlier version."""
    cols = _columns(conn, "comparisons")
    if "owner_id" not in cols:
        conn.execute("ALTER TABLE comparisons ADD COLUMN owner_id INTEGER")
    if "assignment_id" not in cols:
        conn.execute("ALTER TABLE comparisons ADD COLUMN assignment_id INTEGER")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def init_db(db_path: Optional[Path] = None) -> None:
    try:
        with closing(_connect(db_path)) as conn:
            conn.executescript(_SCHEMA)
            _migrate(conn)
            conn.executescript(_INDEXES)
            conn.commit()
    except (sqlite3.Error, OSError) as exc:
        raise DatabaseError(f"Could not initialise the history database: {exc}") from exc


def vacuum(db_path: Optional[Path] = None) -> None:
    """Rewrite the database file so deleted rows leave no residue."""
    try:
        conn = sqlite3.connect(Path(db_path or config.DB_PATH), isolation_level=None)
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()
    except sqlite3.Error:
        pass


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Comparison history (optionally scoped to an owner)
# --------------------------------------------------------------------------- #
def save_comparison(result: ComparisonResult, file_a: SourceFile,
                    file_b: SourceFile, db_path: Optional[Path] = None, *,
                    owner_id: Optional[int] = None,
                    assignment_id: Optional[int] = None) -> int:
    try:
        with closing(_connect(db_path)) as conn:
            cur = conn.execute(
                """INSERT INTO comparisons (created_at, owner_id, assignment_id,
                   file_a, file_b, sha_a, sha_b, language_a, language_b, overall,
                   risk, matched_lines, matched_blocks, method, details_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (now(), owner_id, assignment_id, result.file_a, result.file_b,
                 result.sha_a, result.sha_b, result.language_a, result.language_b,
                 result.overall, result.risk, result.matched_lines,
                 result.matched_blocks, result.method, json.dumps(result.to_dict())),
            )
            conn.commit()
            return int(cur.lastrowid)
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not save the comparison: {exc}") from exc


_LIST_COLUMNS = ("id, created_at, owner_id, assignment_id, file_a, file_b, language_a, "
                 "language_b, overall, risk, matched_lines, matched_blocks, method")


def _rows(sql: str, params: tuple = (), db_path: Optional[Path] = None) -> list:
    try:
        with closing(_connect(db_path)) as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database read failed: {exc}") from exc


def _scope(owner_id: Optional[int]) -> tuple:
    return ("WHERE owner_id = ?", (owner_id,)) if owner_id is not None else ("", ())


def get_recent(limit: int = 10, db_path: Optional[Path] = None, *,
               owner_id: Optional[int] = None) -> list:
    where, params = _scope(owner_id)
    return _rows(f"SELECT {_LIST_COLUMNS} FROM comparisons {where} "
                 "ORDER BY id DESC LIMIT ?", params + (int(limit),), db_path)


def get_all(db_path: Optional[Path] = None, *, owner_id: Optional[int] = None) -> list:
    where, params = _scope(owner_id)
    return _rows(f"SELECT {_LIST_COLUMNS} FROM comparisons {where} ORDER BY id DESC",
                 params, db_path)


def get_result(comparison_id: int, db_path: Optional[Path] = None, *,
               owner_id: Optional[int] = None) -> Optional[ComparisonResult]:
    sql = "SELECT details_json FROM comparisons WHERE id = ?"
    params: tuple = (int(comparison_id),)
    if owner_id is not None:
        sql += " AND owner_id = ?"
        params += (owner_id,)
    rows = _rows(sql, params, db_path)
    if not rows:
        return None
    return ComparisonResult.from_dict(json.loads(rows[0]["details_json"]))


def get_stats(db_path: Optional[Path] = None, *, owner_id: Optional[int] = None) -> dict:
    where, params = _scope(owner_id)
    row = _rows(
        f"SELECT COUNT(*) AS n, COALESCE(AVG(overall), 0) AS avg_score, "
        f"COALESCE(SUM(risk = ?), 0) AS high FROM comparisons {where}",
        (config.RISK_HIGH,) + params, db_path)[0]
    files = _rows(
        f"SELECT COUNT(*) AS n FROM (SELECT sha_a AS sha FROM comparisons {where} "
        f"UNION SELECT sha_b FROM comparisons {where})",
        params + params, db_path)[0]["n"]
    return {"files": int(files), "comparisons": int(row["n"]),
            "average": round(float(row["avg_score"]), 1), "high": int(row["high"])}


def delete_comparison(comparison_id: int, db_path: Optional[Path] = None, *,
                      owner_id: Optional[int] = None) -> None:
    sql = "DELETE FROM comparisons WHERE id = ?"
    params: tuple = (int(comparison_id),)
    if owner_id is not None:
        sql += " AND owner_id = ?"
        params += (owner_id,)
    try:
        with closing(_connect(db_path)) as conn:
            conn.execute(sql, params)
            conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not delete the comparison: {exc}") from exc


def clear_history(db_path: Optional[Path] = None, *,
                  owner_id: Optional[int] = None) -> None:
    where, params = _scope(owner_id)
    try:
        with closing(_connect(db_path)) as conn:
            conn.execute(f"DELETE FROM comparisons {where}", params)
            conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not clear the history: {exc}") from exc
    vacuum(db_path)
