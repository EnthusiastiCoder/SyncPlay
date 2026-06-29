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

        model_grid.addWidget(QLabel("Whisper Model:"), 0, 0)
        self._model_combo = QComboBox()
        for name in ModelManager.available_models():
            info = MODEL_INFO.get(name, {})
            label = f"{name} (~{info.get('size_mb', '?')} MB)"
            self._model_combo.addItem(label, name)
        default_model = self._config.get("whisper_model_size", "base")
        idx = self._model_combo.findData(default_model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        model_grid.addWidget(self._model_combo, 0, 1)

        self._model_status_label = QLabel("")
        model_grid.addWidget(self._model_status_label, 0, 2)

        model_grid.addWidget(QLabel("Language:"), 0, 3)
        self._lang_combo = QComboBox()
        self._lang_combo.setEditable(False)
        _LANGUAGES = [
            ("en", "English"), ("hi", "Hindi"), ("es", "Spanish"),
            ("fr", "French"), ("de", "German"), ("ja", "Japanese"),
            ("ko", "Korean"), ("zh", "Chinese"), ("pt", "Portuguese"),
            ("ru", "Russian"), ("ar", "Arabic"), ("it", "Italian"),
        ]
        for code, name in _LANGUAGES:
            self._lang_combo.addItem(f"{name} ({code})", code)
        default_lang = self._config.get("alignment_language", "en")
        lang_idx = self._lang_combo.findData(default_lang)
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)
        model_grid.addWidget(self._lang_combo, 0, 4)

        layout.addWidget(model_group)

        # -- Align button + progress --
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        self._btn_align = QPushButton("Align")
        self._btn_align.setFixedWidth(100)
        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setFixedWidth(80)
        self._btn_cancel.setEnabled(False)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate
        self._progress_bar.setVisible(False)

        action_layout.addWidget(self._btn_align)
        action_layout.addWidget(self._btn_cancel)
        action_layout.addWidget(self._progress_bar, stretch=1)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # -- Status / output --
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # -- Output + open in player --
        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout(output_group)
        self._output_label = QLabel("No output yet.")
        self._output_label.setWordWrap(True)
        self._btn_open_in_player = QPushButton("Open in Player")
        self._btn_open_in_player.setEnabled(False)
        self._btn_open_in_player.setFixedWidth(120)
        output_layout.addWidget(self._output_label, stretch=1)
        output_layout.addWidget(self._btn_open_in_player)
        layout.addWidget(output_group)

        layout.addStretch()

    def _connect_signals(self) -> None:
        self._btn_browse_audio.clicked.connect(self._browse_audio)
        self._btn_browse_transcript.clicked.connect(self._browse_transcript)
        self._btn_clear_transcript.clicked.connect(self._transcript_edit.clear)
        self._btn_auto_fetch.clicked.connect(self._auto_fetch_lyrics)
        self._btn_align.clicked.connect(self._start_alignment)
        self._btn_cancel.clicked.connect(self._cancel_alignment)
        self._btn_open_in_player.clicked.connect(self._on_open_in_player)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)

    def _refresh_model_status(self) -> None:
        name = self._model_combo.currentData()
        if name and self._model_manager.is_model_cached(name):
            self._model_status_label.setText("Cached")
            self._model_status_label.setStyleSheet("color: green;")
        else:
            self._model_status_label.setText("Will download on first use")
            self._model_status_label.setStyleSheet("color: orange;")

    def _on_model_changed(self) -> None:
        name = self._model_combo.currentData()
        if name:
            self._config.set("whisper_model_size", name)
            self._config.save()
        self._refresh_model_status()
