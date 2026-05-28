"""Theme selection and customization tab."""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QSlider, QLineEdit, QMessageBox, QScrollArea,
    QComboBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from music_player.config import ConfigManager
from music_player.themes.theme_manager import Theme, ThemeManager
from music_player.themes.app_theme_manager import AppThemeManager
from music_player.themes.collapsible_section import CollapsibleSection
from music_player.player.settings_dialog import ColorPickerButton


class ThemeCard(QWidget):
    """A clickable card representing a theme preset."""
    
    clicked = pyqtSignal(str)  # theme name
    
    def __init__(self, theme: Theme, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._theme = theme
        self._is_selected = False
        self._setup_ui()
