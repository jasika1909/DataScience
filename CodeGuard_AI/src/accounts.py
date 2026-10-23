"""Accounts, role-based access control, assignments and submissions.

Security model
* Passwords: PBKDF2-HMAC-SHA256 with a random per-user salt; constant-time
  comparison; lock-out after repeated failures; generic error messages.
* Roles: ``teacher`` and ``student``. Every function here re-checks the acting
  user's role and ownership on the server side; hiding buttons in the UI is
  never the only protection.
* Students see only assignments created by the teacher who created their
  account, and only their own submission. Teachers see only their own
  assignments, students and submissions.
* Deleting data uses SQLite ``secure_delete`` plus VACUUM.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import sqlite3
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import config
from src import database
from src.database import DatabaseError
from src.models import SourceFile

_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
_DUMMY_HASH = None


class AccountError(ValueError):
    """A request that cannot be fulfilled; the message is safe to show."""


class PermissionDenied(PermissionError):
    """The acting user may not do this."""


@dataclass(frozen=True)
class User:
    id: int
    username: str
    display_name: str
    role: str
    is_admin: bool = False
    created_by: Optional[int] = None

    @property
    def is_teacher(self) -> bool:
        return self.role == config.ROLE_TEACHER


def _user_from_row(row) -> User:
    return User(id=row["id"], username=row["username"],
                display_name=row["display_name"], role=row["role"],
                is_admin=bool(row["is_admin"]), created_by=row["created_by"])


@contextmanager
def _tx(db_path: Optional[Path] = None):
    try:
        with closing(database._connect(db_path)) as conn:
            yield conn
            conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database operation failed: {exc}") from exc


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str, iterations: Optional[int] = None) -> str:
    iterations = iterations or config.PBKDF2_ITERATIONS
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return f"pbkdf2_sha256${iterations}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_b64, hash_b64 = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def validate_username(username: str) -> str:
    username = (username or "").strip()
    if not _USERNAME.match(username):
        raise AccountError("Usernames use 3-32 letters, digits, '.', '_' or '-'.")
    return username


def validate_password(password: str, username: str = "") -> None:
    if len(password or "") < config.MIN_PASSWORD_LENGTH:
        raise AccountError(f"Passwords need at least {config.MIN_PASSWORD_LENGTH} characters.")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise AccountError("Passwords need at least one letter and one digit.")
    if username and password.lower() == username.lower():
        raise AccountError("The password must differ from the username.")


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #
def log_event(user_id: Optional[int], action: str, detail: str = "",
              db_path: Optional[Path] = None) -> None:
    try:
        with _tx(db_path) as conn:
            conn.execute("INSERT INTO audit_log (ts, user_id, action, detail) VALUES (?,?,?,?)",
                         (database.now(), user_id, action, detail[:300]))
    except DatabaseError:
        pass


def recent_events(actor: User, limit: int = 20, db_path: Optional[Path] = None) -> list:
    with _tx(db_path) as conn:
        rows = conn.execute(
            "SELECT ts, action, detail FROM audit_log WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?", (actor.id, int(limit))).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
def user_count(db_path: Optional[Path] = None) -> int:
    with _tx(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def _insert_user(conn, username, display_name, password, role, is_admin, created_by) -> int:
    try:
        cur = conn.execute(
            """INSERT INTO users (username, display_name, role, is_admin,
               password_hash, created_by, created_at) VALUES (?,?,?,?,?,?,?)""",
            (username, display_name.strip()[:80] or username, role, int(is_admin),
             hash_password(password), created_by, database.now()))
    except sqlite3.IntegrityError as exc:
        raise AccountError("That username is already taken.") from exc
    return int(cur.lastrowid)


def create_first_teacher(username: str, display_name: str, password: str,
                         db_path: Optional[Path] = None) -> User:
    username = validate_username(username)
    validate_password(password, username)
    with _tx(db_path) as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            raise PermissionDenied("The first account has already been created.")
        uid = _insert_user(conn, username, display_name, password,
                           config.ROLE_TEACHER, True, None)
    log_event(uid, "account_created", "first teacher (admin)", db_path)
    return get_user(uid, db_path)


def list_usernames(db_path: Optional[Path] = None) -> list:
    with _tx(db_path) as conn:
        rows = conn.execute("SELECT username, role, is_admin, active FROM users "
                            "ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def reset_password_offline(username: str, new_password: str,
                           db_path: Optional[Path] = None) -> None:
    """Recovery for a forgotten password. Only used by reset_password.py,
    which needs access to this computer; it is not reachable from the web UI."""
    username = (username or "").strip()
    with _tx(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            raise AccountError("No account with that username.")
        validate_password(new_password, row["username"])
        conn.execute("UPDATE users SET password_hash = ?, failed_attempts = 0, "
                     "locked_until = 0, active = 1 WHERE id = ?",
                     (hash_password(new_password), row["id"]))
    log_event(row["id"], "password_reset_offline", "", db_path)


def get_user(user_id: int, db_path: Optional[Path] = None) -> Optional[User]:
    with _tx(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ? AND active = 1",
                           (int(user_id),)).fetchone()
    return _user_from_row(row) if row else None


def get_or_create_local_user(db_path: Optional[Path] = None) -> User:
    """Single-user mode (CODEGUARD_AUTH=off): an unguessable-password admin."""
    with _tx(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = 'local'").fetchone()
        if row is None:
            uid = _insert_user(conn, "local", "Local user", base64.b64encode(
                os.urandom(18)).decode() + "1a", config.ROLE_TEACHER, True, None)
            row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return _user_from_row(row)


def create_user(actor: User, username: str, display_name: str, password: str,
                role: str = config.ROLE_STUDENT, db_path: Optional[Path] = None) -> User:
    if not actor.is_teacher:
        raise PermissionDenied("Only teachers can create accounts.")
    if role not in (config.ROLE_STUDENT, config.ROLE_TEACHER):
        raise AccountError("Unknown role.")
    if role == config.ROLE_TEACHER and not actor.is_admin:
        raise PermissionDenied("Only the administrator can create teacher accounts.")
    username = validate_username(username)
    validate_password(password, username)
    with _tx(db_path) as conn:
        uid = _insert_user(conn, username, display_name, password, role, False, actor.id)
    log_event(actor.id, "account_created", f"{role} {username}", db_path)
    return get_user(uid, db_path)


def list_teachers(db_path: Optional[Path] = None) -> list:
    """Active teachers a new student can choose at sign-up (name and username only)."""
    with _tx(db_path) as conn:
        rows = conn.execute("SELECT id, username, display_name FROM users "
                            "WHERE role = 'teacher' AND active = 1 AND username != 'local' "
                            "ORDER BY display_name").fetchall()
    return [dict(r) for r in rows]


def register(role: str, username: str, display_name: str, password: str,
             teacher_id: Optional[int] = None, db_path: Optional[Path] = None) -> User:
    """Self-service sign-up for a teacher or a student.

    A student must choose the teacher whose assignments they will see. Teachers
    created this way are ordinary teachers (never administrators) and see only
    their own assignments and students.
    """
    if not config.ALLOW_SELF_SIGNUP:
        raise PermissionDenied("Self-registration is turned off. Ask your teacher "
                               "or the administrator for an account.")
    if role not in (config.ROLE_TEACHER, config.ROLE_STUDENT):
        raise AccountError("Choose whether you are a teacher or a student.")
    username = validate_username(username)
    validate_password(password, username)
    with _tx(db_path) as conn:
        created_by = None
        if role == config.ROLE_STUDENT:
            teacher = conn.execute(
                "SELECT id FROM users WHERE id = ? AND role = 'teacher' AND active = 1 "
                "AND username != 'local'", (teacher_id if teacher_id is not None else -1,)
            ).fetchone()
            if teacher is None:
                raise AccountError("Please choose your teacher.")
            created_by = teacher["id"]
        uid = _insert_user(conn, username, display_name, password, role, False, created_by)
    log_event(uid, "account_created", f"{role} (self sign-up)", db_path)
    return get_user(uid, db_path)


def authenticate(username: str, password: str, db_path: Optional[Path] = None) -> User:
    """Return the user or raise AccountError (with throttling)."""
    global _DUMMY_HASH
    generic = AccountError("Invalid username or password.")
    username = (username or "").strip()
    with _tx(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not row["active"]:
            if _DUMMY_HASH is None:
                _DUMMY_HASH = hash_password("dummy-password-1")
            verify_password(password or "", _DUMMY_HASH)     # equalise timing
            raise generic
        remaining = row["locked_until"] - time.time()
        if remaining > 0:
            raise AccountError(f"Too many failed attempts. Try again in "
                               f"{int(remaining // 60) + 1} minute(s).")
        if verify_password(password or "", row["password_hash"]):
            conn.execute("UPDATE users SET failed_attempts = 0, locked_until = 0 "
                         "WHERE id = ?", (row["id"],))
            user = _user_from_row(row)
            ok = True
        else:
            failed = row["failed_attempts"] + 1
            locked = 0.0
            if failed >= config.MAX_FAILED_LOGINS:
                locked, failed = time.time() + config.LOCKOUT_SECONDS, 0
            conn.execute("UPDATE users SET failed_attempts = ?, locked_until = ? "
                         "WHERE id = ?", (failed, locked, row["id"]))
            ok = False
    log_event(row["id"], "login" if ok else "login_failed", "", db_path)
    if not ok:
        raise generic
    return user


def change_password(actor: User, old_password: str, new_password: str,
                    db_path: Optional[Path] = None) -> None:
    validate_password(new_password, actor.username)
    with _tx(db_path) as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?",
                           (actor.id,)).fetchone()
        if row is None or not verify_password(old_password or "", row["password_hash"]):
            raise AccountError("The current password is not correct.")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (hash_password(new_password), actor.id))
    log_event(actor.id, "password_changed", "", db_path)


def _managed_student(conn, actor: User, student_id: int):
    if not actor.is_teacher:
        raise PermissionDenied("Only teachers can manage student accounts.")
    row = conn.execute("SELECT * FROM users WHERE id = ? AND role = 'student'",
                       (int(student_id),)).fetchone()
    if row is None or (row["created_by"] != actor.id and not actor.is_admin):
        raise PermissionDenied("You can only manage your own students.")
    return row


def list_students(actor: User, db_path: Optional[Path] = None) -> list:
    if not actor.is_teacher:
        raise PermissionDenied("Only teachers can list students.")
    sql = ("SELECT id, username, display_name, active, created_at FROM users "
           "WHERE role = 'student'" + ("" if actor.is_admin else " AND created_by = ?")
           + " ORDER BY username")
    with _tx(db_path) as conn:
        rows = conn.execute(sql, () if actor.is_admin else (actor.id,)).fetchall()
    return [dict(r) for r in rows]


def reset_student_password(actor: User, student_id: int, new_password: str,
                           db_path: Optional[Path] = None) -> None:
    with _tx(db_path) as conn:
        row = _managed_student(conn, actor, student_id)
        validate_password(new_password, row["username"])
        conn.execute("UPDATE users SET password_hash = ?, failed_attempts = 0, "
                     "locked_until = 0 WHERE id = ?",
                     (hash_password(new_password), row["id"]))
    log_event(actor.id, "student_password_reset", f"student {student_id}", db_path)


def set_student_active(actor: User, student_id: int, active: bool,
                       db_path: Optional[Path] = None) -> None:
    with _tx(db_path) as conn:
        row = _managed_student(conn, actor, student_id)
        conn.execute("UPDATE users SET active = ? WHERE id = ?", (int(active), row["id"]))
    log_event(actor.id, "student_active_changed", f"{student_id}={active}", db_path)


def _purge_user_data(conn, user_id: int) -> None:
    conn.execute("DELETE FROM submissions WHERE student_id = ?", (user_id,))
    conn.execute("DELETE FROM comparisons WHERE owner_id = ?", (user_id,))


def delete_student(actor: User, student_id: int, db_path: Optional[Path] = None) -> None:
    with _tx(db_path) as conn:
        row = _managed_student(conn, actor, student_id)
        _purge_user_data(conn, row["id"])
        conn.execute("UPDATE audit_log SET user_id = NULL WHERE user_id = ?", (row["id"],))
        conn.execute("DELETE FROM users WHERE id = ?", (row["id"],))
    log_event(actor.id, "student_deleted", f"student {student_id}", db_path)
    database.vacuum(db_path)


def delete_my_account(actor: User, password: str, db_path: Optional[Path] = None) -> None:
    """Students can erase their account, submissions and comparison history."""
    if actor.is_teacher:
        raise PermissionDenied("Teacher accounts are removed by the administrator.")
    with _tx(db_path) as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (actor.id,)).fetchone()
        if row is None or not verify_password(password or "", row["password_hash"]):
            raise AccountError("The password is not correct.")
        _purge_user_data(conn, actor.id)
        conn.execute("UPDATE audit_log SET user_id = NULL WHERE user_id = ?", (actor.id,))
        conn.execute("DELETE FROM users WHERE id = ?", (actor.id,))
    database.vacuum(db_path)


# --------------------------------------------------------------------------- #
# Assignments
# --------------------------------------------------------------------------- #
def _teacher_assignment(conn, actor: User, assignment_id: int):
    if not actor.is_teacher:
        raise PermissionDenied("Only teachers can manage assignments.")
    row = conn.execute("SELECT * FROM assignments WHERE id = ?", (int(assignment_id),)).fetchone()
    if row is None or row["teacher_id"] != actor.id:
        raise PermissionDenied("That assignment does not belong to you.")
    return row


def create_assignment(actor: User, title: str, description: str, language: str,
                      due_date: Optional[str] = None,
                      template: Optional[SourceFile] = None,
                      db_path: Optional[Path] = None) -> int:
    if not actor.is_teacher:
        raise PermissionDenied("Only teachers can create assignments.")
    title = (title or "").strip()
    if not title:
        raise AccountError("The assignment needs a title.")
    if language != "any" and language not in config.LANGUAGE_LABELS:
        raise AccountError("Unknown language.")
    if due_date:
        try:
            date.fromisoformat(due_date)
        except ValueError as exc:
            raise AccountError("The due date must look like 2026-12-31.") from exc
    with _tx(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO assignments (teacher_id, title, description, language,
               due_date, template_name, template_content, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (actor.id, title[:120], (description or "")[:2000], language,
             due_date or None, template.name if template else None,
             template.content if template else None, database.now()))
        aid = int(cur.lastrowid)
    log_event(actor.id, "assignment_created", title[:80], db_path)
    return aid


def list_assignments(actor: User, db_path: Optional[Path] = None) -> list:
    """Teachers: their own. Students: those of the teacher who made their account."""
    with _tx(db_path) as conn:
        teacher_id = actor.id if actor.is_teacher else actor.created_by
        rows = conn.execute(
            """SELECT a.id, a.title, a.description, a.language, a.due_date, a.closed,
                      a.template_name, a.created_at,
                      (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.id) AS submissions,
                      (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.id
                         AND s.student_id = ?) AS mine
               FROM assignments a WHERE a.teacher_id = ? ORDER BY a.id DESC""",
            (actor.id, teacher_id)).fetchall()
    out = [dict(r) for r in rows]
    if not actor.is_teacher:
        for r in out:
            r["submissions"] = r["mine"]       # students never see class counts
    return out


def set_assignment_closed(actor: User, assignment_id: int, closed: bool,
                          db_path: Optional[Path] = None) -> None:
    with _tx(db_path) as conn:
        row = _teacher_assignment(conn, actor, assignment_id)
        conn.execute("UPDATE assignments SET closed = ? WHERE id = ?", (int(closed), row["id"]))


def delete_assignment(actor: User, assignment_id: int, db_path: Optional[Path] = None) -> None:
    with _tx(db_path) as conn:
        row = _teacher_assignment(conn, actor, assignment_id)
        conn.execute("DELETE FROM submissions WHERE assignment_id = ?", (row["id"],))
        conn.execute("DELETE FROM comparisons WHERE assignment_id = ?", (row["id"],))
        conn.execute("DELETE FROM assignments WHERE id = ?", (row["id"],))
    log_event(actor.id, "assignment_deleted", str(assignment_id), db_path)
    database.vacuum(db_path)


# --------------------------------------------------------------------------- #
# Submissions
# --------------------------------------------------------------------------- #
def submit_file(actor: User, assignment_id: int, source: SourceFile,
                db_path: Optional[Path] = None) -> dict:
    """A student hands in (or replaces) their file for an assignment."""
    if actor.is_teacher:
        raise PermissionDenied("Only students submit work.")
    with _tx(db_path) as conn:
        a = conn.execute("SELECT * FROM assignments WHERE id = ? AND teacher_id = ?",
                         (int(assignment_id), actor.created_by)).fetchone()
        if a is None:
            raise PermissionDenied("That assignment is not available to you.")
        if a["closed"]:
            raise AccountError("This assignment is closed for submissions.")
        if a["language"] != "any" and a["language"] != source.language:
            raise AccountError(f"This assignment expects "
                               f"{config.LANGUAGE_LABELS[a['language']]} code.")
        late = int(bool(a["due_date"]) and date.today() > date.fromisoformat(a["due_date"]))
        conn.execute("DELETE FROM submissions WHERE assignment_id = ? AND student_id = ?",
                     (a["id"], actor.id))
        conn.execute(
            """INSERT INTO submissions (assignment_id, student_id, filename, language,
               content, sha256, line_count, submitted_at, late) VALUES (?,?,?,?,?,?,?,?,?)""",
            (a["id"], actor.id, source.name, source.language, source.content,
             source.sha256, source.line_count, database.now(), late))
    log_event(actor.id, "submitted", f"assignment {assignment_id}", db_path)
    database.vacuum(db_path)           # overwrite any replaced submission
    return {"late": bool(late)}


def my_submission(actor: User, assignment_id: int, db_path: Optional[Path] = None):
    """The acting student's own submission for an assignment, or None."""
    if actor.is_teacher:
        return None
    with _tx(db_path) as conn:
        row = conn.execute(
            """SELECT s.id, s.filename, s.language, s.line_count, s.submitted_at, s.late
               FROM submissions s JOIN assignments a ON a.id = s.assignment_id
               WHERE s.assignment_id = ? AND s.student_id = ? AND a.teacher_id = ?""",
            (int(assignment_id), actor.id, actor.created_by)).fetchone()
    return dict(row) if row else None


