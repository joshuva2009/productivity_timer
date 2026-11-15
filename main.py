"""Entry point for Productivity Timer desktop application."""

from __future__ import annotations

import tkinter as tk

from ui.app import ProductivityTimerApp


def main() -> None:
    """Launch the Productivity Timer Tkinter desktop application."""
    root = tk.Tk()
    ProductivityTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
