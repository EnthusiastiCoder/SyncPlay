"""Tests for OverlayWindow."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from music_player.config import ConfigManager
from music_player.overlay.overlay_window import OverlayWindow

app = QApplication.instance() or QApplication([])


class TestOverlayWindow:

    def _make_overlay(self, tmp_path) -> OverlayWindow:
        config_path = str(tmp_path / "test_config.json")
        config = ConfigManager(config_path=config_path)
        return OverlayWindow(config)

    def test_window_flags(self, tmp_path):
        """Overlay has frameless, always-on-top, and Tool flags."""
        overlay = self._make_overlay(tmp_path)
        flags = overlay.windowFlags()
        assert flags & Qt.WindowType.FramelessWindowHint
        assert flags & Qt.WindowType.WindowStaysOnTopHint
        assert flags & Qt.WindowType.Tool

    def test_translucent_background(self, tmp_path):
        """Overlay has translucent background attribute."""
        overlay = self._make_overlay(tmp_path)
        assert overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def test_show_without_activating(self, tmp_path):
        """Overlay has WA_ShowWithoutActivating."""
        overlay = self._make_overlay(tmp_path)
        assert overlay.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def test_initial_geometry_from_config(self, tmp_path):
        """Overlay height comes from config; position auto-centers when -1."""
        overlay = self._make_overlay(tmp_path)
        # Default config uses -1 for x/y which triggers auto-center
        assert overlay.height() == 200

    def test_set_display_text(self, tmp_path):
        """set_display_text stores lines for painting."""
        overlay = self._make_overlay(tmp_path)
        overlay.set_display_text("prev", "current", "next")
        assert len(overlay._lines) == 3
        assert overlay._lines[0] == ("prev", False)
        assert overlay._lines[1] == ("current", True)
        assert overlay._lines[2] == ("next", False)

    def test_edit_mode_toggle(self, tmp_path):
        """Edit mode can be toggled on and off."""
        overlay = self._make_overlay(tmp_path)
        assert not overlay._edit_mode

        overlay.enter_edit_mode()
        assert overlay._edit_mode

        overlay.exit_edit_mode()
        assert not overlay._edit_mode

    def test_config_change_updates_geometry(self, tmp_path):
        """Changing overlay position in config updates the window."""
        config_path = str(tmp_path / "test_config.json")
        config = ConfigManager(config_path=config_path)
        overlay = OverlayWindow(config)

        config.set("overlay_x", 200)
        config.set("overlay_y", 300)
        assert overlay.x() == 200
        assert overlay.y() == 300

    def test_edit_mode_saves_position(self, tmp_path):
        """Exiting edit mode saves position to config."""
        config_path = str(tmp_path / "test_config.json")
        config = ConfigManager(config_path=config_path)
        overlay = OverlayWindow(config)

        overlay.enter_edit_mode()
        overlay.move(500, 600)
        overlay.exit_edit_mode()

        assert config.get("overlay_x") == 500
        assert config.get("overlay_y") == 600

    def test_hide_requested_signal(self, tmp_path):
        """hide_requested signal exists and is connectable."""
        overlay = self._make_overlay(tmp_path)
        received = []
        overlay.hide_requested.connect(lambda: received.append(True))
        overlay.hide_requested.emit()
        assert len(received) == 1

    def test_settings_requested_signal(self, tmp_path):
        """settings_requested signal exists and is connectable."""
        overlay = self._make_overlay(tmp_path)
        received = []
        overlay.settings_requested.connect(lambda: received.append(True))
        overlay.settings_requested.emit()
        assert len(received) == 1

    def test_paint_without_lines_no_crash(self, tmp_path):
        """Painting with no lines set doesn't crash."""
        overlay = self._make_overlay(tmp_path)
        overlay.resize(400, 200)
        overlay.repaint()  # Should not raise

    def test_paint_with_lines_no_crash(self, tmp_path):
        """Painting with lines set doesn't crash."""
        overlay = self._make_overlay(tmp_path)
        overlay.resize(400, 200)
        overlay.set_display_text("Line 1", "Line 2", "Line 3")
        overlay.repaint()  # Should not raise

    def test_paint_edit_mode_no_crash(self, tmp_path):
        """Painting in edit mode doesn't crash."""
        overlay = self._make_overlay(tmp_path)
        overlay.resize(400, 200)
        overlay._edit_mode = True
        overlay.set_display_text("Line 1", "Line 2", "Line 3")
        overlay.repaint()  # Should not raise
