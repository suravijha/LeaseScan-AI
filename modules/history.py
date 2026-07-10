"""
Local analysis history (SQLite).

Persists a lightweight record of each audit so the user can see past
analyses across sessions instead of losing everything on refresh.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "lease_history.db"


@contextmanager
def _connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                overall_score INTEGER NOT NULL,
                flag_count INTEGER NOT NULL,
                summary TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def record_analysis(filename: str, overall_score: int, flag_count: int, summary: str) -> None:
    with _connection() as conn:
        conn.execute(
            "INSERT INTO analyses (filename, overall_score, flag_count, summary, created_at) VALUES (?, ?, ?, ?, ?)",
            (filename, overall_score, flag_count, summary, datetime.now().isoformat(timespec="seconds")),
        )


def get_history(limit: int = 20) -> list[dict]:
    with _connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT filename, overall_score, flag_count, summary, created_at FROM analyses ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
