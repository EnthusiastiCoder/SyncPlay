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
