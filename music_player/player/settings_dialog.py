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

    def _update_style(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._color}; border: 1px solid #888; border-radius: 3px;"
        )
        self.setText("")

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Pick Color")
        if color.isValid():
            self._color = color.name()
            self._update_style()

    @property
    def color_hex(self) -> str:
        return self._color

    @color_hex.setter
    def color_hex(self, value: str) -> None:
        self._color = value
        self._update_style()


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._model_manager = ModelManager()
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._build_ui()
        self._load_from_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # -- Colors --
        color_group = QGroupBox("Lyric Colors")
        color_form = QFormLayout(color_group)

        played_layout = QHBoxLayout()
        self._played_color_btn = ColorPickerButton()
        self._played_color_edit = QLineEdit()
        self._played_color_edit.setFixedWidth(80)
        self._played_color_edit.setPlaceholderText("#00FF00")
        played_layout.addWidget(self._played_color_btn)
        played_layout.addWidget(self._played_color_edit)
        played_layout.addStretch()
        color_form.addRow("Played color:", played_layout)

        unplayed_layout = QHBoxLayout()
        self._unplayed_color_btn = ColorPickerButton()
        self._unplayed_color_edit = QLineEdit()
        self._unplayed_color_edit.setFixedWidth(80)
        self._unplayed_color_edit.setPlaceholderText("#FFFFFF")
        unplayed_layout.addWidget(self._unplayed_color_btn)
        unplayed_layout.addWidget(self._unplayed_color_edit)
        unplayed_layout.addStretch()
        color_form.addRow("Unplayed color:", unplayed_layout)

        layout.addWidget(color_group)

        # -- Fonts --
        font_group = QGroupBox("Font")
        font_form = QFormLayout(font_group)

        self._font_combo = QFontComboBox()
        font_form.addRow("Font family:", self._font_combo)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 120)
        self._font_size_spin.setSuffix(" pt")
        font_form.addRow("Base font size:", self._font_size_spin)

        self._side_ratio_spin = QDoubleSpinBox()
        self._side_ratio_spin.setRange(0.3, 1.0)
        self._side_ratio_spin.setSingleStep(0.05)
        self._side_ratio_spin.setDecimals(2)
        font_form.addRow("Side line ratio:", self._side_ratio_spin)

        layout.addWidget(font_group)

        # -- Overlay position --
        pos_group = QGroupBox("Overlay Position")
        pos_form = QFormLayout(pos_group)

        self._overlay_x_spin = QSpinBox()
        self._overlay_x_spin.setRange(-5000, 10000)
        self._overlay_x_spin.setSuffix(" px")
        pos_form.addRow("X:", self._overlay_x_spin)

        self._overlay_y_spin = QSpinBox()
        self._overlay_y_spin.setRange(-5000, 10000)
        self._overlay_y_spin.setSuffix(" px")
        pos_form.addRow("Y:", self._overlay_y_spin)

        self._overlay_h_spin = QSpinBox()
        self._overlay_h_spin.setRange(100, 1000)
        self._overlay_h_spin.setSuffix(" px")
        pos_form.addRow("Height:", self._overlay_h_spin)

        layout.addWidget(pos_group)

        # -- Whisper model management --
        model_group = QGroupBox("Whisper Models")
        model_layout = QVBoxLayout(model_group)

        self._model_list_label = QLabel("")
        self._model_list_label.setWordWrap(True)
        model_layout.addWidget(self._model_list_label)

        model_btn_layout = QHBoxLayout()
        self._model_combo = QComboBox()
        for name in ModelManager.available_models():
            info = MODEL_INFO.get(name, {})
            self._model_combo.addItem(f"{name} (~{info.get('size_mb', '?')} MB)", name)
        self._btn_delete_model = QPushButton("Delete Cached Model")
        model_btn_layout.addWidget(self._model_combo)
        model_btn_layout.addWidget(self._btn_delete_model)
        model_btn_layout.addStretch()
        model_layout.addLayout(model_btn_layout)

        layout.addWidget(model_group)
