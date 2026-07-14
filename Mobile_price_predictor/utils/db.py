"""
utils/db.py
-----------
SQLite persistence layer for prediction history and price alerts.
"""

import os
import sqlite3

import pandas as pd

from utils.helper import BASE_DIR

DB_PATH = os.path.join(BASE_DIR, "data", "appraisals.db")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Create tables if they do not already exist."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        DATETIME DEFAULT CURRENT_TIMESTAMP,
                brand     TEXT,
                ram       INTEGER,
                storage   INTEGER,
                battery   INTEGER,
                camera    INTEGER,
                screen    REAL,
                fiveg     TEXT,
                age       REAL,
                condition TEXT,
                predicted REAL,
                listed    REAL,
                verdict   TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                brand     TEXT,
                ram       INTEGER,
                storage   INTEGER,
                condition TEXT,
                target    REAL,
                triggered INTEGER DEFAULT 0,
                created   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
def save_prediction(
    brand: str,
    ram: int,
    storage: int,
    battery: int,
    camera: int,
    screen: float,
    fiveg: str,
    age: float,
    condition: str,
    predicted: float,
    listed: float = 0.0,
    verdict: str = "",
) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO history
                (brand, ram, storage, battery, camera, screen,
                 fiveg, age, condition, predicted, listed, verdict)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brand, ram, storage, battery, camera, screen,
                fiveg, age, condition,
                round(predicted, 2), round(listed, 2), verdict,
            ),
        )
        con.commit()


def get_history(limit: int = 50) -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql(
            f"SELECT * FROM history ORDER BY ts DESC LIMIT {limit}", con
        )
    return df


# ---------------------------------------------------------------------------
# Price alerts
# ---------------------------------------------------------------------------
def add_alert(
    brand: str,
    ram: int,
    storage: int,
    condition: str,
    target_price: float,
) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO alerts (brand, ram, storage, condition, target) VALUES (?, ?, ?, ?, ?)",
            (brand, ram, storage, condition, round(target_price, 2)),
        )
        con.commit()


def get_alerts() -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql("SELECT * FROM alerts ORDER BY created DESC", con)
    return df


def check_and_trigger_alerts(
    current_brand: str,
    current_condition: str,
    current_price: float,
) -> list:
    """
    Check all untriggered alerts for the given brand/condition.
    Fire any whose target price >= current_price and return them.
    """
    triggered = []
    with _conn() as con:
        rows = con.execute(
            "SELECT id, brand, condition, target FROM alerts WHERE triggered = 0"
        ).fetchall()
        for row in rows:
            aid, brand, cond, target = row
            if (
                brand == current_brand
                and cond == current_condition
                and current_price <= target
            ):
                con.execute(
                    "UPDATE alerts SET triggered = 1 WHERE id = ?", (aid,)
                )
                triggered.append(
                    {"brand": brand, "condition": cond, "target": target}
                )
        con.commit()
    return triggered


def delete_alert(alert_id: int) -> None:
    with _conn() as con:
        con.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        con.commit()


# Initialise on import
init_db()
