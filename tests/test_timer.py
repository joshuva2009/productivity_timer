"""Unit tests for PomodoroTimerEngine accuracy, state transitions, and single-timer safety."""

from __future__ import annotations

import unittest

from core.models import AppSettings, TimerMode, TimerState
from core.timer import PomodoroTimerEngine, format_duration_clock, format_human_duration


class _FakeMonotonicClock:
    def __init__(self, initial: float = 1000.0) -> None:
        self.now = initial

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestPomodoroTimerEngine(unittest.TestCase):
    def test_default_durations(self) -> None:
        clock = _FakeMonotonicClock()
        engine = PomodoroTimerEngine(clock=clock)
        self.assertEqual(engine.mode, TimerMode.FOCUS)
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertEqual(engine.duration_for(TimerMode.FOCUS), 25 * 60)
        self.assertEqual(engine.duration_for(TimerMode.SHORT_BREAK), 5 * 60)
        self.assertEqual(engine.duration_for(TimerMode.LONG_BREAK), 15 * 60)
        self.assertEqual(engine.formatted_remaining(), "25:00")

    def test_monotonic_accuracy_across_pause_resume_reset(self) -> None:
        clock = _FakeMonotonicClock(initial=500.0)
        engine = PomodoroTimerEngine(clock=clock)

        self.assertTrue(engine.start())
        self.assertEqual(engine.state, TimerState.RUNNING)

        # Duplicate start while running must be rejected
        self.assertFalse(engine.start())

        clock.advance(10.25)
        self.assertAlmostEqual(engine.elapsed_seconds(), 10.25, places=6)
        self.assertAlmostEqual(engine.remaining_seconds(), 1500.0 - 10.25, places=6)
        self.assertEqual(engine.formatted_remaining(), "24:50")

        # Pause and advance clock; elapsed time must freeze
        self.assertTrue(engine.pause())
        self.assertEqual(engine.state, TimerState.PAUSED)
        clock.advance(120.0)
        self.assertAlmostEqual(engine.elapsed_seconds(), 10.25, places=6)
        self.assertEqual(engine.formatted_remaining(), "24:50")

        # Resume and advance 4.75s -> total elapsed 15.0s
        self.assertTrue(engine.start())
        clock.advance(4.75)
        self.assertAlmostEqual(engine.elapsed_seconds(), 15.0, places=6)
        self.assertEqual(engine.formatted_remaining(), "24:45")

        # Reset returns to full duration and IDLE
        engine.reset()
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertEqual(engine.elapsed_seconds(), 0.0)
        self.assertEqual(engine.formatted_remaining(), "25:00")

    def test_completion_transitions_and_long_break_cycle(self) -> None:
        clock = _FakeMonotonicClock()
        settings = AppSettings(
            focus_minutes=1,
            short_break_minutes=1,
            long_break_minutes=2,
            long_break_interval=2,
            auto_start_break=False,
        )
        engine = PomodoroTimerEngine(settings=settings, clock=clock)

        # Complete Focus #1 -> Short Break (idle because auto_start_break=False)
        engine.start()
        clock.advance(60.0)
        ev1 = engine.tick()
        self.assertIsNotNone(ev1)
        assert ev1 is not None
        self.assertEqual(ev1.completed_mode, TimerMode.FOCUS)
        self.assertEqual(ev1.duration_seconds, 60)
        self.assertEqual(ev1.next_mode, TimerMode.SHORT_BREAK)
        self.assertFalse(ev1.auto_started)
        self.assertEqual(engine.mode, TimerMode.SHORT_BREAK)
        self.assertEqual(engine.state, TimerState.IDLE)

        # Complete Short Break -> Focus
        engine.start()
        clock.advance(60.0)
        ev2 = engine.tick()
        self.assertIsNotNone(ev2)
        assert ev2 is not None
        self.assertEqual(ev2.completed_mode, TimerMode.SHORT_BREAK)
        self.assertEqual(ev2.next_mode, TimerMode.FOCUS)

        # Complete Focus #2 -> Long Break (interval=2)
        engine.start()
        clock.advance(60.0)
        ev3 = engine.tick()
        self.assertIsNotNone(ev3)
        assert ev3 is not None
        self.assertEqual(ev3.completed_mode, TimerMode.FOCUS)
        self.assertEqual(ev3.next_mode, TimerMode.LONG_BREAK)
        self.assertEqual(engine.completed_focus_in_cycle, 0)

    def test_auto_start_break_option(self) -> None:
        clock = _FakeMonotonicClock()
        settings = AppSettings(focus_minutes=1, short_break_minutes=5, auto_start_break=True)
        engine = PomodoroTimerEngine(settings=settings, clock=clock)

        engine.start()
        clock.advance(60.0)
        event = engine.tick()
        self.assertIsNotNone(event)
        assert event is not None
        self.assertTrue(event.auto_started)
        self.assertEqual(engine.mode, TimerMode.SHORT_BREAK)
        self.assertEqual(engine.state, TimerState.RUNNING)

    def test_skip_advances_without_recording_cycle_and_stops_running_timer(self) -> None:
        clock = _FakeMonotonicClock()
        engine = PomodoroTimerEngine(clock=clock)
        engine.start()
        clock.advance(30.0)
        next_mode = engine.skip()
        self.assertEqual(next_mode, TimerMode.SHORT_BREAK)
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertEqual(engine.completed_focus_in_cycle, 0)

    def test_custom_durations_and_formatting(self) -> None:
        settings = AppSettings(focus_minutes=45, short_break_minutes=10, long_break_minutes=30)
        engine = PomodoroTimerEngine(settings=settings)
        self.assertEqual(engine.formatted_remaining(), "45:00")
        self.assertEqual(format_duration_clock(0.0), "00:00")
        self.assertEqual(format_duration_clock(61.0), "01:01")
        self.assertEqual(format_human_duration(0), "0m")
        self.assertEqual(format_human_duration(45 * 60), "45m")
        self.assertEqual(format_human_duration(95 * 60), "1h 35m")


if __name__ == "__main__":
    unittest.main()
