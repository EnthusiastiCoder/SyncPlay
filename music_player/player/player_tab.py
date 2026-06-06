"""Music Player tab UI with playback controls and playlist."""

import os
import random
from pathlib import Path
from typing import Optional
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QFileDialog, QListWidget, QListWidgetItem, QSizePolicy,
    QStyle,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class RepeatMode(Enum):
    """Repeat mode for playlist playback."""
    OFF = "off"
    ALL = "all"
    ONE = "one"

from music_player.config import ConfigManager
from music_player.audio.engine import AudioEngine, SUPPORTED_EXTENSIONS
from music_player.audio.clock import PlaybackClock
from music_player.models.wlrc import load_wlrc
from music_player.models.wlrc_embed import extract_wlrc_from_mp3
from music_player.utils.time_utils import ms_to_display
from music_player.player.widgets import ToggleSwitch
from music_player.player.visualizer_widget import VisualizerWidget


class PlayerTab(QWidget):
    """Main player tab with audio controls and playlist."""

    overlay_toggle_requested = pyqtSignal()
    wlrc_loaded = pyqtSignal(object)  # WlrcData or None

    def __init__(self, config: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config

        # Audio subsystem
        self._engine = AudioEngine(self)
        self._clock = PlaybackClock(self._engine, self)

        # Track seeking state
        self._is_seeking = False
        self._playlist: list[str] = []
        self._current_index: int = -1
        
        # Playback modes
        self._repeat_mode = RepeatMode.OFF
        self._shuffle_enabled = False
        self._shuffle_history: list[int] = []

        self._build_ui()
        self._connect_signals()
