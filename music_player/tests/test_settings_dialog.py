"""Tests for SettingsDialog."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor

from music_player.config import ConfigManager
from music_player.player.settings_dialog import SettingsDialog, ColorPickerButton

app = QApplication.instance() or QApplication([])


class TestColorPickerButton:

    def test_initial_color(self):
        btn = ColorPickerButton("#FF0000")
        assert btn.color_hex == "#FF0000"

    def test_set_color_hex(self):
        btn = ColorPickerButton("#FF0000")
        btn.color_hex = "#00FF00"
        assert btn.color_hex == "#00FF00"

    def test_default_color(self):
        btn = ColorPickerButton()
        assert btn.color_hex == "#FFFFFF"


class TestSettingsDialog:

    def _make_dialog(self, tmp_path) -> SettingsDialog:
        config = ConfigManager(config_path=str(tmp_path / "cfg.json"))
        return SettingsDialog(config)

    def test_loads_default_config(self, tmp_path):
        dialog = self._make_dialog(tmp_path)
        assert dialog._played_color_edit.text() == "#00FF00"
        assert dialog._unplayed_color_edit.text() == "#FFFFFF"
        assert dialog._font_size_spin.value() == 28
        assert dialog._overlay_x_spin.value() == 100
        assert dialog._overlay_y_spin.value() == 800
        assert dialog._overlay_h_spin.value() == 200

    def test_apply_updates_config(self, tmp_path):
        config_path = str(tmp_path / "cfg.json")
        config = ConfigManager(config_path=config_path)
        dialog = SettingsDialog(config)

        dialog._played_color_edit.setText("#FF0000")
        dialog._unplayed_color_edit.setText("#0000FF")
        dialog._font_size_spin.setValue(36)
        dialog._overlay_x_spin.setValue(200)
        dialog._overlay_y_spin.setValue(400)
        dialog._overlay_h_spin.setValue(300)

        dialog._apply()

        assert config.get("played_color") == "#FF0000"
        assert config.get("unplayed_color") == "#0000FF"
        assert config.get("font_size_base") == 36
        assert config.get("overlay_x") == 200
        assert config.get("overlay_y") == 400
        assert config.get("overlay_height") == 300

    def test_apply_persists_to_disk(self, tmp_path):
        config_path = str(tmp_path / "cfg.json")
        config = ConfigManager(config_path=config_path)
        dialog = SettingsDialog(config)

        dialog._played_color_edit.setText("#AABBCC")
        dialog._unplayed_color_edit.setText("#112233")
        dialog._apply()

        # Reload from disk
        config2 = ConfigManager(config_path=config_path)
        assert config2.get("played_color") == "#AABBCC"
        assert config2.get("unplayed_color") == "#112233"

    def test_side_ratio_persists(self, tmp_path):
        config_path = str(tmp_path / "cfg.json")
        config = ConfigManager(config_path=config_path)
        dialog = SettingsDialog(config)

        dialog._side_ratio_spin.setValue(0.60)
        dialog._apply()

        assert abs(config.get("font_ratio_side_lines") - 0.60) < 0.01

    def test_sync_color_from_edit_valid(self, tmp_path):
        dialog = self._make_dialog(tmp_path)
        dialog._played_color_edit.setText("#ABCDEF")
        dialog._sync_played_color_from_edit()
        assert dialog._played_color_btn.color_hex == "#ABCDEF"

    def test_sync_color_from_edit_invalid_reverts(self, tmp_path):
        dialog = self._make_dialog(tmp_path)
        original = dialog._played_color_btn.color_hex
        dialog._played_color_edit.setText("not_a_color")
        dialog._sync_played_color_from_edit()
        assert dialog._played_color_btn.color_hex == original
        assert dialog._played_color_edit.text() == original

    def test_model_list_label_exists(self, tmp_path):
        dialog = self._make_dialog(tmp_path)
        assert dialog._model_list_label is not None
