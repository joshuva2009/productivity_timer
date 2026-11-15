"""Domain models, enums, and settings structures for Productivity Timer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class TimerMode(str, Enum):
    """Supported timer phases."""

    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"

    @property
    def label(self) -> str:
        if self is TimerMode.FOCUS:
            return "Focus"
        if self is TimerMode.SHORT_BREAK:
            return "Short Break"
        return "Long Break"


class TimerState(str, Enum):
    """Execution states of the Pomodoro timer."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass(frozen=True)
class TimerCompletionEvent:
    """Emitted when a timer phase naturally reaches 00:00."""

    completed_mode: TimerMode
    duration_seconds: int
    next_mode: TimerMode
    auto_started: bool


@dataclass
class Task:
    """User task that can be tracked and attached to focus sessions."""

    id: Optional[int]
    title: str
    completed: bool = False
    completed_sessions: int = 0
    is_selected: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class FocusSession:
    """Persisted record of a completed timer phase."""

    id: Optional[int]
    mode: TimerMode
    duration_seconds: int
    completed_at: str
    local_date: str
    task_id: Optional[int] = None
    task_title: Optional[str] = None


@dataclass
class AppSettings:
    """Persisted application preferences and timer configuration."""

    focus_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    long_break_interval: int = 4
    daily_goal_minutes: int = 120
    theme: str = "light"
    sound_enabled: bool = True
    auto_start_break: bool = False

    def clamped(self) -> AppSettings:
        """Return a copy with all numeric and enum settings bounded to safe ranges."""
        theme = self.theme if self.theme in ("light", "dark") else "light"
        return AppSettings(
            focus_minutes=max(1, min(180, int(self.focus_minutes))),
            short_break_minutes=max(1, min(60, int(self.short_break_minutes))),
            long_break_minutes=max(1, min(90, int(self.long_break_minutes))),
            long_break_interval=max(2, min(10, int(self.long_break_interval))),
            daily_goal_minutes=max(10, min(720, int(self.daily_goal_minutes))),
            theme=theme,
            sound_enabled=bool(self.sound_enabled),
            auto_start_break=bool(self.auto_start_break),
        )


@dataclass(frozen=True)
class DayStat:
    """Focus statistics aggregated for a single calendar day."""

    day: date
    label: str
    focus_seconds: int
    session_count: int
    is_today: bool = False

    @property
    def focus_minutes(self) -> int:
        return self.focus_seconds // 60


@dataclass(frozen=True)
class StatisticsSummary:
    """Real aggregated statistics computed from completed session history."""

    today_focus_seconds: int
    weekly_focus_seconds: int
    total_focus_seconds: int
    today_completed_sessions: int
    total_completed_sessions: int
    daily_goal_minutes: int
    daily_series: tuple[DayStat, ...]

    @property
    def today_focus_minutes(self) -> int:
        return self.today_focus_seconds // 60

    @property
    def weekly_focus_minutes(self) -> int:
        return self.weekly_focus_seconds // 60

    @property
    def daily_goal_ratio(self) -> float:
        if self.daily_goal_minutes <= 0:
            return 0.0
        return min(1.0, self.today_focus_seconds / (self.daily_goal_minutes * 60.0))

    @property
    def daily_goal_percent(self) -> int:
        return int(round(self.daily_goal_ratio * 100))
