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