def list_submissions(actor: User, assignment_id: int, db_path: Optional[Path] = None) -> list:
    """Teacher: every submission of their assignment (metadata). Student: own only."""
    with _tx(db_path) as conn:
        if actor.is_teacher:
            _teacher_assignment(conn, actor, assignment_id)
            rows = conn.execute(
                """SELECT s.id, u.username, u.display_name, s.filename, s.language,
                          s.line_count, s.submitted_at, s.late
                   FROM submissions s JOIN users u ON u.id = s.student_id
                   WHERE s.assignment_id = ? ORDER BY u.username""",
                (int(assignment_id),)).fetchall()
        else:
            rows = conn.execute(
                """SELECT s.id, u.username, u.display_name, s.filename, s.language,
                          s.line_count, s.submitted_at, s.late
                   FROM submissions s JOIN users u ON u.id = s.student_id
                   JOIN assignments a ON a.id = s.assignment_id
                   WHERE s.assignment_id = ? AND s.student_id = ? AND a.teacher_id = ?""",
                (int(assignment_id), actor.id, actor.created_by)).fetchall()
    return [dict(r) for r in rows]


def get_submission_source(actor: User, submission_id: int,
                          db_path: Optional[Path] = None) -> SourceFile:
    """The code of one submission. Allowed for the student who submitted it and
    for the teacher who owns the assignment; nobody else."""
    from src.file_handler import sanitize_filename

    with _tx(db_path) as conn:
        row = conn.execute(
            """SELECT s.*, u.username, a.teacher_id FROM submissions s
               JOIN users u ON u.id = s.student_id
               JOIN assignments a ON a.id = s.assignment_id WHERE s.id = ?""",
            (int(submission_id),)).fetchone()
    if row is None:
        raise AccountError("That submission does not exist.")
    owner = row["student_id"] == actor.id
    teacher = actor.is_teacher and row["teacher_id"] == actor.id
    if not (owner or teacher):
        raise PermissionDenied("You may not view this submission.")
    if teacher and not owner:
        log_event(actor.id, "submission_viewed", f"submission {submission_id}", db_path)
    return SourceFile(name=sanitize_filename(f"{row['username']}__{row['filename']}"),
                      language=row["language"], content=row["content"],
                      size_bytes=len(row["content"].encode("utf-8")), sha256=row["sha256"],
                      line_count=row["line_count"], origin="submission")


