"""App-wide theme management: multiple QSS presets for the main UI."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AppTheme:
    """Represents an application-wide color theme."""
    name: str
    qss_file: str       # filename in resources/
    accent_color: str   # primary accent hex color
    is_dark: bool


_BUILTIN_THEMES: list[AppTheme] = [
    AppTheme("Catppuccin Dark", "dark_theme.qss",      "#89b4fa", True),
    AppTheme("Light",           "light_theme.qss",     "#4a7ce0", False),
    AppTheme("Monokai",         "monokai_theme.qss",   "#a6e22e", True),
    AppTheme("Nord",            "nord_theme.qss",      "#88c0d0", True),
    AppTheme("Solarized Dark",  "solarized_theme.qss", "#268bd2", True),
]

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


class AppThemeManager:
    """Loads and applies application-wide QSS themes."""

    def get_all_themes(self) -> list[AppTheme]:
        return list(_BUILTIN_THEMES)

    def get_theme_by_name(self, name: str) -> Optional[AppTheme]:
        for t in _BUILTIN_THEMES:
            if t.name == name:
                return t
        return None

    def load_qss(self, theme: AppTheme) -> str:
        """Load and return QSS content for the given theme."""
        qss_path = _RESOURCES_DIR / theme.qss_file
        if qss_path.exists():
            return qss_path.read_text(encoding="utf-8")
        return ""

    def apply_theme(self, theme: AppTheme) -> None:
        """Apply QSS to the running QApplication instance."""
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            return
        qss = self.load_qss(theme)
        app.setStyleSheet(qss)
