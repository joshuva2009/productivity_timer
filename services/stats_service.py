"""Real statistics computation from persisted Focus session records."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from core.models import DayStat, StatisticsSummary
from data.repository import ProductivityRepository


class StatisticsService:
    """Computes genuine daily, weekly, and all-time focus metrics."""

    def __init__(self, repository: ProductivityRepository) -> None:
        self._repo = repository

    def get_summary(
        self,
        daily_goal_minutes: int,
        today: Optional[date] = None,
    ) -> StatisticsSummary:
        ref_today = today or date.today()
        week_start = ref_today - timedelta(days=6)

        recent_sessions = self._repo.list_focus_sessions_since(week_start)
        total_focus_seconds, total_completed_sessions = self._repo.get_all_time_focus_totals()

        seconds_by_day: dict[str, int] = defaultdict(int)
        count_by_day: dict[str, int] = defaultdict(int)

        for session in recent_sessions:
            if week_start.isoformat() <= session.local_date <= ref_today.isoformat():
                seconds_by_day[session.local_date] += session.duration_seconds
                count_by_day[session.local_date] += 1

        daily_series: list[DayStat] = []
        weekly_focus_seconds = 0
        for offset in range(7):
            current_day = week_start + timedelta(days=offset)
            iso = current_day.isoformat()
            secs = seconds_by_day.get(iso, 0)
            cnt = count_by_day.get(iso, 0)
            weekly_focus_seconds += secs
            is_today = current_day == ref_today
            label = "Today" if is_today else current_day.strftime("%a")
            daily_series.append(
                DayStat(
                    day=current_day,
                    label=label,
                    focus_seconds=secs,
                    session_count=cnt,
                    is_today=is_today,
                )
            )

        today_iso = ref_today.isoformat()
        today_focus_seconds = seconds_by_day.get(today_iso, 0)
        today_completed_sessions = count_by_day.get(today_iso, 0)

        return StatisticsSummary(
            today_focus_seconds=today_focus_seconds,
            weekly_focus_seconds=weekly_focus_seconds,
            total_focus_seconds=total_focus_seconds,
            today_completed_sessions=today_completed_sessions,
            total_completed_sessions=total_completed_sessions,
            daily_goal_minutes=max(1, int(daily_goal_minutes)),
            daily_series=tuple(daily_series),
        )
