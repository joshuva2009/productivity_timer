"""Settings screen: durations, daily focus goal, theme, notification sound, and auto-break."""

from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from typing import Callable

from core.models import AppSettings
from ui.theme import ThemePalette, Typography
from ui.widgets import LuxuryButton, SegmentedControl, ToggleSwitch


class _NumericSettingRow(tk.Frame):
    """Single clean numeric preference row with stepper buttons and direct entry."""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        subtitle: str,
        unit: str,
        value: int,
        min_val: int,
        max_val: int,
        step: int,
        on_change: Callable[[int], None],
        theme: ThemePalette,
        fonts: Typography,
    ) -> None:
        super().__init__(master, bg=theme.surface, pady=10)
        self._min_val = min_val
        self._max_val = max_val
        self._step = step
        self._value = value
        self._on_change = on_change
        self._theme = theme

        left = tk.Frame(self, bg=theme.surface)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._left = left

        self._title_lbl = tk.Label(
            left,
            text=title,
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
            anchor="w",
        )
        self._title_lbl.pack(anchor="w")

        self._sub_lbl = tk.Label(
            left,
            text=subtitle,
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.surface,
            anchor="w",
        )
        self._sub_lbl.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(self, bg=theme.surface)
        right.pack(side=tk.RIGHT)
        self._right = right

        self._minus_btn = LuxuryButton(
            right,
            text="−",
            command=lambda: self._adjust(-self._step),
            theme=theme,
            fonts=fonts,
            width=32,
            height=30,
            radius=15,
            variant="secondary",
            bg_override=theme.surface,
        )
        self._minus_btn.pack(side=tk.LEFT)

        self._var = tk.StringVar(value=str(value))
        self._entry = tk.Entry(
            right,
            textvariable=self._var,
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.input_bg,
            insertbackground=theme.text_primary,
            relief=tk.FLAT,
            justify="center",
            width=5,
            highlightthickness=1,
            highlightbackground=theme.border,
            highlightcolor=theme.accent_focus,
        )
        self._entry.pack(side=tk.LEFT, padx=(8, 4), ipady=4)
        self._entry.bind("<Return>", self._commit_entry)
        self._entry.bind("<FocusOut>", self._commit_entry)

        self._unit_lbl = tk.Label(
            right,
            text=unit,
            font=fonts.caption(),
            fg=theme.text_secondary,
            bg=theme.surface,
            width=4,
            anchor="w",
        )
        self._unit_lbl.pack(side=tk.LEFT, padx=(0, 6))

        self._plus_btn = LuxuryButton(
            right,
            text="+",
            command=lambda: self._adjust(self._step),
            theme=theme,
            fonts=fonts,
            width=32,
            height=30,
            radius=15,
            variant="secondary",
            bg_override=theme.surface,
        )
        self._plus_btn.pack(side=tk.LEFT)

    def set_value(self, value: int) -> None:
        self._value = max(self._min_val, min(self._max_val, int(value)))
        self._var.set(str(self._value))

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        for f in (self, self._left, self._right):
            f.configure(bg=theme.surface)
        self._title_lbl.configure(fg=theme.text_primary, bg=theme.surface)
        self._sub_lbl.configure(fg=theme.text_muted, bg=theme.surface)
        self._unit_lbl.configure(fg=theme.text_secondary, bg=theme.surface)
        self._entry.configure(
            fg=theme.text_primary,
            bg=theme.input_bg,
            insertbackground=theme.text_primary,
            highlightbackground=theme.border,
            highlightcolor=theme.accent_focus,
        )
        self._minus_btn.apply_theme(theme, bg_override=theme.surface)
        self._plus_btn.apply_theme(theme, bg_override=theme.surface)

    def _adjust(self, delta: int) -> None:
        next_val = max(self._min_val, min(self._max_val, self._value + delta))
        if next_val != self._value:
            self.set_value(next_val)
            self._on_change(next_val)

    def _commit_entry(self, _event: tk.Event) -> None:
        try:
            parsed = int(self._var.get().strip())
        except ValueError:
            self._var.set(str(self._value))
            return
        clamped = max(self._min_val, min(self._max_val, parsed))
        self._var.set(str(clamped))
        if clamped != self._value:
            self._value = clamped
            self._on_change(clamped)


