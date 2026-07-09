"""Unit tests for AppThemeManager."""

import unittest
from pathlib import Path

from music_player.themes.app_theme_manager import AppThemeManager, _BUILTIN_THEMES, _RESOURCES_DIR


class TestAppThemeManager(unittest.TestCase):

    def setUp(self):
        self.mgr = AppThemeManager()

    def test_all_themes_returned(self):
        themes = self.mgr.get_all_themes()
        self.assertEqual(len(themes), 5)

    def test_builtin_theme_names(self):
        names = {t.name for t in self.mgr.get_all_themes()}
        self.assertIn("Catppuccin Dark", names)
        self.assertIn("Light", names)
        self.assertIn("Monokai", names)
        self.assertIn("Nord", names)
        self.assertIn("Solarized Dark", names)

    def test_get_theme_by_name_found(self):
        theme = self.mgr.get_theme_by_name("Nord")
        self.assertIsNotNone(theme)
        self.assertEqual(theme.name, "Nord")
        self.assertEqual(theme.accent_color, "#88c0d0")
        self.assertTrue(theme.is_dark)

    def test_get_theme_by_name_not_found(self):
        theme = self.mgr.get_theme_by_name("NonExistent")
        self.assertIsNone(theme)

    def test_all_qss_files_exist(self):
        for theme in self.mgr.get_all_themes():
            qss_path = _RESOURCES_DIR / theme.qss_file
            self.assertTrue(qss_path.exists(), f"QSS file missing: {theme.qss_file}")

    def test_all_qss_files_non_empty(self):
        for theme in self.mgr.get_all_themes():
            qss = self.mgr.load_qss(theme)
            self.assertGreater(len(qss), 100, f"QSS file too short for theme: {theme.name}")

    def test_light_theme_is_not_dark(self):
        theme = self.mgr.get_theme_by_name("Light")
        self.assertIsNotNone(theme)
        self.assertFalse(theme.is_dark)

    def test_catppuccin_accent_color(self):
        theme = self.mgr.get_theme_by_name("Catppuccin Dark")
        self.assertIsNotNone(theme)
        self.assertEqual(theme.accent_color, "#89b4fa")

    def test_load_qss_returns_string(self):
        for theme in self.mgr.get_all_themes():
            qss = self.mgr.load_qss(theme)
            self.assertIsInstance(qss, str)


if __name__ == "__main__":
    unittest.main()
