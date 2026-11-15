"""Tasks screen: clean checklist for adding, editing, deleting, completing, and selecting focus tasks."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from core.models import Task
from ui.theme import ThemePalette, Typography
from ui.widgets import LuxuryButton, TaskCheckboxCanvas


class TasksView(tk.Frame):
    """Minimalist checklist view for managing focus tasks."""

    def __init__(
        self,
        master: tk.Misc,
        theme: ThemePalette,
        fonts: Typography,
        on_add_task: Callable[[str], None],
        on_toggle_task: Callable[[int], None],
        on_edit_task: Callable[[int, str], None],
        on_delete_task: Callable[[int], None],
        on_select_task: Callable[[int], None],
        on_clear_completed: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._fonts = fonts
        self._on_add_task = on_add_task
        self._on_toggle_task = on_toggle_task
        self._on_edit_task = on_edit_task
        self._on_delete_task = on_delete_task
        self._on_select_task = on_select_task
        self._on_clear_completed = on_clear_completed

        self._tasks: list[Task] = []
        self._editing_task_id: Optional[int] = None
        self._placeholder = "Add a task to focus on..."
        self._has_placeholder = True

        self._container = tk.Frame(self, bg=theme.bg)
        self._container.pack(fill=tk.BOTH, expand=True, padx=48, pady=(18, 28))

        # Header Row
        self._header = tk.Frame(self._container, bg=theme.bg)
        self._header.pack(fill=tk.X, pady=(0, 14))

        header_left = tk.Frame(self._header, bg=theme.bg)
        header_left.pack(side=tk.LEFT)
        self._header_left = header_left

        self._title_lbl = tk.Label(
            header_left,
            text="Tasks",
            font=fonts.page_title(),
            fg=theme.text_primary,
            bg=theme.bg,
        )
        self._title_lbl.pack(anchor="w")

        self._count_lbl = tk.Label(
            header_left,
            text="0 active · 0 completed",
            font=fonts.caption(),
            fg=theme.text_muted,
            bg=theme.bg,
        )
        self._count_lbl.pack(anchor="w", pady=(2, 0))

        self._clear_btn = LuxuryButton(
            self._header,
            text="Clear completed",
            command=self._on_clear_completed,
            theme=theme,
            fonts=fonts,
            width=128,
            height=32,
            radius=16,
            variant="ghost",
            bg_override=theme.bg,
        )
        self._clear_btn.pack(side=tk.RIGHT, anchor="s")

        # Add Task Input Bar
        self._input_card = tk.Frame(
            self._container,
            bg=theme.input_bg,
            highlightthickness=1,
            highlightbackground=theme.border,
            padx=14,
            pady=8,
        )
        self._input_card.pack(fill=tk.X, pady=(0, 16))

        self._new_task_entry = tk.Entry(
            self._input_card,
            font=fonts.body(),
            fg=theme.text_muted,
            bg=theme.input_bg,
            insertbackground=theme.text_primary,
            relief=tk.FLAT,
            bd=0,
        )
        self._new_task_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 12))
        self._new_task_entry.insert(0, self._placeholder)
        self._new_task_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self._new_task_entry.bind("<FocusOut>", self._on_entry_focus_out)
        self._new_task_entry.bind("<Return>", lambda _e: self._submit_new_task())

        self._add_btn = LuxuryButton(
            self._input_card,
            text="Add Task",
            command=self._submit_new_task,
            theme=theme,
            fonts=fonts,
            width=96,
            height=34,
            radius=17,
            variant="primary",
            bg_override=theme.input_bg,
        )
        self._add_btn.pack(side=tk.RIGHT)

        # Scrollable Task List Area
        self._list_wrapper = tk.Frame(
            self._container,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
        )
        self._list_wrapper.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(
            self._list_wrapper,
            bg=theme.surface,
            highlightthickness=0,
            bd=0,
        )
        self._scrollbar = tk.Scrollbar(
            self._list_wrapper,
            orient=tk.VERTICAL,
            command=self._canvas.yview,
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._rows_frame = tk.Frame(self._canvas, bg=theme.surface)
        self._canvas_window = self._canvas.create_window(
            (0, 0),
            window=self._rows_frame,
            anchor="nw",
        )

        self._rows_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<Enter>", lambda _e: self._bind_mousewheel())
        self._canvas.bind("<Leave>", lambda _e: self._unbind_mousewheel())

        self._render_tasks()

    def set_tasks(self, tasks: list[Task]) -> None:
        self._tasks = list(tasks)
        if self._editing_task_id is not None and not any(t.id == self._editing_task_id for t in self._tasks):
            self._editing_task_id = None
        self._render_tasks()

    def apply_theme(self, theme: ThemePalette) -> None:
        self._theme = theme
        self.configure(bg=theme.bg)
        for frame in (self._container, self._header, self._header_left):
            frame.configure(bg=theme.bg)
        self._title_lbl.configure(fg=theme.text_primary, bg=theme.bg)
        self._count_lbl.configure(fg=theme.text_muted, bg=theme.bg)
        self._clear_btn.apply_theme(theme, bg_override=theme.bg)

        self._input_card.configure(bg=theme.input_bg, highlightbackground=theme.border)
        self._new_task_entry.configure(
            bg=theme.input_bg,
            fg=theme.text_muted if self._has_placeholder else theme.text_primary,
            insertbackground=theme.text_primary,
        )
        self._add_btn.apply_theme(theme, bg_override=theme.input_bg)

        self._list_wrapper.configure(bg=theme.surface, highlightbackground=theme.border)
        self._canvas.configure(bg=theme.surface)
        self._rows_frame.configure(bg=theme.surface)
        self._render_tasks()

    def _on_frame_configure(self, _event: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._canvas_window, width=event.width)

    def _bind_mousewheel(self) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", lambda _e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>", lambda _e: self._canvas.yview_scroll(1, "units"))

    def _unbind_mousewheel(self) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event) -> None:
        delta = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(delta, "units")

    def _on_entry_focus_in(self, _event: tk.Event) -> None:
        if self._has_placeholder:
            self._new_task_entry.delete(0, tk.END)
            self._new_task_entry.configure(fg=self._theme.text_primary)
            self._has_placeholder = False

    def _on_entry_focus_out(self, _event: tk.Event) -> None:
        if not self._new_task_entry.get().strip():
            self._new_task_entry.delete(0, tk.END)
            self._new_task_entry.insert(0, self._placeholder)
            self._new_task_entry.configure(fg=self._theme.text_muted)
            self._has_placeholder = True

    def _submit_new_task(self) -> None:
        if self._has_placeholder:
            return
        title = " ".join(self._new_task_entry.get().strip().split())
        if not title:
            return
        self._new_task_entry.delete(0, tk.END)
        self._on_add_task(title)

    def _render_tasks(self) -> None:
        for child in self._rows_frame.winfo_children():
            child.destroy()

        active_count = sum(1 for t in self._tasks if not t.completed)
        completed_count = len(self._tasks) - active_count
        self._count_lbl.configure(text=f"{active_count} active  ·  {completed_count} completed")
        self._clear_btn.set_disabled(completed_count == 0)

        t = self._theme
        if not self._tasks:
            empty = tk.Frame(self._rows_frame, bg=t.surface, pady=64)
            empty.pack(fill=tk.BOTH, expand=True)
            tk.Label(
                empty,
                text="No tasks yet",
                font=self._fonts.body_medium(),
                fg=t.text_secondary,
                bg=t.surface,
            ).pack()
            tk.Label(
                empty,
                text="Add a task above to anchor your next focus session.",
                font=self._fonts.caption(),
                fg=t.text_muted,
                bg=t.surface,
            ).pack(pady=(6, 0))
            return

        for idx, task in enumerate(self._tasks):
            assert task.id is not None
            task_id = task.id
            row_bg = t.highlight_tint if task.is_selected else t.surface

            row = tk.Frame(self._rows_frame, bg=row_bg, padx=16, pady=12)
            row.pack(fill=tk.X)

            # Checkbox
            checkbox = TaskCheckboxCanvas(
                row,
                checked=task.completed,
                on_toggle=lambda tid=task_id: self._on_toggle_task(tid),
                theme=t,
                bg_override=row_bg,
            )
            checkbox.pack(side=tk.LEFT, padx=(0, 12))

            # Center title or inline editor
            mid = tk.Frame(row, bg=row_bg)
            mid.pack(side=tk.LEFT, fill=tk.X, expand=True)

            if self._editing_task_id == task_id:
                edit_var = tk.StringVar(value=task.title)
                edit_entry = tk.Entry(
                    mid,
                    textvariable=edit_var,
                    font=self._fonts.body(),
                    fg=t.text_primary,
                    bg=t.input_bg,
                    insertbackground=t.text_primary,
                    relief=tk.FLAT,
                    highlightthickness=1,
                    highlightbackground=t.accent_focus,
                    highlightcolor=t.accent_focus,
                )
                edit_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3, padx=(0, 8))
                edit_entry.focus_set()
                edit_entry.select_range(0, tk.END)

                def save_edit(tid: int = task_id, var: tk.StringVar = edit_var) -> None:
                    new_title = " ".join(var.get().strip().split())
                    self._editing_task_id = None
                    if new_title:
                        self._on_edit_task(tid, new_title)
                    else:
                        self._render_tasks()

                def cancel_edit() -> None:
                    self._editing_task_id = None
                    self._render_tasks()

                edit_entry.bind("<Return>", lambda _e: save_edit())
                edit_entry.bind("<Escape>", lambda _e: cancel_edit())

                LuxuryButton(
                    row,
                    text="Save",
                    command=save_edit,
                    theme=t,
                    fonts=self._fonts,
                    width=64,
                    height=30,
                    radius=15,
                    variant="primary",
                    bg_override=row_bg,
                ).pack(side=tk.RIGHT, padx=(4, 0))

                LuxuryButton(
                    row,
                    text="Cancel",
                    command=cancel_edit,
                    theme=t,
                    fonts=self._fonts,
                    width=68,
                    height=30,
                    radius=15,
                    variant="ghost",
                    bg_override=row_bg,
                ).pack(side=tk.RIGHT, padx=(4, 0))
            else:
                title_font = (
                    (self._fonts.ui, 11, "overstrike")
                    if task.completed
                    else self._fonts.body()
                )
                title_fg = t.text_muted if task.completed else t.text_primary
                title_lbl = tk.Label(
                    mid,
                    text=task.title,
                    font=title_font,
                    fg=title_fg,
                    bg=row_bg,
                    anchor="w",
                    justify="left",
                )
                title_lbl.pack(anchor="w", fill=tk.X)

                if task.completed_sessions > 0 or task.is_selected:
                    meta_parts: list[str] = []
                    if task.is_selected:
                        meta_parts.append("Selected for focus")
                    if task.completed_sessions > 0:
                        word = "session" if task.completed_sessions == 1 else "sessions"
                        meta_parts.append(f"{task.completed_sessions} {word}")
                    tk.Label(
                        mid,
                        text="  ·  ".join(meta_parts),
                        font=self._fonts.caption(),
                        fg=t.accent_focus if task.is_selected else t.text_muted,
                        bg=row_bg,
                        anchor="w",
                    ).pack(anchor="w", pady=(2, 0))

                # Right action buttons
                LuxuryButton(
                    row,
                    text="Delete",
                    command=lambda tid=task_id: self._on_delete_task(tid),
                    theme=t,
                    fonts=self._fonts,
                    width=62,
                    height=28,
                    radius=14,
                    variant="danger_ghost",
                    bg_override=row_bg,
                ).pack(side=tk.RIGHT, padx=(4, 0))

                LuxuryButton(
                    row,
                    text="Edit",
                    command=lambda tid=task_id: self._start_edit(tid),
                    theme=t,
                    fonts=self._fonts,
                    width=54,
                    height=28,
                    radius=14,
                    variant="ghost",
                    bg_override=row_bg,
                ).pack(side=tk.RIGHT, padx=(4, 0))

                if not task.completed:
                    LuxuryButton(
                        row,
                        text="Selected" if task.is_selected else "Focus",
                        command=lambda tid=task_id: self._on_select_task(tid),
                        theme=t,
                        fonts=self._fonts,
                        width=76,
                        height=28,
                        radius=14,
                        variant="primary" if task.is_selected else "secondary",
                        bg_override=row_bg,
                    ).pack(side=tk.RIGHT, padx=(4, 4))

            if idx < len(self._tasks) - 1:
                sep = tk.Frame(self._rows_frame, bg=t.border, height=1)
                sep.pack(fill=tk.X, padx=16)

    def _start_edit(self, task_id: int) -> None:
        self._editing_task_id = task_id
        self._render_tasks()
