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
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Theme name
        name_label = QLabel(self._theme.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(name_label)
        
        # Color preview
        preview = QWidget()
        preview.setFixedHeight(60)
        preview.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self._theme.played_color},
                    stop:1 {self._theme.unplayed_color});
                border-radius: 6px;
            }}
        """)
        layout.addWidget(preview)
