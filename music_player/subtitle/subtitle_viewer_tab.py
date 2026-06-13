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
