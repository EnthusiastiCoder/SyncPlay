"""Subtitle Viewer tab for viewing and managing .wlrc files."""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTextEdit, QMessageBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from music_player.config import ConfigManager
from music_player.models.wlrc import load_wlrc, WlrcData
from music_player.models.wlrc_embed import extract_wlrc_from_mp3, has_embedded_wlrc


class SubtitleViewerTab(QWidget):
    """Tab for viewing and managing WLRC subtitle files."""
    
    load_in_player_requested = pyqtSignal(str, object)  # audio_path, wlrc_data
    
    def __init__(self, config: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config
        self._current_wlrc: Optional[WlrcData] = None
        self._current_file_path: Optional[str] = None
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Subtitle Viewer")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #89b4fa;")
        layout.addWidget(title)
        
        # File info group
        info_group = QGroupBox("File Information")
        info_layout = QVBoxLayout(info_group)
        
        self._file_label = QLabel("No file loaded")
        self._file_label.setWordWrap(True)
        info_layout.addWidget(self._file_label)
        
        self._metadata_label = QLabel("")
        self._metadata_label.setWordWrap(True)
        info_layout.addWidget(self._metadata_label)
        
        layout.addWidget(info_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self._btn_open_wlrc = QPushButton("Open .wlrc File")
        self._btn_open_wlrc.clicked.connect(self._open_wlrc_file)
        button_layout.addWidget(self._btn_open_wlrc)
        
        self._btn_open_mp3 = QPushButton("Extract from MP3")
        self._btn_open_mp3.clicked.connect(self._extract_from_mp3)
        button_layout.addWidget(self._btn_open_mp3)
        
        self._btn_load_player = QPushButton("Load in Player")
        self._btn_load_player.clicked.connect(self._load_in_player)
        self._btn_load_player.setEnabled(False)
        button_layout.addWidget(self._btn_load_player)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Subtitle table
        table_group = QGroupBox("Subtitle Lines")
        table_layout = QVBoxLayout(table_group)
        
        self._subtitle_table = QTableWidget()
        self._subtitle_table.setColumnCount(4)
        self._subtitle_table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        self._subtitle_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._subtitle_table.setAlternatingRowColors(True)
        self._subtitle_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._subtitle_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_layout.addWidget(self._subtitle_table)
        
        layout.addWidget(table_group)
        
        # Word details
        word_group = QGroupBox("Word-Level Timing (Selected Line)")
        word_layout = QVBoxLayout(word_group)
        
        self._word_text = QTextEdit()
        self._word_text.setReadOnly(True)
        self._word_text.setMaximumHeight(150)
        self._word_text.setFont(QFont("Consolas", 9))
        word_layout.addWidget(self._word_text)
        
        layout.addWidget(word_group)
        
        # Connect table selection
        self._subtitle_table.itemSelectionChanged.connect(self._on_line_selected)
    
    def _open_wlrc_file(self):
        """Open a .wlrc file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open WLRC File",
            self._config.get("last_directory", ""),
            "WLRC Files (*.wlrc);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        self._config.set("last_directory", str(Path(file_path).parent))
        self._config.save()
        
        try:
            wlrc = load_wlrc(file_path)
            self._load_wlrc(wlrc, file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load WLRC file: {e}")
    
    def _extract_from_mp3(self):
        """Extract embedded WLRC from an MP3 file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open MP3 File",
            self._config.get("last_directory", ""),
            "MP3 Files (*.mp3);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        self._config.set("last_directory", str(Path(file_path).parent))
        self._config.save()
        
        try:
            if not has_embedded_wlrc(file_path):
                QMessageBox.information(
                    self, "No WLRC Data",
                    "This MP3 file does not contain embedded WLRC data."
                )
                return
            
            wlrc = extract_wlrc_from_mp3(file_path)
            if wlrc:
                self._load_wlrc(wlrc, file_path)
            else:
                QMessageBox.warning(self, "Error", "Failed to extract WLRC data from MP3.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract WLRC: {e}")
    
    def _load_wlrc(self, wlrc: WlrcData, file_path: str):
        """Load WLRC data into the viewer."""
        self._current_wlrc = wlrc
        self._current_file_path = file_path
        
        # Update file info
        self._file_label.setText(f"File: {Path(file_path).name}")
        
        # Update metadata
        duration_sec = wlrc.metadata.duration_ms / 1000.0
        metadata_text = f"Duration: {duration_sec:.2f}s | Lines: {len(wlrc.lines)}"
        self._metadata_label.setText(metadata_text)
        
        # Populate table
        self._subtitle_table.setRowCount(len(wlrc.lines))
        for i, line in enumerate(wlrc.lines):
            # Line number
            self._subtitle_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # Start time
            start_sec = line.start_ms / 1000.0
            self._subtitle_table.setItem(i, 1, QTableWidgetItem(f"{start_sec:.3f}s"))
            
            # End time
            end_sec = line.end_ms / 1000.0
            self._subtitle_table.setItem(i, 2, QTableWidgetItem(f"{end_sec:.3f}s"))
            
            # Text
            self._subtitle_table.setItem(i, 3, QTableWidgetItem(line.text))
        
        self._subtitle_table.resizeColumnsToContents()
        self._btn_load_player.setEnabled(True)
        self._word_text.clear()
    
    def _on_line_selected(self):
        """Show word-level timing for selected line."""
        selected_rows = self._subtitle_table.selectionModel().selectedRows()
        if not selected_rows or not self._current_wlrc:
            self._word_text.clear()
            return
        
        row = selected_rows[0].row()
        if 0 <= row < len(self._current_wlrc.lines):
            line = self._current_wlrc.lines[row]
            
            if line.has_word_timing():
                word_details = []
                for word in line.words:
                    start_sec = word.start_ms / 1000.0
                    end_sec = word.end_ms / 1000.0
                    duration = (word.end_ms - word.start_ms) / 1000.0
                    word_details.append(
                        f"{word.word:20s} | {start_sec:8.3f}s - {end_sec:8.3f}s | {duration:6.3f}s"
                    )
                self._word_text.setPlainText("\n".join(word_details))
            else:
                self._word_text.setPlainText("No word-level timing available for this line.")
    
    def _load_in_player(self):
        """Load the current WLRC in the player."""
        if not self._current_wlrc or not self._current_file_path:
            return
        
        # Try to find the associated audio file
        file_path = Path(self._current_file_path)
        
        # If it's a .wlrc file, look for audio with same name
        if file_path.suffix.lower() == '.wlrc':
            audio_path = None
            for ext in ['.mp3', '.wav', '.ogg', '.flac']:
                candidate = file_path.with_suffix(ext)
                if candidate.exists():
                    audio_path = str(candidate)
                    break
            
            if not audio_path:
                QMessageBox.warning(
                    self, "Audio Not Found",
                    "Could not find audio file with the same name as the .wlrc file."
                )
                return
        else:
            # It's an MP3 file with embedded WLRC
            audio_path = str(file_path)
        
        self.load_in_player_requested.emit(audio_path, self._current_wlrc)
        QMessageBox.information(
            self, "Loaded",
            f"Loaded in player:\n{Path(audio_path).name}"
        )
