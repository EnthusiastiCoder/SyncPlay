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
