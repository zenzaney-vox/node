from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any


@contextmanager
def _connect(database_path: Path):
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(database_path: Path) -> None:
    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS messages_session_id_id
                ON messages(session_id, id);
            """
        )


def create_session(database_path: Path, session_id: str) -> None:
    with _connect(database_path) as connection:
        connection.execute("INSERT INTO sessions (id) VALUES (?)", (session_id,))


def has_session(database_path: Path, session_id: str) -> bool:
    with _connect(database_path) as connection:
        row = connection.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row is not None


def load_messages(database_path: Path, session_id: str, limit: int | None = None) -> list[dict[str, str]]:
    with _connect(database_path) as connection:
        if limit is None:
            rows = connection.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        elif limit == 0:
            return []
        else:
            rows = connection.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content FROM messages
                    WHERE session_id = ? ORDER BY id DESC LIMIT ?
                ) ORDER BY id
                """,
                (session_id, limit),
            ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def append_turn(database_path: Path, session_id: str, user_message: str, assistant_message: str) -> None:
    with _connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            [
                (session_id, "user", user_message),
                (session_id, "assistant", assistant_message),
            ],
        )


def load_session(database_path: Path, session_id: str) -> dict[str, Any] | None:
    with _connect(database_path) as connection:
        session = connection.execute(
            "SELECT id, created_at FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if session is None:
            return None
        messages = connection.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return {
        "session_id": session["id"],
        "created_at": session["created_at"],
        "messages": [
            {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
            for row in messages
        ],
    }
