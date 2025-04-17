# core/auth/users.py
import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path("db/users.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """
        )
        conn.commit()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(user_id: str, password: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (id, password) VALUES (?, ?)",
                (user_id, hash_password(password)),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(user_id: str, password: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
        return row[0] == hash_password(password)