class SettingsView(tk.Frame):
    """Settings screen with persistent timer, goal, theme, sound, and auto-break options."""

    def __init__(
        self,
        master: tk.Misc,
        initial_settings: AppSettings,
        theme: ThemePalette,
        fonts: Typography,
        on_settings_change: Callable[[AppSettings], None],
        on_test_sound: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._fonts = fonts
        self._settings = initial_settings.clamped()
        self._on_settings_change = on_settings_change
        self._on_test_sound = on_test_sound

        self._container = tk.Frame(self, bg=theme.bg)
        self._container.pack(fill=tk.BOTH, expand=True, padx=48, pady=(18, 24))

        # Header
        self._header = tk.Frame(self._container, bg=theme.bg)
        self._header.pack(fill=tk.X, pady=(0, 16))

        self._title_lbl = tk.Label(
            self._header,
            text="Settings",
            font=fonts.page_title(),
            fg=theme.text_primary,
            bg=theme.bg,
        )
        self._title_lbl.pack(side=tk.LEFT)

        self._saved_lbl = tk.Label(
            self._header,
            text="",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.bg,
        )
        self._saved_lbl.pack(side=tk.RIGHT, anchor="s")

        # Section 1: Timer & Goal
        self._timer_kicker = tk.Label(
            self._container,
            text="TIMER & GOALS",
            font=fonts.section_kicker(),
            fg=theme.text_muted,
            bg=theme.bg,
        )
        self._timer_kicker.pack(anchor="w", pady=(0, 6))

        self._timer_card = tk.Frame(
            self._container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            padx=20,
            pady=6,
        )
        self._timer_card.pack(fill=tk.X, pady=(0, 18))

        self._dividers: list[tk.Frame] = []

        self._focus_row = _NumericSettingRow(
            self._timer_card,
            title="Focus duration",
            subtitle="Length of each deep-work session",
            unit="min",
            value=self._settings.focus_minutes,
            min_val=1,
            max_val=180,
            step=5,
            on_change=lambda v: self._update(focus_minutes=v),
            theme=theme,
            fonts=fonts,
        )
        self._focus_row.pack(fill=tk.X)
        self._add_divider(self._timer_card)

        self._short_row = _NumericSettingRow(
            self._timer_card,
            title="Short break",
            subtitle="Rest interval between focus sessions",
            unit="min",
            value=self._settings.short_break_minutes,
            min_val=1,
            max_val=60,
            step=1,
            on_change=lambda v: self._update(short_break_minutes=v),
            theme=theme,
            fonts=fonts,
        )
        self._short_row.pack(fill=tk.X)
        self._add_divider(self._timer_card)

        self._long_row = _NumericSettingRow(
            self._timer_card,
            title="Long break",
            subtitle="Extended rest after a full focus cycle",
            unit="min",
            value=self._settings.long_break_minutes,
            min_val=1,
            max_val=90,
            step=5,
            on_change=lambda v: self._update(long_break_minutes=v),
            theme=theme,
            fonts=fonts,
        )
        self._long_row.pack(fill=tk.X)
        self._add_divider(self._timer_card)

        self._goal_row = _NumericSettingRow(
            self._timer_card,
            title="Daily focus goal",
            subtitle="Target focus time per day",
            unit="min",
            value=self._settings.daily_goal_minutes,
            min_val=10,
            max_val=720,
            step=15,
            on_change=lambda v: self._update(daily_goal_minutes=v),
            theme=theme,
            fonts=fonts,
        )
        self._goal_row.pack(fill=tk.X)

        # Section 2: Preferences
        self._pref_kicker = tk.Label(
            self._container,
            text="PREFERENCES",
            font=fonts.section_kicker(),
            fg=theme.text_muted,
            bg=theme.bg,
        )
        self._pref_kicker.pack(anchor="w", pady=(0, 6))

        self._pref_card = tk.Frame(
            self._container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
            padx=20,
            pady=6,
        )
        self._pref_card.pack(fill=tk.X)

        # Theme row
        self._theme_row = tk.Frame(self._pref_card, bg=theme.surface, pady=10)
        self._theme_row.pack(fill=tk.X)
        self._theme_left = tk.Frame(self._theme_row, bg=theme.surface)
        self._theme_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._theme_title = tk.Label(
            self._theme_left,
            text="Appearance",
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._theme_title.pack(anchor="w")
        self._theme_sub = tk.Label(
            self._theme_left,
            text="Switch between Warm Cream and Dark Charcoal",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._theme_sub.pack(anchor="w", pady=(2, 0))

        self._theme_selector = SegmentedControl(
            self._theme_row,
            options=[("light", "Light"), ("dark", "Dark")],
            initial_value=self._settings.theme,
            on_change=lambda val: self._update(theme=val),
            theme=theme,
            fonts=fonts,
            width=164,
            height=34,
            bg_override=theme.surface,
        )
        self._theme_selector.pack(side=tk.RIGHT)

        self._add_divider(self._pref_card)

        # Notification sound row
        self._sound_row = tk.Frame(self._pref_card, bg=theme.surface, pady=10)
        self._sound_row.pack(fill=tk.X)
        self._sound_left = tk.Frame(self._sound_row, bg=theme.surface)
        self._sound_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._sound_title = tk.Label(
            self._sound_left,
            text="Notification sound",
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._sound_title.pack(anchor="w")
        self._sound_sub = tk.Label(
            self._sound_left,
            text="Play a gentle chime when a timer completes",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._sound_sub.pack(anchor="w", pady=(2, 0))

        self._sound_controls = tk.Frame(self._sound_row, bg=theme.surface)
        self._sound_controls.pack(side=tk.RIGHT)

        self._test_sound_btn = LuxuryButton(
            self._sound_controls,
            text="Test",
            command=self._on_test_sound,
            theme=theme,
            fonts=fonts,
            width=60,
            height=28,
            radius=14,
            variant="secondary",
            bg_override=theme.surface,
        )
        self._test_sound_btn.pack(side=tk.LEFT, padx=(0, 12))

        self._sound_toggle = ToggleSwitch(
            self._sound_controls,
            value=self._settings.sound_enabled,
            on_toggle=lambda val: self._update(sound_enabled=val),
            theme=theme,
            bg_override=theme.surface,
        )
        self._sound_toggle.pack(side=tk.LEFT)

        self._add_divider(self._pref_card)

        # Auto-break row
        self._auto_row = tk.Frame(self._pref_card, bg=theme.surface, pady=10)
        self._auto_row.pack(fill=tk.X)
        self._auto_left = tk.Frame(self._auto_row, bg=theme.surface)
        self._auto_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._auto_title = tk.Label(
            self._auto_left,
            text="Automatic break",
            font=fonts.body_medium(),
            fg=theme.text_primary,
            bg=theme.surface,
        )
        self._auto_title.pack(anchor="w")
        self._auto_sub = tk.Label(
            self._auto_left,
            text="Automatically start Short or Long Break after Focus completes",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.surface,
        )
        self._auto_sub.pack(anchor="w", pady=(2, 0))

        self._auto_toggle = ToggleSwitch(
            self._auto_row,
            value=self._settings.auto_start_break,
            on_toggle=lambda val: self._update(auto_start_break=val),
            theme=theme,
            bg_override=theme.surface,
        )
        self._auto_toggle.pack(side=tk.RIGHT)

        self._saved_after_id: str | None = None

    def _add_divider(self, parent: tk.Misc) -> None:
        div = tk.Frame(parent, bg=self._theme.border, height=1)
        div.pack(fill=tk.X)
        self._dividers.append(div)

    def sync_settings(self, settings: AppSettings) -> None:
        self._settings = settings.clamped()
        self._focus_row.set_value(self._settings.focus_minutes)
        self._short_row.set_value(self._settings.short_break_minutes)
        self._long_row.set_value(self._settings.long_break_minutes)
        self._goal_row.set_value(self._settings.daily_goal_minutes)
        self._theme_selector.set_value(self._settings.theme)
        self._sound_toggle.set_value(self._settings.sound_enabled)
        self._auto_toggle.set_value(self._settings.auto_start_break)

    def _update(self, **changes: object) -> None:
        updated = replace(self._settings, **changes).clamped()  # type: ignore[arg-type]
        self._settings = updated
        self._on_settings_change(updated)
        self._show_saved_indicator()

    def _show_saved_indicator(self) -> None:
        self._saved_lbl.configure(text="Saved locally")
        if self._saved_after_id is not None:
            try:
                self.after_cancel(self._saved_after_id)
            except Exception:
                pass
        self._saved_after_id = self.after(2000, lambda: self._saved_lbl.configure(text=""))

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self.configure(bg=theme.bg)
        self._container.configure(bg=theme.bg)
        self._header.configure(bg=theme.bg)
        self._title_lbl.configure(fg=theme.text_primary, bg=theme.bg)
        self._saved_lbl.configure(fg=theme.text_muted, bg=theme.bg)
        self._timer_kicker.configure(fg=theme.text_muted, bg=theme.bg)
        self._pref_kicker.configure(fg=theme.text_muted, bg=theme.bg)

        self._timer_card.configure(bg=theme.surface, highlightbackground=theme.border)
        self._pref_card.configure(bg=theme.surface, highlightbackground=theme.border)

        for div in self._dividers:
            div.configure(bg=theme.border)

        self._focus_row.apply_theme(theme)
        self._short_row.apply_theme(theme)
        self._long_row.apply_theme(theme)
        self._goal_row.apply_theme(theme)

        for f in (
            self._theme_row,
            self._theme_left,
            self._sound_row,
            self._sound_left,
            self._sound_controls,
            self._auto_row,
            self._auto_left,
        ):
            f.configure(bg=theme.surface)

        for lbl in (self._theme_title, self._sound_title, self._auto_title):
            lbl.configure(fg=theme.text_primary, bg=theme.surface)
        for lbl in (self._theme_sub, self._sound_sub, self._auto_sub):
            lbl.configure(fg=theme.text_muted, bg=theme.surface)

        self._theme_selector.apply_theme(theme, bg_override=theme.surface)
        self._test_sound_btn.apply_theme(theme, bg_override=theme.surface)
        self._sound_toggle.apply_theme(theme, bg_override=theme.surface)
        self._auto_toggle.apply_theme(theme, bg_override=theme.surface)
