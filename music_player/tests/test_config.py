"""Tests for ConfigManager."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from music_player.config import ConfigManager

# Ensure QApplication exists for signal testing
app = QApplication.instance() or QApplication([])


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def _make_config(self, tmp_path: Path) -> ConfigManager:
        config_path = str(tmp_path / "test_config.json")
        return ConfigManager(config_path=config_path)

    def test_creates_default_config(self, tmp_path):
        """Config file is created with defaults on first save."""
        cfg = self._make_config(tmp_path)
        cfg.save()
        assert cfg.config_path.exists()

    def test_default_values_loaded(self, tmp_path):
        """All default keys are present after initialization."""
        cfg = self._make_config(tmp_path)
        assert cfg.get("played_color") == "#00FF00"
        assert cfg.get("unplayed_color") == "#FFFFFF"
        assert cfg.get("font_family") == "Segoe UI"
        assert cfg.get("font_size_base") == 28
        assert cfg.get("font_ratio_side_lines") == 0.75
        assert cfg.get("overlay_x") == 100
        assert cfg.get("overlay_y") == 800
        assert cfg.get("overlay_width") == 1200
        assert cfg.get("whisper_model_size") == "base"
        assert cfg.get("last_directory") == ""
        assert cfg.get("recent_files") == []

    def test_set_and_get(self, tmp_path):
        """Setting a value makes it retrievable."""
        cfg = self._make_config(tmp_path)
        cfg.set("played_color", "#FF0000")
        assert cfg.get("played_color") == "#FF0000"

    def test_save_and_reload(self, tmp_path):
        """Values persist across save and reload."""
        config_path = str(tmp_path / "test_config.json")
        cfg1 = ConfigManager(config_path=config_path)
        cfg1.set("played_color", "#AABBCC")
        cfg1.set("font_size_base", 42)
        cfg1.save()

        cfg2 = ConfigManager(config_path=config_path)
        assert cfg2.get("played_color") == "#AABBCC"
        assert cfg2.get("font_size_base") == 42

    def test_missing_keys_filled_from_defaults(self, tmp_path):
        """If saved config is missing keys, defaults fill them in."""
        config_path = tmp_path / "test_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump({"played_color": "#123456"}, f)

        cfg = ConfigManager(config_path=str(config_path))
        assert cfg.get("played_color") == "#123456"
        assert cfg.get("unplayed_color") == "#FFFFFF"  # default
        assert cfg.get("font_size_base") == 28  # default

    def test_corrupt_json_falls_back_to_defaults(self, tmp_path):
        """Corrupt config file results in all defaults."""
        config_path = tmp_path / "test_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("NOT VALID JSON {{{", encoding="utf-8")

        cfg = ConfigManager(config_path=str(config_path))
        assert cfg.get("played_color") == "#00FF00"

    def test_reset_restores_defaults(self, tmp_path):
        """Reset brings all values back to defaults."""
        cfg = self._make_config(tmp_path)
        cfg.set("played_color", "#000000")
        cfg.set("font_size_base", 99)
        cfg.reset()
        assert cfg.get("played_color") == "#00FF00"
        assert cfg.get("font_size_base") == 28

    def test_get_unknown_key_returns_default(self, tmp_path):
        """Getting a non-existent key returns the provided default."""
        cfg = self._make_config(tmp_path)
        assert cfg.get("nonexistent_key") is None
        assert cfg.get("nonexistent_key", "fallback") == "fallback"

    def test_config_changed_signal(self, tmp_path):
        """Signal is emitted when a value changes."""
        cfg = self._make_config(tmp_path)
        received = []
        cfg.config_changed.connect(lambda k, v: received.append((k, v)))

        cfg.set("played_color", "#ABCDEF")
        assert len(received) == 1
        assert received[0] == ("played_color", "#ABCDEF")

    def test_config_changed_signal_not_emitted_on_same_value(self, tmp_path):
        """Signal is NOT emitted if value doesn't change."""
        cfg = self._make_config(tmp_path)
        received = []
        cfg.config_changed.connect(lambda k, v: received.append((k, v)))

        cfg.set("played_color", "#00FF00")  # same as default
        assert len(received) == 0

    def test_data_property_returns_copy(self, tmp_path):
        """The data property returns a copy, not the internal dict."""
        cfg = self._make_config(tmp_path)
        data = cfg.data
        data["played_color"] = "#MODIFIED"
        assert cfg.get("played_color") == "#00FF00"  # unchanged
