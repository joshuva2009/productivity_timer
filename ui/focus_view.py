"""Focus screen: circular countdown timer, controls, duration selector, and daily summary."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from core.models import AppSettings, StatisticsSummary, Task, TimerMode, TimerState
from core.timer import format_human_duration
from ui.theme import ThemePalette, Typography
from ui.widgets import (
    CircularTimerCanvas,
    GoalProgressBarCanvas,
    LuxuryButton,
    SegmentedControl,
)


class _DurationStepper(tk.Frame):
    """Minimal inline duration selector (- / 25m / +) with click-to-edit custom input."""

    def __init__(
        self,
        master: tk.Misc,
        label: str,
        minutes: int,
        min_val: int,
        max_val: int,
        on_change: Callable[[int], None],
        theme: ThemePalette,
        fonts: Typography,
    ) -> None:
        super().__init__(master, bg=theme.surface, highlightthickness=1, highlightbackground=theme.border)
        self._label_text = label
        self._minutes = minutes
        self._min_val = min_val
        self._max_val = max_val
        self._on_change = on_change
        self._theme = theme
        self._fonts = fonts
        self._editing = False

        self.configure(padx=12, pady=8)

        self._title_lbl = tk.Label(
            self,
            text=label.upper(),
            font=fonts.caption_bold(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._title_lbl.pack(side=tk.TOP, anchor="center")

        controls = tk.Frame(self, bg=theme.surface)
        controls.pack(side=tk.TOP, pady=(4, 0))
        self._controls_frame = controls

        self._minus_btn = tk.Label(
            controls,
            text="−",
            font=fonts.body_medium(),
            fg=theme.text_secondary,
            bg=theme.surface,
            cursor="hand2",
            padx=6,
        )
        self._minus_btn.pack(side=tk.LEFT)
        self._minus_btn.bind("<Button-1>", lambda _e: self._step(-1))

        self._value_lbl = tk.Label(
            controls,
            text=f"{minutes}m",
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
            cursor="hand2",
            width=5,
        )
        self._value_lbl.pack(side=tk.LEFT)
        self._value_lbl.bind("<Button-1>", self._begin_edit)

        self._entry_var = tk.StringVar(value=str(minutes))
        self._entry = tk.Entry(
            controls,
            textvariable=self._entry_var,
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.input_bg,
            insertbackground=theme.text_primary,
            relief=tk.FLAT,
            justify="center",
            width=5,
            highlightthickness=1,
            highlightbackground=theme.accent_focus,
            highlightcolor=theme.accent_focus,
        )
        self._entry.bind("<Return>", self._commit_edit)
        self._entry.bind("<Escape>", self._cancel_edit)
        self._entry.bind("<FocusOut>", self._commit_edit)

        self._plus_btn = tk.Label(
            controls,
            text="+",
            font=fonts.body_medium(),
            fg=theme.text_secondary,
            bg=theme.surface,
            cursor="hand2",
            padx=6,
        )
        self._plus_btn.pack(side=tk.LEFT)
        self._plus_btn.bind("<Button-1>", lambda _e: self._step(1))

    def set_minutes(self, minutes: int) -> None:
        self._minutes = max(self._min_val, min(self._max_val, int(minutes)))
        self._value_lbl.configure(text=f"{self._minutes}m")
        if not self._editing:
            self._entry_var.set(str(self._minutes))

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self.configure(bg=theme.surface, highlightbackground=theme.border)
        self._controls_frame.configure(bg=theme.surface)
        self._title_lbl.configure(fg=theme.text_muted, bg=theme.surface)
        self._minus_btn.configure(fg=theme.text_secondary, bg=theme.surface)
        self._plus_btn.configure(fg=theme.text_secondary, bg=theme.surface)
        self._value_lbl.configure(fg=theme.text_primary, bg=theme.surface)
        self._entry.configure(
            fg=theme.text_primary,
            bg=theme.input_bg,
            insertbackground=theme.text_primary,
            highlightbackground=theme.accent_focus,
            highlightcolor=theme.accent_focus,
        )

    def _step(self, delta: int) -> None:
        next_val = max(self._min_val, min(self._max_val, self._minutes + delta))
        if next_val != self._minutes:
            self.set_minutes(next_val)
            self._on_change(next_val)

    def _begin_edit(self, _event: tk.Event) -> None:
        if self._editing:
            return
        self._editing = True
        self._entry_var.set(str(self._minutes))
        self._value_lbl.pack_forget()
        self._entry.pack(side=tk.LEFT, before=self._plus_btn)
        self._entry.focus_set()
        self._entry.select_range(0, tk.END)

    def _commit_edit(self, _event: Optional[tk.Event] = None) -> None:
        if not self._editing:
            return
        raw = self._entry_var.get().strip()
        self._editing = False
        self._entry.pack_forget()
        self._value_lbl.pack(side=tk.LEFT, before=self._plus_btn)
        try:
            parsed = int(raw)
        except ValueError:
            return
        clamped = max(self._min_val, min(self._max_val, parsed))
        if clamped != self._minutes:
            self.set_minutes(clamped)
            self._on_change(clamped)

    def _cancel_edit(self, _event: tk.Event) -> None:
        if not self._editing:
            return
        self._editing = False
        self._entry.pack_forget()
        self._value_lbl.pack(side=tk.LEFT, before=self._plus_btn)


class FocusView(tk.Frame):
    """Primary Focus view with circular countdown, controls, duration selector, and daily summary."""

    def __init__(
        self,
        master: tk.Misc,
        theme: ThemePalette,
        fonts: Typography,
        on_mode_change: Callable[[TimerMode], None],
        on_start_pause: Callable[[], None],
        on_reset: Callable[[], None],
        on_skip: Callable[[], None],
        on_duration_change: Callable[[TimerMode, int], None],
        on_open_tasks: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._fonts = fonts
        self._on_open_tasks = on_open_tasks
        self._selected_task: Optional[Task] = None

        # Centered container for balanced whitespace
        self._container = tk.Frame(self, bg=theme.bg)
        self._container.pack(expand=True, fill=tk.BOTH, padx=36, pady=(12, 24))

        # 1. Mode Selector
        self._mode_selector = SegmentedControl(
            self._container,
            options=[
                (TimerMode.FOCUS.value, "Focus"),
                (TimerMode.SHORT_BREAK.value, "Short Break"),
                (TimerMode.LONG_BREAK.value, "Long Break"),
            ],
            initial_value=TimerMode.FOCUS.value,
            on_change=lambda val: on_mode_change(TimerMode(val)),
            theme=theme,
            fonts=fonts,
            width=360,
            height=38,
        )
        self._mode_selector.pack(pady=(4, 10))

        # 2. Active Task Line
        self._task_row = tk.Frame(self._container, bg=theme.bg)
        self._task_row.pack(pady=(0, 6))
        self._task_lbl = tk.Label(
            self._task_row,
            text="No task selected — Select a task",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.bg,
            cursor="hand2",
        )
        self._task_lbl.pack()
        self._task_lbl.bind("<Button-1>", lambda _e: self._on_open_tasks())

        # 3. Circular Countdown Timer
        self._timer_canvas = CircularTimerCanvas(
            self._container,
            theme=theme,
            fonts=fonts,
            size=292,
        )
        self._timer_canvas.pack(pady=(6, 14))

        # 4. Primary Controls Row (Reset / Start-Pause / Skip)
        self._controls_row = tk.Frame(self._container, bg=theme.bg)
        self._controls_row.pack(pady=(0, 16))

        self._reset_btn = LuxuryButton(
            self._controls_row,
            text="Reset",
            command=on_reset,
            theme=theme,
            fonts=fonts,
            width=96,
            height=40,
            radius=20,
            variant="secondary",
        )
        self._reset_btn.pack(side=tk.LEFT, padx=8)

        self._start_pause_btn = LuxuryButton(
            self._controls_row,
            text="Start",
            command=on_start_pause,
            theme=theme,
            fonts=fonts,
            width=156,
            height=44,
            radius=22,
            variant="primary",
        )
        self._start_pause_btn.pack(side=tk.LEFT, padx=8)

        self._skip_btn = LuxuryButton(
            self._controls_row,
            text="Skip",
            command=on_skip,
            theme=theme,
            fonts=fonts,
            width=96,
            height=40,
            radius=20,
            variant="secondary",
        )
        self._skip_btn.pack(side=tk.LEFT, padx=8)

        # 5. Duration Selector Row
        self._durations_row = tk.Frame(self._container, bg=theme.bg)
        self._durations_row.pack(pady=(0, 18))

        self._focus_stepper = _DurationStepper(
            self._durations_row,
            label="Focus",
            minutes=25,
            min_val=1,
            max_val=180,
            on_change=lambda m: on_duration_change(TimerMode.FOCUS, m),
            theme=theme,
            fonts=fonts,
        )
        self._focus_stepper.pack(side=tk.LEFT, padx=6)

        self._short_stepper = _DurationStepper(
            self._durations_row,
            label="Short Break",
            minutes=5,
            min_val=1,
            max_val=60,
            on_change=lambda m: on_duration_change(TimerMode.SHORT_BREAK, m),
            theme=theme,
            fonts=fonts,
        )
        self._short_stepper.pack(side=tk.LEFT, padx=6)

        self._long_stepper = _DurationStepper(
            self._durations_row,
            label="Long Break",
            minutes=15,
            min_val=1,
            max_val=90,
            on_change=lambda m: on_duration_change(TimerMode.LONG_BREAK, m),
            theme=theme,
            fonts=fonts,
        )
        self._long_stepper.pack(side=tk.LEFT, padx=6)

        # 6. Quiet Daily Summary Strip
        self._summary_card = tk.Frame(
            self._container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            padx=20,
            pady=12,
        )
        self._summary_card.pack(fill=tk.X, padx=20)

        self._summary_cols = tk.Frame(self._summary_card, bg=theme.surface)
        self._summary_cols.pack(fill=tk.X)
        self._summary_cols.columnconfigure(0, weight=1)
        self._summary_cols.columnconfigure(1, weight=0)
        self._summary_cols.columnconfigure(2, weight=2)
        self._summary_cols.columnconfigure(3, weight=0)
        self._summary_cols.columnconfigure(4, weight=1)

        # Col 0: Today's completed sessions
        col0 = tk.Frame(self._summary_cols, bg=theme.surface)
        col0.grid(row=0, column=0, sticky="nsew", padx=8)
        self._col0_frame = col0
        self._sessions_kicker = tk.Label(
            col0,
            text="TODAY'S SESSIONS",
            font=fonts.caption_bold(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._sessions_kicker.pack(anchor="center")
        self._sessions_val = tk.Label(
            col0,
            text="0",
            font=fonts.metric_small(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._sessions_val.pack(anchor="center", pady=(2, 0))

        self._div1 = tk.Frame(self._summary_cols, bg=theme.border, width=1)
        self._div1.grid(row=0, column=1, sticky="ns", pady=2)

        # Col 2: Daily focus progress
        col2 = tk.Frame(self._summary_cols, bg=theme.surface)
        col2.grid(row=0, column=2, sticky="nsew", padx=18)
        self._col2_frame = col2
        self._progress_kicker = tk.Label(
            col2,
            text="DAILY FOCUS PROGRESS",
            font=fonts.caption_bold(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._progress_kicker.pack(anchor="center")
        self._progress_val = tk.Label(
            col2,
            text="0m / 120m  (0%)",
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._progress_val.pack(anchor="center", pady=(2, 6))
        self._goal_bar = GoalProgressBarCanvas(
            col2,
            theme=theme,
            height=6,
            bg_override=theme.surface,
        )
        self._goal_bar.pack(fill=tk.X, padx=12)

        self._div2 = tk.Frame(self._summary_cols, bg=theme.border, width=1)
        self._div2.grid(row=0, column=3, sticky="ns", pady=2)

        # Col 4: Total focus time
        col4 = tk.Frame(self._summary_cols, bg=theme.surface)
        col4.grid(row=0, column=4, sticky="nsew", padx=8)
        self._col4_frame = col4
        self._total_kicker = tk.Label(
            col4,
            text="TOTAL FOCUS TIME",
            font=fonts.caption_bold(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._total_kicker.pack(anchor="center")
        self._total_val = tk.Label(
            col4,
            text="0m",
            font=fonts.metric_small(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._total_val.pack(anchor="center", pady=(2, 0))

    def update_timer_display(
        self,
        mode: TimerMode,
        state: TimerState,
        progress: float,
        formatted_time: str,
        cycle_completed: int,
        cycle_total: int,
    ) -> None:
        self._mode_selector.set_value(mode.value)
        self._timer_canvas.update_state(
            mode=mode,
            state=state,
            progress=progress,
            time_text=formatted_time,
            cycle_completed=cycle_completed,
            cycle_total=cycle_total,
        )
        accent_role = "focus" if mode is TimerMode.FOCUS else "break"
        self._start_pause_btn.set_accent_role(accent_role)
        if state is TimerState.RUNNING:
            self._start_pause_btn.set_text("Pause")
        elif state is TimerState.PAUSED:
            self._start_pause_btn.set_text("Resume")
        else:
            self._start_pause_btn.set_text("Start")

    def update_durations(self, settings: AppSettings) -> None:
        self._focus_stepper.set_minutes(settings.focus_minutes)
        self._short_stepper.set_minutes(settings.short_break_minutes)
        self._long_stepper.set_minutes(settings.long_break_minutes)

    def update_selected_task(self, task: Optional[Task]) -> None:
        self._selected_task = task
        if task is None:
            self._task_lbl.configure(
                text="No task selected  ·  Choose a task in Tasks",
                fg=self._theme.text_muted,
            )
        else:
            self._task_lbl.configure(
                text=f"Focusing on  ·  {task.title}",
                fg=self._theme.text_secondary,
            )

    def update_summary(self, stats: StatisticsSummary) -> None:
        self._sessions_val.configure(text=str(stats.today_completed_sessions))
        self._progress_val.configure(
            text=f"{stats.today_focus_minutes}m / {stats.daily_goal_minutes}m  ({stats.daily_goal_percent}%)"
        )
        self._goal_bar.set_progress(stats.daily_goal_ratio)
        self._total_val.configure(text=format_human_duration(stats.total_focus_seconds))

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self.configure(bg=theme.bg)
        for frame in (self._container, self._task_row, self._controls_row, self._durations_row):
            frame.configure(bg=theme.bg)
        self._task_lbl.configure(bg=theme.bg)
        self.update_selected_task(self._selected_task)

        self._mode_selector.apply_theme(theme, bg_override=theme.bg)
        self._timer_canvas.apply_theme(theme)
        self._reset_btn.apply_theme(theme, bg_override=theme.bg)
        self._start_pause_btn.apply_theme(theme, bg_override=theme.bg)
        self._skip_btn.apply_theme(theme, bg_override=theme.bg)

        self._focus_stepper.apply_theme(theme)
        self._short_stepper.apply_theme(theme)
        self._long_stepper.apply_theme(theme)

        self._summary_card.configure(bg=theme.surface, highlightbackground=theme.border)
        for frame in (self._summary_cols, self._col0_frame, self._col2_frame, self._col4_frame):
            frame.configure(bg=theme.surface)
        self._div1.configure(bg=theme.border)
        self._div2.configure(bg=theme.border)

        for kicker in (self._sessions_kicker, self._progress_kicker, self._total_kicker):
            kicker.configure(fg=theme.text_muted, bg=theme.surface)
        for val in (self._sessions_val, self._progress_val, self._total_val):
            val.configure(fg=theme.text_primary, bg=theme.surface)
        self._goal_bar.apply_theme(theme, bg_override=theme.surface)
