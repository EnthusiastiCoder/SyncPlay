import json
import os
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal


class ConfigManager(QObject):
    """Manages application configuration with persistent JSON storage."""

    config_changed = pyqtSignal(str, object)  # key, value

    # Default config path: %APPDATA%/MusicPlayerOverlay/config.json
    APP_DIR_NAME = "MusicPlayerOverlay"
    CONFIG_FILE_NAME = "config.json"

    def __init__(self, config_path: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        if config_path:
            self._config_path = Path(config_path)
        else:
            appdata = os.environ.get("APPDATA", str(Path.home()))
            self._config_path = Path(appdata) / self.APP_DIR_NAME / self.CONFIG_FILE_NAME

        self._defaults = self._load_defaults()
        self._data: dict[str, Any] = {}
        self.load()

    def _load_defaults(self) -> dict[str, Any]:
        """Load default configuration from bundled resource."""
        default_path = Path(__file__).parent / "resources" / "default_config.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "played_color": "#00FF00",
            "played_opacity": 1.0,
            "unplayed_color": "#FFFFFF",
            "unplayed_opacity": 1.0,
            "current_theme": "Classic Green",
            "font_family": "Segoe UI",
            "font_size_base": 28,
            "font_ratio_side_lines": 0.75,
            "overlay_x": -1,
            "overlay_y": -1,
            "overlay_height": 200,
            "whisper_model_size": "base",
            "last_directory": "",
            "recent_files": [],
        }

    def load(self) -> None:
        """Load config from disk, falling back to defaults for missing keys."""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

        # Fill in any missing keys from defaults
        for key, value in self._defaults.items():
            if key not in self._data:
                self._data[key] = value

    def save(self) -> None:
        """Persist current config to disk."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value and emit change signal."""
        old_value = self._data.get(key)
        self._data[key] = value
        if old_value != value:
            self.config_changed.emit(key, value)

    def reset(self) -> None:
        """Reset all config values to defaults."""
        self._data = dict(self._defaults)

    @property
    def config_path(self) -> Path:
        return self._config_path

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._data)