def delete_submission(actor: User, submission_id: int, db_path: Optional[Path] = None) -> None:
    with _tx(db_path) as conn:
        row = conn.execute(
            """SELECT s.id, s.student_id, a.teacher_id FROM submissions s
               JOIN assignments a ON a.id = s.assignment_id WHERE s.id = ?""",
            (int(submission_id),)).fetchone()
        if row is None:
            raise AccountError("That submission does not exist.")
        owner = row["student_id"] == actor.id
        teacher = actor.is_teacher and row["teacher_id"] == actor.id
        if not (owner or teacher):
            raise PermissionDenied("You may not delete this submission.")
        conn.execute("DELETE FROM submissions WHERE id = ?", (row["id"],))
    log_event(actor.id, "submission_deleted", str(submission_id), db_path)
    database.vacuum(db_path)


def assignment_sources(actor: User, assignment_id: int, db_path: Optional[Path] = None):
    """(submissions as SourceFiles, template SourceFiles) for a teacher's batch run."""
    from src.file_handler import sanitize_filename

    with _tx(db_path) as conn:
        a = _teacher_assignment(conn, actor, assignment_id)
        rows = conn.execute(
            """SELECT u.username, s.filename, s.language, s.content, s.sha256, s.line_count
               FROM submissions s JOIN users u ON u.id = s.student_id
               WHERE s.assignment_id = ? ORDER BY u.username""", (a["id"],)).fetchall()
    files = [SourceFile(name=sanitize_filename(f"{r['username']}__{r['filename']}"),
                        language=r["language"], content=r["content"],
                        size_bytes=len(r["content"].encode("utf-8")), sha256=r["sha256"],
                        line_count=r["line_count"], origin="submission") for r in rows]
    templates = []
    if a["template_content"]:
        from src.file_handler import source_from_text
        lang = a["language"] if a["language"] != "any" else (files[0].language if files else "python")
        try:
            templates.append(source_from_text(a["template_content"], lang,
                                              a["template_name"] or "template", origin="template"))
        except ValueError:
            pass
    return files, templates


def assignment_overview(actor: User, db_path: Optional[Path] = None) -> list:
    """Per-assignment counts and the highest stored similarity (teacher only)."""
    if not actor.is_teacher:
        raise PermissionDenied("Only teachers have the assignment overview.")
    with _tx(db_path) as conn:
        rows = conn.execute(
            """SELECT a.id, a.title,
                 (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.id) AS submissions,
                 (SELECT COUNT(*) FROM comparisons c WHERE c.assignment_id = a.id) AS comparisons,
                 (SELECT MAX(overall) FROM comparisons c WHERE c.assignment_id = a.id) AS top,
                 (SELECT COUNT(*) FROM comparisons c WHERE c.assignment_id = a.id
                    AND c.risk = ?) AS high
               FROM assignments a WHERE a.teacher_id = ? ORDER BY a.id DESC""",
            (config.RISK_HIGH, actor.id)).fetchall()
    return [dict(r) for r in rows]
