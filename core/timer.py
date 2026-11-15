"""Pure, UI-independent Pomodoro timer engine driven by time.monotonic()."""

from __future__ import annotations

import math
import time
from typing import Callable, Optional

from core.models import AppSettings, TimerCompletionEvent, TimerMode, TimerState


def format_duration_clock(seconds: float) -> str:
    """Format remaining seconds as MM:SS (ceiling so 24:59.1 displays 25:00 until 24:59.0)."""
    clamped = max(0.0, seconds)
    whole_seconds = int(math.ceil(clamped - 1e-6)) if clamped > 0.0 else 0
    minutes, secs = divmod(whole_seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def format_human_duration(total_seconds: int) -> str:
    """Format seconds into a concise editorial duration string (e.g., '1h 25m' or '45m')."""
    total_minutes = max(0, int(total_seconds) // 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h 0m"
    return f"{minutes}m"


class PomodoroTimerEngine:
    """Deterministic timer state machine using a monotonic clock.

    Never uses time.sleep() or UI primitives. Safe against duplicate starts,
    clock jitter, and arbitrary pause/resume/reset sequences.
    """

    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        cfg = (settings or AppSettings()).clamped()

        self._durations: dict[TimerMode, int] = {
            TimerMode.FOCUS: cfg.focus_minutes * 60,
            TimerMode.SHORT_BREAK: cfg.short_break_minutes * 60,
            TimerMode.LONG_BREAK: cfg.long_break_minutes * 60,
        }
        self._long_break_interval: int = cfg.long_break_interval
        self._auto_start_break: bool = cfg.auto_start_break

        self._mode: TimerMode = TimerMode.FOCUS
        self._state: TimerState = TimerState.IDLE
        self._completed_focus_in_cycle: int = 0

        self._elapsed_before_run: float = 0.0
        self._run_started_at: Optional[float] = None

    @property
    def mode(self) -> TimerMode:
        return self._mode

    @property
    def state(self) -> TimerState:
        return self._state

    @property
    def completed_focus_in_cycle(self) -> int:
        return self._completed_focus_in_cycle

    @property
    def long_break_interval(self) -> int:
        return self._long_break_interval

    @property
    def auto_start_break(self) -> bool:
        return self._auto_start_break

    def duration_for(self, mode: TimerMode) -> int:
        return self._durations[mode]

    def total_seconds(self) -> int:
        return self._durations[self._mode]

    def apply_settings(self, settings: AppSettings) -> None:
        """Apply updated settings safely without corrupting an active run."""
        cfg = settings.clamped()
        self._durations[TimerMode.FOCUS] = cfg.focus_minutes * 60
        self._durations[TimerMode.SHORT_BREAK] = cfg.short_break_minutes * 60
        self._durations[TimerMode.LONG_BREAK] = cfg.long_break_minutes * 60
        self._long_break_interval = cfg.long_break_interval
        self._auto_start_break = cfg.auto_start_break

        if self._state is TimerState.IDLE:
            self._elapsed_before_run = 0.0
            self._run_started_at = None

    def set_mode_duration_minutes(self, mode: TimerMode, minutes: int) -> None:
        """Update a single mode's duration in minutes."""
        max_min = 180 if mode is TimerMode.FOCUS else (90 if mode is TimerMode.LONG_BREAK else 60)
        clamped_minutes = max(1, min(max_min, int(minutes)))
        self._durations[mode] = clamped_minutes * 60

    def start(self) -> bool:
        """Start or resume the timer. Returns False if already running."""
        if self._state is TimerState.RUNNING:
            return False
        self._run_started_at = self._clock()
        self._state = TimerState.RUNNING
        return True

    def pause(self) -> bool:
        """Pause a running timer while preserving elapsed time accurately."""
        if self._state is not TimerState.RUNNING or self._run_started_at is None:
            return False
        now = self._clock()
        self._elapsed_before_run += max(0.0, now - self._run_started_at)
        self._run_started_at = None
        self._state = TimerState.PAUSED
        return True

    def toggle_start_pause(self) -> bool:
        """Toggle between running and paused/idle states. Returns True if now running."""
        if self._state is TimerState.RUNNING:
            self.pause()
            return False
        self.start()
        return True

    def reset(self) -> None:
        """Stop timer and restore the current mode to its full duration."""
        self._state = TimerState.IDLE
        self._elapsed_before_run = 0.0
        self._run_started_at = None

    def set_mode(self, mode: TimerMode) -> None:
        """Switch mode cleanly, stopping any running timer first."""
        self.reset()
        self._mode = mode

    def skip(self) -> TimerMode:
        """Skip the current phase without logging completion and advance to next phase."""
        current = self._mode
        self.reset()
        if current is TimerMode.FOCUS:
            next_mode = (
                TimerMode.LONG_BREAK
                if (self._completed_focus_in_cycle + 1) >= self._long_break_interval
                else TimerMode.SHORT_BREAK
            )
        else:
            next_mode = TimerMode.FOCUS
        self._mode = next_mode
        return next_mode

    def elapsed_seconds(self) -> float:
        """Return exact elapsed seconds for the current phase using monotonic clock."""
        if self._state is TimerState.RUNNING and self._run_started_at is not None:
            now = self._clock()
            return self._elapsed_before_run + max(0.0, now - self._run_started_at)
        return self._elapsed_before_run

    def remaining_seconds(self) -> float:
        """Return remaining seconds clamped to [0, total_seconds]."""
        return max(0.0, float(self.total_seconds()) - self.elapsed_seconds())

    def progress(self) -> float:
        """Return completion progress in [0.0, 1.0]."""
        total = float(max(1, self.total_seconds()))
        return min(1.0, max(0.0, self.elapsed_seconds() / total))

    def formatted_remaining(self) -> str:
        """Return MM:SS representation of remaining time."""
        return format_duration_clock(self.remaining_seconds())

    def tick(self) -> Optional[TimerCompletionEvent]:
        """Evaluate timer progress and emit a completion event if 00:00 has been reached."""
        if self._state is not TimerState.RUNNING:
            return None

        if self.remaining_seconds() > 0.0:
            return None

        completed_mode = self._mode
        completed_duration = self.total_seconds()

        self.reset()

        if completed_mode is TimerMode.FOCUS:
            self._completed_focus_in_cycle += 1
            if self._completed_focus_in_cycle >= self._long_break_interval:
                next_mode = TimerMode.LONG_BREAK
                self._completed_focus_in_cycle = 0
            else:
                next_mode = TimerMode.SHORT_BREAK
        else:
            next_mode = TimerMode.FOCUS

        self._mode = next_mode
        auto_started = False
        if completed_mode is TimerMode.FOCUS and self._auto_start_break:
            auto_started = self.start()

        return TimerCompletionEvent(
            completed_mode=completed_mode,
            duration_seconds=completed_duration,
            next_mode=next_mode,
            auto_started=auto_started,
        )
