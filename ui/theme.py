"""Minimalist luxury color palettes, typography detection, and color math."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ThemePalette:
    """Cohesive design tokens derived from the Warm Cream / Forest Green / Charcoal palette."""

    name: str
    bg: str
    surface: str
    surface_alt: str
    border: str
    shadow: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_focus: str
    accent_focus_hover: str
    accent_break: str
    accent_break_hover: str
    accent_fg: str
    track: str
    highlight_tint: str
    danger: str
    danger_hover: str
    input_bg: str


LIGHT_THEME = ThemePalette(
    name="light",
    bg="#F0EEE7",
    surface="#F7F5F0",
    surface_alt="#E5E2D9",
    border="#D8D9CE",
    shadow="#DFDDD4",
    text_primary="#252A25",
    text_secondary="#555C54",
    text_muted="#84917A",
    accent_focus="#34483A",
    accent_focus_hover="#27372C",
    accent_break="#84917A",
    accent_break_hover="#6F7C66",
    accent_fg="#F0EEE7",
    track="#D8D9CE",
    highlight_tint="#E7ECE5",
    danger="#8C4E43",
    danger_hover="#703C32",
    input_bg="#FAF9F5",
)


DARK_THEME = ThemePalette(
    name="dark",
    bg="#252A25",
    surface="#2D332D",
    surface_alt="#1E221E",
    border="#3B423B",
    shadow="#191D19",
    text_primary="#F0EEE7",
    text_secondary="#C2C5BB",
    text_muted="#84917A",
    accent_focus="#84917A",
    accent_focus_hover="#96A38C",
    accent_break="#A3AE99",
    accent_break_hover="#B4BEB0",
    accent_fg="#252A25",
    track="#3B423B",
    highlight_tint="#34483A",
    danger="#C57D70",
    danger_hover="#D48E82",
    input_bg="#1E221E",
)


def get_theme(name: str) -> ThemePalette:
    """Return the light or dark ThemePalette."""
    return DARK_THEME if name == "dark" else LIGHT_THEME


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB string into an (r, g, b) integer tuple."""
    clean = hex_color.lstrip("#")
    if len(clean) != 6:
        raise ValueError(f"Expected 6-digit hex color, got: {hex_color!r}")
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert (r, g, b) integer tuple back to #RRGGBB string."""
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def blend_hex(color_a: str, color_b: str, t: float) -> str:
    """Linearly interpolate between two #RRGGBB colors with t in [0.0, 1.0]."""
    clamped = max(0.0, min(1.0, float(t)))
    ar, ag, ab = hex_to_rgb(color_a)
    br, bg, bb = hex_to_rgb(color_b)
    return rgb_to_hex(
        (
            round(ar + (br - ar) * clamped),
            round(ag + (bg - ag) * clamped),
            round(ab + (bb - ab) * clamped),
        )
    )


def select_font_family(
    available_families: Iterable[str],
    preferred: tuple[str, ...],
    fallback: str = "TkDefaultFont",
) -> str:
    """Choose the first matching installed font family, case-insensitively."""
    lookup = {fam.lower(): fam for fam in available_families}
    for candidate in preferred:
        match = lookup.get(candidate.lower())
        if match is not None:
            return match
    return fallback


class Typography:
    """Resolves clean cross-platform UI and numeric fonts once Tkinter root exists."""

    UI_PREFERRED = (
        "SF Pro Text",
        "SF Pro Display",
        "Segoe UI",
        "Helvetica Neue",
        "Inter",
        "Avenir Next",
        "DejaVu Sans",
        "Arial",
    )
    DISPLAY_PREFERRED = (
        "SF Pro Display",
        "Helvetica Neue",
        "Segoe UI Light",
        "Segoe UI",
        "Avenir Next",
        "Inter",
        "DejaVu Sans",
        "Arial",
    )

    def __init__(self, available_families: Iterable[str]) -> None:
        families = list(available_families)
        self.ui = select_font_family(families, self.UI_PREFERRED, "Helvetica")
        self.display = select_font_family(families, self.DISPLAY_PREFERRED, self.ui)

    def timer_digits(self) -> tuple[str, int, str]:
        return (self.display, 56, "normal")

    def page_title(self) -> tuple[str, int, str]:
        return (self.display, 20, "bold")

    def section_kicker(self) -> tuple[str, int, str]:
        return (self.ui, 9, "bold")

    def metric_value(self) -> tuple[str, int, str]:
        return (self.display, 22, "bold")

    def metric_small(self) -> tuple[str, int, str]:
        return (self.display, 15, "bold")

    def body(self) -> tuple[str, int, str]:
        return (self.ui, 11, "normal")

    def body_medium(self) -> tuple[str, int, str]:
        return (self.ui, 11, "bold")

    def button(self) -> tuple[str, int, str]:
        return (self.ui, 11, "bold")

    def caption(self) -> tuple[str, int, str]:
        return (self.ui, 9, "normal")

    def caption_bold(self) -> tuple[str, int, str]:
        return (self.ui, 9, "bold")
