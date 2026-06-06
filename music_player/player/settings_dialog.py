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

        # -- Dialog buttons --
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._btn_apply = QPushButton("Apply")
        self._btn_ok = QPushButton("OK")
        self._btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(self._btn_apply)
        btn_layout.addWidget(self._btn_ok)
        btn_layout.addWidget(self._btn_cancel)
        layout.addLayout(btn_layout)

        # Connect
        self._btn_apply.clicked.connect(self._apply)
        self._btn_ok.clicked.connect(self._ok)
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_delete_model.clicked.connect(self._delete_model)

        # Sync color button ↔ hex edit
        self._played_color_btn.clicked.connect(
            lambda: self._played_color_edit.setText(self._played_color_btn.color_hex)
        )
        self._unplayed_color_btn.clicked.connect(
            lambda: self._unplayed_color_edit.setText(self._unplayed_color_btn.color_hex)
        )
        self._played_color_edit.editingFinished.connect(self._sync_played_color_from_edit)
        self._unplayed_color_edit.editingFinished.connect(self._sync_unplayed_color_from_edit)

    def _sync_played_color_from_edit(self) -> None:
        hex_val = self._played_color_edit.text().strip()
        if QColor(hex_val).isValid():
            self._played_color_btn.color_hex = hex_val
        else:
            self._played_color_edit.setText(self._played_color_btn.color_hex)

    def _sync_unplayed_color_from_edit(self) -> None:
        hex_val = self._unplayed_color_edit.text().strip()
        if QColor(hex_val).isValid():
            self._unplayed_color_btn.color_hex = hex_val
        else:
            self._unplayed_color_edit.setText(self._unplayed_color_btn.color_hex)

    def _load_from_config(self) -> None:
        """Load current config values into the UI."""
        played = self._config.get("played_color", "#00FF00")
        unplayed = self._config.get("unplayed_color", "#FFFFFF")
        self._played_color_btn.color_hex = played
        self._played_color_edit.setText(played)
        self._unplayed_color_btn.color_hex = unplayed
        self._unplayed_color_edit.setText(unplayed)

        font_family = self._config.get("font_family", "Segoe UI")
        self._font_combo.setCurrentFont(self._font_combo.currentFont())
        # Find and set the font
        idx = self._font_combo.findText(font_family)
        if idx >= 0:
            self._font_combo.setCurrentIndex(idx)

        self._font_size_spin.setValue(self._config.get("font_size_base", 28))
        self._side_ratio_spin.setValue(self._config.get("font_ratio_side_lines", 0.75))

        self._overlay_x_spin.setValue(self._config.get("overlay_x", 100))
        self._overlay_y_spin.setValue(self._config.get("overlay_y", 800))
        self._overlay_h_spin.setValue(self._config.get("overlay_height", 200))

        self._refresh_model_list()

    def _refresh_model_list(self) -> None:
        cached = self._model_manager.cached_models()
        if cached:
            total_mb = self._model_manager.cache_size_mb()
            self._model_list_label.setText(
                f"Cached models: {', '.join(cached)} ({total_mb:.0f} MB total)"
            )
        else:
            self._model_list_label.setText("No cached models.")

    def _apply(self) -> None:
        """Apply settings to config (live update)."""
        # Validate hex colors
        played_hex = self._played_color_edit.text().strip()
        unplayed_hex = self._unplayed_color_edit.text().strip()
