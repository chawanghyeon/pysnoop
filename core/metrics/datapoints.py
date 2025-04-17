# core/metrics/datapoints.py
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

DB_PATH = Path("db/metrics.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                uri TEXT NOT NULL,
                ts TEXT NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (uri, ts)
            )
        """
        )
        conn.commit()


def insert(uri: str, ts: datetime, value: float):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO metrics (uri, ts, value) VALUES (?, ?, ?)",
            (uri, ts.isoformat(), value),
        )
        conn.commit()


def get(uri: str) -> List[Tuple[datetime, float]]:
    with get_connection() as conn:
        cursor = conn.execute("SELECT ts, value FROM metrics WHERE uri = ? ORDER BY ts", (uri,))
        return [(datetime.fromisoformat(row[0]), row[1]) for row in cursor.fetchall()]


def get_latest(uri: str) -> Tuple[datetime, float] | None:
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT ts, value FROM metrics WHERE uri = ? ORDER BY ts DESC LIMIT 1",
            (uri,),
        )
        row = cursor.fetchone()
        return (datetime.fromisoformat(row[0]), row[1]) if row else None
