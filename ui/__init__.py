"""Tkinter user interface package for Productivity Timer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.app import ProductivityTimerApp

__all__ = ["ProductivityTimerApp"]


def __getattr__(name: str) -> object:
    if name == "ProductivityTimerApp":
        from ui.app import ProductivityTimerApp

        return ProductivityTimerApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
