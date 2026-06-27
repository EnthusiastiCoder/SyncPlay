"""Alignment Tool tab UI for forced-aligning transcripts to audio."""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTextEdit, QComboBox, QProgressBar, QMessageBox,
    QGroupBox, QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from music_player.config import ConfigManager
from music_player.alignment.aligner import AlignmentWorker
from music_player.alignment.model_manager import ModelManager, MODEL_INFO
from music_player.audio.engine import SUPPORTED_EXTENSIONS
from music_player.models.wlrc import load_wlrc
from music_player.models.wlrc_embed import embed_wlrc_in_mp3


class AlignmentTab(QWidget):
    """Tab for aligning transcripts to audio using stable-ts."""

    open_in_player_requested = pyqtSignal(str, str)  # audio_path, wlrc_path

    def __init__(self, config: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config
        self._model_manager = ModelManager()
        self._worker: Optional[AlignmentWorker] = None
        self._audio_path: Optional[str] = None
        self._output_path: Optional[str] = None

        self._build_ui()
        self._connect_signals()
        self._refresh_model_status()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
