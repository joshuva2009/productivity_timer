"""Custom Tkinter Canvas widgets crafted for a minimalist luxury desktop feel."""

from __future__ import annotations

import math
import tkinter as tk
from typing import Callable, Optional

from core.models import DayStat, TimerMode, TimerState
from ui.theme import ThemePalette, Typography, blend_hex


def rounded_rect_points(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
) -> list[float]:
    """Return polygon vertices for a smooth rounded rectangle on tk.Canvas."""
    r = max(0.0, min(radius, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
    return [
        x1 + r, y1,
        x1 + r, y1,
        x2 - r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1 + r,
        x1, y1,
    ]


class LuxuryButton(tk.Canvas):
    """Minimalist pill/rounded button drawn on Canvas with subtle shadow and hover feedback."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        theme: ThemePalette,
        fonts: Typography,
        width: int = 136,
        height: int = 42,
        radius: int = 21,
        variant: str = "primary",
        accent_role: str = "focus",
        bg_override: Optional[str] = None,
    ) -> None:
        self._parent_bg = bg_override or theme.bg
        super().__init__(
            master,
            width=width,
            height=height + 2,
            bg=self._parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=1,
        )
        self._text = text
        self._command = command
        self._theme = theme
        self._fonts = fonts
        self._btn_width = width
        self._btn_height = height
        self._radius = radius
        self._variant = variant
        self._accent_role = accent_role
        self._hovered = False
        self._pressed = False
        self._disabled = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", self._on_key_activate)
        self.bind("<space>", self._on_key_activate)

        self._redraw()

    def set_text(self, text: str) -> None:
        if self._text != text:
            self._text = text
            self._redraw()

    def set_variant(self, variant: str) -> None:
        if self._variant != variant:
            self._variant = variant
            self._redraw()

    def set_accent_role(self, accent_role: str) -> None:
        if self._accent_role != accent_role:
            self._accent_role = accent_role
            self._redraw()

    def set_disabled(self, disabled: bool) -> None:
        if self._disabled != disabled:
            self._disabled = disabled
            self.configure(cursor="arrow" if disabled else "hand2")
            self._redraw()

    def apply_theme(self, theme: ThemePalette, bg_override: Optional[str] = None) -> None:
        self._theme = theme
        self._parent_bg = bg_override or theme.bg
        self.configure(bg=self._parent_bg)
        self._redraw()

    def _resolve_colors(self) -> tuple[str, str, str, bool]:
        t = self._theme
        accent = t.accent_break if self._accent_role == "break" else t.accent_focus
        accent_hover = t.accent_break_hover if self._accent_role == "break" else t.accent_focus_hover

        if self._variant == "primary":
            fill = accent_hover if self._hovered else accent
            if self._pressed:
                fill = blend_hex(fill, t.text_primary, 0.12)
            if self._disabled:
                fill = t.border
                return fill, t.text_muted, "", False
            return fill, t.accent_fg, "", True

        if self._variant == "secondary":
            fill = blend_hex(t.surface, t.surface_alt, 0.55) if self._hovered else t.surface
            if self._pressed:
                fill = t.surface_alt
            fg = t.text_muted if self._disabled else t.text_primary
            return fill, fg, t.border, True

        if self._variant == "danger_ghost":
            fill = blend_hex(self._parent_bg, t.danger, 0.12) if self._hovered else self._parent_bg
            fg = t.danger_hover if self._hovered else t.danger
            return fill, fg, "", False

        # ghost
        fill = t.surface_alt if self._hovered else self._parent_bg
        fg = t.text_muted if self._disabled else t.text_primary
        return fill, fg, "", False

    def _redraw(self) -> None:
        self.delete("all")
        w = self._btn_width
        h = self._btn_height
        fill, fg, outline, draw_shadow = self._resolve_colors()
        y_offset = 1 if self._pressed else 0

        if draw_shadow and not self._pressed and not self._disabled:
            shadow_pts = rounded_rect_points(1, 3, w - 1, h + 1, self._radius)
            self.create_polygon(
                shadow_pts,
                smooth=True,
                fill=self._theme.shadow,
                outline="",
            )

        pts = rounded_rect_points(1, 1 + y_offset, w - 1, h - 1 + y_offset, self._radius)
        self.create_polygon(
            pts,
            smooth=True,
            fill=fill,
            outline=outline,
            width=1 if outline else 0,
        )
        self.create_text(
            w / 2,
            h / 2 + y_offset,
            text=self._text,
            fill=fg,
            font=self._fonts.button(),
        )

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _event: tk.Event) -> None:
        if self._disabled:
            return
        self.focus_set()
        self._pressed = True
        self._redraw()

    def _on_release(self, event: tk.Event) -> None:
        if self._disabled:
            return
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if was_pressed and 0 <= event.x <= self._btn_width and 0 <= event.y <= self._btn_height + 2:
            self._command()

    def _on_key_activate(self, _event: tk.Event) -> str:
        if not self._disabled:
            self._command()
        return "break"


class SegmentedControl(tk.Canvas):
    """Clean pill-shaped segmented selector for modes and themes."""

    def __init__(
        self,
        master: tk.Misc,
        options: list[tuple[str, str]],
        initial_value: str,
        on_change: Callable[[str], None],
        theme: ThemePalette,
        fonts: Typography,
        width: int = 348,
        height: int = 38,
        bg_override: Optional[str] = None,
    ) -> None:
        self._parent_bg = bg_override or theme.bg
        super().__init__(
            master,
            width=width,
            height=height,
            bg=self._parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._segmented_options = options
        self._selected = initial_value
        self._on_change = on_change
        self._theme = theme
        self._fonts = fonts
        self._canvas_width = width
        self._canvas_height = height
        self._hover_idx: Optional[int] = None

        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)
        self._redraw()

    def set_value(self, value: str) -> None:
        if self._selected != value:
            self._selected = value
            self._redraw()

    def apply_theme(self, theme: ThemePalette, bg_override: Optional[str] = None) -> None:
        self._theme = theme
        self._parent_bg = bg_override or theme.bg
        self.configure(bg=self._parent_bg)
        self._redraw()

    def _index_at_x(self, x: float) -> Optional[int]:
        if not self._segmented_options:
            return None
        pad = 3.0
        seg_w = (self._canvas_width - 2 * pad) / len(self._segmented_options)
        idx = int((x - pad) // seg_w)
        if 0 <= idx < len(self._segmented_options):
            return idx
        return None

    def _redraw(self) -> None:
        self.delete("all")
        t = self._theme
        w, h = self._canvas_width, self._canvas_height
        outer_pts = rounded_rect_points(1, 1, w - 1, h - 1, (h - 2) / 2)
        self.create_polygon(
            outer_pts,
            smooth=True,
            fill=t.surface_alt,
            outline=t.border,
            width=1,
        )

        if not self._segmented_options:
            return
        pad = 4.0
        seg_w = (w - 2 * pad) / len(self._segmented_options)
        for idx, (value, label) in enumerate(self._segmented_options):
            x1 = pad + idx * seg_w
            x2 = x1 + seg_w
            y1 = pad
            y2 = h - pad
            is_active = value == self._selected
            is_hovered = idx == self._hover_idx

            if is_active:
                pill_pts = rounded_rect_points(x1, y1, x2, y2, (y2 - y1) / 2)
                self.create_polygon(
                    pill_pts,
                    smooth=True,
                    fill=t.surface,
                    outline=t.border,
                    width=1,
                )
                fg = t.text_primary
                font = self._fonts.caption_bold()
            else:
                if is_hovered:
                    pill_pts = rounded_rect_points(x1 + 1, y1 + 1, x2 - 1, y2 - 1, (y2 - y1) / 2)
                    self.create_polygon(
                        pill_pts,
                        smooth=True,
                        fill=blend_hex(t.surface_alt, t.surface, 0.45),
                        outline="",
                    )
                fg = t.text_primary if is_hovered else t.text_secondary
                font = self._fonts.caption()

            self.create_text(
                (x1 + x2) / 2,
                h / 2,
                text=label,
                fill=fg,
                font=font,
            )

    def _on_motion(self, event: tk.Event) -> None:
        idx = self._index_at_x(event.x)
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hover_idx is not None:
            self._hover_idx = None
            self._redraw()

    def _on_click(self, event: tk.Event) -> None:
        idx = self._index_at_x(event.x)
        if idx is not None:
            value = self._segmented_options[idx][0]
            if value != self._selected:
                self._selected = value
                self._redraw()
                self._on_change(value)


class CircularTimerCanvas(tk.Canvas):
    """Watchmaker-inspired circular countdown indicator with smooth arc and end-caps."""

    def __init__(
        self,
        master: tk.Misc,
        theme: ThemePalette,
        fonts: Typography,
        size: int = 304,
    ) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            bg=theme.bg,
            highlightthickness=0,
            bd=0,
        )
        self._size = size
        self._theme = theme
        self._fonts = fonts
        self._mode: TimerMode = TimerMode.FOCUS
        self._state: TimerState = TimerState.IDLE
        self._progress: float = 0.0
        self._time_text: str = "25:00"
        self._cycle_completed: int = 0
        self._cycle_total: int = 4

        self._redraw()

    def update_state(
        self,
        mode: TimerMode,
        state: TimerState,
        progress: float,
        time_text: str,
        cycle_completed: int,
        cycle_total: int,
    ) -> None:
        self._mode = mode
        self._state = state
        self._progress = max(0.0, min(1.0, progress))
        self._time_text = time_text
        self._cycle_completed = cycle_completed
        self._cycle_total = max(1, cycle_total)
        self._redraw()

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self.configure(bg=theme.bg)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        t = self._theme
        cx = cy = self._size / 2.0

        # Subtle outer precision dial ticks
        outer_r = self._size * 0.465
        for step in range(60):
            angle_rad = math.radians(step * 6 - 90)
            is_major = step % 5 == 0
            inner_r = outer_r - (7.0 if is_major else 3.5)
            x1 = cx + inner_r * math.cos(angle_rad)
            y1 = cy + inner_r * math.sin(angle_rad)
            x2 = cx + outer_r * math.cos(angle_rad)
            y2 = cy + outer_r * math.sin(angle_rad)
            tick_color = t.text_muted if is_major else t.border
            self.create_line(x1, y1, x2, y2, fill=tick_color, width=1.4 if is_major else 1.0)

        # Elevated inner circular face with subtle shadow ring
        ring_r = self._size * 0.395
        stroke_w = 8.0
        self.create_oval(
            cx - ring_r - 2,
            cy - ring_r,
            cx + ring_r + 2,
            cy + ring_r + 4,
            fill=t.shadow,
            outline="",
        )
        self.create_oval(
            cx - ring_r,
            cy - ring_r,
            cx + ring_r,
            cy + ring_r,
            fill=t.surface,
            outline=t.track,
            width=stroke_w,
        )

        # Progress arc (remaining fraction vs elapsed sweep: clockwise elapsed fill)
        accent = t.accent_focus if self._mode is TimerMode.FOCUS else t.accent_break
        remaining_ratio = max(0.0, min(1.0, 1.0 - self._progress))
        if remaining_ratio > 0.002:
            if remaining_ratio >= 0.999:
                self.create_oval(
                    cx - ring_r,
                    cy - ring_r,
                    cx + ring_r,
                    cy + ring_r,
                    outline=accent,
                    width=stroke_w,
                )
            else:
                extent = -360.0 * remaining_ratio
                self.create_arc(
                    cx - ring_r,
                    cy - ring_r,
                    cx + ring_r,
                    cy + ring_r,
                    start=90,
                    extent=extent,
                    style=tk.ARC,
                    outline=accent,
                    width=stroke_w,
                )
                # Rounded end-caps for refined craft
                cap_r = stroke_w / 2.0
                for deg in (90.0, 90.0 + extent):
                    rad = math.radians(deg)
                    ex = cx + ring_r * math.cos(rad)
                    ey = cy - ring_r * math.sin(rad)
                    self.create_oval(
                        ex - cap_r,
                        ey - cap_r,
                        ex + cap_r,
                        ey + cap_r,
                        fill=accent,
                        outline="",
                    )

        # Mode tracked uppercase label
        mode_caps = "  ".join(self._mode.label.upper())
        self.create_text(
            cx,
            cy - 54,
            text=mode_caps,
            fill=t.text_muted,
            font=self._fonts.section_kicker(),
        )

        # Hero countdown typography
        self.create_text(
            cx,
            cy - 4,
            text=self._time_text,
            fill=t.text_primary,
            font=self._fonts.timer_digits(),
        )

        # Status text
        if self._state is TimerState.RUNNING:
            status_label = "In progress"
        elif self._state is TimerState.PAUSED:
            status_label = "Paused"
        else:
            status_label = "Ready"

        self.create_text(
            cx,
            cy + 42,
            text=status_label,
            fill=t.text_secondary,
            font=self._fonts.caption(),
        )

        # Cycle indicator dots (shows progress toward long break)
        dot_gap = 12
        total_dots = self._cycle_total
        start_x = cx - ((total_dots - 1) * dot_gap) / 2.0
        dot_y = cy + 66
        for i in range(total_dots):
            dx = start_x + i * dot_gap
            filled = i < self._cycle_completed
            self.create_oval(
                dx - 3,
                dot_y - 3,
                dx + 3,
                dot_y + 3,
                fill=accent if filled else "",
                outline=accent if filled else t.border,
                width=1.2,
            )


class ToggleSwitch(tk.Canvas):
    """Minimalist pill toggle switch drawn on Canvas."""

    def __init__(
        self,
        master: tk.Misc,
        value: bool,
        on_toggle: Callable[[bool], None],
        theme: ThemePalette,
        bg_override: Optional[str] = None,
    ) -> None:
        self._parent_bg = bg_override or theme.surface
        super().__init__(
            master,
            width=46,
            height=26,
            bg=self._parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._value = bool(value)
        self._on_toggle = on_toggle
        self._theme = theme
        self.bind("<ButtonRelease-1>", self._handle_click)
        self._redraw()

    def set_value(self, value: bool) -> None:
        if self._value != bool(value):
            self._value = bool(value)
            self._redraw()

    def apply_theme(self, theme: ThemePalette, bg_override: Optional[str] = None) -> None:
        self._theme = theme
        self._parent_bg = bg_override or theme.surface
        self.configure(bg=self._parent_bg)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        t = self._theme
        track_fill = t.accent_focus if self._value else t.track
        pts = rounded_rect_points(1, 2, 45, 24, 11)
        self.create_polygon(pts, smooth=True, fill=track_fill, outline="")

        knob_cx = 34 if self._value else 12
        knob_fill = t.accent_fg if self._value else t.surface
        self.create_oval(
            knob_cx - 8,
            13 - 8,
            knob_cx + 8,
            13 + 8,
            fill=knob_fill,
            outline="",
        )

    def _handle_click(self, _event: tk.Event) -> None:
        self._value = not self._value
        self._redraw()
        self._on_toggle(self._value)


class GoalProgressBarCanvas(tk.Canvas):
    """Sleek horizontal rounded progress bar."""

    def __init__(
        self,
        master: tk.Misc,
        theme: ThemePalette,
        height: int = 8,
        bg_override: Optional[str] = None,
    ) -> None:
        self._parent_bg = bg_override or theme.bg
        super().__init__(
            master,
            height=height,
            bg=self._parent_bg,
            highlightthickness=0,
            bd=0,
        )
        self._theme = theme
        self._height = height
        self._ratio = 0.0
        self.bind("<Configure>", lambda _e: self._redraw())
        self._redraw()

    def set_progress(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, float(ratio)))
        self._redraw()

    def apply_theme(self, theme: ThemePalette, bg_override: Optional[str] = None) -> None:
        self._theme = theme
        self._parent_bg = bg_override or theme.bg
        self.configure(bg=self._parent_bg)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        w = max(20, self.winfo_width())
        h = self._height
        r = h / 2.0
        track_pts = rounded_rect_points(0, 0, w, h, r)
        self.create_polygon(track_pts, smooth=True, fill=self._theme.track, outline="")

        fill_w = w * self._ratio
        if fill_w >= 4.0:
            fill_pts = rounded_rect_points(0, 0, fill_w, h, r)
            self.create_polygon(
                fill_pts,
                smooth=True,
                fill=self._theme.accent_focus,
                outline="",
            )


class TaskCheckboxCanvas(tk.Canvas):
    """Minimalist circular task completion checkbox."""

    def __init__(
        self,
        master: tk.Misc,
        checked: bool,
        on_toggle: Callable[[], None],
        theme: ThemePalette,
        bg_override: Optional[str] = None,
    ) -> None:
        self._parent_bg = bg_override or theme.surface
        super().__init__(
            master,
            width=22,
            height=22,
            bg=self._parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._checked = checked
        self._on_toggle = on_toggle
        self._theme = theme
        self._hovered = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", lambda _e: self._on_toggle())
        self._redraw()

    def apply_theme(self, theme: ThemePalette, bg_override: Optional[str] = None) -> None:
        self._theme = theme
        self._parent_bg = bg_override or theme.surface
        self.configure(bg=self._parent_bg)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        t = self._theme
        if self._checked:
            self.create_oval(2, 2, 20, 20, fill=t.accent_focus, outline=t.accent_focus, width=1.5)
            self.create_line(
                6.5, 11.2, 9.6, 14.3, 15.5, 7.8,
                fill=t.accent_fg,
                width=2.0,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        else:
            outline = t.accent_focus if self._hovered else t.text_muted
            fill = t.highlight_tint if self._hovered else ""
            self.create_oval(2, 2, 20, 20, fill=fill, outline=outline, width=1.6)

    def _on_enter(self, _e: tk.Event) -> None:
        self._hovered = True
        self._redraw()

    def _on_leave(self, _e: tk.Event) -> None:
        self._hovered = False
        self._redraw()


def compute_chart_scale(values: list[int], goal_minutes: int) -> int:
    """Compute a clean round upper Y-axis bound in minutes for the weekly bar chart."""
    peak = max(values + [goal_minutes, 30])
    step = 30 if peak <= 180 else 60
    return ((peak + step - 1) // step) * step


class WeeklyChartCanvas(tk.Canvas):
    """Minimalist 7-day focus activity bar chart drawn cleanly with Tkinter Canvas."""

    def __init__(
        self,
        master: tk.Misc,
        theme: ThemePalette,
        fonts: Typography,
        bg_override: Optional[str] = None,
    ) -> None:
        self._parent_bg = bg_override or theme.surface
        super().__init__(
            master,
            height=220,
            bg=self._parent_bg,
            highlightthickness=0,
            bd=0,
        )
        self._theme = theme
        self._fonts = fonts
        self._series: tuple[DayStat, ...] = ()
        self._goal_minutes: int = 120
        self._hover_idx: Optional[int] = None
        self._bar_hitboxes: list[tuple[float, float, int]] = []

        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    def set_data(self, series: tuple[DayStat, ...], goal_minutes: int) -> None:
        self._series = series
        self._goal_minutes = max(1, int(goal_minutes))
        self._redraw()

    def apply_theme(self, theme: ThemePalette, bg_override: Optional[str] = None) -> None:
        self._theme = theme
        self._parent_bg = bg_override or theme.surface
        self.configure(bg=self._parent_bg)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        self._bar_hitboxes = []
        t = self._theme
        w = max(320, self.winfo_width())
        h = max(180, self.winfo_height())

        pad_left = 44.0
        pad_right = 20.0
        pad_top = 30.0
        pad_bottom = 34.0
        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom
        baseline_y = pad_top + plot_h

        values = [d.focus_minutes for d in self._series]
        y_max = compute_chart_scale(values, self._goal_minutes)

        # Horizontal hairline grid (0, 50%, 100%)
        for frac in (0.0, 0.5, 1.0):
            gy = baseline_y - frac * plot_h
            self.create_line(
                pad_left,
                gy,
                w - pad_right,
                gy,
                fill=t.border,
                width=1,
            )
            tick_val = int(round(y_max * frac))
            self.create_text(
                pad_left - 8,
                gy,
                text=f"{tick_val}m",
                anchor="e",
                fill=t.text_muted,
                font=self._fonts.caption(),
            )

        # Subtle dashed daily goal line
        if 0 < self._goal_minutes <= y_max:
            goal_y = baseline_y - (self._goal_minutes / y_max) * plot_h
            self.create_line(
                pad_left,
                goal_y,
                w - pad_right,
                goal_y,
                fill=t.text_muted,
                dash=(4, 4),
                width=1.2,
            )
            self.create_text(
                w - pad_right,
                goal_y - 8,
                text=f"Goal {self._goal_minutes}m",
                anchor="e",
                fill=t.text_muted,
                font=self._fonts.caption(),
            )

        if not self._series:
            return

        # Bars
        col_w = plot_w / len(self._series)
        bar_w = min(38.0, max(18.0, col_w * 0.48))

        for idx, stat in enumerate(self._series):
            cx = pad_left + (idx + 0.5) * col_w
            x1 = cx - bar_w / 2.0
            x2 = cx + bar_w / 2.0
            self._bar_hitboxes.append((cx - col_w / 2.0, cx + col_w / 2.0, idx))

            mins = stat.focus_minutes
            is_hovered = idx == self._hover_idx
            if mins > 0:
                bar_h = max(6.0, (mins / y_max) * plot_h)
                y1 = baseline_y - bar_h
                bar_color = (
                    t.accent_focus_hover
                    if (stat.is_today and is_hovered)
                    else (
                        t.accent_focus
                        if stat.is_today
                        else (t.accent_break_hover if is_hovered else t.accent_break)
                    )
                )
                pts = rounded_rect_points(x1, y1, x2, baseline_y, min(6.0, bar_w / 3.0))
                self.create_polygon(pts, smooth=True, fill=bar_color, outline="")

                if mins > 0:
                    self.create_text(
                        cx,
                        y1 - 10,
                        text=f"{mins}m",
                        fill=t.text_primary if is_hovered or stat.is_today else t.text_secondary,
                        font=self._fonts.caption_bold() if is_hovered else self._fonts.caption(),
                    )
            else:
                # Quiet empty-day indicator pill
                pts = rounded_rect_points(x1, baseline_y - 3, x2, baseline_y, 1.5)
                self.create_polygon(pts, smooth=True, fill=t.track, outline="")

            # Day label
            self.create_text(
                cx,
                baseline_y + 16,
                text=stat.label,
                fill=t.text_primary if stat.is_today or is_hovered else t.text_muted,
                font=self._fonts.caption_bold() if stat.is_today else self._fonts.caption(),
            )

        # Hover readout in top-right header area
        if self._hover_idx is not None and 0 <= self._hover_idx < len(self._series):
            hovered = self._series[self._hover_idx]
            sessions_word = "session" if hovered.session_count == 1 else "sessions"
            readout = f"{hovered.day.strftime('%b %d')}  ·  {hovered.focus_minutes}m  ·  {hovered.session_count} {sessions_word}"
            self.create_text(
                w - pad_right,
                12,
                text=readout,
                anchor="e",
                fill=t.text_primary,
                font=self._fonts.caption_bold(),
            )

    def _on_motion(self, event: tk.Event) -> None:
        found: Optional[int] = None
        for x_start, x_end, idx in self._bar_hitboxes:
            if x_start <= event.x <= x_end:
                found = idx
                break
        if found != self._hover_idx:
            self._hover_idx = found
            self._redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hover_idx is not None:
            self._hover_idx = None
            self._redraw()
