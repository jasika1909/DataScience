"""Recover access when a password is forgotten.

Run from the project root with the virtual environment active:

    python reset_password.py

It lists the accounts, asks which one to reset and sets a new password.
Your data (history, assignments, submissions) is kept. This works only for
someone who can run programs on this computer, so it is not a web feature.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import accounts, database  # noqa: E402


def main() -> int:
    database.init_db()
    users = accounts.list_usernames()
    if not users:
        print("There are no accounts yet. Start the app and create the first one.")
        return 0
    print("Accounts:")
    for u in users:
        extra = " (administrator)" if u["is_admin"] else ""
        print(f"  {u['username']}  [{u['role']}]{extra}")
    username = input("\nUsername to reset: ").strip()
    new = getpass.getpass("New password (8+ characters, a letter and a digit): ")
    again = getpass.getpass("Repeat new password: ")
    if new != again:
        print("The passwords do not match. Nothing was changed.")
        return 1
    try:
        accounts.reset_password_offline(username, new)
    except accounts.AccountError as exc:
        print(f"Could not reset: {exc}")
        return 1
    print(f"Done. '{username}' can now sign in with the new password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
