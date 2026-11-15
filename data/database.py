"""SQLite database management and schema initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union


def default_db_path() -> Path:
    """Return the default local SQLite database path inside data/."""
    return Path(__file__).resolve().parent / "productivity_timer.db"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    completed_sessions INTEGER NOT NULL DEFAULT 0,
    is_selected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    completed_at TEXT NOT NULL,
    local_date TEXT NOT NULL,
    task_id INTEGER NULL,
    task_title TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_local_date
    ON sessions (local_date, mode);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    """Thin, deterministic wrapper around standard-library sqlite3."""

    def __init__(self, db_path: Union[str, Path, None] = None) -> None:
        if db_path is None:
            resolved = str(default_db_path())
        else:
            resolved = str(db_path)

        if resolved != ":memory:":
            Path(resolved).parent.mkdir(parents=True, exist_ok=True)

        self._db_path = resolved
        self._conn = sqlite3.connect(self._db_path, check_same_thread=True)
        self._conn.row_factory = sqlite3.Row
        if self._db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    @property
    def path(self) -> str:
        return self._db_path

    def close(self) -> None:
        """Close the SQLite connection cleanly."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]
