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

    # -- File browsing --

    def _browse_audio(self) -> None:
        last_dir = self._config.get("last_directory", "")
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", last_dir, f"Audio Files ({exts})"
        )
        if path:
            self._audio_path = path
            self._audio_label.setText(path)
            self._config.set("last_directory", str(Path(path).parent))
            self._config.save()

    def _auto_fetch_lyrics(self) -> None:
        """Fetch lyrics from lrclib.net using the loaded audio file's metadata."""
        if not self._audio_path:
            QMessageBox.warning(self, "No Audio File", "Please select an audio file first.")
            return

        self._btn_auto_fetch.setEnabled(False)
        self._btn_auto_fetch.setText("Fetching...")
        try:
            from music_player.alignment.lrclib_client import extract_audio_metadata, fetch_lyrics

            meta = extract_audio_metadata(self._audio_path)
            title = meta.get("title", "")
            artist = meta.get("artist", "")
            album = meta.get("album", "")
            duration = meta.get("duration_sec", 0.0)

            if not title:
                QMessageBox.warning(
                    self, "No Metadata",
                    "Could not read track metadata from file. Please fill in the transcript manually."
                )
                return

            result = fetch_lyrics(title, artist, album, duration)

            if result is None or not result.get("plainLyrics"):
                self._status_label.setText(
                    f"No lyrics found on lrclib.net for '{title}'"
                    + (f" by {artist}" if artist else "")
                )
                return

            self._transcript_edit.setPlainText(result["plainLyrics"])
            self._status_label.setText(
                f"Fetched lyrics from lrclib.net for '{title}'"
                + (f" by {artist}" if artist else "")
            )

        except Exception as e:
            self._status_label.setText(f"Failed to fetch lyrics: {e}")
        finally:
            self._btn_auto_fetch.setEnabled(True)
            self._btn_auto_fetch.setText("Auto-fetch Lyrics")

    def _browse_transcript(self) -> None:
        last_dir = self._config.get("last_directory", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Transcript File", last_dir, "Text Files (*.txt *.lrc *.srt);;All Files (*)"
        )
        if path:
            try:
                raw = Path(path).read_text(encoding="utf-8")
                if path.lower().endswith(".srt"):
                    raw = self._parse_srt_to_text(raw)
                self._transcript_edit.setPlainText(raw)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to read file: {e}")

    @staticmethod
    def _parse_srt_to_text(srt_content: str) -> str:
        """Extract plain text from SRT subtitle format."""
        lines = []
        for line in srt_content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            if "-->" in line:
                continue
            if line.startswith("[") and line.endswith("]"):
                continue
            lines.append(line)
        return " ".join(lines)

    # -- Alignment --

    def _start_alignment(self) -> None:
        if not self._audio_path:
            QMessageBox.warning(self, "Missing Input", "Please select an audio file.")
            return

        transcript = self._transcript_edit.toPlainText().strip()
        if not transcript:
            QMessageBox.warning(self, "Missing Input", "Please provide a transcript.")
            return

        model_name = self._model_combo.currentData()
        language = self._lang_combo.currentData() or self._lang_combo.currentText().strip()
        
        # For MP3 files, WLRC gets embedded directly — use a temp sidecar path
        is_mp3 = self._audio_path.lower().endswith('.mp3')
        
        if is_mp3:
            # Temporary sidecar path (will be deleted after embedding)
            audio_stem = Path(self._audio_path).stem
            output_path = str(Path(self._audio_path).parent / f"{audio_stem}_aligned.wlrc")
        else:
            # Non-MP3: show Save As dialog
            audio_stem = Path(self._audio_path).stem
            default_name = f"{audio_stem}_aligned.wlrc"
            default_dir = str(Path(self._audio_path).parent / default_name)
            
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Aligned Lyrics",
                default_dir,
                "WLRC Files (*.wlrc);;All Files (*)",
            )
            if not output_path:
                return  # User cancelled

        # Save language preference
        self._config.set("alignment_language", language)
        self._config.save()

        self._worker = AlignmentWorker(
            audio_path=self._audio_path,
            transcript=transcript,
            model_name=model_name,
            language=language,
            output_path=output_path,
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)

        self._set_running_state(True)
        self._worker.start()

    def _cancel_alignment(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.quit()
            self._worker.wait(3000)
            self._status_label.setText("Alignment cancelled.")
            self._set_running_state(False)
