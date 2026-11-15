"""Main application window, navigation shell, and Tkinter after() timer coordinator."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import replace
from typing import Optional

from core.models import AppSettings, TimerMode, TimerState
from core.timer import PomodoroTimerEngine
from data.database import Database
from data.repository import ProductivityRepository
from services.sound import SoundNotifier
from services.stats_service import StatisticsService
from ui.focus_view import FocusView
from ui.settings_view import SettingsView
from ui.stats_view import StatisticsView
from ui.theme import ThemePalette, Typography, get_theme
from ui.tasks_view import TasksView
from ui.widgets import LuxuryButton


class _NavTab(tk.Frame):
    """Minimalist editorial top-bar navigation tab with active underline."""

    def __init__(
        self,
        master: tk.Misc,
        key: str,
        label: str,
        on_click: object,
        theme: ThemePalette,
        fonts: Typography,
    ) -> None:
        super().__init__(master, bg=theme.bg, cursor="hand2")
        self._key = key
        self._theme = theme
        self._fonts = fonts
        self._active = False
        self._hovered = False

        self._label = tk.Label(
            self,
            text=label,
            font=fonts.caption_bold(),
            fg=theme.text_secondary,
            bg=theme.bg,
            padx=12,
            pady=10,
            cursor="hand2",
        )
        self._label.pack(side=tk.TOP)

        self._underline = tk.Frame(self, bg=theme.bg, height=2)
        self._underline.pack(side=tk.TOP, fill=tk.X, padx=10)

        for widget in (self, self._label, self._underline):
            widget.bind("<ButtonRelease-1>", lambda _e: on_click(key))  # type: ignore[operator]
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def set_active(self, active: bool) -> None:
        self._active = active
        self._refresh_style()

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self._refresh_style()

    def _refresh_style(self) -> None:
        t = self._theme
        self.configure(bg=t.bg)
        if self._active:
            fg = t.text_primary
            bar = t.accent_focus
        elif self._hovered:
            fg = t.text_primary
            bar = t.border
        else:
            fg = t.text_muted
            bar = t.bg
        self._label.configure(fg=fg, bg=t.bg)
        self._underline.configure(bg=bar)

    def _on_enter(self, _e: tk.Event) -> None:
        self._hovered = True
        self._refresh_style()

    def _on_leave(self, _e: tk.Event) -> None:
        self._hovered = False
        self._refresh_style()


class ProductivityTimerApp:
    """Top-level Tkinter desktop application controller for Productivity Timer."""

    SECTIONS = (
        ("focus", "FOCUS"),
        ("tasks", "TASKS"),
        ("statistics", "STATISTICS"),
        ("settings", "SETTINGS"),
    )

    def __init__(
        self,
        root: tk.Tk,
        database: Optional[Database] = None,
    ) -> None:
        self.root = root
        self._db = database or Database()
        self._repo = ProductivityRepository(self._db)
        self._stats_service = StatisticsService(self._repo)
        self._settings: AppSettings = self._repo.load_settings()
        self._theme: ThemePalette = get_theme(self._settings.theme)
        self._fonts = Typography(tkfont.families(self.root))

        self._engine = PomodoroTimerEngine(settings=self._settings)
        self._sound = SoundNotifier(
            bell_fallback=lambda: self.root.after(0, self.root.bell)
        )

        self._tick_after_id: Optional[str] = None
        self._current_section: str = "focus"

        self._configure_window()
        self._build_shell()
        self._refresh_all_data()
        self._show_section("focus")

    def _configure_window(self) -> None:
        self.root.title("Productivity Timer")
        self.root.geometry("920x700")
        self.root.minsize(780, 620)
        self.root.configure(bg=self._theme.bg)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<space>", self._on_space_shortcut)
        self.root.bind("<Control-Key-1>", lambda _e: self._show_section("focus"))
        self.root.bind("<Control-Key-2>", lambda _e: self._show_section("tasks"))
        self.root.bind("<Control-Key-3>", lambda _e: self._show_section("statistics"))
        self.root.bind("<Control-Key-4>", lambda _e: self._show_section("settings"))

    def _build_shell(self) -> None:
        t = self._theme

        # Top Minimalist Navigation Header
        self._topbar = tk.Frame(self.root, bg=t.bg, padx=32, pady=12)
        self._topbar.pack(side=tk.TOP, fill=tk.X)

        self._brand_lbl = tk.Label(
            self._topbar,
            text="P R O D U C T I V I T Y   T I M E R",
            font=self._fonts.section_kicker(),
            fg=t.text_primary,
            bg=t.bg,
        )
        self._brand_lbl.pack(side=tk.LEFT)

        # Quick Light/Dark theme switch icon on far right
        self._theme_toggle_lbl = tk.Label(
            self._topbar,
            text="Dark" if t.name == "light" else "Light",
            font=self._fonts.caption(),
            fg=t.text_muted,
            bg=t.bg,
            cursor="hand2",
            padx=10,
            pady=4,
        )
        self._theme_toggle_lbl.pack(side=tk.RIGHT)
        self._theme_toggle_lbl.bind("<ButtonRelease-1>", lambda _e: self._toggle_theme())

        # Centered/Right Navigation Tabs (4 sections only)
        self._nav_frame = tk.Frame(self._topbar, bg=t.bg)
        self._nav_frame.pack(side=tk.RIGHT, padx=(0, 18))

        self._nav_tabs: dict[str, _NavTab] = {}
        for key, label in self.SECTIONS:
            tab = _NavTab(
                self._nav_frame,
                key=key,
                label=label,
                on_click=self._show_section,
                theme=t,
                fonts=self._fonts,
            )
            tab.pack(side=tk.LEFT, padx=4)
            self._nav_tabs[key] = tab

        self._topbar_divider = tk.Frame(self.root, bg=t.border, height=1)
        self._topbar_divider.pack(side=tk.TOP, fill=tk.X, padx=32)

        # Main Content Stage
        self._stage = tk.Frame(self.root, bg=t.bg)
        self._stage.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._focus_view = FocusView(
            self._stage,
            theme=t,
            fonts=self._fonts,
            on_mode_change=self._handle_mode_change,
            on_start_pause=self._handle_start_pause,
            on_reset=self._handle_reset,
            on_skip=self._handle_skip,
            on_duration_change=self._handle_inline_duration_change,
            on_open_tasks=lambda: self._show_section("tasks"),
        )
        self._tasks_view = TasksView(
            self._stage,
            theme=t,
            fonts=self._fonts,
            on_add_task=self._handle_add_task,
            on_toggle_task=self._handle_toggle_task,
            on_edit_task=self._handle_edit_task,
            on_delete_task=self._handle_delete_task,
            on_select_task=self._handle_select_task,
            on_clear_completed=self._handle_clear_completed,
        )
        self._stats_view = StatisticsView(
            self._stage,
            theme=t,
            fonts=self._fonts,
        )
        self._settings_view = SettingsView(
            self._stage,
            initial_settings=self._settings,
            theme=t,
            fonts=self._fonts,
            on_settings_change=self._handle_settings_change,
            on_test_sound=self._sound.play_completion_chime,
        )

        self._views: dict[str, tk.Frame] = {
            "focus": self._focus_view,
            "tasks": self._tasks_view,
            "statistics": self._stats_view,
            "settings": self._settings_view,
        }

    # ------------------------------------------------------------------
    # Navigation & Refresh
    # ------------------------------------------------------------------
    def _show_section(self, key: str) -> None:
        if key not in self._views:
            return
        self._current_section = key
        for tab_key, tab in self._nav_tabs.items():
            tab.set_active(tab_key == key)
        for view_key, view in self._views.items():
            if view_key == key:
                view.pack(fill=tk.BOTH, expand=True)
            else:
                view.pack_forget()
        if key == "statistics":
            self._refresh_statistics()

    def _refresh_all_data(self) -> None:
        self._sync_timer_ui()
        self._focus_view.update_durations(self._settings)
        self._refresh_tasks()
        self._refresh_statistics()

    def _refresh_tasks(self) -> None:
        tasks = self._repo.list_tasks()
        selected = self._repo.get_selected_task()
        self._tasks_view.set_tasks(tasks)
        self._focus_view.update_selected_task(selected)

    def _refresh_statistics(self) -> None:
        summary = self._stats_service.get_summary(self._settings.daily_goal_minutes)
        self._focus_view.update_summary(summary)
        self._stats_view.update_statistics(summary)

    def _sync_timer_ui(self) -> None:
        formatted = self._engine.formatted_remaining()
        self._focus_view.update_timer_display(
            mode=self._engine.mode,
            state=self._engine.state,
            progress=self._engine.progress(),
            formatted_time=formatted,
            cycle_completed=self._engine.completed_focus_in_cycle,
            cycle_total=self._engine.long_break_interval,
        )
        if self._engine.state is TimerState.RUNNING:
            self.root.title(f"{formatted} · {self._engine.mode.label} — Productivity Timer")
        elif self._engine.state is TimerState.PAUSED:
            self.root.title(f"{formatted} (Paused) — Productivity Timer")
        else:
            self.root.title("Productivity Timer")

    # ------------------------------------------------------------------
    # Timer Loop (Single active after() callback, zero time.sleep)
    # ------------------------------------------------------------------
    def _cancel_tick(self) -> None:
        if self._tick_after_id is not None:
            try:
                self.root.after_cancel(self._tick_after_id)
            except Exception:
                pass
            self._tick_after_id = None

    def _schedule_tick(self) -> None:
        self._cancel_tick()
        if self._engine.state is TimerState.RUNNING:
            self._tick_after_id = self.root.after(50, self._on_tick)

    def _on_tick(self) -> None:
        self._tick_after_id = None
        if self._engine.state is not TimerState.RUNNING:
            self._sync_timer_ui()
            return

        completion = self._engine.tick()
        if completion is not None:
            selected_task = self._repo.get_selected_task()
            self._repo.record_completed_session(
                mode=completion.completed_mode,
                duration_seconds=completion.duration_seconds,
                task_id=selected_task.id if (selected_task and completion.completed_mode is TimerMode.FOCUS) else None,
                task_title=selected_task.title if (selected_task and completion.completed_mode is TimerMode.FOCUS) else None,
            )
            if self._settings.sound_enabled:
                self._sound.play_completion_chime()
            self._refresh_tasks()
            self._refresh_statistics()

        self._sync_timer_ui()
        if self._engine.state is TimerState.RUNNING:
            self._schedule_tick()

    # ------------------------------------------------------------------
    # Timer Actions
    # ------------------------------------------------------------------
    def _handle_start_pause(self) -> None:
        running = self._engine.toggle_start_pause()
        self._sync_timer_ui()
        if running:
            self._schedule_tick()
        else:
            self._cancel_tick()

    def _handle_reset(self) -> None:
        self._cancel_tick()
        self._engine.reset()
        self._sync_timer_ui()

    def _handle_skip(self) -> None:
        self._cancel_tick()
        self._engine.skip()
        self._sync_timer_ui()

    def _handle_mode_change(self, mode: TimerMode) -> None:
        self._cancel_tick()
        self._engine.set_mode(mode)
        self._sync_timer_ui()

    def _handle_inline_duration_change(self, mode: TimerMode, minutes: int) -> None:
        if mode is TimerMode.FOCUS:
            updated = replace(self._settings, focus_minutes=minutes)
        elif mode is TimerMode.SHORT_BREAK:
            updated = replace(self._settings, short_break_minutes=minutes)
        else:
            updated = replace(self._settings, long_break_minutes=minutes)
        self._handle_settings_change(updated)
        self._settings_view.sync_settings(self._settings)

    def _on_space_shortcut(self, _event: tk.Event) -> None:
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, LuxuryButton)):
            return
        if self._current_section == "focus":
            self._handle_start_pause()

    # ------------------------------------------------------------------
    # Task Actions
    # ------------------------------------------------------------------
    def _handle_add_task(self, title: str) -> None:
        self._repo.create_task(title)
        self._refresh_tasks()

    def _handle_toggle_task(self, task_id: int) -> None:
        self._repo.toggle_task_completed(task_id)
        self._refresh_tasks()

    def _handle_edit_task(self, task_id: int, new_title: str) -> None:
        self._repo.update_task_title(task_id, new_title)
        self._refresh_tasks()

    def _handle_delete_task(self, task_id: int) -> None:
        self._repo.delete_task(task_id)
        self._refresh_tasks()

    def _handle_select_task(self, task_id: int) -> None:
        current = self._repo.get_selected_task()
        if current is not None and current.id == task_id:
            self._repo.select_task_for_focus(None)
        else:
            self._repo.select_task_for_focus(task_id)
        self._refresh_tasks()

    def _handle_clear_completed(self) -> None:
        self._repo.clear_completed_tasks()
        self._refresh_tasks()

    # ------------------------------------------------------------------
    # Settings & Theme
    # ------------------------------------------------------------------
    def _handle_settings_change(self, new_settings: AppSettings) -> None:
        old_theme = self._settings.theme
        self._settings = self._repo.save_settings(new_settings)
        self._engine.apply_settings(self._settings)
        self._focus_view.update_durations(self._settings)
        self._sync_timer_ui()
        self._refresh_statistics()

        if self._settings.theme != old_theme:
            self._apply_theme(get_theme(self._settings.theme))

    def _toggle_theme(self) -> None:
        next_theme = "dark" if self._settings.theme == "light" else "light"
        updated = replace(self._settings, theme=next_theme)
        self._handle_settings_change(updated)
        self._settings_view.sync_settings(self._settings)

    def _apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self.root.configure(bg=theme.bg)
        self._topbar.configure(bg=theme.bg)
        self._brand_lbl.configure(fg=theme.text_primary, bg=theme.bg)
        self._theme_toggle_lbl.configure(
            text="Dark" if theme.name == "light" else "Light",
            fg=theme.text_muted,
            bg=theme.bg,
        )
        self._nav_frame.configure(bg=theme.bg)
        for tab in self._nav_tabs.values():
            tab.apply_theme(theme)
        self._topbar_divider.configure(bg=theme.border)
        self._stage.configure(bg=theme.bg)

        self._focus_view.apply_theme(theme)
        self._tasks_view.apply_theme(theme)
        self._stats_view.apply_theme(theme)
        self._settings_view.apply_theme(theme)

    # ------------------------------------------------------------------
    # Clean Shutdown
    # ------------------------------------------------------------------
    def on_close(self) -> None:
        """Stop active callbacks, persist settings, and close database cleanly."""
        self._cancel_tick()
        try:
            self._repo.save_settings(self._settings)
        except Exception:
            pass
        try:
            self._db.close()
        except Exception:
            pass
        self.root.destroy()
