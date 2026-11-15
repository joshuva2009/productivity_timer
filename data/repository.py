"""Repository layer for tasks, focus sessions, and application settings."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Optional

from core.models import AppSettings, FocusSession, Task, TimerMode
from data.database import Database


class ProductivityRepository:
    """Transactional SQLite data access for Productivity Timer."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def load_settings(self) -> AppSettings:
        rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        raw: dict[str, object] = {}
        for row in rows:
            try:
                raw[row["key"]] = json.loads(row["value"])
            except json.JSONDecodeError:
                raw[row["key"]] = row["value"]

        defaults = AppSettings()
        loaded = AppSettings(
            focus_minutes=int(raw.get("focus_minutes", defaults.focus_minutes)),
            short_break_minutes=int(raw.get("short_break_minutes", defaults.short_break_minutes)),
            long_break_minutes=int(raw.get("long_break_minutes", defaults.long_break_minutes)),
            long_break_interval=int(raw.get("long_break_interval", defaults.long_break_interval)),
            daily_goal_minutes=int(raw.get("daily_goal_minutes", defaults.daily_goal_minutes)),
            theme=str(raw.get("theme", defaults.theme)),
            sound_enabled=bool(raw.get("sound_enabled", defaults.sound_enabled)),
            auto_start_break=bool(raw.get("auto_start_break", defaults.auto_start_break)),
        )
        return loaded.clamped()

    def save_settings(self, settings: AppSettings) -> AppSettings:
        clean = settings.clamped()
        payload = {
            "focus_minutes": clean.focus_minutes,
            "short_break_minutes": clean.short_break_minutes,
            "long_break_minutes": clean.long_break_minutes,
            "long_break_interval": clean.long_break_interval,
            "daily_goal_minutes": clean.daily_goal_minutes,
            "theme": clean.theme,
            "sound_enabled": clean.sound_enabled,
            "auto_start_break": clean.auto_start_break,
        }
        with self._conn:
            for key, value in payload.items():
                self._conn.execute(
                    """
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, json.dumps(value)),
                )
        return clean

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=int(row["id"]),
            title=str(row["title"]),
            completed=bool(row["completed"]),
            completed_sessions=int(row["completed_sessions"]),
            is_selected=bool(row["is_selected"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list_tasks(self) -> list[Task]:
        rows = self._conn.execute(
            """
            SELECT id, title, completed, completed_sessions, is_selected, created_at, updated_at
            FROM tasks
            ORDER BY completed ASC, is_selected DESC, id DESC
            """
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, task_id: int) -> Optional[Task]:
        row = self._conn.execute(
            """
            SELECT id, title, completed, completed_sessions, is_selected, created_at, updated_at
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        return self._row_to_task(row) if row is not None else None

    def get_selected_task(self) -> Optional[Task]:
        row = self._conn.execute(
            """
            SELECT id, title, completed, completed_sessions, is_selected, created_at, updated_at
            FROM tasks
            WHERE is_selected = 1
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        return self._row_to_task(row) if row is not None else None

    def create_task(self, title: str) -> Task:
        clean_title = " ".join(title.strip().split())
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO tasks (title, completed, completed_sessions, is_selected, created_at, updated_at)
                VALUES (?, 0, 0, 0, ?, ?)
                """,
                (clean_title, now, now),
            )
            task_id = int(cursor.lastrowid)
        task = self.get_task(task_id)
        assert task is not None
        return task

    def update_task_title(self, task_id: int, title: str) -> Optional[Task]:
        clean_title = " ".join(title.strip().split())
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE tasks SET title = ?, updated_at = ? WHERE id = ?",
                (clean_title, now, task_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_task(task_id)

    def toggle_task_completed(self, task_id: int) -> Optional[Task]:
        existing = self.get_task(task_id)
        if existing is None:
            return None
        new_completed = 0 if existing.completed else 1
        new_selected = 0 if new_completed == 1 else (1 if existing.is_selected else 0)
        now = datetime.now().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET completed = ?, is_selected = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_completed, new_selected, now, task_id),
            )
        return self.get_task(task_id)

    def select_task_for_focus(self, task_id: Optional[int]) -> Optional[Task]:
        now = datetime.now().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute("UPDATE tasks SET is_selected = 0 WHERE is_selected != 0")
            if task_id is not None:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET is_selected = 1, completed = 0, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, task_id),
                )
        return self.get_task(task_id) if task_id is not None else None

    def delete_task(self, task_id: int) -> bool:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def clear_completed_tasks(self) -> int:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM tasks WHERE completed = 1")
            return int(cursor.rowcount)

    # ------------------------------------------------------------------
    # Sessions (History preserved independently of task deletion)
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> FocusSession:
        return FocusSession(
            id=int(row["id"]),
            mode=TimerMode(str(row["mode"])),
            duration_seconds=int(row["duration_seconds"]),
            completed_at=str(row["completed_at"]),
            local_date=str(row["local_date"]),
            task_id=int(row["task_id"]) if row["task_id"] is not None else None,
            task_title=str(row["task_title"]) if row["task_title"] is not None else None,
        )

    def record_completed_session(
        self,
        mode: TimerMode,
        duration_seconds: int,
        task_id: Optional[int] = None,
        task_title: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> FocusSession:
        when = completed_at or datetime.now()
        completed_iso = when.isoformat(timespec="seconds")
        local_day = when.date().isoformat()
        clean_duration = max(1, int(duration_seconds))

        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO sessions (mode, duration_seconds, completed_at, local_date, task_id, task_title)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mode.value, clean_duration, completed_iso, local_day, task_id, task_title),
            )
            session_id = int(cursor.lastrowid)

            if mode is TimerMode.FOCUS and task_id is not None:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET completed_sessions = completed_sessions + 1,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (completed_iso, task_id),
                )

        row = self._conn.execute(
            """
            SELECT id, mode, duration_seconds, completed_at, local_date, task_id, task_title
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        assert row is not None
        return self._row_to_session(row)

    def list_sessions(self, since_date: Optional[date] = None) -> list[FocusSession]:
        if since_date is None:
            rows = self._conn.execute(
                """
                SELECT id, mode, duration_seconds, completed_at, local_date, task_id, task_title
                FROM sessions
                ORDER BY completed_at DESC, id DESC
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, mode, duration_seconds, completed_at, local_date, task_id, task_title
                FROM sessions
                WHERE local_date >= ?
                ORDER BY completed_at DESC, id DESC
                """,
                (since_date.isoformat(),),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def list_focus_sessions_since(self, since_date: date) -> list[FocusSession]:
        rows = self._conn.execute(
            """
            SELECT id, mode, duration_seconds, completed_at, local_date, task_id, task_title
            FROM sessions
            WHERE mode = ? AND local_date >= ?
            ORDER BY completed_at DESC, id DESC
            """,
            (TimerMode.FOCUS.value, since_date.isoformat()),
        ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_all_time_focus_totals(self) -> tuple[int, int]:
        """Return (total_focus_seconds, total_focus_sessions) across all history."""
        row = self._conn.execute(
            """
            SELECT COALESCE(SUM(duration_seconds), 0) AS total_seconds,
                   COUNT(*) AS total_count
            FROM sessions
            WHERE mode = ?
            """,
            (TimerMode.FOCUS.value,),
        ).fetchone()
        assert row is not None
        return int(row["total_seconds"]), int(row["total_count"])
