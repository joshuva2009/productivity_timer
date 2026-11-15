"""Standard-library compliance, syntax compilation, UI safety, and theme math tests."""

from __future__ import annotations

import ast
import py_compile
import sys
import unittest
from pathlib import Path

from ui.theme import DARK_THEME, LIGHT_THEME, blend_hex, get_theme, hex_to_rgb, select_font_family

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_PACKAGES = {"core", "data", "services", "ui", "tests"}
PYTHON_DIRS = ("core", "data", "services", "ui", "tests")


def _all_project_python_files() -> list[Path]:
    files = [PROJECT_ROOT / "main.py"]
    for directory in PYTHON_DIRS:
        files.extend(sorted((PROJECT_ROOT / directory).rglob("*.py")))
    return files


class TestStandardLibraryAndThemeAudit(unittest.TestCase):
    def test_all_python_files_compile_cleanly(self) -> None:
        for path in _all_project_python_files():
            py_compile.compile(str(path), doraise=True)

    def test_standard_library_only_imports(self) -> None:
        stdlib = sys.stdlib_module_names
        for path in _all_project_python_files():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertTrue(
                            top in stdlib or top in LOCAL_PACKAGES,
                            f"Forbidden non-stdlib import {alias.name!r} in {path}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    top = node.module.split(".")[0]
                    self.assertTrue(
                        top in stdlib or top in LOCAL_PACKAGES,
                        f"Forbidden non-stdlib import {node.module!r} in {path}",
                    )

    def test_no_time_sleep_in_ui_or_main(self) -> None:
        targets = [PROJECT_ROOT / "main.py", *(PROJECT_ROOT / "ui").rglob("*.py")]
        for path in targets:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "sleep":
                    self.fail(f"time.sleep() must never be used in UI/main: {path}")

    def test_theme_palettes_and_color_math(self) -> None:
        self.assertEqual(LIGHT_THEME.bg, "#F0EEE7")
        self.assertEqual(LIGHT_THEME.accent_focus, "#34483A")
        self.assertEqual(LIGHT_THEME.text_muted, "#84917A")
        self.assertEqual(LIGHT_THEME.text_primary, "#252A25")
        self.assertEqual(LIGHT_THEME.border, "#D8D9CE")

        self.assertEqual(get_theme("light"), LIGHT_THEME)
        self.assertEqual(get_theme("dark"), DARK_THEME)
        self.assertEqual(hex_to_rgb("#34483A"), (52, 72, 58))
        self.assertEqual(blend_hex("#000000", "#FFFFFF", 0.5), "#808080")

        chosen = select_font_family(["Arial", "Segoe UI"], ("SF Pro Text", "Segoe UI"))
        self.assertEqual(chosen, "Segoe UI")
        fallback = select_font_family(["DejaVu Sans"], ("NonExistentFont",), fallback="Helvetica")
        self.assertEqual(fallback, "Helvetica")


if __name__ == "__main__":
    unittest.main()
