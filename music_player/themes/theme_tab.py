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
