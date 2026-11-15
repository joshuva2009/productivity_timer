"""Statistics screen: genuine today/weekly focus metrics, goal progress, and Canvas chart."""

from __future__ import annotations

import tkinter as tk

from core.models import StatisticsSummary
from core.timer import format_human_duration
from ui.theme import ThemePalette, Typography
from ui.widgets import GoalProgressBarCanvas, WeeklyChartCanvas


class StatisticsView(tk.Frame):
    """Editorial statistics view displaying real persisted focus metrics."""

    def __init__(
        self,
        master: tk.Misc,
        theme: ThemePalette,
        fonts: Typography,
    ) -> None:
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._fonts = fonts

        self._container = tk.Frame(self, bg=theme.bg)
        self._container.pack(fill=tk.BOTH, expand=True, padx=48, pady=(18, 28))

        # Header
        self._header = tk.Frame(self._container, bg=theme.bg)
        self._header.pack(fill=tk.X, pady=(0, 18))

        self._title_lbl = tk.Label(
            self._header,
            text="Statistics",
            font=fonts.page_title(),
            fg=theme.text_primary,
            bg=theme.bg,
        )
        self._title_lbl.pack(anchor="w")

        self._subtitle_lbl = tk.Label(
            self._header,
            text="Measured from your completed focus sessions",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.bg,
        )
        self._subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Top 4-metric strip
        self._metrics_card = tk.Frame(
            self._container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            padx=20,
            pady=18,
        )
        self._metrics_card.pack(fill=tk.X, pady=(0, 16))

        self._metrics_grid = tk.Frame(self._metrics_card, bg=theme.surface)
        self._metrics_grid.pack(fill=tk.X)

        self._metric_frames: list[tk.Frame] = []
        self._metric_kickers: list[tk.Label] = []
        self._metric_values: list[tk.Label] = []
        self._metric_subs: list[tk.Label] = []
        self._dividers: list[tk.Frame] = []

        kicker_names = (
            "TODAY'S FOCUS",
            "WEEKLY FOCUS",
            "COMPLETED SESSIONS",
            "DAILY GOAL",
        )
        col_idx = 0
        for i, kicker in enumerate(kicker_names):
            self._metrics_grid.columnconfigure(col_idx, weight=1)
            cell = tk.Frame(self._metrics_grid, bg=theme.surface)
            cell.grid(row=0, column=col_idx, sticky="nsew", padx=8)
            self._metric_frames.append(cell)

            k_lbl = tk.Label(
                cell,
                text=kicker,
                font=fonts.caption_bold(),
                fg=theme.text_muted,
                bg=theme.surface,
            )
            k_lbl.pack(anchor="w")
            self._metric_kickers.append(k_lbl)

            v_lbl = tk.Label(
                cell,
                text="0m",
                font=fonts.metric_value(),
                fg=theme.text_primary,
                bg=theme.surface,
            )
            v_lbl.pack(anchor="w", pady=(6, 2))
            self._metric_values.append(v_lbl)

            s_lbl = tk.Label(
                cell,
                text="",
                font=fonts.caption(),
                fg=theme.text_secondary,
                bg=theme.surface,
            )
            s_lbl.pack(anchor="w")
            self._metric_subs.append(s_lbl)

            col_idx += 1
            if i < len(kicker_names) - 1:
                self._metrics_grid.columnconfigure(col_idx, weight=0)
                div = tk.Frame(self._metrics_grid, bg=theme.border, width=1)
                div.grid(row=0, column=col_idx, sticky="ns", padx=8, pady=4)
                self._dividers.append(div)
                col_idx += 1

        # Daily Goal Progress section
        self._goal_card = tk.Frame(
            self._container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            padx=22,
            pady=16,
        )
        self._goal_card.pack(fill=tk.X, pady=(0, 16))

        self._goal_top = tk.Frame(self._goal_card, bg=theme.surface)
        self._goal_top.pack(fill=tk.X, pady=(0, 10))

        self._goal_title = tk.Label(
            self._goal_top,
            text="Daily Goal Progress",
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._goal_title.pack(side=tk.LEFT)

        self._goal_detail = tk.Label(
            self._goal_top,
            text="0 of 120 minutes",
            font=fonts.caption(),
            fg=theme.text_secondary,
            bg=theme.surface,
        )
        self._goal_detail.pack(side=tk.RIGHT)

        self._goal_bar = GoalProgressBarCanvas(
            self._goal_card,
            theme=theme,
            height=8,
            bg_override=theme.surface,
        )
        self._goal_bar.pack(fill=tk.X)

        # Weekly Canvas Chart section
        self._chart_card = tk.Frame(
            self._container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            padx=22,
            pady=18,
        )
        self._chart_card.pack(fill=tk.BOTH, expand=True)

        self._chart_header = tk.Frame(self._chart_card, bg=theme.surface)
        self._chart_header.pack(fill=tk.X, pady=(0, 8))

        self._chart_title = tk.Label(
            self._chart_header,
            text="Last 7 Days",
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._chart_title.pack(side=tk.LEFT)

        self._chart_hint = tk.Label(
            self._chart_header,
            text="Hover a day for session details",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._chart_hint.pack(side=tk.RIGHT)

        self._chart_canvas = WeeklyChartCanvas(
            self._chart_card,
            theme=theme,
            fonts=fonts,
            bg_override=theme.surface,
        )
        self._chart_canvas.pack(fill=tk.BOTH, expand=True)

    def update_statistics(self, summary: StatisticsSummary) -> None:
        self._metric_values[0].configure(text=format_human_duration(summary.today_focus_seconds))
        self._metric_subs[0].configure(
            text=f"{summary.today_completed_sessions} completed today"
        )

        self._metric_values[1].configure(text=format_human_duration(summary.weekly_focus_seconds))
        self._metric_subs[1].configure(
            text=f"{format_human_duration(summary.total_focus_seconds)} all-time"
        )

        self._metric_values[2].configure(text=str(summary.total_completed_sessions))
        self._metric_subs[2].configure(
            text=f"{summary.today_completed_sessions} today"
        )

        self._metric_values[3].configure(text=f"{summary.daily_goal_percent}%")
        self._metric_subs[3].configure(
            text=f"Target {summary.daily_goal_minutes}m / day"
        )

        self._goal_detail.configure(
            text=f"{summary.today_focus_minutes} of {summary.daily_goal_minutes} minutes ({summary.daily_goal_percent}%)"
        )
        self._goal_bar.set_progress(summary.daily_goal_ratio)
        self._chart_canvas.set_data(summary.daily_series, summary.daily_goal_minutes)

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self.configure(bg=theme.bg)
        self._container.configure(bg=theme.bg)
        self._header.configure(bg=theme.bg)
        self._title_lbl.configure(fg=theme.text_primary, bg=theme.bg)
        self._subtitle_lbl.configure(fg=theme.text_muted, bg=theme.bg)

        self._metrics_card.configure(bg=theme.surface, highlightbackground=theme.border)
        self._metrics_grid.configure(bg=theme.surface)
        for cell in self._metric_frames:
            cell.configure(bg=theme.surface)
        for k_lbl in self._metric_kickers:
            k_lbl.configure(fg=theme.text_muted, bg=theme.surface)
        for v_lbl in self._metric_values:
            v_lbl.configure(fg=theme.text_primary, bg=theme.surface)
        for s_lbl in self._metric_subs:
            s_lbl.configure(fg=theme.text_secondary, bg=theme.surface)
        for div in self._dividers:
            div.configure(bg=theme.border)

        self._goal_card.configure(bg=theme.surface, highlightbackground=theme.border)
        self._goal_top.configure(bg=theme.surface)
        self._goal_title.configure(fg=theme.text_primary, bg=theme.surface)
        self._goal_detail.configure(fg=theme.text_secondary, bg=theme.surface)
        self._goal_bar.apply_theme(theme, bg_override=theme.surface)

        self._chart_card.configure(bg=theme.surface, highlightbackground=theme.border)
        self._chart_header.configure(bg=theme.surface)
        self._chart_title.configure(fg=theme.text_primary, bg=theme.surface)
        self._chart_hint.configure(fg=theme.text_muted, bg=theme.surface)
        self._chart_canvas.apply_theme(theme, bg_override=theme.surface)
