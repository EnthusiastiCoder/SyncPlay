"""Settings dialog for configuring overlay appearance and Whisper models."""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QFontComboBox, QColorDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from music_player.config import ConfigManager
from music_player.alignment.model_manager import ModelManager, MODEL_INFO


class ColorPickerButton(QPushButton):
    """Button that shows a color and opens a color dialog on click."""

    def __init__(self, initial_hex: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self._color = initial_hex
        self.setFixedSize(60, 28)
        self._update_style()
        self.clicked.connect(self._pick_color)
