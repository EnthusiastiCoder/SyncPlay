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
