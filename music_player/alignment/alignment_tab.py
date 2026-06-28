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

        # -- Audio file selection --
        audio_group = QGroupBox("Audio File")
        audio_layout = QHBoxLayout(audio_group)
        self._btn_browse_audio = QPushButton("Browse...")
        self._btn_browse_audio.setFixedWidth(100)
        self._audio_label = QLabel("No audio file selected")
        self._audio_label.setWordWrap(True)
        audio_layout.addWidget(self._btn_browse_audio)
        audio_layout.addWidget(self._audio_label, stretch=1)
        layout.addWidget(audio_group)

        # -- Transcript input --
        transcript_group = QGroupBox("Transcript")
        transcript_layout = QVBoxLayout(transcript_group)
        transcript_layout.setSpacing(8)

        transcript_btn_layout = QHBoxLayout()
        self._btn_browse_transcript = QPushButton("Load from File...")
        self._btn_clear_transcript = QPushButton("Clear")
        self._btn_auto_fetch = QPushButton("Auto-fetch Lyrics")
        self._btn_auto_fetch.setToolTip("Fetch lyrics from lrclib.net using the loaded audio's metadata")
        transcript_btn_layout.addWidget(self._btn_browse_transcript)
        transcript_btn_layout.addWidget(self._btn_clear_transcript)
        transcript_btn_layout.addWidget(self._btn_auto_fetch)
        transcript_btn_layout.addStretch()
        transcript_layout.addLayout(transcript_btn_layout)

        self._transcript_edit = QTextEdit()
        self._transcript_edit.setPlaceholderText("Paste or load the transcript text here...")
        self._transcript_edit.setMinimumHeight(120)
        transcript_layout.addWidget(self._transcript_edit)
        layout.addWidget(transcript_group)

        # -- Model + Language selection --
        model_group = QGroupBox("Model & Language")
        model_grid = QGridLayout(model_group)
        model_grid.setSpacing(8)
        model_grid.setColumnStretch(1, 1)
        model_grid.setColumnStretch(3, 1)
