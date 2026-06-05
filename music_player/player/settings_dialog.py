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
