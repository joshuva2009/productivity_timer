"""Unit tests for SQLite persistence, tasks CRUD, session history, and real statistics."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from core.models import AppSettings, TimerMode
from data.database import Database
from data.repository import ProductivityRepository
from services.stats_service import StatisticsService


class TestPersistenceAndStatistics(unittest.TestCase):
    def test_settings_round_trip_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            db1 = Database(db_path)
            repo1 = ProductivityRepository(db1)

            custom = AppSettings(
                focus_minutes=50,
                short_break_minutes=10,
                long_break_minutes=20,
                long_break_interval=3,
                daily_goal_minutes=180,
                theme="dark",
                sound_enabled=False,
                auto_start_break=True,
            )
            repo1.save_settings(custom)
            db1.close()

            db2 = Database(db_path)
            repo2 = ProductivityRepository(db2)
            loaded = repo2.load_settings()
            db2.close()

            self.assertEqual(loaded, custom)

    def test_task_crud_selection_and_session_history_preservation(self) -> None:
        db = Database(":memory:")
        repo = ProductivityRepository(db)

        t1 = repo.create_task("  Draft architecture spec  ")
        self.assertEqual(t1.title, "Draft architecture spec")
        self.assertFalse(t1.completed)
        self.assertFalse(t1.is_selected)

        t2 = repo.create_task("Review pull requests")
        assert t1.id is not None and t2.id is not None

        # Only one task may be selected for focus at a time
        repo.select_task_for_focus(t1.id)
        self.assertEqual(repo.get_selected_task().id, t1.id)  # type: ignore[union-attr]
        repo.select_task_for_focus(t2.id)
        self.assertEqual(repo.get_selected_task().id, t2.id)  # type: ignore[union-attr]

        # Edit title
        updated = repo.update_task_title(t2.id, "Review PR #42")
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated.title, "Review PR #42")

        # Record completed focus session linked to task 2
        repo.record_completed_session(
            mode=TimerMode.FOCUS,
            duration_seconds=25 * 60,
            task_id=t2.id,
            task_title=updated.title,
        )
        refreshed_t2 = repo.get_task(t2.id)
        assert refreshed_t2 is not None
        self.assertEqual(refreshed_t2.completed_sessions, 1)

        # Delete the task; completed session history MUST be preserved!
        self.assertTrue(repo.delete_task(t2.id))
        self.assertIsNone(repo.get_task(t2.id))
        sessions = repo.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].task_title, "Review PR #42")
        self.assertEqual(sessions[0].duration_seconds, 25 * 60)

        # Toggle completed and clear completed
        repo.toggle_task_completed(t1.id)
        t1_after = repo.get_task(t1.id)
        assert t1_after is not None
        self.assertTrue(t1_after.completed)
        cleared = repo.clear_completed_tasks()
        self.assertEqual(cleared, 1)
        self.assertEqual(repo.list_tasks(), [])
        db.close()

    def test_statistics_aggregation_no_fake_data(self) -> None:
        db = Database(":memory:")
        repo = ProductivityRepository(db)
        stats = StatisticsService(repo)
        today = date(2026, 11, 14)

        # Empty DB must return exact zeros
        empty_summary = stats.get_summary(daily_goal_minutes=120, today=today)
        self.assertEqual(empty_summary.today_focus_seconds, 0)
        self.assertEqual(empty_summary.weekly_focus_seconds, 0)
        self.assertEqual(empty_summary.total_focus_seconds, 0)
        self.assertEqual(empty_summary.today_completed_sessions, 0)
        self.assertEqual(empty_summary.daily_goal_percent, 0)
        self.assertEqual(len(empty_summary.daily_series), 7)

        # Add sessions: 2 today (25m + 25m = 50m), 1 three days ago (30m), 1 ten days ago (40m), plus a break (5m)
        repo.record_completed_session(
            TimerMode.FOCUS,
            25 * 60,
            completed_at=datetime(2026, 11, 14, 9, 0, 0),
        )
        repo.record_completed_session(
            TimerMode.FOCUS,
            25 * 60,
            completed_at=datetime(2026, 11, 14, 10, 0, 0),
        )
        repo.record_completed_session(
            TimerMode.SHORT_BREAK,
            5 * 60,
            completed_at=datetime(2026, 11, 14, 10, 5, 0),
        )
        repo.record_completed_session(
            TimerMode.FOCUS,
            30 * 60,
            completed_at=datetime.combine(today - timedelta(days=3), datetime.min.time()),
        )
        repo.record_completed_session(
            TimerMode.FOCUS,
            40 * 60,
            completed_at=datetime.combine(today - timedelta(days=10), datetime.min.time()),
        )

        summary = stats.get_summary(daily_goal_minutes=100, today=today)
        # Breaks must NOT count toward focus totals
        self.assertEqual(summary.today_focus_seconds, 50 * 60)
        self.assertEqual(summary.today_completed_sessions, 2)
        self.assertEqual(summary.weekly_focus_seconds, 80 * 60)  # 50m + 30m
        self.assertEqual(summary.total_focus_seconds, 120 * 60)  # 50m + 30m + 40m
        self.assertEqual(summary.total_completed_sessions, 4)
        self.assertEqual(summary.daily_goal_percent, 50)
        self.assertEqual(summary.daily_series[-1].label, "Today")
        self.assertEqual(summary.daily_series[-1].focus_minutes, 50)
        db.close()


if __name__ == "__main__":
    unittest.main()
